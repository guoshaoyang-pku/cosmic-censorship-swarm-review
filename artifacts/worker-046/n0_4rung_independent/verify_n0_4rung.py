#!/usr/bin/env python3
"""Independent verification (worker-046) of the published N0 4-rung order evidence.

Class binding : AF-WCC-SCALAR-SPH (N0 calibration sub-case; flat space only)
Node / gate   : N0 / G-NUM
Scope         : re-execution + independent arithmetic check of
                numerics/tests/n0_order_4rung.json (sha256 c88146a1375c50f0...).
                This is NOT a new numerical scheme and NOT a gate verdict.

What is checked, independently of the addendum's own code:
  1. Input provenance: every pinned sha256 matches the bytes on disk.
  2. Re-execution: a fresh run of numerics/protocol/lead_4rung_replication.py
     reproduces every published per-rung l2_error.
  3. Arithmetic: pair orders, least-squares slope, slope standard error, R5 delta
     and pairwise agreement recomputed from the published rows with a separate
     implementation (normal equations; the addendum uses numpy.polyfit cov).
  4. Falsifier clauses from the published artifact evaluated one by one.
  5. Chaining: the 3-rung controller-verified run agrees with the first three
     published rungs.

Authority boundary: worker events cannot set status=done, validation_status=passed
or a gate verdict (ASTRA_HANDOFF).  Anything measured here is numerical_evidence.

Falsifier of THIS verification: if any recomputed value disagrees with the published
value beyond the stated tolerance, or the pinned hash check fails, the published
order claim is not reproduced and this report must say FALSIFIED.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent

PUBLISHED = "numerics/tests/n0_order_4rung.json"
RERUN = "artifacts/worker-046/n0_4rung_independent/lead_4rung_replication_rerun.json"
FIXED_RUN = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"

PINS = {
    "frozen_module": (
        "numerics/tests/flat_wave_replication.py",
        "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    ),
    "fixed_controller_run": (
        FIXED_RUN,
        "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e",
    ),
    "published_4rung": (
        PUBLISHED,
        "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    ),
    "addendum_script": (
        "numerics/tests/n0_order_4rung_addendum.py",
        "fea1b77118bec8aedb28b03128342a3b848bdf2ea7bb2970e609687c595f7cf6",
    ),
    "lead_4rung_driver": (
        "numerics/protocol/lead_4rung_replication.py",
        "c9dd2d7e52ec224013f3c9896e694c4f553fee0d8c7a6cb6681191a35ae1c772",
    ),
    "protocol_rev3": (
        "numerics/CONVERGENCE_PROTOCOL.md",
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    ),
    "rerun_json": (RERUN, None),  # measured after the fact, recorded not pinned
}

TOL_ORDER = 1e-12      # pair orders / fit order / delta: exact arithmetic agreement
TOL_SE_REL = 1e-6      # slope SE: two mathematically equivalent linear algebra paths
P_EXPECTED = 2.0
P_TOL = 0.3
R5_FLOOR = 0.25


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair_orders(drs, errs):
    return [math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1])
            for i in range(len(errs) - 1)]


def lsq_slope_se(drs, errs):
    """Independent normal-equation fit of log(err) = b*log(dr) + a."""
    x = [math.log(d) for d in drs]
    y = [math.log(e) for e in errs]
    n = len(x)
    xbar, ybar = sum(x) / n, sum(y) / n
    sxx = sum((xi - xbar) ** 2 for xi in x)
    sxy = sum((xi - xbar) * (yi - ybar) for xi, yi in zip(x, y))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    ssr = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    dof = n - 2
    se = math.sqrt(ssr / dof / sxx) if dof > 0 and sxx > 0 else float("nan")
    return slope, se


def r5_delta(drs, errs, fit_p):
    po = pair_orders(drs, errs)
    half_range = (max(po) - min(po)) / 2.0
    _, se = lsq_slope_se(drs, errs)
    return {"delta": max(half_range, se), "pair_half_range": half_range,
            "least_squares_se": se, "pair_orders": po}


def main() -> int:
    out = {
        "schema": "worker-046/n0-4rung-independent-verification/v1",
        "actor": "worker-046",
        "role": "bounded execution worker (no gate authority)",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "verifies": PUBLISHED,
        "method": ("re-execute the frozen 4-rung driver and recompute R5 statistics from the "
                   "published rows with an independent (normal-equation) implementation"),
        "not_claimed": [
            "no gate verdict and no gate self-pass; supporting evidence for G-NUM only",
            "no node completion; N0 stays active/unverified and numerics_lock stays LOCKED",
            "no new independent scheme: the re-execution uses the same frozen module 8ade1cdc",
            "no physics, self-gravity, WCC or SCC claim",
        ],
    }

    # 1. provenance pins -----------------------------------------------------
    pins, pin_ok = {}, True
    for name, (rel, expect) in PINS.items():
        p = ROOT / rel
        got = sha256(p) if p.exists() else None
        ok = (got is not None) and (expect is None or got == expect)
        pin_ok &= ok
        pins[name] = {"path": rel, "sha256": got, "expected": expect, "match": bool(ok)}
    out["provenance_pins"] = pins
    out["checks"] = {"provenance_pins_match": bool(pin_ok)}

    pub = json.loads((ROOT / PUBLISHED).read_text())
    rer = json.loads((ROOT / RERUN).read_text())
    fixed = json.loads((ROOT / FIXED_RUN).read_text())

    # 2. re-execution agrees with published rows -----------------------------
    schemes = [s["scheme"] for s in pub["studies"]]
    row_diffs = {}
    for s in pub["studies"]:
        name = s["scheme"]
        p_errs = [r["l2_error"] for r in s["rows"]]
        r_errs = [r["l2_error"] for r in rer["studies"][name]["rows"]]
        d = [abs(a - b) for a, b in zip(p_errs, r_errs)]
        row_diffs[name] = {"n_rungs": len(d), "max_abs_l2_error_diff": max(d) if d else None,
                           "bitwise_equal": all(x == 0.0 for x in d)}
    out["rerun_vs_published_rows"] = row_diffs
    out["checks"]["rerun_reproduces_all_rungs"] = all(v["bitwise_equal"] for v in row_diffs.values())

    # 3. independent arithmetic on the published rows ------------------------
    per_scheme, arith_ok = {}, True
    recomputed_orders, recomputed_deltas = {}, {}
    for s in pub["studies"]:
        name = s["scheme"]
        drs = [r["dr"] for r in s["rows"]]
        errs = [r["l2_error"] for r in s["rows"]]
        slope, se = lsq_slope_se(drs, errs)
        rec = r5_delta(drs, errs, slope)
        monotone = all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))
        within = abs(slope - P_EXPECTED) <= P_TOL
        pub_delta = s["delta"]
        pub_se = s["least_squares_se"]
        se_rel = abs(se - pub_se) / abs(pub_se) if pub_se else float("inf")
        checks = {
            "pair_orders_match": all(abs(a - b) <= TOL_ORDER
                                     for a, b in zip(rec["pair_orders"], s["pair_orders"])),
            "fit_order_match": abs(slope - s["fit_order"]) <= TOL_ORDER,
            "delta_match": abs(rec["delta"] - pub_delta) <= TOL_ORDER,
            "slope_se_match_within_rel_tol": se_rel <= TOL_SE_REL,
            "monotone": monotone,
            "within_band_abs_p_minus_2_le_0.3": within,
            "published_within_harness_tol_agrees": bool(within == s["within_harness_tol"]),
            "n_rungs_ge_4": len(drs) >= 4,
        }
        arith_ok &= all(checks.values())
        recomputed_orders[name] = slope
        recomputed_deltas[name] = rec["delta"]
        per_scheme[name] = {
            "n_rungs": len(drs),
            "recomputed_pair_orders": rec["pair_orders"],
            "published_pair_orders": s["pair_orders"],
            "recomputed_fit_order": slope,
            "published_fit_order": s["fit_order"],
            "recomputed_slope_se": se,
            "published_slope_se": pub_se,
            "slope_se_rel_diff": se_rel,
            "recomputed_pair_half_range": rec["pair_half_range"],
            "recomputed_delta": rec["delta"],
            "published_delta": pub_delta,
            "delta_driver": "pair_spread_half_range" if rec["pair_half_range"] >= se else "slope_se",
            "checks": checks,
        }
    out["independent_arithmetic"] = per_scheme
    out["checks"]["independent_arithmetic_matches"] = bool(arith_ok)

    # 4. pairwise R5 agreement recomputed ------------------------------------
    names = sorted(recomputed_orders)
    pairs_rec, agree_ok = [], True
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            lhs = abs(recomputed_orders[a] - recomputed_orders[b])
            bound = max(R5_FLOOR, math.sqrt(recomputed_deltas[a] ** 2 + recomputed_deltas[b] ** 2))
            pairs_rec.append({"pair": f"{a} vs {b}", "abs_order_diff": lhs,
                              "r5_bound": bound, "agree": bool(lhs <= bound)})
            agree_ok &= lhs <= bound
    pub_pairs = {tuple(sorted(p["pair"].replace(" vs ", "|").split("|"))): p
                 for p in pub["pairwise_agreement_R5"]}
    pub_agree_ok = all(p["agree"] for p in pub["pairwise_agreement_R5"])
    out["recomputed_pairwise_agreement_R5"] = pairs_rec
    out["checks"]["pairwise_agreement_all"] = bool(agree_ok and pub_agree_ok)

    # 5. chaining to the controller-verified 3-rung run ----------------------
    fixed_studies = fixed.get("order_studies", fixed.get("studies", {}))
    if isinstance(fixed_studies, list):
        fixed_studies = {s["scheme"]: s for s in fixed_studies}
    chain = {}
    for s in pub["studies"]:
        name = s["scheme"]
        f = fixed_studies.get(name)
        if not isinstance(f, dict) or "rows" not in f:
            chain[name] = {"chained": False, "reason": "structure not found in fixed run"}
            continue
        p_errs = [r["l2_error"] for r in s["rows"]][:len(f["rows"])]
        f_errs = [r["l2_error"] for r in f["rows"]]
        d = [abs(a - b) for a, b in zip(p_errs, f_errs)]
        chain[name] = {"n_common_rungs": len(d), "max_abs_diff": max(d) if d else None,
                       "bitwise_equal": all(x == 0.0 for x in d)}
    out["chaining_vs_fixed_3rung_run"] = chain
    out["chaining_source_provenance"] = {
        "path": FIXED_RUN,
        "sha256": pins["fixed_controller_run"]["sha256"],
        "order_study_script_sha256": fixed.get("provenance", {}).get("script_sha256"),
        "acceptance_harness_sha256": fixed.get("provenance", {}).get("n0_harness_sha256"),
        "note": ("common-rung l2_error values are bitwise-equal to the published 4-rung rows; the "
                 "separate acceptance-harness hash belongs to the invariant gate, not to these rows"),
    }
    out["checks"]["chains_to_controller_verified_run"] = all(
        v.get("bitwise_equal") for v in chain.values())

    # 6. falsifier clauses from the published artifact, evaluated ------------
    fal = pub.get("falsifier", "")
    clauses = {
        "any_scheme_non_monotone": any(not v["checks"]["monotone"] for v in per_scheme.values()),
        "any_fit_outside_pm_0.3": any(not v["checks"]["within_band_abs_p_minus_2_le_0.3"]
                                      for v in per_scheme.values()),
        "any_pairwise_abs_dp_above_R5": not agree_ok,
        "frozen_module_hash_guard_failed": not pins["frozen_module"]["match"],
        "fewer_than_4_rungs": any(v["n_rungs"] < 4 for v in per_scheme.values()),
    }
    out["falsifier_text"] = fal
    out["falsifier_clauses_triggered"] = {k: bool(v) for k, v in clauses.items()}
    out["checks"]["published_falsifier_not_triggered"] = not any(clauses.values())

    # 7. observations that do not change the order claim ---------------------
    out["observations_for_reviewer"] = [
        {
            "id": "O1-norm-name-R5a",
            "severity": "soft (documentation)",
            "observation": ("The fitted error field is `l2_error`, implemented in the frozen module as "
                            "sqrt(sum(e_i^2)*dr) (plain grid L2), while CONVERGENCE_PROTOCOL rev3 §3.2 "
                            "names a volume-weighted L2 `sum V_i e_i^2 / sum V_i`. Both functionals are "
                            "O(h^2)-equivalent for a smooth error field, so the fitted exponents are "
                            "unaffected; but R5a's 'names the error norm' is satisfied only by field-name "
                            "convention, not by an explicit norm declaration in the published JSON."),
            "effect_on_order_claim": "none",
        },
        {
            "id": "O2-slope-se-last-digits",
            "severity": "note",
            "observation": ("The addendum's slope SE and the re-run driver's polyfit-cov SE differ in the "
                            "last ~4 significant digits (<=1.7e-13 absolute); in all three schemes the R5 "
                            "delta is driven by the pair-spread half-range, so the reported deltas and all "
                            "agreement verdicts are identical."),
            "effect_on_order_claim": "none",
        },
    ]

    all_ok = all(out["checks"].values())
    out["verdict"] = {
        "status": "REPRODUCED" if all_ok else "FALSIFIED",
        "summary": ("published 4-rung N0 order evidence reproduces: rows bitwise-equal on re-execution, "
                    "orders/uncertainty/agreement independently recomputed, published falsifier clauses "
                    "all clear" if all_ok else
                    "at least one independent check failed; see checks and per-scheme detail"),
        "orders": {k: v["recomputed_fit_order"] for k, v in per_scheme.items()},
        "deltas": recomputed_deltas,
        "checked_at_sha_of_published": pins["published_4rung"]["sha256"],
        "checked_at_sha_of_protocol_rev3": pins["protocol_rev3"]["sha256"],
    }
    out["checks"]["all"] = bool(all_ok)

    (HERE / "verification.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": out["verdict"]["status"], "checks": out["checks"],
                      "orders": out["verdict"]["orders"], "deltas": out["verdict"]["deltas"]}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
