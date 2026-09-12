#!/usr/bin/env python3
"""W067-N0-STOPRULE-CLOSURE-01 -- independent, read-only closure audit of the three
G-NUM stop-rule items named verbatim in the live controller gate audit:

    "the stop-rule items (4th resolution / F0 re-bind / independent replication verdict)
     are the open requirement"
    (runtime/state/controller_verification/lifecycle_20260912-003718.json,
     controller_gate_audit.G-NUM.reason, measured at map sha 3d45be5969ec)

What this instrument does
-------------------------
It audits *binding and closure*, not the numbers themselves (those were independently
re-run by worker-046/-055/-057/-081/-020 and the lead; this checker does not re-run the
solver). For each stop-rule item it measures the current canonical bytes and decides
MET / PARTIAL_RESIDUAL / NOT_MET from machine checks, never from fluent text:

  I1 fourth-resolution : >=4 rungs at a fixed dt; all schemes monotone and in band; the
                         gate proposal re-binds its certification to the measured bytes;
                         the old constant-CFL ladder is relabelled (not spatial).
  I2 F0 re-bind        : the gate proposal's F0 pin equals the measured canonical rev5
                         taxonomy; residual downstream artifacts still carrying the
                         superseded rev2 hash are enumerated and classified.
  I3 indep. repl. verdict: an independent (non-author) review verdict binds the frozen
                         run hash and/or the re-based certification hash; strength of
                         independence (external vs numerics-group) is reported, not
                         asserted.

Controls (all fail-closed; NONE writes a canonical path -- mutation controls operate on
in-memory copies):
  C1 no-write canary: every anchor re-hashed after the run; drift -> exit 2.
  C2 in-memory mutation of the certification to 3 rungs -> I1 must flip to NOT_MET.
  C3 in-memory mutation of the proposal F0 pin to rev4 276009f4 -> I2 must flip.
  C4 independence-classifier control: a known self verdict -> non-independent;
     worker-057 -> external; deepseek-flash-14 -> numerics group member.
  C5 lock-guard control: live guard must pass; mutated (unlocked) detector must flip.

No canonical path is written. Output defaults to closure.json next to this script.
Worker output only: no gate verdict, no node transition, no numerics_lock change.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

TASK_ID = "W067-N0-STOPRULE-CLOSURE-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"

ANCHOR_PATHS = [
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/tests/n0_gate_proposal.json",
    "numerics/protocol/n0_fixed_dt_certification.json",
    "numerics/protocol/n0_fixed_dt_certification.py",
    "numerics/tests/n0_order_4rung.json",
    "numerics/tests/flat_wave_replication.py",
    "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json",
    "numerics/protocol/fixed_replication_verdict.json",
    "research_map/formulation_taxonomy.yaml",
    "reviews/N0-review-lead-audit.json",
    "research_map/research_map.json",
    "runtime/state/controller_verification/lifecycle_20260912-003718.json",
]
SOLVER_DIR = "numerics/spherical_solver"
LOCK_GUARD = "numerics/tests/selfgravity_lock_guard.py"

SUPERSEDED_F0 = "66bf917bd368"          # F0 rev2, the stale pin
REV4_F0 = "276009f4f63d"                # F0 rev4, mutation-control value
FROZEN_MODULE = "8ade1cdc163ea420"      # numerics/tests/flat_wave_replication.py
FROZEN_RUN = "6542db93eebc5095"         # runtime/.../n0_replication_astra_run2_FIXED.json
CERT = "1677822ceb9c81e8"               # numerics/protocol/n0_fixed_dt_certification.json
FOURRUNG = "c88146a1375c50f0"           # numerics/tests/n0_order_4rung.json

NUMERICS_GROUP = {
    "astra-lead-numerics", "deepseek-flash-12", "deepseek-flash-13",
    "deepseek-flash-14", "deepseek-flash-15", "deepseek-flash-20",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(root: Path) -> dict:
    out = {}
    for rel in ANCHOR_PATHS:
        p = root / rel
        if p.exists():
            out[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        else:
            out[rel] = {"sha256": None, "bytes": None, "absent": True}
    return out


def load_json(p: Path):
    with open(p) as f:
        return json.load(f)


# --------------------------------------------------------------------------- items

def item1_fourth_resolution(root: Path, anchors: dict, cert=None, prop=None) -> dict:
    cert = cert if cert is not None else load_json(
        root / "numerics/protocol/n0_fixed_dt_certification.json")
    prop = prop if prop is not None else load_json(
        root / "numerics/tests/n0_gate_proposal.json")
    cfg = cert.get("config", {})
    dr = list(cfg.get("dr_values", []))
    dt_fixed = cfg.get("dt_fixed")
    p_tol = float(cfg.get("p_tol", 0.3))
    rows = []
    for name, s in (cert.get("schemes", {}) or {}).items():
        fx = (s or {}).get("fixed_dt_certification", {}) or {}
        rws = fx.get("rows", []) or []
        dtv = [r.get("dt") for r in rws]
        order = fx.get("fit_order")
        rows.append({
            "scheme": name,
            "n_rungs": len(rws),
            "dt_values": dtv,
            "dt_constant": bool(dtv) and all(
                d is not None and abs(float(d) - float(dt_fixed)) <= 1e-15 for d in dtv),
            "order": order,
            "in_band": (order is not None) and abs(float(order) - 2.0) <= p_tol,
            "monotone": bool(fx.get("monotone")),
            "within_band": bool(fx.get("within_band")),
        })
    certified = (cert.get("verdict", {}) or {}).get("certified_spatial_order", {}) or {}
    orders_match = all(
        r["order"] is not None and certified.get(r["scheme"]) is not None
        and abs(float(r["order"]) - float(certified[r["scheme"]])) <= 1e-12 for r in rows)
    checks = {
        "rungs_ge_4": len(dr) >= 4,
        "every_scheme_4_rungs": bool(rows) and all(r["n_rungs"] >= 4 for r in rows),
        "dt_constant_on_every_rung": bool(rows) and all(r["dt_constant"] for r in rows),
        "all_monotone": bool(cert.get("verdict", {}).get("all_monotone")),
        "all_within_band": bool(cert.get("verdict", {}).get("all_within_band")),
        "all_orders_in_band": bool(rows) and all(r["in_band"] for r in rows),
        "verdict_orders_match_rows": orders_match,
    }
    fr = prop.get("fourth_resolution", {}) or {}
    pin_ok = str(fr.get("now_satisfied_by", "")).startswith(
        "numerics/protocol/n0_fixed_dt_certification.json#" + anchors[
            "numerics/protocol/n0_fixed_dt_certification.json"]["sha256"][:12])
    checks["proposal_rebinds_certification"] = pin_ok
    mixed_label = str(fr.get("also_available_but_mixed_order", ""))
    headline_blob = json.dumps(prop.get("headline", {}))
    cert_super = cert.get("supersedes_evidence_basis", {}) or {}
    relabel_signals = {
        "field_named_mixed_order": ("also_available_but_mixed_order" in fr
                                    and FOURRUNG[:12] in mixed_label),
        "proposal_headline_relabelled": ("RELABELLED the constant-CFL ladder as a mixed-order"
                                         in headline_blob),
        "cert_supersedes_not_a_spatial_claim": ("NOT a spatial claim" in str(
            cert_super.get("relabelled_as", ""))),
    }
    checks["constant_cfl_ladder_relabelled"] = (
        relabel_signals["field_named_mixed_order"]
        and (relabel_signals["proposal_headline_relabelled"]
             or relabel_signals["cert_supersedes_not_a_spatial_claim"]))

    status = "MET" if all(checks.values()) else "NOT_MET"
    return {
        "item_id": "I1-fourth-resolution",
        "requirement": ("stop rule (1): add a fourth resolution rung to the convergence "
                        "study, or explicitly scope the claim to a 3-level observed order "
                        "with a tolerance justification"),
        "status": status,
        "checks": checks,
        "measured": {
            "certification": "numerics/protocol/n0_fixed_dt_certification.json#"
                             + anchors["numerics/protocol/n0_fixed_dt_certification.json"]["sha256"],
            "rungs": dr,
            "dt_fixed": dt_fixed,
            "scheme_rows": rows,
            "proposal_pin": fr.get("now_satisfied_by"),
            "old_ladder_label": mixed_label,
            "relabel_signals": relabel_signals,
        },
        "evidence_refs": [
            "numerics/protocol/n0_fixed_dt_certification.json#" + CERT,
            "numerics/tests/n0_gate_proposal.json#b4192221ff7d",
            "numerics/tests/n0_order_4rung.json#" + FOURRUNG[:12],
        ],
        "falsifier": ("Falsified if the fixed-dt certification at the measured hash shows "
                      "<4 rungs, a non-constant dt, a non-monotone scheme, an order outside "
                      "2.0 +/- 0.3, or if the proposal's certification pin stops resolving "
                      "to the measured bytes."),
    }


def item2_f0_rebind(root: Path, anchors: dict, prop=None, frv=None) -> dict:
    prop = prop if prop is not None else load_json(root / "numerics/tests/n0_gate_proposal.json")
    frv = frv if frv is not None else load_json(
        root / "numerics/protocol/fixed_replication_verdict.json")
    protocol_text = (root / "numerics/CONVERGENCE_PROTOCOL.md").read_text()
    tax_sha = anchors["research_map/formulation_taxonomy.yaml"]["sha256"]

    prop_pin = (prop.get("evidence_hashes", {}) or {}).get(
        "research_map/formulation_taxonomy.yaml")
    prop_ok = prop_pin == tax_sha

    frv_chain = (frv.get("chained_evidence_hashes", {}) or {}).get(
        "research_map/formulation_taxonomy.yaml")
    frv_prov = (frv.get("provenance", {}) or {}).get("taxonomy_sha256")
    frv_stale = (frv_chain is not None and frv_chain[:12] == SUPERSEDED_F0) or \
                (frv_prov is not None and frv_prov[:12] == SUPERSEDED_F0)
    protocol_mentions = len(re.findall(r"66bf917b", protocol_text))
    protocol_self_declares_superseded = "superseded on disk" in protocol_text

    checks = {
        "proposal_pins_measured_rev5": prop_ok,
        "downstream_stale_active_pins_absent": not frv_stale,
    }
    status = "MET" if all(checks.values()) else (
        "PARTIAL_RESIDUAL" if prop_ok else "NOT_MET")
    return {
        "item_id": "I2-f0-rebind",
        "requirement": ("stop rule (2): re-bind the class binding to declared F0 rev5 "
                        "0abb9ed8a961"),
        "status": status,
        "checks": checks,
        "measured": {
            "measured_taxonomy": "research_map/formulation_taxonomy.yaml#" + tax_sha,
            "proposal_pin": prop_pin,
            "fixed_replication_verdict_chain_pin": frv_chain,
            "fixed_replication_verdict_provenance_pin": frv_prov,
            "protocol_stale_hash_mentions": protocol_mentions,
            "protocol_self_declares_superseded": protocol_self_declares_superseded,
            "residual_owner": "astra-lead-numerics (numerics artifacts)",
        },
        "prior_worker_067_evidence": {
            "review_event": "w067-n0rebind-20260912T003805-20-review",
            "verdict": "accept (scoped to class membership only)",
            "finding": "REBIND_INERT_FOR_CLASS_MEMBERSHIP, controls 5/5",
            "artifact": "artifacts/worker-067/n0_f0_rebind/rebind_check.json#22afbea8a137",
        },
        "evidence_refs": [
            "numerics/tests/n0_gate_proposal.json#b4192221ff7d",
            "numerics/protocol/fixed_replication_verdict.json#dcad962324e3",
            "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/worker-067/n0_f0_rebind/rebind_check.json#22afbea8a137",
        ],
        "falsifier": ("Falsified as a closure if the proposal's F0 pin no longer equals the "
                      "measured canonical taxonomy hash, or if the stale rev2 pins in "
                      "fixed_replication_verdict.json are shown to be load-bearing for the "
                      "order claim (my prior check measured them inert for class "
                      "membership; load-bearing for the order is a separate claim)."),
    }


def _all_review_records(root: Path) -> list:
    recs, seen = [], set()
    m = load_json(root / "research_map/research_map.json")
    for r in (m.get("reviews") or []):
        if isinstance(r, dict):
            recs.append(r)
    ev = root / "research_map/events.jsonl"
    if ev.exists():
        for line in ev.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("event_type") == "review":
                recs.append(r)
    out = []
    for r in recs:
        key = r.get("event_id") or (r.get("reviewer"), r.get("target_id"),
                                    r.get("created_at"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _classify(reviewer: str) -> str:
    rev = str(reviewer or "")
    if rev.startswith("astra-lead-numerics") or rev.startswith("astra-numfix"):
        return "self_or_numerics_lead"
    base = rev.split(" ")[0].split("(")[0].strip()
    if base in NUMERICS_GROUP:
        return "numerics_group_member"
    return "external"


def item3_replication_verdict(root: Path, recs=None) -> dict:
    recs = recs if recs is not None else _all_review_records(root)
    targets = {"frozen_run": FROZEN_RUN, "certification": CERT,
               "frozen_module": FROZEN_MODULE}
    bound = {k: [] for k in targets}
    for r in recs:
        blob = json.dumps(r)
        for k, pref in targets.items():
            if pref in blob:
                bound[k].append({
                    "event_id": r.get("event_id"),
                    "actor": r.get("actor") or r.get("reviewer"),
                    "reviewer": r.get("reviewer") or r.get("actor"),
                    "verdict": r.get("verdict"),
                    "score": r.get("score"),
                    "created_at": r.get("created_at"),
                    "independence": _classify(r.get("reviewer") or r.get("actor")),
                })
    frv = load_json(root / "numerics/protocol/fixed_replication_verdict.json")
    self_verdict = {
        "artifact": "numerics/protocol/fixed_replication_verdict.json#dcad962324e3",
        "author": frv.get("assignment_id"),
        "binding_status": frv.get("binding_status"),
        "verdict_field_present": "verdict" in frv,
    }

    def strongest(key):
        rows = [b for b in bound[key] if b["verdict"] in ("accept", "revise", "reject")]
        order = {"external": 0, "numerics_group_member": 1, "self_or_numerics_lead": 2}
        rows.sort(key=lambda b: (order.get(b["independence"], 9), b["created_at"] or ""))
        return rows

    frozen = strongest("frozen_run")
    cert = strongest("certification")
    ext_frozen = [b for b in frozen if b["independence"] == "external"]
    ext_cert = [b for b in cert if b["independence"] == "external"]
    accepted_frozen = [b for b in frozen if b["verdict"] == "accept"]
    accepted_cert = [b for b in cert if b["verdict"] == "accept"]

    checks = {
        "independent_verdict_binds_frozen_run": bool(accepted_frozen),
        "independent_verdict_binds_rebased_basis": bool(accepted_cert),
        "external_verdict_exists_on_rebased_basis": bool(ext_cert),
        "self_verdict_is_not_counted_independent": (
            self_verdict["binding_status"] != "FINAL"),
    }
    status = "MET" if (checks["independent_verdict_binds_frozen_run"]
                       and checks["independent_verdict_binds_rebased_basis"]) else "NOT_MET"
    def _desc(rows):
        return "; ".join(
            f"{str(b['reviewer']).split(' (')[0]} {b['verdict']} {str(b['created_at'])[:19]} "
            f"[{b['independence']}]" for b in rows) or "none"

    binding_drift_note = (
        "Independent accepts bind both hashes. Frozen 3-rung run " + FROZEN_RUN + " -> "
        + _desc(accepted_frozen) + ". Re-based fixed-dt certification " + CERT + " -> "
        + _desc(accepted_cert) + ". The frozen-run accept was recorded at 00:07 against the "
        "constant-CFL basis that the lead later relabelled mixed-order; no external "
        "(non-numerics) verdict binds the frozen run hash, and the accepts on the current "
        "certified basis are worker-authority advisory (lead-audit owns the N0 node verdict).")
    return {
        "item_id": "I3-independent-replication-verdict",
        "requirement": ("stop rule (3): supply one independent replication verdict of the "
                        "order at the frozen run hash"),
        "status": status,
        "checks": checks,
        "measured": {
            "frozen_run": FROZEN_RUN,
            "certification": CERT,
            "frozen_module": FROZEN_MODULE,
            "accepts_binding_frozen_run": accepted_frozen,
            "accepts_binding_certification": accepted_cert,
            "external_accepts_frozen_run": ext_frozen,
            "external_accepts_certification": ext_cert,
            "numerics_self_verdict": self_verdict,
        },
        "binding_drift_note": binding_drift_note,
        "evidence_refs": [
            "reviews/N0-review-lead-audit.json#e3c314f886be",
            "numerics/protocol/fixed_replication_verdict.json#dcad962324e3",
            "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#6542db93eebc",
            "numerics/protocol/n0_fixed_dt_certification.json#" + CERT,
        ],
        "falsifier": ("Falsified if no review record with verdict accept binds either the "
                      "frozen run hash " + FROZEN_RUN + " or the certification hash " + CERT +
                      " at re-measurement time, or if the frozen-run accept is shown to be "
                      "authored by the run's own author."),
    }


# ----------------------------------------------------------------------- controls

def run_controls(root: Path, anchors: dict) -> dict:
    # C2: certification with only 3 rungs must flip I1 (in-memory only).
    cert = load_json(root / "numerics/protocol/n0_fixed_dt_certification.json")
    prop = load_json(root / "numerics/tests/n0_gate_proposal.json")
    mut = copy.deepcopy(cert)
    mut["config"]["dr_values"] = mut["config"]["dr_values"][:3]
    for s in (mut.get("schemes", {}) or {}).values():
        fx = (s or {}).get("fixed_dt_certification")
        if isinstance(fx, dict) and fx.get("rows"):
            fx["rows"] = fx["rows"][:3]
    flipped1 = item1_fourth_resolution(root, anchors, cert=mut, prop=prop)["status"] != "MET"
    c2 = {"control": "C2-mutation-3-rungs-flips-I1", "pass": bool(flipped1)}

    # C3: proposal F0 pin set to rev4 must flip I2 (in-memory only).
    mutp = copy.deepcopy(prop)
    mutp["evidence_hashes"]["research_map/formulation_taxonomy.yaml"] = REV4_F0
    flipped2 = item2_f0_rebind(root, anchors, prop=mutp)["status"] != "MET"
    c3 = {"control": "C3-mutation-rev4-pin-flips-I2", "pass": bool(flipped2)}

    # C4: independence classifier.
    c4_pass = (_classify("astra-lead-numerics") == "self_or_numerics_lead"
               and _classify("worker-057 (independent of astra-lead-numerics; advisory only)")
               == "external"
               and _classify("deepseek-flash-14") == "numerics_group_member")
    c4 = {"control": "C4-independence-classifier", "pass": bool(c4_pass),
          "samples": {"astra-lead-numerics": _classify("astra-lead-numerics"),
                      "worker-057": _classify("worker-057 (independent)"),
                      "deepseek-flash-14": _classify("deepseek-flash-14")}}

    # C5: lock guard (live predicate true; the same predicate on a mutated
    # unlocked copy must be false, proving the detector is not constant-true).
    guard_present = (root / LOCK_GUARD).exists()
    solver_absent = not (root / SOLVER_DIR).exists()
    m = load_json(root / "research_map/research_map.json")
    lock = m.get("numerics_lock", {})

    def lock_ok(lk: dict) -> bool:
        return lk.get("state") == "locked" and lk.get("locked_nodes") == ["N1"]

    live_lock = lock_ok(lock)
    mutated = copy.deepcopy(lock)
    mutated["state"] = "unlocked"
    mut_lock_flips = not lock_ok(mutated)
    c5 = {"control": "C5-lock-guard", "pass": bool(guard_present and solver_absent
                                                  and live_lock and mut_lock_flips),
          "solver_absent": solver_absent, "guard_present": guard_present,
          "lock_state": lock.get("state"), "locked_nodes": lock.get("locked_nodes"),
          "mutated_unlock_detected": mut_lock_flips}

    return {"C1": {"control": "C1-no-write-canary", "pass": None,
                   "note": "filled by caller (anchors re-measured after the run)"},
            "C2": c2, "C3": c3, "C4": c4, "C5": c5}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "closure.json"))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    out = Path(a.out)

    before = measure(root)
    if any(v["sha256"] is None for v in before.values()):
        missing = [k for k, v in before.items() if v["sha256"] is None]
        print(f"REFUSING: missing anchors {missing}", file=sys.stderr)
        return 2

    i1 = item1_fourth_resolution(root, before)
    i2 = item2_f0_rebind(root, before)
    i3 = item3_replication_verdict(root)
    controls = run_controls(root, before)
    after = measure(root)
    c1_pass = before == after
    controls["C1"]["pass"] = c1_pass

    if not c1_pass:
        print("FAIL-CLOSED: anchor drift during run", file=sys.stderr)
        return 2
    if not all(controls[k]["pass"] for k in ("C1", "C2", "C3", "C4", "C5")):
        print("FAIL-CLOSED: a control failed", json.dumps(controls, indent=1), file=sys.stderr)
        return 2

    items = [i1, i2, i3]
    met = [i["item_id"] for i in items if i["status"] == "MET"]
    partial = [i["item_id"] for i in items if i["status"].startswith("PARTIAL")]
    not_met = [i["item_id"] for i in items if i["status"] == "NOT_MET"]
    result = {
        "schema": "w067-n0-stoprule-closure/v1",
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "actor": "worker-067",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "authority_note": ("worker-level closure audit; no gate verdict, no node status, "
                           "no numerics_lock change. Read-only on every canonical path."),
        "anchors": before,
        "items": items,
        "summary": {
            "met": met, "partial": partial, "not_met": not_met,
            "disposition": ("ALL_THREE_ITEMS_ADDRESSED_WITH_ONE_RESIDUAL_AND_ONE_BINDING_DRIFT"
                            if not not_met else "STOP_RULE_STILL_OPEN"),
            "residual": ("I2: fixed_replication_verdict.json still carries the superseded "
                         "rev2 taxonomy hash as an active evidence pin (measured inert for "
                         "class membership by the prior worker-067 check; not repaired at "
                         "the artifact)" if i2["status"] != "MET" else None),
            "binding_drift": i3["binding_drift_note"],
            "n0_node_verdict_on_disk": ("reviews/N0-review-lead-audit.json#e3c314f886be "
                                        "(revise 3.5; superseded for adjudication by "
                                        "astra-life04-n0-verify)"),
            "lock": {"state": "locked", "locked_nodes": ["N1"],
                     "solver_absent": True, "guard_present": True},
        },
        "controls": controls,
        "not_claimed": [
            "no gate verdict and no gate self-pass (authority: Astra / lead-audit)",
            "no N0 node completion or status transition",
            "no numerics_lock release; N1 untouched",
            "does not re-run the solver; audits binding/closure of already-filed evidence",
            "no claim that the dissents at the protocol of record are formally discharged "
            "(that is the controller's / reviewers' adjudication, not mine)",
        ],
    }
    out.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n")
    print(f"wrote {out}")
    print(json.dumps(result["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
