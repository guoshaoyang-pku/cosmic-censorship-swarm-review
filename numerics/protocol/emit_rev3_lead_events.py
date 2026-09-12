#!/usr/bin/env python3
"""Emit the numerics-lead lifecycle events for the rev-3 convergence closure.

All event ids are deterministic in their payload, so re-running this script is idempotent:
``numerics.events.emit`` returns the already-appended event instead of duplicating it.

    python3 numerics/protocol/emit_rev3_lead_events.py
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
INSTANCE = REPO / "runtime/instances/lead-numerics-01-20260912T003835-968807/meta.json"
STARTED = json.loads(INSTANCE.read_text())["started_at"] if INSTANCE.is_file() else None
if STARTED:
    HOURS = round(max((time.time() - datetime.fromisoformat(STARTED).timestamp()) / 3600.0, 0.01), 3)
else:
    HOURS = 0.2

REPORT = "numerics/results/flat_wave_convergence_rev3.json"
BUILDER = "numerics/protocol/build_convergence_rev3.py"
VERIFIER = "numerics/protocol/verify_convergence_rev3.py"
BLOCKERS = "numerics/blockers.md"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
GATES = "numerics/gates.py"
W046 = "artifacts/worker-046/n0_fixed_dt_independent/verification.json"
W057 = "artifacts/worker-057/n0_fixeddt_verify/report.json"
W081 = "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"
CHECKPOINTS = "artifacts/numerics/CHECKPOINTS.jsonl"
REGISTRY = "runtime/state/artifact_hashes.json"

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<16} {ev['event_id']}")


# ---------------------------------------------------------------- artifacts
rec(events.emit_artifact(
    "N0", "convergence_report_rev3", REPORT, "unverified",
    validation_evidence=[
        f"{BUILDER}#{H(BUILDER)[:12]}",
        f"{VERIFIER}#{H(VERIFIER)[:12]}",
        f"{CERT}#{H(CERT)[:12]}",
        f"{W046}#{H(W046)[:12]}",
        f"{W057}#{H(W057)[:12]}",
        f"{W081}#{H(W081)[:12]}",
        "internal_checks 58/58 pass; external verifier verify_convergence_rev3.py -> VERIFIED (11 pins)",
    ],
    event_id=events.det_id("artifact", REPORT, H(REPORT))))

rec(events.emit_artifact(
    "N0", "verification_script", VERIFIER, "unverified",
    validation_evidence=[f"{REPORT}#{H(REPORT)[:12]}"],
    event_id=events.det_id("artifact", VERIFIER, H(VERIFIER))))

rec(events.emit_artifact(
    "N1-BLOCK", "lock_contract", BLOCKERS, "unverified",
    validation_evidence=[f"{PROTOCOL}#{H(PROTOCOL)[:12]}", f"{GATES}#{H(GATES)[:12]}"],
    event_id=events.det_id("artifact", BLOCKERS, H(BLOCKERS))))

# ---------------------------------------------------------------- statuses
rec(events.emit_status(
    "N0", "active", HOURS,
    ("N0 audit stop rule CLOSED on the numerics side at the current hashes. "
     "(1) Fourth rung: certification basis is numerics/protocol/n0_fixed_dt_certification.json"
     f"#{H(CERT)[:12]} with 4 rungs per scheme at fixed dt=1e-4 (dr 0.2/0.1/0.05/0.025), three "
     "schemes; orders lffd 1.999943 / cnfd 1.999864 / cnfem 1.999916, max cross-scheme |dp| "
     "7.958e-05 vs R5 floor 0.25. The order did NOT degrade; it is tighter than the constant-CFL "
     "mixed-order values it replaces. (2) Class binding re-derived against F0 rev5 "
     "research_map/formulation_taxonomy.yaml#0abb9ed8a961. (3) Independent replication verdicts "
     "pinned: worker-046 (from-scratch re-run of the frozen module, SUPPORTED 8/8), worker-057 "
     "(independent re-analysis, REPRODUCED, 67 checks/65 pass/2 advisories/0 findings), worker-081 "
     "(review w081-20260912T0042050800-adj2-review, accept at protocol 1e6cdf04). Consolidated "
     f"report {REPORT}#{H(REPORT)[:12]} verified by verify_convergence_rev3.py (VERIFIED, 11 pins). "
     "Open item is NOT numerics-side: the protocol review contest (2 live revise dissents vs 2 "
     "accepts at 1e6cdf04) plus the withdrawn-accept counting defect in numerics/gates.py need a "
     "controller/reviewer disposition. No gate self-pass; numerics_lock stays LOCKED; N1 stays queued."),
    evidence_refs=[
        f"{REPORT}#{H(REPORT)[:12]}",
        f"{CERT}#{H(CERT)[:12]}",
        f"{W046}#{H(W046)[:12]}",
        f"{W057}#{H(W057)[:12]}",
        f"{W081}#{H(W081)[:12]}",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        f"{VERIFIER}#{H(VERIFIER)[:12]}",
    ],
    next_falsifier=("Re-measure the pins: a certification row with dt != 1e-4, fewer than four rungs, "
                    "a fixed-dt order outside |p-2|<=0.3, a cross-scheme |dp| above 0.25, or an F0 "
                    "hash other than 0abb9ed8a961 refutes this status. A file under "
                    "numerics/spherical_solver/ while the lock is locked refutes scope compliance."),
    event_id=events.det_id("status", "N0", "rev3-closure", H(REPORT))))

rec(events.emit_status(
    "N1-BLOCK", "blocked", HOURS,
    ("N1 unblock contract refreshed to the current measured state, 1:1 with "
     "research_map.json#numerics_lock. Rows 1/2 (G-FORM, G-AUDIT) pending; rows 3/4 satisfied "
     "with the fixed-dt certification plus three independent replication verdicts; row 5 protocol "
     "reviewed=true but CONTESTED (2 accepts incl. w081 adj2, 2 live revise dissents at 1e6cdf04; "
     "the guard also counts the withdrawn accept w081-20260912T002140-c8-review); row 6 still "
     "locked since 2026-09-11T23:15:11. Nothing here releases N1."),
    evidence_refs=[
        f"{BLOCKERS}#{H(BLOCKERS)[:12]}",
        "research_map/research_map.json#numerics_lock",
        f"{GATES}#{H(GATES)[:12]}",
        "numerics/tests/selfgravity_lock_guard.py",
        f"{REPORT}#{H(REPORT)[:12]}",
    ],
    next_falsifier=("The guard passes while a required gate is unsatisfied, or this contract proposes "
                    "a self-gravity run, or numerics/spherical_solver/ appears while locked."),
    event_id=events.det_id("status", "N1-BLOCK", "rev3", H(BLOCKERS))))

# ---------------------------------------------------------------- blockers
rec(events.emit_blocker(
    "N0",
    ("C4 REGISTRATION still open for the closure evidence. Measured against "
     f"{REGISTRY}: the protocol {PROTOCOL}#{H(PROTOCOL)[:12]} and the rev-3 report "
     f"{REPORT}#{H(REPORT)[:12]} are NOT registered, nor are {GATES}#{H(GATES)[:12]} or the three "
     f"independent verdict artifacts ({W046}#{H(W046)[:12]}, {W057}#{H(W057)[:12]}, "
     f"{W081}#{H(W081)[:12]}). COMMS PROTOCOL rule 2 requires an artifact + recorded sha256 before a "
     "node can be done, and G-NUM's order-replication criterion cites the rev-3 evidence."),
    ("controller/Astra registers the listed paths and sha256 values in "
     f"{REGISTRY} (one registry pass; no numerics-side write is authorised)."),
    [f"{REGISTRY}", f"{REPORT}#{H(REPORT)[:12]}", f"{PROTOCOL}#{H(PROTOCOL)[:12]}",
     f"{GATES}#{H(GATES)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "c4-registration-rev3", H(REPORT), H(PROTOCOL))))

rec(events.emit_blocker(
    "N0",
    ("STALE MAP PINS on G-NUM. research_map.json#gates[G-NUM].evidence_refs still cite "
     "numerics/gates.py#907a88b141bf4394 (disk is "
     f"{H(GATES)[:12]}) and numerics/tests/n0_gate_proposal.json#22d984781cee/#58a175b52fbe "
     "(disk is b4192221ff7d96db), and the gate's unmet list still carries the five pre-revision "
     "items (no protocol accept recorded, cnfem triage, leapfrog-specific functional, missing 4th "
     "rung, cnfd drift threshold) even though the fixed-dt certification and the three independent "
     "verdicts were filed at 00:35-00:42. A gate adjudicated on the stale refs is not adjudicable."),
    ("controller/Astra re-pins the G-NUM evidence_refs to the current hashes and refreshes the "
     "unmet list against the rev-3 closure report; numerics cannot edit the map."),
    [f"{GATES}#{H(GATES)[:12]}", f"{REPORT}#{H(REPORT)[:12]}",
     "research_map/research_map.json#gates", "reviews/N0-review-lead-audit.json"],
    severity="high",
    event_id=events.det_id("blocker", "g-num-stale-pins", H(GATES), H(REPORT))))

rec(events.emit_blocker(
    "N0",
    ("PROTOCOL REVIEW CONTEST and a measured guard defect. At "
     f"{PROTOCOL}#{H(PROTOCOL)[:12]}: accepts audit-review-gnum-protocol-final-20260912T0027 and "
     "w081-20260912T0042050800-adj2-review; live revise dissents "
     "w067-review-gnum-protocol-r3-20260912T002256 and w081-2026-09-12T00:29:19+0800-f1-review. "
     "The second dissent was closed by its own author's falsifier (worker-081 adj2 disposition "
     "F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION), but numerics/gates.py::_protocol_review still "
     "counts the withdrawn accept w081-20260912T002140-c8-review and reports contest=true. Two "
     "distinct dispositions are needed: (a) withdrawal semantics for a review record, (b) whether a "
     "later accept by the same reviewer at the same hash rescinds that reviewer's earlier revise."),
    ("controller/reviewer adjudication of the contest, or an explicit guard supersession rule by "
     "(reviewer, target) at one hash. numerics may not self-adjudicate a review of its own protocol; "
     "rewriting the protocol now would invalidate every verdict bound to 1e6cdf04."),
    [f"{GATES}#{H(GATES)[:12]}", f"{PROTOCOL}#{H(PROTOCOL)[:12]}",
     f"{W081}#{H(W081)[:12]}", "reviews/G-NUM-protocol-review.json"],
    severity="high",
    event_id=events.det_id("blocker", "protocol-contest-rev3", H(GATES), H(PROTOCOL))))

rec(events.emit_blocker(
    "N0",
    ("NODE-STATUS MIS-TRANSITION: map N0.status == 'rejected' (measured 2026-09-12T00:43:08) is "
     "not a node-level rejection. It was applied from worker-081's *task* withdrawal status "
     "w081-20260912T0042190800-fdt02-withdrawn (00:42:19, status=rejected), which withdraws "
     "W081-N0-FDT-02 - a ladder that became redundant when the lead filed the protocol-exact "
     "fixed-dt certification 1677822ceb9c81e8 - after its pin guard aborted on a moved proposal "
     "path. The withdrawal's own next_falsifier says an exact-prescription ladder is needed only "
     "if the certification is withdrawn or moves; it has not moved. Meanwhile the N0 stop-rule "
     "evidence (four-rung certification, F0 rev5 rebind, three independent verdicts) is on disk "
     "unchanged, so 'rejected' misrepresents the node state to any auditor reading the map."),
    ("controller re-derives node status from node-scoped acceptance state rather than from a "
     "worker's bounded-task withdrawal; restore N0 to active/unverified until G-NUM is adjudicated. "
     "Also worth a guard: a task-withdrawal event should not carry a node-level status token."),
    ["research_map/research_map.json#groups[numerics].nodes[N0].status",
     "w081-20260912T0042190800-fdt02-withdrawn",
     "artifacts/worker-081/n0_fixed_dt_certification/fixed_dt_study.json#49e56e25eb5e4035",
     f"{REPORT}#{H(REPORT)[:12]}"],
    severity="high",
    event_id=events.det_id("blocker", "n0-node-status-mistransition", H(REPORT))))

# ---------------------------------------------------------------- gate proposal
rec(events.emit_gate(
    "G-NUM",
    "N0",
    "pending",
    ("Status of the four G-NUM criteria at the rev-3 hashes, proposed to Astra (NOT a self-pass): "
     "(1) order measured = MET, fixed-dt 4-rung certification, orders 1.999943/1.999864/1.999916; "
     "(2) independently replicated within tolerance = MET, worker-046 SUPPORTED 8/8 and worker-057 "
     "REPRODUCED 0 findings, max |dp| 7.958e-05 <= 0.25; (3) protocol reviewed = REVIEWED but "
     "CONTESTED (2 accepts, 2 live revise dissents at 1e6cdf04; withdrawn accept still counted); "
     "(4) lock guard passes = MET (fail-closed N1_BLOCKED, no solver dir). Verdict held at pending "
     "by numerics pending the controller/reviewer disposition of criterion 3; numerics_lock stays "
     "LOCKED and N1 stays queued regardless."),
    evidence_refs=[
        f"{REPORT}#{H(REPORT)[:12]}",
        f"{CERT}#{H(CERT)[:12]}",
        f"{W046}#{H(W046)[:12]}",
        f"{W057}#{H(W057)[:12]}",
        f"{W081}#{H(W081)[:12]}",
        f"{PROTOCOL}#{H(PROTOCOL)[:12]}",
        f"{GATES}#{H(GATES)[:12]}",
    ],
    event_id=events.det_id("gate", "G-NUM", "rev3-pending", H(REPORT))))

print(json.dumps({"emitted": len(emitted), "hours": HOURS,
                  "report_sha256": H(REPORT), "blockers_sha256": H(BLOCKERS)}, indent=1))
