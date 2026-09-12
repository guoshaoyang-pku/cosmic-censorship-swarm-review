#!/usr/bin/env python3
"""Emit the numerics-lead lifecycle events for the N0 adjudication (append-only outbox).

Deterministic event ids make re-publication idempotent for the ingest bus.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from numerics import events  # noqa: E402

H = events.sha256_file
START = 1789142636.0  # 2026-09-12T00:03:56+08:00 lifecycle start
HOURS = round(max((time.time() - START) / 3600.0, 0.01), 3)

PROPOSAL = "numerics/tests/n0_gate_proposal.json"
FOUR = "artifacts/numerics/n0/lead_4rung_replication.json"
DRIVER = "numerics/protocol/lead_4rung_replication.py"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
BUILDER = "numerics/protocol/build_n0_gate_proposal.py"
TRIAGE = "numerics/tests/replication_triage.md"
SIREVIEW = "numerics/protocol/scheme_independence_review.md"
FIXEDVERDICT = "numerics/protocol/fixed_replication_verdict.json"

emitted = []


def rec(ev):
    emitted.append(ev)
    print(f"  + {ev['event_type']:<16} {ev['event_id']}")


# 1-5. artifacts produced by this lifecycle
rec(events.emit_artifact(
    "N0", "gate_proposal", PROPOSAL, "unverified",
    validation_evidence=[f"{PROPOSAL}#{H(PROPOSAL)[:12]}",
                         "adjudicates worker-13 triage, worker-14 scheme-independence review, "
                         "class-binding re-check, lead re-runs"],
    event_id=events.det_id("artifact", PROPOSAL, H(PROPOSAL))))
rec(events.emit_artifact(
    "N0", "four_rung_replication", FOUR, "unverified",
    validation_evidence=[f"{DRIVER}#{H(DRIVER)[:12]}", "selftest_pass=true at pinned module hash"],
    event_id=events.det_id("artifact", FOUR, H(FOUR))))
rec(events.emit_artifact(
    "N0", "four_rung_driver", DRIVER, "unverified",
    validation_evidence=[f"{FOUR}#{H(FOUR)[:12]}"],
    event_id=events.det_id("artifact", DRIVER, H(DRIVER))))
rec(events.emit_artifact(
    "N0", "convergence_protocol_rev2", PROTOCOL, "unverified",
    validation_evidence=["adopts R1-R5a from " + SIREVIEW,
                         "awaiting independent review: reviews/G-NUM-protocol-review.json"],
    event_id=events.det_id("artifact", PROTOCOL, H(PROTOCOL))))
rec(events.emit_artifact(
    "N0", "proposal_builder", BUILDER, "unverified",
    validation_evidence=[f"{PROPOSAL}#{H(PROPOSAL)[:12]}"],
    event_id=events.det_id("artifact", BUILDER, H(BUILDER))))

# 6-7. lead reviews of the two worker reports (lead is independent of their authors)
rec(events.emit_review(
    f"{TRIAGE}#{H(TRIAGE)[:12]}", "accept", 4.5, [],
    ["root cause shown at implementation level: (M - cK) instead of (M + cK) on the previous "
     "CN level, so the recurrence was not the trapezoidal rule and had an amplification root "
     "with |rho|>1",
     "one-line fix at numerics/tests/flat_wave_replication.py#8ade1cdc; scheme retained, gate "
     "not relaxed; minimal reproduction included",
     "lead re-ran --selftest and --all at the pinned hash: exit 0, ORDER REPRODUCED, cnfem "
     "1.986324 - the failure is closed by fix, not by exclusion"],
    event_id=events.det_id("review", TRIAGE, H(TRIAGE))))
rec(events.emit_review(
    f"{SIREVIEW}#{H(SIREVIEW)[:12]}", "accept", 4.0,
    [],
    ["Q1 answered with a measured matrix: each scheme conserves its own structural functional "
     "to <=2.04e-14; the pinned cnfd 'own' functional was algebraically the leapfrog staggered "
     "energy (gap 2.07e-15), correcting the adjudication",
     "Q2 answered: the submitted fixed run carried no delta; R5 uncertainty supplied post-hoc "
     "and re-measured, all pairs agree",
     "the harness leapfrog functional is correctly demoted to a labelled cross-check (R4); "
     "adopted as CONVERGENCE_PROTOCOL.md rev2",
     "residual: future reports must carry delta and name the fitted norm (R5a) - protocol "
     "condition, not a measured-number change"],
    event_id=events.det_id("review", SIREVIEW, H(SIREVIEW))))

# 8. adjudication claim
rec(events.emit_claim(
    "AF-WCC-SCALAR-SPH",
    "N0 adjudication (flat-space test-field calibration): the 23:24 replication dispute is "
    "closed by a root-caused fix, not an exclusion (CN-FEM sign error; post-fix order 1.986324, "
    "selftest pass). Independent schemes measure lffd 1.995770, CN-FD 1.993478, CN-FEM 1.986324; "
    "the lead 4-rung re-run (dr = 0.2/0.1/0.05/0.025) gives 1.996625/1.995351/1.988860 with "
    "delta <= 5.2e-3 and all pairs agreeing under R5. Each scheme conserves its own structural "
    "invariant to <=2.04e-14; the leapfrog staggered energy is demoted to a labelled cross-check "
    "for non-leapfrog schemes. The prior claim's number 1.9899 averaged the pre-fix broken CN-FEM "
    "run and must be quoted as the corrected triple.",
    "numerical_evidence",
    ["fixed Minkowski background; massless real scalar; l=0; no gravity coupling",
     "class binding is the test-field sub-case, not an instance of AF-WCC-SCALAR-SPH",
     "agreement rule R5: |pA-pB| <= max(0.25, sqrt(dA^2+dB^2))"],
    "a scheme that passes only because a functional or threshold was retuned to it; a cnfem "
    "exclusion without a shown root cause; a 4-rung rerun with pair disagreement above the R5 "
    "floor; F0/F1 adding an explicit test-field schema node that changes the binding",
    [f"{PROPOSAL}#{H(PROPOSAL)[:12]}", f"{FOUR}#{H(FOUR)[:12]}",
     f"{TRIAGE}#{H(TRIAGE)[:12]}", f"{SIREVIEW}#{H(SIREVIEW)[:12]}",
     f"{FIXEDVERDICT}#{H(FIXEDVERDICT)[:12]}",
     "numerics/results/flat_wave_replication.json#298a4d921c22"],
    node_id="N0",
    event_id=events.det_id("claim", PROPOSAL, H(PROPOSAL))))

# 9. gate proposal (lead cannot pass; verdict pending with criteria status)
rec(events.emit_gate(
    "G-NUM", "N0", "pending",
    "C1 order measured: satisfied (11/11 gates, 5 rungs/study at 8b52014d); "
    "C2 independently replicated: satisfied (ORDER REPRODUCED + 4-rung, spread 0.0095 <= 0.35); "
    "C3 cnfem triaged to root cause and fixed: satisfied; "
    "C4 scheme-appropriate invariants / honest relabelling: satisfied (protocol rev2 R1-R4); "
    "C5 cnfd threshold justified without retuning: satisfied (R3; flip under refinement recorded); "
    "C6 4th resolution: satisfied; C7 class-binding re-check vs F0#66bf917bd368: satisfied with "
    "provisional caveat; C8 independent protocol review: OPEN - reviews/G-NUM-protocol-review.json "
    "absent. Recommended: pass once C8 closes; lead does not self-pass.",
    [f"{PROPOSAL}#{H(PROPOSAL)[:12]}", f"{PROTOCOL}#{H(PROTOCOL)[:12]}",
     "numerics/tests/flat_wave.py#8b52014dac47",
     "numerics/tests/flat_wave_replication.py#8ade1cdc163e",
     "artifacts/numerics/n0/lead_4rung_replication.json",
     "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#6542db93eebc"],
    event_id=events.det_id("gate", "G-NUM", PROPOSAL, H(PROPOSAL))))

# 10. exact unmet criterion as a blocker
rec(events.emit_blocker(
    "N0",
    "G-NUM is held at pending by exactly one unmet criterion: the numerical protocol has no "
    "independent accepting review. Assignment astra-numfix-04 (astra-lead-audit) declares "
    "reviews/G-NUM-protocol-review.json; the file does not exist. C1-C7 are satisfied on "
    "artifact-backed evidence (see proposal).",
    "An independent reviewer (not astra-lead-numerics) emits a review event targeting "
    f"numerics/CONVERGENCE_PROTOCOL.md#{H(PROTOCOL)[:12]} rev2 with verdict=accept and cited "
    "sha256, or lists hard failures. Note the protocol was revised to rev2 before that review, "
    "so the old hash is not a valid target.",
    [f"{PROPOSAL}#{H(PROPOSAL)[:12]}", f"{PROTOCOL}#{H(PROTOCOL)[:12]}",
     "reviews/G-NUM-protocol-review.json (absent)"],
    severity="medium",
    event_id=events.det_id("blocker", "C8", PROTOCOL, H(PROTOCOL))))

# 11. resource request for that review
rec(events.emit_resource_request(
    "numerics", 1, 1.0,
    "G-NUM's last open item is an independent protocol review; the lead cannot self-review and "
    "the protocol changed to rev2, so a reviewer must read the new hash.",
    "Either closes G-NUM's last criterion or finds the defect that keeps N1 locked; both are "
    "decision-relevant and cost <=1 agent-hour.",
    f"One reviewer, one verdict on numerics/CONVERGENCE_PROTOCOL.md#{H(PROTOCOL)[:12]} with "
    "cited sha256; no edits by the reviewer.",
    node_id="N0",
    event_id=events.det_id("resource_request", "C8", PROTOCOL, H(PROTOCOL))))

# 12. status
rec(events.emit_status(
    "N0", "active", HOURS,
    "N0 adjudication complete on all measured criteria: cnfem root-caused and fixed (ORDER "
    "REPRODUCED), scheme-appropriate invariants adopted (protocol rev2 R1-R5a), independent "
    "4-rung replication agrees (p4 1.9966/1.9954/1.9889, delta<=5.2e-3), class binding "
    "re-derived vs F0#66bf917bd368 as the test-field calibration sub-case. Gate proposal "
    "pass_conditional: C1-C7 satisfied, C8 (independent protocol review) open. N1 untouched "
    "and locked.",
    [f"{PROPOSAL}#{H(PROPOSAL)[:12]}", f"{FOUR}#{H(FOUR)[:12]}",
     f"{PROTOCOL}#{H(PROTOCOL)[:12]}", "numerics/blockers.md",
     "reviews/G-NUM-protocol-review.json (absent)"],
    "canonical --all stops passing at 8b52014d; a 4-rung rerun at pinned hashes gives pair "
    "disagreement above the R5 floor; the N1 lock guard starts passing while G-FORM/G-AUDIT "
    "are pending; a reviewer rejects the protocol",
    event_id=events.det_id("status", "N0", PROPOSAL, H(PROPOSAL))))

Path(REPO / "artifacts/numerics/lifecycle_events_20260912.jsonl").write_text(
    "\n".join(json.dumps(e, sort_keys=True) for e in emitted) + "\n")
print(f"emitted {len(emitted)} events")
