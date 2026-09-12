#!/usr/bin/env python3
"""Emit the W043B outbox batch + worker checkpoint, validated before writing.

Usage: python3 emit_events.py            # validate, append events, write checkpoint
       python3 emit_events.py --dry-run  # validate only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "worker-043.jsonl"
CKPT = ROOT / "runtime" / "state" / "w043_checkpoint_2.json"
CKPT_LOG = ROOT / "runtime" / "state" / "w043_checkpoints.jsonl"

D = "artifacts/worker-043/f0_pair_depclosure"


def sha(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    t = now()
    ts = t.replace("-", "").replace(":", "").replace("+", "")[:15]

    hashes = {
        "report": sha(f"{D}/report.json"),
        "readme": sha(f"{D}/README.md"),
        "checker": sha(f"{D}/check_f0_pair.py"),
        "controls": sha(f"{D}/raw/controls.json"),
        "pointer_matrix": sha(f"{D}/raw/pointer_matrix.json"),
        "reference_scan": sha(f"{D}/raw/reference_scan.json"),
    }
    h12 = {k: v[:12] for k, v in hashes.items()}

    ev = [
        {
            "event_id": f"w043b-{ts}-status-claim",
            "event_type": "status",
            "created_at": t,
            "actor": "worker-043",
            "node_id": "F0",
            "node_ids": ["F0", "F1", "F2a", "F2b"],
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "status": "active",
            "hours": 0.4,
            "task_id": "W043B-F0-PAIR-DEPCLOSURE-01",
            "summary": (
                "No inbox card exists for worker-043. Took one bounded class-bound task from the live "
                "critical path: independent dependency-closure audit of leadform-blocker-0007 (the F0 "
                "companion/mirror conflict awaiting controller REC-1/REC-2 adjudication). Read-only on "
                "every shared path; the checker under test is executed only with a source-patched ROOT "
                "inside scratch."
            ),
            "evidence_refs": ["artifacts/formulation/evidence/f0_mirror_conflict.json#7e3a7bc89a75",
                              "runtime/state/current_checkpoint.json"],
            "next_falsifier": (
                "The task is void if the F0 pair, the three schemas, the checker or FROZEN.json change "
                "hash before the report is consumed."
            ),
        },
        {
            "event_id": f"w043b-{ts}-artifact-report",
            "event_type": "artifact",
            "created_at": t,
            "actor": "worker-043",
            "node_id": "F0",
            "class_id": "AF-WCC-VAC-GEN",
            "artifact_type": "independent_dependency_closure_audit",
            "path": f"{D}/report.json",
            "sha256": hashes["report"],
            "validation_status": "unverified",
            "summary": (
                "Verdict LEAD_BLOCKER_SUPPORTED: both single-artifact publication directions fail closed "
                "under the real consistency checker (KeyError class_contracts / class_ids); all three "
                "schema class_contract_pointers resolve only in the authoring supplement; REC-1 needs a "
                "shared companion-pair policy in two hard-coded MIRRORS lists; REC-2 re-cuts 3 schema "
                "hashes, the fixture tree and all current F1/F2a/F2b bindings."
            ),
            "evidence_refs": [f"{D}/report.json#{h12['report']}",
                              f"{D}/raw/controls.json#{h12['controls']}"],
        },
        {
            "event_id": f"w043b-{ts}-artifact-checker",
            "event_type": "artifact",
            "created_at": t,
            "actor": "worker-043",
            "node_id": "F0",
            "class_id": "AF-WCC-VAC-GEN",
            "artifact_type": "reproducible_instrument",
            "path": f"{D}/check_f0_pair.py",
            "sha256": hashes["checker"],
            "validation_status": "unverified",
            "summary": (
                "Read-only audit instrument (hash-pinned); exits 0 iff the current pair is CONSISTENT "
                "and both single-artifact publication simulations fail closed."
            ),
            "evidence_refs": [f"{D}/check_f0_pair.py#{h12['checker']}"],
        },
        {
            "event_id": f"w043b-{ts}-claim-f0pair",
            "event_type": "claim",
            "created_at": t,
            "actor": "worker-043",
            "node_id": "F0",
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "conclusion_type": "formal_model",
            "statement": (
                "At the measured hashes (canonical F0 276009f4f63d 35145 B; authoring supplement "
                "c8e979a1eb48 20937 B; F1 9a8bd4c96800, F2a b6123750b37d, F2b 1bb78ce9b357; FROZEN "
                "rev26 2554e276a0db), leadform-blocker-0007 is reproduced by execution: the two F0 "
                "paths hold different artifacts (23 canonical-only / 18 authoring-only keys, 6 of 7 "
                "shared keys conflicting); every schema class_contract_pointer (#class_contracts.<CLASS>) "
                "resolves only in the authoring artifact; the real check_taxonomy_consistency.py returns "
                "CONSISTENT on the current pair but raises KeyError 'class_contracts' when the canonical "
                "artifact is published over the supplement and KeyError 'class_ids' in the reverse "
                "direction. REC-1 is not a one-line audit exception: the same divergence is computed by "
                "a second hard-coded MIRRORS list in research_map/astra_lifecycle.py:44 feeding "
                "publication_status/CF-13, and it flips from soft to hard if a frozen canonical F0 entry "
                "is re-activated. REC-2 changes the three schema hashes and the supplement path, so it "
                "must re-cut 42 fixture files (40 pinning a schema/F0 hash) and all current F1/F2a/F2b "
                "review bindings. This is worker evidence only; the REC-1/REC-2 choice belongs to the "
                "controller."
            ),
            "assumptions": [
                "the measured hashes did not change during the window (verified start/end)",
                "the checker executed under test is the canonical file at its measured hash, patched only in its ROOT constant so its write lands in scratch",
                "worker verdicts cannot set a gate verdict, node status or validation_status",
            ],
            "falsifier": (
                "Re-run artifacts/worker-043/f0_pair_depclosure/check_f0_pair.py on unchanged inputs: "
                "falsified if the current pair is not CONSISTENT, if either single-artifact publication "
                "does not fail closed with a KeyError, if a class_contract_pointer resolves in the "
                "canonical F0 alone, or if any measured input hash differs between the start and end "
                "windows."
            ),
            "evidence_refs": [f"{D}/report.json#{h12['report']}",
                              f"{D}/raw/controls.json#{h12['controls']}",
                              f"{D}/raw/pointer_matrix.json#{h12['pointer_matrix']}",
                              f"{D}/raw/reference_scan.json#{h12['reference_scan']}",
                              "research_map/formulation_taxonomy.yaml#276009f4f63d",
                              "artifacts/formulation/formulation_taxonomy.yaml#c8e979a1eb48",
                              "artifacts/formulation/FROZEN.json#2554e276a0db"],
            "artifact_refs": [f"{D}/report.json#{h12['report']}"],
        },
        {
            "event_id": f"w043b-{ts}-review-f0pair",
            "event_type": "review",
            "created_at": t,
            "actor": "worker-043",
            "node_id": "F0",
            "class_id": "AF-WCC-VAC-GEN",
            "reviewer": "worker-043",
            "target_id": "blocker:leadform-blocker-0007",
            "artifact": "artifacts/formulation/evidence/f0_mirror_conflict.json",
            "artifact_sha256": "7e3a7bc89a75bd27576dba5cf10ade5a46b24aaef8387ac046c60fb043a4d211",
            "verdict": "inconclusive",
            "score": 4.0,
            "evidence_claim_verdict": "supported",
            "gate_eligible": False,
            "counts_as_full_schema_verdict": False,
            "authority_note": (
                "worker evidence only; cannot set a gate verdict, node status or validation_status; "
                "target is the blocker, not F0, so this verdict must not be counted in G-F0/G-FORM."
            ),
            "hard_failures": [],
            "findings": [
                "W043B-F-01..04: two-artifact divergence, pointer matrix, executed destructive-direction controls, 6 shared-key conflicts",
                "W043B-F-05: REC-1 requires a shared companion-pair policy consumed by audit_evidence.py:123 AND astra_lifecycle.py:44; divergence flips hard on F0 re-freeze",
                "W043B-F-06: REC-2 surface: 326 authoring-path / 350 canonical-path / 103 consistency-evidence references; 42 fixtures, 40 hash-pinned",
                "W043B-F-07: a first-wins union resolves all pointers but is not mechanical (6 conflicting keys)",
                "Concurrent worker-090 review supports the same two-artifact claim; this audit adds the executed controls and both options' blast radius",
            ],
            "evidence_refs": [f"{D}/report.json#{h12['report']}",
                              f"{D}/raw/reference_scan.json#{h12['reference_scan']}"],
        },
        {
            "event_id": f"w043b-{ts}-status-complete",
            "event_type": "status",
            "created_at": t,
            "actor": "worker-043",
            "node_id": "F0",
            "node_ids": ["F0", "F1", "F2a", "F2b"],
            "class_id": "AF-WCC-VAC-GEN",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "status": "active",
            "hours": 0.8,
            "task_id": "W043B-F0-PAIR-DEPCLOSURE-01",
            "summary": (
                "W043B-F0-PAIR-DEPCLOSURE-01 complete at worker level: artifacts on disk and "
                "hash-pinned, controls executed, checkpoint written to runtime/state/w043_checkpoint_2.json. "
                "Completion claim only; no node transition, no gate verdict, no canonical byte changed."
            ),
            "evidence_refs": [f"{D}/report.json#{h12['report']}",
                              f"{D}/README.md#{h12['readme']}",
                              "runtime/state/w043_checkpoint_2.json"],
            "next_falsifier": (
                "Any hash change of the F0 pair, the three schemas, the checker or FROZEN.json after "
                "this emission voids the audit and requires re-issue at the new hashes."
            ),
        },
    ]

    errors = []
    for e in ev:
        try:
            validate_event(e)
        except SchemaError as exc:
            errors.append((e["event_id"], str(exc)))
    if errors:
        for eid, msg in errors:
            print(f"INVALID {eid}: {msg}")
        return 1
    print(f"validated {len(ev)} events")
    if a.dry_run:
        return 0

    with OUTBOX.open("a") as f:
        for e in ev:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {
        "checkpoint": 2,
        "at": t,
        "worker": "worker-043",
        "task_id": "W043B-F0-PAIR-DEPCLOSURE-01",
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "status": "complete_pending_controller_use",
        "hours_spent_estimate": 0.8,
        "verdict": "LEAD_BLOCKER_SUPPORTED",
        "controls_ok": True,
        "inputs_stable_during_window": True,
        "reviewed_hashes": {
            "research_map/formulation_taxonomy.yaml": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
            "artifacts/formulation/formulation_taxonomy.yaml": "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
            "schemas/af_wcc_vacuum.yaml": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
            "schemas/af_scc_c2_vacuum.yaml": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
            "schemas/af_scc_c0_vacuum.yaml": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
            "artifacts/formulation/FROZEN.json": "2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3",
        },
        "findings_summary": {
            "F0_pair_two_artifacts": "confirmed_23_canonical_only_18_authoring_only_6_of_7_shared_conflict",
            "schema_pointer_resolution": "authoring_only_none_in_canonical_all_in_union",
            "destructive_directions_executed": "canonical_to_authoring=KeyError_class_contracts; authoring_to_canonical=KeyError_class_ids",
            "rec1_blast_radius": "two_hardcoded_MIRRORS_lists_audit_evidence_123_and_astra_lifecycle_44; soft_now_hard_on_F0_refreeze",
            "rec2_blast_radius": "3_schema_hashes_plus_42_fixtures_40_hash_pinned_plus_all_current_F1_F2a_F2b_bindings",
            "shared_key_conflicts": ["authored_by", "class_scope_adjudication", "provenance", "revision", "schema_version", "timestamp_provenance"],
        },
        "artifacts": {
            f"{D}/report.json": {"sha256": hashes["report"], "note": "primary audit report"},
            f"{D}/README.md": {"sha256": hashes["readme"], "note": "human-readable summary"},
            f"{D}/check_f0_pair.py": {"sha256": hashes["checker"], "note": "reproducible instrument"},
            f"{D}/raw/controls.json": {"sha256": hashes["controls"], "note": "patched-checker control output"},
            f"{D}/raw/pointer_matrix.json": {"sha256": hashes["pointer_matrix"], "note": "pointer resolution matrix"},
            f"{D}/raw/reference_scan.json": {"sha256": hashes["reference_scan"], "note": "uncapped reference scan"},
        },
        "discipline": {
            "read_only_on_shared_paths": True,
            "scratch_writes_outside_repo": True,
            "checker_under_test_never_run_unpatched": True,
            "no_gate_verdict_no_node_status": True,
        },
        "next_falsifier": (
            "Re-run check_f0_pair.py on unchanged inputs; falsified if controls_ok or stable is false, "
            "or if any reviewed hash moved."
        ),
    }
    ckpt_text = json.dumps(ckpt, indent=2) + "\n"
    CKPT.write_text(ckpt_text)
    with CKPT_LOG.open("a") as f:
        f.write(json.dumps({
            "checkpoint": 2, "at": t, "worker": "worker-043",
            "task_id": ckpt["task_id"], "status": ckpt["status"],
            "verdict": ckpt["verdict"],
            "file": "runtime/state/w043_checkpoint_2.json",
            "sha256": hashlib.sha256(ckpt_text.encode()).hexdigest(),
        }, sort_keys=True) + "\n")

    print(f"appended {len(ev)} events -> {OUTBOX.relative_to(ROOT)}")
    print(f"checkpoint -> {CKPT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
