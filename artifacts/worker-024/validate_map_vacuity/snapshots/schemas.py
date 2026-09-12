"""Typed validation for research-map events and artifacts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

# Upward (group lead -> Astra): status, claim, artifact, blocker, direction_update, resource_request
# Downward (Astra -> group lead/worker): assignment, budget, gate, priority_change, kill, revive
EVENT_TYPES = {
    "direction_update", "claim", "artifact", "review", "resource_request",
    "status", "blocker", "assignment", "budget", "gate", "priority_change",
    "kill", "revive",
}
UPWARD = {"status", "claim", "artifact", "blocker", "direction_update", "resource_request"}
DOWNWARD = {"assignment", "budget", "gate", "priority_change", "kill", "revive"}
STATUSES = {"queued", "active", "blocked", "done", "rejected", "killed"}

@dataclass
class SchemaError(Exception):
    message: str
    def __str__(self): return self.message

def _required(x: dict, keys: tuple[str, ...], label: str):
    missing = [k for k in keys if k not in x]
    if missing: raise SchemaError(f"{label}: missing {', '.join(missing)}")

def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    _required(event, ("event_id", "event_type", "created_at", "actor"), "event")
    typ = event["event_type"]
    if typ not in EVENT_TYPES: raise SchemaError(f"event: unknown event_type {typ}")
    validators = {
        "direction_update": (("group_id", "old_direction", "new_direction", "reason", "evidence_refs", "budget_delta_agent_hours"),),
        "claim": (("class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"),),
        "artifact": (("node_id", "artifact_type", "path", "sha256", "validation_status"),),
        "review": (("target_id", "reviewer", "verdict", "score", "hard_failures", "findings"),),
        "resource_request": (("group_id", "requested_agents", "requested_agent_hours", "justification", "expected_information_gain", "stop_rule"),),
        "status": (("node_id", "status", "hours", "summary", "evidence_refs", "next_falsifier"),),
        "blocker": (("node_id", "description", "needed_to_unblock", "evidence_refs"),),
        "assignment": (("node_id", "assignee", "artifact", "gate", "evidence_refs", "falsifier"),),
        "budget": (("group_id", "delta_agent_hours", "reason"),),
        "gate": (("gate_id", "scope", "verdict", "criteria", "evidence_refs"),),
        "priority_change": (("scope", "old_priority", "new_priority", "reason"),),
        "kill": (("target_id", "reason"),),
        "revive": (("target_id", "reason"),),
    }
    _required(event, validators[typ][0], typ)
    if typ == "claim" and event["conclusion_type"] not in {"theorem", "conditional_theorem", "stability_result", "counterexample", "numerical_evidence", "formal_model", "open_problem"}:
        raise SchemaError("claim: invalid conclusion_type")
    if typ == "artifact" and event["validation_status"] not in {"unverified", "passed", "failed", "retracted"}:
        raise SchemaError("artifact: invalid validation_status")
    if typ == "review" and event["verdict"] not in {"accept", "revise", "reject", "inconclusive"}:
        raise SchemaError("review: invalid verdict")
    if typ == "review" and not (0 <= float(event["score"]) <= 5): raise SchemaError("review: score must be 0..5")
    if typ == "status" and event["status"] not in STATUSES: raise SchemaError("status: invalid node status")
    if typ == "gate" and event["verdict"] not in {"pass", "fail", "pending"}: raise SchemaError("gate: invalid verdict")
    if typ == "claim" and event.get("conclusion_type") == "theorem" and not event.get("artifact_refs"):
        raise SchemaError("claim: theorem conclusion requires artifact_refs (no fluent-text promotion)")
    return event

def validate_artifact_hash(path: str, expected: str) -> bool:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest() == expected
