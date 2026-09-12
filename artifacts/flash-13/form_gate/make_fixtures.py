#!/usr/bin/env python3
"""Build the FORM-GATE-01 fixture corpus: 3 conforming schemas, 18 single-rule mutants,
6 rephrased (token-evading) mutants. Deterministic; writes YAML + manifest.json.

Kept compact on purpose so every mutant's diff is auditable by eye. The conforming bases
mirror the canonical field contract of FORM-RULE-SPEC v1.0 (not the canonical file contents).
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def base_wcc() -> dict:
    return {
        "schema_version": "1.0",
        "artifact_kind": "class_schema",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "owner": "lead-formulation",
        "epistemic_status": "open_problem",
        "class_components": {
            # frozen canonical shape: one axis per class-id token
            "asymptotics": "AF", "censorship": "WCC", "matter": "VAC", "genericity": "GEN",
            "regularity_token": "none",
        },
        "quantifiers": {
            "ordered": [
                {"kind": "forall", "binder": "(Sigma,h,K)", "domain": "generic vacuum AF data",
                 "domain_id": "D_GEN"},
                {"kind": "exists", "binder": "(M,g)", "domain": "maximal development",
                 "domain_id": "DEV"},
                {"kind": "exists", "binder": "p", "domain": "future boundary points",
                 "domain_id": "VIS"},
            ],
            "formal": "forall (Sigma,h,K) in D_GEN : exists (M,g) in DEV : "
                      "not exists p in VIS with Visible(p)",
            "order_matters": True,
            "negation": "there exists data outside the residual set, or a visible boundary point "
                        "reached from I+",
            "domains": {
                "D_GEN": {"definition": "data in the residual set G = intersection of open dense "
                                         "sets in the H^4_{1/2+eps} topology",
                          "definition_ref": "genericity.generic_set"},
                "DEV": {"definition": "the maximal globally hyperbolic development of the data"},
                "VIS": {"definition": "future boundary points p with p in J^-(I+)"},
            },
        },
        "topology": {
            "spacetime_dimension": 4,
            "slice_topology": "Sigma connected, complete, oriented, one-ended and asymptotically flat",
            "completeness_of_slice": True,
            "conformal_boundary": ["I+ (future null infinity)", "I- (past null infinity)",
                                   "i0 (spatial infinity)"],
            "I_plus_topology": "R x S^2",
            "forbidden": ["closed (compact without boundary) slices", "periodic slices"],
        },
        "data_class": {
            "matter": "none",
            "cosmological_constant": 0,
            "constraints": {
                "hamiltonian": "R(h) - K_ij K^ij + (tr K)^2 = 0",
                "momentum": "div K - d tr K = 0",
            },
            "adm_mass_status": "finite ADM 4-momentum; the Minkowski point is excluded",
            "adm_mass": {"exists": True, "sign": "m_ADM >= 0"},
            "asymptotic_decay": {
                "metric": "h - delta = O(r^-1); d^k h = O(r^{-1-k})",
                "curvature": "K = O(r^-2); d^k K = O(r^{-2-k})",
            },
            "regularity_class": {"default": "smooth-with-decay",
                                 "sobolev_variant": {"s": 4, "delta": "1/2 + epsilon"}},
            "sobolev_index": {"s": 4},
            "weight": {"delta": "1/2 + epsilon"},
        },
        "regularity": {
            "data_regularity": "h in H^4_loc, K in H^3_loc",
            "solution_regularity": "C^2 Lorentzian metric on the maximal development",
            "i_plus_regularity": "conformal factor extends to I+ with C^3 regularity",
            "extension_regularity": None,
            "extension_solution_concept": None,
            "must_not_conflate": [
                "data regularity is not solution regularity",
                "I+ regularity is not extension regularity",
            ],
        },
        "genericity": {
            "kind": "residual_comeager",
            "ambient_space": "D_w, completion of smooth AF vacuum data in H^4_{1/2+eps}",
            "topology_or_measure": "norm topology of H^4_{1/2+eps}",
            "generic_set": "G = intersection over n of open dense U_n",
            "excluded_set": "meagre complement; candidate members recorded, not asserted",
            "transfer_failures": [{"notion": "full_measure",
                                   "why_transfer_fails": "no canonical Gaussian measure"}],
            "is_part_of_class": True,
            "is_part_of_class_statement": "changing the genericity notion yields a different class",
            "class_change_warning": "genericity is part of the class; substituting another notion "
                                    "yields a different class",
        },
        "non_vacuity": {
            "condition": "there exists data in D_GEN with a future-incomplete development",
            "witness_type": "existence witness: a collapsing family",
        },
        "i_plus": {
            "role": "conclusion",
            "in_conclusion": True,
            "definition": "future null infinity of the conformal completion",
            "completeness_definition": "every null geodesic generator of I+ is future-complete "
                                       "(infinite affine length)",
        },
        "visibility": {
            "role": "conclusion",
            "predicate_name": "VisibleFromIplus(p)",
            "definition": "p is reached by a future-directed causal curve that escapes to I+",
            "negation_conclusion": "not exists p in partial_sing(M) with VisibleFromIplus(p)",
        },
        "conclusion": {
            "conclusion_type": "weak_cosmic_censorship",
            "epistemic_status": "open_problem",
            "statement": "for all generic data: no singularity is visible at I+",
            "statement_natural_language": "for all generic data: no singularity is visible at I+",
            "statement_formal": "forall D in G : not exists p visible from I+",
            "forbidden_strengthenings": [
                "upgrading to theorem without artifact_refs",
                "importing an extendibility conclusion",
            ],
        },
        "falsifier": {
            "tier_1": {
                "refutes": "AF-WCC-VAC-GEN",
                "statement": "an open set of generic data whose maximal development has a visible "
                             "incomplete causal geodesic",
                "robustness_requirement": "must hold on an open (or residual) set of data",
                "witness_type": "visible incomplete causal geodesic",
                "family_witness_type": "visible incomplete causal geodesic",
                "machine_checkable_steps": [
                    "check the vacuum constraint equations",
                    "integrate to the singular boundary",
                    "verify the causal curve reaches I+",
                ],
            },
            "tier_2": {
                "refutes": "a strengthening only: a claimed decay rate or norm-specific bound",
                "statement": "refutes a strengthening, not the class",
                "witness_type": "a single data set violating the strengthening",
                "labelling_required": "refutes_strengthening_only",
            },
            "witness_type": "visible incomplete causal geodesic; none constructed in this fixture",
        },
        "provenance": {
            "citation_status": "unresolved",
            "sources": [],
            "unresolved_citations": ["no source in this fixture establishes the class conclusion"],
            "source_conclusion_disclaimer": "no source is presented as establishing the class conclusion",
        },
    }


def base_scc(token: str) -> dict:
    d = base_wcc()
    d["class_id"] = f"AF-SCC-{token}-VAC-GEN"
    d["node_id"] = "F2"
    d["class_components"] = {
        "asymptotics": "AF", "censorship": "SCC", "matter": "VAC", "genericity": "GEN",
        "regularity_token": token,
    }
    d["regularity"]["extension_regularity"] = token
    d["regularity"]["extension_solution_concept"] = "classical_ricci" if token == "C2" else "none"
    d["regularity"]["extension_solution_concept_note"] = (
        "classical vacuum extension (Ric = 0) for C2" if token == "C2"
        else "continuous nondegenerate metric extension; no field equations imposed")
    d["regularity"]["must_not_conflate"] = [
        "differentiability smuggled in through smooth coordinates",
        "WCC content must not appear as this class's conclusion",
    ]
    d["i_plus"] = {
        "role": "assumption",
        "in_conclusion": False,
        "definition": "future null infinity defines the data class and the maximal development; "
                      "it appears nowhere in the conclusion",
        "forbidden": ["asserting I+ completeness as part of the class conclusion"],
    }
    d["visibility"] = {
        "role": "not_in_conclusion",
        "reason": "visibility from I+ is the WCC predicate; it is logically independent of "
                  "extendibility of the development",
        "visible_singularity_is_wcc": True,
        "forbidden_falsifier": "a visible incomplete causal geodesic is a WCC falsifier, "
                               "not a falsifier of this class",
    }
    d["conclusion"] = {
        "conclusion_type": f"scc_{token.lower()}_future_inextendibility",
        "epistemic_status": "open_problem",
        "statement": f"generic AF vacuum data have a maximal development that is "
                     f"future-inextendible as a {token} Lorentzian manifold",
        "statement_natural_language": f"generic AF vacuum data are future-inextendible as "
                                      f"{token} Lorentzian manifolds",
        "statement_formal": f"forall D in G : not exists proper future {token} extension of MGHD(D)",
        "forbidden_strengthenings": [
            "two-sided inextendibility",
            "upgrading to theorem without artifact_refs",
        ],
    }
    d["falsifier"]["tier_1"] = {
        "refutes": f"AF-SCC-{token}-VAC-GEN",
        "witness_type": f"a non-meager set of one-ended AF vacuum data whose maximal "
                        f"developments admit proper future {token} metric extensions",
        "genericity_requirement": "tier 1 requires non-meagerness of the extendible set",
        "family_witness_type": f"extension witness: a proper future {token} metric extension",
        "machine_checkable_steps": [
            "check constraint residuals below tolerance",
            f"verify the {token} extension is nondegenerate on a neighbourhood of the boundary",
            "verify the embedding is an isometry onto an open proper subset",
        ],
    }
    d["falsifier"]["tier_2"] = {
        "refutes": "only the strictly stronger class 'for all AF vacuum data'",
        "witness_type": "a single extendible data set",
        "labelling_required": "refutes_strengthening_only",
    }
    d["falsifier"]["witness_type"] = f"proper future {token} extension; none constructed here"
    d["implication_ledger"] = {
        "one_way_entailments": [
            {"from": "no proper future C0 extension", "to": "no proper future C2 extension",
             "relation": "entails",
             "reason": "every C2 metric extension is a C0 metric extension, so the C2 extension "
                       "class is strictly smaller (C2 subset C0)"},
        ],
        "forbidden_transfers": [
            {"from": "no proper future C2 extension", "to": "this class",
             "reason": "C2-inextendibility is strictly weaker and does not transfer"},
            {"from": "AF-WCC-VAC-GEN", "to": "this class",
             "reason": "WCC <-> SCC transfer is forbidden here"},
        ],
        "cross_family": "no WCC <-> SCC transfer is licensed by this fixture",
    }
    return d


def mutant_bases():
    wcc = base_wcc()
    c2 = base_scc("C2")
    c0 = base_scc("C0")
    return {"wcc": wcc, "c2": c2, "c0": c0}


def mutations(base: dict):
    """Return {name: (base_key, expected_rule, mutation_fn, note)}."""
    def m(fn):
        return fn

    def m01(d):
        del d["owner"]
    def m02(d):
        d["class_components"]["matter"] = "SCALAR"
    def m03(d):
        d["quantifiers"]["ordered"][0]["domain_id"] = "D_MISSING"
    def m04(d):
        d["quantifiers"]["domains"]["DEV"] = {"definition": "a suitable development"}
    def m05(d):
        d["topology"]["forbidden"] = ["no restriction is imposed on the slice"]
    def m06(d):
        d["data_class"]["asymptotic_decay"] = {"metric": "decays fast enough"}
        d["data_class"].pop("sobolev_index", None)
        d["data_class"].pop("weight", None)
    def m07(d):
        del d["regularity"]["i_plus_regularity"]
    def m08(d):
        d["genericity"]["kind"] = "generic_enough"
    def m09(d):
        del d["non_vacuity"]
    def m10(d):
        d["i_plus"]["in_conclusion"] = True
        d["i_plus"]["completeness_definition"] = "every generator is complete to the future"
    def m11(d):
        d["visibility"]["role"] = "conclusion"
    def m12(d):
        d["conclusion"]["epistemic_status"] = "theorem"
    def m13(d):
        d["data_class"]["regularity"] = "C2 or C0 data are admitted"
    def m14(d):
        wrong = "a generic data set whose development fails to be maximal"
        d["falsifier"]["tier_1"]["witness_type"] = wrong
        d["falsifier"]["tier_1"]["family_witness_type"] = wrong
    def m15(d):
        d["provenance"]["citation_status"] = "verified"
        d["provenance"]["sources"] = [{
            "identifier": "arXiv:0000.00000", "retrieval_date": "2026-09-11",
            "establishes_class_conclusion": True}]
        d["provenance"].pop("source_conclusion_disclaimer", None)
    def m16(d):
        del d["implication_ledger"]
    def m17(d):
        d["conclusion"]["statement"] = ("the maximal development is C^2-inextendible past the "
                                        "Cauchy horizon")
    def m18(d):
        d["falsifier"]["tier_2"]["statement"] = ("refutes a strengthening involving a scalar "
                                                 "field coupling")

    # --- extended coverage for R09/R12/R15/R16 (rule_spec v1.2 request) ---
    def m19(d):
        d["i_plus"]["definition"] = (d["i_plus"]["definition"] +
                                     "; I+ completeness is asserted as part of this class conclusion")
    def m20(d):
        d["i_plus"]["role"] = "assumption"
    def m21(d):
        d["conclusion"]["statement"] = (d["conclusion"]["statement"] +
                                        " through asymptotic predictability at infinity")
    def m22(d):
        d["conclusion"]["statement"] = (d["conclusion"]["statement"] +
                                        " under strong cosmic censorship")
    def m23(d):
        d["provenance"]["citation_status"] = "verified"
        d["provenance"]["sources"] = [{"title": "anonymous note with no locator"}]
    def m24(d):
        d["implication_ledger"].pop("forbidden_transfers", None)

    # --- revision 1.2: R03 declared-binder usage (mirrors the rev13 canonical WCC defect:
    # a tuple binder is declared but the formal sentence renders the quantifier variable-wise) ---
    def m25(d):
        d["quantifiers"]["ordered"][2]["binder"] = "(p,t0)"

    return {
        "m01_missing_owner": ("wcc", "R01", m01, "identity block loses owner"),
        "m02_token_mismatch": ("wcc", "R02", m02, "class_components tokens do not decompose class_id"),
        "m03_unresolved_domain": ("wcc", "R03", m03, "quantifier domain_id does not resolve"),
        "m04_vague_domain": ("wcc", "R03", m04, "domain definition is vague with no ref or number"),
        "m05_closed_slice_admitted": ("wcc", "R04", m05, "closed/periodic slices no longer forbidden"),
        "m06_vague_data_class": ("wcc", "R05", m06, "decay is non-numeric and no (s,delta)"),
        "m07_missing_regularity_slot": ("wcc", "R06", m07, "i_plus_regularity slot deleted"),
        "m08_genericity_kind_offvocab": ("wcc", "R07", m08, "genericity.kind not in vocabulary"),
        "m09_no_nonvacuity": ("wcc", "R08", m09, "non_vacuity block deleted"),
        "m10_scc_iplus_completeness": ("c2", "R09", m10, "SCC puts I+ completeness in the conclusion"),
        "m11_scc_visibility_wrong_role": ("c2", "R10", m11, "SCC visibility claimed as conclusion"),
        "m12_theorem_inflation": ("wcc", "R11", m12, "theorem label without artifact_refs"),
        "m13_composite_regularity": ("c2", "R13", m13, "C2-or-C0 composite class phrase"),
        "m14_wrong_family_witness": ("c2", "R14", m14, "SCC tier_1 witness is not an extension witness"),
        "m15_citation_overclaim": ("wcc", "R15", m15, "source presented as establishing the conclusion"),
        "m16_scc_ledger_missing": ("c2", "R16", m16, "SCC implication_ledger deleted"),
        "m17_scc_leak_into_wcc": ("wcc", "R12", m17, "SCC conclude-token inside a WCC conclusion"),
        "m18_matter_leak_into_vacuum": ("wcc", "R12", m18, "scalar-field token inside a vacuum falsifier"),
        "m19_scc_completeness_flag": ("c2", "R09", m19, "SCC sets completeness_in_conclusion=true"),
        "m20_wcc_iplus_role_assumption": ("wcc", "R09", m20, "WCC demotes i_plus.role to assumption"),
        "m21_scc_predictability_leak": ("c2", "R12", m21, "WCC predictability token in an SCC conclusion"),
        "m22_wcc_strong_censorship_leak": ("wcc", "R12", m22, "SCC token in a WCC conclusion"),
        "m23_verified_without_locator": ("wcc", "R15", m23, "verified status without identifier/date"),
        "m24_scc_ledger_missing_transfers": ("c2", "R16", m24, "ledger lacks forbidden/unresolved transfers"),
        "m25_wcc_binder_unused": ("wcc", "R03", m25, "declared tuple binder (p,t0) never occurs in quantifiers.formal"),
    }


def rephrased(base: dict):
    def r01(d):
        d["conclusion"]["statement"] = ("the maximal development admits no continuous extension "
                                        "beyond the horizon")
    def r02(d):
        d["conclusion"]["statement"] = ("the singular boundary cannot be observed from far away "
                                        "in any causal sense")
    def r03(d):
        d["data_class"]["regularity"] = "C-two or C-zero data are admitted"
    def r04(d):
        d["genericity"]["generic_set"] = "most data in the ambient space"
    def r05(d):
        d["falsifier"]["tier_1"]["family_witness_type"] = ("a data set whose development can be "
                                                           "continued continuously past its boundary")
    def r06(d):
        d["conclusion"]["statement"] = ("generic data do not produce a singularity observable at "
                                        "future null infinity, since that is the other family's question")

    return {
        "r01_extension_without_token": ("wcc", r01, "extension semantics, no SCC token"),
        "r02_observed_without_visible": ("c0", r02, "visibility semantics without 'visible'"),
        "r03_regularity_spelled_out": ("c2", r03, "C-two/C-zero instead of C2/C0"),
        "r04_most_data": ("wcc", r04, "measure claim without a Baire formula"),
        "r05_continued_not_extended": ("c2", r05, "extension witness phrased as 'continued'"),
        "r06_observable_not_visible": ("c0", r06, "WCC-style statement without WCC tokens"),
    }


def main():
    FIX.mkdir(parents=True, exist_ok=True)
    bases = mutant_bases()
    manifest = {"positives": {}, "mutants": {}, "rephrased": {}}

    for key, data in (("wcc", bases["wcc"]), ("c2", bases["c2"]), ("c0", bases["c0"])):
        name = {"wcc": "conforming_wcc.yaml", "c2": "conforming_scc_c2.yaml",
                "c0": "conforming_scc_c0.yaml"}[key]
        out = FIX / name
        out.write_text("# GENERATED by make_fixtures.py (FORM-GATE-01) - conforming fixture\n"
                       + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        manifest["positives"][name] = {"path": str(out), "class_id": data["class_id"],
                                       "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}

    for name, (bkey, rule, fn, note) in mutations(bases).items():
        d = copy.deepcopy(bases[bkey])
        fn(d)
        out = FIX / f"{name}.yaml"
        out.write_text(f"# GENERATED mutant for FORM-GATE-01: expected {rule} - {note}\n"
                       + yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
        manifest["mutants"][name] = {"path": str(out), "class_id": d["class_id"],
                                     "expected_rule": rule, "note": note,
                                     "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}

    for name, (bkey, fn, note) in rephrased(bases).items():
        d = copy.deepcopy(bases[bkey])
        fn(d)
        out = FIX / f"{name}.yaml"
        out.write_text(f"# GENERATED rephrased mutant for FORM-GATE-01 (lexical evasion) - {note}\n"
                       + yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
        manifest["rephrased"][name] = {"path": str(out), "class_id": d["class_id"], "note": note,
                                       "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}

    (FIX / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"positives={len(manifest['positives'])} mutants={len(manifest['mutants'])} "
          f"rephrased={len(manifest['rephrased'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
