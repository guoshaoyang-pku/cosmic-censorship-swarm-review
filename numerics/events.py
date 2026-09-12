"""Structured event emission for the numerics group.

Conforms to ``comms/PROTOCOL.md`` and ``research_map/schemas.py``:

* upward stream: ``comms/outbox/astra-lead-numerics.jsonl`` (append-only);
* ``status``  requires node_id, status, hours, summary, evidence_refs, next_falsifier;
* ``blocker`` requires node_id, description, needed_to_unblock, evidence_refs;
* ``artifact`` requires node_id, artifact_type, path, sha256, validation_status.

Blockers are additionally mirrored to ``artifacts/numerics/blockers.jsonl`` and
statuses to ``artifacts/numerics/status.jsonl`` so the numerics record survives
outbox rotation.  Callers may pass a deterministic ``event_id`` so re-publication
of an unchanged artifact is deduplicated by the ingest bus.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTOR = "astra-lead-numerics"
OUTBOX = "comms/outbox/astra-lead-numerics.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _event_id(prefix: str) -> str:
    return f"lnum-{prefix}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"


def det_id(prefix: str, *parts: str) -> str:
    """Deterministic event id from content, for idempotent re-publication."""
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]
    return f"lnum-{prefix}-{digest}"


def append_event(event: dict, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _find_existing(path: Path, event_id: str) -> dict | None:
    """Return an already-appended event with this id, for idempotent re-publication."""
    if not path.is_file():
        return None
    for line in path.read_text(errors="replace").splitlines():
        if event_id not in line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict) and doc.get("event_id") == event_id:
            return doc
    return None


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def emit(
    event_type: str,
    fields: dict,
    root: Path = REPO_ROOT,
    mirror: str | None = None,
    event_id: str | None = None,
) -> dict:
    event = {
        "event_id": event_id or _event_id(event_type),
        "event_type": event_type,
        "created_at": _now(),
        "actor": ACTOR,
    }
    event.update(fields)
    if event_id is not None:
        existing = _find_existing(root / OUTBOX, event_id)
        if existing is not None:
            return existing
    append_event(event, root / OUTBOX)
    if mirror:
        append_event(event, root / mirror)
    return event


def emit_status(
    node_id: str,
    status: str,
    hours: float,
    summary: str,
    evidence_refs: list[str],
    next_falsifier: str,
    group_id: str = "numerics",
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    return emit(
        "status",
        {
            "node_id": node_id,
            "group_id": group_id,
            "status": status,
            "hours": hours,
            "summary": summary,
            "evidence_refs": evidence_refs,
            "next_falsifier": next_falsifier,
        },
        root=root,
        mirror="artifacts/numerics/status.jsonl",
        event_id=event_id,
    )


def emit_blocker(
    node_id: str,
    description: str,
    needed_to_unblock: str,
    evidence_refs: list[str],
    group_id: str = "numerics",
    severity: str = "high",
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    return emit(
        "blocker",
        {
            "node_id": node_id,
            "group_id": group_id,
            "description": description,
            "needed_to_unblock": needed_to_unblock,
            "evidence_refs": evidence_refs,
            "severity": severity,
        },
        root=root,
        mirror="artifacts/numerics/blockers.jsonl",
        event_id=event_id,
    )


def emit_artifact(
    node_id: str,
    artifact_type: str,
    path: str,
    validation_status: str,
    root: Path = REPO_ROOT,
    sha256: str | None = None,
    validation_evidence: list[str] | None = None,
    mirror: str = "artifacts/numerics/artifacts.jsonl",
    event_id: str | None = None,
) -> dict:
    fields = {
        "node_id": node_id,
        "artifact_type": artifact_type,
        "path": path,
        "sha256": sha256 or sha256_file(path),
        "validation_status": validation_status,
        "validation_evidence": validation_evidence or [],
    }
    return emit("artifact", fields, root=root, mirror=mirror, event_id=event_id)


def emit_claim(
    class_id: str,
    statement: str,
    conclusion_type: str,
    assumptions: list[str],
    falsifier: str,
    evidence_refs: list[str],
    node_id: str | None = None,
    group_id: str = "numerics",
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    fields = {
        "class_id": class_id,
        "statement": statement,
        "conclusion_type": conclusion_type,
        "assumptions": assumptions,
        "falsifier": falsifier,
        "evidence_refs": evidence_refs,
    }
    if node_id:
        fields["node_id"] = node_id
    if group_id:
        fields["group_id"] = group_id
    return emit("claim", fields, root=root, mirror="artifacts/numerics/claims.jsonl",
                event_id=event_id)


def emit_review(
    target_id: str,
    verdict: str,
    score: float,
    hard_failures: list[str],
    findings: list[str],
    reviewer: str = ACTOR,
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    return emit(
        "review",
        {
            "target_id": target_id,
            "reviewer": reviewer,
            "verdict": verdict,
            "score": score,
            "hard_failures": hard_failures,
            "findings": findings,
        },
        root=root,
        mirror="artifacts/numerics/reviews.jsonl",
        event_id=event_id,
    )


def emit_direction_update(
    group_id: str,
    old_direction: str,
    new_direction: str,
    reason: str,
    evidence_refs: list[str],
    budget_delta_agent_hours: float,
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    return emit(
        "direction_update",
        {
            "group_id": group_id,
            "old_direction": old_direction,
            "new_direction": new_direction,
            "reason": reason,
            "evidence_refs": evidence_refs,
            "budget_delta_agent_hours": budget_delta_agent_hours,
        },
        root=root,
        event_id=event_id,
    )


def emit_gate(
    gate_id: str,
    scope: str,
    verdict: str,
    criteria: str,
    evidence_refs: list[str],
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    return emit(
        "gate",
        {
            "gate_id": gate_id,
            "scope": scope,
            "verdict": verdict,
            "criteria": criteria,
            "evidence_refs": evidence_refs,
        },
        root=root,
        event_id=event_id,
    )


def emit_resource_request(
    group_id: str,
    requested_agents: int,
    requested_agent_hours: float,
    justification: str,
    expected_information_gain: str,
    stop_rule: str,
    node_id: str | None = None,
    root: Path = REPO_ROOT,
    event_id: str | None = None,
) -> dict:
    fields = {
        "group_id": group_id,
        "requested_agents": requested_agents,
        "requested_agent_hours": requested_agent_hours,
        "justification": justification,
        "expected_information_gain": expected_information_gain,
        "stop_rule": stop_rule,
    }
    if node_id:
        fields["node_id"] = node_id
    return emit("resource_request", fields, root=root, event_id=event_id)
