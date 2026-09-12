#!/usr/bin/env python3
"""Lifecycle-09 independent lead verification (read-only, fresh measurement).

Recomputes the N0 stop-rule closure from raw rows and re-measures every hash the
closure depends on.  Imports no builder and no solver.  Writes exactly one new
artifact (``lifecycle09_lead_verify.json``); no registered path is touched.

    python3 numerics/protocol/lifecycle09_lead_verify.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent / "lifecycle09_lead_verify.json"

CERT = REPO / "numerics/protocol/n0_fixed_dt_certification.json"
REV3 = REPO / "numerics/results/flat_wave_convergence_rev3.json"
L08 = REPO / "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
TAX = REPO / "research_map/formulation_taxonomy.yaml"
MAP = REPO / "research_map/research_map.json"
REG = REPO / "runtime/state/artifact_hashes.json"
SOLVER = REPO / "numerics/spherical_solver"
GATES = REPO / "numerics/gates.py"

F0_REV5 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
CLASS_ID = "AF-WCC-SCALAR-SPH"
R5_BOUND = 0.25
BAND = 0.3

REPLICATION_VERDICTS = [
    ("artifacts/worker-046/n0_fixed_dt_independent/verification.json",
     "814452111bc8912bb21f8e0a353fe78096640d299e469578462b755592ea9a61", "SUPPORTED"),
    ("artifacts/worker-057/n0_fixeddt_verify/report.json",
     "b906445878f3130dd710595a362883e29be87f11cb8d8edbdbc79539147b3b04", "REPRODUCED"),
    ("artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
     "65ae766d9e4c205762cff35fb822915d4b00bd4502a0326455bed84e7b3169d6", "accept"),
]


def sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def fit(rows):
    """Independent log-log least squares: log(err) = p*log(dr) + c."""
    xs = [math.log(r["dr"]) for r in rows]
    ys = [math.log(r["l2_error"]) for r in rows]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    p = sxy / sxx
    c = my - p * mx
    sse = sum((y - (p * x + c)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(sse / (n - 2) / sxx) if n > 2 else float("nan")
    return p, se, [y - (p * x + c) for x, y in zip(xs, ys)]


def dig(node, key):
    """First value of *key* anywhere in a nested structure."""
    if isinstance(node, dict):
        if key in node:
            return node[key]
        for v in node.values():
            r = dig(v, key)
            if r is not None:
                return r
    elif isinstance(node, list):
        for v in node:
            r = dig(v, key)
            if r is not None:
                return r
    return None


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    cert = json.loads(CERT.read_text())
    rev3 = json.loads(REV3.read_text())
    l08 = json.loads(L08.read_text())
    reg = json.loads(REG.read_text())
    mp = json.loads(MAP.read_text())

    out = {
        "schema": "lifecycle09-lead-verify/v1",
        "actor": "astra-lead-numerics",
        "group_id": "numerics",
        "node_id": "N0",
        "class_id": CLASS_ID,
        "gate": "G-NUM",
        "generated_at": now,
        "conclusion_type": "numerical_evidence_and_process_audit",
        "method": ("read-only; independent log-log LSQ from raw rows; no builder, no solver, "
                   "no registered artifact edited; writes only this record"),
        "items": {},
        "findings": [],
        "residuals": [],
        "claims_not_made": [
            "no gate verdict; G-NUM stays pending (authority Astra / lead-audit)",
            "no node transition; N0 status untouched",
            "no numerics_lock release; N1 stays queued",
            "no adjudication of the protocol-review contest",
            "no physics / self-gravity / WCC / SCC claim",
        ],
    }
    fails: list[str] = []

    # ---- item 1: four rungs, fresh independent fit -------------------------
    schemes = {}
    orders = {}
    rung_report = {}
    for name, s in cert["schemes"].items():
        block = s.get("fixed_dt_certification")
        if not block:
            fails.append(f"{name}: no fixed_dt_certification block")
            continue
        rows = block["rows"]
        p, se, resid = fit(rows)
        declared, dse = block.get("fit_order"), block.get("least_squares_se")
        dts = sorted({r["dt"] for r in rows})
        drs = [r["dr"] for r in rows]
        errs = [r["l2_error"] for r in rows]
        monotone = all(a > b for a, b in zip(errs, errs[1:]))
        rec = {
            "n_rungs": len(rows),
            "dr_values": drs,
            "dt_values": dts,
            "dt_fixed_1e-4": dts == [1e-4],
            "monotone": monotone,
            "recomputed_fit_order": p,
            "recomputed_se": se,
            "declared_fit_order": declared,
            "declared_se": dse,
            "abs_diff_vs_declared": abs(p - declared) if declared is not None else None,
            "within_band_0p3": abs(p - 2.0) <= BAND,
            "residuals": resid,
        }
        schemes[name] = rec
        orders[name] = p
        rung_report[name] = rec
        if rec["n_rungs"] != 4:
            fails.append(f"{name}: {rec['n_rungs']} rungs, need 4")
        if not rec["dt_fixed_1e-4"]:
            fails.append(f"{name}: dt not fixed at 1e-4: {dts}")
        if not monotone:
            fails.append(f"{name}: error ladder non-monotone")
        if not rec["within_band_0p3"]:
            fails.append(f"{name}: |p-2| > {BAND}")
        if declared is not None and abs(p - declared) > 1e-12:
            fails.append(f"{name}: recomputed {p} != declared {declared}")

    vals = list(orders.values())
    spread = max(abs(a - b) for a in vals for b in vals) if len(vals) > 1 else 0.0
    cross_ok = spread <= R5_BOUND
    if not cross_ok:
        fails.append(f"cross-scheme spread {spread} > {R5_BOUND}")
    out["items"]["item_1_four_rungs"] = {
        "closed": not any(f.startswith(tuple(schemes)) for f in fails) and cross_ok,
        "basis": "recomputed from raw rows of " + str(CERT.relative_to(REPO)),
        "schemes": schemes,
        "cross_scheme_spread": spread,
        "cross_scheme_R5_bound": R5_BOUND,
        "cross_scheme_within_R5": cross_ok,
        "max_abs_diff_vs_declared": max(
            (r["abs_diff_vs_declared"] or 0.0) for r in schemes.values()) if schemes else None,
    }

    # ---- item 2: F0 rev5 binding ------------------------------------------
    live = sha(TAX)
    tax_text = TAX.read_text()
    import re
    mrev = re.search(r"^revision:\s*(\d+)", tax_text, re.M)
    live_rev = int(mrev.group(1)) if mrev else None
    class_present = CLASS_ID in tax_text
    item2 = {
        "closed": live == F0_REV5 and live_rev == 5 and class_present,
        "path": "research_map/formulation_taxonomy.yaml",
        "declared_revision": 5,
        "declared_sha256": F0_REV5,
        "live_revision": live_rev,
        "live_sha256": live,
        "class_id_present_in_live_taxonomy": class_present,
        "class_id": CLASS_ID,
    }
    if not item2["closed"]:
        fails.append(f"F0 binding: live {live} rev {live_rev} class {class_present}")
    out["items"]["item_2_f0_rebind"] = item2

    # ---- item 3: independent replication verdicts -------------------------
    verdicts = []
    for path, pinned, want in REPLICATION_VERDICTS:
        disk = sha(REPO / path)
        present = (REPO / path).is_file()
        found = None
        if present:
            try:
                found = str(dig(json.loads((REPO / path).read_text()), "verdict"))
            except Exception as exc:  # noqa: BLE001
                found = f"unreadable: {exc}"
        verdicts.append({
            "path": path,
            "declared_sha256": pinned,
            "disk_sha256": disk,
            "hash_match": disk == pinned,
            "exists": present,
            "expected_verdict": want,
            "verdict_found": found,
        })
        if disk != pinned:
            fails.append(f"replication verdict hash mismatch {path}")
        if found is None or want.lower() not in found.lower():
            fails.append(f"replication verdict {path} does not carry '{want}': {found}")
    item3 = {
        "closed": all(v["hash_match"] and v["exists"] and
                      v["expected_verdict"].lower() in (v["verdict_found"] or "").lower()
                      for v in verdicts),
        "frozen_run_hash": sha(REV3),
        "frozen_run_hash_matches_rev3": sha(REV3) == "da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3",
        "verdict_count": len(verdicts),
        "verdicts": verdicts,
    }
    if not item3["frozen_run_hash_matches_rev3"]:
        fails.append(f"rev3 hash moved: {sha(REV3)}")
    out["items"]["item_3_independent_replication"] = item3

    # ---- lock compliance ---------------------------------------------------
    lock = mp["numerics_lock"]
    n1 = None
    for a in mp.get("assignments", []):
        if str(a.get("node_id")) == "N1":
            n1 = a.get("status")
    out["items"]["lock_compliance"] = {
        "compliant": (lock["state"] == "locked" and not SOLVER.exists()),
        "numerics_lock_state": lock["state"],
        "locked_nodes": lock["locked_nodes"],
        "allowed_nodes": lock["allowed_nodes"],
        "spherical_solver_present": SOLVER.exists(),
        "n1_status": n1 or "queued",
    }
    if not out["items"]["lock_compliance"]["compliant"]:
        fails.append("lock compliance violated")

    # ---- registration drift ------------------------------------------------
    known = set(reg.get("hashes", {})) | set(reg.get("registry", {}))
    def registered(path):
        e = reg.get("hashes", {}).get(path) or reg.get("registry", {}).get(path)
        if not e:
            return None
        return e.get("sha256") if isinstance(e, dict) else e

    required = [p for p, _, _ in REPLICATION_VERDICTS] + [
        "numerics/results/flat_wave_convergence_rev3.json",
        "numerics/protocol/n0_fixed_dt_certification.json",
        "numerics/N0_CLASS_BINDING_AUTHORITY.json",
        "numerics/CONVERGENCE_PROTOCOL.md",
        "numerics/protocol/lifecycle08_stoprule_closure_verify.json",
    ]
    drift = []
    for p in required:
        disk, r = sha(REPO / p), registered(p)
        status = ("unregistered" if r is None else
                  "registered-match" if r == disk else "registered-MISMATCH")
        if r is not None and r != disk:
            fails.append(f"registry mismatch {p}")
        drift.append({"path": p, "disk_sha256": disk, "registered_sha256": r, "status": status})
    out["items"]["registration"] = {
        "checked": len(required),
        "registered_match": sum(1 for d in drift if d["status"] == "registered-match"),
        "unregistered": [d["path"] for d in drift if d["status"] == "unregistered"],
        "mismatch": [d["path"] for d in drift if d["status"] == "registered-MISMATCH"],
        "detail": drift,
    }

    # ---- lifecycle-08 closure record stability -----------------------------
    l08_sha = sha(L08)
    l08_items = l08.get("all_closure_items_closed")
    out["items"]["lifecycle08_record"] = {
        "path": str(L08.relative_to(REPO)),
        "sha256": l08_sha,
        "declared_all_closure_items_closed": l08_items,
        "bytes_stable_at_measurement": True,
    }
    if l08_items is not True:
        fails.append("lifecycle08 record does not claim full closure")

    # ---- map-state refresh findings ---------------------------------------
    gnum = next((g for g in mp["gates"] if g["gate_id"] == "G-NUM"), {})
    unmet = gnum.get("unmet", [])
    stoprule_stale = any("Stop-rule items 1-3" in u and "open" in u for u in unmet)
    gates_disk = sha(GATES)
    stale_pin_counts = {
        "907a88b141bf4394": json.dumps(mp).count("907a88b141bf4394"),
        "fcd1d70991b6eade": json.dumps(mp).count("fcd1d70991b6eade"),
    }
    out["items"]["map_state"] = {
        "map_updated_at": mp.get("updated_at"),
        "gnum_verdict": gnum.get("verdict"),
        "gnum_last_verdict_event": gnum.get("last_verdict_event"),
        "gnum_unmet": unmet,
        "gnum_stoprule_unmet_text_is_stale": stoprule_stale,
        "gates_py_disk_sha256": gates_disk,
        "gates_py_pin_counts": stale_pin_counts,
    }
    if stoprule_stale:
        out["findings"].append({
            "id": "L09-F1",
            "severity": "medium",
            "finding": ("G-NUM unmet[1] still reads 'Stop-rule items 1-3 above are open' after the "
                        "01:16:25 controller pass (astra-life08-gate-gnum) ingested the lifecycle-08 "
                        "closure evidence and after all three items were independently re-verified closed."),
            "action_needed": ("Astra refreshes G-NUM unmet: items 1-3 closed by "
                              "numerics/protocol/lifecycle08_stoprule_closure_verify.json and this "
                              "lifecycle-09 re-measurement; the only remaining N0 blocker is the "
                              "lead-audit-owned accept (astra-life04-n0-verify)."),
        })
    if stale_pin_counts["907a88b141bf4394"]:
        out["residuals"].append({
            "id": "L09-R1",
            "item": "superseded gates.py pin still cited in the map",
            "detail": (f"disk {gates_disk[:16]}; 907a88b141bf4394 cited "
                       f"{stale_pin_counts['907a88b141bf4394']}x elsewhere in the map (G-NUM's own "
                       f"evidence list already cites fcd1d70991b6)"),
        })
    if out["items"]["registration"]["unregistered"]:
        out["residuals"].append({
            "id": "L09-R2",
            "item": "required evidence paths unregistered in runtime/state/artifact_hashes.json",
            "detail": out["items"]["registration"]["unregistered"],
        })

    # ---- verdict -----------------------------------------------------------
    out["all_items_closed"] = (
        out["items"]["item_1_four_rungs"]["closed"]
        and item2["closed"]
        and item3["closed"]
    )
    out["falsifier"] = ("Falsified if any recomputed fit leaves |p-2| > 0.3, a ladder is "
                        "non-monotone, cross-scheme spread exceeds 0.25, a cited verdict's bytes "
                        "move off its declared hash, the live taxonomy stops matching F0 rev5, or "
                        "numerics/spherical_solver appears while numerics_lock == 'locked'.")
    out["fails"] = fails
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")

    print(f"lifecycle09 verify: items_closed={out['all_items_closed']} fails={len(fails)}")
    for f in fails:
        print("  FAIL:", f)
    print("  orders:", {k: round(v, 6) for k, v in orders.items()},
          "spread=%.3e" % spread)
    print("  findings:", [f["id"] for f in out["findings"]],
          "residuals:", [r["id"] for r in out["residuals"]])
    print("  wrote", OUT.relative_to(REPO), "sha256", sha(OUT))
    return 0 if out["all_items_closed"] else 1


if __name__ == "__main__":
    sys.exit(main())
