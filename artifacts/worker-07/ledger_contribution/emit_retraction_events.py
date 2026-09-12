#!/usr/bin/env python3
"""Emit worker-07 retraction/confirmation events after the gate fix landed.

Falsifier fired: at revision 6873cb51 the class-separation gate detects 17/17
corpus violations and accepts 10/10 controls.  The counterexample claim
(w07-claim-A1-classsep-20260911T2335) is therefore RETRACTED FOR THE CURRENT
REVISION; it remains true for the two pinned revisions that were tested earlier.
"""
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
CORPUS = ROOT / "artifacts" / "worker-07" / "class_separation_falsification"
RESULTS = CORPUS / "results.json"
HISTORY = CORPUS / "revision_history.json"
SNAP_NEW = CORPUS / "target_snapshots" / "audit_evidence.6873cb512431.py"
LIVE = ROOT / "research_map" / "audit_evidence.py"
REPORT = ROOT / "artifacts" / "worker-07" / "REPORT.md"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


HISTORY_ROWS = [
    {"revision": "c4769b99ab706146c4091fbe51d3e4dcd4faa8ded0c77f12342c74df6d9064a5",
     "observed_at": "2026-09-11T23:20:00+08:00", "violations_detected": 3, "violations_total": 17,
     "missed": 14, "controls_accepted": 9, "controls_total": 10, "spurious_flags": 1,
     "verdict": "DEFECTIVE", "snapshot": "target_snapshots/audit_evidence.c4769b99ab70.py"},
    {"revision": "bb0522e941489df2", "observed_at": "2026-09-11T23:38:00+08:00",
     "violations_detected": 3, "violations_total": 17, "missed": 14,
     "controls_accepted": 9, "controls_total": 10, "spurious_flags": 1,
     "verdict": "DEFECTIVE (unchanged)", "snapshot": "target_snapshots/audit_evidence.bb0522e94148.py"},
    {"revision": "6873cb5124318a9d", "observed_at": "2026-09-11T23:45:00+08:00",
     "violations_detected": 17, "violations_total": 17, "missed": 0,
     "controls_accepted": 10, "controls_total": 10, "spurious_flags": 0,
     "verdict": "SOUND AND PRECISE - FIX CONFIRMED", "snapshot": "target_snapshots/audit_evidence.6873cb512431.py",
     "fix": "class separation moved to research_map/class_separation.py; adopted corpus test "
            "runtime/bin/classsep_regression.py (PASS 17/17 + 10/10)"},
]


def main() -> int:
    HISTORY.write_text(json.dumps({
        "corpus": "artifacts/worker-07/class_separation_falsification",
        "note": "Session-observed regression history for the shared class-separation gate. "
                "Each revision was pinned and snapshotted before testing; earlier snapshots are kept.",
        "revisions": HISTORY_ROWS,
    }, indent=2) + "\n")

    events = [
        {
            "event_id": "w07-status-A1-fix-confirmed-20260911T2345",
            "event_type": "status",
            "created_at": NOW,
            "actor": ACTOR,
            "node_id": "A1",
            "status": "active",
            "hours": 1.1,
            "summary": (
                "RETRACTION/CONFIRMATION. The falsifier stated in w07-claim-A1-classsep-20260911T2335 "
                "has fired: at revision 6873cb512431 the shared class-separation gate detects 17/17 "
                "corpus violations and accepts 10/10 legitimate controls (0 misses, 0 spurious). The "
                "counterexample claim is RETRACTED FOR THE CURRENT REVISION; it remains true for the "
                "two earlier pinned revisions c4769b99ab70 and bb0522e94148 (3/17 detected, 1/10 "
                "false-flagged), whose snapshots are preserved. The fix moved the check to "
                "research_map/class_separation.py and adopted worker-07's 27-fixture corpus as the "
                "regression suite runtime/bin/classsep_regression.py, which PASSES. Worker-07 claims "
                "no credit for the fix and marks no node done."
            ),
            "evidence_refs": [
                f"artifacts/worker-07/class_separation_falsification/results.json#{sha(RESULTS)[:8]}",
                f"artifacts/worker-07/class_separation_falsification/revision_history.json#{sha(HISTORY)[:8]}",
                "runtime/bin/classsep_regression.py",
                f"artifacts/worker-07/REPORT.md#{sha(REPORT)[:8]}",
            ],
            "next_falsifier": (
                "A later edit reintroduces an escape (re-run the regression suite after every edit to "
                "class_separation.py), or a new fixture passes the gate while the formulation lead "
                "rules it a genuine merge."
            ),
        },
        {
            "event_id": "w07-artifact-A1-regression-history-20260911T2345",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": ACTOR,
            "node_id": "A1",
            "artifact_type": "gate_regression_history",
            "path": rel(HISTORY),
            "sha256": sha(HISTORY),
            "validation_status": "unverified",
            "tested_revisions": 3,
            "current_result": "PASS 17/17 leaks detected, 10/10 controls accepted",
            "live_revision_at_emit": sha(LIVE),
            "next_falsifier": ("Rerun artifacts/worker-07/class_separation_falsification/"
                               "run_falsification.py after any edit; exit 1 means a regression."),
        },
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    for e in events:
        validate_event(e)
    for e in events:
        p = OUT / f"{e['event_id']}.json"
        p.write_text(json.dumps(e, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        print(f"wrote {p.relative_to(ROOT)}")
    print("history:", rel(HISTORY), sha(HISTORY)[:12])
    print(f"{len(events)} events validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
