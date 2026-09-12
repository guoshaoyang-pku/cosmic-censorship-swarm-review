#!/usr/bin/env python3
"""N0 candidate (draft, UNVERIFIED): flat-space spherical scalar-wave calibration.

Status
------
Worker-20 proposal artifact for node N0 "Flat-space scalar-wave test"
(research_map/research_map.json), declared path ``numerics/tests/flat_wave.py``.
No group-lead assignment existed in ``comms/inbox`` when this was written, so this
file is a *candidate* for N0, not an accepted N0 artifact. It carries no map
status and claims no node completion.

Class binding
-------------
``AF-WCC-SCALAR-SPH`` (PROVISIONAL).  The binding cannot be confirmed from the
frozen taxonomy because node F0's declared artifact
``research_map/formulation_taxonomy.yaml`` is missing on disk (HARD finding in
``research_map/audit_evidence.py``).  The scope below is therefore deliberately
minimal and stays inside the class name: a *spherical scalar* sector on a
*fixed* flat background.

Scope (exact)
-------------
* Fixed Minkowski background.  No Einstein equations, no self-gravity, no
  collapse, no apparent horizon, no critical behaviour.
* Massless real scalar field, spherical symmetry: u(t, r),
  ``u_tt = u_rr + (2/r) u_r`` for r in (0, R], regularity ``u_r(t, 0) = 0``.
* Reduced variable v = r*u gives the 1+1D wave equation ``v_tt = v_rr`` with
  ``v(t, 0) = v(t, R) = 0`` (perfectly reflecting calibration box; no claim
  about an outgoing/incoming radiation boundary at I+).
* Conclusion type of anything measured here: **numerical calibration only**.
  No theorem, no counterexample, no statement about cosmic censorship.

What the artifact provides
--------------------------
1. ``solve_case(n, ...)`` -- solver contract expected by the independent N0
   acceptance gate (worker-18 ``n0_gate.py``): dx, dt, l2_error, linf_error,
   energy_initial, energy_final, plus provenance extras.
2. Manufactured-solution convergence for two exact families:
   * ``standing`` -- v = sum_m a_m sin(k_m r) cos(k_m t)/k_m, k_m = m*pi/R,
     exact in the box for all time (smooth, single/two-mode).
   * ``pulse``    -- v = 1/2 [V(r-t) + V(r+t)] with V(x) = x*U(|x|), U
     even-smooth, zero initial velocity; crosses the regular centre and is the
     broad-band control.  Wall not reached for t_end < R - r0 - 4*sigma.
3. Invariant diagnostics: reduced energy H = 1/2 int (v_t^2 + v_r^2) dr drift,
   and the exact identity H = E_u/(4*pi) with the physical u-energy
   4*pi * 1/2 int (u_t^2 + u_r^2) r^2 dr.
4. Operator self-tests that *measure* the design order on the eigenfunction
   (so passing means "the code implements the stencil it claims", not merely
   "the error got smaller").
5. Negative controls the declared gates must reject: frozen-in-time solver
   (order ~0), sign-flipped Laplacian (unbounded), CFL = 1.5 random-data run
   (RK4 stability limit |lambda|dt <= 2.828, here 2*1.5 = 3.0).

Determinism / cost
------------------
Pure numpy, no network, no randomness except the seeded CFL control.  The full
``--all`` run is < ~60 s on one core.

Usage
-----
    python3 numerics/tests/flat_wave.py --selftest
    python3 numerics/tests/flat_wave.py --all --json-out numerics/results/flat_wave_convergence.json
    python3 numerics/tests/flat_wave.py --n 256
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

# --------------------------------------------------------------------------
# exact manufactured solutions
# --------------------------------------------------------------------------


def standing_v(r, t, R=1.0, modes=((2, 1.0),)):
    """Exact standing-wave solution of v_tt = v_rr with v(t,0)=v(t,R)=0."""
    r = np.asarray(r, dtype=float)
    out = np.zeros_like(r)
    for m, a in modes:
        k = m * math.pi / R
        out += a * np.sin(k * r) * np.cos(k * t) / k
    return out


def _pulse_U(x, r0=12.0, sigma=2.0):
    """Even, smooth U; V(x) = x*U(x) is odd and smooth."""
    return np.exp(-((x - r0) / sigma) ** 2) + np.exp(-((x + r0) / sigma) ** 2)


def pulse_v(r, t, R=40.0, r0=12.0, sigma=2.0):
    """Exact d'Alembert solution, zero initial velocity, odd smooth data."""
    r = np.asarray(r, dtype=float)
    xp, xm = r + t, r - t
    return 0.5 * (xp * _pulse_U(xp, r0, sigma) + xm * _pulse_U(xm, r0, sigma))


# --------------------------------------------------------------------------
# discrete operators
# --------------------------------------------------------------------------


def second_derivative_weights(offsets):
    """Finite-difference weights for f''(0) on the given integer offsets.

    Solved from the moment conditions sum_k w_k k^p = 2 if p == 2 else 0 for
    p = 0..len(offsets)-1, so the weights are exact for polynomials of degree
    len(offsets)-1 and no table is hand-transcribed.
    """
    offsets = np.asarray(offsets, dtype=float)
    m = len(offsets)
    A = np.vstack([offsets ** p for p in range(m)])
    b = np.zeros(m)
    b[2] = 2.0
    return np.linalg.solve(A, b)


_W_CENTRAL5 = second_derivative_weights([2, 1, 0, -1, -2])
_W_RIGHT4 = second_derivative_weights([1, 0, -1, -2, -3])


def d2(v, h, order=2):
    """Second derivative on a uniform grid with v[0] = v[-1] = 0.

    order=2: central everywhere (boundaries enter through the zeros).
    order=4: 5-point central in the interior, odd-reflection closure at the
             regular centre (v is odd about r=0), 4th-order one-sided closure
             at the Dirichlet outer wall.
    """
    v = np.asarray(v, dtype=float)
    n = len(v) - 1
    out = np.zeros_like(v)
    if order == 2:
        out[1:-1] = (v[:-2] - 2.0 * v[1:-1] + v[2:]) / h ** 2
        return out
    if order != 4:
        raise ValueError("order must be 2 or 4")
    if n < 6:
        raise ValueError("order=4 needs n >= 6")
    w = _W_CENTRAL5  # offsets +2,+1,0,-1,-2
    out[2:-2] = (w[0] * v[4:] + w[1] * v[3:-1] + w[2] * v[2:-2]
                 + w[3] * v[1:-3] + w[4] * v[:-4]) / h ** 2
    # centre: v[0] = 0 and v[-1] = -v[1] (odd data), so only the +2,+1,0,-1 slots survive.
    out[1] = (w[0] * v[3] + w[1] * v[2] + (w[2] - w[4]) * v[1]) / h ** 2
    # outer wall: v[n] = 0; one-sided stencil uses j = n-1, n-2, n-3, n-4.
    wb = _W_RIGHT4  # offsets +1,0,-1,-2,-3
    out[n - 1] = (wb[1] * v[n - 1] + wb[2] * v[n - 2]
                  + wb[3] * v[n - 3] + wb[4] * v[n - 4]) / h ** 2
    return out


def energy_discrete(v, w, h, order=2):
    """Quadratic invariant of the semi-discrete scheme, exactly conserved by its flow.

    H_h = h/2 * sum_interior w_j^2 + h/2 * sum_interior v_j * (-D2 v)_j.
    For order=2 this equals the summation-by-parts forward-difference energy;
    for order=4 it is the correct invariant of *that* operator, so a measured
    drift is genuine RK4 error rather than a quadrature mismatch.
    """
    lap = d2(v, h, order)
    return 0.5 * h * (float(np.sum(w[1:-1] ** 2)) - float(np.sum(v[1:-1] * lap[1:-1])))


def energy_quadrature(v, w, h):
    """Continuum H = 1/2 int (v_t^2 + v_r^2) dr by trapezoid (identity checks only)."""
    grad = np.gradient(v, h)
    return 0.5 * float(np.trapezoid(w ** 2 + grad ** 2, dx=h))


def energy_u(v, w, r, h):
    """E_u = 4*pi * 1/2 int (u_t^2 + u_r^2) r^2 dr, u = v/r, regular centre."""
    u = np.empty_like(v)
    ut = np.empty_like(v)
    u[0] = v[1] / h          # u(0) = v'(0) + O(h^2) for v ~ c*r
    ut[0] = w[1] / h
    u[1:] = v[1:] / r[1:]
    ut[1:] = w[1:] / r[1:]
    gu = np.gradient(u, h)
    gut = np.gradient(ut, h)
    return 4.0 * math.pi * 0.5 * float(np.trapezoid((gut ** 2 + gu ** 2) * r ** 2, dx=h))


# --------------------------------------------------------------------------
# time integration
# --------------------------------------------------------------------------


def integrate(v0, w0, h, t_end, cfl, order=2, sample_energy=True):
    """Classical RK4 on (v, w=vt): dv/dt = w, dw/dt = d2(v)."""
    n_steps = max(1, int(math.ceil(t_end / (cfl * h))))
    dt = t_end / n_steps
    v = np.array(v0, dtype=float)
    w = np.array(w0, dtype=float)
    e0 = energy_discrete(v, w, h, order)
    max_drift = 0.0
    for _ in range(n_steps):
        k1v, k1w = w, d2(v, h, order)
        k2v, k2w = w + 0.5 * dt * k1w, d2(v + 0.5 * dt * k1v, h, order)
        k3v, k3w = w + 0.5 * dt * k2w, d2(v + 0.5 * dt * k2v, h, order)
        k4v, k4w = w + dt * k3w, d2(v + dt * k3v, h, order)
        v = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        w = w + (dt / 6.0) * (k1w + 2 * k2w + 2 * k3w + k4w)
        if sample_energy and e0 != 0.0:
            max_drift = max(max_drift, abs(energy_discrete(v, w, h, order) - e0) / abs(e0))
    return {"v": v, "w": w, "n_steps": n_steps, "dt": dt,
            "energy_initial": e0, "energy_final": energy_discrete(v, w, h, order),
            "energy_drift": max_drift}


# --------------------------------------------------------------------------
# case driver: the contract the independent N0 gate can call
# --------------------------------------------------------------------------


def _case_setup(n, family, R, t_end, r0, sigma, modes):
    h = R / n
    r = np.linspace(0.0, R, n + 1)
    if family == "standing":
        v0 = standing_v(r, 0.0, R, modes)
        w0 = np.zeros_like(v0)
    elif family == "pulse":
        v0 = pulse_v(r, 0.0, R, r0, sigma)
        w0 = np.zeros_like(v0)
    else:
        raise ValueError(f"unknown family {family!r}")
    v0[0] = v0[-1] = 0.0
    return h, r, v0, w0


def solve_case(n, t_end=0.5, cfl=0.25, order=2, family="standing", R=1.0,
               r0=12.0, sigma=2.0, modes=((2, 1.0),)):
    """One resolution of the N0 calibration; returns the gate contract fields."""
    h, r, v0, w0 = _case_setup(n, family, R, t_end, r0, sigma, modes)
    t0 = time.perf_counter()
    res = integrate(v0, w0, h, t_end, cfl, order)
    wall = time.perf_counter() - t0
    exact = (standing_v(r, t_end, R, modes) if family == "standing"
             else pulse_v(r, t_end, R, r0, sigma))
    err = res["v"][1:-1] - exact[1:-1]
    l2 = float(np.sqrt(np.mean(err ** 2)))
    linf = float(np.max(np.abs(err)))
    err_u = float(np.max(np.abs(res["v"][1:-1] / r[1:-1] - exact[1:-1] / r[1:-1])))
    return {
        "n": int(n), "dx": float(h), "dt": float(res["dt"]), "n_steps": int(res["n_steps"]),
        "cfl": float(cfl), "order_scheme": int(order), "family": family,
        "t_end": float(t_end),
        "l2_error": l2, "linf_error": linf, "linf_error_u": err_u,
        "energy_initial": float(res["energy_initial"]),
        "energy_final": float(res["energy_final"]),
        "energy_drift": float(res["energy_drift"]),
        "wall_seconds": round(wall, 4),
    }


run_case = solve_case  # alias for gate contracts that call run_case(n, ...)


def observed_order(rows, key="l2_error"):
    """p_i = log(e_i / e_{i+1}) / log(dx_i / dx_{i+1}), i.e. log2 for doublings."""
    out = []
    for a, b in zip(rows, rows[1:]):
        if a[key] > 0 and b[key] > 0 and a["dx"] > b["dx"] > 0:
            out.append(float(math.log(a[key] / b[key]) / math.log(a["dx"] / b["dx"])))
        else:
            out.append(float("nan"))
    return out


# --------------------------------------------------------------------------
# self-tests and negative controls
# --------------------------------------------------------------------------


def _operator_order(order, resolutions=(64, 128, 256)):
    """Measure the design order of d2 on sin(k r), excluding the centre point."""
    k = 2.0 * math.pi
    errs = []
    for n in resolutions:
        h = 1.0 / n
        r = np.linspace(0.0, 1.0, n + 1)
        v = np.sin(k * r)
        v[0] = v[-1] = 0.0
        got = d2(v, h, order)
        want = -k ** 2 * np.sin(k * r)
        idx = np.arange(2, n - 1)  # interior + wall closure, skip j=1 centre closure
        errs.append(float(np.max(np.abs(got[idx] - want[idx]))))
    orders = [math.log(a / b) / math.log(2.0) for a, b in zip(errs, errs[1:])]
    return errs, orders


def selftest(verbose=True):
    """Operator and identity tests.  Failure means the calibration code is wrong."""
    checks = []

    def rec(name, ok, detail):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        if verbose:
            print(f"  [{'ok' if ok else 'FAIL'}] {name}: {detail}")

    # 1. moment weights reproduce exact second derivatives of polynomials
    for order, offset_sets in ((2, [[-1, 0, 1]]), (4, [[-2, -1, 0, 1, 2], [1, 0, -1, -2, -3]])):
        worst = 0.0
        for offs in offset_sets:
            w = second_derivative_weights(offs)
            for deg in range(0, len(offs)):
                got = float(sum(wi * (o ** deg) for wi, o in zip(w, offs)))
                worst = max(worst, abs(got - (2.0 if deg == 2 else 0.0)))
        rec(f"stencil moments order={order}", worst < 1e-10, f"max moment error {worst:.2e}")

    # 2. measured design order of d2 on sin(kr): 2 for order=2, 4 for order=4
    for order, want in ((2, 2.0), (4, 4.0)):
        errs, orders = _operator_order(order)
        ok = all(abs(p - want) < 0.35 for p in orders)
        rec(f"d2 design order={order}", ok,
            f"errs={['%.2e' % e for e in errs]} orders={['%.2f' % p for p in orders]}")

    # 3. exact standing solution + u<->v energy identity at t=0
    n = 256
    h = 1.0 / n
    r = np.linspace(0.0, 1.0, n + 1)
    v0 = standing_v(r, 0.0, 1.0, ((2, 1.0),))
    w0 = np.zeros_like(v0)
    hv = energy_quadrature(v0, w0, h)
    eu = energy_u(v0, w0, r, h)
    rel = abs(hv - eu / (4 * math.pi)) / abs(hv)
    rec("u<->v energy identity", rel < 1e-3, f"relative difference {rel:.2e}")

    # 4. sign conventions on an odd cubic that obeys both Dirichlet walls:
    #    v = r(r^2 - R^2), v'' = 6r.  Exact for the 2nd- and 4th-order stencils.
    worst = 0.0
    for order in (2, 4):
        approx = d2(r * (r ** 2 - 1.0), h, order)
        worst = max(worst, float(np.max(np.abs(approx[1:-1] - 6.0 * r[1:-1]))))
    rec("odd-cubic sign convention", worst < 1e-8, f"max deviation {worst:.2e}")

    return {"pass": all(c["pass"] for c in checks), "checks": checks}


def convergence_study(resolutions=None, cfl=0.25, order=2, family="standing",
                      R=1.0, t_end=0.5, modes=((2, 1.0),), r0=12.0, sigma=2.0):
    resolutions = resolutions or ([64, 128, 256, 512, 1024] if order == 2 else [32, 64, 128, 256, 512])
    rows = [solve_case(n, t_end=t_end, cfl=cfl, order=order, family=family,
                       R=R, r0=r0, sigma=sigma, modes=modes) for n in resolutions]
    pl2 = observed_order(rows, "l2_error")
    plinf = observed_order(rows, "linf_error")
    monotone = all(b["l2_error"] < a["l2_error"] for a, b in zip(rows, rows[1:]))
    lo, hi = (1.8, 2.2) if order == 2 else (3.6, 4.4)
    finite = [p for p in pl2 if not math.isnan(p)]
    at_least = all(p >= lo - 0.1 for p in finite)
    within = bool(finite) and all(lo <= p <= hi for p in finite)
    return {
        "family": family, "order_scheme": order, "cfl": cfl, "R": R, "t_end": t_end,
        "rows": rows, "order_l2": pl2, "order_linf": plinf,
        "monotone_decrease": bool(monotone),
        "order_gate": {"lo": lo, "hi": hi, "all_pairs_within_band": bool(within),
                       "pass": bool(monotone and at_least and within)},
    }


def frozen_control(n=512, t_end=0.5):
    """A solver that never integrates must fail the order gate."""
    h, r, v0, w0 = _case_setup(n, "standing", 1.0, t_end, 12.0, 2.0, ((2, 1.0),))
    exact = standing_v(r, t_end, 1.0, ((2, 1.0),))
    err = float(np.sqrt(np.mean((v0[1:-1] - exact[1:-1]) ** 2)))
    rows = [{"n": n, "dx": 1.0 / n, "l2_error": err} for n in (128, 256, 512)]
    orders = observed_order(rows, "l2_error")
    return {"name": "frozen_in_time", "l2_error": err, "order_l2": orders,
            "rejected": bool(all(abs(p) < 0.5 for p in orders))}


def wrong_sign_control(n=256, t_end=0.5):
    """Sign-flipped Laplacian (elliptic, unbounded growth) must be rejected."""
    h, r, v0, w0 = _case_setup(n, "standing", 1.0, t_end, 12.0, 2.0, ((2, 1.0),))
    n_steps = max(1, int(math.ceil(t_end / (0.25 * h))))
    dt = t_end / n_steps
    v, w = v0.copy(), w0.copy()
    for _ in range(n_steps):
        k1v, k1w = w, -d2(v, h, 2)
        k2v, k2w = w + 0.5 * dt * k1w, -d2(v + 0.5 * dt * k1v, h, 2)
        k3v, k3w = w + 0.5 * dt * k2w, -d2(v + 0.5 * dt * k2v, h, 2)
        k4v, k4w = w + dt * k3w, -d2(v + dt * k3v, h, 2)
        v = v + (dt / 6.0) * (k1v + 2 * k2v + 2 * k3v + k4v)
        w = w + (dt / 6.0) * (k1w + 2 * k2w + 2 * k3w + k4w)
    err = float(np.sqrt(np.mean((v[1:-1] - standing_v(r, t_end, 1.0, ((2, 1.0),))[1:-1]) ** 2)))
    return {"name": "wrong_sign_laplacian", "l2_error": err, "rejected": bool(err > 1e-2)}


def cfl_control(n=64, cfl=1.5, seed=12345, order=2):
    """RK4 + central d2 is unstable when max|lambda|dt > 2.828 (here 2*cfl)."""
    h = 1.0 / n
    rng = np.random.default_rng(seed)
    r = np.linspace(0.0, 1.0, n + 1)
    v0 = rng.standard_normal(n + 1) * np.sin(math.pi * r)
    v0[0] = v0[-1] = 0.0
    w0 = np.zeros_like(v0)
    res = integrate(v0, w0, h, 1.0, cfl, order, sample_energy=False)
    growth = float(np.linalg.norm(res["v"][1:-1]) / np.linalg.norm(v0[1:-1]))
    return {"name": f"cfl={cfl}", "growth_factor": growth, "rejected": bool(growth > 10.0)}


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_all(json_out=None):
    here = Path(__file__).resolve()
    report = {
        "artifact": "numerics/tests/flat_wave.py",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "binding_status": "PROVISIONAL - F0 taxonomy artifact missing on disk",
        "validation_status": "unverified",
        "conclusion_type_of_measurements": "numerical_evidence",
        "scope": {
            "background": "fixed Minkowski",
            "field": "massless real scalar, spherical symmetry",
            "equation": "u_tt = u_rr + (2/r) u_r ; v = r*u, v_tt = v_rr",
            "boundary": "v(t,0)=v(t,R)=0 reflecting calibration box",
            "not_in_scope": ["self-gravity", "collapse", "apparent horizon",
                             "critical behaviour", "outgoing radiation at I+",
                             "any cosmic-censorship conclusion"],
        },
        "provenance": {
            "script_sha256": file_sha256(here),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "assignment": "none found in comms/inbox at generation time",
        },
        "selftest": selftest(verbose=False),
        "studies": [],
        "controls": [],
    }
    report["studies"].append(convergence_study(order=2, family="standing", cfl=0.25,
                                               t_end=0.37))
    report["studies"].append(convergence_study(order=2, family="pulse", cfl=0.25,
                                               R=40.0, t_end=8.0, r0=12.0, sigma=2.0))
    report["studies"].append(convergence_study(order=4, family="standing", cfl=0.1,
                                               modes=((2, 1.0), (5, 0.5)), t_end=0.37))
    report["controls"].append(frozen_control())
    report["controls"].append(wrong_sign_control())
    report["controls"].append(cfl_control(cfl=1.5))
    report["controls"].append(cfl_control(cfl=0.25))

    a = solve_case(128, t_end=0.5, cfl=0.25, order=2, family="standing")
    b = solve_case(128, t_end=0.5, cfl=0.25, order=2, family="standing")
    ka = {k: v for k, v in a.items() if k != "wall_seconds"}
    kb = {k: v for k, v in b.items() if k != "wall_seconds"}
    report["determinism"] = {
        "bitwise_equal_numerics": bool(ka == kb),
        "excluded_fields": ["wall_seconds"],
        "pass": bool(ka == kb),
    }

    # control: temporal error must be subdominant to the measured spatial error
    e_a = solve_case(256, t_end=0.37, cfl=0.25, order=2, family="standing")["l2_error"]
    e_b = solve_case(256, t_end=0.37, cfl=0.10, order=2, family="standing")["l2_error"]
    report["temporal_control"] = {
        "n": 256, "t_end": 0.37, "l2_cfl_0.25": e_a, "l2_cfl_0.10": e_b,
        "relative_change": abs(e_a - e_b) / e_a,
        "pass": bool(abs(e_a - e_b) / e_a < 0.02),
        "note": "if halving dt moves the error, the measured order is temporal, not spatial",
    }
    # control: the half-period point is special; document it instead of gating on it
    tp = []
    for t_end in (0.37, 0.5):
        st = convergence_study(order=2, family="standing", cfl=0.25, t_end=t_end,
                               resolutions=[128, 256, 512])
        tp.append({"t_end": t_end, "order_l2": st["order_l2"]})
    report["time_point_control"] = {
        "note": ("t=0.5 is half a period of mode m=2: cos(omega_h t) - cos(k t) is "
                 "second order in the frequency shift, so the leading O(h^2) term "
                 "cancels and the measured order is a fragile O(h^4) accident. "
                 "The primary standing gate uses the generic time t=0.37."),
        "runs": tp,
    }

    standing2, pulse2, standing4 = report["studies"]
    gates = {
        "G1_standing_order2": bool(standing2["order_gate"]["pass"]),
        "G2_standing_order4": bool(standing4["order_gate"]["pass"]),
        "G3_energy_drift_standing_order2": bool(
            max(r["energy_drift"] for r in standing2["rows"]) < 1e-8),
        "G4_pulse_order2_and_error": bool(
            pulse2["order_gate"]["pass"]
            and pulse2["rows"][-1]["l2_error"] < 1e-3
            and pulse2["rows"][-1]["energy_drift"] < 1e-8
            and all(b["energy_drift"] < a["energy_drift"]
                    for a, b in zip(pulse2["rows"], pulse2["rows"][1:]))),
        "G5_determinism": bool(report["determinism"]["pass"]),
        "G6_u_v_energy_identity": bool(
            next(c["pass"] for c in report["selftest"]["checks"]
                 if c["name"] == "u<->v energy identity")),
        "G7_selftest": bool(report["selftest"]["pass"]),
        "G8_negative_controls_rejected": bool(
            all(c["rejected"] for c in report["controls"] if c["name"] != "cfl=0.25")
            and not cfl_control(cfl=0.25)["rejected"]),
        "G9_temporal_error_subdominant": bool(report["temporal_control"]["pass"]),
        "G10_energy_drift_standing_order4": bool(
            standing4["rows"][-1]["energy_drift"] < 1e-8),
    }
    report["gates"] = gates
    report["all_gates_pass"] = bool(all(gates.values()))
    report["claims_not_made"] = [
        "no claim that N0 is complete or accepted",
        "no claim about self-gravitating or non-linear scalar dynamics",
        "no claim about cosmic censorship, WCC or SCC",
        "no claim that the AF-WCC-SCALAR-SPH class binding is frozen (F0 artifact missing)",
    ]
    if json_out:
        p = Path(json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, sort_keys=True))
        print(f"wrote {p}")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="operator/identity tests only")
    ap.add_argument("--all", action="store_true", help="self-tests, studies and controls")
    ap.add_argument("--n", type=int, default=None, help="single-resolution solve_case run")
    ap.add_argument("--order", type=int, default=2, choices=(2, 4))
    ap.add_argument("--cfl", type=float, default=0.25)
    ap.add_argument("--family", default="standing", choices=("standing", "pulse"))
    ap.add_argument("--t-end", type=float, default=0.5)
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args(argv)

    if a.selftest:
        st = selftest(verbose=True)
        print(json.dumps({"selftest_pass": st["pass"]}, indent=2))
        return 0 if st["pass"] else 1
    if a.n is not None:
        print(json.dumps(solve_case(a.n, t_end=a.t_end, cfl=a.cfl, order=a.order,
                                    family=a.family), indent=2, sort_keys=True))
        return 0
    report = run_all(a.json_out)
    print(json.dumps({"all_gates_pass": report["all_gates_pass"],
                      "gates": report["gates"]}, indent=2, sort_keys=True))
    return 0 if report["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
