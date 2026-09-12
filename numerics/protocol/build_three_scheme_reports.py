#!/usr/bin/env python3
"""Three-scheme R1-R5 conformance reports at four rungs (worker-14, N0/G-NUM).

Closes the residue named in the independent G-NUM protocol review
(``reviews/G-NUM-protocol-review.json``, finding C4: "cnfem reports
solver_tolerance_reported=null") and the canonical protocol rev3 requirement of
``>= 4`` rungs for an order-certification claim.

What this does
--------------
Builds an ``n0-convergence-report/v1`` record for **each** of the three
replication schemes (lffd, cnfd, cnfem) at ``dr = [0.2, 0.1, 0.05, 0.025]``:

* R1: a declared ``energy_functional`` per scheme, including a non-null
  ``solver_tolerance`` (all three are direct tridiagonal solves, so 0.0 with the
  method named -- the field is declared, not omitted);
* R2: the drift series is the scheme's **own** structural invariant, sampled
  through the frozen module's own ``own_energy()`` (no reimplementation, so
  scheme A's functional is never used to judge scheme B, R4);
* R5/R5a: ``order_uncertainty`` carries ``fit_order``, ``standard_error`` and
  ``pair_spread_half_range``; the report also carries an explicit ``delta`` and
  names the fitted error norm (L-infinity, the audit's C3/C4 norm).

It then runs the reference audit (C0-C9) on each report and the R5 pairwise
agreement rule on every pair. Determinism is checked by rebuilding every report
a second time and comparing the payloads with ``generated_at`` removed.

Guards
------
* The frozen replication module ``numerics/tests/flat_wave_replication.py`` is
  imported **read-only** and hash-guarded to the controller-verified revision
  ``8ade1cdc...``; a mismatch refuses to run (exit 2), so this evidence can
  never silently attach to a different revision.
* Flat space only. No self-gravitating solver, no N1, no
  ``numerics/spherical_solver/``; ``numerics_lock`` stays LOCKED.
* No gate verdict, no node completion. Worker-level evidence for G-NUM only.

Outputs
-------
``report_lffd_4rung.json``, ``report_cnfd_4rung.json``, ``report_cnfem_4rung.json``,
``three_scheme_r1r5_summary.json`` (all under ``numerics/protocol/``).

Usage:  python3 numerics/protocol/build_three_scheme_reports.py
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
OUT_DIR = Path(__file__).resolve().parent
REPLICATION = REPO_ROOT / "numerics" / "tests" / "flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
CANONICAL_PROTOCOL = REPO_ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
DRS = (0.2, 0.1, 0.05, 0.025)
CFL = 0.5
R_MAX = 30.0
T_END = 6.0
T_RESIDUAL = 4.0
SCHEMES = ("lffd", "cnfd", "cnfem")

FUNCTIONALS = {
    "lffd": {
        "name": "leapfrog_staggered_energy",
        "definition": "h/2 sum ((psi-prev)/dt)^2 + h/2 sum Dpsi Dprev",
        "quadrature": "exact differences, Dirichlet ends",
        "structural_class": "exact_discrete",
        "solver_tolerance": 0.0,
        "solver_tolerance_basis": "explicit scheme, no linear solve",
    },
    "cnfd": {
        "name": "average_acceleration_invariant",
        "definition": "1/2|V|^2 - 1/4<A psi_new,psi_new> - 1/4<A psi_old,psi_old>",
        "quadrature": "exact differences, Dirichlet ends",
        "structural_class": "exact_discrete",
        "solver_tolerance": 0.0,
        "solver_tolerance_basis": "direct tridiagonal (Thomas) solve; no iterative tolerance",
    },
    "cnfem": {
        "name": "p1_fem_average_acceleration_invariant",
        "definition": ("1/2 V^T M V + 1/4 psi_new^T K psi_new + 1/4 psi_old^T K psi_old, "
                       "V = (psi_new - psi_old)/dt"),
        "quadrature": "P1 consistent mass and stiffness, Dirichlet ends",
        "structural_class": "exact_discrete",
        "solver_tolerance": 0.0,
        "solver_tolerance_basis": "direct tridiagonal (Thomas) solve; no iterative tolerance",
    },
}


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


def run_scheme(rep, scheme: str, dr: float):
    """Integrate one scheme, sampling its own structural invariant every step."""
    r = rep.grid(R_MAX, dr)
    dt = CFL * dr
    factory = rep.make_factory(scheme, cfl=CFL)
    solver = factory(r, dt)
    energies = []
    step_cap = int(math.ceil(T_END / dt)) * 10 + 100
    steps = 0
    while solver.t < T_END - 1e-12:
        solver.step()
        steps += 1
        if steps > step_cap:
            raise RuntimeError(f"step cap exceeded scheme={scheme} dr={dr}")
        e = solver.own_energy()
        if e is not None:
            energies.append(float(e))
    pulse = rep.PulseExact()
    exact = pulse.psi(r, solver.t)
    err = solver.psi[1:-1] - exact[1:-1]
    return {
        "dr": float(dr), "dt": float(dt), "n": int(round(R_MAX / dr)), "steps": steps,
        "final_t": float(solver.t),
        "linf": float(np.max(np.abs(err))),
        "l2": float(math.sqrt(float(np.sum(err ** 2)) * dr)),
        "drift": relative_drift(energies),
        "stable": bool(np.all(np.isfinite(solver.psi)))
        and float(np.max(np.abs(solver.psi))) < 1e6,
        "state": solver.psi.copy(),
    }


def build(rep, scheme: str) -> dict:
    rows = [run_scheme(rep, scheme, dr) for dr in DRS]
    states = [row.pop("state") for row in rows]

    # truncation residual of the shared 3-point spatial operator on the exact pulse
    pulse = rep.PulseExact()
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

    # Richardson self-convergence on the common coarsest-pair grid
    fine, mid, coarse = states[-1], states[-2], states[-3]
    d1 = float(np.max(np.abs(mid[::2] - coarse)))
    d2v = float(np.max(np.abs(fine[::2] - mid)))
    p_rich = math.log(d1 / d2v) / math.log(2.0)

    hs = np.array([row["dr"] for row in rows])
    es = np.array([row["linf"] for row in rows])
    x, y = np.log(hs), np.log(es)
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    se = float(math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) /
                         float(np.sum((x - x.mean()) ** 2))))
    pairs = [math.log(rows[i]["linf"] / rows[i + 1]["linf"]) /
             math.log(rows[i]["dr"] / rows[i + 1]["dr"]) for i in range(len(rows) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0
    delta = max(se, half)

    func = dict(FUNCTIONALS[scheme])
    return {
        "schema": "n0-convergence-report/v1",
        "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "assignment_ref": "astra-numfix-03 (continuation: review finding C4 / R1-R5 matrix)",
        "scheme_id": f"replication_{scheme}",
        "implementation": str(REPLICATION.relative_to(REPO_ROOT)),
        "script_sha256": sha256_file(REPLICATION),
        "declared_order": 2.0, "cfl": CFL,
        "exact_family": "pulse_mms",
        "measurement_times": [T_END],
        "resolutions": [row["n"] for row in rows],
        "linf_errors": [row["linf"] for row in rows],
        "l2_errors": [row["l2"] for row in rows],
        "error_norm_fitted": "L_infinity",
        "rung_count": len(DRS),
        "residual_orders": res_orders,
        "richardson_order": p_rich,
        "energy_drift": [row["drift"] for row in rows],
        "energy_diagnostic": func["name"],
        "energy_functional": func,
        "order_uncertainty": {"fit_order": float(slope), "standard_error": se,
                              "pair_spread_half_range": float(half), "delta": delta,
                              "norm": "L_infinity"},
        "fitted_order": float(slope),
        "delta": delta,
        "stable": bool(all(row["stable"] for row in rows)),
        "non_degeneracy": {"single_mode": False, "times": [T_END],
                           "note": "broadband pulse, no mode turning point"},
        "integrator": {"lffd": "leapfrog", "cnfd": "implicit-average-acceleration",
                       "cnfem": "implicit-average-acceleration"}[scheme],
        "protocol_ref": {"path": str(CANONICAL_PROTOCOL.relative_to(REPO_ROOT)),
                         "sha256": sha256_file(CANONICAL_PROTOCOL),
                         "requires_rungs_order_claim": 4},
        "rows": rows,
    }


def main() -> int:
    got = sha256_file(REPLICATION)
    if got != FROZEN_SHA:
        print(f"REFUSE: frozen replication sha256 {got} != controller-verified {FROZEN_SHA}")
        return 2
    protocol_sha = sha256_file(CANONICAL_PROTOCOL)

    sys.path.insert(0, str(REPO_ROOT / "numerics"))
    import tests.flat_wave_replication as rep  # type: ignore
    sys.path.insert(0, str(OUT_DIR))
    from audit_convergence_report import audit, compare_reports  # type: ignore

    reports = {s: build(rep, s) for s in SCHEMES}
    for r in reports.values():
        r["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # determinism: rebuild and compare payloads with the timestamp removed
    rebuild = {s: build(rep, s) for s in SCHEMES}
    deterministic = all(
        json.dumps({k: v for k, v in reports[s].items() if k != "generated_at"}, sort_keys=True)
        == json.dumps(rebuild[s], sort_keys=True) for s in SCHEMES)

    audits, paths = {}, {}
    for s in SCHEMES:
        path = OUT_DIR / f"report_{s}_4rung.json"
        path.write_text(json.dumps(reports[s], indent=2, sort_keys=True) + "\n")
        paths[s] = path
        audits[s] = audit(reports[s], REPO_ROOT)

    pairs = []
    for i, a in enumerate(SCHEMES):
        for b in SCHEMES[i + 1:]:
            pairs.append(compare_reports(reports[a], reports[b]))

    summary = {
        "artifact": "numerics/protocol/build_three_scheme_reports.py",
        "artifact_sha256": sha256_file(Path(__file__).resolve()),
        "actor": "deepseek-flash-14",
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "assignment_ref": "astra-numfix-03 (continuation: review finding C4 / R1-R5 matrix)",
        "purpose": ("close the independent review residue 'cnfem solver_tolerance_reported=null' "
                    "and produce a homogeneous four-rung R1-R5 report for each replication scheme"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "provenance": {
            "frozen_module": str(REPLICATION.relative_to(REPO_ROOT)),
            "frozen_module_sha256": got,
            "canonical_protocol": str(CANONICAL_PROTOCOL.relative_to(REPO_ROOT)),
            "canonical_protocol_sha256": protocol_sha,
            "python": sys.version.split()[0], "numpy": np.__version__,
            "platform": platform.platform(),
            "seeds": "none: deterministic, no RNG",
        },
        "config": {"dr_values": list(DRS), "cfl": CFL, "r_max": R_MAX, "t_end": T_END,
                   "declared_order": 2.0, "rung_requirement": "canonical rev3: >=4 for order claim",
                   "uncertainty_rule": "R5: delta = max(least-squares SE, pair-spread half-range)",
                   "agreement_rule": "|pA-pB| <= max(0.25, sqrt(dA^2+dB^2))"},
        "deterministic_rebuild": bool(deterministic),
        "reports": {
            s: {
                "path": str(paths[s].relative_to(REPO_ROOT)),
                "sha256": sha256_file(paths[s]),
                "report_scheme": reports[s]["scheme_id"],
                "functional": reports[s]["energy_functional"],
                "order": reports[s]["order_uncertainty"],
                "drift_finest": reports[s]["energy_drift"][-1],
                "rung_count": reports[s]["rung_count"],
                "audit_verdict": audits[s]["verdict"],
                "failed_checks": audits[s]["failed_checks"],
            } for s in SCHEMES
        },
        "pairwise_agreement_R5": pairs,
        "verdict": {
            "all_audits_pass_C0_C9": all(audits[s]["verdict"] == "PASS" for s in SCHEMES),
            "all_pairs_agree_R5": all(p["agree"] for p in pairs),
            "all_have_declared_solver_tolerance": all(
                reports[s]["energy_functional"].get("solver_tolerance") is not None for s in SCHEMES),
            "orders": {s: reports[s]["fitted_order"] for s in SCHEMES},
            "deltas": {s: reports[s]["delta"] for s in SCHEMES},
            "summary": ("three schemes, four rungs each, each judged on its own structural "
                        "invariant; no cross-scheme functional used as a gate"),
        },
        "falsifier": ("a re-run at frozen hash 8ade1cdc that yields any audit FAIL, any R5 pair "
                      "disagreeing, any scheme reporting a null solver_tolerance or non-finite "
                      "delta, a deterministic_rebuild=false, or the frozen-module hash guard firing"),
        "not_claimed": [
            "no G-NUM verdict and no gate self-pass (authority: Astra)",
            "no N0 completion; numerics_lock stays LOCKED, N1 not started",
            "no independent review: this worker may not review its own artifact",
            "no physics/censorship claim; flat-space calibration evidence only",
            "no edit to any other agent's artifact; frozen module imported read-only",
        ],
    }
    out = OUT_DIR / "three_scheme_r1r5_summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"summary": str(out.relative_to(REPO_ROOT)),
                      "sha256": sha256_file(out),
                      "deterministic_rebuild": deterministic,
                      "audits": {s: audits[s]["verdict"] for s in SCHEMES},
                      "orders": summary["verdict"]["orders"],
                      "all_pairs_agree": summary["verdict"]["all_pairs_agree_R5"]}))
    ok = (summary["verdict"]["all_audits_pass_C0_C9"]
          and summary["verdict"]["all_pairs_agree_R5"]
          and deterministic
          and summary["verdict"]["all_have_declared_solver_tolerance"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
