#!/usr/bin/env python3
"""Correct revision_history.json observed_at values to snapshot mtimes and report it.

The first version of revision_history.json used nominal clock labels (23:38/23:45)
that were ahead of the container clock.  The authoritative observation times are the
snapshot file mtimes written when each harness run pinned the revision.  This script
rewrites the history with those times and emits one short correction status event.
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

CORPUS = ROOT / "artifacts" / "worker-07" / "class_separation_falsification"
HISTORY = CORPUS / "revision_history.json"
OUT = ROOT / "comms" / "outbox" / "deepseek-flash-07"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mt(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, CST).isoformat(timespec="seconds")


SNAPS = {
    "c4769b99ab70": CORPUS / "target_snapshots" / "audit_evidence.c4769b99ab70.py",
    "bb0522e94148": CORPUS / "target_snapshots" / "audit_evidence.bb0522e94148.py",
    "6873cb512431": CORPUS / "target_snapshots" / "audit_evidence.6873cb512431.py",
}

hist = json.loads(HISTORY.read_text())
for r in hist["revisions"]:
    short = r["revision"][:12]
    if short in SNAPS:
        r["observed_at"] = mt(SNAPS[short])
        r["observed_at_source"] = "snapshot file mtime (authoritative)"
hist["timestamp_correction"] = (
    "First issue used nominal clock labels 23:38/23:45 that were ahead of the container clock; "
    "observed_at values were replaced by the snapshot mtimes written during each run. Event ids "
    "ending T2340/T2345 are nominal labels; their created_at fields are accurate."
)
HISTORY.write_text(json.dumps(hist, indent=2) + "\n")

event = {
    "event_id": "w07-status-A1-timestamp-correction-20260911T2331",
    "event_type": "status",
    "created_at": NOW,
    "actor": "deepseek-flash-07",
    "node_id": "A1",
    "status": "active",
    "hours": 0.05,
    "summary": (
        "Provenance correction, no result change. revision_history.json previously carried nominal "
        "observed_at labels (23:38/23:45) ahead of the container clock; it now carries the actual "
        "snapshot mtimes 23:20:13 (c4769b99ab70), 23:29:08 (bb0522e94148), 23:30:22 (6873cb512431). "
        "The fix-confirmation finding and the retraction in w07-status-A1-fix-confirmed are unchanged."
    ),
    "evidence_refs": [f"artifacts/worker-07/class_separation_falsification/revision_history.json#{sha(HISTORY)[:8]}"],
    "next_falsifier": "Any evidence ref whose hash no longer matches its file after this correction.",
}
validate_event(event)
OUT.mkdir(parents=True, exist_ok=True)
p = OUT / f"{event['event_id']}.json"
p.write_text(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
print("corrected:", json.dumps([{ "rev": r["revision"][:12], "observed_at": r["observed_at"]}
                                for r in hist["revisions"]], indent=1))
print("wrote", p.relative_to(ROOT), "| history sha", sha(HISTORY)[:12])
