# worker-087 — F0 open-case re-binding audit (G-F0)

**Task (immediate queue, no card issued to worker-087):** independently re-bind the 9 open
F0 taxonomy cases and the flash-02 disposition matrix to the *current* canonical taxonomy
rev4, without using flash-02's own checker. Class-bound: node `F0`, gate `G-F0`, all four
frozen class ids.

**Inputs (measured at run, re-measured before the report was written — no drift):**

| input | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0, rev4, canonical) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `schemas/taxonomy_cases.jsonl` (36 cases: 16 positive, 20 negative, 9 open) | `b9699119bbabf01489f851b6dfa0c05a56f457c031e4e69992b8f57c30c489a2` |
| `artifacts/flash-02/open_case_disposition.json` (author self-checked) | `ee05eb8e7cdef44e6ab028652185c80f0737603a4d2c5a26c2de3008cb511bcf` |

**Instrument:** `audit.py` (this directory) — 8 checks, 7 controls, fail-closed on input drift.
Reproduce: `python3 artifacts/worker-087/f0_rebind_audit/audit.py` (exit 0 instrument valid,
1 controls failed, 2 hash drift).

## Verdict: `REBIND_REQUIRED_CONSISTENT`

The **dispositions themselves are mechanically consistent with rev4**:

- 9 open cases ↔ 9 disposition rows, no missing/extra rows.
- Every disposition token is declared in the matrix's `disposition_tokens`, and each maps
  legally from the case's own `expected_resolution` (`reject_new_class_required` →
  `NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI`; `reject_split_required` →
  `SPLIT_REQUIRED`/`SPLIT_AND_BRIDGE_REQUIRED`).
- Every `bound_parent_class_ids` entry is one of the four frozen ids; no unknown `AF-*`
  token occurs anywhere in the 9 rows.
- All 41 taxonomy anchors used by the 36 cases resolve at rev4 (guards `G1`–`G7`,
  `transfer_rules.forbidden` `X1`–`X5`, `coverage_gaps` `CG1`/`CG2`, per-class
  `exclusions`/`axes`/`hypotheses`, `field_vocabulary`).
- Every guard/hypothesis/transfer-rule/gap named by an open case's decisive hypothesis
  exists in rev4.
- The 5 recomputed axis vectors match no frozen class axes, as their
  `NO_CLASS_IN_TAXONOMY` classification requires.

The **binding metadata is stale**, which is what blocks a clean G-F0 disposition:

| id | severity | finding |
|---|---|---|
| F-087-1 | medium | the 9 disposition rows pin `research_map/formulation_taxonomy.yaml#565a6e505188` (rev3); canonical is rev4 `276009f4f63d` |
| F-087-2 | medium | all 36 cases still declare `binding_status: bound_taxonomy_sha_66bf917bd368` while the corpus meta records a rebind to `565a6e505188` and canonical is now `276009f4f63d` |
| F-087-7 | low | 4 case refs address test cases as `test_cases.positive.F0-Px`; rev4 stores them under keys, so they resolve only with an id-value lookup rule |
| F-087-3 | info | canonical F0 and `artifacts/formulation/formulation_taxonomy.yaml` are different documents; this audit binds canonical only |
| F-087-6 | info | the 9 cases remain `open=true` with no `disposition` field in the corpus; the matrix is a sidecar, so machine closure is a lead-side annotation |

A non-binding re-pin suggestion is recorded in `audit_report.json.rebind_patch_suggestion`
(corpus `binding_status` → `bound_taxonomy_sha_276009f4f63d`; row evidence ref →
`research_map/formulation_taxonomy.yaml#276009f4f63d`). No lead-owned or canonical artifact
was edited by this worker.

## Scope limits (travel with the report)

- **Classification direction only.** C4/C5/C6 verify that each row's claimed classification
  is legal and its cited guards exist. The physics reading of each statement is *not*
  re-derived here; that needs a domain reviewer.
- **Canonical only.** Because the authoring tree is a different document, taxonomy anchors
  are not expected to resolve there; the divergence is recorded, not adjudicated.
- **Authority.** Worker adjudication input only: no class id created, no gate verdict, no
  node status, no review verdict.

## Falsifier

Re-run `audit.py` at the pinned hashes. The audit is falsified if any check verdict changes,
if a taxonomy anchor that resolved here fails to resolve, if an open case loses its row or
maps to a token outside its `expected_resolution` family, if a row names a non-frozen parent
class, or if the corpus is later annotated with a disposition contradicting its row. A
control failure voids the audit.
