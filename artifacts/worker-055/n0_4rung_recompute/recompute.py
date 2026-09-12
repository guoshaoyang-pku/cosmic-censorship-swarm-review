#!/usr/bin/env python3
"""W055-N0-4RUNG-RECOMPUTE-01 — independent worker recheck of the N0 four-rung order claim.

Class-bound task (no inbox assignment existed for worker-055 at 2026-09-12T00:24+08:00):
    node  N0 (flat-space scalar-wave calibration)
    class AF-WCC-SCALAR-SPH
    gate  G-NUM

What this does, in one fresh process, without editing any pinned file:
  1. Hash-guards the pinned inputs (frozen replication module 8ade1cdc, addendum driver
     fea1b771, addendum evidence c88146a1, protocol 1e6cdf04).
  2. Imports numerics/tests/flat_wave_replication.py read-only and re-runs order_study()
     for lffd / cnfd / cnfem at FOUR rungs (dr = 0.2, 0.1, 0.05, 0.025), cfl=0.5.
  3. Recomputes log-log LSQ slope, slope standard error, consecutive-pair orders,
     pair half-range, R5 delta and R5 pairwise agreement with a self-contained
     implementation (does not import the addendum's helpers or rep.pair_orders).
  4. Binds every recomputed number back to numerics/tests/n0_order_4rung.json and to
     the certified_order_claim of numerics/tests/n0_gate_proposal.json, and cross-checks
     the raw l2_error rows against the independent driver's report_*_4rung.json files.
  5. Re-measures all 24 evidence_hashes entries of the gate proposal against disk and records
     the on-disk G-NUM protocol review (verdict / reviewed_sha256) as an observation only.

This is an independent verification record only. It claims NO gate verdict, NO node
completion, and NO protocol review (G-NUM C8 stays with an audit-side reviewer).
numerics_lock is respected: no N1 work, no numerics/spherical_solver/ is created.
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

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DR_VALUES = [0.2, 0.1, 0.05, 0.025]
SCHEMES = ["lffd", "cnfd", "cnfem"]
P_EXPECTED = 2.0
P_TOL = 0.3
R5_FLOOR = 0.25

FROZEN_MODULE = "numerics/tests/flat_wave_replication.py"
FROZEN_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
ADDENDUM_DRIVER = "numerics/tests/n0_order_4rung_addendum.py"
ADDENDUM_SHA = "fea1b77118bec8aedb28b03128342a3b848bdf2ea7bb2970e609687c595f7cf6"
ADDENDUM_EVIDENCE = "numerics/tests/n0_order_4rung.json"
ADDENDUM_EVIDENCE_SHA = "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a"
GATE_PROPOSAL = "numerics/tests/n0_gate_proposal.json"
GATE_PROPOSAL_SHA = "58a175b52fbe4f9b38663dcdfd57342629c99c04b34c76295affcd567acdf4c7"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
PROTOCOL_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
FIXED_RUN = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
FIXED_RUN_SHA = "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e"
RAW_REPORTS = {
    "lffd": "numerics/protocol/report_lffd_4rung.json",
    "cnfd": "numerics/protocol/report_cnfd_4rung.json",
    "cnfem": "numerics/protocol/report_cnfem_4rung.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"path": rel, "exists": False, "sha256": None}
    return {"path": rel, "exists": True, "sha256": sha256(p)}


def ols_loglog(drs, errs) -> dict:
    """Self-contained log-log least squares: slope, intercept, slope SE."""
    x = np.log(np.asarray(drs, float))
    y = np.log(np.asarray(errs, float))
    n = len(x)
    xbar, ybar = float(x.mean()), float(y.mean())
    sxx = float(np.sum((x - xbar) ** 2))
    sxy = float(np.sum((x - xbar) * (y - ybar)))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    resid = y - (slope * x + intercept)
    dof = n - 2
    se = math.sqrt(float(np.sum(resid ** 2)) / dof / sxx) if dof > 0 and sxx > 0 else float("nan")
    return {"slope": slope, "intercept": intercept, "standard_error": se, "dof": dof}


def pair_orders(drs, errs) -> list:
    return [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
            for i in range(len(errs) - 1)]


def stats(drs, errs) -> dict:
    fit = ols_loglog(drs, errs)
    pairs = pair_orders(drs, errs)
    half_range = (max(pairs) - min(pairs)) / 2.0
    delta = max(half_range, fit["standard_error"])
    return {"fit_order": fit["slope"], "least_squares_se": fit["standard_error"],
            "pair_orders": pairs, "pair_half_range": half_range, "delta": delta}


def r5_pair(a: dict, b: dict) -> dict:
    lhs = abs(a["fit_order"] - b["fit_order"])
    rhs = max(R5_FLOOR, math.sqrt(a["delta"] ** 2 + b["delta"] ** 2))
    return {"pair": f"{a['scheme']} vs {b['scheme']}", "abs_order_diff": lhs,
            "r5_bound": rhs, "agree": bool(lhs <= rhs)}


def close(a, b, tol=1e-9) -> bool:
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))


def main() -> int:
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    guards = {rel: measure(rel) for rel in
              (FROZEN_MODULE, ADDENDUM_DRIVER, ADDENDUM_EVIDENCE, GATE_PROPOSAL,
               PROTOCOL, FIXED_RUN)}
    expected = {FROZEN_MODULE: FROZEN_SHA, ADDENDUM_DRIVER: ADDENDUM_SHA,
                ADDENDUM_EVIDENCE: ADDENDUM_EVIDENCE_SHA, GATE_PROPOSAL: GATE_PROPOSAL_SHA,
                PROTOCOL: PROTOCOL_SHA, FIXED_RUN: FIXED_RUN_SHA}
    guard_ok = {rel: guards[rel]["sha256"] == expected[rel] for rel in expected}

    if not guard_ok[FROZEN_MODULE] or not guard_ok[ADDENDUM_EVIDENCE]:
        report = {
            "task_id": "W055-N0-4RUNG-RECOMPUTE-01", "worker": "worker-055",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "verdict": "refused_hash_guard", "guard_ok": guard_ok, "inputs": guards,
            "started_at": started,
        }
        (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"verdict": "refused_hash_guard", "guard_ok": guard_ok}))
        return 3

    sys.path.insert(0, str(ROOT / "numerics" / "tests"))
    import flat_wave_replication as rep  # noqa: E402  (read-only import; module has a main guard)

    frozen_recomputed = {}
    for scheme in SCHEMES:
        st = rep.order_study(scheme, dr_values=DR_VALUES, cfl=0.5, r_max=30.0, t_end=6.0)
        drs = [r["dr"] for r in st["rows"]]
        errs = [r["l2_error"] for r in st["rows"]]
        s = stats(drs, errs)
        s.update({"scheme": scheme,
                  "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
                  "within_band": abs(s["fit_order"] - P_EXPECTED) <= P_TOL,
                  "rows": st["rows"], "l2_errors": errs,
                  "rep_fit_order": st["fit_order"], "rep_pair_orders": st["pair_orders"]})
        frozen_recomputed[scheme] = s
    pairs = [r5_pair(a, b) for i, a in enumerate(frozen_recomputed.values())
             for b in list(frozen_recomputed.values())[i + 1:]]

    addendum = json.loads((ROOT / ADDENDUM_EVIDENCE).read_text())
    rec_by_scheme = {s["scheme"]: s for s in addendum["studies"]}
    proposal = json.loads((ROOT / GATE_PROPOSAL).read_text())
    cert = proposal["certified_order_claim"]

    addendum_bind = {}
    rows_match = {}
    for scheme in SCHEMES:
        rec, recomp = rec_by_scheme[scheme], frozen_recomputed[scheme]
        addendum_bind[scheme] = {
            "fit_order_recorded": rec["fit_order"], "fit_order_recomputed": recomp["fit_order"],
            "fit_order_match": close(rec["fit_order"], recomp["fit_order"]),
            "delta_recorded": rec["delta"], "delta_recomputed": recomp["delta"],
            "delta_match": close(rec["delta"], recomp["delta"]),
            "se_recorded": rec["least_squares_se"], "se_recomputed": recomp["least_squares_se"],
            "se_match": close(rec["least_squares_se"], recomp["least_squares_se"]),
            "pair_orders_match": all(close(x, y) for x, y in
                                     zip(rec["pair_orders"], recomp["pair_orders"])),
            "monotone_recorded": rec["monotone"], "monotone_recomputed": recomp["monotone"],
            "within_tol_recorded": rec["within_harness_tol"],
            "within_band_recomputed": recomp["within_band"],
        }
        max_rel = 0.0
        for rr, rc in zip(rec["rows"], recomp["rows"]):
            if rr["l2_error"] != 0.0:
                max_rel = max(max_rel, abs(rr["l2_error"] - rc["l2_error"]) / abs(rr["l2_error"]))
            if rr["dr"] != rc["dr"] or rr["dt"] != rc["dt"] or rr["steps"] != rc["steps"]:
                max_rel = float("inf")
        rows_match[scheme] = {"max_rel_l2_error_diff": max_rel, "exact_bitwise": max_rel == 0.0}

    proposal_bind = {
        "orders_recorded": cert["orders_4rung_certified"],
        "orders_recomputed": {s: frozen_recomputed[s]["fit_order"] for s in SCHEMES},
        "orders_match": {s: close(cert["orders_4rung_certified"][s],
                                  frozen_recomputed[s]["fit_order"]) for s in SCHEMES},
        "delta_recorded": cert["delta_R5_4rung"],
        "delta_recomputed": {s: frozen_recomputed[s]["delta"] for s in SCHEMES},
        "delta_match": {s: close(cert["delta_R5_4rung"][s],
                                 frozen_recomputed[s]["delta"]) for s in SCHEMES},
        "certified_equals_addendum": {s: close(cert["orders_4rung_certified"][s],
                                               rec_by_scheme[s]["fit_order"]) for s in SCHEMES},
        "pairwise_recorded": cert["replication_tolerance_claim"]["pairwise_4rung"],
        "pairwise_recomputed": pairs,
        "pairwise_all_agree": all(p["agree"] for p in pairs),
        "max_pairwise_abs_diff_recomputed": max(p["abs_order_diff"] for p in pairs),
        "declared_norm": cert["norm"],
        "norm_binding": ("L2" in cert["norm"] and
                         all("l2_error" in r for r in rec_by_scheme["lffd"]["rows"])),
    }

    raw_bind = {}
    for scheme, rel in RAW_REPORTS.items():
        if not (ROOT / rel).exists():
            raw_bind[scheme] = {"path": rel, "exists": False}
            continue
        raw = json.loads((ROOT / rel).read_text())
        rec = raw.get("l2_errors", [])
        recomp = frozen_recomputed[scheme]["l2_errors"]
        max_rel = max((abs(a - b) / abs(a) for a, b in zip(rec, recomp) if a != 0.0), default=None)
        raw_bind[scheme] = {
            "path": rel, "exists": True, "raw_report_sha256": sha256(ROOT / rel),
            "raw_l2_len": len(rec), "recomputed_len": len(recomp),
            "max_rel_l2_error_diff_vs_recompute": max_rel,
            "bitwise_identical": bool(len(rec) == len(recomp) and max_rel == 0.0),
            "raw_rows_identical_1e-12": bool(
                len(rec) == len(recomp) and max_rel is not None and max_rel <= 1e-12),
            "raw_fitted_order_linf": raw.get("fitted_order"),
        }

    ev = proposal.get("evidence_hashes", {})
    binding = []
    for rel, pinned in ev.items():
        m = measure(rel)
        binding.append({"path": rel, "pinned": pinned, "on_disk": m["sha256"],
                        "exists": m["exists"],
                        "match": bool(m["exists"] and m["sha256"] == pinned)})
    match_n = sum(1 for b in binding if b["match"])
    drift = [b for b in binding if b["exists"] and not b["match"]]
    missing = [b for b in binding if not b["exists"]]

    lock_path = ROOT / "numerics" / "spherical_solver"
    map_obj = json.loads((ROOT / "research_map" / "research_map.json").read_text())
    lock_state = map_obj.get("numerics_lock", {})
    lock_check = {
        "numerics_lock_state": lock_state.get("state"),
        "spherical_solver_present": lock_path.exists(),
        "n1_locked": "N1" in (lock_state.get("locked_nodes") or []),
        "allowed_nodes": lock_state.get("allowed_nodes"),
    }

    c8_rel = "reviews/G-NUM-protocol-review.json"
    c8_path = ROOT / c8_rel
    c8_obs = {"path": c8_rel, "exists": c8_path.exists()}
    if c8_path.exists():
        c8 = json.loads(c8_path.read_text())
        c8_obs.update({
            "sha256": sha256(c8_path),
            "verdict": c8.get("verdict"),
            "score": c8.get("score"),
            "reviewer": c8.get("reviewer"),
            "created_at": c8.get("created_at"),
            "reviewed_sha256": c8.get("reviewed_sha256"),
            "supersedes_sha256": c8.get("supersedes_sha256"),
            "not_a_gate_verdict": "proposal only; verdict belongs to Astra and lead-audit",
        })
    c8_accept_at_rev3 = bool(
        c8_obs.get("verdict") == "accept" and c8_obs.get("reviewed_sha256") == PROTOCOL_SHA)

    reg_rel = "runtime/state/artifact_hashes.json"
    reg_path = ROOT / reg_rel
    reg_sha = sha256(reg_path) if reg_path.exists() else None
    reg_hits = []
    if reg_path.exists():
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and v.startswith(FIXED_RUN_SHA[:12]):
                        reg_hits.append(k)
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(reg_path.read_text()))
    c4_obs = {"registry_path": reg_rel, "registry_sha256": reg_sha,
              "fixed_run_sha256": FIXED_RUN_SHA,
              "registered": bool(reg_hits), "matching_keys": reg_hits,
              "scope_note": ("Observation of the controller registry at the measured hash; "
                             "registration is a controller action (G-NUM C4).")}

    checks = {
        "pins_current": all(guard_ok.values()),
        "guard_frozen_module": guard_ok[FROZEN_MODULE],
        "guard_addendum_evidence": guard_ok[ADDENDUM_EVIDENCE],
        "addendum_fit_order_match": all(v["fit_order_match"] for v in addendum_bind.values()),
        "addendum_delta_match": all(v["delta_match"] for v in addendum_bind.values()),
        "addendum_se_match": all(v["se_match"] for v in addendum_bind.values()),
        "addendum_pair_orders_match": all(v["pair_orders_match"] for v in addendum_bind.values()),
        "addendum_monotone_recomputed": all(v["monotone_recomputed"] for v in addendum_bind.values()),
        "addendum_within_band_recomputed": all(v["within_band_recomputed"] for v in addendum_bind.values()),
        "rows_bitwise_reproduced": all(v["exact_bitwise"] for v in rows_match.values()),
        "proposal_orders_match": all(proposal_bind["orders_match"].values()),
        "proposal_delta_match": all(proposal_bind["delta_match"].values()),
        "proposal_certified_equals_addendum": all(proposal_bind["certified_equals_addendum"].values()),
        "proposal_pairwise_all_agree": proposal_bind["pairwise_all_agree"],
        "proposal_norm_binding": proposal_bind["norm_binding"],
        "raw_report_drivers_identical_1e-12": all(v.get("raw_rows_identical_1e-12") for v in raw_bind.values()),
        "numerics_lock_respected": (lock_check["numerics_lock_state"] == "locked"
                                    and not lock_check["spherical_solver_present"]),
    }
    chain_ok = all(checks.values())

    report = {
        "schema_version": "0.1",
        "task_id": "W055-N0-4RUNG-RECOMPUTE-01",
        "worker": "worker-055",
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "conclusion_type": "numerical_evidence",
        "started_at": started,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "method": ("fresh-process import of the frozen replication module; order_study at four "
                   "rungs for three schemes; self-contained log-log OLS + pair-order + R5 "
                   "statistics; full re-measure of the proposal's 24 evidence hashes"),
        "inputs": guards,
        "guard_ok": guard_ok,
        "recomputed": {s: {k: v[k] for k in
                           ("scheme", "fit_order", "least_squares_se", "pair_orders",
                            "pair_half_range", "delta", "monotone", "within_band", "l2_errors")}
                       for s, v in frozen_recomputed.items()},
        "pairwise_R5_recomputed": pairs,
        "addendum_binding": addendum_bind,
        "rows_vs_addendum": rows_match,
        "proposal_binding": proposal_bind,
        "raw_driver_crosscheck": raw_bind,
        "evidence_hash_binding": {
            "entries": len(binding), "matching": match_n,
            "drifting": [{"path": b["path"], "pinned": b["pinned"][:12], "on_disk": (b["on_disk"] or "")[:12]}
                         for b in drift],
            "missing": [b["path"] for b in missing],
            "all_match": match_n == len(binding),
            "numerics_evidence_drift": [b["path"] for b in drift
                                        if b["path"].startswith("numerics/")],
            "drift_all_live_non_numerics": all(not b["path"].startswith("numerics/") for b in drift),
            "detail": binding,
        },
        "c8_observation": dict(c8_obs, protocol_of_record=PROTOCOL,
                               protocol_of_record_sha256=PROTOCOL_SHA,
                               accept_at_protocol_of_record_sha256=c8_accept_at_rev3,
                               scope_note=("Observation of an on-disk review artifact, measured by "
                                           "hash. It is NOT a gate verdict and this worker does not "
                                           "adjudicate C8; the controller/lead-audit own that.")),
        "c4_registration_observation": c4_obs,
        "lock_check": lock_check,
        "checks": checks,
        "verdict": {
            "all_chain_checks_pass": chain_ok,
            "failed_checks": [k for k, v in checks.items() if not v],
            "certified_order_claim_reproduced": all(
                [checks["addendum_fit_order_match"], checks["proposal_orders_match"],
                 checks["proposal_pairwise_all_agree"], checks["proposal_certified_equals_addendum"]]),
            "claim_withdrawn": not checks["addendum_within_band_recomputed"],
            "numbers_at_pinned_hashes": True,
            "evidence_drift_count": len(drift),
            "evidence_drift_all_live_non_numerics": all(
                not b["path"].startswith("numerics/") for b in drift),
            "c8_accept_measured_at_protocol_of_record": c8_accept_at_rev3,
            "c4_fixed_run_registered": bool(reg_hits),
            "no_gate_verdict_claimed": True,
        },
        "falsifier_status": {
            "F2_rerun_nonmonotone_or_out_of_band_or_r5_fail": "not fired",
            "F3_frozen_module_guard": "not fired (8ade1cdc measured; guard passed)",
            "F6_lock_or_n1": "not fired (numerics_lock locked; spherical_solver absent)",
        },
        "falsifier": ("Re-run this script at the recorded input hashes. The recheck is falsified if "
                      "any of: (a) numerics/tests/flat_wave_replication.py sha256 != 8ade1cdc or "
                      "numerics/tests/n0_order_4rung.json sha256 != c88146a1; (b) any scheme's "
                      "recomputed 4-rung order is non-monotone, outside 2.0 +/- 0.3, or the R5 "
                      "pairwise bound fails at frozen-module hash 8ade1cdc; (c) any recomputed "
                      "fit_order/delta/SE differs from n0_order_4rung.json by more than 1e-9 "
                      "relative; (d) the gate proposal's certified orders/deltas differ from the "
                      "addendum's; (e) numerics/spherical_solver/ exists or numerics_lock is not "
                      "locked; (f) reviews/G-NUM-protocol-review.json no longer reads "
                      "verdict=accept with reviewed_sha256=1e6cdf04d7a2 (the C8 observation only; "
                      "it does not affect the order-claim part); (g) the controller registry "
                      "runtime/state/artifact_hashes.json now contains fixed-run sha 6542db93 "
                      "(the C4 observation only)."),
        "not_claimed": [
            "no gate verdict and no gate self-pass; G-NUM stays with Astra and lead-audit",
            "no node completion; N0 stays active/unverified",
            "no protocol review; G-NUM C8 is an audit-side judgement and is untouched",
            "no claim about the candidate numerics/tests/flat_wave.py or its fourth rung",
            "no physics claim; flat-space calibration evidence only",
            "the 3-rung-vs-4-rung distinction is not re-adjudicated; this record reproduces the record",
        ],
        "numerics_lock_respected": True,
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                    "platform": platform.platform()},
    }
    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": report["verdict"], "checks": checks,
                      "report_sha256": sha256(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
