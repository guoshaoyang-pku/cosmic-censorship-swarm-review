#!/usr/bin/env python3
"""Emit W064-GNUM-GUARD-CHANNELS-02 outbox events + checkpoint (schema-validated).

Appends to comms/outbox/worker-064.jsonl and writes the checkpoint to
runtime/state/.  Does not run ingest (controller-only) and does not touch any canonical file.
Unknown/rejected schema is caught before any write.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-064.jsonl"
STATE = ROOT / "runtime" / "state"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
INSTANCE = "worker-064-20260912T011002-968807"
TASK = "W064-GNUM-GUARD-CHANNELS-02"
CLASS = "AF-WCC-SCALAR-SPH"
NODE = "N0"
GATE = "G-NUM"
GATES_SHA = "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"
PROTO_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"

ART = [
    ("prereg", "artifacts/worker-064/guard_channels/prereg.json", "preregistration"),
    ("harness", "artifacts/worker-064/guard_channels/w064_guard_channels.py", "instrument"),
    ("report", "artifacts/worker-064/guard_channels/report.json", "guard_channel_report"),
    ("channels", "artifacts/worker-064/guard_channels/channels.jsonl", "channel_arm_rows"),
    ("controls", "artifacts/worker-064/guard_channels/controls.jsonl", "negative_control_rows"),
    ("readme", "artifacts/worker-064/guard_channels/README.md", "summary"),
    ("snapshot", "artifacts/worker-064/guard_channels/raw/events_snapshot.jsonl", "event_snapshot"),
    ("controlv1", "artifacts/worker-064/guard_channels/raw/control_v1_failures.json", "rejected_control_round"),
    ("pinsbefore", "artifacts/worker-064/guard_channels/raw/pins_before.json", "pins"),
    ("pinsafter", "artifacts/worker-064/guard_channels/raw/pins_after.json", "pins"),
    ("pingates", "artifacts/worker-064/guard_channels/pinned/gates_fcd1d70991b6.py", "pinned_instrument"),
    ("pinproto", "artifacts/worker-064/guard_channels/pinned/CONVERGENCE_PROTOCOL_1e6cdf04d7a2.md", "pinned_protocol"),
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    hashes = {}
    for _, rel, _ in ART:
        p = ROOT / rel
        if not p.exists():
            print(f"missing artifact: {rel}")
            return 2
        hashes[rel] = sha(p)
    ref = lambda rel: f"{rel}#{hashes[rel][:12]}"

    events = []
    events.append({
        "event_id": "w064-guard-channels-02-status-start",
        "event_type": "status", "created_at": NOW, "actor": "worker-064",
        "node_id": NODE, "status": "active", "hours": 0.1, "gate": GATE,
        "class_id": CLASS, "class_ids": [CLASS],
        "summary": ("Taking ONE bounded class-bound task (no inbox card existed for worker-064): "
                    "W064-GNUM-GUARD-CHANNELS-02, channel-closure test of numerics/gates.py::"
                    "_protocol_review at protocol 1e6cdf04d7a2 / gates.py fcd1d70991b6. Question: "
                    "can any protocol-conformant stream event discharge a counted dissent, or is a "
                    "guard rule change required? Read-only; no canonical write."),
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/prereg.json")],
        "next_falsifier": ("Any single channel arm yielding contest=false under the live predicate, "
                           "any negative control clearing contest under the shadow rule, or a live-pin "
                           "move falsifies the corresponding expectation."),
    })
    for tag, rel, atype in ART:
        events.append({
            "event_id": f"w064-guard-channels-02-artifact-{tag}",
            "event_type": "artifact", "created_at": NOW, "actor": "worker-064",
            "node_id": NODE, "gate": GATE, "class_id": CLASS, "class_ids": [CLASS],
            "artifact_type": atype, "path": rel, "sha256": hashes[rel],
            "validation_status": "unverified",
            "evidence_refs": [ref(rel)],
        })
    events.append({
        "event_id": "w064-guard-channels-02-claim-c1-channel-closure",
        "event_type": "claim", "created_at": NOW, "actor": "worker-064",
        "node_id": NODE, "gate": GATE, "class_id": CLASS, "class_ids": [CLASS],
        "conclusion_type": "formal_model",
        "statement": ("At the live bytes (gates.py fcd1d70991b6, protocol 1e6cdf04d7a2) no "
                      "protocol-conformant stream event clears the C8 protocol-review contest: all "
                      "nine tested channels leave contest=true while the baseline is accepts=5 / "
                      "dissents=5 / advisory=3. A review that explicitly lists the two F1/F1' "
                      "dissents as discharged (A5) and a hash-rebound accept (A4, accepts 5->6) both "
                      "still leave contest=true, because _protocol_review reads only review events, "
                      "ignores discharges/withdraws fields and disposition prose, and never lets a "
                      "later accept rescind an earlier revise. Disposition-by-event therefore cannot "
                      "satisfy audit-l06-b4."),
        "assumptions": ["the channel events are protocol-shaped simulations, not emitted events",
                        "the frozen event snapshot is the review basis",
                        "the pinned gate module bytes are the instrument of record"],
        "falsifier": ("Any one channel arm yielding contest=false under the live predicate falsifies "
                      "this claim."),
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/report.json"),
                          ref("artifacts/worker-064/guard_channels/channels.jsonl"),
                          f"numerics/gates.py#{GATES_SHA}"],
        "not_claimed": ["no gate verdict", "no node completion", "no adoption", "no canonical write"],
    })
    events.append({
        "event_id": "w064-guard-channels-02-claim-c2-rule-safety",
        "event_type": "claim", "created_at": NOW, "actor": "worker-064",
        "node_id": NODE, "gate": GATE, "class_id": CLASS, "class_ids": [CLASS],
        "conclusion_type": "formal_model",
        "statement": ("A shadow guard rule (R1 restrict protocol review state to the protocol "
                      "targets + R2 author-only structured withdrawal + R3 explicit fail-closed "
                      "discharge list on a later same-hash accept) clears the guard on the frozen "
                      "snapshot (accepts=5, dissents=0, contest=false) while R1 alone and R1+R2 "
                      "without a structured field do not. Six negative controls all fail closed: "
                      "unknown discharge id, fully stale-hash carrier, pre-dated carrier, uncited "
                      "carrier, third-party withdrawal, fresh unlisted dissent. A hooks-off "
                      "equivalence control reproduces the pinned live predicate exactly. NOT "
                      "ADOPTED: this is a proposal for the owner; numerics/gates.py is unchanged."),
        "assumptions": ["the shadow rule is an extracted reimplementation, not a patch",
                        "a discharge carrier must itself bind the protocol hash and postdate the dissent",
                        "a withdrawal is authoritative only from the review's own author"],
        "falsifier": ("Any negative control clearing contest, or any discharged dissent lacking an "
                      "explicit same-hash carrier, falsifies this rule's safety."),
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/report.json"),
                          ref("artifacts/worker-064/guard_channels/controls.jsonl"),
                          ref("artifacts/worker-064/guard_channels/w064_guard_channels.py")],
        "not_claimed": ["not adopted", "not a gate verdict", "no canonical modification"],
    })
    events.append({
        "event_id": "w064-guard-channels-02-review-guard",
        "event_type": "review", "created_at": NOW, "actor": "worker-064",
        "node_id": NODE, "gate": GATE, "class_id": CLASS, "class_ids": [CLASS],
        "target_id": f"numerics/gates.py#{GATES_SHA}",
        "reviewer": "worker-064", "verdict": "revise", "score": 3.5, "hard_failures": [],
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": False,
        "findings": [
            ("The guard's dissent accounting is not resolvable by any stream channel (C1); the "
             "blocker audit-l06-b4 needs an owner rule/code disposition, not another event."),
            ("The failing instrument as written also counts 3 N0-node reviews and the self-withdrawn "
             "accept; the candidate R1+R2+R3 rule addresses all three with 6/6 controls holding."),
        ],
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/report.json"),
                          f"numerics/gates.py#{GATES_SHA}"],
    })
    events.append({
        "event_id": "w064-guard-channels-02-blocker-owner-ruling",
        "event_type": "blocker", "created_at": NOW, "actor": "worker-064",
        "node_id": NODE, "gate": GATE, "class_id": CLASS, "class_ids": [CLASS],
        "description": ("C8 protocol-review contest is not dischargeable through the event protocol "
                        "at gates.py fcd1d70991b6: nine protocol-conformant channels tested, none "
                        "clears contest; a review that names the two F1/F1' dissents as discharged "
                        "is ignored by the instrument. The open remedy named by audit-l06-b4 must be "
                        "an owner decision on the guard rule/code (R1+R2+R3 verified safe on six "
                        "controls) or an explicit recorded disposition outside the guard."),
        "needed_to_unblock": ("One owner (controller + audit) decision: adopt/decline the R1+R2+R3 "
                              "supersession rule or a byte-equivalent patch to numerics/gates.py, "
                              "with an independent review at the new hash; no worker may self-adopt."),
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/report.json"),
                          ref("artifacts/worker-064/guard_channels/controls.jsonl"),
                          "reviews/G-NUM-protocol-r4-adjudication.json#b836902fa4ae"],
    })
    events.append({
        "event_id": "w064-guard-channels-02-status-complete",
        "event_type": "status", "created_at": NOW, "actor": "worker-064",
        "node_id": NODE, "status": "active", "hours": 0.4, "gate": GATE,
        "class_id": CLASS, "class_ids": [CLASS],
        "summary": ("W064-GNUM-GUARD-CHANNELS-02 complete at worker level (completion claim only: "
                    "workers cannot set done/passed or a gate verdict). Verdict CHANNEL_CLOSED: "
                    "no stream event clears contest (9/9 arms); R1+R2+R3 shadow rule clears with "
                    "6/6 controls fail-closed; hooks-off equivalence exact; live pins unchanged. "
                    "Artifacts hashed; checkpoint written; no canonical write."),
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/report.json"),
                          ref("artifacts/worker-064/guard_channels/README.md")],
        "next_falsifier": ("After the owner adopts a supersession rule / the structured discharge "
                           "lands and gates.py moves off fcd1d70991b6, re-run w064_guard_channels.py "
                           "at the new hash; expect accepts>=6 / dissents=0 with controls holding."),
    })

    for e in events:
        try:
            validate_event(dict(e))
        except SchemaError as exc:
            print(f"SCHEMA REJECT {e['event_id']}: {exc}")
            return 3

    data = OUTBOX.read_bytes() if OUTBOX.exists() else b""
    if data and not data.endswith(b"\n"):
        data += b"\n"
    with open(OUTBOX, "wb") as f:
        f.write(data)
        for e in events:
            f.write((json.dumps(e, sort_keys=True) + "\n").encode())

    emitted = HERE / "events_emitted.jsonl"
    with open(emitted, "w") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ckpt = {
        "schema_version": "0.1",
        "checkpoint_id": "w064-guard-channels-ckpt-" + datetime.now(CST).strftime("%Y-%m-%dT%H%M%S%z"),
        "task_id": TASK, "actor": "worker-064", "instance_id": INSTANCE, "created_at": NOW,
        "node_id": NODE, "gate": GATE, "class_ids": [CLASS],
        "status": "worker_task_complete_no_node_transition",
        "verdict": "CHANNEL_CLOSED__NO_STREAM_EVENT_CLEARS_CONTEST__ONLY_GUARD_RULE_R1R2R3_CLEARS_WITH_6_OF_6_CONTROLS",
        "pins": {"numerics/gates.py": GATES_SHA, "numerics/CONVERGENCE_PROTOCOL.md": PROTO_SHA,
                 "events_snapshot": hashes["artifacts/worker-064/guard_channels/raw/events_snapshot.jsonl"]},
        "measured_results": {
            "baseline": {"accepts": 5, "dissents": 5, "advisory": 3, "contest": True},
            "channel_arms_clearing": [], "channel_arms_tested": 9,
            "shadow_rule_r1r2r3_contest": False, "negative_controls_passed": "6/6",
            "hooks_off_equivalence": True, "pins_stable": True,
        },
        "artifacts": hashes,
        "evidence_refs": [ref("artifacts/worker-064/guard_channels/report.json"),
                          ref("artifacts/worker-064/guard_channels/channels.jsonl"),
                          ref("artifacts/worker-064/guard_channels/controls.jsonl")],
        "falsifier": ("Any single channel arm yielding contest=false under the live predicate, any "
                      "negative control clearing contest under the shadow rule, or a live-pin move "
                      "falsifies the corresponding result."),
        "next_falsifier": ("Re-run w064_guard_channels.py after the owner adopts a supersession rule "
                           "or gates.py moves; expect accepts>=6 / dissents=0, controls fail-closed."),
        "not_claimed": ["no gate verdict", "no node completion", "no adoption of R1-R3",
                        "no canonical modification", "no physics claim"],
        "outbox": "comms/outbox/worker-064.jsonl",
        "outbox_event_ids": [e["event_id"] for e in events],
    }
    ck = STATE / "w064_guard_channels_checkpoint.json"
    ck.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
    with open(STATE / "w064_checkpoints.jsonl", "a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    sums = ROOT / "artifacts/worker-064/guard_channels/SHA256SUMS"
    lines = []
    for p in sorted((HERE).rglob("*")):
        if p.is_file() and p != sums:
            lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
    sums.write_text("\n".join(lines) + "\n")
    print(json.dumps({"emitted": len(events), "checkpoint": str(ck),
                      "outbox": str(OUTBOX), "artifacts": len(hashes)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
