"""Binding overlay for the FROZEN F1 revision 4.

Frozen artifact: `artifacts/formulation/schemas/af_wcc_vacuum.yaml`
sha256 f512af5f4db39b029fdfe900699d69fa4d9220f75080faf9713006321309381c
pinned in `artifacts/formulation/FROZEN.json` (revision 4; the 23:33:37 message cited
17873b9d, which the manifest superseded at 23:35:45 with f512af5f).

Lead-formulation's rulings are in
`artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md`; the frozen
companion vocabulary map is `artifacts/formulation/VOCAB_ALIASES.json`.

`schema_open_expected` is the runner-level expectation:
determinate deciding value AND no matching entry in `unresolved` /
`unresolved_items` (via `unresolved_keywords`).

`falsifier_strength`:
  decided                 - field determines the answer for this probe
  decided_by_ruling       - determined by a recorded lead ruling
  decided_by_alias_file   - determined with the frozen VOCAB_ALIASES companion
  accepted_obligation     - lead accepted it as a declared open proof obligation
"""

BINDING_META = {
    "schema_under_test": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "schema_sha256": "f512af5f4db39b029fdfe900699d69fa4d9220f75080faf9713006321309381c",
    "schema_snapshot": ("artifacts/flash-04/f1_ambiguity/schema_snapshots/"
                        "af_wcc_vacuum.f512af5f.yaml"),
    "binding_at_authoring": (
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
        "#sha256:f512af5f4db39b029fdfe900699d69fa4d9220f75080faf9713006321309381c"
        " (frozen revision 4 via artifacts/formulation/FROZEN.json; snapshot in "
        "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.f512af5f.yaml)"
    ),
}

SCHEMA_BINDING_REV4 = {
    "F1-AMB-01": dict(
        deciding_field="non_vacuity.condition",
        deciding_field_contract="non_vacuity.condition",
        deciding_field_alternates=["non_vacuity.status", "non_vacuity.vacuity_falsifier"],
        deciding_field_status="accepted_open_obligation", schema_open_expected=True,
        falsifier_strength="accepted_obligation",
        unresolved_keywords=["non-vacuity", "witness"],
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="vacuous",
        schema_finding=(
            "Rev4 keeps the non-vacuity condition and adds vacuity_falsifier; status is "
            "'UNVERIFIED here'. Adjudication (ADJUDICATION_flash04_ambiguity.md) accepts this as a "
            "declared open obligation, and unresolved_items lists non-vacuity witness membership as "
            "UNVERIFIED. Not a silent closure.")),
    "F1-AMB-02": dict(
        deciding_field="genericity.excluded_set",
        deciding_field_contract="quantifiers.ordered",
        deciding_field_alternates=["genericity.excluded_set_status", "genericity.generic_set"],
        deciding_field_status="accepted_open_obligation", schema_open_expected=True,
        falsifier_strength="accepted_obligation",
        unresolved_keywords=["meager", "self-similar", "critical"],
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails if in G",
        schema_finding=(
            "Rev4 lists self-similar/scale-invariant and finite-dimensional analytic families as "
            "candidates that must be shown meager or explicitly excluded; excluded_set_status is "
            "unresolved and unresolved_items says the meagerness is UNVERIFIED. Adjudication accepts "
            "this as a theorem obligation.")),
    "F1-AMB-03": dict(
        deciding_field="genericity.excluded_set",
        deciding_field_contract="genericity.generic_set",
        deciding_field_alternates=["genericity.excluded_set_status", "genericity.generic_set"],
        deciding_field_status="accepted_open_obligation", schema_open_expected=True,
        falsifier_strength="accepted_obligation",
        unresolved_keywords=["meager", "killing", "finite-dimensional", "analytic"],
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails if in G",
        schema_finding=(
            "The closed-proper-subspace argument is explicitly not assumed: adjudication says it "
            "must be stated, and excluded_set_status stays unresolved. Kerr-type finite-dimensional "
            "families are a named meagerness obligation.")),
    "F1-AMB-04": dict(
        deciding_field="data_class.adm_mass",
        deciding_field_contract="class_components.symmetry",
        deciding_field_alternates=["data_class.excluded_data", "data_class.symmetry"],
        deciding_field_status="resolved_positive_mass", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=(
            "Rev4 asserts m_ADM >= 0 by the positive mass theorem with the Minkowski rigidity case; "
            "negative-mass Schwarzschild is excluded at the data-class level. data_class.excluded_data "
            "adds that non-generic subfamilies are members of other classes, not counterexamples.")),
    "F1-AMB-05": dict(
        deciding_field="data_class.matter", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["class_components.matter"], deciding_field_status="determinate",
        schema_open_expected=False, falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding="Electrovacuum is excluded by data_class.matter = none."),
    "F1-AMB-06": dict(
        deciding_field="data_class.matter", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["class_id"], deciding_field_status="determinate",
        schema_open_expected=False, falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding="Scalar matter is excluded by the frozen class id and the matter slot."),
    "F1-AMB-07": dict(
        deciding_field="genericity.membership_ruling",
        deciding_field_contract="class_components.symmetry",
        deciding_field_alternates=["data_class.symmetry", "genericity.excluded_set"],
        deciding_field_status="ruled_set_level_membership", schema_open_expected=False,
        falsifier_strength="decided_by_ruling",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="yes",
        schema_finding=(
            "RULED: membership is set-level only. The class quantifies over a comeager set G and the "
            "schema does not decide membership of an individual datum; symmetric data are expected "
            "outside G but that expectation is a proof obligation. Ruling recorded in "
            "genericity.membership_ruling and the adjudication doc. Delta: the undeclared "
            "interpretation gap is closed by an explicit ruling.")),
    "F1-AMB-08": dict(
        deciding_field="topology.slice_topology",
        deciding_field_contract="topology.slice_topology",
        deciding_field_alternates=["topology.end_structure", "data_class.excluded_data"],
        deciding_field_status="resolved_R3_only", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=(
            "Delta: frozen rev4 narrows the slice to a complete Riemannian 3-manifold diffeomorphic "
            "to R^3 with exactly one asymptotically flat end, so the lens-space-summand datum is "
            "excluded. The r3 breadth decision is reverted; the constraint-solvability concern is "
            "subsumed by the non-vacuity condition and the declared obligations.")),
    "F1-AMB-09": dict(
        deciding_field="genericity.ambient_space_is_data_space",
        deciding_field_contract="genericity.ambient_space",
        deciding_field_alternates=["genericity.ambient_space", "genericity.membership_ruling"],
        deciding_field_status="ruled_data_space", schema_open_expected=False,
        falsifier_strength="decided_by_ruling",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails if in G",
        schema_finding=(
            "RULED: the ambient space is the data space (explicit "
            "genericity.ambient_space_is_data_space = true); the development is not an element of the "
            "ambient space. Delta: closed by ruling.")),
    "F1-AMB-10": dict(
        deciding_field="genericity.kind", deciding_field_contract="genericity.kind",
        deciding_field_alternates=["genericity.vocabulary_aliases_ref", "class_components.genericity"],
        deciding_field_status="resolved_by_vocab_aliases", schema_open_expected=False,
        falsifier_strength="decided_by_alias_file",
        does_it_satisfy_f1="yes", satisfies_in_class="yes", satisfies_conclusion="weak_cosmic_censorship",
        schema_finding=(
            "RULED: one canonical token residual_comeager, with baire_residual and "
            "provisional_baire_residual accepted aliases in the frozen companion "
            "artifacts/formulation/VOCAB_ALIASES.json (referenced by "
            "genericity.vocabulary_aliases_ref). Delta: the token duality is resolved by an external "
            "frozen alias map rather than by a single in-file vocabulary.")),
    "F1-AMB-11": dict(
        deciding_field="visibility.definition", deciding_field_contract="visibility.definition",
        deciding_field_alternates=["visibility.singularity_definition", "visibility.must_not_conflate"],
        deciding_field_status="resolved_geodesic", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="yes", satisfies_in_class="yes",
        satisfies_conclusion="yes under the frozen geodesic reading",
        schema_finding=(
            "Rev4 defines visibility through future-inextendible causal geodesics of finite affine "
            "length and adds witness_protocol plus observability_note; the accelerated-observer "
            "datum is not a counterexample under the frozen definition.")),
    "F1-AMB-12": dict(
        deciding_field="i_plus.completeness_definition",
        deciding_field_contract="topology.conformal_boundary",
        deciding_field_alternates=["i_plus.completeness_definition_status", "i_plus.required_properties"],
        deciding_field_status="resolved_explicit_completeness", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails for partial-completion data; not vacuous",
        schema_finding=(
            "Generator completeness of I+ is explicit, and completeness_definition_status records "
            "that this is a definitional restatement, NOT the unverified equivalence to future "
            "asymptotic predictability (reviewer 16 F1-16-01). Partial-I+ data fail the conclusion "
            "rather than passing vacuously.")),
    "F1-AMB-13": dict(
        deciding_field="regularity.solution_regularity",
        deciding_field_contract="regularity.solution_regularity",
        deciding_field_alternates=["regularity.data_regularity", "regularity.existence_theorem"],
        deciding_field_status="resolved_smooth_or_Hs", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=(
            "Rev4 pins smooth-with-decay data or H^s_delta with s > 5/2 and a C^infinity (H^s_loc) "
            "development; the C^0 low-regularity datum is excluded, so the MGHD-uniqueness probe is "
            "decided against membership.")),
    "F1-AMB-14": dict(
        deciding_field="data_class.matter", deciding_field_contract="data_class.matter",
        deciding_field_alternates=["regularity.solution_regularity", "regularity.extension_solution_concept"],
        deciding_field_status="resolved_classical_solution_concept", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="no", satisfies_in_class="no", satisfies_conclusion="n/a",
        schema_finding=(
            "Matter is none and extension_solution_concept is not asserted; a C^0 conical-defect "
            "metric is outside the smooth/H^s solution concept, so the classical-vs-distributional "
            "probe is decided against membership.")),
    "F1-AMB-15": dict(
        deciding_field="conclusion.equivalent_standard_formulation",
        deciding_field_contract="conclusion.equivalence_claim",
        deciding_field_alternates=["conclusion.statement_formal", "conclusion.conclusion_type"],
        deciding_field_status="accepted_open_obligation", schema_open_expected=True,
        falsifier_strength="accepted_obligation",
        unresolved_keywords=["equivalence", "asymptotic predictability"],
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous", satisfies_conclusion="ambiguous",
        schema_finding=(
            "Rev4 binds the class to statement_formal and marks the equivalent standard formulation "
            "as 'claimed equivalence, UNVERIFIED'; adjudication accepts it as a declared open L1 "
            "obligation. Delta: field renamed and explicitly gated, still open.")),
    "F1-AMB-16": dict(
        deciding_field="conclusion.conclusion_type",
        deciding_field_contract="conclusion.conclusion_type",
        deciding_field_alternates=["conclusion.epistemic_status", "conclusion.family"],
        deciding_field_status="resolved_contract_leaf", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="yes", satisfies_in_class="yes", satisfies_conclusion="weak_cosmic_censorship",
        schema_finding=(
            "Frozen rev4 keeps conclusion.conclusion_type = weak_cosmic_censorship with the "
            "epistemic status separated and claim_promotion rules stated.")),
    "F1-AMB-17": dict(
        deciding_field="visibility.definition", deciding_field_contract="visibility.definition",
        deciding_field_alternates=["visibility.negation_conclusion", "visibility.observability_note"],
        deciding_field_status="resolved_single_geodesic", schema_open_expected=False,
        falsifier_strength="decided",
        does_it_satisfy_f1="ambiguous", satisfies_in_class="ambiguous",
        satisfies_conclusion="fails under single-geodesic reading; set-valued reading is outside the class",
        schema_finding=(
            "Rev4 defines the predicate through a single finite-affine-length geodesic and the "
            "observability_note ties falsification to a non-meager failure set; the set-valued "
            "variant is outside the frozen class definition.")),
}

UNPROBED_UNRESOLVED_ITEM = (
    "the diffeomorphism-quotient construction for genericity is a declared technical gap "
    "(unresolved_items[0]) - not covered by any suite row; flagged for A1"
)
