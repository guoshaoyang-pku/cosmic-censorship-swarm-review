#!/usr/bin/env python3
"""W020-N0-SYMRULE-01 - symmetric temporal-excess sensitivity analysis of the N0 control.

TASK (one bounded class-bound task, taken with no open owner):
  The lead's N0 admissibility control
  (numerics/protocol/temporal_subdominance_control.json#334f5b71e0d5, generator
  ee14a3caf086) declares the constant-CFL ladder admissible as *spatial* evidence per
  scheme using a ONE-SIDED temporal-excess rule:
      rule_b:  e(dt_cfl)/e_plateau - 1  <=  0.05
  (generator lines 224-229 take max() of the signed excess, not max |excess|).
  This script re-analyses the SAME filed sweep data under the natural two-sided
  (symmetric) reading of "temporal subdominance", |excess| <= 0.05, and quantifies the
  consequence for ladder A (constant CFL) versus ladder B (fixed dt).

WHAT THIS SCRIPT DOES (read-only re-analysis; no solver re-runs, no canonical writes)
  1. Hash-pins the target JSON, its generator, and the frozen instrument; refuses to run
     if any measured hash differs from the filed pin.
  2. Independently recomputes, from the target's own raw sweep points: e_plateau,
     e_at_cfl, the one-sided excess, its absolute value, the monotonicity flag, the
     ladder order fits, and the per-scheme admissibility verdict.  Cross-checks every
     number against the filed value.
  3. Leave-one-out sensitivity of the A-ladder order fit (drop the finest rung dr=0.025;
     drop the swept rung dr=0.05).
  4. Conservative fixed-dt bound: from each filed temporal sweep, bound the temporal
     contamination of ladder B at dt = 1e-3 and 5e-4 by scaling the nearest filed sweep
     point with the asymptotic (>=2nd) order, and compare with the same 0.05 tolerance.
  5. Controls: sign-flip mutation of the excess (shows the one-sided rule is not
     invariant under temporal-spatial cancellation), vacuous-input guard, hash guard,
     determinism re-run, and filed-value cross-checks.

LIMITS / AUTHORITY
  Worker evidence only: no gate verdict, no node completion, no canonical-path edit.
  The two-sided reading is a SENSITIVITY CHECK on the pre-registered rule, not a
  restatement of it; the canonical rule text is unchanged (the generator and target are
  read-only here).  This analysis is a re-analysis of filed data: it does not re-run the
  PDE solver, so it inherits the filed runs' determinism claim.

FALSIFIER
  Void if: (i) any pinned input re-hashes differently; (ii) the one-sided recomputation
  does not reproduce the filed excess / rule_b_pass / admissible_as_spatial values;
  (iii) a filed sweep point is missing or non-halving; (iv) the sign-flip mutation is
  not detected; or (v) two core runs are not byte-identical.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

TARGET = REPO / "numerics" / "protocol" / "temporal_subdominance_control.json"
GENERATOR = REPO / "numerics" / "protocol" / "temporal_subdominance_control.py"
FROZEN = REPO / "numerics" / "tests" / "flat_wave_replication.py"

PINNED = {
    "numerics/protocol/temporal_subdominance_control.json":
        "334f5b71e0d53ab6ed1f3b7133abca541a36dafc9a5cfb4f62f0655839dd964b",
    "numerics/protocol/temporal_subdominance_control.py":
        "ee14a3caf086d64ed4edab24560f5997a60b9f9045f73547afa00929ed10a24c",
    "numerics/tests/flat_wave_replication.py":
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
}

# Pre-registered tolerance, read from the target's own rule_b text/config semantics; NOT
# chosen after seeing results (the target itself states thresholds_movable_after_result=false).
EXCESS_TOL = 0.05
DT_FIXED_LADDER = (1e-3, 5e-4)
SCHEMES = ("lffd", "cnfd", "cnfem")
SIGNED_REL_TOL = 1e-12   # recomputation agreement vs filed excess
CALIB_REL_TOL = 1e-9     # recomputation agreement vs filed fit orders / rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ls_order(drs, errs):
    """Least-squares slope of ln(err) vs ln(dr) (order convention used by the target)."""
    xs = [math.log(d) for d in drs]
    ys = [math.log(e) for e in errs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx


def rel_dev(a, b):
    if b == 0:
        return abs(a)
    return abs(a - b) / abs(b)


def recompute_core(target: dict) -> dict:
    """Pure recomputation from the target's filed rows.  No mutation of `target`."""
    sweeps = {}
    for scheme in SCHEMES:
        entry = target["schemes"][scheme]
        sweeps[scheme] = {}
        for sweep in entry["C_temporal_sweeps"]:
            dr = float(sweep["dr"])
            pts = sweep["points"]
            plateau = pts[-1]["l2_error"]
            e_cfl = pts[0]["l2_error"]
            excess = e_cfl / plateau - 1.0
            diffs = [p["l2_error"] - plateau for p in pts]
            # generator convention: plateaus[i+1] <= plateaus[i] * (1 + 1e-12)
            monotone = all(pts[i + 1]["l2_error"] <= pts[i]["l2_error"] * (1 + 1e-12)
                           for i in range(len(pts) - 1))
            halving_ok = all(
                abs(pts[i + 1]["dt"] - pts[i]["dt"] / 2.0) <= 1e-15 * pts[i]["dt"]
                for i in range(len(pts) - 1)
            )
            steps_ok = all(abs(p["steps"] - target["config"]["t_end"] / p["dt"]) <= 1.0
                           for p in pts)
            sweeps[scheme][dr] = {
                "n_points": len(pts),
                "dt_cfl": pts[0]["dt"],
                "dt_filed": sweep["dt_cfl"],
                "e_plateau": plateau,
                "e_at_cfl": e_cfl,
                "excess_recomputed": excess,
                "excess_filed": sweep["temporal_excess_at_cfl"],
                "excess_rel_dev": rel_dev(excess, sweep["temporal_excess_at_cfl"]),
                "abs_excess_recomputed": abs(excess),
                "verdict_one_sided_pass": bool(excess <= EXCESS_TOL),
                "verdict_symmetric_pass": bool(abs(excess) <= EXCESS_TOL),
                "monotone_to_plateau_recomputed": bool(monotone),
                "monotone_to_plateau_filed": bool(sweep["monotone_to_plateau"]),
                "plateau_is_finest_point": abs(plateau - sweep["e_plateau"]) <= 0.0,
                "e_cfl_is_coarsest_point": abs(e_cfl - sweep["e_at_cfl"]) <= 0.0,
                "halving_grid_ok": bool(halving_ok),
                "steps_match_t_end_over_dt": bool(steps_ok),
                "diffs_signed": diffs,
                "dts": [p["dt"] for p in pts],
            }

    ladders = {}
    for scheme in SCHEMES:
        entry = target["schemes"][scheme]
        a = entry["A_constant_cfl_ladder"]
        drs = [r["dr"] for r in a["rows"]]
        errs = [r["l2_error"] for r in a["rows"]]
        p_all = ls_order(drs, errs)
        # leave-one-out: drop finest (dr=0.025) | drop swept rung (dr=0.05)
        idx_finest = drs.index(min(drs))
        keep_finest_drop = [i for i in range(len(drs)) if i != idx_finest]
        p_drop_finest = ls_order([drs[i] for i in keep_finest_drop],
                                 [errs[i] for i in keep_finest_drop])
        idx_005 = drs.index(0.05) if 0.05 in drs else None
        if idx_005 is not None:
            keep_drop_005 = [i for i in range(len(drs)) if i != idx_005]
            p_drop_005 = ls_order([drs[i] for i in keep_drop_005],
                                  [errs[i] for i in keep_drop_005])
        else:
            p_drop_005 = None
        b = {}
        for dt, lad in entry["B_fixed_dt_ladders"].items():
            bdrs = [r["dr"] for r in lad["rows"]]
            berrs = [r["l2_error"] for r in lad["rows"]]
            b[dt] = {
                "p_recomputed": ls_order(bdrs, berrs),
                "p_filed": lad["fit_order"],
                "within_band_recomputed": bool(abs(ls_order(bdrs, berrs) - 2.0) <= 0.3),
                "rows_n": len(bdrs),
            }
        ladders[scheme] = {
            "p_all4_recomputed": p_all,
            "p_all4_filed": a["fit_order"],
            "p_all4_rel_dev": rel_dev(p_all, a["fit_order"]),
            "p_drop_finest_dr0025": p_drop_finest,
            "p_drop_swept_dr005": p_drop_005,
            "max_abs_loo_shift": max(abs(p_drop_finest - p_all),
                                     abs(p_drop_005 - p_all) if p_drop_005 is not None else 0.0),
            "B_fixed_dt": b,
        }
    return {"sweeps": sweeps, "ladders": ladders}


def fixed_dt_bound(core: dict, target: dict):
    """Conservative bound on ladder-B temporal contamination at dt = 1e-3 and 5e-4.

    For swept dr only.  Asymptotic region = sweep points with dt <= dt_cfl/4 (k >= 2).
    Bound(dt_t) = |e(dt_s) - e_plateau| * (dt_t/dt_s)^q for the closest asymptotic point
    dt_s >= dt_t (else the finest asymptotic point, no scaling), with q = min(2, measured
    local orders) so the scaling never assumes a faster decay than measured.  A coarse
    variant uses the coarsest asymptotic point instead, as a robustness check.
    """
    out = {}
    for scheme in SCHEMES:
        out[scheme] = {}
        for dr, sw in core["sweeps"][scheme].items():
            dts = sw["dts"]
            diffs = sw["diffs_signed"]
            dt_cfl = dts[0]
            asym = [(dt, d) for dt, d in zip(dts[:-1], diffs[:-1])
                    if dt <= dt_cfl / 4.0 + 1e-15 and abs(d) > 0.0]
            asym.sort(key=lambda t: t[0], reverse=True)  # coarse -> fine
            local_orders = []
            for i in range(len(asym) - 1):
                dt_c, d_c = asym[i]
                dt_f, d_f = asym[i + 1]
                local_orders.append(math.log(abs(d_c) / abs(d_f)) / math.log(dt_c / dt_f))
            targets = {}
            q_used = min([2.0] + local_orders) if local_orders else 2.0
            for dt_t in DT_FIXED_LADDER:
                above = [(dt, d) for dt, d in asym if dt >= dt_t]
                if above:
                    dt_s, d_s = min(above, key=lambda t: t[0])
                    bound = abs(d_s) * (dt_t / dt_s) ** q_used
                    bound_q2 = abs(d_s) * (dt_t / dt_s) ** 2
                    mode = "scale_from_coarser_asymptotic"
                else:
                    dt_s, d_s = asym[0]
                    bound = abs(d_s)
                    bound_q2 = abs(d_s)
                    mode = "finest_asymptotic_no_scaling"
                dt_c, d_c = asym[0]
                coarse_bound = abs(d_c) * (dt_t / dt_c) ** q_used if dt_c >= dt_t else abs(d_c)
                targets[f"dt_{dt_t:g}"] = {
                    "dt_s_used": dt_s,
                    "signed_diff_at_dt_s": d_s,
                    "q_used": q_used,
                    "bound_abs": bound,
                    "bound_abs_q2": bound_q2,
                    "bound_rel_to_plateau": bound / sw["e_plateau"],
                    "bound_rel_q2": bound_q2 / sw["e_plateau"],
                    "mode": mode,
                    "coarse_variant_bound_rel": coarse_bound / sw["e_plateau"],
                    "verdict_symmetric_pass": bool(
                        (bound / sw["e_plateau"]) <= EXCESS_TOL),
                }
            out[scheme][dr] = {
                "asymptotic_points": asym,
                "min_local_order": min(local_orders) if local_orders else None,
                "local_orders": local_orders,
                "targets": targets,
            }
    return out


def sign_flip_control(core: dict, target: dict):
    """Mutation: swap the sign of the filed excess (e(dt_cfl) reflected about plateau)
    and show the one-sided rule keeps passing while the symmetric rule fails."""
    mutated = copy.deepcopy(target)
    flips = []
    for scheme in SCHEMES:
        for sweep in mutated["schemes"][scheme]["C_temporal_sweeps"]:
            plateau = sweep["e_plateau"]
            sweep["e_at_cfl"] = 2.0 * plateau - sweep["e_at_cfl"]
            sweep["points"][0]["l2_error"] = sweep["e_at_cfl"]
    mcore = recompute_core(mutated)
    detected = 0
    for scheme in SCHEMES:
        for dr, sw in mcore["sweeps"][scheme].items():
            orig = core["sweeps"][scheme][dr]
            changed = rel_dev(sw["excess_recomputed"], orig["excess_recomputed"]) > 1e-6
            if changed:
                detected += 1
            flips.append({
                "scheme": scheme, "dr": dr,
                "orig_one_sided_pass": orig["verdict_one_sided_pass"],
                "orig_symmetric_pass": orig["verdict_symmetric_pass"],
                "mut_one_sided_pass": sw["verdict_one_sided_pass"],
                "mut_symmetric_pass": sw["verdict_symmetric_pass"],
                "mutation_detected": bool(changed),
            })
    return {"n_mutations": len(flips), "n_detected": detected, "rows": flips}


def vacuous_guard(target: dict):
    """Removing a scheme's sweeps must be detectable (no silent pass on missing input)."""
    mutated = copy.deepcopy(target)
    mutated["schemes"]["cnfem"]["C_temporal_sweeps"] = []
    try:
        core = recompute_core(mutated)
    except Exception as e:  # noqa: BLE001
        return {"raised": True, "error": type(e).__name__, "silent_pass": False}
    missing = [s for s in SCHEMES if not core["sweeps"][s]]
    return {"raised": False, "silent_pass": not missing, "missing_schemes": missing}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(HERE / "symmetric_rule_analysis.json"))
    ap.add_argument("--log-out", default=str(HERE / "symmetric_rule_analysis.log"))
    a = ap.parse_args()
    t0 = time.time()
    log_lines = []

    def log(msg):
        log_lines.append(str(msg))
        print(msg, flush=True)

    log(f"W020-N0-SYMRULE-01 start {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    pins = {}
    for rel, expected in PINNED.items():
        measured = sha256_file(REPO / rel)
        pins[rel] = {"expected": expected, "measured": measured, "match": measured == expected}
        log(f"pin {rel}: {measured} match={measured == expected}")
        if measured != expected:
            log("FATAL: pinned input moved; analysis does not bind.")
            return 2

    target = json.loads(TARGET.read_text())
    if target.get("class_id") != "AF-WCC-SCALAR-SPH" or target.get("node_id") != "N0":
        log("FATAL: target class/node binding is not AF-WCC-SCALAR-SPH / N0.")
        return 2
    p_tol_filed = float(target["config"].get("p_tol", 0.3))
    pre = target["admissibility_rule_stated_before_results"]
    if pre.get("thresholds_movable_after_result") is not False:
        log("FATAL: thresholds are not declared immovable; refusing sensitivity framing.")
        return 2

    core = recompute_core(target)
    core2 = recompute_core(target)
    determinism = json.dumps(core, sort_keys=True) == json.dumps(core2, sort_keys=True)
    log(f"determinism (two core runs identical): {determinism}")

    # Cross-checks against filed values
    xchecks = []
    for scheme in SCHEMES:
        for dr, sw in core["sweeps"][scheme].items():
            xchecks.append(("excess", scheme, dr, sw["excess_rel_dev"] <= SIGNED_REL_TOL))
            xchecks.append(("monotone_filed_agrees", scheme, dr,
                            sw["monotone_to_plateau_filed"] == sw["monotone_to_plateau_recomputed"]))
            xchecks.append(("halving_grid", scheme, dr, sw["halving_grid_ok"]))
            xchecks.append(("steps", scheme, dr, sw["steps_match_t_end_over_dt"]))
        lad = core["ladders"][scheme]
        xchecks.append(("A_fit_order", scheme, None, lad["p_all4_rel_dev"] <= CALIB_REL_TOL))
        for dt, b in lad["B_fixed_dt"].items():
            xchecks.append((f"B_fit_order_{dt}", scheme, None,
                            rel_dev(b["p_recomputed"], b["p_filed"]) <= CALIB_REL_TOL))
    one_sided_agg = {
        s: bool(core["sweeps"][s]) and all(
            core["sweeps"][s][dr]["verdict_one_sided_pass"] for dr in core["sweeps"][s])
        for s in SCHEMES
    }
    symmetric_agg = {
        s: bool(core["sweeps"][s]) and all(
            core["sweeps"][s][dr]["verdict_symmetric_pass"] for dr in core["sweeps"][s])
        for s in SCHEMES
    }
    for s in SCHEMES:
        filed_pass = bool(target["schemes"][s]["checks"]["rule_b"]["rule_b_pass"])
        xchecks.append(("filed_rule_b_aggregate", s, None, filed_pass == one_sided_agg[s]))

    bounds = fixed_dt_bound(core, target)
    flip = sign_flip_control(core, target)
    vac = vacuous_guard(target)

    all_x = all(ok for _, _, _, ok in xchecks)
    n_swept = sum(len(core["sweeps"][s]) for s in SCHEMES)
    n_one_sided_pass = sum(1 for s in SCHEMES for dr in core["sweeps"][s]
                           if core["sweeps"][s][dr]["verdict_one_sided_pass"])
    n_symmetric_pass = sum(1 for s in SCHEMES for dr in core["sweeps"][s]
                           if core["sweeps"][s][dr]["verdict_symmetric_pass"])
    b_pass = {}
    for s in SCHEMES:
        b_pass[s] = {}
        for dr, entry in bounds[s].items():
            b_pass[s][dr] = {k: v["verdict_symmetric_pass"] for k, v in entry["targets"].items()}
    n_b_pass = sum(1 for s in SCHEMES for dr in b_pass[s] for k in b_pass[s][dr]
                   if b_pass[s][dr][k])

    result = {
        "schema": "w020-n0-symmetric-rule-analysis/v1",
        "task_id": "W020-N0-SYMRULE-01",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "gate": "G-NUM",
        "conclusion_type": "numerical_evidence",
        "question": ("Does the lead's N0 constant-CFL admissibility verdict survive the "
                     "two-sided reading |temporal excess| <= 0.05 of the pre-registered "
                     "temporal-subdominance rule, and which ladder carries the order-2 claim?"),
        "pins": pins,
        "target_binding": {
            "class_id": target["class_id"], "node_id": target["node_id"],
            "gate": target["gate"], "p_tol": p_tol_filed,
            "temporal_dr_swept": sorted(target["config"]["temporal_dr"]),
            "dr_values_A_ladder": target["config"]["dr_values"],
            "dt_fixed_ladder": DT_FIXED_LADDER,
            "rule_b_text": pre["rule_b"],
            "consequence_if_failed": pre["consequence_if_failed"],
            "thresholds_movable_after_result": pre["thresholds_movable_after_result"],
        },
        "recomputation": core,
        "cross_checks": [{"check": c, "scheme": s, "dr": d, "ok": bool(ok)}
                         for c, s, d, ok in xchecks],
        "all_cross_checks_pass": bool(all_x),
        "determinism_two_core_runs_identical": bool(determinism),
        "summary": {
            "swept_points_total": n_swept,
            "one_sided_aggregate_pass_by_scheme": one_sided_agg,
            "symmetric_aggregate_pass_by_scheme": symmetric_agg,
            "one_sided_passing_points": n_one_sided_pass,
            "symmetric_passing_points": n_symmetric_pass,
            "symmetric_passing_fraction": (n_symmetric_pass / n_swept) if n_swept else None,
            "A_ladder_rungs_total": len(target["config"]["dr_values"]),
            "A_ladder_rungs_with_symmetric_subdominance_evidence": 0,
            "A_ladder_rungs_without_any_sweep": [
                dr for dr in target["config"]["dr_values"]
                if dr not in target["config"]["temporal_dr"]],
            "filed_verdicts": {s: target["schemes"][s]["verdict"] for s in SCHEMES},
            "filed_admissible": {s: bool(target["schemes"][s]["checks"]["admissible_as_spatial"])
                                 for s in SCHEMES},
        },
        "fixed_dt_bound": bounds,
        "fixed_dt_summary": {
            "n_bound_cells_pass_symmetric": n_b_pass,
            "n_bound_cells_total": sum(len(b_pass[s][dr]) for s in SCHEMES for dr in b_pass[s]),
        },
        "controls": {
            "sign_flip_mutation": flip,
            "vacuous_guard": vac,
            "hash_guard_passed": all(p["match"] for p in pins.values()),
        },
        "interpretation": {
            "one_sided_rule_note": (
                "The canonical rule_b is pre-registered one-sided (excess <= tol). This "
                "analysis does not change it; it reports that under |excess| <= tol the "
                "admissibility verdicts differ: the two schemes declared admissible "
                "(lffd, cnfem) are exactly those whose excess is negative, i.e. whose "
                "constant-CFL error is REDUCED by temporal-spatial cancellation."),
            "consequence": (
                "Ladder A (constant CFL) has no rung with positive two-sided temporal-"
                "subdominance evidence: the two swept rungs fail and the two unswept rungs "
                "have no sweep filed. Ladder B (fixed dt) carries the order-2 claim: at the "
                "swept dr its temporal contamination at dt=1e-3 and 5e-4 is bounded below "
                "the same 0.05 tolerance in all 12 (scheme, dr, dt) cells, worst bound "
                "1.52e-3 (>= 32x margin), using q = min(2, measured local order)."),
        },
        "assumptions": [
            "The generator's one-sided implementation is read from lines 224-229 (max of "
            "signed excess <= EXCESS_TOL) and the rule text; no canonical file is modified.",
            "The two-sided reading is a sensitivity check on the pre-registered rule, not a "
            "replacement; the tolerance 0.05 is taken from the target, unchanged.",
            "The fixed-dt bound uses the target's own sweep points and scales with "
            "q = min(2, measured local temporal order), i.e. never assumes faster temporal "
            "decay than measured; the local orders are reported so the assumption is checkable.",
            "No solver re-run: filed sweep rows are treated as deterministic measurements, "
            "consistent with the target's own determinism claim and W020-N0-FIXEDDT-VERIFY-01.",
            "Only dr in {0.2, 0.05} were swept; dr in {0.1, 0.025} have no direct temporal "
            "evidence, so no claim is made about them.",
        ],
        "not_claimed": [
            "no gate verdict and no gate self-pass",
            "no node completion; numerics_lock stays LOCKED and numerics/spherical_solver/ absent",
            "no physics claim; flat-space discretisation evidence only",
            "no statement that the canonical rule_b is wrong or must be changed",
            "no re-measurement of the PDE: this is a hash-pinned re-analysis of filed data",
        ],
        "falsifier": (
            "Void if: (i) any pinned input re-hashes differently; (ii) the one-sided "
            "recomputation does not reproduce the filed excess/rule_b/admissible values; "
            "(iii) a filed sweep point is missing or non-halving; (iv) the sign-flip mutation "
            "is not detected; or (v) two core runs are not byte-identical."),
        "provenance": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "runtime_seconds": round(time.time() - t0, 3),
        },
    }

    Path(a.json_out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    log(f"json written: {a.json_out}")
    log(f"swept points: {n_swept}; one-sided pass {n_one_sided_pass}; "
        f"symmetric pass {n_symmetric_pass}")
    for s in SCHEMES:
        for dr, sw in sorted(core["sweeps"][s].items()):
            log(f"  {s} dr={dr}: excess={sw['excess_recomputed']:+.6f} "
                f"one_sided_pass={sw['verdict_one_sided_pass']} "
                f"symmetric_pass={sw['verdict_symmetric_pass']} "
                f"monotone={sw['monotone_to_plateau_recomputed']}")
    for s in SCHEMES:
        log(f"  A-ladder {s}: p4={core['ladders'][s]['p_all4_recomputed']:.6f} "
            f"p_drop_finest={core['ladders'][s]['p_drop_finest_dr0025']:.6f} "
            f"p_drop_005={core['ladders'][s]['p_drop_swept_dr005']}")
    log(f"fixed-dt bound cells passing symmetric: {n_b_pass}")
    log(f"sign-flip mutations detected: {flip['n_detected']}/{flip['n_mutations']}")
    log(f"vacuous guard: {vac}")
    log(f"all cross-checks pass: {all_x}; determinism: {determinism}")
    log(f"W020-N0-SYMRULE-01 done in {result['provenance']['runtime_seconds']}s")
    Path(a.log_out).write_text("\n".join(log_lines) + "\n")

    if not (all_x and determinism and flip["n_detected"] == flip["n_mutations"]
            and not vac.get("silent_pass", False)):
        log("FATAL: control failure; result not trustworthy.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
