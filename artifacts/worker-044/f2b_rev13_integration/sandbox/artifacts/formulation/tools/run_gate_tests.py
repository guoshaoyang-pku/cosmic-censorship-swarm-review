#!/usr/bin/env python3
"""Acceptance harness for the canonical class-schema gate.

Decides three things by command:
  1. NULL CONTROLS: the 3 canonical schemas and 3 harmless perturbations of them PASS.
     (A gate that rejects everything is not a gate; per HANDOFF "run the null first".)
  2. MUTANTS: 22 targeted mutations each FAIL with their expected rule id.
  3. REPHRASED PROBES: semantic leaks with no forbidden token. These are RECORDED, not
     asserted; each miss is a measured blind spot handed to the semantic-corpus task.

Writes artifacts/formulation/evidence/gate_test_report.{json,txt}.
Usage: python3 run_gate_tests.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
FORM = ROOT / "artifacts" / "formulation"
GATE = FORM / "tools" / "check_class_schema.py"
FIX = FORM / "fixtures"
CANON = {
    "AF-WCC-VAC-GEN": FORM / "schemas" / "af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": FORM / "schemas" / "af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": FORM / "schemas" / "af_scc_c0_vacuum.yaml",
}


def load(p):
    return yaml.safe_load(Path(p).read_text())


def dump(doc, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(yaml.safe_dump(doc, sort_keys=False, width=110))


def run_gate(p):
    r = subprocess.run([sys.executable, str(GATE), "--json", str(p)],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"verdict": "error", "failed_rules": [], "stderr": r.stderr[-500:]}


def mutation(name, src, expected_rule, fn):
    return {"name": name, "src": src, "expected_rule": expected_rule, "fn": fn}


def build_mutations():
    M = []
    M.append(mutation("m01_drop_quantifiers", "AF-WCC-VAC-GEN", "R03",
                      lambda d: d.pop("quantifiers", None)))
    M.append(mutation("m02_unresolved_domain", "AF-WCC-VAC-GEN", "R03",
                      lambda d: d["quantifiers"]["ordered"][0].__setitem__("domain_id", "D99")))
    M.append(mutation("m03_vague_domain", "AF-WCC-VAC-GEN", "R03",
                      lambda d: d["quantifiers"]["domains"].__setitem__("D0", {"definition": "suitable data"})))
    M.append(mutation("m04_topology_allows_closed", "AF-WCC-VAC-GEN", "R04",
                      lambda d: (d["topology"].__setitem__("slice_topology", "closed 3-manifold"),
                                 d["topology"].__setitem__("forbidden", []))))
    M.append(mutation("m05_i_plus_topology_wrong", "AF-WCC-VAC-GEN", "R04",
                      lambda d: d["topology"].__setitem__("I_plus_topology", "S^3")))
    M.append(mutation("m06_genericity_none", "AF-WCC-VAC-GEN", "R07",
                      lambda d: (d["genericity"].__setitem__("kind", "none"),
                                 d["genericity"].pop("excluded_set", None))))
    M.append(mutation("m07_no_transfer_failures", "AF-WCC-VAC-GEN", "R07",
                      lambda d: d["genericity"].__setitem__("transfer_failures", [])))
    M.append(mutation("m08_scc_i_plus_conclusion", "AF-SCC-C2-VAC-GEN", "R09",
                      lambda d: d.__setitem__("i_plus", {"role": "conclusion", "in_conclusion": True,
                                                         "completeness_definition": "every generator is complete"})))
    M.append(mutation("m09_scc_visibility_conclusion", "AF-SCC-C0-VAC-GEN", "R10",
                      lambda d: d.__setitem__("visibility", {"role": "conclusion",
                                                             "predicate_name": "visible_singularity_from_I_plus",
                                                             "definition": "as in the WCC class",
                                                             "negation_conclusion": "no visible singularity"})))
    M.append(mutation("m10_conclusion_type_mismatch", "AF-WCC-VAC-GEN", "R11",
                      lambda d: d["conclusion"].__setitem__("conclusion_type", "scc_c0_future_inextendibility")))
    M.append(mutation("m11_epistemic_theorem", "AF-SCC-C2-VAC-GEN", "R11",
                      lambda d: d["conclusion"].__setitem__("epistemic_status", "theorem")))
    M.append(mutation("m12_composite_regularity", "AF-SCC-C2-VAC-GEN", "R13",
                      lambda d: d["regularity"].__setitem__("extension_regularity", "C0 or C2")))
    M.append(mutation("m13_foreign_conclusion_in_wcc", "AF-WCC-VAC-GEN", "R12",
                      lambda d: d["conclusion"].__setitem__("statement_formal",
                                                            "the maximal development is future-inextendible as a C0 Lorentzian manifold")))
    M.append(mutation("m14_missing_extension_class", "AF-SCC-C0-VAC-GEN", "R06",
                      lambda d: d["regularity"].__setitem__("extension_regularity", None)))
    M.append(mutation("m15_scc_no_nonvacuity", "AF-SCC-C2-VAC-GEN", "R08",
                      lambda d: d.pop("non_vacuity", None)))
    M.append(mutation("m16_verified_without_sources", "AF-SCC-C2-VAC-GEN", "R15",
                      lambda d: (d["provenance"].__setitem__("citation_status", "verified"),
                                 d["provenance"].__setitem__("sources", []))))
    M.append(mutation("m17_no_implication_ledger", "AF-SCC-C0-VAC-GEN", "R16",
                      lambda d: d.pop("implication_ledger", None)))
    M.append(mutation("m18_wcc_extension_regularity", "AF-WCC-VAC-GEN", "R06",
                      lambda d: (d["regularity"].__setitem__("extension_regularity", "C2"),
                                 d["regularity"].__setitem__("extension_solution_concept", "classical_ricci"))))
    M.append(mutation("m19_falsifier_wrong_family", "AF-SCC-C2-VAC-GEN", "R14",
                      lambda d: d["falsifier"]["tier_1"].__setitem__("witness_type",
                                                                     "a visible incomplete causal geodesic")))
    M.append(mutation("m20_missing_constraints", "AF-WCC-VAC-GEN", "R05",
                      lambda d: d["data_class"].__setitem__("constraints", {})))
    M.append(mutation("m21_no_visibility_wcc", "AF-WCC-VAC-GEN", "R10",
                      lambda d: d.pop("visibility", None)))
    M.append(mutation("m22_falsifier_unlabelled", "AF-WCC-VAC-GEN", "R14",
                      lambda d: d["falsifier"]["tier_2"].__setitem__("labelling_required", "")))
    # mutants contributed by the R3 independent review (2026-09-11T23:40) - 5/8 of its novel
    # mutants escaped the previous gate revision; these four are now asserted.
    M.append(mutation("m23_scc_ledger_converse", "AF-SCC-C2-VAC-GEN", "R16",
                      lambda d: d["implication_ledger"]["one_way_entailments"].append(
                          {"from": "no proper future C2 extension", "to": "no proper future C0 extension",
                           "relation": "entails", "reason": "converse claimed", "status": "elementary"})))
    M.append(mutation("m24_scc_i_plus_completeness", "AF-SCC-C0-VAC-GEN", "R09",
                      lambda d: d["i_plus"].__setitem__("completeness_definition",
                                                        "every null generator of I+ is complete")))
    M.append(mutation("m25_source_establishes_conclusion", "AF-SCC-C2-VAC-GEN", "R15",
                      lambda d: d["provenance"]["sources"].append(
                          {"concept": "a paper that establishes the class conclusion", "identifier": "placeholder",
                           "status": "unresolved"})))
    M.append(mutation("m31_unknown_top_level_key", "AF-WCC-VAC-GEN", "R22",
                      lambda d: d.__setitem__("experiment_note", {"oops": True})))
    M.append(mutation("m29_malformed_not_mapping", "AF-WCC-VAC-GEN", "R01",
                      lambda d: None))  # special-cased below: writes a YAML list
    M.append(mutation("m30_empty_document", "AF-WCC-VAC-GEN", "R01",
                      lambda d: d.clear()))
    M.append(mutation("m28_prose_converse_reversed", "AF-SCC-C0-VAC-GEN", "R16",
                      lambda d: d["non_vacuity"].__setitem__(
                          "condition", "C0-inextendibility follows from the C2 result for every datum in the generic set")))
    M.append(mutation("m27_prose_converse_c2_c0", "AF-SCC-C0-VAC-GEN", "R16",
                      lambda d: d["non_vacuity"].__setitem__(
                          "c0_specific_note", "a C2-inextendibility proof subsumes this class's conclusion")))
    M.append(mutation("m26_wcc_prose_in_scc_nonvacuity", "AF-SCC-C2-VAC-GEN", "R12",
                      lambda d: d["non_vacuity"].__setitem__(
                          "condition", "the development must be visible from future null infinity in the asymptotic-predictability sense")))
    return M


def rephrased_probes():
    return [
        {"name": "p01_scc_schema_wcc_meaning", "src": "AF-SCC-C2-VAC-GEN",
         "text": "no observer who escapes to infinity can be shielded from the breakdown of predictability by generic asymptotically flat vacuum data",
         "fn": lambda d, t: d["conclusion"].__setitem__("statement_natural_language", t),
         "leak_family": "WCC"},
        {"name": "p02_wcc_schema_scc_meaning", "src": "AF-WCC-VAC-GEN",
         "text": "generic asymptotically flat vacuum data have a maximal development that cannot be continued to a larger solution of the same equations",
         "fn": lambda d, t: d["conclusion"].__setitem__("statement_natural_language", t),
         "leak_family": "SCC"},
        {"name": "p03_c2_schema_c0_meaning", "src": "AF-SCC-C2-VAC-GEN",
         "text": "there is no proper continuation whose metric is merely continuous across the boundary of the development",
         "fn": lambda d, t: d["conclusion"].__setitem__("statement_formal", t),
         "leak_family": "C0-regularity"},
        {"name": "p04_wcc_genericity_weakened", "src": "AF-WCC-VAC-GEN",
         "text": "an open dense set of data with the property that the development has complete future null infinity",
         "fn": lambda d, t: d["genericity"].__setitem__("generic_set", t),
         "leak_family": "genericity-transfer"},
        {"name": "p05_scc_i_plus_completeness_rephrased", "src": "AF-SCC-C0-VAC-GEN",
         "text": "every light ray that reaches the far future is defined for all values of its parameter",
         "fn": lambda d, t: d["i_plus"].__setitem__("definition", t),
         "leak_family": "I+-completeness-in-SCC"},
    ]


def parse_and_label_checks():
    """Self-application: every formulation artifact must parse, and no artifact may carry a
    bare composite regularity label. Added after a bad edit briefly produced invalid YAML."""
    import re
    artifacts = [FORM / "formulation_taxonomy.yaml", FORM / "rule_spec.json"] + list(CANON.values())
    parse_ok, composite_hits = {}, []
    for p in artifacts:
        try:
            doc = yaml.safe_load(p.read_text())
            parse_ok[str(p.relative_to(ROOT))] = doc is not None
        except Exception as e:  # noqa: BLE001
            parse_ok[str(p.relative_to(ROOT))] = f"PARSE_ERROR: {type(e).__name__}"
    comp_or = re.compile(r"(C0|C2)\s+(or|and)\s+(C0|C2)", re.I)
    comp_slash = re.compile(r"(C0|C2)\s*/\s*(C0|C2)", re.I)
    neg = re.compile(r"(never|forbidden|no |not |cannot|merge|split|separate|distinct|ban|two files|registry|outside|anti_scope|either)", re.I)
    bare = re.compile(r"^\W*(C0|C2)\s*(?:or|and|/)\s*(C0|C2)\W*$", re.I)

    exempt = re.compile(
        r"^(forbidden|must_not|anti_scope|not_|excluded|exclusions|variants|phrases_that_are_not|why_|reason$|"
        r"sibling_|derived_|no_|never_|schema_falsifiers$|vacuity_falsifier$|class_change_warning$|"
        r"composite_regularity_ban$|non_goals$|forbidden_strengthenings$|forbidden_weakenings$|"
        r"forbidden_transfers$|repair|remediation_notes$)", re.I)

    def walk(n, path="$", key=None):
        if key is not None and exempt.match(str(key)):
            return
        if isinstance(n, dict):
            for k, v in n.items():
                walk(v, f"{path}.{k}", k)
        elif isinstance(n, list):
            for i, v in enumerate(n):
                walk(v, f"{path}[{i}]", key)
        elif isinstance(n, str):
            if bare.match(n):
                composite_hits.append(f"{path}: BARE {n[:50]}")
            elif (comp_or.search(n) or comp_slash.search(n)) and not neg.search(n):
                composite_hits.append(f"{path}: {n[:80]}")

    for p in artifacts:
        try:
            walk(yaml.safe_load(p.read_text()))
        except Exception:  # noqa: BLE001
            pass
    return {"artifact_parse": parse_ok, "composite_label_hits": composite_hits,
            "clean": all(v is True for v in parse_ok.values()) and not composite_hits}


def main():
    import shutil
    if FIX.exists():
        shutil.rmtree(FIX)  # stale mutant/fixture clones from earlier revisions must not survive
    docs = {k: load(v) for k, v in CANON.items()}
    canon_hash = {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in CANON.items()}
    report = {"canonical": {}, "null_controls": [], "mutants": [], "rephrased_probes": [],
              "canonical_sha256": canon_hash, "self_application": parse_and_label_checks()}
    # 1. canonical
    for k, p in CANON.items():
        rep = run_gate(p)
        report["canonical"][k] = rep
    # 2. null controls
    controls = [
        ("null_unchanged", lambda d: None),
        # R22 exists, so a bare extra key is a REJECTION by design; the harmless control must use
        # the documented escape hatch `extensions:` instead.
        ("null_extra_key", lambda d: d.__setitem__("extensions", {"experiment_note": {"harmless": True}})),
        ("null_reordered", lambda d: d.update({k: d[k] for k in reversed(list(d.keys()))})),
        # control for the new R09 negation-aware scan: a negated completeness mention must PASS
        ("null_scc_completeness_negated", lambda d: d["i_plus"].__setitem__(
            "definition", "no completeness of I+ is asserted anywhere in this class")),
    ]
    for name, fn in controls:
        for k in (("AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN") if name not in ("null_reordered", "null_scc_completeness_negated") else ("AF-SCC-C2-VAC-GEN",)):
            d = copy.deepcopy(docs[k]); fn(d)
            p = FIX / "controls" / f"{name}__{k}.yaml"; dump(d, p)
            rep = run_gate(p)
            report["null_controls"].append({"name": name, "class": k, **rep})
    # 3. mutants
    for m in build_mutations():
        d = copy.deepcopy(docs[m["src"]]); m["fn"](d)
        p = FIX / "negative" / f"{m['name']}.yaml"
        if m["name"] == "m29_malformed_not_mapping":
            p.write_text("- this is a list, not a class-schema mapping\n- second item\n")
        else:
            dump(d, p)
        rep = run_gate(p)
        caught = m["expected_rule"] in rep.get("failed_rules", [])
        report["mutants"].append({"name": m["name"], "src": m["src"], "expected_rule": m["expected_rule"],
                                  "caught_with_expected_rule": caught,
                                  "failed_rules": rep.get("failed_rules", []), "verdict": rep.get("verdict")})
    # 4. rephrased probes (recorded, not asserted)
    for pr in rephrased_probes():
        d = copy.deepcopy(docs[pr["src"]]); pr["fn"](d, pr["text"])
        p = FIX / "rephrased" / f"{pr['name']}.yaml"; dump(d, p)
        rep = run_gate(p)
        report["rephrased_probes"].append({"name": pr["name"], "leak_family": pr["leak_family"],
                                           "caught": rep.get("verdict") == "fail",
                                           "failed_rules": rep.get("failed_rules", [])})
    ok = (all(v.get("verdict") == "pass" for v in report["canonical"].values())
          and all(c.get("verdict") == "pass" for c in report["null_controls"])
          and all(m["caught_with_expected_rule"] for m in report["mutants"])
          and report["self_application"]["clean"])
    report["verdict"] = "PASS" if ok else "FAIL"
    report["counts"] = {"canonical_pass": sum(v.get("verdict") == "pass" for v in report["canonical"].values()),
                        "null_controls_pass": sum(c.get("verdict") == "pass" for c in report["null_controls"]),
                        "mutants_caught": sum(m["caught_with_expected_rule"] for m in report["mutants"]),
                        "mutants_total": len(report["mutants"]),
                        "rephrased_caught": sum(p["caught"] for p in report["rephrased_probes"]),
                        "rephrased_total": len(report["rephrased_probes"])}
    out = FORM / "evidence" / "gate_test_report.json"
    out.write_text(json.dumps(report, indent=2))
    lines = [f"GATE TEST REPORT: {report['verdict']}",
             f"canonical pass : {report['counts']['canonical_pass']}/3",
             f"null controls  : {report['counts']['null_controls_pass']}/{len(report['null_controls'])}",
             f"mutants caught : {report['counts']['mutants_caught']}/{report['counts']['mutants_total']}",
             f"rephrased leak probes caught (blind spots = misses): {report['counts']['rephrased_caught']}/{report['counts']['rephrased_total']}",
             f"self-application (parse + composite labels): {'clean' if report['self_application']['clean'] else report['self_application']}"]
    for m in report["mutants"]:
        if not m["caught_with_expected_rule"]:
            lines.append(f"  MISS {m['name']} expected {m['expected_rule']} got {m['failed_rules']}")
    for p in report["rephrased_probes"]:
        lines.append(f"  probe {p['name']} ({p['leak_family']}): {'caught' if p['caught'] else 'MISSED -> documented blind spot'}")
    (FORM / "evidence" / "gate_test_report.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
