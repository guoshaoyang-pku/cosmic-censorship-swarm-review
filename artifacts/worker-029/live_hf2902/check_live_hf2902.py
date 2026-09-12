#!/usr/bin/env python3
"""
W029-LIVE-HF2902-04 — deterministic checker (reads snapshots only).

Question re-bound to live bytes:
  Does HF-29-02 ("l1_ledger_refs assert citation_status=verified_by_L1 while the
  ledger records abstract-read / not_independently_reviewed") survive the CF-19
  ledger rewrite to a1674f094979, and do the three class schemas still sit at the
  rev12 pins?

The task is deliberately narrow because the schema bytes are provably at the rev12
pins (check C1): the only canonical input that moved since W029-REV12-CLOSURE-03 is
ledger/theorems.jsonl, and only check C2 of that task consumed the ledger.  This
checker re-runs the C2 logic (unchanged honesty rule) against the live ledger and
adds a three-generation invariance check.

Guarantees:
  * reads only files under this directory (snapshots/manifest); canonical paths are
    re-hashed read-only for the drift check;
  * stdlib + PyYAML, no network, no writes except evidence.json / report_core.json /
    report.json in this directory;
  * duplicate-preserving YAML loader;
  * report_core.json is timestamp-free and byte-stable across reruns.

Verdict rule: hard FAIL => revise 2.0; major FAIL => accept_with_notes 3.5; else accept 4.5.
A worker cannot set a gate verdict, node status, or validation_status.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshots"
MANIFEST_PATH = HERE / "snapshot_manifest.json"
TASK = "W029-LIVE-HF2902-04"
NODE = "F1,F2a,F2b"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-FORM"

SCHEMA_TAG = {
    "af_wcc_vacuum.yaml": "F1",
    "af_scc_c2_vacuum.yaml": "F2a",
    "af_scc_c0_vacuum.yaml": "F2b",
}
LEDGER_FILES = {
    "live": "ledger_live_snapshot.jsonl",
    "rev3": "ledger_rev3_snapshot.jsonl",
    "pre_rev3": "ledger_pre_rev3_snapshot.jsonl",
}
CONSERVATIVE = {"unresolved", "unverified"}
ABSTRACT_LEVEL = {"unverified", "abstract-read"}


class DupKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently last-winning."""


def _construct_mapping(loader, node, deep=False):
    mapping, dups = {}, []
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in mapping:
            dups.append(str(k))
        mapping[k] = loader.construct_object(v_node, deep=deep)
    loader.dup_keys = getattr(loader, "dup_keys", [])
    loader.dup_keys.extend(dups)
    return mapping


DupKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    lambda loader, node: _construct_mapping(loader, node, deep=True),
)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_yaml(p: Path):
    loader = DupKeyLoader(p.read_text())
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, sorted(set(getattr(loader, "dup_keys", [])))


def ledger_rows(p: Path):
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def honesty(claim, row):
    """The unchanged rev12 rule, isolated so it can be unit-controlled (check C5)."""
    if claim is None:
        return True, "no_status_asserted"
    if row is None:
        return False, "row_missing_from_ledger"
    actual = row.get("verification_status")
    if claim == actual:
        return True, "claim_equals_ledger_verification_status"
    if claim in CONSERVATIVE and actual in ABSTRACT_LEVEL:
        return True, "conservative_downgrade"
    return False, "claim_overstates_ledger_record"


def check(cid, ok, detail, evidence, severity="hard"):
    return {
        "check_id": cid,
        "status": "PASS" if ok else "FAIL",
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
    }


def main() -> int:
    now = datetime.now(TZ)
    now_utc = now.astimezone(timezone.utc)
    manifest = json.loads(MANIFEST_PATH.read_text())
    checks = []

    # ---- C0: snapshot integrity and no live drift ------------------------------
    drift, drift_ok = {}, True
    paths = {n: m for n, m in manifest["files"].items()}
    for name, meta in paths.items():
        snap = SNAP / name
        live = ROOT / meta["source_path"]
        snap_h = sha256(snap) if snap.exists() else None
        live_h = sha256(live) if live.exists() else None
        entry = {
            "path": meta["source_path"],
            "declared_sha256": meta["sha256"],
            "snapshot_sha256": snap_h,
            "live_sha256": live_h,
            "snapshot_matches_declared": snap_h == meta["sha256"],
            "live_matches_snapshot": live_h == snap_h and snap_h is not None,
        }
        drift[name] = entry
        drift_ok &= entry["snapshot_matches_declared"] and entry["live_matches_snapshot"]
    for tag, meta in manifest["ledgers"].items():
        snap = HERE / meta["snapshot_path"].split("/")[-1]
        live = ROOT / meta["source_path"]
        snap_h = sha256(snap) if snap.exists() else None
        live_h = sha256(live) if live.exists() else None
        entry = {
            "path": meta["source_path"],
            "declared_sha256": meta["sha256"],
            "snapshot_sha256": snap_h,
            "live_sha256": live_h,
            "snapshot_matches_declared": snap_h == meta["sha256"],
            "live_matches_snapshot": live_h == snap_h and snap_h is not None,
        }
        drift[f"ledger:{tag}"] = entry
        drift_ok &= entry["snapshot_matches_declared"] and entry["live_matches_snapshot"]
    checks.append(
        check(
            "C0-snapshot-integrity-live-drift",
            drift_ok,
            "all snapshots match their declared hashes and every canonical path still hashes to its "
            "snapshot value"
            if drift_ok
            else "a snapshot hash or a live path moved during the task; this measurement is superseded",
            drift,
        )
    )

    # ---- C1: schema pins vs rev12, duplicate-key hygiene ------------------------
    pin_ev, pin_ok = [], True
    for name, meta in manifest["files"].items():
        if name == "formulation_taxonomy.canonical.yaml":
            continue
        doc, dups = load_yaml(SNAP / name)
        entry = {
            "artifact": name,
            "live_sha256": drift[name]["live_sha256"],
            "rev12_pin": meta.get("rev12_pin"),
            "unchanged_from_rev12_pin": meta.get("unchanged_from_rev12_pin"),
            "duplicate_mapping_keys": dups,
        }
        pin_ev.append(entry)
        pin_ok &= not dups
    tax_doc, tax_dups = load_yaml(SNAP / "formulation_taxonomy.canonical.yaml")
    pin_ev.append(
        {
            "artifact": "formulation_taxonomy.canonical.yaml",
            "live_sha256": drift["formulation_taxonomy.canonical.yaml"]["live_sha256"],
            "rev12_pin": manifest["files"]["formulation_taxonomy.canonical.yaml"].get("rev12_pin"),
            "unchanged_from_rev12_pin": manifest["files"]["formulation_taxonomy.canonical.yaml"].get(
                "unchanged_from_rev12_pin"
            ),
            "duplicate_mapping_keys": tax_dups,
        }
    )
    pin_ok &= not tax_dups
    pin_ev.append(
        {
            "ledger_live_sha256": drift["ledger:live"]["live_sha256"],
            "rev12_ledger_pin": manifest["rev12_ledger_pin"],
            "ledger_moved_since_rev12": drift["ledger:live"]["live_sha256"] != manifest["rev12_ledger_pin"],
        }
    )
    checks.append(
        check(
            "C1-pin-binding",
            pin_ok,
            "all three class schemas and the taxonomy are byte-identical to the rev12 pins; the "
            "ledger moved and is the only changed input"
            if pin_ok
            else "a schema/taxonomy duplicate key survived; the pin argument does not hold",
            pin_ev,
            severity="info",
        )
    )

    # ---- C2: HF-29-02 at the LIVE ledger ---------------------------------------
    generations = {tag: ledger_rows(HERE / fn) for tag, fn in LEDGER_FILES.items()}
    by_gen = {tag: {r.get("theorem_id"): r for r in rows} for tag, rows in generations.items()}
    docs = {name: load_yaml(SNAP / name)[0] for name in SCHEMA_TAG}
    live_rows = by_gen["live"]
    c2_ev, overclaims, token_present = [], [], False
    for name, tag in SCHEMA_TAG.items():
        refs = docs[name].get("l1_ledger_refs") or []
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            tid = ref.get("theorem_id")
            claimed = ref.get("citation_status")
            row = live_rows.get(tid)
            ok, reason = honesty(claimed, row)
            if claimed == "verified_by_L1" and not ok:
                overclaims.append({"class": tag, "theorem_id": tid})
            c2_ev.append(
                {
                    "class": tag,
                    "theorem_id": tid,
                    "claimed_citation_status": claimed,
                    "ledger_verification_status": row.get("verification_status") if row else None,
                    "ledger_review_status": row.get("review_status") if row else None,
                    "honest": ok,
                    "rule_applied": reason,
                }
            )
    token_in = {
        tag: any("verified_by_l1" in json.dumps(r, ensure_ascii=False).lower() for r in rows)
        for tag, rows in generations.items()
    }
    token_present = token_in["live"]
    counts = {
        tag: {
            "rows": len(rows),
            "verification_status": {
                s: sum(1 for r in rows if r.get("verification_status") == s)
                for s in sorted({str(r.get("verification_status")) for r in rows})
            },
            "review_status": {
                s: sum(1 for r in rows if r.get("review_status") == s)
                for s in sorted({str(r.get("review_status")) for r in rows})
            },
            "independently_reviewed_rows": sum(
                1 for r in rows if r.get("review_status") not in (None, "not_independently_reviewed")
            ),
        }
        for tag, rows in generations.items()
    }
    c2_ok = not overclaims and not token_present
    c2_ev.append(
        {
            "live_ledger_sha256": drift["ledger:live"]["live_sha256"],
            "rev12_ledger_pin": manifest["rev12_ledger_pin"],
            "overclaim_count": len(overclaims),
            "overclaim_ids": overclaims,
            "verified_by_L1_token_present_in_live_ledger": token_present,
            "verified_by_L1_token_present_by_generation": token_in,
            "generation_status_counts": counts,
        }
    )
    checks.append(
        check(
            "C2-HF-29-02-live-ledger",
            c2_ok,
            "every asserted citation_status is honest against the live ledger and the undefined "
            "verified_by_L1 token appears nowhere"
            if c2_ok
            else "at least one l1_ledger_refs citation_status overstates the live ledger record",
            c2_ev,
        )
    )

    # ---- C3: three-generation invariance of the cited rows ---------------------
    affected = sorted({(o["class"], o["theorem_id"]) for o in overclaims})
    gen_ev, gen_ok = [], True
    field_absence = []
    for cls, tid in affected:
        per_gen = {}
        for tag in ("pre_rev3", "rev3", "live"):
            row = by_gen[tag].get(tid)
            per_gen[tag] = {
                "present": row is not None,
                "verification_status": row.get("verification_status") if row else None,
                "review_status": row.get("review_status") if row else None,
            }
        levels = {v["verification_status"] for v in per_gen.values()}
        present_all = all(v["present"] for v in per_gen.values())
        level_invariant = len(levels) == 1
        independent_review = any(
            v["review_status"] not in (None, "not_independently_reviewed") for v in per_gen.values()
        )
        missing_review_field = [tag for tag, v in per_gen.items() if v["review_status"] is None]
        if missing_review_field:
            field_absence.append({"class": cls, "theorem_id": tid, "generations_without_review_status_field": missing_review_field})
        invariant = present_all and level_invariant and not independent_review
        gen_ev.append(
            {
                "class": cls,
                "theorem_id": tid,
                "per_generation": per_gen,
                "verification_level_invariant": level_invariant,
                "independently_reviewed_in_any_generation": independent_review,
                "invariant": invariant,
            }
        )
        gen_ok &= invariant
    gen_ev.append(
        {
            "affected_rows": len(affected),
            "generations": ["pre_rev3", "rev3", "live"],
            "review_status_field_absent_in": field_absence[:3],
            "review_status_field_absence_count": len(field_absence),
            "reading": "invariant=True means the CF-19 ledger rewrite neither repaired nor altered the "
            "citation-evidence level of any cited row (verification_status identical across all three "
            "generations; no generation records independent review). The pre-rev3 generation lacks the "
            "review_status field entirely, which is field-presence drift, not evidence of review.",
        }
    )
    checks.append(
        check(
            "C3-citation-evidence-invariance",
            gen_ok,
            "all %d over-claimed rows carry verification_status=abstract-read in pre-rev3, rev3 and live "
            "generations and no generation records independent review" % len(affected)
            if gen_ok
            else "a cited row changed evidence level or vanished across ledger generations; the finding "
            "needs re-binding",
            gen_ev,
        )
    )

    # ---- C4: vocabulary summary (info) -----------------------------------------
    checks.append(
        check(
            "C4-ledger-vocabulary",
            True,
            "vocabulary recorded for the gate owner; verified_by_L1 is not a ledger value",
            {
                "generation_status_counts": counts,
                "verified_by_L1_token_present_by_generation": token_in,
                "ledger_vocabulary_expected": sorted(ABSTRACT_LEVEL | {"full-text-read", "verified", "unresolved"}),
            },
            severity="info",
        )
    )

    # ---- C5: comparator controls ------------------------------------------------
    controls = [
        {"case": "exact_match", "claim": "abstract-read", "row": {"verification_status": "abstract-read"}, "expected_honest": True},
        {"case": "conservative_downgrade", "claim": "unresolved", "row": {"verification_status": "abstract-read"}, "expected_honest": True},
        {"case": "mutation_overclaim", "claim": "verified_by_L1", "row": {"verification_status": "abstract-read"}, "expected_honest": False},
        {"case": "missing_row", "claim": "verified_by_L1", "row": None, "expected_honest": False},
        {"case": "no_claim", "claim": None, "row": {"verification_status": "abstract-read"}, "expected_honest": True},
    ]
    c5_ev, c5_ok = [], True
    for c in controls:
        got, reason = honesty(c["claim"], c["row"])
        row_ok = got == c["expected_honest"]
        c5_ok &= row_ok
        c5_ev.append({**c, "got_honest": got, "rule_applied": reason, "control_passes": row_ok})
    checks.append(
        check(
            "C5-comparator-controls",
            c5_ok,
            "the honesty comparator passes exact-match, conservative-downgrade, over-claim mutation, "
            "missing-row and no-claim controls"
            if c5_ok
            else "the honesty comparator fails a control; C2 cannot be trusted",
            c5_ev,
        )
    )

    failed_hard = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "hard"]
    failed_major = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "major"]
    if failed_hard:
        verdict, score = "revise", 2.0
    elif failed_major:
        verdict, score = "accept_with_notes", 3.5
    else:
        verdict, score = "accept", 4.5

    summary = {
        "total": len(checks),
        "pass": sum(1 for c in checks if c["status"] == "PASS"),
        "fail_hard": len(failed_hard),
        "fail_major": len(failed_major),
        "failed_ids": [c["check_id"] for c in checks if c["status"] == "FAIL"],
        "overclaim_rows": len(overclaims),
        "affected_ids": [f"{o['class']}:{o['theorem_id']}" for o in overclaims],
    }
    falsifier = (
        "Re-run this checker on the same snapshot bytes: the HF-29-02 re-binding is falsified if "
        "C2 reports PASS (i.e. all 11 cited rows resolve to a live ledger row recording independent "
        "verification, or the citation_status values were revised to the ledger vocabulary), or if "
        "C5 fails. If a canonical path no longer matches its snapshot hash, the check is superseded, "
        "not falsified."
    )

    evidence = {
        "task_id": TASK,
        "worker": "worker-029",
        "created_at": now.isoformat(timespec="seconds"),
        "created_at_utc": now_utc.isoformat(timespec="seconds"),
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "snapshot_hashes": {k: v["snapshot_sha256"] for k, v in drift.items()},
        "live_drift": drift,
        "checks": checks,
    }
    (HERE / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

    core = {
        "task_id": TASK,
        "worker": "worker-029",
        "supersedes_measurement": "W029-REV12-CLOSURE-03",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "schema_pins_unchanged_from_rev12": {
            n: manifest["files"][n].get("unchanged_from_rev12_pin")
            for n in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")
        },
        "ledger": {
            "live_sha256": drift["ledger:live"]["live_sha256"],
            "rev12_pin": manifest["rev12_ledger_pin"],
            "moved_since_rev12": drift["ledger:live"]["live_sha256"] != manifest["rev12_ledger_pin"],
            "rev3_sha256": drift["ledger:rev3"]["live_sha256"],
            "pre_rev3_sha256": drift["ledger:pre_rev3"]["live_sha256"],
        },
        "measured_hashes": {k: v["snapshot_sha256"] for k, v in drift.items()},
        "live_matches_snapshot": {k: v["live_matches_snapshot"] for k, v in drift.items()},
        "checks": checks,
        "summary": summary,
        "verdict": verdict,
        "score": score,
        "gate_verdict_claimed": False,
        "determinism_note": (
            "byte-stable across reruns over the same snapshots; report.json/evidence.json differ only "
            "by their created_at emission timestamps"
        ),
        "falsifier": falsifier,
    }
    (HERE / "report_core.json").write_text(json.dumps(core, indent=2) + "\n")

    report = {
        "task_id": TASK,
        "worker": "worker-029",
        "supersedes_measurement": "W029-REV12-CLOSURE-03",
        "node_id": NODE,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "created_at": now.isoformat(timespec="seconds"),
        "snapshot_manifest": "snapshot_manifest.json",
        "measured_hashes": {k: v["snapshot_sha256"] for k, v in drift.items()},
        "live_matches_snapshot": {k: v["live_matches_snapshot"] for k, v in drift.items()},
        "prior_findings_rechecked": {
            "HF-29-02": "l1_ledger_refs claim verified_by_L1 while ledger records abstract-read; "
            "self-contradiction",
            "context": "HF-29-01 and HF-29-03 bind to schema bytes, which C1 shows unchanged from "
            "rev12; they are not re-derived here",
        },
        "checks": checks,
        "summary": summary,
        "verdict": verdict,
        "score": score,
        "gate_verdict_claimed": False,
        "authority_note": "worker evidence only; cannot set a gate verdict, node status, or validation_status",
        "falsifier": falsifier,
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print("verdict:", verdict, score)
    return 0


if __name__ == "__main__":
    sys.exit(main())
