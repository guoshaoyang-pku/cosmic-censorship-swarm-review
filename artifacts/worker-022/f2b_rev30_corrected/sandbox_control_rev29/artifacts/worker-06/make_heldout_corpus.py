#!/usr/bin/env python3
"""Generate the FORM-HELDOUT-07 held-out corpus (fresh mutants, canonical layout).

H1: >=20 mutants over >=10 leak families, >=8 rephrased (no forbidden token),
    all applied to the FROZEN canonical C0 schema layout.
H2: this script writes fixtures + manifest.json only. The manifest is frozen (hashed)
    by run_heldout_corpus.py BEFORE any gate runs.

Fixture naming: h01..h26 (leaking mutants), c01..c06 (controls).
Controls required by H5: the three frozen canonical schemas (checked by the runner),
2 conforming controls, 2 negated-phrase controls.

Usage: python3 make_heldout_corpus.py
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BASE_C0 = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
BASE_WCC = ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
OUT = HERE / "heldout_corpus"


def load(p):
    return yaml.safe_load(p.read_text())


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


def mut(name, family, rephrased, mutation, apply_fn):
    return {"fixture": f"{name}.yaml", "family": family, "rephrased": rephrased,
            "mutation": mutation, "apply": apply_fn}


MUTANTS = [
    mut("h01_regularity_selector_prose", "composite-regularity", True,
        "regularity.extensions.regularity_requirement = 'the extension may be taken continuous, or alternatively twice differentiable'",
        lambda d: d["regularity"].setdefault("extensions", {}).__setitem__(
            "regularity_requirement", "the extension may be taken continuous, or alternatively twice differentiable")),
    mut("h02_conclusion_c2_prose", "c2-conclusion-in-c0", True,
        "conclusion.statement_natural_language = 'the maximal development cannot be continued as a twice-differentiable Lorentzian manifold'",
        lambda d: d["conclusion"].__setitem__(
            "statement_natural_language",
            "the maximal development cannot be continued as a twice-differentiable Lorentzian manifold")),
    mut("h03_wcc_observer_prose", "wcc-content-in-scc", True,
        "visibility.reason = 'an observer at infinity can watch the singularity form'",
        lambda d: d["visibility"].__setitem__("reason", "an observer at infinity can watch the singularity form")),
    mut("h04_iplus_completeness_claim", "iplus-completeness", True,
        "i_plus.definition = 'I+ is complete; this completeness is used to rule out extensions'",
        lambda d: d["i_plus"].__setitem__("definition", "I+ is complete; this completeness is used to rule out extensions")),
    mut("h05_visible_falsifier_prose", "visibility-falsifier", True,
        "falsifier.tier_1.witness_type = 'an incomplete geodesic whose endpoint can be seen from infinity'",
        lambda d: d["falsifier"]["tier_1"].__setitem__(
            "witness_type", "an incomplete geodesic whose endpoint can be seen from infinity")),
    mut("h06_genericity_kind_swap", "genericity-notion", False,
        "genericity.kind = 'open_dense_escape' while generic_set stays comeager",
        lambda d: d["genericity"].__setitem__("kind", "open_dense_escape")),
    mut("h07_generic_set_plain_open", "genericity-prose", True,
        "genericity.generic_set = 'a set that is open and dense in the data space'",
        lambda d: d["genericity"].__setitem__("generic_set", "a set that is open and dense in the data space")),
    mut("h08_transfer_row_false", "transfer-failure", True,
        "append transfer_failures row {pair: [full_measure, residual_comeager], direction: entails, witness: 'a full-measure set is comeager'}",
        lambda d: d["genericity"]["transfer_failures"].append(
            {"pair": ["full_measure", "residual_comeager"], "direction": "entails",
             "witness": "a full-measure set is comeager", "status": "elementary"})),
    mut("h09_vacuity_prose", "vacuity", True,
        "non_vacuity.condition = 'the class is applied to data of interest'",
        lambda d: d["non_vacuity"].__setitem__("condition", "the class is applied to data of interest")),
    mut("h10_vacuity_witness_none", "vacuity", False,
        "non_vacuity.witness_type = 'none required'",
        lambda d: d["non_vacuity"].__setitem__("witness_type", "none required")),
    mut("h11_topology_two_ends", "topology-ends", False,
        "topology.slice_topology = '... two asymptotically flat ends'",
        lambda d: d["topology"].__setitem__(
            "slice_topology", "Sigma connected, oriented, complete Riemannian 3-manifold with two asymptotically flat ends")),
    mut("h12_iplus_topology_RxR", "topology-iplus", False,
        "topology.I_plus_topology = 'R x R'",
        lambda d: d["topology"].__setitem__("I_plus_topology", "R x R")),
    mut("h13_matter_scalar", "matter-smuggle", False,
        "data_class.matter = 'massless scalar field'",
        lambda d: d["data_class"].__setitem__("matter", "massless scalar field")),
    mut("h14_symmetry_assumed", "symmetry-assumption", True,
        "data_class.extensions.symmetry_note = 'we restrict to spherical symmetry'",
        lambda d: d["data_class"].setdefault("extensions", {}).__setitem__(
            "symmetry_note", "we restrict to spherical symmetry")),
    mut("h15_all_data_quantifier", "quantifier-strength", True,
        "quantifiers.formal drops the comeager set: 'forall D in X_vac(AF): not exists proper_future_C0_metric_extension(MGHD(D))'",
        lambda d: d["quantifiers"].__setitem__(
            "formal", "forall D in X_vac(AF): not exists proper_future_C0_metric_extension(MGHD(D))")),
    mut("h16_theorem_promotion", "conclusion-inflation", True,
        "conclusion.epistemic_status = 'conditional_theorem'; statement adds 'we prove the C0-inextendibility theorem'",
        lambda d: (d["conclusion"].__setitem__("epistemic_status", "conditional_theorem"),
                   d["conclusion"].__setitem__("statement_natural_language",
                                                "We prove the C0-inextendibility theorem for generic data."))),
    mut("h17_source_overclaim", "provenance-overclaim", True,
        "provenance.sources[0].role = 'settles the class conclusion'",
        lambda d: d["provenance"]["sources"][0].__setitem__("role", "settles the class conclusion")),
    mut("h18_converse_ledger", "converse-implication", False,
        "append converse C2 => C0 to implication_ledger.one_way_entailments",
        lambda d: d["implication_ledger"]["one_way_entailments"].append(
            {"from": "no proper future C2 extension", "to": "no proper future C0 metric extension",
             "relation": "entails", "reason": "asserted", "status": "unresolved"})),
    mut("h19_h2loc_substitution", "regularity-substitution", True,
        "extension_predicate.extensions.category = H2_loc extension class is the intended class",
        lambda d: d["extension_predicate"].setdefault("extensions", {}).__setitem__(
            "category", "the intended extension class is the locally square-integrable-curvature class; smoothness is not assumed")),
    mut("h20_two_sided", "direction", False,
        "extension_predicate.frozen_direction = 'two_sided'",
        lambda d: d["extension_predicate"].__setitem__("frozen_direction", "two_sided")),
    mut("h21_equation_swap", "equation-concept", False,
        "extension_predicate.frozen_equation_concept = 'distributional_ricci' while extension_solution_concept stays none",
        lambda d: d["extension_predicate"].__setitem__("frozen_equation_concept", "distributional_ricci")),
    mut("h22_curvature_hypothesis", "curvature-hypothesis", True,
        "non_vacuity.extensions.curvature_bound = 'the Kretschmann scalar is bounded across the boundary'",
        lambda d: d["non_vacuity"].setdefault("extensions", {}).__setitem__(
            "curvature_bound", "the Kretschmann scalar is bounded across the boundary")),
    mut("h23_contract_pointer_c2", "identity-binding", False,
        "class_contract_pointer ends with AF-SCC-C2-VAC-GEN",
        lambda d: d.__setitem__(
            "class_contract_pointer", "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN")),
    mut("h24_scope_c2_prose", "scope-prose", True,
        "scope_statement adds 'and no extension with a twice-differentiable metric exists'",
        lambda d: d.__setitem__("scope_statement", d["scope_statement"].rstrip()
                                + " Moreover no extension with a twice-differentiable metric exists.")),
    mut("h25_decay_removed", "data-class-vague", False,
        "delete data_class.asymptotic_decay",
        lambda d: del_path(d, "data_class.asymptotic_decay")),
    mut("h26_quantifier_order", "quantifier-order", True,
        "quantifiers.ordered: extension quantifier moved before the data quantifier",
        lambda d: d["quantifiers"].__setitem__("ordered", [
            {"kind": "exists", "binder": "G", "domain_id": "D1"},
            {"kind": "not_exists", "binder": "(M',g',iota)", "domain_id": "D3"},
            {"kind": "forall", "binder": "D", "domain_id": "D2"}])),
]


def build_controls(base_c0, base_wcc):
    controls = [
        ("c01_conforming_canonical_c0", base_c0, "conforming"),
        ("c02_conforming_worker_rev6", load(ROOT / "schemas" / "af_scc_c0_vacuum.yaml"), "conforming"),
        ("c03_negated_phrase_c0", copy.deepcopy(base_c0), "negated-phrase"),
        ("c04_negated_phrase_wcc", copy.deepcopy(base_wcc), "negated-phrase"),
    ]
    c03 = controls[2][1]
    c03["anti_scope"].setdefault("extensions", {})["quoted_forbidden_phrases"] = [
        {"phrase": "C0 or C2", "tag": "exempt_forbidden_phrase_quotation",
         "why": "quoted only to forbid it"}]
    c04 = controls[3][1]
    c04["anti_scope"].setdefault("extensions", {})["negated_phrases"] = [
        "this schema does not assert strong cosmic censorship",
        "no visible singularity and no asymptotic predictability claim is made here"]
    return controls


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base_c0, base_wcc = load(BASE_C0), load(BASE_WCC)
    entries = []
    for m in MUTANTS:
        doc = copy.deepcopy(base_c0)
        m["apply"](doc)
        path = OUT / m["fixture"]
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        entries.append({k: v for k, v in m.items() if k != "apply"}
                       | {"path": str(path.relative_to(ROOT)),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    ctl_entries = []
    for name, doc, kind in build_controls(base_c0, base_wcc):
        path = OUT / f"{name}.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        ctl_entries.append({"fixture": path.name, "kind": kind, "path": str(path.relative_to(ROOT)),
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {
        "corpus_id": "FORM-HELDOUT-07",
        "frozen_base_c0": str(BASE_C0.relative_to(ROOT)),
        "frozen_base_c0_sha256": hashlib.sha256(BASE_C0.read_bytes()).hexdigest(),
        "frozen_base_wcc_sha256": hashlib.sha256(BASE_WCC.read_bytes()).hexdigest(),
        "frozen_taxonomy_sha256": hashlib.sha256((ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml").read_bytes()).hexdigest(),
        "frozen_rule_spec_sha256": hashlib.sha256((ROOT / "artifacts" / "formulation" / "rule_spec.json").read_bytes()).hexdigest(),
        "mutants": entries,
        "controls": ctl_entries,
        "frozen_canonical_controls": [
            "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"],
        "families": sorted({e["family"] for e in entries}),
        "rephrased_count": sum(1 for e in entries if e["rephrased"]),
        "corpus_definition_note": "written before any gate run; the runner records this file's sha256 before executing stage A and stage B",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {len(entries)} mutants over {len(manifest['families'])} families "
          f"({manifest['rephrased_count']} rephrased) and {len(ctl_entries)} controls to {OUT}")


if __name__ == "__main__":
    main()
