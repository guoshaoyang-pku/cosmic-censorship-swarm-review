#!/usr/bin/env python3
"""One-shot append-only hash re-binding for W043G after the post-ingest restamp.

The first W043G emission bound report.json, raw/history_frontier_raw.json and MANIFEST.json
at hashes produced while those files still carried wall-clock stamps; a subsequent
determinism check re-ran the instrument and the stamps (and therefore the hashes) moved.
The instrument and emitter are now byte-deterministic (fixed STAMP).  This script emits
superseding artifact events for the three drifted paths plus one status correction, so the
latest event per path equals the bytes on disk.  It never edits or deletes prior events.

Idempotent: skips event_ids already present in the outbox.
"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-043.jsonl"
TASK = "W043G-F2B-HISTORY-CLOSURE-01"
STAMP = "2026-09-12T01:24:00+08:00"

SUPERSEDES = {
    "raw": ("w043g-artifact-raw", "artifacts/worker-043/w043g_f2b_history_closure/raw/history_frontier_raw.json",
            "76ccd36f27cd"),
    "report": ("w043g-artifact-report", "artifacts/worker-043/w043g_f2b_history_closure/report.json",
               "b74639830c68"),
    "manifest": ("w043g-artifact-manifest", "artifacts/worker-043/w043g_f2b_history_closure/MANIFEST.json",
                 "c5abfb7b4d83"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    outbox_ids = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                outbox_ids.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue

    events = []
    for key, (old_id, relp, old_sha) in SUPERSEDES.items():
        p = ROOT / relp
        new_sha = sha(p)
        events.append({
            "event_id": f"w043g-artifact-{key}-r2", "event_type": "artifact",
            "created_at": STAMP, "actor": "worker-043", "task_id": TASK, "gate": "G-FORM",
            "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
            "artifact_type": ("measurement_raw" if key == "raw" else
                              "report" if key == "report" else "manifest"),
            "path": relp, "sha256": new_sha, "validation_status": "unverified",
            "supersedes": old_id, "supersedes_sha256": old_sha,
            "restamp_reason": ("post-ingest determinism repair: the first emission bound this path while it "
                               "still carried a wall-clock generated_at/created_at; the instrument and emitter "
                               "now use a fixed STAMP, so this hash is the stable authoritative one"),
            "evidence_refs": [f"{relp}#{new_sha[:12]}"],
        })

    relp = "artifacts/worker-043/w043g_f2b_history_closure/emit_hash_correction.py"
    events.append({
        "event_id": "w043g-artifact-correction-script", "event_type": "artifact",
        "created_at": STAMP, "actor": "worker-043", "task_id": TASK, "gate": "G-FORM",
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "artifact_type": "instrument",
        "path": relp, "sha256": sha(ROOT / relp), "validation_status": "unverified",
        "evidence_refs": [f"{relp}#{sha(ROOT / relp)[:12]}"],
    })

    drifted = ", ".join(f"{k}:{v[2]}->{events[i]['sha256'][:12]}" for i, (k, v) in enumerate(SUPERSEDES.items()))
    events.append({
        "event_id": "w043g-status-hash-restamp-correction", "event_type": "status",
        "created_at": STAMP, "actor": "worker-043", "task_id": TASK, "gate": "G-FORM",
        "node_id": "F2b", "node_ids": ["F2b"], "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"], "status": "active", "hours": 0.1,
        "summary": ("Correction after ingest: the three artifact events w043g-artifact-raw/-report/-manifest "
                    "bound hashes taken before the instrument was made byte-deterministic; re-running the "
                    "instrument moved only the wall-clock generated_at/created_at stamps. Determinism repair "
                    f"is now in place (fixed STAMP) and the -r2 artifact events re-bind {drifted}. Claim "
                    "statement, review findings, controls (9/9), pin set (14/14) and the closure candidate "
                    "28dc0d3df53d are unchanged; the earlier report/raw hashes cited inside "
                    "w043g-claim-history-frontier and w043g-review-f2b-history are superseded by the -r2 "
                    "events. Two consecutive instrument+emitter runs now append zero events and reproduce "
                    "identical hashes."),
        "evidence_refs": [f"artifacts/worker-043/w043g_f2b_history_closure/MANIFEST.json#{sha(OUT / 'MANIFEST.json')[:12]}",
                          f"artifacts/worker-043/w043g_f2b_history_closure/report.json#{sha(OUT / 'report.json')[:12]}",
                          f"artifacts/worker-043/w043g_f2b_history_closure/raw/history_frontier_raw.json#{sha(OUT / 'raw' / 'history_frontier_raw.json')[:12]}"],
        "next_falsifier": ("Re-run check_f2b_history_closure.py and emit_events.py twice: any appended event or "
                           "any hash move falsifies the determinism claim; a reviewer reproducing report.json "
                           "from the pinned inputs and the fixed STAMP must obtain the bound hash."),
    })

    appended = 0
    with OUTBOX.open("a") as fh:
        for e in events:
            if e["event_id"] in outbox_ids:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1
    print(json.dumps({"appended": appended, "total": len(events),
                      "authoritative": {k: events[i]["sha256"][:12] for i, k in enumerate(SUPERSEDES)}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
