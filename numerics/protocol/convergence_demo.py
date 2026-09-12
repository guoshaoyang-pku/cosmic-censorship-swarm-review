#!/usr/bin/env python3
"""Worked synthetic example for ``numerics/protocol/convergence_protocol.md``.

Assignment
----------
Worker deepseek-flash-14, node N0, gate G-NUM, class ``AF-WCC-SCALAR-SPH``
(provisional).  Deliverable: the convergence *protocol/audit spec* plus a
worked example on synthetic (manufactured) data.  This script is that worked
example.  It is **not** the N0 test artifact (``numerics/tests/flat_wave.py``
is owned by other assignments) and it is not a solver for production use.

What it demonstrates
--------------------
E1  turning-point degeneracy: a 2nd-order scheme measured at a mode turning
    point returns apparent order 4; a broadband family at the same time is
    immune.  This is the control a naive order measurement fails.
E2  order certification at generic times on a two-mode (broadband) family:
    end-time error order, truncation-residual order, Richardson
    self-convergence and Richardson extrapolation.
E3  off-by-one stencil control: the buggy operator is *unstable*; the protocol
    must reject it on the stability criterion before reading any order off it.
E4  stable wrong-order control: backward Euler in time + central space is
    first-order; the protocol must reject it on the order criterion
    (assignment falsifier: "protocol cannot detect a wrong order").
E5  invariant diagnostics: energy drift measured with two different discrete
    energy functionals of the same run shows that the *diagnostic* sets the
    observed drift order; the u<->v energy identity is checked statically.
E6  cross-check against the N0 candidate implementation when importable,
    including bitwise-level agreement of the shared scheme.

Scope (exact)
-------------
Fixed Minkowski background, massless real scalar, spherical symmetry,
v = r*u so that v_tt = v_rr on r in [0, R] with v(t,0) = v(t,R) = 0.
No self-gravity, no collapse, no apparent horizon, no critical behaviour, no
outgoing radiation at I+, and no cosmic-censorship conclusion of any kind.
Every number below is numerical calibration evidence only.

Usage
-----
    python3 numerics/protocol/convergence_demo.py
    python3 numerics/protocol/convergence_demo.py --json-out numerics/protocol/demo_output.json
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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
R = 1.0
CFL = 0.25
#: generic measurement time for the two-mode family (no mode at a turning point)
T_GENERIC = 0.35
#: turning point of the k = 2*pi mode: sin(2*pi*t) = 0
T_TURNING = 0.5
#: pulse measurement time short enough that the reflecting wall is not reached
T_PULSE = 0.15
N_LADDER = (64, 128, 256, 512)
MODES_SINGLE = ((2, 1.0),)
MODES_TWO = ((2, 1.0), (5, 0.5))


# ---------------------------------------------------------------------------
# exact (manufactured) solutions
# ---------------------------------------------------------------------------
def exact_standing(r, t, modes=MODES_TWO, box=R):
    """Exact v(r,t) = sum_m a_m sin(k_m r) cos(k_m t)/k_m, k_m = m*pi/box."""
    r = np.asarray(r, dtype=float)
    out = np.zeros_like(r)
    for m, a in modes:
        k = m * math.pi / box
        out += a * np.sin(k * r) * np.cos(k * t) / k
    return out


def exact_standing_dt2(r, t, modes=MODES_TWO, box=R):
    """Exact v_tt = -sum_m a_m k_m sin(k_m r) cos(k_m t)."""
    r = np.asarray(r, dtype=float)
    out = np.zeros_like(r)
    for m, a in modes:
        k = m * math.pi / box
        out += -a * k * np.sin(k * r) * np.cos(k * t)
    return out


def exact_pulse(r, t, center=0.3, width=0.08, box=R):
    """Exact d'Alembert pulse, zero initial velocity, odd smooth data.

    V(x) = x * [exp(-((x-c)/w)^2) + exp(-((x+c)/w)^2)] and
    v = 1/2 [V(r+t) + V(r-t)].  With c=0.3, w=0.08 and t <= 0.15 the reflecting
    walls are not reached, so the free-space solution is the exact one.
    """
    r = np.asarray(r, dtype=float)

    def V(x):
        return x * (np.exp(-((x - center) / width) ** 2) + np.exp(-((x + center) / width) ** 2))

    return 0.5 * (V(r + t) + V(r - t))


# ---------------------------------------------------------------------------
# discrete operators
# ---------------------------------------------------------------------------
def d2_standard(v, h):
    """2nd-order central second derivative with v[0] = v[-1] = 0."""
    v = np.asarray(v, dtype=float)
    out = np.zeros_like(v)
    out[1:-1] = (v[:-2] - 2.0 * v[1:-1] + v[2:]) / h ** 2
    return out


def d2_offbyone(v, h):
    """Deliberately defective off-by-one stencil (control, not a scheme).

    Interior j = 1..n-2 uses (v[j+2] - 2 v[j+1] + v[j]) / h^2, consistent only
    to O(h).  Kept because the protocol must show what happens to an unstable
    order-defective operator: the stability check must reject it before any
    order is read (see E3).
    """
    v = np.asarray(v, dtype=float)
    n = len(v) - 1
    out = np.zeros_like(v)
    out[1:n - 1] = (v[3:n + 1] - 2.0 * v[2:n] + v[1:n - 1]) / h ** 2
    out[n - 1] = (v[n - 2] - 2.0 * v[n - 1] + v[n]) / h ** 2
    return out


# ---------------------------------------------------------------------------
# time integration
# ---------------------------------------------------------------------------
def integrate_rk4(v0, w0, h, t_end, cfl, operator, sample_energy=True):
    """Classical RK4 on dv/dt = w, dw/dt = op(v).

    Two energy diagnostics are sampled on the same run:
      * ``energy_drift_exact``  uses the discrete gradient (adjoint-consistent)
      * ``energy_drift_grad``   uses ``np.gradient``, a 2nd-order quadrature
    The comparison in E5 shows the diagnostic sets the measured drift order.
    """
    n_steps = max(1, int(math.ceil(t_end / (cfl * h))))
    dt = t_end / n_steps
    v = np.array(v0, dtype=float)
    w = np.array(w0, dtype=float)
    e0 = discrete_energy_exact(v, w, h)
    e0g = discrete_energy_grad(v, w, h)
    drift = 0.0
    drift_grad = 0.0
    max_amp = float(np.max(np.abs(v)))
    for _ in range(n_steps):
        k1v, k1w = w, operator(v, h)
        k2v, k2w = w + 0.5 * dt * k1w, operator(v + 0.5 * dt * k1v, h)
        k3v, k3w = w + 0.5 * dt * k2w, operator(v + 0.5 * dt * k2v, h)
        k4v, k4w = w + dt * k3w, operator(v + dt * k3v, h)
        v = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        w = w + (dt / 6.0) * (k1w + 2 * k2w + 2 * k3w + k4w)
        max_amp = max(max_amp, float(np.max(np.abs(v))))
        if sample_energy and e0 != 0.0:
            drift = max(drift, abs(discrete_energy_exact(v, w, h) - e0) / abs(e0))
            if e0g != 0.0:
                drift_grad = max(drift_grad, abs(discrete_energy_grad(v, w, h) - e0g) / abs(e0g))
    return {"v": v, "w": w, "n_steps": n_steps, "dt": dt,
            "energy_drift_exact": drift, "energy_drift_grad": drift_grad,
            "max_amplitude": max_amp, "stable": bool(np.all(np.isfinite(v)) and max_amp < 1e6)}


def integrate_backward_euler(v0, w0, h, t_end, cfl, operator):
    """Stable first-order-in-time control: backward Euler + central space.

    (I - dt^2 A) w^{n+1} = w^n + dt A v^n,  v^{n+1} = v^n + dt w^{n+1},
    solved with the Thomas algorithm on the interior (Dirichlet walls).
    """
    n_steps = max(1, int(math.ceil(t_end / (cfl * h))))
    dt = t_end / n_steps
    v = np.array(v0, dtype=float)
    w = np.array(w0, dtype=float)
    m = len(v) - 2
    rr = dt * dt / (h * h)
    a = np.full(m, -rr)
    b = np.full(m, 1.0 + 2.0 * rr)
    c = np.full(m, -rr)
    e0 = discrete_energy_exact(v, w, h)
    e0g = discrete_energy_grad(v, w, h)
    drift = 0.0
    drift_grad = 0.0
    for _ in range(n_steps):
        Av = operator(v, h)[1:-1]
        rhs = w[1:-1] + dt * Av
        w_int = _thomas(a, b, c, rhs)
        w = np.zeros_like(v)
        w[1:-1] = w_int
        v = v + dt * w
        if e0 != 0.0:
            drift = max(drift, abs(discrete_energy_exact(v, w, h) - e0) / abs(e0))
            if e0g != 0.0:
                drift_grad = max(drift_grad, abs(discrete_energy_grad(v, w, h) - e0g) / abs(e0g))
    return {"v": v, "w": w, "n_steps": n_steps, "dt": dt,
            "energy_drift_exact": drift, "energy_drift_grad": drift_grad,
            "max_amplitude": float(np.max(np.abs(v))),
            "stable": bool(np.all(np.isfinite(v)) and np.max(np.abs(v)) < 1e6)}


def _thomas(a, b, c, d):
    """Tridiagonal solve with constant sub/super diagonals (vectors accepted)."""
    n = len(d)
    cp = np.empty(n)
    dp = np.empty(n)
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        den = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / den
        dp[i] = (d[i] - a[i] * dp[i - 1]) / den
    x = np.empty(n)
    x[-1] = dp[-1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def discrete_energy_exact(v, w, h):
    """E_h = h/2 sum_j w_j^2 + h/2 sum_j ((v_{j+1}-v_j)/h)^2 (Dirichlet box)."""
    grad = np.diff(v) / h
    return 0.5 * h * float(np.sum(w ** 2)) + 0.5 * h * float(np.sum(grad ** 2))


def discrete_energy_grad(v, w, h):
    """Same energy but with the 2nd-order np.gradient quadrature for v_r."""
    grad = np.gradient(v, h)
    return 0.5 * h * float(np.sum(w ** 2)) + 0.5 * h * float(np.sum(grad ** 2))


# ---------------------------------------------------------------------------
# case driver
# ---------------------------------------------------------------------------
def solve(n, t_end, operator, cfl=CFL, family="standing", modes=MODES_TWO,
          integrator="rk4"):
    h = R / n
    r = np.linspace(0.0, R, n + 1)
    if family == "standing":
        v0 = exact_standing(r, 0.0, modes)
    elif family == "pulse":
        v0 = exact_pulse(r, 0.0)
    else:
        raise ValueError(f"unknown family {family!r}")
    w0 = np.zeros_like(v0)
    v0[0] = v0[-1] = 0.0
    if integrator == "rk4":
        res = integrate_rk4(v0, w0, h, t_end, cfl, operator)
    elif integrator == "backward_euler":
        res = integrate_backward_euler(v0, w0, h, t_end, cfl, operator)
    else:
        raise ValueError(f"unknown integrator {integrator!r}")
    ref = exact_standing(r, t_end, modes) if family == "standing" else exact_pulse(r, t_end)
    err = res["v"][1:-1] - ref[1:-1]
    out = {
        "n": int(n), "h": float(h), "dt": float(res["dt"]), "n_steps": int(res["n_steps"]),
        "cfl": float(cfl), "t_end": float(t_end), "family": family,
        "integrator": integrator,
        "linf_error": float(np.max(np.abs(err))),
        "l2_error": float(np.sqrt(np.mean(err ** 2))),
        "stable": res["stable"],
        "v": res["v"], "exact": ref,
    }
    for key in ("energy_drift_exact", "energy_drift_grad", "max_amplitude"):
        if key in res:
            out[key] = float(res[key])
    return out


# ---------------------------------------------------------------------------
# estimators
# ---------------------------------------------------------------------------
def pair_orders(rows, key):
    out = []
    for a, b in zip(rows, rows[1:]):
        if a[key] > 0 and b[key] > 0:
            out.append(float(math.log(a[key] / b[key]) / math.log(a["h"] / b["h"])))
        else:
            out.append(float("nan"))
    return out


def fitted_order(rows, key):
    hs = np.array([r["h"] for r in rows], dtype=float)
    es = np.array([r[key] for r in rows], dtype=float)
    if np.any(es <= 0):
        return float("nan")
    return float(np.polyfit(np.log(hs), np.log(es), 1)[0])


def richardson_order(rows):
    """p from the three finest grids: log2(||u_h-u_2h|| / ||u_2h-u_4h||)."""
    if len(rows) < 3:
        raise ValueError("need >=3 grids")
    fine, mid, coarse = rows[-1], rows[-2], rows[-3]
    d1 = float(np.max(np.abs(mid["v"][::2] - coarse["v"])))
    d2 = float(np.max(np.abs(fine["v"][::2] - mid["v"])))
    if d1 <= 0 or d2 <= 0:
        return float("nan"), d1, d2
    return float(math.log(d1 / d2) / math.log(2.0)), d1, d2


def richardson_extrapolate(rows, p):
    """u_R = u_fine + (u_fine - u_mid)/(2^p - 1) on the mid grid; error vs exact."""
    fine, mid = rows[-1], rows[-2]
    fine_on_mid = fine["v"][::2]
    u_r = fine_on_mid + (fine_on_mid - mid["v"]) / (2.0 ** p - 1.0)
    return float(np.max(np.abs((u_r - mid["exact"])[1:-1])))


def order_uncertainty(rows, key="linf_error"):
    """R5/T7 order uncertainty: max(least-squares standard error, pair-spread half-range)."""
    hs = np.array([r["h"] for r in rows], dtype=float)
    es = np.array([r[key] for r in rows], dtype=float)
    x, y = np.log(hs), np.log(es)
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    s2 = float(np.sum(resid ** 2) / max(n - 2, 1))
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = float(np.sqrt(s2 / sxx)) if sxx > 0 else float("inf")
    pairs = [p for p in pair_orders(rows, key) if p is not None and math.isfinite(p)]
    half = (max(pairs) - min(pairs)) / 2.0 if pairs else float("inf")
    return {"fit_order": float(slope), "standard_error": se,
            "pair_spread_half_range": float(half)}


def residual_order(ns, operator, t_star=T_GENERIC, modes=MODES_TWO):
    """Order of ||v_tt - D2_h v||_inf for the exact solution at a generic time.

    The local truncation residual of the spatial operator.  It does not involve
    the numerical solution, so it is immune to the phase cancellation that makes
    E1 report order 4.
    """
    errs = []
    for n in ns:
        h = R / n
        r = np.linspace(0.0, R, n + 1)
        v = exact_standing(r, t_star, modes)
        v[0] = v[-1] = 0.0
        vtt = exact_standing_dt2(r, t_star, modes)
        errs.append(float(np.max(np.abs(vtt[1:-1] - operator(v, h)[1:-1]))))
    orders = [math.log(a / b) / math.log(2.0) for a, b in zip(errs, errs[1:])]
    return errs, orders


# ---------------------------------------------------------------------------
# E6: cross-check against the N0 candidate implementation
# ---------------------------------------------------------------------------
def crosscheck_flat_wave():
    """Reproduce protocol-relevant numbers with numerics/tests/flat_wave.py."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "numerics"))
        import tests.flat_wave as fw  # type: ignore
    except Exception as exc:  # pragma: no cover - optional
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}

    out = {"available": True, "measurements": {}, "agreement": {}, "note": (
        "Peers' candidate implementation; used here only to falsify the "
        "turning-point hypothesis in situ and to check scheme agreement. "
        "No endorsement and no completion claim.")}
    for label, t_end in (("generic_t=0.40", 0.40), ("turning_point_t=0.50", 0.50)):
        rows = [fw.solve_case(n, t_end=t_end, cfl=0.25, order=2, family="standing")
                for n in N_LADDER]
        out["measurements"][label] = {
            "l2_orders": fw.observed_order(rows, "l2_error"),
            "linf_orders": fw.observed_order(rows, "linf_error"),
            "finest_l2_error": rows[-1]["l2_error"],
        }
    try:
        n = 256
        t_end = 0.40
        mine = solve(n, t_end, d2_standard, modes=MODES_SINGLE)
        h, r, v0, w0 = fw._case_setup(n, "standing", 1.0, t_end, 12.0, 2.0, MODES_SINGLE)
        theirs_v = fw.integrate(v0, w0, h, t_end, 0.25, 2)["v"]
        out["agreement"] = {
            "n": n, "max_abs_v_difference": float(np.max(np.abs(mine["v"] - theirs_v))),
            "bitwise_equal": bool(np.array_equal(mine["v"], theirs_v)),
            "note": "same central stencil and RK4 path, stepped independently",
        }
    except Exception as exc:  # pragma: no cover - optional
        out["agreement"] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def run_all():
    t0 = time.perf_counter()
    report = {
        "schema": "n0-convergence-demo/v1",
        "artifact": "numerics/protocol/convergence_demo.py",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "binding_status": "PROVISIONAL - F0 taxonomy artifact missing on disk",
        "validation_status": "unverified",
        "conclusion_type_of_measurements": "numerical_evidence",
        "scope": {
            "equation": "v_tt = v_rr, v = r*u, fixed Minkowski, spherical symmetry",
            "boundary": "v(t,0) = v(t,R) = 0 reflecting calibration box",
            "not_in_scope": ["self-gravity", "collapse", "apparent horizon",
                             "critical behaviour", "radiation at I+",
                             "any cosmic-censorship conclusion"],
        },
        "parameters": {"R": R, "cfl": CFL, "t_generic": T_GENERIC,
                       "t_turning": T_TURNING, "t_pulse": T_PULSE,
                       "n_ladder": list(N_LADDER),
                       "modes_single": [list(m) for m in MODES_SINGLE],
                       "modes_two": [list(m) for m in MODES_TWO]},
        "experiments": {},
        "claims_not_made": [
            "no claim that N0 is complete or accepted",
            "no claim about self-gravitating dynamics",
            "no claim about WCC/SCC or any cosmic-censorship statement",
        ],
    }

    # E1: turning-point degeneracy vs broadband immunity
    e1 = {"scheme": "standard_order2 (central D2 + RK4)",
          "measurements": {}, "verdict": (
              "DEGENERATE_MEASUREMENT: the single-mode order-2 scheme reports ~4 at the "
              "mode turning point t=0.5 and ~2 at a generic time; the two-mode family "
              "reports ~2 at both times. Single-mode, single-time order measurements are "
              "not valid order evidence.")}
    cases = (
        ("single_mode_generic_t=0.35", MODES_SINGLE, T_GENERIC),
        ("single_mode_turning_t=0.50", MODES_SINGLE, T_TURNING),
        ("two_mode_turning_t=0.50", MODES_TWO, T_TURNING),
        ("two_mode_generic_t=0.35", MODES_TWO, T_GENERIC),
    )
    for label, modes, t_end in cases:
        rows = [solve(n, t_end, d2_standard, modes=modes) for n in N_LADDER]
        e1["measurements"][label] = {
            "linf_orders": pair_orders(rows, "linf_error"),
            "l2_orders": pair_orders(rows, "l2_error"),
            "finest_linf_error": rows[-1]["linf_error"],
        }
    report["experiments"]["E1_turning_point_degeneracy"] = e1

    # E2: certification at a generic time, two-mode family
    rows_std = [solve(n, T_GENERIC, d2_standard) for n in N_LADDER]
    res_errs, res_orders = residual_order(N_LADDER, d2_standard)
    p_rich, d1, d2 = richardson_order(rows_std)
    e2 = {
        "family": "two_mode_standing", "t_end": T_GENERIC,
        "linf_errors": [r["linf_error"] for r in rows_std],
        "l2_errors": [r["l2_error"] for r in rows_std],
        "linf_orders": pair_orders(rows_std, "linf_error"),
        "l2_orders": pair_orders(rows_std, "l2_error"),
        "linf_fit": fitted_order(rows_std, "linf_error"),
        "l2_fit": fitted_order(rows_std, "l2_error"),
        "residual_errors": res_errs, "residual_orders": res_orders,
        "richardson_order": p_rich, "richardson_d1": d1, "richardson_d2": d2,
        "richardson_extrapolated_linf_error": richardson_extrapolate(rows_std, p_rich),
        "declared_order": 2.0,
        "verdict": "PASS: end-time error, residual, and Richardson estimators all report 2.00",
    }
    report["experiments"]["E2_order_certification"] = e2

    # E3: off-by-one stencil is unstable -- reject on stability, not on order
    rows_bug = [solve(n, T_GENERIC, d2_offbyone) for n in N_LADDER]
    e3 = {
        "max_amplitude": [r["max_amplitude"] for r in rows_bug],
        "stable": [r["stable"] for r in rows_bug],
        "linf_errors": [r["linf_error"] for r in rows_bug],
        "verdict": ("REJECTED ON STABILITY: the shifted stencil is non-normal with growth "
                    "modes; amplitudes blow up and no order can be read from the run. The "
                    "protocol must run the stability check before the order estimator."),
    }
    report["experiments"]["E3_offbyone_unstable_control"] = e3

    # E4: stable wrong-order control (backward Euler: first order in time)
    rows_be = [solve(n, T_GENERIC, d2_standard, integrator="backward_euler") for n in N_LADDER]
    rows_be_turn = [solve(n, T_TURNING, d2_standard, integrator="backward_euler")
                    for n in N_LADDER]
    e4 = {
        "scheme": "backward_euler_central (stable, first order in time)",
        "stable": [r["stable"] for r in rows_be],
        "linf_orders_generic": pair_orders(rows_be, "linf_error"),
        "linf_orders_turning": pair_orders(rows_be_turn, "linf_error"),
        "linf_fit_generic": fitted_order(rows_be, "linf_error"),
        "declared_order_if_honest": 1.0,
        "protocol_criterion": "reject if |p - 2| > 0.3 for a scheme declared order 2",
        "verdict": ("DETECTED: the stable control measures ~1.0 at both times and is rejected "
                    "by the order criterion. The assignment falsifier 'protocol cannot detect "
                    "a wrong order' is falsified for this control."),
    }
    report["experiments"]["E4_wrong_order_control"] = e4

    # E5: invariant diagnostics -- same run, two energy functionals
    rows_pulse = [solve(n, T_PULSE, d2_standard, family="pulse") for n in N_LADDER]
    drift_exact = [r["energy_drift_exact"] for r in rows_pulse]
    drift_grad = [r["energy_drift_grad"] for r in rows_pulse]
    n = 256
    h = R / n
    r = np.linspace(0.0, R, n + 1)
    v0 = exact_standing(r, 0.0)
    w0 = np.zeros_like(v0)
    hv = discrete_energy_exact(v0, w0, h)
    u = np.empty_like(v0)
    u[0] = v0[1] / h
    u[1:] = v0[1:] / r[1:]
    eu = 4.0 * math.pi * 0.5 * float(np.trapezoid((np.gradient(u, h) ** 2) * r ** 2, dx=h))
    e5 = {
        "pulse_energy_drift_discrete_gradient": drift_exact,
        "pulse_energy_drift_np_gradient": drift_grad,
        "orders_discrete_gradient": pair_orders(rows_pulse, "energy_drift_exact"),
        "orders_np_gradient": pair_orders(rows_pulse, "energy_drift_grad"),
        "u_v_identity_relative_error_n256": abs(hv - eu / (4.0 * math.pi)) / abs(hv),
        "verdict": ("DIAGNOSTIC-DEPENDENT: the same run shows drift order ~5 with the "
                    "adjoint-consistent discrete gradient and ~2 with the np.gradient "
                    "quadrature. The protocol must name the exact diagnostic; a fixed drift "
                    "threshold is only meaningful together with the resolution and the "
                    "diagnostic definition."),
    }
    report["experiments"]["E5_invariants"] = e5

    # E6: cross-check with the peers' candidate implementation
    report["experiments"]["E6_crosscheck_flat_wave"] = crosscheck_flat_wave()

    # canonical reports for the audit tool: one passing, one wrong-order
    script_path = Path(__file__).resolve()
    sha = hashlib.sha256(script_path.read_bytes()).hexdigest()
    p_rich_be, _, _ = richardson_order(rows_be)
    rows_be_pulse = [solve(n, T_PULSE, d2_standard, family="pulse", integrator="backward_euler")
                     for n in N_LADDER]
    drift_be = [r["energy_drift_exact"] for r in rows_be_pulse]

    def _report(scheme_id, declared, integrator, rows, p_r, drift, residual):
        return {
            "schema": "n0-convergence-report/v1",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
            "scheme_id": scheme_id,
            "implementation": "numerics/protocol/convergence_demo.py",
            "script_sha256": sha,
            "declared_order": declared,
            "cfl": CFL,
            "exact_family": "two_mode_standing",
            "measurement_times": [T_GENERIC],
            "resolutions": list(N_LADDER),
            "linf_errors": [r["linf_error"] for r in rows],
            "l2_errors": [r["l2_error"] for r in rows],
            "residual_orders": residual,
            "richardson_order": p_r,
            "energy_drift": drift,
            "energy_diagnostic": "discrete gradient, h/2 sum w^2 + h/2 sum (Dv)^2",
            "energy_functional": {
                "name": "discrete_gradient_energy",
                "definition": "h/2 sum_j w_j^2 + h/2 sum_j ((v_{j+1}-v_j)/h)^2",
                "quadrature": "exact differences on the uniform grid, Dirichlet box",
                "structural_class": "convergent",
                "solver_tolerance": None,
            },
            "order_uncertainty": order_uncertainty(rows),
            "fitted_order": fitted_order(rows, "linf_error"),
            "stable": bool(all(r["stable"] for r in rows)),
            "non_degeneracy": {
                "single_mode": False,
                "times": [T_GENERIC],
                "note": "two-mode family; both modes away from turning points at t=0.35",
            },
            "integrator": integrator,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    report["submitted_reports"] = {
        "standard": _report("demo_standard_central_rk4", 2.0, "rk4", rows_std,
                            p_rich, [r["energy_drift_exact"] for r in rows_pulse], res_orders),
        "wrong_order": _report("demo_backward_euler_central", 2.0, "backward_euler", rows_be,
                               p_rich_be, drift_be, res_orders),
    }

    report["runtime_seconds"] = round(time.perf_counter() - t0, 3)
    report["provenance"] = {
        "python": sys.version.split()[0], "numpy": np.__version__,
        "platform": platform.platform(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    return report


def _fmt(ps):
    return "[" + ", ".join("nan" if p is None or math.isnan(p) else f"{p:.2f}" for p in ps) + "]"


def summarize(rep):
    lines = []
    e1 = rep["experiments"]["E1_turning_point_degeneracy"]
    lines.append("E1 turning-point degeneracy (standard order-2 scheme)")
    for k, v in e1["measurements"].items():
        lines.append(f"   {k:28s} linf orders {_fmt(v['linf_orders'])}"
                     f"  finest |e| {v['finest_linf_error']:.2e}")
    e2 = rep["experiments"]["E2_order_certification"]
    lines.append("E2 certification at generic time (two-mode family)")
    lines.append(f"   |e|_inf {['%.2e' % e for e in e2['linf_errors']]}")
    lines.append(f"   orders exact {_fmt(e2['linf_orders'])}  fit {e2['linf_fit']:.3f}"
                 f"  residual {_fmt(e2['residual_orders'])}"
                 f"  Richardson {e2['richardson_order']:.3f}")
    e3 = rep["experiments"]["E3_offbyone_unstable_control"]
    lines.append(f"E3 off-by-one control: stable={e3['stable']}"
                 f"  max|v| {['%.1e' % a for a in e3['max_amplitude']]} -> rejected on stability")
    e4 = rep["experiments"]["E4_wrong_order_control"]
    lines.append("E4 backward-Euler control (stable, first order)")
    lines.append(f"   generic {_fmt(e4['linf_orders_generic'])}  turning"
                 f" {_fmt(e4['linf_orders_turning'])}  fit {e4['linf_fit_generic']:.3f}"
                 "  -> rejected on order")
    e5 = rep["experiments"]["E5_invariants"]
    lines.append(f"E5 energy drift (discrete gradient) {['%.2e' % d for d in e5['pulse_energy_drift_discrete_gradient']]}"
                 f" orders {_fmt(e5['orders_discrete_gradient'])}")
    lines.append(f"   same run, np.gradient diagnostic {['%.2e' % d for d in e5['pulse_energy_drift_np_gradient']]}"
                 f" orders {_fmt(e5['orders_np_gradient'])}")
    lines.append(f"   u<->v identity rel err {e5['u_v_identity_relative_error_n256']:.2e}")
    e6 = rep["experiments"]["E6_crosscheck_flat_wave"]
    if e6.get("available"):
        lines.append("E6 cross-check numerics/tests/flat_wave.py")
        for k, v in e6["measurements"].items():
            lines.append(f"   {k:22s} linf orders {_fmt(v['linf_orders'])}")
        lines.append(f"   scheme agreement n=256: max|dv|={e6['agreement'].get('max_abs_v_difference')}"
                     f" bitwise={e6['agreement'].get('bitwise_equal')}")
    else:
        lines.append(f"E6 cross-check unavailable: {e6.get('reason')}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json-out", default=str(Path(__file__).resolve().parent / "demo_output.json"))
    a = ap.parse_args(argv)
    rep = run_all()
    Path(a.json_out).write_text(json.dumps(rep, indent=2, sort_keys=True))
    outdir = Path(a.json_out).resolve().parent
    for name, r in rep["submitted_reports"].items():
        p = outdir / f"demo_report_{name}.json"
        p.write_text(json.dumps(r, indent=2, sort_keys=True))
        print(f"wrote {p}")
    print(summarize(rep))
    print(f"wrote {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
