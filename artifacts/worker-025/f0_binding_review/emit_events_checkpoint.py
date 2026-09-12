#!/usr/bin/env python3
"""Emit the four protocol events to comms/outbox/worker-025.jsonl and the worker checkpoint.
Idempotent by event_id. Aborts if the bound F0 hash moved since the review was written.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-025.jsonl"
STATE = ROOT / "runtime/state"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


review_path = ROOT / "reviews/F0-review-025.json"
ev_path = HERE / "evidence.json"
review = json.loads(review_path.read_text())
evidence = json.loads(ev_path.read_text())
BOUND = review["reviewed_sha256"]
live = sha(ROOT / "research_map/formulation_taxonomy.yaml")
if live != BOUND:
    print(json.dumps({"MOVING_TARGET_AT_EMIT": {"bound": BOUND, "live": live}}, indent=1))
    raise SystemExit(2)

TS = time.strftime("%Y%m%dT%H%M%S")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
REV_H = sha(review_path)
EV_H = sha(ev_path)
FROZEN_H = sha(ROOT / "artifacts/formulation/FROZEN.json")
CKPT_NAME = f"w025_f0_bind_checkpoint_{TS}.json"
CKPT_PATH = STATE / CKPT_NAME

refs = [
    f"research_map/formulation_taxonomy.yaml#{BOUND[:12]}",
    f"artifacts/formulation/FROZEN.json#{FROZEN_H[:12]}",
    f"reviews/F0-review-025.json#{REV_H[:12]}",
    f"artifacts/worker-025/f0_binding_review/evidence.json#{EV_H[:12]}",
    "artifacts/worker-025/f0_binding_review/raw/final_output.json",
    "artifacts/worker-025/f0_binding_review/SHA256SUMS",
]

summary_common = ("Independent G-F0 binding review of canonical F0 at 0abb9ed8 (rev5, settled after the "
                  "closure revision). Verdict accept, score 4.0, no hard failures: D1/D3 discharged, "
                  "no duplicate keys, FROZEN rev28 verifies 0 problems, all three schemas bind the live "
                  "canonical hash and their class_contract_pointer targets #classes.<CID>, consistency and "
                  "class-schema checkers exit 0, class-separation 0 findings. Two non-blocking objections "
                  "(scalar genericity_kind unresolved; draft_unverified status) and the open REC-1/REC-2 "
                  "companion-pair decision are recorded. No gate verdict claimed.")

events = [
    {
        "event_id": f"w025-f0bind-{TS}-status-active",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-025",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-F0",
        "task_id": "W025-F0-BIND-01",
        "status": "active",
        "hours": 0.5,
        "completion_scope": "worker lifecycle only; not a node done / gate verdict",
        "summary": "Took item (2) of leadform-resource-request-2026-09-12T00:44: bind research_map/formulation_taxonomy.yaml for G-F0. Observed the closure revision land mid-first-probe (F0 276009f4 -> 0abb9ed8 at 00:31:41, schemas -> cce9c601/5476a3f2/55d0a1ea at 00:32:02, FROZEN drift), waited for FROZEN rev28 (0 problems), then re-measured stability over 20 s + 3x15 s before binding. Wrote independent probe/recheck/final-verify scripts, evidence bundle and reviews/F0-review-025.json.",
        "evidence_refs": refs,
        "next_falsifier": evidence["next_falsifier"],
    },
    {
        "event_id": f"w025-f0bind-{TS}-artifact",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-025",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-F0",
        "artifact_type": "independent_class_schema_review",
        "path": "reviews/F0-review-025.json",
        "sha256": REV_H,
        "validation_status": "unverified",
        "inputs_frozen": {
            "research_map/formulation_taxonomy.yaml": BOUND,
            "artifacts/formulation/FROZEN.json": FROZEN_H,
        },
        "supporting_artifacts": {
            "artifacts/worker-025/f0_binding_review/evidence.json": EV_H,
            "artifacts/worker-025/f0_binding_review/raw/final_output.json": sha(HERE / "raw/final_output.json"),
            "artifacts/worker-025/f0_binding_review/raw/probe_output.json": sha(HERE / "raw/probe_output.json"),
            "artifacts/worker-025/f0_binding_review/raw/recheck_output.json": sha(HERE / "raw/recheck_output.json"),
        },
        "summary": {"verdict": "accept", "score": 4.0, "hard_failures": [],
                    "checks": evidence["checks"]},
    },
    {
        "event_id": f"w025-f0bind-{TS}-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-025",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-F0",
        "target_id": f"research_map/formulation_taxonomy.yaml#{BOUND}",
        "reviewed_path": "research_map/formulation_taxonomy.yaml",
        "reviewed_sha256": BOUND,
        "reviewer": "worker-025",
        "independent": True,
        "counts_as_full_schema_verdict": True,
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "findings": evidence["findings"],
        "evidence_refs": refs,
        "falsifier": evidence["next_falsifier"],
    },
    {
        "event_id": f"w025-f0bind-{TS}-status-final",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-025",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-F0",
        "task_id": "W025-F0-BIND-01",
        "status": "active",
        "hours": 1.0,
        "completion_scope": "worker lifecycle only; this event is a completion claim, not a node done / gate verdict",
        "summary": "W025-F0-BIND-01 complete and bounded. " + summary_common,
        "evidence_refs": refs,
        "next_falsifier": evidence["next_falsifier"],
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
appended = []
with OUTBOX.open("a") as fh:
    for ev in events:
        if ev["event_id"] in existing:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        appended.append(ev["event_id"])

checkpoint = {
    "worker": "worker-025",
    "task_id": "W025-F0-BIND-01",
    "checkpoint_at": NOW,
    "status": "COMPLETE",
    "node_id": "F0",
    "class_ids": review["class_ids"],
    "gate": "G-F0",
    "verdict": "ACCEPT",
    "score": 4.0,
    "hard_failures": [],
    "pins": evidence["pins"],
    "checks": evidence["checks"],
    "events_emitted": [e["event_id"] for e in events],
    "checkpoint": f"runtime/state/{CKPT_NAME}",
    "artifacts": {
        "reviews/F0-review-025.json": REV_H,
        "artifacts/worker-025/f0_binding_review/evidence.json": EV_H,
        "artifacts/worker-025/f0_binding_review/probe_f0_binding.py": sha(HERE / "probe_f0_binding.py"),
        "artifacts/worker-025/f0_binding_review/recheck_f0_binding.py": sha(HERE / "recheck_f0_binding.py"),
        "artifacts/worker-025/f0_binding_review/final_verify_f0.py": sha(HERE / "final_verify_f0.py"),
        "artifacts/worker-025/f0_binding_review/SHA256SUMS": sha(HERE / "SHA256SUMS"),
    },
    "next_falsifier": evidence["next_falsifier"],
    "non_claims": evidence["non_claims"],
    "completion_scope": "worker lifecycle only; not a node done / gate verdict",
    "clock_note": "binding-time wall clock; the first probe observed the closure revision land mid-run (moving target, resolved by FROZEN rev28)",
}
CKPT_PATH.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
with (STATE / "w025_f0_bind_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

print(json.dumps({"appended_events": appended, "checkpoint": str(CKPT_PATH.relative_to(ROOT)),
                  "review_sha256": REV_H, "bound_f0": BOUND}, indent=1))
