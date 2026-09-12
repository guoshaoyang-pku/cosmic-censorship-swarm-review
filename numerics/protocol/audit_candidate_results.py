#!/usr/bin/env python3
"""Apply the N0 protocol to the candidate's own published results (read-only).

Produces two ``n0-convergence-report/v1`` reports derived from
``numerics/results/flat_wave_convergence.json`` (candidate:
``numerics/tests/flat_wave.py``) and audits them with the reference tool:

  report_candidate_standing.json  study[0]: single mode, order 2, t_end = 0.5
  report_candidate_pulse.json     study[1]: pulse,     order 2, t_end = 8.0

Expected, and the point of the exercise:

  * the standing report FAILS C2/C4/C6 — t_end = 0.5 is the mode turning point,
    so the run is rejected as order evidence (the documented false negative);
  * the pulse report passes order/stability/residual/uncertainty but FAILS C7 —
    the candidate's ``np.gradient`` energy diagnostic is O(h^2) and its finest
    drift 9.4e-06 (standing) / 2.3e-04 (pulse) is above the 1e-6 budget.

Nothing here edits the candidate; no gate verdict is claimed.

Usage: python3 numerics/protocol/audit_candidate_results.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = REPO_ROOT / "numerics" / "results" / "flat_wave_convergence.json"
CANDIDATE = REPO_ROOT / "numerics" / "tests" / "flat_wave.py"
OUT_DIR = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def uncertainty(rows, key="linf"):
    hs = np.array([r["dr"] for r in rows], dtype=float)
    es = np.array([r[key] for r in rows], dtype=float)
    x, y = np.log(hs), np.log(es)
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    se = math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) / float(np.sum((x - x.mean()) ** 2)))
    pairs = [math.log(rows[i][key] / rows[i + 1][key]) /
             math.log(rows[i]["dr"] / rows[i + 1]["dr"]) for i in range(len(rows) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0
    return {"fit_order": float(slope), "standard_error": float(se),
            "pair_spread_half_range": float(half)}


def richardson_from_states(fine, mid, coarse):
    d1 = float(np.max(np.abs(mid[::2] - coarse)))
    d2 = float(np.max(np.abs(fine[::2] - mid)))
    return math.log(d1 / d2) / math.log(2.0)


def build_standing(fw, study, provenance):
    t_end = float(study["t_end"])
    rows = [{"dr": 1.0 / r["n"], "linf": r["linf_error"], "l2": r["l2_error"],
             "n": r["n"], "drift": r["energy_drift"]} for r in study["rows"]]
    # truncation residual of the central stencil at the study's own time
    modes = ((2, 1.0),)
    res = []
    for n in (64, 128, 256, 512):
        h = 1.0 / n
        r = np.linspace(0.0, 1.0, n + 1)
        v = fw.standing_v(r, t_end, 1.0, modes)
        v[0] = v[-1] = 0.0
        got = fw.d2(v, h, 2)
        k = 2.0 * math.pi
        want = -k ** 2 * v  # v_tt = -k^2 v for a single mode
        res.append(float(np.max(np.abs((want - got)[2:-1]))))
    res_orders = [math.log(a / b) / math.log(2.0) for a, b in zip(res, res[1:])]
    states = []
    for n in (256, 512, 1024):
        h, r, v0, w0 = fw._case_setup(n, "standing", 1.0, t_end, 12.0, 2.0, modes)
        states.append(fw.integrate(v0, w0, h, t_end, 0.25, 2)["v"])
    return {
        "schema": "n0-convergence-report/v1", "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "scheme_id": f"candidate_flat_wave_standing_t{t_end}",
        "implementation": "numerics/tests/flat_wave.py", "script_sha256": provenance,
        "implementation_sha256_now": sha256_file(CANDIDATE),
        "declared_order": 2.0, "cfl": float(study.get("cfl", 0.25)),
        "exact_family": "single_mode_standing",
        "measurement_times": [t_end],
        "resolutions": [r["n"] for r in rows],
        "linf_errors": [r["linf"] for r in rows], "l2_errors": [r["l2"] for r in rows],
        "residual_orders": res_orders,
        "richardson_order": richardson_from_states(states[2], states[1], states[0]),
        "energy_drift": [r["drift"] for r in rows],
        "energy_diagnostic": "results-file drift series (revision 0d1c24f8)",
        "energy_functional": {"name": "results_file_drift_series", "structural_class": "convergent",
                              "solver_tolerance": None,
                              "definition": "as recorded in numerics/results/flat_wave_convergence.json"},
        "order_uncertainty": uncertainty(rows),
        "stable": True,
        "non_degeneracy": {"single_mode": True, "times": [t_end],
                           "note": ("single generic time; per V2 a single-mode study needs >=3 times "
                                    "for standalone order certification, so this is supporting evidence")},
        "integrator": "RK4", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def build_pulse(fw, study, provenance):
    t_end = float(study["t_end"])
    rows = [{"dr": 40.0 / r["n"], "linf": r["linf_error"], "l2": r["l2_error"],
             "n": r["n"], "drift": r["energy_drift"]} for r in study["rows"]]
    # truncation residual on the exact pulse at a generic time before the walls
    t_star, eps = 6.0, 1e-4
    res = []
    for n in (64, 128, 256, 512):
        dr = 40.0 / n
        r = np.linspace(0.0, 40.0, n + 1)
        v = fw.pulse_v(r, t_star)
        v[0] = v[-1] = 0.0
        got = fw.d2(v, dr, 2)
        vtt = (fw.pulse_v(r, t_star + eps) - 2.0 * fw.pulse_v(r, t_star)
               + fw.pulse_v(r, t_star - eps)) / eps ** 2
        res.append(float(np.max(np.abs((vtt - got)[2:-1]))))
    res_orders = [math.log(a / b) / math.log(2.0) for a, b in zip(res, res[1:])]
    states = []
    for n in (256, 512, 1024):
        h, r, v0, w0 = fw._case_setup(n, "pulse", 40.0, t_end, 12.0, 2.0, ((2, 1.0),))
        states.append(fw.integrate(v0, w0, h, t_end, 0.25, 2)["v"])
    return {
        "schema": "n0-convergence-report/v1", "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "scheme_id": f"candidate_flat_wave_pulse_t{t_end}",
        "implementation": "numerics/tests/flat_wave.py", "script_sha256": provenance,
        "implementation_sha256_now": sha256_file(CANDIDATE),
        "declared_order": 2.0, "cfl": float(study.get("cfl", 0.25)),
        "exact_family": "pulse_mms",
        "measurement_times": [t_end],
        "resolutions": [r["n"] for r in rows],
        "linf_errors": [r["linf"] for r in rows], "l2_errors": [r["l2"] for r in rows],
        "residual_orders": res_orders,
        "richardson_order": richardson_from_states(states[2], states[1], states[0]),
        "energy_drift": [r["drift"] for r in rows],
        "energy_diagnostic": "results-file drift series (revision 0d1c24f8)",
        "energy_functional": {"name": "results_file_drift_series", "structural_class": "convergent",
                              "solver_tolerance": None,
                              "definition": "as recorded in numerics/results/flat_wave_convergence.json"},
        "order_uncertainty": uncertainty(rows),
        "stable": True,
        "non_degeneracy": {"single_mode": False, "times": [t_end],
                           "note": "broadband pulse, no mode turning point"},
        "integrator": "RK4", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def main():
    sys.path.insert(0, str(REPO_ROOT / "numerics"))
    import tests.flat_wave as fw  # type: ignore
    sys.path.insert(0, str(OUT_DIR))
    from audit_convergence_report import audit  # type: ignore

    doc = json.loads(RESULTS.read_text())
    standing = next(s for s in doc["studies"] if s["family"] == "standing" and s["order_scheme"] == 2)
    pulse = next(s for s in doc["studies"] if s["family"] == "pulse")
    provenance = doc.get("provenance", {}).get("script_sha256", "")
    now_hash = sha256_file(CANDIDATE)
    summary = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "candidate_sha256_now": now_hash,
               "results_sha256": sha256_file(RESULTS),
               "results_provenance_script_sha256": provenance,
               "revision_note": (
                   "The results file records the generating script hash. If it differs from the "
                   "on-disk script, C8 provenance fails by design: the published results cannot be "
                   "attributed to the current script and must be re-pinned."),
               "reports": {}}
    for name, report in (("standing", build_standing(fw, standing, provenance)),
                         ("pulse", build_pulse(fw, pulse, provenance))):
        path = OUT_DIR / f"report_candidate_{name}.json"
        path.write_text(json.dumps(report, indent=2, sort_keys=True))
        result = audit(report, REPO_ROOT)
        summary["reports"][name] = {"path": str(path.relative_to(REPO_ROOT)),
                                    "verdict": result["verdict"],
                                    "failed_checks": result["failed_checks"],
                                    "checks": {c["id"]: c["pass"] for c in result["checks"]}}
        print(f"candidate[{name}]: {result['verdict']} failed={result['failed_checks']}")
    (OUT_DIR / "candidate_audit_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
