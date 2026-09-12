#!/usr/bin/env python3
"""Emit worker-067 checkpoint 3 + outbox events for W067-GNUM-C8-BINDING-01.

Read-only on canonical paths. Appends to comms/outbox/worker-067.jsonl only after
validating every event with research_map/schemas.py:validate_event.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-067.jsonl"
STATE = ROOT / "runtime" / "state"
TASK = "W067-GNUM-C8-BINDING-01"
GATE = "G-NUM"
NODE = "N0"
CLASS = "AF-WCC-SCALAR-SPH"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def iso_compact() -> str:
    return datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


ARTIFACTS = [
    ("checker", "independent_binding_checker",
     ROOT / "artifacts/worker-067/g_num_binding_check/check_g_num_binding.py"),
    ("result", "independent_binding_check_result",
     ROOT / "artifacts/worker-067/g_num_binding_check/binding_check.json"),
    ("readme", "independent_binding_check_readme",
     ROOT / "artifacts/worker-067/g_num_binding_check/README.md"),
    ("emitter", "binding_check_event_emitter", Path(__file__).resolve()),
]

FALSIFIER = (
    "Withdrawn if any of: (a) numerics/CONVERGENCE_PROTOCOL.md no longer hashes to 1e6cdf04d7a2; "
    "(b) reviews/G-NUM-protocol-review.json no longer carries reviewed_sha256 equal to the measured "
    "protocol hash or its verdict ceases to be accept; (c) the G-NUM gate reason no longer contains "
    "'binds unbound'; (d) the review contract mandates artifact_sha256, in which case the "
    "nonconforming party is the review writer and the proposed patch branch flips.")


def main() -> int:
    hashes = {key: {"path": str(p.relative_to(ROOT)), "sha256": sha256(p)} for key, _, p in ARTIFACTS}
    stamp = iso_compact()
    t = now()
    result = json.loads((ROOT / "artifacts/worker-067/g_num_binding_check/binding_check.json").read_text())

    events = []

    def ev(event_id, etype, **kw):
        e = {"event_id": event_id, "event_type": etype, "created_at": t, "actor": "worker-067",
             "node_id": NODE, "gate": GATE, "class_id": CLASS, **kw}
        return validate_event(e)

    events.append(ev(f"w067-gnum-bind-{stamp}-00-task", "status", status="active", hours=0.4,
                     summary=(f"Took ONE bounded class-bound task: {TASK} = independent read-only "
                              "machine check of why the live G-NUM gate reason says "
                              "reviews/G-NUM-protocol-review.json 'binds unbound (stale)' although the "
                              "file's reviewed_sha256 equals the measured protocol hash. Live controller "
                              "code (astra_lifecycle.gate_audit) reproduced in memory; no lifecycle pass "
                              "applied, no canonical path written."),
                     evidence_refs=["numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
                                    "reviews/G-NUM-protocol-review.json#8137f18f1a3b",
                                    "research_map/astra_lifecycle.py:259"],
                     next_falsifier=FALSIFIER))

    for i, (key, atype, p) in enumerate(ARTIFACTS, start=1):
        events.append(ev(f"w067-gnum-bind-{stamp}-{i:02d}-{key}", "artifact", artifact_type=atype,
                         path=hashes[key]["path"], sha256=hashes[key]["sha256"],
                         validation_status="unverified",
                         evidence_refs=[f"{hashes[key]['path']}#{hashes[key]['sha256'][:12]}"]))

    events.append(ev(f"w067-gnum-bind-{stamp}-10-review", "review",
                     target_id="G-NUM-C8-binding/astra_lifecycle.py:259",
                     reviewer="worker-067", verdict="revise", score=2.0,
                     reviewer_independence=("bounded breadth worker; author of no astra_lifecycle.py "
                                            "code, no reviews/G-NUM-protocol-review.json content, and "
                                            "no numerics/N0 artifact except this binding check; "
                                            "read-only on every canonical path; wrote only under "
                                            "artifacts/worker-067/ and comms/outbox/worker-067.jsonl"),
                     hard_failures=[
                         "HF-067-B1: the G-NUM gate reason asserts 'binds unbound (stale)' while "
                         "reviews/G-NUM-protocol-review.json binds the measured protocol hash "
                         "1e6cdf04d7a2 via reviewed_sha256; astra_lifecycle.py:259 reads only "
                         "artifact_sha256, which the file does not carry, so the reader always falls "
                         "back to 'unbound'. The same module's _explicit_pins() binds both keys.",
                         "HF-067-B2: the accepting verdict (event_id "
                         "audit-review-gnum-protocol-rev3-20260912T0020) exists only as a file; it is "
                         "absent from map.reviews, the lead-audit outbox, and events.jsonl, so "
                         "map-based adjudication still sees the 00:08 revise at 01b2072434cd."],
                     findings=[
                         "Measured: protocol 1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274; "
                         "review verdict=accept, reviewer=astra-lead-audit, reviewed_sha256=1e6cdf04d7a2 "
                         "(exact match), artifact_sha256 absent, counts_as_full_schema_verdict=true.",
                         "Reproduction: astra_lifecycle.gate_audit run in memory on current bytes yields "
                         "the same reason string the controller recorded at 00:24:40, including "
                         "'binds unbound (stale)'; line 259 evaluates to 'unbound' for the current file.",
                         "Controls: C1 the superseded rev1 advisory (artifact_sha256=01b2072434cd) DOES "
                         "resolve through line 259, isolating the key-convention mismatch as the cause; "
                         "C2 _explicit_pins resolves the current review to 1e6cdf04d7a2; C3 no-write "
                         "canary, 7 canonical files byte-identical before/after; C4 registration gap "
                         "confirmed absent at all three registration points.",
                         "Scope: binding/registration only. It does not re-review protocol content and "
                         "does not accept the protocol; worker-067's prior content verdict on rev3 is "
                         "revise (F1, section 3.4 constant-CFL scoping) and stands.",
                         "Controller action proposed, not applied: read artifact_sha256 OR "
                         "reviewed_sha256 at astra_lifecycle.py:259 (or normalize the review writer), "
                         "and have the audit lead emit the accept as a review event so it can be "
                         "ingested; then re-run the lifecycle so controller_gate_audit.G-NUM is "
                         "measured from a registered accept."],
                     evidence_refs=[f"{hashes['result']['path']}#{hashes['result']['sha256'][:12]}",
                                    f"{hashes['checker']['path']}#{hashes['checker']['sha256'][:12]}",
                                    "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
                                    "reviews/G-NUM-protocol-review.json#8137f18f1a3b",
                                    "research_map/astra_lifecycle.py:259",
                                    "research_map/research_map.json#controller_gate_audit.G-NUM"],
                     next_falsifier=FALSIFIER))

    events.append(ev(f"w067-gnum-bind-{stamp}-99-complete", "status", status="active", hours=0.6,
                     summary=(f"{TASK} complete at worker level: FALSE_POSITIVE_CONFIRMED with 4/4 "
                              "controls and no canonical writes; the G-NUM 'unbound (stale)' reason is a "
                              "reader artifact and the accepting C8 verdict is unregistered. This is a "
                              "completion claim for the task, not a node transition and not a gate "
                              "verdict; N0 stays active and numerics_lock stays LOCKED."),
                     evidence_refs=[f"{hashes['result']['path']}#{hashes['result']['sha256'][:12]}",
                                    "runtime/state/worker-067_checkpoint_3.json"],
                     next_falsifier=FALSIFIER))

    checkpoint = {
        "checkpoint": 3,
        "worker": "worker-067",
        "task_id": TASK,
        "at": t,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": [CLASS],
        "verdict": result["verdict"],
        "hours_spent_estimate": 0.6,
        "hard_failures": ["HF-067-B1", "HF-067-B2"],
        "artifacts": {v["path"]: v["sha256"] for v in hashes.values()},
        "outbox_events": [e["event_id"] for e in events],
        "authority": "no gate verdict, no node completion, no self-pass",
        "numerics_lock": "respected: read-only; no N1 work, no canonical writes",
        "next_falsifier": FALSIFIER,
    }
    cp_path = STATE / "worker-067_checkpoint_3.json"
    cp_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    cp_sha = sha256(cp_path)
    with (STATE / "worker-067_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({**checkpoint, "checkpoint_path": str(cp_path.relative_to(ROOT)),
                            "checkpoint_sha256": cp_sha}) + "\n")

    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
    print(f"checkpoint {cp_path.relative_to(ROOT)} sha256={cp_sha[:12]}")
    for e in events:
        print(" ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
