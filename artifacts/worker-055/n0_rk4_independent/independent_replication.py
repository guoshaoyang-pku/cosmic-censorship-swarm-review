#!/usr/bin/env python3
"""W055-N0-RK4-INDEP-01 — independent-method replication of the N0 flat-space order claim.

Task taken by worker-055 under open map node N0 (no assignment existed in
comms/inbox/worker-055.jsonl). Class AF-WCC-SCALAR-SPH, gate G-NUM, group numerics.
Self-contained: imports nothing from numerics/ at solve time, so a bug in the
frozen harness cannot be inherited silently.

WHAT IS REPLICATED
  The N0 claim of record (numerics/tests/n0_order_4rung.json#c88146a1) is:
  "order 2 measured at four rungs for three schemes; all within p = 2.0 +/- 0.3",
  with R5 pairwise agreement, for the outgoing Gaussian pulse r0=10, sigma=1.5,
  r in [0,30], t_end=6, dr in {0.2,0.1,0.05,0.025}, dt = 0.5*dr.

  The frozen replication (numerics/tests/flat_wave_replication.py#8ade1cdc) itself
  lists its KNOWN SHARED AXES with the reference: the psi = r*phi reduction, the
  psi(0)=psi(R)=0 Dirichlet condition, the Taylor start, and the Gaussian family.
  This file is an independent replication along the axes that were NOT covered:

    * dependent variable   : phi is evolved directly, psi = r*phi is never formed
                             inside the solver (used only in the comparison metric);
    * origin regularity    : l'Hopital limit phi_tt(0) = 3*phi_rr(0) with an even
                             ghost point (psi's Dirichlet condition is not used);
    * time integration     : classical RK4 method-of-lines (no Taylor start, no
                             three-level leapfrog/Crank-Nicolson);
    * spatial operator     : centred 2nd-order difference of d2/dr2 + (2/r) d/dr,
                             a different stencil from the psi-family Laplacian;
    * error norm plumbing  : independent implementation of the same l2 rule.

  Shared (unavoidable, same physical problem): the PDE psi_tt = psi_rr, the
  Gaussian-pulse family, the outer Dirichlet truncation at r=30, and the
  comparison metric formula. Those are the claim's own definition, not a
  replication shortcut.

CONTROLS (both run by this file)
  lffd_reimpl : third independent implementation of the psi leapfrog family,
                written here from scratch. It shares the reference axes on purpose
                and is a WIRING CONTROL: if it does not reproduce the recorded
                lffd order 1.996624864320 within R5, this file's grid/dt/t_end/norm
                plumbing is wrong and the rk4fd result must not be read.
  upwind1     : same RK4 time integration but a FIRST-ORDER one-sided radial
                derivative. A correct measurement pipeline must report order ~1
                and fall outside 2.0 +/- 0.3. If this control measures ~2, the
                pipeline cannot detect a wrong-order scheme and the primary
                result is vacuous.

HASH GUARDS
  Refuses to run unless the two pinned inputs match the hashes of record, and
  re-measures them after the run; a mid-run change is reported as unstable rather
  than silently bound.

USAGE
  python3 artifacts/worker-055/n0_rk4_independent/independent_replication.py
  python3 artifacts/worker-055/n0_rk4_independent/independent_replication.py --quick
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

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

# ---------------------------------------------------------------------------
# pinned inputs of record
# ---------------------------------------------------------------------------
PINNED = {
    "numerics/tests/flat_wave_replication.py": (
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
    ),
    "numerics/tests/n0_order_4rung.json": (
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a"
    ),
}
RECORDED_PATH = REPO / "numerics/tests/n0_order_4rung.json"

CONFIG = {
    "r0": 10.0,
    "sigma": 1.5,
    "r_max": 30.0,
    "t_end": 6.0,
    "dr_values": [0.2, 0.1, 0.05, 0.025],
    "cfl": 0.5,
    "p_expected": 2.0,
    "p_tol": 0.3,
    "r5_floor": 0.25,
    "uncertainty_rule": "R5: max(pair-spread half-range, least-squares slope SE)",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# exact solution, re-derived independently
# ---------------------------------------------------------------------------
class GaussianPulse:
    """psi(r,t) = F(r-t) - F(-r-t), F(s) = exp(-(s-r0)^2/(2 sigma^2)).

    psi solves psi_tt = psi_rr on r >= 0 with psi(0,t)=0; phi = psi/r is the
    regular spherical massless test field, phi_r(0,t)=0.
    """

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

    def psi(self, r, t):
        r = np.asarray(r, dtype=float)
        return self.F(r - t) - self.F(-r - t)

    def psi_t(self, r, t):
        r = np.asarray(r, dtype=float)
        return -self.Fp(r - t) + self.Fp(-r - t)

    def phi(self, r, t):
        """phi = psi/r with the regular limit phi(0,t) = 2*F'(-t)."""
        r = np.asarray(r, dtype=float)
        out = np.empty_like(r)
        small = r < 1e-12
        out[~small] = self.psi(r[~small], t) / r[~small]
        if np.any(small):
            out[small] = 2.0 * self.Fp(-t)
        return out

    def phi_t(self, r, t):
        """phi_t = psi_t/r with the regular limit phi_t(0,t) = -2*F''(-t)."""
        r = np.asarray(r, dtype=float)
        out = np.empty_like(r)
        small = r < 1e-12
        out[~small] = self.psi_t(r[~small], t) / r[~small]
        if np.any(small):
            out[small] = -2.0 * self.Fpp(-t)
        return out


def grid(r_max: float, dr: float) -> np.ndarray:
    n = int(round(r_max / dr))
    return np.linspace(0.0, n * dr, n + 1)


def l2_error(numeric, reference, dr) -> float:
    diff = np.asarray(numeric, float) - np.asarray(reference, float)
    return float(math.sqrt(float(np.sum(diff * diff)) * dr))


def fit_order(drs, errs) -> float:
    x, y = np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float))
    return float(np.polyfit(x, y, 1)[0])


def pair_orders(drs, errs):
    return [
        float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
        for i in range(len(errs) - 1)
    ]


def slope_uncertainty(drs, errs, fit_p):
    x, y = np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float))
    pair = pair_orders(drs, errs)
    half_range = (max(pair) - min(pair)) / 2.0
    resid = y - (fit_p * x + (y.mean() - fit_p * x.mean()))
    dof = len(x) - 2
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = math.sqrt(float(np.sum(resid ** 2)) / dof / sxx) if dof > 0 and sxx > 0 else float("nan")
    return {"delta": max(half_range, se), "pair_half_range": half_range,
            "least_squares_se": se, "pair_orders": pair}


def r5_bound(a, b) -> float:
    return max(CONFIG["r5_floor"], math.sqrt(a["delta"] ** 2 + b["delta"] ** 2))


# ---------------------------------------------------------------------------
# primary independent scheme: RK4 method-of-lines on phi directly
# ---------------------------------------------------------------------------
def spatial_accel_centred(phi, r, dr):
    """phi_rr + (2/r) phi_r, centred 2nd order; even ghost at r=0 => 3*phi_rr(0)."""
    acc = np.empty_like(phi)
    acc[1:-1] = (
        (phi[2:] - 2.0 * phi[1:-1] + phi[:-2]) / dr ** 2
        + (2.0 / r[1:-1]) * (phi[2:] - phi[:-2]) / (2.0 * dr)
    )
    # phi_r(0)=0, even extension phi(-dr)=phi(dr):
    # phi_rr(0) = 2(phi1-phi0)/dr^2  =>  phi_tt(0) = 3*phi_rr(0) = 6(phi1-phi0)/dr^2
    acc[0] = 6.0 * (phi[1] - phi[0]) / dr ** 2
    acc[-1] = 0.0
    return acc


def spatial_accel_upwind1(phi, r, dr):
    """WRONG-ORDER CONTROL: 1st-order one-sided radial derivative, same time integrator."""
    acc = np.empty_like(phi)
    acc[1:-1] = (
        (phi[2:] - 2.0 * phi[1:-1] + phi[:-2]) / dr ** 2
        + (2.0 / r[1:-1]) * (phi[1:-1] - phi[:-2]) / dr
    )
    acc[0] = 6.0 * (phi[1] - phi[0]) / dr ** 2
    acc[-1] = 0.0
    return acc


def run_rk4(pulse, dr, cfl, r_max, t_end, accel_fn):
    r = grid(r_max, dr)
    dt = cfl * dr
    n_steps = int(round(t_end / dt))
    if abs(n_steps * dt - t_end) > 1e-12:
        raise ValueError(f"t_end={t_end} not an integer number of steps at dr={dr}")
    phi = pulse.phi(r, 0.0)
    w = pulse.phi_t(r, 0.0)
    phi[0] = pulse.phi(np.array([0.0]), 0.0)[0]
    w[0] = pulse.phi_t(np.array([0.0]), 0.0)[0]
    # outer Dirichlet truncation is the same boundary data as the claim of record
    phi[-1] = 0.0
    w[-1] = 0.0

    def rhs(p, q):
        return q, accel_fn(p, r, dr)

    for _ in range(n_steps):
        k1p, k1w = rhs(phi, w)
        k2p, k2w = rhs(phi + 0.5 * dt * k1p, w + 0.5 * dt * k1w)
        k3p, k3w = rhs(phi + 0.5 * dt * k2p, w + 0.5 * dt * k2w)
        k4p, k4w = rhs(phi + dt * k3p, w + dt * k3w)
        phi = phi + (dt / 6.0) * (k1p + 2.0 * k2p + 2.0 * k3p + k4p)
        w = w + (dt / 6.0) * (k1w + 2.0 * k2w + 2.0 * k3w + k4w)
        phi[-1] = 0.0
        w[-1] = 0.0
        if not np.all(np.isfinite(phi)):
            raise FloatingPointError(f"non-finite state at dr={dr}")
    return {"r": r, "dt": dt, "steps": n_steps, "phi": phi, "w": w, "t": n_steps * dt}


# ---------------------------------------------------------------------------
# wiring control: psi leapfrog re-implemented from scratch (shares reference axes)
# ---------------------------------------------------------------------------
def run_lffd_reimpl(pulse, dr, cfl, r_max, t_end):
    r = grid(r_max, dr)
    dt = cfl * dr
    n_steps = int(round(t_end / dt))
    psi0 = pulse.psi(r, 0.0)
    psit0 = pulse.psi_t(r, 0.0)
    # psi_tt = psi_rr exactly at t=0 (independent of the reference's own helper)
    psitt0 = np.empty_like(r)
    h = dr
    psitt0[1:-1] = (psi0[2:] - 2.0 * psi0[1:-1] + psi0[:-2]) / h ** 2
    psitt0[0] = 0.0
    psitt0[-1] = 0.0
    psi = psi0.copy()
    older = psi0.copy()
    newer = psi0 + dt * psit0 + 0.5 * dt ** 2 * psitt0
    older[0] = older[-1] = 0.0
    newer[0] = newer[-1] = 0.0
    lam2 = (dt / dr) ** 2
    for _ in range(n_steps - 1):
        nxt = np.empty_like(newer)
        nxt[1:-1] = (
            2.0 * newer[1:-1] - older[1:-1]
            + lam2 * (newer[2:] - 2.0 * newer[1:-1] + newer[:-2])
        )
        nxt[0] = nxt[-1] = 0.0
        older, newer = newer, nxt
        if not np.all(np.isfinite(newer)):
            raise FloatingPointError(f"non-finite state at dr={dr}")
    return {"r": r, "dt": dt, "steps": n_steps, "psi": newer, "t": n_steps * dt}


# ---------------------------------------------------------------------------
# studies
# ---------------------------------------------------------------------------
def study(scheme: str, pulse: GaussianPulse, dr_values, cfl, r_max, t_end):
    rows = []
    for dr in dr_values:
        if scheme == "lffd_reimpl":
            case = run_lffd_reimpl(pulse, dr, cfl, r_max, t_end)
            psi_num = case["psi"]
            phi_num = None
        elif scheme == "rk4fd":
            case = run_rk4(pulse, dr, cfl, r_max, t_end, spatial_accel_centred)
            psi_num = case["r"] * case["phi"]
            phi_num = case["phi"]
        elif scheme == "upwind1":
            case = run_rk4(pulse, dr, cfl, r_max, t_end, spatial_accel_upwind1)
            psi_num = case["r"] * case["phi"]
            phi_num = case["phi"]
        else:
            raise ValueError(scheme)
        r = case["r"]
        t = case["t"]
        row = {
            "dr": dr,
            "dt": case["dt"],
            "cfl": cfl,
            "steps": case["steps"],
            "l2_error": l2_error(psi_num, pulse.psi(r, t), dr),
        }
        if phi_num is not None:
            row["l2_error_phi"] = l2_error(phi_num, pulse.phi(r, t), dr)
        rows.append(row)
    errs = [row["l2_error"] for row in rows]
    out = {
        "scheme": scheme,
        "rows": rows,
        "fit_order": fit_order(dr_values, errs),
        "pair_orders": pair_orders(dr_values, errs),
        "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
    }
    out.update(slope_uncertainty(dr_values, errs, out["fit_order"]))
    out["within_harness_tol"] = bool(abs(out["fit_order"] - CONFIG["p_expected"]) <= CONFIG["p_tol"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="dr in {0.2,0.1,0.05} only")
    args = ap.parse_args()

    t_start = time.time()
    # ---- hash guards -----------------------------------------------------
    pinned_measured_before = {p: sha256(REPO / p) for p in PINNED}
    mismatches = {p: {"expected": PINNED[p], "measured": pinned_measured_before[p]}
                  for p in PINNED if pinned_measured_before[p] != PINNED[p]}
    if mismatches:
        print(json.dumps({"refuse": "pinned input hash mismatch", "mismatches": mismatches}, indent=2))
        return 2

    recorded = json.loads(RECORDED_PATH.read_text())
    recorded_orders = {s["scheme"]: s["fit_order"] for s in recorded["studies"]}
    recorded_delta = {s["scheme"]: s["delta"] for s in recorded["studies"]}

    dr_values = [0.2, 0.1, 0.05] if args.quick else list(CONFIG["dr_values"])
    pulse = GaussianPulse(CONFIG["r0"], CONFIG["sigma"])

    studies = [
        study("rk4fd", pulse, dr_values, CONFIG["cfl"], CONFIG["r_max"], CONFIG["t_end"]),
        study("lffd_reimpl", pulse, dr_values, CONFIG["cfl"], CONFIG["r_max"], CONFIG["t_end"]),
        study("upwind1", pulse, dr_values, CONFIG["cfl"], CONFIG["r_max"], CONFIG["t_end"]),
    ]
    by = {s["scheme"]: s for s in studies}

    # ---- determinism control: the primary study must repeat bitwise -------
    rerun = study("rk4fd", pulse, dr_values, CONFIG["cfl"], CONFIG["r_max"], CONFIG["t_end"])
    determinism = {
        "primary_study_repeats_bitwise": bool(
            json.dumps(rerun, sort_keys=True) == json.dumps(by["rk4fd"], sort_keys=True)
        ),
        "rerun_fit_order": rerun["fit_order"],
        "no_rng": True,
    }

    # ---- comparisons -----------------------------------------------------
    comparisons = []
    for ref in ("lffd", "cnfd", "cnfem"):
        ref_rec = {"scheme": ref, "fit_order": recorded_orders[ref], "delta": recorded_delta[ref]}
        lhs = abs(by["rk4fd"]["fit_order"] - recorded_orders[ref])
        bound = r5_bound(by["rk4fd"], ref_rec)
        comparisons.append({
            "pair": f"rk4fd vs recorded {ref}",
            "abs_order_diff": lhs,
            "r5_bound": bound,
            "agree": bool(lhs <= bound),
        })
    wiring = {
        "recorded_lffd_fit_order": recorded_orders["lffd"],
        "reimpl_fit_order": by["lffd_reimpl"]["fit_order"],
        "abs_order_diff": abs(by["lffd_reimpl"]["fit_order"] - recorded_orders["lffd"]),
        "r5_bound": r5_bound(by["lffd_reimpl"],
                             {"delta": recorded_delta["lffd"]}),
    }
    wiring["agree"] = bool(wiring["abs_order_diff"] <= wiring["r5_bound"])
    control_upwind = {
        "fit_order": by["upwind1"]["fit_order"],
        "within_2p0_tol_0p3": by["upwind1"]["within_harness_tol"],
        "detects_wrong_order": bool(not by["upwind1"]["within_harness_tol"]),
        "expected": "order ~1 and outside 2.0 +/- 0.3",
    }

    # ---- anti-drift re-measure ------------------------------------------
    pinned_measured_after = {p: sha256(REPO / p) for p in PINNED}
    stable = pinned_measured_after == pinned_measured_before

    verdict = {
        "primary_rk4fd_fit_order": by["rk4fd"]["fit_order"],
        "primary_rk4fd_within_2p0_tol_0p3": by["rk4fd"]["within_harness_tol"],
        "primary_rk4fd_monotone": by["rk4fd"]["monotone"],
        "rk4fd_agrees_with_all_recorded_schemes_R5": all(c["agree"] for c in comparisons),
        "wiring_control_reproduces_recorded_lffd": wiring["agree"],
        "failure_detection_control_fires": control_upwind["detects_wrong_order"],
        "primary_study_repeats_bitwise": determinism["primary_study_repeats_bitwise"],
        "pinned_inputs_stable_during_run": stable,
    }
    verdict["all_checks_pass"] = bool(
        verdict["primary_rk4fd_within_2p0_tol_0p3"]
        and verdict["primary_rk4fd_monotone"]
        and verdict["rk4fd_agrees_with_all_recorded_schemes_R5"]
        and verdict["wiring_control_reproduces_recorded_lffd"]
        and verdict["failure_detection_control_fires"]
        and verdict["primary_study_repeats_bitwise"]
        and stable
    )

    report = {
        "schema_version": "w055-independent-replication-1.0",
        "task_id": "W055-N0-RK4-INDEP-01",
        "artifact": "artifacts/worker-055/n0_rk4_independent/independent_replication.py",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "author": "worker-055",
        "node_id": "N0",
        "gate": "G-NUM",
        "group_id": "numerics",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "claims_completion": False,
        "purpose": (
            "independent-method replication of the N0 order claim along the axes the frozen "
            "replication declares shared with the reference (psi=r*phi reduction, Dirichlet "
            "origin, Taylor start, leapfrog/CN time integration)"
        ),
        "independence_axes": [
            "phi evolved directly; psi=r*phi never formed inside the solver",
            "l'Hopital origin closure 3*phi_rr(0) with even ghost, not psi(0)=0",
            "classical RK4 method-of-lines, no Taylor start, no three-level scheme",
            "centred d2/dr2 + (2/r) d/dr stencil, different from the psi-family Laplacian",
            "independent implementation of the l2 error rule",
        ],
        "shared_axes_not_covered": [
            "same PDE psi_tt = psi_rr / spherical massless test field (the claim's definition)",
            "same Gaussian-pulse family r0=10, sigma=1.5",
            "same outer Dirichlet truncation at r=30 (data negligible there for t<=6)",
            "same l2 metric formula and the same four-rung config",
        ],
        "config": CONFIG,
        "dr_values_used": dr_values,
        "pinned_inputs": {
            p: {"expected": PINNED[p], "measured_before": pinned_measured_before[p],
                "measured_after": pinned_measured_after[p]}
            for p in PINNED
        },
        "recorded_orders_of_claim": recorded_orders,
        "studies": studies,
        "comparisons_vs_recorded": comparisons,
        "wiring_control": wiring,
        "failure_detection_control": control_upwind,
        "determinism_control": determinism,
        "verdict": verdict,
        "falsifier": (
            "Re-run this script at the pinned input hashes. The replication is falsified if any of: "
            "(a) flat_wave_replication.py sha256 != 8ade1cdc or n0_order_4rung.json sha256 != c88146a1 "
            "(the run refuses instead of binding a superseded revision); (b) rk4fd is non-monotone, "
            "leaves 2.0 +/- 0.3, or disagrees with any recorded scheme beyond the R5 bound; "
            "(c) the wiring control lffd_reimpl fails to reproduce the recorded lffd order 1.996624864320 "
            "within R5, which would indict this file's grid/dt/t_end/norm plumbing and void the rk4fd "
            "reading; (d) the failure-detection control upwind1 measures order inside 2.0 +/- 0.3, "
            "which would mean this pipeline cannot detect a wrong-order scheme; (e) the pinned inputs "
            "change mid-run (reported as unstable, no verdict)."
        ),
        "not_claimed": [
            "no gate verdict and no gate self-pass; this is supporting evidence for G-NUM only",
            "no node completion; N0 stays active and numerics_lock stays LOCKED",
            "no judgement on the C8 protocol review or on the candidate numerics/tests/flat_wave.py",
            "no physics claim; flat-space calibration sub-case only, no self-gravity",
            "no claim that the shared axes above are error-free; only the independence axes are tested",
        ],
        "lock_state": "numerics_lock respected: no N1 work, no numerics/spherical_solver/ created or touched",
        "runtime": {
            "seconds": round(time.time() - t_start, 3),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
            "seeds": "none: deterministic, no RNG",
        },
    }
    out_path = HERE / "report.json"
    # wall-clock-independent content hash: the numbers must be re-derivable byte-for-byte
    # even though created_at / runtime.seconds necessarily differ between runs
    serializable = dict(report)
    serializable["created_at"] = ""
    serializable["runtime"] = {**report["runtime"], "seconds": 0}
    report["content_sha256"] = hashlib.sha256(
        json.dumps(serializable, indent=2, sort_keys=True).encode()
    ).hexdigest()
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(out_path.relative_to(REPO)),
        "sha256": sha256(out_path),
        "content_sha256": report["content_sha256"],
        "orders": {s["scheme"]: s["fit_order"] for s in studies},
        "verdict": verdict,
    }, indent=2))
    return 0 if verdict["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
