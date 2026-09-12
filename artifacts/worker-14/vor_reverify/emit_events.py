#!/usr/bin/env python3
"""Emit the W014-GNUM-VOR-REVERIFY-01 events to comms/outbox/worker-014.jsonl.

Validates every event against research_map/schemas.validate_event before appending, so a schema
error fails here instead of landing in comms/rejected.jsonl. Read-only with respect to canonical
paths except the outbox append and the checkpoint file under the task directory.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TASK = ROOT / "artifacts/worker-14/vor_reverify"
OUTBOX = ROOT / "comms/outbox/worker-014.jsonl"
CST = timezone(timedelta(hours=8))

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    report = TASK / "report.json"
    instrument = TASK / "verify_vor.py"
    prereg = TASK / "PRE_REGISTRATION.md"
    readme = TASK / "README.md"
    rep = json.loads(report.read_text())
    h = {p.name: {"path": str(p.relative_to(ROOT)), "sha256": sha(p), "bytes": p.stat().st_size}
         for p in (report, instrument, prereg, readme)}

    vor_rev = rep["pins_before"]["numerics/protocol/n0_gate_proposal_leadverify.json"]["measured_sha256"]
    prop_rev = rep["pins_before"]["numerics/tests/n0_gate_proposal.json"]["measured_sha256"]

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "task_id": "W014-GNUM-VOR-REVERIFY-01",
        "actor": "worker-014",
        "runtime_slot": "worker-014",
        "created_at": now,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "status": "delivered-worker-level",
        "verdict": rep["verdict"],
        "controls_ok": rep["controls_ok"],
        "instrument_valid": rep["instrument_valid"],
        "input_drift": rep["input_drift"],
        "verified_record_revision": f"numerics/protocol/n0_gate_proposal_leadverify.json#{vor_rev[:12]}",
        "verified_proposal_revision": f"numerics/tests/n0_gate_proposal.json#{prop_rev[:12]}",
        "artifacts": h,
        "open_items": [
            "BA-5b: proposal mutable_registry_snapshots prefix d69b62dc93e5336e5109 / measured_at 2026-09-12T01:06 is future-dated and matches no observed registry state; non-load-bearing annotation defect (owner: proposal author/controller)",
            "C8 protocol-review contest and astra-life05-gnum-protocol-adjudication remain outside this task",
        ],
        "next_falsifier": rep["falsifier"],
        "not_claimed": rep["not_claimed"],
    }
    ck = TASK / "checkpoint.json"
    ck.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    state_ck = ROOT / "runtime/state/worker-014_checkpoint_vorreverify.json"
    state_ck.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    h["checkpoint.json"] = {"path": str(ck.relative_to(ROOT)), "sha256": sha(ck), "bytes": ck.stat().st_size}
    h["runtime/state/worker-014_checkpoint_vorreverify.json"] = {
        "path": str(state_ck.relative_to(ROOT)),
        "sha256": sha(state_ck),
        "bytes": state_ck.stat().st_size,
    }

    base = f"w014-vor-{stamp}"
    events = [
        {
            "event_id": f"{base}-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "provenance_report",
            "path": h["report.json"]["path"],
            "sha256": h["report.json"]["sha256"],
            "validation_status": "unverified",
            "summary": (
                "W014-GNUM-VOR-REVERIFY-01: independent read-only verification of the re-issued N0 "
                f"verification of record {vor_rev[:12]} against proposal {prop_rev[:12]}. "
                "Verdict VOR_VERIFIED_BA1_CLOSED_BA5B_ANNOTATION_DEFECT_OPEN: 23/23 chain rows "
                "match, artifact event binds the same bytes, gate-evaluator reproduction and the "
                "4-rung refit reproduce exactly, lock guard passes; 13/13 controls, no input drift."
            ),
            "evidence_refs": [
                f"numerics/protocol/n0_gate_proposal_leadverify.json#{vor_rev[:12]}",
                f"numerics/tests/n0_gate_proposal.json#{prop_rev[:12]}",
                "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#13600a5d4130",
            ],
        },
        {
            "event_id": f"{base}-artifact-instrument",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "instrument",
            "path": h["verify_vor.py"]["path"],
            "sha256": h["verify_vor.py"]["sha256"],
            "validation_status": "unverified",
            "summary": (
                "Read-only deterministic instrument (sections A-G, 13 fail-closed controls, "
                "before/after input drift guard); re-runnable via "
                "python3 verify_vor.py --out report.json."
            ),
            "evidence_refs": [f"{h['report.json']['path']}#{h['report.json']['sha256'][:12]}"],
        },
        {
            "event_id": f"{base}-artifact-prereg",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "pre_registration",
            "path": h["PRE_REGISTRATION.md"]["path"],
            "sha256": h["PRE_REGISTRATION.md"]["sha256"],
            "validation_status": "unverified",
            "summary": (
                "Predictions P1-P8 and falsifier declared before measurement; P3 deviates "
                "(registry rewritten between the record's snapshot and verification) and is "
                "reported as expected churn in README.md."
            ),
            "evidence_refs": [f"{h['report.json']['path']}#{h['report.json']['sha256'][:12]}"],
        },
        {
            "event_id": f"{base}-review",
            "event_type": "review",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "target_id": f"numerics/protocol/n0_gate_proposal_leadverify.json#{vor_rev[:12]}",
            "reviewer": "worker-014 (independent of the author astra-lead-numerics; advisory only)",
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "findings": [
                "BA-1 closed: the record binds proposal " + prop_rev[:12]
                + " and names artifact event lnum-artifact-1789144642810-0d42bd, which carries the "
                "same path+sha256; the 23-entry chain re-measures 23/23 match, 0 stale, 0 missing.",
                "BA-5b advisory (non-load-bearing): the proposal's declared mutable snapshot "
                "d69b62dc93e5336e5109 at measured_at 2026-09-12T01:06 is future-dated and matches "
                "the registry under neither the full-file nor the section-digest basis.",
                "Verdict binds revision " + vor_rev[:12] + " only; the path is rewritten in place, "
                "so a later rewrite voids this review for the new bytes.",
                "The record's gate_evaluator block is a summary: lock_state maps to lock.state in "
                "the evaluator output.",
            ],
            "evidence_refs": [
                f"{h['report.json']['path']}#{h['report.json']['sha256'][:12]}",
                f"numerics/tests/n0_gate_proposal.json#{prop_rev[:12]}",
            ],
        },
        {
            "event_id": f"{base}-claim-ba1",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "conclusion_type": "numerical_evidence",
            "statement": (
                "At the pinned revision numerics/protocol/n0_gate_proposal_leadverify.json#"
                + vor_rev[:12]
                + " the verification of record binds the current N0 gate proposal "
                + "numerics/tests/n0_gate_proposal.json#" + prop_rev[:12]
                + ": declared proposal sha equals measured bytes, the named artifact event "
                "lnum-artifact-1789144642810-0d42bd carries the same path+sha256, all 23 evidence "
                "rows re-measure match, 23/23 are registered in the union of the registry's "
                "declared and scanned sections, the gate-evaluator run reproduces exit 3 / "
                "N1_BLOCKED / locked / production_allowed=false with all recorded dissenters, the "
                "independent 4-rung refit reproduces every declared order and slope SE exactly "
                "(max pairwise |dp| 7.958e-05 <= 0.25), and the lock guard passes. BA-1 is closed "
                "at this revision; BA-5b (proposal's future-dated mutable snapshot d69b62dc) "
                "persists as a non-load-bearing annotation defect."
            ),
            "assumptions": [
                "the bounded input set (proposal, record, registry, certification, gates.py, map) "
                "is the full verification surface for this claim",
                "the controller registry is rewritten continuously and is measured at one instant, "
                "not treated as stable evidence",
                "the record path may be rewritten again after this measurement; the claim binds "
                "the pinned revision only",
            ],
            "falsifier": rep["falsifier"],
            "evidence_refs": [
                f"numerics/protocol/n0_gate_proposal_leadverify.json#{vor_rev[:12]}",
                f"numerics/tests/n0_gate_proposal.json#{prop_rev[:12]}",
                f"{h['report.json']['path']}#{h['report.json']['sha256'][:12]}",
            ],
        },
        {
            "event_id": f"{base}-blocker-ba5b",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "description": (
                "BA-5b (advisory, non-load-bearing): the N0 gate proposal's declared mutable "
                "registry snapshot runtime/state/artifact_hashes.json#d69b62dc93e5336e5109 with "
                "measured_at 2026-09-12T01:06 is future-dated relative to measurement and matches "
                "the registry on disk under neither the full-file sha256 nor the registry-section "
                "digest basis; the controller rewrites the registry continuously (mtime observed "
                "00:55:27), so the declared instant is not reachable or reproducible. The proposal "
                "itself classifies the field snapshot-pin-of-mutable-registry / 'not as a pin', so "
                "it does not bind the certified order claim."
            ),
            "needed_to_unblock": (
                "Proposal author (astra-lead-numerics) or controller: annotate or re-issue the "
                "mutable_registry_snapshots entry with a wall-clock measurement instant and a "
                "prefix that can be reproduced against the checkpoint artifact of that instant, or "
                "mark the field explicitly non-reproducible. Worker-side re-measurement cannot "
                "close it without moving the proposal hash and voiding verdicts bound to "
                + prop_rev[:12] + "."
            ),
            "evidence_refs": [
                f"numerics/tests/n0_gate_proposal.json#{prop_rev[:12]}",
                f"numerics/protocol/n0_gate_proposal_leadverify.json#{vor_rev[:12]}",
                f"{h['report.json']['path']}#{h['report.json']['sha256'][:12]}",
            ],
        },
        {
            "event_id": f"{base}-status",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-014",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "CHECKPOINT / worker-014, one bounded class-bound task taken (no inbox card for "
                "this slot): W014-GNUM-VOR-REVERIFY-01. Delivered report.json + instrument + "
                "pre-registration + README + checkpoint; 13/13 controls, instrument valid, no "
                "input drift. Verdict VOR_VERIFIED_BA1_CLOSED_BA5B_ANNOTATION_DEFECT_OPEN at "
                "record revision " + vor_rev[:12] + " / proposal revision " + prop_rev[:12] + ". "
                "BA-1 closed; BA-5b persists as a non-load-bearing annotation defect; C8 contest "
                "untouched and the gate stays pending. Worker-level only: no gate verdict, no node "
                "completion, no canonical-path write."
            ),
            "evidence_refs": [
                f"{h['report.json']['path']}#{h['report.json']['sha256'][:12]}",
                f"{h['checkpoint.json']['path']}#{h['checkpoint.json']['sha256'][:12]}",
                f"numerics/protocol/n0_gate_proposal_leadverify.json#{vor_rev[:12]}",
            ],
            "next_falsifier": (
                "A rewrite of the record path (new sha256 != " + vor_rev[:12] + "), a moved "
                "proposal (new sha256 != " + prop_rev[:12] + "), any chain row re-measuring stale, "
                "or a control behaving differently on re-run."
            ),
        },
    ]

    for e in events:
        try:
            validate_event(e)
        except SchemaError as exc:
            print(f"SCHEMA REJECT {e['event_id']}: {exc}", file=sys.stderr)
            return 2
    with open(OUTBOX, "a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], e["event_type"])
    print("checkpoint:", ck.relative_to(ROOT), h["checkpoint.json"]["sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
