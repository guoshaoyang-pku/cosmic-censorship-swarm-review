#!/usr/bin/env python3
"""Write the numerics-lead rev-3 lifecycle record and emit the closing GLOBAL status.

    python3 numerics/protocol/emit_rev3_lifecycle_record.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
INSTANCE_ID = "lead-numerics-01-20260912T003835-968807"
INSTANCE = REPO / "runtime/instances" / INSTANCE_ID
META = json.loads((INSTANCE / "meta.json").read_text())
STARTED = META["started_at"]
HOURS = round(max((time.time() - datetime.fromisoformat(STARTED).timestamp()) / 3600.0, 0.01), 3)
ENDED = datetime.now().astimezone().isoformat(timespec="seconds")

OUT = REPO / "artifacts/numerics/lifecycle_rev3_20260912.json"

PRODUCED = [
    "numerics/results/flat_wave_convergence_rev3.json",
    "numerics/protocol/build_convergence_rev3.py",
    "numerics/protocol/verify_convergence_rev3.py",
    "numerics/protocol/emit_rev3_lead_events.py",
    "numerics/blockers.md",
    "artifacts/numerics/REV3_CLOSURE.md",
]
BLOCKERS = [
    "lnum-blocker-19abcac59057b2d37171",  # C4 registration
    "lnum-blocker-6fa9470dea32d5404f73",  # stale G-NUM map pins
    "lnum-blocker-e9e939acc0856fa77127",  # protocol review contest + withdrawn accept
    "lnum-blocker-5a0058b17270d4813fd9",  # N0 node-status mis-transition from a task withdrawal
]
STATUSES = ["lnum-status-c3a8b6e7c4d1bfbfde1e", "lnum-status-16a74726cec2d12b12d6"]
ARTIFACT_EVENTS = [
    "lnum-artifact-ffe9eb57789e80b71d42",
    "lnum-artifact-18fb147b68814d99254b",
    "lnum-artifact-9a04bd9bfdad377c9cfa",
]

record = {
    "schema": "numerics-lead-lifecycle/v1",
    "group": "numerics",
    "instance_id": INSTANCE_ID,
    "started_at": STARTED,
    "ended_at": ENDED,
    "agent_hours_this_lead": HOURS,
    "run_card_consumed": {
        "event_id": "astra-life04-n0-stoprule",
        "node_id": "N0",
        "artifact_required": "numerics/results/flat_wave_convergence_rev3.json",
        "stop_rule": "2 agent-hours; a named blocker with measured evidence is acceptable closure.",
    },
    "predicates_closed": {
        "fourth_rung": True,
        "f0_rev5_rebind": True,
        "independent_replication_verdict": True,
    },
    "order_reported": {
        "lffd": 1.999943173893314,
        "cnfd": 1.9998635927240203,
        "cnfem": 1.9999163079874884,
        "degraded": False,
        "max_cross_scheme_abs_dp": 7.958116929374093e-05,
        "r5_floor": 0.25,
    },
    "artifacts_produced": {rel: H(rel) for rel in PRODUCED},
    "events_emitted": {
        "artifacts": ARTIFACT_EVENTS,
        "statuses": STATUSES,
        "blockers": BLOCKERS,
        "gate_proposal": "lnum-gate-ce4e3a37fb046e16eb73",
        "final_global_status": None,  # set after emission
    },
    "checkpoint": "num-ckpt-20260912-004552",
    "gate_state_after": {
        "verdict": "N1_BLOCKED",
        "production_allowed": False,
        "lock": "locked",
        "protocol_reviewed": True,
        "protocol_contest": True,
        "spherical_solver_present": False,
    },
    "open_items_handed_back": [
        "C4 registration of CONVERGENCE_PROTOCOL.md#1e6cdf04, the rev-3 report, gates.py#fcd1d709 and the three independent verdict artifacts in runtime/state/artifact_hashes.json",
        "stale G-NUM map pins (gates.py#907a88b141bf4394, n0_gate_proposal.json#22d984781cee/#58a175b52fbe) and a pre-revision unmet list",
        "protocol review contest at 1e6cdf04 (2 accepts, 2 live revise dissents) plus the withdrawn-accept counting defect in numerics/gates.py::_protocol_review",
        "map N0.status=='rejected' applied from worker-081's task-level withdrawal (W081-N0-FDT-02) rather than from node-scoped acceptance state",
    ],
    "scope_compliance": {
        "self_gravitating_code_written_or_run": False,
        "spherical_solver_dir_present": (REPO / "numerics/spherical_solver").exists(),
        "n1_status_moved": False,
        "gate_self_pass": False,
        "self_review": False,
    },
    "verify_commands": [
        "python3 numerics/protocol/verify_convergence_rev3.py",
        "python3 -m numerics.gates --check",
        "python3 numerics/tests/flat_wave.py --lock-guard",
    ],
}

OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

final = events.emit_status(
    "GLOBAL", "done", HOURS,
    ("NUMERICS GROUP LEAD LIFECYCLE COMPLETE -- exiting. Handoff/map/comms read; card "
     "astra-life04-n0-stoprule consumed. N0 audit stop rule closed on the numerics side: (1) 4-rung "
     "fixed-dt certification basis (dt=1e-4, three schemes, orders 1.999943/1.999864/1.999916, max "
     "|dp| 7.958e-05 vs R5 floor 0.25; order did not degrade); (2) class binding re-derived to F0 "
     "rev5 research_map/formulation_taxonomy.yaml#0abb9ed8a961; (3) three independent replication "
     "verdicts pinned (worker-046 SUPPORTED 8/8, worker-057 REPRODUCED 0 findings, worker-081 accept). "
     f"Deliverable numerics/results/flat_wave_convergence_rev3.json#{H('numerics/results/flat_wave_convergence_rev3.json')[:12]} "
     "with 58/58 internal checks and an external verifier returning VERIFIED (11 pins). One "
     "checkpoint num-ckpt-20260912-004552; 10 structured events (3 artifacts, 2 statuses, 4 blockers, "
     "1 gate proposal). Four blockers handed to the controller: C4 registration gap, stale G-NUM map "
     "pins, the protocol review contest incl. the withdrawn-accept counting defect, and the N0 "
     "node-status mis-transition to 'rejected' applied from a worker's task-level withdrawal. No gate "
     "self-pass; numerics_lock stays LOCKED; N1 stays queued; numerics/spherical_solver/ absent."),
    evidence_refs=[
        "artifacts/numerics/lifecycle_rev3_20260912.json",
        f"numerics/results/flat_wave_convergence_rev3.json#{H('numerics/results/flat_wave_convergence_rev3.json')[:12]}",
        f"numerics/blockers.md#{H('numerics/blockers.md')[:12]}",
        "artifacts/numerics/CHECKPOINTS.jsonl",
        "research_map/research_map.json#numerics_lock",
    ],
    next_falsifier=("Any numerics/spherical_solver file while the lock is locked, any N1 activation, "
                    "or a gate pass recorded on the stale pins listed in the blockers."),
    event_id=events.det_id("status", "GLOBAL", "lead-numerics-rev3-done",
                           H("numerics/results/flat_wave_convergence_rev3.json"), *BLOCKERS))
record["events_emitted"]["final_global_status"] = final["event_id"]
record["events_emitted"]["final_global_status_note"] = (
    "supersedes lnum-status-b583abd603f1de59e137, emitted before the fourth blocker was filed")
OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

print(json.dumps({
    "record": "artifacts/numerics/lifecycle_rev3_20260912.json",
    "record_sha256": H("artifacts/numerics/lifecycle_rev3_20260912.json"),
    "hours": HOURS,
    "final_status_event": final["event_id"],
    "gate": "N1_BLOCKED",
}, indent=1))
