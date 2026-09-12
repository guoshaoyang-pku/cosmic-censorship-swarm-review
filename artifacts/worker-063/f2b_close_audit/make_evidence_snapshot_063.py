#!/usr/bin/env python3
"""W063-F2B-CLOSE-AUDIT-01 evidence-snapshot builder (run once, 2026-09-12T01:09+08:00).

Freezes the accepted-stream review/blocker events that are part of the F2b rev13/rev29
open-finding record into a byte-verbatim snapshot, because research_map/events.jsonl is a
growing stream and cannot itself be pinned. Each extracted event carries its source line
number and the sha256 of its canonical JSON so a later re-run can prove the snapshot was
not edited.

This script writes evidence/review_events_snapshot.json. It does not modify any canonical
path and asserts no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVENTS = ROOT / "research_map" / "events.jsonl"
OUT = Path(__file__).resolve().parent / "evidence" / "review_events_snapshot.json"
CST = timezone(timedelta(hours=8))

WANTED = [
    "w044-20260912T0104-liveclosure-review",
    "w095-hold-r4-20260912T010257-review-binding",
    "w062-rev13-2026-09-12T01:02:53+08:00-review",
    "w017-20260912-vocab-source-blocker",
    "lead-form-20260912T005743-91",
    "w047-f2a13-20260912T010049-blocker",
]


def canonical_sha256(doc: dict) -> str:
    return hashlib.sha256(
        json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> dict:
    found: dict[str, dict] = {}
    total_lines = 0
    with EVENTS.open() as fh:
        for lineno, line in enumerate(fh, 1):
            total_lines = lineno
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except ValueError:
                continue
            eid = doc.get("event_id")
            if eid in WANTED and eid not in found:
                found[eid] = {
                    "event_id": eid,
                    "source": "research_map/events.jsonl",
                    "source_line": lineno,
                    "source_received_at": doc.get("_received_at"),
                    "event_type": doc.get("event_type"),
                    "actor": doc.get("actor"),
                    "canonical_sha256": canonical_sha256(doc),
                    "event": doc,
                }
    missing = [e for e in WANTED if e not in found]
    if missing:
        raise SystemExit(f"snapshot FAIL: missing events {missing}")
    snap = {
        "snapshot_id": "w063-f2b-close-audit-review-events",
        "task_id": "W063-F2B-CLOSE-AUDIT-01",
        "extracted_at": datetime.now(CST).isoformat(timespec="seconds"),
        "source": "research_map/events.jsonl",
        "source_total_lines_at_extraction": total_lines,
        "canonicalization": "sha256 of json.dumps(event, sort_keys=True, separators=(',',':'))",
        "event_count": len(found),
        "events": [found[e] for e in WANTED],
    }
    OUT.write_text(json.dumps(snap, indent=2) + "\n")
    print(json.dumps({
        "out": str(OUT.relative_to(ROOT)),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "events": len(found),
        "source_total_lines": total_lines,
    }, indent=2))
    return snap


if __name__ == "__main__":
    main()
