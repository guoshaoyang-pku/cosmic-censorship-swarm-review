#!/usr/bin/env python3
"""Generate the W06 semantic/rephrased fixture corpus for FORM-RULE-SPEC 1.0.

Covers the assignment's S1 leak list (>=14 classes a lexical gate should reject) and
S2 (>=6 rephrased mutants carrying no forbidden token). Every fixture is a deep
mutation of a conforming canonical-format C0 schema, so the leak is carried by field
semantics; a mutant that the auditor accepts while carrying a real leak becomes a
documented blind spot, not a pass.

Controls in controls/: a conforming base and a tagged forbidden-phrase quotation, both
of which must be accepted (the lead's canonical schemas contain the same pattern).

Usage: python3 make_semantic_fixtures.py
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FROZEN_C0 = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
BASE = FROZEN_C0 if FROZEN_C0.exists() else ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
OUT = HERE / "semantic_fixtures"
CTL = OUT / "controls"


def load_base():
    return yaml.safe_load(BASE.read_text())


def set_path(doc, dotted, value):
    cur = doc
    parts = dotted.split(".")
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def del_path(doc, dotted):
    cur = doc
    parts = dotted.split(".")
    for p in parts[:-1]:
        cur = cur[p]
    cur.pop(parts[-1], None)


def mut(fixture, path, value, expected_rules, leak_family, repair, rephrased=False,
        delete=False, s1=None, apply_fn=None):
    def apply(d):
        if apply_fn is not None:
            apply_fn(d)
        elif delete:
            del_path(d, path)
        else:
            set_path(d, path, value)
    return {"fixture": fixture, "expected_verdict": "reject", "expected_rules": expected_rules,
            "leak": True, "leak_family": leak_family, "mutation_path": path,
            "mutation": ("delete " if delete else "") + f"{path} = {value!r}",
            "rephrased": rephrased, "s1_class": s1, "apply": apply, "repair": repair}


MUTATIONS = [
    # ---------------- S1 leak classes (mechanical mutants) ----------------
    mut("struct01_composite_regularity.yaml", "regularity.extension_regularity", "C0 or C2",
        ["R13"], "composite regularity selector (S1)", "none needed: lexical rule catches it.",
        s1="composite C0-or-C2"),
    mut("struct02_conclusion_type_swap.yaml", "conclusion.conclusion_type", "scc_c2_future_inextendibility",
        ["R11"], "conclusion_type swapped to the C2 vocabulary value (S1)",
        "none needed: vocabulary rule catches it.", s1="C2 result cited as C0"),
    mut("struct03_visibility_role_swap.yaml", "visibility.role", "conclusion",
        ["R10"], "SCC schema declares visibility as its conclusion (S1)",
        "none needed: family-role rule catches it.", s1="visibility conclusion inside SCC"),
    mut("struct04_wcc_conclusion_in_scc.yaml", "conclusion.conclusion_type", "weak_cosmic_censorship",
        ["R11"], "WCC conclusion type inside an SCC schema (S1)",
        "none needed: vocabulary rule catches it.", s1="WCC conclusion inside SCC"),
    mut("struct05_i_plus_topology_wrong.yaml", "topology.I_plus_topology", "R x R",
        ["R04"], "I+ not R x S^2 (S1)", "none needed: topology rule catches it.",
        s1="I+ not R x S^2"),
    mut("struct06_genericity_omitted.yaml", "genericity", None,
        ["R07"], "genericity block deleted (S1)", "none needed: presence rule catches it.",
        delete=True, s1="genericity omitted"),
    mut("struct07_matter_smuggled.yaml", "data_class.matter", "massless_scalar_field",
        ["R05"], "matter smuggled into a VAC class (S1)", "none needed: matter rule catches it.",
        s1="matter smuggled into VAC"),
    mut("struct08_multi_end_slice.yaml", "topology.slice_topology",
        "Sigma connected, complete Riemannian 3-manifold with two asymptotically flat ends",
        ["R04"], "multi-end slice undeclared in the one-ended class (S1)",
        "none needed: end-structure rule catches it.", s1="multi-end slice undeclared"),
    mut("struct09_nonvacuity_vacuous.yaml", "non_vacuity.witness_type", "none required",
        ["R08"], "vacuous non-vacuity clause (S1)", "hardened value check would also flag 'none required'.",
        s1="vacuous SCC"),
    mut("struct10_equation_requirement_omitted.yaml", "extension_predicate.frozen_equation_concept", None,
        ["R06"], "extension equation requirement left undeclared (S1)",
        "none needed if R06 requires the field.", delete=True,
        s1="extension equation requirement undeclared"),
    mut("struct11_theorem_without_artifact.yaml", "conclusion.epistemic_status", "theorem",
        ["R11"], "theorem labelling without artifact_refs (S1)",
        "none needed: R11 guard catches it.", s1="theorem without artifact_refs"),
    mut("struct12_i_plus_completeness_lexical.yaml", "i_plus.completeness_in_conclusion", True,
        ["R09"], "SCC asserts I+ completeness in the conclusion, lexically (S1)",
        "none needed: R09 flag check catches it.", s1="I+ completeness as SCC conclusion"),
    # ---------------- S2 rephrased mutants (no forbidden token) ----------------
    mut("sem01_smuggled_smoothness_key.yaml", "regularity.extension_smoothness_assumption",
        "the extended metric is twice differentiable on the added region",
        ["R06"], "C2-regularity smuggled as an extra key",
        "R06: reject extra keys under `regularity` naming a different differentiability class.",
        rephrased=True, s1="H2_loc/C2 written as C0"),
    mut("sem02_inherited_sibling_conclusion.yaml", "conclusion.inherited_from",
        {"class_id": "AF-SCC-C2-VAC-GEN",
         "statement": "no proper future extension with a twice-differentiable metric exists"},
        ["R11", "R12"], "conclusion inherited from the C2 sibling, in prose",
        "R11: reject sibling class ids or sibling conclusion paraphrases inside the conclusion block.",
        rephrased=True, s1="C2 result cited as C0"),
    mut("sem03_genericity_open_dense_swap.yaml", "genericity.generic_set",
        "an open dense subset of the ambient data space",
        ["R07"], "genericity notion silently weakened to open dense",
        "R07: require generic_set wording to match genericity.kind.",
        rephrased=True, s1="comeager->open-dense transfer"),
    mut("sem04_all_data_strengthening.yaml", "genericity.kind", "none",
        ["R07"], "quantifier strengthened to all data while keeping the word generic",
        "R07: kind='none' must flip is_part_of_class and remove the comeager binder.",
        rephrased=True, s1="genericity omitted / all-data strengthening"),
    mut("sem05_curvature_hypothesis.yaml", "non_vacuity.curvature_assumption",
        "the Kretschmann scalar remains bounded across the future boundary",
        ["R06", "R08"], "C2-flavoured curvature hypothesis added to a C0 class",
        "R08: ban curvature-invariant hypotheses in an SCC-C0 schema.",
        rephrased=True, s1="H2_loc/C2 written as C0"),
    mut("sem06_visibility_falsifier_rephrased.yaml", "falsifier.tier_1.witness_type",
        "an incomplete causal geodesic whose endpoint is seen by an observer at infinity",
        ["R12", "R14"], "WCC falsifier expressed without the word visible",
        "R12: add visibility paraphrase tokens ('seen by an observer at infinity').",
        rephrased=True, s1="visibility as SCC falsifier"),
    mut("sem07_i_plus_used_in_conclusion.yaml", "i_plus.used_in_conclusion",
        "the completeness of I+ is what rules out extensions",
        ["R09", "R12"], "I+ completeness driving the conclusion while flags stay false",
        "R09: scan the whole i_plus block for conclusion import, not only the boolean flags.",
        rephrased=True, s1="I+ completeness as SCC conclusion"),
    mut("sem08_extension_solution_concept_swap.yaml", "regularity.extension_solution_concept",
        "distributional_ricci", ["R06"],
        "distributional-vacuum variant substituted for the bare-metric class",
        "R06: require extension_solution_concept to agree with frozen_equation_concept.",
        rephrased=True, s1="extension equation requirement mismatch"),
    mut("sem09_two_sided_direction.yaml", "extension_predicate.frozen_direction", "two_sided",
        ["R06", "R11"], "future direction quietly replaced by two-sided",
        "R06: require frozen_direction to equal the class contract's future direction.",
        rephrased=True, s1="direction axis silently changed"),
    mut("sem10_h2loc_extension_class.yaml", "extension_predicate.frozen_regularity", "H2_loc",
        ["R06", "R13"], "H2_loc extension class substituted for bare C0",
        "R06: require frozen_regularity to equal regularity.extension_regularity.",
        rephrased=True, s1="H2_loc written as C0"),
    mut("sem11_contract_pointer_c2.yaml", "class_contract_pointer",
        "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN",
        ["R02"], "class contract pointer silently points at the C2 sibling",
        "R02: require the pointer's class segment to match class_id.",
        rephrased=True, s1="C2 result cited as C0"),
    mut("sem12_theorem_promotion.yaml", "conclusion.statement_natural_language",
        "We prove the generic C0-inextendibility theorem",
        ["R11"], "conclusion promoted with a prove-theorem phrase and no artifact",
        "R11: keep the prove/establish-theorem guard (already caught in baseline).",
        rephrased=True, s1="theorem without artifact_refs"),
    mut("sem13_comeager_to_full_measure.yaml", "genericity.kind", "full_measure",
        ["R07"], "comeager silently replaced by full measure (a non-transferable notion)",
        "R07: cross-check kind against generic_set wording and the transfer_failures ledger.",
        rephrased=True, s1="comeager->full-measure transfer"),
    mut("sem14_c2_result_cited_as_c0.yaml", "conclusion.citation_use",
        {"source_claim": "a published result rules out twice-differentiable extensions",
         "used_as": "evidence that this class's conclusion holds"},
        ["R11", "R15"], "a C2-level result cited as if it established this C0 class",
        "R11/R15: forbid using a sibling-regularity result as evidence for this class; subsumption must be labelled.",
        rephrased=True, s1="C2 result cited as C0"),
    mut("sem15_vacuous_nonvacuity.yaml", "non_vacuity.condition",
        "every development has some future boundary",
        ["R08"], "non-vacuity condition made trivially true",
        "R08: require the condition to name an incompleteness/trapped-surface marker, not any boundary.",
        rephrased=True, s1="vacuous SCC"),
    # ---- priority leak classes named by the formulation lead (23:31 follow-up) ----
    mut("sem16_converse_implication.yaml", "implication_ledger.one_way_entailments",
        "appended converse entry C2 => C0",
        ["R16"], "forbidden converse implication inserted into the one-way ledger",
        "R16: reject a one_way_entailment whose from/to is the C2 => C0 converse.",
        rephrased=True, s1="converse implication ledger",
        apply_fn=lambda d: d["implication_ledger"]["one_way_entailments"].append(
            {"from": "no proper future C2 extension", "to": "no proper future C0 metric extension",
             "relation": "entails", "reason": "asserted without proof", "status": "unresolved"})),
    mut("sem17_i_plus_completeness_definition.yaml", "i_plus.completeness_definition",
        "I+ is complete in the conformal sense",
        ["R09", "R12"], "I+ completeness imported through a definition key while the flags stay false",
        "R09: reject any i_plus completeness assertion when the class excludes I+ from the conclusion.",
        rephrased=True, s1="completeness in i_plus.completeness_definition",
        apply_fn=lambda d: d["i_plus"].update(
            {"completeness_definition": "I+ is complete in the conformal sense",
             "completeness_definition_status": "verified"})),
    mut("sem18_provenance_overclaim.yaml", "provenance.sources[0].role",
        "establishes the conclusion of this class",
        ["R15"], "source entry claims to establish the class conclusion",
        "R15: scan source role/note prose for establish/prove/settle-the-class overclaims.",
        rephrased=True, s1="source overclaim in provenance",
        apply_fn=lambda d: d["provenance"]["sources"][0].update(
            {"role": "establishes the conclusion of this class", "status": "verified"})),
    mut("sem19_prose_nonvacuity_condition.yaml", "non_vacuity.condition",
        "the development is interesting enough to test",
        ["R08"], "non-vacuity condition replaced by prose with no marker",
        "R08: require an incompleteness/trapped-surface/boundary marker in the condition.",
        rephrased=True, s1="prose leak in non_vacuity.condition"),
    mut("sem20_prose_genericity_set.yaml", "genericity.generic_set",
        "a large set of data in the ambient space",
        ["R07"], "genericity set rephrased as a large set, dropping the comeager condition",
        "R07: require generic_set wording to match genericity.kind (comeager/residual condition).",
        rephrased=True, s1="prose leak in genericity.generic_set"),
]

CONTROLS = [
    {
        "fixture": "control_comment_only_composite.yaml",
        "expected_verdict": "accept",
        "note": "known parser blind spot: the composite phrase appears only in a YAML comment; a conforming schema must still be accepted",
        "apply": lambda d: None,
    },
    {
        "fixture": "control_conforming_base.yaml",
        "expected_verdict": "accept",
        "note": "unmutated conforming C0 schema; a gate that rejects it is over-strict",
        "apply": lambda d: None,
    },
    {
        "fixture": "control_quoted_forbidden_phrase.yaml",
        "expected_verdict": "accept",
        "note": "conforming schema carrying a tagged forbidden-phrase quotation; R13 exempts explicit quotations, and the lead's canonical schemas contain exactly this pattern",
        "apply": lambda d: d.setdefault("anti_scope", {}).setdefault("extensions", {}).__setitem__(
            "quoted_forbidden_phrases",
            [{"phrase": "C0 or C2", "tag": "exempt_forbidden_phrase_quotation",
              "why": "quoted only to forbid it; R13 permits explicit forbidden-phrase quotations; placed under extensions so the R22 key manifest also passes"}]),
    },
]


def main(base=None):
    global BASE
    if base:
        BASE = Path(base)
    OUT.mkdir(parents=True, exist_ok=True)
    CTL.mkdir(parents=True, exist_ok=True)
    manifest = {"base": str(BASE.relative_to(ROOT)),
                "base_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
                "rules_version": "w06-semantic-3", "fixtures": []}
    for m in MUTATIONS:
        doc = copy.deepcopy(load_base())
        m["apply"](doc)
        path = OUT / m["fixture"]
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        entry = {k: v for k, v in m.items() if k != "apply"}
        entry["path"] = str(path.relative_to(ROOT))
        manifest["fixtures"].append(entry)
    controls = []
    for c in CONTROLS:
        doc = copy.deepcopy(load_base())
        c["apply"](doc)
        path = CTL / c["fixture"]
        body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
        if c["fixture"] == "control_comment_only_composite.yaml":
            # documented parser blind spot: the forbidden composite phrase lives only in a
            # comment, so a YAML parser never sees it. Lead instruction: document, do not fix.
            body += "# known parser blind spot (documented, not fixed): a composite regularity phrase 'C0 or C2' in a comment is invisible to any YAML-based gate.\n"
        path.write_text(body)
        controls.append({k: v for k, v in c.items() if k != "apply"} | {"path": str(path.relative_to(ROOT))})
    manifest["controls"] = controls
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    s1 = {m.get("s1_class") for m in MUTATIONS if m.get("s1_class")}
    print(f"wrote {len(manifest['fixtures'])} fixtures ({sum(1 for m in MUTATIONS if m['rephrased'])} rephrased) "
          f"and {len(controls)} controls; S1 classes covered: {len(s1)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="base schema to mutate (default: frozen canonical C0)")
    a = ap.parse_args()
    main(a.base)
