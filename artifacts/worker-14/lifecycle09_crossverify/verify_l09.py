#!/usr/bin/env python3
"""W014-GNUM-N0-L09-CROSSVERIFY-01 — independent read-only cross-verification of the
lifecycle-09 lead verification record for N0 / G-NUM.

Read-only over every pinned input. Writes only report.json (and nothing else) under
artifacts/worker-14/lifecycle09_crossverify/. No gate verdict, no node transition, no
numerics_lock action. Re-runnable:  python3 verify_l09.py --out report.json

Design notes:
  * The OLS log-log fit is implemented here from first principles (no import of any project
    module, no numpy) so that agreement is independent evidence.
  * Controls exercise the same detector functions on synthetic mutated inputs; a control
    that does not fire fails the run (fail-closed).
  * All pinned inputs are hashed before and after; any drift aborts with INCONCLUSIVE.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

TARGET = "numerics/protocol/lifecycle09_lead_verify.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = "numerics/results/flat_wave_convergence_rev3.json"
TAXO = "research_map/formulation_taxonomy.yaml"
MAP = "research_map/research_map.json"
L08 = "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
VERDICTS = (
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json",
    "artifacts/worker-057/n0_fixeddt_verify/report.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
)

PINS = {
    TARGET: None,  # target is the object under test; anchored by prefix in A4, drift-guarded
    CERT: "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    REV3: "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
    TAXO: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/worker-046/n0_fixed_dt_independent/verification.json": (
        "814452111bc8912bb21f8e0a353fe78096640d299e469578462b755592ea9a61"),
    "artifacts/worker-057/n0_fixeddt_verify/report.json": (
        "b906445878f3130dd710595a362883e29be87f11cb8d8edbdbc79539147b3b04"),
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json": (
        "65ae766d9e4c205762cff35fb822915d4b00bd4502a0326455bed84e7b3169d6"),
    L08: "88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75",
    MAP: None,  # live; drift-guarded only
}
# The target's full pin is taken from disk at run time and recorded; the prefix above is a
# sanity anchor against the lead's record.
TARGET_PREFIX = "baa93446d3702180"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text())


# --------------------------------------------------------------------------------------
# independent estimators
# --------------------------------------------------------------------------------------
def ols_loglog(rows: list[dict]) -> dict:
    """Pure-Python OLS of y=ln(l2_error) on x=ln(dr); analytic slope SE with n-2 dof."""
    xs = [math.log(r["dr"]) for r in rows]
    ys = [math.log(r["l2_error"]) for r in rows]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    p = sxy / sxx
    a = my - p * mx
    res = [y - (a + p * x) for x, y in zip(xs, ys)]
    sse = sum(r * r for r in res)
    se = math.sqrt((sse / (n - 2)) / sxx) if n > 2 else None
    return {"fit_order": p, "least_squares_se": se, "lsq_residuals": res, "sse": sse,
            "n_rungs": n, "dr_values": [r["dr"] for r in rows],
            "dt_values": sorted({r["dt"] for r in rows})}


def pair_orders(rows: list[dict]) -> list[float]:
    out = []
    for i in range(len(rows) - 1):
        e0, e1 = rows[i]["l2_error"], rows[i + 1]["l2_error"]
        h0, h1 = rows[i]["dr"], rows[i + 1]["dr"]
        out.append(math.log(e0 / e1) / math.log(h0 / h1))
    return out


def strictly_decreasing(xs: list[float]) -> bool:
    return all(xs[i] > xs[i + 1] for i in range(len(xs) - 1))


def band_ok(p: float, p_design: float = 2.0, tol: float = 0.3) -> bool:
    return abs(p - p_design) <= tol


def r5_delta(pair: list[float], se: float) -> float:
    half_range = (max(pair) - min(pair)) / 2.0 if pair else 0.0
    return max(half_range, se)


def agreement_ok(d: float, bound_floor: float = 0.25) -> bool:
    return d <= bound_floor


def agreement_ok_r5(pa: float, pb: float, da: float, db: float) -> bool:
    return abs(pa - pb) <= max(0.25, math.sqrt(da * da + db * db))


# --------------------------------------------------------------------------------------
# detector functions (also used by controls on synthetic inputs)
# --------------------------------------------------------------------------------------
def detect_not_monotone(errors: list[float]) -> bool:
    return not strictly_decreasing(errors)


def detect_band_violation(p: float, tol: float = 0.3) -> bool:
    return not band_ok(p, 2.0, tol)


def detect_spread_violation(spread: float, floor: float = 0.25) -> bool:
    return spread > floor


def detect_pin_mismatch(declared: str, measured: str) -> bool:
    return declared != measured


def detect_token_mismatch(observed, expected) -> bool:
    return observed != expected


def detect_class_absent(text: str, class_id: str) -> bool:
    return class_id not in text


def detect_lock_violation(solver_present: bool, lock_state: str, locked_nodes: list) -> bool:
    return solver_present or lock_state != "locked" or "N1" not in locked_nodes


def detect_map_stale(unmet: list, criteria: str) -> bool:
    """True when the criteria text declares items 1-3 closed but unmet still calls them open."""
    criteria_closed = "items 1-3" in criteria and "CLOSED" in criteria.upper()
    unmet_open = any("items 1-3" in u and "open" in u.lower() for u in unmet)
    return bool(criteria_closed and unmet_open)


def detect_drift(before: dict, after: dict) -> bool:
    return before != after


# --------------------------------------------------------------------------------------
# check plumbing
# --------------------------------------------------------------------------------------
class Run:
    def __init__(self):
        self.checks: list[dict] = []
        self.controls: list[dict] = []
        self.findings: list[dict] = []

    def check(self, cid, desc, observed, expected, ok, severity="hard"):
        self.checks.append({"id": cid, "description": desc, "observed": observed,
                            "expected": expected, "pass": bool(ok), "severity": severity})
        return bool(ok)

    def control(self, cid, desc, fired):
        self.controls.append({"id": cid, "description": desc, "fired": bool(fired)})
        return bool(fired)

    def finding(self, fid, severity, text, action_needed=None):
        f = {"id": fid, "severity": severity, "text": text}
        if action_needed:
            f["action_needed"] = action_needed
        self.findings.append(f)


def now_cst() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    args = ap.parse_args()

    run = Run()
    measured_before = {rel: sha256_file(ROOT / rel) for rel in PINS if (ROOT / rel).exists()}
    missing = [rel for rel in PINS if rel not in measured_before]

    # ---- Section A: target + pin integrity (fail-closed) ------------------------------
    run.check("A1", "every pinned input exists", {"missing": missing}, [], not missing)
    target = load_json(TARGET) if (ROOT / TARGET).exists() else {}
    run.check("A2", "target schema/class/node/gate",
              {k: target.get(k) for k in ("schema", "class_id", "node_id", "gate")},
              {"schema": "lifecycle09-lead-verify/v1", "class_id": "AF-WCC-SCALAR-SPH",
               "node_id": "N0", "gate": "G-NUM"},
              target.get("schema") == "lifecycle09-lead-verify/v1"
              and target.get("class_id") == "AF-WCC-SCALAR-SPH"
              and target.get("node_id") == "N0" and target.get("gate") == "G-NUM")
    pin_mismatch = {}
    for rel, declared in PINS.items():
        if declared is None or rel not in measured_before:
            continue
        if detect_pin_mismatch(declared, measured_before[rel]):
            pin_mismatch[rel] = {"declared": declared, "measured": measured_before[rel]}
    run.check("A3", "all declared pins match disk", pin_mismatch, {}, not pin_mismatch)
    run.check("A4", "target hash anchored to lead's declared prefix",
              measured_before.get(TARGET, "")[:16], TARGET_PREFIX,
              measured_before.get(TARGET, "").startswith(TARGET_PREFIX))

    # ---- Section B: item 1 — order re-measurement -------------------------------------
    cert = load_json(CERT) if (ROOT / CERT).exists() else {}
    item1 = (target.get("items") or {}).get("item_1_four_rungs") or {}
    schemes = cert.get("schemes", {})
    recompute = {}
    b1_ok = b2_ok = b3_ok = b4_ok = b5_ok = b7_ok = True
    for name, sv in schemes.items():
        f = sv["fixed_dt_certification"]
        rows = f["rows"]
        fit = ols_loglog(rows)
        pair = pair_orders(rows)
        delta = r5_delta(pair, fit["least_squares_se"])
        errors = [r["l2_error"] for r in rows]
        d_order = abs(fit["fit_order"] - f["fit_order"])
        recompute[name] = {
            "n_rungs": fit["n_rungs"], "dr_values": fit["dr_values"],
            "dt_values": fit["dt_values"],
            "recomputed_fit_order": fit["fit_order"],
            "recomputed_se": fit["least_squares_se"],
            "recomputed_pair_orders": pair,
            "recomputed_delta_R5": delta,
            "declared_fit_order": f["fit_order"],
            "declared_se": f["least_squares_se"],
            "declared_pair_orders": f["pair_orders"],
            "declared_delta_R5": f["delta_R5"],
            "abs_diff_order": abs(fit["fit_order"] - f["fit_order"]),
            "abs_diff_se": abs(fit["least_squares_se"] - f["least_squares_se"]),
            "max_abs_diff_pair": max(abs(a - b) for a, b in zip(pair, f["pair_orders"])),
            "abs_diff_delta_R5": abs(delta - f["delta_R5"]),
            "monotone": strictly_decreasing(errors),
            "within_band_0p3": band_ok(fit["fit_order"]),
            "l2_errors_positive": all(e > 0 for e in errors),
        }
        lead_s = (item1.get("schemes") or {}).get(name, {})
        b1_ok &= (fit["n_rungs"] == 4 and fit["dt_values"] == [1e-4]
                  and fit["dr_values"] == [0.2, 0.1, 0.05, 0.025])
        b2_ok &= strictly_decreasing(errors) and all(e > 0 for e in errors)
        b3_ok &= (recompute[name]["abs_diff_order"] <= 1e-12
                  and recompute[name]["abs_diff_se"] <= 1e-12)
        b4_ok &= band_ok(fit["fit_order"])
        b5_ok &= (recompute[name]["max_abs_diff_pair"] <= 1e-12
                  and recompute[name]["abs_diff_delta_R5"] <= 1e-12)
        b7_ok &= (lead_s.get("recomputed_fit_order") == f["fit_order"]
                  and lead_s.get("n_rungs") == 4
                  and lead_s.get("dt_fixed_1e-4") is True
                  and lead_s.get("monotone") is True
                  and lead_s.get("within_band_0p3") is True)
    b7_ok &= (item1.get("closed") is True
              and abs(item1.get("max_abs_diff_vs_declared", 9e9)) <= 1e-12
              and target.get("all_items_closed") is True and target.get("fails") == [])

    orders = {k: v["recomputed_fit_order"] for k, v in recompute.items()}
    deltas = {k: v["recomputed_delta_R5"] for k, v in recompute.items()}
    spread = max(abs(orders[a] - orders[b]) for a, b in itertools.combinations(orders, 2))
    pair_ok_r5 = all(agreement_ok_r5(orders[a], orders[b], deltas[a], deltas[b])
                     for a, b in itertools.combinations(orders, 2))

    run.check("B1", "4 rungs per scheme at fixed dt=1e-4, ratio-2 dr ladder",
              {k: {"n": v["n_rungs"], "dt": v["dt_values"], "dr": v["dr_values"]}
               for k, v in recompute.items()}, "n=4, dt=[1e-4], dr=[.2,.1,.05,.025]", b1_ok)
    run.check("B2", "L2 errors positive and strictly decreasing (monotone)",
              {k: {"monotone": v["monotone"], "positive": v["l2_errors_positive"]}
               for k, v in recompute.items()}, "all true", b2_ok)
    run.check("B3", "independent OLS reproduces declared fit_order and SE (<=1e-12)",
              {k: {"d_order": v["abs_diff_order"], "d_se": v["abs_diff_se"]}
               for k, v in recompute.items()}, "<=1e-12", b3_ok)
    run.check("B4", "|p-2| <= 0.3 for all three schemes",
              {k: abs(v["recomputed_fit_order"] - 2.0) for k, v in recompute.items()},
              "<=0.3", b4_ok)
    run.check("B5", "pair orders and R5 delta = max(half-range, SE) reproduce (<=1e-12)",
              {k: {"d_pair": v["max_abs_diff_pair"], "d_delta": v["abs_diff_delta_R5"]}
               for k, v in recompute.items()}, "<=1e-12", b5_ok)
    run.check("B6", "cross-scheme spread <= 0.25 AND per-pair R5 agreement rule",
              {"spread": spread, "r5_pairs_ok": pair_ok_r5, "bound": 0.25},
              "spread<=0.25 and each pair <= max(0.25,sqrt(da^2+db^2))",
              agreement_ok(spread) and pair_ok_r5)
    run.check("B7", "lead's item_1 fields and closure claims match raw-row recomputation",
              {"lead_orders": {k: (item1.get("schemes") or {}).get(k, {}).get(
                  "recomputed_fit_order") for k in orders},
               "item1_closed": item1.get("closed"),
               "item1_max_abs_diff": item1.get("max_abs_diff_vs_declared")},
              {"lead_orders": orders, "item1_closed": True, "item1_max_abs_diff": 0.0}, b7_ok)

    # ---- Section C: item 2 — F0 re-bind ----------------------------------------------
    taxo_text = (ROOT / TAXO).read_text(errors="replace")
    rev = None
    for line in taxo_text.splitlines():
        if line.startswith("revision:"):
            rev = int(line.split(":", 1)[1].strip().strip('"'))
            break
    item2 = (target.get("items") or {}).get("item_2_f0_rebind") or {}
    class_present = "AF-WCC-SCALAR-SPH" in taxo_text
    c1 = measured_before.get(TAXO) == PINS[TAXO]
    c2 = rev == 5
    c3 = class_present
    c4 = (item2.get("live_sha256") == measured_before.get(TAXO)
          and item2.get("declared_sha256") == PINS[TAXO]
          and item2.get("class_id_present_in_live_taxonomy") is True
          and item2.get("closed") is True
          and item2.get("live_revision") == rev)
    run.check("C1", "live taxonomy hashes to F0 rev5 pin 0abb9ed8a961",
              measured_before.get(TAXO), PINS[TAXO], c1)
    run.check("C2", "live taxonomy revision == 5", rev, 5, c2)
    run.check("C3", "live taxonomy contains class AF-WCC-SCALAR-SPH", class_present, True, c3)
    run.check("C4", "lead's item_2 fields match live bytes", 
              {k: item2.get(k) for k in ("live_sha256", "live_revision",
                                         "class_id_present_in_live_taxonomy")},
              {"live_sha256": measured_before.get(TAXO), "live_revision": rev,
               "class_id_present_in_live_taxonomy": True}, c4)

    # ---- Section D: item 3 — independent replication ----------------------------------
    v46 = load_json(VERDICTS[0])
    v57 = load_json(VERDICTS[1])
    v81 = load_json(VERDICTS[2])
    tokens = {
        "verdict_046": v46.get("verdict"),
        "verdict_057": v57.get("verdict"),
        "binding_accept_081": (v81.get("verdict") or {}).get("binding_accept_at_current_hash"),
        "blocks_gate_pass_081": (v81.get("verdict") or {}).get("blocks_gate_pass"),
    }
    d1 = all(sha256_file(ROOT / p) == PINS[p] for p in VERDICTS)
    d2 = (tokens["verdict_046"] == "SUPPORTED" and tokens["verdict_057"] == "REPRODUCED"
          and tokens["binding_accept_081"] is True and tokens["blocks_gate_pass_081"] is False)
    d3 = sha256_file(ROOT / REV3) == (target.get("items") or {}).get(
        "item_3_independent_replication", {}).get("frozen_run_hash")
    item3 = (target.get("items") or {}).get("item_3_independent_replication") or {}
    d4 = (item3.get("verdict_count") == 3 and item3.get("closed") is True
          and all(v.get("hash_match") is True and v.get("exists") is True
                  for v in item3.get("verdicts", [])))
    run.check("D1", "three replication verdicts hash to declared pins", 
              {p: measured_before[p] for p in VERDICTS},
              {p: PINS[p] for p in VERDICTS}, d1)
    run.check("D2", "verdict tokens SUPPORTED / REPRODUCED / accept, no gate block",
              tokens, {"verdict_046": "SUPPORTED", "verdict_057": "REPRODUCED",
                       "binding_accept_081": True, "blocks_gate_pass_081": False}, d2)
    run.check("D3", "frozen_run_hash equals sha256 of rev3 result",
              sha256_file(ROOT / REV3),
              (target.get("items") or {}).get("item_3_independent_replication", {}).get(
                  "frozen_run_hash"), d3)
    run.check("D4", "lead's item_3 structure (3 verdicts, closed, hash_match)", 
              {"count": item3.get("verdict_count"), "closed": item3.get("closed")},
              {"count": 3, "closed": True}, d4)

    # ---- Section E: lock compliance ---------------------------------------------------
    m = load_json(MAP)
    lock = m.get("numerics_lock", {})
    solver_present = (ROOT / "numerics" / "spherical_solver").exists()
    n1_artifacts = [str(p.relative_to(ROOT)) for p in
                    (ROOT / "numerics").rglob("*spherical*") if p.is_file()]
    lead_lock = (target.get("items") or {}).get("lock_compliance") or {}
    e1 = not solver_present
    e2 = (lock.get("state") == "locked" and "N1" in lock.get("locked_nodes", [])
          and lock.get("allowed_nodes") == ["N0"])
    e3 = (lead_lock.get("numerics_lock_state") == lock.get("state")
          and lead_lock.get("locked_nodes") == lock.get("locked_nodes")
          and lead_lock.get("allowed_nodes") == lock.get("allowed_nodes")
          and lead_lock.get("spherical_solver_present") is False)
    run.check("E1", "numerics/spherical_solver absent", solver_present, False, e1)
    run.check("E2", "live map lock locked, N1 locked, N0 allowed",
              {"state": lock.get("state"), "locked": lock.get("locked_nodes"),
               "allowed": lock.get("allowed_nodes")},
              {"state": "locked", "locked": ["N1"], "allowed": ["N0"]}, e2)
    run.check("E3", "lead's lock_compliance fields match live map", 
              {k: lead_lock.get(k) for k in ("numerics_lock_state", "locked_nodes",
                                             "allowed_nodes", "spherical_solver_present")},
              {"numerics_lock_state": lock.get("state"), "locked_nodes": lock.get("locked_nodes"),
               "allowed_nodes": lock.get("allowed_nodes"), "spherical_solver_present": False}, e3)
    run.finding("W14-L09-R1", "advisory",
                "lead lock_compliance.n1_status='queued' is not a live map field; verifiable "
                "only indirectly (N1 in locked_nodes, no N1 production artifact). Files matching "
                f"*spherical* under numerics/ are the N0 flat-space harness: {n1_artifacts} "
                "(numerics/spherical.py implements flat-space scalar-wave schemes and is imported "
                "by the N0 calibration; it is not a self-gravitating solver), and "
                "numerics/spherical_solver/ remains absent.",
                "Astra may treat 'queued' as inferred; no repair required.")

    # ---- Section F: map-state finding L09-F1 vs live bytes ----------------------------
    gnum = next((g for g in m.get("gates", []) if g.get("gate_id") == "G-NUM"), {})
    unmet = gnum.get("unmet", [])
    criteria = gnum.get("criteria", "")
    lead_map = (target.get("items") or {}).get("map_state") or {}
    lead_snapshot_claim = bool(
        lead_map.get("gnum_stoprule_unmet_text_is_stale") is True
        and any("items 1-3" in u and "open" in u.lower()
                for u in lead_map.get("gnum_unmet", []))
        and lead_map.get("gnum_verdict") == "pending")
    live_contradiction = detect_map_stale(unmet, criteria)
    live_unmet_items_open = any("items 1-3" in u and "open" in u.lower() for u in unmet)
    f1 = gnum.get("verdict") == "pending"
    f2 = lead_snapshot_claim
    f3 = not live_contradiction
    f4 = not live_unmet_items_open
    run.check("F1", "live G-NUM verdict is pending", gnum.get("verdict"), "pending", f1)
    run.check("F2", "lead's recorded 01:16:26 snapshot internally asserts the stale "
                    "items-1-3-open text (L09-F1 valid for those bytes)",
              {"is_stale": lead_map.get("gnum_stoprule_unmet_text_is_stale"),
               "map_updated_at": lead_map.get("map_updated_at")},
              {"is_stale": True, "map_updated_at": "2026-09-12T01:16:26+08:00"},
              f2)
    run.check("F3", "live map carries no criteria(closed)-vs-unmet(open) contradiction "
                    "(L09-F1 superseded at live bytes)",
              {"criteria_closed": ("items 1-3" in criteria and "CLOSED" in criteria.upper()),
               "live_contradiction": live_contradiction}, "contradiction=False", f3,
              severity="finding")
    run.check("F4", "live G-NUM unmet no longer claims items 1-3 open",
              [u for u in unmet if "items 1-3" in u], [], f4, severity="finding")
    run.check("F5", "live map hash recorded for drift guard", measured_before.get(MAP, "")[:16],
              "recorded", bool(measured_before.get(MAP)))

    # ---- Section G: controls (detectors must fire on synthetic inputs) ----------------
    synth_rows = [{"dr": h, "dt": 1e-4, "l2_error": h ** 2} for h in (0.2, 0.1, 0.05, 0.025)]
    fit = ols_loglog(synth_rows)
    run.control("G1", "known-answer LSQ recovers exact p=2",
                abs(fit["fit_order"] - 2.0) < 1e-12)
    rows15 = [{"dr": h, "dt": 1e-4, "l2_error": h ** 1.5} for h in (0.2, 0.1, 0.05, 0.025)]
    run.control("G2", "known-answer LSQ recovers p=1.5",
                abs(ols_loglog(rows15)["fit_order"] - 1.5) < 1e-12)
    bad = [r["l2_error"] for r in synth_rows]
    bad[2] = bad[1] * 1.5
    run.control("G3", "monotonicity detector fires on non-monotone ladder",
                detect_not_monotone(bad))
    run.control("G4", "band detector fires on p=1.6 ladder",
                detect_band_violation(ols_loglog(rows15)["fit_order"]))
    run.control("G5", "spread detector fires on synthetic 0.30 spread",
                detect_spread_violation(0.30))
    run.control("G6", "pin detector fires on mutated hash",
                detect_pin_mismatch(PINS[CERT], "0" * 64))
    run.control("G7", "token detector fires on mutated verdict token",
                detect_token_mismatch("REVISED", "REPRODUCED"))
    run.control("G8", "class detector fires when class id absent from taxonomy text",
                detect_class_absent("schema_version: '0.1'\n", "AF-WCC-SCALAR-SPH"))
    run.control("G9", "lock detector fires on solver presence",
                detect_lock_violation(True, "locked", ["N1"]))
    run.control("G10", "stale-map detector fires on inconsistent synthetic map",
                detect_map_stale(["Stop-rule items 1-3 above are open"],
                                 "items 1-3 are CLOSED"))
    run.control("G11", "stale-map detector stays silent on consistent synthetic map",
                not detect_map_stale(["items 1-3 closed"], "items 1-3 are CLOSED"))
    run.control("G12", "drift guard fires on changed byte map",
                detect_drift({"a": "1"}, {"a": "2"}))

    # ---- after-hash drift guard --------------------------------------------------------
    measured_after = {rel: sha256_file(ROOT / rel) for rel in PINS if (ROOT / rel).exists()}
    drift = {rel: {"before": measured_before.get(rel), "after": measured_after.get(rel)}
             for rel in PINS if measured_before.get(rel) != measured_after.get(rel)}
    run.check("H1", "no pinned input drifted during the run", drift, {}, not drift)

    # ---- verdict ----------------------------------------------------------------------
    controls_fired = sum(1 for c in run.controls if c["fired"])
    hard_fail = [c["id"] for c in run.checks if not c["pass"] and c["severity"] == "hard"]
    if pin_mismatch or missing:
        verdict = "L09_CROSSVERIFY_INCONCLUSIVE_INPUT_DRIFT"
    elif controls_fired != len(run.controls):
        verdict = "L09_CROSSVERIFY_REVISE_CONTROL_FAILURE"
    elif hard_fail:
        verdict = "L09_CROSSVERIFY_REVISE_" + "_".join(hard_fail)
    elif live_unmet_items_open:
        verdict = "LIFECYCLE09_LEAD_VERIFY_CROSSVERIFIED_ACCEPT_MAP_UNMET_STALE_CONFIRMED"
    else:
        verdict = "LIFECYCLE09_LEAD_VERIFY_CROSSVERIFIED_ACCEPT_MAP_UNMET_REFRESHED"

    if lead_snapshot_claim and live_unmet_items_open:
        run.finding("W14-L09-F1", "medium",
                    "L09-F1 is confirmed live: G-NUM unmet[1] still claims stop-rule items 1-3 "
                    "open after the lifecycle-09 re-measurement closed them. Astra should refresh "
                    "the unmet text.",
                    "Astra refreshes G-NUM unmet; remaining N0 blocker is the lead-audit-owned "
                    "accept (astra-life04-n0-verify).")
    elif lead_snapshot_claim:
        run.finding("W14-L09-F1", "info",
                    "L09-F1 was valid at the record's own snapshot (map_updated_at 01:16:26: "
                    "unmet[1] claimed items 1-3 open) and is superseded at the live bytes: the "
                    "controller refresh at 01:22:04 rewrote G-NUM criteria/unmet into a "
                    "consistent state (unmet now names only the two remaining lead-owned "
                    "stop-rule assignments). No repair owed for L09-F1.",
                    "None; recorded for provenance.")

    report = {
        "schema": "w014-lifecycle09-crossverify/v1",
        "task_id": "W014-GNUM-N0-L09-CROSSVERIFY-01",
        "actor": "worker-014",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "N0",
        "gate": "G-NUM",
        "generated_at": now_cst(),
        "verdict": verdict,
        "verdict_scope": ("worker-level independent read-only cross-verification at the pinned "
                          "hashes; not a G-NUM gate verdict, not an N0 node verdict "
                          "(authority: Astra / lead-audit)"),
        "counts": {"checks": len(run.checks),
                   "checks_passed": sum(1 for c in run.checks if c["pass"]),
                   "checks_failed": sum(1 for c in run.checks if not c["pass"]),
                   "hard_failures": hard_fail,
                   "controls_total": len(run.controls), "controls_fired": controls_fired},
        "target": {"path": TARGET, "sha256": measured_before.get(TARGET)},
        "pins": {rel: {"declared": PINS[rel], "measured": measured_before.get(rel),
                       "stable": measured_before.get(rel) == measured_after.get(rel)}
                 for rel in PINS},
        "recompute": recompute,
        "cross_scheme": {"spread": spread, "bound_floor": 0.25,
                         "r5_pair_rule_ok": pair_ok_r5,
                         "max_pairwise_abs_diff_cert": cert.get("cross_scheme_R5", {}).get(
                             "max_pairwise_abs_diff")},
        "map_state": {"map_sha256": measured_before.get(MAP),
                      "gnum_verdict": gnum.get("verdict"),
                      "live_criteria": criteria,
                      "live_unmet": unmet,
                      "live_contradiction": live_contradiction,
                      "live_unmet_claims_items_1_3_open": live_unmet_items_open,
                      "lead_snapshot_stale_claim": lead_snapshot_claim,
                      "lead_snapshot_map_updated_at": lead_map.get("map_updated_at"),
                      "lead_snapshot_unmet": lead_map.get("gnum_unmet")},
        "checks": run.checks,
        "controls": run.controls,
        "findings": run.findings,
        "falsifier": ("Re-run this script at the pinned inputs. Falsified if any declared pin "
                      "moves, any recomputed fit leaves |p-2|>0.3, a ladder is non-monotone, "
                      "cross-scheme spread >0.25 or the per-pair R5 rule fails, a cited verdict "
                      "loses its token, live taxonomy != 0abb9ed8a961 or lacks "
                      "AF-WCC-SCALAR-SPH, numerics_lock != locked or numerics/spherical_solver "
                      "appears, the record's map-snapshot claim or the live G-NUM criteria/unmet "
                      "state is not as reported, any control fails to fire, or any pinned input "
                      "drifts pre/post."),
        "not_claimed": [
            "not a G-NUM gate verdict; gate authority stays Astra / lead-audit",
            "not an N0 node completion or status transition",
            "no numerics_lock release; N1 stays queued",
            "no adjudication of the contested protocol review (reviews/G-NUM-protocol-review.json)",
            "no canonical-path write; read-only over every pinned input",
            "no physics / self-gravity / WCC / SCC claim",
        ],
        "instrument_sha256": sha256_file(Path(__file__).resolve()),
    }
    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).with_name(args.out)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"verdict={verdict}")
    print(f"checks={report['counts']['checks_passed']}/{report['counts']['checks']} "
          f"controls={controls_fired}/{len(run.controls)} hard_failures={hard_fail} "
          f"spread={spread:.3e}")
    print(f"report={out}")
    return 0 if (not hard_fail and controls_fired == len(run.controls)
                 and not pin_mismatch and not missing) else 1


if __name__ == "__main__":
    sys.exit(main())
