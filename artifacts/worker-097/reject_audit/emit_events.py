#!/usr/bin/env python3
"""Emit W097-REJECT-STREAM-AUDIT-01 events to comms/outbox/worker-097.jsonl (append)
and write the worker checkpoint. Every event is validated with the pinned schemas.py
before it is written. No canonical file is modified.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
now = lambda: datetime.now(CST).isoformat(timespec="seconds")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUTBOX = ROOT / "comms/outbox/worker-097.jsonl"
CKPT = ROOT / "runtime/state/w097_checkpoint_reject_audit.json"
CKPT_LOG = ROOT / "runtime/state/w097_checkpoints.jsonl"
TASK = "W097-REJECT-STREAM-AUDIT-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


schemas = load("pinned_schemas_emit", "research_map/schemas.py")

rep_path = HERE / "report.json"
ctl_path = HERE / "controls.json"
aud_path = HERE / "audit.py"
pre_path = HERE / "PRE_REGISTRATION.md"
rdm_path = HERE / "README.md"
rep = json.loads(rep_path.read_text())
H = {p.name: sha256(p) for p in (rep_path, ctl_path, aud_path, pre_path, rdm_path)}
pins = rep["pins"]
LEDGER = "comms/rejected.jsonl"
summ = rep["summary"]

def ref(p: Path) -> str:
    return f"artifacts/worker-097/reject_audit/{p.name}#sha256:{sha256(p)}"

events = []
t = now()

events.append({
    "event_id": f"w097-rejectaudit-status-open-{t}",
    "event_type": "status", "created_at": t, "actor": "worker-097",
    "node_id": "A1", "class_id": ";".join(CLASS_IDS), "gate": "G-AUDIT",
    "task_id": TASK, "status": "active", "hours": 0.15,
    "summary": ("Took ONE bounded class-bound task (no inbox card for slot worker-097): "
                "W097-REJECT-STREAM-AUDIT-01, read-only replay of every row of comms/rejected.jsonl "
                "through the pinned ingest pipeline to test for class-bound evidence loss."),
    "evidence_refs": [f"{LEDGER}#sha256:{pins['comms/rejected.jsonl']['sha256']}",
                      "research_map/comms.py#sha256:" + pins["research_map/comms.py"]["sha256"],
                      "research_map/schemas.py#sha256:" + pins["research_map/schemas.py"]["sha256"]],
    "next_falsifier": ("Find a rejected event_id that is neither in research_map/events.jsonl nor in "
                       "runtime/state/ingested_ids.json, or a REPLAY_VALID row the pinned pipeline rejects."),
})

for k, label in [("report.json", "rejected-stream replay report (143 rows, per-row classification)"),
                 ("controls.json", "5 pre-registered controls (C1 accepted-sample replay, C2a/C2b synthetic, C3 determinism, C4 pin drift)"),
                 ("audit.py", "stdlib-only fail-closed instrument (pins on drift, exit 3)"),
                 ("PRE_REGISTRATION.md", "pre-registration with 5 predictions and the falsifier, written before measurement")]:
    events.append({
        "event_id": f"w097-rejectaudit-artifact-{k}-{t}",
        "event_type": "artifact", "created_at": t, "actor": "worker-097",
        "node_id": "A1", "artifact_type": "evidence_audit_artifact",
        "path": f"artifacts/worker-097/reject_audit/{k}",
        "sha256": sha256(HERE / k), "validation_status": "unverified",
        "class_id": ";".join(CLASS_IDS), "gate": "G-AUDIT", "task_id": TASK,
        "summary": label,
        "evidence_refs": [ref(HERE / k), f"{LEDGER}#sha256:{pins['comms/rejected.jsonl']['sha256']}"],
    })

events.append({
    "event_id": f"w097-rejectaudit-claim-stability-{t}",
    "event_type": "claim", "created_at": t, "actor": "worker-097",
    "node_id": "A1", "class_id": ";".join(CLASS_IDS), "gate": "G-AUDIT", "task_id": TASK,
    "conclusion_type": "stability_result",
    "statement": (f"At pins comms/rejected.jsonl#{pins['comms/rejected.jsonl']['sha256'][:12]} and "
                  f"comms.py#{pins['research_map/comms.py']['sha256'][:12]}: all "
                  f"{summ['total_rejected_rows']} rejected event_ids are accounted for in the accepted stream "
                  f"or the ingester seen-set (ACCEPTED_LATER {summ['statuses'].get('ACCEPTED_LATER',0)}, "
                  f"ACCEPTED_ID_ONLY {summ['statuses'].get('ACCEPTED_ID_ONLY',0)}, "
                  f"SOURCE_NOT_FOUND_ACCEPTED {summ['statuses'].get('SOURCE_NOT_FOUND_ACCEPTED',0)}); "
                  f"replay-valid-not-in-stream {summ['replay_valid_not_in_stream']}, lost rows "
                  f"{summ['replay_invalid_lost']}; lost class-bound rows are 0 for all four frozen classes. "
                  "The rejected stream is transient bookkeeping, not a class-bound evidence-loss record."),
    "assumptions": [
        "event_id identity is the join key; a later accepted event with the same id counts as recovery",
        "runtime/state/ingested_ids.json is the ingester seen-set (includes rejected and duplicate ids)",
        "counts are instant-bound: rejected.jsonl grew from 138 to 143 rows while this audit ran",
    ],
    "falsifier": ("Find one rejected event_id absent from both research_map/events.jsonl and "
                  "runtime/state/ingested_ids.json, or show a rejected event carries a class id that never "
                  "reaches the accepted stream under any id."),
    "evidence_refs": [ref(rep_path), ref(ctl_path), ref(aud_path),
                      f"{LEDGER}#sha256:{pins['comms/rejected.jsonl']['sha256']}"],
    "artifact_refs": [ref(rep_path), ref(ctl_path)],
})

events.append({
    "event_id": f"w097-rejectaudit-status-final-{t}",
    "event_type": "status", "created_at": t, "actor": "worker-097",
    "node_id": "A1", "class_id": ";".join(CLASS_IDS), "gate": "G-AUDIT",
    "task_id": TASK, "status": "active", "hours": 0.2,
    "summary": (f"CHECKPOINT + EXIT. {TASK} complete at worker level: 143/143 reject rows accounted for, "
                "0 class-bound evidence loss, 5/5 controls PASS, pins re-measured. Worker measurement only; "
                "no ingest, no gate verdict, no node status, no canonical write."),
    "evidence_refs": [ref(rep_path), ref(ctl_path), ref(aud_path)],
    "next_falsifier": rep["falsifier"],
})

# validate + append
lines = []
for e in events:
    schemas.validate_event(e)
    lines.append(json.dumps(e, sort_keys=True))
with OUTBOX.open("a") as f:
    for ln in lines:
        f.write(ln + "\n")

ck = {
    "task_id": TASK, "actor": "worker-097", "created_at": t, "status": "complete_worker_level",
    "gate": "G-AUDIT", "node_id": "A1", "class_ids": CLASS_IDS,
    "pins": {k: v["sha256"] for k, v in pins.items() if isinstance(v, dict) and v.get("sha256")},
    "deliverables": {f"artifacts/worker-097/reject_audit/{k}": v for k, v in H.items()},
    "controls_pass": rep["controls_pass"], "controls": rep["controls"],
    "summary": summ,
    "events_appended": len(events),
    "outbox": "comms/outbox/worker-097.jsonl",
    "authority": "worker measurement only; no gate verdict, no node status, no canonical write",
    "falsifier": rep["falsifier"],
    "checkpoint_prev": "runtime/state/w097_checkpoint_l0_rev4_review.json",
}
ck["checkpoint_sha256_self"] = None
CKPT.write_text(json.dumps(ck, indent=1))
with CKPT_LOG.open("a") as f:
    f.write(json.dumps({"task_id": TASK, "at": t, "checkpoint": str(CKPT.relative_to(ROOT)),
                        "sha256": sha256(CKPT), "events": len(events),
                        "controls_pass": rep["controls_pass"]}, sort_keys=True) + "\n")
print(json.dumps({"events": len(events), "outbox_sha256": sha256(OUTBOX),
                  "checkpoint_sha256": sha256(CKPT), "controls_pass": rep["controls_pass"]}, indent=1))
