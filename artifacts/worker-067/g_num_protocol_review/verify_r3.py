#!/usr/bin/env python3
"""Independent verification of numerics/CONVERGENCE_PROTOCOL.md rev3 (G-NUM C8).

Reviewer: worker-067 (breadth worker; author of no N0 artifact).
Writes only under artifacts/worker-067/g_num_protocol_review/.  Reads canonical
artifacts read-only.  Stdlib only; subprocesses run pinned scripts by path.

Checks:
  A. hash window on the protocol (T0/T1) and all pinned evidence
  B. stdlib re-fit of the certified 4-rung rows (n0_order_4rung.json) + R5 recompute
  C. protocol-text numbers vs fixed_replication_verdict.json (R2 drifts, F7 ratios)
  D. re-execution of pinned scripts (lock guard, flat_wave, replication) at pinned hashes
  E. re-execution of frozen negative/positive controls through the audit tool
  F. scope/lock checks (no spherical_solver, no N1+ artifact)

Usage: python3 artifacts/worker-067/g_num_protocol_review/verify_r3.py [--root DIR] [--out FILE]
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

ROOT_DEFAULT = "/data3/guoshaoyang/workdir/ai4math-swarm"
PROTO = "numerics/CONVERGENCE_PROTOCOL.md"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def fit(rows, err_key):
    hkey = "dr" if "dr" in rows[0] else ("dx" if "dx" in rows[0] else "h")
    hs = [r[hkey] for r in rows]
    es = [r[err_key] for r in rows]
    assert len(hs) >= 2
    xs = [math.log(h) for h in hs]
    ys = [math.log(e) for e in es]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in resid)
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 else float("nan")
    pair = [
        math.log(es[i] / es[i + 1]) / math.log(hs[i] / hs[i + 1])
        for i in range(n - 1)
    ]
    half = (max(pair) - min(pair)) / 2.0
    return {
        "fit_order": slope,
        "least_squares_se": se,
        "pair_orders": pair,
        "pair_half_range": half,
        "delta": max(half, se),
        "n_rungs": n,
    }


def run(cmd, cwd, timeout=900):
    t0 = time.time()
    p = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    return {
        "argv": cmd,
        "returncode": p.returncode,
        "seconds": round(time.time() - t0, 3),
        "stdout_tail": p.stdout[-4000:],
        "stderr_tail": p.stderr[-2000:],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT_DEFAULT)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = args.out or os.path.join(here, "verification_log.json")

    evidence = [
        PROTO,
        "numerics/tests/flat_wave.py",
        "numerics/tests/flat_wave_replication.py",
        "numerics/tests/selfgravity_lock_guard.py",
        "numerics/tests/n0_order_4rung.json",
        "numerics/tests/n0_gate_proposal.json",
        "numerics/protocol/fixed_replication_verdict.json",
        "numerics/protocol/scheme_independence_evidence.json",
        "numerics/protocol/gate_reports_summary.json",
        "numerics/protocol/protocol_negative_controls.json",
        "numerics/protocol/format_conditions_disposition.json",
        "numerics/protocol/audit_convergence_report.py",
        "numerics/protocol/demo_report_standard.json",
        "numerics/protocol/demo_report_wrong_order.json",
    ]
    rep = {
        "schema": "worker-067/g-num-protocol-review-verification/v1",
        "reviewer": "worker-067",
        "actor": "worker-067",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "root": root,
        "t0": now(),
        "hash_window": {},
        "checks": {},
        "findings": [],
        "hard_failures": [],
        "writes": "artifacts/worker-067/g_num_protocol_review/ only",
    }
    rep["hash_window"]["t0_hashes"] = {
        p: sha256(os.path.join(root, p)) for p in evidence if os.path.exists(os.path.join(root, p))
    }
    missing = [p for p in evidence if not os.path.exists(os.path.join(root, p))]
    if missing:
        rep["findings"].append({"severity": "note", "text": "missing evidence: %s" % missing})

    # B. stdlib re-fit of the certified 4-rung rows
    d4 = json.load(open(os.path.join(root, "numerics/tests/n0_order_4rung.json")))
    b = {"schemes": {}, "all_match": True}
    for st in d4["studies"]:
        f = fit(st["rows"], "l2_error")
        decl = {
            "fit_order": st["fit_order"],
            "least_squares_se": st["least_squares_se"],
            "pair_orders": st["pair_orders"],
            "pair_half_range": st["pair_half_range"],
            "delta": st["delta"],
            "n_rungs": len(st["rows"]),
        }
        ok = (
            abs(f["fit_order"] - decl["fit_order"]) < 1e-9
            and abs(f["least_squares_se"] - decl["least_squares_se"]) < 1e-9
            and all(abs(a - c) < 1e-9 for a, c in zip(f["pair_orders"], decl["pair_orders"]))
            and abs(f["pair_half_range"] - decl["pair_half_range"]) < 1e-9
            and abs(f["delta"] - decl["delta"]) < 1e-9
            and f["n_rungs"] == decl["n_rungs"]
        )
        b["schemes"][st["scheme"]] = {
            "recomputed": f,
            "declared": decl,
            "match": ok,
            "within_band_pm_0.3": abs(f["fit_order"] - 2.0) <= 0.3,
            "monotone": all(
                st["rows"][i]["l2_error"] > st["rows"][i + 1]["l2_error"]
                for i in range(len(st["rows"]) - 1)
            ),
        }
        b["all_match"] &= ok
    # R5 pairwise recompute
    deltas = {k: v["recomputed"]["delta"] for k, v in b["schemes"].items()}
    orders = {k: v["recomputed"]["fit_order"] for k, v in b["schemes"].items()}
    pairs = {}
    for a in sorted(orders):
        for c in sorted(orders):
            if a >= c:
                continue
            bound = max(0.25, math.sqrt(deltas[a] ** 2 + deltas[c] ** 2))
            dp = abs(orders[a] - orders[c])
            pairs["%s vs %s" % (a, c)] = {
                "abs_order_diff": dp,
                "r5_bound": bound,
                "agree": dp <= bound,
            }
    b["pairwise_agreement_R5_recomputed"] = pairs
    declared_pairs = {
        tuple(sorted(x["pair"].split(" vs "))): x for x in d4["pairwise_agreement_R5"]
    }
    b["pairwise_matches_declared"] = all(
        abs(pairs["%s vs %s" % k]["abs_order_diff"] - v["abs_order_diff"]) < 1e-9
        and pairs["%s vs %s" % k]["agree"] == v["agree"]
        for k, v in declared_pairs.items()
    )
    rep["checks"]["B_four_rung_refit"] = b
    if not b["all_match"]:
        rep["hard_failures"].append("B: 4-rung refit does not reproduce declared fit/delta")
    if not b["pairwise_matches_declared"]:
        rep["hard_failures"].append("B: recomputed R5 agreement does not match declared")

    # C. protocol numbers vs fixed verdict
    fv = json.load(open(os.path.join(root, "numerics/protocol/fixed_replication_verdict.json")))
    q1 = fv["q1_invariant_functional_scheme_appropriate"]["schemes"]
    text = open(os.path.join(root, PROTO)).read()
    ntext = " ".join(text.split())  # whitespace-normalised probe text
    c = {
        "r2_drifts": {
            "lffd_measured": q1["lffd"]["own_drift_fixed"],
            "lffd_in_text_3.38e-15": abs(q1["lffd"]["own_drift_fixed"] - 3.38e-15) < 5e-18,
            "cnfd_measured": q1["cnfd"]["own_drift_fixed"],
            "cnfd_in_text_1.11e-14": abs(q1["cnfd"]["own_drift_fixed"] - 1.11e-14) < 5e-17,
            "cnfem_measured": q1["cnfem"]["own_drift_fixed"],
            "cnfem_in_text_2.04e-14": abs(q1["cnfem"]["own_drift_fixed"] - 2.04e-14) < 5e-17,
            "all_pass_r2_bound_1e-12": all(
                v["r2_pass"] and v["own_drift_fixed"] <= 1e-12 for v in q1.values()
            ),
        },
        "f7_ratios": {
            "cnfd_measured": q1["cnfd"]["r4_harness_over_own_ratio"],
            "cnfd_in_text_5.95e6": round(q1["cnfd"]["r4_harness_over_own_ratio"] / 1e6, 2) == 5.95,
            "cnfem_measured": q1["cnfem"]["r4_harness_over_own_ratio"],
            "cnfem_in_text_4.15e5": round(q1["cnfem"]["r4_harness_over_own_ratio"] / 1e5, 2) == 4.15,
            "harness_functional_discriminates": fv["q1_invariant_functional_scheme_appropriate"][
                "harness_functional_discriminates_exact_conservation"
            ],
        },
        "r5a_named_norm_in_text": ("names the error norm" in ntext and "R5a" in ntext),
        "four_rung_rule_in_text": ("At least four resolutions" in ntext and "four or more rungs" in ntext),
        "scope_block_present": (
            "does not define, authorise, or prepare any self-gravitating evolution" in ntext
        ),
        "conclusion_type_cap": (
            "may be promoted above `conclusion_type: numerical_evidence`" in ntext
        ),
        "residual_ambiguity_6_vs_rev2a": (
            "agree within `0.35` absolute" in ntext and "The agreement test is the R5 rule" in ntext
        ),
    }
    rep["checks"]["C_text_numbers_vs_evidence"] = c
    if not all(
        [
            c["r2_drifts"]["lffd_in_text_3.38e-15"],
            c["r2_drifts"]["cnfd_in_text_1.11e-14"],
            c["r2_drifts"]["cnfem_in_text_2.04e-14"],
            c["r2_drifts"]["all_pass_r2_bound_1e-12"],
            c["f7_ratios"]["cnfd_in_text_5.95e6"],
            c["f7_ratios"]["cnfem_in_text_4.15e5"],
            c["r5a_named_norm_in_text"],
            c["four_rung_rule_in_text"],
            c["scope_block_present"],
        ]
    ):
        rep["hard_failures"].append("C: protocol text does not match pinned evidence")

    # D. re-execution at pinned hashes
    d = {"hash_guard": {}, "runs": {}}
    scripts = [
        "numerics/tests/selfgravity_lock_guard.py",
        "numerics/tests/flat_wave.py",
        "numerics/tests/flat_wave_replication.py",
    ]
    for s in scripts:
        d["hash_guard"][s] = {"sha256_before": sha256(os.path.join(root, s))}
    outdir = here
    d["runs"]["lock_guard_selftest"] = run(
        [sys.executable, "numerics/tests/selfgravity_lock_guard.py", "--self-test"], root
    )
    d["runs"]["lock_guard_real"] = run(
        [sys.executable, "numerics/tests/selfgravity_lock_guard.py"], root
    )
    d["runs"]["flat_wave_selftest"] = run(
        [sys.executable, "numerics/tests/flat_wave.py", "--selftest"], root
    )
    d["runs"]["flat_wave_all"] = run(
        [
            sys.executable,
            "numerics/tests/flat_wave.py",
            "--all",
            "--json-out",
            os.path.join(outdir, "flat_wave_all.json"),
        ],
        root,
    )
    d["runs"]["replication_selftest"] = run(
        [sys.executable, "numerics/tests/flat_wave_replication.py", "--selftest"], root
    )
    d["runs"]["replication_all"] = run(
        [
            sys.executable,
            "numerics/tests/flat_wave_replication.py",
            "--all",
            "--json-out",
            os.path.join(outdir, "flat_wave_replication_all.json"),
        ],
        root,
    )
    for s in scripts:
        d["hash_guard"][s]["sha256_after"] = sha256(os.path.join(root, s))
        d["hash_guard"][s]["unchanged"] = (
            d["hash_guard"][s]["sha256_before"] == d["hash_guard"][s]["sha256_after"]
        )
    # extract measured orders from reruns (explicit schemas)
    fw_path = os.path.join(outdir, "flat_wave_all.json")
    rp_path = os.path.join(outdir, "flat_wave_replication_all.json")
    if os.path.exists(fw_path):
        j = json.load(open(fw_path))
        d["measured_flat_wave"] = {
            "all_gates_pass": j.get("all_gates_pass"),
            "gates": j.get("gates"),
            "determinism": j.get("determinism"),
            "controls_rejected": [
                {"name": c.get("name"), "rejected": c.get("rejected")} for c in j.get("controls", [])
            ],
            "studies": [
                {
                    "scheme_order": s.get("order_scheme"),
                    "family": s.get("family"),
                    "n_rungs": len(s.get("rows", [])),
                    "order_l2": s.get("order_l2"),
                    "order_linf": s.get("order_linf"),
                    "order_gate_pass": (s.get("order_gate") or {}).get("pass"),
                    "monotone": s.get("monotone_decrease"),
                    "refit_l2": fit(s["rows"], "l2_error") if s.get("rows") and "l2_error" in s["rows"][0] else None,
                }
                for s in j.get("studies", [])
            ],
            "lock_guard": j.get("lock_guard"),
        }
    if os.path.exists(rp_path):
        j = json.load(open(rp_path))
        res = j.get("result", {})
        d["measured_replication"] = {
            "independent_orders": res.get("independent_orders"),
            "replication_verdict": res.get("replication_verdict"),
            "reference_measured_order": res.get("reference_measured_order"),
            "agreement_within_harness_tol": res.get("order_agreement_with_reference_within_harness_tol"),
            "selftest_pass": (j.get("selftest") or {}).get("pass"),
            "determinism": j.get("determinism"),
            "controls": {
                k: (v.get("rejected") if isinstance(v, dict) else v)
                for k, v in (j.get("controls") or {}).items()
            },
            "invariant_gate_calibration_hypothesis": (j.get("invariant_gate_calibration") or {}).get(
                "hypothesis_tested"
            ),
        }
        io = res.get("independent_orders") or {}
        d["replication_matches_fixed_verdict"] = all(
            abs(io.get(k, float("nan")) - fv["q2_order_fit_carries_uncertainty"]["schemes"][k][
                "lsq_fit_order_from_rows"
            ]) < 1e-9
            for k in ("cnfd", "cnfem")
        )
    rep["checks"]["D_reruns"] = d
    if not all(v.get("returncode") == 0 for k, v in d["runs"].items()):
        bad = [k for k, v in d["runs"].items() if v.get("returncode") != 0]
        rep["hard_failures"].append("D: script rerun nonzero: %s" % bad)
    if not all(v["unchanged"] for v in d["hash_guard"].values()):
        rep["hard_failures"].append("D: pinned script hash changed during rerun")

    # E. frozen control re-execution through the audit tool
    e = {"controls": [], "all_expected": True}
    audit = "numerics/protocol/audit_convergence_report.py"
    ctrl_specs = [
        ("positive_standard", "numerics/protocol/demo_report_standard.json", 0, None),
        ("negative_wrong_order", "numerics/protocol/demo_report_wrong_order.json", 1, "C4_order"),
    ]
    for name, path, exp_rc, exp_check in ctrl_specs:
        r = run([sys.executable, audit, path], root)
        ok = r["returncode"] == exp_rc and (exp_check is None or exp_check in r["stdout_tail"])
        e["controls"].append(
            {"name": name, "input": path, "input_sha256": sha256(os.path.join(root, path)),
             "expected_rc": exp_rc, "expected_failed_check": exp_check,
             "measured_rc": r["returncode"], "ok": ok,
             "stdout_tail": r["stdout_tail"][-600:]}
        )
        e["all_expected"] &= ok
    neg = json.load(open(os.path.join(root, "numerics/protocol/protocol_negative_controls.json")))
    e["negative_controls_overall"] = neg["overall"]
    e["negative_controls_claimed_pass"] = bool(neg["overall"]["pass"])
    rep["checks"]["E_controls"] = e
    if not e["all_expected"]:
        rep["hard_failures"].append("E: frozen control re-execution deviates from expectation")

    # F. lock/scope
    f = {
        "spherical_solver_absent": not os.path.exists(os.path.join(root, "numerics/spherical_solver")),
        "lock_guard_sha256": sha256(os.path.join(root, "numerics/tests/selfgravity_lock_guard.py")),
        "lock_guard_rc": d["runs"]["lock_guard_real"]["returncode"],
    }
    rep["checks"]["F_lock_scope"] = f
    if not f["spherical_solver_absent"] or f["lock_guard_rc"] != 0:
        rep["hard_failures"].append("F: lock/scope check failed")

    rep["t1"] = now()
    rep["hash_window"]["t1_hashes"] = {
        p: sha256(os.path.join(root, p)) for p in evidence if os.path.exists(os.path.join(root, p))
    }
    rep["hash_window"]["stable"] = (
        rep["hash_window"]["t0_hashes"] == rep["hash_window"]["t1_hashes"]
    )
    if not rep["hash_window"]["stable"]:
        rep["hard_failures"].append("A: a pinned evidence hash moved inside the review window")
    rep["verdict_inputs"] = {
        "hard_failures": rep["hard_failures"],
        "c1_closed": c["r5a_named_norm_in_text"] and c["f7_ratios"]["harness_functional_discriminates"] is False,
        "c2_closed": c["four_rung_rule_in_text"] and b["all_match"] and b["pairwise_matches_declared"],
        "c3_closed": c["r5a_named_norm_in_text"]
        and all(
            v["declared"].get("delta") is not None and v["declared"].get("least_squares_se") is not None
            for v in b["schemes"].values()
        )
        and all(v["agree"] for v in pairs.values()),
        "c4_registration_open_controller_side": None,
    }
    json.dump(rep, open(out_path, "w"), indent=1, sort_keys=True)
    print(json.dumps({"out": out_path, "hard_failures": rep["hard_failures"],
                      "stable": rep["hash_window"]["stable"],
                      "all_pairwise_agree": all(v["agree"] for v in pairs.values()),
                      "four_rung_match": b["all_match"]}, indent=1))
    return 0 if not rep["hard_failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
