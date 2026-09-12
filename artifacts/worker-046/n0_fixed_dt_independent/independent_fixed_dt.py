#!/usr/bin/env python3
"""W046-N0-FIXEDDT-INDEP-01 — protocol-section-3.4-exact fixed-dt spatial-order study.

TASK (one bounded, class-bound task selected by worker-046; no inbox card existed)
  node N0 / gate G-NUM / class AF-WCC-SCALAR-SPH.

WHY THIS EXISTS
  Worker-067's independent C8 review (`artifacts/worker-067/g_num_protocol_review/review.json`,
  finding F1, major, blocks accept) and worker-081's independent confirmation state that the
  certified N0 order evidence is carried by constant-CFL ladders (cfl = 0.5, dt = 0.5*dr),
  while `numerics/CONVERGENCE_PROTOCOL.md` section 3.4 says:

      "Spatial order is measured with a fixed, small `dt` (`1e-4`) so RK4 error is negligible;
       ... (`dt ∝ h` runs are reported as mixed-order and never quoted as spatial)."

  Worker-067's F1 falsifier is exact: "A 4-rung order-certification study at fixed dt=1e-4 for
  schemes A/B exists at the pinned protocol hash, or the pinned protocol text does not contain
  the quoted section 3.4 sentence -> F1 is withdrawn."

  This script performs exactly that prescribed study, independently of the numerics lead's
  in-flight `numerics/protocol/n0_fixed_dt_certification.py` (written 00:31, no output at the
  time this worker started). It re-executes the FROZEN module under a hash guard and re-derives
  every statistic with this worker's own arithmetic.

PRE-REGISTERED CRITERIA (fixed before the study ran; see `criteria` in results.json)
  A1  frozen module hash == 8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422
  A2  published 4-rung artifact hash == c88146a1375c50f0... (declared orders read from it)
  A3  every scheme ladder has exactly 4 rungs and dt == 1e-4 on every rung
  A4  l2_error strictly decreasing in dr for every scheme
  A5  independently refit order p in [2.0-0.3, 2.0+0.3] for every scheme
  A6  fixed-dt order R5-agrees with the published constant-CFL order for every scheme,
      bound = max(0.25, sqrt(delta_fixed^2 + delta_published^2))
  A7  F1-closure test: A3+A4+A5 hold for at least lffd and cnfd -> worker-067 F1 falsifier
      clause ("fixed-dt 4-rung study for schemes A/B exists") is triggered
  A8  controls: C1 same-object constant-CFL ladder reproduces published orders to < 1e-9 rel;
      C2 dt=dr^0.5 contamination ladder drops below fit 1.5 for an implicit scheme;
      C3 determinism: repeated coarsest-rung l2_error bitwise equal

VERDICT RULE (pre-registered)
  REFUTED    if A1 or A2 fails (hash guard, exit 2) or A3/A4 fails for any scheme
  SUPPORTED  if A1-A8 all pass; otherwise PARTIAL (report which criterion failed)

NOT CLAIMED
  no gate verdict, no node completion, no numerics-lock release, no physics claim.
  The frozen module and the published artifact are read-only; nothing outside this directory
  is written.

FALSIFIER
  Re-run after any change to this script or to the three pinned inputs: a scheme outside
  p = 2.0 +/- 0.3, non-monotone errors, dt != 1e-4 on any rung, an A8 control failing, an R5
  disagreement with the published order, or any hash-guard mismatch falsifies/voids the result
  (hash mismatch exits 2 fail-closed).
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
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

FROZEN = REPO / "numerics" / "tests" / "flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
PUBLISHED = REPO / "numerics" / "tests" / "n0_order_4rung.json"
PUBLISHED_SHA = "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a"
PROTOCOL = REPO / "numerics" / "CONVERGENCE_PROTOCOL.md"
PROTOCOL_SHA_EXPECTED = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"

DR_VALUES = [0.2, 0.1, 0.05, 0.025]
DT_FIXED = 1e-4
CFL_PUBLISHED = 0.5
R_MAX, T_END = 30.0, 6.0
P_DESIGN, P_TOL = 2.0, 0.3
R5_FLOOR = 0.25
SCHEMES = ("lffd", "cnfd", "cnfem")

CRITERIA = {
    "A1": "frozen module sha256 == 8ade1cdc...",
    "A2": "published n0_order_4rung.json sha256 == c88146a1375c... (declared orders read from it)",
    "A3": "4 rungs per scheme and dt == 1e-4 on every rung",
    "A4": "l2_error strictly decreasing in dr for every scheme",
    "A5": "independent refit order within 2.0 +/- 0.3 for every scheme",
    "A6": "fixed-dt order R5-agrees with the published constant-CFL order for every scheme",
    "A7": "F1 falsifier clause triggered: fixed-dt in-band ladder exists for lffd and cnfd",
    "A8": "controls C1 (same-object reproduction), C2 (contamination detectable), C3 (determinism)",
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_frozen():
    spec = importlib.util.spec_from_file_location("fwr_w046_indep", FROZEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ols_loglog(drs, errs):
    """This worker's own OLS on log e vs log h (no use of the frozen module's fit)."""
    x = np.log(np.asarray(drs, dtype=float))
    y = np.log(np.asarray(errs, dtype=float))
    xbar, ybar = float(x.mean()), float(y.mean())
    sxx = float(np.sum((x - xbar) ** 2))
    sxy = float(np.sum((x - xbar) * (y - ybar)))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    resid = y - (intercept + slope * x)
    dof = len(x) - 2
    se = float(math.sqrt(float(np.sum(resid ** 2)) / dof / sxx)) if dof > 0 else float("nan")
    return slope, se, intercept


def pair_orders(drs, errs):
    return [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
            for i in range(len(errs) - 1)]


def r5_delta(pairs, se):
    half_range = (max(pairs) - min(pairs)) / 2.0 if len(pairs) > 1 else 0.0
    return max(half_range, se), half_range, se


def study_stats(rows):
    drs = [r["dr"] for r in rows]
    errs = [r["l2_error"] for r in rows]
    p, se, _ = ols_loglog(drs, errs)
    pairs = pair_orders(drs, errs)
    delta, half_range, _ = r5_delta(pairs, se)
    return {
        "fit_order": p,
        "least_squares_se": se,
        "pair_orders": pairs,
        "pair_half_range": half_range,
        "delta_R5": delta,
        "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
        "within_band": bool(abs(p - P_DESIGN) <= P_TOL),
        "dt_all_fixed": all(abs(r["dt"] - DT_FIXED) < 1e-15 for r in rows),
        "n_rungs": len(rows),
    }


def run_ladder(mod, scheme, dt_rule, cfl=CFL_PUBLISHED):
    t0 = time.time()
    out = mod.order_study(scheme, dr_values=list(DR_VALUES), cfl=cfl, r_max=R_MAX,
                          t_end=T_END, dt_rule=dt_rule)
    wall = time.time() - t0
    rows = [{"dr": r["dr"], "dt": r["dt"], "cfl": r["cfl"], "steps": r["steps"],
             "l2_error": r["l2_error"], "final_t": r["final_t"], "l2_error_u": r["l2_error_u"]}
            for r in out["rows"]]
    return rows, wall


def r5_bound(da, db):
    return max(R5_FLOOR, math.sqrt(da ** 2 + db ** 2))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(HERE / "results.json"))
    args = ap.parse_args(argv)

    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    frozen_sha = sha256_file(FROZEN)
    published_sha = sha256_file(PUBLISHED)
    protocol_sha = sha256_file(PROTOCOL)

    hard_guards = {"frozen_module": frozen_sha == FROZEN_SHA,
                   "published_4rung": published_sha == PUBLISHED_SHA}
    if not all(hard_guards.values()):
        print(json.dumps({"verdict": "GUARD_FAIL", "hard_guards": hard_guards,
                          "frozen_sha256": frozen_sha, "published_sha256": published_sha,
                          "expected_frozen": FROZEN_SHA,
                          "expected_published": PUBLISHED_SHA}, indent=2))
        return 2

    published = json.loads(PUBLISHED.read_text())
    declared = {v["scheme"]: v for v in published["studies"]}
    missing = [s for s in SCHEMES if s not in declared]
    if missing:
        print(json.dumps({"verdict": "GUARD_FAIL", "reason": "schemes missing from published artifact",
                          "missing": missing}, indent=2))
        return 2

    mod = load_frozen()
    results = {
        "task_id": "W046-N0-FIXEDDT-INDEP-01",
        "worker": "worker-046",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "started_at": started,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "inputs": {
            "frozen_module": {"path": str(FROZEN.relative_to(REPO)), "sha256": frozen_sha,
                              "expected": FROZEN_SHA, "match": hard_guards["frozen_module"]},
            "published_4rung": {"path": str(PUBLISHED.relative_to(REPO)), "sha256": published_sha,
                                "expected": PUBLISHED_SHA, "match": hard_guards["published_4rung"]},
            "protocol": {"path": str(PROTOCOL.relative_to(REPO)), "sha256": protocol_sha,
                         "expected": PROTOCOL_SHA_EXPECTED,
                         "match": protocol_sha == PROTOCOL_SHA_EXPECTED},
        },
        "config": {"dr_values": DR_VALUES, "dt_fixed": DT_FIXED, "cfl_control": CFL_PUBLISHED,
                   "r_max": R_MAX, "t_end": T_END, "p_design": P_DESIGN, "p_tol": P_TOL,
                   "r5_floor": R5_FLOOR, "schemes": list(SCHEMES)},
        "criteria": CRITERIA,
        "fixed_dt_study": {},
        "controls": {},
        "published_declared": {s: {"fit_order": declared[s]["fit_order"],
                                   "delta_R5": declared[s].get("delta_R5") or declared[s].get("delta"),
                                   "n_rungs": declared[s].get("n_rungs"),
                                   "config_cfl": published["config"].get("cfl")}
                               for s in SCHEMES},
    }

    # ---- primary study: protocol section 3.4 exact (fixed dt = 1e-4) --------------------
    for scheme in SCHEMES:
        t0 = time.time()
        rows, wall = run_ladder(mod, scheme, dt_rule=lambda dr: DT_FIXED)
        stats = study_stats(rows)
        pub_p = float(declared[scheme]["fit_order"])
        pub_d = float(declared[scheme].get("delta_R5") or declared[scheme].get("delta"))
        bound = r5_bound(stats["delta_R5"], pub_d)
        diff = abs(stats["fit_order"] - pub_p)
        stats.update({"scheme": scheme, "rows": rows, "wall_s": wall,
                      "published_fit_order": pub_p, "published_delta_R5": pub_d,
                      "abs_diff_vs_published": diff, "r5_bound": bound,
                      "r5_agrees": bool(diff <= bound)})
        results["fixed_dt_study"][scheme] = stats
        print(f"[fixed-dt] {scheme}: p={stats['fit_order']:.6f} +/- {stats['delta_R5']:.6f} "
              f"monotone={stats['monotone']} dt_fixed={stats['dt_all_fixed']} "
              f"|p-pub|={diff:.6f} bound={bound:.4f} wall={wall:.1f}s", flush=True)

    # ---- controls ----------------------------------------------------------------------
    c1 = {}
    for scheme in SCHEMES:
        rows, wall = run_ladder(mod, scheme, dt_rule=None)  # cfl = 0.5 ladder (published object)
        stats = study_stats(rows)
        pub_p = float(declared[scheme]["fit_order"])
        c1[scheme] = {"fit_order": stats["fit_order"], "published_fit_order": pub_p,
                      "rel_diff": abs(stats["fit_order"] - pub_p) / abs(pub_p),
                      "reproduces_lt_1e-9": bool(abs(stats["fit_order"] - pub_p) / abs(pub_p) < 1e-9),
                      "monotone": stats["monotone"], "n_rungs": stats["n_rungs"],
                      "wall_s": wall, "rows": rows}
        print(f"[C1 cfl=0.5] {scheme}: p={stats['fit_order']:.9f} vs pub {pub_p:.9f} "
              f"reproduces={c1[scheme]['reproduces_lt_1e-9']}", flush=True)

    c2 = {}
    for scheme in ("cnfd", "cnfem"):
        rows, wall = run_ladder(mod, scheme, dt_rule=lambda dr: dr ** 0.5)
        stats = study_stats(rows)
        c2[scheme] = {"fit_order": stats["fit_order"], "pair_orders": stats["pair_orders"],
                      "monotone": stats["monotone"], "dt_rule": "dt = dr**0.5",
                      "contamination_detected": bool(stats["fit_order"] < 1.5),
                      "wall_s": wall, "rows": rows}
        print(f"[C2 dt=dr^0.5] {scheme}: p={stats['fit_order']:.4f} "
              f"contamination_detected={c2[scheme]['contamination_detected']}", flush=True)

    # C3 determinism: repeat the coarsest rung at fixed dt, require bitwise-equal l2_error
    rows_a, _ = run_ladder(mod, "lffd", dt_rule=lambda dr: DT_FIXED)
    rows_b, _ = run_ladder(mod, "lffd", dt_rule=lambda dr: DT_FIXED)
    ea = [r["l2_error"] for r in rows_a]
    eb = [r["l2_error"] for r in rows_b]
    c3 = {"err_a": ea, "err_b": eb, "bitwise_equal": ea == eb,
          "max_rel_diff": max(abs(a - b) / abs(a) for a, b in zip(ea, eb))}
    print(f"[C3 determinism] bitwise_equal={c3['bitwise_equal']}", flush=True)

    results["controls"] = {"C1_same_object_cfl_0.5": c1, "C2_contamination_dt_dr_pow_half": c2,
                           "C3_determinism_repeat": c3}

    # ---- criteria outcomes --------------------------------------------------------------
    per = results["fixed_dt_study"]
    out = {
        "A1": hard_guards["frozen_module"],
        "A2": hard_guards["published_4rung"],
        "A3": all(per[s]["n_rungs"] == 4 and per[s]["dt_all_fixed"] for s in SCHEMES),
        "A4": all(per[s]["monotone"] for s in SCHEMES),
        "A5": all(per[s]["within_band"] for s in SCHEMES),
        "A6": all(per[s]["r5_agrees"] for s in SCHEMES),
        "A7": bool(all(per[s]["n_rungs"] == 4 and per[s]["dt_all_fixed"] and per[s]["monotone"]
                       and per[s]["within_band"] for s in ("lffd", "cnfd"))),
        "A8": bool(all(v["reproduces_lt_1e-9"] for v in c1.values())
                   and all(v["contamination_detected"] for v in c2.values())
                   and c3["bitwise_equal"]),
    }
    results["criteria_outcomes"] = out
    results["protocol_hash_moved_during_run"] = sha256_file(PROTOCOL) != protocol_sha
    if out["A1"] and out["A2"] and out["A3"] and out["A4"]:
        verdict = "SUPPORTED" if all(out.values()) else "PARTIAL"
    else:
        verdict = "REFUTED"
    results["verdict"] = verdict
    results["verdict_rule"] = ("REFUTED if A1/A2/A3/A4 fail; SUPPORTED if A1-A8 pass; "
                               "PARTIAL otherwise (list failed criteria)")
    results["failed_criteria"] = [k for k, v in out.items() if not v]
    results["f1_falsifier_clause_triggered"] = out["A7"]
    results["f1_statement"] = ("worker-067 F1: no fixed-dt=1e-4 4-rung order study for schemes "
                               "lffd/cnfd existed at protocol 1e6cdf04d7a2; the required closure "
                               "is exactly such a study. A7 true means this worker's independent "
                               "run supplies that evidence; F1 withdrawal remains a reviewer/"
                               "controller decision.")
    results["not_claimed"] = ["no gate verdict", "no node completion",
                              "numerics_lock stays LOCKED", "no physics claim"]
    results["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    Path(args.out).write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "criteria_outcomes": out,
                      "failed_criteria": results["failed_criteria"],
                      "out": args.out}, indent=2))
    return 0 if verdict in ("SUPPORTED", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(main())
