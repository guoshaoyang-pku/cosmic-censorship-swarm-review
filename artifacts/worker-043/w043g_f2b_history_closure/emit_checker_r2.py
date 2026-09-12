#!/usr/bin/env python3
"""Final W043G re-binding: the checker instrument was patched post-ingest to make its outputs
byte-deterministic (fixed STAMP), so the ingested w043g-artifact-checker hash is superseded.
This script emits that one artifact event plus an artifact event for itself.  Idempotent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-043.jsonl"
TASK = "W043G-F2B-HISTORY-CLOSURE-01"
STAMP = "2026-09-12T01:24:00+08:00"
REL = "artifacts/worker-043/w043g_f2b_history_closure/check_f2b_history_closure.py"
SELF = "artifacts/worker-043/w043g_f2b_history_closure/emit_checker_r2.py"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    events = [{
        "event_id": "w043g-artifact-checker-r2", "event_type": "artifact",
        "created_at": STAMP, "actor": "worker-043", "task_id": TASK, "gate": "G-FORM",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "artifact_type": "instrument",
        "path": REL, "sha256": sha(ROOT / REL), "validation_status": "unverified",
        "supersedes": "w043g-artifact-checker", "supersedes_sha256": "6c473fb68c97",
        "restamp_reason": ("the instrument was patched after ingest to replace the wall-clock generated_at "
                           "with a fixed STAMP so that report.json/raw/MANIFEST.json are byte-deterministic; "
                           "checks, controls, verdict and pins are unchanged, verified by two consecutive "
                           "re-runs producing identical bytes"),
        "evidence_refs": [f"{REL}#{sha(ROOT / REL)[:12]}"],
    }, {
        "event_id": "w043g-artifact-checker-r2-emitter", "event_type": "artifact",
        "created_at": STAMP, "actor": "worker-043", "task_id": TASK, "gate": "G-FORM",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "artifact_type": "instrument",
        "path": SELF, "sha256": sha(ROOT / SELF), "validation_status": "unverified",
        "evidence_refs": [f"{SELF}#{sha(ROOT / SELF)[:12]}"],
    }]
    appended = 0
    with OUTBOX.open("a") as fh:
        for e in events:
            if e["event_id"] in seen:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1
    print(json.dumps({"appended": appended,
                      "checker": sha(ROOT / REL)[:12], "emitter": sha(ROOT / SELF)[:12]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
