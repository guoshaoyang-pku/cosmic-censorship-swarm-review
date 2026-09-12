#!/usr/bin/env python3
"""W063-F2B-CLOSE-AUDIT-01 addendum snapshot: owner's 01:13 acceptance-pipeline blocker.

Separate from review_events_snapshot.json (already frozen, bytes authoritative) so the
earlier snapshot is never rewritten. Extracts one accepted-stream event byte-verbatim with
its source line and canonical sha256.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVENTS = ROOT / "research_map" / "events.jsonl"
OUT = Path(__file__).resolve().parent / "evidence" / "owner_blocker_snapshot.json"
CST = timezone(timedelta(hours=8))
WANTED = ["lead-form-20260912T0113-106"]


def canonical_sha256(doc: dict) -> str:
    return hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    found = {}
    total = 0
    with EVENTS.open() as fh:
        for lineno, line in enumerate(fh, 1):
            total = lineno
            line = line.strip()
            if not line or not any(w in line for w in WANTED):
                continue
            try:
                doc = json.loads(line)
            except ValueError:
                continue
            eid = doc.get("event_id")
            if eid in WANTED and eid not in found:
                found[eid] = {
                    "event_id": eid, "source": "research_map/events.jsonl",
                    "source_line": lineno, "source_received_at": doc.get("_received_at"),
                    "event_type": doc.get("event_type"), "actor": doc.get("actor"),
                    "canonical_sha256": canonical_sha256(doc), "event": doc,
                }
    missing = [w for w in WANTED if w not in found]
    if missing:
        raise SystemExit(f"addendum snapshot FAIL: missing {missing}")
    snap = {
        "snapshot_id": "w063-f2b-close-audit-owner-blocker",
        "task_id": "W063-F2B-CLOSE-AUDIT-01",
        "extracted_at": datetime.now(CST).isoformat(timespec="seconds"),
        "source": "research_map/events.jsonl",
        "source_total_lines_at_extraction": total,
        "event_count": len(found),
        "events": [found[w] for w in WANTED],
    }
    OUT.write_text(json.dumps(snap, indent=2) + "\n")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)),
                      "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                      "events": len(found)}, indent=2))


if __name__ == "__main__":
    main()
