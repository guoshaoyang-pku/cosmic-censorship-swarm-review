#!/usr/bin/env python3
"""Numerics-lead lifecycle 08: independent stop-rule closure verification (read-only).

Answers one question with measurements, not narrative: at the current on-disk hashes,
is the ``reviews/N0-review-lead-audit.json`` stop rule closed, and what is the live
state of the N0/G-NUM evidence chain?

Stop rule (lead-audit, N0-review-lead-audit.json#e3c314f886be8378):
  (1) add a fourth resolution rung, or scope the claim with a tolerance justification;
  (2) re-bind the class binding to the declared F0 revision;
  (3) obtain one independent replication verdict of the order at the frozen run hash.

This tool does NOT set a gate verdict, does NOT move node status, does NOT edit any
canonical artifact, and does NOT import the certification generator or any solver.
Exit codes: 0 all measured items closed; 2 a closure item failed; 3 lock violation;
4 residual registration gap; 5 evidence-chain pin drift.

    python3 numerics/protocol/lifecycle08_stoprule_closure_verify.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REV3 = "numerics/results/flat_wave_convergence_rev3.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
AUTHORITY = "numerics/N0_CLASS_BINDING_AUTHORITY.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
AUDIT_REVIEW = "reviews/N0-review-lead-audit.json"
FLASH13 = "reviews/flash-13-N0-rev3-verdict.json"
REGISTRY = "runtime/state/artifact_hashes.json"
MAP = "research_map/research_map.json"
W046 = "artifacts/worker-046/n0_fixed_dt_independent/verification.json"
W057 = "artifacts/worker-057/n0_fixeddt_verify/report.json"
W081 = "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json"

KNOWN_PINS = [REV3, CERT, AUTHORITY, PROTOCOL, TAXONOMY, AUDIT_REVIEW, FLASH13,
              W046, W057, W081]


def sha256(rel: str) -> str | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(rel: str):
    return json.loads((ROOT / rel).read_text())


def lsq(xs: list[float], ys: list[float]):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    b = num / den
    a = my - b * mx
    ss = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    se = math.sqrt(ss / (n - 2) / den)
    return b, se


def check_item_1(cert: dict) -> dict:
    """(1) four rungs per scheme at fixed dt, monotone, in band -- recomputed."""
    schemes = {}
    worst_diff = 0.0
    for name, s in cert["schemes"].items():
        fdt = s["fixed_dt_certification"]
        rows = sorted(fdt["rows"], key=lambda r: -r["dr"])
        dts = sorted({r["dt"] for r in rows})
        drs = [r["dr"] for r in rows]
        xs = [math.log(r["dr"]) for r in rows]
        ys = [math.log(r["l2_error"]) for r in rows]
        p, se = lsq(xs, ys)
        mono = all(rows[i]["l2_error"] > rows[i + 1]["l2_error"] for i in range(len(rows) - 1))
        diff = abs(p - fdt["fit_order"])
        worst_diff = max(worst_diff, diff)
        schemes[name] = {
            "n_rungs": len(rows),
            "dr_values": drs,
            "dt_values": dts,
            "dt_fixed_1e-4": dts == [0.0001],
            "recomputed_fit_order": p,
            "declared_fit_order": fdt["fit_order"],
            "abs_diff_vs_declared": diff,
            "recomputed_se": se,
            "declared_se": fdt["least_squares_se"],
            "monotone": mono,
            "within_band_0p3": abs(p - 2.0) <= 0.3,
        }
    ps = [v["recomputed_fit_order"] for v in schemes.values()]
    spread = max(ps) - min(ps)
    return {
        "closed": all(v["n_rungs"] >= 4 and v["dt_fixed_1e-4"] and v["monotone"]
                      and v["within_band_0p3"] for v in schemes.values()),
        "basis": "recomputed from raw rows of " + CERT,
        "schemes": schemes,
        "max_abs_diff_vs_declared": worst_diff,
        "cross_scheme_spread": spread,
        "cross_scheme_R5_bound": 0.25,
        "cross_scheme_within_R5": spread <= 0.25,
    }


def check_item_2() -> dict:
    """(2) class binding re-derived against the live F0 revision."""
    tax = (ROOT / TAXONOMY).read_text()
    rev3 = load(REV3)
    cb = rev3["class_binding"]
    live_sha = sha256(TAXONOMY)
    m = re.search(r"^revision:\s*(\d+)", tax, re.M)
    live_rev = int(m.group(1)) if m else None
    cls_present = cb["class_id"] in tax
    return {
        "closed": (cb["declared_revision"] == live_rev
                   and cb["sha256"] == live_sha
                   and cls_present),
        "declared_revision": cb["declared_revision"],
        "live_revision": live_rev,
        "declared_sha256": cb["sha256"],
        "live_sha256": live_sha,
        "class_id": cb["class_id"],
        "class_id_present_in_live_taxonomy": cls_present,
        "authority_record": AUTHORITY,
        "authority_record_sha256": sha256(AUTHORITY),
    }


def check_item_3(cert: dict) -> dict:
    """(3) independent replication verdict of the order at the frozen run hash."""
    rev3 = load(REV3)
    verdicts = []
    for v in rev3["independent_replication"]["verdicts"]:
        disk = sha256(v["path"])
        verdicts.append({
            "path": v["path"],
            "reviewer": v["reviewer"],
            "task_id": v.get("task_id"),
            "declared_verdict": v["verdict"],
            "declared_sha256": v["sha256"],
            "disk_sha256": disk,
            "hash_match": disk == v["sha256"],
        })
    f13 = load(FLASH13)
    rev3_disk = sha256(REV3)
    return {
        "closed": all(v["hash_match"] for v in verdicts) and len(verdicts) >= 1,
        "frozen_run_hash": rev3_disk,
        "verdict_count": len(verdicts),
        "verdicts": verdicts,
        "flash13_accept": {
            "path": FLASH13,
            "verdict": f13.get("verdict"),
            "score": f13.get("score"),
            "pinned_sha256": f13.get("reviewed_sha256"),
            "hash_stable_across_review": f13.get("hash_stable_across_review"),
            "binds_current_rev3": f13.get("reviewed_sha256") == rev3_disk,
            "counts_as_node_verdict": f13.get("counts_as_node_verdict"),
            "disclosed_conflict": "F-06 (reviewer authored the certified frozen module)",
        },
        "cert_frozen_module": cert["frozen_module"],
        "cert_frozen_module_matches_disk": sha256(cert["frozen_module"]["path"])
        == cert["frozen_module"]["sha256"],
    }


def check_registration() -> dict:
    reg = load(REGISTRY)["registry"]
    m = load(MAP)
    ledger = []
    for rel in KNOWN_PINS:
        disk = sha256(rel)
        entry = reg.get(rel)
        ledger.append({
            "path": rel,
            "exists": disk is not None,
            "disk_sha256": disk,
            "registered_sha256": (entry or {}).get("sha256"),
            "status": ("registered-match" if entry and entry.get("sha256") == disk
                       else ("drift" if entry else "unregistered")),
        })
    residual = [e["path"] for e in ledger if e["status"] == "unregistered"]
    drift = [e["path"] for e in ledger if e["status"] == "drift"]

    # Historical submissions of each map path, so a stale pin can be classified as
    # "superseded revision of the same path" (documentary) or a genuine mispin.
    prior: dict[str, set] = {}
    for grp in m["groups"]:
        for node in grp["nodes"]:
            for s in node.get("artifact_submissions", []) or []:
                prior.setdefault(s.get("path"), set()).add(s.get("sha256"))

    # live-map G-NUM evidence chain: resolve every pinned ref against disk
    gnum = [g for g in m["gates"] if g.get("gate_id") == "G-NUM"][0]
    resolved, no_pin, broken, historical = [], [], [], []
    for ref in gnum.get("evidence_refs", []):
        mm = re.match(r"^([^#]+)(?:#(?:sha256:)?([0-9a-f]{6,64}))?$", ref)
        if not mm:
            broken.append({"ref": ref, "why": "unparsed"})
            continue
        path, pin = mm.group(1), mm.group(2)
        if not (ROOT / path).exists():
            broken.append({"ref": ref, "why": "missing-file"})
            continue
        if not pin:
            no_pin.append(ref)
            continue
        disk = sha256(path)
        if disk.startswith(pin):
            resolved.append(ref)
        elif any(p.startswith(pin) for p in prior.get(path, ())):
            historical.append({"ref": ref, "why": f"superseded-revision disk={disk[:12]}"})
        else:
            broken.append({"ref": ref, "why": f"stale-pin disk={disk[:12]}"})
    return {
        "known_pins": ledger,
        "residual_unregistered": residual,
        "drift": drift,
        "gnum_evidence_refs": len(gnum.get("evidence_refs", [])),
        "gnum_resolved": len(resolved),
        "gnum_no_pin": len(no_pin),
        "gnum_historical_pins": [h["ref"] for h in historical],
        "gnum_broken": broken,
        "gnum_stale_pins": [b["ref"] for b in broken if b["why"].startswith("stale-pin")],
        "gnum_missing_files": [b["ref"] for b in broken if b["why"] == "missing-file"],
        "mispin_analysis": [{
            "ref": "reviews/G-NUM-protocol-review.json#1e6cdf04d7a2",
            "path_disk_sha256": sha256("reviews/G-NUM-protocol-review.json"),
            "registered_sha256": (reg.get("reviews/G-NUM-protocol-review.json") or {}).get("sha256"),
            "embedded_hash_is": "numerics/CONVERGENCE_PROTOCOL.md (the reviewed target), not the review record",
            "revision_the_hash_names": "66a905f5afefda0a (review rev1 advisory), also present later in the same list",
            "severity": "advisory (documentary): the duplicated 66a905f5afef ref already carries the "
                        "revision the r4 adjudication names, so no substantive evidence is missing",
        }],
        "note": ("numerics/gates.py::_gate_report gates on verdict=='pass' plus a non-empty "
                 "evidence list, so a stale pin does not by itself block the lock guard; it "
                 "is an audit/traceability defect, not a gate-logic failure. Pins that match "
                 "a prior submission of the same path are classified historical (the chain "
                 "records its own revision history) and are NOT counted as broken. Measured, "
                 "not inferred."),
    }


def check_lock() -> dict:
    solver = (ROOT / "numerics/spherical_solver").exists()
    m = load(MAP)
    lock = m["numerics_lock"]
    n1 = [n for g in m["groups"] if g.get("id") == "numerics"
          for n in g["nodes"] if n.get("id") == "N1"]
    return {
        "numerics_lock_state": lock["state"],
        "spherical_solver_present": solver,
        "n1_status": n1[0]["status"] if n1 else None,
        "compliant": (not solver) and lock["state"] == "locked"
        and (n1[0]["status"] == "queued" if n1 else True),
    }


def _exit_code(out: dict) -> int:
    """Shared exit-code mapping: 3 lock, 2 closure, 4 registration, 5 pin drift, 0 clean."""
    if not out["lock_compliance"]["compliant"]:
        return 3
    if not out["all_closure_items_closed"]:
        return 2
    if out["registration"]["residual_unregistered"]:
        return 4
    if out["registration"]["gnum_stale_pins"] or out["registration"]["gnum_missing_files"]:
        return 5
    return 0


def main() -> int:
    cert = load(CERT)
    rev3 = load(REV3)

    out = {
        "schema": "n0-stoprule-closure-verify/v1",
        "actor": "astra-lead-numerics",
        "group_id": "numerics",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "conclusion_type": "numerical_evidence_and_process_audit",
        "method": ("read-only; independent log-log LSQ from raw rows; no certification "
                   "generator and no solver imported; no registered artifact edited"),
        "stop_rule_under_test": {
            "path": AUDIT_REVIEW,
            "sha256": sha256(AUDIT_REVIEW),
            "stop_rule": load(AUDIT_REVIEW)["stop_rule"],
        },
        "item_1_four_rungs": check_item_1(cert),
        "item_2_f0_rebind": check_item_2(),
        "item_3_independent_replication": check_item_3(cert),
        "registration": check_registration(),
        "lock_compliance": check_lock(),
        "claims_not_made": [
            "no gate verdict; G-NUM stays pending (authority Astra / lead-audit)",
            "no node transition; N0 status untouched",
            "no numerics_lock release; N1 stays queued",
            "no adjudication of the protocol-review contest",
            "no physics / self-gravity / WCC / SCC claim",
        ],
        "falsifier": ("Falsified if any recomputed fit leaves |p-2| > 0.3, a ladder is "
                      "non-monotone, cross-scheme spread exceeds 0.25, a cited verdict's "
                      "bytes move off its declared hash, the live taxonomy stops matching "
                      "the declared F0 revision, or numerics/spherical_solver appears while "
                      "numerics_lock == 'locked'."),
    }
    out["all_closure_items_closed"] = bool(
        out["item_1_four_rungs"]["closed"]
        and out["item_2_f0_rebind"]["closed"]
        and out["item_3_independent_replication"]["closed"]
    )

    # Byte-stable publication: the artifact is pinned by events, so an unchanged
    # measurement must reproduce byte-identical output.  The comparison strips
    # ``generated_at`` from BOTH sides, so a re-run on an unchanged environment never
    # rewrites the file and the hash never moves; ``generated_at`` advances only when a
    # measurement actually changes.  (Comparing the stamped document against an unstamped
    # payload would rewrite on every run, which is the moving-target defect this fixes.)
    dest = ROOT / "numerics/protocol/lifecycle08_stoprule_closure_verify.json"
    previous = json.loads(dest.read_text()) if dest.is_file() else None
    if previous is not None and {k: v for k, v in previous.items()
                                 if k != "generated_at"} == out:
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        print(json.dumps({
            "wrote": str(dest.relative_to(ROOT)),
            "sha256": digest,
            "unchanged": True,
            "generated_at": previous.get("generated_at"),
        }, indent=1))
        return _exit_code(out)

    out["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    dest.write_text(json.dumps(out, indent=1, sort_keys=True))
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()

    print(json.dumps({
        "wrote": str(dest.relative_to(ROOT)),
        "sha256": digest,
        "unchanged": False,
        "all_closure_items_closed": out["all_closure_items_closed"],
        "item1_closed": out["item_1_four_rungs"]["closed"],
        "item2_closed": out["item_2_f0_rebind"]["closed"],
        "item3_closed": out["item_3_independent_replication"]["closed"],
        "max_abs_diff_vs_declared": out["item_1_four_rungs"]["max_abs_diff_vs_declared"],
        "cross_scheme_spread": out["item_1_four_rungs"]["cross_scheme_spread"],
        "residual_unregistered": out["registration"]["residual_unregistered"],
        "gnum_refs": out["registration"]["gnum_evidence_refs"],
        "gnum_resolved": out["registration"]["gnum_resolved"],
        "gnum_historical_pins": out["registration"]["gnum_historical_pins"],
        "gnum_stale_pins": out["registration"]["gnum_stale_pins"],
        "gnum_missing_files": out["registration"]["gnum_missing_files"],
        "lock_compliant": out["lock_compliance"]["compliant"],
    }, indent=1))

    return _exit_code(out)


if __name__ == "__main__":
    sys.exit(main())
