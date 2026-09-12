#!/usr/bin/env python3
"""Emit W081-N0-C8-01 events to comms/outbox/worker-081.jsonl and checkpoint.

Idempotent: events already present in the outbox (by event_id) are skipped.
Every event is validated with research_map/schemas.validate_event before it is
written, so the controller's `comms.py ingest` cannot reject it on schema.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-081.jsonl"
STATE = ROOT / "runtime" / "state"
ART = ROOT / "artifacts" / "worker-081" / "n0_c8_protocol_review"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: Path) -> str:
    return f"{path.relative_to(ROOT)}#{sha256(path)[:16]}"


ev = json.loads((ART / "evidence_check.json").read_text())
review = json.loads((ART / "review.json").read_text())
artifacts = {p.name: sha256(p) for p in sorted(ART.iterdir()) if p.is_file()}
protocol_hash = review["artifact_sha256"]
checked = ev["checks"]

events: list[dict] = []


def add(e: dict):
    e.setdefault("created_at", NOW)
    e.setdefault("actor", "worker-081")
    e.setdefault("node_id", "N0")
    e.setdefault("gate", "G-NUM")
    e.setdefault("class_id", "AF-WCC-SCALAR-SPH")
    e.setdefault("class_ids", ["AF-WCC-SCALAR-SPH"])
    e.setdefault("task_id", "W081-N0-C8-01")
    events.append(e)


add({
    "event_id": f"w081-{STAMP}-task-claim",
    "event_type": "status",
    "status": "active",
    "hours": 0.1,
    "summary": "Taking one bounded class-bound task from the live queue: astra-life02-n0-c8-refresh "
               "(N0, G-NUM, AF-WCC-SCALAR-SPH). Independent C8 verdict on "
               "numerics/CONVERGENCE_PROTOCOL.md at the hash measured at review time, with a "
               "machine-checked evidence audit. Worker evidence only: no node completion, no gate verdict.",
    "evidence_refs": ["numerics/CONVERGENCE_PROTOCOL.md", "numerics/tests/n0_gate_proposal.json"],
    "next_falsifier": "Protocol hash moves during the review, or a binding cited reference fails to re-hash.",
})

for name, label in (("verify_protocol_evidence.py", "verification_script"),
                    ("evidence_check.json", "evidence"),
                    ("review.json", "review"),
                    ("README.md", "summary")):
    p = ART / name
    add({
        "event_id": f"w081-{STAMP}-artifact-{name}",
        "event_type": "artifact",
        "artifact_type": label,
        "path": str(p.relative_to(ROOT)),
        "sha256": artifacts[name],
        "validation_status": "unverified",
        "evidence_refs": [ref(p)],
        "note": "Measured by worker-081; validation_status stays unverified until a reviewer/controller "
                "binds it. Not a theorem and not physics evidence.",
    })

add({
    "event_id": f"w081-{STAMP}-c8-review",
    "event_type": "review",
    "target_id": "G-NUM-protocol",
    "reviewer": "worker-081",
    "reviewer_independence": review["reviewer_independence"],
    "verdict": review["verdict"],
    "score": review["score"],
    "hard_failures": review["hard_failures"],
    "findings": review["findings"],
    "reviewed_sha256": protocol_hash,
    "artifact_sha256": protocol_hash,
    "reviewed_artifacts": review["reviewed_artifacts"],
    "criteria_verdicts": review["criteria_verdicts"],
    "falsifier": review["falsifier"],
    "evidence_refs": [
        ref(ART / "review.json"), ref(ART / "evidence_check.json"),
        f"numerics/CONVERGENCE_PROTOCOL.md#{protocol_hash[:16]}",
    ],
    "authority_note": "Worker review event: proposes a C8 verdict for lead-audit/controller adjudication. "
                      "Does not set status=done, validation_status=passed, or any gate verdict.",
    "concurrent_audit_verdict": checked["H_concurrent_audit_verdict"],
})

add({
    "event_id": f"w081-{STAMP}-c8-claim",
    "event_type": "claim",
    "conclusion_type": "formal_model",
    "statement": f"For the N0 flat-space calibration sub-case of AF-WCC-SCALAR-SPH at protocol hash "
                 f"{protocol_hash[:16]}, all four C8 criteria are present in the protocol text with line anchors "
                 f"(R1/R2/R4 scheme-appropriate functional; R3 resolution-aware drift; R5/R5a order fit with "
                 f"uncertainty; section 5 negative controls); of 21 cited path#hash references 17 match on disk "
                 f"and 4 are non-binding (superseded F0 pin, superseded review record preserved byte-identically, "
                 f"mutable-registry snapshot pin, supersedes pointer) with 0 binding mismatches; the 4-rung studies "
                 f"independently re-fit to the reported orders and R5 uncertainties (max pairwise |dp| = "
                 f"{checked['D_four_rung_refit']['max_pairwise_order_diff']:.6f} <= 0.25); and the lock guard "
                 f"exits 0 with numerics_lock.state=locked and no numerics/spherical_solver.",
    "assumptions": [
        "The reviewed revision is the sha256 measured at review time; the verdict does not bind any other revision.",
        "A reference counts as binding unless it is a supersedes pointer, a snapshot pin of a registry regenerated "
        "each checkpoint, an acknowledged-superseded pin, or a review record whose predecessor is preserved.",
        "Independent re-fit uses log-log least squares over the rows recorded in n0_order_4rung.json; it re-derives "
        "the reported numbers rather than trusting them.",
        "The concurrent lead-audit accept (reviews/G-NUM-protocol-review.json) is recorded as context, not as a "
        "substitute for this worker's own measurements.",
    ],
    "falsifier": review["falsifier"],
    "evidence_refs": [
        ref(ART / "evidence_check.json"), ref(ART / "review.json"),
        f"numerics/CONVERGENCE_PROTOCOL.md#{protocol_hash[:16]}",
        "numerics/tests/n0_order_4rung.json#c88146a1375c50f0",
        "numerics/tests/selfgravity_lock_guard.py#7535ec84ac9ceb0b",
    ],
    "artifact_refs": [ref(ART / "review.json"), ref(ART / "evidence_check.json")],
    "fixed_run_registered": checked["F_proposal_numbers"]["checks"]["fixed_run_registered"],
    "registration_gap_present": not checked["F_proposal_numbers"]["checks"]["fixed_run_registered"],
})

add({
    "event_id": f"w081-{STAMP}-complete",
    "event_type": "status",
    "status": "active",
    "hours": 0.4,
    "summary": "W081-N0-C8-01 complete: artifacts exist and are hash-pinned; verdict accept at "
               f"{protocol_hash[:16]} with 0 hard failures and 5 documented non-blocking findings. "
               "This is a completion claim for the task, not a node transition and not a gate verdict; "
               "C4/C5 registration (6542db93, 1e6cdf04) remains controller-owned.",
    "evidence_refs": [ref(ART / "review.json"), ref(ART / "README.md"),
                      f"numerics/CONVERGENCE_PROTOCOL.md#{protocol_hash[:16]}"],
    "next_falsifier": "Re-run artifacts/worker-081/n0_c8_protocol_review/verify_protocol_evidence.py: any binding "
                      "hash mismatch, a non-monotone/out-of-band 4-rung study, or a lock-guard failure falsifies "
                      "the accept; a protocol hash change voids it.",
})

# ---------------------------------------------------------------- validate + write
for e in events:
    validate_event(e)

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                pass

new = [e for e in events if e["event_id"] not in existing]
OUTBOX.parent.mkdir(parents=True, exist_ok=True)
with open(OUTBOX, "a", encoding="utf-8") as f:
    for e in new:
        f.write(json.dumps(e, sort_keys=True) + "\n")

# ---------------------------------------------------------------- checkpoint
checkpoint = {
    "checkpoint": 1,
    "at": NOW,
    "worker": "worker-081",
    "hours_spent_estimate": 0.4,
    "assignment": "astra-life02-n0-c8-refresh (Astra, 2026-09-12T00:15+08:00) - independent C8 protocol "
                  "review at the hash measured at review time",
    "node_id": "N0",
    "gate_routing": {
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "worker_may_set_gate_verdict": False,
        "effect": "independent accept evidence for criterion C8; registration (proposal C5) stays controller-owned",
    },
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "status": {
        "delivered": True,
        "validation_status": "unverified",
        "verdict": review["verdict"],
        "score": review["score"],
        "hard_failures": review["hard_failures"],
        "reviewed_sha256": protocol_hash,
        "protocol_hash_stable": checked["A_moving_target"]["stable"],
        "hash_refs": {k: checked["B_hash_refs"][k] for k in ("total", "match", "mismatch", "binding_mismatch")},
        "criteria_verdicts": review["criteria_verdicts"],
        "four_rung_refit_ok": checked["D_four_rung_refit"]["all_studies_ok"],
        "max_pairwise_order_diff": checked["D_four_rung_refit"]["max_pairwise_order_diff"],
        "lock_ok": checked["E_lock"]["guard_passed"] and checked["E_lock"]["numerics_lock_ok"],
        "non_blocking_findings": [f["id"] for f in review["findings"]],
        "no_completion_claim": "worker cannot set done/passed/gate verdict; no theorem and no physics claim",
    },
    "artifacts": {f"artifacts/worker-081/n0_c8_protocol_review/{k}": {"sha256": v} for k, v in artifacts.items()},
    "outbox": {"path": "comms/outbox/worker-081.jsonl", "event_ids": [e["event_id"] for e in events]},
    "falsifier": review["falsifier"],
    "next_falsifier": "independent re-run of verify_protocol_evidence.py at the same protocol hash; any binding "
                      "reference mismatch, 4-rung failure, or lock violation converts this accept to revise.",
}
STATE.mkdir(parents=True, exist_ok=True)
(STATE / "w081_checkpoint_1.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with open(STATE / "w081_checkpoints.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

print(json.dumps({
    "outbox": str(OUTBOX.relative_to(ROOT)),
    "events_written": len(new),
    "events_total_after": len(existing) + len(new),
    "artifact_hashes": artifacts,
    "checkpoint": str((STATE / "w081_checkpoint_1.json").relative_to(ROOT)),
    "verdict": review["verdict"],
    "reviewed_sha256": protocol_hash,
}, indent=1))
