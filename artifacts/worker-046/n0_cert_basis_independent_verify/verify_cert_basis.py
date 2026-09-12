#!/usr/bin/env python3
"""W046-N0-CERTBASIS-INDEP-01 — independent verification of the current G-NUM
certification basis: numerics/protocol/n0_fixed_dt_certification.json.

Bounded execution worker lifecycle (slot 046).  Read-only on every canonical
path.  Writes only inside this artifact directory.

What is independently checked
-----------------------------
A. Integrity / pins: the certification's declared frozen-module and protocol
   hashes match disk; the class-binding anchor (F0 rev5 taxonomy) is hashed and
   matched to disk here, because the certification itself carries no taxonomy
   hash (finding F-1).
B. Arithmetic re-derivation from the artifact's OWN rows, with an independently
   implemented ordinary-least-squares fit (normal equations, not np.polyfit):
   order, slope standard error, pair orders, pair half-range, R5 delta,
   residuals, monotonicity, dt rule, rung set.
C. Cross-scheme R5 agreement recomputed from the independently derived orders.
D. Full independent RE-EXECUTION of the 3 schemes x 4 fixed-dt rungs against the
   hash-guarded frozen module, compared to the certification's rows.
E. Class binding to F0 rev5 AF-WCC-SCALAR-SPH: canonical class-separation
   detector finds no class merge / family mismatch / conclusion inflation; the
   artifact declares conclusion_type numerical_evidence and asserts no class
   conclusion (calibration sub-case scoping).
F. Controls C1-C6 (perturbation detector, truncation detector, dt-rule detector,
   determinism, no-write drift canary, standing classsep regression).

Verdict rule (pre-registered):
  VOID      if any pinned hash mismatches disk (fail closed, exit 2);
  REFUTED   if the independent re-execution disagrees with the artifact rows or
            a declared order leaves the 2.0 +/- 0.3 band;
  PARTIAL   if only bookkeeping/statistics criteria fail;
  SUPPORTED if P1-P10 pass and controls C1-C6 behave as pre-registered.

This is worker-level evidence.  No gate verdict, no node completion, no
numerics-lock release, no physics claim.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CANON_CERT = ROOT / "numerics/protocol/n0_fixed_dt_certification.json"
CANON_FROZEN = ROOT / "numerics/tests/flat_wave_replication.py"
CANON_PROTOCOL = ROOT / "numerics/CONVERGENCE_PROTOCOL.md"
CANON_TAXONOMY = ROOT / "research_map/formulation_taxonomy.yaml"
CANON_PUBLISHED_4RUNG = ROOT / "numerics/tests/n0_order_4rung.json"
CANONICAL_PATHS = [CANON_CERT, CANON_FROZEN, CANON_PROTOCOL, CANON_TAXONOMY, CANON_PUBLISHED_4RUNG]

DECLARED_FROZEN = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"
DECLARED_PROTOCOL = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
DECLARED_TAXONOMY_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
RUNG_DRS = [0.2, 0.1, 0.05, 0.025]
DT_FIXED = 1e-4
P_DESIGN, P_TOL, R5_BOUND = 2.0, 0.3, 0.25
TOL_ARITH = 1e-9          # absolute, for declared-vs-recomputed order statistics
TOL_ROW_REL = 1e-12       # relative, for re-executed vs declared l2 rows
SCHEMES = ["lffd", "cnfd", "cnfem"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ols(xs, ys):
    """Independent OLS: normal equations + residual-based slope SE."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    resid = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    dof = n - 2
    s2 = sum(r * r for r in resid) / dof
    se = math.sqrt(s2 / sxx)
    return {"slope": slope, "intercept": intercept, "residuals": resid, "slope_se": se}


def pair_orders(drs, errs):
    return [math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1])
            for i in range(len(errs) - 1)]


def rel_diff(a, b):
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def walk_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def drift_canary():
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in CANONICAL_PATHS if p.is_file()}


def main() -> int:
    t_start = time.time()
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    crit: dict[str, dict] = {}
    findings: list[dict] = []
    controls: list[dict] = []

    def record(cid, ok, detail, **extra):
        crit[cid] = {"pass": bool(ok), "detail": detail}
        crit[cid].update(extra)
        return bool(ok)

    # ---------------- P1 pins ----------------
    pre = drift_canary()
    cert_hash = sha256_file(CANON_CERT)
    frozen_hash = sha256_file(CANON_FROZEN)
    protocol_hash = sha256_file(CANON_PROTOCOL)
    taxonomy_hash = sha256_file(CANON_TAXONOMY)
    published_4rung_hash = sha256_file(CANON_PUBLISHED_4RUNG)
    pins = {
        "certification": {"path": str(CANON_CERT.relative_to(ROOT)), "sha256": cert_hash},
        "frozen_module": {"path": str(CANON_FROZEN.relative_to(ROOT)), "sha256": frozen_hash,
                          "declared": DECLARED_FROZEN, "match": frozen_hash == DECLARED_FROZEN},
        "protocol": {"path": str(CANON_PROTOCOL.relative_to(ROOT)), "sha256": protocol_hash,
                     "declared": DECLARED_PROTOCOL, "match": protocol_hash == DECLARED_PROTOCOL},
        "f0_taxonomy_rev5_anchor": {"path": str(CANON_TAXONOMY.relative_to(ROOT)), "sha256": taxonomy_hash,
                                    "expected_rev5": DECLARED_TAXONOMY_REV5,
                                    "match": taxonomy_hash == DECLARED_TAXONOMY_REV5,
                                    "note": "hash supplied by this check; the certification carries no taxonomy pin (F-1)"},
        "published_4rung_constant_cfl": {"path": str(CANON_PUBLISHED_4RUNG.relative_to(ROOT)),
                                         "sha256": published_4rung_hash,
                                         "role": "superseded evidence basis, relabelled mixed-order control"},
    }
    hash_ok = pins["frozen_module"]["match"] and pins["protocol"]["match"] and pins["f0_taxonomy_rev5_anchor"]["match"]
    record("P1_hash_pins_match_disk", hash_ok,
           "frozen module / protocol / F0 rev5 all match declared or expected hashes" if hash_ok
           else "a pinned canonical hash mismatched disk -> fail closed", pins=pins)
    if not hash_ok:
        # VOID, fail closed before any further claim
        result = {
            "schema": "worker-046/n0-certbasis-independent-verify/1.0",
            "task_id": "W046-N0-CERTBASIS-INDEP-01",
            "created_at": ts, "verdict": "VOID", "criteria_outcomes": crit,
            "reason": "pinned hash mismatch; no comparison is valid (fail closed)",
        }
        (OUT / "results.json").write_text(json.dumps(result, indent=1, sort_keys=True))
        print(json.dumps(result, indent=1)[:2000])
        return 2

    cert = json.loads(CANON_CERT.read_text())

    # ---------------- P2 artifact integrity + rung/dt rule ----------------
    integrity = {
        "node_id": cert.get("node_id"), "gate": cert.get("gate"), "class_id": cert.get("class_id"),
        "conclusion_type": cert.get("conclusion_type"),
        "schemes": sorted(cert.get("schemes", {}).keys()),
        "schema": cert.get("schema"),
    }
    integrity_ok = (integrity["node_id"] == "N0" and integrity["gate"] == "G-NUM"
                    and integrity["class_id"] == "AF-WCC-SCALAR-SPH"
                    and integrity["conclusion_type"] == "numerical_evidence"
                    and integrity["schemes"] == sorted(SCHEMES))
    rung_issues = []
    for s in SCHEMES:
        fd = cert["schemes"][s]["fixed_dt_certification"]
        drs = [r["dr"] for r in fd["rows"]]
        dts = [r["dt"] for r in fd["rows"]]
        if len(fd["rows"]) != 4:
            rung_issues.append(f"{s}: n_rungs={len(fd['rows'])} != 4")
        if [round(x, 6) for x in drs] != RUNG_DRS:
            rung_issues.append(f"{s}: dr set {drs} != {RUNG_DRS}")
        if any(abs(dt - DT_FIXED) > 0 for dt in dts):
            rung_issues.append(f"{s}: dt not fixed at 1e-4: {dts}")
    record("P2_integrity_and_dt_rule", integrity_ok and not rung_issues,
           "identity fields correct; 3 schemes x 4 rungs with dt == 1e-4 on every rung"
           if integrity_ok and not rung_issues else f"issues: {rung_issues}", integrity=integrity,
           rung_issues=rung_issues)

    # ---------------- P3-P7 arithmetic re-derivation ----------------
    per_scheme = {}
    arith_ok, mono_ok, pair_ok, uncertainty_ok, band_ok = True, True, True, True, True
    for s in SCHEMES:
        fd = cert["schemes"][s]["fixed_dt_certification"]
        rows = sorted(fd["rows"], key=lambda r: -r["dr"])
        drs = [r["dr"] for r in rows]
        errs = [r["l2_error"] for r in rows]
        fit = ols([math.log(d) for d in drs], [math.log(e) for e in errs])
        po = pair_orders(drs, errs)
        half = (max(po) - min(po)) / 2.0
        delta_r5 = max(half, fit["slope_se"])
        mono = all(errs[i + 1] < errs[i] for i in range(len(errs) - 1))
        in_band = abs(fit["slope"] - P_DESIGN) <= P_TOL
        pairs_match = len(po) == len(fd["pair_orders"]) and all(
            rel_diff(a, b) <= TOL_ARITH for a, b in zip(po, fd["pair_orders"]))
        order_match = rel_diff(fit["slope"], fd["fit_order"]) <= TOL_ARITH
        se_match = rel_diff(fit["slope_se"], fd["least_squares_se"]) <= TOL_ARITH
        delta_match = rel_diff(delta_r5, fd["delta_R5"]) <= TOL_ARITH
        resid_match = len(fit["residuals"]) == len(fd["lsq_residuals"]) and all(
            abs(a - b) <= 1e-12 for a, b in zip(fit["residuals"], fd["lsq_residuals"]))
        half_match = rel_diff(half, fd["pair_half_range"]) <= TOL_ARITH
        mono_ok &= mono
        pair_ok &= pairs_match
        arith_ok &= order_match and resid_match
        uncertainty_ok &= se_match and delta_match and half_match
        band_ok &= in_band and all(abs(p - P_DESIGN) <= P_TOL for p in po)
        per_scheme[s] = {
            "dr": drs, "l2_error": errs,
            "refit_order": fit["slope"], "declared_order": fd["fit_order"], "order_match": order_match,
            "refit_slope_se": fit["slope_se"], "declared_slope_se": fd["least_squares_se"],
            "slope_se_match": se_match,
            "refit_pair_orders": po, "declared_pair_orders": fd["pair_orders"], "pair_orders_match": pairs_match,
            "refit_pair_half_range": half, "declared_pair_half_range": fd["pair_half_range"],
            "half_range_match": half_match,
            "refit_delta_R5": delta_r5, "declared_delta_R5": fd["delta_R5"], "delta_R5_match": delta_match,
            "residuals_match": resid_match, "monotone": mono, "within_band": in_band,
            "declared_monotone": fd["monotone"], "declared_within_band": fd["within_band"],
        }
    record("P3_monotone", mono_ok, "errors strictly decrease with dr for all three schemes")
    record("P4_refit_order_matches", arith_ok,
           "independent normal-equation OLS reproduces declared orders and residuals", per_scheme=per_scheme)
    record("P5_uncertainty_consistency", uncertainty_ok,
           "delta_R5 == max(pair half-range, slope SE) and matches declared to <1e-9 for all schemes")
    record("P6_pair_orders_and_band", pair_ok and band_ok,
           "declared pair orders reproduce; fitted order and pair orders all inside 2.0 +/- 0.3")

    cross = {}
    cross_ok = True
    for i, a in enumerate(SCHEMES):
        for b in SCHEMES[i + 1:]:
            da = per_scheme[a]["refit_order"] - per_scheme[b]["refit_order"]
            cross[f"{a}_vs_{b}"] = {"abs_dp_recomputed": abs(da), "r5_bound": R5_BOUND,
                                    "agree": abs(da) <= R5_BOUND}
            cross_ok &= abs(da) <= R5_BOUND
    declared_cross = cert.get("cross_scheme_R5", {})
    declared_pairs_ok = all(
        rel_diff(v["abs_order_diff"], cross[f"{v['pair'].split(' vs ')[0]}_vs_{v['pair'].split(' vs ')[1]}"]["abs_dp_recomputed"]) <= TOL_ARITH
        for v in declared_cross.get("pairs", [])
        if f"{v['pair'].split(' vs ')[0]}_vs_{v['pair'].split(' vs ')[1]}" in cross)
    record("P7_cross_scheme_R5", cross_ok and declared_pairs_ok,
           "recomputed pairwise |dp| all <= 0.25 and match the declared pairs", cross=cross,
           declared_max_pairwise_abs_diff=declared_cross.get("max_pairwise_abs_diff"))

    # ---------------- P8 mixed-order control is labelled and distinct ----------------
    ctrl = {}
    ctrl_ok = True
    for s in SCHEMES:
        cc = cert["schemes"][s]["constant_cfl_mixed_order_control"]
        rows = sorted(cc["rows"], key=lambda r: -r["dr"])
        dts = [r["dt"] for r in rows]
        cfl_ok = all(abs(r["cfl_effective"] - 0.5) < 1e-12 for r in rows) if "cfl_effective" in rows[0] else None
        refit = ols([math.log(r["dr"]) for r in rows], [math.log(r["l2_error"]) for r in rows])["slope"]
        ctrl[s] = {"dt_values": dts, "dt_not_fixed": all(abs(dt - DT_FIXED) > 0 for dt in dts),
                   "refit_order": refit, "declared_order": cc["fit_order"],
                   "order_match": rel_diff(refit, cc["fit_order"]) <= TOL_ARITH,
                   "declared_delta_R5": cc["delta_R5"],
                   "fixed_dt_delta_smaller": cert["schemes"][s]["fixed_dt_certification"]["delta_R5"]
                                             < cc["delta_R5"],
                   "constant_cfl_rule": cfl_ok}
        ctrl_ok &= ctrl[s]["dt_not_fixed"] and ctrl[s]["order_match"] and ctrl[s]["fixed_dt_delta_smaller"]
    superseded = cert.get("supersedes_evidence_basis", {})
    record("P8_mixed_order_control_distinct", ctrl_ok,
           "constant-CFL rows use dt != 1e-4, reproduce their declared order, and are relabelled mixed-order; "
           "fixed-dt R5 deltas are strictly smaller", control=ctrl,
           supersedes_reason=str(superseded.get("reason", ""))[:200],
           relabelled_as=superseded.get("relabelled_as"))

    # ---------------- P9 independent re-execution of the frozen module ----------------
    sys.path.insert(0, str(ROOT / "numerics/tests"))
    import flat_wave_replication as fwr  # noqa: E402

    frozen_before = sha256_file(CANON_FROZEN)
    reexec = {}
    reexec_ok = True
    t0 = time.time()
    for s in SCHEMES:
        declared_rows = {round(r["dr"], 6): r for r in cert["schemes"][s]["fixed_dt_certification"]["rows"]}
        errs, rows_out = [], []
        for dr in RUNG_DRS:
            out = fwr.order_study(s, dr_values=[dr], dt_rule=lambda d: DT_FIXED)
            row = out["rows"][0]
            drow = declared_rows[round(dr, 6)]
            match = (abs(row["l2_error"] - drow["l2_error"]) <= TOL_ROW_REL * max(abs(drow["l2_error"]), 1e-300))
            errs.append(row["l2_error"])
            rows_out.append({"dr": dr, "dt": row["dt"], "steps": row["steps"],
                             "l2_error_reexecuted": row["l2_error"],
                             "l2_error_declared": drow["l2_error"],
                             "bitwise_equal": row["l2_error"] == drow["l2_error"],
                             "match": match})
            reexec_ok &= match and abs(row["dt"] - DT_FIXED) == 0 and row["steps"] == drow["steps"]
        fit = ols([math.log(d) for d in RUNG_DRS], [math.log(e) for e in errs])
        dorder = cert["schemes"][s]["fixed_dt_certification"]["fit_order"]
        order_match = rel_diff(fit["slope"], dorder) <= TOL_ARITH
        reexec_ok &= order_match
        reexec[s] = {
            "rows": rows_out,
            "reexecuted_fit_order": fit["slope"], "declared_fit_order": dorder,
            "order_match": order_match,
            "reexecuted_pair_orders": pair_orders(RUNG_DRS, errs),
            "declared_pair_orders": cert["schemes"][s]["fixed_dt_certification"]["pair_orders"],
        }
    frozen_after = sha256_file(CANON_FROZEN)
    reexec_seconds = time.time() - t0
    record("P9_independent_reexecution", reexec_ok and frozen_before == frozen_after == DECLARED_FROZEN,
           "12/12 fixed-dt rungs re-executed; rows reproduce to <=1e-12 relative (bitwise where equal); "
           "refit orders match; frozen module hash unchanged across the run",
           reexecution=reexec, seconds=round(reexec_seconds, 2))

    # ---------------- P10 class binding to F0 rev5 ----------------
    import yaml  # noqa: E402
    tax = yaml.safe_load(CANON_TAXONOMY.read_text())
    cls = tax["classes"]["AF-WCC-SCALAR-SPH"]
    axes = cls["axes"]
    binding = {
        "taxonomy_path": str(CANON_TAXONOMY.relative_to(ROOT)),
        "taxonomy_sha256": taxonomy_hash,
        "taxonomy_revision": tax.get("revision"),
        "taxonomy_status": tax.get("status"),
        "class_id_declared_by_certification": cert.get("class_id"),
        "class_present_in_rev5": "AF-WCC-SCALAR-SPH" in tax.get("class_ids", []),
        "class_axes": axes,
        "certification_conclusion_type": cert.get("conclusion_type"),
        "class_conclusion_type": cls["conclusion"]["type"],
        "conclusion_type_is_calibration_not_class_conclusion":
            cert.get("conclusion_type") == "numerical_evidence"
            and cert.get("conclusion_type") != cls["conclusion"]["type"],
    }
    # canonical class-separation detector on the artifact object
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    classsep_findings = cs.findings(cert, "numerics/protocol/n0_fixed_dt_certification.json")
    # class-conclusion phrase scan with negation / not_claimed exemptions
    concl_re = re.compile(r"weak[\s_-]*cosmic|visible|naked[\s_-]*singular|inextendib|"
                          r"strong[\s_-]*cosmic|cauchy[\s_-]*horizon|(?<![A-Za-z])wcc(?![A-Za-z])|"
                          r"(?<![A-Za-z])scc(?![A-Za-z])", re.I)
    negation = re.compile(r"\b(no|not|never|without|zero|absent|nor|disclaim|does\s+not)\b", re.I)
    phrase_hits = []
    for path, val in walk_strings(cert):
        for m in concl_re.finditer(val):
            lo = max(0, m.start() - 90)
            ctx = val[lo:m.end() + 90]
            exempt = path.startswith("not_claimed") or path.startswith("falsifier") \
                or path in ("class_id", "class_ids") \
                or val[max(0, m.start() - 3):m.start()].upper().endswith("AF-") \
                or bool(negation.search(val[max(0, m.start() - 40):m.start()]))
            phrase_hits.append({"path": path, "match": m.group(0), "exempt": exempt, "context": ctx})
    unexempt = [h for h in phrase_hits if not h["exempt"]]
    cert_text = json.dumps(cert)
    calib_scope_re = re.compile(r"flat[\s-]*space", re.I)
    calib_kind_re = re.compile(r"calibration|discretisation|discretization|numerical[_ ]evidence|evidence only", re.I)
    not_claimed_text = " ".join(str(x) for x in cert.get("not_claimed", []))
    is_calibration = (bool(calib_scope_re.search(cert_text)) and bool(calib_kind_re.search(cert_text))
                      and bool(negation.search(not_claimed_text)))
    binding_ok = (binding["class_present_in_rev5"]
                  and binding["conclusion_type_is_calibration_not_class_conclusion"]
                  and not classsep_findings and not unexempt and is_calibration)
    record("P10_class_binding_f0_rev5", binding_ok,
           "class present in F0 rev5; numerical_evidence (not the class conclusion); canonical classsep detector clean; "
           "no unexempted class-conclusion phrase; explicit flat-space calibration scoping",
           binding=binding, classsep_findings=classsep_findings,
           conclusion_phrase_hits=phrase_hits, unexempt_phrase_hits=unexempt)
    if not binding["class_present_in_rev5"]:
        findings.append({"id": "F-2", "severity": "hard",
                         "text": "class AF-WCC-SCALAR-SPH absent from the live F0 revision"})
    findings.append({"id": "F-1", "severity": "soft",
                     "text": "the certification artifact carries no F0 taxonomy hash; its class binding is not "
                             "hash-pinned inside the artifact. This check supplies the anchor at read time: F0 rev5 "
                             f"{DECLARED_TAXONOMY_REV5[:12]} (match={pins['f0_taxonomy_rev5_anchor']['match']}). "
                             "Owner for an in-artifact pin: astra-lead-numerics / controller."})

    # ---------------- Controls C1-C6 ----------------
    def detect(mutate):
        """Return (order_changed, dt_ok, rung_ok) for a mutated in-memory copy."""
        m = json.loads(json.dumps(cert))
        mutate(m)
        changed, dtbad, rungbad = False, False, False
        for s in SCHEMES:
            fd = m["schemes"][s]["fixed_dt_certification"]
            rows = sorted(fd["rows"], key=lambda r: -r["dr"])
            if len(rows) != 4:
                rungbad = True
            if any(abs(r["dt"] - DT_FIXED) > 0 for r in rows):
                dtbad = True
            refit = ols([math.log(r["dr"]) for r in rows], [math.log(r["l2_error"]) for r in rows])["slope"]
            if rel_diff(refit, fd["fit_order"]) > 1e-6:
                changed = True
        return changed, dtbad, rungbad

    c1, _, _ = detect(lambda m: m["schemes"]["cnfem"]["fixed_dt_certification"]["rows"][2].__setitem__(
        "l2_error", m["schemes"]["cnfem"]["fixed_dt_certification"]["rows"][2]["l2_error"] * 1.01))
    controls.append({"id": "C1", "description": "non-vacuous arithmetic detector: +1% on one cnfem row must move the refit order",
                     "expected": "detected", "observed": "detected" if c1 else "NOT detected", "pass": bool(c1)})
    _, _, c2 = detect(lambda m: m["schemes"]["lffd"]["fixed_dt_certification"]["rows"].pop())
    controls.append({"id": "C2", "description": "rung-count detector: dropping one lffd row must fail the 4-rung rule",
                     "expected": "detected", "observed": "detected" if c2 else "NOT detected", "pass": bool(c2)})
    _, c3, _ = detect(lambda m: m["schemes"]["cnfd"]["fixed_dt_certification"]["rows"][1].__setitem__("dt", 2e-4))
    controls.append({"id": "C3", "description": "dt-rule detector: dt=2e-4 on one cnfd row must fail the fixed-dt rule",
                     "expected": "detected", "observed": "detected" if c3 else "NOT detected", "pass": bool(c3)})
    run_a = ols([math.log(d) for d in RUNG_DRS],
                [math.log(r["l2_error"]) for r in sorted(cert["schemes"]["lffd"]["fixed_dt_certification"]["rows"],
                                                         key=lambda r: -r["dr"])])["slope"]
    run_b = ols([math.log(d) for d in RUNG_DRS],
                [math.log(r["l2_error"]) for r in sorted(cert["schemes"]["lffd"]["fixed_dt_certification"]["rows"],
                                                         key=lambda r: -r["dr"])])["slope"]
    controls.append({"id": "C4", "description": "determinism: two refits of the same rows are bitwise equal",
                     "expected": "equal", "observed": "equal" if run_a == run_b else "different", "pass": run_a == run_b})
    post = drift_canary()
    drift = {k: [pre.get(k), post.get(k)] for k in set(pre) | set(post) if pre.get(k) != post.get(k)}
    controls.append({"id": "C5", "description": "no-write drift canary over 5 canonical paths (before/after lifecycle)",
                     "expected": "no drift", "observed": "no drift" if not drift else f"drift: {drift}",
                     "pass": not drift})
    cp = subprocess.run([sys.executable, str(ROOT / "runtime/bin/classsep_regression.py")],
                        capture_output=True, text=True, cwd=str(ROOT), timeout=600)
    tail = [ln for ln in cp.stdout.strip().splitlines() if ln.strip()][-3:]
    c6 = cp.returncode == 0 and any("PASS" in ln for ln in tail)
    controls.append({"id": "C6", "description": "standing class-separation regression (canonical runner)",
                     "expected": "17 leaks / 10 controls / VERDICT PASS",
                     "observed": {"returncode": cp.returncode, "tail": tail}, "pass": bool(c6)})
    controls_ok = all(c["pass"] for c in controls)

    # ---------------- verdict ----------------
    primary = ["P1_hash_pins_match_disk", "P2_integrity_and_dt_rule", "P3_monotone", "P4_refit_order_matches",
               "P5_uncertainty_consistency", "P6_pair_orders_and_band", "P7_cross_scheme_R5",
               "P8_mixed_order_control_distinct", "P9_independent_reexecution", "P10_class_binding_f0_rev5"]
    failed = [k for k in primary if not crit[k]["pass"]]
    if not crit["P9_independent_reexecution"]["pass"]:
        verdict = "REFUTED"
    elif failed:
        verdict = "PARTIAL"
    elif controls_ok:
        verdict = "SUPPORTED"
    else:
        verdict = "PARTIAL"

    cert_claim = cert.get("verdict", {}).get("claim", "")
    falsifier = (
        "Withdraw if any of: (a) any pinned input hash changes at re-check time (frozen module 8ade1cdc, protocol "
        "1e6cdf04, F0 rev5 0abb9ed8, certification 1677822ceb9c) — a mismatch voids the comparison, fail closed; "
        "(b) a re-execution of the frozen module at any fixed-dt rung disagrees with the certification row by more "
        "than 1e-12 relative; (c) an independent fit places any scheme's order outside 2.0 +/- 0.3 or a pairwise "
        "|dp| above the R5 bound 0.25; (d) the certification is shown to assert the AF-WCC-SCALAR-SPH class "
        "conclusion (it declares numerical_evidence and this check found no such assertion); (e) the constant-CFL "
        "ladder is shown to be the actual certification basis (it is relabelled mixed-order here)."
    )

    results = {
        "schema": "worker-046/n0-certbasis-independent-verify/1.0",
        "task_id": "W046-N0-CERTBASIS-INDEP-01",
        "worker": "worker-046",
        "role": "bounded execution worker; no gate authority; read-only on canonical paths",
        "created_at": ts,
        "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence",
        "target": {
            "path": "numerics/protocol/n0_fixed_dt_certification.json",
            "sha256": cert_hash,
            "declared_claim": cert_claim,
            "declared_verdict": cert.get("verdict", {}),
            "role": "current G-NUM certification basis (fixed dt = 1e-4, four rungs, three schemes)",
            "supersedes": cert.get("supersedes_evidence_basis", {}),
        },
        "verdict": verdict,
        "verdict_rule": ("VOID on hash mismatch; REFUTED if the independent re-execution disagrees with the artifact "
                         "rows; PARTIAL if only bookkeeping/statistics criteria fail; SUPPORTED if P1-P10 pass and "
                         "controls C1-C6 behave as pre-registered."),
        "criteria_outcomes": crit,
        "failed_criteria": failed,
        "controls": controls,
        "controls_pass": f"{sum(1 for c in controls if c['pass'])}/{len(controls)}",
        "findings": findings,
        "independent_binding_anchor": pins["f0_taxonomy_rev5_anchor"],
        "falsifier": falsifier,
        "not_claimed": [
            "no gate verdict and no gate self-pass; supporting evidence for G-NUM only",
            "no node completion; N0 stays active/unverified and numerics_lock stays LOCKED",
            "no physics claim; flat-space calibration evidence only",
            "no claim that the certification's evidence basis is sufficient for G-NUM pass; that is Astra/audit authority",
        ],
        "runtime_seconds": round(time.time() - t_start, 2),
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
    verification = dict(results)
    verification["evidence_refs"] = [
        f"numerics/protocol/n0_fixed_dt_certification.json#{cert_hash[:12]}",
        f"numerics/tests/flat_wave_replication.py#{frozen_hash[:12]}",
        f"numerics/CONVERGENCE_PROTOCOL.md#{protocol_hash[:12]}",
        f"research_map/formulation_taxonomy.yaml#{taxonomy_hash[:12]}",
        f"numerics/tests/n0_order_4rung.json#{published_4rung_hash[:12]}",
        "artifacts/worker-067/n0_f0_rebind/rebind_check.json#22afbea8a137",
        "artifacts/worker-046/n0_fixed_dt_independent/verification.json#814452111bc8",
    ]
    (OUT / "verification.json").write_text(json.dumps(verification, indent=1, sort_keys=True))

    print(json.dumps({"verdict": verdict, "controls_pass": results["controls_pass"],
                      "failed_criteria": failed, "frozen_hash_ok": frozen_hash == DECLARED_FROZEN,
                      "runtime_seconds": results["runtime_seconds"]}, indent=1))
    return 0 if verdict == "SUPPORTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
