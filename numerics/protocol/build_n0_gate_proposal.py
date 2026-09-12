#!/usr/bin/env python3
"""Build the N0 / G-NUM adjudication and gate proposal (lead-owned).

Writes ``numerics/tests/n0_gate_proposal.json`` (assigned canonical path,
assignment ``astra-adj2-05-assignment`` / ``astra-indep-1-N0-numerics``).

The proposal integrates:

* controller adjudication of 2026-09-11T23:28+08:00 (N0_adjudication.md);
* worker-13 cnfem triage (``numerics/tests/replication_triage.md``);
* worker-14 scheme-independence review and fixed-run verdict
  (``numerics/protocol/scheme_independence_review.md``,
  ``numerics/protocol/fixed_replication_verdict.json``);
* the lead independent re-run suite and the lead 4-rung replication driver;
* the class-binding re-check against the hash-pinned F0 taxonomy.

It does NOT set a gate verdict.  No numerics artifact is edited here.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# NOTE: `numerics/tests/n0_gate_proposal.json` was declared by two assignments at once
# (astra-numfix-02 -> deepseek-flash-13 and astra-adj2-05/astra-indep-1 -> astra-lead-numerics).
# Worker 13 published its worker-level submission there at 00:08:22; this lead adjudication is
# therefore published at the lead-owned path below and records the collision.
OUT = REPO / "artifacts/numerics/n0/n0_gate_proposal_lead.json"
COLLIDED_PATH = REPO / "numerics/tests/n0_gate_proposal.json"
VERIFY_DIR = REPO / "artifacts/numerics/n0/lead_verify_20260912T000528"
FOUR_RUNG = REPO / "artifacts/numerics/n0/lead_4rung_replication.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path):
    with open(path) as fh:
        return json.load(fh)


def measured(path: Path) -> dict:
    return {"path": str(path.relative_to(REPO)), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    mp = load(REPO / "research_map/research_map.json")
    gates = {g["gate_id"]: g for g in mp["gates"]}
    lock = mp["numerics_lock"]
    node = None
    groups = mp["groups"]
    for g in (groups if isinstance(groups, list) else groups.values()):
        if isinstance(g, dict) and g.get("id") == "numerics":
            for n in g.get("nodes", []):
                if n.get("id") == "N0":
                    node = n

    fw = load(VERIFY_DIR / "02_flat_wave_all.json")
    rc = load(VERIFY_DIR / "05_replication_all.json")
    r4 = load(FOUR_RUNG)
    fv = load(REPO / "numerics/protocol/fixed_replication_verdict.json")
    exit_codes = (VERIFY_DIR / "exit_codes.txt").read_text().strip().splitlines()

    study_summary = []
    for i, s in enumerate(fw["studies"]):
        study_summary.append({
            "index": i,
            "family": s["family"],
            "order_scheme": s["order_scheme"],
            "rungs": [r["n"] for r in s["rows"]],
            "order_l2": s["order_l2"],
            "order_linf": s["order_linf"],
            "order_gate_pass": s["order_gate"]["pass"],
        })

    criteria = [
        {
            "id": "C1_order_measured",
            "criterion": "N0 convergence order measured on closed-form solutions",
            "status": "satisfied",
            "evidence_refs": [
                f"numerics/tests/flat_wave.py#{sha256(REPO / 'numerics/tests/flat_wave.py')[:12]}",
                f"artifacts/numerics/n0/lead_verify_20260912T000528/02_flat_wave_all.json#{sha256(VERIFY_DIR / '02_flat_wave_all.json')[:12]}",
            ],
            "note": "Lead re-run at the pinned revision 8b52014d: --all exit 0, 11/11 gates, "
                    "five rungs per study (n=64..1024 order 2; n=32..512 order 4) and all pair "
                    "orders inside the declared band. Standalone reference calibration also "
                    "passes its own gates.",
        },
        {
            "id": "C2_order_replicated",
            "criterion": "N0 order independently replicated within tolerance",
            "status": "satisfied",
            "evidence_refs": [
                f"numerics/tests/flat_wave_replication.py#{sha256(REPO / 'numerics/tests/flat_wave_replication.py')[:12]}",
                f"numerics/results/flat_wave_replication.json#{sha256(REPO / 'numerics/results/flat_wave_replication.json')[:12]}",
                f"artifacts/numerics/n0/lead_4rung_replication.json#{sha256(FOUR_RUNG)[:12]}",
            ],
            "note": "Independent CN-FD 1.993478, CN-FEM 1.986324, reference-family lffd 1.995770; "
                    "lead 4-rung re-run (adds dr=0.025) gives p=1.9954/1.9889/1.9966 with "
                    "delta<=5.2e-3; all pairs agree under R5. Spread 0.0095 << tolerance 0.35.",
        },
        {
            "id": "C3_cnfem_triage",
            "criterion": "cnfem defect triaged to a root cause (fixed, or excluded with evidence)",
            "status": "satisfied",
            "evidence_refs": [
                f"numerics/tests/replication_triage.md#{sha256(REPO / 'numerics/tests/replication_triage.md')[:12]}",
                f"runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#{sha256(REPO / 'runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json')[:12]}",
            ],
            "note": "Root cause: CN/FEM recurrence used (M - cK) instead of (M + cK) on the "
                    "previous level, i.e. not the trapezoidal rule; amplification root |rho|>1. "
                    "One-line fix, scheme not deleted, gate not relaxed; ORDER DISAGREES -> "
                    "ORDER REPRODUCED (cnfem 1.9863, selftest pass). Lead re-ran the fixed "
                    "script: exit 0, ORDER REPRODUCED.",
        },
        {
            "id": "C4_scheme_appropriate_invariant",
            "criterion": "scheme-agnostic invariant check, or honest relabelling of the harness functional",
            "status": "satisfied",
            "evidence_refs": [
                f"numerics/protocol/scheme_independence_review.md#{sha256(REPO / 'numerics/protocol/scheme_independence_review.md')[:12]}",
                f"numerics/protocol/fixed_replication_verdict.json#{sha256(REPO / 'numerics/protocol/fixed_replication_verdict.json')[:12]}",
                f"numerics/CONVERGENCE_PROTOCOL.md#{sha256(REPO / 'numerics/CONVERGENCE_PROTOCOL.md')[:12]}",
            ],
            "note": "Each scheme now declares and conserves its own structural functional "
                    "(leapfrog 3.38e-15, CN-FD average-acceleration 1.11e-14, CN-FEM 2.04e-14). "
                    "Protocol rev2 adopts R1-R4: the leapfrog staggered energy is a labelled "
                    "cross-check diagnostic on non-leapfrog trajectories, never a pass/fail "
                    "gate for them. The controller's 'own-energy self-check false' item is "
                    "resolved: at the pin that functional was algebraically the leapfrog form "
                    "(gap 2.07e-15).",
        },
        {
            "id": "C5_cnfd_threshold_justified",
            "criterion": "cnfd drift threshold justified (not tuned to pass)",
            "status": "satisfied",
            "evidence_refs": [
                f"numerics/protocol/scheme_independence_review.md#{sha256(REPO / 'numerics/protocol/scheme_independence_review.md')[:12]}",
                f"numerics/CONVERGENCE_PROTOCOL.md#{sha256(REPO / 'numerics/CONVERGENCE_PROTOCOL.md')[:12]}",
            ],
            "note": "No threshold was moved. R3 replaces the fixed 1e-8 with: exact-discrete "
                    "functionals at max(1e-12, 10*solver_tol); other diagnostics must converge "
                    "at order >= p_decl-0.5 over >=3 rungs and reach <=1e-6. The diagnostic "
                    "flip (6.59e-8 at dr=0.05 vs 4.17e-9 at dr=0.025 for the same scheme and "
                    "functional) is recorded as evidence that a single-rung absolute threshold "
                    "is resolution-arbitrary.",
        },
        {
            "id": "C6_fourth_resolution",
            "criterion": "a 4th resolution for the order claim",
            "status": "satisfied",
            "evidence_refs": [
                f"artifacts/numerics/n0/lead_4rung_replication.json#{sha256(FOUR_RUNG)[:12]}",
                f"numerics/protocol/lead_4rung_replication.py#{sha256(REPO / 'numerics/protocol/lead_4rung_replication.py')[:12]}",
            ],
            "note": "Canonical artifact already fits 5 rungs per study at the current revision "
                    "(the audit finding quoted an earlier 3-point configuration). "
                    "The lead 4-rung driver adds dr=0.025 to the acceptance harness set for "
                    "lffd/cnfd/cnfem: errors monotone, pair orders approach 2, p4 within "
                    "0.0089 of 2.0. Worker 13's independently written 4-rung addendum "
                    "(numerics/tests/n0_order_4rung.json) reproduces the same p4 to <1e-6.",
        },
        {
            "id": "C7_class_binding_recheck",
            "criterion": "stale PROVISIONAL binding re-checked against the now-present F0 artifact",
            "status": "satisfied_with_caveat",
            "evidence_refs": [
                f"research_map/formulation_taxonomy.yaml#{sha256(REPO / 'research_map/formulation_taxonomy.yaml')[:12]}",
                f"numerics/results/flat_wave_convergence.json#{sha256(REPO / 'numerics/results/flat_wave_convergence.json')[:12]}",
            ],
            "note": "F0 taxonomy now exists at 66bf917bd368 (G-F0 pending). Re-derived binding: "
                    "N0 is the test-field, fixed-Minkowski flat-space calibration sub-case of "
                    "the matter sector; it does not exercise the Einstein-coupled class "
                    "AF-WCC-SCALAR-SPH (no gravity coupling, no I+/MGHD) and must not be cited "
                    "as an instance. Binding remains provisional because G-F0/G-FORM are "
                    "pending and the taxonomy has no schema node for this class. The canonical "
                    "artifact's inline binding string reflects 'G-F0 review pending', which is "
                    "accurate as of this proposal.",
        },
        {
            "id": "C8_protocol_reviewed_by_audit",
            "criterion": "numerical protocol reviewed by an independent reviewer (not the author)",
            "status": "OPEN",
            "evidence_refs": [
                f"numerics/CONVERGENCE_PROTOCOL.md#{sha256(REPO / 'numerics/CONVERGENCE_PROTOCOL.md')[:12]}",
                "reviews/G-NUM-protocol-review.json (absent)",
            ],
            "note": "EXACT UNMET CRITERION. Assignment astra-numfix-04 (astra-lead-audit) "
                    "declares reviews/G-NUM-protocol-review.json; it does not exist. The lead "
                    "cannot self-review. Protocol was revised (rev2) before that review, so "
                    "the review must target the new hash above.",
        },
    ]

    evidence = {}
    for rel in [
        "numerics/tests/flat_wave.py",
        "numerics/results/flat_wave_convergence.json",
        "numerics/tests/flat_wave_replication.py",
        "numerics/results/flat_wave_replication.json",
        "numerics/tests/replication_triage.md",
        "numerics/tests/lead_calibration.py",
        "artifacts/numerics/n0/lead_calibration_report.json",
        "numerics/CONVERGENCE_PROTOCOL.md",
        "numerics/protocol/scheme_independence_review.md",
        "numerics/protocol/scheme_independence_evidence.json",
        "numerics/protocol/fixed_replication_verdict.json",
        "numerics/gates.py",
        "numerics/blockers.md",
        "research_map/formulation_taxonomy.yaml",
        "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json",
    ]:
        p = REPO / rel
        if p.is_file():
            evidence[rel] = sha256(p)
    evidence["artifacts/numerics/n0/lead_4rung_replication.json"] = sha256(FOUR_RUNG)
    for rel in ["numerics/tests/n0_order_4rung.json", "numerics/tests/n0_gate_proposal.json"]:
        p = REPO / rel
        if p.is_file():
            evidence[rel] = sha256(p)
    for name in ["02_flat_wave_all.json", "05_replication_all.json"]:
        evidence[f"artifacts/numerics/n0/lead_verify_20260912T000528/{name}"] = sha256(VERIFY_DIR / name)

    proposal = {
        "schema_version": "n0-gate-proposal/v1",
        "artifact": "N0 G-NUM adjudication and gate proposal",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "actor": "astra-lead-numerics",
        "authority_note": "Lead proposal only. A lead cannot set a gate verdict; Astra applies "
                          "it, and the protocol review must come from an independent reviewer.",
        "assignments": [
            "astra-adj2-05-assignment (adjudicate replication dispute; propose G-NUM with hashes)",
            "astra-indep-1-N0-numerics (close the N0 adjudication follow-ups)",
        ],
        "path_ownership_note": {
            "collided_path": "numerics/tests/n0_gate_proposal.json",
            "assignments_declaring_it": [
                "astra-numfix-02 -> deepseek-flash-13 (worker-level proposal)",
                "astra-adj2-05-assignment / astra-indep-1-N0-numerics -> astra-lead-numerics",
            ],
            "current_content_of_collided_path": (
                "deepseek-flash-13 submission, sha256 "
                + sha256(COLLIDED_PATH) if COLLIDED_PATH.is_file() else "absent"
            ),
            "resolution": "this lead-level adjudication is published at "
                          "artifacts/numerics/n0/n0_gate_proposal_lead.json; worker-13's "
                          "submission remains on disk with its own sha and is accepted below; "
                          "controller to confirm the N0 node artifact path or rename one card.",
        },
        "node_id": "N0",
        "gate_id": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_binding": "test-field flat-space calibration sub-case; NOT an instance of the "
                         "Einstein-coupled class (provisional: G-F0 pending)",
        "conclusion_type": "numerical_evidence",
        "numerics_lock_at_proposal": {
            "state": lock["state"],
            "required_gates": lock["required_gates"],
            "gate_verdicts": {g: gates[g]["verdict"] for g in lock["required_gates"]},
            "additional_requirements": lock["additional_requirements"],
        },
        "adjudication": {
            "controller_23_28": {
                "verdict": "partly superseded",
                "accepted": [
                    "cnfem order ~0 / drift 1e1 was an implementation defect, not counter-evidence",
                    "a scheme-agnostic invariant functional is required, or affected checks relabelled",
                    "G-NUM is not passed while the protocol review is missing",
                ],
                "corrected": [
                    "the cnfd 'own-energy' check at the pin was algebraically the leapfrog "
                    "staggered energy (relative gap 2.07e-15), so it was not evidence that cnfd "
                    "fails to conserve its own invariant;",
                    "cnfd harness-functional drift 6.59e-8 is below the harness drift_tol=1e-6 "
                    "and recorded harness_gate_would_pass=true, so the adjudication's own "
                    "scheme-dependence falsifier is triggered at the harness threshold;",
                    "the defensible residual is the candidate's 1e-8 single-rung threshold, "
                    "which flips to pass at dr=0.025; adopted fix is R1-R4, not a new constant.",
                ],
                "evidence_refs": [
                    f"runtime/state/controller_verification/N0_adjudication.md#{sha256(REPO / 'runtime/state/controller_verification/N0_adjudication.md')[:12]}",
                    "numerics/protocol/scheme_independence_review.md",
                ],
            },
            "worker_13_cnfem_triage": {
                "verdict": "accept",
                "root_cause": "CrankNicolsonFEM used (M - cK) on the previous level instead of "
                              "(M + cK); the recurrence was not the trapezoidal rule and had an "
                              "amplification root with |rho|>1.",
                "disposition": "fixed at numerics/tests/flat_wave_replication.py#8ade1cdc; "
                               "scheme retained; no gate relaxed; minimal reproduction documented.",
                "lead_verification": "lead re-ran --selftest and --all at the pinned hash: exit 0, "
                                     "ORDER REPRODUCED, cnfem 1.986324.",
            },
            "worker_14_scheme_independence": {
                "verdict": "accept",
                "findings_accepted": [
                    "Q1: per-scheme R1/R2 invariants yes; the harness leapfrog functional is not "
                    "scheme-appropriate for non-leapfrog schemes and is demoted to a labelled "
                    "cross-check (R4);",
                    "Q2: the submitted fixed run carried no delta; R5 uncertainty is supplied "
                    "post-hoc and is admissible for the proposal, but a future report must carry "
                    "delta and name the fitted norm (R5a);",
                    "the replication is re-pinned at script 8ade1cdc, harness 0646de3f, taxonomy "
                    "66bf917bd368, FIXED run 6542db93.",
                ],
                "protocol_action": "adopted as numerics/CONVERGENCE_PROTOCOL.md rev2 (R1-R5a).",
            },
            "worker_13_numfix02_proposal": {
                "verdict": "accept (worker-level submission, consistent with this adjudication)",
                "detail": "deepseek-flash-13 published a worker-level G-NUM proposal at the "
                          "contested path (sha256 "
                          + (sha256(COLLIDED_PATH)[:16] if COLLIDED_PATH.is_file() else "absent")
                          + "), with an independent 4-rung artifact "
                          "numerics/tests/n0_order_4rung.json. Its 4-rung orders "
                          "(lffd 1.996625, cnfd 1.995351, cnfem 1.988860) reproduce this lead's "
                          "independently written driver to <1e-6, and its only unmet item is the "
                          "same C8 protocol review. No gate self-pass is claimed by either.",
            },
            "class_binding_recheck": {
                "verdict": "scope note confirmed; no promotion",
                "detail": "See criterion C7. N0 result may be cited only as the flat-space "
                          "test-field calibration of the matter sector.",
            },
        },
        "claim_corrections": [
            {
                "claim_event": "lnum-claim-a84d21315673a501ee24",
                "issue": "the statement cites the independent replication number 1.9899, which "
                         "averaged the pre-fix (broken) CN-FEM run with CN-FD.",
                "corrected": "independent schemes measure lffd 1.995770, CN-FD 1.993478, "
                             "CN-FEM 1.986324; spread 0.0095 (tolerance 0.35). The qualitative "
                             "claim (independent second-order schemes agree) stands; the number "
                             "must be quoted as the corrected triple.",
            }
        ],
        "lead_independent_reruns": {
            "directory": "artifacts/numerics/n0/lead_verify_20260912T000528",
            "exit_codes": exit_codes,
            "flat_wave_all": {
                "all_gates_pass": fw["all_gates_pass"],
                "gates_passed": sum(1 for v in fw["gates"].values() if v),
                "gates_total": len(fw["gates"]),
                "studies": study_summary,
            },
            "replication_all": {
                "replication_verdict": rc["result"]["replication_verdict"],
                "independent_orders": rc["result"]["independent_orders"],
                "harness_verdicts": [
                    {"scheme": h["scheme"], "verdict": h["verdict"], "order": h["measured_order"]}
                    for h in rc["harness_evaluation"]
                ],
            },
            "four_rung_replication": {
                "per_scheme": {
                    s: {
                        "fit_order_3rung": v["fit_order_3rung"],
                        "fit_order_4rung": v["fit_order_4rung"],
                        "delta": v["uncertainty"]["reported_delta"],
                        "monotone": v["monotone"],
                    }
                    for s, v in r4["studies"].items()
                },
                "agreement_pairs": r4["agreement_pairs"],
            },
            "gates_check": "python3 -m numerics.gates --check exits 3 (N1_BLOCKED) while locked; "
                           "exit 3 is the correct fail-closed outcome, not a failure of N0.",
        },
        "criteria_status": criteria,
        "proposal": {
            "recommended_gate_verdict": "pass_conditional",
            "measured_criteria": "C1-C7 satisfied (C7 with the provisional-binding caveat)",
            "open_item": "C8: independent reviewer verdict on numerics/CONVERGENCE_PROTOCOL.md "
                         f"rev2 #{sha256(REPO / 'numerics/CONVERGENCE_PROTOCOL.md')[:12]} "
                         "(reviews/G-NUM-protocol-review.json absent)",
            "if_the_open_item_closes": "G-NUM can be applied as pass for N0",
            "effect_on_N1": "none: numerics_lock stays locked; G-FORM and G-AUDIT are still "
                            "pending, so even a G-NUM pass does not release N1",
        },
        "falsifiers": [
            "a scheme that passes only because an invariant functional or threshold was retuned "
            "to it (falsified for this proposal: R3/R4 change the criterion, no measured number "
            "was moved, and the flip under refinement is documented);",
            "a cnfem exclusion without a shown root cause (not applicable: fixed and re-verified);",
            "the 4-rung agreement is falsified if a rerun at the pinned hashes gives "
            "|p_A - p_B| > max(0.25, sqrt(delta_A^2 + delta_B^2));",
            "the class-binding note is falsified if F0/F1 add an explicit test-field sub-case "
            "schema node, or if a reviewer shows N0 exercises gravity coupling or I+/MGHD.",
        ],
        "claims_not_made": [
            "no theorem or counterexample; no cosmic-censorship claim",
            "no gate verdict by the lead (proposal only)",
            "no self-review of the protocol",
            "no N1/self-gravity work or code path",
        ],
        "evidence_hashes": evidence,
        "validation_status": "unverified",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"sha256 {sha256(OUT)}")
    rc_out = subprocess.run(
        [sys.executable, "-c",
         "import json,sys;d=json.load(open(sys.argv[1]));"
         "print('criteria:',[(c['id'],c['status']) for c in d['criteria_status']]);"
         "print('recommended:',d['proposal']['recommended_gate_verdict'])",
         str(OUT)],
        capture_output=True, text=True)
    print(rc_out.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
