#!/usr/bin/env python3
"""Append the clock-label correction event for W054-GFORM-LIVE-ACCEPT-CENSUS-01
and patch the worker-local checkpoint.  Append-only; no hash-pinned byte changes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-054.jsonl"
CKPT = ROOT / "runtime" / "state" / "w054_gform_live_accept_census_checkpoint.json"

summary = (
    "CLOCK-LABEL CORRECTION (append-only; no artifact byte changed). The batch "
    "w054-gformcov-2026-09-12T01:25:00+08:00 and report.json --created-at 2026-09-12T01:23:00+08:00 "
    "were authored ahead of the true wall clock. The census was measured at approximately "
    "2026-09-12T01:19:40-01:20:20+08:00 and the events were ingested by checkpoint "
    "ckpt-20260912-012038 at 2026-09-12T01:20:38+08:00 (label worker-054-gform-live-accept-census). "
    "Substantive anchors are the pinned input hashes (F1 d9cebb9404b2, F2a e9a27996dfd3, "
    "F2b b2ab6acb2bbe, FROZEN 815e08079aef) and the report/census/checker hashes, not the "
    "timestamp labels; no count, classification, control or falsifier changes. Report bytes stay "
    "at sha256 28d512e7e5a7."
)

ev = {
    "actor": "worker-054",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "node_id": "F1,F2a,F2b",
    "gate": "G-FORM",
    "created_at": "2026-09-12T01:21:30+08:00",
    "event_id": "w054-gformcov-2026-09-12T01:21:30+08:00-status-clock-correction",
    "event_type": "status",
    "status": "active",
    "task_id": "W054-GFORM-LIVE-ACCEPT-CENSUS-01",
    "summary": summary,
    "evidence_refs": [
        "artifacts/worker-054/gform_live_accept_census/report.json#28d512e7e5a7",
        "artifacts/worker-054/gform_live_accept_census/census.json#622384cb3305",
        "artifacts/worker-054/gform_live_accept_census/checker.py#18f93669ae3e",
        "runtime/state/checkpoints/ckpt-20260912-012038.json",
    ],
    "checkpoint_id": "ckpt-20260912-012038",
    "next_falsifier": (
        "Re-run checker.py against unchanged bytes; any changed classification, control or input "
        "hash falsifies the census. The clock correction is falsified only if the events were in "
        "fact emitted at 01:25:00+08:00, which the checkpoint ingest time 01:20:38 rules out."
    ),
    "not_claimed": ["no gate verdict", "no node status", "no validation_status=passed"],
}

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            continue
if ev["event_id"] not in existing:
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, sort_keys=True) + "\n")

d = json.loads(CKPT.read_text())
d["created_at_label"] = "2026-09-12T01:25:00+08:00"
d["wall_clock_at_emit"] = "2026-09-12T01:20:5x+08:00"
d["clock_correction"] = ("labels 01:23:00/01:25:00 were ahead of wall clock; measurement window "
                         "~01:19:40-01:20:20; ingested by ckpt-20260912-012038 at 01:20:38; the "
                         "hashes are the anchors")
if ev["event_id"] not in d["events_emitted"]:
    d["events_emitted"].append(ev["event_id"])
CKPT.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
print("appended", ev["event_id"])
