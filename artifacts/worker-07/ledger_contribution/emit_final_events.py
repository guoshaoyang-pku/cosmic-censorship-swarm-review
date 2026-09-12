#!/usr/bin/env python3
"""Emit worker-07 final outbox events (validated against research_map/schemas.py)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

OUT = ROOT / "comms" / "outbox" / "deepseek-flash-07"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-07"

REPORT = ROOT / "artifacts" / "worker-07" / "REPORT.md"
DEDUP = ROOT / "artifacts" / "worker-07" / "ledger_contribution" / "duplication_report.json"
GROUND = ROOT / "artifacts" / "worker-07" / "ledger_contribution" / "grounding_report.json"
HARNESS = ROOT / "artifacts" / "worker-07" / "class_separation_falsification" / "results.json"
SNAP_NEW = (ROOT / "artifacts" / "worker-07" / "class_separation_falsification"
            / "target_snapshots" / "audit_evidence.bb0522e94148.py")
W07_THM = ROOT / "artifacts" / "worker-07" / "ledger_contribution" / "batches" / "batch-w07-theorems.jsonl"
LEDGER = ROOT / "ledger" / "theorems.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


EVENTS = [
    {
        "event_id": "w07-status-L0-final-20260911T2340",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": "L0",
        "status": "active",
        "hours": 0.9,
        "summary": (
            "L0 final status. (1) Delivered 7 sources + 15 theorem rows at 23:26; the literature "
            "lead's 23:27 directory rewrite deleted the injected batch-w07 files and rebuilt the "
            "ledger without them (0 W07 rows verified). (2) On re-inspection all 15 rows are now "
            "superseded by equal-or-stronger canonical rows (D-001, T-101, T-103, T-201, T-206, "
            "T-208, T-209), so I did NOT re-inject duplicates; the annotated mapping and durable "
            "batches live under artifacts/worker-07/ledger_contribution/. (3) The durable additions "
            "are two verification tools: quote-grounding (all 30 W07 quotes match; 34/43 accepted "
            "lead rows declare no grounding) and duplication triage (10 actionable pairs in 5 "
            "clusters, 23 review-tier, 0 duplicate source records). (4) A blocker is filed for the "
            "batch deletion. No node/gate state claimed."
        ),
        "evidence_refs": [
            f"artifacts/worker-07/REPORT.md#{sha(REPORT)[:8]}",
            f"artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl#{sha(W07_THM)[:8]}",
            f"ledger/theorems.jsonl#{sha(LEDGER)[:8]}",
        ],
        "next_falsifier": (
            "A future lead rebuild drops contributor batches again (incident recurs), or an L1 "
            "review shows one of the W07 rows was NOT actually superseded (then it must return)."
        ),
    },
    {
        "event_id": "w07-artifact-dedup-20260911T2340",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": "A2",
        "artifact_type": "duplication_triage_report",
        "path": rel(DEDUP),
        "sha256": sha(DEDUP),
        "validation_status": "unverified",
        "tool": "artifacts/worker-07/ledger_contribution/check_duplication.py",
        "finding": ("43-row ledger, canonical work keys: 10 actionable pairs in 5 clusters "
                    "(D-004/T-503; D-005/T-304/T-506; D-006/T-101/T-102/T-107; T-208/T-209; "
                    "T-301/T-305/T-402), 23 review-tier pairs, 0 duplicate source records."),
        "next_falsifier": ("An adjudicator shows an actionable pair is genuinely complementary -> "
                           "detector precision is insufficient and thresholds must move."),
    },
    {
        "event_id": "w07-artifact-grounding-final-20260911T2340",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": "L1",
        "artifact_type": "quote_grounding_report",
        "path": rel(GROUND),
        "sha256": sha(GROUND),
        "validation_status": "unverified",
        "tool": "artifacts/worker-07/ledger_contribution/check_grounding.py",
        "finding": ("All 30 declared quotes in 13 W07 rows are verbatim substrings of cited source "
                    "evidence; 34 of 43 accepted rows in the lead tree declare no grounding entries "
                    "(checkability gap, not proof of error). Supersedes the earlier grounding "
                    "artifact event."),
        "next_falsifier": ("L1 reviewers accept ungrounded accepted rows (gap, not defect) or "
                           "reject them (34 rows fail the stricter contract)."),
    },
    {
        "event_id": "w07-artifact-classsep-rerun-20260911T2340",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": "A1",
        "artifact_type": "falsification_harness_rerun",
        "path": rel(HARNESS),
        "sha256": sha(HARNESS),
        "validation_status": "unverified",
        "target": "research_map/audit_evidence.py::audit",
        "target_revision_snapshot": rel(SNAP_NEW),
        "target_revision_sha256": sha(SNAP_NEW),
        "target_live_sha256_now": sha(ROOT / "research_map" / "audit_evidence.py"),
        "finding": ("Defects persist unchanged on revision bb0522e94148 (5th observed revision): "
                    "3/17 class-hygiene violations detected, 14 missed, 1/10 legitimate controls "
                    "falsely flagged - identical to revision c4769b99ab70. Supersedes the earlier "
                    "class-separation artifact event's hash; the counterexample claim stands for "
                    "both tested revisions."),
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "next_falsifier": ("The current live revision (8c324338) passes all 17 leaks and 10 controls "
                           "when re-tested -> the fix landed and the claim is retracted for the "
                           "current revision."),
    },
    {
        "event_id": "w07-blocker-L0-batch-deletion-20260911T2340",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": "L0",
        "description": (
            "Concurrent restructure hazard: the literature lead's 23:27 rewrite of "
            "artifacts/literature/{sources,theorems}/ deleted worker-07's injected "
            "batch-w07.jsonl files minutes after delivery, and the canonical ledger was rebuilt "
            "without them (0 W07 rows). No data was lost (durable generator + batches kept under "
            "artifacts/worker-07/), but any contributor batch can be silently removed the same way."
        ),
        "needed_to_unblock": (
            "A lead decision on the integration contract: either (a) declare the batch directory "
            "append-only and preserve foreign batch files across rebuilds, or (b) have the lead run "
            "a merge tool that explicitly takes contributor batches as input. Worker-07's generator "
            "now defaults to its own tree and no longer injects."
        ),
        "evidence_refs": [
            f"artifacts/worker-07/REPORT.md#{sha(REPORT)[:8]}",
            "comms/inbox/deepseek-flash-07.jsonl",
            "artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl",
        ],
        "impact": "medium: no work lost, but a contributor's accepted-path artifact can vanish between checkpoint and review.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for e in EVENTS:
        validate_event(e)
    for e in EVENTS:
        p = OUT / f"{e['event_id']}.json"
        p.write_text(json.dumps(e, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        print(f"wrote {p.relative_to(ROOT)}")
    print(f"{len(EVENTS)} final events validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
