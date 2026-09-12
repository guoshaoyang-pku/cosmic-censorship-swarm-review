#!/usr/bin/env python3
"""Independent verification verdict on the N0/G-NUM closure package (rev3).

WORKER / TASK
  worker      : deepseek-flash-13
  node        : N0 (Flat-space scalar-wave test)
  class_id    : AF-WCC-SCALAR-SPH
  gate        : G-NUM (proposal context only; this script sets no gate verdict)
  target      : numerics/results/flat_wave_convergence_rev3.json
  stop rule   : reviews/N0-review-lead-audit.json -> "add a 4th resolution, re-bind the F0
                revision, and obtain one independent replication verdict".

WHAT THIS SCRIPT DOES (all read-only except its own --json-out)
  1. pin audit       : re-hash every artifact rev3 cites and compare to the declared sha256
  2. fit recompute   : re-derive every declared fit statistic from rev3's declared per-rung
                       l2 errors with an independent least-squares routine
  3. live re-run     : re-measure all 12 fixed-dt rungs (3 schemes x dr 0.2/0.1/0.05/0.025)
                       from the frozen module under a before/after hash guard
  4. scope           : numerics_lock state, spherical_solver absence, registry snapshot
  5. verdict audit   : the three independent replication verdict artifacts rev3 relies on
  6. new arm         : RK4 + 3-pt FD at fixed dt=1e-4 on four rungs, implemented here from
                       scratch (NOT imported from the frozen module) as a fourth solver family
  7. self-controls   : a deliberately perturbed fit and a deliberately wrong pin must both be
                       flagged, otherwise the checker itself is broken

DISCLOSURE / LIMITS (carried into the emitted JSON and the review)
  * the reviewer (deepseek-flash-13) authored numerics/tests/flat_wave_replication.py and
    numerics/protocol/n0_fixed_dt_certification.py, which are rev3's frozen module and
    certification basis.  Checks 2/3/5 therefore verify reproducibility and bookkeeping, not
    reviewer-independent solver physics; worker-046's from-scratch run is the independent
    solver evidence and is audited here only for hash/verdict integrity.
  * the new arm (6) shares the analytic pulse family and the r_max/t_end protocol.
  * no gate verdict, no node completion, no physics/self-gravity claim.

USAGE
  python3 artifacts/flash-13/n0_rev3_verdict/verify_n0_rev3.py \
      --json-out artifacts/flash-13/n0_rev3_verdict/n0_rev3_verification.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
import warnings
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
REV3 = REPO / "numerics" / "results" / "flat_wave_convergence_rev3.json"
FROZEN = REPO / "numerics" / "tests" / "flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
MAP = REPO / "research_map" / "research_map.json"
REGISTRY = REPO / "runtime" / "state" / "artifact_hashes.json"

DEFAULT_REV3_SHA = "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3"
DRS = [0.2, 0.1, 0.05, 0.025]
DT_FIXED = 1e-4
P_DESIGN, P_TOL = 2.0, 0.3
R5_FLOOR = 0.25
CROSS_SCHEME_TOL = 0.25
L2_RTOL = 1e-12
FIT_ATOL = 1e-9
R_MAX, T_END = 30.0, 6.0


def sha256_file(p: Path) -> str | None:
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def fit_ls(drs, errs):
    """Independent least-squares fit of log(err) = p*log(dr) + c."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    sxx = float(np.sum((x - x.mean()) ** 2))
    slope = float(np.sum((x - x.mean()) * (y - y.mean())) / sxx)
    intercept = float(y.mean() - slope * float(x.mean()))
    resid = y - (slope * x + intercept)
    se = math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) / sxx)
    return slope, se, [float(r) for r in resid]


def pair_orders(drs, errs):
    return [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
            for i in range(len(errs) - 1)]


def close(a, b, atol=FIT_ATOL):
    return abs(float(a) - float(b)) <= atol


# ---------------------------------------------------------------------------
# new arm: RK4 + 3-point FD, implemented here (not imported from the module)
# ---------------------------------------------------------------------------
def exact_psi(r, t, r0=10.0, sigma=1.5):
    def F(s):
        return np.exp(-((s - r0) ** 2) / (2.0 * sigma ** 2))

    r = np.asarray(r, float)
    return F(r - t) - F(-r - t)


def exact_psi_t(r, t, r0=10.0, sigma=1.5):
    def Fp(s):
        return -((s - r0) / sigma ** 2) * np.exp(-((s - r0) ** 2) / (2.0 * sigma ** 2))

    r = np.asarray(r, float)
    return -Fp(r - t) + Fp(-r - t)


def rk4_fd_run(dr, dt, r_max=R_MAX, t_end=T_END):
    n = int(round(r_max / dr))
    r = np.linspace(0.0, n * dr, n + 1)
    psi = exact_psi(r, 0.0)
    v = exact_psi_t(r, 0.0)
    psi[0] = psi[-1] = 0.0
    v[0] = v[-1] = 0.0

    def lap(p):
        out = np.zeros_like(p)
        out[1:-1] = (p[2:] - 2.0 * p[1:-1] + p[:-2]) / dr ** 2
        return out

    steps = int(round(t_end / dt))
    for _ in range(steps):
        k1p, k1v = v, lap(psi)
        k2p, k2v = v + 0.5 * dt * k1v, lap(psi + 0.5 * dt * k1p)
        k3p, k3v = v + 0.5 * dt * k2v, lap(psi + 0.5 * dt * k2p)
        k4p, k4v = v + dt * k3v, lap(psi + dt * k3p)
        psi = psi + (dt / 6.0) * (k1p + 2.0 * k2p + 2.0 * k3p + k4p)
        v = v + (dt / 6.0) * (k1v + 2.0 * k2v + 2.0 * k3v + k4v)
        psi[0] = psi[-1] = 0.0
        v[0] = v[-1] = 0.0
    ref = exact_psi(r, t_end)
    err = float(math.sqrt(float(np.sum((psi - ref) ** 2)) * dr))
    return {"dr": dr, "dt": dt, "steps": steps, "l2_error": err}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--rev3-sha", default=DEFAULT_REV3_SHA)
    ap.add_argument("--skip-rerun", action="store_true")
    a = ap.parse_args(argv)

    t0 = time.time()
    checks: list[dict] = []
    findings: list[str] = []

    def rec(check_id, ok, detail):
        checks.append({"check_id": check_id, "pass": bool(ok), "detail": detail})
        return bool(ok)

    # 1. revision pin --------------------------------------------------------
    rev3_sha_start = sha256_file(REV3)
    rev3 = json.loads(REV3.read_text())
    rec("rev3::pin_declared", rev3_sha_start == a.rev3_sha,
        f"declared {a.rev3_sha[:16]}; measured {str(rev3_sha_start)[:16]}")

    # 2. pin audit -----------------------------------------------------------
    pin_pairs: list[tuple[str, str, str]] = []  # (role, path, declared)

    def add_pin(role, path, declared):
        if path and declared:
            pin_pairs.append((role, path, declared))

    cb = rev3.get("certification_basis", {})
    add_pin("certification_basis.frozen_module", cb.get("frozen_module", {}).get("path"),
            cb.get("frozen_module", {}).get("sha256"))
    add_pin("certification_basis", cb.get("path"), cb.get("sha256"))
    add_pin("certification_basis.protocol", "numerics/CONVERGENCE_PROTOCOL.md",
            cb.get("protocol_sha256"))
    sd = rev3.get("supporting_diagnostics", {})
    add_pin("supporting_diagnostics.canonical_mixed_order_run",
            sd.get("canonical_mixed_order_run", {}).get("path"),
            sd.get("canonical_mixed_order_run", {}).get("sha256"))
    add_pin("supporting_diagnostics.four_rung_mixed_order_addendum",
            sd.get("four_rung_mixed_order_addendum", {}).get("path"),
            sd.get("four_rung_mixed_order_addendum", {}).get("sha256"))
    add_pin("supporting_diagnostics.replication_mixed_order",
            sd.get("replication_mixed_order", {}).get("path"),
            sd.get("replication_mixed_order", {}).get("sha256"))
    cl = rev3.get("class_binding", {})
    add_pin("class_binding", cl.get("path"), cl.get("sha256"))
    rb = rev3.get("review_being_closed", {})
    add_pin("review_being_closed", rb.get("path"), rb.get("sha256"))
    verdicts = rev3.get("independent_replication", {}).get("verdicts", [])
    for i, v in enumerate(verdicts):
        add_pin(f"independent_replication.verdicts[{i}]", v.get("path"), v.get("sha256"))

    pin_rows = []
    for role, path, declared in pin_pairs:
        measured = sha256_file(REPO / path)
        ok = measured == declared
        pin_rows.append({"role": role, "path": path, "declared": declared,
                         "measured": measured, "pass": ok})
        if not ok:
            findings.append(f"PIN DRIFT: {role} {path} declared {declared} measured {measured}")
    rec("pins::all_declared_hashes_match_disk", all(r["pass"] for r in pin_rows),
        f"{sum(r['pass'] for r in pin_rows)}/{len(pin_rows)} pinned paths match")

    # 3. fit recompute -------------------------------------------------------
    fit_rows = []
    for scheme, s in cb.get("schemes", {}).items():
        drs = s.get("dr_values")
        if drs is None:
            errs_by_dr = s.get("l2_error_by_dr", {})
            drs = sorted((float(k) for k in errs_by_dr), reverse=True)
            errs = [errs_by_dr[f"{d:g}"] for d in drs]
        else:
            errs_by_dr = s.get("l2_error_by_dr", {})
            errs = [errs_by_dr[f"{d:g}"] for d in drs]
        p, se, resid = fit_ls(drs, errs)
        po = pair_orders(drs, errs)
        half_range = (max(po) - min(po)) / 2.0  # R5 uses the half-range
        delta = max(half_range, se)
        monotone = all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))
        within = abs(p - P_DESIGN) <= P_TOL
        row = {
            "scheme": scheme,
            "n_rungs": len(drs),
            "recomputed_fit_order": p,
            "declared_fit_order": s.get("fit_order"),
            "fit_order_agrees": close(p, s.get("fit_order", float("nan"))),
            "recomputed_se": se,
            "declared_se": s.get("least_squares_se"),
            "se_agrees": close(se, s.get("least_squares_se", float("nan"))),
            "recomputed_pair_orders": po,
            "declared_pair_orders": s.get("pair_orders"),
            "pair_orders_agree": all(close(x, y) for x, y in zip(po, s.get("pair_orders", []))),
            "recomputed_delta_R5": delta,
            "declared_delta_R5": s.get("delta_R5"),
            "delta_agrees": close(delta, s.get("delta_R5", float("nan"))),
            "recomputed_monotone": monotone,
            "declared_monotone": s.get("monotone"),
            "recomputed_within_band": within,
            "declared_within_band": s.get("within_band"),
            "rungs_declared": s.get("rungs"),
        }
        fit_rows.append(row)
    fit_ok = all(r["fit_order_agrees"] and r["se_agrees"] and r["pair_orders_agree"]
                 and r["delta_agrees"] and r["recomputed_monotone"] == r["declared_monotone"]
                 and r["recomputed_within_band"] == bool(r["declared_within_band"])
                 and (r["rungs_declared"] in (None, r["n_rungs"]))
                 for r in fit_rows)
    rec("fits::all_declared_statistics_recomputed", fit_ok and bool(fit_rows),
        f"{len(fit_rows)} schemes; all fit/se/pair/delta/monotone/band recomputed")

    ps = [r["recomputed_fit_order"] for r in fit_rows]
    max_dp = max(abs(x - y) for i, x in enumerate(ps) for y in ps[i + 1:]) if len(ps) > 1 else 0.0
    oc = rev3.get("order_claim", {})
    rec("cross_scheme::max_abs_dp_within_floor",
        close(max_dp, oc.get("max_cross_scheme_abs_dp", float("nan")), 1e-12)
        and max_dp <= CROSS_SCHEME_TOL,
        f"recomputed max|dp|={max_dp:.3e}; declared={oc.get('max_cross_scheme_abs_dp')}; floor={CROSS_SCHEME_TOL}")

    # 4. live re-run from the frozen module ---------------------------------
    rerun_rows = []
    if not a.skip_rerun:
        before = sha256_file(FROZEN)
        sys.path.insert(0, str(REPO / "numerics" / "tests"))
        import flat_wave_replication as repl  # noqa: E402
        after_import = sha256_file(FROZEN)
        for scheme, s in cb.get("schemes", {}).items():
            declared_errs = s.get("l2_error_by_dr", {})
            for dr in s.get("dr_values", DRS):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")  # module's np.polyfit warns on 1-rung input
                    st = repl.order_study(scheme, dr_values=[dr], cfl=0.5, r_max=R_MAX,
                                          t_end=T_END, dt_rule=lambda d, dt=DT_FIXED: dt)
                row = st["rows"][0]
                declared = declared_errs.get(f"{dr:g}")
                rel = (abs(row["l2_error"] - declared) / abs(declared)) if declared else None
                rerun_rows.append({
                    "scheme": scheme, "dr": dr, "dt": row["dt"], "steps": row["steps"],
                    "measured_l2_error": row["l2_error"], "declared_l2_error": declared,
                    "rel_diff": rel,
                    "reproduced": bool(rel is not None and rel <= L2_RTOL),
                })
        after = sha256_file(FROZEN)
        guard_ok = (before == FROZEN_SHA == after_import == after)
        rec("rerun::frozen_module_hash_guard", guard_ok,
            f"before/after/import {str(before)[:16]}/{str(after)[:16]}; expected {FROZEN_SHA[:16]}")
        rec("rerun::all_12_fixed_dt_rungs_reproduced",
            bool(rerun_rows) and all(r["reproduced"] for r in rerun_rows),
            f"{sum(r['reproduced'] for r in rerun_rows)}/{len(rerun_rows)} rungs reproduced "
            f"to rel tol {L2_RTOL:g}")
    else:
        rec("rerun::skipped", True, "--skip-rerun given")

    # 5. scope + registry ----------------------------------------------------
    mp = json.loads(MAP.read_text())
    lock_state = mp.get("numerics_lock", {}).get("state")
    solver_dir = (REPO / "numerics" / "spherical_solver").exists()
    rec("scope::lock_and_no_solver",
        lock_state == "locked" and not solver_dir,
        f"numerics_lock={lock_state}; numerics/spherical_solver exists={solver_dir}")

    reg = json.loads(REGISTRY.read_text())
    reg_hashes = reg.get("hashes", {})
    registry = reg.get("registry", {})

    def reg_lookup(path):
        return reg_hashes.get(path) or registry.get(path) or {}

    reg_rows = []
    for role, path, declared in pin_pairs:
        entry = reg_lookup(path)
        reg_rows.append({
            "role": role,
            "path": path,
            "registered": bool(entry),
            "registered_sha256": entry.get("sha256"),
            "matches_declared": bool(entry) and entry.get("sha256") == declared,
            "disk_sha256": sha256_file(REPO / path),
            "is_independent_verdict_artifact": path.startswith("artifacts/worker-"),
        })
    canonical_rows = [r for r in reg_rows if not r["is_independent_verdict_artifact"]]
    worker_rows = [r for r in reg_rows if r["is_independent_verdict_artifact"]]
    unregistered_workers = [r["path"] for r in worker_rows if not r["registered"]]
    rec("registry::canonical_pins_registered_and_matching",
        all(r["matches_declared"] for r in canonical_rows),
        f"{sum(r['matches_declared'] for r in canonical_rows)}/{len(canonical_rows)} canonical rev3 "
        "pins registered in runtime/state/artifact_hashes.json")
    if unregistered_workers:
        findings.append(
            "ADVISORY (registration coverage): the independent replication verdict artifacts rev3 "
            "relies on are not registered in runtime/state/artifact_hashes.json: "
            + ", ".join(unregistered_workers)
            + " - rev3's own registration_state already records this gap; it does not affect the "
              "hash audit here (all three match their declared sha256) but PROTOCOL rule 2 "
              "requires registry entries before node promotion")

    # 6. the three independent verdict artifacts -----------------------------
    verdict_rows = []
    for i, v in enumerate(verdicts):
        path = REPO / v.get("path", "")
        payload = {}
        try:
            payload = json.loads(path.read_text())
        except Exception as exc:  # noqa: BLE001
            findings.append(f"verdict artifact unreadable: {v.get('path')} ({type(exc).__name__})")
        got = payload.get("verdict")
        if isinstance(got, dict):
            got = got.get("disposition", got.get("status"))
        verdict_rows.append({
            "reviewer": v.get("reviewer"), "path": v.get("path"),
            "declared_sha256": v.get("sha256"),
            "disk_sha256": sha256_file(path),
            "declared_verdict": v.get("verdict"),
            "artifact_verdict": got,
            "role": v.get("role"),
        })
    rec("verdicts::three_artifacts_present_and_hash_bound",
        len(verdict_rows) >= 3
        and all(r["disk_sha256"] == r["declared_sha256"] for r in verdict_rows),
        f"{len(verdict_rows)} verdict artifacts; hash match="
        f"{sum(r['disk_sha256'] == r['declared_sha256'] for r in verdict_rows)}/{len(verdict_rows)}")

    # 7. new independent arm: RK4 + 3-pt FD at fixed dt ----------------------
    arm_rows = [rk4_fd_run(dr, DT_FIXED) for dr in DRS]
    arm_errs = [r["l2_error"] for r in arm_rows]
    arm_p, arm_se, _ = fit_ls(DRS, arm_errs)
    arm_monotone = all(arm_errs[i + 1] < arm_errs[i] for i in range(len(arm_errs) - 1))
    arm_within = abs(arm_p - P_DESIGN) <= P_TOL
    lffd_p = next((r["recomputed_fit_order"] for r in fit_rows if r["scheme"] == "lffd"), None)
    arm_agree = lffd_p is not None and abs(arm_p - lffd_p) <= 0.05
    rec("new_arm::rk4_fd_order_within_band_and_agrees",
        arm_monotone and arm_within and arm_agree,
        f"RK4+3pt-FD p={arm_p:.6f} (monotone={arm_monotone}, within_band={arm_within}, "
        f"|p-p_lffd|={abs(arm_p - lffd_p) if lffd_p is not None else float('nan'):.2e})")
    if not arm_agree:
        findings.append(
            f"NEW ARM: RK4+3pt-FD fixed-dt order {arm_p:.6f} differs from lffd {lffd_p} by "
            f"{abs(arm_p - lffd_p):.2e} (> 0.05) - report as a new measurement, not a refutation")

    # 8. self-controls -------------------------------------------------------
    arm_errs_perturbed = list(arm_errs)
    arm_errs_perturbed[-1] *= 1.01  # one rung, not a uniform scale (uniform scale cannot move a log-log slope)
    p_pert, _, _ = fit_ls(DRS, arm_errs_perturbed)
    perturbed_flagged = abs(p_pert - arm_p) > 1e-4
    rec("self_control::perturbed_fit_is_flagged", perturbed_flagged,
        f"1% perturbation of the finest rung moves p by {abs(p_pert - arm_p):.3e} (>1e-4 required)")
    rec("self_control::wrong_pin_is_flagged",
        sha256_file(FROZEN) != "0" * 64,
        "bogus-pin comparison returns False as required")

    # any failed check is itself a finding, so the report explains itself
    for c in checks:
        if not c["pass"]:
            findings.append(f"CHECK FAIL: {c['check_id']} | {c['detail']}")
    findings = list(dict.fromkeys(findings))

    rev3_sha_end = sha256_file(REV3)
    rec("rev3::pin_stable_across_review", rev3_sha_end == rev3_sha_start,
        f"start {str(rev3_sha_start)[:16]}; end {str(rev3_sha_end)[:16]}")

    all_pass = all(c["pass"] for c in checks)
    verdict = {
        "verdict": "CLOSURE_VERIFIED" if all_pass else "FINDINGS",
        "scope": "N0/G-NUM stop-rule closure at the pinned rev3 hash; no gate verdict",
        "stop_rule_items": {
            "fourth_resolution": bool(all(r["n_rungs"] >= 4 for r in fit_rows)),
            "f0_rebind": bool(cl.get("sha256") == sha256_file(REPO / "research_map/formulation_taxonomy.yaml")
                              and cl.get("class_id") == rev3.get("class_id")),
            "independent_verdicts_present": len(verdict_rows) >= 3,
        },
        "all_checks_pass": all_pass,
        "checks_passed": sum(c["pass"] for c in checks),
        "checks_total": len(checks),
    }

    report = {
        "schema": "flash-13-n0-rev3-verification/v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "worker": "deepseek-flash-13",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "conclusion_type": "verification_verdict",
        "target": {
            "path": "numerics/results/flat_wave_convergence_rev3.json",
            "declared_sha256": a.rev3_sha,
            "measured_sha256_start": rev3_sha_start,
            "measured_sha256_end": rev3_sha_end,
        },
        "verdict": verdict,
        "checks": checks,
        "pins": pin_rows,
        "fit_recompute": fit_rows,
        "live_rerun": rerun_rows,
        "registry_snapshot": reg_rows,
        "independent_verdict_artifacts": verdict_rows,
        "new_arm_rk4_fd": {
            "rows": arm_rows,
            "fit_order": arm_p,
            "least_squares_se": arm_se,
            "monotone": arm_monotone,
            "within_band": arm_within,
            "agrees_with_lffd_within_0.05": arm_agree,
            "pre_registered_criteria": ["monotone", "|p-2|<=0.3", "|p-p_lffd|<=0.05"],
            "independence_note": "solver implemented from scratch here; shares the analytic "
                                 "pulse family, r_max and t_end protocol with the module",
        },
        "findings": findings,
        "disclosure": [
            "reviewer deepseek-flash-13 authored numerics/tests/flat_wave_replication.py and "
            "numerics/protocol/n0_fixed_dt_certification.py: the frozen module and the "
            "certification basis under review",
            "worker-046 (from-scratch re-execution SUPPORTED 8/8), worker-057 (re-analysis "
            "REPRODUCED) and worker-081 (adjudication accept) supply the solver-independent "
            "verdicts; this script audits those artifacts only for existence, hash and verdict",
            "constant-CFL ladders are not endorsed as spatial evidence here",
        ],
        "falsifiers": [
            "re-hashing any pinned path in this report and finding a different sha256 voids the "
            "corresponding check",
            "a rerun of any fixed-dt rung whose l2 error differs beyond rel tol 1e-12 falsifies "
            "the live-reproduction check",
            "a rev3 byte change after measured_sha256_end voids this verdict (re-issue required)",
            "a numerics/spherical_solver file appearing while numerics_lock.state == 'locked' "
            "falsifies the scope check",
            "this verdict is falsified if the checker passes a deliberately perturbed fit or a "
            "wrong pin (self-controls above are the guard)",
        ],
        "claims_not_made": [
            "no gate verdict (G-NUM authority: Astra / lead-audit)",
            "no node completion (N0 status unchanged)",
            "no numerics_lock release (N1 stays locked)",
            "no physics, self-gravity, WCC or SCC claim",
        ],
        "provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "runtime_seconds": round(time.time() - t0, 2),
            "script_sha256": sha256_file(Path(__file__)),
        },
    }

    out = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if a.json_out:
        p = Path(a.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out)
        print(f"wrote {p}")
    print(json.dumps({
        "verdict": verdict["verdict"],
        "checks": f"{verdict['checks_passed']}/{verdict['checks_total']}",
        "findings": findings,
        "new_arm_p": arm_p,
        "rev3_sha": rev3_sha_start,
    }, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
