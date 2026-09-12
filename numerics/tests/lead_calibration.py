#!/usr/bin/env python3
"""N0 lead reference calibration (independent of numerics/tests/flat_wave.py).

Role
----
``numerics/tests/flat_wave.py`` (worker 12) is the canonical N0 artifact;
``numerics/tests/flat_wave_replication.py`` (worker 13) is the independent
replication.  This file is the *lead's* cross-check: a third implementation
family (cell-centred finite-volume spherical SBP scheme + periodic Cartesian
stencils) used to (a) confirm the measured convergence orders, (b) provide the
invariant diagnostics the canonical file does not cover (dispersion,
SBP energy identity, boundary-flux closure, constraint preservation, charge),
and (c) enforce the N1 lock guard.

Scope is flat space only.  No self-gravitating code exists in this package;
``study_lock_guard`` machine-checks that the map lock still refuses N1.

Usage:
    python3 numerics/tests/lead_calibration.py --selftest
    python3 numerics/tests/lead_calibration.py --all --json-out artifacts/numerics/n0/lead_calibration_report.json
"""
from __future__ import annotations

import argparse
import json
import math
import platform
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from numerics.cartesian import CartesianWave1D  # noqa: E402
from numerics.convergence import fit_order, format_table, observed_order  # noqa: E402
from numerics.exact import CartesianMMS, SphericalMMS, SphericalPulse  # noqa: E402
from numerics.fd import numerical_frequency, symbol_d2  # noqa: E402
from numerics.grids import PeriodicGrid, SphericalGrid  # noqa: E402
from numerics.integrate import integrate, rk4_step  # noqa: E402
from numerics.invariants import (  # noqa: E402
    energy_budget_residual,
    symbol_spectrum_check,
    trapezoid,
)
from numerics.spherical import SphericalCollocated, SphericalSBP  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def l2_weighted(err: np.ndarray, w: np.ndarray) -> float:
    return float(math.sqrt(float(np.sum(w * err**2)) / float(np.sum(w))))


def fit_frequency(series: np.ndarray, times: np.ndarray, omega_ref: float) -> float:
    """Measure the oscillation frequency by windowed phase fitting.

    On each half of the record, fit ``A cos(omega_ref t) + B sin(omega_ref t)``.
    The effective phase is ``phi = atan2(B, A)`` and advances at the frequency
    offset, so ``omega = omega_ref + (phi_2 - phi_1) / (t_c2 - t_c1)`` with the
    window midpoints as times.  Robust for |omega - omega_ref| * T << pi.
    """
    mid = len(series) // 2
    out = []
    for sl in (slice(0, mid), slice(mid, None)):
        y = series[sl]
        t = times[sl]
        M = np.column_stack([np.cos(omega_ref * t), np.sin(omega_ref * t)])
        coef, *_ = np.linalg.lstsq(M, y, rcond=None)
        out.append((math.atan2(coef[1], coef[0]), 0.5 * (t[0] + t[-1])))
    dphi = out[1][0] - out[0][0]
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return omega_ref + dphi / (out[1][1] - out[0][1])


def normalise_orders(orders) -> list[float]:
    return [float(p) for p in orders if isinstance(p, (int, float)) and p == p]


def order_ok(orders, expected: float, tol: float = 0.3) -> bool:
    vals = normalise_orders(orders)
    return bool(vals) and all(abs(p - expected) <= tol for p in vals)


# ---------------------------------------------------------------------------
# Cartesian studies
# ---------------------------------------------------------------------------
def study_cartesian_mms(order: int, resolutions, T: float = 0.5, dt: float = 1e-4) -> dict:
    """Two-mode manufactured solution; dt fixed so time error is negligible."""
    L = 1.0
    k1, k2 = 2 * math.pi / L, 4 * math.pi / L
    omega = k1

    def profile(x):
        return np.sin(k1 * x) + 0.5 * np.sin(k2 * x)

    def source(x, t):
        return (
            (omega**2 - k1**2) * np.sin(k1 * x) + 0.5 * (omega**2 - k2**2) * np.sin(k2 * x)
        ) * np.sin(omega * t)

    errors = []
    rows = []
    for n in resolutions:
        g = PeriodicGrid(n, L)
        w = CartesianWave1D(g, order, source=source)
        y = w.initial(np.zeros(n), omega * profile(g.x))
        y, nsteps = integrate(w.rhs, y, 0.0, T, dt)
        exact = np.sin(omega * T) * profile(g.x)
        err = float(np.sqrt(np.mean((y[:n] - exact) ** 2)))
        errors.append(err)
        rows.append({"n": n, "h": g.h, "dt": dt, "l2_error": err, "steps": nsteps})
    return {
        "study": f"cartesian_mms_order{order}",
        "order_scheme": order,
        "rows": rows,
        "orders": observed_order(errors),
        "fitted_order": fit_order([r["h"] for r in rows], errors),
    }


def study_cartesian_dispersion(order: int, resolutions=(16, 32, 64, 128)) -> dict:
    """Symbol consistency + phase-speed order + one evolution anchor."""
    L = 1.0
    k = 2 * math.pi / L
    rows = []
    for n in resolutions:
        g = PeriodicGrid(n, L)
        mode = np.exp(1j * k * g.x)
        lam = float(np.real(np.mean(CartesianWave1D(g, order).d2(mode) / mode)))
        lam_sym = symbol_d2(k, g.h, order)
        omega_sym = numerical_frequency(k, g.h, order)
        rows.append(
            {
                "n": n,
                "h": g.h,
                "lambda_measured": lam,
                "lambda_symbol": lam_sym,
                "symbol_rel_error": abs(lam - lam_sym) / max(abs(lam_sym), 1e-300),
                "phase_speed_error": abs(omega_sym / k - 1.0),
            }
        )
    speed_orders = observed_order([r["phase_speed_error"] for r in rows])
    # evolution anchor at n=64: does the code actually oscillate at omega_sym?
    n = 64
    g = PeriodicGrid(n, L)
    w = CartesianWave1D(g, order)
    dt, T = 2e-4, 10.0
    y = w.initial(np.cos(k * g.x), np.zeros(n))
    times = []
    series = []
    t = 0.0
    while t < T - 1e-15:
        h = min(dt, T - t)
        y = rk4_step(w.rhs, t, y, h)
        t += h
        times.append(t)
        series.append(float(y[0]))
    omega_ref = numerical_frequency(k, g.h, order)
    omega_meas = fit_frequency(np.asarray(series), np.asarray(times), omega_ref)
    return {
        "study": f"cartesian_dispersion_order{order}",
        "order_scheme": order,
        "rows": rows,
        "phase_speed_orders": speed_orders,
        "symbol_spectrum_check": symbol_spectrum_check(32, L, order),
        "evolution_anchor": {
            "n": n,
            "dt": dt,
            "t_end": T,
            "omega_symbol": omega_ref,
            "omega_measured": omega_meas,
            "rel_difference": abs(omega_meas - omega_ref) / omega_ref,
        },
    }


def study_cartesian_invariants(order: int, n: int = 128, T: float = 10.0, dt: float = 2e-4) -> dict:
    """Spectral energy, gradient energy defect, momentum and U(1) charge."""
    L = 1.0
    g = PeriodicGrid(n, L)
    k1, k2 = 2 * math.pi / L, 6 * math.pi / L

    real = CartesianWave1D(g, order)
    # Traveling right-mover: psi_t = -psi_x, so P = h sum Pi D1 psi is nonzero and
    # a relative drift is meaningful (a standing wave has P == 0 identically).
    shape = np.cos(k1 * g.x) + 0.3 * np.cos(k2 * g.x)
    y = real.initial(shape, k1 * np.sin(k1 * g.x) + 0.3 * k2 * np.sin(k2 * g.x))
    e_sp, e_gr, mom = [], [], []
    t = 0.0
    while t < T - 1e-15:
        h = min(dt, T - t)
        y = rk4_step(real.rhs, t, y, h)
        t += h
        e_sp.append(real.energy_spectral(y))
        e_gr.append(real.energy_grad(y))
        mom.append(real.momentum(y))

    cmplx = CartesianWave1D(g, order, complex_field=True)
    yc = cmplx.initial(
        np.exp(1j * k1 * g.x) + 0.4 * np.exp(1j * k2 * g.x),
        1j * (np.exp(1j * k1 * g.x) + 0.2 * np.exp(1j * k2 * g.x)),
    )
    q = []
    t = 0.0
    while t < T - 1e-15:
        h = min(dt, T - t)
        yc = rk4_step(cmplx.rhs, t, yc, h)
        t += h
        q.append(cmplx.charge(yc))

    def drift(series):
        a = np.asarray(series)
        scale = max(float(np.max(np.abs(a))), 1e-300)
        return float((np.max(a) - np.min(a)) / scale)

    return {
        "study": f"cartesian_invariants_order{order}",
        "order_scheme": order,
        "n": n,
        "dt": dt,
        "t_end": T,
        "spectral_energy_rel_drift": drift(e_sp),
        "gradient_energy_rel_drift": drift(e_gr),
        "momentum_rel_drift": drift(mom),
        "charge_rel_drift": drift(q),
        "energy_grad_spectral_relative_defect": float(
            abs(np.mean(e_gr) - np.mean(e_sp)) / max(abs(np.mean(e_sp)), 1e-300)
        ),
    }


def study_energy_defect_order(order: int, resolutions=(16, 32, 64, 128)) -> dict:
    """|E_grad - E_spectral| / E scaled with h at order p (integration-by-parts defect)."""
    L = 1.0
    g0 = PeriodicGrid(8, L)
    defects = []
    hs = []
    for n in resolutions:
        g = PeriodicGrid(n, L)
        w = CartesianWave1D(g, order)
        k = 2 * math.pi / L
        y = w.initial(np.cos(k * g.x) + 0.3 * np.cos(2 * k * g.x), np.zeros(n))
        hs.append(g.h)
        defects.append(w.energy_defect(y) / max(w.energy_spectral(y), 1e-300))
    return {
        "study": f"cartesian_energy_defect_order{order}",
        "order_scheme": order,
        "h": hs,
        "relative_defects": defects,
        "orders": observed_order(defects),
    }


# ---------------------------------------------------------------------------
# Spherical studies
# ---------------------------------------------------------------------------
def _spherical_mms_run(N: int, R: float = 1.0, T: float = 0.5, cfl: float = 0.2, omega: float = 3.0):
    g = SphericalGrid(N, R)
    ex = SphericalMMS(omega=omega)
    sch = SphericalSBP(
        g, bc="exact", phi_boundary=lambda t: float(ex.phi(R, t)),
        source=lambda r, t: ex.source(r, t),
    )
    psi = ex.psi(g.r_cell, 0.0)
    pi = ex.pi(g.r_cell, 0.0)
    phi = (psi[1:] - psi[:-1]) / g.h  # discrete-gradient init: constraint exactly zero
    y = sch.pack(psi, pi, phi)
    y, _ = integrate(sch.rhs, y, 0.0, T, cfl * g.h)
    return g, ex, sch, y


def study_spherical_mms(resolutions=(32, 64, 128, 256), R: float = 1.0, T: float = 0.5) -> dict:
    rows = []
    psi_errs, pi_errs = [], []
    for N in resolutions:
        g, ex, sch, y = _spherical_mms_run(N, R, T)
        psi, pi, _ = sch.unpack(y)
        ep = sch.energy(y)
        res = sch.semi_discrete_residual(y, T)
        e_psi = l2_weighted(psi - ex.psi(g.r_cell, T), g.volume)
        e_pi = l2_weighted(pi - ex.pi(g.r_cell, T), g.volume)
        psi_errs.append(e_psi)
        pi_errs.append(e_pi)
        rows.append(
            {
                "N": N,
                "h": g.h,
                "l2_error_psi": e_psi,
                "l2_error_pi": e_pi,
                "origin_error_psi": float(abs(psi[0] - ex.psi(g.r_cell[0], T))),
                "constraint_residual": sch.constraint_residual(y),
                "sbp_semidiscrete_residual": res,
                "energy": ep,
            }
        )
    return {
        "study": "spherical_mms_sbp",
        "rows": rows,
        "orders_psi": observed_order(psi_errs),
        "orders_pi": observed_order(pi_errs),
        "orders_origin_psi": observed_order([r["origin_error_psi"] for r in rows]),
        "max_sbp_residual": max(abs(r["sbp_semidiscrete_residual"]) for r in rows),
        "max_constraint_residual": max(r["constraint_residual"] for r in rows),
    }


def study_spherical_pulse(resolutions=(100, 200, 400, 800), R: float = 12.0, T: float = 10.0,
                          width: float = 0.6, s0: float = -4.0) -> dict:
    """Outgoing pulse: energy budget, continuum flux closure, constraint, regularity."""
    ex = SphericalPulse(width=width, s0=s0, amp=1.0)
    rows = []
    flux_diffs = []
    for N in resolutions:
        g = SphericalGrid(N, R)
        sch = SphericalSBP(g, bc="outgoing")
        psi = ex.psi(g.r_cell, 0.0)
        pi = ex.pi(g.r_cell, 0.0)
        phi = (psi[1:] - psi[:-1]) / g.h
        y = sch.pack(psi, pi, phi)
        dt = 0.2 * g.h
        ts, Es, Fs, Cs = [0.0], [sch.energy(y)], [sch.flux(y, 0.0)], [sch.constraint_residual(y)]
        t = 0.0
        while t < T - 1e-15:
            h = min(dt, T - t)
            y = rk4_step(sch.rhs, t, y, h)
            t += h
            ts.append(t)
            Es.append(sch.energy(y))
            Fs.append(sch.flux(y, t))
            Cs.append(sch.constraint_residual(y))
        bud = energy_budget_residual(Es[0], Es[-1], ts, Fs)
        tt = np.asarray(ts)
        Fex = g.area[N] * ex.pi(R, tt) * ex.phi(R, tt)
        Fex_int = trapezoid(ts, Fex)
        rel = abs(bud["flux_integral"] - Fex_int) / max(abs(Fex_int), 1e-300)
        flux_diffs.append(rel)
        psi_num, _, _ = sch.unpack(y)
        # By T=10 the pulse has left [0, R]; the exact interior energy is ~0, so the
        # meaningful diagnostic is the fraction of energy left behind by the scheme's
        # dispersive tail (absolute, not normalised by a vanishing exact value).
        remaining = abs(Es[-1]) / max(abs(Es[0]), 1e-300)
        rows.append(
            {
                "N": N,
                "h": g.h,
                "dt": dt,
                "energy_initial": Es[0],
                "energy_final": Es[-1],
                "energy_remaining_fraction": remaining,
                "sbp_budget_relative_residual": bud["relative_residual"],
                "flux_integral_numeric": bud["flux_integral"],
                "flux_integral_continuum": Fex_int,
                "flux_closure_relative_difference": rel,
                "max_constraint_residual": max(Cs),
                "origin_psi_error": float(abs(psi_num[0] - float(ex.psi(g.r_cell[0], T)))),
            }
        )
    remaining_fractions = [r["energy_remaining_fraction"] for r in rows]
    return {
        "study": "spherical_pulse_sbp",
        "rows": rows,
        "flux_closure_orders": observed_order(flux_diffs),
        "remaining_fraction_orders": observed_order(remaining_fractions),
        "max_sbp_budget_residual": max(r["sbp_budget_relative_residual"] for r in rows),
        "max_constraint_residual": max(r["max_constraint_residual"] for r in rows),
    }


def study_collocated_control(resolutions=(32, 64, 128, 256), R: float = 1.0, T: float = 0.5) -> dict:
    """Control: naive D2+(2/r)D1 converges at order 2 but is not SBP.

    Measured energy-residual behaviour (exact data, verified independently of the
    time integration):

    * full residual O(h), boundary-closure dominated (1.5e-4 -> 7.3e-5 -> 3.6e-5);
    * volume/interior defect O(1) relative to the energy scale: the centred D1 is
      not the weighted SBP adjoint of itself for r^2 weights, leaving an O(h)
      defect per cell that accumulates over N ~ 1/h cells.

    Either way it is >1e15 times larger than the SBP scheme's machine-precision
    identity (7e-18), which is the point of the control.
    """
    rows = []
    errs, residuals, interior_residuals = [], [], []
    for N in resolutions:
        g = SphericalGrid(N, R)
        ex = SphericalMMS(omega=3.0)
        m = 1  # order 2 needs one outer ghost

        def ghosts(name, t, ex=ex, g=g):
            r = g.radius + (np.arange(1) + 0.5) * g.h
            return {"psi": ex.psi(r, t), "pi": ex.pi(r, t)}[name]

        sch = SphericalCollocated(g, order=2, source=lambda r, t: ex.source(r, t), outer_ghosts=ghosts)
        psi = ex.psi(g.r_cell, 0.0)
        pi = ex.pi(g.r_cell, 0.0)
        phi = ex.phi(g.r_cell, 0.0)
        y = sch.pack(psi, pi, phi)
        y, _ = integrate(sch.rhs, y, 0.0, T, 0.2 * g.h)
        e = l2_weighted(y[:N] - ex.psi(g.r_cell, T), g.volume)
        errs.append(e)
        # full semi-discrete dE/dt residual: boundary closure contributes O(h)
        res = abs(sch.semi_discrete_residual(y, T))
        scale = max(sch.energy(y), 1e-300) / max(T, 1e-300)
        # interior-only residual: isolates the non-telescoping volume defect (O(h^2))
        dpi = sch.laplacian(y[:N], T)
        dphi = sch.d1(y[N : 2 * N], "pi", T)
        rcell = g.volume * (y[N : 2 * N] * dpi + y[2 * N :] * dphi)
        res_int = float(abs(np.sum(rcell[2:-2]))) / scale
        residuals.append(res / scale)
        interior_residuals.append(res_int)
        rows.append(
            {
                "N": N,
                "h": g.h,
                "l2_error_psi": e,
                "relative_semidiscrete_residual": res / scale,
                "relative_semidiscrete_residual_interior": res_int,
            }
        )
    return {
        "study": "spherical_collocated_control",
        "rows": rows,
        "orders_psi": observed_order(errs),
        "residual_orders": observed_order(residuals),
        "interior_residual_orders": observed_order(interior_residuals),
    }


def study_lock_guard() -> dict:
    """The N1 lock guard must refuse production while numerics_lock is locked."""
    from numerics import gates

    rep = gates.evaluate(ROOT)
    blocked = rep["verdict"] == "N1_BLOCKED"
    raised = False
    try:
        gates.ensure_n1_allowed(ROOT)
    except gates.ProductionLocked:
        raised = True
    solver_dir = ROOT / "numerics" / "spherical_solver"
    scope_ok = not solver_dir.exists()
    return {
        "study": "n1_lock_guard",
        "verdict": rep["verdict"],
        "blocking_reasons": rep["blocking_reasons"],
        "guard_raises_while_locked": raised,
        "self_gravitating_solver_dir_absent": scope_ok,
        "pass": bool(blocked and raised and scope_ok),
    }


# ---------------------------------------------------------------------------
# self-tests (fail closed)
# ---------------------------------------------------------------------------
def selftest() -> dict:
    checks = []

    def rec(name, ok, detail):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})

    # 1. closed-form pulse really solves the spherical wave equation (continuum residual)
    ex = SphericalPulse(width=0.6, s0=-4.0)
    r = np.linspace(0.5, 7.5, 4001)
    t = 2.0
    dr = r[1] - r[0]
    psi = ex.psi(r, t)
    d2psi = np.gradient(np.gradient(psi, dr, edge_order=2), dr, edge_order=2)
    d1psi = np.gradient(psi, dr, edge_order=2)
    lap = d2psi + (2.0 / r) * d1psi
    dtl = dr
    psi_tt = (ex.psi(r, t + dtl) - 2 * psi + ex.psi(r, t - dtl)) / dtl**2
    sl = slice(4, -4)  # interior only: one-sided boundary stencils are not the object of the test
    wave_resid = float(np.max(np.abs(psi_tt[sl] - lap[sl])))
    rec("pulse solves u_tt = u_rr + 2/r u_r", wave_resid < 5e-3, f"max|residual|={wave_resid:.2e}")

    # 2. MMS source matches the analytic Laplacian
    mms = SphericalMMS(omega=2.5)
    rr = np.linspace(0.1, 0.9, 400)
    tt = 0.7
    drr = rr[1] - rr[0]
    psi_m = mms.psi(rr, tt)
    lap_m = np.gradient(np.gradient(psi_m, drr, edge_order=2), drr, edge_order=2) + (
        2.0 / rr
    ) * np.gradient(psi_m, drr, edge_order=2)
    psi_tt_m = -mms.omega**2 * psi_m
    src_err = float(np.max(np.abs(psi_tt_m[4:-4] - lap_m[4:-4] - mms.source(rr, tt)[4:-4])))
    rec("spherical MMS source identity", src_err < 5e-3, f"max|S - (psi_tt - lap)|={src_err:.2e}")

    # 3. FD symbol equals dense-matrix eigenvalue
    chk = symbol_spectrum_check(32, 1.0, 2)
    rec("symbol vs dense operator", chk["max_rel_error"] < 1e-12, f"rel={chk['max_rel_error']:.2e}")

    # 4. SBP boundary identity holds at t=0 for exact MMS data
    g, exs, sch, y = _spherical_mms_run(64, 1.0, 0.0)
    res = abs(sch.semi_discrete_residual(y, 0.0))
    rec("SBP semi-discrete identity", res < 1e-12, f"residual={res:.2e}")

    # 5. integration is deterministic
    a = study_cartesian_mms(2, (32,))["rows"][0]["l2_error"]
    b = study_cartesian_mms(2, (32,))["rows"][0]["l2_error"]
    rec("determinism", a == b, f"{a!r} == {b!r}")

    # 6. lock guard refuses N1 while locked
    guard = study_lock_guard()
    rec("N1 lock guard fails closed", guard["pass"], json.dumps(guard["blocking_reasons"])[:220])

    return {"pass": all(c["pass"] for c in checks), "checks": checks}


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def run_all(json_out: str | None = None) -> dict:
    t0 = time.perf_counter()
    report = {
        "artifact": "numerics/tests/lead_calibration.py",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "role": "lead independent reference calibration (third implementation family)",
        "scope_discipline": "flat space only; no self-gravitating solver code written or run",
        "provenance": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
        "selftest": selftest(),
        "studies": {},
    }
    report["studies"]["cartesian_mms"] = [
        study_cartesian_mms(o, res)
        for o, res in ((2, (64, 128, 256, 512)), (4, (32, 64, 128, 256)), (6, (16, 32, 64, 128)))
    ]
    report["studies"]["cartesian_dispersion"] = [
        study_cartesian_dispersion(o) for o in (2, 4, 6)
    ]
    report["studies"]["cartesian_invariants"] = [
        study_cartesian_invariants(o) for o in (2, 4, 6)
    ]
    report["studies"]["energy_defect"] = [study_energy_defect_order(o) for o in (2, 4, 6)]
    report["studies"]["spherical_mms"] = study_spherical_mms()
    report["studies"]["spherical_pulse"] = study_spherical_pulse()
    report["studies"]["collocated_control"] = study_collocated_control()
    report["studies"]["lock_guard"] = study_lock_guard()

    mms = report["studies"]["cartesian_mms"]
    disp = report["studies"]["cartesian_dispersion"]
    inv = report["studies"]["cartesian_invariants"]
    defect = report["studies"]["energy_defect"]
    sph = report["studies"]["spherical_mms"]
    pulse = report["studies"]["spherical_pulse"]
    ctrl = report["studies"]["collocated_control"]

    gates = {
        "L1_cartesian_mms_orders": all(
            order_ok(s["orders"], s["order_scheme"]) for s in mms
        ),
        "L2_dispersion_symbol_and_orders": all(
            all(r["symbol_rel_error"] < 1e-12 for r in s["rows"])
            and order_ok(s["phase_speed_orders"], s["order_scheme"], tol=0.35)
            and s["evolution_anchor"]["rel_difference"] < 1e-6
            for s in disp
        ),
        "L3_cartesian_invariants": all(
            s["spectral_energy_rel_drift"] < 1e-9
            and s["momentum_rel_drift"] < 1e-9
            and s["charge_rel_drift"] < 1e-9
            for s in inv
        ),
        "L4_energy_defect_orders": all(
            order_ok(s["orders"], s["order_scheme"], tol=0.45) for s in defect
        ),
        "L5_spherical_mms_order2": order_ok(sph["orders_psi"], 2.0, tol=0.25),
        "L6_sbp_identity_and_constraint": bool(
            sph["max_sbp_residual"] < 1e-12 and sph["max_constraint_residual"] < 1e-12
        ),
        "L7_pulse_flux_closure": bool(
            order_ok(pulse["flux_closure_orders"], 2.0, tol=0.6)
            and pulse["max_sbp_budget_residual"] < 1e-5
            and pulse["max_constraint_residual"] < 1e-12
            and pulse["rows"][-1]["energy_remaining_fraction"] < 1e-3
            and all(
                b["energy_remaining_fraction"] < a["energy_remaining_fraction"]
                for a, b in zip(pulse["rows"], pulse["rows"][1:])
            )
        ),
        "L8_collocated_control": bool(
            order_ok(ctrl["orders_psi"], 2.0, tol=0.25)
            and all(p >= 0.8 for p in normalise_orders(ctrl["residual_orders"]))
            and min(r["relative_semidiscrete_residual"] for r in ctrl["rows"])
            > 1e6 * max(sph["max_sbp_residual"], 1e-300)
            and min(r["relative_semidiscrete_residual_interior"] for r in ctrl["rows"]) > 0.1
        ),
        "L9_self_tests": report["selftest"]["pass"],
        "L10_lock_guard": report["studies"]["lock_guard"]["pass"],
    }
    report["gates"] = gates
    report["all_gates_pass"] = bool(all(gates.values()))
    report["wall_seconds"] = round(time.perf_counter() - t0, 3)
    report["claims_not_made"] = [
        "no claim that N0 is complete or accepted",
        "no claim about self-gravity, collapse, or critical phenomena",
        "no claim about WCC/SCC or any cosmic-censorship statement",
    ]
    if json_out:
        p = Path(json_out)
        if not p.is_absolute():
            p = ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, sort_keys=True))
        print(f"wrote {p}")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json-out", default=None)
    a = ap.parse_args(argv)
    if a.selftest:
        st = selftest()
        for c in st["checks"]:
            print(f"  [{'ok' if c['pass'] else 'FAIL'}] {c['name']}: {c['detail']}")
        print(json.dumps({"selftest_pass": st["pass"]}))
        return 0 if st["pass"] else 1
    rep = run_all(a.json_out)
    print(format_table(["gate", "pass"], [[k, v] for k, v in rep["gates"].items()]))
    print(json.dumps({"all_gates_pass": rep["all_gates_pass"],
                      "wall_seconds": rep["wall_seconds"]}, indent=2))
    return 0 if rep["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
