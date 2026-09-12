#!/usr/bin/env python3
"""Emit worker-067's G-NUM protocol review: review.json, README.md, outbox events,
runtime/state checkpoint.  Run from the swarm root."""
import hashlib
import json
import os
import time

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = os.path.join(ROOT, "artifacts/worker-067/g_num_protocol_review")
PROTO = "numerics/CONVERGENCE_PROTOCOL.md"


def sha(p):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, p), "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ts():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def short(h):
    return h[:12]


log = json.load(open(os.path.join(HERE, "verification_log.json")))
proto_hash = log["hash_window"]["t1_hashes"][PROTO]
vhash = sha("artifacts/worker-067/g_num_protocol_review/verification_log.json")
now = ts()
stamp = time.strftime("%Y%m%dT%H%M%S")

reviewed = {
    p: log["hash_window"]["t1_hashes"][p]
    for p in log["hash_window"]["t1_hashes"]
    if p != PROTO
}
reviewed[PROTO] = proto_hash
reviewed["numerics/tests/lead_calibration.py"] = sha("numerics/tests/lead_calibration.py")

# ---- findings -------------------------------------------------------------
F1 = {
    "id": "F1",
    "severity": "major",
    "blocks_accept": True,
    "title": "Protocol section 3.4 forbids the very runs its own certified order claim uses",
    "statement": (
        "Section 3.4 states spatial order is measured with a fixed small dt (1e-4) and that "
        "'dt proportional to h runs are reported as mixed-order and never quoted as spatial'. "
        "The gate proposal's certified claim is the SPATIAL second-order result obtained from "
        "constant-CFL runs (dt proportional to h): the 4-rung addendum rows have cfl=0.5 and "
        "dt=0.1/0.05/0.025/0.0125, and the canonical five-rung studies run at cfl=0.25. No "
        "fixed-dt=1e-4 order study exists for schemes A/B; the only 1e-4 path is the reference "
        "Cartesian MMS study in numerics/tests/lead_calibration.py:95. As written, the protocol "
        "does not authorise the evidence it cites for order certification."
    ),
    "protocol_evidence": [
        "numerics/CONVERGENCE_PROTOCOL.md#%s lines 58-60 (section 3.4)" % short(proto_hash),
        "numerics/tests/n0_order_4rung.json#%s config.cfl=0.5, dr_values=[0.2,0.1,0.05,0.025]"
        % short(reviewed["numerics/tests/n0_order_4rung.json"]),
        "numerics/tests/n0_gate_proposal.json#%s certified_order_claim.statement ('the spatial "
        "discretisation is second order ... cfl=0.5')" % short(reviewed["numerics/tests/n0_gate_proposal.json"]),
        "numerics/tests/lead_calibration.py#%s:95 study_cartesian_mms(..., dt=1e-4) -- reference "
        "MMS only" % short(reviewed["numerics/tests/lead_calibration.py"]),
    ],
    "purpose_is_met_by_controls": [
        "flat_wave.py --all temporal_control at n=256: l2(cfl=0.10)=4.796480180660643e-06 vs "
        "l2(cfl=0.25)=4.796482388024776e-06, relative change 4.6020478238610736e-07 -> temporal "
        "error subdominant; gate G9_temporal_error_subdominant = true (independently re-run)",
        "flat_wave_replication.py --all control dt_probe_dt_eq_dr_pow_half: fit_order 1.0601, "
        "order_drops_below_2 = true -> the study detects temporal contamination when it is made "
        "dominant",
    ],
    "why_not_a_hard_failure": (
        "No measured number changes and no claim is unsupported: temporal subdominance is "
        "directly measured by two controls, and all orders were independently reproduced. The "
        "defect is normative text that contradicts the cited practice."
    ),
    "required_action_rev4": (
        "Scope the fixed-dt sentence to the MMS/reference studies (lead_calibration.py "
        "study_cartesian_mms, dt=1e-4). Replace the blanket prohibition with the actual rule: "
        "pulse/canonical studies refine at constant CFL and must carry (i) a two-CFL temporal "
        "probe with the relative error change tolerance and (ii) a dt-contamination control "
        "(dt=dr^0.5) whose order must fall below the band; both already exist and reproduce."
    ),
    "falsifier": (
        "A 4-rung order-certification study at fixed dt=1e-4 for schemes A/B exists at the "
        "pinned protocol hash, or the pinned protocol text does not contain the quoted "
        "section 3.4 sentence -> F1 is withdrawn."
    ),
}
F2 = {
    "id": "F2",
    "severity": "minor",
    "blocks_accept": False,
    "title": "R2 bound's multiplicative branch (10 x solver_tolerance) is untested and uncapped",
    "statement": (
        "Section 4.1 R2 sets the exact-conservation bound to max(1e-12, 10 x solver_tolerance). "
        "All three schemes report solver_tolerance_reported=null, so only the 1e-12 floor is "
        "exercised. A future scheme declaring a loose tolerance would obtain a bound above the "
        "floor with no stated cap."
    ),
    "required_action_rev4": (
        "Require solver_tolerance to be reported with the R2 claim, or cap the R2 bound at a "
        "stated maximum (e.g. 1e-12 governs unless a tolerance <=1e-13 is declared)."
    ),
    "falsifier": (
        "A scheme with reported solver_tolerance >= 1e-13 passes R2 with own drift > 1e-12 "
        "without a stated cap -> F2 escalates."
    ),
}
F3 = {
    "id": "F3",
    "severity": "minor",
    "blocks_accept": False,
    "title": "Section 6 body retains the superseded 0.35 absolute agreement rule",
    "statement": (
        "Section 6 says the two primary orders must agree within 0.35 absolute, while revision-2 "
        "amendment (a) replaces the agreement test with the R5 rule |pA-pB| <= max(0.25, "
        "sqrt(dA^2+dB^2)). Both sentences are present; the R5 rule governs in practice (all "
        "measured |dp| <= 0.0078)."
    ),
    "required_action_rev4": "Delete or mark the 0.35 sentence as superseded in section 6.",
    "falsifier": (
        "A gate or review quotes the 0.35 clause to accept a pair with |dp| > R5 bound but "
        "<= 0.35 -> F3 escalates."
    ),
}
positive = [
    {
        "id": "P1",
        "title": "C1 closed (scheme-appropriate invariants)",
        "detail": (
            "Section 4.1 R1-R4 present; per-scheme own drifts lffd 3.382842841969448e-15, cnfd "
            "1.1087052118571544e-14, cnfem 2.0438718559608235e-14 all <= 1e-12; F7 not "
            "triggered (harness/own ratios 1.0, 5.947122360242183e6, 414990.2053252012). "
            "Protocol text matches numerics/protocol/fixed_replication_verdict.json."
        ),
    },
    {
        "id": "P2",
        "title": "C2 closed (>= 4 rungs) and re-derived from raw rows",
        "detail": (
            "Section 3.2/3.8/6(e) require >=4 rungs for certification. The 4-rung addendum has 4 "
            "rows per scheme (dr=0.2/0.1/0.05/0.025, ratio 2). A stdlib re-fit of the raw rows "
            "reproduces every declared fit order, LS standard error, pair order and delta to "
            "<1e-9: lffd 1.9966248643204345 +/- 0.0017749505081917638, cnfd 1.9953510343613228 "
            "+/- 0.004172438339596352, cnfem 1.9888598802332438 +/- 0.005142648496443636; all "
            "monotone and inside |p-2|<=0.3; all three pairwise |dp| <= 0.0078 <= R5 floor 0.25."
        ),
    },
    {
        "id": "P3",
        "title": "C3 closed (order uncertainty + named norm)",
        "detail": (
            "Section 3.8 R5/R5a define delta = max(pair-spread half-range, LS standard error) "
            "and require the norm to be named; the 4-rung evidence carries delta and the lead "
            "claim names the L2 integral norm. The historical FIXED run carries no delta, which "
            "is recorded rather than hidden, and the protocol now requires it going forward."
        ),
    },
    {
        "id": "P4",
        "title": "Independent re-execution reproduces the certified claim",
        "detail": (
            "At pinned hashes (flat_wave.py 8b52014dac47f996, flat_wave_replication.py "
            "8ade1cdc163ea420, unchanged before/after), the canonical suite reports 11/11 gates "
            "true and the replication reports ORDER REPRODUCED with cnfd 1.9934777747080437 and "
            "cnfem 1.9863235066828981, bit-for-bit equal to the fixed verdict; determinism "
            "bitwise_equal true; frozen wrong-order report rejected C4_order; positive report "
            "PASS; lock guard PASS with planted-violation selftest FAIL; spherical_solver absent; "
            "N1_BLOCKED. All evidence hashes were stable across the review window."
        ),
    },
]
review = {
    "schema": "worker-review/g-num-protocol/v1",
    "event_id": "w067-review-gnum-protocol-r3-%s" % stamp,
    "event_type": "review",
    "created_at": now,
    "actor": "worker-067",
    "reviewer": "worker-067",
    "reviewer_independence": (
        "bounded breadth worker; author of no numerics/N0 artifact and of no reviewed file; "
        "read-only on every canonical path; wrote only under artifacts/worker-067/; did not "
        "overwrite reviews/G-NUM-protocol-review.json (astra-lead-audit's stale artifact binds "
        "01b2072434cd and is left untouched)"
    ),
    "target_id": "%s#%s" % (PROTO, proto_hash),
    "node_id": "N0",
    "gate": "G-NUM",
    "class_id": "AF-WCC-SCALAR-SPH",
    "verdict": "revise",
    "score": 4.0,
    "hard_failures": [],
    "artifact_sha256": proto_hash,
    "reviewed_artifacts": reviewed,
    "hash_window": {
        "t0": log["t0"],
        "t1": log["t1"],
        "stable": log["hash_window"]["stable"],
        "rechecked_at": now,
        "protocol_sha256_at_recheck": sha(PROTO),
    },
    "summary": (
        "Rev 3 closes audit findings C1, C2 and C3 and every checkable protocol claim was "
        "independently reproduced from the pinned artifacts and re-runs; no hard failure. One "
        "normative text defect remains: section 3.4 forbids dt-proportional-to-h runs as spatial "
        "evidence, while the proposal's certified spatial order claim rests on exactly those "
        "constant-CFL runs (temporal subdominance is demonstrated by controls). Verdict revise "
        "on F1 alone; F2/F3 are minor. C4 (registration) remains controller-side and outside the "
        "protocol text."
    ),
    "criteria_verified": {
        "C1_scheme_appropriate_invariant": "closed - verified against fixed_replication_verdict",
        "C2_four_resolutions": "closed - verified by stdlib re-fit of n0_order_4rung rows",
        "C3_fit_uncertainty_and_named_norm": "closed - delta R5 in text and evidence",
        "C4_registration": "open, controller-side; not a protocol-text defect",
    },
    "findings": [F1, F2, F3] + positive,
    "evidence_verdicts": {
        "order_4rung": "accept",
        "cross_scheme_replication": "accept",
        "negative_controls": "accept",
        "determinism": "accept",
        "lock_guard": "accept",
        "scope_and_conclusion_type": "accept",
        "protocol_text": "revise (F1)",
    },
    "independent_verification": {
        "verification_log": "artifacts/worker-067/g_num_protocol_review/verification_log.json#%s" % short(vhash),
        "verification_log_sha256": vhash,
        "tool": "artifacts/worker-067/g_num_protocol_review/verify_r3.py (stdlib; pinned-hash guards; no canonical writes)",
        "four_rung_refit": "match to <1e-9 on fit, SE, pair orders and delta for all three schemes",
        "reruns": {
            "flat_wave_all_rc": 0,
            "flat_wave_all_gates": "11/11 true",
            "flat_wave_replication_all_rc": 0,
            "replication_verdict": "ORDER REPRODUCED",
            "replication_orders": {"cnfd": 1.9934777747080437, "cnfem": 1.9863235066828981},
            "replication_matches_fixed_verdict": True,
            "lock_guard_rc": 0,
            "lock_guard_verdict": "PASS (N1_BLOCKED, production_allowed false)",
        },
        "controls": {
            "frozen_positive_standard": "PASS (rc 0)",
            "frozen_negative_wrong_order": "FAIL C4_order (rc 1)",
            "canonical_suite_controls": "frozen_in_time, wrong_sign_laplacian, cfl=1.5 rejected; cfl=0.25 not flagged",
            "worker014_negative_controls": "12/12 checks pass at audit tool dbdc6344643d",
        },
        "writes": "artifacts/worker-067/g_num_protocol_review/ only; no canonical file modified",
    },
    "falsifiers": [
        F1["falsifier"],
        F2["falsifier"],
        F3["falsifier"],
        "a rerun at the pinned script hashes that leaves 2.0 +/- 0.3, loses monotonicity, or "
        "pushes a pairwise |dp| above max(0.25, sqrt(dA^2+dB^2)) -> the accept evidence verdicts flip",
        "the protocol hash moving after this review -> this verdict is void (hash-bound)",
    ],
    "next_falsifier": (
        "Publish rev 4 with section 3.4 scoped to the MMS/reference fixed-dt study and the "
        "constant-CFL temporal-control rule stated; then a fresh review at the new hash can "
        "accept. Conversely, any rerun at the pinned hashes in which a scheme leaves the band, "
        "loses monotonicity, or exceeds the R5 bound withdraws the order evidence."
    ),
    "not_claimed": [
        "no G-NUM verdict, no gate self-pass, no node completion (authority: Astra / audit lead)",
        "no physics result; flat-space numerical evidence only",
        "no claim that this worker's review is the binding A1 review; it is independent evidence",
        "no edit to any canonical artifact; reviews/G-NUM-protocol-review.json left untouched",
    ],
}

review_path = "artifacts/worker-067/g_num_protocol_review/review.json"
with open(os.path.join(ROOT, review_path), "w") as f:
    json.dump(review, f, indent=1, sort_keys=True)
review_hash = sha(review_path)

# ---- README ---------------------------------------------------------------
readme = """# worker-067 - independent G-NUM protocol review (C8)

Target: `numerics/CONVERGENCE_PROTOCOL.md` rev 3 at sha256
`%s` (stable across the whole review window).

Verdict: **revise** (score 4.0, no hard failures), on finding F1 only.
C1/C2/C3 are closed and independently reproduced; C4 is controller-side.
F1: section 3.4 says `dt proportional to h` runs are never quoted as spatial, but the
proposal's certified *spatial* order claim is built exactly on constant-CFL runs
(dt = 0.1/0.05/0.025/0.0125 at cfl=0.5). Temporal subdominance is nevertheless
measured (two-CFL probe relative change 4.6e-07; dt=dr^0.5 control collapses the
order to 1.06), so no measured number changes - the normative text needs scoping in
rev 4 (see review.json F1.required_action_rev4).

Reproduce: `python3 artifacts/worker-067/g_num_protocol_review/verify_r3.py`
(stdlib; writes verification_log.json plus the two rerun JSONs in this directory).
""" % proto_hash

with open(os.path.join(HERE, "README.md"), "w") as f:
    f.write(readme)

# ---- outbox events --------------------------------------------------------
events = [
    {
        "event_id": "w067-status-%s-n0-gnum-c8-taken" % stamp,
        "event_type": "status",
        "created_at": now,
        "actor": "worker-067",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "status": "active",
        "hours": 0.4,
        "summary": (
            "Took the open G-NUM criterion C8: independent review of "
            "numerics/CONVERGENCE_PROTOCOL.md at the current hash %s (recorded verdict is stale "
            "at 01b2072434cd). Read-only on canonical paths; verification underway." % short(proto_hash)
        ),
        "evidence_refs": [
            "research_map/research_map.json#controller_gate_audit.G-NUM",
            "%s#%s" % (PROTO, short(proto_hash)),
        ],
        "next_falsifier": F1["falsifier"],
    },
    {
        "event_id": "w067-art-%s-review-json" % stamp,
        "event_type": "artifact",
        "created_at": now,
        "actor": "worker-067",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "artifact_type": "independent_protocol_review",
        "path": review_path,
        "sha256": review_hash,
        "validation_status": "unverified",
        "evidence_refs": [
            "artifacts/worker-067/g_num_protocol_review/verification_log.json#%s" % short(vhash),
        ],
    },
    {
        "event_id": review["event_id"],
        "event_type": "review",
        "created_at": now,
        "actor": "worker-067",
        "reviewer": "worker-067",
        "reviewer_independence": review["reviewer_independence"],
        "target_id": review["target_id"],
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "verdict": "revise",
        "score": 4.0,
        "hard_failures": [],
        "artifact_sha256": proto_hash,
        "findings": [
            "F1 major (blocks accept): protocol section 3.4 forbids dt-proportional-to-h runs as "
            "spatial evidence, yet the proposal's certified spatial order claim uses exactly "
            "those constant-CFL runs; temporal subdominance is measured by controls, so no "
            "number changes - scope the text in rev 4.",
            "F2 minor: R2 bound max(1e-12, 10 x solver_tolerance) has an untested, uncapped "
            "multiplicative branch; all schemes report solver_tolerance=null.",
            "F3 minor: section 6 body keeps the superseded 0.35 agreement clause next to the R5 rule.",
            "P1-P4: C1 closed; C2 closed and re-derived from raw 4-rung rows to <1e-9; C3 closed; "
            "canonical and replication reruns reproduce the certified orders bit-for-bit.",
        ],
        "evidence_refs": [
            review_path + "#" + review_hash,
            "artifacts/worker-067/g_num_protocol_review/verification_log.json#%s" % short(vhash),
            "%s#%s" % (PROTO, short(proto_hash)),
            "numerics/tests/n0_order_4rung.json#%s" % short(reviewed["numerics/tests/n0_order_4rung.json"]),
            "numerics/tests/n0_gate_proposal.json#%s" % short(reviewed["numerics/tests/n0_gate_proposal.json"]),
        ],
        "next_falsifier": review["next_falsifier"],
    },
    {
        "event_id": "w067-status-%s-complete" % stamp,
        "event_type": "status",
        "created_at": now,
        "actor": "worker-067",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "status": "active",
        "hours": 0.6,
        "summary": (
            "Bounded task complete: independent G-NUM C8 review emitted (verdict revise on F1, "
            "no hard failures); C1-C3 closed and reproduced; C4 remains controller-side. "
            "Checkpoint runtime/state/worker-067_checkpoint_1.json. No canonical artifact edited; "
            "N0 stays active and numerics_lock stays LOCKED."
        ),
        "evidence_refs": [
            review_path + "#" + review_hash,
            "runtime/state/worker-067_checkpoint_1.json",
        ],
        "next_falsifier": review["next_falsifier"],
    },
]
out_path = os.path.join(ROOT, "comms/outbox/worker-067.jsonl")
with open(out_path, "w") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

# ---- checkpoint -----------------------------------------------------------
checkpoint = {
    "worker": "worker-067",
    "checkpoint": 1,
    "at": now,
    "instance": "worker-067",
    "task_id": "G-NUM-C8-independent-protocol-review",
    "assignment_source": "research_map.json controller_gate_audit.G-NUM (C8) + lnum-blocker-...accept-review",
    "class_ids": ["AF-WCC-SCALAR-SPH"],
    "node_id": "N0",
    "gate": "G-NUM",
    "verdict": "revise",
    "score": 4.0,
    "hard_failures": [],
    "artifacts": {
        review_path: review_hash,
        "artifacts/worker-067/g_num_protocol_review/verification_log.json": vhash,
        "artifacts/worker-067/g_num_protocol_review/verify_r3.py": sha(
            "artifacts/worker-067/g_num_protocol_review/verify_r3.py"
        ),
        "artifacts/worker-067/g_num_protocol_review/flat_wave_all.json": sha(
            "artifacts/worker-067/g_num_protocol_review/flat_wave_all.json"
        ),
        "artifacts/worker-067/g_num_protocol_review/flat_wave_replication_all.json": sha(
            "artifacts/worker-067/g_num_protocol_review/flat_wave_replication_all.json"
        ),
    },
    "target": {PROTO: proto_hash},
    "outbox_events": [e["event_id"] for e in events],
    "hours_spent_estimate": 0.6,
    "delta": (
        "Independent C8 review of protocol rev 3: fixed-dt vs constant-CFL contradiction found "
        "(F1, blocks accept), two minor findings; C1/C2/C3 closed and independently reproduced."
    ),
    "numerics_lock": "respected: read-only; no N1 work, no numerics/spherical_solver, no canonical writes",
    "authority": "no gate verdict, no node completion, no self-pass; verdict is reviewer evidence only",
    "checkpoint_path": "runtime/state/worker-067_checkpoint_1.json",
    "next_falsifier": review["next_falsifier"],
}
with open(os.path.join(ROOT, "runtime/state/worker-067_checkpoint_1.json"), "w") as f:
    json.dump(checkpoint, f, indent=1, sort_keys=True)

# ---- validate + report ----------------------------------------------------
import sys

sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

for e in events:
    validate_event(json.loads(json.dumps(e)))
print(json.dumps({
    "review_path": review_path, "review_sha256": review_hash,
    "protocol_sha256": proto_hash, "verdict": review["verdict"],
    "verification_log_sha256": vhash,
    "outbox": "comms/outbox/worker-067.jsonl",
    "events": [e["event_id"] for e in events],
    "checkpoint": "runtime/state/worker-067_checkpoint_1.json",
    "events_schema_valid": True,
}, indent=1))
