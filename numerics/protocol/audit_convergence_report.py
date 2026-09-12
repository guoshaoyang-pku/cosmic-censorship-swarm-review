#!/usr/bin/env python3
"""Audit an N0 convergence report against ``convergence_protocol.md``.

This is the reference implementation of the protocol's failure criteria.  It
recomputes every criterion from the report's raw arrays; it never trusts a
self-declared ``checks`` or ``verdict`` field.  Intended users: the numerics
group lead (gate G-NUM), the independent replicator, and the audit lead.

Report schema ``n0-convergence-report/v1`` (required fields)
------------------------------------------------------------
schema, node_id, class_id, scheme_id, declared_order, cfl, exact_family,
measurement_times, resolutions, linf_errors, stable, implementation,
script_sha256, non_degeneracy.

Recommended: l2_errors, residual_orders, richardson_order, energy_drift,
energy_diagnostic, fitted_order, wall_seconds, notes.

Checks
------
C0 completeness      required fields, matching array lengths, schema string
C1 stability         stable flag, CFL margin, finite positive errors
C2 non-degeneracy    measurement time(s) declared, single-mode rule
C3 monotone          e_{i+1} <= e_i / 2^(declared - 0.5)
C4 order             finest two pair orders and fitted slope within tolerance
C5 residual          truncation-residual orders >= declared - tolerance
C6 richardson        three-grid self-convergence order within tolerance
C7 invariant         functional-aware: exact_discrete roundoff, else convergence + budget
C8 provenance        implementation + sha256, hash verified when file exists
C9 uncertainty       order_uncertainty delta = max(se, half-range) <= 0.15

Usage
-----
    python3 numerics/protocol/audit_convergence_report.py REPORT.json
    python3 numerics/protocol/audit_convergence_report.py --root . REPORT.json
    python3 numerics/protocol/audit_convergence_report.py --tolerance 0.3 REPORT.json
    python3 numerics/protocol/audit_convergence_report.py --compare A.json B.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

SCHEMA = "n0-convergence-report/v1"
REQUIRED = ("schema", "node_id", "class_id", "scheme_id", "declared_order", "cfl",
            "exact_family", "measurement_times", "resolutions", "linf_errors",
            "stable", "implementation", "script_sha256", "non_degeneracy")
RECOMMENDED = ("l2_errors", "residual_orders", "richardson_order", "energy_drift",
               "energy_diagnostic", "energy_functional", "order_uncertainty",
               "fitted_order", "wall_seconds")
#: absolute drift budget at the finest rung for convergent diagnostics (relative)
DRIFT_BUDGET = 1e-6
#: roundoff-level drift tolerance for exactly conserving (scheme, functional) pairs
STRUCTURAL_TOL = 1e-12
#: CFL must stay below this margin of the declared stability limit
CFL_MARGIN = 0.9
#: maximum admissible order uncertainty delta
DELTA_MAX = 0.15
#: floor for cross-scheme order agreement
AGREEMENT_FLOOR = 0.25


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _pair_orders(resolutions, errors):
    """p_i = log(e_i/e_{i+1}) / log(h_i/h_{i+1}) with h = 1/resolution."""
    out = []
    for i, (a, b) in enumerate(zip(errors, errors[1:])):
        if a > 0 and b > 0 and resolutions[i] != resolutions[i + 1]:
            out.append(math.log(a / b) / math.log(resolutions[i + 1] / resolutions[i]))
        else:
            out.append(float("nan"))
    return out


def _fit_order(resolutions, errors):
    if any(e <= 0 for e in errors):
        return float("nan")
    xs = [-math.log(r) for r in resolutions]  # log h, h = 1/resolution
    ys = [math.log(e) for e in errors]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def audit(rep: dict, root: Path, tolerance: float = 0.30,
          allow_missing_optional: bool = False, drift_budget: float = DRIFT_BUDGET):
    checks = []

    def rec(cid, ok, detail):
        checks.append({"id": cid, "pass": bool(ok), "detail": detail})

    # C0 completeness
    missing = [k for k in REQUIRED if k not in rep]
    schema_ok = rep.get("schema") == SCHEMA
    lens = {k: len(rep[k]) for k in ("resolutions", "linf_errors") if isinstance(rep.get(k), list)}
    len_ok = len(set(lens.values())) <= 1 and len(lens) == 2
    rec("C0_completeness", not missing and schema_ok and len_ok,
        f"missing={missing or 'none'} schema={rep.get('schema')!r} "
        f"lengths={lens or 'n/a'}")

    declared = float(rep.get("declared_order", float("nan")))
    res = list(rep.get("resolutions", []))
    linf = [float(x) for x in rep.get("linf_errors", [])]
    l2 = [float(x) for x in rep.get("l2_errors", [])] if isinstance(rep.get("l2_errors"), list) else []

    # C1 stability
    finite = bool(linf) and all(math.isfinite(x) and x > 0 for x in linf)
    cfl = float(rep.get("cfl", float("nan")))
    cfl_ok = math.isfinite(cfl) and 0 < cfl <= CFL_MARGIN
    rec("C1_stability", bool(rep.get("stable")) and finite and cfl_ok,
        f"stable={rep.get('stable')} finite_positive_errors={finite} cfl={cfl}")

    # C2 non-degeneracy
    times = rep.get("measurement_times", [])
    nd = rep.get("non_degeneracy", {}) or {}
    single = bool(nd.get("single_mode", False))
    nd_ok = bool(times) and (len(times) >= 2 if single else True) and bool(nd)
    rec("C2_non_degeneracy", nd_ok,
        f"times={times} single_mode={single} attestation={'present' if nd else 'MISSING'}")

    # C3 monotone
    if len(linf) >= 2 and finite:
        ratio_needed = 2.0 ** (declared - 0.5)
        worst = min(a / b for a, b in zip(linf, linf[1:]))
        rec("C3_monotone", worst >= ratio_needed,
            f"min coarse/fine ratio {worst:.3f} >= {ratio_needed:.3f}")
    else:
        rec("C3_monotone", False, "need >=2 finite positive errors")

    # C4 order from end-time errors
    if len(linf) >= 3 and finite:
        p = _pair_orders(res, linf)
        fit = _fit_order(res, linf)
        finest_two = p[-2:]
        ok = all(abs(x - declared) <= tolerance for x in finest_two) and abs(fit - declared) <= tolerance
        rec("C4_order", ok,
            f"pair_orders={['%.3f' % x for x in p]} fit={fit:.3f} declared={declared} tol={tolerance}")
    else:
        rec("C4_order", False, "need >=3 finite positive errors")

    # C5 truncation residual
    resid = rep.get("residual_orders")
    if isinstance(resid, list) and resid:
        worst = min(resid)
        rec("C5_residual", worst >= declared - tolerance,
            f"residual_orders={['%.3f' % x for x in resid]} min={worst:.3f} "
            f"needs >= {declared - tolerance:.3f}")
    else:
        rec("C5_residual", allow_missing_optional, "residual_orders missing")

    # C6 Richardson self-convergence
    pr = rep.get("richardson_order")
    if isinstance(pr, (int, float)) and math.isfinite(float(pr)):
        rec("C6_richardson", abs(float(pr) - declared) <= tolerance,
            f"richardson={float(pr):.3f} declared={declared} tol={tolerance}")
    else:
        rec("C6_richardson", allow_missing_optional, "richardson_order missing")

    # C7 invariant: functional-aware (R1-R4 of scheme_independence_review.md)
    drift = rep.get("energy_drift")
    ef = rep.get("energy_functional") or {}
    structural = ef.get("structural_class")
    if isinstance(drift, list) and drift and all(float(d) > 0 for d in drift):
        finest = float(drift[-1])
        if structural == "exact_discrete":
            tol = max(STRUCTURAL_TOL, 10.0 * float(ef.get("solver_tolerance") or 0.0))
            ok = finest <= tol
            detail = (f"exact_discrete '{ef.get('name', '?')}' finest={finest:.2e} <= {tol:.1e}")
        else:
            dorders = _pair_orders(res, [float(d) for d in drift])
            # convergence is only meaningful above the roundoff floor: once the
            # drift reaches roundoff, further refinement cannot decrease it
            above = [d for i, d in enumerate(dorders)
                     if float(drift[i]) > 10.0 * STRUCTURAL_TOL
                     and float(drift[i + 1]) > STRUCTURAL_TOL and math.isfinite(d)]
            conv_ok = len(above) >= 2 and min(above) >= declared - 0.5
            roundoff_ok = finest <= STRUCTURAL_TOL
            budget_ok = finest <= drift_budget
            ok = budget_ok and (roundoff_ok or conv_ok)
            detail = (f"functional='{ef.get('name', 'UNDECLARED')}' structural={structural} "
                      f"drift_orders={['%.2f' % d for d in dorders]} finest={finest:.2e} "
                      f"budget={drift_budget:.1e} floor={STRUCTURAL_TOL:.0e} "
                      f"(roundoff={roundoff_ok} converged_above_floor={conv_ok} within_budget={budget_ok})")
        rec("C7_invariant", ok, detail)
    else:
        rec("C7_invariant", allow_missing_optional, "energy_drift series missing or non-positive")

    # C8 provenance
    impl = rep.get("implementation")
    declared_hash = rep.get("script_sha256")
    hash_ok = None
    if impl:
        p = Path(impl)
        if not p.is_absolute():
            p = root / p
        if p.is_file() and declared_hash:
            hash_ok = sha256_file(p) == declared_hash
    rec("C8_provenance", bool(impl) and bool(declared_hash) and hash_ok is not False,
        f"implementation={impl} hash_declared={bool(declared_hash)} hash_verified={hash_ok}")

    # C9 order uncertainty
    ou = rep.get("order_uncertainty") or {}
    cands = [float(ou[k]) for k in ("standard_error", "pair_spread_half_range")
             if isinstance(ou.get(k), (int, float)) and math.isfinite(float(ou[k]))]
    if cands:
        delta = max(cands)
        rec("C9_uncertainty", delta <= DELTA_MAX,
            f"delta={delta:.4f} <= {DELTA_MAX} (standard_error={ou.get('standard_error')}, "
            f"pair_spread_half_range={ou.get('pair_spread_half_range')})")
    else:
        rec("C9_uncertainty", allow_missing_optional, "order_uncertainty missing")

    passed = all(c["pass"] for c in checks)
    return {"schema": SCHEMA, "report_scheme": rep.get("scheme_id"),
            "checks": checks, "passed": passed,
            "verdict": "PASS" if passed else "FAIL",
            "failed_checks": [c["id"] for c in checks if not c["pass"]]}


def compare_reports(a: dict, b: dict) -> dict:
    """Cross-scheme agreement on the fitted order with reported uncertainties (R5)."""

    def p_delta(rep):
        ou = rep.get("order_uncertainty") or {}
        p = rep.get("fitted_order", ou.get("fit_order"))
        dd = [float(ou[k]) for k in ("standard_error", "pair_spread_half_range")
              if isinstance(ou.get(k), (int, float)) and math.isfinite(float(ou[k]))]
        if p is None or not dd:
            raise ValueError(f"{rep.get('scheme_id')}: fitted_order/order_uncertainty missing")
        return float(p), max(dd)

    pa, da = p_delta(a)
    pb, db = p_delta(b)
    allowed = max(AGREEMENT_FLOOR, math.sqrt(da * da + db * db))
    diff = abs(pa - pb)
    return {"scheme_a": a.get("scheme_id"), "order_a": pa, "delta_a": da,
            "scheme_b": b.get("scheme_id"), "order_b": pb, "delta_b": db,
            "difference": diff, "allowed": allowed, "agree": bool(diff <= allowed),
            "rule": "|pA - pB| <= max(0.25, sqrt(dA^2 + dB^2))"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report", nargs="+", help="one report, or two with --compare")
    ap.add_argument("--compare", action="store_true",
                    help="compare two reports' fitted orders under the R5 agreement rule")
    ap.add_argument("--root", default=".", help="repo root for hash verification")
    ap.add_argument("--tolerance", type=float, default=0.30)
    ap.add_argument("--drift-budget", type=float, default=DRIFT_BUDGET)
    ap.add_argument("--allow-missing-optional", action="store_true",
                    help="do not fail on absent residual/Richardson/drift fields")
    ap.add_argument("--pretty", action="store_true")
    a = ap.parse_args(argv)
    if a.compare:
        if len(a.report) != 2:
            ap.error("--compare needs exactly two report paths")
        ra = json.loads(Path(a.report[0]).read_text())
        rb = json.loads(Path(a.report[1]).read_text())
        result = compare_reports(ra, rb)
        print(json.dumps(result, indent=2) if a.pretty else json.dumps(result))
        return 0 if result["agree"] else 1
    rep = json.loads(Path(a.report[0]).read_text())
    result = audit(rep, Path(a.root), a.tolerance, a.allow_missing_optional, a.drift_budget)
    print(json.dumps(result, indent=2) if a.pretty else json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
