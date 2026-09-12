# FORM-SEP-04 — C2/C0 pairwise separation audit (worker 08) — v2 [canonical]

**Scope declaration (X5).** Audits *separation* only: field disjointness on frozen axes,
foreign-regularity semantic leakage, and the direction of the implication ledger. Does **not**
audit physical truth, citation scope, or definitional correctness. Claims **no node
completion**; `astra-lead-formulation` binds interpretation. Read-only.

Generated 2026-09-11T23:37:04+08:00 by `deepseek-flash-08`. Generator `artifacts/worker08/c2_c0_separation_audit.py` (v2,
negation-aware).

## Inputs (hashes)

| path | sha256 |
|---|---|
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `836746b39be49d3d80eed2b47d4f571ec53b7aa239cf4c5ff45175e780f5a507` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | `188e513130c6f5540f5b93be4759c7e086b30e73d7eb921a4f0b5c6d48ae72b1` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e` |

Recorded gate run (`check_class_schema.py --json`):
C2 `pass` (exit 0),
C0 `pass` (exit 0).
Both structural gates pass; findings below are the semantic residue.

## Verdict: **PASS**

Hard-failure groups: **0**.

## X1 — pairwise field matrix

- leaf paths: 305; identical: 178; differing/one-sided: 127
- frozen-axis expectation violations: **0**
- none
- naming asymmetries (one-sided shared fields, flags): **1**
- `data_class` -> data_class.adm_mass.hypotheses_reconciliation
- class-parameterized fields (allowed to differ): `conclusion.statement_formal`, `genericity.excluded_set`, `unresolved_items`

Full path-level matrix: `c2_c0_separation_matrix.json#X1_pairwise.matrix`.

## X2 — foreign regularity semantics outside anti_scope/variants

- C0 tokens inside the C2 file: 13; C2 tokens inside the C0 file: 20
- hits inside rule_spec leakage blocks (`conclusion`/`visibility`/`i_plus`/`falsifier`): 5
- **unjustified** mentions: **0**

- none

Every surviving hit is a pointer (`sibling_disjoint_from`, `class_contract_pointer`), an
implication-ledger statement, an explicit exclusion ("different class", "NOT ...", "forbidden"),
or mandated by R10 (SCC visibility must name the WCC falsifier). The R10/R12 tension is recorded
as a spec flag, not a schema defect.

## X2b — conclusion regularity axis (assertive fields only)

Foreign-regularity tokens inside `conclusion.*` (excluding `conclusion.forbidden*`):
hits 0, **violations 0**.

- none

This rule closes the lead gate's documented blind spot `p03_c2_schema_c0_meaning`, where the C2
formal statement asserts "no proper continuation whose metric is merely continuous" — a C0
conclusion in the C2 class with no literal `C0` token.

## X3 — implication ledger and converse scan

Curated ledger checks:

- X3-C2-entailment: PASS — expected C0-inext => C2-inext recorded
- X3-C2-forbidden-converse: PASS — expected C2-inext => C0-inext marked forbidden
- X3-C0-entailment: PASS — expected C0-inext => C2-inext recorded
- X3-C0-forbidden-converse: PASS — expected C2-inext => C0-inext marked forbidden

Negation-aware sentence scan over every string in both files: 21 dual mentions classified;
**converse assertions: 0**; unclassified dual mentions: 0.

- none

### Hard failure H1 (if converse_assertions non-empty)

- no failure in non_vacuity notes

`non_vacuity.c0_specific_note` in the C0 schema asserts that a **C2**-inextendibility proof
*SUBSUMES* the C0 conclusion while its own parenthetical says C0-inextendibility is *stronger*.
Under extension-class containment (C2 extensions are a subset of C0 extensions), the only valid
entailment is C0 => C2. The sentence therefore states the forbidden converse and contradicts the
same file's `implication_ledger`, `regularity.must_not_conflate[2]`, and
`conclusion.forbidden_strengthenings[0]`.

**Repair (wording only, exact path `non_vacuity.c0_specific_note`):** replace
"a C2-inextendibility proof SUBSUMES this class's conclusion (C0-inextendibility is stronger)"
with "a C2-inextendibility proof does NOT subsume this class's conclusion; the implication runs
C0 => C2 only (C0-inextendibility is stronger)". Re-hash and re-run this audit.

## X3b — propagation of the defective sentence

The phrase "C2-inextendibility proof SUBSUMES" also appears in **2** adjacent
fixture/control files (fixtures clone the C0 schema): `artifacts/formulation/reviews/novel_mutants/n02_scc_c0_relabelled_as_c2.yaml`, `artifacts/formulation/reviews/novel_mutants/n07_scc_completeness_in_unscanned_i_plus_key.yaml`. Repairing only the canonical
schema would leave the wrong statement inside the test corpus; regenerate or patch these files
and re-hash them with the schema.

## Frozen-manifest consistency

`FROZEN.json` sha256 `8d0725ef3a79`: 0 mismatch(es); self-entry skipped: True.
- all frozen entries match disk

## X4 — composite-regularity ban

Composite-token hits: 3; violations: **0**.
All hits are the exempt forbidden quotation in `anti_scope.phrases_that_are_not_this_class[0]`.

## X5 — declaration

Recorded under `declaration` in the JSON matrix: audits separation only; no truth/citation/
definitional audit; no completion claim; interpretation owned by `astra-lead-formulation`.

## Flags (not failures)

- R10 (SCC visibility must state the WCC falsifier belongs to WCC) forces WCC tokens into visibility/i_plus/conclusion exclusion lists that R12's lexical scan would flag: rule_spec tension, resolved for R10, recorded not failed.
- Pointer and ledger fields (sibling_disjoint_from, implication_ledger) necessarily name the sibling class; exempted from X2 leakage, kept in the matrix for transparency.
- Editorial drift in i_plus.definition between the two files is recorded in X1 as a difference; it is not a separation defect (semantically equivalent).
- Lexical scans cannot see semantic leaks expressed without regularity tokens; the lead gate's documented blind spot (rephrased probe p03) remains the residual risk.

## Next falsifier

Apply the repair to artifacts/formulation/schemas/af_scc_c0_vacuum.yaml non_vacuity.c0_specific_note, re-hash, re-run this audit. If X3 converse assertions are empty and X1/X2/X4 stay clean, separation passes at the new hash. Any further wording asserting C2-inextendibility => C0-inextendibility reopens the failure.
