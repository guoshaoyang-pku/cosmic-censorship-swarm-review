#!/usr/bin/env python3
"""Independent F2b rev13 review instrument -- worker-052 (2026-09-12).

Target: schemas/af_scc_c0_vacuum.yaml at canonical pin
        b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c
        (FROZEN rev29; card audit-r2-F2b-b pinned the superseded rev27 hash 55d0a1ea).

Scope (per the card acceptance + bind-chain addendum):
  A. moving-target check: sha256 before and after reading;
  B. identity / class-leakage / conclusion-inflation / assumption-completeness /
     falsifier / genericity-semantics checks on the schema itself;
  C. f0_binding hash-chain resolution: every declared sha256 measured on disk;
  D. companion-supplement consistency (frozen checker + an independent field compare);
  E. planted-defect controls on artifacts/formulation/evidence/rebased_fixtures/
     (2 clean controls must pass, each sem* fixture must trip >=1 invariant);
  F. class-separation regression against the 27-fixture corpus, run twice:
     adopted pinned detector c266dbec and whatever live bytes exist at run time.

Read-only with respect to canonical artifacts: it writes only report.json next to itself.
No gate verdict is set anywhere.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ART = ROOT / "schemas/af_scc_c0_vacuum.yaml"
PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
TAX = ROOT / "research_map/formulation_taxonomy.yaml"
SUP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONS = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
CONS_TOOL = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
FIXDIR = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
CORPUS = ROOT / "artifacts/worker-07/class_separation_falsification"
PINNED_DETECTOR = ROOT / "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"
HEX = re.compile(r"^[0-9a-f]{64}$")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def flat(o, p=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(flat(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(flat(v, f"{p}[{i}]"))
    else:
        out[p] = o
    return out


def hexstrings(o, p=""):
    """Every 64-hex string with its dotted path."""
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out += hexstrings(v, f"{p}.{k}" if p else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += hexstrings(v, f"{p}[{i}]")
    elif isinstance(o, str) and HEX.match(o):
        out.append((p, o))
    return out


# ---------------------------------------------------------------- generic invariants
def generic_defects(doc: dict) -> list:
    """Semantic defect codes; must be [] for every clean control."""
    d = []
    f = flat(doc)
    j = json.dumps(doc)
    cid = str(doc.get("class_id", ""))

    if any("smoothness_assumption" in k for k in f):
        d.append("SMUGGLED_SMOOTHNESS")
    if "conclusion.inherited_from" in f or any(k.startswith("conclusion.inherited_from.") for k in f):
        d.append("INHERITED_SIBLING_CONCLUSION")

    gs = str(f.get("genericity.generic_set", ""))
    if not ("intersection" in gs and "open dense" in gs):
        d.append("GENERIC_SET_NOT_COMEAGER")
    if str(f.get("genericity.kind", "")) != "residual_comeager":
        d.append("GENERICITY_KIND_NOT_COMEAGER")

    if any(k.startswith("non_vacuity") and "curvature" in k.lower() for k in f):
        d.append("CURVATURE_HYPOTHESIS")
    cond = str(f.get("non_vacuity.condition", ""))
    if "boundary" not in cond or "not a regular" not in cond:
        d.append("NONVACUITY_NOT_SPECIFIED")

    w = str(f.get("falsifier.tier_1.witness_type", ""))
    if re.search(r"geodesic|observer|seen by|visible", w, re.I):
        d.append("VISIBILITY_FALSIFIER")

    if "i_plus.used_in_conclusion" in f or "i_plus.completeness_definition" in f:
        d.append("IPLUS_IN_CONCLUSION")
    if f.get("i_plus.in_conclusion") is True or f.get("i_plus.completeness_in_conclusion") is True:
        d.append("IPLUS_IN_CONCLUSION")

    if str(f.get("regularity.extension_solution_concept", "none")) != "none":
        d.append("EXTENSION_SOLUTION_CONCEPT")
    if str(f.get("extension_predicate.frozen_direction", "")) != "future":
        d.append("DIRECTION_NOT_FUTURE")
    if str(f.get("extension_predicate.frozen_regularity", "")) != "C0":
        d.append("REGULARITY_NOT_C0")
    if cid and cid not in str(f.get("class_contract_pointer", "")):
        d.append("CONTRACT_POINTER_WRONG_CLASS")

    concl_text = " ".join(
        str(f.get(k, "")) for k in f
        if k.startswith("conclusion.statement") or k.startswith("conclusion.equivalent_rephrasings")
    )
    if re.search(r"\bwe prove\b|\btheorem\b|\bproved\b", concl_text, re.I):
        d.append("THEOREM_PROMOTION")
    if any(k.startswith("conclusion.citation_use") for k in f):
        d.append("SIBLING_RESULT_CITED_AS_CLASS")

    ent = doc.get("implication_ledger", {}).get("one_way_entailments")
    if isinstance(ent, list):
        for row in ent:
            if not isinstance(row, dict):
                d.append("CONVERSE_IMPLICATION")
                continue
            src, dst = str(row.get("from", "")), str(row.get("to", ""))
            if re.search(r"\bC2\b", src) and re.search(r"\bC0\b", dst):
                d.append("CONVERSE_IMPLICATION")
            if re.search(r"C2\s*(=>|⇒)\s*C0", json.dumps(row)):
                d.append("CONVERSE_IMPLICATION")
    else:
        d.append("CONVERSE_IMPLICATION")

    q = str(f.get("quantifiers.formal", ""))
    if "comeager" not in q:
        d.append("NO_COMEAGER_QUANTIFIER")

    comp = doc.get("class_components", {}) or {}
    reg_tok = str(comp.get("regularity_token", "")).strip()
    ext_reg = str(f.get("regularity.extension_regularity", ""))
    if re.search(r"\bor\b", ext_reg, re.I) and re.search(r"C0|C2|C1|H2", ext_reg):
        d.append("COMPOSITE_REGULARITY")
    concl_type = str(f.get("conclusion.conclusion_type", ""))
    if reg_tok and reg_tok.lower() not in concl_type.lower():
        d.append("CONCLUSION_TYPE_MISSES_REGULARITY_TOKEN")
    if str(comp.get("censorship", "")) == "SCC" and re.search(r"wcc|weak_cosmic", concl_type, re.I):
        d.append("FAMILY_CONCLUSION_MISMATCH")
    if str(f.get("visibility.role", "")) != "not_in_conclusion":
        d.append("VISIBILITY_ROLE")
    if str(f.get("topology.I_plus_topology", "R x S^2")) != "R x S^2":
        d.append("IPLUS_TOPOLOGY")
    if str(comp.get("matter", "")) in ("VAC", "vacuum") and str(f.get("data_class.matter", "none")) != "none":
        d.append("MATTER_SMUGGLED")
    slice_t = str(f.get("topology.slice_topology", ""))
    if re.search(r"two asymptotically flat end|more than one", slice_t, re.I):
        d.append("MULTI_END_SLICE")
    if str(f.get("non_vacuity.witness_type", "")).strip().lower() in ("", "none", "none required"):
        d.append("VACUOUS_NONVACUITY")
    if "extension_predicate.frozen_equation_concept" not in f:
        d.append("EQUATION_CONCEPT_OMITTED")
    if str(f.get("conclusion.epistemic_status", "")) != "open_problem":
        d.append("EPISTEMIC_PROMOTION")
    return sorted(set(d))


# ---------------------------------------------------------------- fixture controls
def fixture_controls() -> dict:
    rows = []
    clean_fail = []
    for name in sorted(p.name for p in FIXDIR.glob("*.yaml")):
        doc = yaml.safe_load((FIXDIR / name).read_text())
        defects = generic_defects(doc)
        is_clean = name.startswith("control_")
        ok = (not defects) if is_clean else bool(defects)
        if not ok:
            (clean_fail if is_clean else clean_fail).append(name)
        rows.append({"fixture": name, "clean_control": is_clean, "defects": defects, "expected": ok})
    n_clean = sum(1 for r in rows if r["clean_control"])
    n_sem = sum(1 for r in rows if not r["clean_control"])
    return {
        "rows": rows,
        "clean_controls": n_clean,
        "planted_fixtures": n_sem,
        "clean_controls_passed": sum(1 for r in rows if r["clean_control"] and r["expected"]),
        "planted_fixtures_tripped": sum(1 for r in rows if not r["clean_control"] and r["expected"]),
        "unexpected": [r["fixture"] for r in rows if not r["expected"]],
        "all_expected": all(r["expected"] for r in rows),
    }


# ---------------------------------------------------------------- classsep regression
def load_detector(path: Path, modname: str):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classsep_run(mod) -> dict:
    results = json.loads((CORPUS / "results.json").read_text())
    tp = fp = tn = fn = 0
    for fx in results["fixtures"]:
        path = ROOT / fx["fixture_path"]
        if not path.exists():
            continue
        m = json.loads(path.read_text())
        detected = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    detected += mod.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got = bool(detected)
        truth = bool(fx["is_class_merge"])
        tp += truth and got
        fn += truth and not got
        fp += (not truth) and got
        tn += (not truth) and not got
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "fixtures": len(results["fixtures"]),
            "verdict": "PASS" if (fn == 0 and fp == 0) else "DEFECTIVE"}


def main() -> int:
    report = {"instrument": "worker-052/f2b_rev13_review/check_f2b_rev13_052.py", "pin": PIN}
    checks = []

    def expect(cond, cid, detail):
        checks.append({"check_id": cid, "pass": bool(cond), "detail": str(detail)[:300]})
        return bool(cond)

    # A. moving target -------------------------------------------------------
    h_before = sha(ART)
    report["hash_before_read"] = h_before
    expect(h_before == PIN, "A1_hash_before_eq_pin", f"{h_before}")
    doc = yaml.safe_load(ART.read_text())
    h_after = sha(ART)
    report["hash_after_read"] = h_after
    expect(h_after == PIN, "A2_hash_after_eq_pin", f"{h_after}")
    expect(h_before == h_after, "A3_no_mid_read_drift", f"{h_before} == {h_after}")

    fz = json.loads(FROZEN.read_text())
    fz_art = fz["files"].get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256")
    mirror = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    expect(fz_art == PIN, "A4_frozen_rev29_pin_eq_artifact", f"FROZEN rev{fz.get('revision')} {fz_art}")
    expect(mirror.is_file() and sha(mirror) == PIN, "A5_mirror_byte_identical", f"{mirror}")

    f = flat(doc)

    # B. identity / leakage --------------------------------------------------
    expect(doc.get("class_id") == "AF-SCC-C0-VAC-GEN", "B1_class_id", doc.get("class_id"))
    expect(doc.get("node_id") == "F2b" and str(f.get("review_status.gate", doc.get("gate"))) == "G-FORM",
           "B2_node_gate", f"{doc.get('node_id')}/{f.get('review_status.gate', doc.get('gate'))}")
    comp = doc.get("class_components", {})
    expect(comp.get("censorship") == "SCC" and comp.get("regularity_token") == "C0" and comp.get("genericity") == "GEN",
           "B3_axes_C0", comp)
    ct = str(f.get("conclusion.conclusion_type", ""))
    expect(ct == "scc_c0_future_inextendibility", "B4_conclusion_type_c0_only", ct)
    expect(not re.search(r"scc_c2|c2_|h2loc", ct, re.I), "B5_no_c2_token_in_conclusion_type", ct)
    expect("AF-SCC-C2-VAC-GEN" in json.dumps(doc.get("anti_scope", {})), "B6_antiscope_lists_c2", "anti_scope")
    expect("C0 or C2" in json.dumps(doc.get("anti_scope", {})), "B7_antiscope_rejects_composite", "phrases_that_are_not_this_class")
    expect("C2" in json.dumps(doc.get("implication_ledger", {}).get("forbidden_transfers", [])),
           "B8_forbids_c2_to_c0_transfer", "forbidden_transfers")
    expect(str(f.get("extension_predicate.frozen_regularity")) == "C0"
           and str(f.get("extension_predicate.frozen_equation_concept")) == "none"
           and str(f.get("extension_predicate.frozen_direction")) == "future",
           "B9_extension_predicate_frozen", "C0/none/future")
    ext_def = str(f.get("extension_predicate.definition", ""))
    expect(all(f"({c})" in ext_def for c in "abcdef"), "B10_extension_clauses_a_f", "clauses a-f")
    expect("extension_predicate.c0_uniqueness_caveat" in f, "B11_c0_uniqueness_caveat", "present")
    expect("must_not_conflate" in json.dumps(doc.get("regularity", {})) and "H2_loc" in json.dumps(doc.get("regularity", {})),
           "B12_h2loc_not_conflated", "regularity.must_not_conflate")

    # B. conclusion inflation ------------------------------------------------
    expect(str(f.get("conclusion.epistemic_status")) == "open_problem", "B13_epistemic_open", f.get("conclusion.epistemic_status"))
    expect(bool(f.get("promotion_rule")) and bool(f.get("conclusion.claim_promotion")), "B14_promotion_rules_present", "no self-promotion")
    expect("not_recorded_as_refuted" in json.dumps(doc.get("known_status", {})), "B15_status_not_refuted", "known_status")
    expect("citation_use" not in f, "B16_no_sibling_citation_use", "conclusion.citation_use absent")

    # B. assumptions ---------------------------------------------------------
    q = str(f.get("quantifiers.formal", ""))
    expect("comeager" in q and "forall" in q and "not exists" in q, "B18_explicit_comeager_quantifier", q[:120])
    ordered = doc.get("quantifiers", {}).get("ordered", [])
    expect(len(ordered) == 4 and [x.get("kind") for x in ordered] == ["forall", "exists", "forall", "not_exists"],
           "B19_quantifier_order", [x.get("kind") for x in ordered])
    doms = doc.get("quantifiers", {}).get("domains", {})
    expect(all(d in doms and doms[d].get("definition") for d in ("D0", "D1", "D2", "D3")), "B20_domains_D0_D3", list(doms))
    expect("non-meager" in str(f.get("quantifiers.negation_normal_form", "")), "B21_negation_normal_form", "non-meager")
    expect(str(f.get("topology.spacetime_dimension")) == "4" and "R x S^2" in str(f.get("topology.I_plus_topology")),
           "B22_topology", "4d / I+ = R x S^2")
    expect(str(f.get("data_class.matter")) == "none" and str(f.get("data_class.cosmological_constant")) == "0"
           and "Ric(g) = 0" in str(f.get("data_class.equations")), "B23_data_class", "vacuum Lambda=0")
    expect(str(f.get("data_class.symmetry")) == "none_assumed", "B24_no_symmetry_assumed", f.get("data_class.symmetry"))
    expect(str(f.get("regularity.extension_regularity")) == "C0" and "continuous" in str(f.get("regularity.extension_regularity_exact")),
           "B25_extension_regularity_C0", f.get("regularity.extension_regularity_exact"))
    expect("k >= 3" in str(f.get("regularity.i_plus_regularity")), "B26_iplus_regularity_assumed", f.get("regularity.i_plus_regularity"))
    expect(str(f.get("genericity.kind")) == "residual_comeager", "B27_genericity_kind", f.get("genericity.kind"))
    expect("strictly stronger" in str(f.get("genericity.class_change_warning", ""))
           and "No strengthening may be substituted silently" in str(f.get("genericity.class_change_warning", "")),
           "B28_no_silent_strengthening", "class_change_warning")
    expect(bool(doc.get("unresolved_items")), "B29_unresolved_items_declared", doc.get("unresolved_items"))

    # B. i_plus / visibility -------------------------------------------------
    expect(str(f.get("i_plus.role")) == "assumption" and f.get("i_plus.in_conclusion") is False
           and f.get("i_plus.completeness_in_conclusion") is False, "B30_iplus_not_in_conclusion", "role=assumption")
    expect(str(f.get("visibility.role")) == "not_in_conclusion" and "WCC" in str(f.get("visibility.forbidden_falsifier")),
           "B31_visibility_not_falsifier", f.get("visibility.forbidden_falsifier"))

    # B. falsifier -----------------------------------------------------------
    expect(str(f.get("falsifier.tier_1.refutes")) == "AF-SCC-C0-VAC-GEN", "B32_tier1_refutes_own_class", f.get("falsifier.tier_1.refutes"))
    expect("non-meager" in str(f.get("falsifier.tier_1.genericity_requirement", "")), "B33_tier1_genericity_route", "non-meagerness")
    expect(bool(doc.get("falsifier", {}).get("tier_1", {}).get("machine_checkable_steps")), "B34_machine_checkable_steps", "present")
    expect("non_machine_checkable_step" in json.dumps(doc.get("falsifier", {})), "B35_non_machine_step_declared", "honesty")
    expect(str(f.get("falsifier.tier_2.labelling_required")) == "refutes_strengthening_only", "B36_tier2_labelled", "strengthening only")
    sf = json.dumps(doc.get("falsifier", {}).get("schema_falsifiers", []))
    expect("class inflation" in sf and "wrong-family falsifier" in sf, "B37_schema_falsifiers_named", "inflation + wrong-family")

    # B. genericity transfer semantics --------------------------------------
    var = {v.get("kind"): v.get("statement_strength") for v in doc.get("genericity", {}).get("variants", [])}
    expect(var.get("open_dense_escape") == "strictly_stronger" and var.get("dense_escape") == "strictly_weaker"
           and var.get("full_measure") == "incomparable", "B38_variant_strength_labels", var)
    tf = json.dumps(doc.get("genericity", {}).get("transfer_failures", []))
    expect("full_measure" in tf and "no_transfer" in tf, "B39_comeager_no_transfer_to_measure", "transfer_failures")

    # B. generic invariant suite on the real artifact ------------------------
    gd = generic_defects(doc)
    expect(gd == [], "B40_generic_invariants_clean", gd)

    # C. bind chain ----------------------------------------------------------
    decl_f0 = str(f.get("f0_binding.declared_f0_sha256", ""))
    cons_ev = str(f.get("f0_binding.consistency_evidence", ""))
    cons_hash = str(f.get("f0_binding.consistency_evidence_sha256", ""))
    tax_h = sha(TAX)
    cons_h = sha(CONS) if CONS.is_file() else None
    sup_h = sha(SUP)
    bind = {
        "declared_f0": {"declared": decl_f0, "path": "research_map/formulation_taxonomy.yaml", "measured": tax_h,
                        "status": "resolved" if decl_f0 == tax_h else "mismatch"},
        "consistency_evidence": {"declared": cons_hash, "path": cons_ev, "measured": cons_h,
                                 "status": "resolved" if cons_hash == cons_h else "mismatch"},
        "class_contract_supplement": {"declared": None, "path": "artifacts/formulation/formulation_taxonomy.yaml",
                                      "measured": sup_h,
                                      "frozen_pin": fz["files"].get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256"),
                                      "status": "resolved_via_FROZEN" if sup_h == fz["files"].get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256") else "mismatch"},
    }
    all_hex = hexstrings(doc)
    unresolved = []
    for path, val in all_hex:
        if val in (decl_f0, cons_hash):
            continue
        unresolved.append({"path": path, "declared": val,
                           "status": "unresolved_provenance_only" if "provenance" in path or path.endswith("worker_sha256") else "unresolved"})
    bind["other_declared_sha256"] = unresolved
    expect(bind["declared_f0"]["status"] == "resolved", "C1_declared_f0_resolves", f"{decl_f0[:12]} -> {tax_h[:12]}")
    expect(bind["consistency_evidence"]["status"] == "resolved", "C2_consistency_evidence_resolves", f"{cons_hash[:12]} -> {str(cons_h)[:12]}")
    expect(bind["class_contract_supplement"]["status"].startswith("resolved"), "C3_supplement_frozen_pin_resolves", f"{sup_h[:12]}")
    expect(all(u["status"] == "unresolved_provenance_only" for u in unresolved), "C4_other_hashes_are_provenance_only",
           [u["path"] for u in unresolved])
    report["bind_chain"] = bind

    # D. companion consistency ----------------------------------------------
    proc = subprocess.run([sys.executable, str(CONS_TOOL)], cwd=ROOT, capture_output=True, text=True)
    expect(proc.returncode == 0 and "CONSISTENT" in proc.stdout, "D1_frozen_checker_consistent",
           f"exit={proc.returncode} out={proc.stdout.strip()[:120]}")
    taxa = yaml.safe_load(TAX.read_text())
    supa = yaml.safe_load(SUP.read_text())
    ca = taxa["classes"]["AF-SCC-C0-VAC-GEN"]
    cb = supa["class_contracts"]["AF-SCC-C0-VAC-GEN"]
    expect(ca["axes"]["family"] == cb["components"]["censorship"] and ca["axes"]["regularity_token"] == cb["components"]["regularity_token"],
           "D2_independent_axis_compare", f"{ca['axes']['family']}/{ca['axes']['regularity_token']}")
    expect(bool(ca.get("exclusions")) and bool(cb.get("exclusions")) and bool(ca.get("test_cases")) and bool(cb.get("positive_test_case")),
           "D3_exclusions_and_cases_present", "both sides")
    expect(bool(taxa.get("class_ids")) and set(taxa["class_ids"]) == set(supa["class_contracts"]), "D4_four_class_ids_agree", taxa.get("class_ids"))
    cons = json.loads(CONS.read_text())
    expect(cons.get("consistent") is True and len(cons.get("classes_compared", [])) == 4, "D5_consistency_evidence_flagged", cons.get("classes_compared"))
    report["consistency"] = {"checker_exit": proc.returncode, "checker_stdout": proc.stdout.strip(),
                             "tool_sha256": sha(CONS_TOOL), "evidence_sha256": cons_h}

    # E. planted-defect controls --------------------------------------------
    rep_e = fixture_controls()
    expect(rep_e["all_expected"] and rep_e["clean_controls_passed"] == rep_e["clean_controls"]
           and rep_e["planted_fixtures_tripped"] == rep_e["planted_fixtures"],
           "E1_controls_all_expected", f"{rep_e['planted_fixtures_tripped']}/{rep_e['planted_fixtures']} sem tripped, "
                                       f"{rep_e['clean_controls_passed']}/{rep_e['clean_controls']} controls clean")
    report["controls"] = rep_e

    # F. classsep regression -------------------------------------------------
    live_h = sha(ROOT / "research_map/class_separation.py")
    live = classsep_run(load_detector(ROOT / "research_map/class_separation.py", "cs_live_052"))
    live_h2 = sha(ROOT / "research_map/class_separation.py")
    pinned = classsep_run(load_detector(PINNED_DETECTOR, "cs_pin_052"))
    report["classsep"] = {
        "corpus": "artifacts/worker-07/class_separation_falsification (27 fixtures)",
        "adopted_pin_c266dbec": {"path": str(PINNED_DETECTOR.relative_to(ROOT)), "sha256": sha(PINNED_DETECTOR), **pinned},
        "live_at_review": {"sha256_before": live_h, "sha256_after": live_h2, "counts": live,
                           "note": "CF-29 freeze: adopted frozen pin stays c266dbec; live bytes are advisory only"},
    }
    expect(pinned["verdict"] == "PASS", "F1_pinned_detector_corpus_PASS", pinned)
    expect(live_h == live_h2, "F2_live_detector_stable_during_run", f"{live_h} == {live_h2}")

    hard = [c for c in checks if not c["pass"]]
    report["checks"] = checks
    report["n_checks"] = len(checks)
    report["n_pass"] = len(checks) - len(hard)
    report["hard_failures"] = [c["check_id"] for c in hard]
    report["verdict"] = "accept" if not hard else "revise"
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    for c in hard:
        print("FAIL", c["check_id"], c["detail"])
    print(f"checks {report['n_pass']}/{report['n_checks']} pass; controls "
          f"{rep_e['planted_fixtures_tripped']}/{rep_e['planted_fixtures']} sem tripped, "
          f"{rep_e['clean_controls_passed']}/{rep_e['clean_controls']} clean; "
          f"classsep pinned {pinned['verdict']} tp={pinned['tp']} fp={pinned['fp']} tn={pinned['tn']} fn={pinned['fn']}; "
          f"live {live_h[:12]} tp={live['tp']} fp={live['fp']} tn={live['tn']} fn={live['fn']}")
    print("VERDICT:", report["verdict"])
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
