#!/usr/bin/env python3
"""Idempotent emitter for the W012-LOCKGUARD-FAILCLOSED-01 live-drift addendum."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-12.jsonl"
CKPT_LOG = REPO / "runtime" / "state" / "w12_checkpoints.jsonl"
ADDENDUM = "artifacts/worker-012/n0/lockguard_failclosed/drift_addendum.json"
EMITTER = "artifacts/worker-012/n0/lockguard_failclosed/emit_drift.py"
NOW = "2026-09-12T00:47:00+08:00"
TASK = "W012-LOCKGUARD-FAILCLOSED-01"


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def artifact(eid: str, rel: str, atype: str, note: str) -> dict:
    return {
        "event_id": eid, "event_type": "artifact", "created_at": NOW, "actor": "deepseek-flash-12",
        "node_id": "N1-BLOCK", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
        "slot": "worker-012", "task_id": TASK,
        "artifact_type": atype, "path": rel, "sha256": sha(rel),
        "validation_status": "unverified", "note": note,
    }


EV = [
    artifact(
        "w012-lockguard-artifact-0009-drift", ADDENDUM, "drift_addendum",
        "Supersedes the blockers.md evidence citation in w012-lockguard-claim-0001: blockers.md moved 33dd7a21 -> 3c9d8a84 at 00:36:57 (C8 row update). Subject guard and candidate hashes unchanged; no matrix row changes.",
    ),
    artifact(
        "w012-lockguard-artifact-0010-drift-emitter", EMITTER, "protocol_event_emitter",
        "Emitter for the drift addendum events; idempotent by event_id.",
    ),
]

STATUS = {
    "event_id": "w012-lockguard-status-0002-drift",
    "event_type": "status", "created_at": NOW, "actor": "deepseek-flash-12",
    "node_id": "N1-BLOCK", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
    "slot": "worker-012", "task_id": TASK,
    "status": "active", "hours": 0.1, "kind": "drift_addendum",
    "summary": (
        "Live-drift addendum to W012-LOCKGUARD-FAILCLOSED-01: numerics/blockers.md moved 33dd7a21 -> 3c9d8a84"
        " at 00:36:57 (C8 protocol-review row 5 rewrite: a binding accept is now recorded and contested), while the"
        " subject guard 7535ec84ac9c, gates.py fcd1d709, candidate 0b72a987, matrix 7493b84d and the 11 fail-open"
        " witnesses are unchanged; no matrix re-run required. The claim's blockers.md evidence citation is superseded"
        " by 3c9d8a84; the must-fail-closed contract phrase is still present in the revised file."
    ),
    "evidence_refs": [
        f"{ADDENDUM}#{sha(ADDENDUM)[:12]}",
        "numerics/blockers.md#3c9d8a84d498",
        "numerics/tests/selfgravity_lock_guard.py#7535ec84ac9c",
        f"{EMITTER}#{sha(EMITTER)[:12]}",
    ],
    "next_falsifier": "Re-measure the guard: if its sha256 is no longer 7535ec84ac9c, or the revised blockers.md drops the must-fail-closed guard section, or guard_matrix.py at these hashes yields a different witness list, this addendum is void.",
    "claims_completion": False, "sets_gate_verdict": False, "sets_node_status": False,
}
EV.append(STATUS)

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass

for e in EV:
    validate_event(e)
new = [e for e in EV if e["event_id"] not in existing]
if new:
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

log = {
    "worker": "worker-012", "actor": "deepseek-flash-12", "at": NOW,
    "checkpoint": "4-drift", "path": "runtime/state/w12_checkpoint_4.json",
    "task": TASK, "verdict": "DRIFT_ADDENDUM: blockers.md citation superseded 33dd7a21 -> 3c9d8a84; subject unchanged",
    "addendum": ADDENDUM, "addendum_sha256": sha(ADDENDUM),
}
already = False
if CKPT_LOG.exists():
    for line in CKPT_LOG.read_text().splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("addendum_sha256") == log["addendum_sha256"]:
            already = True
            break
if not already:
    with CKPT_LOG.open("a") as fh:
        fh.write(json.dumps(log, ensure_ascii=False) + "\n")

print(json.dumps({"emitted": [e["event_id"] for e in new],
                  "addendum_sha256": sha(ADDENDUM),
                  "checkpoint_log_appended": not already}, indent=2))
