"""N0 acceptance harness: measure, do not trust.

The harness drives a solver under test through three independent gates and
combines them into one verdict:

1. **Convergence order** -- refine the grid (``dr``, and ``dt = cfl*dr``) over
   >= 3 levels and fit ``log L2_error`` vs ``log dr``.  PASS requires the fitted
   slope to be within ``p_tol`` of the declared order *and* errors to decrease
   monotonically.
2. **Invariant conservation** -- the harness itself recomputes the leapfrog
   discrete energy from the states the solver exposes (``psi`` and ``psi_prev``)
   and measures the maximum relative drift.  A solver that does not expose
   ``psi_prev`` gets INCONCLUSIVE, never PASS: missing evidence is not evidence.
3. **Stability** -- run the finest grid at several CFL numbers; non-finite state
   or amplitude growth beyond ``max_growth_tol`` is a hard FAIL.

Verdict combination: any FAIL -> FAIL; else any INCONCLUSIVE -> INCONCLUSIVE;
else PASS.  INCONCLUSIVE is a first-class outcome and must not be reported as
success (HANDOFF.md: "HTTP success, output length, or agent consensus is not
completion").

Everything here is deterministic: no clocks, no randomness, no network, no I/O
beyond what the caller passes in.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Callable, Optional

import numpy as np

from reference_solutions import GaussianPulse

__all__ = [
    "DEFAULT_CONFIG",
    "grid",
    "l2_error",
    "fit_order",
    "discrete_energy",
    "run_case",
    "measure_order",
    "measure_invariant",
    "check_stability",
    "evaluate",
    "report_digest",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "dr_values": (0.2, 0.1, 0.05),
    "cfl_order": 0.5,
    "cfl_stability": (0.25, 0.5, 0.8),
    "stability_dr": None,  # None -> finest dr_values
    "r_max": 30.0,
    "t_end": 6.0,
    "p_expected": 2.0,
    "p_tol": 0.3,
    "drift_tol": 1e-6,
    "invariant_sample_every": 4,
    "max_growth_tol": 50.0,
    "min_levels": 3,
}

TINY = 1e-300


def grid(r_max: float, dr: float) -> np.ndarray:
    """Uniform radial grid ``0, dr, ..., <= r_max`` including both endpoints."""
    if dr <= 0.0 or r_max <= 0.0:
        raise ValueError("dr and r_max must be positive")
    n = int(round(r_max / dr))
    if n < 3:
        raise ValueError("grid too small")
    return np.linspace(0.0, n * dr, n + 1)


def l2_error(numeric, reference, dr: float) -> float:
    """Discrete L2 norm of the pointwise difference."""
    diff = np.asarray(numeric, dtype=float) - np.asarray(reference, dtype=float)
    if diff.shape != np.asarray(reference, dtype=float).shape:
        raise ValueError("shape mismatch in l2_error")
    return float(math.sqrt(float(np.sum(diff * diff)) * dr))


def fit_order(dr_values, errors) -> float:
    """Least-squares slope of ``log(error)`` against ``log(dr)``."""
    x = np.log(np.asarray(dr_values, dtype=float))
    y = np.log(np.asarray(errors, dtype=float))
    if x.size < 2 or not np.all(np.isfinite(y)):
        return float("nan")
    return float(np.polyfit(x, y, 1)[0])


def discrete_energy(psi, psi_prev, dt: float, dr: float) -> float:
    """Leapfrog discrete energy, recomputed by the harness (not self-reported).

    ``E = 1/2 sum_j [ ((psi_j - psi_prev_j)/dt)^2
                      + (psi_{j+1}-psi_j)(psi_prev_{j+1}-psi_prev_j)/dr^2 ] dr``
    """
    psi = np.asarray(psi, dtype=float)
    prev = np.asarray(psi_prev, dtype=float)
    if psi.shape != prev.shape or psi.size < 3:
        raise ValueError("energy needs matching psi/psi_prev of size >= 3")
    kin = ((psi - prev) / dt) ** 2
    grad = (psi[1:] - psi[:-1]) * (prev[1:] - prev[:-1]) / dr**2
    return float(0.5 * (float(np.sum(kin)) + float(np.sum(grad))) * dr)


def run_case(
    factory: Callable[[np.ndarray, float], Any],
    dr: float,
    cfl: float,
    r_max: float,
    t_end: float,
    sample_every: int = 1,
) -> dict:
    """Drive one solver instance from ``t=0`` to ``t_end``; return sampled states.

    Raises ``HarnessError`` if the solver overruns the step cap (a solver that
    never advances ``t`` must not hang the harness) and propagates
    ``SolverFailure`` / ``SolverTimeout`` from the solver itself.
    """
    from solvers import HarnessError  # local import keeps harness import-light

    r = grid(r_max, dr)
    dt = cfl * dr
    solver = factory(r, dt)
    times = [0.0]
    states = [np.array(solver.psi, dtype=float, copy=True)]
    prevs: list[Optional[np.ndarray]] = [None]
    step_cap = int(math.ceil(t_end / dt)) * 10 + 100
    steps = 0
    while solver.t < t_end - 1e-12:
        solver.step()
        steps += 1
        if steps > step_cap:
            raise HarnessError(
                f"step cap {step_cap} exceeded at dr={dr}, cfl={cfl}; solver t={solver.t}"
            )
        if steps % sample_every == 0 or solver.t >= t_end - 1e-12:
            times.append(float(solver.t))
            states.append(np.array(solver.psi, dtype=float, copy=True))
            p = solver.psi_prev
            prevs.append(None if p is None else np.array(p, dtype=float, copy=True))
    return {"r": r, "dt": dt, "t": times, "psi": states, "psi_prev": prevs, "steps": steps}


def _case_failure(exc: Exception) -> dict:
    return {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"}


def measure_order(factory, config: dict, exact: GaussianPulse) -> dict:
    drs = list(config["dr_values"])
    if len(drs) < config["min_levels"]:
        raise ValueError("need at least min_levels resolutions")
    errors: list[float] = []
    for dr in drs:
        try:
            case = run_case(
                factory,
                dr=dr,
                cfl=config["cfl_order"],
                r_max=config["r_max"],
                t_end=config["t_end"],
                sample_every=1,
            )
        except Exception as exc:  # solver failure is a FAIL for this gate
            return _case_failure(exc)
        ref = exact.psi(case["r"], case["t"][-1])
        err = l2_error(case["psi"][-1], ref, dr)
        if not math.isfinite(err):
            return {"status": "FAIL", "reason": f"non-finite L2 error at dr={dr}"}
        errors.append(err)
    p = fit_order(drs, errors)
    decreasing = all(errors[i + 1] < errors[i] for i in range(len(errors) - 1))
    ok = (
        math.isfinite(p)
        and abs(p - config["p_expected"]) <= config["p_tol"]
        and decreasing
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "measured_order": p,
        "expected_order": config["p_expected"],
        "tolerance": config["p_tol"],
        "errors": errors,
        "dr_values": drs,
        "monotone_decreasing": decreasing,
        "reason": "" if ok else (
            f"measured order {p:.3f} not within {config['p_tol']} of "
            f"{config['p_expected']} (monotone={decreasing})"
        ),
    }


def measure_invariant(factory, config: dict) -> dict:
    dr = config["stability_dr"] or min(config["dr_values"])
    try:
        case = run_case(
            factory,
            dr=dr,
            cfl=config["cfl_order"],
            r_max=config["r_max"],
            t_end=config["t_end"],
            sample_every=config["invariant_sample_every"],
        )
    except Exception as exc:
        return _case_failure(exc)
    energies: list[tuple[float, float]] = []
    for t, psi, prev in zip(case["t"], case["psi"], case["psi_prev"]):
        if prev is None:
            continue
        try:
            energies.append((t, discrete_energy(psi, prev, case["dt"], dr)))
        except ValueError as exc:
            return {"status": "FAIL", "reason": f"energy contract: {exc}"}
    if len(energies) < 3:
        return {
            "status": "INCONCLUSIVE",
            "reason": (
                "solver exposed <3 states with psi_prev over the run; "
                "invariant drift is not measurable, so no PASS is allowed"
            ),
            "samples": len(energies),
            "dr": dr,
        }
    e0 = energies[0][1]
    if not math.isfinite(e0) or abs(e0) < TINY:
        return {"status": "FAIL", "reason": f"degenerate reference energy {e0}"}
    drift = max(abs(e - e0) / abs(e0) for _, e in energies)
    ok = math.isfinite(drift) and drift <= config["drift_tol"]
    return {
        "status": "PASS" if ok else "FAIL",
        "relative_drift": drift,
        "drift_tol": config["drift_tol"],
        "samples": len(energies),
        "dr": dr,
        "reason": "" if ok else f"relative energy drift {drift:.3e} > {config['drift_tol']:.1e}",
    }


def check_stability(factory, config: dict) -> dict:
    dr = config["stability_dr"] or min(config["dr_values"])
    results = []
    for cfl in config["cfl_stability"]:
        try:
            case = run_case(
                factory,
                dr=dr,
                cfl=cfl,
                r_max=config["r_max"],
                t_end=config["t_end"],
                sample_every=config["invariant_sample_every"],
            )
        except Exception as exc:
            return _case_failure(exc)
        finite = all(np.all(np.isfinite(s)) for s in case["psi"])
        amp0 = float(np.max(np.abs(case["psi"][0])))
        amp = max(float(np.max(np.abs(s))) for s in case["psi"])
        growth = amp / max(amp0, TINY)
        ok = finite and growth <= config["max_growth_tol"]
        results.append({"cfl": cfl, "finite": finite, "growth": growth, "ok": ok})
    ok = all(r["ok"] for r in results)
    return {
        "status": "PASS" if ok else "FAIL",
        "dr": dr,
        "max_growth_tol": config["max_growth_tol"],
        "cases": results,
        "reason": "" if ok else "non-finite state or amplitude growth beyond tolerance",
    }


def evaluate(
    factory,
    config: Optional[dict] = None,
    exact: Optional[GaussianPulse] = None,
    label: str = "solver",
) -> dict:
    """Run all three gates and combine them into one verdict."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    exact = exact or GaussianPulse()
    order = measure_order(factory, cfg, exact)
    invariant = measure_invariant(factory, cfg)
    stability = check_stability(factory, cfg)
    gates = {"order": order, "invariant": invariant, "stability": stability}
    statuses = [g["status"] for g in gates.values()]
    if "FAIL" in statuses:
        verdict = "FAIL"
    elif "INCONCLUSIVE" in statuses:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS"
    report: dict[str, Any] = {
        "harness": "n0_flat_wave_acceptance",
        "harness_version": "0.1.0-draft",
        "label": label,
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "scope_note": "flat-space test-field scalar wave only; no self-gravity; no censorship claim",
        "verdict": verdict,
        "config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in cfg.items()},
        "gates": gates,
        "failed_gates": [k for k, g in gates.items() if g["status"] == "FAIL"],
        "inconclusive_gates": [k for k, g in gates.items() if g["status"] == "INCONCLUSIVE"],
    }
    report["report_digest"] = report_digest(report)
    return report


def report_digest(report: dict) -> str:
    """Deterministic digest of a report, excluding the digest field itself."""
    payload = {k: v for k, v in report.items() if k != "report_digest"}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()
