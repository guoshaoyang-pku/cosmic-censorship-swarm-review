#!/usr/bin/env python3
"""N0 constant-CFL temporal-confound control (worker deepseek-flash-13, bounded task).

Question (pre-registered).  The certified N0 spatial order-2 claim
(`numerics/tests/n0_order_4rung.json#c88146a1375c50f0`) is fitted on constant-CFL runs
(`dt = 0.5*dr`, so `dt` and `dr` refine together).  Protocol revision 3 section 3.4 says
spatial order must be measured with a *fixed, small dt* and that "`dt ∝ h` runs are
reported as mixed-order and never quoted as spatial".  Independent review
`w067-review-gnum-protocol-r3-20260912T002256` (verdict revise, F1 major) records exactly
that contradiction and asks for scoping in a rev 4.  Because both the spatial error and
the (leapfrog / Crank-Nicolson) temporal error are O(dr^2) under constant CFL, the
published fit mixes two same-order error terms.  This control isolates the spatial term.

Method.  Re-run the same three frozen schemes (`lffd`, `cnfd`, `cnfem`) on the same four
resolutions `dr = 0.2/0.1/0.05/0.025` (`r_max=30`, `t_end=6`, same Gaussian pulse) with
`dt` held fixed at `1e-4` (protocol section 3.4's own value), so temporal error is
O(1e-8) and negligible against the O(1e-4) spatial error.  A secondary fixed `dt = 1e-3`
run checks that the measured spatial order is dt-independent over four decades.

Positive control.  Before the control runs, the runner reproduces all 12 published
constant-CFL `l2_error` rows of `n0_order_4rung.json` from the frozen module; the run is
void unless they match to `<= 1e-9` relative.

Pre-registered decision rule (written before the control runs; see `decision_rule`).
  * control invalid  -> positive control mismatch, or a non-finite/step-cap failure;
  * SUPPORTED        -> every scheme at fixed dt=1e-4 is monotone, |p-2.0| <= 0.3, and
                        every pairwise |dp| is within the R5 bound; the constant-CFL
                        claim then has measured temporal subdominance at the certified
                        configuration and rev 4 may scope section 3.4 accordingly;
  * CONFOUNDED       -> any scheme leaves the band / loses monotonicity / breaks R5; the
                        constant-CFL order-2 claim is then withdrawn as spatial evidence
                        pending a fixed-dt recertification.

No gate verdict, no node completion, no self-pass.  Flat-space N0 calibration only:
numerics_lock stays LOCKED and no self-gravitating solver is written or run.

Usage:  python3 artifacts/flash-13/n0_dt_confound/dt_confound_control.py
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "numerics" / "tests"))
import flat_wave_replication as rep  # noqa: E402

FROZEN_MODULE = ROOT / "numerics" / "tests" / "flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
PUBLISHED_4RUNG = ROOT / "numerics" / "tests" / "n0_order_4rung.json"
PROTOCOL = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
DR_VALUES = [0.2, 0.1, 0.05, 0.025]
SCHEMES = ["lffd", "cnfd", "cnfem"]
R_MAX, T_END = 30.0, 6.0
P_EXPECTED, P_TOL = 2.0, 0.3
FIXED_DT_PRIMARY = 1.0e-4
FIXED_DT_SECONDARY = 1.0e-3
OUT = HERE / "dt_confound_control.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_final(scheme: str, dr: float, dt: float, pulse=None):
    """Run to t_end with a fixed dt, keeping only the final state (memory-safe).

    Semantics match the frozen module's `run_case` stopping rule exactly, so final
    states at the same (dr, dt) are bitwise comparable with published runs.
    """
    pulse = pulse or rep.PulseExact()
    r = rep.grid(R_MAX, dr)
    solver = rep.make_factory(scheme, pulse=pulse)(r, dt)
    cap = int(math.ceil(T_END / dt)) * 10 + 100
    steps = 0
    while solver.t < T_END - 1e-12:
        solver.step()
        steps += 1
        if steps > cap:
            raise RuntimeError(f"step cap exceeded scheme={scheme} dr={dr} dt={dt}")
    return r, solver, steps


def measure(scheme: str, dr: float, dt: float, pulse) -> dict:
    r, solver, steps = run_final(scheme, dr, dt, pulse)
    err = rep.l2_error(solver.psi, pulse.psi(r, solver.t), dr)
    err_u = rep.l2_error(
        solver.psi / np.maximum(r, 1e-300), pulse.psi(r, solver.t) / np.maximum(r, 1e-300), dr
    )
    if not np.all(np.isfinite(solver.psi)):
        raise FloatingPointError(f"non-finite state scheme={scheme} dr={dr} dt={dt}")
    return {
        "scheme": scheme, "dr": dr, "dt": dt, "steps": int(steps), "final_t": float(solver.t),
        "cfl": dt / dr, "l2_error": float(err), "l2_error_u": float(err_u),
    }


def slope_uncertainty(drs, errs, fit_p):
    """R5 delta = max(pair-spread half-range, least-squares slope standard error)."""
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


def study(scheme: str, dt: float, pulse, err_key: str = "l2_error") -> dict:
    rows = [measure(scheme, dr, dt, pulse) for dr in DR_VALUES]
    errs = [r[err_key] for r in rows]
    p = rep.fit_order(DR_VALUES, errs)
    unc = slope_uncertainty(DR_VALUES, errs, p)
    return {
        "scheme": scheme, "dt": dt, "norm_fitted": err_key, "rows": rows,
        "fit_order": p, "pair_orders": rep.pair_orders(DR_VALUES, errs),
        "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
        "within_band": bool(abs(p - P_EXPECTED) <= P_TOL),
        **unc,
    }


def r5_agree(a, b):
    lhs = abs(a["fit_order"] - b["fit_order"])
    rhs = max(0.25, math.sqrt(a["delta"] ** 2 + b["delta"] ** 2))
    return {"pair": f"{a['scheme']} vs {b['scheme']}", "abs_order_diff": float(lhs),
            "r5_bound": float(rhs), "agree": bool(lhs <= rhs)}


def main() -> int:
    t0 = time.time()
    frozen_sha = sha256(FROZEN_MODULE)
    if frozen_sha != FROZEN_SHA:
        print(f"REFUSE: frozen module sha256 {frozen_sha} != controller-verified {FROZEN_SHA}")
        return 2

    published = json.loads(PUBLISHED_4RUNG.read_text())
    published_studies = {s["scheme"]: s for s in published["studies"]}
    pulse = rep.PulseExact()

    # ---- positive control: reproduce all 12 published constant-CFL rows -------------
    control_rows, max_rel = [], 0.0
    for scheme in SCHEMES:
        for row in published_studies[scheme]["rows"]:
            got = measure(scheme, row["dr"], row["dt"], pulse)
            rel = abs(got["l2_error"] - row["l2_error"]) / abs(row["l2_error"])
            max_rel = max(max_rel, rel)
            control_rows.append({
                "scheme": scheme, "dr": row["dr"], "dt": row["dt"],
                "published_l2_error": row["l2_error"], "rerun_l2_error": got["l2_error"],
                "rel_diff": rel, "steps_match": got["steps"] == row["steps"],
            })
    control_ok = max_rel <= 1e-9 and all(r["steps_match"] for r in control_rows)

    # ---- fixed-dt spatial studies ---------------------------------------------------
    studies = {f"{dt:.0e}": [study(s, dt, pulse) for s in SCHEMES]
               for dt in (FIXED_DT_PRIMARY, FIXED_DT_SECONDARY)}

    primary = studies[f"{FIXED_DT_PRIMARY:.0e}"]
    secondary = studies[f"{FIXED_DT_SECONDARY:.0e}"]
    primary_pairs = [r5_agree(a, b) for i, a in enumerate(primary) for b in primary[i + 1:]]
    secondary_pairs = [r5_agree(a, b) for i, a in enumerate(secondary) for b in secondary[i + 1:]]

    primary_ok = (all(s["monotone"] and s["within_band"] for s in primary)
                  and all(p["agree"] for p in primary_pairs))
    dt_stable = all(
        abs(a["fit_order"] - b["fit_order"]) <= 0.05
        for a, b in zip(primary, secondary)
    )

    # ---- per-scheme comparison against the published constant-CFL fit --------------
    comparison = []
    for s in SCHEMES:
        pub = published_studies[s]
        pri = next(x for x in primary if x["scheme"] == s)
        excess = []
        for pr, cr in zip(pri["rows"], pub["rows"]):
            excess.append({
                "dr": pr["dr"],
                "fixed_dt_l2_error": pr["l2_error"],
                "constant_cfl_l2_error": cr["l2_error"],
                "temporal_excess": cr["l2_error"] - pr["l2_error"],
                "relative_excess": (cr["l2_error"] - pr["l2_error"]) / pr["l2_error"],
            })
        comparison.append({
            "scheme": s,
            "constant_cfl_fit": pub["fit_order"],
            "fixed_dt_fit": pri["fit_order"],
            "fixed_dt_fit_secondary": next(x for x in secondary if x["scheme"] == s)["fit_order"],
            "abs_fit_diff_vs_constant_cfl": abs(pub["fit_order"] - pri["fit_order"]),
            "per_rung_excess": excess,
        })

    if not control_ok:
        verdict, detail = "control_invalid", "positive control mismatch; no inferential use"
    elif primary_ok:
        verdict, detail = "SUPPORTED", (
            "all three schemes at fixed dt=1e-4 are monotone, inside |p-2.0|<=0.3, and R5-agree; "
            "constant-CFL temporal subdominance is measured at the certified configuration"
        )
    else:
        verdict, detail = "CONFOUNDED", (
            "at least one scheme at fixed dt=1e-4 is non-monotone, outside the band, or breaks R5; "
            "the constant-CFL order-2 claim must be withdrawn as spatial evidence"
        )

    rec = {
        "schema_version": "0.1",
        "artifact": "artifacts/flash-13/n0_dt_confound/dt_confound_control.py",
        "result": "artifacts/flash-13/n0_dt_confound/dt_confound_control.json",
        "author": "deepseek-flash-13",
        "author_role": "bounded execution worker; author of the N0 replication, not of the protocol",
        "assignment_source": (
            "worker-proposed from the immediate queue (ASTRA_HANDOFF.md 'Immediate queue: N0') to "
            "resolve the live G-NUM blocking finding w067-review-gnum-protocol-r3 F1; no lead assignment "
            "was open for flash-13 at write time (FORM-GATE-01 and astra-numfix-02 closed 00:25/00:09)"
        ),
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": (
            "Is the certified constant-CFL (dt=0.5*dr) 4-rung spatial order-2 claim contaminated by "
            "temporal error, given CONVERGENCE_PROTOCOL.md rev3 section 3.4 forbids quoting dt-proportional-h "
            "runs as spatial evidence?"
        ),
        "decision_rule": (
            "control_invalid if the 12-row positive control mismatches (>1e-9 rel) or a run fails; "
            "SUPPORTED iff every scheme at fixed dt=1e-4 is monotone, |p-2.0|<=0.3 and all pairwise |dp| "
            "within R5; CONFOUNDED otherwise (withdraw the constant-CFL order claim)."
        ),
        "evidence_refs": {
            "numerics/CONVERGENCE_PROTOCOL.md": sha256(PROTOCOL),
            "numerics/tests/n0_order_4rung.json": sha256(PUBLISHED_4RUNG),
            "numerics/tests/flat_wave_replication.py": frozen_sha,
        },
        "config": {
            "dr_values": DR_VALUES, "r_max": R_MAX, "t_end": T_END, "pulse": "Gaussian, PulseExact",
            "fixed_dt_primary": FIXED_DT_PRIMARY, "fixed_dt_secondary": FIXED_DT_SECONDARY,
            "p_expected": P_EXPECTED, "p_tol": P_TOL,
            "constant_cfl_reference": "dt = 0.5*dr as published in n0_order_4rung.json",
        },
        "provenance": {
            "frozen_module": "numerics/tests/flat_wave_replication.py",
            "frozen_module_sha256": frozen_sha,
            "module_hash_guard": "refuses to run if the frozen module changed",
            "python": sys.version.split()[0], "numpy": np.__version__, "platform": platform.platform(),
            "determinism": "no RNG; identical inputs reproduce identical final states",
            "wall_seconds": None,
        },
        "positive_control": {
            "description": "runner reproduces all 12 published constant-CFL l2_error rows",
            "ok": control_ok, "max_rel_diff": max_rel, "rows": control_rows,
        },
        "studies_fixed_dt": studies,
        "pairwise_agreement_R5_fixed_dt": {f"{FIXED_DT_PRIMARY:.0e}": primary_pairs,
                                           f"{FIXED_DT_SECONDARY:.0e}": secondary_pairs},
        "comparison_vs_constant_cfl": comparison,
        "dt_stability": {"max_fit_diff_1e-4_vs_1e-3": max(
            abs(a["fit_order"] - b["fit_order"]) for a, b in zip(primary, secondary)),
            "stable_within_0.05": bool(dt_stable)},
        "verdict": {"status": verdict, "detail": detail,
                    "constant_cfl_claim_supported": bool(control_ok and primary_ok)},
        "falsifier": (
            "re-running this driver at frozen module sha 8ade1cdc yields a scheme at fixed dt=1e-4 that is "
            "non-monotone, outside |p-2.0|<=0.3, or breaks the R5 pairwise bound; or the positive control "
            "fails to reproduce the published constant-CFL rows; or an independent re-run shows the final "
            "states here differ from the frozen module at the same (dr, dt)"
        ),
        "not_claimed": [
            "no gate verdict and no gate self-pass; G-NUM stays pending and this is reviewer evidence only",
            "no node completion; N0 stays active and numerics_lock stays LOCKED",
            "no modification of the protocol, the frozen module, or any canonical artifact",
            "no physics claim; flat-space numerical calibration evidence only",
        ],
    }
    rec["provenance"]["wall_seconds"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(OUT.relative_to(ROOT)), "sha256": sha256(OUT),
        "positive_control_ok": control_ok, "max_rel_diff": max_rel,
        "verdict": verdict,
        "fixed_dt_fits": {s["scheme"]: round(s["fit_order"], 6) for s in primary},
        "constant_cfl_fits": {s: round(published_studies[s]["fit_order"], 6) for s in SCHEMES},
        "wall_seconds": rec["provenance"]["wall_seconds"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
