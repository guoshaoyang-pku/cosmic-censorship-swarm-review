#!/usr/bin/env python3
"""W051-N0-DTSUBDOM-04: direct temporal-subdominance bound AT the fixed-dt certification point.

WHY THIS EXISTS
  The current N0 order-certification basis is
  `numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c` (lead-numerics):
  four rungs dr = 0.2/0.1/0.05/0.025, dt FIXED at 1e-4, schemes lffd/cnfd/cnfem.
  Its docstring says temporal subdominance at dt = 1e-4 is "bounded by the companion control
  (dt = 1e-3 and 5e-4 ladders)".  That control brackets the certification dt only by
  extrapolation: no measurement exists AT 1e-4 or between 1e-4 and 5e-5.  The lead's own
  falsifier F7 is "the fixed-dt ladder is shown temporally contaminated at dt <= 1e-4".

  This task measures the residual temporal contribution directly at the certification dt by
  re-running the SAME frozen module at dt = 1e-4, 5e-5, 2.5e-5 on the SAME four rungs, and
  bounds (a) the temporal contamination of each rung error at 1e-4, (b) the shift of the
  four-rung fitted order between 1e-4 and 5e-5, and (c) the measured temporal order.
  The 1e-4 arm doubles as a positive control: it must reproduce the published certificate rows
  bitwise.

WHAT THIS IS NOT
  No gate verdict, no node completion, no self-gravity, no N1 work, no solver code.  The
  frozen module is imported READ-ONLY under a sha256 guard; the script writes only under
  artifacts/worker-051/n0_dt_subdominance/.  Flat-space calibration sub-case only.
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

REPO = Path(__file__).resolve().parents[3]
FROZEN = REPO / "numerics" / "tests" / "flat_wave_replication.py"
CERT_JSON = REPO / "numerics" / "protocol" / "n0_fixed_dt_certification.json"
CERT_PY = REPO / "numerics" / "protocol" / "n0_fixed_dt_certification.py"
PROTOCOL = REPO / "numerics" / "CONVERGENCE_PROTOCOL.md"

PINS = {
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/protocol/n0_fixed_dt_certification.json":
        "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "numerics/protocol/n0_fixed_dt_certification.py":
        "3c7c9087838446046d7462f92c9ffdd9ff137cc6a07ac63bf41e7db90dfbf145",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
}

# --- pre-registered configuration and thresholds (fixed before any measurement) -------------
SCHEMES = ("lffd", "cnfd", "cnfem")
DR_VALUES = (0.2, 0.1, 0.05, 0.025)
DT_LEVELS = (1e-4, 5e-5, 2.5e-5)
DT_CERT = 1e-4
R_MAX, T_END = 30.0, 6.0
P_DESIGN, P_TOL = 2.0, 0.3
CONTAM_REL_BOUND = 0.05        # F3: |e(1e-4)-e(5e-5)| / e(5e-5) <= 5% on every rung
ORDER_SHIFT_BOUND = 1e-3       # F4: |p(1e-4)-p(5e-5)| <= 1e-3 (10x the largest delta_R5)
Q_TEMPORAL_BAND = (1.5, 2.5)   # F5: Richardson temporal order on coarse rungs
ROUNDOFF_FLOOR = 1e-13         # F5: below this relative gap the probe is inconclusive, not failed
REPRO_REL_TOL = 1e-12          # F2: 1e-4 arm vs published certificate (bitwise expected)
DETERMINISM_CASES = (("cnfd", 0.05, 1e-4), ("lffd", 0.025, 5e-5))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fit_order(drs, errs):
    """Own log-log OLS; same estimator family as the certificate, re-implemented here."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    sxx = float(np.sum((x - x.mean()) ** 2))
    slope = float(np.sum((x - x.mean()) * (y - y.mean())) / sxx)
    intercept = float(y.mean() - slope * x.mean())
    resid = y - (slope * x + intercept)
    se = math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) / sxx)
    pairs = [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
             for i in range(len(errs) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0
    return {"fit_order": slope, "least_squares_se": se, "pair_orders": pairs,
            "pair_half_range": half, "delta_R5": max(half, se),
            "lsq_residuals": [float(r) for r in resid],
            "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
            "within_band": bool(abs(slope - P_DESIGN) <= P_TOL)}


def run_case(mod, scheme, dr, dt):
    s = mod.order_study(scheme, dr_values=[dr], cfl=0.5, r_max=R_MAX, t_end=T_END,
                        dt_rule=lambda d, dt=dt: dt)
    r = s["rows"][0]
    return {"dr": dr, "dt_requested": dt, "dt_reported": r["dt"], "steps": r["steps"],
            "l2_error": r["l2_error"], "final_t": r["final_t"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    args = ap.parse_args(argv)

    t0 = time.time()
    out = {
        "schema": "n0-dt-subdominance/v1",
        "task_id": "W051-N0-DTSUBDOM-04",
        "actor": "worker-051",
        "role": "bounded execution worker",
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "purpose": ("Direct temporal-subdominance bound at the N0 fixed-dt certification point: "
                    "re-run the frozen module at dt = 1e-4 / 5e-5 / 2.5e-5 on the same four rungs "
                    "and three schemes; bound the residual temporal contribution to each rung "
                    "error and to the four-rung fitted order; measure the temporal order. The "
                    "1e-4 arm is a positive control against the published certificate."),
        "falsifier_of_this_task": (
            "Triggered if any pin fails to resolve (F1); if the 1e-4 arm does not reproduce the "
            "published certificate rows/orders to <= 1e-12 relative (F2); if any scheme/rung has "
            "|e(1e-4)-e(5e-5)|/e(5e-5) > 0.05 (F3, falsifier F7 of the certificate); if "
            "|p(1e-4)-p(5e-5)| > 1e-3 or either fit leaves |p-2| <= 0.3 / loses monotonicity (F4); "
            "if the measurable Richardson temporal order leaves [1.5, 2.5] (F5); if steps != "
            "t_end/dt or e(1e-4) == e(5e-5) bitwise (F6); or if the repeated cases are not "
            "bitwise deterministic (F7)."),
        "pre_registered": {
            "stated_before_measurement": True,
            "schemes": list(SCHEMES), "dr_values": list(DR_VALUES), "dt_levels": list(DT_LEVELS),
            "dt_certification": DT_CERT, "r_max": R_MAX, "t_end": T_END,
            "p_design": P_DESIGN, "p_tol": P_TOL,
            "F3_contamination_rel_bound": CONTAM_REL_BOUND,
            "F4_order_shift_bound": ORDER_SHIFT_BOUND,
            "F5_temporal_order_band": list(Q_TEMPORAL_BAND),
            "F5_roundoff_floor": ROUNDOFF_FLOOR,
            "F2_reproduction_rel_tol": REPRO_REL_TOL,
            "determinism_cases": [list(c) for c in DETERMINISM_CASES],
            "thresholds_movable_after_result": False,
        },
        "not_claimed": [
            "no gate verdict and no gate self-pass (authority: Astra / group leads)",
            "no node completion; N0 stays active and numerics_lock stays LOCKED, N1 stays queued",
            "no physics claim; flat-space calibration evidence only",
            "no claim about the shared axes (psi=r*phi reduction, Dirichlet box, Taylor start, "
            "Gaussian-pulse family)",
            "this is a faithful re-execution of the frozen module, not an independent "
            "discretisation; implementation independence is covered by workers 046/057",
        ],
    }

    # F1: pins ---------------------------------------------------------------------------------
    pins = {}
    pin_ok = True
    for rel, want in PINS.items():
        p = REPO / rel
        got = sha256_file(p) if p.exists() else None
        ok = got == want
        pin_ok = pin_ok and ok
        pins[rel] = {"expected_sha256": want, "measured_sha256": got, "resolves": bool(ok)}
    out["pins"] = pins
    if not pin_ok:
        out["verdict"] = {"overall": "refused_pin_mismatch", "falsifier_triggered": ["F1"]}
        out["checks"] = {"F1_pins_resolve": False}
        out["runtime_seconds"] = round(time.time() - t0, 2)
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        print(json.dumps(out["verdict"]))
        return 2

    sys.path.insert(0, str(FROZEN.parent))
    import flat_wave_replication as mod  # noqa: E402  (read-only, hash-guarded above)

    cert = json.loads(CERT_JSON.read_text())

    # measurement grid -------------------------------------------------------------------------
    studies = {}
    for scheme in SCHEMES:
        per_dt = {}
        for dt in DT_LEVELS:
            rows = [run_case(mod, scheme, dr, dt) for dr in DR_VALUES]
            errs = [r["l2_error"] for r in rows]
            per_dt[repr(dt)] = {"dt": dt, "rows": rows, "fit": fit_order(DR_VALUES, errs)}
        studies[scheme] = per_dt
    out["studies"] = studies

    # F2: 1e-4 arm reproduces the published certificate ---------------------------------------
    f2 = {"pass": True, "max_rel_row_diff": 0.0, "max_abs_order_diff": 0.0, "schemes": {}}
    for scheme in SCHEMES:
        mine = {r["dr"]: r for r in studies[scheme][repr(DT_CERT)]["rows"]}
        pub = {r["dr"]: r for r in
               cert["schemes"][scheme]["fixed_dt_certification"]["rows"]}
        row_diffs = {dr: {"abs": abs(mine[dr]["l2_error"] - pub[dr]["l2_error"]),
                          "rel": abs(mine[dr]["l2_error"] - pub[dr]["l2_error"]) / pub[dr]["l2_error"],
                          "bitwise_equal": mine[dr]["l2_error"] == pub[dr]["l2_error"]}
                     for dr in DR_VALUES}
        p_mine = studies[scheme][repr(DT_CERT)]["fit"]["fit_order"]
        p_pub = cert["schemes"][scheme]["fixed_dt_certification"]["fit_order"]
        max_rel = max(v["rel"] for v in row_diffs.values())
        ok = max_rel <= REPRO_REL_TOL and abs(p_mine - p_pub) <= REPRO_REL_TOL
        f2["pass"] = f2["pass"] and ok
        f2["schemes"][scheme] = {"row_diffs": row_diffs, "fit_order_mine": p_mine,
                                 "fit_order_published": p_pub,
                                 "abs_fit_order_diff": abs(p_mine - p_pub), "pass": bool(ok)}
        f2["max_rel_row_diff"] = max(f2["max_rel_row_diff"], max_rel)
        f2["max_abs_order_diff"] = max(f2["max_abs_order_diff"], abs(p_mine - p_pub))

    # F3/F4/F5: temporal analysis --------------------------------------------------------------
    temporal = {}
    f3 = {"pass": True, "bound": CONTAM_REL_BOUND, "schemes": {}}
    f4 = {"pass": True, "bound": ORDER_SHIFT_BOUND, "schemes": {}}
    f5 = {"pass": True, "band": list(Q_TEMPORAL_BAND), "schemes": {}, "inconclusive": []}
    for scheme in SCHEMES:
        e1 = {r["dr"]: r["l2_error"] for r in studies[scheme][repr(1e-4)]["rows"]}
        e2 = {r["dr"]: r["l2_error"] for r in studies[scheme][repr(5e-5)]["rows"]}
        e3 = {r["dr"]: r["l2_error"] for r in studies[scheme][repr(2.5e-5)]["rows"]}
        per_rung = {}
        for dr in DR_VALUES:
            gap12 = abs(e1[dr] - e2[dr])
            rel = gap12 / e2[dr]
            f3["pass"] = f3["pass"] and (rel <= CONTAM_REL_BOUND)
            gap23 = abs(e2[dr] - e3[dr])
            q = None
            status = "measured"
            if gap12 <= ROUNDOFF_FLOOR * e1[dr] or gap23 <= ROUNDOFF_FLOOR * e2[dr]:
                status = "at_roundoff_inconclusive"
                f5["inconclusive"].append(f"{scheme}@dr={dr}")
            else:
                q = math.log(gap12 / gap23) / math.log(2.0)
                if not (Q_TEMPORAL_BAND[0] <= q <= Q_TEMPORAL_BAND[1]):
                    f5["pass"] = False
            per_rung[dr] = {"e_dt_1e-4": e1[dr], "e_dt_5e-5": e2[dr], "e_dt_2p5e-5": e3[dr],
                            "gap_1e-4_vs_5e-5": gap12, "gap_5e-5_vs_2p5e-5": gap23,
                            "rel_contamination_at_1e-4": rel, "q_temporal": q, "q_status": status}
        p1 = studies[scheme][repr(1e-4)]["fit"]
        p2 = studies[scheme][repr(5e-5)]["fit"]
        p3 = studies[scheme][repr(2.5e-5)]["fit"]
        shift = abs(p1["fit_order"] - p2["fit_order"])
        ok4 = (shift <= ORDER_SHIFT_BOUND and p2["within_band"] and p2["monotone"]
               and p1["within_band"] and p1["monotone"] and p3["within_band"] and p3["monotone"])
        f4["pass"] = f4["pass"] and ok4
        f4["schemes"][scheme] = {
            "fit_order_1e-4": p1["fit_order"], "fit_order_5e-5": p2["fit_order"],
            "fit_order_2p5e-5": p3["fit_order"], "order_shift_1e-4_vs_5e-5": shift,
            "delta_R5_1e-4": p1["delta_R5"], "within_band_all": bool(
                p1["within_band"] and p2["within_band"] and p3["within_band"]),
            "monotone_all": bool(p1["monotone"] and p2["monotone"] and p3["monotone"]),
            "pass": bool(ok4)}
        temporal[scheme] = {"per_rung": per_rung,
                            "max_rel_contamination_at_1e-4":
                                max(v["rel_contamination_at_1e-4"] for v in per_rung.values())}
        f3["schemes"][scheme] = {"max_rel_contamination_at_1e-4":
                                 temporal[scheme]["max_rel_contamination_at_1e-4"]}
    out["temporal_analysis"] = temporal

    # F6: dt actually applied and arms differ -------------------------------------------------
    f6 = {"pass": True, "schemes": {}}
    for scheme in SCHEMES:
        per = {}
        for dt in DT_LEVELS:
            want_steps = round(T_END / dt)
            steps_ok = all(r["steps"] == want_steps for r in studies[scheme][repr(dt)]["rows"])
            per[repr(dt)] = {"expected_steps": want_steps,
                             "steps_observed": sorted({r["steps"] for r in
                                                       studies[scheme][repr(dt)]["rows"]}),
                             "steps_ok": steps_ok}
            f6["pass"] = f6["pass"] and steps_ok
        distinct = (studies[scheme][repr(1e-4)]["rows"][0]["l2_error"]
                    != studies[scheme][repr(5e-5)]["rows"][0]["l2_error"])
        per["arms_differ_bitwise"] = bool(distinct)
        f6["pass"] = f6["pass"] and distinct
        f6["schemes"][scheme] = per

    # F7: determinism --------------------------------------------------------------------------
    det = {"pass": True, "cases": []}
    for (scheme, dr, dt) in DETERMINISM_CASES:
        a = run_case(mod, scheme, dr, dt)
        b = run_case(mod, scheme, dr, dt)
        eq = (a["l2_error"] == b["l2_error"] and a["steps"] == b["steps"])
        det["pass"] = det["pass"] and eq
        det["cases"].append({"scheme": scheme, "dr": dr, "dt": dt,
                             "l2_error_run1": a["l2_error"], "l2_error_run2": b["l2_error"],
                             "bitwise_equal": bool(eq)})

    out["checks"] = {
        "F1_pins_resolve": bool(pin_ok),
        "F2_positive_control_reproduces_certificate": f2,
        "F3_temporal_contamination_at_cert_dt_within_bound": f3,
        "F4_certified_order_stable_under_dt_halving": f4,
        "F5_measured_temporal_order_in_band": f5,
        "F6_dt_actually_applied_and_arms_differ": f6,
        "F7_bitwise_determinism": det,
    }
    triggered = [k.split("_")[0] for k, v in out["checks"].items()
                 if isinstance(v, dict) and v.get("pass") is False]
    triggered += [k.split("_")[0] for k, v in out["checks"].items() if v is False]
    out["verdict"] = {
        "overall": "falsifier_not_triggered" if not triggered else "falsifier_triggered",
        "falsifier_triggered": triggered,
        "bound_at_certification_dt": {
            scheme: {"max_rel_temporal_contamination_at_1e-4":
                     temporal[scheme]["max_rel_contamination_at_1e-4"]}
            for scheme in SCHEMES},
        "order_shift_under_dt_halving": {
            scheme: f4["schemes"][scheme]["order_shift_1e-4_vs_5e-5"] for scheme in SCHEMES},
        "measured_temporal_order_range": {
            scheme: (lambda qs: [min(qs), max(qs)] if qs else None)(
                [v["q_temporal"] for v in temporal[scheme]["per_rung"].values()
                 if v["q_temporal"] is not None])
            for scheme in SCHEMES},
        "note": ("F5 inconclusive at rungs flagged at_roundoff: "
                 + (", ".join(f5["inconclusive"]) if f5["inconclusive"] else "none")),
    }
    out["runtime_seconds"] = round(time.time() - t0, 2)
    out["provenance"] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generator": "worker-051 bounded execution worker; frozen module imported read-only "
                     "under sha256 guard; own OLS fit; writes only under artifacts/worker-051/",
        "python": platform.python_version(), "numpy": np.__version__,
        "platform": platform.platform(),
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": out["verdict"], "checks_pass": {
        k: (v.get("pass") if isinstance(v, dict) else v) for k, v in out["checks"].items()},
        "runtime_seconds": out["runtime_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
