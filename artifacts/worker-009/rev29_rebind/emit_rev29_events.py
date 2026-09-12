#!/usr/bin/env python3
"""Emit worker-009 rev29-rebind events to comms/outbox/worker-009.jsonl (append-only).

Drift guard: every anchor recorded in the verification record is re-hashed before
any event is written.  If any anchor moved, NOTHING is emitted and the script exits 2
so the verifier can be re-run at the new bytes (this is the falsifier of the record).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / "artifacts" / "worker-009" / "rev29_rebind" / "verification_rev29_rebind_worker-009.json"
CHECKPOINT = ROOT / "runtime" / "state" / "w009_rev29_rebind_checkpoint_1.json"
OUTBOX = ROOT / "comms" / "outbox" / "worker-009.jsonl"
REMEDIATED = ROOT / "artifacts" / "worker-009" / "rev29_rebind" / "dryrun_applied_citation_audit_12row_remediated.csv"
REM_CSV = ROOT / "artifacts" / "worker-009" / "rev29_rebind" / "remediation_classmapping_2row_worker-009.csv"
REM_JSONL = ROOT / "artifacts" / "worker-009" / "rev29_rebind" / "remediation_classmapping_2row_worker-009.jsonl"
TOOL = ROOT / "artifacts" / "worker-009" / "rev29_rebind" / "verify_rev29_rebind.py"

CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path, digest: str | None = None) -> str:
    return f"{p.relative_to(ROOT)}#{(digest or h(p))[:16]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", default="2026-09-12T01:01:40+08:00")
    args = ap.parse_args()
    ts = args.created_at
    tag = ts.replace("-", "").replace(":", "")[:15]

    record = json.loads(RECORD.read_text(encoding="utf-8"))

    # ---- drift guard ----------------------------------------------------
    drift = {}
    for name, meta in record["inputs"].items():
        cur = h(ROOT / meta["path"])
        if cur != meta["sha256"]:
            drift[name] = {"recorded": meta["sha256"], "current": cur}
    if drift:
        print(json.dumps({"status": "DRIFT", "drift": drift}, indent=1))
        return 2

    rec_sha = h(RECORD)
    rem_sha, remcsv_sha, remjsonl_sha, tool_sha, ckpt_sha = (
        h(REMEDIATED), h(REM_CSV), h(REM_JSONL), h(TOOL), h(CHECKPOINT),
    )
    remaining = record["detector"]["dryrun_strict_remaining"]
    counts = record["counts"]
    anchors = [
        ref(ROOT / "ledger" / "citation_audit.csv"),
        ref(ROOT / "ledger" / "theorems.jsonl"),
        ref(ROOT / "schemas" / "af_wcc_vacuum.yaml"),
        ref(ROOT / "schemas" / "af_scc_c2_vacuum.yaml"),
        ref(ROOT / "schemas" / "af_scc_c0_vacuum.yaml"),
        ref(ROOT / "artifacts" / "formulation" / "FROZEN.json"),
        ref(ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"),
        ref(ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"),
        ref(ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.csv"),
    ]
    falsifier = record["falsifier"]
    nxt = record["next_falsifier"]

    prefix = f"w009-rev29-{tag}"
    events = [
        {
            "event_id": prefix + "-task-receipt",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.3,
            "summary": (
                "No inbox card for worker-009. Took ONE bounded class-bound task: after the "
                "rev13 schema repair + FROZEN rev29, re-bind the 12-row SCC class-binding "
                "correction proposal and run its declared next-falsifier (DET-REV12 over the "
                "12-row dry-run), then emit a minimal 2-row textual remediation for the rows "
                "the strict detector still flags."
            ),
            "evidence_refs": anchors + [ref(RECORD, rec_sha)],
            "next_falsifier": nxt,
        },
        {
            "event_id": prefix + "-artifact-01",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "artifact_type": "verification_record",
            "path": str(RECORD.relative_to(ROOT)),
            "sha256": rec_sha,
            "validation_status": "unverified",
            "note": (
                f"rev29 re-binding record: {counts['pass']} PASS / {counts['fail']} FAIL / "
                f"{counts['advisory']} ADVISORY. Anchors hold at rev13 + FROZEN rev29; the 12-row "
                f"reproduction is byte-identical; the declared strict DET-REV12 closure falsifier "
                f"FAILS on {remaining} (literal frozen id left in the removal phrase); a 2-cell "
                f"remediation makes strict and removal-aware readings agree at 0 hits. Canonical "
                f"ledger and patch files untouched."
            ),
            "evidence_refs": anchors + [ref(RECORD, rec_sha)],
            "falsifier": falsifier,
        },
        {
            "event_id": prefix + "-artifact-02",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "artifact_type": "dryrun_ledger",
            "path": str(REMEDIATED.relative_to(ROOT)),
            "sha256": rem_sha,
            "validation_status": "unverified",
            "note": (
                "12-row dry-run with the 2-cell class_mapping remediation (SRC-014, SRC-061): "
                "strict DET-REV12 returns zero hits; exactly 2 cells differ from the pinned "
                "12-row dry-run and no other byte/cell changes. Candidate-only; the canonical "
                "ledger is not written by worker-009."
            ),
            "evidence_refs": [ref(REMEDIATED, rem_sha), ref(RECORD, rec_sha),
                              ref(ROOT / "ledger" / "citation_audit.csv")],
            "falsifier": falsifier,
        },
        {
            "event_id": prefix + "-artifact-03",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "artifact_type": "class_binding_correction_remediation",
            "path": str(REM_CSV.relative_to(ROOT)),
            "sha256": remcsv_sha,
            "validation_status": "unverified",
            "note": (
                "Minimal 2-row machine-applicable remediation (same 21-column schema as the "
                "candidate patch) replacing the two class_mapping cells that name a frozen "
                "vacuum class id inside a removal phrase. Companion JSONL: "
                f"{REM_JSONL.relative_to(ROOT)}#{remjsonl_sha[:16]}. All other columns are "
                "byte-identical to the original rows."
            ),
            "evidence_refs": [ref(REM_CSV, remcsv_sha), ref(REM_JSONL, remjsonl_sha),
                              ref(RECORD, rec_sha)],
            "falsifier": falsifier,
        },
        {
            "event_id": prefix + "-artifact-04",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "artifact_type": "verification_tool",
            "path": str(TOOL.relative_to(ROOT)),
            "sha256": tool_sha,
            "validation_status": "unverified",
            "note": (
                "Deterministic re-binding verifier (--verified-at): anchor pins, rev12->rev13 "
                "leaf-path delta audit, byte-identical dry-run reproduction, DET-REV12 strict and "
                "removal-aware readings, remediation dry-run, first/last anchor stability check "
                "(A22). Read-only against canonical state."
            ),
            "evidence_refs": [ref(TOOL, tool_sha), ref(RECORD, rec_sha),
                              ref(CHECKPOINT, ckpt_sha)],
            "falsifier": falsifier,
        },
        {
            "event_id": prefix + "-review-01",
            "event_type": "review",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "target_id": "ledger/citation_audit_scc_candidates_worker-009.csv",
            "reviewer": "worker-009",
            "verdict": "revise",
            "score": 3.0,
            "review_scope": (
                "adversarial re-review of worker-009's own prior proposal at the new rev13 / "
                "FROZEN rev29 bytes; author self-verification, NOT an independent verdict"
            ),
            "hard_failures": record["review_of_prior_patch"]["hard_failures"],
            "findings": record["review_of_prior_patch"]["findings"] + [
                f"DET-REV12 strict remaining: {remaining} "
                f"({record['detector']['dryrun_strict_reasons']}); removal-clause-aware remaining: "
                f"{record['detector']['dryrun_removal_aware_remaining']}.",
                "Inputs re-anchored in-session: FROZEN rev29 bytes 3d9e3d77fd87 -> 815e08079aef at "
                "00:57:26; VARIANT_REGISTRY 5eb42f9a384a -> 6bac9adea19e (C4 repair). CH/LIP under "
                "AF-SCC-C0-VAC-GEN and the no-leakage rule verified at the new registry byte.",
            ],
            "evidence_refs": [ref(RECORD, rec_sha), ref(REMEDIATED, rem_sha),
                              ref(ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.csv"),
                              ref(ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json")],
            "falsifier": falsifier,
        },
        {
            "event_id": prefix + "-status-01",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-009",
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "node_id": "L1",
            "gate": "G-LIT",
            "group_id": "literature",
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.4,
            "summary": (
                "Bounded task complete at worker level; node status, validation_status and gates "
                "deliberately unchanged. rev13 + FROZEN rev29 anchors hold; the 12-row dry-run "
                "reproduces byte-identically; declared strict DET-REV12 closure fails on SRC-014 "
                "and SRC-061 (literal frozen class ids inside removal phrases) and is reported as "
                f"a hard failure; the 2-cell remediation dry-run returns zero strict hits. "
                f"Checks: {counts['pass']} PASS / {counts['fail']} FAIL / {counts['advisory']} "
                f"ADVISORY. Canonical ledger 315c19145065 and both patch files untouched; "
                f"numerics lock respected; no solver created."
            ),
            "evidence_refs": [ref(RECORD, rec_sha), ref(REMEDIATED, rem_sha),
                              ref(REM_CSV, remcsv_sha), ref(TOOL, tool_sha),
                              ref(CHECKPOINT, ckpt_sha), ref(ROOT / "ledger" / "citation_audit.csv")],
            "next_falsifier": nxt,
        },
    ]

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(json.dumps({
        "emitted": [e["event_id"] for e in events],
        "count": len(events),
        "record_sha256": rec_sha,
        "remediated_dryrun_sha256": rem_sha,
        "remediation_csv_sha256": remcsv_sha,
        "checkpoint_sha256": ckpt_sha,
        "strict_remaining": remaining,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
