#!/usr/bin/env python3
"""N0-AXIS-051 -- independent direct-variable (unreduced) convergence test for N0.

Class binding: AF-WCC-SCALAR-SPH (calibration sub-case: fixed Minkowski, test field,
spherical symmetry, massless scalar, no self-gravity, no WCC/SCC statement).

Motivation (recorded gap, not invented here).  ``numerics/results/flat_wave_replication.json``
lists axes shared by all three published schemes and therefore NOT independently tested:

  1. the ``psi = r*phi`` reduction,
  2. the Dirichlet condition ``psi(0) = psi(R) = 0``,
  3. the Taylor start ``psi^1 = psi^0 + dt psi_t^0 + dt^2/2 psi_tt^0``.

Its own falsifier for the N0 order-2 claim is: "a demonstration that the shared Taylor
start / psi=r*phi reduction carries a discretization bug common to all three schemes."

This script attacks that falsifier with a discretisation that shares none of those axes:

  * evolved variable: the physical field ``u = phi`` directly (no ``psi = r*phi``);
  * origin treatment: the regular-centre rule ``L u(0) = 6 (u_1 - u_0)/dr^2``
    (correct for an even field; ``3 u_rr(0)``), not a Dirichlet value;
  * start: exact-time start ``u^1 = u_exact(., dt)`` (also run with a Taylor start to
    isolate that axis on its own);
  * time integration: implicit Crank-Nicolson, as in the published cnfd/cnfem pair.

Two cases are run against the same exact solution family as the harness
(``psi = F(r-t) - F(-r-t)``, ``F(s)=exp(-(s-r0)^2/(2 sigma^2))``, ``u = psi/r``):

  * ``pulse_far``    r0=10, sigma=1.5, t_end=6, r_max=30 -- the published harness case
    (note: this pulse does not excite the origin: u(0,t) <~ 1e-9);
  * ``pulse_origin`` r0=2,  sigma=1.0, t_end=6, r_max=30 -- added here because it makes
    u(0,t) = O(0.5), so the origin / reduction axis is actually exercised.

Positive control: the same direct scheme with the naive even-extension origin rule
``L u(0) = 2 (u_1 - u_0)/dr^2`` (which converges to ``u_rr`` not ``3 u_rr``) must lose
second order in ``pulse_origin``.  If it does not, the test is not sensitive to the axis
and the negative result is inconclusive.

Deterministic, numpy-only, no I/O except the report it writes.  Never claims node
completion, a gate verdict, or a theorem.
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

REPO = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

PUBLISHED_RESULT = REPO / "numerics" / "results" / "flat_wave_replication.json"
PUBLISHED_SOURCE = REPO / "numerics" / "tests" / "flat_wave_replication.py"
HARNESS_REFERENCE = REPO / "artifacts" / "flash-04" / "n0_acceptance" / "reference_solutions.py"
TAXONOMY = REPO / "research_map" / "formulation_taxonomy.yaml"
RESEARCH_MAP = REPO / "research_map" / "research_map.json"

TASK_ID = "W051-N0-AXIS-DIRECT-01"
NODE_ID = "N0"
CLASS_ID = "AF-WCC-SCALAR-SPH"

CONFIG = {
    "dr_values": [0.2, 0.1, 0.05],
    "cfl": 0.5,
    "r_max": 30.0,
    "t_end": 6.0,
    "p_expected": 2.0,
    "p_tol": 0.3,
    "temporal_cfl_values": [0.5, 0.25, 0.125, 0.0625],
}

CASES = {
    "pulse_far": {"r0": 10.0, "sigma": 1.5, "note": "published harness pulse; origin quiet"},
    "pulse_origin": {"r0": 2.0, "sigma": 1.0, "note": "added; u(0,t)=O(0.5), origin excited"},
}


# ---------------------------------------------------------------------------
# exact solution (same analytic family as the harness reference, re-derived here)
# ---------------------------------------------------------------------------
class PulseExact:
    """psi(r,t) = F(r-t) - F(-r-t); u(r,t) = psi(r,t)/r with the regular limit at r=0."""

    def __init__(self, r0: float = 10.0, sigma: float = 1.5) -> None:
        self.r0 = float(r0)
        self.sigma = float(sigma)

    def F(self, s):
        s = np.asarray(s, dtype=float)
        return np.exp(-((s - self.r0) ** 2) / (2.0 * self.sigma ** 2))

    def Fp(self, s):
        s = np.asarray(s, dtype=float)
        return -((s - self.r0) / self.sigma ** 2) * self.F(s)

    def Fpp(self, s):
        s = np.asarray(s, dtype=float)
        return (((s - self.r0) ** 2) / self.sigma ** 4 - 1.0 / self.sigma ** 2) * self.F(s)

    def Fppp(self, s):
        s = np.asarray(s, dtype=float)
        return (3.0 * (s - self.r0) / self.sigma ** 4
                - (s - self.r0) ** 3 / self.sigma ** 6) * self.F(s)

    # psi family -----------------------------------------------------------
    def psi(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.F(r - t) - self.F(-r - t)

    def psi_t(self, r, t):
        r = np.asarray(r, dtype=float)
        return -self.Fp(r - t) + self.Fp(-r - t)

    def psi_tt(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.Fpp(r - t) - self.Fpp(-r - t)

    def psi_rr(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.Fpp(r - t) - self.Fpp(-r - t)

    # regular physical field u = psi / r ----------------------------------
    def u(self, r, t):
        r = np.asarray(r, dtype=float)
        psi = self.psi(r, t)
        out = np.empty_like(r)
        nz = r > 0.0
        out[nz] = psi[nz] / r[nz]
        # u(0,t) = d_r psi(0,t) = Fp(-t) + Fp(t)
        out[~nz] = self.Fp(np.asarray(-t, dtype=float)) + self.Fp(np.asarray(t, dtype=float))
        return out

    def u_t(self, r, t):
        r = np.asarray(r, dtype=float)
        psi_t = self.psi_t(r, t)
        out = np.empty_like(r)
        nz = r > 0.0
        out[nz] = psi_t[nz] / r[nz]
        # u_t(0,t) = d_r psi_t(0,t) = -Fpp(-t) - Fpp(t)
        out[~nz] = -self.Fpp(np.asarray(-t, dtype=float)) - self.Fpp(np.asarray(t, dtype=float))
        return out

    def u_tt(self, r, t):
        r = np.asarray(r, dtype=float)
        psi_tt = self.psi_tt(r, t)
        out = np.empty_like(r)
        nz = r > 0.0
        out[nz] = psi_tt[nz] / r[nz]
        # u_tt(0,t) = d_r psi_tt(0,t) = Fppp(-t) + Fppp(t)
        out[~nz] = self.Fppp(np.asarray(-t, dtype=float)) + self.Fppp(np.asarray(t, dtype=float))
        return out


# ---------------------------------------------------------------------------
# grid / errors / fits  (psi-L2 metric matches the published replication exactly)
# ---------------------------------------------------------------------------
def grid(r_max: float, dr: float) -> np.ndarray:
    n = int(round(r_max / dr))
    if n < 4:
        raise ValueError("grid too small")
    return np.linspace(0.0, n * dr, n + 1)


def l2_error_psi(numeric_psi, exact_psi, dr) -> float:
    diff = np.asarray(numeric_psi, float) - np.asarray(exact_psi, float)
    return float(math.sqrt(float(np.sum(diff * diff)) * dr))


def l2_error_u_volume(numeric_u, exact_u, r, dr) -> float:
    """Absolute volume-weighted L2: sqrt(sum (du)^2 r^2 dr)."""
    diff = np.asarray(numeric_u, float) - np.asarray(exact_u, float)
    return float(math.sqrt(float(np.sum(diff * diff * np.asarray(r, float) ** 2)) * dr))


def rel_l2_error_u_volume(numeric_u, exact_u, r, dr) -> float:
    num = l2_error_u_volume(numeric_u, exact_u, r, dr)
    den = l2_error_u_volume(exact_u, np.zeros_like(np.asarray(exact_u, float)), r, dr)
    return float(num / den) if den > 0.0 else float("nan")


def linf_error_u(numeric_u, exact_u) -> float:
    return float(np.max(np.abs(np.asarray(numeric_u, float) - np.asarray(exact_u, float))))


def fit_order(drs, errs) -> float:
    x, y = np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float))
    return float(np.polyfit(x, y, 1)[0])


def pair_orders(drs, errs):
    return [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
            for i in range(len(errs) - 1)]


# ---------------------------------------------------------------------------
# linear algebra (general tridiagonal, precomputed Thomas factorisation)
# ---------------------------------------------------------------------------
class Tridiag:
    def __init__(self, a, b, c):
        self.a = np.asarray(a, float).copy()
        self.b = np.asarray(b, float).copy()
        self.c = np.asarray(c, float).copy()
        m = len(self.b)
        cp = np.empty(m)
        cp[0] = self.c[0] / self.b[0]
        for i in range(1, m):
            den = self.b[i] - self.a[i] * cp[i - 1]
            if den == 0.0:
                raise ZeroDivisionError("singular tridiagonal factorisation")
            cp[i] = self.c[i] / den
        self.cp = cp

    def solve(self, d):
        d = np.asarray(d, float)
        m = len(d)
        dp = np.empty(m)
        dp[0] = d[0] / self.b[0]
        for i in range(1, m):
            dp[i] = (d[i] - self.a[i] * dp[i - 1]) / (self.b[i] - self.a[i] * self.cp[i - 1])
        x = np.empty(m)
        x[-1] = dp[-1]
        for i in range(m - 2, -1, -1):
            x[i] = dp[i] - self.cp[i] * x[i + 1]
        return x

    def matvec(self, x):
        x = np.asarray(x, float)
        y = self.b * x
        y[:-1] += self.c[:-1] * x[1:]
        y[1:] += self.a[1:] * x[:-1]
        return y


# ---------------------------------------------------------------------------
# spatial operators
# ---------------------------------------------------------------------------
def reduced_laplacian(r, dr):
    """3-point Laplacian on interior nodes, Dirichlet psi(0)=psi(R)=0 (published form)."""
    m = len(r) - 2
    s = 1.0 / dr ** 2
    return Tridiag(np.full(m, s), np.full(m, -2.0 * s), np.full(m, s))


def direct_operator(r, dr, origin_mode="regular"):
    """Spherical operator L u = u_rr + (2/r) u_r on ALL nodes, Dirichlet row at r=R.

    origin_mode='regular' : L u(0) = 6 (u_1 - u_0)/dr^2   (correct for even u; 3 u_rr(0))
    origin_mode='even3pt' : L u(0) = 2 (u_1 - u_0)/dr^2   (2/3 of the correct curvature)
    origin_mode='garbage' : L u(0) = (54321 u_1 - 12345 u_0)/dr^2  (decoupling control)
    Row N is identity so u(R)=0 is imposed directly.

    Structural note under test: for a uniform grid with r_1 = dr the interior row 1 has
    lower coefficient 1/dr^2 - 1/(r_1 dr) = 0 exactly, and r_i * L_sph = Delta_1D (r .)
    identically on interior rows, so no origin rule can reach the interior.
    """
    n = len(r) - 1
    a = np.zeros(n + 1)
    b = np.zeros(n + 1)
    c = np.zeros(n + 1)
    if origin_mode == "regular":
        b[0], c[0] = -6.0 / dr ** 2, 6.0 / dr ** 2
    elif origin_mode == "even3pt":
        b[0], c[0] = -2.0 / dr ** 2, 2.0 / dr ** 2
    elif origin_mode == "garbage":
        b[0], c[0] = -12345.0 / dr ** 2, 54321.0 / dr ** 2
    else:
        raise ValueError(origin_mode)
    for i in range(1, n):
        # (2/r) u_r  ->  (u_{i+1}-u_{i-1}) / (r_i dr)
        a[i] = 1.0 / dr ** 2 - 1.0 / (r[i] * dr)
        b[i] = -2.0 / dr ** 2
        c[i] = 1.0 / dr ** 2 + 1.0 / (r[i] * dr)
    b[n] = 1.0
    return a, b, c


def apply_direct_operator(a, b, c, u):
    y = b * u
    y[:-1] += c[:-1] * u[1:]
    y[1:] += a[1:] * u[:-1]
    return y


# ---------------------------------------------------------------------------
# solvers
# ---------------------------------------------------------------------------
class ReducedCN:
    """Published cnfd: CN + 3-pt FD on psi = r*phi with Dirichlet ends (re-implemented).

    start='taylor' : published start psi^1 = psi^0 + dt psi_t^0 + dt^2/2 A psi^0
    start='exact'  : psi^1 = psi_exact(., dt)   [removes the Taylor-start axis]
    """

    name = "reduced_cn"

    def __init__(self, r, dt, pulse, start="taylor"):
        self.r, self.dr, self.dt = r, float(r[1] - r[0]), float(dt)
        self.pulse = pulse
        self.n = len(r) - 1
        self.m = self.n - 1
        self.A = reduced_laplacian(r, self.dr)
        c = 0.5 * self.dt ** 2
        s = 1.0 / self.dr ** 2
        self.B = Tridiag(np.full(self.m, -c * s), np.full(self.m, 1.0 + 2.0 * c * s),
                         np.full(self.m, -c * s))
        psi0, psi_t0, psi_tt0 = pulse.psi(r, 0.0), pulse.psi_t(r, 0.0), pulse.psi_tt(r, 0.0)
        self.psi = np.array(psi0, float)
        self.psi_prev = None
        self.t = 0.0
        self.steps = 0
        psi1 = np.zeros_like(self.psi)
        if start == "taylor":
            psi1[1:-1] = (psi0[1:-1] + self.dt * psi_t0[1:-1]
                          + 0.5 * self.dt ** 2 * self.A.matvec(psi0[1:-1]))
        elif start == "exact":
            psi1[1:-1] = pulse.psi(r[1:-1], self.dt)
        else:
            raise ValueError(start)
        psi1[0] = psi1[-1] = 0.0
        self._psi1 = psi1

    def step(self):
        if self.psi_prev is None:
            self.psi_prev, self.psi = self.psi, self._psi1
        else:
            rhs = 2.0 * self.psi[1:-1] - self.B.matvec(self.psi_prev[1:-1])
            nxt = np.zeros_like(self.psi)
            nxt[1:-1] = self.B.solve(rhs)
            if not np.all(np.isfinite(nxt)):
                raise FloatingPointError("non-finite reduced CN state")
            self.psi_prev, self.psi = self.psi, nxt
        self.t += self.dt
        self.steps += 1

    def u_numeric(self):
        """u = psi/r for the reduced scheme (limit 0 at r=0 is exactly psi(0)=0)."""
        return self.psi / np.where(self.r > 0, self.r, 1.0)


class DirectCN:
    """CN on the physical field u directly, no psi = r*phi reduction.

    L u = u_rr + (2/r) u_r, regular origin rule, u(R)=0.
    B u^{n+1} = 2 u^n - B u^{n-1},  B = I - dt^2/2 L.
    start='taylor' : u^1 = u^0 + dt u_t^0 + dt^2/2 (L u^0)   (scheme-consistent)
    start='exact'  : u^1 = u_exact(., dt)
    origin_mode    : 'regular' (6/dr^2) or 'even3pt' (2/dr^2, positive control)
    """

    name = "direct_cn"

    def __init__(self, r, dt, pulse, start="exact", origin_mode="regular", pin_origin=None):
        self.r, self.dr, self.dt = r, float(r[1] - r[0]), float(dt)
        self.pulse = pulse
        self.start_kind = start
        self.origin_mode = origin_mode
        self.pin_origin = pin_origin
        self.n = len(r) - 1
        a, b, c = direct_operator(r, self.dr, origin_mode=origin_mode)
        self.La, self.Lb, self.Lc = a, b, c
        cc = 0.5 * self.dt ** 2
        self.B = Tridiag(-cc * a, 1.0 - cc * b, -cc * c)
        u0 = pulse.u(r, 0.0)
        self.u = np.array(u0, float)
        self.u_prev = None
        self.t = 0.0
        self.steps = 0
        u1 = np.zeros_like(self.u)
        if start == "taylor":
            ut0 = pulse.u_t(r, 0.0)
            Lu0 = apply_direct_operator(a, b, c, u0)
            u1 = u0 + self.dt * ut0 + 0.5 * self.dt ** 2 * Lu0
        elif start == "exact":
            u1 = pulse.u(r, self.dt)
        else:
            raise ValueError(start)
        u1[-1] = 0.0
        if self.pin_origin is not None:
            u1[0] = float(self.pin_origin)
        self._u1 = u1

    def step(self):
        if self.u_prev is None:
            self.u_prev, self.u = self.u, self._u1
        else:
            rhs = 2.0 * self.u - self.B.matvec(self.u_prev)
            nxt = self.B.solve(rhs)
            nxt[-1] = 0.0
            if not np.all(np.isfinite(nxt)):
                raise FloatingPointError("non-finite direct CN state")
            self.u_prev, self.u = self.u, nxt
        if self.pin_origin is not None:
            self.u[0] = float(self.pin_origin)
        self.t += self.dt
        self.steps += 1

    def psi_numeric(self):
        return self.r * self.u


SOLVERS = {
    "reduced_cn_taylor": lambda r, dt, p: ReducedCN(r, dt, p, start="taylor"),
    "reduced_cn_exact": lambda r, dt, p: ReducedCN(r, dt, p, start="exact"),
    "direct_cn_taylor": lambda r, dt, p: DirectCN(r, dt, p, start="taylor", origin_mode="regular"),
    "direct_cn_exact": lambda r, dt, p: DirectCN(r, dt, p, start="exact", origin_mode="regular"),
    "direct_cn_wrongorigin_taylor": lambda r, dt, p: DirectCN(r, dt, p, start="taylor", origin_mode="even3pt"),
    "direct_cn_wrongorigin_exact": lambda r, dt, p: DirectCN(r, dt, p, start="exact", origin_mode="even3pt"),
    "direct_cn_garbage_exact": lambda r, dt, p: DirectCN(r, dt, p, start="exact", origin_mode="garbage"),
    "direct_cn_pinned_exact": lambda r, dt, p: DirectCN(r, dt, p, start="exact", origin_mode="regular",
                                                         pin_origin=17.0),
}


def run_case(scheme, dr, cfl, pulse, r_max=30.0, t_end=6.0):
    r = grid(r_max, dr)
    dt = cfl * dr
    solver = SOLVERS[scheme](r, dt, pulse)
    n_steps = int(math.ceil(t_end / dt - 1e-12))
    for _ in range(n_steps):
        solver.step()
    tf = solver.t
    if hasattr(solver, "psi"):
        psi_num = np.array(solver.psi, float)
        u_num = solver.u_numeric()
    else:
        psi_num = solver.psi_numeric()
        u_num = np.array(solver.u, float)
    return {
        "scheme": scheme, "dr": dr, "dt": dt, "cfl": cfl, "steps": solver.steps,
        "final_t": tf, "r": r, "psi_num": psi_num, "u_num": u_num,
        "max_abs_u": float(np.max(np.abs(u_num))),
    }


def metrics(case, pulse):
    r = case["r"]
    t = case["final_t"]
    ex_u = pulse.u(r, t)
    ex_psi = r * ex_u
    return {
        "E_psi_abs": l2_error_psi(case["psi_num"], ex_psi, case["dr"]),
        "E_u_abs_vol": l2_error_u_volume(case["u_num"], ex_u, r, case["dr"]),
        "E_u_rel_vol": rel_l2_error_u_volume(case["u_num"], ex_u, r, case["dr"]),
        "E_u_inf": linf_error_u(case["u_num"], ex_u),
        "max_abs_u": case["max_abs_u"],
    }


def order_study(scheme, case_name, dr_values=None, cfl=None, pulse=None):
    dr_values = dr_values or CONFIG["dr_values"]
    cfl = CONFIG["cfl"] if cfl is None else cfl
    pulse = pulse or PulseExact(**{k: CASES[case_name][k] for k in ("r0", "sigma")})
    rows = []
    for dr in dr_values:
        case = run_case(scheme, dr, cfl, pulse, CONFIG["r_max"], CONFIG["t_end"])
        m = metrics(case, pulse)
        rows.append({"dr": float(dr), "dt": case["dt"], "steps": case["steps"],
                     "final_t": case["final_t"], **m})
    out = {"scheme": scheme, "case": case_name, "cfl": cfl, "rows": rows, "fits": {}}
    for metric in ("E_psi_abs", "E_u_abs_vol", "E_u_rel_vol", "E_u_inf"):
        errs = [row[metric] for row in rows]
        finite = all(math.isfinite(e) and e > 0.0 for e in errs)
        monotone = all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))
        out["fits"][metric] = {
            "fit_order": fit_order(dr_values, errs) if finite else None,
            "pair_orders": pair_orders(dr_values, errs) if finite else None,
            "monotone": monotone,
            "within_p_tol": (bool(abs(fit_order(dr_values, errs) - CONFIG["p_expected"]) <= CONFIG["p_tol"])
                             if finite else False),
        }
    return out


# ---------------------------------------------------------------------------
# self-tests and controls
# ---------------------------------------------------------------------------
def operator_consistency_analytic(dr_values=None):
    """L u vs exact Laplacian on an even analytic function with O(1) origin value.

    u(r) = exp(-r^2/(2 s^2));  Delta u = (r^2/s^4 - 3/s^2) u.  The origin rule is
    exactly what is under test: 6(u_1-u_0)/dr^2 must reproduce 3 u_rr(0) = -3/s^2.
    """
    dr_values = dr_values or CONFIG["dr_values"]
    s = 1.5
    rows = []
    for dr in dr_values:
        r = grid(10.0, dr)
        u = np.exp(-r ** 2 / (2.0 * s ** 2))
        exact = (r ** 2 / s ** 4 - 3.0 / s ** 2) * u
        a, b, c = direct_operator(r, dr, origin_mode="regular")
        Lu = apply_direct_operator(a, b, c, u)
        a_w, b_w, c_w = direct_operator(r, dr, origin_mode="even3pt")
        Lu_w = apply_direct_operator(a_w, b_w, c_w, u)
        # row N of L is the Dirichlet constraint (identity), not a differential stencil:
        # compare the operator rows 0..N-1 only.
        rows.append({
            "dr": float(dr),
            "origin_exact": float(exact[0]),
            "origin_regular": float(Lu[0]),
            "origin_even3pt": float(Lu_w[0]),
            "linf_regular": float(np.max(np.abs(Lu[:-1] - exact[:-1]))),
            "linf_even3pt": float(np.max(np.abs(Lu_w[:-1] - exact[:-1]))),
        })
    reg = [row["linf_regular"] for row in rows]
    return {
        "rows": rows,
        "regular_fit_order": fit_order(dr_values, reg),
        "regular_pair_orders": pair_orders(dr_values, reg),
        "origin_regular_relative_error": [abs(row["origin_regular"] - row["origin_exact"]) / abs(row["origin_exact"])
                                          for row in rows],
        "origin_even3pt_relative_error": [abs(row["origin_even3pt"] - row["origin_exact"]) / abs(row["origin_exact"])
                                          for row in rows],
        "regular_second_order": bool(abs(fit_order(dr_values, reg) - 2.0) < 0.25),
    }


def operator_consistency_pulse_origin(dr_values=None):
    """Same consistency test on the origin-excited pulse at t=0 (checks u_tt limit too)."""
    dr_values = dr_values or CONFIG["dr_values"]
    pulse = PulseExact(**{k: CASES["pulse_origin"][k] for k in ("r0", "sigma")})
    rows = []
    for dr in dr_values:
        r = grid(CONFIG["r_max"], dr)
        u0 = pulse.u(r, 0.0)
        utt = pulse.u_tt(r, 0.0)
        a, b, c = direct_operator(r, dr, origin_mode="regular")
        Lu = apply_direct_operator(a, b, c, u0)
        rows.append({"dr": float(dr), "u_origin": float(u0[0]),
                     "linf_Lu_minus_utt": float(np.max(np.abs(Lu[:-1] - utt[:-1])))})
    errs = [row["linf_Lu_minus_utt"] for row in rows]
    return {"rows": rows, "fit_order": fit_order(dr_values, errs),
            "pair_orders": pair_orders(dr_values, errs),
            "second_order": bool(abs(fit_order(dr_values, errs) - 2.0) < 0.3)}


def published_wiring_check(control, published):
    """The re-implemented published cnfd must reproduce the published numbers."""
    ref = None
    for v in published["order_studies"]:
        if v["scheme"] == "cnfd":
            ref = v
    rows_pub = {float(r["dr"]): float(r["l2_error"]) for r in ref["rows"]}
    rel = []
    for row in control["rows"]:
        rel.append(abs(row["E_psi_abs"] - rows_pub[float(row["dr"])]) / rows_pub[float(row["dr"])])
    return {
        "published_fit_order": float(ref["fit_order"]),
        "reimplementation_fit_order": float(control["fits"]["E_psi_abs"]["fit_order"]),
        "abs_fit_order_delta": abs(float(control["fits"]["E_psi_abs"]["fit_order"]) - float(ref["fit_order"])),
        "max_rel_row_error": float(max(rel)),
        "pass": bool(max(rel) < 1e-6 and abs(float(control["fits"]["E_psi_abs"]["fit_order"])
                                            - float(ref["fit_order"])) < 1e-6),
    }


def structural_checks(pulse, case_name, dr_values=None, cfl=None):
    """Measure the two structural claims directly.

    (1) reduction identity: the direct (unreduced) psi must equal the reduced psi.
    (2) origin decoupling: four different origin rules must give the same interior;
        their u(0) values must nevertheless differ (otherwise the control is vacuous).
    """
    dr_values = dr_values or [0.2, 0.05]
    cfl = CONFIG["cfl"] if cfl is None else cfl
    out = {"case": case_name, "cfl": cfl, "per_dr": []}
    for dr in dr_values:
        red = run_case("reduced_cn_exact", dr, cfl, pulse, CONFIG["r_max"], CONFIG["t_end"])
        dirs = {name: run_case(name, dr, cfl, pulse, CONFIG["r_max"], CONFIG["t_end"])
                for name in ("direct_cn_exact", "direct_cn_wrongorigin_exact",
                             "direct_cn_garbage_exact", "direct_cn_pinned_exact")}
        psi_ref = red["psi_num"]
        denom = float(np.max(np.abs(psi_ref))) or 1.0
        # interior = nodes r>0 (origin row is the only place the rules differ)
        red_u_interior = red["psi_num"][1:] / red["r"][1:]
        reductions = {}
        for name, case in dirs.items():
            d = np.abs(case["psi_num"] - psi_ref)
            reductions[name] = {
                "max_abs_diff_vs_reduced_psi": float(np.max(d)),
                "max_rel_diff_vs_reduced_psi": float(np.max(d) / denom),
                "u0_final": float(case["u_num"][0]),
            }
        base = dirs["direct_cn_exact"]
        decoupling = {}
        for name, case in dirs.items():
            d_interior = np.abs(case["u_num"][1:] - base["u_num"][1:])
            decoupling[name] = {
                "max_abs_interior_diff_vs_regular": float(np.max(d_interior)),
                "u0_final": float(case["u_num"][0]),
                "u0_diff_vs_regular": float(abs(case["u_num"][0] - base["u_num"][0])),
            }
        out["per_dr"].append({
            "dr": float(dr),
            "u0_regular": float(base["u_num"][0]),
            "reduction_identity": reductions,
            "origin_decoupling": decoupling,
        })
    max_red_rel = max(v["max_rel_diff_vs_reduced_psi"]
                      for p in out["per_dr"] for v in p["reduction_identity"].values())
    max_dec_abs = max(v["max_abs_interior_diff_vs_regular"]
                      for p in out["per_dr"] for v in p["origin_decoupling"].values())
    min_u0_spread = min(
        max(v["u0_diff_vs_regular"] for v in p["origin_decoupling"].values())
        for p in out["per_dr"])
    out["reduction_identity_confirmed"] = bool(max_red_rel < 1e-12)
    out["origin_decoupling_confirmed"] = bool(max_dec_abs < 1e-12 and min_u0_spread > 1e-6)
    out["max_rel_reduction_diff"] = float(max_red_rel)
    out["max_abs_interior_decoupling_diff"] = float(max_dec_abs)
    out["min_u0_spread_between_rules"] = float(min_u0_spread)
    return out


def discrete_identity_check(dr_values=None):
    """Directly check r_i (L_sph u)_i = (Delta_1D (r u))_i on interior rows, and a_1 == 0.

    These are the two algebraic facts that make the psi=r*phi reduction and the origin
    rule non-independent axes.  They are semi-discrete statements: they do not reference
    the time integrator, so they hold for any method of lines on this grid.
    """
    dr_values = dr_values or CONFIG["dr_values"]
    rng = np.random.default_rng(20260912)
    rows = []
    for dr in dr_values:
        r = grid(CONFIG["r_max"], dr)
        n = len(r) - 1
        u = rng.standard_normal(n + 1)
        u[0] = 0.0  # psi_0 = r_0 u_0 = 0 by construction; value of u_0 is free
        u[-1] = 0.0
        a, b, c = direct_operator(r, dr, origin_mode="regular")
        Lu = apply_direct_operator(a, b, c, u)
        psi = r * u
        Apsi = np.zeros(n + 1)
        Apsi[1:n] = (psi[2:] - 2.0 * psi[1:n] + psi[:n - 1]) / dr ** 2
        lhs = r[1:n] * Lu[1:n]
        res = np.abs(lhs - Apsi[1:n])
        scale = max(float(np.max(np.abs(Apsi[1:n]))), 1e-300)
        rows.append({
            "dr": float(dr),
            "row1_lower_coefficient_a1": float(a[1]),
            "row1_lower_coefficient_is_exactly_zero": bool(a[1] == 0.0),
            "max_abs_residual": float(np.max(res)),
            "max_rel_residual": float(np.max(res) / scale),
        })
    return {
        "rows": rows,
        "all_row1_lower_exactly_zero": bool(all(row["row1_lower_coefficient_is_exactly_zero"] for row in rows)),
        "max_rel_residual": float(max(row["max_rel_residual"] for row in rows)),
        "identity_holds_to_roundoff": bool(max(row["max_rel_residual"] for row in rows) < 1e-12),
    }


def temporal_spatial_split(case_name, dr_values, cfl_values, pulse, scheme="direct_cn_exact"):
    """E(dr,dt) = a(dr) + b dt^q.  Fit in dt^2 at fixed dr -> intercept a(dr), then order of a(dr)."""
    per_dr = []
    for dr in dr_values:
        rows = []
        for cfl in cfl_values:
            case = run_case(scheme, dr, cfl, pulse, CONFIG["r_max"], CONFIG["t_end"])
            m = metrics(case, pulse)
            rows.append({"cfl": cfl, "dt": cfl * dr, "steps": case["steps"], **m})
        dts = np.array([row["dt"] for row in rows])
        fit = {}
        for metric in ("E_psi_abs", "E_u_abs_vol", "E_u_rel_vol", "E_u_inf"):
            y = np.array([row[metric] for row in rows])
            coef = np.polyfit(dts ** 2, y, 1)
            pred = np.polyval(coef, dts ** 2)
            ss_res = float(np.sum((y - pred) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            diffs = [float((y[i] - y[i + 1]) / (y[i + 1] - y[i + 2])) if (y[i + 1] - y[i + 2]) != 0 else None
                     for i in range(len(y) - 2)]
            fit[metric] = {
                "intercept_a_dr": float(coef[1]),
                "slope_b": float(coef[0]),
                "linear_in_dt2_r2": (1.0 - ss_res / ss_tot) if ss_tot > 0 else None,
                "successive_ratio_4x_if_q2": diffs,
            }
        per_dr.append({"dr": float(dr), "rows": rows, "fit_vs_dt2": fit})

    spatial = {}
    for metric in ("E_psi_abs", "E_u_abs_vol", "E_u_rel_vol", "E_u_inf"):
        a_vals = [p["fit_vs_dt2"][metric]["intercept_a_dr"] for p in per_dr]
        if all(math.isfinite(v) and v > 0.0 for v in a_vals):
            spatial[metric] = {
                "intercepts": a_vals,
                "fit_order_spatial": fit_order([p["dr"] for p in per_dr], a_vals),
                "pair_orders_spatial": pair_orders([p["dr"] for p in per_dr], a_vals),
            }
        else:
            spatial[metric] = {"intercepts": a_vals, "fit_order_spatial": None, "pair_orders_spatial": None}
    return {"scheme": scheme, "case": case_name, "per_dr": per_dr, "spatial_from_intercepts": spatial}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    t0 = time.time()
    published = json.loads(PUBLISHED_RESULT.read_text())

    report = {
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "artifact_kind": "independent_numerical_falsifier_test",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "config": CONFIG,
        "cases": CASES,
        "scope": {
            "class_binding": "calibration sub-case of AF-WCC-SCALAR-SPH (fixed Minkowski, "
                             "test field, no self-gravity); class binding remains PROVISIONAL",
            "shared_axes_attacked": ["psi = r*phi reduction",
                                     "Dirichlet psi(0)=0 origin treatment",
                                     "Taylor start"],
            "why_case_pulse_origin": "pulse_far leaves the origin quiet (u(0,t) <~ 1e-9), so an "
                                     "origin-rule bug would be invisible there; pulse_origin has "
                                     "u(0,0) = O(0.5).",
            "not_covered": ["temporal order of the published schemes at fixed dt (only the "
                            "direct scheme is split here)",
                            "any self-gravitating or non-linear dynamics",
                            "any statement about WCC/SCC",
                            "phi reconstruction at r=0 for the reduced scheme (published harness "
                            "item, untouched)"],
            "structural_claim_limit": "the discrete identity r_i (L_sph u)_i = (Delta_1D r u)_i "
                                      "and the exact origin decoupling are properties of the uniform "
                                      "node-centered grid with r_1 = dr and the 1/r form; a staggered, "
                                      "finite-volume or non-uniform scheme, or one with a non-trivial "
                                      "origin closure on the reduced variable, is not covered.",
        },
        "selftest": {},
        "order_studies": {},
        "structural_checks": {},
        "temporal_spatial_split": {},
        "controls": {},
        "determinism": {},
        "falsifier": {},
    }

    # 1. analytic operator consistency (origin rule)
    report["selftest"]["operator_consistency_analytic"] = operator_consistency_analytic()
    report["selftest"]["operator_consistency_pulse_origin"] = operator_consistency_pulse_origin()
    report["selftest"]["discrete_identity"] = discrete_identity_check()

    pulses = {name: PulseExact(r0=cfg["r0"], sigma=cfg["sigma"]) for name, cfg in CASES.items()}

    # 2. order studies
    for case_name, pulse in pulses.items():
        report["order_studies"][case_name] = {}
        for scheme in SOLVERS:
            study = order_study(scheme, case_name, pulse=pulse)
            report["order_studies"][case_name][scheme] = study
            if not study["fits"]["E_psi_abs"]["monotone"]:
                # record but continue; non-monotone is itself a finding
                pass

    # 3. wiring check against the published cnfd numbers
    report["selftest"]["published_wiring"] = published_wiring_check(
        report["order_studies"]["pulse_far"]["reduced_cn_taylor"], published)

    # 4. structural checks: reduction identity and origin decoupling
    report["structural_checks"] = {name: structural_checks(pulse, name) for name, pulse in pulses.items()}

    # 5. temporal/spatial separation for the direct scheme (case A and B)
    for case_name, pulse in pulses.items():
        report["temporal_spatial_split"][case_name] = temporal_spatial_split(
            case_name, CONFIG["dr_values"][1:], CONFIG["temporal_cfl_values"], pulse)

    # 6. controls
    p_org = pulses["pulse_origin"]
    dir_exact_far = report["order_studies"]["pulse_far"]["direct_cn_exact"]["fits"]["E_psi_abs"]["fit_order"]
    dir_exact_org = report["order_studies"]["pulse_origin"]["direct_cn_exact"]["fits"]["E_psi_abs"]["fit_order"]
    red_taylor_far = report["order_studies"]["pulse_far"]["reduced_cn_taylor"]["fits"]["E_psi_abs"]["fit_order"]
    red_exact_far = report["order_studies"]["pulse_far"]["reduced_cn_exact"]["fits"]["E_psi_abs"]["fit_order"]
    taylor_deltas = {}
    for case_name in CASES:
        for scheme, exact_scheme in (("reduced_cn_taylor", "reduced_cn_exact"),
                                     ("direct_cn_taylor", "direct_cn_exact")):
            p_t = report["order_studies"][case_name][scheme]["fits"]["E_psi_abs"]["fit_order"]
            p_e = report["order_studies"][case_name][exact_scheme]["fits"]["E_psi_abs"]["fit_order"]
            taylor_deltas[f"{case_name}:{scheme}"] = {
                "taylor": p_t, "exact": p_e,
                "delta": (None if (p_t is None or p_e is None) else p_t - p_e),
                "row_identical": bool(np.allclose(
                    [r["E_psi_abs"] for r in report["order_studies"][case_name][scheme]["rows"]],
                    [r["E_psi_abs"] for r in report["order_studies"][case_name][exact_scheme]["rows"]],
                    rtol=1e-12, atol=0.0)),
            }
    report["controls"] = {
        "taylor_start_axis": taylor_deltas,
        "taylor_start_immaterial": bool(all(
            v["delta"] is not None and abs(v["delta"]) < 0.05 for v in taylor_deltas.values())),
        "origin_rules_are_not_vacuous": {
            name: {"min_u0_spread_between_rules": sc["min_u0_spread_between_rules"]}
            for name, sc in report["structural_checks"].items()},
    }

    # 7. determinism
    a = run_case("direct_cn_exact", 0.1, 0.5, p_org, CONFIG["r_max"], CONFIG["t_end"])
    b = run_case("direct_cn_exact", 0.1, 0.5, p_org, CONFIG["r_max"], CONFIG["t_end"])
    report["determinism"] = {
        "bitwise_equal": bool(np.array_equal(a["u_num"], b["u_num"]) and a["final_t"] == b["final_t"]),
        "final_t": a["final_t"],
    }

    # 8. verdict + falsifier
    tol = CONFIG["p_tol"]
    p_tol_hit = bool(dir_exact_far is not None and dir_exact_org is not None
                     and abs(dir_exact_far - 2.0) <= tol and abs(dir_exact_org - 2.0) <= tol)
    wiring_ok = report["selftest"]["published_wiring"]["pass"]
    struct_ok = all(sc["reduction_identity_confirmed"] and sc["origin_decoupling_confirmed"]
                    for sc in report["structural_checks"].values())
    identity_ok = bool(report["selftest"]["discrete_identity"]["identity_holds_to_roundoff"]
                       and report["selftest"]["discrete_identity"]["all_row1_lower_exactly_zero"])
    spatial_ok = all(
        (split["spatial_from_intercepts"]["E_psi_abs"]["fit_order_spatial"] is not None
         and abs(split["spatial_from_intercepts"]["E_psi_abs"]["fit_order_spatial"] - 2.0) <= tol)
        for split in report["temporal_spatial_split"].values())
    report["verdict"] = {
        "direct_second_order_within_p_tol": p_tol_hit,
        "direct_fit_order_pulse_far": dir_exact_far,
        "direct_fit_order_pulse_origin": dir_exact_org,
        "reduction_identity_confirmed": bool(all(
            sc["reduction_identity_confirmed"] for sc in report["structural_checks"].values())),
        "origin_decoupling_confirmed": bool(all(
            sc["origin_decoupling_confirmed"] for sc in report["structural_checks"].values())),
        "discrete_operator_identity_confirmed": identity_ok,
        "taylor_start_immaterial": report["controls"]["taylor_start_immaterial"],
        "spatial_order_isolated_from_temporal": bool(spatial_ok),
        "published_wiring_ok": bool(wiring_ok),
        "overall": ("falsifier_not_triggered"
                    if (p_tol_hit and wiring_ok and struct_ok and identity_ok
                        and report["controls"]["taylor_start_immaterial"] and spatial_ok)
                    else "falsifier_triggered_or_inconclusive"),
    }
    report["falsifier"] = {
        "target_claim": "N0 shared-axis risk that psi=r*phi reduction / origin treatment / "
                        "Taylor start carries a discretisation bug common to the three published schemes",
        "primary": "CONFIRMED if any of: (a) direct-equivalent psi departs from reduced psi by more "
                   "than 1e-12 relative (reduction is not discretely exact); (b) any origin rule moves "
                   "an interior node by more than 1e-12 absolute while the rules genuinely differ at "
                   "r=0; (c) the direct psi-L2 order leaves [2.0 +/- 0.3] in either case, or the "
                   "Taylor-start vs exact-start orders differ by more than 0.05; (d) the spatial order "
                   "recovered from dt->0 intercepts leaves [2.0 +/- 0.3].",
        "sensitivity": "The decoupling claim is VACUOUS if the four origin rules do not produce "
                       "different u(0) values; min_u0_spread_between_rules is reported.",
        "wiring": "All numbers are VOID if the reduced_cn_taylor re-implementation does not reproduce "
                  "the published cnfd fit order 1.993478 and row errors to < 1e-6 relative.",
        "expected_if_no_bug": "reduction identity to roundoff, origin decoupling to roundoff, all "
                              "orders within [1.7, 2.3], Taylor-start delta < 0.05",
    }

    # 8. input hashes (provenance of what was read)
    inputs = {}
    for label, path in (("published_result", PUBLISHED_RESULT), ("published_source", PUBLISHED_SOURCE),
                        ("harness_reference", HARNESS_REFERENCE), ("taxonomy", TAXONOMY),
                        ("research_map", RESEARCH_MAP)):
        inputs[label] = {"path": str(path.relative_to(REPO)), "sha256": sha256_file(path)} if path.exists() else None
    report["inputs"] = inputs
    report["script"] = {"path": str(Path(__file__).resolve().relative_to(REPO)),
                        "sha256": sha256_file(Path(__file__).resolve())}
    report["wall_seconds"] = round(time.time() - t0, 2)

    out_path = OUT_DIR / "report.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    report["report_sha256"] = sha256_file(out_path)

    # human summary
    print(f"{TASK_ID}  class={CLASS_ID} node={NODE_ID}")
    print(f"published wiring: {report['selftest']['published_wiring']}")
    print(f"operator consistency (analytic): order={report['selftest']['operator_consistency_analytic']['regular_fit_order']:.4f} "
          f"origin rel err regular={report['selftest']['operator_consistency_analytic']['origin_regular_relative_error']} "
          f"even3pt={report['selftest']['operator_consistency_analytic']['origin_even3pt_relative_error']}")
    for case_name in CASES:
        for scheme in SOLVERS:
            f = report["order_studies"][case_name][scheme]["fits"]["E_psi_abs"]
            print(f"  {case_name:13s} {scheme:30s} p={f['fit_order'] if f['fit_order'] is None else round(f['fit_order'],6)} "
                  f"pairs={[round(p,4) for p in (f['pair_orders'] or [])]}")
    for case_name, split in report["temporal_spatial_split"].items():
        ss = split["spatial_from_intercepts"]["E_psi_abs"]
        print(f"temporal split {case_name}: spatial order from dt->0 intercepts = "
              f"{ss['fit_order_spatial']} (intercepts={['%.3e' % v for v in ss['intercepts']]})")
    for case_name, sc in report["structural_checks"].items():
        print(f"structural {case_name}: reduction max rel diff={sc['max_rel_reduction_diff']:.3e} "
              f"confirmed={sc['reduction_identity_confirmed']}; origin decoupling max abs diff="
              f"{sc['max_abs_interior_decoupling_diff']:.3e} min u0 spread={sc['min_u0_spread_between_rules']:.3e} "
              f"confirmed={sc['origin_decoupling_confirmed']}")
    di = report["selftest"]["discrete_identity"]
    print(f"discrete identity: a1==0 exactly={di['all_row1_lower_exactly_zero']} "
          f"max rel residual={di['max_rel_residual']:.3e} holds={di['identity_holds_to_roundoff']}")
    print(f"verdict: {report['verdict']}")
    print(f"report sha256: {report['report_sha256']}")
    print(f"wall_seconds: {report['wall_seconds']}")
    return report


if __name__ == "__main__":
    main()
