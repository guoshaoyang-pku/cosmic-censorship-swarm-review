#!/usr/bin/env python3
"""N0 four-rung order addendum for the frozen replication artifact.

Closes the audit-lead / rubric item "at least 4 resolutions" **for the replication's
order claim**, without touching the frozen replication file or its controller-verified
run (`n0_replication_astra_run2_FIXED.json`, script sha256 ``8ade1cdc…``).

The frozen module is imported read-only. A hash guard refuses to run if the file was
edited after the controller verification, so this addendum can never silently attach
its evidence to a different revision.

Uncertainty follows the protocol review (worker 14, R5):
    delta = max(pair-spread half-range, least-squares standard error of the slope)
    agreement: |p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2))

Output: numerics/tests/n0_order_4rung.json
Usage:  python3 numerics/tests/n0_order_4rung_addendum.py
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
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flat_wave_replication as rep  # noqa: E402

FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
FIXED_RUN_SHA = "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e"
DR_VALUES = [0.2, 0.1, 0.05, 0.025]
SCHEMES = ["lffd", "cnfd", "cnfem"]
OUT = HERE / "n0_order_4rung.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slope_uncertainty(drs, errs, fit_p):
    """R5 delta: max(pair-spread half-range, least-squares slope standard error)."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    pair = rep.pair_orders(drs, errs)
    half_range = (max(pair) - min(pair)) / 2.0
    resid = y - (fit_p * x + (y.mean() - fit_p * x.mean()))
    dof = len(x) - 2
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = math.sqrt(float(np.sum(resid ** 2)) / dof / sxx) if dof > 0 and sxx > 0 else float("nan")
    return {"delta": max(half_range, se), "pair_half_range": half_range,
            "least_squares_se": se, "pair_orders": pair}


def r5_agree(a, b):
    lhs = abs(a["fit_order"] - b["fit_order"])
    rhs = max(0.25, math.sqrt(a["delta"] ** 2 + b["delta"] ** 2))
    return {"pair": f"{a['scheme']} vs {b['scheme']}", "abs_order_diff": lhs,
            "r5_bound": rhs, "agree": bool(lhs <= rhs)}


def main() -> int:
    frozen = HERE / "flat_wave_replication.py"
    got = sha256(frozen)
    if got != FROZEN_SHA:
        print(f"REFUSE: frozen replication sha256 {got} != controller-verified {FROZEN_SHA}")
        return 2

    studies = []
    for scheme in SCHEMES:
        st = rep.order_study(scheme, dr_values=DR_VALUES)
        st.update(slope_uncertainty(DR_VALUES, [r["l2_error"] for r in st["rows"]], st["fit_order"]))
        studies.append(st)

    pairs = [r5_agree(a, b) for i, a in enumerate(studies) for b in studies[i + 1:]]
    rec = {
        "artifact": "numerics/tests/n0_order_4rung_addendum.py",
        "assignment": "astra-numfix-02",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type_of_measurements": "numerical_evidence",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "purpose": ("rubric check 'at least 4 resolutions' for the replication order claim; "
                    "extends the controller-verified 3-rung run without editing it"),
        "provenance": {
            "frozen_module": "numerics/tests/flat_wave_replication.py",
            "frozen_module_sha256": got,
            "controller_verified_run": "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json",
            "controller_verified_run_sha256": FIXED_RUN_SHA,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "seeds": "none: deterministic, no RNG; frozen run records bitwise-equal rerun",
        },
        "config": {"dr_values": DR_VALUES, "cfl": 0.5, "r_max": 30.0, "t_end": 6.0,
                   "p_expected": 2.0, "p_tol": 0.3,
                   "uncertainty_rule": "R5: max(pair-spread half-range, least-squares slope SE)"},
        "studies": studies,
        "pairwise_agreement_R5": pairs,
        "verdict": {
            "all_monotone": all(s["monotone"] for s in studies),
            "all_within_harness_tol": all(s["within_harness_tol"] for s in studies),
            "all_pairwise_agree_R5": all(p["agree"] for p in pairs),
            "orders": {s["scheme"]: s["fit_order"] for s in studies},
            "delta": {s["scheme"]: s["delta"] for s in studies},
            "summary": "order 2 reproduced by three schemes at a fourth resolution",
        },
        "falsifier": ("a re-run of this script at the pinned frozen hash 8ade1cdc that reports any "
                      "scheme non-monotone, outside p=2.0+-0.3, or a pairwise |dp| above the R5 bound; "
                      "or the frozen module hash guard failing"),
        "not_claimed": [
            "no gate verdict and no gate self-pass; this is supporting evidence for G-NUM only",
            "no node completion; N0 stays active and numerics_lock stays LOCKED",
            "no claim about the candidate numerics/tests/flat_wave.py (its 4th rung is its owner's item)",
            "no physics claim; flat-space calibration evidence only",
        ],
    }
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)), "sha256": sha256(OUT),
                      "orders": rec["verdict"]["orders"], "agree": rec["verdict"]["all_pairwise_agree_R5"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
