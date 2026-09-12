#!/usr/bin/env python3
"""W012-GNUM-SUCCESSOR-VERIFY-01 — independent read-only verification of the C8 supersession
successor numerics/protocol/fixed_replication_verdict_rev2.json.

Class binding: AF-WCC-SCALAR-SPH / N0 / G-NUM.  Read-only: the only file this instrument
writes is its own report.json under artifacts/worker-012/n0_successor_verify/.

Run:  python3 artifacts/worker-012/n0_successor_verify/verify_successor.py
Exit: 0 verified (possibly with annotations), 2 verification failure, 3 moving-target void.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

TASK_ID = "W012-GNUM-SUCCESSOR-VERIFY-01"
WORKER = "worker-012"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "N0"
GATE = "G-NUM"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

REV2_REL = "numerics/protocol/fixed_replication_verdict_rev2.json"
PRED_REL = "numerics/protocol/fixed_replication_verdict.json"
TAX_REL = "research_map/formulation_taxonomy.yaml"
FROZEN_REL = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
HARNESS_REL = "artifacts/flash-04/n0_acceptance/harness.py"
REPL_REL = "numerics/tests/flat_wave_replication.py"
SV_REL = "numerics/protocol/verify_fixed_scheme_independence.py"
PROPOSAL_REL = "numerics/tests/n0_gate_proposal.json"
REGISTRY_REL = "runtime/state/artifact_hashes.json"
GATES_REL = "numerics/gates.py"
PROTOCOL_REL = "numerics/CONVERGENCE_PROTOCOL.md"

DECLARED = {
    REV2_REL: "7954d2d355451e3dbd3e7b7c23769ba204451cc8adf5eb04515910069a10fa60",
    PRED_REL: "dcad962324e3be156d1ef1577b7ee2613fac803058351b643d2c8f67bc787a36",
    TAX_REL: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    FROZEN_REL: "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e",
    HARNESS_REL: "0646de3f75bd4335849f135eb41c1b1d25e55133191c3b4ddbf88f962488df7e",
    REPL_REL: "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    SV_REL: "a0daf1271bfb556d148180c479b03bd395eefd522818cf4c31228df67d2a7b3e",
    PROPOSAL_REL: "b4192221ff7d96dbb61ce37fa667e1a59b7b290b8ca34f77e7674c03ca5ba2e3",
    GATES_REL: "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
    PROTOCOL_REL: "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
}
FROZEN_F0_PIN = "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232"
WALL_CLOCK_NUMERIC = {"runtime_seconds"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(o, pre=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flatten(v, f"{pre}.{k}" if pre else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(flatten(v, f"{pre}[{i}]"))
    else:
        out[pre] = o
    return out


def numeric_leaves(doc):
    return {k: v for k, v in flatten(doc).items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def numeric_delta(pred, rev2):
    a, b = numeric_leaves(pred), numeric_leaves(rev2)
    common = sorted(set(a) & set(b))
    diff_all = [k for k in common if a[k] != b[k]]
    excluded = sorted(k for k in diff_all if k in WALL_CLOCK_NUMERIC)
    unexcluded = sorted(k for k in diff_all if k not in WALL_CLOCK_NUMERIC)
    compared = [k for k in common if k not in WALL_CLOCK_NUMERIC]
    max_abs = max((abs(a[k] - b[k]) for k in compared), default=0.0)
    return {
        "numeric_leaves_common": len(common),
        "numeric_leaves_compared": len(compared),
        "differing_leaves_before_exclusion": diff_all,
        "excluded_wall_clock_leaves": excluded,
        "differing_leaves": unexcluded,
        "unexpected_differing_leaves": unexcluded,
        "max_abs_difference": max_abs,
        "only_wall_clock_excluded": excluded == sorted(WALL_CLOCK_NUMERIC) and not unexcluded,
    }


def subtree_equal(doc_a, doc_b, prefix):
    a = {k: v for k, v in flatten(doc_a).items() if k == prefix or k.startswith(prefix + ".") or k.startswith(prefix + "[")}
    b = {k: v for k, v in flatten(doc_b).items() if k == prefix or k.startswith(prefix + ".") or k.startswith(prefix + "[")}
    return a == b, {"n_leaves": len(a), "only_a": sorted(set(a) - set(b)), "only_b": sorted(set(b) - set(a)),
                    "differing": sorted(k for k in set(a) & set(b) if a[k] != b[k])}


def check_pred_supersedes(pred, rev2, measured_pred_sha):
    return rev2.get("supersedes", {}).get("sha256") == measured_pred_sha, {
        "declared_supersedes_sha256": rev2.get("supersedes", {}).get("sha256"),
        "measured_predecessor_sha256": measured_pred_sha,
        "supersedes_path": rev2.get("supersedes", {}).get("path"),
    }


def check_pred_defect(pred, live_tax_sha):
    chained = pred.get("chained_evidence_hashes", {}).get(TAX_REL)
    asserted = pred.get("provenance", {}).get("fixed_taxonomy_sha256_matches_on_disk")
    return (asserted is True and chained == FROZEN_F0_PIN and live_tax_sha != chained), {
        "predecessor_assertion": asserted,
        "predecessor_chained_taxonomy_sha": chained,
        "live_taxonomy_sha": live_tax_sha,
        "assertion_false_at_live_disk": (asserted is True and chained != live_tax_sha),
    }


def check_taxonomy_rebind(rev2, frozen, live_tax_sha):
    chained = rev2.get("chained_evidence_hashes", {}).get(TAX_REL)
    reb = rev2.get("taxonomy_rebind", {})
    frozen_decl = frozen.get("provenance", {}).get("f0_taxonomy_sha256")
    prov_assert = rev2.get("provenance", {}).get("fixed_taxonomy_sha256_matches_on_disk")
    ok = (chained == live_tax_sha
          and reb.get("current_f0_disk") == live_tax_sha
          and reb.get("frozen_run_f0_pin") == frozen_decl == FROZEN_F0_PIN
          and reb.get("frozen_run_f0_pin_matches_current_disk") is False
          and prov_assert is False
          and reb.get("load_bearing_for_order_claim") is False)
    return ok, {"successor_chained_taxonomy_sha": chained, "live_taxonomy_sha": live_tax_sha,
                "current_f0_disk": reb.get("current_f0_disk"), "frozen_run_f0_pin": reb.get("frozen_run_f0_pin"),
                "frozen_run_declared_f0_pin": frozen_decl,
                "frozen_run_f0_pin_matches_current_disk": reb.get("frozen_run_f0_pin_matches_current_disk"),
                "successor_provenance_assertion": prov_assert,
                "load_bearing_for_order_claim": reb.get("load_bearing_for_order_claim")}


def check_chained(rev2, measured):
    rows = []
    for rel, expect in rev2.get("chained_evidence_hashes", {}).items():
        got = measured.get(rel, "<missing>")
        rows.append({"path": rel, "declared": expect, "measured": got, "match": expect == got})
    return all(r["match"] for r in rows) and len(rows) == 4, {"entries": rows}


def check_order_identical(pred, rev2):
    detail = {}
    ok = True
    for prefix in ("q1_invariant_functional_scheme_appropriate", "q2_order_fit_carries_uncertainty",
                   "falsifier_tests"):
        same, d = subtree_equal(pred, rev2, prefix)
        detail[prefix] = d
        ok = ok and same
    detail["r4_note_identical"] = pred.get("r4_note") == rev2.get("r4_note")
    detail["class_node_gate_identical"] = all(pred.get(k) == rev2.get(k) for k in ("class_id", "node_id", "gate"))
    ok = ok and detail["r4_note_identical"] and detail["class_node_gate_identical"]
    return ok, detail


def check_source_verifier(rev2, measured_sv_sha):
    sv = rev2.get("source_verifier", {})
    return sv.get("sha256") == measured_sv_sha and bool(sv.get("method")), {
        "declared": sv.get("sha256"), "measured": measured_sv_sha, "path": sv.get("path"),
        "method": sv.get("method")}


def check_proposal_pin(pred, proposal):
    pin = (proposal.get("evidence_hashes") or {}).get(PRED_REL)
    rev2_pin = (proposal.get("evidence_hashes") or {}).get(REV2_REL)
    return pin == DECLARED[PRED_REL], {"proposal_pin_predecessor": pin, "proposal_pin_successor": rev2_pin}


def check_registration(rev2_sha, registry):
    reg = registry.get("registry", {})
    entry = reg.get(REV2_REL)
    return bool(entry) and entry.get("sha256") == rev2_sha, {
        "registered": bool(entry), "entry": entry, "expected_sha256": rev2_sha}


def find_n1_artifacts(root: Path, reviewed_refs):
    hits = []
    for rel in reviewed_refs:
        low = str(rel).lower()
        if "spherical_solver" in low or "/n1_" in low or low.startswith("n1"):
            hits.append(rel)
    solver_dir = root / "numerics" / "spherical_solver"
    scan = []
    for p in (root / "numerics").rglob("*"):
        if p.is_file() and ("spherical_solver" in str(p.relative_to(root)) or p.name.startswith("n1_")):
            scan.append(str(p.relative_to(root)))
    return {"spherical_solver_dir_exists": solver_dir.exists(), "reviewed_ref_hits": hits,
            "numerics_scan_hits": sorted(scan)}


def lock_guard_snapshot(root: Path):
    sys.path.insert(0, str(root))
    from numerics import gates  # local import; read-only evaluate()
    rep = gates.evaluate(root)
    return {"production_allowed": rep.get("production_allowed"), "verdict": rep.get("verdict"),
            "blocking_reasons": rep.get("blocking_reasons", []),
            "protocol_review_contest": rep.get("protocol_review", {}).get("contest"),
            "protocol_review_accepts": rep.get("protocol_review", {}).get("accepting_reviews"),
            "protocol_review_dissents": [d.get("event_id") for d in rep.get("protocol_review", {}).get("dissenting_reviews", [])]}


def main() -> int:
    t0 = time.time()
    annotations, hard_failures, open_items = [], [], []
    checks, controls = [], []

    def add(cid, ok, detail, severity="load_bearing"):
        checks.append({"id": cid, "ok": bool(ok), "severity": severity, "detail": detail})
        return bool(ok)

    def ctl(cid, ok, detail):
        controls.append({"id": cid, "ok": bool(ok), "detail": detail})
        return bool(ok)

    # ---- pins before ----
    measured_before = {}
    pin_ok = True
    for rel, expect in DECLARED.items():
        p = ROOT / rel
        got = sha256_file(p) if p.is_file() else "<missing>"
        measured_before[rel] = got
        if got != expect:
            pin_ok = False
    add("V0-pins-stable-before", pin_ok, {"declared": DECLARED, "measured": measured_before})
    if not pin_ok:
        hard_failures.append("moving target: at least one pinned input did not match its declared sha256 before measurement")
        report = {"schema": "worker-verification-report/v1", "task_id": TASK_ID, "worker": WORKER,
                  "verdict": "VOID_MOVING_TARGET", "checks": checks, "controls": controls,
                  "hard_failures": hard_failures, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 3

    rev2 = json.loads((ROOT / REV2_REL).read_text())
    pred = json.loads((ROOT / PRED_REL).read_text())
    frozen = json.loads((ROOT / FROZEN_REL).read_text())
    proposal = json.loads((ROOT / PROPOSAL_REL).read_text())
    registry = json.loads((ROOT / REGISTRY_REL).read_text())
    live_tax_sha = measured_before[TAX_REL]

    # ---- V1..V10 ----
    add("V1-supersedes-sha256", *check_pred_supersedes(pred, rev2, measured_before[PRED_REL]))
    add("V2-predecessor-contradicted-assertion", *check_pred_defect(pred, live_tax_sha))
    add("V3-successor-taxonomy-rebind", *check_taxonomy_rebind(rev2, frozen, live_tax_sha))
    add("V4-chained-evidence-hashes-on-disk", *check_chained(rev2, measured_before))
    delta = numeric_delta(pred, rev2)
    claim = rev2.get("numeric_delta_vs_superseded", {})

    def empty(v):
        return v in ([], {})

    delta_ok = (delta["numeric_leaves_compared"] == claim.get("numeric_leaves_compared") == 79
                and abs(delta["max_abs_difference"] - claim.get("max_abs_difference", 1)) < 1e-15
                and empty(delta["differing_leaves"]) and empty(claim.get("differing_leaves"))
                and delta["only_wall_clock_excluded"])
    add("V5-numeric-delta-reproduced", delta_ok, {"independent": delta, "declared": claim})
    types_ok = (isinstance(claim.get("differing_leaves"), list)
                and isinstance(claim.get("excluded_wall_clock_leaves"), list)
                and all(isinstance(x, str) for x in claim.get("excluded_wall_clock_leaves", []))
                and isinstance(claim.get("numeric_leaves_compared"), int)
                and isinstance(claim.get("max_abs_difference"), (int, float)))
    add("V5b-declared-delta-field-types", types_ok,
        {"differing_leaves_type": type(claim.get("differing_leaves")).__name__,
         "excluded_wall_clock_leaves": claim.get("excluded_wall_clock_leaves"),
         "numeric_leaves_compared_type": type(claim.get("numeric_leaves_compared")).__name__,
         "max_abs_difference_type": type(claim.get("max_abs_difference")).__name__},
        severity="annotation")
    add("V6-order-invariant-leaves-identical", *check_order_identical(pred, rev2))
    add("V7-source-verifier-pin", *check_source_verifier(rev2, measured_before[SV_REL]))
    add("V8-proposal-still-pins-predecessor", *check_proposal_pin(pred, proposal))
    add("V9-successor-registered-in-artifact-hashes", *check_registration(measured_before[REV2_REL], registry))
    n1 = find_n1_artifacts(ROOT, rev2.get("chained_evidence_hashes", {}).keys())
    lg = lock_guard_snapshot(ROOT)
    add("V10-lock-guard",
        (not n1["spherical_solver_dir_exists"]) and (not n1["reviewed_ref_hits"]) and (not n1["numerics_scan_hits"])
        and lg["production_allowed"] is False and lg["verdict"] == "N1_BLOCKED",
        {"n1": n1, "gates": lg})

    # ---- controls ----
    rev2_mut = copy.deepcopy(rev2)
    pred_mut = copy.deepcopy(pred)
    mut_key = sorted(set(numeric_leaves(pred)) & set(numeric_leaves(rev2)) - WALL_CLOCK_NUMERIC)[0]
    rev2_mut_leaf = copy.deepcopy(rev2)
    rev2_mut_leaf["q2_order_fit_carries_uncertainty"]["r5_floor"] = 0.5
    d1 = numeric_delta(pred, rev2_mut_leaf)
    ctl("K1-flipped-numeric-leaf-detected", d1["max_abs_difference"] != 0.0 and len(d1["differing_leaves"]) >= 1,
        {"first_common_numeric_leaf": mut_key, "delta": {k: d1[k] for k in ("max_abs_difference", "differing_leaves")}})
    d2 = numeric_delta(pred, rev2)
    saved = set(WALL_CLOCK_NUMERIC)
    WALL_CLOCK_NUMERIC.clear()
    d3 = numeric_delta(pred, rev2)
    WALL_CLOCK_NUMERIC.update(saved)
    ctl("K2-wall-clock-exclusion-load-bearing",
        d2["only_wall_clock_excluded"] and "runtime_seconds" in d3["differing_leaves_before_exclusion"]
        and d3["only_wall_clock_excluded"] is False,
        {"with_exclusion": d2["excluded_wall_clock_leaves"], "without_exclusion": d3["differing_leaves_before_exclusion"]})
    rev2_mut_sha = copy.deepcopy(rev2)
    rev2_mut_sha["supersedes"]["sha256"] = "0" * 64
    ctl("K3-corrupt-supersedes-sha-detected", check_pred_supersedes(pred, rev2_mut_sha, measured_before[PRED_REL])[0] is False, {})
    rev2_mut_tax = copy.deepcopy(rev2)
    rev2_mut_tax["chained_evidence_hashes"][TAX_REL] = FROZEN_F0_PIN
    ctl("K4-taxonomy-rebind-regression-detected", check_taxonomy_rebind(rev2_mut_tax, frozen, live_tax_sha)[0] is False, {})
    rev2_mut_chain = copy.deepcopy(rev2)
    rev2_mut_chain["chained_evidence_hashes"].pop(HARNESS_REL)
    ctl("K5-missing-chain-entry-detected", check_chained(rev2_mut_chain, measured_before)[0] is False, {})
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "pred_copy.json"
        raw = (ROOT / PRED_REL).read_bytes()
        tmp.write_bytes(raw)
        h1 = sha256_file(tmp)
        tmp.write_bytes(raw[:-1] + (b" " if raw[-1:] != b" " else b"\n"))
        h2 = sha256_file(tmp)
    ctl("K6-one-byte-hash-sensitivity", h1 != h2, {"h1": h1[:16], "h2": h2[:16]})
    prop_mut = copy.deepcopy(proposal)
    prop_mut["evidence_hashes"][PRED_REL] = DECLARED[REV2_REL]
    ctl("K7-proposal-pin-substitution-detected", check_proposal_pin(pred, prop_mut)[0] is False, {})
    reg_mut = copy.deepcopy(registry)
    reg_mut["registry"][REV2_REL]["sha256"] = "0" * 64
    ctl("K8-registry-mismatch-detected", check_registration(measured_before[REV2_REL], reg_mut)[0] is False, {})
    ctl("K9-n1-sentinel-discriminates",
        find_n1_artifacts(ROOT, ["numerics/tests/flat_wave.py"])["reviewed_ref_hits"] == []
        and find_n1_artifacts(ROOT, ["numerics/spherical_solver/poisson.py"])["reviewed_ref_hits"] != [],
        {})
    muts = [("K10a", check_pred_supersedes(pred, rev2_mut_sha, measured_before[PRED_REL])[0] is False),
            ("K10b", check_taxonomy_rebind(rev2_mut_tax, frozen, live_tax_sha)[0] is False),
            ("K10c", check_chained(rev2_mut_chain, measured_before)[0] is False),
            ("K10d", check_proposal_pin(pred, prop_mut)[0] is False),
            ("K10e", check_registration(measured_before[REV2_REL], reg_mut)[0] is False)]
    ctl("K10-no-vacuous-pass", all(v for _, v in muts), {k: v for k, v in muts})

    # ---- pins after ----
    measured_after = {rel: (sha256_file(ROOT / rel) if (ROOT / rel).is_file() else "<missing>") for rel in DECLARED}
    add("V11-pins-stable-after", measured_after == measured_before, {"drift": {k: [measured_before[k], measured_after[k]] for k in DECLARED if measured_before[k] != measured_after[k]}})

    # ---- annotations ----
    excl = rev2.get("numeric_delta_vs_superseded", {}).get("excluded_wall_clock_leaves")
    if excl == ["/runtime_seconds"]:
        annotations.append({"id": "A1-path-notation", "text": "successor declares the excluded leaf as '/runtime_seconds'; the natural flattened path is 'runtime_seconds' (notation only, exclusion set is identical)"})
    annotations.append({"id": "A2-assertion-semantics", "text": "successor provenance.fixed_taxonomy_sha256_matches_on_disk=false is the recomputed truth for the FROZEN run pin (66bf917b vs live 0abb9ed8), not a regression of the repair; taxonomy_rebind documents it and load_bearing_for_order_claim=false"})
    annotations.append({"id": "A3-binding", "text": "successor binding_status=PROVISIONAL, validation_status=unverified, and numerics/tests/n0_gate_proposal.json still pins the predecessor in evidence_hashes; if the adjudication accepts the successor as replication evidence of record, the controller must bind it in the proposal/map"})
    ann_fail = [c for c in checks if not c["ok"] and c.get("severity") == "annotation"]
    for c in ann_fail:
        if c["id"] == "V5b-declared-delta-field-types":
            annotations.append({"id": "A4-declared-type-defect", "text": "numeric_delta_vs_superseded.differing_leaves is declared as an empty JSON object {} instead of an empty array []; the substantive claim (no differing leaves) is verified, but list-typed consumers would need to tolerate an object. Non-load-bearing type defect in the successor record; a follow-up successor/erratum would fix it without changing any number."})
    load_fail = [c for c in checks if not c["ok"] and c.get("severity") != "annotation"]
    if not load_fail:
        open_items.append("OI-1 (controller): successor is registered but not yet the proposal's pinned replication evidence; proposal evidence_hashes still cites the predecessor dcad962324e3.")
        open_items.append("OI-2 (lead-audit): whether supersession discharges w067-provledger is an adjudication, not a worker call; this report only measures numeric identity, the corrected provenance assertion, and pin integrity.")
        if ann_fail:
            open_items.append("OI-3 (non-blocking, successor record): numeric_delta_vs_superseded.differing_leaves is {} (object) where a list is declared elsewhere; type-only defect recorded as A4.")
    else:
        for c in load_fail:
            hard_failures.append(f"{c['id']} failed")

    if hard_failures:
        verdict = "SUCCESSOR_NOT_VERIFIED"
    elif ann_fail:
        verdict = "SUCCESSOR_VERIFIED_WITH_ANNOTATIONS"
    else:
        verdict = "SUCCESSOR_VERIFIED"
    report = {
        "schema": "worker-verification-report/v1", "task_id": TASK_ID, "worker": WORKER,
        "class_id": CLASS_ID, "node_id": NODE_ID, "gate": GATE,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_seconds": round(time.time() - t0, 3),
        "verdict": verdict,
        "target": f"{REV2_REL}#{measured_before[REV2_REL]}",
        "supersedes": f"{PRED_REL}#{measured_before[PRED_REL]}",
        "pins_declared": DECLARED, "pins_measured": measured_before, "pins_after": measured_after,
        "checks": checks, "controls": controls, "hard_failures": hard_failures,
        "annotations": annotations, "open_items": open_items,
        "falsifier": ("Void if any pinned input re-hashes (rev2 7954d2d355451e3d, predecessor dcad962324e3be15, taxonomy 0abb9ed8a961, frozen run 6542db93eebc, harness 0646de3f75bd, replication module 8ade1cdc163e, source verifier a0daf1271bfb, proposal b4192221ff7d, gates fcd1d70991b6, protocol 1e6cdf04d7a2). Falsified if the leaf-rule recomputation does not yield 79 compared numeric leaves / max |diff| 0.0 / no non-wall-clock differing leaf, if any chained evidence hash does not match disk, if the successor does not bind live F0 rev5 while marking the frozen pin as non-matching, or if the lock guard reports production_allowed=true or an N1/spherical-solver artifact exists."),
        "non_claims": ["worker evidence only; no gate verdict, no node status, no validation_status",
                       "does not adjudicate the C8 contest or accept/reject the protocol",
                       "does not edit any canonical artifact; only report.json under this task directory was written",
                       "does not release numerics_lock or authorise N1"],
        "instrument": "artifacts/worker-012/n0_successor_verify/verify_successor.py",
        "preregistration": "artifacts/worker-012/n0_successor_verify/PRE_REGISTRATION.md",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"verdict": verdict, "checks_total": len(checks),
                      "checks_failed": [c["id"] for c in checks if not c["ok"]],
                      "annotation_failures": [c["id"] for c in ann_fail],
                      "controls_failed": [c["id"] for c in controls if not c["ok"]],
                      "numeric_delta": {k: delta[k] for k in ("numeric_leaves_compared", "max_abs_difference", "differing_leaves", "excluded_wall_clock_leaves")},
                      "lock_guard": {"production_allowed": lg["production_allowed"], "verdict": lg["verdict"]},
                      "runtime_seconds": report["runtime_seconds"]}, indent=2))
    return 0 if not hard_failures else 2


if __name__ == "__main__":
    sys.exit(main())
