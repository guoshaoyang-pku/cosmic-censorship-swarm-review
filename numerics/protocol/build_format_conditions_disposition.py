#!/usr/bin/env python3
"""Worker-14 (deepseek-flash-14) format-condition disposition builder.

Class-bound task (proposed, not assigned a new card): N0 / AF-WCC-SCALAR-SPH / G-NUM.
Purpose: dispose the two format conditions of the worker-14 scheme-independence
verdict (astra-numfix-03, scheme_independence_review.md section 10) against the
current on-disk revisions, and audit whether the audit review's protocol verdict
still binds the current protocol hash.

This script measures; it does not decide any gate. Falsifiable: every claim in the
output carries path#sha256 and a re-run re-measures every anchor; a changed anchor
sets anchors_ok=false and invalidates the disposition.

Run:  python3 numerics/protocol/build_format_conditions_disposition.py
Writes: numerics/protocol/format_conditions_disposition.json
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "numerics", "protocol", "format_conditions_disposition.json")

# Anchors this disposition cites. The prefix is what the disposition asserts at
# build time; a differing measurement invalidates the disposition, it is not
# silently rewritten (hash-bound evidence policy).
EXPECTED = {
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2",
    "numerics/protocol/convergence_protocol.md": "6d9b8ab03282",
    "numerics/protocol/scheme_independence_review.md": "2fdb85b23f7d",
    "numerics/protocol/fixed_replication_verdict.json": "dcad962324e3",
    "numerics/tests/n0_order_4rung.json": "c88146a1375c",
    "artifacts/numerics/n0/lead_4rung_replication.json": "a1f04d2a3cb4",
    "reviews/G-NUM-protocol-review.json": "66a905f5afef",
    "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json": "6542db93eebc",
    "numerics/tests/n0_gate_proposal.json": "a1109b32cf16",
    "artifacts/numerics/n0/n0_gate_proposal_lead.json": "bfce1460fafa",
    "numerics/tests/flat_wave_replication.py": "8ade1cdc163e",
    "numerics/tests/selfgravity_lock_guard.py": "7535ec84ac9c",
    "numerics/tests/replication_triage.md": "f27a253ec928",
}


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def measure_anchors() -> tuple[dict, bool]:
    anchors = {}
    ok = True
    for rel, prefix in EXPECTED.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            anchors[rel] = {"exists": False, "expected_prefix": prefix, "match": False}
            ok = False
            continue
        digest = sha256(p)
        match = digest.startswith(prefix)
        ok = ok and match
        anchors[rel] = {
            "exists": True,
            "sha256": digest,
            "sha256_prefix": digest[:16],
            "expected_prefix": prefix,
            "match": match,
        }
    return anchors, ok


def locate(text: str, needle: str) -> dict:
    """Return 1-based line of the first literal occurrence, or -1."""
    idx = text.find(needle)
    if idx < 0:
        return {"present": False}
    line = text.count("\n", 0, idx) + 1
    return {"present": True, "line": line}


def main() -> int:
    os.chdir(ROOT)
    anchors, anchors_ok = measure_anchors()

    lead_protocol = read_text("numerics/CONVERGENCE_PROTOCOL.md")
    worker_protocol = read_text("numerics/protocol/convergence_protocol.md")
    addendum = json.load(open("numerics/tests/n0_order_4rung.json"))
    lead_addendum = json.load(open("artifacts/numerics/n0/lead_4rung_replication.json"))
    fixed_raw = read_text(
        "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
    )
    audit_review = json.load(open("reviews/G-NUM-protocol-review.json"))
    registry = json.load(open("runtime/state/artifact_hashes.json"))
    research_map = json.load(open("research_map/research_map.json"))
    registry_blob = json.dumps(registry)
    registry_sha = sha256("runtime/state/artifact_hashes.json")
    map_sha = sha256("research_map/research_map.json")

    # ---- lead protocol rev2 textual locators (C1, C2, C3) -------------------
    lead_c1_r4 = locate(lead_protocol, "**R4 — no cross-scheme functional gate.**")
    lead_c1_diag = locate(lead_protocol, "allowed only as a labelled *mismatch diagnostic*")
    lead_c3_delta = locate(lead_protocol, "**Order carries an uncertainty (R5).**")
    lead_c3_rule = locate(lead_protocol, "max(0.25, sqrt(delta_A^2 + delta_B^2))")
    lead_r5a_norm = locate(lead_protocol, "names the error norm")
    lead_c2_four = locate(lead_protocol, "**At least four resolutions for an order-certification claim**")
    lead_c2_diag = locate(lead_protocol, "three rungs = supporting diagnostic")
    lead_rev2 = locate(lead_protocol, "**rev 2 — 2026-09-12")
    lead_rev3 = locate(lead_protocol, "**rev 3 — 2026-09-12")
    lead_rev2_scheme_own = locate(
        lead_protocol, "Each scheme is judged on its own declared invariant"
    )

    # ---- worker-14 protocol revision (my assigned artifact) -----------------
    wp_r4 = locate(worker_protocol, "scheme A's functional is never a pass/fail")
    wp_t7 = locate(worker_protocol, "order uncertainty")
    wp_norm = locate(worker_protocol, "\(L2 integral")

    # ---- 4-rung addendum measurements (R5 delta carrier) --------------------
    dr_values = addendum.get("config", {}).get("dr_values", [])
    study_checks = []
    for study in addendum.get("studies", []):
        se = study.get("least_squares_se")
        phr = study.get("pair_half_range")
        delta = study.get("delta")
        consistent = (
            se is not None
            and phr is not None
            and delta is not None
            and abs(delta - max(se, phr)) <= 1e-12
        )
        study_checks.append(
            {
                "scheme": study.get("scheme"),
                "n_rungs": len(study.get("rows", [])),
                "delta": delta,
                "least_squares_se": se,
                "pair_half_range": phr,
                "delta_equals_max_se_phr": consistent,
                "monotone": study.get("monotone"),
            }
        )
    pairwise = addendum.get("pairwise_agreement_R5", [])
    addendum_delta_ok = (
        len(dr_values) == 4
        and all(s["n_rungs"] == 4 for s in study_checks)
        and all(s["delta_equals_max_se_phr"] for s in study_checks)
        and bool(pairwise)
        and all(p.get("agree") is True for p in pairwise)
    )
    provenance = addendum.get("provenance", {})
    addendum_pin_ok = (
        provenance.get("controller_verified_run_sha256")
        == anchors["runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"].get("sha256")
        and provenance.get("frozen_module_sha256")
        == anchors["numerics/tests/flat_wave_replication.py"].get("sha256")
    )
    lead_pairs = lead_addendum.get("agreement_pairs", [])
    lead_4rung_ok = len(lead_addendum.get("studies", [])) == 3 and bool(lead_pairs) and all(
        p.get("agree") is True for p in lead_pairs
    )

    # ---- FIXED run output: does it carry delta / norm? ----------------------
    fixed_has_delta = any(
        token in fixed_raw
        for token in ("delta", "standard_error", "pair_half_range", "least_squares")
    )
    fixed_has_harness = "harness_evaluation" in fixed_raw or "invariant_gate_calibration" in fixed_raw

    # ---- review binding audit ----------------------------------------------
    reviewed_prefix = audit_review.get("artifact_sha256", "")[:16]
    current_protocol_prefix = anchors["numerics/CONVERGENCE_PROTOCOL.md"]["sha256_prefix"]
    binding_drift = reviewed_prefix != current_protocol_prefix
    map_gate = next(g for g in research_map["gates"] if g["gate_id"] == "G-NUM")
    map_unmet = list(map_gate.get("unmet", []))
    map_review_ids = {r.get("event_id") for r in research_map.get("reviews", [])}
    audit_review_recorded = "audit-review-20260912T0009-gnum-protocol" in map_review_ids
    map_evidence_refs = map_gate.get("evidence_refs", [])
    map_pinned_protocol_prefixes = [
        ref.split("#", 1)[1][:16]
        for ref in map_evidence_refs
        if ref.startswith("numerics/CONVERGENCE_PROTOCOL.md#")
    ]
    map_pins_current_protocol = current_protocol_prefix in map_pinned_protocol_prefixes

    # ---- registration (C4) and lock ----------------------------------------
    fixed_registered = anchors[
        "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
    ].get("sha256", "")[:16] in registry_blob
    current_protocol_registered = current_protocol_prefix in registry_blob
    solver_dir_absent = not os.path.isdir("numerics/spherical_solver")
    lock = research_map.get("numerics_lock", {})

    now = datetime.datetime.now().astimezone()
    artifact_id = "w14-fc-disposition-" + now.strftime("%Y%m%dT%H%M%S%z")

    disposition = {
        "schema": "w14/format-conditions-disposition/v1",
        "artifact_id": artifact_id,
        "artifact": "numerics/protocol/format_conditions_disposition.json",
        "author": "deepseek-flash-14",
        "actor": "deepseek-flash-14",
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "assignment_context": {
            "direct_assignments_for_this_actor": [
                "asg-2026-09-11-N0-deepseek-flash-14-23",
                "astra-adj2-03-assignment",
                "astra-numfix-03",
            ],
            "new_card_for_this_artifact": None,
            "basis": (
                "no unread assignment exists in comms/inbox/deepseek-flash-14.jsonl; "
                "this is the residual named in the G-NUM proposal condition "
                "('the two format conditions of worker 14's section 10 verdict are "
                "dispositioned as recorded in worker14_verdict') and is emitted as a "
                "proposed, artifact-backed task, not as an assigned completion"
            ),
            "supersedes": None,
        },
        "anchors_ok": anchors_ok,
        "anchors": anchors,
        "map_sha256": map_sha,
        "registry_sha256": registry_sha,
        "section_10_format_conditions": {
            "FC-i-r5-delta-in-fit-record": {
                "statement": (
                    "Section 10 condition (i): the run output must carry delta in the fit "
                    "record (R5); at verdict time it was supplied only by the post-hoc "
                    "verification."
                ),
                "status": "partially_met_addendum_carries_delta_run_output_does_not",
                "measured": {
                    "fixed_run_has_delta_or_fit_uncertainty_field": fixed_has_delta,
                    "worker_4rung_addendum_has_delta_and_norm": addendum_delta_ok,
                    "worker_4rung_provenance_pins_fixed_run_and_frozen_script": addendum_pin_ok,
                    "lead_4rung_replication_agrees": lead_4rung_ok,
                    "worker_4rung_studies": study_checks,
                    "worker_pairwise_agreement_R5": pairwise,
                },
                "met_at": [
                    "numerics/tests/n0_order_4rung.json (4 rungs, per-scheme delta = max(SLR SE, pair half-range), all pairs agree)",
                    "artifacts/numerics/n0/lead_4rung_replication.json (independent lead driver, all pairs agree)",
                    "numerics/protocol/convergence_protocol.md T7/FC9 (delta required, norm named)",
                    "numerics/CONVERGENCE_PROTOCOL.md rev3 section 3.2 (>= 4 rungs for an "
                    "order-certification claim) and section 3.8 (R5, R5a, agreement floor)",
                ],
                "not_met_at": [
                    "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#6542db93 "
                    "ships fit slopes without delta/standard error/pair half-range "
                    "(verified by string absence in the pinned JSON; audit finding C3)"
                ],
                "residual_owner": (
                    "lead-numerics: either cite the 4-rung addendum delta in any acceptance "
                    "statement that quotes the FIXED fit, or re-issue the run record with delta; "
                    "lead-audit: record which of the two the G-NUM review accepts"
                ),
            },
            "FC-ii-harness-functional-labelled-cross-check": {
                "statement": (
                    "Section 10 condition (ii): the harness leapfrog functional must be "
                    "demoted to a labelled cross-check (R4), not a scheme-independent gate."
                ),
                "status": "met_in_both_protocol_revisions_at_current_hashes",
                "measured": {
                    "lead_protocol_R4_rule": lead_c1_r4,
                    "lead_protocol_mismatch_diagnostic": lead_c1_diag,
                    "lead_protocol_own_invariant_rule": lead_rev2_scheme_own,
                    "worker_protocol_R4_rule": wp_r4,
                    "fixed_run_retains_harness_gate_block": fixed_has_harness,
                },
                "met_at": [
                    "numerics/CONVERGENCE_PROTOCOL.md rev3 section 4.1 R4 and section 6(b) (current hash)",
                    "numerics/protocol/convergence_protocol.md section 4 R4 / T4a (current hash)",
                ],
                "residual_owner": (
                    "lead-numerics: the FIXED run JSON still contains an "
                    "invariant_gate_calibration/harness_evaluation block whose PASS is on the "
                    "leapfrog functional; any downstream reader must treat it as the labelled "
                    "cross-check only. Report-writer relabel is the only mechanical residue."
                ),
            },
        },
        "review_binding_audit": {
            "finding": (
                "The audit protocol review binds a superseded, pre-rev2 protocol revision: "
                "reviews/G-NUM-protocol-review.json records artifact_sha256="
                + str(audit_review.get("artifact_sha256"))
                + ", while numerics/CONVERGENCE_PROTOCOL.md on disk is "
                + anchors["numerics/CONVERGENCE_PROTOCOL.md"]["sha256"]
                + " (rev3, which textually adopts C1, C2 and C3). The verdict 'revise' "
                "therefore cannot bind the current revision, no accepting verdict is "
                "invalidated by the rev2/rev3 writes, and the map's G-NUM evidence_refs "
                "still pin " + str(map_pinned_protocol_prefixes) + " (rev2), not the "
                "current revision. The remaining G-NUM protocol criterion is a fresh "
                "independent review bound to the current hash."
            ),
            "review_verdict": audit_review.get("verdict"),
            "review_score": audit_review.get("score"),
            "reviewed_protocol_sha256": audit_review.get("artifact_sha256"),
            "current_protocol_sha256": anchors["numerics/CONVERGENCE_PROTOCOL.md"]["sha256"],
            "binding_drift": binding_drift,
            "map_pinned_protocol_prefixes": map_pinned_protocol_prefixes,
            "map_pins_current_protocol_in_gate_evidence": map_pins_current_protocol,
            "review_recorded_in_map": audit_review_recorded,
            "revision_log_locators": {
                "rev2": lead_rev2,
                "rev3_closes_C2": lead_rev3,
            },
            "c_item_textual_status_in_current_revision": {
                "C1_scheme_appropriate_invariant": "addressed: section 4.1 R1-R4 + section 6(b)"
                if lead_c1_r4.get("present") and lead_rev2_scheme_own.get("present")
                else "not located",
                "C2_four_resolutions": (
                    "addressed in rev3: section 3.2 now requires >= 4 rungs for an "
                    "order-certification claim; three rungs demoted to supporting diagnostic"
                    if lead_c2_four.get("present") and lead_c2_diag.get("present")
                    else "not located"
                ),
                "C3_fit_uncertainty": "addressed: section 3.8 R5/R5a + agreement rule"
                if lead_c3_delta.get("present") and lead_c3_rule.get("present")
                else "not located",
                "C4_registration": (
                    "open, controller-side: fixed-run hash registered="
                    + str(fixed_registered)
                    + ", current protocol hash registered="
                    + str(current_protocol_registered)
                ),
            },
            "required_next_step": (
                "lead-audit re-reviews numerics/CONVERGENCE_PROTOCOL.md at the current hash "
                + current_protocol_prefix
                + " (astra-numfix-04 / astra-n0add-02); this artifact is not that review and "
                "does not self-review."
            ),
        },
        "gnum_unmet_disposition": [
            {
                "map_bullet": "independent numerical-protocol review is not recorded (nobody may self-review)",
                "status": "recorded_but_binds_superseded_hash",
                "evidence": [
                    "reviews/G-NUM-protocol-review.json#"
                    + anchors["reviews/G-NUM-protocol-review.json"]["sha256_prefix"],
                    "research_map/research_map.json#G-NUM-reviews",
                ],
                "owner": "lead-audit",
            },
            {
                "map_bullet": "cnfem triage from the N0 adjudication is not closed: fix with root cause, or exclude with evidence",
                "status": "evidence_closed_root_cause_and_fix_on_disk_pending_gate_verdict",
                "evidence": [
                    "numerics/tests/n0_gate_proposal.json#"
                    + anchors["numerics/tests/n0_gate_proposal.json"]["sha256_prefix"],
                    "numerics/tests/replication_triage.md#"
                    + anchors["numerics/tests/replication_triage.md"]["sha256_prefix"],
                ],
                "owner": "lead-audit / astra",
            },
            {
                "map_bullet": "the replication harness invariant functional is leapfrog-specific; a scheme-agnostic check or relabelling is required",
                "status": "protocol_text_met_report_label_residual",
                "evidence": [
                    "numerics/CONVERGENCE_PROTOCOL.md#"
                    + anchors["numerics/CONVERGENCE_PROTOCOL.md"]["sha256_prefix"]
                    + " section 4.1 R4",
                    "numerics/protocol/convergence_protocol.md#"
                    + anchors["numerics/protocol/convergence_protocol.md"]["sha256_prefix"]
                    + " R4",
                ],
                "owner": "lead-numerics",
            },
            {
                "map_bullet": "the audit lead asks for a 4th resolution before the order claim is accepted",
                "status": "supplied_and_protocol_rev3_requires_4_rungs_unreviewed",
                "evidence": [
                    "numerics/tests/n0_order_4rung.json#"
                    + anchors["numerics/tests/n0_order_4rung.json"]["sha256_prefix"],
                    "artifacts/numerics/n0/lead_4rung_replication.json#"
                    + anchors["artifacts/numerics/n0/lead_4rung_replication.json"]["sha256_prefix"],
                ],
                "owner": "lead-audit (review) / lead-numerics (proposal)",
            },
            {
                "map_bullet": "cnfd own-energy drift 6.6e-8 has no principled threshold justification",
                "status": "superseded_by_R1_R2_own_functionals_label_remains_cross_check",
                "evidence": [
                    "numerics/protocol/fixed_replication_verdict.json#"
                    + anchors["numerics/protocol/fixed_replication_verdict.json"]["sha256_prefix"],
                    "numerics/protocol/scheme_independence_review.md#"
                    + anchors["numerics/protocol/scheme_independence_review.md"]["sha256_prefix"]
                    + " section 10 Q1",
                ],
                "owner": "lead-audit / astra",
            },
        ],
        "registration_and_lock": {
            "fixed_run_registered_in_artifact_hashes": fixed_registered,
            "current_protocol_registered_in_artifact_hashes": current_protocol_registered,
            "registry_sha256": registry_sha,
            "numerics_lock_state": lock.get("state"),
            "spherical_solver_dir_absent": solver_dir_absent,
            "lock_guard_present": anchors["numerics/tests/selfgravity_lock_guard.py"]["exists"],
        },
        "remaining_open_items": [
            "lead-audit re-review of numerics/CONVERGENCE_PROTOCOL.md at the current hash "
            + current_protocol_prefix
            + " (G-NUM criterion C8; nobody may self-review)",
            "controller registration of runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#"
            + anchors["runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"]["sha256_prefix"]
            + " and of the current protocol hash in runtime/state/artifact_hashes.json (C4)",
            "lead-numerics disposition of FC-i: cite the 4-rung addendum delta or re-issue the FIXED run record with delta",
            "map gates.G-NUM.unmet list is stale relative to the 00:07-00:10 evidence; controller ingest + gate application required",
            "G-NUM verdict and any N0 completion remain with astra; N1 stays locked",
        ],
        "falsifiers": [
            "F-D1: re-running this builder finds any anchor whose sha256 no longer matches its recorded value -> the whole disposition is void and must be rebuilt.",
            "F-D2: a protocol revision drops R1-R5a or re-promotes the harness functional to a pass/fail gate -> FC-ii status is withdrawn.",
            "F-D3: the 4-rung addendum is shown to lack delta, to have non-monotone schemes, or to have a pairwise |dp| above max(0.25, sqrt(dA^2+dB^2)) -> FC-i 'met_at addendum' is withdrawn.",
            "F-D4: a re-issued FIXED run at a new hash carries delta and a labelled harness cross-check -> FC-i/FC-ii become met_at the run output as well; the residual owners close.",
            "F-D5: this artifact is read as a G-NUM verdict, an A1 audit review, an N0 completion, or a physics claim -> that reading is invalid by construction; it contains no verdict and no self-pass.",
        ],
        "not_claimed": [
            "no G-NUM verdict and no gate self-pass",
            "no N0 completion and no N1 release; numerics_lock stays LOCKED",
            "not the independent audit review of the protocol (astra-numfix-04); this artifact is worker-level and may not self-review",
            "no theorem, no cosmic-censorship claim, no physics interpretation; flat-space numerical evidence only",
            "no edit of any other agent's artifact",
        ],
        "reproduction": "python3 numerics/protocol/build_format_conditions_disposition.py",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cwd": ROOT,
        },
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(disposition, fh, indent=2, sort_keys=True)
        fh.write("\n")

    digest = sha256(OUT)
    print("wrote", OUT)
    print("sha256", digest)
    print("anchors_ok", anchors_ok)
    print("FC-i addendum_delta_ok", addendum_delta_ok, "| pin_ok", addendum_pin_ok)
    print("FC-ii lead_c1_r4", lead_c1_r4, "| worker_r4", wp_r4)
    print("binding_drift", binding_drift, "| fixed_registered", fixed_registered)
    return 0 if anchors_ok else 1


if __name__ == "__main__":
    sys.exit(main())
