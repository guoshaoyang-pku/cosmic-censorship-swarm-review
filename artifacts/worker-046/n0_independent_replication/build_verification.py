#!/usr/bin/env python3
"""Build the hash-chained verification report for W046-N0-INDEP-REPL-01.

Reads results.json (written by independent_replication.py), re-checks the hash guards and the
pre-registered acceptance, recomputes the published-vs-independent comparisons from the two
JSON files, and emits verification.json. Fails closed (exit 2) if the run verdict is not
REPRODUCED, if any acceptance criterion is false, or if any pinned input hash has moved.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

PINS = {
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/n0_order_4rung.json":
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    res = json.loads((HERE / "results.json").read_text())
    if res["verdict"] != "REPRODUCED" or not all(res["acceptance"].values()):
        print("refusing to emit a verification report for a non-REPRODUCED run")
        return 2
    guard = {rel: {"pinned": want, "measured": sha256(REPO / rel),
                   "match": sha256(REPO / rel) == want} for rel, want in PINS.items()}
    if not all(v["match"] for v in guard.values()):
        print("hash guard moved; report void")
        return 2

    pub = json.loads((REPO / "numerics/tests/n0_order_4rung.json").read_text())
    pub_err = {st["scheme"]: [r["l2_error"] for r in st["rows"]] for st in pub["studies"]}
    sec_err = [r["l2_error_u"] for r in res["secondary_u_mol"]["rows"]]
    ratios = [a / b for a, b in zip(sec_err, pub_err["lffd"])]

    report = {
        "artifact": "artifacts/worker-046/n0_independent_replication/verification.json",
        "actor": "worker-046",
        "task_id": "W046-N0-INDEP-REPL-01",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "conclusion_type": "numerical_evidence",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "role": "bounded execution worker (no gate authority)",
        "verdict": "REPRODUCED",
        "verdict_scope": "the published N0 order-2 claim survives an independent implementation "
                         "that shares none of the r*phi reduction / Dirichlet-origin / Taylor-start "
                         "/ leapfrog axes of the published replication module",
        "acceptance": res["acceptance"],
        "headline": {
            "primary_sph_fv_fit_order": res["primary_sph_fv"]["fit_order"],
            "primary_sph_fv_delta_r5": res["primary_sph_fv"]["delta_r5"],
            "primary_sph_fv_pair_orders": res["primary_sph_fv"]["pair_orders"],
            "secondary_u_mol_fit_order": res["secondary_u_mol"]["fit_order"],
            "secondary_u_mol_delta_r5": res["secondary_u_mol"]["delta_r5"],
            "c1_first_order_control": res["controls"]["C1_first_order"]["fit_order"],
            "c2_exact_injection_error": res["controls"]["C2_exact_injection"]["l2_error_phi"],
            "c3_time_tol_relative_change": res["controls"]["C3_time_tolerance"]["relative_change"],
            "c4_pulse_variant_fit_order": res["controls"]["C4_pulse_variant"]["fit_order"],
            "c4_pulse_variant_delta_r5": res["controls"]["C4_pulse_variant"]["delta_r5"],
            "published_orders": {s: st["fit_order"] for s, st in
                                 res["published_comparison"]["published_studies"].items()},
        },
        "published_agreement": {
            "primary_vs_all_published": res["published_comparison"]["primary_vs_all_published"],
            "secondary_vs_published_lffd": res["published_comparison"]["secondary_vs_lffd"],
            "r5_rule": "|dp| <= max(0.25, sqrt(delta_A^2 + delta_B^2)); R5 definitions pinned "
                       "against the published lffd row before the study ran",
        },
        "absolute_error_ratio_secondary_over_published_lffd": {
            "per_rung": [round(r, 6) for r in ratios],
            "note": "same variable u=r*phi and same spatial stencil family, different time "
                    "integrator (DOP853 vs leapfrog) and start; a constant ~1.30 ratio is "
                    "consistent with the published absolute errors being reproduced up to the "
                    "leapfrog temporal-error factor. Not an equality claim.",
        },
        "hash_chain": {
            "independent_replication.py": sha256(HERE / "independent_replication.py"),
            "results.json": sha256(HERE / "results.json"),
            "README.md": sha256(HERE / "README.md"),
            "pinned_inputs": guard,
        },
        "method": {
            "independence_axes": ["space discretisation (cell-centred finite volume flux form "
                                  "in the unreduced field phi vs centred differences in u=r*phi)",
                                  "origin treatment (zero regularity flux vs Dirichlet u(0)=0)",
                                  "time integration (DOP853 vs leapfrog / Crank-Nicolson)",
                                  "start procedure (exact velocity, no Taylor bootstrap)",
                                  "error-norm and fit implementation (rewritten; R5 definitions "
                                  "pinned against the published lffd row)"],
            "shared_axes": ["PDE and exact pulse family", "domain, t_end, rung set, CFL-free "
                            "refinement ratio", "error-norm formula sqrt(sum e^2 dr)"],
            "rng": "none (deterministic)",
            "runtime_seconds": res["runtime_seconds"],
            "environment": res["environment"],
        },
        "reviewer_instructions": [
            "Re-measure sha256 of independent_replication.py and results.json; any drift voids "
            "this report.",
            "Re-run `python3 independent_replication.py` and confirm verdict REPRODUCED and the "
            "hash guards on the three pinned inputs.",
            "An accept here is evidence for the G-NUM criterion 'N0 convergence order measured "
            "AND independently replicated'; it is not a gate verdict and does not release "
            "numerics_lock.",
        ],
        "not_claimed": res["not_claimed"],
        "falsifier": res["falsifier"],
    }
    (HERE / "verification.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print("verification.json written; sha256 =", sha256(HERE / "verification.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
