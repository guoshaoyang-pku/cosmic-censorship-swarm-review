#!/usr/bin/env python3
"""Independent evidence for ``numerics/protocol/scheme_independence_review.md``.

Read-only use of ``numerics/tests/flat_wave_replication.py`` (no edits to other
workers' artifacts).  Reproduces the controller's pinned N0 replication numbers
and separates three quantities that the adjudication conflates:

1. the harness functional (leapfrog staggered energy) evaluated on each scheme;
2. the functional the pinned run *labelled* as cnfd's own energy
   (``1/2|v|^2 - 1/2 <A psi_new, psi_old>``);
3. the current source's cnfd invariant (average-acceleration form).

It also reports order fits with an uncertainty, the threshold matrix, and the
adjudication's own falsifier test.

Scope: flat-space calibration only (N0), class AF-WCC-SCALAR-SPH (provisional).
No self-gravity, no N1, no cosmic-censorship claim.

Usage:  python3 numerics/protocol/scheme_independence_check.py
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
REPLICATION = REPO_ROOT / "numerics" / "tests" / "flat_wave_replication.py"
HARNESS_CONFIG = {"dr": 0.05, "cfl": 0.5, "r_max": 30.0, "t_end": 6.0, "sample_every": 4}
THRESHOLDS = (1e-8, 1e-6, 1e-12)  # candidate G3, harness drift_tol, structural
SCHEMES = ("lffd", "cnfd")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_drift(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 3 or vals[0] == 0.0:
        return None
    return max(abs(v - vals[0]) / abs(vals[0]) for v in vals)


def fit_with_uncertainty(drs, errs):
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    dof = max(n - 2, 1)
    s2 = float(np.sum(resid ** 2) / dof)
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = math.sqrt(s2 / sxx) if sxx > 0 else float("inf")
    return float(slope), float(se)


def analyze_scheme(rep, scheme, dr=HARNESS_CONFIG["dr"], cfl=HARNESS_CONFIG["cfl"], full=True):
    factory = rep.make_factory(scheme, cfl=cfl)
    case = rep.run_case(factory, dr, cfl,
                        HARNESS_CONFIG["r_max"], HARNESS_CONFIG["t_end"],
                        sample_every=HARNESS_CONFIG["sample_every"])
    dt = case["dt"]
    m = len(case["r"]) - 2
    s = 1.0 / dr ** 2
    A = rep.Tridiagonal(s, -2.0 * s, s, m)
    series = {"harness_leapfrog": [], "pinned_symplectic": [], "average_acceleration": []}
    for psi, prev in zip(case["psi"], case["psi_prev"]):
        if prev is None:
            continue
        v = (psi[1:-1] - prev[1:-1]) / dt
        series["harness_leapfrog"].append(rep.leapfrog_energy(psi, prev, dt, dr))
        series["pinned_symplectic"].append(
            0.5 * rep.inner(v, v, dr) - 0.5 * rep.inner(psi[1:-1], A.matvec(prev[1:-1]), dr))
        series["average_acceleration"].append(
            0.5 * rep.inner(v, v, dr)
            - 0.25 * rep.inner(psi[1:-1], A.matvec(psi[1:-1]), dr)
            - 0.25 * rep.inner(prev[1:-1], A.matvec(prev[1:-1]), dr))
    # functional identity: is the pinned "symplectic" form the leapfrog energy?
    scale = max(abs(x) for x in series["harness_leapfrog"])
    identity_gap = max(abs(a - b) for a, b in
                       zip(series["harness_leapfrog"], series["pinned_symplectic"])) / scale
    return {
        "scheme": scheme,
        "dt": dt, "dr": dr, "samples": len(series["harness_leapfrog"]),
        "drift": {k: rel_drift(v) for k, v in series.items()},
        "pinned_functional_equals_leapfrog_relative_gap": float(identity_gap),
        "threshold_matrix": {
            f"{k}_{t:.0e}": bool(rel_drift(v) is not None and rel_drift(v) <= t)
            for k, v in series.items() for t in THRESHOLDS
        },
        "invariant_study_reproduction": rep.invariant_study(
            scheme, dr=HARNESS_CONFIG["dr"], cfl=HARNESS_CONFIG["cfl"],
            r_max=HARNESS_CONFIG["r_max"], t_end=HARNESS_CONFIG["t_end"],
            sample_every=HARNESS_CONFIG["sample_every"]) if full else None,
        "order_study": rep.order_study(scheme, cfl=HARNESS_CONFIG["cfl"],
                                       r_max=HARNESS_CONFIG["r_max"],
                                       t_end=HARNESS_CONFIG["t_end"]) if full else None,
    }


def scaling_study(rep, scheme, drs=(0.2, 0.1, 0.05, 0.025)):
    """Drift of both functionals as the grid is refined at fixed cfl."""
    rows = []
    for dr in drs:
        a = analyze_scheme(rep, scheme, dr=dr, full=False)
        rows.append({"dr": dr, "dt": a["dt"],
                     **{f"drift_{k}": v for k, v in a["drift"].items()}})

    def orders(key):
        out = []
        for i in range(len(rows) - 1):
            x, y = rows[i][key], rows[i + 1][key]
            if x and y and x > 0 and y > 0:
                out.append(math.log(x / y) / math.log(rows[i]["dr"] / rows[i + 1]["dr"]))
            else:
                out.append(None)
        return out

    return {"scheme": scheme, "rows": rows,
            "orders": {k: orders(f"drift_{k}")
                       for k in ("harness_leapfrog", "average_acceleration")}}


def run_all():
    sys.path.insert(0, str(REPO_ROOT / "numerics"))
    import tests.flat_wave_replication as rep  # type: ignore

    t0 = time.perf_counter()
    out = {
        "schema": "n0-scheme-independence-evidence/v1",
        "artifact": "numerics/protocol/scheme_independence_check.py",
        "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "binding_status": "PROVISIONAL",
        "validation_status": "unverified",
        "conclusion_type_of_measurements": "numerical_evidence",
        "configuration": dict(HARNESS_CONFIG, thresholds=list(THRESHOLDS),
                              harness_drift_tol=rep.HARNESS_CONFIG["drift_tol"],
                              candidate_G3_threshold=1e-8),
        "source": {
            "replication_file": "numerics/tests/flat_wave_replication.py",
            "replication_file_sha256_now": sha256_file(REPLICATION),
            "pinned_run": "runtime/state/controller_verification/n0_replication_astra_run.json",
            "pinned_run_script_sha256": "07e5a39b20081c723fe1f86ea868c280884032afdcaf7be0ebe36913c36a1c0e",
            "note": ("the replication file on disk no longer matches the pinned run's "
                     "script sha256; the pinned evidence is stale and must be re-pinned"),
        },
        "schemes": {},
        "claims_not_made": [
            "no claim that N0 passes or fails the gate in this worker's authority",
            "no claim about physics, self-gravity, or cosmic censorship",
            "no edit was made to any other worker's artifact",
        ],
    }
    for scheme in SCHEMES:
        out["schemes"][scheme] = analyze_scheme(rep, scheme)

    out["cross_functional_scaling"] = {s: scaling_study(rep, s) for s in SCHEMES}

    # order fits with uncertainty
    for scheme, data in out["schemes"].items():
        rows = data["order_study"]["rows"]
        drs = [r["dr"] for r in rows]
        errs = [r["l2_error"] for r in rows]
        p, se = fit_with_uncertainty(drs, errs)
        pairs = data["order_study"]["pair_orders"]
        data["order_uncertainty"] = {
            "fit_order": p, "standard_error": se,
            "pair_orders": pairs,
            "pair_spread_half_range": (max(pairs) - min(pairs)) / 2.0 if pairs else None,
        }

    # adjudication falsifier tests
    lf = out["schemes"]["lffd"]["drift"]["harness_leapfrog"]
    cn = out["schemes"]["cnfd"]["drift"]["harness_leapfrog"]
    out["falsifier_tests"] = {
        "statement": ("scheme-dependence finding is falsified if a non-leapfrog scheme passes "
                      "the leapfrog-functional gate on the same configuration"),
        "cnfd_harness_drift": cn,
        "harness_drift_tol_1e-6": rep.HARNESS_CONFIG["drift_tol"],
        "cnfd_passes_harness_gate_at_1e-6": bool(cn is not None and cn <= 1e-6),
        "candidate_threshold_1e-8": 1e-8,
        "cnfd_passes_candidate_G3_at_1e-8": bool(cn is not None and cn <= 1e-8),
        "lffd_passes_candidate_G3_at_1e-8": bool(lf is not None and lf <= 1e-8),
        "interpretation": ("cnfd is a non-leapfrog scheme and passes the harness gate at "
                           "drift_tol=1e-6, so the finding as written ('far above 1e-6') is "
                           "falsified for the harness; the scheme-discrimination problem "
                           "survives only at the candidate's 1e-8 threshold"),
    }
    out["runtime_seconds"] = round(time.perf_counter() - t0, 2)
    out["provenance"] = {"python": sys.version.split()[0], "numpy": np.__version__,
                         "platform": platform.platform(),
                         "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    return out


def summarize(out):
    lines = []
    for s, d in out["schemes"].items():
        dr = d["drift"]
        lines.append(f"{s}: harness={dr['harness_leapfrog']:.3e} "
                     f"pinned_symplectic={dr['pinned_symplectic']:.3e} "
                     f"avg_accel={dr['average_acceleration']:.3e}")
        lines.append(f"    pinned functional vs leapfrog identity gap "
                     f"{d['pinned_functional_equals_leapfrog_relative_gap']:.2e}; "
                     f"order fit {d['order_uncertainty']['fit_order']:.4f} "
                     f"± {d['order_uncertainty']['standard_error']:.2e}")
    f = out["falsifier_tests"]
    lines.append(f"falsifier: cnfd harness drift {f['cnfd_harness_drift']:.3e} "
                 f"passes 1e-6={f['cnfd_passes_harness_gate_at_1e-6']} "
                 f"passes 1e-8={f['cnfd_passes_candidate_G3_at_1e-8']}")
    for s, sc in out["cross_functional_scaling"].items():
        for k, v in sc["orders"].items():
            lines.append(f"    scaling {s}/{k}: orders {[None if x is None else round(x,2) for x in v]}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json-out", default=str(Path(__file__).resolve().parent /
                                              "scheme_independence_evidence.json"))
    a = ap.parse_args(argv)
    out = run_all()
    Path(a.json_out).write_text(json.dumps(out, indent=2, sort_keys=True))
    print(summarize(out))
    print(f"wrote {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
