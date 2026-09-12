#!/usr/bin/env python3
"""W051-N0-SCHEME-AXES-02 -- spatial/temporal operator-axis multiplicity of the
published N0 replication schemes, plus completion of the 2x2 design.

Node N0, class AF-WCC-SCALAR-SPH (flat-space test-field calibration sub-case).
No self-gravity, no coupling to geometry, no N1 code.  Reads the frozen
published module numerics/tests/flat_wave_replication.py at its pinned sha256;
writes only its own report/stdout under artifacts/worker-051/.

What is measured (all reproducible from the pinned module):

1. Operator extraction and code-path verification for the three published
   replication schemes:
       lffd  = explicit leapfrog        + 3-point FD             (FD, LF)
       cnfd  = implicit Crank-Nicolson  + 3-point FD             (FD, CN)
       cnfem = implicit Crank-Nicolson  + P1 consistent-mass FEM (FEM, CN)
   The published solvers satisfy exact one-step identities that pin their
   semi-discrete spatial operators:
       LF    : d2 = A cur
       CN-FD : d2 = A (psi_new + psi_old)/2,   d2 = (psi_new - 2 psi + psi_old)/dt^2
       CN-FEM: M d2 = -K (psi_new + psi_old)/2
   The CN-FD operator attribute is compared to the FD matrix built from the
   same tridiagonal coefficients, entry by entry.

2. Distinctness of the FEM and FD spatial operators.  Two consistent
   discretisations do NOT converge to each other in matrix norm (the norm is
   dominated by grid-scale modes), so distinctness is measured where it is
   well defined:
     * grid-scale (Nyquist) response on interior rows -- exact constants;
     * low-mode (smooth) response, whose relative difference must shrink at
       order 2 if both operators are second-order consistent.
   The full-matrix Frobenius difference is reported too, labelled as
   boundary/grid-scale dominated, not as a convergence metric.

3. Completion of the 2x2 design {FD, FEM} x {leapfrog, CN}: the missing cell
   (FEM + leapfrog) is implemented here and all four cells are run through the
   published order study at 4 rungs (dr = 0.2/0.1/0.05/0.025).  The three
   published cells are also checked against the published 4-rung artifact.

4. Isolated spatial order per cell via dt -> 0 extrapolation at each dr
   (three cfl values, linear fit in dt^2), so the mixed-order numbers are not
   read as spatial evidence.

5. Determinism control (bitwise rerun).

Exit code 0 if the run completed; the verdict is data, not an exit status.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PUB_PATH = ROOT / "numerics" / "tests" / "flat_wave_replication.py"
PUB_PIN = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
FOUR_RUNG_PATH = ROOT / "numerics" / "tests" / "n0_order_4rung.json"
PROTOCOL_PATH = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
CST = timezone(timedelta(hours=8))

RUNGS = [0.2, 0.1, 0.05, 0.025]
CFLS = [0.5, 0.25, 0.125]
R_MAX = 30.0
T_END = 6.0
P_EXPECTED = 2.0
P_TOL = 0.3
PULSE = {"r0": 10.0, "sigma": 1.5}


def now() -> str:
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_published():
    sha = sha256_file(PUB_PATH)
    spec = importlib.util.spec_from_file_location("n0_replication_pinned", PUB_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # safe: module guards main under __main__
    return mod, sha


# ---------------------------------------------------------------------------
# the missing cell of the published 2x2 design
# ---------------------------------------------------------------------------
def make_fem_leapfrog(pub):
    class FEMLeapfrog(pub._BaseSolver):
        """Leapfrog + P1 consistent-mass FEM: M a = -K psi, explicit in time.

        Same discrete spatial operator as the published CrankNicolsonFEM; only
        the time integrator differs.  Stability at cfl=0.5: omega_max*dt =
        sqrt(12)/h * 0.5h = 1.732 < 2.
        """

        def __init__(self, r, dt, psi0, psi_t0, psi_tt0):
            super().__init__(r, dt, psi0, psi_t0, psi_tt0)
            m = len(self.r) - 2
            h = self.dr
            self.M = pub.Tridiagonal(h / 6.0, 2.0 * h / 3.0, h / 6.0, m)
            self.K = pub.Tridiagonal(-1.0 / h, 2.0 / h, -1.0 / h, m)
            acc0 = -self.M.solve(self.K.matvec(self.psi[1:-1]))
            p1 = self.psi.copy()
            p1[1:-1] = (
                self.psi[1:-1] + self.dt * psi_t0[1:-1] + 0.5 * self.dt ** 2 * acc0
            )
            p1[0] = p1[-1] = 0.0
            self._psi1 = p1

        def step(self):
            if not self._started:
                self.psi_prev, self.psi, self._started = self.psi, self._psi1, True
                self.t += self.dt
                return
            cur, prev = self.psi, self.psi_prev
            acc = -self.M.solve(self.K.matvec(cur[1:-1]))
            nxt = np.empty_like(cur)
            nxt[1:-1] = 2.0 * cur[1:-1] - prev[1:-1] + self.dt ** 2 * acc
            nxt[0] = nxt[-1] = 0.0
            if not np.all(np.isfinite(nxt)):
                raise FloatingPointError("non-finite state in FEMLeapfrog")
            self.psi_prev, self.psi = cur, nxt
            self.t += self.dt

        def own_energy(self):
            if self.psi_prev is None:
                return None
            V = (self.psi[1:-1] - self.psi_prev[1:-1]) / self.dt
            return (
                0.5 * pub.inner(V, self.M.matvec(V), self.dr)
                + 0.25 * pub.inner(self.psi[1:-1], self.K.matvec(self.psi[1:-1]), self.dr)
                + 0.25
                * pub.inner(self.psi_prev[1:-1], self.K.matvec(self.psi_prev[1:-1]), self.dr)
            )

    return FEMLeapfrog


# ---------------------------------------------------------------------------
# operator extraction
# ---------------------------------------------------------------------------
def dense_from_tridiag(T, m: int) -> np.ndarray:
    """Dense matrix by applying the published matvec to each basis vector."""
    eye = np.eye(m)
    cols = [T.matvec(eye[:, j]) for j in range(m)]
    return np.column_stack(cols)


def fd_operator(pub, m: int, h: float) -> np.ndarray:
    return dense_from_tridiag(pub.Tridiagonal(1.0 / h ** 2, -2.0 / h ** 2, 1.0 / h ** 2, m), m)


def fem_matrices(pub, m: int, h: float):
    M = dense_from_tridiag(pub.Tridiagonal(h / 6.0, 2.0 * h / 3.0, h / 6.0, m), m)
    K = dense_from_tridiag(pub.Tridiagonal(-1.0 / h, 2.0 / h, -1.0 / h, m), m)
    return M, K


def one_step(solver, cur: np.ndarray, prev: np.ndarray):
    """Drive the published solver through exactly one non-starter step."""
    solver.psi = cur.copy()
    solver.psi_prev = prev.copy()
    solver._started = True
    solver.step()
    nxt = solver.psi.copy()
    d2 = (nxt[1:-1] - 2.0 * cur[1:-1] + prev[1:-1]) / solver.dt ** 2
    return nxt, d2


def rel_fro(X: np.ndarray, Y: np.ndarray) -> float:
    return float(np.linalg.norm(X - Y, "fro") / np.linalg.norm(Y, "fro"))


def operator_block(pub, rng) -> dict:
    """Extract and cross-verify the three published spatial operators."""
    h = 0.05
    m = int(round(R_MAX / h)) - 1
    A = fd_operator(pub, m, h)
    M, K = fem_matrices(pub, m, h)
    L_fem = np.linalg.solve(M, -K)
    r = pub.grid(R_MAX, h)

    cur = np.zeros(m + 2)
    prev = np.zeros(m + 2)
    cur[1:-1] = rng.standard_normal(m)
    prev[1:-1] = rng.standard_normal(m)

    pulse = pub.PulseExact(**PULSE)
    psi0, pt0, ptt0 = pulse.initial_data(r)
    dt = 0.5 * h

    # --- exact one-step identities: each pins the semi-discrete operator ---
    lf = pub.LeapfrogFD(r, dt, psi0, pt0, ptt0)
    _, d2_lf = one_step(lf, cur, prev)
    res_lf = float(np.max(np.abs(d2_lf - A @ cur[1:-1])) / np.max(np.abs(d2_lf)))

    cn = pub.CrankNicolsonFD(r, dt, psi0, pt0, ptt0)
    nxt_cn, d2_cn = one_step(cn, cur, prev)
    mid_cn = 0.5 * (nxt_cn[1:-1] + prev[1:-1])
    res_cn = float(np.max(np.abs(d2_cn - A @ mid_cn)) / np.max(np.abs(d2_cn)))
    A_cn_attr = dense_from_tridiag(cn.A, m)
    res_cn_attr = float(np.max(np.abs(A_cn_attr - A)))

    fem = pub.CrankNicolsonFEM(r, dt, psi0, pt0, ptt0)
    nxt_fem, d2_fem = one_step(fem, cur, prev)
    mid_fem = 0.5 * (nxt_fem[1:-1] + prev[1:-1])
    res_fem = float(np.max(np.abs(M @ d2_fem + K @ mid_fem)) / np.max(np.abs(M @ d2_fem)))
    res_fem_attr = float(np.max(np.abs(dense_from_tridiag(fem.M, m) - M))
                         + np.max(np.abs(dense_from_tridiag(fem.K, m) - K)))

    # --- start-step semantics ---------------------------------------------
    # The published LeapfrogFD starter uses the ANALYTIC psi_tt0; the two CN
    # starters use their own DISCRETE acceleration.  Both are checked as stated.
    s_lf = pub.LeapfrogFD(r, dt, psi0, pt0, ptt0)
    s_lf.step()
    pred_taylor = psi0[1:-1] + dt * pt0[1:-1] + 0.5 * dt ** 2 * ptt0[1:-1]
    lffd_taylor_res = float(np.max(np.abs(s_lf.psi[1:-1] - pred_taylor))
                            / np.max(np.abs(s_lf.psi[1:-1])))
    lffd_own_accel_gap = float(
        np.max(np.abs(0.5 * dt ** 2 * (ptt0[1:-1] - A @ psi0[1:-1])))
        / np.max(np.abs(s_lf.psi[1:-1])))

    femlf_cls = make_fem_leapfrog(pub)
    starts = {}
    for name, s, acc in (
        ("cnfd", pub.CrankNicolsonFD(r, dt, psi0, pt0, ptt0), lambda: A @ psi0[1:-1]),
        ("cnfem", pub.CrankNicolsonFEM(r, dt, psi0, pt0, ptt0),
         lambda: -np.linalg.solve(M, K @ psi0[1:-1])),
        ("femlf", femlf_cls(r, dt, psi0, pt0, ptt0),
         lambda: -np.linalg.solve(M, K @ psi0[1:-1])),
    ):
        s.step()
        pred = psi0[1:-1] + dt * pt0[1:-1] + 0.5 * dt ** 2 * acc()
        starts[name] = float(np.max(np.abs(s.psi[1:-1] - pred)) / np.max(np.abs(s.psi[1:-1])))

    # --- exactness control on u = r(R-r), u'' = -2, zero Dirichlet data ----
    # The FD stencil is exact on every row because u(0) = u(R) = 0.  The FEM
    # mass matrix has truncated first/last rows (no boundary DOF), so its
    # exactness identity M(-2*1) = -K u holds on interior rows only; the
    # boundary-row residual is reported separately, not used as a control.
    uq = r[1:-1] * (R_MAX - r[1:-1])
    ones = np.ones(m)
    fd_all = A @ uq + 2.0
    fem_all = M @ (-2.0 * ones) + K @ uq
    exact_fd = float(np.max(np.abs(fd_all)))
    exact_fem = float(np.max(np.abs(fem_all[1:-1])))
    boundary_res = {"fd_first_last_row_max": float(max(abs(fd_all[0]), abs(fd_all[-1]))),
                    "fem_first_last_row_max": float(max(abs(fem_all[0]), abs(fem_all[-1])))}

    # --- distinctness vs dr ------------------------------------------------
    # Two consistent discretisations do not converge to each other in matrix
    # norm (grid-scale modes dominate), so measure (i) the exact Nyquist
    # response on interior rows and (ii) the smooth-mode relative difference,
    # which is the physically meaningful second-order-consistency comparison.
    dr_rows = []
    for dr in RUNGS:
        hh = dr
        mm = int(round(R_MAX / hh)) - 1
        rr = pub.grid(R_MAX, hh)
        A_h = fd_operator(pub, mm, hh)
        M_h, K_h = fem_matrices(pub, mm, hh)
        L_h = np.linalg.solve(M_h, -K_h)
        D = L_h - A_h
        # smooth low mode, vanishing at both walls
        u = np.sin(np.pi * rr[1:-1] / R_MAX)
        rel_sup_smooth1 = float(np.max(np.abs(D @ u)) / np.max(np.abs(A_h @ u)))
        Au = A_h @ u
        ray = []
        for j in (1, 2, 3, 5, 8):
            v = np.sin(np.pi * j * rr[1:-1] / R_MAX)
            lam_exact = (j * np.pi / R_MAX) ** 2
            lam_fd = float(v @ (A_h @ v) / (v @ v)) * -1.0
            lam_fem = float(v @ (K_h @ v) / (v @ (M_h @ v)))
            ray.append({
                "mode": j,
                "lambda_exact": lam_exact,
                "lambda_fd": lam_fd,
                "lambda_fem": lam_fem,
                "rel_err_fd": (lam_fd - lam_exact) / lam_exact,
                "rel_err_fem": (lam_fem - lam_exact) / lam_exact,
                "rel_diff_fd_fem": abs(lam_fd - lam_fem) / lam_exact,
            })
        # exact Nyquist response, measured at the central interior row (the
        # implied eigenvalue is exact there; the dense FEM inverse only
        # contaminates rows within ~exp(-c*distance) of the truncated boundary)
        vny = (-1.0) ** np.arange(1, mm + 1)
        i0 = mm // 2
        lam_fd_nyq = -(A_h @ vny)[i0] / vny[i0]
        lam_fem_nyq = -(L_h @ vny)[i0] / vny[i0]
        nyq_dev_fd = abs(lam_fd_nyq - 4.0 / hh ** 2) / (4.0 / hh ** 2)
        nyq_dev_fem = abs(lam_fem_nyq - 12.0 / hh ** 2) / (12.0 / hh ** 2)
        dr_rows.append({
            "dr": dr,
            "m_interior": mm,
            "rel_sup_smooth_mode1": rel_sup_smooth1,
            "rel_diff_rayleigh_mode1": ray[0]["rel_diff_fd_fem"],
            "lambda_fd_nyquist_center": lam_fd_nyq,
            "lambda_fem_nyquist_center": lam_fem_nyq,
            "nyquist_ratio_fem_over_fd": lam_fem_nyq / lam_fd_nyq,
            "nyquist_center_dev_fd": nyq_dev_fd,
            "nyquist_center_dev_fem": nyq_dev_fem,
            "full_matrix_rel_fro": rel_fro(L_h, A_h),
            "boundary_row_rel_diff": float(np.max(np.abs(D[0, :])) / np.max(np.abs(A_h[0, :]))),
            "rayleigh": ray,
        })
    smooth = [row["rel_sup_smooth_mode1"] for row in dr_rows]
    rayleigh = [row["rel_diff_rayleigh_mode1"] for row in dr_rows]
    order_smooth = float(np.polyfit(np.log(RUNGS), np.log(smooth), 1)[0])
    order_rayleigh = float(np.polyfit(np.log(RUNGS), np.log(rayleigh), 1)[0])
    nyq_ratios = [row["nyquist_ratio_fem_over_fd"] for row in dr_rows]
    return {
        "grid": {"r_max": R_MAX, "dr": h, "m_interior": m},
        "one_step_identity_residuals": {
            "lffd_d2_minus_A_cur": res_lf,
            "cnfd_d2_minus_A_mid": res_cn,
            "cnfd_A_attribute_minus_FD": res_cn_attr,
            "cnfem_M_d2_plus_K_mid": res_fem,
            "cnfem_MK_attribute_minus_rebuild": res_fem_attr,
        },
        "lffd_and_cnfd_share_the_FD_operator": bool(
            res_lf < 1e-12 and res_cn < 1e-12 and res_cn_attr == 0.0),
        "start_step": {
            "lffd_analytic_taylor_residual": lffd_taylor_res,
            "lffd_taylor_minus_discrete_accel_rel": lffd_own_accel_gap,
            "discrete_accel_starters": starts,
            "note": ("lffd's published starter is analytic Taylor (psi_tt0), so its offset "
                     "from the discrete-acceleration starter is the h^2 truncation of A psi0, "
                     "measured above; cnfd/cnfem/femlf use the discrete acceleration."),
        },
        "exactness_control_vanishing_quadratic": {
            "fd_on_u_all_rows_max_dev": exact_fd,
            "fem_row_identity_interior_max_dev": exact_fem,
            "boundary_row_residuals": boundary_res,
            "note": ("u = r(R-r), u'' = -2, zero Dirichlet data; FD stencil exact on all rows, "
                     "FEM identity M(-2*1) = -K u exact on interior rows; truncated FEM "
                     "boundary rows are reported but excluded from the control"),
        },
        "fem_vs_fd": {
            "order_smooth_mode1": order_smooth,
            "order_rayleigh_mode1": order_rayleigh,
            "nyquist_ratio_min": min(nyq_ratios),
            "nyquist_ratio_max": max(nyq_ratios),
            "nyquist_ratio_expected": 3.0,
            "rows": dr_rows,
            "full_matrix_note": ("full-matrix Frobenius relative difference stays O(1) "
                                 "(boundary/grid-scale dominated) and is NOT a convergence "
                                 "metric; it is reported for completeness only"),
        },
    }


# ---------------------------------------------------------------------------
# order studies
# ---------------------------------------------------------------------------
def isolated_spatial_orders(pub, scheme: str) -> dict:
    pulse = pub.PulseExact(**PULSE)
    e0s, rows = [], []
    for dr in RUNGS:
        errs = []
        for cfl in CFLS:
            case = pub.run_case(pub.make_factory(scheme, pulse=pulse), dr, cfl, R_MAX, T_END,
                                sample_every=64)
            err = pub.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
            errs.append({"cfl": cfl, "dt": case["dt"], "steps": case["steps"], "l2_error": err})
        dt2 = np.array([e["dt"] ** 2 for e in errs])
        ee = np.array([e["l2_error"] for e in errs])
        slope, intercept = np.polyfit(dt2, ee, 1)
        pred = slope * dt2 + intercept
        rows.append({"dr": dr, "runs": errs, "temporal_slope": float(slope),
                     "e0_dt0": float(intercept),
                     "temporal_fit_max_rel_resid": float(np.max(np.abs(pred - ee) / ee))})
        e0s.append(float(intercept))
    p = float(pub.fit_order(RUNGS, e0s))
    return {"scheme": scheme, "rungs": rows, "e0_by_dr": e0s,
            "spatial_order_dt0": p,
            "pair_orders_dt0": pub.pair_orders(RUNGS, e0s),
            "monotone": all(e0s[i + 1] < e0s[i] for i in range(len(e0s) - 1)),
            "within_band": bool(abs(p - P_EXPECTED) <= P_TOL)}


def published_4rung_orders() -> dict:
    if not FOUR_RUNG_PATH.exists():
        return {"present": False}
    d = json.loads(FOUR_RUNG_PATH.read_text())
    orders = d.get("verdict", {}).get("orders", {})
    return {"present": True, "path": str(FOUR_RUNG_PATH.relative_to(ROOT)),
            "sha256": sha256_file(FOUR_RUNG_PATH),
            "orders": {k: float(v) for k, v in orders.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "report.json"))
    args = ap.parse_args()

    pub, pub_sha = load_published()
    rng = np.random.default_rng(5102)
    t0 = datetime.now(CST)

    design_axes = {
        "published_schemes": {
            "lffd": {"spatial": "3-point FD", "time": "explicit leapfrog"},
            "cnfd": {"spatial": "3-point FD", "time": "implicit Crank-Nicolson"},
            "cnfem": {"spatial": "P1 consistent-mass FEM", "time": "implicit Crank-Nicolson"},
        },
        "added_cell": {"femlf": {"spatial": "P1 consistent-mass FEM",
                                 "time": "explicit leapfrog"}},
    }

    report: dict = {
        "task_id": "W051-N0-SCHEME-AXES-02",
        "worker": "worker-051",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_binding": ("flat-space test-field calibration sub-case only; fixed Minkowski, "
                          "massless scalar, no coupling to geometry; not an instance of the "
                          "Einstein-coupled class"),
        "conclusion_type": "numerical_evidence",
        "created_at": now(),
        "published_module": {
            "path": "numerics/tests/flat_wave_replication.py",
            "sha256": pub_sha,
            "expected_pin": PUB_PIN,
            "pin_matches": pub_sha == PUB_PIN,
        },
        "protocol": {"path": "numerics/CONVERGENCE_PROTOCOL.md",
                     "sha256": sha256_file(PROTOCOL_PATH)},
        "config": {"rungs": RUNGS, "cfls_isolated": CFLS, "r_max": R_MAX, "t_end": T_END,
                   "pulse": PULSE, "p_expected": P_EXPECTED, "p_tol": P_TOL},
        "design_axes": design_axes,
    }

    print(f"[{now()}] operator extraction ...", flush=True)
    report["operator_block"] = operator_block(pub, rng)

    print(f"[{now()}] 4-rung mixed-order study (4 cells) ...", flush=True)
    femlf = make_fem_leapfrog(pub)
    pub.SCHEMES["femlf"] = (femlf, "added cell: leapfrog + P1 consistent-mass FEM")
    cells = {}
    for scheme in ("lffd", "cnfd", "cnfem", "femlf"):
        st = pub.order_study(scheme, dr_values=RUNGS, cfl=0.5, r_max=R_MAX, t_end=T_END)
        label = design_axes["published_schemes"].get(scheme) or design_axes["added_cell"][scheme]
        cells[scheme] = {
            "spatial": label["spatial"],
            "time": label["time"],
            "fit_order_4rung": st["fit_order"],
            "pair_orders": st["pair_orders"],
            "rows": st["rows"],
            "monotone": st["monotone"],
            "within_band": bool(abs(st["fit_order"] - P_EXPECTED) <= P_TOL),
        }
        print(f"    {scheme:6s} p={st['fit_order']:.6f} monotone={st['monotone']} "
              f"in_band={cells[scheme]['within_band']}", flush=True)
    report["mixed_order_4rung"] = cells

    print(f"[{now()}] isolated spatial order by dt->0 extrapolation ...", flush=True)
    iso = {}
    for scheme in ("lffd", "cnfd", "cnfem", "femlf"):
        iso[scheme] = isolated_spatial_orders(pub, scheme)
        print(f"    {scheme:6s} p_spatial={iso[scheme]['spatial_order_dt0']:.6f} "
              f"monotone={iso[scheme]['monotone']} in_band={iso[scheme]['within_band']}",
              flush=True)
    report["isolated_spatial_order"] = iso

    print(f"[{now()}] determinism control ...", flush=True)
    pulse = pub.PulseExact(**PULSE)
    c1 = pub.run_case(pub.make_factory("femlf", pulse=pulse), 0.05, 0.5, R_MAX, T_END,
                      sample_every=64)
    c2 = pub.run_case(pub.make_factory("femlf", pulse=pulse), 0.05, 0.5, R_MAX, T_END,
                      sample_every=64)
    report["determinism"] = {
        "case": "femlf dr=0.05 cfl=0.5",
        "final_psi_bitwise_equal": bool(np.array_equal(c1["psi"][-1], c2["psi"][-1])),
        "final_t_equal": bool(c1["t"][-1] == c2["t"][-1]),
        "steps_equal": bool(c1["steps"] == c2["steps"]),
    }

    pub4 = published_4rung_orders()
    report["published_4rung_reference"] = pub4
    repro = {}
    if pub4.get("present") and pub4.get("orders"):
        for scheme, p_pub in pub4["orders"].items():
            if scheme in cells:
                p_meas = cells[scheme]["fit_order_4rung"]
                repro[scheme] = {"published": p_pub, "measured": p_meas,
                                 "abs_delta": abs(p_meas - p_pub)}
    report["published_reproduction"] = {
        "compared": repro,
        "max_abs_delta": max((v["abs_delta"] for v in repro.values()), default=None),
        "all_within_1e-9": bool(repro) and all(v["abs_delta"] < 1e-9 for v in repro.values()),
    }

    # ---------------- verdict / falsifier ------------------------------
    ob = report["operator_block"]
    fv = ob["fem_vs_fd"]
    checks = {
        "F1_lffd_cnfd_same_spatial_operator": bool(
            ob["lffd_and_cnfd_share_the_FD_operator"]
            and max(ob["one_step_identity_residuals"].values()) < 1e-10),
        "F2_fem_fd_distinct_and_both_second_order": bool(
            min(fv["nyquist_ratio_min"], fv["nyquist_ratio_max"]) > 2.9
            and max(fv["nyquist_ratio_min"], fv["nyquist_ratio_max"]) < 3.1
            and fv["order_smooth_mode1"] >= 1.5
            and fv["order_rayleigh_mode1"] >= 1.5),
        "F3_operator_extraction_verified": bool(
            max(ob["start_step"]["discrete_accel_starters"].values()) < 1e-10
            and ob["start_step"]["lffd_analytic_taylor_residual"] < 1e-10
            and ob["exactness_control_vanishing_quadratic"]["fd_on_u_all_rows_max_dev"] < 1e-9
            and ob["exactness_control_vanishing_quadratic"]["fem_row_identity_interior_max_dev"]
            < 1e-9),
        "F4_all_four_cells_mixed_order_in_band": bool(
            all(c["within_band"] and c["monotone"] for c in cells.values())),
        "F5_all_four_cells_isolated_spatial_order_in_band": bool(
            all(v["within_band"] and v["monotone"] for v in iso.values())),
        "F6_published_three_cells_reproduced": bool(report["published_reproduction"]["all_within_1e-9"]),
    }
    triggered = sorted(k for k, v in checks.items() if not v)
    report["falsifier"] = {
        "statement": (
            "The multiplicity finding is FALSIFIED if (a) lffd and cnfd do not use the identical "
            "spatial operator, or (b) the FEM and FD operators are not distinct at grid scale "
            "(Nyquist response ratio 1) or are not both second-order consistent at low modes, or "
            "(c) the extracted operators fail their published code-path/start-step/exactness "
            "checks, or (d) any of the four design cells leaves the |p-2|<=0.3 band or loses "
            "monotonicity, either in mixed order or in dt->0 isolated spatial order, or (e) the "
            "three published cells are not reproduced by this harness at <1e-9."
        ),
        "checks": checks,
        "triggered": triggered,
        "overall": "falsifier_triggered" if triggered else "falsifier_not_triggered",
    }

    pub_spatial = {v["spatial"] for v in design_axes["published_schemes"].values()}
    pub_time = {v["time"] for v in design_axes["published_schemes"].values()}
    all_spatial = {c["spatial"] for c in cells.values()}
    all_time = {c["time"] for c in cells.values()}
    report["verdict"] = {
        "published_schemes_measured": 3,
        "distinct_spatial_discretisations_across_published_3": len(pub_spatial),
        "distinct_time_integrators_across_published_3": len(pub_time),
        "cells_after_completion": 4,
        "distinct_spatial_discretisations_after_completion": len(all_spatial),
        "distinct_time_integrators_after_completion": len(all_time),
        "published_spatial_independence_multiplicity": len(pub_spatial),
        "published_claim_spatial_independence_supported_at_multiplicity_3": False,
        "femlf_cell_filled": "femlf" in cells,
        "overall": report["falsifier"]["overall"],
        "read_this_as": ("numerical evidence about discretisation axes of the flat-space "
                         "calibration only; no gate verdict, no node completion, no class claim"),
    }
    report["scope_limits"] = [
        "flat-space test field on a fixed Minkowski background; no gravity coupling, no N1",
        "operator comparison is on the published uniform node-centred grid only",
        "class AF-WCC-SCALAR-SPH calibration sub-case; cannot be cited as an instance of the class",
        "order claims are for the published harness configuration (pulse r0=10 sigma=1.5, "
        "r in [0,30], t_end=6) at 4 rungs; no claim about other data families",
        "the added FEM+leapfrog cell is new code in this artifact, not a published scheme",
    ]
    report["non_claims"] = ["no node status change", "no validation_status=passed",
                            "no gate verdict", "no theorem or class-level claim",
                            "no edit to any canonical or published numerics file"]
    report["runtime_seconds"] = (datetime.now(CST) - t0).total_seconds()

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"[{now()}] wrote {out}")
    print(json.dumps({"verdict": report["verdict"], "falsifier": report["falsifier"]["triggered"],
                      "cells": {k: round(v["fit_order_4rung"], 6) for k, v in cells.items()},
                      "isolated": {k: round(v["spatial_order_dt0"], 6) for k, v in iso.items()},
                      "nyquist_ratio": [fv["nyquist_ratio_min"], fv["nyquist_ratio_max"]],
                      "smooth_order": fv["order_smooth_mode1"],
                      "rayleigh_order": fv["order_rayleigh_mode1"]},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
