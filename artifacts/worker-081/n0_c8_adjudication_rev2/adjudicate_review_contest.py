#!/usr/bin/env python3
"""W081-N0-C8-ADJ2-03: adjudicate the G-NUM rev-3 protocol review contest after evidence re-basing.

Question (named condition #1 of numerics/tests/n0_gate_proposal.json#b4192221):
    Do worker-067 finding F1 and worker-081 finding F1' -- both revise verdicts at
    numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313 -- remain blocking now that the certified
    spatial-order evidence has been replaced by numerics/protocol/n0_fixed_dt_certification.json
    #1677822ceb9c81e8 (fixed dt = 1e-4 on all four rungs, three schemes)?

Method (read-only; declared before running)
  P   re-measure the pinned inputs; abort with verdict input_moved on any mismatch.
  B   text/structural checks: section 3.4 fixed-dt clause present at the pinned protocol hash
      with line anchors; every certification row has dt == 1e-4; four distinct rungs; the
      four-rung certification requirement of section 3.2 is met.
  C   independent recomputation, from the certification's own raw rows and with this script's
      own arithmetic, of fit order, pair orders, pair half-range, least-squares standard error,
      residuals, delta_R5 = max(half-range, SE), monotonicity, band membership, and the three
      cross-scheme |dp| values against the R5 agreement rule.
  D   binding checks on the proposal: certified orders equal the certification orders; the
      certified_study hash equals the certification on disk; the superseded constant-CFL study
      is cited only under mixed-order/control/supersedes keys; the supersedes hash matches.
  E   falsifier evaluation for the two dissents: scan numerics/**/*.json for filed constant-dt
      ladders with >= 3 rungs and dt <= 1e-3 (this is the literal falsifier of W081's F1'
      review); check F1's predicate is now false (the certified claim no longer uses dt ~ h);
      check both dissent records are present in the proposal's protocol_review_state.
  F   guard evaluation: import numerics/gates.py read-only and report the protocol-review tally
      it computes at the current hash (accepts, dissents, contest).

Declared disposition rule (before measurement)
  If B, C, D all pass at the pinned hashes AND E finds a filed constant-dt study meeting the F1'
  falsifier predicate AND F shows a binding accept at the current hash, then both rev-3 dissents
  are DISCHARGED-BY-SUPERSESSION with respect to the evidence basis, and the standing audit
  accept is the operative protocol verdict.  Otherwise the dissents STAND and the failure is
  named.  This adjudication does not delete the dissents; it evaluates whether their factual
  predicate is cured.  No gate verdict, no node completion.

Falsifier (binds this adjudication)
  Re-measure the pinned inputs: if numerics/CONVERGENCE_PROTOCOL.md is not 1e6cdf04d7a24313 or
  numerics/protocol/n0_fixed_dt_certification.json is not 1677822ceb9c81e8, this adjudication
  does not bind.  It is falsified if any certification row has dt != 1e-4, if the recomputed
  statistics disagree with the certification beyond 1e-9 relative, if the certified claim still
  cites a constant-CFL study as its basis, or if no filed constant-dt (<= 1e-3) ladder with
  >= 3 rungs exists (then the F1' falsifier predicate is unmet and the dissent stands).

Usage: python3 artifacts/worker-081/n0_c8_adjudication_rev2/adjudicate_review_contest.py
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "adjudication.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "numerics"))

PIN = {
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
    "numerics/protocol/n0_fixed_dt_certification.json": "1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920",
    "numerics/protocol/n0_fixed_dt_certification.py": "3c7c9087838446046d7462f92c9ffdd9ff137cc6a07ac63bf41e7db90dfbf145",
    "numerics/tests/n0_gate_proposal.json": "b4192221ff7d96dbb61ce37fa667e1a59b7b290b8ca34f77e7674c03ca5ba2e3",
    "numerics/gates.py": "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
    "numerics/tests/flat_wave_replication.py": "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422",
    "numerics/tests/n0_order_4rung.json": "c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a",
    "numerics/protocol/temporal_subdominance_control.json": "334f5b71e0d53ab6ed1f3b7133abca541a36dafc9a5cfb4f62f0655839dd964b",
}
SCHEMES = ("lffd", "cnfd", "cnfem")
DR4 = [0.2, 0.1, 0.05, 0.025]
DT_EXACT = 1e-4
P_TOL = 0.3
R5_FLOOR = 0.25
REL_TOL = 1e-9
TASK = {"task_id": "W081-N0-C8-ADJ2-03", "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"], "gate": "G-NUM", "actor": "worker-081",
        "instance": "worker-081-20260912T002948-968807"}
PRIOR_W081_REVIEW = "w081-2026-09-12T00:29:19+0800-f1-review"
PRIOR_W067_REVIEW = "w067-review-gnum-protocol-r3-20260912T002256"
AUDIT_ACCEPT = "audit-review-gnum-protocol-final-20260912T0027"


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def relerr(a, b):
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b), 1e-300)


def recompute(rows):
    import numpy as np

    drs = [r["dr"] for r in rows]
    errs = [r["l2_error"] for r in rows]
    x, y = np.log(np.asarray(drs, float)), np.log(np.asarray(errs, float))
    slope, cov = np.polyfit(x, y, 1, cov=True)
    residuals = y - (slope[0] * x + slope[1])
    se = float(math.sqrt(float(cov[0, 0])))
    pairs = [float(math.log(errs[i] / errs[i + 1]) / math.log(drs[i] / drs[i + 1]))
             for i in range(len(errs) - 1)]
    half = (max(pairs) - min(pairs)) / 2.0
    return {"fit_order": float(slope[0]), "least_squares_se": se, "pair_orders": pairs,
            "pair_half_range": float(half), "delta_R5": float(max(se, half)),
            "lsq_residuals": [float(v) for v in residuals],
            "monotone": all(errs[i + 1] < errs[i] for i in range(len(errs) - 1)),
            "within_band": bool(abs(float(slope[0]) - 2.0) <= P_TOL)}


def find_constant_dt_ladders(root: Path):
    """Scan numerics/**/*.json for row lists with a single constant dt and >= 3 distinct dr."""
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list) and len(node) >= 3 and all(isinstance(r, dict) for r in node):
            if all("dr" in r and "dt" in r for r in node):
                dts = {round(float(r["dt"]), 15) for r in node}
                drs = [float(r["dr"]) for r in node]
                if len(dts) == 1 and len(set(drs)) == len(drs) and len(drs) >= 3:
                    dt = dts.pop()
                    if dt <= 1e-3:
                        found.append({"path": path, "dt": dt, "n_rungs": len(drs),
                                      "dr_values": drs})

    for p in sorted(root.rglob("*.json")):
        try:
            doc = json.loads(p.read_text())
        except Exception:
            continue
        before = len(found)
        walk(doc, "")
        for rec in found[before:]:
            rec["file"] = str(p.relative_to(root))
    return found


def hash_paths_in(doc, needle):
    """All JSON paths whose serialized value contains needle, with the nearest dict context."""
    hits = []

    def walk(node, path, ctx):
        if isinstance(node, dict):
            ctx = json.dumps(node)[:4000]
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k, ctx)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", ctx)
        else:
            if needle in str(node):
                hits.append({"path": path, "context": ctx})

    walk(doc, "", json.dumps(doc)[:4000])
    return hits


def main() -> int:
    started = time.time()
    rep = {"schema": "worker-081/n0-review-contest-adjudication/v1", **TASK,
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "host": {"python": sys.version.split()[0], "platform": platform.platform()},
           "prior_w081_review_event": PRIOR_W081_REVIEW,
           "prior_w067_review_event": PRIOR_W067_REVIEW,
           "audit_accept_event": AUDIT_ACCEPT,
           "declared_disposition_rule": ("B,C,D pass at pinned hashes AND a filed constant-dt "
                                         "(<=1e-3, >=3 rungs) study exists AND a binding accept "
                                         "exists at the current hash -> both rev-3 dissents are "
                                         "discharged-by-supersession; else they stand."),
           "not_claimed": [
               "no gate verdict, no node completion; numerics_lock stays LOCKED",
               "no numerical re-run of the certification ladder (that is a separate replication task)",
               "no deletion or rewriting of any review record; the dissents remain on the record",
               "no physics claim; flat-space discretisation evidence only"]}

    # P pins
    rep["input_pins_start"] = {rel: {"sha256": sha256(ROOT / rel), "expected": exp,
                                     "match": sha256(ROOT / rel) == exp} for rel, exp in PIN.items()}
    moved = [rel for rel, v in rep["input_pins_start"].items() if not v["match"]]
    rep["input_pins_start_ok"] = not moved
    if moved:
        rep["verdict"] = {"status": "input_moved", "moved": moved,
                          "note": "aborted before checks; adjudication does not bind"}
        OUT.write_text(json.dumps(rep, indent=1, sort_keys=True))
        print("ABORT: pinned inputs moved:", moved)
        return 3

    protocol_txt = (ROOT / "numerics/CONVERGENCE_PROTOCOL.md").read_text().splitlines()
    cert = json.loads((ROOT / "numerics/protocol/n0_fixed_dt_certification.json").read_text())
    prop = json.loads((ROOT / "numerics/tests/n0_gate_proposal.json").read_text())

    # B text/structural
    sec34 = [i + 1 for i, l in enumerate(protocol_txt) if "Temporal/spatial separation" in l]
    line34 = protocol_txt[sec34[0] - 1: sec34[0] + 2] if sec34 else []
    rep["check_B_protocol_and_structure"] = {
        "B1_section_3.4_line": sec34[0] if sec34 else None,
        "B1_text": line34,
        "B1_fixed_dt_clause": bool(sec34 and any("1e-4" in l for l in line34)),
        "B1_never_spatial_clause": bool(sec34 and any("never quoted as spatial" in l for l in line34)),
        "B2_dt_exact_per_row": {s: all(abs(float(r["dt"]) - DT_EXACT) <= 1e-18
                                       for r in cert["schemes"][s]["fixed_dt_certification"]["rows"])
                                for s in SCHEMES},
        "B2_rungs_per_scheme": {s: [float(r["dr"]) for r in cert["schemes"][s]["fixed_dt_certification"]["rows"]]
                                for s in SCHEMES},
        "B2_steps_per_row": {s: sorted({int(r["steps"]) for r in cert["schemes"][s]["fixed_dt_certification"]["rows"]})
                             for s in SCHEMES},
        "B3_four_rungs": all(len(cert["schemes"][s]["fixed_dt_certification"]["rows"]) >= 4 for s in SCHEMES),
    }
    rep["check_B_protocol_and_structure"]["B_pass"] = bool(
        rep["check_B_protocol_and_structure"]["B1_fixed_dt_clause"]
        and rep["check_B_protocol_and_structure"]["B1_never_spatial_clause"]
        and all(rep["check_B_protocol_and_structure"]["B2_dt_exact_per_row"].values())
        and all(v == [0.2, 0.1, 0.05, 0.025] for v in rep["check_B_protocol_and_structure"]["B2_rungs_per_scheme"].values())
        and rep["check_B_protocol_and_structure"]["B3_four_rungs"])

    # C independent arithmetic
    C = {}
    for s in SCHEMES:
        fd = cert["schemes"][s]["fixed_dt_certification"]
        rec = recompute(fd["rows"])
        fields = ["fit_order", "least_squares_se", "pair_half_range", "delta_R5"]
        C[s] = {"recomputed": rec,
                "filed": {k: fd[k] for k in fields},
                "rel_err": {k: relerr(rec[k], float(fd[k])) for k in fields},
                "pairs_match": all(relerr(a, b) <= REL_TOL for a, b in zip(rec["pair_orders"], fd["pair_orders"])),
                "residuals_match": all(relerr(a, b) <= 1e-6 for a, b in zip(rec["lsq_residuals"], fd["lsq_residuals"])),
                "monotone_match": rec["monotone"] == bool(fd["monotone"]),
                "within_band_match": rec["within_band"] == bool(fd["within_band"]),
                "delta_rule_ok": abs(rec["delta_R5"] - max(rec["pair_half_range"], rec["least_squares_se"])) < 1e-15}
        C[s]["stats_pass"] = bool(max(C[s]["rel_err"].values()) <= REL_TOL and C[s]["pairs_match"]
                                  and C[s]["residuals_match"] and C[s]["monotone_match"]
                                  and C[s]["within_band_match"] and C[s]["delta_rule_ok"])
    # cross-scheme R5
    pairs = []
    for i, a in enumerate(SCHEMES):
        for b in SCHEMES[i + 1:]:
            da, db = C[a]["recomputed"]["delta_R5"], C[b]["recomputed"]["delta_R5"]
            bound = max(R5_FLOOR, math.sqrt(da * da + db * db))
            diff = abs(C[a]["recomputed"]["fit_order"] - C[b]["recomputed"]["fit_order"])
            pairs.append({"pair": f"{a} vs {b}", "abs_order_diff": diff, "r5_bound": bound,
                          "agree": bool(diff <= bound)})
    filed_max = float(cert["cross_scheme_R5"]["max_pairwise_abs_diff"])
    computed_max = max(p["abs_order_diff"] for p in pairs)
    rep["check_C_independent_arithmetic"] = {
        "per_scheme": C,
        "cross_scheme_pairs": pairs,
        "filed_max_pairwise_abs_diff": filed_max,
        "computed_max_pairwise_abs_diff": computed_max,
        "max_diff_rel_err": relerr(computed_max, filed_max),
        "all_agree": all(p["agree"] for p in pairs),
        "C_pass": bool(all(C[s]["stats_pass"] for s in SCHEMES) and all(p["agree"] for p in pairs)
                       and relerr(computed_max, filed_max) <= 1e-9)}

    # D proposal binding
    claim_orders = prop["certified_order_claim"]["orders_4rung_certified_fixed_dt_1e-4"]
    def ref_binds(ref, rel, full):
        """A `path#hashprefix` ref binds iff the path equals rel and the prefix matches full."""
        if "#" not in ref:
            return False
        p, h = ref.split("#", 1)
        return p == rel and full.startswith(h)

    checks = {
        "D1_orders_match_certification": all(
            relerr(float(claim_orders[s]), C[s]["recomputed"]["fit_order"]) <= REL_TOL for s in SCHEMES),
        "D2_certified_study_hash_matches": ref_binds(
            prop["certified_order_claim"]["certified_study"],
            "numerics/protocol/n0_fixed_dt_certification.json",
            PIN["numerics/protocol/n0_fixed_dt_certification.json"]),
        "D3_certified_driver_hash_matches": ref_binds(
            prop["certified_order_claim"].get("certified_driver", ""),
            "numerics/protocol/n0_fixed_dt_certification.py",
            PIN["numerics/protocol/n0_fixed_dt_certification.py"]),
        "D4_constant_cfl_cited_only_as_control": None,
    }
    cfl_refs = hash_paths_in(prop, PIN["numerics/tests/n0_order_4rung.json"][:16])
    markers = ("mixed", "control", "relabel", "supersed", "also_available", "not_admissible", "previous")
    bad_paths = [h["path"] for h in cfl_refs
                 if not any(m in (h["path"] + " " + h["context"]).lower() for m in markers)]
    checks["D4_constant_cfl_cited_only_as_control"] = bad_paths == []
    checks["D4_constant_cfl_ref_paths"] = [h["path"] for h in cfl_refs]
    checks["D4_unlabelled_paths"] = bad_paths
    checks["D5_supersedes_block_present"] = "supersedes" in json.dumps(prop).lower()
    rep["check_D_proposal_binding"] = {**checks,
                                       "D_pass": bool(checks["D1_orders_match_certification"]
                                                      and checks["D2_certified_study_hash_matches"]
                                                      and checks["D3_certified_driver_hash_matches"]
                                                      and checks["D4_constant_cfl_cited_only_as_control"])}

    # E falsifier evaluation
    ladders = find_constant_dt_ladders(ROOT / "numerics")
    f1_predicate = not all(abs(float(r["dt"]) - DT_EXACT) <= 1e-18
                           for s in SCHEMES
                           for r in cert["schemes"][s]["fixed_dt_certification"]["rows"])
    rep["check_E_dissent_falsifier"] = {
        "E1_filed_constant_dt_ladders": ladders,
        "E1_count": len(ladders),
        "E1_predicate_met": len(ladders) > 0,
        "E1_with_four_rungs": [l for l in ladders if l["n_rungs"] >= 4],
        "E2_F1_predicate_still_true": f1_predicate,
        "E2_note": ("F1's premise was 'the certified claim uses dt ~ h'; every certified row has "
                    "dt = 1e-4, so the premise is false for the current certification."
                    if not f1_predicate else "a certified row still has dt != 1e-4"),
        "E3_proposal_records_both_dissents": sorted(
            d.get("event_id") for d in prop["protocol_review_state"]["dissents_at_this_hash"]) if
            "protocol_review_state" in prop else None,
        "E4_prior_w081_falsifier_condition_met": len(ladders) > 0,
    }
    rep["check_E_dissent_falsifier"]["E_pass"] = bool(len(ladders) > 0 and not f1_predicate)

    # F guard tally (read-only)
    import gates as G  # numerics/gates.py
    events = G.load_event_stream(ROOT)
    protocol_sha = sha256(ROOT / "numerics/CONVERGENCE_PROTOCOL.md")
    tally = G._protocol_review(events, protocol_sha)
    rep["check_F_guard_tally"] = {
        "protocol_sha256_measured": protocol_sha,
        "reviewed": tally["reviewed"],
        "accepting_reviews": tally["accepting_reviews"],
        "dissenting_reviews": tally["dissenting_reviews"],
        "contest": tally["contest"],
        "advisory_reviews_at_other_hashes": tally["advisory_reviews_at_other_hashes"],
        "F_note": ("the guard counts every review event; a later accept from a dissent author does "
                   "not mechanically rescind the earlier revise, so the contest flag needs an "
                   "explicit controller disposition or a guard rescission rule"),
    }

    # V verdict
    structural = bool(rep["check_B_protocol_and_structure"]["B_pass"]
                      and rep["check_C_independent_arithmetic"]["C_pass"]
                      and rep["check_D_proposal_binding"]["D_pass"])
    falsifier_met = bool(rep["check_E_dissent_falsifier"]["E_pass"])
    accept_present = bool(tally["reviewed"])
    rep["verdict"] = {
        "status": "adjudicated",
        "structural_checks_pass": structural,
        "f1prime_falsifier_predicate_met": falsifier_met,
        "binding_accept_at_current_hash": accept_present,
        "disposition": ("F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION" if (structural and falsifier_met
                        and accept_present) else "DISSENTS_STAND"),
        "scope": ("worker-level adjudication of the review contest for controller/Astra use; does "
                  "not set the gate, does not complete N0, does not alter any review record"),
    }
    rep["verdict"]["blocks_gate_pass"] = not (structural and falsifier_met and accept_present)
    rep["input_pins_end"] = {rel: sha256(ROOT / rel) for rel in PIN}
    rep["input_pins_end_ok"] = all(rep["input_pins_end"][rel] == v["sha256"]
                                   for rel, v in rep["input_pins_start"].items())
    rep["runtime_s"] = round(time.time() - started, 2)
    OUT.write_text(json.dumps(rep, indent=1, sort_keys=True))

    print(f"verdict={rep['verdict']['disposition']} structural={structural} "
          f"falsifier_met={falsifier_met} accept={accept_present} pins_end={rep['input_pins_end_ok']} "
          f"runtime={rep['runtime_s']}s")
    print(f"  B={rep['check_B_protocol_and_structure']['B_pass']} "
          f"C={rep['check_C_independent_arithmetic']['C_pass']} "
          f"D={rep['check_D_proposal_binding']['D_pass']} E_ladders={len(ladders)}")
    print(f"  guard: accepts={tally['accepting_reviews']} dissents={[d['event_id'] for d in tally['dissenting_reviews']]} contest={tally['contest']}")
    return 0 if rep["input_pins_end_ok"] and not rep["verdict"]["blocks_gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
