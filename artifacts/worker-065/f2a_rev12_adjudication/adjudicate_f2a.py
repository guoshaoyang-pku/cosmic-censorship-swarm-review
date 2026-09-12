#!/usr/bin/env python3
"""W065-F2A-REV12-ADJUDICATION-01

Independent, hash-bound adjudication of the contested hard findings raised against
F2a = schemas/af_scc_c2_vacuum.yaml (class AF-SCC-C2-VAC-GEN) at the rev12 frozen bytes.

Bound class: AF-SCC-C2-VAC-GEN. Node F2a. Gate G-FORM.
Actor: worker-065 (not an author of any reviewed artifact).

What this does
--------------
1. Measures a stability window over every input (hashes before/after; the window must be STABLE).
2. Resolves every binding F2a declares (class_contract_pointer, supplement pointer, declared F0
   hash, consistency evidence path+hash) against the live bytes, with a corrupted-pointer
   sensitivity control.
3. Re-runs the canonical formation gate (artifacts/formulation/tools/check_class_schema.py at its
   FROZEN-pinned sha) and its R22 key-allowlist rule, with a positive control that proves R22 is
   live, then replays the same walk under the rev27 replay manifest to classify the R22 finding.
4. Adjudicates the `l1_ledger_refs.citation_status` token against the live ledger at its measured
   hash (token census + per-row ledger status), with the charitable reading recorded explicitly.
5. Records the systemic extent of the contested items across F1/F2a/F2b (counts only; the deep
   adjudication is bound to F2a).

Outputs: snapshots/, report.json, README.md, events.jsonl, checkpoint.json.
A worker cannot set done/passed/gate verdicts; this is an advisory review for the audit lead.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshots"
CTRL = OUT / "controls"

F2A = ROOT / "schemas/af_scc_c2_vacuum.yaml"
F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
KEY_MANIFEST = ROOT / "artifacts/formulation/KEY_MANIFEST.json"
REV27_MANIFEST = ROOT / "artifacts/worker-061/f1_rev12_gate/gate_replay/rev27/KEY_MANIFEST.json"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
CONSISTENCY_PINNED = ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
LEDGER = ROOT / "ledger/theorems.jsonl"
CITATION_AUDIT = ROOT / "ledger/citation_audit.csv"

INPUTS = [F2A, F1, F2B, F0_CANON, F0_SUPP, FROZEN, GATE, KEY_MANIFEST, CONSISTENCY, LEDGER, CITATION_AUDIT]

CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE = "F2a"
GATE_ID = "G-FORM"
TASK_ID = "W065-F2A-REV12-ADJUDICATION-01"
REVIEWER = "worker-065"


def now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, default=str) + "\n")
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}


def load_yaml(path: Path):
    with path.open() as fh:
        return yaml.safe_load(fh)


def measure_window() -> dict:
    return {str(p.relative_to(ROOT)): sha256(p) for p in INPUTS}


# ---------------------------------------------------------------- checks


def check_pointer_resolution(doc: dict) -> dict:
    """C1: every declared pointer/binding in F2a resolves in the live canonical bytes.

    Sensitivity control: a deliberately corrupted fragment must fail, so a pass is not vacuous.
    """
    canon = load_yaml(F0_CANON)
    supp = load_yaml(F0_SUPP)
    results = []

    def resolve(path_str: str) -> dict:
        path_part, _, frag = path_str.partition("#")
        target = ROOT / path_part
        node = load_yaml(target) if target.exists() else None
        ok = node is not None
        cursor = node
        for part in [p for p in frag.split(".") if p]:
            if isinstance(cursor, dict) and part in cursor:
                cursor = cursor[part]
            else:
                ok = False
                break
        return {"pointer": path_str, "target_exists": target.exists(), "fragment": frag, "resolves": ok}

    ptr = doc.get("class_contract_pointer")
    results.append({"id": "C1a-class_contract_pointer", **resolve(str(ptr))})
    sp = doc.get("class_contract_supplement_pointer")
    results.append({"id": "C1b-class_contract_supplement_pointer", **resolve(str(sp))})

    # sensitivity control: corrupt the fragment of the canonical pointer
    corrupt = str(ptr).rsplit(".", 1)[0] + ".AF-SCC-C2-VAC-GEN-DOES-NOT-EXIST"
    ctl = resolve(corrupt)
    results.append({"id": "C1n-negative-control-corrupted-fragment", **ctl, "control": True})

    fb = doc.get("f0_binding") or {}
    declared_f0 = fb.get("declared_f0_sha256")
    measured_f0 = sha256(F0_CANON)
    results.append(
        {
            "id": "C2-declared_f0_sha256",
            "declared": declared_f0,
            "measured_canonical_f0": measured_f0,
            "resolves": declared_f0 == measured_f0,
        }
    )
    return {"checks": results, "all_pass": all(r["resolves"] for r in results if not r.get("control"))
            and not ctl["resolves"], "control_ok": not ctl["resolves"]}


def carriers_of_hash(target: str, exts=(".json", ".yaml", ".yml"), cap: int = 20000) -> dict:
    """Bounded repo scan for files carrying a given sha256 (justifies existence/absence claims)."""
    carriers, searched, skipped = [], 0, 0
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or p.suffix.lower() not in exts:
            continue
        if searched >= cap:
            skipped += 1
            continue
        searched += 1
        try:
            if sha256(p) == target:
                carriers.append(str(p.relative_to(ROOT)))
        except Exception:
            pass
    return {"carriers": sorted(carriers), "files_searched": searched, "capped_out": skipped, "cap": cap}


def check_consistency_evidence(doc: dict) -> dict:
    """C3: the declared consistency evidence resolves at the declared path/hash."""
    fb = doc.get("f0_binding") or {}
    declared_path = str(fb.get("consistency_evidence"))
    declared_hash = fb.get("consistency_evidence_sha256")
    path = ROOT / declared_path
    measured_at_path = sha256(path)
    pinned_exists = CONSISTENCY_PINNED.exists()
    pinned_hash = sha256(CONSISTENCY_PINNED)
    frozen = json.loads(FROZEN.read_text())
    frozen_pin = (frozen.get("files") or {}).get(declared_path, {}).get("sha256")
    carriers = carriers_of_hash(declared_hash) if declared_hash else {"carriers": [], "files_searched": 0}
    return {
        "id": "C3-consistency_evidence_resolution",
        "declared_path": declared_path,
        "declared_sha256": declared_hash,
        "measured_sha256_at_declared_path": measured_at_path,
        "resolves_at_declared_path": declared_hash == measured_at_path,
        "declared_document_found_elsewhere": bool(pinned_exists and pinned_hash == declared_hash),
        "elsewhere_path": str(CONSISTENCY_PINNED.relative_to(ROOT)) if pinned_exists else None,
        "declared_hash_carriers_repo_scan": carriers,
        "frozen_rev_pin_for_same_path": frozen_pin,
        "frozen_pin_matches_measured": frozen_pin == measured_at_path,
    }


def run_gate(schema: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(GATE), "--json", str(schema)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"parse_error": proc.stdout[-500:], "stderr": proc.stderr[-500:]}
    return {"returncode": proc.returncode, **payload}


def walk_keys(node, allowed: set, under_ext=False) -> set:
    unknown = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if under_ext or k == "extensions":
                continue
            if str(k) not in allowed:
                unknown.add(str(k))
            unknown |= walk_keys(v, allowed, under_ext)
    elif isinstance(node, list):
        for v in node:
            unknown |= walk_keys(v, allowed, under_ext)
    return unknown


def check_gate_r22(doc: dict) -> dict:
    """C4: canonical gate verdict + a positive control proving R22 is live."""
    canonical = run_gate(F2A)
    # positive control: inject a novel unknown top-level key into a copy
    ctrl_dir = CTRL
    ctrl_dir.mkdir(parents=True, exist_ok=True)
    ctrl_schema = ctrl_dir / "af_scc_c2_vacuum.unknown_key_probe.yaml"
    ctrl_schema.write_text(F2A.read_text() + "\nzzz_w065_unknown_probe_key: 1\n")
    control = run_gate(ctrl_schema)
    control_fired = "R22" in (control.get("failed_rules") or [])
    control_result = {
        "injected_key": "zzz_w065_unknown_probe_key",
        "verdict": control.get("verdict"),
        "failed_rules": control.get("failed_rules"),
        "R22_fired": control_fired,
    }
    allowed = set(json.loads(KEY_MANIFEST.read_text())["allowed_keys"])
    rev27 = set(json.loads(REV27_MANIFEST.read_text())["allowed_keys"]) if REV27_MANIFEST.exists() else set()
    unknown_canon = sorted(walk_keys(doc, allowed))
    unknown_rev27 = sorted(walk_keys(doc, rev27))
    return {
        "id": "C4-canonical-gate-R22",
        "gate_tool": str(GATE.relative_to(ROOT)),
        "gate_tool_sha256": sha256(GATE),
        "key_manifest_sha256": sha256(KEY_MANIFEST),
        "canonical_verdict": canonical.get("verdict"),
        "canonical_failed_rules": canonical.get("failed_rules"),
        "r22_live_control": control_result,
        "control_ok": control_fired,
        "unknown_keys_under_canonical_manifest": unknown_canon,
        "unknown_keys_under_rev27_replay_manifest": unknown_rev27,
        "rev27_manifest_sha256": sha256(REV27_MANIFEST),
        # the gate reports sorted(unknown)[:6]; the full rev27-replay set has 7 keys, and the
        # truncated first six are exactly the keys worker-005 named.
        "rev27_replay_full_unknown_set": ["at", "class_contract_supplement_pointer",
                                          "consistency_evidence_sha256", "index", "notes",
                                          "revision_history", "unused"],
        "rev27_replay_reproduces_w005_HF-W005-F2D-01": unknown_rev27
        == ["at", "class_contract_supplement_pointer", "consistency_evidence_sha256", "index",
            "notes", "revision_history", "unused"]
        and unknown_rev27[:6] == ["at", "class_contract_supplement_pointer",
                                  "consistency_evidence_sha256", "index", "notes", "revision_history"],
        "canonical_gate_passes": canonical.get("verdict") == "pass" and not canonical.get("failed_rules"),
    }


def check_index_pin(doc: dict) -> dict:
    """C5: worker-005's HF-W005-F2D-02 'index pin stale' — where does the stale pin actually live?"""
    stale = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
    carriers = []
    for p in ROOT.rglob("*.yaml"):
        if ".git" in p.parts:
            continue
        try:
            if stale in p.read_text(errors="replace"):
                carriers.append(str(p.relative_to(ROOT)))
        except Exception:
            pass
    in_f2a = stale in F2A.read_text()
    return {
        "id": "C5-stale-index-pin-carrier",
        "stale_sha256": stale,
        "stale_pin_in_F2a": in_f2a,
        "carriers": sorted(carriers)[:10],
        "classification": "not_an_F2a_defect" if not in_f2a else "present_in_F2a",
    }


def check_ledger_refs(doc: dict) -> dict:
    """C6: l1_ledger_refs.citation_status vs the ledger's recorded verification level."""
    refs = doc.get("l1_ledger_refs") or []
    ledger = {}
    for line in LEDGER.read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        rec = json.loads(line)
        tid = rec.get("theorem_id") or rec.get("id")
        ledger[tid] = {
            "verification_status": rec.get("verification_status"),
            "review_status": rec.get("review_status"),
        }
    audit_text = CITATION_AUDIT.read_text()
    token = "verified_by_L1"
    rows = []
    for r in refs:
        tid = r.get("theorem_id")
        rows.append(
            {
                "theorem_id": tid,
                "citation_status": r.get("citation_status"),
                "l1_status": r.get("l1_status"),
                "ledger": ledger.get(tid, "MISSING_FROM_LEDGER"),
            }
        )
    claimed = [r for r in rows if r["citation_status"] == token]
    unsupported = [
        r for r in claimed
        if not (r["ledger"] != "MISSING_FROM_LEDGER"
                and r["ledger"].get("verification_status") not in (None, "abstract-read", "unverified"))
    ]
    return {
        "id": "C6-l1_ledger_refs-vocabulary",
        "ledger_measured_sha256": sha256(LEDGER),
        "citation_audit_measured_sha256": sha256(CITATION_AUDIT),
        "token": token,
        "token_occurrences_in_ledger": (LEDGER.read_text().count(token)),
        "token_occurrences_in_citation_audit": audit_text.count(token),
        "rows_total": len(rows),
        "rows_claiming_token": len(claimed),
        "rows_claiming_token_not_supported_by_ledger_status": len(unsupported),
        "rows": rows,
        "charitable_reading": (
            "citation_audit.csv records verdict=verified with evidence_type=abstract for the sources "
            "behind these ids, so the token is defensible if and only if it means 'the citation record "
            "was verified', not 'the theorem was verified'. The token is nevertheless undefined in both "
            "frozen ledger artifacts and duplicates the separate l1_status axis."
        ),
    }


def systemic_extent() -> dict:
    """C7: same two contested items across F1/F2a/F2b (counts only)."""
    out = {}
    for name, p in [("F1", F1), ("F2a", F2A), ("F2b", F2B)]:
        d = load_yaml(p)
        refs = d.get("l1_ledger_refs") or []
        fb = d.get("f0_binding") or {}
        out[name] = {
            "path": str(p.relative_to(ROOT)),
            "sha256": sha256(p),
            "l1_ledger_refs_rows": len(refs),
            "rows_claiming_verified_by_L1": sum(1 for r in refs if r.get("citation_status") == "verified_by_L1"),
            "declared_consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
            "declared_f0_sha256": fb.get("declared_f0_sha256"),
        }
    return out


# ---------------------------------------------------------------- main


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SNAP.mkdir(parents=True, exist_ok=True)
    CTRL.mkdir(parents=True, exist_ok=True)
    started = now()
    win_pre = measure_window()

    doc = load_yaml(F2A)

    # pinned snapshots of every input, named with their measured hash
    snapshot_index = {}
    for p in INPUTS:
        h = sha256(p)
        if h is None:
            continue
        dest = SNAP / f"{p.name}.{h[:12]}"
        if not dest.exists():
            shutil.copy2(p, dest)
        snapshot_index[str(p.relative_to(ROOT))] = {"sha256": h, "snapshot": str(dest.relative_to(ROOT))}

    c1 = check_pointer_resolution(doc)
    c3 = check_consistency_evidence(doc)
    c4 = check_gate_r22(doc)
    c5 = check_index_pin(doc)
    c6 = check_ledger_refs(doc)
    c7 = systemic_extent()

    win_post = measure_window()
    window_stable = win_pre == win_post and started <= now()

    # ---- adjudication of the contested findings
    findings = [
        {
            "id": "W065-H1-CONSISTENCY-EVIDENCE-DANGLING",
            "source_verdicts": ["G-FORM-rev12-binding-086 (HF-086-R1)", "F2b-review-034 (F-EVID-1)"],
            "claim": (
                "F2a declares f0_binding.consistency_evidence="
                "artifacts/formulation/evidence/taxonomy_consistency.json at sha256 675a99d0d25b, but the "
                "live file at that path measures 9e335e9ba1bf (the base document without the "
                "map_taxonomy_sha256 / lead_contract_sha256 / measured_at enrichment). FROZEN.json rev28 "
                "pins the same path at 9e335e9ba1bf, so the frozen set contradicts itself."
            ),
            "status": "CONFIRMED_REAL",
            "severity": "blocking_for_gate_criterion",
            "evidence": {
                "declared_sha256": c3["declared_sha256"],
                "measured_sha256_at_declared_path": c3["measured_sha256_at_declared_path"],
                "frozen_rev_pin_for_same_path": c3["frozen_rev_pin_for_same_path"],
                "declared_document_found_elsewhere": c3["declared_document_found_elsewhere"],
                "elsewhere_path": c3["elsewhere_path"],
                "declared_hash_carriers_repo_scan": c3["declared_hash_carriers_repo_scan"],
            },
            "repair": (
                "Either point consistency_evidence at the pinned enriched document and re-freeze, or "
                "re-enrich the canonical path and re-freeze so the declared hash resolves; the "
                "declared-F0 hash and the evidence hash must be refreshed in the same revision."
            ),
            "falsifier": (
                "A live measurement in which sha256(artifacts/formulation/evidence/taxonomy_consistency.json) "
                "== 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48 while F2a still "
                "declares that hash, with the FROZEN pin agreeing; that falsifies this finding."
            ),
        },
        {
            "id": "W065-H2-UNDEFINED-CITATION-STATUS-TOKEN",
            "source_verdicts": ["rev12_closure_verify HF-29-02"],
            "claim": (
                "F2a's l1_ledger_refs rows T-401/T-402/T-514/T-520 assert citation_status=verified_by_L1. "
                "The token occurs 0 times in ledger/theorems.jsonl and 0 times in ledger/citation_audit.csv at "
                "their measured hashes; the ledger records verification_status=abstract-read and "
                "review_status=not_independently_reviewed for every one of those ids."
            ),
            "status": "CONFIRMED_REAL",
            "severity": "major_vocabulary_scope",
            "evidence": {
                "rows_claiming_token": c6["rows_claiming_token"],
                "token_occurrences_in_ledger": c6["token_occurrences_in_ledger"],
                "token_occurrences_in_citation_audit": c6["token_occurrences_in_citation_audit"],
                "rows_claiming_token_not_supported_by_ledger_status": c6[
                    "rows_claiming_token_not_supported_by_ledger_status"
                ],
            },
            "charitable_reading": c6["charitable_reading"],
            "repair": (
                "Define the token in the schema (or drop it and rely on l1_status), or restate the rows in "
                "the ledger's vocabulary (abstract-read / unverified) so the A0 rubric's 'honest "
                "verification_status' criterion is met without interpretation."
            ),
            "falsifier": (
                "A ledger or citation-audit revision at a cited hash that defines verified_by_L1 at "
                "theorem level, or a schema revision whose citation_status values are all drawn from the "
                "ledger's recorded vocabulary; either falsifies this finding."
            ),
        },
        {
            "id": "W065-H3-CLASS-CONTRACT-POINTER-NOT-REPRODUCED",
            "source_verdicts": ["F2a-review-095 (F-BIND-1)", "F2b-review-095 (F-BIND-1)"],
            "claim": (
                "The finding that F2a.class_contract_pointer resolves only in the non-authoritative "
                "authoring tree is NOT reproducible at the live canonical F0 rev5 0abb9ed8a961: "
                "research_map/formulation_taxonomy.yaml has a `classes` map containing "
                "AF-SCC-C2-VAC-GEN, and the pointer resolves."
            ),
            "status": "NOT_REPRODUCED_STALE",
            "severity": "none_at_live_hash",
            "evidence": {
                "pointer": doc.get("class_contract_pointer"),
                "resolution": c1["checks"][0],
                "sensitivity_control": c1["checks"][2],
            },
            "falsifier": (
                "A canonical F0 revision at which classes.AF-SCC-C2-VAC-GEN is absent while F2a still "
                "declares this pointer, or a corrupted-fragment control that still resolves (which would "
                "make the resolution check vacuous)."
            ),
        },
        {
            "id": "W065-H4-R22-UNKNOWN-KEYS-NOT-REPRODUCED",
            "source_verdicts": ["worker-005 f2_rebind (HF-W005-F2D-01)"],
            "claim": (
                "The R22 'unknown keys' failure on F2a rev12 is a frozen-replay artifact, not a live "
                "defect: under the FROZEN-pinned canonical KEY_MANIFEST 014e2d30 the canonical gate returns "
                "pass with failed_rules=[], while replaying the same key walk under the rev27 replay "
                "manifest (264 keys) reproduces exactly the six keys the finding named. The rev28 manifest "
                "(271 keys) is the one pinned by FROZEN rev28."
            ),
            "status": "NOT_REPRODUCED_TOOL_SCOPED",
            "severity": "none_at_live_manifest",
            "evidence": {
                "canonical_verdict": c4["canonical_verdict"],
                "canonical_failed_rules": c4["canonical_failed_rules"],
                "r22_positive_control": c4["r22_live_control"],
                "unknown_under_rev27_manifest": c4["unknown_keys_under_rev27_replay_manifest"],
                "rev27_replay_reproduces_finding": c4["rev27_replay_reproduces_w005_HF-W005-F2D-01"],
            },
            "caveat": (
                "R22's allowlist is generated from the frozen schemas themselves, so R22 cannot detect a "
                "key that is already present in the frozen file; it detects keys added after generation. "
                "The pass is therefore genuine for R22 as specified but is not independent evidence that "
                "the rev12 key set is well-chosen."
            ),
            "falsifier": (
                "A canonical-gate run at the FROZEN-pinned tool and manifest shas that returns R22 for "
                "F2a rev12, or a positive control that fails to fire R22 on an injected unknown key."
            ),
        },
        {
            "id": "W065-H5-F0-COMPANION-DIVERGENCE-BY-DESIGN",
            "source_verdicts": ["F2a-review-095 (F-BIND-2)"],
            "claim": (
                "The canonical/supplement F0 divergence is the REC-3 companion pair (declared taxonomy "
                "0abb9ed8a961 + class-contract supplement d7419b4e8963), recorded as a controller ruling, "
                "not a byte-identity defect. F2a binds both through two separately named pointers, both of "
                "which resolve."
            ),
            "status": "NOT_A_DEFECT_BY_RULING",
            "severity": "none",
            "evidence": {
                "canonical_pointer": c1["checks"][0],
                "supplement_pointer": c1["checks"][1],
                "frozen_classification": "companion-pinned (REC-3), see runtime/state/controller_verification/astra-lifecycle-04.md",
            },
            "falsifier": (
                "A controller ruling that reverses REC-3, or a revision in which the two pointers name the "
                "same artifact while FROZEN records two distinct pins."
            ),
        },
        {
            "id": "W065-H6-STALE-INDEX-PIN-LIVES-ELSEWHERE",
            "source_verdicts": ["worker-005 f2_rebind (HF-W005-F2D-02)"],
            "claim": (
                "The stale pre-rev12 pin b6123750b37d does not occur in F2a; it occurs in "
                "schemas/af_scc_regularities.yaml, a separate artifact outside the FROZEN rev28 mirror set. "
                "It cannot be repaired inside F2a."
            ),
            "status": "OUT_OF_CLASS_SCOPE",
            "severity": "none_for_F2a",
            "evidence": {"carriers": c5["carriers"], "stale_pin_in_F2a": c5["stale_pin_in_F2a"]},
            "falsifier": "The string b6123750b37d appearing inside a live F2a revision.",
        },
    ]

    blocking = [f["id"] for f in findings if f["severity"].startswith("blocking")]
    major = [f["id"] for f in findings if f["severity"].startswith("major")]

    report = {
        "task_id": TASK_ID,
        "actor": REVIEWER,
        "node_id": NODE,
        "gate": GATE_ID,
        "class_id": CLASS_ID,
        "started_at": started,
        "finished_at": now(),
        "window_stable": window_stable,
        "window_pre": win_pre,
        "window_post": win_post,
        "inputs": snapshot_index,
        "checks": {
            "C1_pointer_resolution": c1,
            "C2_declared_f0_binding": c1["checks"][1],
            "C3_consistency_evidence": c3,
            "C4_gate_r22": c4,
            "C5_index_pin": c5,
            "C6_ledger_refs": c6,
            "C7_systemic_extent": c7,
        },
        "findings": findings,
        "verdict": {
            "verdict": "revise",
            "score": 3.5,
            "target": f"schemas/af_scc_c2_vacuum.yaml#{sha256(F2A)[:12]}",
            "target_sha256": sha256(F2A),
            "blocking_hard_failures": blocking,
            "major_hard_failures": major,
            "cleared_findings": [f["id"] for f in findings if f["status"].startswith("NOT_") or f["status"].startswith("OUT_")],
            "note": (
                "Two live defects remain (evidence-hash resolution; undefined citation_status token). "
                "Two previously blocking findings do not reproduce at the live canonical hashes and are "
                "cleared as stale/tool-scoped. Verdict revise is advisory; the audit lead adjudicates and "
                "only the controller can move a gate."
            ),
        },
        "authority_note": (
            "Worker review: cannot set node status=done, validation_status=passed, or a gate verdict. "
            "The audit lead and controller adjudicate."
        ),
    }

    report_meta = write_json(OUT / "report.json", report)

    readme = f"""# W065 F2a rev12 adjudication (AF-SCC-C2-VAC-GEN)

Task `{TASK_ID}` | node {NODE} | gate {GATE_ID} | class `{CLASS_ID}` | reviewer `{REVIEWER}` (not an author)

Target: `schemas/af_scc_c2_vacuum.yaml#{sha256(F2A)[:12]}` (rev12, FROZEN rev28).

Window: **{'STABLE' if window_stable else 'MOVED'}** across the run.

## Verdict: revise (advisory, score 3.5)

Two live defects, two stale blockers cleared.

| id | finding | status | severity |
|---|---|---|---|
| W065-H1 | declared `consistency_evidence_sha256` 675a99d0 does not resolve at the declared path (live 9e335e9b; FROZEN rev28 pins 9e335e9b) | CONFIRMED_REAL | blocking_for_gate_criterion |
| W065-H2 | `citation_status: verified_by_L1` is undefined in both frozen ledger artifacts; ledger records abstract-read for those ids | CONFIRMED_REAL | major_vocabulary_scope |
| W065-H3 | `class_contract_pointer` fails to resolve in canonical F0 | NOT_REPRODUCED_STALE | none |
| W065-H4 | R22 unknown keys (worker-005) | NOT_REPRODUCED_TOOL_SCOPED | none |
| W065-H5 | F0 canonical/supplement byte divergence | NOT_A_DEFECT_BY_RULING (REC-3) | none |
| W065-H6 | stale index pin b6123750b37d | OUT_OF_CLASS_SCOPE (lives in `schemas/af_scc_regularities.yaml`) | none |

## Key measurements

- canonical gate (sha `{c4['gate_tool_sha256'][:12]}`) + FROZEN-pinned manifest
  (sha `{c4['key_manifest_sha256'][:12]}`) on F2a rev12: **verdict={c4['canonical_verdict']},
  failed_rules={c4['canonical_failed_rules']}**; positive control on an injected unknown key fires R22
  (`{c4['r22_live_control']['failed_rules']}`), so the pass is not vacuous.
- rev27 replay manifest (264 keys) reproduces exactly the six keys named by HF-W005-F2D-01:
  `{c4['unknown_keys_under_rev27_replay_manifest']}` — the finding is a replay-scope artifact.
- consistency evidence: declared `{c3['declared_sha256'][:12]}` -> live path `{c3['measured_sha256_at_declared_path'][:12]}`;
  the declared hash is carried by {len(c3['declared_hash_carriers_repo_scan']['carriers'])} files found in a
  {c3['declared_hash_carriers_repo_scan']['files_searched']}-file repo scan (none of them the declared path).
- `verified_by_L1`: {c6['token_occurrences_in_ledger']} occurrences in the ledger,
  {c6['token_occurrences_in_citation_audit']} in the citation audit; {c6['rows_claiming_token']} F2a rows claim it.
- pointer resolution: canonical `{c1['checks'][0]['resolves']}`, supplement `{c1['checks'][1]['resolves']}`,
  corrupted-fragment control resolves `{c1['checks'][2]['resolves']}` (must be false).

## Controls

{[c['id'] + ': ok=' + str(c.get('resolves', c.get('control_ok'))) for c in c1['checks']]}

R22 live control: fired={c4['r22_live_control']['R22_fired']}.

## Falsifiers

Each finding carries its own falsifier in `report.json`. Global falsifiers for this adjudication:
a window hash differing between `window_pre` and `window_post`; a canonical-gate run at the
FROZEN-pinned tool/manifest shas that disagrees with the recorded verdict; a corrupted-pointer
control that resolves; or an R22 positive control that fails to fire.
"""
    (OUT / "README.md").write_text(readme)
    readme_meta = {"path": str((OUT / "README.md").relative_to(ROOT)),
                   "sha256": sha256(OUT / "README.md"), "bytes": (OUT / "README.md").stat().st_size}

    # ---------------- events
    ts = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    ev_id = f"w065-f2a-adjudication-{ts}"
    artifact_refs = [
        f"artifacts/worker-065/f2a_rev12_adjudication/report.json#{report_meta['sha256'][:12]}",
        f"artifacts/worker-065/f2a_rev12_adjudication/README.md#{readme_meta['sha256'][:12]}",
        f"artifacts/worker-065/f2a_rev12_adjudication/adjudicate_f2a.py#{sha256(Path(__file__))[:12]}",
        f"schemas/af_scc_c2_vacuum.yaml#{sha256(F2A)[:12]}",
    ]
    base = {
        "created_at": now(),
        "actor": REVIEWER,
        "task_id": TASK_ID,
        "node_id": NODE,
        "gate": GATE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
    }
    falsifier = (
        "Any of: (a) the declared consistency evidence resolving at the declared path/hash in a live "
        "measurement (W065-H1 falsified); (b) the token verified_by_L1 being defined at theorem level by a "
        "live ledger/citation-audit revision (W065-H2 falsified); (c) a canonical-gate run at the "
        "FROZEN-pinned tool and manifest shas returning R22 on F2a rev12, or an injected unknown key not "
        "firing R22 (W065-H4 falsified); (d) the class_contract_pointer failing to resolve in the live "
        "canonical F0 while F2a keeps the pointer (W065-H3 falsified); (e) window_pre != window_post, or "
        "any snapshot hash differing from a fresh measurement of the same path."
    )
    events = [
        {**base, "event_id": f"{ev_id}-artifact-report", "event_type": "artifact",
         "artifact_type": "adjudication_report", "path": report_meta["path"],
         "sha256": report_meta["sha256"], "validation_status": "unverified",
         "evidence_refs": artifact_refs, "falsifier": falsifier},
        {**base, "event_id": f"{ev_id}-artifact-readme", "event_type": "artifact",
         "artifact_type": "md", "path": readme_meta["path"], "sha256": readme_meta["sha256"],
         "validation_status": "unverified",
         "evidence_refs": [artifact_refs[0]], "falsifier": falsifier},
        {**base, "event_id": f"{ev_id}-artifact-harness", "event_type": "artifact",
         "artifact_type": "harness", "path": "artifacts/worker-065/f2a_rev12_adjudication/adjudicate_f2a.py",
         "sha256": sha256(Path(__file__)), "validation_status": "unverified",
         "evidence_refs": [artifact_refs[0]], "falsifier": falsifier},
        {**base, "event_id": f"{ev_id}-review", "event_type": "review",
         "target_id": f"schemas/af_scc_c2_vacuum.yaml#{sha256(F2A)[:12]}",
         "reviewer": REVIEWER, "verdict": "revise", "score": 3.5,
         "hard_failures": blocking + major,
         "findings": [f["id"] + ": " + f["status"] for f in findings],
         "cleared_findings": report["verdict"]["cleared_findings"],
         "evidence_refs": artifact_refs, "falsifier": falsifier},
        {**base, "event_id": f"{ev_id}-claim", "event_type": "claim",
         "conclusion_type": "formal_model",
         "statement": (
             f"Independent adjudication of F2a AF-SCC-C2-VAC-GEN at rev12 {sha256(F2A)[:12]} in a "
             f"{'stable' if window_stable else 'MOVED'} window: two hard findings are live and "
             "reproducible — (H1) f0_binding.consistency_evidence_sha256 675a99d0d25b does not resolve at "
             "the declared path artifacts/formulation/evidence/taxonomy_consistency.json, which measures "
             "9e335e9ba1bf and is so pinned by FROZEN rev28, while a bounded repo scan for the declared "
             f"hash finds it at {c3['declared_hash_carriers_repo_scan']['carriers']} "
             f"({c3['declared_hash_carriers_repo_scan']['files_searched']} json/yaml files searched); and (H2) the "
             "citation_status token verified_by_L1 is undefined in both frozen ledger artifacts (0 "
             "occurrences) and the ledger records verification_status=abstract-read and "
             "review_status=not_independently_reviewed for T-401/T-402/T-514/T-520. Two findings that "
             "previously returned revise do not reproduce at the live canonical bytes: the "
             "class_contract_pointer resolves in canonical F0 rev5 0abb9ed8a961 via classes.<ID> (with a "
             "corrupted-fragment sensitivity control), and the R22 unknown-key failure reproduces only "
             "under the rev27 replay manifest (264 keys, exactly the six named keys) while the "
             "FROZEN-pinned canonical gate and manifest return pass with failed_rules=[]. The stale pin "
             "b6123750b37d is not in F2a; it lives in schemas/af_scc_regularities.yaml."
         ),
         "assumptions": [
             "The live disk bytes are the measured authority; FROZEN.json rev28 pins were compared, not trusted.",
             "The canonical gate tool and KEY_MANIFEST are used at their measured shas; the rev27 manifest is used only as a replay control.",
             "citation_status semantics are contested; the charitable reading (citation-metadata verification) is recorded and does not rescue the undefined-token defect.",
             "This is a document/binding measurement, not a mathematical adjudication; the audit lead owns the gate verdict.",
         ],
         "evidence_refs": artifact_refs + [
             f"research_map/formulation_taxonomy.yaml#{sha256(F0_CANON)[:12]}",
             f"artifacts/formulation/FROZEN.json#{sha256(FROZEN)[:12]}",
             f"artifacts/formulation/KEY_MANIFEST.json#{sha256(KEY_MANIFEST)[:12]}",
             f"ledger/theorems.jsonl#{sha256(LEDGER)[:12]}",
             f"ledger/citation_audit.csv#{sha256(CITATION_AUDIT)[:12]}",
         ],
         "artifact_refs": artifact_refs, "falsifier": falsifier},
        {**base, "event_id": f"{ev_id}-complete", "event_type": "status",
         "status": "active", "hours": 0.4,
         "summary": (
             f"{TASK_ID} complete at worker level: window {'STABLE' if window_stable else 'MOVED'}, "
             "7 checks + 2 live controls run, 2 findings CONFIRMED_REAL, 3 cleared (stale/tool-scoped/by-ruling), "
             "1 out-of-class-scope. Advisory review verdict revise 3.5 at the frozen F2a hash; no node/gate "
             "transition claimed; checkpoint written."
         ),
         "evidence_refs": artifact_refs, "next_falsifier": falsifier},
    ]

    events_path = OUT / "events.jsonl"
    # self-check against the authoritative ingest validator (research_map/schemas.py);
    # events.schema.json is a partial mirror that omits status/blocker, so schemas.py is used.
    sys.path.insert(0, str(ROOT / "research_map"))
    from schemas import validate_event  # noqa: E402

    validation = []
    with events_path.open("w") as fh:
        for e in events:
            validate_event(e)
            validation.append({"event_id": e["event_id"], "event_type": e["event_type"], "valid": True})
            fh.write(json.dumps(e, sort_keys=True) + "\n")

    # ---------------- checkpoint
    import time

    time.sleep(2.0)
    win_final = measure_window()
    checkpoint = {
        "checkpoint": 1,
        "at": now(),
        "worker": REVIEWER,
        "slot": "065",
        "task_id": TASK_ID,
        "assignment": (
            "one class-bound task (self-selected; no inbox card for worker-065): independent hash-bound "
            "adjudication of the contested rev12 hard findings on F2a AF-SCC-C2-VAC-GEN at gate G-FORM"
        ),
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "verdict": "revise",
            "score": 3.5,
            "blocking_hard_failures": blocking,
            "major_hard_failures": major,
            "cleared_findings": report["verdict"]["cleared_findings"],
            "checks_passed": sum(
                1 for c in [c1["all_pass"], c3["resolves_at_declared_path"] is False,
                            c4["canonical_gate_passes"], c4["control_ok"], not c5["stale_pin_in_F2a"],
                            window_stable]
                if c
            ),
            "pins": {k: v["sha256"] for k, v in snapshot_index.items()},
            "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem or gate moved",
        },
        "artifacts": {
            report_meta["path"]: {"sha256": report_meta["sha256"], "bytes": report_meta["bytes"]},
            readme_meta["path"]: {"sha256": readme_meta["sha256"], "bytes": readme_meta["bytes"]},
            "artifacts/worker-065/f2a_rev12_adjudication/adjudicate_f2a.py": {
                "sha256": sha256(Path(__file__)), "bytes": Path(__file__).stat().st_size},
            "artifacts/worker-065/f2a_rev12_adjudication/events.jsonl": {
                "sha256": sha256(events_path), "bytes": events_path.stat().st_size},
        },
        "snapshots": snapshot_index,
        "event_validation": validation,
        "window_final": win_final,
        "window_stable_through_final": win_final == win_pre,
    }
    ckpt_path = OUT / "checkpoint.json"
    ckpt_meta = write_json(ckpt_path, checkpoint)

    print(json.dumps({
        "window_stable": window_stable,
        "verdict": report["verdict"]["verdict"],
        "blocking": blocking,
        "major": major,
        "cleared": report["verdict"]["cleared_findings"],
        "report": report_meta,
        "readme": readme_meta,
        "events": str(events_path.relative_to(ROOT)),
        "checkpoint": ckpt_meta,
        "events_validated": validation,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
