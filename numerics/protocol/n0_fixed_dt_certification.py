#!/usr/bin/env python3
"""N0 certification ladder: the protocol-section-3.4-EXACT fixed-dt spatial study.

WHY THIS EXISTS
  Review finding F1 (worker-067) and its independent confirmation F1' (worker-081, whose own
  accept W081-N0-C8-01 was withdrawn on the strength of it) establish that the certified N0
  order claim was carried by constant-CFL ladders (cfl = 0.5, dt = 0.5*dr).  The protocol of
  record `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2` section 3.4 says spatial order is
  measured with a FIXED small dt and that `dt ~ h` runs "are reported as mixed-order and never
  quoted as spatial".

  The protocol text is therefore CORRECT; the EVIDENCE did not follow it.  The remedy is to
  file the study section 3.4 prescribes, not to amend the protocol -- which also avoids
  invalidating the standing rev-3 accept and respects the audit group's freeze-first direction.

WHAT THIS RUNS
  dr = 0.2 / 0.1 / 0.05 / 0.025 (four rungs), dt = 1e-4 FIXED on every rung (the value named in
  section 3.4), for each of the three methodologically independent schemes lffd / cnfd / cnfem.
  Temporal subdominance at this dt is bounded by the companion control
  `numerics/protocol/temporal_subdominance_control.json` (dt = 1e-3 and 5e-4 ladders) and by
  the fixed-h refine-dt sweeps recorded there.

OUTPUTS per scheme: fit order, least-squares standard error, pair orders, pair half-range,
  R5 delta, monotonicity, band membership.  Cross-scheme: pairwise |dp| against the R5 bound.
  The cfl = 0.5 mixed-order ladder is carried alongside as a LABELLED control.

FROZEN-MODULE GUARD: read-only import; sha256 must equal 8ade1cdc...
NOT CLAIMED: no gate verdict, no node completion, no self-gravity, no physics.
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
DT_FIXED = 1e-4
CFL_MIXED = 0.5
R_MAX, T_END = 30.0, 6.0
P_DESIGN, P_TOL = 2.0, 0.3
R5_FLOOR = 0.25
SCHEMES = ("lffd", "cnfd", "cnfem")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fit(drs, errs):
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    sxx = float(np.sum((x - x.mean()) ** 2))
    slope = float(np.sum((x - x.mean()) * (y - y.mean())) / sxx)
    intercept = float(y.mean() - slope * x.mean())
    resid = y - (slope * x + intercept)
    se = math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) / sxx)
    return slope, se, [float(r) for r in resid]


def study(mod, scheme, drs, dt_of):
    rows = []
    for dr in drs:
        dt = dt_of(dr)
        s = mod.order_study(scheme, dr_values=[dr], cfl=CFL_MIXED, r_max=R_MAX, t_end=T_END,
                            dt_rule=lambda d, dt=dt: dt)
        r = s["rows"][0]
        rows.append({"dr": dr, "dt": dt, "cfl_effective": dt / dr, "steps": r["steps"],
                     "l2_error": r["l2_error"]})
    errs = [r["l2_error"] for r in rows]
    p, se, resid = fit(drs, errs)
    pairs = [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
             for i in range(len(errs) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0
    return {"rows": rows, "fit_order": p, "least_squares_se": se, "lsq_residuals": resid,
            "pair_orders": pairs, "pair_half_range": half, "delta_R5": max(half, se),
            "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
            "within_band": bool(abs(p - P_DESIGN) <= P_TOL)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    measured = sha256_file(FROZEN)
    if measured != FROZEN_SHA:
        print(json.dumps({"error": "frozen module hash mismatch", "measured": measured}))
        return 2
    sys.path.insert(0, str(FROZEN.parent))
    import flat_wave_replication as mod  # noqa: E402

    t0 = time.time()
    out = {
        "artifact": "numerics/protocol/n0_fixed_dt_certification.py",
        "schema": "n0-fixed-dt-certification/v1",
        "purpose": ("Certification evidence for G-NUM that follows protocol section 3.4 exactly: "
                    "spatial order at FIXED dt = 1e-4, four rungs, three independent schemes. "
                    "Replaces the constant-CFL ladder as the certification basis after review "
                    "findings F1 / F1'."),
        "assignment_context": ["astra-indep-1-N0-numerics", "astra-life01-n0-proposal"],
        "supersedes_evidence_basis": {
            "constant_cfl_ladder": "numerics/tests/n0_order_4rung.json#c88146a1375c50f0",
            "relabelled_as": "mixed-order corroborating control (NOT a spatial claim)",
            "reason": ("cfl = 0.5 with dt = 0.5*dr; fixed-h refine-dt sweeps in "
                       "numerics/protocol/temporal_subdominance_control.json show the temporal "
                       "contribution is not negligible (cnfd excess +126% at dr = 0.05), and "
                       "worker-067 / worker-081 independently measured the same defect"),
        },
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "frozen_module": {"path": "numerics/tests/flat_wave_replication.py",
                          "sha256": measured, "hash_guard_passed": True},
        "config": {"dr_values": DR_VALUES, "dt_fixed": DT_FIXED, "dt_rule": "constant on every rung",
                   "protocol_clause": "numerics/CONVERGENCE_PROTOCOL.md section 3.4",
                   "r_max": R_MAX, "t_end": T_END, "p_design": P_DESIGN, "p_tol": P_TOL,
                   "uncertainty_rule": "R5: max(pair-spread half-range, least-squares slope SE)"},
        "schemes": {}, "not_claimed": [
            "no gate verdict and no gate self-pass (authority: Astra)",
            "no node completion; numerics_lock stays LOCKED and N1 stays queued",
            "no physics claim; flat-space discretisation evidence only",
            "no claim that the shared axes (psi=r*phi, Dirichlet box, Taylor start, "
            "Gaussian-pulse family) are independent",
        ],
    }

    for scheme in SCHEMES:
        cert = study(mod, scheme, DR_VALUES, lambda dr: DT_FIXED)
        mixed = study(mod, scheme, DR_VALUES, lambda dr: CFL_MIXED * dr)
        out["schemes"][scheme] = {
            "fixed_dt_certification": cert,
            "constant_cfl_mixed_order_control": mixed,
            "order_shift_vs_mixed": abs(cert["fit_order"] - mixed["fit_order"]),
        }

    # cross-scheme R5 agreement on the CERTIFICATION ladder
    pairs = []
    for i, a in enumerate(SCHEMES):
        for b in SCHEMES[i + 1:]:
            pa = out["schemes"][a]["fixed_dt_certification"]
            pb = out["schemes"][b]["fixed_dt_certification"]
            bound = max(R5_FLOOR, math.sqrt(pa["delta_R5"] ** 2 + pb["delta_R5"] ** 2))
            diff = abs(pa["fit_order"] - pb["fit_order"])
            pairs.append({"pair": f"{a} vs {b}", "abs_order_diff": diff, "r5_bound": bound,
                          "agree": bool(diff <= bound)})
    out["cross_scheme_R5"] = {
        "pairs": pairs,
        "max_pairwise_abs_diff": max(p["abs_order_diff"] for p in pairs),
        "all_agree": all(p["agree"] for p in pairs),
        "delta_R5_by_scheme": {s: out["schemes"][s]["fixed_dt_certification"]["delta_R5"]
                               for s in SCHEMES},
    }
    out["verdict"] = {
        "certified_spatial_order": {s: out["schemes"][s]["fixed_dt_certification"]["fit_order"]
                                    for s in SCHEMES},
        "all_within_band": all(out["schemes"][s]["fixed_dt_certification"]["within_band"]
                               for s in SCHEMES),
        "all_monotone": all(out["schemes"][s]["fixed_dt_certification"]["monotone"]
                            for s in SCHEMES),
        "cross_scheme_agree": out["cross_scheme_R5"]["all_agree"],
        "claim": ("second-order spatial discretisation, certified at four rungs with dt fixed at "
                  "1e-4, for three methodologically independent schemes, cross-scheme |dp| within "
                  "the R5 bound"),
    }
    out["runtime_seconds"] = round(time.time() - t0, 2)
    out["provenance"] = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                         "generator": "astra-lead-numerics (lead certification run, read-only "
                                      "frozen import; no worker artifact edited)",
                         "python": platform.python_version(), "numpy": np.__version__,
                         "platform": platform.platform()}

    text = json.dumps(out, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n")
    print(json.dumps({"certified": out["verdict"], "runtime_seconds": out["runtime_seconds"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
