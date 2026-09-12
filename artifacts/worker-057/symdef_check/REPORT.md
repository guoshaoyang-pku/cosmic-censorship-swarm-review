# GFORM-SYMDEF-057 — normative-symbol definition consistency (worker-057, lifecycle 2)

Gate **G-FORM** · nodes F1 / F2a / F2b · classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN

Task: apply the *same* definition-site rule that produced F1's recorded hard failure for `AF_{I+}`
to the sibling class schemas at the current canonical rev-11 hashes, and report the uniformity table.
No gate verdict, no mathematical claim.

## Measured inputs

- `schemas/af_wcc_vacuum.yaml#9a8bd4c96800` (rev 11, 33642 bytes, mtime 2026-09-12T00:19:14.626692+08:00)
- `schemas/af_scc_c2_vacuum.yaml#b6123750b37d` (rev 11, 28268 bytes, mtime 2026-09-12T00:19:14.626692+08:00)
- `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357` (rev 11, 33276 bytes, mtime 2026-09-12T00:19:14.626692+08:00)
- `research_map/formulation_taxonomy.yaml#276009f4f63d` (canonical F0 taxonomy)
- measurements_sha256 `3a0ce8a6426b`

## Uniformity table (same rule, three classes)

| node | class | local definition | file-prose definition | taxonomy acronym/prose only | no definition site |
|---|---|---|---|---|---|
| F1 | AF-WCC-VAC-GEN | visible_singularity_from_I_plus | complete | — | AF_{I+}, P_WCC |
| F2a | AF-SCC-C2-VAC-GEN | proper_future_extension_in_class | — | MGHD | — |
| F2b | AF-SCC-C0-VAC-GEN | proper_future_extension_in_class | — | MGHD | — |

## Findings

**1. [MAJOR] `F1:undefined_normative_symbol` — AF_{I+}** (sites: conclusion.statement_formal)

- normative site uses 'AF_{I+}(M_D)'; no local definition site in the file; no occurrence in the canonical taxonomy either
- evidence: `schemas/af_wcc_vacuum.yaml#9a8bd4c96800`

**2. [INFO] `F1:binder_alias_undeclared` — D** (sites: conclusion.statement_formal)

- statement realizes binder 'D' that is not a quantifiers.ordered binder name (notational alias)
- declared binders: ['G', 'K', 'Mtilde', 'Omega', 'Sigma', 'delta', 'gamma', 'gtilde', 'h', 'q', 's']
- evidence: `schemas/af_wcc_vacuum.yaml#9a8bd4c96800`

**3. [MAJOR] `F1:undefined_normative_symbol` — P_WCC** (sites: quantifiers.negation_normal_form)

- normative site uses 'P_WCC(D)'; no local definition site in the file; no occurrence in the canonical taxonomy either
- evidence: `schemas/af_wcc_vacuum.yaml#9a8bd4c96800`

**4. [MAJOR] `F2a:predicate_argument_role` — proper_future_extension_in_class** (sites: conclusion.statement_formal)

- 'proper_future_extension_in_class' is defined on the extension tuple ["M'", "g'", 'iota'] of ['M', 'g'], but is applied to 'MGHD(D)' (the development of the data), so the extension existential is implicit at the use site
- definition subject tuple `["M'", "g'", 'iota']`, base `['M', 'g']`; use argument matches subject by name: False, base: False
- evidence: `schemas/af_scc_c2_vacuum.yaml#b6123750b37d`

**5. [MAJOR] `F2a:acronym_prose_only_symbol` — MGHD** (sites: conclusion.statement_formal, quantifiers.negation_normal_form)

- normative site uses 'MGHD(D)'; no local definition site in the file; canonical taxonomy occurrence at research_map/formulation_taxonomy.yaml:171 (prose/acronym only, no definition_ref)
- evidence: `schemas/af_scc_c2_vacuum.yaml#b6123750b37d`

**6. [INFO] `F2a:binder_alias_undeclared` — D** (sites: conclusion.statement_formal)

- statement realizes binder 'D' that is not a quantifiers.ordered binder name (notational alias)
- declared binders: ['G', 'K', "M'", 'Sigma', 'delta', "g'", 'h', 'iota', 's']
- evidence: `schemas/af_scc_c2_vacuum.yaml#b6123750b37d`

**7. [MAJOR] `F2b:predicate_argument_role` — proper_future_extension_in_class** (sites: conclusion.statement_formal)

- 'proper_future_extension_in_class' is defined on the extension tuple ["M'", "g'", 'iota'] of ['M', 'g'], but is applied to 'MGHD(D)' (the development of the data), so the extension existential is implicit at the use site
- definition subject tuple `["M'", "g'", 'iota']`, base `['M', 'g']`; use argument matches subject by name: False, base: False
- evidence: `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357`

**8. [MAJOR] `F2b:acronym_prose_only_symbol` — MGHD** (sites: conclusion.statement_formal, quantifiers.negation_normal_form)

- normative site uses 'MGHD(D)'; no local definition site in the file; canonical taxonomy occurrence at research_map/formulation_taxonomy.yaml:171 (prose/acronym only, no definition_ref)
- evidence: `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357`

**9. [INFO] `F2b:binder_alias_undeclared` — D** (sites: conclusion.statement_formal)

- statement realizes binder 'D' that is not a quantifiers.ordered binder name (notational alias)
- declared binders: ['G', 'K', "M'", 'Sigma', 'delta', "g'", 'h', 'iota', 's']
- evidence: `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357`

Novelty (measured, best effort): findings 1 and 3 are known (F1-review-19 HF-06 / worker-090 HF090-03; `complete` is prose-defined at
`i_plus.completeness_definition`); finding 2 (`P_WCC` in F1 `quantifiers.negation_normal_form`) and findings 4–6 (F2a/F2b `MGHD`,
predicate argument role) were not found in `reviews/`, `research_map.json` claims, or any outbox event at the time of this run.
worker-17 (`artifacts/worker-17/quantifier_nf/qnf_report.json`) types `D` as an alias and `MGHD` under `context_vocabulary` with
`C3_free_variable_capture=true`; the binder-alias items are therefore reported here as INFO, and the difference is policy, not measurement.

## Controls

- C1 visibility predicate resolves (F1): True
- C2 extension predicate resolves (F2a/F2b): True
- C3 mutant self-test (5 mutants): [True, True, True, True, True]

## Adjudication note

This report does not decide the policy.  Two readings are coherent: (strict) a normative statement bound into the class conclusion must use only symbols with a definition site, which makes F2a/F2b 'MGHD' the same defect class as F1's AF_{I+}; (lenient) an acronym expanded in prose in the canonical F0 taxonomy is an external definition, which clears MGHD while leaving P_WCC (F1 negation_normal_form, nowhere) as the only new undefined normative symbol.  The uniformity table is the evidence either way.

## Falsifier

Re-hash the three schemas and the taxonomy and re-run this script: the report is falsified for the recorded hashes if any measured sha256 differs; if a definition site for MGHD or P_WCC appears in the same file (or a definition_ref binds the symbol); if the extension predicate is redefined to take the development as its first-class argument; or if the realized/declared binder-name sets change.  A control C1/C2 flipping to False or any C3 mutant failing falsifies the scanner.

## Limits

- structural/syntactic only; no mathematical or physical correctness is decided
- no citation-scope verification (L1 owns it); no gate verdict
- the 'taxonomy_prose_only' class is a keyword occurrence in prose, not a formal definition; it is deliberately reported as a separate class from 'nowhere'
- canonical paths only; the authoring tree is not read

## Reproduce

```bash
python3 artifacts/worker-057/symdef_check/check_normative_symbols.py   # rewrites report.json
```
