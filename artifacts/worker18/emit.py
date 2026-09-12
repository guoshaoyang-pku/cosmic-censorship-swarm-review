#!/usr/bin/env python3
"""Self-checking outbox emitter for worker deepseek-flash-18.

Rule 5 of comms/PROTOCOL.md: reject your own output before sending.
This helper validates one JSON event against research_map/schemas.py, then appends it to
comms/outbox/deepseek-flash-18.jsonl. It refuses duplicates by event_id, refuses events
whose evidence_refs cite files that do not exist, and prints the sha256 of the emitted line.

Usage:
  python3 artifacts/worker18/emit.py <event.json>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-18.jsonl"


def _existing_ref(ref: str) -> bool:
    """A ref is 'path', 'path:line', 'path#sha-prefix', optionally 'path#... ; note',
    or an http(s) URL (primary-source locator)."""
    p = ref.split("#", 1)[0].split(";", 1)[0].strip()
    if p.startswith("http://") or p.startswith("https://"):
        return True
    # strip a trailing :NNN line locator, but not a Windows drive or a URL scheme
    if "://" not in p:
        head, sep, tail = p.rpartition(":")
        if sep and tail.isdigit():
            p = head
    return (ROOT / p).exists()


def main(path: str) -> int:
    event = json.loads(Path(path).read_text())
    try:
        validate_event(event)
    except SchemaError as e:
        print(f"REJECT schema: {e}")
        return 1
    missing = [r for r in event.get("evidence_refs", []) if not _existing_ref(r)]
    if missing:
        print(f"REJECT missing evidence files: {missing}")
        return 1
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    old = OUTBOX.read_text() if OUTBOX.exists() else ""
    ids = set()
    for line in old.splitlines():
        try:
            ids.add(json.loads(line)["event_id"])
        except Exception:
            pass
    if event["event_id"] in ids:
        print(f"REJECT duplicate event_id {event['event_id']}")
        return 1
    line = json.dumps(event, sort_keys=True)
    with OUTBOX.open("a") as f:
        f.write(line + "\n")
    print(f"OK {event['event_type']} {event['event_id']} sha256={hashlib.sha256(line.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
