#!/usr/bin/env python3
"""Lead control: is the constant-CFL replication ladder a *spatial* order measurement?

WHY THIS EXISTS
  An independent review (worker-067, 2026-09-12T00:22:56) raised a major finding F1:
  `numerics/CONVERGENCE_PROTOCOL.md` section 3.4 says spatial order is measured with a
  fixed small dt and that `dt ~ h` (constant-CFL) runs "are reported as mixed-order and
  never quoted as spatial" -- yet the certified N0 replication claim quotes exactly those
  constant-CFL runs (numerics/tests/n0_order_4rung.json, cfl = 0.5 at every rung) as the
  spatial order.  That is a real internal inconsistency between the protocol of record and
  the claim it is used to certify.

  The project rule is that such a question is settled by a control, not by argument.  This
  driver measures it, read-only, against the frozen replication module.

WHAT IS MEASURED, per scheme (lffd / cnfd / cnfem)
  A. constant-CFL ladder   dr = 0.2/0.1/0.05/0.025, dt = 0.5*dr   (the certified ladder)
  B. fixed-dt ladder       same dr, dt = 1e-3 and 5e-4            (section 3.4 compliant)
  C. temporal refinement   fixed dr in {0.2, 0.05}, dt = cfl*dr / 2^k, k = 0..32
                           -> plateau error e_spatial(h) as dt -> 0 and the temporal excess
                              of the CFL point

ADMISSIBILITY RULE (stated before the numbers are seen)
  The constant-CFL ladder may be quoted as spatial evidence iff BOTH hold per scheme:
    (a) |p_fixed_dt - p_cfl| <= 0.25   (the R5 agreement floor), and
    (b) temporal excess at the COARSEST rung, e(dr=0.2, dt=0.1)/e_plateau - 1 <= 0.05.
  If (a) or (b) fails, the constant-CFL runs may not be quoted as spatial and the certified
  order must be re-derived from the fixed-dt ladder only.  No threshold here is movable after
  seeing the result.

FROZEN-MODULE GUARD
  `numerics/tests/flat_wave_replication.py` is imported read-only and its sha256 must equal
  the pinned 8ade1cdc163ea420...; the driver refuses to run otherwise.  It writes one JSON
  artifact and edits nothing.

NOT CLAIMED: no gate verdict, no node completion, no self-gravity, no physics.  The lock
stays LOCKED; numerics/spherical_solver/ is not touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FROZEN = REPO / "numerics" / "tests" / "flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
DR_VALUES = [0.2, 0.1, 0.05, 0.025]
CFL = 0.5
R_MAX = 30.0
T_END = 6.0
DT_FIXED_LADDER = [1e-3, 5e-4]
TEMPORAL_DR = [0.2, 0.05]
TEMPORAL_KMAX = 5          # dt = cfl*dr / 2^k, k = 0..5  (worst case 32x refinement)
EXCESS_TOL = 0.05          # rule (b)
R5_FLOOR = 0.25            # rule (a)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fit_with_se(drs, errs):
    """Independent log-log LSQ slope with standard error. Returns (slope, se, residuals)."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    xbar = x.mean()
    sxx = float(np.sum((x - xbar) ** 2))
    slope = float(np.sum((x - xbar) * (y - y.mean())) / sxx)
    intercept = float(y.mean() - slope * xbar)
    resid = y - (slope * x + intercept)
    dof = max(n - 2, 1)
    sigma2 = float(np.sum(resid ** 2) / dof)
    se = math.sqrt(sigma2 / sxx) if sxx > 0 else float("nan")
    return slope, se, [float(r) for r in resid]


def pair_orders(drs, errs):
    return [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
            for i in range(len(errs) - 1)]


def r5_delta(drs, errs):
    p = pair_orders(drs, errs)
    half_range = (max(p) - min(p)) / 2.0 if p else float("nan")
    _, se, _ = fit_with_se(drs, errs)
    return max(half_range, se), half_range, se


def ladder(mod, scheme, drs, dt_of_dr):
    rows = []
    for dr in drs:
        dt = dt_of_dr(dr)
        study = mod.order_study(scheme, dr_values=[dr], cfl=CFL,
                                r_max=R_MAX, t_end=T_END, dt_rule=lambda d, dt=dt: dt)
        row = study["rows"][0]
        rows.append({"dr": dr, "dt": dt, "steps": row["steps"],
                     "l2_error": row["l2_error"]})
    errs = [r["l2_error"] for r in rows]
    fit, se, resid = fit_with_se(drs, errs)
    delta, half_range, _ = r5_delta(drs, errs)
    return {
        "rows": rows,
        "fit_order": fit,
        "least_squares_se": se,
        "lsq_residuals": resid,
        "pair_orders": pair_orders(drs, errs),
        "pair_half_range": half_range,
        "delta_R5": delta,
        "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
        "p_design": 2.0,
        "within_band": bool(abs(fit - 2.0) <= 0.3),
    }


def temporal_sweep(mod, scheme, dr):
    """Fixed h, refine dt: error(dt) -> plateau e_spatial(h); report the CFL excess."""
    cfl_dt = CFL * dr
    pts = []
    for k in range(TEMPORAL_KMAX + 1):
        dt = cfl_dt / (2 ** k)
        study = mod.order_study(scheme, dr_values=[dr], cfl=CFL,
                                r_max=R_MAX, t_end=T_END, dt_rule=lambda d, dt=dt: dt)
        pts.append({"k": k, "dt": dt, "steps": study["rows"][0]["steps"],
                    "l2_error": study["rows"][0]["l2_error"]})
    plateaus = [p["l2_error"] for p in pts]
    e_plateau = plateaus[-1]
    e_cfl = plateaus[0]
    excess = e_cfl / e_plateau - 1.0
    # temporal order from the two finest points that are still above the plateau
    orders = [float(math.log(plateaus[i] / plateaus[i + 1]) / math.log(2.0))
              for i in range(len(plateaus) - 1)]
    return {"dr": dr, "dt_cfl": cfl_dt, "points": pts,
            "e_plateau": e_plateau, "e_at_cfl": e_cfl,
            "temporal_excess_at_cfl": float(excess),
            "temporal_orders_per_doubling": orders,
            "monotone_to_plateau": all(plateaus[i + 1] <= plateaus[i] * (1 + 1e-12)
                                       for i in range(len(plateaus) - 1))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    measured = sha256_file(FROZEN)
    if measured != FROZEN_SHA:
        print(json.dumps({"error": "frozen module hash mismatch", "expected": FROZEN_SHA,
                          "measured": measured}, indent=1))
        return 2

    sys.path.insert(0, str(FROZEN.parent))
    import flat_wave_replication as mod  # noqa: E402  (read-only import, hash-guarded)

    t0 = time.time()
    out = {
        "artifact": "numerics/protocol/temporal_subdominance_control.py",
        "schema": "n0-temporal-subdominance-control/v1",
        "purpose": ("Resolve review finding F1: measure whether the constant-CFL replication "
                    "ladder measures spatial order, and produce a protocol section 3.4 "
                    "compliant fixed-dt ladder."),
        "assignment_context": ["astra-indep-1-N0-numerics", "astra-life01-n0-proposal"],
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "review_finding_addressed": {
            "id": "F1",
            "raised_by": "worker-067",
            "raised_at": "2026-09-12T00:22:56+08:00",
            "text": ("protocol section 3.4 forbids dt-proportional-to-h runs as spatial evidence, "
                     "yet the proposal's certified spatial order claim uses those constant-CFL runs"),
        },
        "admissibility_rule_stated_before_results": {
            "rule_a": "|p_fixed_dt - p_cfl| <= 0.25 (R5 floor)",
            "rule_b": "temporal excess at dr=0.2: e(dt=0.1)/e_plateau - 1 <= 0.05",
            "consequence_if_failed": ("constant-CFL runs may not be quoted as spatial; the "
                                      "certified order must come from the fixed-dt ladder only"),
            "thresholds_movable_after_result": False,
        },
        "frozen_module": {"path": "numerics/tests/flat_wave_replication.py",
                          "sha256": measured, "hash_guard_passed": True},
        "config": {"dr_values": DR_VALUES, "cfl_for_constant_ladder": CFL,
                   "dt_fixed_ladder": DT_FIXED_LADDER, "temporal_dr": TEMPORAL_DR,
                   "temporal_kmax": TEMPORAL_KMAX, "r_max": R_MAX, "t_end": T_END,
                   "p_design": 2.0, "p_tol": 0.3},
        "schemes": {},
        "not_claimed": [
            "no gate verdict and no gate self-pass",
            "no node completion; numerics_lock stays LOCKED and numerics/spherical_solver/ is absent",
            "no physics claim; flat-space discretisation evidence only",
            "no claim that the three shared axes (psi=r*phi, Dirichlet box, Taylor start) are independent",
        ],
    }

    for scheme in ("lffd", "cnfd", "cnfem"):
        entry = {}
        entry["A_constant_cfl_ladder"] = ladder(mod, scheme, DR_VALUES,
                                                lambda dr: CFL * dr)
        entry["B_fixed_dt_ladders"] = {
            f"dt_{dt:g}": ladder(mod, scheme, DR_VALUES, lambda dr, dt=dt: dt)
            for dt in DT_FIXED_LADDER
        }
        entry["C_temporal_sweeps"] = [temporal_sweep(mod, scheme, dr) for dr in TEMPORAL_DR]

        p_cfl = entry["A_constant_cfl_ladder"]["fit_order"]
        checks = {}
        for name, lad in entry["B_fixed_dt_ladders"].items():
            gap = abs(lad["fit_order"] - p_cfl)
            checks[name] = {
                "p_fixed": lad["fit_order"], "p_cfl": p_cfl, "abs_gap": gap,
                "rule_a_pass": bool(gap <= R5_FLOOR),
                "fixed_ladder_within_band": lad["within_band"],
                "fixed_ladder_monotone": lad["monotone"],
            }
        worst = max(e["temporal_excess_at_cfl"] for e in entry["C_temporal_sweeps"])
        checks["rule_b"] = {
            "worst_temporal_excess_at_cfl": float(worst),
            "dr_of_worst": max(entry["C_temporal_sweeps"],
                               key=lambda e: e["temporal_excess_at_cfl"])["dr"],
            "rule_b_pass": bool(worst <= EXCESS_TOL),
        }
        checks["admissible_as_spatial"] = bool(
            all(c["rule_a_pass"] for c in checks.values() if isinstance(c, dict) and "rule_a_pass" in c)
            and checks["rule_b"]["rule_b_pass"]
        )
        entry["checks"] = checks
        entry["verdict"] = ("constant-CFL ladder measures the spatial order (temporal "
                            "contribution below the pre-stated tolerance)"
                            if checks["admissible_as_spatial"] else
                            "constant-CFL ladder is NOT admissible as spatial evidence; "
                            "use the fixed-dt ladder")
        out["schemes"][scheme] = entry

    out["overall"] = {
        "all_schemes_admissible": all(
            e["checks"]["admissible_as_spatial"] for e in out["schemes"].values()),
        "p_cfl_by_scheme": {s: e["A_constant_cfl_ladder"]["fit_order"]
                            for s, e in out["schemes"].items()},
        "p_fixed_1e-3_by_scheme": {s: e["B_fixed_dt_ladders"]["dt_0.001"]["fit_order"]
                                   for s, e in out["schemes"].items()},
        "p_fixed_5e-4_by_scheme": {s: e["B_fixed_dt_ladders"]["dt_0.0005"]["fit_order"]
                                   for s, e in out["schemes"].items()},
        "runtime_seconds": None,
    }
    out["overall"]["runtime_seconds"] = round(time.time() - t0, 2)
    out["provenance"] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generator": "astra-lead-numerics (lead control; frozen module imported read-only)",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
    }

    text = json.dumps(out, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n")
    print(json.dumps({
        "all_schemes_admissible": out["overall"]["all_schemes_admissible"],
        "p_cfl": {k: round(v, 6) for k, v in out["overall"]["p_cfl_by_scheme"].items()},
        "p_fixed_1e-3": {k: round(v, 6) for k, v in out["overall"]["p_fixed_1e-3_by_scheme"].items()},
        "p_fixed_5e-4": {k: round(v, 6) for k, v in out["overall"]["p_fixed_5e-4_by_scheme"].items()},
        "rule_b_worst_excess": {s: e["checks"]["rule_b"]["worst_temporal_excess_at_cfl"]
                                for s, e in out["schemes"].items()},
        "runtime_seconds": out["overall"]["runtime_seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
