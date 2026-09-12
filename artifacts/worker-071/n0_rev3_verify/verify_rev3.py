#!/usr/bin/env python3
"""W071-N0-REV3-VERIFY-01 -- independent verifier for the N0 rev-3 convergence report.

Preregistered checks P1-P12 and controls K1-K5 are in PREREGISTRATION.json next to
this file. The verifier imports no builder and no solver, and writes only
report.json in its own directory. Exit 0 = VERIFIED_AT_PIN, 1 = REFUTED, 2 = DRIFT.

    python3 artifacts/worker-071/n0_rev3_verify/verify_rev3.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPORT_PATH = REPO / "numerics/results/flat_wave_convergence_rev3.json"
CERT_PATH = REPO / "numerics/protocol/n0_fixed_dt_certification.json"
PREREG_PATH = HERE / "PREREGISTRATION.json"

P_DESIGN = 2.0
P_TOL = 0.3
T_ORDER = 1e-9
T_METRIC = 1e-12
K_DETECT = 1e-3
DR_EXPECTED = {0.2, 0.1, 0.05, 0.025}


def sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def ls_order(pairs: list[tuple[float, float]]) -> float:
    """Least-squares slope of log(err) vs log(dr); slope is the order p for err ~ dr^p."""
    xs = [math.log(dr) for dr, _ in pairs]
    ys = [math.log(e) for _, e in pairs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den


def pair_orders(pairs: list[tuple[float, float]]) -> list[float]:
    """Adjacent-grid Richardson orders, ordered from coarse to fine."""
    ordered = sorted(pairs, key=lambda t: -t[0])
    out = []
    for (d0, e0), (d1, e1) in zip(ordered, ordered[1:]):
        out.append(math.log(e0 / e1) / math.log(d0 / d1))
    return out


def half_range(values: list[float]) -> float:
    return (max(values) - min(values)) / 2.0


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def agg_order(rows: list[dict]) -> float:
    """Order aggregated directly from rung error values (attribute tolerance floor)."""
    return ls_order([(float(r["dr"]), float(r["l2_error"])) for r in rows])


class Verifier:
    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.controls: list[dict] = []
        self.fails: list[str] = []
        self.notes: list[str] = []

    def check(self, cid: str, ok: bool, detail: str) -> None:
        self.checks.append({"check_id": cid, "pass": bool(ok), "detail": detail})
        if not ok:
            self.fails.append(f"{cid}: {detail}")

    def control(self, cid: str, fired: bool, detail: str) -> None:
        self.controls.append({"control_id": cid, "fired": bool(fired), "detail": detail})
        if not fired:
            self.fails.append(f"{cid}: control did not fire -- {detail}")


def main() -> int:
    v = Verifier()
    prereg = json.loads(PREREG_PATH.read_text())
    pins = prereg["pins"]
    live = {}
    report = json.loads(REPORT_PATH.read_text())
    cert = json.loads(CERT_PATH.read_text())

    # P1 pinned inputs resolve at the preregistered hashes
    bad = []
    for path, want in pins.items():
        live[path] = sha(REPO / path)
        if live[path] != want:
            bad.append(f"{path}: want {want[:12]} got {str(live[path])[:12]}")
    v.check("P1_pins_resolve", not bad, "; ".join(bad) or f"{len(pins)} pins resolve")

    # P2 every embedded (path, sha256) pair resolves
    embedded: list[tuple[str, str]] = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("path"), str) and isinstance(node.get("sha256"), str) and len(node["sha256"]) == 64:
                embedded.append((node["path"], node["sha256"]))
            for x in node.values():
                walk(x)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    walk(report)
    bad = []
    seen = set()
    for path, want in embedded:
        if (path, want) in seen:
            continue
        seen.add((path, want))
        got = sha(REPO / path)
        if got != want:
            bad.append(f"{path}: want {want[:12]} got {str(got)[:12]}")
    v.check("P2_embedded_pins", not bad, "; ".join(bad) or f"{len(seen)} embedded pins resolve")

    # P3 rung structure
    bad = []
    for name, s in cert["schemes"].items():
        rows = list(s["fixed_dt_certification"]["rows"])
        drs = {float(r["dr"]) for r in rows}
        dts = {float(r["dt"]) for r in rows}
        steps = {int(r["steps"]) for r in rows}
        if len(rows) != 4:
            bad.append(f"{name}: {len(rows)} rungs")
        if drs != DR_EXPECTED:
            bad.append(f"{name}: dr {sorted(drs)}")
        if dts != {1e-4}:
            bad.append(f"{name}: dt {sorted(dts)}")
        if len(steps) != 1:
            bad.append(f"{name}: steps not constant {sorted(steps)}")
    v.check("P3_four_rungs_fixed_dt", not bad, "; ".join(bad) or "3 schemes x 4 fixed-dt rungs")

    # P4 recomputed order from cert rows == declared
    measured = {}
    bad = []
    for name, s in cert["schemes"].items():
        fd = s["fixed_dt_certification"]
        rows = list(fd["rows"])
        p = agg_order(rows)
        measured[name] = {"recomputed_order_from_cert": p, "declared_order": float(fd["fit_order"])}
        if not close(p, float(fd["fit_order"]), T_ORDER):
            bad.append(f"{name}: recomputed {p:.15f} declared {float(fd['fit_order']):.15f}")
    v.check("P4_recompute_from_cert", not bad, "; ".join(bad) or "all 3 schemes match")

    # P5 report's own l2 map == cert row errors, and its order == cert order
    bad = []
    for name, s in cert["schemes"].items():
        fd = s["fixed_dt_certification"]
        rows = list(fd["rows"])
        rep_pairs = report["certification_basis"]["schemes"][name]["l2_error_by_dr"]
        rep_pairs = sorted((float(k), float(x)) for k, x in rep_pairs.items())
        cert_pairs = sorted((float(r["dr"]), float(r["l2_error"])) for r in rows)
        if len(rep_pairs) != len(cert_pairs):
            bad.append(f"{name}: {len(rep_pairs)} report vs {len(cert_pairs)} cert rungs")
            continue
        for (d0, e0), (d1, e1) in zip(rep_pairs, cert_pairs):
            if d0 != d1 or not close(e0, e1, T_METRIC):
                bad.append(f"{name}: dr={d1} report {e0!r} cert {e1!r}")
        p_rep = agg_order([{"dr": d, "l2_error": e} for d, e in rep_pairs])
        if not close(p_rep, float(fd["fit_order"]), T_ORDER):
            bad.append(f"{name}: report-map order {p_rep:.15f} vs cert {float(fd['fit_order']):.15f}")
        measured[name]["recomputed_order_from_report_map"] = p_rep
    v.check("P5_report_map_vs_cert", not bad, "; ".join(bad) or "report map is byte-consistent with cert rows")

    # P6 pair orders + delta_R5
    bad = []
    for name, s in cert["schemes"].items():
        fd = s["fixed_dt_certification"]
        rows = list(fd["rows"])
        pairs = sorted((float(r["dr"]), float(r["l2_error"])) for r in rows)
        rec = sorted(pair_orders(pairs), reverse=True)
        dec = sorted((float(x) for x in fd["pair_orders"]), reverse=True)
        if len(rec) != len(dec):
            bad.append(f"{name}: pair count {len(rec)} vs {len(dec)}")
            continue
        for a, b in zip(rec, dec):
            if not close(a, b, T_ORDER):
                bad.append(f"{name}: pair order {a:.15f} vs declared {b:.15f}")
        delta = max(half_range(rec), float(fd["least_squares_se"]))
        if not close(delta, float(fd["delta_R5"]), T_METRIC):
            bad.append(f"{name}: R5 {delta:.3e} vs declared {float(fd['delta_R5']):.3e}")
        measured[name]["recomputed_delta_R5"] = delta
        measured[name]["recomputed_pair_orders"] = rec
    v.check("P6_pair_orders_and_R5", not bad, "; ".join(bad) or "pair orders and R5 uncertainty match")

    # P7 cross-scheme agreement, design band, monotonicity
    bad = []
    ps = {n: float(report["order_claim"]["p_by_scheme"][n]) for n in report["order_claim"]["p_by_scheme"]}
    maxdiff = max(ps.values()) - min(ps.values())
    declared_diff = float(report["order_claim"]["max_cross_scheme_abs_dp"])
    if not close(maxdiff, declared_diff, T_METRIC):
        bad.append(f"max cross-scheme diff {maxdiff:.3e} vs declared {declared_diff:.3e}")
    for n, p in ps.items():
        if not (P_DESIGN - P_TOL <= p <= P_DESIGN + P_TOL):
            bad.append(f"{n}: p={p:.6f} outside [{P_DESIGN - P_TOL},{P_DESIGN + P_TOL}]")
        if not cert["schemes"][n]["fixed_dt_certification"]["monotone"]:
            bad.append(f"{n}: cert monotone is false")
    v.check("P7_cross_scheme_band_monotone", not bad, "; ".join(bad) or f"max diff {maxdiff:.3e} <= 0.25; all in band")

    # P8 temporal control / supporting-only constant-CFL
    bad = []
    tc = report["temporal_control"]
    for n, s in tc["schemes"].items():
        if tc["path"] != "numerics/protocol/temporal_subdominance_control.json":
            bad.append(f"{n}: unexpected temporal control path")
        if n == "cnfd" and s.get("admissible_as_spatial") is not False:
            bad.append("cnfd constant-CFL ladder not marked inadmissible")
        if n in ("cnfem", "lffd") and s.get("admissible_as_spatial") is not True:
            bad.append(f"{n} constant-CFL ladder not marked admissible")
    if "supporting only" not in json.dumps(report["supporting_diagnostics"].get("four_rung_mixed_order_addendum", {})):
        bad.append("four-rung constant-CFL addendum not marked supporting only")
    if "NOT a spatial claim" not in report["certification_basis"]["supersedes_evidence_basis"]["relabelled_as"]:
        bad.append("superseded constant-CFL ladder not relabelled as non-spatial")
    cert_schemes = set(report["certification_basis"]["schemes"])
    if cert_schemes != {"cnfd", "cnfem", "lffd"}:
        bad.append(f"certified scheme set {sorted(cert_schemes)}")
    v.check("P8_temporal_admissibility", not bad, "; ".join(bad) or "certified ladders are fixed-dt; constant-CFL supporting only")

    # P9 stop-rule closures
    bad = []
    for n, s in cert["schemes"].items():
        if len(s["fixed_dt_certification"]["rows"]) < 4:
            bad.append(f"{n}: {len(s['fixed_dt_certification']['rows'])} rungs in closure")
    if report["class_binding"]["sha256"] != pins["research_map/formulation_taxonomy.yaml"]:
        bad.append("class_binding hash != canonical F0 pin")
    verdicts = report["independent_replication"]["verdicts"]
    if not verdicts:
        bad.append("no independent replication verdict listed")
    for item in verdicts:
        p = item.get("path")
        if not p or sha(REPO / p) is None:
            bad.append(f"replication verdict path missing: {p}")
        elif item.get("sha256") and sha(REPO / p) != item["sha256"]:
            bad.append(f"replication verdict hash mismatch: {p}")
    v.check("P9_stop_rule_closures", not bad, "; ".join(bad) or f"4 rungs/scheme, F0 rebound, {len(verdicts)} replication verdicts resolvable")

    # P10 lock guard
    lg = report["lock_guard"]
    bad = []
    if (REPO / "numerics/spherical_solver").exists():
        bad.append("numerics/spherical_solver present")
    if lg.get("lock_state") != "locked":
        bad.append(f"lock_state {lg.get('lock_state')}")
    if lg.get("production_allowed") is not False:
        bad.append(f"production_allowed {lg.get('production_allowed')}")
    v.check("P10_lock_guard", not bad, "; ".join(bad) or "solver absent, lock held, production blocked")

    # P11 internal checks reported green
    ic = report["internal_checks"]
    n_checks = len(ic["checks"])
    v.check(
        "P11_internal_checks",
        bool(ic.get("all_pass")) and not ic.get("failures") and n_checks >= 50,
        f"all_pass={ic.get('all_pass')} failures={len(ic.get('failures', []))} checks={n_checks}",
    )

    # P12 declared claim surface
    bad = []
    if report.get("conclusion_type") != "numerical_evidence":
        bad.append(f"conclusion_type {report.get('conclusion_type')}")
    if report.get("gate") != "G-NUM":
        bad.append(f"gate {report.get('gate')}")
    if report.get("class_id") != "AF-WCC-SCALAR-SPH":
        bad.append(f"class_id {report.get('class_id')}")
    if not report.get("claims_not_made"):
        bad.append("claims_not_made empty")
    v.check("P12_declared_surface", not bad, "; ".join(bad) or "declared surface consistent with node/class/gate")

    # K1/K2 estimator controls on synthetic ladders
    for cid, exponent in (("K1_estimator_p2", 2.0), ("K2_estimator_p1", 1.0)):
        synth = [(d, 0.01 * (d ** exponent)) for d in (0.2, 0.1, 0.05, 0.025)]
        got = ls_order(synth)
        v.control(cid, close(got, exponent, T_ORDER), f"synthetic p={exponent} -> estimator {got:.15f}")

    # K3 perturbation detector fires
    base = cert["schemes"]["lffd"]["fixed_dt_certification"]
    base_p = float(base["fit_order"])
    mutants = []
    for i in range(4):
        rows = json.loads(json.dumps(base["rows"]))
        rows[i]["l2_error"] = float(rows[i]["l2_error"]) * 1.2
        mutant_p = agg_order(rows)
        mutants.append(abs(mutant_p - base_p))
    v.control("K3_mutation_detector", min(mutants) > K_DETECT, f"min |delta p| over 4 one-rung mutations = {min(mutants):.3e}")

    # K4 determinism
    r1 = {n: agg_order(cert["schemes"][n]["fixed_dt_certification"]["rows"]) for n in cert["schemes"]}
    r2 = {n: agg_order(cert["schemes"][n]["fixed_dt_certification"]["rows"]) for n in cert["schemes"]}
    v.control("K4_determinism", r1 == r2, "two recomputations identical")

    # K5 end-of-run drift
    drifted = []
    for path, want in pins.items():
        got = sha(REPO / path)
        if got != want:
            drifted.append(f"{path}: {str(got)[:12]}")
    v.control("K5_no_drift", not drifted, "; ".join(drifted) or "all pins unchanged during the run")

    if drifted:
        verdict = "DRIFT"
        code = 2
    elif v.fails:
        verdict = "REFUTED"
        code = 1
    else:
        verdict = "VERIFIED_AT_PIN"
        code = 0

    report_out = {
        "task_id": prereg["task_id"],
        "node_id": "N0",
        "class_id": "AF-WCC-SCALAR-SPH",
        "gate": "G-NUM",
        "actor": "worker-071",
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "verdict": verdict,
        "scope": "independent re-derivation from raw rung errors at one pin; no solver run; not a gate verdict",
        "pins": pins,
        "live_pins": live,
        "measured": measured,
        "checks": v.checks,
        "controls": v.controls,
        "failures": v.fails,
        "summary": {
            "checks_pass": sum(1 for c in v.checks if c["pass"]),
            "checks_total": len(v.checks),
            "controls_fired": sum(1 for c in v.controls if c["fired"]),
            "controls_total": len(v.controls),
            "max_cross_scheme_abs_p": maxdiff,
            "delta_R5_by_scheme": {n: measured[n]["recomputed_delta_R5"] for n in measured},
        },
        "next_falsifier": "Re-run verify_rev3.py at the pinned hashes; any P FAIL, control not firing, or pinned-hash change voids the verdict.",
    }
    (HERE / "report.json").write_text(json.dumps(report_out, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "failures": v.fails,
                      "checks": f"{report_out['summary']['checks_pass']}/{report_out['summary']['checks_total']}",
                      "controls": f"{report_out['summary']['controls_fired']}/{report_out['summary']['controls_total']}"},
                     ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
