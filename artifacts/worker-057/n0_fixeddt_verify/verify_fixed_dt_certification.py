#!/usr/bin/env python3
"""W057-N0-FIXEDDT-VERIFY-01: independent re-analysis of the N0 fixed-dt certification.

Task (class-bound): AF-WCC-SCALAR-SPH.  Node N0.  Gate G-NUM.  Actor worker-057.
Lifecycle 3 (worker slot 057).

Question.  The lead-numerics certification
``numerics/protocol/n0_fixed_dt_certification.json`` claims a second-order
spatial discretisation at fixed dt = 1e-4 for three schemes (lffd, cnfd,
cnfemd), cross-scheme |dp| within the R5 bound, with a stated uncertainty rule
(max of pair half-range and least-squares slope SE).  The file embeds the raw
per-rung (dr, l2_error) rows.  This instrument recomputes every derived number
from those raw rows with its own closed-form estimators (least squares in
log-log space, pairwise log-ratio orders, and a robust median-of-pairwise-slopes
estimator), checks the file's internal consistency (fixed dt, cfl = dt/dr,
steps = t_end/dt, monotone ladder, R5 band), and checks the cross-scheme and
mixed-order-control relations.  It never imports or executes the lead's
generator script, and it never writes to any canonical path.

What this does NOT do.  It does not re-run the solver, so it cannot confirm
that the embedded l2_error values were produced by the frozen module; it checks
the derivation chain from published rows, and it hash-guards the frozen module
the certification names.  No gate verdict, no node completion, no N1 release.

Controls (fail-closed).  The estimator battery is run on synthetic ladders with
known order: p=2 (exact), p=3, p=1 (must leave the R5 band), large-constant
p=2, a non-monotone ladder, and a tampered real ladder.  Any control that does
not behave as specified sets instrument_valid=false and exit code 2.  Exit 0
means the instrument ran and is valid; findings on the certification are in the
report.

Reproduce:
  python3 artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

CERT_PATH = "numerics/protocol/n0_fixed_dt_certification.json"
FROZEN_MODULE = "numerics/tests/flat_wave_replication.py"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"

TOL_EXACT = 1e-12          # declared derived numbers must reproduce exactly
TOL_SYNTH = 1e-9           # synthetic ladders: float noise only
SCHEMES = ("lffd", "cnfd", "cnfem")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_err(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def lsq_loglog(rows):
    """Least-squares slope/intercept of ln(e) vs ln(dr), residuals (obs-pred),
    slope SE, and the robust median-of-pairwise-slopes estimate."""
    x = [math.log(r["dr"]) for r in rows]
    y = [math.log(r["l2_error"]) for r in rows]
    n = len(x)
    xbar = sum(x) / n
    ybar = sum(y) / n
    sxx = sum((xi - xbar) ** 2 for xi in x)
    sxy = sum((xi - xbar) * (yi - ybar) for xi, yi in zip(x, y))
    slope = sxy / sxx
    intercept = ybar - slope * xbar
    resid = [yi - (intercept + slope * xi) for xi, yi in zip(x, y)]
    ssr = sum(r * r for r in resid)
    se = math.sqrt((ssr / (n - 2)) / sxx) if n > 2 and sxx > 0 else float("nan")
    pair_slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            pair_slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    robust = statistics.median(pair_slopes)
    return {
        "order_ls": slope,
        "intercept": intercept,
        "residuals": resid,
        "ssr": ssr,
        "se": se,
        "robust_order": robust,
        "pairwise_slopes": pair_slopes,
    }


def pair_orders(rows):
    out = []
    for a, b in zip(rows, rows[1:]):
        out.append(
            math.log(a["l2_error"] / b["l2_error"]) / math.log(a["dr"] / b["dr"])
        )
    return out


def monotone(rows):
    errs = [r["l2_error"] for r in rows]
    return all(errs[i] > errs[i + 1] for i in range(len(errs) - 1))


def synthetic_ladder(p, const=1.0):
    drs = [0.2, 0.1, 0.05, 0.025]
    return [
        {"dr": d, "l2_error": const * (d ** p), "dt": 1e-4, "steps": 60000}
        for d in drs
    ]


class Report:
    def __init__(self):
        self.checks = []
        self.controls = []
        self.findings = []
        self.advisories = []

    def check(self, cid, desc, expected, observed, ok, detail=None, severity="finding"):
        self.checks.append({
            "check_id": cid,
            "description": desc,
            "expected": expected,
            "observed": observed,
            "pass": bool(ok),
            "severity": severity,
            "detail": detail,
        })
        if not ok:
            row = {"check_id": cid, "description": desc,
                   "expected": expected, "observed": observed,
                   "severity": severity, "detail": detail}
            (self.advisories if severity == "advisory" else self.findings).append(row)
        return bool(ok)

    def control(self, cid, desc, expected_behaviour, observed_behaviour, ok):
        self.controls.append({
            "control_id": cid,
            "description": desc,
            "expected_behaviour": expected_behaviour,
            "observed_behaviour": observed_behaviour,
            "pass": bool(ok),
        })
        return bool(ok)


def main() -> int:
    now = datetime.now(CST)
    cert_file = ROOT / CERT_PATH
    cert_sha = sha256_file(cert_file)
    cert = json.loads(cert_file.read_text())
    module_sha = sha256_file(ROOT / FROZEN_MODULE)
    protocol_sha = sha256_file(ROOT / PROTOCOL)
    protocol_text = (ROOT / PROTOCOL).read_text()
    rep = Report()

    # ---------------- A. input integrity ----------------
    rep.check("A1", "certification declares its own schema id",
              "n0-fixed-dt-certification/v1", cert.get("schema"),
              cert.get("schema") == "n0-fixed-dt-certification/v1")
    declared_module = (cert.get("frozen_module") or {}).get("sha256")
    rep.check("A2", "frozen module hash in certification matches disk",
              declared_module, module_sha, declared_module == module_sha)
    rep.check("A3", "frozen module hash guard flag is true",
              True, (cert.get("frozen_module") or {}).get("hash_guard_passed"),
              (cert.get("frozen_module") or {}).get("hash_guard_passed") is True)
    cfg = cert.get("config") or {}
    clause = str(cfg.get("protocol_clause", ""))
    fixed_dt_rule = "Temporal/spatial separation" in protocol_text and "fixed, small `dt`" in protocol_text
    rep.check("A4a", "protocol rule named by the clause resolves (section 3 item 4: fixed small dt)",
              "section 3 item 4 fixed-dt rule present", fixed_dt_rule, fixed_dt_rule)
    rep.check("A4b", "citation token 'section 3.4' appears literally in the protocol",
              "literal 'section 3.4' heading", "absent (document numbers section 3, items 1-8)",
              "section 3.4" in protocol_text, severity="advisory",
              detail=("The rule resolves at CONVERGENCE_PROTOCOL.md section 3 item 4 (line 58), so the "
                      "citation is resolvable by section+item convention; the token '3.4' itself does not occur."))
    rep.check("A5", "R5 uncertainty rule text present in protocol",
              "R5 present", "R5 present" if "R5" in protocol_text else "R5 absent",
              "R5" in protocol_text)
    norm_named = any(tok in json.dumps(cert).lower()
                     for tok in ("l2 integral", "l-infinity", "linfinity", "linf", "error norm"))
    rep.check("A6", "protocol R5a requires the fitted error norm to be named",
              "explicit L2-integral/L-infinity token in certification",
              "explicit token present" if norm_named else "field name 'l2_error' only",
              norm_named, severity="advisory",
              detail=("R5a asks order claims to name the error norm. The certification names it only through the "
                      "JSON key 'l2_error'; the claim text does not spell out 'L2 integral'. Unambiguous but not explicit."))

    # ---------------- B. per-scheme independent recomputation ----------------
    recomp = {}
    for s in SCHEMES:
        block = ((cert.get("schemes") or {}).get(s) or {}).get("fixed_dt_certification")
        if not block:
            rep.check(f"B0-{s}", f"{s}: fixed_dt_certification block present",
                      True, False, False)
            continue
        rows = block["rows"]
        fit = lsq_loglog(rows)
        po = pair_orders(rows)
        phr = (max(po) - min(po)) / 2.0
        delta = max(phr, fit["se"])
        recomp[s] = {"fit": fit, "pair_orders": po, "pair_half_range": phr,
                     "delta_R5": delta, "monotone": monotone(rows), "rows": rows}

        rep.check(f"B1-{s}", f"{s}: declared fit_order reproduces from raw rows",
                  block["fit_order"], fit["order_ls"],
                  rel_err(block["fit_order"], fit["order_ls"]) <= TOL_EXACT)
        rep.check(f"B2-{s}", f"{s}: declared pair_orders reproduce",
                  block["pair_orders"], po,
                  len(po) == len(block["pair_orders"]) and all(
                      rel_err(a, b) <= TOL_EXACT for a, b in zip(po, block["pair_orders"])))
        direct = all(rel_err(a, b) <= TOL_EXACT for a, b in zip(fit["residuals"], block["lsq_residuals"]))
        flipped = all(rel_err(a, -b) <= TOL_EXACT for a, b in zip(fit["residuals"], block["lsq_residuals"]))
        rep.check(f"B3-{s}", f"{s}: declared lsq_residuals reproduce (sign convention documented)",
                  block["lsq_residuals"], fit["residuals"], direct or flipped,
                  {"sign_convention": "obs-pred" if direct else ("pred-obs" if flipped else "MISMATCH")})
        rep.check(f"B4-{s}", f"{s}: declared least_squares_se reproduces",
                  block["least_squares_se"], fit["se"],
                  rel_err(block["least_squares_se"], fit["se"]) <= TOL_EXACT)
        rep.check(f"B5-{s}", f"{s}: declared pair_half_range reproduces",
                  block["pair_half_range"], phr,
                  rel_err(block["pair_half_range"], phr) <= TOL_EXACT)
        rep.check(f"B6-{s}", f"{s}: declared delta_R5 == max(pair_half_range, least_squares_se)",
                  block["delta_R5"], delta, rel_err(block["delta_R5"], delta) <= TOL_EXACT)
        rep.check(f"B7-{s}", f"{s}: l2_error strictly decreasing as dr halves (monotone ladder)",
                  True, monotone(rows), monotone(rows) == block.get("monotone"))
        rep.check(f"B8-{s}", f"{s}: fit order within R5 band |p - p_design| <= p_tol",
                  f"|p-2.0| <= {cfg.get('p_tol')}",
                  abs(fit["order_ls"] - float(cfg.get("p_design", 2.0))),
                  abs(fit["order_ls"] - float(cfg.get("p_design", 2.0))) <= float(cfg.get("p_tol", 0.3)))
        rep.check(f"B9-{s}", f"{s}: robust median-of-pairwise-slopes also inside R5 band",
                  f"|p_robust-2.0| <= {cfg.get('p_tol')}",
                  abs(fit["robust_order"] - float(cfg.get("p_design", 2.0))),
                  abs(fit["robust_order"] - float(cfg.get("p_design", 2.0))) <= float(cfg.get("p_tol", 0.3)),
                  {"robust_minus_ls": fit["robust_order"] - fit["order_ls"],
                   "robust_within_declared_delta": abs(fit["robust_order"] - fit["order_ls"]) <= delta})
        # fixed-dt claim: dt constant on every rung, cfl = dt/dr, steps = t_end/dt
        dts = {r["dt"] for r in rows}
        cfl_ok = all(rel_err(r["cfl_effective"], r["dt"] / r["dr"]) <= 1e-12 for r in rows)
        steps_ok = all(abs(r["steps"] - float(cfg.get("t_end", 6.0)) / r["dt"]) <= 1.0 for r in rows)
        rep.check(f"B10-{s}", f"{s}: dt constant on every rung (fixed-dt claim)",
                  f"dt == {cfg.get('dt_fixed')}", sorted(dts), len(dts) == 1)
        rep.check(f"B11-{s}", f"{s}: cfl_effective == dt/dr on every rung",
                  True, cfl_ok, cfl_ok)
        rep.check(f"B12-{s}", f"{s}: steps == t_end/dt on every rung",
                  True, steps_ok, steps_ok)
        n_rungs = len(rows)
        rep.check(f"B13-{s}", f"{s}: at least 4 resolutions (protocol section 3 item 2)",
                  4, n_rungs, n_rungs >= 4)
        ratios = [a["dr"] / b["dr"] for a, b in zip(rows, rows[1:])]
        rep.check(f"B14-{s}", f"{s}: refinement ratio is 2 on every step (protocol section 3 item 2)",
                  [2.0] * (n_rungs - 1), ratios,
                  all(abs(r - 2.0) <= 1e-12 for r in ratios))

    # ---------------- C. cross-scheme agreement ----------------
    xs = cert.get("cross_scheme_R5") or {}
    pairs_expected = [("lffd", "cnfd"), ("lffd", "cnfem"), ("cnfd", "cnfem")]
    maxdiff = 0.0
    pair_rows = []
    pair_ok = True
    for a, b in pairs_expected:
        d = abs(recomp[a]["fit"]["order_ls"] - recomp[b]["fit"]["order_ls"])
        maxdiff = max(maxdiff, d)
        ok = d <= float(xs.get("r5_bound", 0.25)) if "r5_bound" in xs else d <= 0.25
        pair_rows.append({"pair": f"{a} vs {b}", "abs_order_diff": d, "agree": ok})
        pair_ok = pair_ok and ok
    rep.check("C1", "cross-scheme max |dp| reproduces",
              xs.get("max_pairwise_abs_diff"), maxdiff,
              rel_err(float(xs.get("max_pairwise_abs_diff", -1)), maxdiff) <= TOL_EXACT)
    rep.check("C2", "all cross-scheme pairs within the declared R5 bound",
              f"bound {xs.get('r5_bound')}", pair_rows, pair_ok)
    rep.check("C3", "declared all_agree flag matches recomputation",
              xs.get("all_agree"), pair_ok, bool(xs.get("all_agree")) == pair_ok)
    agreed_pairs = {(p.get("pair")): p.get("abs_order_diff") for p in (xs.get("pairs") or [])}
    decl_pair_ok = all(
        any(pr["pair"] == name and rel_err(float(agreed_pairs.get(name, -1)), pr["abs_order_diff"]) <= TOL_EXACT
            for name in agreed_pairs)
        for pr in pair_rows)
    rep.check("C4", "declared per-pair abs_order_diff reproduces",
              agreed_pairs, {p["pair"]: p["abs_order_diff"] for p in pair_rows}, decl_pair_ok)
    protocol_bounds = {}
    protocol_agree = True
    for a, b in pairs_expected:
        bound = max(0.25, math.sqrt(recomp[a]["delta_R5"] ** 2 + recomp[b]["delta_R5"] ** 2))
        d = abs(recomp[a]["fit"]["order_ls"] - recomp[b]["fit"]["order_ls"])
        protocol_bounds[f"{a} vs {b}"] = {"bound": bound, "abs_order_diff": d, "agree": d <= bound}
        protocol_agree = protocol_agree and d <= bound
    rep.check("C5", "exact protocol R5 agreement rule max(0.25, sqrt(dA^2+dB^2)) is satisfied per pair",
              "all pairs agree under the exact rule",
              protocol_bounds, protocol_agree,
              detail="declared per-pair r5_bound must equal this bound (verified in C4) for the file to be conformant")

    # ---------------- D. mixed-order control and verdict self-consistency ----------------
    shifts = {}
    for s in SCHEMES:
        mb = ((cert.get("schemes") or {}).get(s) or {}).get("constant_cfl_mixed_order_control")
        if not mb:
            rep.check(f"D0-{s}", f"{s}: constant-CFL control block present", True, False, False)
            continue
        mrows = mb["rows"]
        mfit = lsq_loglog(mrows)
        shift = recomp[s]["fit"]["order_ls"] - mfit["order_ls"]
        shifts[s] = shift
        rep.check(f"D1-{s}", f"{s}: declared mixed-control fit_order reproduces",
                  mb["fit_order"], mfit["order_ls"],
                  rel_err(mb["fit_order"], mfit["order_ls"]) <= TOL_EXACT)
        rep.check(f"D2-{s}", f"{s}: mixed-control ladder is constant-CFL (dt/dr constant)",
                  "dt/dr constant", sorted({round(r["dt"] / r["dr"], 12) for r in mrows}),
                  len({round(r["dt"] / r["dr"], 12) for r in mrows}) == 1)
        rep.check(f"D3-{s}", f"{s}: order_shift_vs_mixed == fixed_order - mixed_order",
                  ((cert["schemes"][s]).get("order_shift_vs_mixed")), shift,
                  rel_err(float((cert["schemes"][s]).get("order_shift_vs_mixed", -1)), shift) <= TOL_EXACT)

    v = cert.get("verdict") or {}
    if all(s in recomp for s in SCHEMES):
        rep.check("D4", "verdict.all_monotone matches independent recomputation",
                  v.get("all_monotone"), all(recomp[s]["monotone"] for s in SCHEMES),
                  bool(v.get("all_monotone")) == all(recomp[s]["monotone"] for s in SCHEMES))
        band_ok = all(abs(recomp[s]["fit"]["order_ls"] - float(cfg.get("p_design", 2.0)))
                      <= float(cfg.get("p_tol", 0.3)) for s in SCHEMES)
        rep.check("D5", "verdict.all_within_band matches independent recomputation",
                  v.get("all_within_band"), band_ok, bool(v.get("all_within_band")) == band_ok)
        rep.check("D6", "verdict.cross_scheme_agree matches independent recomputation",
                  v.get("cross_scheme_agree"), pair_ok, bool(v.get("cross_scheme_agree")) == pair_ok)
        cert_orders = v.get("certified_spatial_order") or {}
        rep.check("D7", "verdict.certified_spatial_order reproduces",
                  cert_orders, {s: recomp[s]["fit"]["order_ls"] for s in SCHEMES},
                  all(rel_err(float(cert_orders.get(s, -1)), recomp[s]["fit"]["order_ls"]) <= TOL_EXACT
                      for s in SCHEMES))

    # ---------------- E. estimator controls (fail-closed) ----------------
    c2 = lsq_loglog(synthetic_ladder(2.0))
    ok = abs(c2["order_ls"] - 2.0) <= TOL_SYNTH and abs(c2["robust_order"] - 2.0) <= TOL_SYNTH
    rep.control("E1", "exact second-order synthetic ladder recovers p=2",
                "p_ls = p_robust = 2", {"p_ls": c2["order_ls"], "p_robust": c2["robust_order"]}, ok)

    c3 = lsq_loglog(synthetic_ladder(3.0))
    ok = abs(c3["order_ls"] - 3.0) <= TOL_SYNTH
    rep.control("E2", "exact third-order synthetic ladder recovers p=3 (estimator responds to order)",
                "p_ls = 3", {"p_ls": c3["order_ls"]}, ok)

    c1 = lsq_loglog(synthetic_ladder(1.0))
    band_fail = abs(c1["order_ls"] - 2.0) > 0.3
    rep.control("E3", "first-order synthetic ladder must fail the R5 band",
                "|p_ls-2.0| > 0.3", {"p_ls": c1["order_ls"], "band_fail": band_fail}, band_fail)

    cbig = lsq_loglog(synthetic_ladder(2.0, const=1e6))
    ok = abs(cbig["order_ls"] - 2.0) <= TOL_SYNTH
    rep.control("E4", "large multiplicative constant does not change the slope",
                "p_ls = 2 for C=1e6", {"p_ls": cbig["order_ls"]}, ok)

    tam = [dict(r) for r in recomp["lffd"]["rows"]]
    tam[-1]["l2_error"] *= 1.01
    ctam = lsq_loglog(tam)
    declared = cert["schemes"]["lffd"]["fixed_dt_certification"]["fit_order"]
    detect = rel_err(ctam["order_ls"], declared) > TOL_EXACT
    rep.control("E5", "1% tamper on the finest rung is detected against the declared fit",
                "recomputed != declared", {"recomputed": ctam["order_ls"], "declared": declared,
                                           "shift_ls": ctam["order_ls"] - declared,
                                           "shift_robust": ctam["robust_order"] - recomp["lffd"]["fit"]["robust_order"],
                                           "detected": detect}, detect)

    nm = synthetic_ladder(2.0)
    nm[0]["l2_error"], nm[1]["l2_error"] = nm[1]["l2_error"], nm[0]["l2_error"]
    rep.control("E6", "non-monotone ladder is detected by the monotonicity check",
                "monotone = False", {"monotone": monotone(nm)}, monotone(nm) is False)

    instrument_valid = all(c["pass"] for c in rep.controls)

    drift_cert_sha = sha256_file(cert_file)
    drift = {
        "cert_sha256_at_start": cert_sha,
        "cert_sha256_at_end": drift_cert_sha,
        "stable": cert_sha == drift_cert_sha,
    }

    report = {
        "task_id": "W057-N0-FIXEDDT-VERIFY-01",
        "actor": "worker-057",
        "generated_at": now.isoformat(),
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "node_id": "N0",
        "gate": "G-NUM",
        "question": ("Does the lead-numerics fixed-dt certification reproduce, from its own "
                     "embedded raw l2_error rows, under independent estimators and internal-"
                     "consistency checks?"),
        "inputs": {
            CERT_PATH: {"sha256": cert_sha, "bytes": cert_file.stat().st_size},
            FROZEN_MODULE: {"sha256": module_sha},
            PROTOCOL: {"sha256": protocol_sha},
        },
        "method": {
            "estimator_ls": "ordinary least squares slope of ln(l2_error) vs ln(dr); p = slope",
            "estimator_pairwise": "p_i = ln(e_i/e_{i+1}) / ln(dr_i/dr_{i+1})",
            "estimator_robust": "median of all pairwise ln-log slopes (Theil-Sen style)",
            "se": "sqrt( SSR/(n-2) / Sxx )",
            "uncertainty": "delta_R5 = max(pair half-range, LS slope SE)",
            "note": "generator script not imported; derived numbers recomputed from published rows",
        },
        "recomputed": {
            s: {
                "order_ls": recomp[s]["fit"]["order_ls"],
                "order_robust": recomp[s]["fit"]["robust_order"],
                "se": recomp[s]["fit"]["se"],
                "pair_orders": recomp[s]["pair_orders"],
                "pair_half_range": recomp[s]["pair_half_range"],
                "delta_R5": recomp[s]["delta_R5"],
                "monotone": recomp[s]["monotone"],
                "robust_minus_ls": recomp[s]["fit"]["robust_order"] - recomp[s]["fit"]["order_ls"],
            } for s in recomp
        },
        "cross_scheme": {"pairs": pair_rows, "max_pairwise_abs_diff": maxdiff,
                         "all_agree": pair_ok, "declared_bound": xs.get("r5_bound"),
                         "protocol_rule_pairs": protocol_bounds},
        "order_shift_vs_mixed": shifts,
        "checks": rep.checks,
        "controls": rep.controls,
        "instrument_valid": instrument_valid,
        "findings": rep.findings,
        "finding_count": len(rep.findings),
        "advisories": rep.advisories,
        "advisory_count": len(rep.advisories),
        "drift": drift,
        "verdict": ("REPRODUCED" if instrument_valid and not rep.findings
                    else ("REPRODUCED_WITH_FINDINGS" if instrument_valid else "INSTRUMENT_INVALID")),
        "not_claimed": [
            "no gate verdict and no gate self-pass (authority: controller / lead-audit)",
            "no node completion; numerics_lock stays LOCKED and N1 stays queued",
            "no physics claim; this is a re-analysis of published flat-space evidence rows",
            "no confirmation that the embedded l2_error values were produced by the frozen module "
            "(the module hash is guarded, the solver is not re-run here)",
        ],
        "reproduce": "python3 artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py",
        "falsifier": ("Re-hash the certification and re-run this instrument: the result is falsified for "
                      "the recorded cert sha256 if any declared derived number fails to reproduce from the "
                      "embedded rows, if any check flips to fail, or if any control in E1-E6 stops behaving "
                      "as specified. A moved certification hash voids this report for the new bytes."),
    }

    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    print(json.dumps({
        "verdict": report["verdict"],
        "checks": len(rep.checks),
        "failed_checks": len(rep.findings),
        "controls": len(rep.controls),
        "controls_passed": sum(1 for c in rep.controls if c["pass"]),
        "instrument_valid": instrument_valid,
        "orders": {s: round(recomp[s]["fit"]["order_ls"], 12) for s in recomp},
        "cert_sha256": cert_sha,
        "stable": drift["stable"],
    }, indent=1))
    return 0 if instrument_valid else 2


if __name__ == "__main__":
    sys.exit(main())
