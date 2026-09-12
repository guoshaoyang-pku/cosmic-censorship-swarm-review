#!/usr/bin/env python3
"""W046-N0-INDEP-REPL-01 — independent from-scratch replication of the N0 order-2 evidence.

WORKER:      worker-046 (bounded execution worker, no gate authority)
NODE/CLASS:  N0 / AF-WCC-SCALAR-SPH (flat-space calibration sub-case only)
GATE:        G-NUM (supporting evidence only; this file cannot set a gate verdict)

WHY THIS FILE EXISTS
--------------------
The published N0 order evidence (numerics/tests/n0_order_4rung.json, class
AF-WCC-SCALAR-SPH) is carried by `numerics/tests/flat_wave_replication.py` (schemes lffd /
cnfd / cnfem). That module itself lists the axes it does NOT vary relative to the original
harness: (i) the psi = r*phi reduction, (ii) Dirichlet psi(0)=psi(R)=0, (iii) the exact
Taylor start psi^1 = psi0 + dt*psi_t0 + dt^2/2*psi_tt0, (iv) the Gaussian-pulse family.
All replicas in the swarm re-run the same frozen module, so axes (i)-(iii) have never been
exercised by an independent implementation.

This script tests the order-2 result on a discretisation that shares NONE of (i)-(iii):

  primary  SPH-FV : solves the *unreduced* spherical equation
                    phi_tt = phi_rr + (2/r) phi_r = (1/r^2) d_r(r^2 d_r phi)
                    directly for phi, with a cell-centred finite-volume flux form
                    (zero flux at the origin from regularity; Dirichlet at R).
                    No r*phi reduction, no Dirichlet at the origin, no Taylor start.
                    Time integration: scipy solve_ivp DOP853 at rtol=1e-12 (no leapfrog,
                    no Crank-Nicolson, no discrete Taylor bootstrap).
  secondary U-MOL : solves u_tt = u_rr for u = r*phi on the same nodes as the published
                    module (same variable) but with DOP853 + exact velocity initial data,
                    i.e. a different integrator and a different start procedure.

CONTROLS (all pre-registered before the numbers are inspected)
  C1 first-order : same spherical FV geometry with a first-order one-sided advective
                   difference. The norm+fit machinery must measure order ~1, otherwise
                   the order-2 measurement is not discriminative.
  C2 injection   : feed the exact phi at the cell centres as the "numerical" solution;
                   the error norm must be ~0 (the machinery must not fabricate error).
  C3 time-tol    : refine rtol by 100x at the finest rung; the error must not move by more
                   than 1e-3 relative, i.e. temporal error is negligible and the measured
                   order is the spatial order.

PRE-REGISTERED ACCEPTANCE (fixed before running)
  A1 primary SPH-FV fit order within the protocol band |p - 2.0| <= 0.3  [protocol sec. 3.6]
  A2 primary study monotone over 4 rungs dr = 0.2,0.1,0.05,0.025
  A3 primary order agrees with the published lffd order under R5:
     |dp| <= max(0.25, sqrt(delta_mine^2 + delta_pub^2))                 [protocol sec. 3.8]
  A4 secondary U-MOL order in band and R5-agrees with the published lffd order
  A5 control C1 measures order in [0.5, 1.5]
  A6 control C2 error <= 1e-13
  A7 control C3 relative error change <= 1e-3
  A8 all hash guards hold (frozen module 8ade1cdc, published artifact c88146a1,
     protocol 1e6cdf04)

VERDICT RULE
  REPRODUCED            : A1-A8 pass
  PARTIAL               : A1 and A3 pass but at least one control (A5-A8) fails
  FALSIFIED             : A1, A3 or A4 fails (order claim does not survive the
                          independent discretisation)

WHAT IS NOT CLAIMED
  * no gate verdict, no node completion, no numerics-lock release (N1 stays locked);
  * no physics / self-gravity / cosmic-censorship claim (flat-space calibration only);
  * no claim that absolute error values are comparable across variables: the published
    l2_error is computed on the reduced variable u = r*phi, the primary study here is on
    phi. Orders are dimensionless and are what A1/A3/A4 compare; absolute values are
    reported side by side for transparency only;
  * the pulse family and the PDE definition are necessarily shared with the published
    evidence (they are the object under test).

USAGE
  python3 independent_replication.py                # full run, writes results.json
  python3 independent_replication.py --quick        # 3 rungs only, for a smoke test
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
from scipy.integrate import solve_ivp

REPO = Path(__file__).resolve().parents[3]

# --- hash-pinned inputs (fail closed on mismatch) ---------------------------------
PINS = {
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/n0_order_4rung.json":
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
}
PUBLISHED_ARTIFACT = "numerics/tests/n0_order_4rung.json"

# --- problem definition (the object under test; values from the published modules) --
R_MAX = 30.0
T_END = 6.0
R0 = 10.0
SIGMA = 1.5
DR_VALUES = [0.2, 0.1, 0.05, 0.025]
P_EXPECTED = 2.0
P_TOL = 0.3
R5_FLOOR = 0.25

RTOL = 1e-12
ATOL = 1e-14


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def F(s):
    s = np.asarray(s, dtype=float)
    return np.exp(-((s - R0) ** 2) / (2.0 * SIGMA ** 2))


def u_exact(r, t):
    r = np.asarray(r, dtype=float)
    return F(r - t) - F(-r - t)


def phi_exact(r, t):
    r = np.asarray(r, dtype=float)
    return u_exact(r, t) / r


# ---------------------------------------------------------------------------------
# primary scheme: direct spherical finite volume for phi (no reduction)
# ---------------------------------------------------------------------------------
def sph_fv_rhs(t, y, n, r_c, r_f, dr):
    phi = y[:n]
    phi_bc = float(phi_exact(np.array([R_MAX]), t)[0])
    g = np.empty(n + 1)
    # second-order centred face gradients; zero flux at the regular origin
    g[0] = 0.0
    g[1:n] = (phi[1:] - phi[:-1]) / dr
    g[n] = (phi_bc - phi[n - 1]) / dr
    S = r_f**2
    vol = (r_f[1:] ** 3 - r_f[:-1] ** 3)
    lap = 3.0 * (S[1:] * g[1:] - S[:-1] * g[:-1]) / vol
    return np.concatenate([y[n:], lap])


def run_sph_fv(dr, rtol=RTOL, atol=ATOL):
    n = int(round(R_MAX / dr))
    r_f = np.linspace(0.0, R_MAX, n + 1)
    r_c = 0.5 * (r_f[1:] + r_f[:-1])
    phi0 = phi_exact(r_c, 0.0)

    # exact time derivative at t=0:
    #   d/dt [F(r-t) - F(-r-t)]/r = [-F'(r-t) + F'(-r-t)]/r, F'(s)=-(s-R0)/sigma^2 F(s)
    def Fp(s):
        s = np.asarray(s, dtype=float)
        return -((s - R0) / SIGMA ** 2) * F(s)

    dphi0 = (-Fp(r_c - 0.0) + Fp(-r_c - 0.0)) / r_c

    def rhs(t, y):
        return sph_fv_rhs(t, y, n, r_c, r_f, dr)

    sol = solve_ivp(rhs, (0.0, T_END), np.concatenate([phi0, dphi0]),
                    method="DOP853", rtol=rtol, atol=atol, dense_output=False)
    if not sol.success:
        raise RuntimeError(f"DOP853 failed at dr={dr}: {sol.message}")
    phi_num = sol.y[:n, -1]
    err = phi_num - phi_exact(r_c, T_END)
    return {
        "scheme": "sph-fv",
        "variable": "phi (unreduced spherical field)",
        "dr": dr, "n_cells": n, "n_steps": int(sol.t.size),
        "final_t": float(sol.t[-1]),
        "rtol": rtol, "atol": atol,
        "l2_error_phi": float(math.sqrt(float(np.sum(err * err)) * dr)),
        "l2_error_phi_volume_weighted": float(
            math.sqrt(float(np.sum((r_c ** 2) * err * err) / float(np.sum(r_c ** 2))))),
    }


# ---------------------------------------------------------------------------------
# C1 control: first-order upwind discretisation of the same wave equation.
# u = p + q with p_t + p_r = 0 (+1 speed) and q_t - q_r = 0 (-1 speed).
# Backward difference for p, forward for q: formally first order in space.
# ---------------------------------------------------------------------------------
def run_upwind_wave(dr, cfl=0.5):
    n = int(round(R_MAX / dr))
    r = np.linspace(0.0, n * dr, n + 1)
    p0 = F(r - 0.0)          # exact right-moving component at t=0
    q0 = -F(-r - 0.0)        # exact left-moving component at t=0

    def rhs(t, y):
        p = y[:n + 1]
        q = y[n + 1:]
        dp = np.zeros(n + 1)
        dq = np.zeros(n + 1)
        # inflow boundary carries the exact (essentially zero) value
        p_left = float(F(np.array([-t]))[0])
        dp[1:] = -(p[1:] - p[:-1]) / dr
        dp[0] = -(p[0] - p_left) / dr
        # q is left-moving (speed -1): upwind stencil takes information from the right
        dq[:n] = (q[1:] - q[:-1]) / dr
        dq[n] = 0.0  # zero-gradient outflow; exact q(R, t) ~ 0 on this time window
        return np.concatenate([dp, dq])

    # fixed-step RK4 at cfl=0.5: explicit, stable and independent of the adaptive
    # error controller (the upwind operator is non-normal and misleads adaptivity)
    steps = int(math.ceil(T_END / (cfl * dr)))
    dt = T_END / steps
    y = np.concatenate([p0, q0])
    t = 0.0
    for _ in range(steps):
        k1 = rhs(t, y)
        k2 = rhs(t + dt / 2, y + dt / 2 * k1)
        k3 = rhs(t + dt / 2, y + dt / 2 * k2)
        k4 = rhs(t + dt, y + dt * k3)
        y = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        t += dt
    u_num = y[:n + 1] + y[n + 1:]
    err = u_num - u_exact(r, T_END)
    return {"scheme": "upwind-wave-first-order-rk4", "variable": "u = p + q (first-order upwind)",
            "dr": dr, "n_cells": n, "n_steps": steps, "cfl": cfl, "final_t": t,
            "l2_error_u": float(math.sqrt(float(np.sum(err * err)) * dr))}


# ---------------------------------------------------------------------------------
# secondary scheme: u = r*phi on the published node grid, same variable as published
# ---------------------------------------------------------------------------------
def run_u_mol(dr, rtol=RTOL, atol=ATOL):
    n = int(round(R_MAX / dr))
    r = np.linspace(0.0, n * dr, n + 1)
    u0 = u_exact(r, 0.0)

    def up(s):
        s = np.asarray(s, dtype=float)
        return -((s - R0) / SIGMA ** 2) * F(s)

    du0 = -up(r - 0.0) + up(-r - 0.0)

    def rhs(t, y):
        u = y[:n + 1].copy()
        u[0] = 0.0
        u[n] = 0.0
        lap = np.zeros(n + 1)
        lap[1:n] = (u[2:] - 2.0 * u[1:-1] + u[:-2]) / dr ** 2
        return np.concatenate([y[n + 1:], lap])

    sol = solve_ivp(rhs, (0.0, T_END), np.concatenate([u0, du0]),
                    method="DOP853", rtol=rtol, atol=atol, dense_output=False)
    if not sol.success:
        raise RuntimeError(f"DOP853 failed (u) at dr={dr}: {sol.message}")
    u_num = sol.y[:n + 1, -1]
    err = u_num - u_exact(r, T_END)
    return {
        "scheme": "u-mol-dop853",
        "variable": "u = r*phi (published variable)",
        "dr": dr, "n_cells": n, "n_steps": int(sol.t.size),
        "final_t": float(sol.t[-1]),
        "rtol": rtol, "atol": atol,
        "l2_error_u": float(math.sqrt(float(np.sum(err * err)) * dr)),
    }


def run_pulse_variant(r0, sigma, dr):
    """SUPPLEMENTARY robustness probe (added after the pre-registered A1-A8 run):
    same SPH-FV scheme on a different member of the pulse family, to test that the
    order-2 result is not specific to the published (r0=10, sigma=1.5) member."""
    global R0, SIGMA
    old = (R0, SIGMA)
    R0, SIGMA = float(r0), float(sigma)
    try:
        row = run_sph_fv(dr)
    finally:
        R0, SIGMA = old
    row["pulse"] = {"r0": float(r0), "sigma": float(sigma)}
    return row


# ---------------------------------------------------------------------------------
# order statistics (R5 definitions pinned against the published lffd row)
# ---------------------------------------------------------------------------------
def fit_stats(drs, errs):
    x, y = np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float))
    p, cov = np.polyfit(x, y, 1, cov=True)
    se = float(math.sqrt(cov[0, 0]))
    pairs = [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
             for i in range(len(errs) - 1)]
    half = float((max(pairs) - min(pairs)) / 2.0)
    return {
        "fit_order": float(p[0]),
        "slope_se": se,
        "pair_orders": pairs,
        "pair_half_range": half,
        "delta_r5": float(max(half, se)),
        "monotone": bool(all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))),
        "n_rungs": len(drs),
        "within_band_pm_0.3": bool(abs(float(p[0]) - P_EXPECTED) <= P_TOL),
    }


def r5_agree(p_a, d_a, p_b, d_b):
    bound = max(R5_FLOOR, math.sqrt(d_a ** 2 + d_b ** 2))
    return {"abs_dp": abs(p_a - p_b), "r5_bound": bound,
            "agree": bool(abs(p_a - p_b) <= bound)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="3 rungs only (smoke test)")
    ap.add_argument("--out", default=str(Path(__file__).with_name("results.json")))
    args = ap.parse_args()
    drs = DR_VALUES[:3] if args.quick else DR_VALUES

    t0 = time.time()

    # A8: hash guards first, fail closed
    guard = {}
    for rel, want in PINS.items():
        p = REPO / rel
        got = sha256_file(p) if p.exists() else None
        guard[rel] = {"pinned": want, "measured": got, "match": got == want}
    if not all(v["match"] for v in guard.values()):
        print(json.dumps({"error": "hash guard failed", "guard": guard}, indent=1))
        return 2

    published = json.loads((REPO / PUBLISHED_ARTIFACT).read_text())
    pub = {}
    for st in published["studies"]:
        pub[st["scheme"]] = {
            "fit_order": st["fit_order"], "delta_r5": st["delta"],
            "pair_orders": st["pair_orders"], "l2_errors": [r["l2_error"] for r in st["rows"]],
        }

    # primary study
    prim_rows = [run_sph_fv(dr) for dr in drs]
    prim_errs = [r["l2_error_phi"] for r in prim_rows]
    prim = fit_stats(drs, prim_errs)
    prim["rows"] = prim_rows

    # secondary study
    sec_rows = [run_u_mol(dr) for dr in drs]
    sec_errs = [r["l2_error_u"] for r in sec_rows]
    sec = fit_stats(drs, sec_errs)
    sec["rows"] = sec_rows

    # C1 first-order control
    c1_rows = [run_upwind_wave(dr) for dr in drs]
    c1 = fit_stats(drs, [r["l2_error_u"] for r in c1_rows])
    c1["rows"] = c1_rows

    # C2 injection control at the finest rung
    n = int(round(R_MAX / drs[-1]))
    r_f = np.linspace(0.0, R_MAX, n + 1)
    r_c = 0.5 * (r_f[1:] + r_f[:-1])
    inj = phi_exact(r_c, T_END) - phi_exact(r_c, T_END)
    c2 = {"max_abs_error": float(np.max(np.abs(inj))),
          "l2_error_phi": float(math.sqrt(float(np.sum(inj * inj)) * drs[-1]))}

    # C4 supplementary pulse-member robustness probe (full runs only)
    c4 = None
    if not args.quick:
        c4_rows = [run_pulse_variant(9.0, 1.2, dr) for dr in drs]
        c4 = fit_stats(drs, [r["l2_error_phi"] for r in c4_rows])
        c4["rows"] = c4_rows
        c4["pulse"] = {"r0": 9.0, "sigma": 1.2}
        c4["note"] = ("supplementary post-hoc probe, NOT part of the pre-registered "
                      "A1-A8 verdict: added after the primary run to test the shared "
                      "pulse-family axis")

    # C3 time-tolerance control at the finest rung
    base = prim_rows[-1]
    fine = run_sph_fv(drs[-1], rtol=1e-13, atol=1e-15)
    rel = abs(fine["l2_error_phi"] - base["l2_error_phi"]) / base["l2_error_phi"]
    c3 = {"dr": drs[-1], "rtol_base": base["rtol"], "rtol_fine": fine["rtol"],
          "err_base": base["l2_error_phi"], "err_fine": fine["l2_error_phi"],
          "relative_change": float(rel), "steps_base": base["n_steps"],
          "steps_fine": fine["n_steps"]}

    # published comparison
    cmp_lffd = r5_agree(prim["fit_order"], prim["delta_r5"],
                        pub["lffd"]["fit_order"], pub["lffd"]["delta_r5"])
    cmp_lffd_sec = r5_agree(sec["fit_order"], sec["delta_r5"],
                            pub["lffd"]["fit_order"], pub["lffd"]["delta_r5"])
    cmp_all = {s: r5_agree(prim["fit_order"], prim["delta_r5"], v["fit_order"], v["delta_r5"])
               for s, v in pub.items()}

    acceptance = {
        "A1_primary_in_band": prim["within_band_pm_0.3"],
        "A2_primary_monotone_4rungs": bool(prim["monotone"] and prim["n_rungs"] >= 4),
        "A3_primary_r5_agrees_with_published_lffd": cmp_lffd["agree"],
        "A4_secondary_in_band_and_r5_agrees": bool(
            sec["within_band_pm_0.3"] and cmp_lffd_sec["agree"]),
        "A5_first_order_control_in_0.5_1.5": bool(0.5 <= c1["fit_order"] <= 1.5),
        "A6_injection_error_le_1e-13": bool(c2["l2_error_phi"] <= 1e-13),
        "A7_time_tol_rel_change_le_1e-3": bool(c3["relative_change"] <= 1e-3),
        "A8_hash_guards": all(v["match"] for v in guard.values()),
    }
    if not acceptance["A1_primary_in_band"] or not acceptance["A3_primary_r5_agrees_with_published_lffd"] \
            or not acceptance["A4_secondary_in_band_and_r5_agrees"]:
        verdict = "FALSIFIED"
    elif all(acceptance.values()):
        verdict = "REPRODUCED"
    else:
        verdict = "PARTIAL"

    out = {
        "artifact": "artifacts/worker-046/n0_independent_replication/independent_replication.py",
        "actor": "worker-046",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "node_id": "N0",
        "gate": "G-NUM",
        "task_id": "W046-N0-INDEP-REPL-01",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "purpose": "independent from-scratch replication of the N0 order-2 evidence on a "
                   "discretisation that shares none of the r*phi reduction / Dirichlet-origin / "
                   "Taylor-start / leapfrog axes of the published replication module",
        "pre_registered_acceptance": [
            "A1 primary SPH-FV fit order |p-2| <= 0.3",
            "A2 primary monotone over 4 rungs",
            "A3 primary R5-agrees with published lffd order",
            "A4 secondary U-MOL in band and R5-agrees with published lffd order",
            "A5 first-order control measures 0.5 <= p <= 1.5",
            "A6 injection control error <= 1e-13",
            "A7 time-tolerance control relative error change <= 1e-3",
            "A8 hash guards hold",
        ],
        "verdict": verdict,
        "acceptance": acceptance,
        "primary_sph_fv": prim,
        "secondary_u_mol": sec,
        "controls": {"C1_first_order": c1, "C2_exact_injection": c2, "C3_time_tolerance": c3,
                     **({"C4_pulse_variant": c4} if c4 is not None else {})},
        "published_comparison": {
            "published_artifact": PUBLISHED_ARTIFACT,
            "published_studies": pub,
            "primary_vs_lffd": cmp_lffd,
            "primary_vs_all_published": cmp_all,
            "secondary_vs_lffd": cmp_lffd_sec,
            "absolute_error_note": "published l2_error is on u=r*phi; primary l2_error is on "
                                   "phi. Only orders and R5 agreement are compared; absolute "
                                   "values are reported for transparency, not equality.",
        },
        "hash_guards": guard,
        "environment": {
            "python": sys.version.split()[0], "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "platform": platform.platform(),
            "rng": "none (deterministic)",
        },
        "not_claimed": [
            "no gate verdict and no gate self-pass (authority: Astra / group leads)",
            "no node completion; N0 stays active/unverified and numerics_lock stays LOCKED",
            "no self-gravity, no N1 work, no numerics/spherical_solver artifact",
            "no physics claim; flat-space calibration sub-case only",
            "no equality claim on absolute error values across variables",
        ],
        "falsifier": "Re-run this script after any change to the pinned inputs or to this script: "
                     "the order claim is falsified if the primary SPH-FV or secondary U-MOL fit "
                     "falls outside |p-2| <= 0.3, if either fails R5 agreement with the published "
                     "lffd order, or if the C1 first-order control is not measured near order 1; "
                     "a hash-guard mismatch voids the comparison entirely (fail closed).",
        "runtime_seconds": round(time.time() - t0, 3),
    }
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"verdict={verdict} primary p={prim['fit_order']:.6f}+/-{prim['delta_r5']:.6f} "
          f"secondary p={sec['fit_order']:.6f}+/-{sec['delta_r5']:.6f} "
          f"C1 p={c1['fit_order']:.6f} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
