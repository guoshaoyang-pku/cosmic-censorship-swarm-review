#!/usr/bin/env python3
"""Close astra-numfix-02: emit the N0/G-NUM gate proposal, its evidence hashes and the
upward events, then a worker checkpoint.

Deliverable: numerics/tests/n0_gate_proposal.json  (assignment astra-numfix-02)
Supporting: numerics/tests/n0_order_4rung.json + addendum script
No gate self-pass: the gate event below is a proposal with verdict ``pending``.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-13"
RUN = "run-2026-09-12T00:00+08:00"
PROPOSAL = "numerics/tests/n0_gate_proposal.json"
ADDENDUM_PY = "numerics/tests/n0_order_4rung_addendum.py"
ADDENDUM_JSON = "numerics/tests/n0_order_4rung.json"
CHECKPOINT = "runtime/state/w13_checkpoint_1.json"

EVIDENCE_PATHS = [
    "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json",
    "numerics/tests/flat_wave_replication.py",
    "numerics/tests/replication_triage.md",
    ADDENDUM_PY, ADDENDUM_JSON,
    "numerics/results/flat_wave_replication.json",
    "artifacts/flash-12/n0/replication_recheck.json",
    "numerics/protocol/scheme_independence_review.md",
    "numerics/protocol/scheme_independence_evidence.json",
    "numerics/protocol/convergence_protocol.md",
    "numerics/protocol/report_lffd.json",
    "numerics/protocol/report_cnfd.json",
    "numerics/protocol/gate_reports_summary.json",
    "numerics/tests/selfgravity_lock_guard.py",
    "runtime/state/controller_verification/N0_adjudication.md",
    "numerics/tests/flat_wave.py",
    "reviews/N0-review-lead-audit.json",
]


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#sha256:{sha(rel)[:16]}"


def main() -> int:
    h = {p: sha(p) for p in EVIDENCE_PATHS}
    addendum = json.loads((ROOT / ADDENDUM_JSON).read_text())
    fixed = json.loads((ROOT / EVIDENCE_PATHS[0]).read_text())
    r4 = addendum["verdict"]["orders"]
    r4d = addendum["verdict"]["delta"]
    r3 = {"lffd": fixed["result"]["reference_measured_order"],
          **fixed["result"]["independent_orders"]}

    proposal = {
        "schema_version": "0.1",
        "artifact": PROPOSAL,
        "assignment": "astra-numfix-02",
        "created_at": NOW,
        "author": ACTOR,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "proposal": {
            "recommended_verdict": "pending",
            "recommended_verdict_if": "pass",
            "condition": ("lead-audit records the independent numerical-protocol review "
                          "(reviews/G-NUM-protocol-review.json) at the fixed run hash "
                          "6542db93 accepting the scheme-independence evidence and R1-R5, "
                          "with no new hard finding"),
            "no_self_pass": ("this worker does not set the gate. Submitted to Astra as a "
                             "proposal; see the gate event f13-n0-numfix02-gate-proposal."),
            "scope": "N0 flat-space calibration only; N1 queued, numerics_lock LOCKED",
        },
        "criteria": [
            {"id": "order-measured", "status": "met",
             "evidence": [ref("numerics/tests/flat_wave_replication.py"),
                          ref("numerics/results/flat_wave_replication.json")]},
            {"id": "independent-replication-within-tolerance", "status": "met",
             "detail": {"3_rung": r3, "4_rung": r4,
                        "reference_order": fixed["result"]["reference_measured_order"],
                        "p_expected": 2.0, "p_tol": 0.3},
             "evidence": [ref("runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"),
                          ref(ADDENDUM_JSON)]},
            {"id": "clean-self-tests", "status": "met",
             "detail": {"selftest_pass": fixed["selftest"]["pass"],
                        "determinism_bitwise_equal": fixed["determinism"]["bitwise_equal"],
                        "controls_reject_frozen_and_wrong_sign": True},
             "evidence": [ref("runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json")]},
            {"id": "protocol-reviewed-by-audit", "status": "unmet",
             "owner": "lead-audit (astra-numfix-04); nobody may self-review",
             "detail": "reviews/G-NUM-protocol-review.json absent at generation time; "
                       "peer review " + ref("numerics/protocol/scheme_independence_review.md") +
                       " exists but is pre-fix-pinned and is not the audit review",
             "evidence": [ref("reviews/N0-review-lead-audit.json")]},
            {"id": "lock-guard-passes", "status": "met",
             "detail": "verdict PASS; numerics/spherical_solver/ absent; N1 blocked",
             "evidence": [ref("numerics/tests/selfgravity_lock_guard.py")]},
            {"id": "rubric-four-resolutions", "status": "met_for_replication",
             "detail": ("replication order claim now carried at 4 rungs (dr 0.2/0.1/0.05/0.025); "
                        "the candidate numerics/tests/flat_wave.py 4th rung remains its owner's item"),
             "evidence": [ref(ADDENDUM_JSON), ref("reviews/N0-review-lead-audit.json")]},
        ],
        "scheme_independence": {
            "methods": fixed["candidate_comparison"]["replication_methods"],
            "independent_axes": ["time integration (explicit symplectic vs implicit trapezoidal)",
                                 "spatial discretisation (FD vs consistent-mass P1 FEM)",
                                 "energy functional (leapfrog staggered vs average-acceleration)"],
            "orders_3_rung": r3,
            "orders_4_rung": r4,
            "delta_4_rung_R5": r4d,
            "pairwise_agreement_R5": addendum["pairwise_agreement_R5"],
            "pre_fix_pin_resolved": ("the earlier review " + ref("numerics/protocol/scheme_independence_review.md") +
                                     " was pinned to the pre-fix run 7adab492; its disposition 1 "
                                     "(re-pin) is satisfied by the controller re-run 6542db93 at "
                                     "script 8ade1cdc"),
            "harness_functional_finding": (
                "the harness invariant functional is the leapfrog staggered energy; it is now "
                "reported as harness_leapfrog_energy_drift (labelled cross-check) beside each "
                "scheme's own_energy_drift, so no scheme is gated on another scheme's functional. "
                "cnfd's 6.6e-8 is a labelled cross-functional mismatch diagnostic, not its own "
                "drift (own drift 1.11e-14); worker 14's falsifier at drift_tol=1e-6 is triggered "
                "and recorded."),
            "shared_axes_not_tested": fixed["candidate_comparison"]["shared_axes_not_tested"],
        },
        "cnfem_root_cause": {
            "defect": ("CrankNicolsonFEM assembled the recurrence as (M + cK) psi^{n+1} = "
                       "2 M psi^n - (M - cK) psi^{n-1}, c = dt^2/2; the trapezoidal rule "
                       "requires -(M + cK) psi^{n-1} on the right-hand side"),
            "effect": ("the scheme is no longer CN; one amplification root has |rho| > 1 per "
                       "generalized eigenmode, giving order -0.0773, harness drift 1.0e+01 "
                       "and a failing self-test in the pinned pre-fix run"),
            "fix": "one line: use B = M + cK on the right-hand side",
            "post_fix": {"order": r3["cnfem"], "harness_drift": 8.481868011635823e-09,
                         "own_energy_drift": 2.0438718559608235e-14, "harness_verdict": "PASS",
                         "selftest_pass": fixed["selftest"]["pass"]},
            "disposition": "retained, not deleted; no threshold relaxed",
            "minimal_reproduction": ref("numerics/tests/replication_triage.md"),
            "peer_recheck": ref("artifacts/flash-12/n0/replication_recheck.json"),
        },
        "protocol_state": {
            "peer_review": ref("numerics/protocol/scheme_independence_review.md"),
            "peer_review_requirements": "R1 declare functional, R2 exact-discrete tolerance, "
                                        "R3 convergent diagnostics, R4 no cross-scheme functional "
                                        "gates, R5 order with uncertainty, R6 freeze thresholds",
            "end_to_end_check": {"lffd": "1.9977 +/- 4.2e-05 PASS C0-C9",
                                 "cnfd": "1.9948 +/- 1.21e-03 PASS C0-C9",
                                 "source": ref("numerics/protocol/scheme_independence_review.md")},
            "audit_review_absent": "reviews/G-NUM-protocol-review.json (astra-numfix-04, open)",
        },
        "unmet_items_after_this_submission": [
            {"item": "independent numerical-protocol review is not recorded",
             "owner": "lead-audit / worker 14", "closed_by_this_submission": False},
            {"item": "cnfem triage from the N0 adjudication is not closed",
             "owner": ACTOR, "closed_by_this_submission": True},
            {"item": "replication harness invariant functional is leapfrog-specific",
             "owner": ACTOR, "closed_by_this_submission": "relabelled scheme-appropriate; "
             "R1-R4 replacement is a protocol-owner decision"},
            {"item": "audit lead asks for a 4th resolution",
             "owner": ACTOR + " + candidate owner",
             "closed_by_this_submission": "replication order claim: yes, 4 rungs "
             "(n0_order_4rung.json); candidate flat_wave.py: its owner's item"},
            {"item": "cnfd own-energy drift 6.6e-8 has no principled threshold justification",
             "owner": ACTOR,
             "closed_by_this_submission": "6.6e-8 is the labelled cross-functional mismatch, "
             "not cnfd's own drift (1.11e-14); the principled criterion is protocol R2/R3"},
        ],
        "falsifiers": [
            "F1: an independent protocol review re-pinned at 6542db93 rejects scheme independence "
            "(e.g. shows cnfd/cnfem share the pre-fix defect) -> proposal withdrawn",
            "F2: re-running the addendum at frozen hash 8ade1cdc gives a non-monotone scheme, an "
            "order outside 2.0 +/- 0.3, or a pairwise |dp| above the R5 bound -> 4-rung claim withdrawn",
            "F3: the frozen-module hash guard fails (file edited after controller verification) -> "
            "addendum evidence is void",
            "F4: audit finds the labelled leapfrog cross-check still counts as scheme-agnostic "
            "evidence -> relabelling insufficient, G-NUM stays pending",
            "F5: cnfem reproduces with the corrected RHS in the pre-fix revision (sign was not the "
            "cause) -> triage root cause withdrawn",
        ],
        "not_claimed": [
            "no gate verdict and no gate self-pass; recommended verdict is pending with a named condition",
            "no node completion; N0 stays active and N1 stays locked",
            "no claim that the candidate numerics/tests/flat_wave.py is correct",
            "no physics claim; flat-space calibration evidence only",
        ],
        "provenance": {"python": platform.python_version(), "generated_at": NOW, "run_id": RUN},
    }
    (ROOT / PROPOSAL).write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
    ph = sha(PROPOSAL)

    claim = validate_event({
        "event_id": "f13-n0-numfix02-claim-orders",
        "event_type": "claim", "created_at": NOW, "actor": ACTOR,
        "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "statement": (
            "On the controller-verified replication run (script 8ade1cdc, run 6542db93) the N0 "
            "flat-space order-2 claim is reproduced by three methodologically independent schemes: "
            f"lffd {r3['lffd']:.4f}, cnfd {r3['cnfd']:.4f} (implicit CN + FD), cnfem {r3['cnfem']:.4f} "
            "(implicit CN + P1 FEM), all within the harness tolerance with clean self-tests. At a "
            f"fourth resolution (dr=0.025) the orders are lffd {r4['lffd']:.4f}, cnfd {r4['cnfd']:.4f}, "
            f"cnfem {r4['cnfem']:.4f}, monotone and pairwise agreeing under the protocol R5 bound. "
            "cnfem's pre-fix failure (order -0.0773) was a one-line CN RHS sign defect (M-cK vs M+cK), "
            "root-caused, fixed and not deleted. Independence holds along time integration, spatial "
            "discretisation and energy functional; the shared psi=r*phi reduction, Dirichlet walls, "
            "Taylor start and manufactured-pulse methodology remain untested axes. Not a gate verdict."),
        "assumptions": [
            "the controller-verified run 6542db93 is the evidence of record, not this worker's report",
            "independence is claimed along the three named axes only; shared axes are listed as untested",
            "the harness leapfrog functional is a labelled cross-check, not a scheme-agnostic pass/fail",
            "frozen-module hash guard held at generation time",
        ],
        "falsifier": ("a re-pinned independent review showing a shared discretisation defect, or the "
                      "addendum at frozen hash 8ade1cdc reporting non-monotone/out-of-band orders or "
                      "|dp| above the R5 bound, or the frozen-module hash guard failing"),
        "evidence_refs": [ref("runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"),
                          ref("numerics/tests/replication_triage.md"), ref(ADDENDUM_JSON),
                          ref("artifacts/flash-12/n0/replication_recheck.json")],
    })
    gate = validate_event({
        "event_id": "f13-n0-numfix02-gate-proposal",
        "event_type": "gate", "created_at": NOW, "actor": ACTOR,
        "gate_id": "G-NUM", "scope": "N0", "verdict": "pending",
        "criteria": ("order measured AND replicated by >=2 independent schemes with clean self-tests "
                     "(met: lffd/cnfd/cnfem, 3-rung and 4-rung); protocol reviewed by audit (UNMET: "
                     "reviews/G-NUM-protocol-review.json absent, nobody may self-review); lock guard "
                     "passes (met, PASS). PROPOSAL ONLY - no self-pass; see " + PROPOSAL),
        "evidence_refs": [f"{PROPOSAL}#sha256:{ph[:16]}",
                          ref("runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"),
                          ref(ADDENDUM_JSON), ref("reviews/N0-review-lead-audit.json")],
    })
    artifacts = [
        validate_event({"event_id": "f13-n0-numfix02-art-proposal", "event_type": "artifact",
                        "created_at": NOW, "actor": ACTOR, "node_id": "N0",
                        "class_id": "AF-WCC-SCALAR-SPH", "artifact_type": "gate_proposal",
                        "path": PROPOSAL, "sha256": ph, "validation_status": "unverified"}),
        validate_event({"event_id": "f13-n0-numfix02-art-4rung", "event_type": "artifact",
                        "created_at": NOW, "actor": ACTOR, "node_id": "N0",
                        "class_id": "AF-WCC-SCALAR-SPH", "artifact_type": "numerical_evidence",
                        "path": ADDENDUM_JSON, "sha256": h[ADDENDUM_JSON],
                        "validation_status": "unverified"}),
        validate_event({"event_id": "f13-n0-numfix02-art-addendum-src", "event_type": "artifact",
                        "created_at": NOW, "actor": ACTOR, "node_id": "N0",
                        "class_id": "AF-WCC-SCALAR-SPH", "artifact_type": "code",
                        "path": ADDENDUM_PY, "sha256": h[ADDENDUM_PY],
                        "validation_status": "unverified"}),
    ]
    status = validate_event({
        "event_id": "f13-n0-numfix02-status-cp1",
        "event_type": "status", "created_at": NOW, "actor": ACTOR,
        "node_id": "N0", "status": "active", "hours": 1.5,
        "summary": (
            "CHECKPOINT 1 / astra-numfix-02 closed. Emitted n0_gate_proposal.json "
            f"(sha256 {ph[:16]}) with the new replication hashes (controller-verified run 6542db93, "
            "script 8ade1cdc, clean re-run 298a4d92), the cnfem root cause (CN RHS sign M-cK vs M+cK; "
            "not deleted; gate not relaxed) and a hash-cited G-NUM proposal: recommended verdict "
            "pending, pass if lead-audit records the protocol review at 6542db93. Closed by evidence: "
            "cnfem triage, scheme-appropriate invariant relabelling, 4th resolution for the replication "
            "order claim (new n0_order_4rung.json c88146a1: lffd 1.9966/cnfd 1.9954/cnfem 1.9889, "
            "monotone, R5-agreeing). Still open and not mine: the independent audit protocol review "
            "(astra-numfix-04). No gate self-pass, no node completion, no physics claim. Checkpoint "
            f"record: {CHECKPOINT}."),
        "evidence_refs": [f"{PROPOSAL}#sha256:{ph[:16]}", ref(ADDENDUM_JSON),
                          ref("runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"),
                          ref("numerics/tests/replication_triage.md")],
        "next_falsifier": ("lead-audit protocol review at 6542db93 rejects scheme independence, or a "
                           "candidate-owner 4-rung run changes the candidate order claim, or the frozen "
                           "module hash 8ade1cdc changes"),
    })
    events = [artifacts[0], artifacts[1], artifacts[2], claim, gate, status]

    checkpoint = {
        "checkpoint": 1, "at": NOW, "worker": ACTOR, "run": RUN,
        "assignments": {
            "astra-numfix-02": "closed: proposal + cnfem root cause + 4-rung addendum",
            "astra-adj2-02-assignment": "closed earlier: replication_triage.md f27a253e",
            "asg-2026-09-11-N0-deepseek-flash-13-22": "closed earlier: replication 8ade1cdc/298a4d92",
            "assign-FORM-GATE-01-20260911T2331": "closed earlier under F-GATE-4 blocker (unpublished R17-R22)",
        },
        "hours_spent_estimate": 1.5,
        "artifacts": {PROPOSAL: ph[:16], ADDENDUM_JSON: h[ADDENDUM_JSON][:16],
                      ADDENDUM_PY: h[ADDENDUM_PY][:16],
                      "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json": h[EVIDENCE_PATHS[0]][:16],
                      "numerics/tests/flat_wave_replication.py": h["numerics/tests/flat_wave_replication.py"][:16],
                      "numerics/tests/replication_triage.md": h["numerics/tests/replication_triage.md"][:16]},
        "outbox_events": [e["event_id"] for e in events],
        "gate_proposal": "G-NUM pending; pass-if lead-audit protocol review at 6542db93",
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver/",
        "next": ["await lead-audit protocol review at 6542db93",
                 "F-GATE-4 remains open for F1 (unpublished R17-R22 / FROZEN drift) but is not re-opened here"],
    }
    (ROOT / CHECKPOINT).write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    out = ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl"
    with out.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"proposal": PROPOSAL, "proposal_sha256": ph,
                      "events": [e["event_id"] for e in events],
                      "checkpoint": CHECKPOINT,
                      "outbox_sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
