#!/usr/bin/env python3
"""Append the W014-GNUM-GUARD-VERIFY-01 events to comms/outbox/worker-014.jsonl.

Deterministic content from on-disk hashes; created_at is taken from the clock.
Writes only the outbox and a local copy under artifacts/worker-14/guard_verify/.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-014.jsonl"
LOCAL = ROOT / "artifacts" / "worker-14" / "guard_verify" / "events_emitted.jsonl"
BASE = ROOT / "artifacts" / "worker-14" / "guard_verify"
CST = timezone(timedelta(hours=8))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


now = datetime.now(CST).replace(microsecond=0).isoformat()
report = sha256(BASE / "report.json")
instrument = sha256(BASE / "verify_guard_census.py")
prereg = sha256(BASE / "PRE_REGISTRATION.md")
readme = sha256(BASE / "README.md")
emitter = sha256(Path(__file__))
checkpoint = sha256(ROOT / "runtime" / "state" / "w014_guard_verify_checkpoint.json")

W64_REPORT = "artifacts/worker-064/gnum_guard/report.json#e3ebf9e502491f65"
W64_SNAP = "artifacts/worker-064/gnum_guard/raw/events_snapshot.jsonl#b476b9e5e54fbcbd"
PIN_GATES = "numerics/gates.py#fcd1d70991b6eade"
PIN_PROTO = "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313"

FALSIFIER = (
    "Re-run artifacts/worker-14/guard_verify/verify_guard_census.py at the pinned inputs "
    "(numerics/gates.py#fcd1d70991b6eade, numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313, "
    "artifacts/worker-064/gnum_guard/report.json#e3ebf9e502491f65, "
    "artifacts/worker-064/gnum_guard/raw/events_snapshot.jsonl#b476b9e5e54fbcbd). Any check status "
    "that flips, any arm that stops matching, a declared hash that no longer matches disk, a "
    "shadow/guard disagreement, a non-deterministic payload, a canonical write, or a lock-state "
    "change falsifies the corresponding verdict. A later write to worker-064's reviewed revision or "
    "to either canonical pin voids this verification for the new bytes."
)

NOT_CLAIMED = [
    "not a G-NUM gate verdict and no gate self-pass (Astra / lead-audit authority)",
    "not an N0 node completion or status transition",
    "not adoption of the candidate rule; proposal for the owner only",
    "no canonical write; numerics_lock stays LOCKED and N1 queued",
    "no physics / self-gravity / WCC / SCC claim",
]

events = [
    {
        "actor": "worker-014", "event_type": "artifact", "event_id": "w014-gvf-20260912T011430-artifact-report",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01",
        "artifact_type": "independent_guard_census_verification_report",
        "path": "artifacts/worker-14/guard_verify/report.json", "sha256": report,
        "validation_status": "unverified",
        "verdict": "W064_CENSUS_AND_RULE_INDEPENDENTLY_REPRODUCED",
        "evidence_refs": [W64_REPORT, W64_SNAP, PIN_GATES, PIN_PROTO,
                          "artifacts/worker-14/guard_verify/report.json#" + report[:16],
                          "runtime/state/w014_guard_verify_checkpoint.json#" + checkpoint[:16]],
        "supporting_artifacts": {
            "artifacts/worker-14/guard_verify/verify_guard_census.py": instrument,
            "artifacts/worker-14/guard_verify/PRE_REGISTRATION.md": prereg,
            "artifacts/worker-14/guard_verify/README.md": readme,
            "artifacts/worker-14/guard_verify/emit_events.py": emitter,
            "runtime/state/w014_guard_verify_checkpoint.json": checkpoint,
        },
        "does_not_claim": NOT_CLAIMED,
        "falsifier": FALSIFIER,
    },
    {
        "actor": "worker-014", "event_type": "artifact", "event_id": "w014-gvf-20260912T011430-artifact-instrument",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01", "artifact_type": "audit-instrument/v1",
        "controls_passed": True, "controls_total": 13,
        "path": "artifacts/worker-14/guard_verify/verify_guard_census.py", "sha256": instrument,
        "validation_status": "unverified",
        "summary": "Independent re-implementation of the guard semantics and the R1-R3 candidate rule; does not import "
                   "worker-064's harness. 12 checks, 6 author controls reproduced, 7 adversarial controls "
                   "(4 fail-closed + 3 specification-gap demonstrations), shadow/guard equivalence control, "
                   "deterministic rebuild. Re-runnable: python3 verify_guard_census.py --out report.json.",
        "evidence_refs": ["artifacts/worker-14/guard_verify/report.json#" + report[:16], W64_REPORT, W64_SNAP],
        "does_not_claim": NOT_CLAIMED, "falsifier": FALSIFIER,
    },
    {
        "actor": "worker-014", "event_type": "artifact", "event_id": "w014-gvf-20260912T011430-artifact-prereg",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01", "artifact_type": "pre_registration",
        "path": "artifacts/worker-14/guard_verify/PRE_REGISTRATION.md", "sha256": prereg,
        "validation_status": "unverified",
        "summary": "Predictions V1-V8 declared before the instrument was implemented or run; every prediction held. "
                   "No prediction was re-labelled.",
        "evidence_refs": ["artifacts/worker-14/guard_verify/report.json#" + report[:16]],
        "does_not_claim": NOT_CLAIMED, "falsifier": FALSIFIER,
    },
    {
        "actor": "worker-014", "event_type": "artifact", "event_id": "w014-gvf-20260912T011430-artifact-emitter",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01", "artifact_type": "emitter_script",
        "path": "artifacts/worker-14/guard_verify/emit_events.py", "sha256": emitter,
        "validation_status": "unverified",
        "summary": "Deterministic outbox emitter for this task; hashes all deliverables from disk at emission time.",
        "evidence_refs": ["artifacts/worker-14/guard_verify/report.json#" + report[:16]],
        "does_not_claim": NOT_CLAIMED, "falsifier": FALSIFIER,
    },
    {
        "actor": "worker-014", "event_type": "review", "event_id": "w014-gvf-20260912T011430-review",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01",
        "target_id": W64_REPORT, "reviewer": "worker-014 (independent of the author worker-064)",
        "verdict": "accept", "score": 4.0, "hard_failures": [],
        "findings": [
            "V1: all 7 declared gnum_guard artifact hashes and both pinned copies match disk; the live canonical gates.py/protocol equal the two pins.",
            "V2: the frozen-snapshot census reproduces exactly (5 accepts / 5 dissents / 3 advisory, contest=true); my independent re-implementation equals both the live numerics.gates._protocol_review and worker-064's guard_verdict, verified on their 11,604-event frozen snapshot.",
            "V3: findings F-GUARD-1..5 all confirmed by direct measurement: r4 adjudication accept advisory (hash only in the cited artifact, not the event); 4 of 10 counted verdicts are N0-artifact reviews; prose-only withdrawal of w081-20260912T002140-c8-review with no structured withdrawal field anywhere; worker-081 counted on both sides at one hash; contest is a blocking reason but not the gate decider (N1_BLOCKED).",
            "V4: all six published arms reproduce exactly under my independent implementation, including the three R1/R2/R3 arms and the two inert-R2 arms.",
            "V5: the author's six negative controls C1-C6 reproduce.",
            "V6 (added value): three specification gaps in R3, each demonstrated by a planted control - X1 a reviewer can discharge their own dissent (R2 is author-scoped, R3 is not); X2 an empty-evidence carrier discharges listed ids (the list is trusted, not evidence-bound); X7 a carrier that does not target the protocol at all, and reuses the generic field name supersedes_event_ids already used by worker-029 task chains, discharges listed dissents. X3/X4/X5/X6 fail closed.",
            "V7: the minimal one-field repair (reviewed_sha256 on the r4 event) makes it bind but leaves contest=true; event-layer repair is necessary, not sufficient.",
            "Advisory (non-load-bearing): this verification assesses worker-064's artifact, not worker-064's reviewer independence or the truth of the adjudications the discharge list would carry; the candidate rule remains proposal-only.",
        ],
        "evidence_refs": ["artifacts/worker-14/guard_verify/report.json#" + report[:16], W64_REPORT],
        "does_not_claim": NOT_CLAIMED, "falsifier": FALSIFIER,
    },
    {
        "actor": "worker-014", "event_type": "claim", "event_id": "w014-gvf-20260912T011430-claim",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01", "conclusion_type": "numerical_evidence",
        "statement": (
            "Independent non-author verification at numerics/gates.py#fcd1d70991b6eade and "
            "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313 on worker-064's frozen revision "
            "(report e3ebf9e502491f65, snapshot b476b9e5e54fbcbd, 11,604 events): the guard census is "
            "5 accepts / 5 dissents / 3 advisory with contest=true, reproduced by an independent "
            "re-implementation that agrees with both the live guard and the author; F-GUARD-1..5 are "
            "confirmed; all six published rule arms and six author controls reproduce; the minimal "
            "one-field r4 hash repair binds the accept but leaves contest=true; and the discharge arm "
            "R3 has three specification gaps (self-discharge permitted, discharge list not "
            "evidence-bound, generic supersedes_event_ids field collision with unrelated worker-029 "
            "events) demonstrated by planted controls, while X3/X4/X5/X6 fail closed."
        ),
        "assumptions": [
            "worker-064's frozen snapshot is the binding input set for the census (the live stream has since grown)",
            "the reviewed revision is the bytes at the declared hashes; later writes void this verification for the new bytes",
            "the candidate rule text in candidate_rules.json is the object of the arm/control tests; no adoption is claimed",
        ],
        "evidence_refs": ["artifacts/worker-14/guard_verify/report.json#" + report[:16], W64_REPORT, W64_SNAP,
                          PIN_GATES, PIN_PROTO],
        "does_not_claim": NOT_CLAIMED, "falsifier": FALSIFIER,
    },
    {
        "actor": "worker-014", "event_type": "status", "event_id": "w014-gvf-20260912T011430-status",
        "created_at": now, "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "task_id": "W014-GNUM-GUARD-VERIFY-01", "status": "active", "hours": 0.6,
        "summary": (
            "CHECKPOINT / worker-014. One bounded class-bound task taken (no inbox card for this slot): "
            "W014-GNUM-GUARD-VERIFY-01, independent non-author verification of worker-064's fresh "
            "W064-GNUM-GUARD-CENSUS-01 (their guard-census task was claimed at 01:08 while this slot was in "
            "recon, so this instance verified instead of duplicating). Verdict "
            "W064_CENSUS_AND_RULE_INDEPENDENTLY_REPRODUCED: 12/12 checks, all six arms and six author controls "
            "reproduce, and three R3 specification gaps are demonstrated with new controls (self-discharge; "
            "list trusted without evidence; generic field-name collision). The candidate rule is not adopted; "
            "the owner disposition on lnum-blocker-e9e939acc0856fa77127 / astra-life06-b4 gains an independent "
            "verification. Worker-level only: no gate verdict, no node completion, no canonical write; "
            "numerics_lock LOCKED, N1_BLOCKED, numerics/spherical_solver absent. Checkpoint: "
            "runtime/state/w014_guard_verify_checkpoint.json."
        ),
        "evidence_refs": ["runtime/state/w014_guard_verify_checkpoint.json#" + checkpoint[:16],
                          "artifacts/worker-14/guard_verify/report.json#" + report[:16],
                          W64_REPORT, PIN_GATES, PIN_PROTO],
        "next_falsifier": FALSIFIER,
        "does_not_claim": NOT_CLAIMED,
    },
]

for e in events:
    assert e["event_id"] and e["event_type"] and e["created_at"] and e["actor"], e
    with OUTBOX.open("a") as f:
        f.write(json.dumps(e, sort_keys=True) + "\n")
LOCAL.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
print(json.dumps({"emitted": len(events), "outbox": str(OUTBOX), "local": str(LOCAL),
                  "event_ids": [e["event_id"] for e in events]}, indent=1))
