#!/usr/bin/env python3
"""Build ``n0-convergence-report/v1`` reports for the two replication schemes.

Read-only use of ``numerics/tests/flat_wave_replication.py``.  Produces
``report_lffd.json`` and ``report_cnfd.json`` so the reference audit tool can be
run end-to-end on the real independent schemes:

    python3 numerics/protocol/build_gate_reports.py
    python3 numerics/protocol/audit_convergence_report.py --root . numerics/protocol/report_lffd.json
    python3 numerics/protocol/audit_convergence_report.py --root . numerics/protocol/report_cnfd.json
    python3 numerics/protocol/audit_convergence_report.py --compare numerics/protocol/report_lffd.json numerics/protocol/report_cnfd.json

Each scheme reports its **own** structural invariant (R1/R2), so the reports are
expected to pass C0-C9 without either scheme being asked to conserve the other's
functional.  Scope: flat-space calibration only; no gate verdict is claimed.
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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPLICATION = REPO_ROOT / "numerics" / "tests" / "flat_wave_replication.py"
OUT_DIR = Path(__file__).resolve().parent
DRS = (0.2, 0.1, 0.05)
CFL = 0.5
R_MAX = 30.0
T_END = 6.0
T_RESIDUAL = 4.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_drift(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 3 or vals[0] == 0.0:
        return None
    return max(abs(v - vals[0]) / abs(vals[0]) for v in vals)


def build(rep, scheme: str) -> dict:
    factory = rep.make_factory(scheme, cfl=CFL)
    pulse = rep.PulseExact()
    rows, states, drift_series = [], [], []
    for dr in DRS:
        case = rep.run_case(factory, dr, CFL, R_MAX, T_END, sample_every=1)
        exact = pulse.psi(case["r"], case["t"][-1])
        err = case["psi"][-1][1:-1] - exact[1:-1]
        m = len(case["r"]) - 2
        s = 1.0 / dr ** 2
        A = rep.Tridiagonal(s, -2.0 * s, s, m)
        series = []
        for psi, prev in zip(case["psi"], case["psi_prev"]):
            if prev is None:
                continue
            if scheme == "lffd":
                series.append(rep.leapfrog_energy(psi, prev, case["dt"], dr))
            else:
                v = (psi[1:-1] - prev[1:-1]) / case["dt"]
                series.append(
                    0.5 * rep.inner(v, v, dr)
                    - 0.25 * rep.inner(psi[1:-1], A.matvec(psi[1:-1]), dr)
                    - 0.25 * rep.inner(prev[1:-1], A.matvec(prev[1:-1]), dr))
        rows.append({"dr": float(dr), "dt": float(case["dt"]), "n": int(round(R_MAX / dr)),
                     "linf": float(np.max(np.abs(err))),
                     "l2": float(math.sqrt(float(np.sum(err ** 2)) * dr)),
                     "stable": bool(np.all(np.isfinite(case["psi"][-1])))
                     and float(np.max(np.abs(case["psi"][-1]))) < 1e6})
        states.append(case["psi"][-1])
        drift_series.append(relative_drift(series))

    # truncation residual of the 3-point stencil on the exact pulse
    res = []
    for dr in DRS:
        r = rep.grid(R_MAX, dr)
        psi = pulse.psi(r, T_RESIDUAL)
        psi[0] = psi[-1] = 0.0
        d2 = np.zeros_like(psi)
        d2[1:-1] = (psi[:-2] - 2.0 * psi[1:-1] + psi[2:]) / dr ** 2
        vtt = pulse.psi_tt(r, T_RESIDUAL)
        res.append(float(np.max(np.abs(vtt[1:-1] - d2[1:-1]))))
    res_orders = [math.log(a / b) / math.log(2.0) for a, b in zip(res, res[1:])]

    # Richardson self-convergence on the common mid grid
    fine, mid, coarse = states[-1], states[-2], states[-3]
    d1 = float(np.max(np.abs(mid[::2] - coarse)))
    d2v = float(np.max(np.abs(fine[::2] - mid)))
    p_rich = math.log(d1 / d2v) / math.log(2.0)

    hs = np.array([r["dr"] for r in rows])
    es = np.array([r["linf"] for r in rows])
    x, y = np.log(hs), np.log(es)
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    se = float(math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) /
                         float(np.sum((x - x.mean()) ** 2))))
    pairs = [math.log(rows[i]["linf"] / rows[i + 1]["linf"]) /
             math.log(rows[i]["dr"] / rows[i + 1]["dr"]) for i in range(len(rows) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0

    functional = ({"name": "leapfrog_staggered_energy",
                   "definition": "h/2 sum ((psi-prev)/dt)^2 + h/2 sum Dpsi Dprev",
                   "quadrature": "exact differences, Dirichlet ends",
                   "structural_class": "exact_discrete", "solver_tolerance": 0.0}
                  if scheme == "lffd" else
                  {"name": "average_acceleration_invariant",
                   "definition": "1/2|V|^2 - 1/4<A psi_new,psi_new> - 1/4<A psi_old,psi_old>",
                   "quadrature": "exact differences, Dirichlet ends",
                   "structural_class": "exact_discrete", "solver_tolerance": 0.0})
    return {
        "schema": "n0-convergence-report/v1",
        "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "scheme_id": f"replication_{scheme}",
        "implementation": "numerics/tests/flat_wave_replication.py",
        "script_sha256": sha256_file(REPLICATION),
        "declared_order": 2.0, "cfl": CFL,
        "exact_family": "pulse_mms",
        "measurement_times": [T_END],
        "resolutions": [r["n"] for r in rows],
        "linf_errors": [r["linf"] for r in rows],
        "l2_errors": [r["l2"] for r in rows],
        "residual_orders": res_orders,
        "richardson_order": p_rich,
        "energy_drift": drift_series,
        "energy_diagnostic": functional["name"],
        "energy_functional": functional,
        "order_uncertainty": {"fit_order": float(slope), "standard_error": se,
                              "pair_spread_half_range": float(half)},
        "fitted_order": float(slope),
        "stable": bool(all(r["stable"] for r in rows)),
        "non_degeneracy": {"single_mode": False, "times": [T_END],
                           "note": "broadband pulse, no mode turning point"},
        "integrator": "leapfrog" if scheme == "lffd" else "implicit-average-acceleration",
        "rows": rows,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main():
    sys.path.insert(0, str(REPO_ROOT / "numerics"))
    import tests.flat_wave_replication as rep  # type: ignore
    sys.path.insert(0, str(OUT_DIR))
    from audit_convergence_report import audit, compare_reports  # type: ignore

    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "python": sys.version.split()[0], "numpy": np.__version__,
               "platform": platform.platform(), "reports": {}}
    for scheme in ("lffd", "cnfd"):
        report = build(rep, scheme)
        path = OUT_DIR / f"report_{scheme}.json"
        path.write_text(json.dumps(report, indent=2, sort_keys=True))
        result = audit(report, REPO_ROOT)
        summary["reports"][scheme] = {
            "path": str(path.relative_to(REPO_ROOT)),
            "verdict": result["verdict"], "failed_checks": result["failed_checks"],
            "order": report["order_uncertainty"],
            "drift_finest": report["energy_drift"][-1],
            "functional": report["energy_functional"]["name"],
        }
        print(f"{scheme}: {result['verdict']} {result['failed_checks']} "
              f"p={report['order_uncertainty']['fit_order']:.4f} "
              f"drift={report['energy_drift'][-1]:.2e}")
    a = json.loads((OUT_DIR / "report_lffd.json").read_text())
    b = json.loads((OUT_DIR / "report_cnfd.json").read_text())
    summary["comparison"] = compare_reports(a, b)
    (OUT_DIR / "gate_reports_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print("compare:", json.dumps(summary["comparison"]))
    return 0 if all(v["verdict"] == "PASS" for v in summary["reports"].values()) \
        and summary["comparison"]["agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
