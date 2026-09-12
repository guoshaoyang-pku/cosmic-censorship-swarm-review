#!/usr/bin/env python3
"""Independent adversarial verification of the canonical N0 artifact.

Assignment context
------------------
``comms/inbox/deepseek-flash-12.jsonl`` (event ``asg-2026-09-11-N0-deepseek-flash-12-21``)
assigns worker 12 the artifact ``numerics/tests/flat_wave.py`` for node N0
(``AF-WCC-SCALAR-SPH``), acceptance: "closed-form solution, 3+ resolutions, measured order,
asserts order >= declared - tol, exit code reflects pass/fail".

Reality found on disk
---------------------
The assigned path is occupied by an actively maintained candidate authored by
``deepseek-flash-20`` (whose own assignment is A2).  Worker 12 does not overwrite another
worker's live file.  Instead this script *pins* the artifact by sha256, snapshots it, and
attacks it adversarially.  If the canonical file changes during verification the verdict is
marked stale for the canonical path and valid only for the pinned snapshot.

What is verified (the artifact is the hypothesis; each check can fail it)
  V1 convergence at an independent non-degenerate time (t=0.29, not the artifact's 0.37)
     with independent closed form, independent resolutions (96/192/384) and independent
     L2/L_inf computation; requires every measured order >= 1.8 (declared 2, tol 0.2)
  V1b the same at a third time t=0.23 with a non-power-of-two refinement ratio 1.5
     (n=100/150/225), so the order cannot be an artifact of halving
  V1c the artifact's 4th-order path at t=0.29 with ratio 1.5 (n=64/96/144); requires
     every measured order >= 3.6
  V2 temporal subdominance: halving dt at fixed n moves the error by < 3% (so V1 measures
     spatial order, not RK4 order)
  V3 wrong-operator control: scaling the discrete Laplacian by 1.02 must destroy the
     measured order (< 0.8); if it still converges, the convergence test has no power
  V4 wrong-reference control: a 2% frequency error in the reference must also destroy the
     measured order (< 0.8); the reported convergence is not metric-blind
  V5 black-box CLI: two fresh ``--all`` runs exit 0, report ``all_gates_pass`` true, and
     agree numerically (wall-clock fields excluded)
  V6 scope guards: no ``numerics/spherical_solver`` directory or import; the report carries
     claims_not_made for self-gravity and cosmic censorship; class binding is marked
     provisional rather than promoted
  V7 pin stability: canonical sha256 unchanged across the run; snapshot sha matches
  V8 invariant: discrete energy drift decreases with resolution and is < 1e-10 at the
     finest order-2 standing resolution

Scope of this script: it verifies the artifact, it does not author it and does not claim N0
complete.  Gate G-NUM also requires lead review and worker-13's independent replication.

Usage:
  python3 verify_flat_wave.py [--canonical ../../numerics/tests/flat_wave.py]
Exit code: 0 iff every check passes (stale pin is reported, not silently accepted).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DECLARED_ORDER = 2.0
ORDER_TOL = 0.2
MIN_ORDER = DECLARED_ORDER - ORDER_TOL
T_INDEPENDENT = 0.29
RESOLUTIONS = (96, 192, 384)
MODES = ((2, 1.0),)
R = 1.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def my_standing(r, t, modes=MODES, R=R):
    """Independent closed form: sum_m a sin(k r) cos(k t)/k, k = m pi / R."""
    r = np.asarray(r, dtype=float)
    out = np.zeros_like(r)
    for m, a in modes:
        k = m * math.pi / R
        out += a * np.sin(k * r) * np.cos(k * t) / k
    return out


def l2(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    return float(np.sqrt(np.mean(d ** 2)))


def linf(a, b):
    d = np.asarray(a, float) - np.asarray(b, float)
    return float(np.max(np.abs(d)))


def orders_of(errs, ratios):
    return [math.log(a / b) / math.log(rr) for a, b, rr in zip(errs[:-1], errs[1:], ratios)]


def load_snapshot(path: Path):
    spec = importlib.util.spec_from_file_location("pinned_flat_wave", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_numerics(mod, n, t_end, cfl):
    """Run the pinned solver internals and return (r, numeric, exact, exact_shift)."""
    h, r, v0, w0 = mod._case_setup(n, "standing", R, t_end, 12.0, 2.0, MODES)
    res = mod.integrate(v0, w0, h, t_end, cfl, 2)
    shifted = my_standing(r, t_end, ((2, 1.02),))
    return r, res["v"], my_standing(r, t_end), shifted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default=str(REPO / "numerics" / "tests" / "flat_wave.py"))
    a = ap.parse_args()
    canonical = Path(a.canonical).resolve()
    sha_before = sha256_file(canonical)
    pinned = HERE / f"pinned_flat_wave_{sha_before[:12]}.py"
    if not pinned.exists():
        shutil.copyfile(canonical, pinned)
    sha_pin = sha256_file(pinned)
    mod = load_snapshot(pinned)

    checks: list[dict] = []

    def rec(cid, ok, detail, **extra):
        checks.append({"id": cid, "status": "pass" if ok else "fail", "detail": detail, **extra})

    def convergence(cfl=0.25, exact_fn=None, model=None, t_end=T_INDEPENDENT, resolutions=RESOLUTIONS,
                    order=2):
        errs2, errsinf = [], []
        for n in resolutions:
            h, r, v0, w0 = mod._case_setup(n, "standing", R, t_end, 12.0, 2.0, MODES)
            res = model(v0, w0, h, cfl) if model else mod.integrate(v0, w0, h, t_end, cfl, order)
            ref = exact_fn(r) if exact_fn else my_standing(r, t_end)
            errs2.append(l2(res["v"][1:-1], ref[1:-1]))
            errsinf.append(linf(res["v"][1:-1], ref[1:-1]))
        ratios = [(resolutions[i + 1] / resolutions[i]) for i in range(len(resolutions) - 1)]
        return errs2, errsinf, orders_of(errs2, ratios), orders_of(errsinf, ratios)

    # V1 independent-time convergence
    e2, einf, p2, pinf = convergence()
    ok1 = (len(p2) >= 2 and all(p >= MIN_ORDER for p in p2)
           and all(p >= MIN_ORDER for p in pinf) and all(e > 0 for e in e2))
    rec("V1_independent_convergence", ok1,
        f"t={T_INDEPENDENT} n={RESOLUTIONS} l2={['%.3e' % e for e in e2]} "
        f"order_l2={['%.3f' % p for p in p2]} order_linf={['%.3f' % p for p in pinf]}",
        min_order=min(p2) if p2 else None, declared=DECLARED_ORDER, tol=ORDER_TOL)

    # V1b independent time point AND non-power-of-two refinement ratio 1.5
    e2b, _, p2b, _ = convergence(t_end=0.23, resolutions=(100, 150, 225))
    rec("V1b_offgrid_refinement", bool(p2b) and all(p >= MIN_ORDER for p in p2b),
        f"t=0.23 n=(100,150,225) ratio=1.5 l2={['%.3e' % e for e in e2b]} "
        f"order_l2={['%.3f' % p for p in p2b]}")

    # V1c the declared 4th-order path at an independent time and ratio
    e4, _, p4, _ = convergence(t_end=T_INDEPENDENT, resolutions=(64, 96, 144), order=4)
    rec("V1c_order4_independent", bool(p4) and all(p >= 3.6 for p in p4),
        f"order=4 t={T_INDEPENDENT} n=(64,96,144) ratio=1.5 l2={['%.3e' % e for e in e4]} "
        f"order_l2={['%.3f' % p for p in p4]}")

    # V2 temporal subdominance (same n, two cfl)
    h, r, v0, w0 = mod._case_setup(256, "standing", R, T_INDEPENDENT, 12.0, 2.0, MODES)
    r1 = mod.integrate(v0, w0, h, T_INDEPENDENT, 0.25, 2)
    r2 = mod.integrate(v0, w0, h, T_INDEPENDENT, 0.05, 2)
    ref = my_standing(r, T_INDEPENDENT)
    ea, eb = l2(r1["v"][1:-1], ref[1:-1]), l2(r2["v"][1:-1], ref[1:-1])
    rel = abs(ea - eb) / ea if ea else float("inf")
    rec("V2_temporal_subdominant", rel < 0.03,
        f"n=256 l2(cfl=0.25)={ea:.6e} l2(cfl=0.05)={eb:.6e} relative_change={rel:.4f}")

    # V3 wrong-operator control: 2% Laplacian scaling must destroy the order
    orig_d2 = mod.d2
    try:
        mod.d2 = lambda v, h, order=2: 1.02 * orig_d2(v, h, order)
        _, _, p_bad, _ = convergence()
    finally:
        mod.d2 = orig_d2
    rec("V3_wrong_operator_control", bool(p_bad) and max(p_bad) < 0.8,
        f"order_l2 with 1.02*Laplacian: {['%.3f' % p for p in p_bad]} (expected < 0.8)")

    # V4 wrong-reference control: 2% frequency error in the reference must destroy the order
    _, _, p_ref, _ = convergence(exact_fn=lambda rr: my_standing(rr, T_INDEPENDENT, ((2, 1.02),)))
    rec("V4_wrong_reference_control", bool(p_ref) and max(p_ref) < 0.8,
        f"order_l2 vs 2%-shifted reference: {['%.3f' % p for p in p_ref]} (expected < 0.8)")

    # V5 black-box CLI, twice
    cli = {"runs": [], "stdout_sha256": []}
    for k in (1, 2):
        out_json = HERE / f"cli_run{k}_report.json"
        t0 = time.perf_counter()
        p = subprocess.run([sys.executable, str(pinned), "--all", "--json-out", str(out_json)],
                           capture_output=True, text=True, timeout=1800)
        cli["runs"].append({"exit": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-1000:],
                            "wall_seconds": round(time.perf_counter() - t0, 3),
                            "json_out": str(out_json)})
        cli["stdout_sha256"].append(hashlib.sha256(p.stdout.encode()).hexdigest())
    rep1 = json.loads((HERE / "cli_run1_report.json").read_text())
    rep2 = json.loads((HERE / "cli_run2_report.json").read_text())

    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items()
                    if k not in {"wall_seconds", "generated_at", "checked_at"}}
        if isinstance(obj, list):
            return [strip(v) for v in obj]
        return obj

    numeric1 = strip({k: v for k, v in rep1.items() if k != "provenance"})
    numeric2 = strip({k: v for k, v in rep2.items() if k != "provenance"})
    ok5 = (all(r["exit"] == 0 for r in cli["runs"]) and rep1["all_gates_pass"] and rep2["all_gates_pass"]
           and numeric1 == numeric2)
    rec("V5_cli_black_box", ok5,
        f"exits={[r['exit'] for r in cli['runs']]} all_gates_pass={[rep1['all_gates_pass'], rep2['all_gates_pass']]} "
        f"numeric_reports_equal={numeric1 == numeric2}")
    (HERE / "cli_stdout.txt").write_text(cli["runs"][0]["stdout"])

    # V8 invariant drift: must sit at roundoff level.  Strict monotonicity is only demanded
    # above the 1e-12 roundoff floor; at 1e-14 the sequence is machine noise and may wiggle.
    studies = {s["family"] + f"/order{s['order_scheme']}": s for s in rep1["studies"]}
    st2 = next(s for k, s in studies.items() if k.startswith("standing/order2"))
    drifts = [row["energy_drift"] for row in st2["rows"]]
    above_floor = [d for d in drifts if d > 1e-12]
    monotone = all(b <= a for a, b in zip(above_floor, above_floor[1:]))
    ok8 = bool(max(drifts) < 1e-8 and drifts[-1] < 1e-12 and monotone)
    rec("V8_invariant_drift", ok8,
        f"drift={['%.2e' % d for d in drifts]} max={max(drifts):.2e} final={drifts[-1]:.2e} "
        f"monotone_above_1e-12={monotone} (machine-noise wiggle below the floor is allowed)")

    # V6 scope guards.  The source may *reference* numerics/spherical_solver in order to guard
    # it (rev-1 lock guard does exactly that); what is forbidden is importing or creating it.
    src = pinned.read_text()
    claims = rep1.get("claims_not_made", [])
    imports_solver = bool(re.search(r"(?:import|from)\s+numerics[.\s]*spherical_solver", src))
    ok6 = (not (REPO / "numerics" / "spherical_solver").exists()
           and not imports_solver
           and any("self-gravitating" in c for c in claims)
           and any("cosmic censorship" in c for c in claims)
           and "PROVISIONAL" in rep1.get("binding_status", ""))
    rec("V6_scope_guards", ok6,
        f"spherical_solver_exists={(REPO / 'numerics' / 'spherical_solver').exists()} "
        f"imports_solver={imports_solver} binding={rep1.get('binding_status')!r} claims_not_made={len(claims)}")

    # V7 pin stability
    sha_after = sha256_file(canonical)
    stable = sha_after == sha_before and sha_pin == sha_before
    rec("V7_pin_stability", stable,
        f"canonical_before={sha_before[:16]} canonical_after={sha_after[:16]} pin={sha_pin[:16]}")

    failed = [c for c in checks if c["status"] == "fail"]
    verdict = "pass" if not failed else "fail"
    report = {
        "verifier": "artifacts/flash-12/n0/verify_flat_wave.py",
        "verified_by": "deepseek-flash-12",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "assignment_event": "asg-2026-09-11-N0-deepseek-flash-12-21",
        "canonical_artifact": str(canonical.relative_to(REPO)),
        "canonical_sha256_before": sha_before,
        "canonical_sha256_after": sha_after,
        "pinned_snapshot": str(pinned.relative_to(REPO)),
        "pinned_sha256": sha_pin,
        "applies_to_canonical": bool(stable),
        "stale_reason": None if stable else "canonical file changed during verification; verdict is valid for the pinned snapshot only",
        "verdict": verdict,
        "checks": checks,
        "cli": cli,
        "declared_order": DECLARED_ORDER,
        "order_tolerance": ORDER_TOL,
        "independence_notes": [
            "independent time points t=0.29 and t=0.23 (artifact gates use t=0.37)",
            "independent resolutions 96/192/384 plus off-grid 100/150/225 and 64/96/144 with ratio 1.5",
            "independent closed form and independent L2/L_inf computation",
            "both the declared 2nd-order and 4th-order paths are probed",
            "V3/V4 controls measure the discriminating power of the convergence metric",
            "does not reuse the artifact's own gate verdicts",
        ],
        "limitations": [
            "validates the pinned sha only; re-run after any edit",
            "manufactured-solution tests cannot detect a solver that returns the exact solution",
            "no domain review of the PDE reduction or class binding; gate G-NUM still needs lead-numerics review and worker-13 replication",
        ],
        "checked_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    (HERE / "verification_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"verdict": verdict, "applies_to_canonical": stable,
                      "canonical_sha256": sha_before, "checks_failed": failed}, indent=2))
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
