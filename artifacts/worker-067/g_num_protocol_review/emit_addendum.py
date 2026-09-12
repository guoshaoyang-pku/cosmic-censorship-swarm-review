#!/usr/bin/env python3
"""Addendum to worker-067's G-NUM protocol review: record the concurrent A1 accept at the
same hash, correct the parent review's statement about the A1 file, keep the verdict.
Appends events to comms/outbox/worker-067.jsonl and writes checkpoint 2."""
import hashlib
import json
import os
import sys
import time

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = os.path.join(ROOT, "artifacts/worker-067/g_num_protocol_review")
os.chdir(ROOT)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
stamp = time.strftime("%Y%m%dT%H%M%S")
parent_path = "artifacts/worker-067/g_num_protocol_review/review.json"
parent_hash = sha(parent_path)
a1_path = "reviews/G-NUM-protocol-review.json"
a1_hash = sha(a1_path)
adv_path = "reviews/G-NUM-protocol-review-rev1-advisory.json"
adv_hash = sha(adv_path)
proto_hash = sha("numerics/CONVERGENCE_PROTOCOL.md")
prop_hash = sha("numerics/tests/n0_gate_proposal.json")

add = {
    "schema": "worker-review/g-num-protocol-addendum/v1",
    "event_id": "w067-review-addendum-concurrent-a1-%s" % stamp,
    "event_type": "review_addendum",
    "created_at": now,
    "actor": "worker-067",
    "node_id": "N0",
    "gate": "G-NUM",
    "class_id": "AF-WCC-SCALAR-SPH",
    "parent_review": {
        "path": parent_path,
        "sha256": parent_hash,
        "verdict": "revise",
        "protocol_sha256": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    },
    "concurrent_verdict_observed": {
        "path": a1_path,
        "sha256": a1_hash,
        "actor": "astra-lead-audit",
        "created_at": "2026-09-12T00:20:00+08:00",
        "verdict": "accept",
        "score": 4.5,
        "binds_protocol_sha256": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
        "addresses_section_3_4": False,
        "note": (
            "The concurrent accept independently recomputes the same 4-rung fits, R5 "
            "agreement, controls and lock state as this review and reaches the same positive "
            "evidence verdicts. It does not evaluate section 3.4's fixed-dt clause against the "
            "constant-CFL order studies, so finding F1 is not rebutted by it."
        ),
    },
    "correction_to_parent_review": {
        "wrong_statement": (
            "review.json reviewer_independence says reviews/G-NUM-protocol-review.json "
            "'binds 01b2072434cd and is left untouched'."
        ),
        "measured_state": (
            "At parent emit time the A1 file had already been replaced (00:19-00:20) by an "
            "accept at 1e6cdf04 (%s); the superseded revise review is preserved at %s#%s. "
            "This reviewer wrote neither file and edited no canonical path."
            % (a1_hash[:12], adv_path, adv_hash[:12])
        ),
        "disposition": "parent verdict unaffected; parent artifact remains byte-identical and hash-bound",
    },
    "divergence": {
        "positions": [
            "astra-lead-audit (accept, 4.5): protocol rev 3 ready, C1-C3 closed; section 3.4 not examined.",
            "worker-067 (revise, 4.0): same positive evidence verdicts, but section 3.4 forbids the "
            "constant-CFL runs on which the certified spatial order claim rests (F1).",
        ],
        "hash_observations": [
            "both verdicts bind the same current protocol hash %s; the protocol was byte-stable "
            "across both review windows" % proto_hash,
            "the concurrent accept cites numerics/tests/n0_gate_proposal.json#22d984781cee; the "
            "on-disk proposal measured %s at %s (revision updated 00:15). The protocol binding is "
            "unaffected; recorded for evidence hygiene." % (prop_hash[:12], now),
        ],
        "resolution_path": (
            "F1 is a three-line text fix in section 3.4 (scope the fixed-dt sentence to the "
            "MMS/reference study; state the constant-CFL temporal-control rule). Either the "
            "controller treats the A1 accept as satisfying C8 and records F1 as a non-blocking "
            "dissent, or lead-numerics publishes rev 4 and both current verdicts become void by "
            "hash, requiring one fresh review."
        ),
        "reviewer_note": (
            "No measured number is disputed and no hard failure is alleged against the author. "
            "The dissent is solely that the normative text, as written, does not authorise the "
            "evidence it certifies."
        ),
    },
    "verdict_unchanged": {
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": [],
        "reason": "F1 remains unrebutted: section 3.4 bans dt-proportional-to-h runs as spatial "
        "evidence while the certified spatial order claim uses them.",
    },
    "falsifier": (
        "A 4-rung fixed-dt=1e-4 spatial order study for schemes A/B at the pinned protocol hash, "
        "or a protocol revision whose section 3.4 states the constant-CFL temporal-control rule, "
        "withdraws F1 (in the second case this addendum is void by hash)."
    ),
    "not_claimed": [
        "no gate verdict or node completion; this addendum is reviewer evidence only",
        "no accusation against astra-lead-audit; the two reviews share the same measured evidence",
        "no edit to any canonical artifact or to either review file",
    ],
}
add_path = "artifacts/worker-067/g_num_protocol_review/review_addendum_concurrent_a1.json"
with open(add_path, "w") as f:
    json.dump(add, f, indent=1, sort_keys=True)
add_hash = sha(add_path)

events = [
    {
        "event_id": "w067-art-%s-review-addendum" % stamp,
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-067",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "artifact_type": "review_addendum",
        "path": add_path,
        "sha256": add_hash,
        "validation_status": "unverified",
        "evidence_refs": [a1_path + "#" + a1_hash[:12], parent_path + "#" + parent_hash[:12]],
    },
    {
        "event_id": "w067-status-%s-addendum-divergence" % stamp,
        "event_type": "status",
        "created_at": now,
        "actor": "worker-067",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "status": "active",
        "hours": 0.7,
        "summary": (
            "Correction + divergence recorded. astra-lead-audit replaced reviews/G-NUM-protocol-review.json "
            "with an accept at the same protocol hash (%s) while this review was running; the parent "
            "review's statement that the A1 file still bound 01b2072434cd is corrected in the addendum. "
            "worker-067 keeps verdict revise: F1 (section 3.4 bans dt-proportional-to-h runs while the "
            "certified spatial order uses them) is not addressed by the concurrent accept. No measured "
            "number is disputed."
            % proto_hash[:12]
        ),
        "evidence_refs": [add_path + "#" + add_hash[:12], a1_path + "#" + a1_hash[:12]],
        "next_falsifier": add["falsifier"],
    },
]
with open("comms/outbox/worker-067.jsonl", "a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

checkpoint = {
    "worker": "worker-067",
    "checkpoint": 2,
    "at": now,
    "task_id": "G-NUM-C8-independent-protocol-review",
    "node_id": "N0",
    "gate": "G-NUM",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "verdict": "revise",
    "score": 4.0,
    "hard_failures": [],
    "artifacts": {
        parent_path: parent_hash,
        add_path: add_hash,
        "artifacts/worker-067/g_num_protocol_review/verification_log.json": sha(
            "artifacts/worker-067/g_num_protocol_review/verification_log.json"
        ),
    },
    "concurrent_a1_accept": {"path": a1_path, "sha256": a1_hash, "verdict": "accept", "score": 4.5},
    "divergence_recorded": True,
    "outbox_events": [e["event_id"] for e in events],
    "hours_spent_estimate": 0.7,
    "numerics_lock": "respected: read-only; no N1 work, no canonical writes",
    "authority": "no gate verdict, no node completion, no self-pass",
    "next_falsifier": add["falsifier"],
}
cp_path = "runtime/state/worker-067_checkpoint_2.json"
with open(cp_path, "w") as f:
    json.dump(checkpoint, f, indent=1, sort_keys=True)

sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

# validate the whole outbox file (parent + addendum events)
all_events = [json.loads(l) for l in open("comms/outbox/worker-067.jsonl")]
for e in all_events:
    validate_event(e)
print(json.dumps({
    "addendum": add_path, "addendum_sha256": add_hash,
    "parent_review_sha256": parent_hash,
    "a1_accept_sha256": a1_hash,
    "checkpoint": cp_path,
    "outbox_events_total": len(all_events),
    "events_schema_valid": True,
}, indent=1))
