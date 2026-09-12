#!/usr/bin/env python3
"""W14-GNUM-NORMROBUST-01: is the N0 4-rung order claim robust to the error norm?

Motivation (astra-lead-numerics review lnum-review-three-scheme-r1r5-20260912T002216):
the three registered per-scheme 4-rung reports fit the L_infinity error series, while
the lead's certified addendum numerics/tests/n0_order_4rung.json fits the L2 integral
norm.  The reviewer recorded a "norm caveat that must travel with the numbers": the two
fits must not be quoted as numerically identical.  This checker turns that caveat into a
measured, falsifiable number:

  * Q1  does the fitted order stay inside 2.0 +/- 0.3 under BOTH norms for all schemes?
  * Q2  does R5 pairwise agreement hold under BOTH norms?
  * Q3  how large is the per-scheme |p_Linf - p_L2| relative to the R5 floor 0.25, and
        does the L2 recomputation reproduce the lead addendum's L2 orders?

Read-only: no file outside artifacts/worker-14/ is written; the three reports and the
addendum are inputs, never edited.  Deterministic: no RNG, no wall-clock in any number.

Exit codes: 0 = report written; 2 = pinned-input hash drift (measurement void).
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../ai4math-swarm

# Pinned inputs: full sha256 as registered/published; any drift voids the measurement.
PINS = {
    "reports": {
        "numerics/protocol/report_lffd_4rung.json":
            "3166dcf82c148d7760c3163b3605bd953210a13622745b4a129f42ea7ac9da5d",
        "numerics/protocol/report_cnfd_4rung.json":
            "8ec024c6b711fd92dea42fae163c5ac0890d68609ac02ec53c0289a4015ba384",
        "numerics/protocol/report_cnfem_4rung.json":
            "5514e51f81ce1963ef2deb57ea554d50f97df92b9cfcc2f8f37fd8740abc332f",
    },
    "addendum": ("numerics/tests/n0_order_4rung.json",
                 "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a"),
    "frozen_module": ("numerics/tests/flat_wave_replication.py",
                      "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"),
    "summary": ("numerics/protocol/three_scheme_r1r5_summary.json",
                "6e1ded36be6f14406276bdea8e29eb4cafa9c3aac4b12cbc369cc8157192484e"),
}
SCHEMES = ("lffd", "cnfd", "cnfem")
P_EXPECTED = 2.0
P_TOL = 0.3                 # rubric/order tolerance, from n0_order_4rung.json config
R5_FLOOR = 0.25             # R5 pairwise agreement floor
LSQ_ABS_TOL = 1e-12         # control C1: recomputed L_inf fit == published fitted_order
ADDENDUM_TOL = 1e-2         # control C2: L2 recomputation == lead addendum L2 order


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_order(drs, errs):
    """Replicate build_three_scheme_reports.py:168-179 exactly (polyfit slope + SE)."""
    hs = np.array([float(h) for h in drs])
    es = np.array([float(e) for e in errs])
    x, y = np.log(hs), np.log(es)
    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    se = float(math.sqrt(float(np.sum(resid ** 2) / max(n - 2, 1)) /
                         float(np.sum((x - x.mean()) ** 2))))
    pairs = [math.log(es[i] / es[i + 1]) / math.log(hs[i] / hs[i + 1])
             for i in range(len(es) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0
    delta = max(se, half)
    return {
        "pairs": [float(p) for p in pairs],
        "fit_order": float(slope),
        "standard_error": se,
        "pair_spread_half_range": float(half),
        "delta_r5": float(delta),
        "monotone": bool(all(p > 0 for p in pairs)),
    }


def r5_agree(a, b):
    bound = max(R5_FLOOR, math.sqrt(a["delta_r5"] ** 2 + b["delta_r5"] ** 2))
    return {
        "schemes": sorted([a["scheme"], b["scheme"]]),
        "abs_order_diff": abs(a["fit_order"] - b["fit_order"]),
        "r5_bound": float(bound),
        "agree": bool(abs(a["fit_order"] - b["fit_order"]) <= bound),
    }


def main() -> int:
    t0 = time.time()
    measured = {}
    for path, want in PINS["reports"].items():
        got = sha256_file(ROOT / path)
        measured[path] = got
        if got != want:
            print(f"REFUSE: {path} sha256 {got} != pinned {want}")
            return 2
    for key in ("addendum", "frozen_module", "summary"):
        path, want = PINS[key]
        got = sha256_file(ROOT / path)
        measured[path] = got
        if got != want:
            print(f"REFUSE: {path} sha256 {got} != pinned {want}")
            return 2

    addendum = json.loads((ROOT / PINS["addendum"][0]).read_text())
    addendum_orders = {k: float(v) for k, v in addendum["verdict"]["orders"].items()}
    addendum_deltas = {k: float(v) for k, v in addendum["verdict"]["delta"].items()}

    studies = {}
    for scheme in SCHEMES:
        rep = json.loads((ROOT / f"numerics/protocol/report_{scheme}_4rung.json").read_text())
        drs = [row["dr"] for row in rep["rows"]]
        assert len(drs) == 4 and rep["rung_count"] == 4, f"{scheme}: not 4 rungs"
        entry = {
            "report_sha256": measured[f"numerics/protocol/report_{scheme}_4rung.json"],
            "report_error_norm_fitted": rep["error_norm_fitted"],
            "dr_values": drs,
            "errors": {
                "linf": [float(e) for e in rep["linf_errors"]],
                "l2": [float(e) for e in rep["l2_errors"]],
            },
            "published_linf_fit_order": float(rep["fitted_order"]),
            "published_linf_delta": float(rep["delta"]),
            "addendum_l2_fit_order": addendum_orders[scheme],
            "addendum_l2_delta": addendum_deltas[scheme],
            "fits": {norm: fit_order(drs, entry_errors)
                     for norm, entry_errors in {"linf": rep["linf_errors"],
                                                "l2": rep["l2_errors"]}.items()},
        }
        # C1: the L_inf recomputation must reproduce the published fit exactly.
        entry["control_C1_linf_match_published"] = bool(
            abs(entry["fits"]["linf"]["fit_order"] - entry["published_linf_fit_order"])
            <= LSQ_ABS_TOL)
        # C2: the L2 recomputation must reproduce the lead addendum's L2 fit.
        entry["control_C2_l2_match_addendum"] = bool(
            abs(entry["fits"]["l2"]["fit_order"] - entry["addendum_l2_fit_order"])
            <= ADDENDUM_TOL)
        entry["cross_norm_abs_order_diff"] = abs(
            entry["fits"]["linf"]["fit_order"] - entry["fits"]["l2"]["fit_order"])
        entry["within_2pm03"] = {
            norm: bool(abs(f["fit_order"] - P_EXPECTED) <= P_TOL)
            for norm, f in entry["fits"].items()}
        studies[scheme] = entry

    # Controls: the same machinery must flag a wrong order and a non-monotone series.
    neg_wrong_order = {}
    neg_non_monotone = {}
    for scheme in SCHEMES:
        drs = studies[scheme]["dr_values"]
        linf = studies[scheme]["errors"]["linf"]
        sqrt_errs = [math.sqrt(e) for e in linf]           # p -> p/2, i.e. ~order 1
        neg_wrong_order[scheme] = {
            "control": "sqrt(error series): order halved",
            "fit": fit_order(drs, sqrt_errs),
        }
        neg_wrong_order[scheme]["flagged"] = bool(
            abs(neg_wrong_order[scheme]["fit"]["fit_order"] - P_EXPECTED) > P_TOL)
        rev = list(reversed(linf))
        neg_non_monotone[scheme] = {
            "control": "reversed error series",
            "fit": fit_order(drs, rev),
        }
        neg_non_monotone[scheme]["flagged"] = bool(
            not neg_non_monotone[scheme]["fit"]["monotone"])

    controls = {
        "C1_linf_reproduces_published_fit": all(
            s["control_C1_linf_match_published"] for s in studies.values()),
        "C2_l2_reproduces_lead_addendum": all(
            s["control_C2_l2_match_addendum"] for s in studies.values()),
        "NEG1_wrong_order_detected": all(
            v["flagged"] for v in neg_wrong_order.values()),
        "NEG2_non_monotone_detected": all(
            v["flagged"] for v in neg_non_monotone.values()),
    }

    agreements = {}
    for norm in ("linf", "l2"):
        rows = []
        for i, a in enumerate(SCHEMES):
            for b in SCHEMES[i + 1:]:
                ra = dict(studies[a]["fits"][norm], scheme=a)
                rb = dict(studies[b]["fits"][norm], scheme=b)
                rows.append(r5_agree(ra, rb))
        agreements[norm] = {
            "pairs": rows,
            "all_agree": bool(all(r["agree"] for r in rows)),
            "max_abs_order_diff": max(r["abs_order_diff"] for r in rows),
        }

    max_cross_norm = max(s["cross_norm_abs_order_diff"] for s in studies.values())
    norm_robust = bool(
        all(s["within_2pm03"][n] for s in studies.values() for n in ("linf", "l2"))
        and agreements["linf"]["all_agree"] and agreements["l2"]["all_agree"]
        and max_cross_norm <= R5_FLOOR
        and all(controls.values()))

    report = {
        "schema": "n0-norm-robustness-check/v1",
        "artifact_type": "n0_order_norm_robustness",
        "task_id": "W14-GNUM-NORMROBUST-01",
        "assignment_ref": "astra-numfix-03 (follow-up to lead review "
                          "lnum-review-three-scheme-r1r5-20260912T002216, norm caveat)",
        "actor": "deepseek-flash-14",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "conclusion_type_if_claimed": "numerical_evidence",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": "Is the N0 4-rung fitted order (and its cross-scheme R5 agreement) "
                    "robust to the choice of error norm, given the three registered "
                    "reports fit L_infinity and the lead addendum fits L2?",
        "pinned_inputs": measured,
        "rule": {
            "fit": "least-squares slope of log(error) vs log(dr) (polyfit), "
                   "SE = sqrt(SSE/(n-2) / sum((x-xbar)^2))",
            "delta_r5": "max(pair-spread half-range, least-squares slope SE)",
            "r5_agreement": "|pA - pB| <= max(0.25, sqrt(dA^2 + dB^2))",
            "order_tolerance": f"{P_EXPECTED} +/- {P_TOL}",
        },
        "studies": studies,
        "cross_norm_max_abs_order_diff": max_cross_norm,
        "r5_agreement": agreements,
        "negative_controls": {"NEG1_wrong_order": neg_wrong_order,
                              "NEG2_non_monotone": neg_non_monotone},
        "controls": controls,
        "verdict": {
            "norm_robust": norm_robust,
            "answer_Q1_order_within_tol_both_norms": all(
                s["within_2pm03"][n] for s in studies.values() for n in ("linf", "l2")),
            "answer_Q2_r5_agreement_both_norms": bool(
                agreements["linf"]["all_agree"] and agreements["l2"]["all_agree"]),
            "answer_Q3_cross_norm_diff_below_r5_floor": bool(max_cross_norm <= R5_FLOOR),
            "summary": ("L_inf and L2 fits agree per scheme to <= "
                        f"{max_cross_norm:.3e} order units, far below the R5 floor "
                        f"{R5_FLOOR}; all schemes stay inside {P_EXPECTED}+/-{P_TOL} and "
                        "all R5 pairs agree under both norms."
                        if norm_robust else
                        "NORM-DEPENDENCE MATERIAL: at least one control/answer failed."),
        },
        "falsifier": (
            "Falsified if, at these pinned input hashes, any scheme's L2 or L_inf fit "
            f"leaves {P_EXPECTED}+/-{P_TOL}, or any R5 pair under either norm has "
            "|dp| > max(0.25, sqrt(dA^2+dB^2)), or the L2 recomputation differs from the "
            f"lead addendum order by more than {ADDENDUM_TOL}, or the L_inf recomputation "
            f"differs from the published fitted_order by more than {LSQ_ABS_TOL}, or any "
            "pinned input's sha256 moves, or either negative control stops being flagged."),
        "does_not_claim": [
            "no G-NUM verdict and no gate self-pass; G-NUM adjudication is Astra's",
            "no N0 completion; numerics_lock stays LOCKED, N1 not started, "
            "numerics/spherical_solver absent",
            "no independent review; this worker may not review its own artifacts",
            "no physics, self-gravity, WCC or SCC claim; flat-space calibration evidence only",
            "no claim that the L_inf and L2 fits are numerically identical; the measured "
            "per-scheme difference is reported instead",
            "no edit to any other agent's artifact; all inputs were read read-only",
        ],
        "provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "runtime_seconds": round(time.time() - t0, 3),
            "deterministic": "no RNG; pure arithmetic on pinned inputs",
        },
    }

    out = HERE / "norm_robustness.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    digest = sha256_file(out)
    (HERE / "norm_robustness.json.sha256").write_text(
        f"{digest}  norm_robustness.json\n")
    print(f"wrote {out.relative_to(ROOT)} sha256={digest}")
    print(f"norm_robust={norm_robust} cross_norm_max_abs_order_diff={max_cross_norm:.6e} "
          f"controls={controls}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
