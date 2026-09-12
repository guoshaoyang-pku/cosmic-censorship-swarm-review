#!/usr/bin/env python3
"""Build `schemas/f1_falsifier_tests.jsonl` — ambiguity attack suite for F1.

Assignment: asg-2026-09-11-F1-deepseek-flash-04-13 (node F1, class AF-WCC-VAC-GEN,
gate G-FORM, artifact `schemas/f1_falsifier_tests.jsonl`).

Acceptance contract: >=10 tests, each with a spacetime description, an answer to
"does it satisfy F1?", and the schema field that decides the answer.  The declared
falsifier is "a test that no schema field can decide" — so tests carrying
`deciding_field: null` are first-class results, not defects.

Every row is a *probe*, not a physics claim.  Literature pointers are marked
`unresolved_pending_L1`; no citation is treated as verified here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
OUT = ROOT / "schemas" / "f1_falsifier_tests.jsonl"

CONTRACT = "artifacts/formulation/rule_spec.json"
TAXONOMY = "research_map/formulation_taxonomy.yaml"

BASE = {
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "schema_under_test": "schemas/af_wcc_vacuum.yaml",
    "binding_at_authoring": "provisional_contract:FORM-RULE-SPEC-v1.0 + F0 taxonomy v0.1 (schema absent at authoring time)",
    "question": "Is this datum in AF-WCC-VAC-GEN, and does the F1 class conclusion hold for it?",
    "literature_status": "unresolved_pending_L1",
    "citation_status": "unresolved",
    "author": "deepseek-flash-04",
    "artifact_version": "0.1.0",
}
CONTRACT_REFS = [CONTRACT, TAXONOMY, "research_map/ASTRA_HANDOFF.md:30-31,38-39",
                 "comms/inbox/deepseek-flash-04.jsonl"]


def row(**kw):
    out = dict(BASE)
    out.update(kw)
    missing = [k for k in (
        "test_id", "spacetime_description", "does_it_satisfy_f1", "deciding_field",
        "deciding_field_status", "why", "falsifier_strength", "evidence_refs",
        "next_falsifier",
    ) if k not in out]
    if missing:
        raise SystemExit(f"row missing keys: {missing}")
    return out


TESTS = [
    row(
        test_id="F1-AMB-01",
        title="Minkowski datum: vacuous conclusion / non-vacuity probe",
        spacetime_description=(
            "Minkowski initial data (Sigma = R^3, h = delta, K = 0); the MGHD is Minkowski "
            "spacetime, every causal geodesic is complete, and B = M \\ J^-(I+) is empty. "
            "The conclusion's conditional antecedent ('the development is future-incomplete') "
            "is false, so the geodesic clause holds vacuously."
        ),
        known_properties=["vacuum", "asymptotically flat", "globally hyperbolic",
                          "future-complete", "no black-hole region"],
        satisfies_in_class="yes",
        satisfies_conclusion="vacuous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="non_vacuity.condition",
        deciding_field_alternates=["non_vacuity.witness_type"],
        deciding_field_status="value_dependent",
        ambiguity_kind="vacuous_conclusion",
        why=(
            "If 'satisfies F1' means class membership + conclusion, Minkowski satisfies F1 "
            "trivially. If it means the class conclusion is non-trivially exercised, it does "
            "not. R08 requires a non-vacuity block precisely to separate these, so the answer "
            "is decided only by the exact wording of non_vacuity.condition."
        ),
        falsifier_strength="schema_precision_gap",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R08"],
        next_falsifier=(
            "Produce a gate-passing schema whose non_vacuity.condition is satisfied by Minkowski "
            "data; then the non-vacuity gate is vacuous."
        ),
    ),
    row(
        test_id="F1-AMB-02",
        title="Exactly critical vacuum gravitational-wave collapse (naked singularity)",
        spacetime_description=(
            "Axisymmetric vacuum gravitational-wave initial data tuned exactly to the critical "
            "amplitude of type-II critical collapse (Abrahams-Evans family analogue); at the "
            "critical parameter a naked singularity forms. The critical set is codimension-one "
            "inside its one-parameter family and non-generic in the full vacuum data space."
        ),
        known_properties=["vacuum", "asymptotically flat", "naked singularity at exact criticality",
                          "critical set non-generic (codimension >= 1)"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="no",
        does_it_satisfy_f1="ambiguous",
        deciding_field="quantifiers.ordered",
        deciding_field_alternates=["genericity.generic_set", "genericity.kind"],
        deciding_field_status="class_level_vs_instance_level",
        ambiguity_kind="generic_quantifier_scope",
        why=(
            "The datum violates the conclusion, but it lies in a codimension-one (non-generic) "
            "set. If F1 quantifies 'exists a generic set G, forall data in G' (generic-first), "
            "the datum is outside the quantified domain and is not a counterexample. If F1 "
            "quantifies 'forall data, generically the conclusion holds' (generic inside the "
            "predicate), the datum is in the domain and falsifies the class. The quantifier "
            "order in quantifiers.ordered is the only field that can separate the readings."
        ),
        falsifier_strength="counterexample_candidate",
        counterexample_candidate=True,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R03,R07", f"{TAXONOMY}#H4"],
        next_falsifier=(
            "Submit the same datum to two reviewers who read quantifiers.ordered differently; "
            "if they return opposite class verdicts, the field is ambiguous."
        ),
    ),
    row(
        test_id="F1-AMB-03",
        title="Exact subextremal Kerr datum (non-generic family; interior ring singularity)",
        spacetime_description=(
            "Exact Kerr initial data with 0 < |a| < M. The spacetime is vacuum and asymptotically "
            "flat; the ring singularity is timelike and the interior contains incomplete causal "
            "geodesics. No incomplete causal geodesic from I+ lies in J^-(I+): the interior is "
            "not in the past of I+."
        ),
        known_properties=["vacuum", "asymptotically flat", "two-parameter family (measure zero)",
                          "timelike ring singularity", "incomplete interior geodesics"],
        satisfies_in_class="no",
        satisfies_conclusion="yes",
        does_it_satisfy_f1="no",
        deciding_field="genericity.generic_set",
        deciding_field_alternates=["visibility.definition", "quantifiers.domains"],
        deciding_field_status="determinate_under_standard_reading",
        ambiguity_kind="nakedness_wording_vs_J_minus_I_plus_containment",
        why=(
            "A wording-level checker that treats 'timelike singularity' as 'naked' would call "
            "this a WCC violation. The J^-(I+) containment clause in the conclusion excludes it. "
            "The class membership is separately decided by genericity: the Kerr family is "
            "measure-zero in the vacuum data space. The row verifies that both fields are needed "
            "and that either one alone gives the wrong answer."
        ),
        falsifier_strength="decided",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R03,R07,R10,R14"],
        next_falsifier=(
            "Find a schema reading in which genericity.generic_set admits the Kerr family while "
            "keeping the J^-(I+) conclusion; that reading is a documented blind spot."
        ),
    ),
    row(
        test_id="F1-AMB-04",
        title="Negative-mass Schwarzschild (visible incomplete geodesics from I+)",
        spacetime_description=(
            "Schwarzschild initial data with ADM mass M < 0 (spherically symmetric, static, "
            "vacuum, asymptotically flat). The r = 0 singularity is timelike and visible from "
            "I+; future-inextendible causal geodesics in J^-(I+) are incomplete and terminate "
            "at it."
        ),
        known_properties=["vacuum", "asymptotically flat", "negative ADM mass",
                          "timelike naked singularity", "incomplete causal geodesics in J^-(I+)"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="no",
        does_it_satisfy_f1="ambiguous",
        deciding_field="class_components.symmetry",
        deciding_field_alternates=["symmetry", "data_class.adm_mass_status"],
        deciding_field_status="class_level_vs_instance_level",
        ambiguity_kind="individual_vs_class_level_symmetry_hypothesis",
        why=(
            "H1-H3 hold and the datum appears to falsify WCC. H5 ('no symmetry is assumed: the "
            "data are not restricted to a spherical or axisymmetric family') is a statement "
            "about the class, not about each datum; read literally it does not exclude a "
            "spherical instance. If F1 provides no datum-level field excluding symmetric data "
            "(and no mass/positivity condition in data_class), then either the class contains a "
            "WCC counterexample or membership is undecidable."
        ),
        falsifier_strength="counterexample_candidate",
        counterexample_candidate=True,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R05", f"{TAXONOMY}#H5"],
        next_falsifier=(
            "Write a schema field whose value excludes this datum at the instance level; if no "
            "such field exists in the gate-passing schema, the class is refuted or ill-posed."
        ),
    ),
    row(
        test_id="F1-AMB-05",
        title="Superextremal Reissner-Nordstrom (matter-model control)",
        spacetime_description=(
            "Reissner-Nordstrom data with Q^2 > M^2: an electrovacuum solution with a timelike "
            "naked singularity visible from I+ and incomplete causal geodesics in J^-(I+)."
        ),
        known_properties=["electrovacuum (T != 0)", "asymptotically flat", "naked singularity"],
        satisfies_in_class="no",
        satisfies_conclusion="no",
        does_it_satisfy_f1="no",
        deciding_field="data_class.matter",
        deciding_field_alternates=["class_components.matter_model"],
        deciding_field_status="determinate",
        ambiguity_kind="control_matter_model_exclusion",
        why=(
            "The datum is excluded before the conclusion is evaluated: matter_model = vacuum "
            "requires T = 0, and this solution has a non-zero electromagnetic stress tensor. "
            "This is a control row: a correct F1 must answer 'no' for a reason independent of "
            "genericity and visibility."
        ),
        falsifier_strength="decided",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R05", f"{TAXONOMY}#matter_model"],
        next_falsifier=(
            "If any gate-passing reading admits this datum, the matter slot is not decisive and "
            "R05 is not implemented."
        ),
    ),
    row(
        test_id="F1-AMB-06",
        title="Spherically symmetric massless-scalar critical collapse (class-boundary control)",
        spacetime_description=(
            "Spherically symmetric massless scalar-field data at the black-hole threshold "
            "(Choptuik family): a naked singularity forms; the datum belongs to the scalar "
            "spherical class, not the vacuum class."
        ),
        known_properties=["massless scalar matter (T != 0)", "spherical symmetry",
                          "naked singularity", "belongs to AF-WCC-SCALAR-SPH"],
        satisfies_in_class="no",
        satisfies_conclusion="no",
        does_it_satisfy_f1="no",
        deciding_field="data_class.matter",
        deciding_field_alternates=["class_components.matter_model", "class_id"],
        deciding_field_status="determinate",
        ambiguity_kind="control_class_boundary",
        why=(
            "At least two fields must agree: matter = massless_scalar_field and the class id "
            "must resolve to AF-WCC-SCALAR-SPH. This row checks that the vacuum schema does not "
            "absorb the scalar class and that class_id and matter_model cannot disagree."
        ),
        falsifier_strength="decided",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R02,R05,R12", f"{TAXONOMY}#classes"],
        next_falsifier=(
            "A gate-passing schema that accepts this datum under any field reading is a "
            "class-leakage finding for A1."
        ),
    ),
    row(
        test_id="F1-AMB-07",
        title="Time-symmetric spherical vacuum datum (inclusion counterpart of AMB-04)",
        spacetime_description=(
            "Time-symmetric, spherically symmetric, vacuum, asymptotically flat initial data "
            "with ADM mass > 0 (Schwarzschild-type moment of time symmetry). The MGHD is "
            "Schwarzschild; it is future-incomplete, but no incomplete causal geodesic lies in "
            "J^-(I+)."
        ),
        known_properties=["vacuum", "asymptotically flat", "spherical symmetry",
                          "future-incomplete", "conclusion holds"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="yes",
        does_it_satisfy_f1="ambiguous",
        deciding_field="class_components.symmetry",
        deciding_field_alternates=["symmetry"],
        deciding_field_status="class_level_vs_instance_level",
        ambiguity_kind="individual_vs_class_level_symmetry_hypothesis",
        why=(
            "Paired with AMB-04 this pins the ambiguity: if H5 is read at the datum level, both "
            "this datum and AMB-04 are excluded; if it is read at the class level, both are "
            "admitted. F1 therefore needs one field that states the reading explicitly, or the "
            "symmetry slot decides membership by convention only."
        ),
        falsifier_strength="schema_precision_gap",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{TAXONOMY}#H5"],
        next_falsifier=(
            "Ask two reviewers to classify AMB-04 and AMB-07 under the same schema; opposite "
            "inclusion verdicts on the pair demonstrate the ambiguity."
        ),
    ),
    row(
        test_id="F1-AMB-08",
        title="Asymptotically flat data with non-simply-connected interior (lens-space summand)",
        spacetime_description=(
            "Complete, connected, one-ended asymptotically flat vacuum initial data whose "
            "spatial slice is a punctured lens space L(p,1) \\ B^3 glued along its S^2 boundary "
            "to the standard flat end R^3 \\ B; the interior has H_1 = Z_p != 0. Data are a "
            "small asymptotically flat perturbation of a flat metric on that manifold "
            "(constraint existence check owed to L0/L1)."
        ),
        known_properties=["vacuum (if constraints solved)", "asymptotically flat end",
                          "one end", "non-trivial interior topology", "complete"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="topology.slice_topology",
        deciding_field_alternates=["topology.forbidden", "topology.manifold"],
        deciding_field_status="missing_refinement",
        ambiguity_kind="interior_topology_unconstrained",
        why=(
            "R04 requires only that slice_topology declare connected, complete, one-ended "
            "asymptotically flat. None of those words fixes the interior diffeomorphism type "
            "or forbids a closed summand, and no other required block addresses interior "
            "topology. If F1 mirrors R04 literally, no field decides this datum, although it "
            "changes which theorems apply (spin structures, positive-mass-technique hypotheses) "
            "and is not obviously outside the asymptotically flat literature."
        ),
        falsifier_strength="no_field_decides",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R04"],
        next_falsifier=(
            "Have F1 add an explicit spatial-topology field (e.g. 'slice diffeomorphic to R^3 "
            "outside a compact set' plus a closed-summand prohibition); then this test becomes "
            "decidable and the ambiguity is closed."
        ),
    ),
    row(
        test_id="F1-AMB-09",
        title="Genericity measured on data space vs on development space",
        spacetime_description=(
            "A codimension-one family of non-generic vacuum initial data whose MGHDs foliate an "
            "open set in the space of vacuum developments; the critical family member contains "
            "a naked singularity."
        ),
        known_properties=["vacuum", "asymptotically flat", "non-generic family in data space",
                          "open image in development space", "naked singularity at criticality"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="no",
        does_it_satisfy_f1="ambiguous",
        deciding_field="genericity.ambient_space",
        deciding_field_alternates=["genericity.topology_or_measure", "genericity.generic_set"],
        deciding_field_status="value_dependent",
        ambiguity_kind="genericity_space_choice",
        why=(
            "The data-to-development map is many-to-one and not required to preserve Baire or "
            "measure properties. A family that is codimension-one in data space can be open in "
            "development space. If genericity.ambient_space does not name the space and "
            "topology/measure explicitly, the same datum is generic under one reading and "
            "non-generic under the other, with opposite class verdicts."
        ),
        falsifier_strength="schema_precision_gap",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R07"],
        next_falsifier=(
            "Check whether genericity.ambient_space names both the carrier set and the topology/"
            "measure in one resolvable domain_id; a bare 'data space' string is not enough."
        ),
    ),
    row(
        test_id="F1-AMB-10",
        title="Comeager-but-null genericity instance and vocabulary conflict",
        spacetime_description=(
            "A vacuum datum whose perturbations that preserve genericity form a comeager set in "
            "the Frechet topology on C^inf asymptotically flat data but a null set for every "
            "admissible Gaussian measure on the same space (comeager-and-null instance)."
        ),
        known_properties=["vacuum", "asymptotically flat", "Baire-generic",
                          "measure-zero", "no canonical measure"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="genericity.kind",
        deciding_field_alternates=["genericity.topology_or_measure"],
        deciding_field_status="conflicting_vocabulary",
        ambiguity_kind="cross_artifact_vocabulary_conflict",
        why=(
            "Two binding artifacts use different token sets for the same field: FORM-RULE-SPEC "
            "R07 allows {residual_comeager, full_measure, open_dense_escape, "
            "finite_codimension_complement, none}, while the F0 taxonomy field_vocabulary "
            "allows {baire_residual, dense_open, measure_one, unresolved}. A checker keyed to "
            "one list rejects the other, so no single schema value is simultaneously valid "
            "under both. The spacetime instance above is the semantic reason the conflict "
            "matters: Baire-generic and measure-one are not interchangeable."
        ),
        falsifier_strength="no_field_decides",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R07", f"{TAXONOMY}#field_vocabulary.genericity_kind"],
        next_falsifier=(
            "Ask lead-formulation to freeze one genericity vocabulary and have F1 cite its "
            "sha256; if both lists remain binding, every genericity row is ambiguous."
        ),
    ),
    row(
        test_id="F1-AMB-11",
        title="Visibility by accelerated observer vs visibility by causal geodesic",
        spacetime_description=(
            "A vacuum asymptotically flat development with a future-incomplete timelike "
            "geodesic whose endpoint can be reached from I+ along a causal curve of unbounded "
            "acceleration, while no incomplete causal geodesic from I+ terminates at it."
        ),
        known_properties=["vacuum", "asymptotically flat", "singularity visible to accelerated "
                          "observers", "geodesically not visible"],
        satisfies_in_class="yes",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="visibility.definition",
        deciding_field_alternates=["falsifier.tier_1", "conclusion.text"],
        deciding_field_status="definition_dependent",
        ambiguity_kind="visibility_curve_class",
        why=(
            "WCC is standardly a statement about causal geodesics; some formulations use "
            "bounded-acceleration curves or light rays. The datum is a violation under the "
            "accelerated-observer definition and a non-violation under the geodesic definition. "
            "R10 requires a predicate name and definition, but a definition that does not name "
            "the admissible curve class cannot decide this row."
        ),
        falsifier_strength="schema_precision_gap",
        counterexample_candidate=True,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R10,R14"],
        next_falsifier=(
            "Have F1 state the admissible curve class (causal geodesic / bounded-acceleration "
            "causal curve / light ray) and re-run; if both readings are admitted, the class is "
            "ill-posed."
        ),
    ),
    row(
        test_id="F1-AMB-12",
        title="Partial future null infinity (vacuous conclusion probe)",
        spacetime_description=(
            "Asymptotically flat vacuum data whose MGHD admits a conformal completion in which "
            "a non-empty open set of I+ generators is incomplete (partial I+), and J^-(I+) does "
            "not contain the incomplete region; no incomplete causal geodesic lies in J^-(I+)."
        ),
        known_properties=["vacuum", "asymptotically flat", "partial I+",
                          "conclusion vacuous on J^-(I+)"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="vacuous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="topology.conformal_boundary",
        deciding_field_alternates=["i_plus.completeness_definition", "topology.slice_topology"],
        deciding_field_status="missing_completeness_assertion",
        ambiguity_kind="conformal_boundary_completeness",
        why=(
            "The F0 taxonomy says the class has 'a complete I+ unless the class states "
            "otherwise'. If F1's conformal-boundary block does not assert completeness of I+ "
            "and the i_plus completeness definition only explains what completeness means, then "
            "this datum is admitted with a vacuous conclusion, and no required field decides "
            "whether that is allowed."
        ),
        falsifier_strength="no_field_decides",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R04,R09", f"{TAXONOMY}#asymptotics"],
        next_falsifier=(
            "Demand an explicit boolean completeness assertion in topology.conformal_boundary "
            "(not merely a definition string); then this test is decided."
        ),
    ),
    row(
        test_id="F1-AMB-13",
        title="Low-regularity data and MGHD uniqueness",
        spacetime_description=(
            "Vacuum initial data whose metric regularity is below the threshold for "
            "Choquet-Bruhat-Geroch MGHD uniqueness (e.g. C^0 metric with curvature only in "
            "L^2_loc), for which two non-isometric maximal globally hyperbolic developments are "
            "admitted by the stated regularity class (construction owed to L0/L1)."
        ),
        known_properties=["vacuum (classically)", "low regularity", "MGHD uniqueness not assured",
                          "development choice affects the conclusion"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="regularity.solution_regularity",
        deciding_field_alternates=["regularity.data_regularity", "regularity.extension_solution_concept"],
        deciding_field_status="value_dependent",
        ambiguity_kind="mghd_uniqueness_and_regularity_slot",
        why=(
            "H3 requires that 'the MGHD exists'. Existence and uniqueness of the MGHD depend on "
            "the solution_regularity slot. If F1 leaves solution_regularity unresolved or weak, "
            "the definite article in 'the MGHD' is not licensed, and the class conclusion is "
            "ambiguous for low-regularity data. R06 separates data/solution/I+/extension "
            "regularity, so the deciding value exists in principle but may be unset."
        ),
        falsifier_strength="schema_precision_gap",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R06", f"{TAXONOMY}#H3"],
        next_falsifier=(
            "Check that solution_regularity is a single determinate value strong enough for "
            "MGHD uniqueness, or that the schema states the uniqueness hypothesis separately."
        ),
    ),
    row(
        test_id="F1-AMB-14",
        title="Conical-deficit line: classical vs distributional vacuum",
        spacetime_description=(
            "A spacetime that is Ricci-flat on the complement of a timelike line, around which "
            "the metric has a conical deficit; the distributional Ricci tensor is supported on "
            "the line with magnitude proportional to the deficit angle (standard "
            "conical-singularity computation owed to L0/L1)."
        ),
        known_properties=["classically vacuum off the line", "distributional stress-energy on "
                          "the line", "no curvature singularity", "not C^2 across the line"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="data_class.matter",
        deciding_field_alternates=["regularity.solution_regularity", "regularity.extension_solution_concept"],
        deciding_field_status="value_dependent",
        ambiguity_kind="classical_vs_distributional_vacuum",
        why=(
            "Under 'T = 0 wherever the metric is C^2' the datum is vacuum and in class; under "
            "'the metric solves the vacuum Einstein equations as a distribution' it is not "
            "vacuum. R05's matter slot and R06's regularity/extension_solution_concept slots "
            "together must state which reading is binding; if either is silent the test is "
            "undecided."
        ),
        falsifier_strength="schema_precision_gap",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R05,R06", f"{TAXONOMY}#matter_model"],
        next_falsifier=(
            "Require matter to name the solution concept (classical vs distributional); then "
            "the datum is decidable one way."
        ),
    ),
    row(
        test_id="F1-AMB-15",
        title="Unstated hypotheses of the 'equivalently' clause in the conclusion",
        spacetime_description=(
            "Hypothetical vacuum datum with a marginally trapped surface and a complete "
            "development: it would break the schema's asserted equivalence between (a) causal "
            "geodesic completeness inside J^-(I+) and (b) non-empty interior of B = M \\ J^-(I+) "
            "if the regularity and energy hypotheses under which Penrose-type incompleteness "
            "applies are not stated. No such vacuum example is known to this worker."
        ),
        known_properties=["vacuum", "asymptotically flat", "trapped surface",
                          "complete development (hypothetical)", "tests an equivalence claim"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field=None,
        deciding_field_alternates=["conclusion.equivalence_claim", "conclusion.text",
                                   "conclusion.epistemic_status"],
        deciding_field_status="no_required_field",
        ambiguity_kind="unstated_equivalence_hypotheses",
        why=(
            "The conclusion asserts 'equivalently' between a geodesic-visibility statement and "
            "a black-hole-interior statement. R11 requires only conclusion_type, "
            "epistemic_status and forbidden_strengthenings; no required field records whether "
            "the equivalence is definitional, conditional on a theorem, or restricted to a "
            "regularity class. A gate-passing schema can therefore assert an equivalence whose "
            "hypotheses are unstated. This is the suite's explicit 'no schema field decides' "
            "row: it is the declared falsifier of the assignment."
        ),
        falsifier_strength="no_field_decides",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R11", f"{TAXONOMY}#conclusion"],
        next_falsifier=(
            "Add a required conclusion.equivalence_claim field with values "
            "{definitional, conditional_theorem, not_asserted} plus its hypotheses; then this "
            "row is decided and the no-field-decides falsifier is closed."
        ),
    ),
    row(
        test_id="F1-AMB-16",
        title="Conclusion-type key collision: class family vs epistemic status",
        spacetime_description=(
            "Schema-level test, instantiated by any asymptotically flat vacuum datum: which value "
            "is the schema's conclusion_type? FORM-RULE-SPEC R11 requires "
            "conclusion.conclusion_type = weak_cosmic_censorship, while revision 2 stores the "
            "class family in conclusion.family, the epistemic status in conclusion.type = "
            "open_problem, and the F0 slot value in vocabulary_alignment.f0_slot_conclusion_type."
        ),
        known_properties=["schema-level", "no spacetime counterexample required",
                          "contract leaf absent under its R11 name"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="ambiguous",
        does_it_satisfy_f1="ambiguous",
        deciding_field="conclusion.conclusion_type",
        deciding_field_alternates=["conclusion.family", "vocabulary_alignment.f0_slot_conclusion_type",
                                   "conclusion.type"],
        deciding_field_status="contract_name_collision",
        ambiguity_kind="conclusion_type_name_collision",
        why=(
            "A checker keyed to R11 finds conclusion.conclusion_type absent. A checker that falls "
            "back to conclusion.type reads 'open_problem' and may report conclusion inflation or "
            "deflation. The intended value exists only under a different key. The schema's "
            "vocabulary_alignment block explains the collision but no machine-readable mapping "
            "is provided, so the gate cannot decide which key is authoritative."
        ),
        falsifier_strength="no_field_decides",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R11", f"{TAXONOMY}#field_vocabulary.conclusion_type",
                                       "schemas/af_wcc_vacuum.yaml#vocabulary_alignment"],
        next_falsifier=(
            "Add a name map (R11 leaf -> schema path) accepted by lead-formulation; then run the "
            "gate and this test becomes decidable."
        ),
    ),
    row(
        test_id="F1-AMB-17",
        title="Single-point vs open-set visibility (strength of the conclusion)",
        spacetime_description=(
            "A vacuum asymptotically flat development in which exactly one future boundary point "
            "is visible from I+ (a single incomplete null geodesic terminates at a naked point), "
            "while no open set of boundary points is visible."
        ),
        known_properties=["vacuum", "asymptotically flat", "one visible singular boundary point",
                          "no open set of visible boundary points"],
        satisfies_in_class="ambiguous",
        satisfies_conclusion="fails under point reading; holds under open-set reading",
        does_it_satisfy_f1="ambiguous",
        deciding_field="visibility.definition",
        deciding_field_alternates=["visibility.negation_conclusion", "i_plus.visibility.set_vs_point"],
        deciding_field_status="class_decision_point_reading",
        ambiguity_kind="set_vs_point_visibility",
        why=(
            "Single-point visibility and open-set visibility define different strengths: the "
            "datum refutes the point reading and satisfies the open-set reading. Revision 3 pins "
            "the point reading in the class definition, which closes the ambiguity by decision; "
            "whether A1 accepts that strength is a review question, and the set-valued variant is "
            "recorded as defining a different class."
        ),
        falsifier_strength="decided",
        counterexample_candidate=False,
        evidence_refs=CONTRACT_REFS + [f"{CONTRACT}#R10", f"{TAXONOMY}#conclusion"],
        next_falsifier=(
            "If A1 rules that WCC must hide an open set of boundary points, the class definition "
            "changes and this datum moves from a counterexample to a non-counterexample."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Rebinding overlay for F1 revision 2.
#
# The tests were authored against the FORM-RULE-SPEC vocabulary while the F1
# artifact was absent.  Revision 2 landed at 23:26+08:00; the overlay below moves
# each row's primary `deciding_field` onto the schema's actual path, records the
# contract path separately, and states what revision 2 does about the probe.
# `schema_open_expected` is the suite's own expectation for the runner; it is not
# a verification result.
# ---------------------------------------------------------------------------
SCHEMA_BINDING_R2_SUPERSEDED = {
    "F1-AMB-01": dict(
        deciding_field="non_vacuity.condition", deciding_field_contract="non_vacuity.condition",
        deciding_field_alternates=["data_class.mass", "conclusion.conclusion_scope"],
        deciding_field_status="missing_block_required_by_R08", schema_open_expected=True,
        schema_finding=("R08 requires a non_vacuity block; revision 2 has none. data_class.mass "
                        "excludes the Minkowski point from the generic slice but is not a "
                        "non-vacuity condition, so the probe stays undecided.")),
    "F1-AMB-02": dict(
        deciding_field="quantifiers.scope_of_universal", deciding_field_contract="quantifiers.ordered",
        deciding_field_alternates=["quantifiers.genericity_placement", "genericity.kind"],
        deciding_field_status="resolved_generic_first_declared_unresolved", schema_open_expected=True,
        schema_finding=("Revision 2 pins generic-first quantification and states that data outside "
                        "D_gen are 'the expected home of known naked-singularity constructions'; the "
                        "critical datum is therefore not a counterexample. unresolved[0] declares "
                        "that meagreness of the known exceptional families is unproven.")),
    "F1-AMB-03": dict(
        deciding_field="genericity.kind", deciding_field_contract="genericity.generic_set",
        deciding_field_alternates=["quantifiers.scope_of_universal", "i_plus.visibility.definition"],
        deciding_field_status="resolved_family_outside_D_gen", schema_open_expected=False,
        schema_finding=("Baire-residual genericity on D_w excludes finite-dimensional families "
                        "(Kerr) from D_gen up to the standard 'proper closed subspace is meagre' "
                        "step; the J^-(I+) clause additionally protects the interior ring "
                        "singularity. No source for the topological step is claimed here.")),
    "F1-AMB-04": dict(
        deciding_field="data_class.mass", deciding_field_contract="class_components.symmetry",
        deciding_field_alternates=["class_axes.symmetry", "topology.symmetry"],
        deciding_field_status="resolved_by_mass_causality_declared_unresolved", schema_open_expected=True,
        schema_finding=("data_class.mass requires the ADM 4-momentum to be causal (E >= |P|), which "
                        "excludes M < 0 as written. unresolved[7] declares that whether a strict "
                        "positivity/lower bound belongs to the class or the generic subset is a "
                        "lead-formulation decision, and the symmetry fields remain class-level.")),
    "F1-AMB-05": dict(
        deciding_field="class_axes.matter_model", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["matter"], deciding_field_status="determinate",
        schema_open_expected=False,
        schema_finding="Electrovacuum is excluded by matter_model = vacuum and by the T = 0 statement."),
    "F1-AMB-06": dict(
        deciding_field="class_axes.matter_model", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["class_id", "class_separation.frozen_class_ids"],
        deciding_field_status="determinate", schema_open_expected=False,
        schema_finding="Scalar matter is excluded twice: by matter_model and by the frozen class id."),
    "F1-AMB-07": dict(
        deciding_field="topology.symmetry", deciding_field_contract="class_components.symmetry",
        deciding_field_alternates=["class_axes.symmetry"], deciding_field_status="class_level_vs_instance_level",
        schema_open_expected=True,
        schema_finding=("Revision 2 states 'none assumed' at the class level but provides no "
                        "datum-level field excluding a symmetric instance; the AMB-04/AMB-07 pair "
                        "still receives opposite inclusion verdicts under the two readings.")),
    "F1-AMB-08": dict(
        deciding_field="topology.initial_slice_topology", deciding_field_contract="topology.slice_topology",
        deciding_field_alternates=["topology.manifold"], deciding_field_status="declared_unresolved_by_schema",
        schema_open_expected=True,
        schema_finding=("The field says 'canonical case: Sigma diffeomorphic to R^3' but does not "
                        "exclude an exotic interior; unresolved[2] explicitly declares "
                        "R^3-versus-general-one-ended open. The schema acknowledges the gap rather "
                        "than silently deciding it.")),
    "F1-AMB-09": dict(
        deciding_field="genericity.parameter_space", deciding_field_contract="genericity.ambient_space",
        deciding_field_alternates=["genericity.topology_name", "genericity.kind"],
        deciding_field_status="resolved_to_data_space_declared_unresolved", schema_open_expected=True,
        schema_finding=("genericity.parameter_space names the weighted data space (not the space of "
                        "developments) and topology_name names the norm topology; the data-space "
                        "reading is therefore fixed. unresolved[0] keeps the genericity proposal "
                        "unreviewed.")),
    "F1-AMB-10": dict(
        deciding_field="genericity.kind", deciding_field_contract="genericity.kind",
        deciding_field_alternates=["class_axes.genericity_kind"], deciding_field_status="conflicting_vocabulary",
        schema_open_expected=True,
        schema_finding=("Revision 2 uses the F0 token 'baire_residual' (class_axes) and prose "
                        "'Baire residual, comeagre' (genericity.kind), while R07 requires one of "
                        "{residual_comeager, full_measure, open_dense_escape, "
                        "finite_codimension_complement, none}. No mapping is provided; a gate "
                        "keyed to R07 rejects the F0 token.")),
    "F1-AMB-11": dict(
        deciding_field="i_plus.visibility.curve_class", deciding_field_contract="visibility.definition",
        deciding_field_alternates=["i_plus.visibility.definition"],
        deciding_field_status="resolved_to_geodesic_reading_declared_unresolved", schema_open_expected=True,
        schema_finding=("curve_class explicitly proposes the geodesic reading, records the "
                        "causal-curve alternative, and states the two are not equivalent in "
                        "general; unresolved[3] leaves the choice to A1 plus a primary source.")),
    "F1-AMB-12": dict(
        deciding_field="i_plus.defining_properties", deciding_field_contract="topology.conformal_boundary",
        deciding_field_alternates=["i_plus.name"], deciding_field_status="resolved_explicit_completeness",
        schema_open_expected=False,
        schema_finding=("I+ future-completeness is an explicit defining property and sits inside "
                        "the conclusion (existence of the completion is not assumed of the data), "
                        "so the partial-I+ vacuity probe is closed.")),
    "F1-AMB-13": dict(
        deciding_field="premise.regularity_of_development", deciding_field_contract="regularity.solution_regularity",
        deciding_field_alternates=["data_class.regularity"],
        deciding_field_status="resolved_C2_declared_unresolved", schema_open_expected=True,
        schema_finding=("The development is pinned to C^2, which restores a definite article for "
                        "the MGHD in the canonical case; unresolved[6] declares the interaction "
                        "between that regularity and the definition of singular points open.")),
    "F1-AMB-14": dict(
        deciding_field="matter", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["premise.regularity_of_development"],
        deciding_field_status="resolved_classical_reading", schema_open_expected=False,
        schema_finding=("T = 0 plus a C^2 development excludes a C^0 conical-defect metric from "
                        "the solution concept; the distributional reading is not separately "
                        "declared but is not admitted by the regularity premise.")),
    "F1-AMB-15": dict(
        deciding_field="i_plus.equivalence_status", deciding_field_contract="conclusion.equivalence_claim",
        deciding_field_alternates=["conclusion.f0_equivalent_form"],
        deciding_field_status="explicitly_unverified", schema_open_expected=True,
        schema_finding=("Revision 2 records the equivalence as 'unverified' (i_plus.equivalence_status) "
                        "and explains the F0 form under conclusion.f0_equivalent_form, so a field "
                        "does exist. R11 does not require it, so a gate keyed to R11 cannot see it; "
                        "the no-field-decides attack is downgraded to a gate-coverage gap.")),
    "F1-AMB-16": dict(
        deciding_field="conclusion.conclusion_type", deciding_field_contract="conclusion.conclusion_type",
        deciding_field_alternates=["conclusion.family", "vocabulary_alignment.f0_slot_conclusion_type",
                                   "conclusion.type"],
        deciding_field_status="contract_name_collision", schema_open_expected=True,
        schema_finding=("The R11 leaf conclusion.conclusion_type is absent; its intended value is "
                        "split across conclusion.family and vocabulary_alignment, while "
                        "conclusion.type carries the epistemic status. A fallback checker reads "
                        "'open_problem' and can misreport inflation; no name map is provided.")),
}


# ---------------------------------------------------------------------------
# Current binding: F1 revision 3 as settled at sha256 7a3e1f93...
#
# The F1 artifact was revised while this suite was being authored (r2 f15ea523,
# r3 f55722a7, r3-amended a7ef0398, r3-settled 7a3e1f93; same revision number).
# All rows are bound to the snapshot kept at
# artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.7a3e1f93.yaml.
# `schema_open_expected` is the runner-level expectation (determinate deciding
# value and no matching entry in the schema's own `unresolved` list).
# `falsifier_strength != "decided"` marks rows that remain review findings even
# when the structural value is determinate.
# ---------------------------------------------------------------------------
SCHEMA_BINDING_R3_SUPERSEDED = {
    "F1-AMB-01": dict(
        deciding_field="non_vacuity.condition", deciding_field_contract="non_vacuity.condition",
        deciding_field_alternates=["non_vacuity.witness_type", "data_class.adm_mass_status"],
        deciding_field_status="resolved_non_vacuity_declared_unresolved", schema_open_expected=True,
        falsifier_strength="declared_unresolved",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="vacuous",
        schema_finding=("r3 adds the R08 non_vacuity block with an explicit condition and names "
                        "Minkowski as the vacuous case it excludes; witness_status is 'unresolved' "
                        "and unresolved[non_vacuity.witness] states that no family is verified to "
                        "lie in D_gen while being future-incomplete. Minkowski data are excluded "
                        "from D_gen by adm_mass_status, and the class conclusion must not be "
                        "called non-trivial until a witness is filed.")),
    "F1-AMB-02": dict(
        deciding_field="genericity.excluded_set", deciding_field_contract="quantifiers.ordered",
        deciding_field_alternates=["quantifiers.ordered", "genericity.kind", "falsifier.tier_1"],
        deciding_field_status="resolved_critical_data_named_in_excluded_set", schema_open_expected=True,
        falsifier_strength="counterexample_candidate",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="fails if in D_gen",
        schema_finding=("r3 puts generic-first quantification in quantifiers.ordered and names "
                        "'fine-tuned threshold data of type-II critical collapse' as candidate "
                        "E_gen members (not asserted); tier_1 requires an open/residual violating "
                        "set. The critical datum is therefore outside the quantified domain by "
                        "design, but whether that family is meagre in the named topology stays "
                        "unresolved (genericity.kind_and_ambient_space), so the exclusion is "
                        "provisional.")),
    "F1-AMB-03": dict(
        deciding_field="genericity.generic_set", deciding_field_contract="genericity.generic_set",
        deciding_field_alternates=["quantifiers.ordered", "genericity.kind", "genericity.ambient_space",
                                   "visibility.predicate"],
        deciding_field_status="resolved_family_outside_D_gen_topological_step_unstated",
        schema_open_expected=True, falsifier_strength="schema_precision_gap",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="fails if in D_gen",
        schema_finding=("D_gen is a countable intersection of open dense sets, so a "
                        "finite-dimensional family such as Kerr is meagre by the standard "
                        "closed-proper-subspace argument. The schema does not state that step, and "
                        "the genericity proposal itself is declared unresolved; the J^-(I+) "
                        "predicate additionally protects the interior ring singularity.")),
    "F1-AMB-04": dict(
        deciding_field="data_class.adm_mass_status", deciding_field_contract="class_components.symmetry",
        deciding_field_alternates=["class_components.symmetry", "topology.forbidden"],
        deciding_field_status="resolved_by_causal_ADM_decision", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=("r3 decides that no strict positivity bound E > 0 is imposed and that "
                        "D_w admits all causal ADM 4-momenta; M < 0 fails E >= |P|, so negative-mass "
                        "Schwarzschild is excluded by data_class.adm_mass_status. The earlier "
                        "positivity question is closed; the symmetry reading it exposed is tracked "
                        "separately in AMB-07.")),
    "F1-AMB-05": dict(
        deciding_field="data_class.matter", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["class_components.matter_model"], deciding_field_status="determinate",
        schema_open_expected=False, falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding="Electrovacuum is excluded by data_class.matter = none (vacuum)."),
    "F1-AMB-06": dict(
        deciding_field="class_components.matter_model", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["class_id", "data_class.matter"], deciding_field_status="determinate",
        schema_open_expected=False, falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding="Scalar matter is excluded by the class components and the frozen class id."),
    "F1-AMB-07": dict(
        deciding_field="class_components.symmetry", deciding_field_contract="class_components.symmetry",
        deciding_field_alternates=["topology.symmetry", "class_axes.symmetry"],
        deciding_field_status="class_level_vs_instance_level_undeclared", schema_open_expected=False,
        falsifier_strength="interpretation_undeclared",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="yes",
        schema_finding=("Three symmetry slots say 'none_assumed', but that is a class-level "
                        "hypothesis; no field excludes a single symmetric datum, and symmetry does "
                        "not appear in the unresolved list. AMB-04 (excluded by mass) and AMB-07 "
                        "(spherical vacuum) still receive opposite membership verdicts under the "
                        "two readings. This is the sharpest undeclared gap the suite found: the "
                        "structural value is determinate, the interpretation is not.")),
    "F1-AMB-08": dict(
        deciding_field="topology.slice_topology", deciding_field_contract="topology.slice_topology",
        deciding_field_alternates=["topology.slice_topology_class_decision", "topology.forbidden"],
        deciding_field_status="class_decision_recorded_constraint_existence_undecided", schema_open_expected=False,
        falsifier_strength="schema_precision_gap",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="holds if in D_gen",
        schema_finding=("r3 records an explicit F1 class decision: any connected complete one-ended "
                        "asymptotically flat slice is admitted, with R^3 as the canonical instance. "
                        "The lens-space-summand datum is therefore admitted by decision rather than "
                        "silently. Whether vacuum constraint data exist on such a slice, and whether the "
                        "class requires solvability on every admitted topology, is not decided by any "
                        "field; whether A1 accepts the breadth is a review question, and the residual "
                        "only concerns additional ends.")),
    "F1-AMB-09": dict(
        deciding_field="genericity.ambient_space", deciding_field_contract="genericity.ambient_space",
        deciding_field_alternates=["genericity.kind", "genericity.topology_or_measure"],
        deciding_field_status="resolved_to_data_space_declared_unresolved", schema_open_expected=True,
        falsifier_strength="declared_unresolved",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="fails if in D_gen",
        schema_finding=("genericity.ambient_space names D_w (data space) and topology_or_measure "
                        "names the H^4_{1/2+eps} norm topology, so the data-space reading is fixed "
                        "and the many-to-one data-to-development objection does not change "
                        "membership. The genericity proposal is still declared unresolved.")),
    "F1-AMB-10": dict(
        deciding_field="genericity.kind", deciding_field_contract="genericity.kind",
        deciding_field_alternates=["class_axes.genericity_kind", "genericity.transfer_failures"],
        deciding_field_status="cross_slot_token_divergence", schema_open_expected=True,
        falsifier_strength="cross_artifact_token_divergence",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="ambiguous",
        schema_finding=("The contract slot genericity.kind uses the R07 token 'residual_comeager', "
                        "while class_axes.genericity_kind keeps the F0 token 'baire_residual'; "
                        "vocabulary_alignment reconciles conclusion_type only. No mapping between "
                        "the two genericity token sets is provided, so an R07-keyed checker and an "
                        "F0-axis checker read the same class differently, and the underlying "
                        "genericity claim is in any case declared unresolved.")),
    "F1-AMB-11": dict(
        deciding_field="visibility.definition", deciding_field_contract="visibility.definition",
        deciding_field_alternates=["i_plus.completeness_definition", "conclusion.equivalence_claim"],
        deciding_field_status="class_decision_geodesic_reading", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="yes", satisfies_in_class="yes", satisfies_conclusion="yes under the geodesic reading",
        schema_finding=("r3 records an F1 class decision for geodesic completeness and keeps the "
                        "causal-curve alternative as a non-equivalent variant; the equivalence "
                        "question is carried by conclusion.equivalence_claim and tracked in "
                        "AMB-15. The accelerated-observer datum is not a counterexample under the "
                        "decided reading.")),
    "F1-AMB-12": dict(
        deciding_field="i_plus.completeness_definition", deciding_field_contract="topology.conformal_boundary",
        deciding_field_alternates=["i_plus.in_conclusion", "i_plus.role"],
        deciding_field_status="resolved_explicit_completeness", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails for partial-completion data; not vacuous",
        schema_finding=("I+ future-completeness is a defining property and sits inside the "
                        "conclusion (existence of the completion is not assumed of the data), so "
                        "data admitting only a partial I+ fail the conclusion rather than passing "
                        "it vacuously. Membership in D_gen remains a separate question.")),
    "F1-AMB-13": dict(
        deciding_field="regularity.solution_regularity", deciding_field_contract="regularity.solution_regularity",
        deciding_field_alternates=["regularity.data_regularity"], deciding_field_status="resolved_C2_excludes_datum",
        schema_open_expected=False, falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=("The development is pinned to a C^2 Lorentzian metric and the data class "
                        "to H^4_loc / H^3_loc, which restores a definite article for the MGHD in "
                        "the canonical case; no regularity entry remains in the unresolved list.")),
    "F1-AMB-14": dict(
        deciding_field="data_class.matter", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["regularity.solution_regularity", "regularity.extension_solution_concept"],
        deciding_field_status="resolved_classical_reading", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=("T = 0 plus a C^2 development excludes a C^0 conical-defect metric from the "
                        "solution concept; the distributional reading is not admitted by the "
                        "regularity premise, and extension_solution_concept is explicitly not "
                        "asserted.")),
    "F1-AMB-15": dict(
        deciding_field="conclusion.equivalence_claim", deciding_field_contract="conclusion.equivalence_claim",
        deciding_field_alternates=["conclusion.conclusion_type", "i_plus.equivalence_status"],
        deciding_field_status="explicitly_unverified", schema_open_expected=True,
        falsifier_strength="explicitly_unverified",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="ambiguous",
        schema_finding=("r3 adds conclusion.equivalence_claim with status 'unverified' and records "
                        "the F0 phrasing under variants, so the schema now owns the equivalence "
                        "question instead of leaving it implicit. The equivalence itself remains "
                        "unproven and is a named A1 item.")),
    "F1-AMB-16": dict(
        deciding_field="conclusion.conclusion_type", deciding_field_contract="conclusion.conclusion_type",
        deciding_field_alternates=["conclusion.epistemic_status", "vocabulary_alignment.f0_slot_conclusion_type"],
        deciding_field_status="resolved_contract_leaf_present", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="yes", satisfies_in_class="yes", satisfies_conclusion="weak_cosmic_censorship",
        schema_finding=("r3 implements the R11 leaf exactly: conclusion.conclusion_type = "
                        "weak_cosmic_censorship, with the epistemic status separated into "
                        "conclusion.epistemic_status = open_problem and the collision documented in "
                        "vocabulary_alignment. The r2 name collision is closed.")),
    "F1-AMB-17": dict(
        deciding_field="visibility.definition", deciding_field_contract="visibility.definition",
        deciding_field_alternates=["visibility.negation_conclusion", "visibility.set_vs_point"],
        deciding_field_status="class_decision_point_reading", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails under point reading; holds under set reading",
        schema_finding=("r3 records the class decision that single-point visibility is the "
                        "definition and that the set-valued variant is strictly stronger and would "
                        "define a different class. The single-visible-point datum is therefore a "
                        "counterexample by decision, not by ambiguity; if A1 prefers the set-valued "
                        "reading this becomes a direction update, not a silent reinterpretation.")),
}


def _apply_schema_binding(tests: list[dict]) -> None:
    from binding_rev4 import BINDING_META, SCHEMA_BINDING_REV4

    for t in tests:
        nb = SCHEMA_BINDING_REV4[t["test_id"]]
        t["deciding_field_contract"] = nb["deciding_field_contract"]
        t["deciding_field"] = nb["deciding_field"]
        t["deciding_field_alternates"] = nb["deciding_field_alternates"]
        t["deciding_field_status"] = nb["deciding_field_status"]
        t["schema_finding"] = nb["schema_finding"]
        t["schema_open_expected"] = nb["schema_open_expected"]
        t["unresolved_keywords"] = nb.get("unresolved_keywords", [])
        t["falsifier_strength"] = nb.get("falsifier_strength", t["falsifier_strength"])
        for key in ("does_it_satisfy_f1", "satisfies_in_class", "satisfies_conclusion"):
            if key in nb:
                t[key] = nb[key]
        t["binding_at_authoring"] = BINDING_META["binding_at_authoring"]
        t["schema_under_test"] = BINDING_META["schema_under_test"]
        t["schema_snapshot"] = BINDING_META["schema_snapshot"]


def main() -> int:
    _apply_schema_binding(TESTS)
    ids = [t["test_id"] for t in TESTS]
    assert len(ids) == len(set(ids)), "duplicate test ids"
    assert len(TESTS) >= 10, "acceptance requires >=10 tests"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(t, sort_keys=True, ensure_ascii=True) + "\n" for t in TESTS)
    OUT.write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    no_field = [t["test_id"] for t in TESTS if t["deciding_field"] is None]
    expected_open = [t["test_id"] for t in TESTS if t.get("schema_open_expected")]
    print(f"wrote {OUT} rows={len(TESTS)} sha256={digest}")
    print(f"no_field_decides_rows={no_field}")
    print(f"schema_open_expected={expected_open}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
