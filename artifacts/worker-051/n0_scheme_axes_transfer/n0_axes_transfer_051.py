#!/usr/bin/env python3
"""W051-N0-SCHEME-AXES-03 — configuration-transfer falsifier test of the N0
scheme-axis multiplicity finding (worker-051's previous bounded task).

Claim under test (artifact: artifacts/worker-051/n0_scheme_axes/report.json,
sha256 7ddac5e40d9e134fe73cdb19c85950cd63a9754d9b5518e580503b2e6dcef100):

  At the frozen module numerics/tests/flat_wave_replication.py
  (sha256 8ade1cdc...) the three published N0 schemes (lffd, cnfd, cnfem) span
  only 2 distinct spatial discretisations x 2 distinct time integrators
  (3 of the 4 design cells), lffd and cnfd share the identical 3-point FD
  spatial operator, the FEM operator is distinct (grid-Nyquist ratio exactly 3)
  and second-order consistent, and the added fourth cell femlf is order 2 in
  the protocol band |p-2| <= 0.3.

The previous artifact's own next-falsifier (verbatim, section 5 of its README):

  "re-run at the same pinned module hash on a different grid (e.g. r_max = 40,
   or a different pulse family) and check that the FEM/FD Nyquist ratio is
   still 3 and that the femlf cell stays in band."

This script performs exactly that transfer.  Everything is read-only on the
canonical/published tree; outputs are written under
artifacts/worker-051/n0_scheme_axes_transfer/ only.

Numerics lock: N0 is the allowed node; no self-gravitating code is written,
imported, or run (numerics/spherical_solver/ is never touched).

Exit code is 0 when the harness completed (the verdict is data, not an exit
status); 3 when hash pins do not resolve (a real falsifier outcome, reported).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PUB_PATH = ROOT / "numerics" / "tests" / "flat_wave_replication.py"
AX_PATH = ROOT / "artifacts" / "worker-051" / "n0_scheme_axes" / "n0_scheme_axes_051.py"
FOUR_RUNG_PATH = ROOT / "numerics" / "tests" / "n0_order_4rung.json"
PROTOCOL_PATH = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
AX_REPORT_PATH = ROOT / "artifacts" / "worker-051" / "n0_scheme_axes" / "report.json"
CST = timezone(timedelta(hours=8))

# Hash pins: refuse to measure against drifted bytes.  Expected values were
# re-measured on disk at task start (2026-09-12T00:39+0800).
PINS = {
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/tests/n0_order_4rung.json":
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "artifacts/worker-051/n0_scheme_axes/n0_scheme_axes_051.py":
        "9b08d95effcfe88e8d1dee0ae8d37f5c4f456b831aaa3266c6faceb53e7026b0",
    "artifacts/worker-051/n0_scheme_axes/report.json":
        "7ddac5e40d9e134fe73cdb19c85950cd63a9754d9b5518e580503b2e6dcef100",
}

P_EXPECTED = 2.0
P_TOL = 0.3
RUNGS = [0.2, 0.1, 0.05, 0.025]
CFLS_ISO = [0.5, 0.25, 0.125]
CELLS = ["lffd", "cnfd", "cnfem", "femlf"]

# Configurations.  C0 re-runs the published configuration as a bitwise control.
# T1 changes the grid (r_max 30 -> 40) and lets the pulse travel to r=30.
# T2 changes the pulse family (narrower, closer to the origin).
# T3 changes the pulse family (wider) and shortens t_end.
# Boundary-cleanliness criterion (pre-registered): r0 + t_end + 4*sigma < r_max,
# so the outer Dirichlet wall sees only a ~e^{-8} tail.
CONFIGS = [
    {"id": "C0_published_control", "kind": "control", "r_max": 30.0, "t_end": 6.0,
     "pulse": {"r0": 10.0, "sigma": 1.5}},
    {"id": "T1_grid_r40", "kind": "transfer", "r_max": 40.0, "t_end": 20.0,
     "pulse": {"r0": 10.0, "sigma": 1.5}},
    {"id": "T2_pulse_narrow", "kind": "transfer", "r_max": 30.0, "t_end": 6.0,
     "pulse": {"r0": 6.0, "sigma": 0.9}},
    {"id": "T3_pulse_wide", "kind": "transfer", "r_max": 30.0, "t_end": 5.0,
     "pulse": {"r0": 8.0, "sigma": 2.5}},
]

# Transfer acceptance bands (pre-registered, same as the protocol band)
SMOOTH_ORDER_BAND = (P_EXPECTED - P_TOL, P_EXPECTED + P_TOL)
NYQUIST_RATIO_EXPECTED = 3.0
NYQUIST_RATIO_TOL = 1e-12
TAIL_TOL = 1e-9


def now() -> str:
    return datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # both pinned modules guard main under __main__
    return mod


def verify_pins() -> dict:
    out = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        measured = sha256_file(p) if p.exists() else None
        out[rel] = {"expected": expected, "measured": measured,
                    "match": measured == expected}
    return out


# ---------------------------------------------------------------------------
# order studies (generic in config)
# ---------------------------------------------------------------------------
def build_factories(pub, ax, pulse):
    """factories[cell] = factory(r, dt) -> solver, all four cells."""
    fac = {c: pub.make_factory(c, pulse=pulse) for c in CELLS[:3]}
    femlf_cls = ax.make_fem_leapfrog(pub)

    def femlf_factory(r, dt):
        psi0, pt0, ptt0 = pulse.initial_data(r)
        return femlf_cls(r, dt, psi0, pt0, ptt0)

    fac["femlf"] = femlf_factory
    return fac


def mixed_order(pub, factory, cfg: dict) -> dict:
    pulse = pub.PulseExact(**cfg["pulse"])
    rows = []
    for dr in RUNGS:
        case = pub.run_case(factory, dr, 0.5, cfg["r_max"], cfg["t_end"])
        err = pub.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = case["r"]
            num = case["psi"][-1] / np.maximum(r, 1e-300)
            ref = pulse.psi(r, case["t"][-1]) / np.maximum(r, 1e-300)
        rows.append({"dr": dr, "dt": case["dt"], "steps": case["steps"],
                     "final_t": case["t"][-1], "l2_error": err,
                     "l2_error_u": pub.l2_error(num, ref, dr)})
    errs = [r["l2_error"] for r in rows]
    p = pub.fit_order(RUNGS, errs)
    return {"scheme": None, "rows": rows, "fit_order": p,
            "pair_orders": pub.pair_orders(RUNGS, errs),
            "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
            "within_band": bool(abs(p - P_EXPECTED) <= P_TOL)}


def isolated_spatial_order(pub, factory, cfg: dict) -> dict:
    pulse = pub.PulseExact(**cfg["pulse"])
    e0s, rows = [], []
    for dr in RUNGS:
        errs = []
        for cfl in CFLS_ISO:
            case = pub.run_case(factory, dr, cfl, cfg["r_max"], cfg["t_end"],
                                sample_every=64)
            err = pub.l2_error(case["psi"][-1], pulse.psi(case["r"], case["t"][-1]), dr)
            errs.append({"cfl": cfl, "dt": case["dt"], "steps": case["steps"],
                         "l2_error": err})
        dt2 = np.array([e["dt"] ** 2 for e in errs])
        ee = np.array([e["l2_error"] for e in errs])
        slope, intercept = np.polyfit(dt2, ee, 1)
        pred = slope * dt2 + intercept
        rows.append({"dr": dr, "runs": errs, "temporal_slope": float(slope),
                     "e0_dt0": float(intercept),
                     "temporal_fit_max_rel_resid":
                         float(np.max(np.abs(pred - ee) / ee))})
        e0s.append(float(intercept))
    p = float(pub.fit_order(RUNGS, e0s))
    return {"rungs": rows, "e0_by_dr": e0s, "spatial_order_dt0": p,
            "pair_orders_dt0": pub.pair_orders(RUNGS, e0s),
            "monotone": all(e0s[i + 1] < e0s[i] for i in range(len(e0s) - 1)),
            "within_band": bool(abs(p - P_EXPECTED) <= P_TOL)}


def boundary_cleanliness(pub, cfg: dict) -> dict:
    """Outer-wall contamination control for the transfer configurations."""
    pulse = pub.PulseExact(**cfg["pulse"])
    r = cfg["r_max"]
    t = cfg["t_end"]
    tail_now = float(abs(pulse.psi(r, t)))
    tail_init = float(abs(pulse.psi(r, 0.0)))
    margin = r - (cfg["pulse"]["r0"] + t)
    margin_sigmas = margin / cfg["pulse"]["sigma"]
    ok = tail_now < TAIL_TOL and tail_init < TAIL_TOL and margin_sigmas >= 4.0
    return {"r_max": r, "t_end": t, "outer_tail_at_t_end": tail_now,
            "outer_tail_at_t0": tail_init, "margin_r_minus_r0_plus_t": margin,
            "margin_in_sigma": margin_sigmas, "margin_criterion_sigmas": 4.0,
            "tail_tolerance": TAIL_TOL, "clean": bool(ok)}


# ---------------------------------------------------------------------------
# operator checks (config-independent algebra, re-measured per r_max)
# ---------------------------------------------------------------------------
def operator_checks(pub, ax, r_max: float, rng) -> dict:
    h = 0.05
    m = int(round(r_max / h)) - 1
    A = ax.fd_operator(pub, m, h)
    M, K = ax.fem_matrices(pub, m, h)
    L_fem = np.linalg.solve(M, -K)
    r = pub.grid(r_max, h)
    pulse = pub.PulseExact(10.0, 1.5)
    psi0, pt0, ptt0 = pulse.initial_data(r)
    dt = 0.5 * h

    cur = np.zeros(m + 2)
    prev = np.zeros(m + 2)
    cur[1:-1] = rng.standard_normal(m)
    prev[1:-1] = rng.standard_normal(m)

    lf = pub.LeapfrogFD(r, dt, psi0, pt0, ptt0)
    _, d2_lf = ax.one_step(lf, cur, prev)
    res_lf = float(np.max(np.abs(d2_lf - A @ cur[1:-1])) / np.max(np.abs(d2_lf)))

    cn = pub.CrankNicolsonFD(r, dt, psi0, pt0, ptt0)
    nxt_cn, d2_cn = ax.one_step(cn, cur, prev)
    res_cn = float(np.max(np.abs(d2_cn - A @ (0.5 * (nxt_cn[1:-1] + prev[1:-1]))))
                   / np.max(np.abs(d2_cn)))
    A_attr = ax.dense_from_tridiag(cn.A, m)
    res_cn_attr = float(np.max(np.abs(A_attr - A)))

    fem = pub.CrankNicolsonFEM(r, dt, psi0, pt0, ptt0)
    nxt_fem, d2_fem = ax.one_step(fem, cur, prev)
    mid_fem = 0.5 * (nxt_fem[1:-1] + prev[1:-1])
    res_fem = float(np.max(np.abs(M @ d2_fem + K @ mid_fem)) / np.max(np.abs(M @ d2_fem)))
    res_fem_attr = float(np.max(np.abs(ax.dense_from_tridiag(fem.M, m) - M))
                         + np.max(np.abs(ax.dense_from_tridiag(fem.K, m) - K)))

    femlf_cls = ax.make_fem_leapfrog(pub)
    fl = femlf_cls(r, dt, psi0, pt0, ptt0)
    nxt_fl, d2_fl = ax.one_step(fl, cur, prev)
    res_fl = float(np.max(np.abs(M @ d2_fl + K @ cur[1:-1])) / np.max(np.abs(M @ d2_fl)))

    # distinctness / second-order consistency across the rung ladder
    rows = []
    for dr in RUNGS:
        mm = int(round(r_max / dr)) - 1
        rr = pub.grid(r_max, dr)
        A_h = ax.fd_operator(pub, mm, dr)
        M_h, K_h = ax.fem_matrices(pub, mm, dr)
        L_h = np.linalg.solve(M_h, -K_h)
        D = L_h - A_h
        u = np.sin(np.pi * rr[1:-1] / r_max)
        rel_smooth = float(np.max(np.abs(D @ u)) / np.max(np.abs(A_h @ u)))
        vny = (-1.0) ** np.arange(1, mm + 1)
        i0 = mm // 2
        lam_fd = float(-(A_h @ vny)[i0] / vny[i0])
        lam_fem = float(-(L_h @ vny)[i0] / vny[i0])
        rows.append({"dr": dr, "m_interior": mm,
                     "rel_sup_smooth_mode1": rel_smooth,
                     "lambda_fd_nyquist_center": lam_fd,
                     "lambda_fem_nyquist_center": lam_fem,
                     "nyquist_ratio_fem_over_fd": lam_fem / lam_fd,
                     "nyquist_dev_fd": abs(lam_fd - 4.0 / dr ** 2) / (4.0 / dr ** 2),
                     "nyquist_dev_fem": abs(lam_fem - 12.0 / dr ** 2) / (12.0 / dr ** 2),
                     "boundary_row_rel_diff":
                         float(np.max(np.abs(D[0, :])) / np.max(np.abs(A_h[0, :])))})
    smooth = [row["rel_sup_smooth_mode1"] for row in rows]
    order_smooth = float(np.polyfit(np.log(RUNGS), np.log(smooth), 1)[0])
    ratios = [row["nyquist_ratio_fem_over_fd"] for row in rows]
    return {
        "r_max": r_max, "h_check": h, "m_check": m,
        "one_step_identity_residuals": {
            "lffd_d2_minus_A_cur": res_lf,
            "cnfd_d2_minus_A_mid": res_cn,
            "cnfd_A_attribute_minus_rebuilt_FD": res_cn_attr,
            "cnfem_M_d2_plus_K_mid": res_fem,
            "cnfem_MK_attribute_minus_rebuilt": res_fem_attr,
            "femlf_M_d2_plus_K_cur": res_fl,
        },
        "lffd_cnfd_share_FD_operator": bool(
            res_lf < 1e-12 and res_cn < 1e-12 and res_cn_attr == 0.0),
        "fem_vs_fd": {
            "order_smooth_mode1": order_smooth,
            "smooth_order_in_band": bool(
                SMOOTH_ORDER_BAND[0] <= order_smooth <= SMOOTH_ORDER_BAND[1]),
            "nyquist_ratio_min": min(ratios),
            "nyquist_ratio_max": max(ratios),
            "nyquist_ratio_exact": bool(
                max(abs(x - NYQUIST_RATIO_EXPECTED) for x in ratios)
                <= NYQUIST_RATIO_TOL),
            "rows": rows,
        },
    }


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.json"))
    args = ap.parse_args()

    t0 = time.time()
    started = now()
    rng = np.random.default_rng(5103)

    pins = verify_pins()
    pins_ok = all(v["match"] for v in pins.values())
    report = {
        "task_id": "W051-N0-SCHEME-AXES-03",
        "worker": "worker-051",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_binding": ("flat-space test-field calibration sub-case only; fixed Minkowski, "
                          "massless scalar, no coupling to geometry; not an instance of the "
                          "Einstein-coupled class"),
        "conclusion_type": "numerical_evidence",
        "created_at": started,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "pins": pins,
        "numerics_lock_state_at_task_start": "locked; N0 allowed, no N1 artifact touched",
        "configs": CONFIGS,
        "rungs": RUNGS, "cfls_isolated": CFLS_ISO,
        "p_expected": P_EXPECTED, "p_tol": P_TOL,
    }

    if not pins_ok:
        report["pins_ok"] = False
        report["verdict"] = {
            "overall": "falsifier_triggered",
            "triggered": ["F1_hash_pins_resolve"],
            "statement": ("A pinned input (published module, protocol, published order "
                          "artifact, or the prior harness/report) no longer matches the bytes "
                          "this task pre-registered; the transfer measurement is refused "
                          "rather than silently re-bound."),
        }
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report["pins"], indent=2))
        print("PINS DO NOT RESOLVE — measurement refused (falsifier_triggered).")
        return 3

    pub = load_module("n0_replication_pinned", PUB_PATH)
    ax = load_module("w051_scheme_axes_pinned", AX_PATH)
    four_rung = json.loads(FOUR_RUNG_PATH.read_text())
    published_orders = {k: float(v) for k, v in
                        four_rung.get("verdict", {}).get("orders", {}).items()}
    prior = json.loads(AX_REPORT_PATH.read_text())
    prior_mixed = {c: float(prior["mixed_order_4rung"][c]["fit_order_4rung"])
                   for c in CELLS[:3]}
    prior_femlf_mixed = float(prior["mixed_order_4rung"]["femlf"]["fit_order_4rung"])
    prior_iso = {c: float(prior["isolated_spatial_order"][c]["spatial_order_dt0"])
                 for c in CELLS}

    # ---- controls ---------------------------------------------------------
    control_cfg = CONFIGS[0]
    control = {"boundary": boundary_cleanliness(pub, control_cfg),
               "published_reproduction": {}, "prior_artifact_reproduction": {}}
    facs0 = build_factories(pub, ax, pub.PulseExact(**control_cfg["pulse"]))
    control["mixed_orders"] = {}
    for cell in CELLS:
        mres = mixed_order(pub, facs0[cell], control_cfg)
        control["mixed_orders"][cell] = mres["fit_order"]
        if cell in published_orders:
            control["published_reproduction"][cell] = {
                "published": published_orders[cell], "measured": mres["fit_order"],
                "abs_delta": abs(mres["fit_order"] - published_orders[cell])}
        else:
            control["prior_artifact_reproduction"][cell] = {
                "prior_artifact": prior_femlf_mixed, "measured": mres["fit_order"],
                "abs_delta": abs(mres["fit_order"] - prior_femlf_mixed)}
    control["published_reproduction_all_bitwise_lt_1e-12"] = all(
        v["abs_delta"] < 1e-12 for v in control["published_reproduction"].values())
    control["prior_artifact_reproduction_all_lt_1e-12"] = all(
        v["abs_delta"] < 1e-12
        for v in control["prior_artifact_reproduction"].values())

    # determinism control: repeat one transfer case bitwise
    fc = CONFIGS[2]
    facs_det = build_factories(pub, ax, pub.PulseExact(**fc["pulse"]))
    c1 = pub.run_case(facs_det["femlf"], 0.05, 0.5, fc["r_max"], fc["t_end"])
    c2 = pub.run_case(facs_det["femlf"], 0.05, 0.5, fc["r_max"], fc["t_end"])
    control["determinism"] = {
        "case": f"{fc['id']} femlf dr=0.05 cfl=0.5",
        "final_psi_bitwise_equal": bool(np.array_equal(c1["psi"][-1], c2["psi"][-1])),
        "final_t_equal": bool(c1["t"][-1] == c2["t"][-1]),
        "steps_equal": bool(c1["steps"] == c2["steps"]),
    }
    report["controls"] = control

    # ---- operator checks at both r_max values -----------------------------
    report["operator_checks"] = {
        "r_max_30": operator_checks(pub, ax, 30.0, rng),
        "r_max_40": operator_checks(pub, ax, 40.0, rng),
    }

    # ---- transfer runs ----------------------------------------------------
    results = {}
    for cfg in CONFIGS:
        pulse = pub.PulseExact(**cfg["pulse"])
        facs = build_factories(pub, ax, pulse)
        entry = {"kind": cfg["kind"], "r_max": cfg["r_max"], "t_end": cfg["t_end"],
                 "pulse": cfg["pulse"],
                 "boundary_cleanliness": boundary_cleanliness(pub, cfg),
                 "cells": {}}
        for cell in CELLS:
            mr = mixed_order(pub, facs[cell], cfg)
            ir = isolated_spatial_order(pub, facs[cell], cfg)
            entry["cells"][cell] = {"mixed_order_4rung": mr,
                                    "isolated_spatial_order": ir}
        results[cfg["id"]] = entry
    report["results"] = results

    # ---- falsifier evaluation --------------------------------------------
    checks = {
        "F1_hash_pins_resolve": bool(pins_ok),
        "F2_control_published_orders_reproduced_bitwise":
            bool(control["published_reproduction_all_bitwise_lt_1e-12"]),
        "F2b_control_prior_femlf_order_reproduced":
            bool(control["prior_artifact_reproduction_all_lt_1e-12"]),
        "F3_all_configs_boundary_clean":
            bool(all(v["boundary_cleanliness"]["clean"] for v in results.values())),
        "F4_lffd_cnfd_share_FD_operator_at_both_grids":
            bool(all(v["lffd_cnfd_share_FD_operator"]
                     for v in report["operator_checks"].values())),
        "F5_fem_fd_distinct_and_second_order_at_both_grids":
            bool(all(v["fem_vs_fd"]["nyquist_ratio_exact"]
                     and v["fem_vs_fd"]["smooth_order_in_band"]
                     for v in report["operator_checks"].values())),
        "F6_all_cells_mixed_order_in_band_all_configs":
            bool(all(c["mixed_order_4rung"]["within_band"]
                     and c["mixed_order_4rung"]["monotone"]
                     for v in results.values() for c in v["cells"].values())),
        "F7_all_cells_isolated_spatial_order_in_band_all_configs":
            bool(all(c["isolated_spatial_order"]["within_band"]
                     and c["isolated_spatial_order"]["monotone"]
                     for v in results.values() for c in v["cells"].values())),
        "F8_determinism_bitwise":
            bool(control["determinism"]["final_psi_bitwise_equal"]),
    }
    triggered = [k for k, v in checks.items() if not v]
    report["falsifier"] = {
        "statement": (
            "The multiplicity/order finding is FALSIFIED if, at these pins and under the "
            "pre-registered transfer configurations, (a) any pin does not resolve; (b) the "
            "published 4-rung orders are not reproduced bitwise (<1e-12) or the prior femlf "
            "order is not reproduced; (c) an outer Dirichlet wall is not tail-clean "
            "(r0+t_end+4sigma < r_max and outer tail < 1e-9); (d) lffd/cnfd do not share the "
            "identical FD operator; (e) the FEM/FD grid-Nyquist ratio leaves 3 (tol 1e-12) or "
            "the smooth-mode relative-difference order leaves [1.7, 2.3] at either r_max=30 "
            "or r_max=40; (f) any of the four cells leaves the |p-2|<=0.3 band or loses "
            "monotonicity in mixed order, or (g) in dt->0 isolated spatial order, in any "
            "configuration; or (h) a rerun is not bitwise deterministic."),
        "checks": checks,
        "triggered": triggered,
        "overall": "falsifier_not_triggered" if not triggered else "falsifier_triggered",
    }

    # headline transfer summary
    summary = {}
    for cid, v in results.items():
        summary[cid] = {cell: {"mixed": v["cells"][cell]["mixed_order_4rung"]["fit_order"],
                               "isolated": v["cells"][cell]["isolated_spatial_order"]["spatial_order_dt0"]}
                        for cell in CELLS}
    report["transfer_summary"] = summary
    report["runtime_seconds"] = round(time.time() - t0, 3)
    report["finished_at"] = now()
    report["non_claims"] = [
        "no gate verdict, no node status change, no validation_status=passed",
        "no theorem or physics result",
        "flat-space test-field calibration sub-case only; not an instance of AF-WCC-SCALAR-SPH",
        "no canonical or published file was modified",
        "the transfer harness re-uses the pinned operator helpers; it tests configuration "
        "transfer, not implementation independence (that axis belongs to workers 046/055)",
    ]

    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    print("== W051-N0-SCHEME-AXES-03 transfer run ==")
    print("pins ok:", pins_ok)
    print("controls:", json.dumps({k: v for k, v in control.items()
                                   if k != "mixed_orders"}, indent=1, sort_keys=True))
    print("operator checks:",
          json.dumps({k: {"lffd_cnfd_share": v["lffd_cnfd_share_FD_operator"],
                          "nyquist_exact": v["fem_vs_fd"]["nyquist_ratio_exact"],
                          "smooth_order": v["fem_vs_fd"]["order_smooth_mode1"]}
                      for k, v in report["operator_checks"].items()}, indent=1))
    print("transfer summary (mixed | isolated):")
    for cid, cells in summary.items():
        print(f"  {cid}: " + "  ".join(
            f"{c}={cells[c]['mixed']:.6f}|{cells[c]['isolated']:.6f}" for c in CELLS))
    print("falsifier:", report["falsifier"]["overall"], "triggered:", triggered)
    print("runtime_seconds:", report["runtime_seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
