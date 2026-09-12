#!/usr/bin/env python3
"""W085-CANDIDATE-CLASSSEP-DIFF-03 — read-only differential audit of the staged
class-separation candidate detector.

Question
--------
At the pinned revision, does swapping the canonical detector
`research_map/class_separation.py` (sha256 c266dbceca87) for the staged candidate
`proposed/class_separation.py` (sha256 e2d24b927ee8, worker-16 CANDIDATE-PATCH.md)
change any class-separation finding on the live map / live artifact surfaces?
In particular: does the staged patch clear the live hard CLASSSEP findings that the
controller evidence audit routes from `claims[i].statement` (CF-16 class)?

Method
------
Freeze-first, read-only.  Both modules are loaded by file location with bytecode
writes disabled; the frozen map snapshot and frozen artifact snapshots are the
measured inputs.  The audit routing of `research_map/audit_evidence.py` section 3 is
replicated exactly:

    findings_for_map(map)                          -> hard unless "CLASSSEP-SOFT:"
    findings_for_text(node artifact text, ...)     -> same routing, files < 2 MB

A labeled synthetic battery attributes any behavioral delta to a specific hunk of the
candidate patch, and `class_separation.regression()` scores both modules against the
worker-07 27-fixture corpus.  No canonical file is written; the report is written next
to this script unless --out points elsewhere.

Exit codes: 0 = every check matched the recorded expectation; 1 = a check failed;
3 = a pinned input drifted (measurement window void).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SNAP = HERE / "snapshot"

CANONICAL_LIVE = REPO / "research_map/class_separation.py"
PROPOSED_LIVE = REPO / "proposed/class_separation.py"
MAP_LIVE = REPO / "research_map/research_map.json"
CORPUS_REL = "artifacts/worker-07/class_separation_falsification"

# Frozen pins taken at task freeze time (2026-09-12T00:38+08:00).
PINS = {
    "research_map/class_separation.py": {
        "sha256": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "snapshot": "snapshot/class_separation.canonical.py",
    },
    "proposed/class_separation.py": {
        "sha256": "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
        "snapshot": "snapshot/class_separation.proposed.py",
    },
    "research_map/research_map.json": {
        "sha256": "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005",
        "snapshot": "snapshot/research_map.json",
    },
    "runtime/bin/classsep_regression.py": {
        "sha256": "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091",
        "snapshot": "snapshot/classsep_regression.py",
    },
    "artifacts/worker-07/class_separation_falsification/results.json": {
        "sha256": "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
        "snapshot": "snapshot/worker07_results.json",
    },
}

# Labeled synthetic battery: (id, kind, payload, mode, expected_canonical_n, expected_proposed_n)
BATTERY = [
    ("S1_decl_statement_bare", "obj", {"statement": "the C0 or C2 regularities are recorded"},
     "declaration", 1, 0),
    ("S2_decl_statement_merge_assert", "obj", {"statement": "C0 and C2 are one class"},
     "declaration", 1, 1),
    ("S3_decl_label_negated_split", "obj", {"label": "do not split: C0 or C2 regularity"},
     "declaration", 0, 1),
    ("S4_prose_statement_live_shape", "obj",
     {"statement": "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities)"}, "prose", 1, 1),
    ("S5_decl_label_bare", "obj", {"label": "C0 or C2 regularity"}, "declaration", 1, 1),
    ("S6_decl_statement_unknown_4seg", "obj", {"statement": "see AF-WCC-VAC-BH"},
     "declaration", 0, 0),
    ("S7_artifact_text_merge_shape", "text", "TC-F0-N14 merged C0/C2 regularities", None, 1, 1),
    ("S8_decl_statement_list_bare", "obj", {"statement": ["the C0 or C2 regularities are recorded"]},
     "declaration", 1, 0),
    ("S9_decl_statement_live_shape", "obj",
     {"statement": "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities)"}, "declaration", 1, 1),
    ("S10_decl_statement_prohibited", "obj", {"statement": "avoid writing 'C0 or C2' anywhere"},
     "declaration", 0, 0),
    ("S11_artifact_text_bare_no_assert", "text", "the C0 or C2 regularities are recorded", None, 0, 0),
    ("S12_artifact_text_unknown_5seg", "text", "class_id: AF-WCC-VAC-BH-FORM", None, 1, 1),
]

FROZEN_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def route(items) -> tuple[list, list]:
    """Replicate audit_evidence.py section 3 severity routing."""
    hard, soft = [], []
    for it in items:
        (soft if str(it).startswith("CLASSSEP-SOFT:") else hard).append(str(it))
    return hard, soft


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "report.json")
    ap.add_argument("--repo", type=Path, default=REPO)
    args = ap.parse_args()
    repo = args.repo.resolve()
    sys.dont_write_bytecode = True

    checks: list[dict] = []

    def check(name: str, expected, observed) -> bool:
        ok = expected == observed
        checks.append({"check": name, "expected": expected, "observed": observed, "pass": ok})
        return ok

    # ---- 0. freeze checks -------------------------------------------------
    pins_record = {}
    frozen_ok = True
    for rel, spec in PINS.items():
        live = repo / rel
        snap = HERE / spec["snapshot"]
        rec = {"path": rel, "pinned_sha256": spec["sha256"], "snapshot": spec["snapshot"]}
        rec["snapshot_sha256"] = sha256_file(snap) if snap.is_file() else None
        rec["live_sha256"] = sha256_file(live) if live.is_file() else None
        rec["snapshot_matches_pin"] = rec["snapshot_sha256"] == spec["sha256"]
        rec["live_matches_pin"] = rec["live_sha256"] == spec["sha256"]
        pins_record[rel] = rec
        frozen_ok &= rec["snapshot_matches_pin"]
    check("all snapshot copies match their pinned sha256", True, frozen_ok)
    if not frozen_ok:
        print("PIN DRIFT: snapshot copy does not match pin", file=sys.stderr)
        return 3

    # Load the two detectors from the live paths (hash-asserted); corpus paths inside
    # regression() resolve against the real repo root only from these locations.
    if not pins_record["research_map/class_separation.py"]["live_matches_pin"] or \
       not pins_record["proposed/class_separation.py"]["live_matches_pin"]:
        print("PIN DRIFT: detector live bytes differ from pinned revision", file=sys.stderr)
        return 3
    canon = load_module("w085_canon", CANONICAL_LIVE)
    prop = load_module("w085_prop", PROPOSED_LIVE)

    map_snap = SNAP / "research_map.json"
    m = json.loads(map_snap.read_text())

    # ---- 1. live map differential ----------------------------------------
    canon_map = [str(x) for x in canon.findings_for_map(m)]
    prop_map = [str(x) for x in prop.findings_for_map(m)]
    check("live map findings identical between canonical and candidate",
          canon_map, prop_map)
    origin_counts: dict[str, int] = {}
    for x in canon_map:
        key = "claims" if ".claims[" in x or " in claims[" in x else "other"
        origin_counts[key] = origin_counts.get(key, 0) + 1
    canon_map_hard, canon_map_soft = route(canon_map)
    prop_map_hard, prop_map_soft = route(prop_map)
    check("live map hard count unchanged by candidate",
          len(canon_map_hard), len(prop_map_hard))
    check("live map soft count unchanged by candidate",
          len(canon_map_soft), len(prop_map_soft))
    check("all live map findings originate on claims[*].statement (prose path)",
          len(canon_map), origin_counts.get("claims", 0))

    # ---- 2. live artifact differential (audit routing, snapshot bytes) ----
    art_dir = SNAP / "live_artifacts"
    canon_art, prop_art, scanned = [], [], []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            rel = n.get("artifact")
            if not rel:
                continue
            live = repo / rel
            snap = art_dir / rel
            if not (live.is_file() and live.stat().st_size < 2_000_000):
                continue
            if not snap.is_file():
                continue
            text = snap.read_text(errors="replace")
            where = f"{n['id']} artifact {rel}"
            canon_art += [str(x) for x in canon.findings_for_text(text, where)]
            prop_art += [str(x) for x in prop.findings_for_text(text, where)]
            scanned.append({"node": n["id"], "artifact": rel, "snapshot_sha256": sha256_file(snap)})
    check("live artifact findings identical between canonical and candidate",
          canon_art, prop_art)
    canon_art_hard, _ = route(canon_art)
    prop_art_hard, _ = route(prop_art)
    check("live artifact hard count unchanged by candidate",
          len(canon_art_hard), len(prop_art_hard))
    check("live artifact surface is clean for both detectors",
          0, len(canon_art))

    # ---- 3. synthetic battery --------------------------------------------
    battery = []
    battery_ok = True
    for pid, kind, payload, mode, exp_c, exp_p in BATTERY:
        if kind == "text":
            got_c = [str(x) for x in canon.findings_for_text(payload, pid)]
            got_p = [str(x) for x in prop.findings_for_text(payload, pid)]
        else:
            got_c = [str(x) for x in canon.findings(payload, pid, mode=mode)]
            got_p = [str(x) for x in prop.findings(payload, pid, mode=mode)]
        ok = (len(got_c) == exp_c and len(got_p) == exp_p)
        battery_ok &= ok
        battery.append({"id": pid, "surface": kind, "mode": mode, "input": payload,
                        "canonical": got_c, "proposed": got_p,
                        "expected_canonical_n": exp_c, "expected_proposed_n": exp_p,
                        "match": ok})
    check("synthetic battery matches recorded expectations", True, battery_ok)

    # ---- 4. attribute deltas to patch hunks ------------------------------
    cleared = [b["id"] for b in battery if b["canonical"] and not b["proposed"]]
    added = [b["id"] for b in battery if b["proposed"] and not b["canonical"]]
    check("candidate exposes the R2-3 declaration-statement hunk (bare composite cleared)",
          ["S1_decl_statement_bare", "S8_decl_statement_list_bare"], sorted(cleared))
    check("candidate exposes the R2-2 negated-split hunk (new hard flag)",
          ["S3_decl_label_negated_split"], sorted(added))
    check("candidate does NOT clear the live false-positive shape even in declaration mode",
          1, len([b for b in battery if b["id"] == "S9_decl_statement_live_shape"
                  and b["proposed"]]))

    # ---- 5. worker-07 corpus regression ----------------------------------
    reg_canon = canon.regression()
    reg_prop = prop.regression()
    check("canonical regression PASS 17/0/10/0",
          {"tp": 17, "fn": 0, "tn": 10, "fp": 0, "corpus_size": 27, "verdict": "PASS"},
          {k: reg_canon[k] for k in ("tp", "fn", "tn", "fp", "corpus_size", "verdict")})
    check("candidate regression PASS 17/0/10/0",
          {"tp": 17, "fn": 0, "tn": 10, "fp": 0, "corpus_size": 27, "verdict": "PASS"},
          {k: reg_prop[k] for k in ("tp", "fn", "tn", "fp", "corpus_size", "verdict")})

    # ---- 6. tokenizer-window control -------------------------------------
    sens = {}
    for mod_name, mod in (("canonical", canon), ("proposed", prop)):
        matched = [t for t in FROZEN_IDS if mod._class_tokens(t)]
        sens[mod_name] = {"frozen_ids_matched": matched, "frozen_sensitivity": f"{len(matched)}/4",
                          "four_seg_unknown_token": mod._class_tokens("AF-WCC-VAC-BH"),
                          "three_seg_unknown_token": mod._class_tokens("AF-SCC-OTHER-MODELS")}
    check("both detectors carry the same 2/4 frozen-id tokenizer window",
          sens["canonical"], sens["proposed"])
    check("candidate does not fix the tokenizer window",
          {"frozen_sensitivity": "2/4", "four_seg_unknown_token": []},
          {"frozen_sensitivity": sens["proposed"]["frozen_sensitivity"],
           "four_seg_unknown_token": sens["proposed"]["four_seg_unknown_token"]})

    # ---- 7. drift check ---------------------------------------------------
    drift = {}
    for rel in PINS:
        live = repo / rel
        now = sha256_file(live) if live.is_file() else None
        drift[rel] = {"start": pins_record[rel]["live_sha256"], "end": now,
                      "changed": pins_record[rel]["live_sha256"] != now}
    drifted = [k for k, v in drift.items() if v["changed"]]

    all_ok = all(c["pass"] for c in checks)
    live_inert = canon_map == prop_map and canon_art == prop_art
    hard_unchanged = len(canon_map_hard) + len(canon_art_hard) == \
        len(prop_map_hard) + len(prop_art_hard)
    verdict = ("CANDIDATE_LIVE_INERT_HARD_COUNT_UNCHANGED"
               if (live_inert and hard_unchanged and all_ok)
               else "MEASUREMENT_MISMATCH")

    report = {
        "schema_version": "1.0",
        "task_id": "W085-CANDIDATE-CLASSSEP-DIFF-03",
        "actor": "worker-085",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": "G-F0",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": FROZEN_IDS,
        "claims_theorem_status": False,
        "completion_claim": False,
        "authority_note": ("Worker evidence only: a checker-differential measurement. It sets no gate "
                           "verdict, no node status and no validation_status, and it edits no canonical file."),
        "question": ("Does the staged candidate detector proposed/class_separation.py (e2d24b927ee8) "
                     "change any class-separation finding on the live map / live artifact surfaces "
                     "relative to canonical research_map/class_separation.py (c266dbceca87), and does "
                     "it clear the live hard CLASSSEP findings routed from claims[i].statement?"),
        "pinned_inputs": pins_record,
        "pins_note": ("The map snapshot 3d45be59 and the artifact snapshots bind the measurement. "
                      "ledger/theorems.jsonl moved before freeze (live ce42d205e761 at the controller's "
                      "00:33 checkpoint -> snapshot a1674f09 at freeze); that moving target is pinned "
                      "here and named in scope_limits."),
        "detector_pair": {
            "canonical": {"path": "research_map/class_separation.py",
                          "sha256": PINS["research_map/class_separation.py"]["sha256"]},
            "candidate": {"path": "proposed/class_separation.py",
                          "sha256": PINS["proposed/class_separation.py"]["sha256"]},
            "candidate_origin": ("artifacts/worker-16/audit_calibration/CANDIDATE-PATCH.md + "
                                 "detector_fixes.patch (staged, not applied)"),
        },
        "live_map_differential": {
            "map_sha256": PINS["research_map/research_map.json"]["sha256"],
            "canonical_findings": canon_map,
            "candidate_findings": prop_map,
            "removed_by_candidate": sorted(set(canon_map) - set(prop_map)),
            "added_by_candidate": sorted(set(prop_map) - set(canon_map)),
            "canonical_hard": len(canon_map_hard),
            "canonical_soft": len(canon_map_soft),
            "candidate_hard": len(prop_map_hard),
            "candidate_soft": len(prop_map_soft),
            "origin_counts": origin_counts,
            "note": ("findings_for_map scans claims with mode='prose' in both revisions; the candidate's "
                     "R2-3 hunk only changes mode selection for declaration-mode call sites."),
        },
        "live_artifact_differential": {
            "scanned": scanned,
            "canonical_findings": canon_art,
            "candidate_findings": prop_art,
            "removed_by_candidate": sorted(set(canon_art) - set(prop_art)),
            "added_by_candidate": sorted(set(prop_art) - set(canon_art)),
            "canonical_hard": len(canon_art_hard),
            "candidate_hard": len(prop_art_hard),
        },
        "audit_route_snapshot": {
            "hard_total_canonical": len(canon_map_hard) + len(canon_art_hard),
            "hard_total_candidate": len(prop_map_hard) + len(prop_art_hard),
            "explanation": ("audit_evidence.py section 3 routes class_separation results: 'CLASSSEP-SOFT:' "
                            "-> soft, everything else -> hard. Swapping in the candidate leaves this "
                            "total unchanged, so the staged patch cannot clear the live hard count."),
        },
        "probe_battery": battery,
        "latent_deltas": {
            "cleared_bare_composite_in_declaration_statement": cleared,
            "newly_flagged_negated_split": added,
            "not_cleared_live_shape_in_declaration_statement": "S9_decl_statement_live_shape",
        },
        "regression_worker07": {"canonical": reg_canon, "candidate": reg_prop},
        "tokenizer_window_control": sens,
        "drift": {"paths": drift, "changed": drifted},
        "verdict": verdict,
        "verdict_detail": (
            "The staged candidate detector is LIVE-INERT on the class-separation surfaces measured "
            "here: 0 findings removed and 0 added on the frozen live map (10 hard findings, all on "
            "claims[*].statement, prose path) and 0 findings on the 10 audited node artifact texts. "
            "Its verified behavioral deltas are latent-only and attribute to two hunks: R2-3 clears a "
            "*bare* composite in a declaration-mode `statement` (S1/S8), and R2-2 newly flags "
            "'do not split: C0 or C2' (S3). Crucially, the live false-positive shape "
            "('... merged C0/C2 ...' inside a statement) is NOT cleared by R2-3 even in declaration "
            "mode, because _MERGE_ASSERT fires in prose mode too (S9): the CF-16 hard findings require "
            "a different change (or the assigned claim rephrase), not this patch. The candidate also "
            "carries the unchanged tokenizer window (frozen-id sensitivity 2/4)."
        ),
        "falsifiers": [
            "F1 live-inert: any live map or node-artifact CLASSSEP finding removed or added by the candidate at the pinned map hash.",
            "F2 origin attribution: any live hard finding not routed from claims[*].statement via findings_for_map(mode='prose').",
            "F3 latent R2-3: a declaration-mode bare-composite `statement` (S1/S8) that the candidate does not clear.",
            "F4 latent R2-2: 'do not split: C0 or C2' that the candidate does not newly flag (S3).",
            "F5 shape coverage: the live false-positive shape in declaration mode (S9) being cleared by the candidate.",
            "F6 tokenizer control: either detector's _class_tokens matching all four frozen ids, or matching a 4-segment unknown AF-WCC token.",
            "F7 moving target: any pinned input hash changing mid-run voids the window, not the finding; restore from the snapshot copies to re-run.",
        ],
        "scope_limits": [
            "Live-inert is measured on the frozen map snapshot and the 10 audited node artifact texts; it does not bound surfaces the audit never scans (reviews/, assignments, gate_proposals), where the candidate's R2-3 hunk could still change a declaration-mode `statement`.",
            "The candidate's own claimed green calibration (worker-16 corpus) is not re-run here because that harness invokes audit_evidence.audit(), which writes canonical runtime/state/artifact_hashes.json; only the class-separation module behavior is measured.",
            "ledger/theorems.jsonl moved before freeze (ce42d205e761 -> a1674f09); the artifact differential binds the snapshot, not the controller's 00:33 measurement.",
            "Worker evidence only; the detector owner applies any checker change (CF-4).",
        ],
        "reproduce_command": "python3 artifacts/worker-085/candidate_diff/probe_candidate_diff.py",
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
    }

    payload = json.dumps(report, indent=2, sort_keys=True)
    args.out.write_text(payload)
    print(payload)
    print(f"\nchecks {report['checks_passed']}/{report['checks_total']} | verdict {verdict}",
          file=sys.stderr)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
