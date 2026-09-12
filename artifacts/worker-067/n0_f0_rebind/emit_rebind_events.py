#!/usr/bin/env python3
"""Emit worker-067 outbox events for W067-N0-F0-REBIND-01 (validated, idempotent-ish)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SW = HERE.parents[2]
sys.path.insert(0, str(SW / "research_map"))
from schemas import validate_event  # noqa: E402

OUTBOX = SW / "comms/outbox/worker-067.jsonl"
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sha(SW / rel)[:n]}"


def main() -> int:
    d = json.loads((HERE / "rebind_check.json").read_text())
    ts = datetime.now(CST).isoformat(timespec="seconds")
    tag = ts.replace("-", "").replace(":", "").replace("+", "").replace("T", "T")[:15]
    falsifier = d["falsifier"]
    ev = [
        {
            "event_id": f"w067-n0rebind-{tag}-00-take",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-067",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "status": "active",
            "hours": 0.1,
            "summary": (
                "Took W067-N0-F0-REBIND-01 (no worker-067 inbox assignment; claimed from the live "
                "G-NUM stop-rule item 'F0 re-bind' in lifecycle_20260912-003316.json): independently "
                "verify whether re-binding the N0 chain's stale F0 pin to canonical rev5 changes "
                "AF-WCC-SCALAR-SPH class membership. Read-only; no canonical writes."
            ),
            "evidence_refs": [
                ref("runtime/state/controller_verification/lifecycle_20260912-003316.json"),
                ref("research_map/formulation_taxonomy.yaml"),
            ],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w067-n0rebind-{tag}-10-check-py",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-067",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "reproducible_check_script",
            "path": "artifacts/worker-067/n0_f0_rebind/check_rebind.py",
            "sha256": sha(HERE / "check_rebind.py"),
            "validation_status": "unverified",
            "evidence_refs": [ref("research_map/formulation_taxonomy.yaml")],
        },
        {
            "event_id": f"w067-n0rebind-{tag}-11-check-json",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-067",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "class_rebind_evidence",
            "path": "artifacts/worker-067/n0_f0_rebind/rebind_check.json",
            "sha256": sha(HERE / "rebind_check.json"),
            "validation_status": "unverified",
            "summary": (
                f"verdict={d['verdict']} controls={d['controls_pass']}; membership fields "
                "axes/hypotheses/exclusions/conclusion.type invariant 276009f4->rev5; only "
                "conclusion.text changed and is not load-bearing for N0; residual active stale pins "
                "in fixed_replication_verdict.json (L7/L39) and CONVERGENCE_PROTOCOL.md (L7)."
            ),
            "evidence_refs": [
                ref("artifacts/worker-067/n0_f0_rebind/rebind_check.json"),
                ref("artifacts/flash-02/frozen_rebind_report.json"),
                ref("schemas/taxonomy_cases.jsonl"),
                ref("numerics/tests/n0_gate_proposal.json"),
                ref("numerics/protocol/fixed_replication_verdict.json"),
                ref("numerics/CONVERGENCE_PROTOCOL.md"),
            ],
        },
        {
            "event_id": f"w067-n0rebind-{tag}-12-readme",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-067",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "method_and_findings_note",
            "path": "artifacts/worker-067/n0_f0_rebind/README.md",
            "sha256": sha(HERE / "README.md"),
            "validation_status": "unverified",
            "evidence_refs": [ref("artifacts/worker-067/n0_f0_rebind/rebind_check.json")],
        },
        {
            "event_id": f"w067-n0rebind-{tag}-13-emitter",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-067",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "artifact_type": "event_emitter",
            "path": "artifacts/worker-067/n0_f0_rebind/emit_rebind_events.py",
            "sha256": sha(HERE / "emit_rebind_events.py"),
            "validation_status": "unverified",
            "evidence_refs": [ref("comms/PROTOCOL.md")],
        },
        {
            "event_id": f"w067-n0rebind-{tag}-20-review",
            "event_type": "review",
            "created_at": ts,
            "actor": "worker-067",
            "reviewer": "worker-067",
            "target_id": "N0-class-binding",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "verdict": "accept",
            "score": 4.0,
            "counts_as_full_schema_verdict": False,
            "hard_failures": [],
            "findings": [
                (
                    "F1 (accept basis): the re-bind of the N0 class pin from 66bf917b to canonical "
                    "rev5 0abb9ed8a961 is INERT for AF-WCC-SCALAR-SPH membership. Axes certified "
                    "identical across 66bf917b->565a6e50 (taxonomy_cases meta) == 565a6e50-era "
                    "certified axis block (frozen_rebind_report) == 276009f4 == rev5 (byte "
                    "extraction); label/hypotheses/exclusions/conclusion_type byte-identical "
                    "276009f4->rev5; five controls pass."
                ),
                (
                    "F2 (scope, not a hard failure): hypotheses/exclusions are byte-verified only "
                    "from the last preserved predecessor 276009f4; no byte copy of 66bf917b or "
                    "565a6e50 exists on disk, so that segment rests on the axis-vector certificate."
                ),
                (
                    "F3 (residual, not this verdict's target): fixed_replication_verdict.json "
                    "L7/L39 and CONVERGENCE_PROTOCOL.md L7 still carry the superseded 66bf917b pin "
                    "as an active binding; proposed new value is the measured rev5 hash, owner "
                    "astra-lead-numerics. The lead's rewritten n0_gate_proposal.json already pins rev5."
                ),
            ],
            "evidence_refs": [
                ref("artifacts/worker-067/n0_f0_rebind/rebind_check.json"),
                ref("research_map/formulation_taxonomy.yaml"),
                ref("artifacts/worker-067/n0_f0_rebind/pinned/F0_rev5_0abb9ed8.yaml"),
                ref("artifacts/worker-067/n0_f0_rebind/pinned/F0_prev_276009f4.yaml"),
                ref("artifacts/flash-02/frozen_rebind_report.json"),
                ref("schemas/taxonomy_cases.jsonl"),
            ],
            "reviewer_independence": (
                "bounded breadth worker; author of no F0 taxonomy content, no N0 numerics artifact, "
                "and no astra-lead-numerics file; read-only on every canonical path; wrote only under "
                "artifacts/worker-067/ and comms/outbox/worker-067.jsonl"
            ),
            "independence_limits": (
                "This is a SCOPED accept (counts_as_full_schema_verdict=false): it accepts the class "
                "re-bind only, not the N0 node, not the order claim, and not G-NUM. The independent "
                "replication verdict remains PROVISIONAL and is a separate stop-rule item."
            ),
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w067-n0rebind-{tag}-99-complete",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-067",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "W067-N0-F0-REBIND-01 complete at worker level: REBIND_INERT_FOR_CLASS_MEMBERSHIP, "
                "5/5 controls, no canonical writes. Disclosed concurrent lead rewrite of "
                "n0_gate_proposal.json (58a175b5->b4192221) which already carries the rev5 pin; this "
                "check verifies that re-bind independently. Residual stale active pins listed in the "
                "artifact, not applied. No gate verdict, no node transition; N0 stays active and "
                "numerics_lock stays LOCKED."
            ),
            "evidence_refs": [
                ref("artifacts/worker-067/n0_f0_rebind/rebind_check.json"),
                "runtime/state/worker-067_checkpoint_5.json",
            ],
            "next_falsifier": falsifier,
        },
    ]
    for e in ev:
        validate_event(e)
    with open(OUTBOX, "a") as f:
        for e in ev:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(ev)} schema-valid events to {OUTBOX}")
    for e in ev:
        print(" ", e["event_type"], e["event_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
