# FORM-SEP-04 — C2/C0 pairwise separation audit (worker 08) — v3 [c2_sibling_live]

**Scope declaration (X5).** Audits *separation* only: field disjointness on frozen axes,
foreign-regularity semantic leakage, and the direction of the implication ledger. Does **not**
audit physical truth, citation scope, or definitional correctness. Claims **no node
completion**; `astra-lead-formulation` binds interpretation. Read-only.

Generated 2026-09-12T01:15:33+08:00 by `deepseek-flash-08`. Generator `artifacts/worker08/c2_c0_separation_audit.py` (v3,
rev18 re-bind; the three v3 rule changes are recorded under `rule_changes_v3` in the JSON).

## Inputs (hashes)

| path | sha256 |
|---|---|
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `n/a` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `n/a` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e` |

Recorded gate run (`check_class_schema.py --json`):
C2 `pass` (exit 0),
C0 `pass` (exit 0).
Both structural gates pass; findings below are the semantic residue.

## Verdict: **FAIL**

Hard-failure groups: **38**.

## X1 — pairwise field matrix

- leaf paths: 385; identical: 385; differing/one-sided: 0
- frozen-axis expectation violations: **36**
- expected_axis_not_separated on `class_id` -> class_id
- expected_axis_not_separated on `node_id` -> node_id
- expected_axis_not_separated on `sibling_disjoint_from` -> sibling_disjoint_from
- expected_axis_not_separated on `class_contract_pointer` -> class_contract_pointer
- expected_axis_not_separated on `scope_statement` -> scope_statement
- expected_axis_not_separated on `class_components.regularity_token` -> class_components.regularity_token
- expected_axis_not_separated on `extension_predicate.frozen_regularity` -> extension_predicate.frozen_regularity
- expected_axis_not_separated on `extension_predicate.frozen_equation_concept` -> extension_predicate.frozen_equation_concept
- expected_axis_not_separated on `extension_predicate.definition` -> extension_predicate.definition
- expected_axis_not_separated on `regularity.extension_regularity` -> regularity.extension_regularity
- expected_axis_not_separated on `regularity.extension_regularity_exact` -> regularity.extension_regularity_exact
- expected_axis_not_separated on `regularity.extension_solution_concept` -> regularity.extension_solution_concept
- expected_axis_not_separated on `conclusion.conclusion_type` -> conclusion.conclusion_type
- expected_axis_not_separated on `conclusion.statement_natural_language` -> conclusion.statement_natural_language
- expected_axis_not_separated on `conclusion.known_obstruction` -> conclusion.known_obstruction
- expected_axis_not_separated on `conclusion.forbidden_strengthenings` -> conclusion.forbidden_strengthenings[0], conclusion.forbidden_strengthenings[1], conclusion.forbidden_strengthenings[2], conclusion.forbidden_strengthenings[3], conclusion.forbidden_strengthenings[4]
- expected_axis_not_separated on `conclusion.forbidden_weakenings` -> conclusion.forbidden_weakenings[0], conclusion.forbidden_weakenings[1], conclusion.forbidden_weakenings[2], conclusion.forbidden_weakenings[3]
- expected_axis_not_separated on `implication_ledger.one_way_entailments` -> implication_ledger.one_way_entailments[0].from, implication_ledger.one_way_entailments[0].reason, implication_ledger.one_way_entailments[0].relation, implication_ledger.one_way_entailments[0].status, implication_ledger.one_way_entailments[0].to
- expected_axis_not_separated on `implication_ledger.forbidden_transfers` -> implication_ledger.forbidden_transfers[0].from, implication_ledger.forbidden_transfers[0].reason, implication_ledger.forbidden_transfers[0].to, implication_ledger.forbidden_transfers[1].from, implication_ledger.forbidden_transfers[1].reason
- expected_axis_not_separated on `falsifier.tier_1.witness_type` -> falsifier.tier_1.witness_type
- expected_axis_not_separated on `falsifier.tier_1.machine_checkable_steps` -> falsifier.tier_1.machine_checkable_steps[0], falsifier.tier_1.machine_checkable_steps[1], falsifier.tier_1.machine_checkable_steps[2], falsifier.tier_1.machine_checkable_steps[3]
- expected_axis_not_separated on `falsifier.tier_2.witness_type` -> falsifier.tier_2.witness_type
- expected_axis_not_separated on `falsifier.schema_falsifiers` -> falsifier.schema_falsifiers[0], falsifier.schema_falsifiers[1], falsifier.schema_falsifiers[2], falsifier.schema_falsifiers[3]
- expected_axis_not_separated on `non_vacuity.condition` -> non_vacuity.condition
- expected_axis_not_separated on `non_vacuity.witness_type` -> non_vacuity.witness_type
- expected_axis_not_separated on `non_vacuity.vacuity_falsifier` -> non_vacuity.vacuity_falsifier
- expected_axis_not_separated on `provenance.sources` -> provenance.sources[0].concept, provenance.sources[0].identifier, provenance.sources[0].needed_for, provenance.sources[0].status, provenance.sources[1].concept
- expected_axis_not_separated on `provenance.unresolved_citations` -> provenance.unresolved_citations[0], provenance.unresolved_citations[1]
- expected_axis_not_separated on `review_status.requested_reviewers` -> review_status.requested_reviewers[0], review_status.requested_reviewers[1]
- expected_axis_not_separated on `topology.extension_topology` -> topology.extension_topology
- expected_axis_not_separated on `topology.forbidden` -> topology.forbidden[0], topology.forbidden[1], topology.forbidden[2], topology.forbidden[3]
- expected_axis_not_separated on `anti_scope.not_this_class` -> anti_scope.not_this_class[0].class_id, anti_scope.not_this_class[0].why, anti_scope.not_this_class[1].class_id, anti_scope.not_this_class[1].why, anti_scope.not_this_class[2].class_id
- expected_axis_not_separated on `anti_scope.phrases_that_are_not_this_class` -> anti_scope.phrases_that_are_not_this_class[0], anti_scope.phrases_that_are_not_this_class[1], anti_scope.phrases_that_are_not_this_class[2]
- expected_axis_not_separated on `quantifiers.domains.D3.definition` -> quantifiers.domains.D3.definition
- expected_axis_not_separated on `quantifiers.negation` -> quantifiers.negation
- expected_axis_not_separated on `quantifiers.negation_normal_form` -> quantifiers.negation_normal_form
- naming asymmetries (one-sided shared fields, flags): **0**
- none
- class-parameterized fields (allowed to differ): `conclusion.statement_formal`, `genericity.excluded_set`, `unresolved_items`

Full path-level matrix: `c2_c0_separation_matrix.json#X1_pairwise.matrix`.

## X2 — foreign regularity semantics outside anti_scope/variants

- C0 tokens inside the C2 file: 18; C2 tokens inside the C0 file: 48
- hits inside rule_spec leakage blocks (`conclusion`/`visibility`/`i_plus`/`falsifier`): 8
- **unjustified** mentions: **17**
- reviewed path-exemptions (not leaks, listed in the JSON): **32**

- `class_id` [unjustified_mention] AF-SCC-C2-VAC-GEN
- `class_components.regularity_token` [unjustified_mention] C2
- `class_contract_supplement_pointer` [unjustified_mention] artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN
- `quantifiers.domains.D3.definition` [unjustified_mention] proper future C2 vacuum extensions of the maximal development, in the exact sense of extension_predicate
- `quantifiers.negation` [unjustified_mention] there exists r in D0 such that for every comeager G_r subset X^r_vac(AF) there is (Sigma,h,K) in G_r whose maximal development admits a proper future C2 vacuum extension; equivalently the set of data admitting such an extension is
- `quantifiers.negation_normal_form` [unjustified_mention] { r in D0 : { D in X : exists proper future C2 vacuum extension of MGHD(D) } is non-meager } is non-empty
- `class_boundary.one_class_only` [unjustified_mention] AF-SCC-C2-VAC-GEN
- `extension_predicate.frozen_regularity` [unjustified_mention] C2
- `extension_predicate.definition` [unjustified_mention] A triple (M', g', iota) is a proper future C2 vacuum extension of (M,g) iff: (a) iota: M -> M' is an isometric embedding (iota_* g = g' restricted to iota(M)); (b) iota(M) is an open, proper subset of M'; (c) M' is connected and t
- `regularity.extension_regularity` [unjustified_mention] C2
- `conclusion.statement_natural_language` [leakage_block_UNJUSTIFIED] Generic asymptotically flat vacuum initial data have a maximal development that is future-inextendible as a C2 vacuum solution.
- `conclusion.equivalent_rephrasings[0].phrasing` [leakage_block_UNJUSTIFIED] the maximal development is future inextendible in the C2 class
- `falsifier.tier_1.refutes` [leakage_block_UNJUSTIFIED] AF-SCC-C2-VAC-GEN
- `falsifier.tier_1.machine_checkable_steps[1]` [leakage_block_UNJUSTIFIED] the extension's metric is C2 across the boundary and Ric = 0 holds at sample points
- `falsifier.tier_2.witness_type` [leakage_block_UNJUSTIFIED] one AF vacuum data set (e.g. exact Kerr data) with an exhibited proper future C2 vacuum extension
- ... and 2 more (see JSON)

Every surviving hit is a pointer (`sibling_disjoint_from`, `class_contract_pointer`), an
implication-ledger statement, an explicit exclusion ("different class", "NOT ...", "forbidden"),
or mandated by R10 (SCC visibility must name the WCC falsifier). The R10/R12 tension is recorded
as a spec flag, not a schema defect.

## X2b — conclusion regularity axis (assertive fields only)

Foreign-regularity tokens inside `conclusion.*` (excluding `conclusion.forbidden*`):
hits 3, **violations 3**.

- `C0#conclusion.statement_natural_language` [AXIS_VIOLATION] ally flat vacuum initial data have a maximal development that is future-inextendible as a C2 vacuum solution.
- `C0#conclusion.equivalent_rephrasings[0].phrasing` [AXIS_VIOLATION] the maximal development is future inextendible in the C2 class
- `C0#conclusion.equivalent_rephrasings[1].phrasing` [AXIS_VIOLATION] no Cauchy horizon of the development can be crossed by a C2 vacuum extension

This rule closes the lead gate's documented blind spot `p03_c2_schema_c0_meaning`, where the C2
formal statement asserts "no proper continuation whose metric is merely continuous" — a C0
conclusion in the C2 class with no literal `C0` token.

## X3 — implication ledger and converse scan

Curated ledger checks:

- X3-C2-entailment: PASS — expected C0-inext => C2-inext recorded
- X3-C2-forbidden-converse: PASS — expected C2-inext => C0-inext marked forbidden
- X3-C0-entailment: PASS — expected C0-inext => C2-inext recorded
- X3-C0-forbidden-converse: PASS — expected C2-inext => C0-inext marked forbidden

Negation-aware sentence scan over every string in both files: 24 dual mentions classified;
**converse assertions: 0**; unclassified dual mentions: 0.

- none

### Hard failure H1 (historical; rendered only when converse_assertions is non-empty)

- no failure in non_vacuity notes

At the rev4 repair the defect was: `non_vacuity.c0_specific_note` in the C0 schema asserted that a
**C2**-inextendibility proof *SUBSUMES* the C0 conclusion while its own parenthetical said
C0-inextendibility is *stronger*. Under extension-class containment (C2 extensions are a subset of
C0 extensions) the only valid entailment is C0 => C2, so that sentence stated the forbidden
converse. The current canonical pair (FROZEN rev29) no longer carries it; this paragraph is retained as the record
of what the check detects.

## X3b — propagation of the pre-rev4 defective sentence

The phrase "C2-inextendibility proof SUBSUMES" appears in **2** adjacent
fixture/review files: `artifacts/formulation/reviews/novel_mutants/n02_scc_c0_relabelled_as_c2.yaml`, `artifacts/formulation/reviews/novel_mutants/n07_scc_completeness_in_unscanned_i_plus_key.yaml`. The canonical pair is clean; the carriers are pre-rev4 clones.
Reusing them as held-out evidence would confound their intended mutation with the stale clause;
regenerate or patch them and re-hash with the schema.

## Frozen-manifest consistency

`FROZEN.json` sha256 `815e08079aef`: 0 mismatch(es); self-entry skipped: False.
- all frozen entries match disk

## X4 — composite-regularity ban

Composite-token hits: 2; violations: **0**.
All hits are the exempt forbidden quotation in `anti_scope.phrases_that_are_not_this_class[0]`.

## X3c — containment-premise inversion (new in v3)

Hits: **0**. The frozen containment is
`E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0`; a sentence calling C2 the *larger* (or C0 the
*smaller*) extension class is a hard failure even when the transfer it forbids is the correct one.

- none

**Exact repair (wording only, path `implication_ledger.forbidden_transfers[0].reason`):** replace
"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker" with
"C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly
weaker". Re-hash, re-freeze, re-run this audit.

## X5 — declaration

Recorded under `declaration` in the JSON matrix: audits separation only; no truth/citation/
definitional audit; no completion claim; interpretation owned by `astra-lead-formulation`.

## Flags (not failures)

- R10 (SCC visibility must state the WCC falsifier belongs to WCC) forces WCC tokens into visibility/i_plus/conclusion exclusion lists that R12's lexical scan would flag: rule_spec tension, resolved for R10, recorded not failed.
- Pointer and ledger fields (sibling_disjoint_from, implication_ledger) necessarily name the sibling class; exempted from X2 leakage, kept in the matrix for transparency.
- v3: conclusion.forbidden_* lists name the sibling regularity by construction; exempted from X2 leakage (path-classified `exempt_forbidden_list`), kept in the matrix for transparency.
- v3: l1_ledger_refs/known_status are ledger-status metadata; exempted from X2 leakage (path-classified `exempt_ledger_metadata`), kept in the matrix for transparency.
- Editorial drift in i_plus.definition between the two files is recorded in X1 as a difference; it is not a separation defect (semantically equivalent).
- Lexical scans cannot see semantic leaks expressed without regularity tokens; the lead gate's documented blind spot (rephrased probe p03) remains the residual risk.
- Corpus hygiene (not a canonical defect): two pre-rev4 held-out mutants under artifacts/formulation/reviews/novel_mutants/ (n02, n07) still clone the old C0 sentence 'a C2-inextendibility proof SUBSUMES ...'; the current canonical pair (FROZEN rev29) no longer carries it. Reusing those mutants as held-out evidence would confound the intended mutation with the stale clause.

## Next falsifier

Re-run at the next FROZEN revision hash (this run binds FROZEN rev29: C2 e9a27996..., C0 e9a27996...). A genuine separation defect is any placement where the C2 conclusion is satisfied by a C0-only extension class or vice versa, any Cx => Cy converse prose, any composite regularity token outside anti_scope, any containment-premise inversion (C2 called larger / C0 called smaller), or any foreign-regularity token in an assertive conclusion field; any of those reopens FAIL at the new hash. The three v3 exemptions (forbidden lists, ledger metadata, subject-aware strength) are individually re-checkable from the matrix's reviewed_exemptions.
