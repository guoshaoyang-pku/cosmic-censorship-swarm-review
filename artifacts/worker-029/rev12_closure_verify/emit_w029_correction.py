#!/usr/bin/env python3
"""
Append the post-emission correction record for W029-REV12-CLOSURE-03.

Why this exists: REVIEW.md was edited after the artifact events were emitted (a controller note was
appended to its Reproduce section), so its sha256 changed.  The review/claim already emitted point
at report.json#… and evidence.json#…, which are unchanged; this record pins the new REVIEW.md hash
so no stale hash remains in the outbox.  Idempotent on event_id.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
HERE = Path(__file__).resolve().parent
REL = "artifacts/worker-029/rev12_closure_verify"
TASK = "W029-REV12-CLOSURE-03"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"

OLD = "95d26088f9f464063b65d2372b41a44d8455d9de526ff8dc5122ffe09a8244d2"
new_readme = hashlib.sha256((HERE / "REVIEW.md").read_bytes()).hexdigest()
report_hash = hashlib.sha256((HERE / "report.json").read_bytes()).hexdigest()
evidence_hash = hashlib.sha256((HERE / "evidence.json").read_bytes()).hexdigest()

EVENT = {
    "event_id": "w029r-20260912T0042-artifact-review-corrected",
    "event_type": "artifact",
    "created_at": NOW,
    "actor": "worker-029",
    "node_id": "F1,F2a,F2b",
    "class_id": CLASSES,
    "gate": "G-FORM",
    "task_id": TASK,
    "artifact_type": "summary",
    "path": f"{REL}/REVIEW.md",
    "sha256": new_readme,
    "supersedes_sha256": OLD,
    "validation_status": "unverified",
    "note": (
        "Hash correction: REVIEW.md gained a controller note (fleet-wide claim: invalid "
        "conclusion_type rejects; permitted enum in research_map/schemas.py:46). report.json and "
        "evidence.json are unchanged and remain bound at their emitted hashes; the emitted review "
        "and claim reference those two, not this file. No verdict, score, or finding changed."
    ),
    "evidence_refs": [
        f"{REL}/report.json#{report_hash[:12]}",
        f"{REL}/evidence.json#{evidence_hash[:12]}",
        "research_map/schemas.py:46",
    ],
    "falsifier": (
        "Re-hash artifacts/worker-029/rev12_closure_verify/REVIEW.md: this correction is falsified if "
        "the file does not hash to the value above, or if report.json/evidence.json no longer hash to "
        "their emitted values (the binding is then superseded)."
    ),
}

try:
    validate_event(dict(EVENT))
except SchemaError as ex:
    print("VALIDATION FAILED — nothing written:", ex)
    sys.exit(1)

outbox = ROOT / "comms/outbox/worker-029.jsonl"
existing = set()
for line in outbox.read_text().splitlines():
    if line.strip():
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            pass
if EVENT["event_id"] in existing:
    print("already present; nothing appended")
else:
    with outbox.open("a") as f:
        f.write(json.dumps(EVENT) + "\n")
    print("appended", EVENT["event_id"])
print("REVIEW.md", OLD[:12], "->", new_readme[:12])
print("report.json", report_hash[:12], "| evidence.json", evidence_hash[:12])
