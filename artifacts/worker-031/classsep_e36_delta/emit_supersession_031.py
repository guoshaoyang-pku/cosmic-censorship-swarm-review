#!/usr/bin/env python3
"""Append the supersession/closure event for W031-CLASSSEP-E36-DELTA-01.

Why this file exists. The main emitter (emit_events_031.py) was run three times while
the deliverable hashes were still settling, so the controller ledger
(research_map/events.jsonl, runtime/state/ingested_ids.json) contains three
w031-e36 revisions. The two earlier revisions were withdrawn from the outbox before
this checkpoint (01:12:30 reproduced the detector's toxic composite in its claim text
and tripped the live detector on self-scan; 01:14:30 carried a pre-final report hash).
This event closes that trace explicitly: it names the two withdrawn event_ids, the one
surviving revision, and the stable hashes, so a reader of the ledger does not have to
infer which revision is operative.

Idempotent by event_id. Writes only to the worker's lifecycle outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LIFECYCLE_OUTBOX = ROOT / "comms/outbox/worker-031.jsonl"
STAMP = "20260912T012000"
NOW = "2026-09-12T01:20:00+08:00"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    event = {
        "actor": "worker-031",
        "event_id": f"w031-e36-{STAMP}-supersession-closure",
        "event_type": "status",
        "outside_event_schema": True,
        "created_at": NOW,
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "status": "active",
        "status_subtype": "revision_supersession",
        "task_id": "W031-CLASSSEP-E36-DELTA-01",
        "surviving_revision": "w031-e36-20260912T011700",
        "withdrawn_revisions": {
            "w031-e36-20260912T011230": (
                "withdrawn from the outbox before checkpoint; its claim text reproduced the "
                "detector's own toxic composite and the live detector flagged it on self-scan "
                "(0 CLASSSEP findings after rewording)"),
            "w031-e36-20260912T011430": (
                "withdrawn from the outbox before checkpoint; correct wording but bundled the "
                "pre-final report sha256"),
        },
        "operative_hashes": {
            "artifacts/worker-031/classsep_e36_delta/out/report.json": sha256(HERE / "out/report.json"),
            "artifacts/worker-031/classsep_e36_delta/measure_e36_delta_031.py":
                sha256(HERE / "measure_e36_delta_031.py"),
            "artifacts/worker-031/classsep_e36_delta/README.md": sha256(HERE / "README.md"),
            "artifacts/worker-031/classsep_e36_delta/CHECKPOINT.json":
                sha256(HERE / "CHECKPOINT.json"),
            "comms/outbox/worker-031-classsep-e36.jsonl":
                sha256(ROOT / "comms/outbox/worker-031-classsep-e36.jsonl"),
        },
        "note": (
            "Supersession is by event_id, not by content: the two withdrawn revisions remain "
            "in the controller ledger and MUST NOT be read as operative. The report and "
            "checkpoint have been re-verified against the surviving revision's hashes, and "
            "every surviving w031-e36 event scans clean under the live detector "
            "a8c04fc31e4a."),
    }
    seen = set()
    if LIFECYCLE_OUTBOX.exists():
        for line in LIFECYCLE_OUTBOX.read_text(errors="replace").splitlines():
            if '"event_id"' in line:
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:  # noqa: BLE001
                    pass
    if event["event_id"] in seen:
        print("idempotent skip:", event["event_id"])
        return 0
    with LIFECYCLE_OUTBOX.open("a") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
    print("emitted:", event["event_id"])
    print("lifecycle outbox:", sha256(LIFECYCLE_OUTBOX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
