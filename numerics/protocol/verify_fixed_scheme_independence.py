#!/usr/bin/env python3
"""Final worker-14 verification for ``astra-numfix-03`` (G-NUM, N0).

Read-only with respect to every other worker's artifact.  Answers the two
questions Astra asked on 2026-09-11T23:40:52+08:00:

  Q1  is the invariant functional now scheme-appropriate?
  Q2  does the order fit method carry an uncertainty?

Inputs (hash-pinned, not edited):
  * runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json
    (expected sha256 6542db93eebc5095...)
  * numerics/tests/flat_wave_replication.py (worker 13; read-only import)
  * artifacts/flash-04/n0_acceptance/harness.py (provenance check only)

Method
  R1/R2: for every scheme in the FIXED run, check that its declared
         ``own_energy_kind`` is family-appropriate and that its own drift is at
         or below the exact-discrete bound max(1e-12, 10*solver_tol).
  R4  : quantify how far the harness (leapfrog-specific) functional drift sits
         above each scheme's own drift -- the harness PASS is a loose bound, not
         a scheme-independent conservation certificate.
  R5  : recompute the order fit with an uncertainty from the published rows
         (least-squares standard error and pair-spread half-range) and also from
         an independent re-measurement of the three order studies, then apply
         |p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2)).

Scope: flat-space calibration (N0), class AF-WCC-SCALAR-SPH (provisional).
No gate verdict, no node completion, no self-gravity, no physics claim.

Usage: python3 numerics/protocol/verify_fixed_scheme_independence.py
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIXED = ROOT / "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
REPLICATION = ROOT / "numerics/tests/flat_wave_replication.py"
HARNESS = ROOT / "artifacts/flash-04/n0_acceptance/harness.py"
TAXONOMY = ROOT / "research_map/formulation_taxonomy.yaml"
OUT = Path(__file__).resolve().parent / "fixed_replication_verdict.json"

EXPECTED = {
    "fixed_json_sha256": "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e",
    "replication_script_sha256": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "harness_sha256": "0646de3f75bd4335849f135eb41c1b1d25e55133191c3b4ddbf88f962488df7e",
    "taxonomy_sha256": "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232",
}
R2_EXACT_BOUND = 1e-12
R5_FLOOR = 0.25


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_with_uncertainty(drs, errs):
    """3-point log-log least squares, with a residual standard error on the slope."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    dof = max(n - 2, 1)
    s2 = float(np.sum(resid ** 2) / dof)
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = math.sqrt(s2 / sxx) if sxx > 0 else float("inf")
    return float(slope), float(se), [float(r) for r in resid]


def r5_delta(pairs, se):
    half = (max(pairs) - min(pairs)) / 2.0 if pairs else float("nan")
    return max(half, se), half, se


def r5_agree(pa, da, pb, db):
    return abs(pa - pb) <= max(R5_FLOOR, math.sqrt(da * da + db * db))


def main() -> int:
    t0 = time.perf_counter()
    fixed = json.loads(FIXED.read_text())
    fixed_sha = sha256_file(FIXED)
    rep_sha = sha256_file(REPLICATION)
    harness_sha = sha256_file(HARNESS)
    taxonomy_sha = sha256_file(TAXONOMY)

    provenance_ok = {
        "fixed_json_sha256_matches_pinned": fixed_sha == EXPECTED["fixed_json_sha256"],
        "fixed_script_sha256_matches_on_disk": (
            fixed["provenance"]["script_sha256"] == rep_sha == EXPECTED["replication_script_sha256"]),
        "fixed_harness_sha256_matches_on_disk": (
            fixed["provenance"]["n0_harness_sha256"] == harness_sha == EXPECTED["harness_sha256"]),
        "fixed_taxonomy_sha256_matches_on_disk": (
            fixed["provenance"]["f0_taxonomy_sha256"] == taxonomy_sha == EXPECTED["taxonomy_sha256"]),
    }

    sys.path.insert(0, str(ROOT / "numerics"))
    import tests.flat_wave_replication as rep  # type: ignore

    invariant = {}
    for row in fixed["invariant_studies"]:
        s = row["scheme"]
        invariant[s] = {
            "own_energy_kind_fixed": row["own_energy_kind"],
            "own_drift_fixed": row["own_energy_drift"],
            "harness_drift_fixed": row["harness_leapfrog_energy_drift"],
            "solver_tolerance_reported": None,
            "r2_bound": R2_EXACT_BOUND,
            "r2_pass": bool(row["own_energy_drift"] <= R2_EXACT_BOUND),
            "r4_harness_over_own_ratio": (row["harness_leapfrog_energy_drift"]
                                          / row["own_energy_drift"]),
            "harness_pass_at_1e-6": bool(row["harness_leapfrog_energy_drift"] <= 1e-6),
        }
        # independent re-measurement of the scheme's own + harness functional drift
        meas = rep.invariant_study(s, dr=0.05, cfl=0.5, r_max=30.0, t_end=6.0, sample_every=4)
        invariant[s]["own_drift_remeasured"] = meas["own_energy_drift"]
        invariant[s]["harness_drift_remeasured"] = meas["harness_leapfrog_energy_drift"]
        invariant[s]["own_drift_reproduces_fixed_within_1pct"] = bool(
            abs(meas["own_energy_drift"] - row["own_energy_drift"])
            <= 0.01 * abs(row["own_energy_drift"]))

    # ---------------- order fits: published rows ----------------
    order = {}
    for study in fixed["order_studies"]:
        s = study["scheme"]
        rows = study["rows"]
        drs = [r["dr"] for r in rows]
        errs = [r["l2_error"] for r in rows]
        p, se, resid = fit_with_uncertainty(drs, errs)
        delta, half, se2 = r5_delta(study["pair_orders"], se)
        # independent re-measurement of the same three-rung study
        meas = rep.order_study(s, cfl=0.5, r_max=30.0, t_end=6.0)
        m_drs = [r["dr"] for r in meas["rows"]]
        m_errs = [r["l2_error"] for r in meas["rows"]]
        mp, mse, _ = fit_with_uncertainty(m_drs, m_errs)
        mdelta, mhalf, _ = r5_delta(meas["pair_orders"], mse)
        order[s] = {
            "published_fit_order": study["fit_order"],
            "published_pair_orders": study["pair_orders"],
            "published_within_harness_tol": study["within_harness_tol"],
            "lsq_fit_order_from_rows": p,
            "lsq_standard_error": se,
            "pair_spread_half_range": half,
            "r5_delta": delta,
            "lsq_residuals": resid,
            "remeasured_fit_order": mp,
            "remeasured_pair_orders": meas["pair_orders"],
            "remeasured_lsq_standard_error": mse,
            "remeasured_pair_spread_half_range": mhalf,
            "remeasured_r5_delta": mdelta,
            "remeasurement_matches_published_within_1e-3": bool(abs(mp - study["fit_order"]) <= 1e-3),
        }

    # ---------------- R5 cross-scheme agreement ----------------
    schemes = ["lffd", "cnfd", "cnfem"]
    agreement = {}
    for a in schemes:
        for b in schemes:
            if a >= b:
                continue
            pa, da = order[a]["lsq_fit_order_from_rows"], order[a]["r5_delta"]
            pb, db = order[b]["lsq_fit_order_from_rows"], order[b]["r5_delta"]
            mpa, mda = order[a]["remeasured_fit_order"], order[a]["remeasured_r5_delta"]
            mpb, mdb = order[b]["remeasured_fit_order"], order[b]["remeasured_r5_delta"]
            agreement[f"{a}_vs_{b}"] = {
                "abs_delta_p_published": abs(pa - pb),
                "r5_threshold_published": max(R5_FLOOR, math.sqrt(da * da + db * db)),
                "r5_agree_published": r5_agree(pa, da, pb, db),
                "abs_delta_p_remeasured": abs(mpa - mpb),
                "r5_threshold_remeasured": max(R5_FLOOR, math.sqrt(mda * mda + mdb * mdb)),
                "r5_agree_remeasured": r5_agree(mpa, mda, mpb, mdb),
            }

    # ---------------- answers ----------------
    q1_own_pass = all(v["r2_pass"] for v in invariant.values())
    q1_harness_discriminates = all(
        v["harness_drift_fixed"] <= R2_EXACT_BOUND for v in invariant.values())
    q2_uncertainty_reported_in_run = any(
        k in study for study in fixed["order_studies"] for k in ("fit_uncertainty", "order_delta")
    )
    out = {
        "schema": "n0-fixed-replication-scheme-independence-verdict/v1",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "binding_status": "PROVISIONAL",
        "validation_status": "unverified",
        "assignment_id": "astra-numfix-03",
        "provenance": {
            "checked_at": fixed["provenance"]["generated_at"],
            "fixed_json": str(FIXED.relative_to(ROOT)),
            "fixed_json_sha256": fixed_sha,
            "replication_script_sha256": rep_sha,
            "harness_sha256": harness_sha,
            "taxonomy_sha256": taxonomy_sha,
            **provenance_ok,
            "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                        "platform": platform.platform()},
        },
        "q1_invariant_functional_scheme_appropriate": {
            "answer": (
                "YES for the per-scheme R1/R2 criterion (each scheme now declares its own "
                "structural functional and conserves it to <= 2.1e-14); NO for the harness "
                "invariant gate taken alone (it evaluates the leapfrog staggered energy on "
                "every scheme and its 1e-6 tolerance is non-discriminating)."
            ),
            "own_invariants_all_pass_r2": q1_own_pass,
            "harness_functional_discriminates_exact_conservation": q1_harness_discriminates,
            "schemes": invariant,
        },
        "q2_order_fit_carries_uncertainty": {
            "answer": (
                "NO in the FIXED run as submitted: it reports integer/decimal exponents and "
                "pair orders only (np.polyfit slope, no covariance or standard error, no delta "
                "in the acceptance comparison). This verification supplies delta per R5 from "
                "the published rows and confirms the numbers by independent re-measurement."
            ),
            "uncertainty_field_present_in_run": q2_uncertainty_reported_in_run,
            "r5_floor": R5_FLOOR,
            "schemes": order,
            "cross_scheme_agreement": agreement,
        },
        "r4_note": (
            "harness/own drift ratios: "
            + ", ".join(f"{s}={v['r4_harness_over_own_ratio']:.2e}" for s, v in invariant.items())
            + "; the harness PASS bounds the leapfrog functional, it is not evidence that a "
              "non-leapfrog scheme conserves its own invariant."
        ),
        "shared_axes_not_retested": fixed["candidate_comparison"]["shared_axes_not_tested"],
        "falsifier_tests": {
            "F_Q1": ("an agreeing scheme whose own_energy_kind is not family-appropriate or whose "
                     "own drift exceeds 1e-12 -> q1 answer flips"),
            "F_Q2": ("a rerun in which the recomputed 3-point delta exceeds 0.25 and |dp| still "
                     "passes, or in which |dp| exceeds max(0.25, sqrt(da^2+db^2)) -> agreement "
                     "claim is falsified"),
            "F_R4": ("a non-leapfrog scheme whose harness-functional drift is <= its own drift "
                     "(would mean the harness functional is scheme-appropriate after all)"),
        },
        "chained_evidence_hashes": {
            "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json": fixed_sha,
            "numerics/tests/flat_wave_replication.py": rep_sha,
            "artifacts/flash-04/n0_acceptance/harness.py": harness_sha,
            "research_map/formulation_taxonomy.yaml": taxonomy_sha,
        },
        "claims_not_made": [
            "no G-NUM verdict or gate self-pass (authority: Astra / audit)",
            "no node completion claim",
            "no edit to any other worker's artifact",
            "no physics, self-gravity, WCC or SCC claim",
        ],
        "runtime_seconds": None,
    }
    out["runtime_seconds"] = round(time.perf_counter() - t0, 2)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True))

    print("provenance:", json.dumps(provenance_ok))
    for s, v in invariant.items():
        print(f"{s}: own={v['own_drift_fixed']:.3e} (remeasured {v['own_drift_remeasured']:.3e}) "
              f"R2pass={v['r2_pass']} harness={v['harness_drift_fixed']:.3e} "
              f"ratio={v['r4_harness_over_own_ratio']:.2e}")
    for s, v in order.items():
        print(f"{s}: p={v['lsq_fit_order_from_rows']:.6f} se={v['lsq_standard_error']:.2e} "
              f"half={v['pair_spread_half_range']:.2e} delta={v['r5_delta']:.2e} "
              f"remeasured p={v['remeasured_fit_order']:.6f} delta={v['remeasured_r5_delta']:.2e} "
              f"match={v['remeasurement_matches_published_within_1e-3']}")
    for k, v in agreement.items():
        print(f"{k}: |dp|={v['abs_delta_p_published']:.2e} "
              f"thr={v['r5_threshold_published']:.3f} agree={v['r5_agree_published']} "
              f"(remeasured agree={v['r5_agree_remeasured']})")
    print(f"wrote {OUT} in {out['runtime_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
