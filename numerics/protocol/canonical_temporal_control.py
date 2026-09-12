#!/usr/bin/env python3
"""Lead control: does the CANONICAL N0 study measure spatial order, or mixed order?

WHY THIS EXISTS
  Review finding F1 (worker-067) exposed that `numerics/CONVERGENCE_PROTOCOL.md` section 3.4
  prescribed a fixed, small dt (1e-4) for spatial-order measurement, while the certified
  N0 ladders actually used constant CFL (dt proportional to h).  The replication family is
  re-based on a fixed-dt ladder in `numerics/protocol/temporal_subdominance_control.json`.
  The CANONICAL artifact `numerics/tests/flat_wave.py` also steps with
  `n_steps = ceil(t_end/(cfl*h))`, `dt = t_end/n_steps`, i.e. also constant CFL -- so the same
  question must be asked of the primary evidence, not only of the replication.

TEST (read-only; the canonical file is NOT edited)
  Re-run each canonical `convergence_study` at the declared cfl and at successively smaller cfl
  values, holding the resolution list fixed.  At fixed h, dt -> 0 isolates the spatial error:
  the per-resolution errors converge to a plateau e_spatial(h).  Reported per study:
    * fitted l2 order at each cfl;
    * temporal excess at the coarsest and finest resolution: e(baseline)/e(plateau) - 1;
    * order stability |p(baseline) - p(smallest cfl)|.
  PRE-STATED RULE: the constant-CFL study may be quoted as spatial evidence iff the temporal
  excess at the COARSEST resolution is <= 0.05 and the fitted order moves <= 0.05.  Otherwise
  its order is labelled MIXED-ORDER and it may not be the sole basis of a spatial claim.
  Thresholds are fixed here, before the numbers are seen.

NOT CLAIMED: no gate verdict, no node completion, no self-gravity, no physics, no edit to the
canonical artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CANON = REPO / "numerics" / "tests" / "flat_wave.py"
EXCESS_TOL = 0.05
ORDER_MOVE_TOL = 0.05

# (label, kwargs, baseline_cfl, cfl_ladder)
STUDIES = [
    ("order2_standing", dict(order=2, family="standing", t_end=0.37), 0.25,
     [0.25, 0.05, 0.01, 0.002]),
    ("order2_pulse", dict(order=2, family="pulse", R=40.0, t_end=8.0, r0=12.0, sigma=2.0),
     0.25, [0.25, 0.05, 0.01, 0.002]),
    ("order4_standing", dict(order=4, family="standing", t_end=0.37,
                             modes=((2, 1.0), (5, 0.5))), 0.1, [0.1, 0.02, 0.004, 0.0008]),
]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    measured = sha256_file(CANON)
    sys.path.insert(0, str(CANON.parent))
    import flat_wave as fw  # noqa: E402  read-only

    t0 = time.time()
    out = {
        "artifact": "numerics/protocol/canonical_temporal_control.py",
        "schema": "n0-canonical-temporal-control/v1",
        "purpose": ("Determine whether the canonical flat_wave.py convergence studies measure "
                    "spatial order under constant CFL, per review finding F1."),
        "assignment_context": ["astra-indep-1-N0-numerics", "astra-life01-n0-proposal"],
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "canonical_artifact": {"path": "numerics/tests/flat_wave.py", "sha256": measured,
                               "edited": False},
        "pre_stated_rule": {
            "temporal_excess_tol": EXCESS_TOL,
            "order_move_tol": ORDER_MOVE_TOL,
            "criterion": ("spatial-admissible iff excess at coarsest resolution <= 0.05 "
                          "and |p(baseline) - p(plateau)| <= 0.05"),
            "thresholds_movable_after_result": False,
        },
        "method": ("hold the resolution list fixed, shrink cfl (hence dt) until per-resolution "
                   "errors plateau; the plateau is the spatial error e_spatial(h)"),
        "studies": {},
        "not_claimed": ["no gate verdict", "no node completion", "no physics claim",
                        "no edit to numerics/tests/flat_wave.py"],
    }

    for label, kwargs, base_cfl, cfls in STUDIES:
        runs = {}
        for cfl in cfls:
            st = fw.convergence_study(cfl=cfl, **kwargs)
            runs[f"{cfl:g}"] = {
                "cfl": cfl,
                "rows": [{"n": r["n"], "dt": r["dt"], "l2_error": r["l2_error"]}
                         for r in st["rows"]],
                "order_l2": st["order_l2"],
                "fit_order": float(np.polyfit(
                    np.log([r["dx"] for r in st["rows"]]),
                    np.log([r["l2_error"] for r in st["rows"]]), 1)[0]),
                "order_gate_pass": st["order_gate"]["pass"],
            }
        plateau_key = f"{cfls[-1]:g}"
        base_key = f"{base_cfl:g}"
        e_plateau = [r["l2_error"] for r in runs[plateau_key]["rows"]]
        e_base = [r["l2_error"] for r in runs[base_key]["rows"]]
        excess = [b / p - 1.0 for b, p in zip(e_base, e_plateau)]
        p_base = runs[base_key]["fit_order"]
        p_plat = runs[plateau_key]["fit_order"]
        rec = {
            "baseline_cfl": base_cfl,
            "cfl_ladder": cfls,
            "runs": runs,
            "temporal_excess_at_baseline": excess,
            "excess_coarsest": float(excess[0]),
            "excess_finest": float(excess[-1]),
            "p_baseline": p_base,
            "p_plateau": p_plat,
            "order_move": abs(p_base - p_plat),
            "spatial_admissible": bool(excess[0] <= EXCESS_TOL
                                       and abs(p_base - p_plat) <= ORDER_MOVE_TOL),
            "verdict": None,
        }
        rec["verdict"] = ("constant-CFL study is spatial-dominated at the baseline cfl"
                          if rec["spatial_admissible"] else
                          "MIXED-ORDER at the baseline cfl: temporal contribution is not "
                          "negligible; label it mixed-order and re-base any spatial claim")
        out["studies"][label] = rec

    out["overall"] = {
        "all_spatial_admissible": all(s["spatial_admissible"] for s in out["studies"].values()),
        "per_study": {k: {"excess_coarsest": v["excess_coarsest"],
                          "order_move": v["order_move"],
                          "spatial_admissible": v["spatial_admissible"]}
                      for k, v in out["studies"].items()},
        "runtime_seconds": None,
    }
    out["overall"]["runtime_seconds"] = round(time.time() - t0, 2)
    out["provenance"] = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                         "generator": "astra-lead-numerics (lead control, read-only import)",
                         "python": platform.python_version(), "numpy": np.__version__,
                         "platform": platform.platform()}

    text = json.dumps(out, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n")
    print(json.dumps({
        "all_spatial_admissible": out["overall"]["all_spatial_admissible"],
        "per_study": out["overall"]["per_study"],
        "runtime_seconds": out["overall"]["runtime_seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
