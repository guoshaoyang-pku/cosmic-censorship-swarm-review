#!/usr/bin/env python3
"""W051-N0-DTSUBDOM-04 addendum: matched-final-time probe of the dt=5e-5 arm.

WHY THIS EXISTS
  The main study (report.json) found that the frozen harness stops on a tolerance rule:
  at dt = 1e-4 it takes 60000 steps and lands at t = 5.999999999999355, but at dt = 5e-5 and
  2.5e-5 it takes one extra full step and lands at t = t_end + dt (6.00005 / 6.000025).  So the
  dt = 5e-5 arm of the direct temporal comparison is evaluated 5e-5 later than the dt = 1e-4 arm.
  This probe re-runs the cnfd dt = 5e-5 ladder and evaluates the L2 error at the stored step
  closest to t = 6.0, i.e. at the same physical time as the dt = 1e-4 arm, and contrasts it with
  the harness-final-time error.  It bounds how much of the measured dt-difference is the
  final-time offset and how much is temporal discretisation.

POST-HOC, LABELLED: this probe was written after the main study's pre-registered result and does
not move any threshold.  It writes only under artifacts/worker-051/n0_dt_subdominance/ and
imports the frozen module read-only under the same sha256 guard.
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
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
CERT_JSON = REPO / "numerics" / "protocol" / "n0_fixed_dt_certification.json"
CERT_JSON_SHA = "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920"
DR_VALUES = (0.2, 0.1, 0.05, 0.025)
DT = 5e-5
SCHEME = "cnfd"
R_MAX, T_END = 30.0, 6.0
T_MATCH = 6.0


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fit_order(drs, errs):
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    sxx = float(np.sum((x - x.mean()) ** 2))
    slope = float(np.sum((x - x.mean()) * (y - y.mean())) / sxx)
    intercept = y.mean() - slope * x.mean()
    resid = y - (slope * x + intercept)
    se = math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) / sxx)
    pairs = [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
             for i in range(len(errs) - 1)]
    return {"fit_order": slope, "least_squares_se": se, "pair_orders": pairs,
            "delta_R5": max((max(pairs) - min(pairs)) / 2.0, se)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("matched_time_probe.json")))
    args = ap.parse_args(argv)
    t0 = time.time()

    pins = {"numerics/tests/flat_wave_replication.py": FROZEN_SHA,
            "numerics/protocol/n0_fixed_dt_certification.json": CERT_JSON_SHA}
    resolved = {k: (sha256_file(REPO / k) == v) for k, v in pins.items()}
    if not all(resolved.values()):
        out = {"task_id": "W051-N0-DTSUBDOM-04-addendum", "refused": "pin mismatch",
               "pins": resolved}
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        return 2

    sys.path.insert(0, str(FROZEN.parent))
    import flat_wave_replication as mod  # noqa: E402
    pulse = mod.PulseExact()
    cert = json.loads(CERT_JSON.read_text())

    rows = []
    for dr in DR_VALUES:
        case = mod.run_case(mod.make_factory(SCHEME, pulse=pulse), dr, DT / dr, R_MAX, T_END)
        times = np.asarray(case["t"], float)
        idx = int(np.argmin(np.abs(times - T_MATCH)))
        t_at = float(times[idx])
        e_final = mod.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
        e_match = mod.l2_error(case["psi"][idx], pulse.psi(case["r"], t_at), dr)
        cert_row = [r for r in cert["schemes"][SCHEME]["fixed_dt_certification"]["rows"]
                    if r["dr"] == dr][0]
        rows.append({
            "dr": dr, "dt_requested": DT, "steps": case["steps"],
            "t_final": float(case["t"][-1]), "t_matched": t_at,
            "t_matched_index": idx, "t_matched_offset": t_at - T_MATCH,
            "l2_error_harness_final_t": e_final,
            "l2_error_matched_t6": e_match,
            "final_minus_matched": e_final - e_match,
            "final_minus_matched_rel": (e_final - e_match) / e_match,
            "certificate_dt_1e-4_l2_error": cert_row["l2_error"],
            "matched_minus_certificate_rel": (e_match - cert_row["l2_error"]) / cert_row["l2_error"],
            "harness_final_minus_certificate_rel":
                (e_final - cert_row["l2_error"]) / cert_row["l2_error"],
        })
        del case

    drs = [r["dr"] for r in rows]
    fit_final = fit_order(drs, [r["l2_error_harness_final_t"] for r in rows])
    fit_match = fit_order(drs, [r["l2_error_matched_t6"] for r in rows])
    p_cert = cert["schemes"][SCHEME]["fixed_dt_certification"]["fit_order"]
    out = {
        "schema": "n0-dt-subdominance-matched-time-probe/v1",
        "task_id": "W051-N0-DTSUBDOM-04-addendum",
        "actor": "worker-051", "role": "bounded execution worker",
        "post_hoc": True, "thresholds_moved": False,
        "purpose": ("Bound the frozen harness's one-step final-time overshoot on the dt=5e-5 arm "
                    "by re-evaluating the L2 error at the stored step closest to t=6.0 and "
                    "refitting the four-rung order at matched final time."),
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "pins": {k: {"sha256": v, "resolves": resolved[k]} for k, v in pins.items()},
        "config": {"scheme": SCHEME, "dt": DT, "dr_values": list(DR_VALUES),
                   "match_time": T_MATCH, "harness_final_time_rule":
                   "while t < t_end - 1e-12: step(); final t is t_end-1e-12 rounded up by one dt"},
        "rows": rows,
        "fits": {
            "certificate_dt_1e-4_fit_order": p_cert,
            "dt_5e-5_harness_final_time_fit_order": fit_final,
            "dt_5e-5_matched_t6_fit_order": fit_match,
            "order_shift_harness_final_vs_certificate": abs(fit_final["fit_order"] - p_cert),
            "order_shift_matched_vs_certificate": abs(fit_match["fit_order"] - p_cert),
        },
        "max_abs_overshoot_effect_on_error":
            max(abs(r["final_minus_matched"]) for r in rows),
        "max_rel_overshoot_effect_on_error":
            max(abs(r["final_minus_matched_rel"]) for r in rows),
        "not_claimed": [
            "no gate verdict, no node completion, no numerics_lock change",
            "post-hoc diagnostic; the pre-registered verdict in report.json is unchanged",
            "cnfd only; the other two schemes are not probed here",
        ],
        "runtime_seconds": round(time.time() - t0, 2),
        "provenance": {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                       "python": platform.python_version(), "numpy": np.__version__,
                       "platform": platform.platform()},
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"rows": [{k: r[k] for k in
                                ("dr", "steps", "t_final", "t_matched_offset",
                                 "l2_error_harness_final_t", "l2_error_matched_t6",
                                 "final_minus_matched_rel")} for r in rows],
                      "fits": out["fits"],
                      "max_rel_overshoot_effect_on_error":
                          out["max_rel_overshoot_effect_on_error"],
                      "runtime_seconds": out["runtime_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
