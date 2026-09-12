# worker-045 / W045-F2-VOCAB-SEP-ADJ-01

Independent adjudication of two live G-FORM findings on the frozen
`AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` schemas:

- **worker-033 HF-02** (critical, filed as class leakage): the F2a/F2b `conclusion_type`
  tokens are not members of the canonical F0 vocabulary at
  `research_map/formulation_taxonomy.yaml#276009f4f63d`.
- **worker-088 F-088-2** (major): the F2a/F2b `data_class` blocks are key-identical and their
  `regularity_class` values are equal, so C2/C0 separation allegedly rests on
  `extension_predicate` + `conclusion` only.

## Verdict

| finding | verdict |
|---|---|
| HF-02 | **CONFIRMED-AS-LITERAL-MISMATCH / NOT-CLASS-LEAKAGE.** Both schema tokens are absent from canonical F0's `field_vocabulary.conclusion_type.allowed`; canonical F0 contains neither an alias registry nor the canonical tokens. `artifacts/formulation/VOCAB_ALIASES.json#46cd9f1e` declares the F0 tokens accepted aliases of the schemas' `scc_*` canonical tokens and keeps C2/C0 distinct, so there is no class merge or conclusion inflation. It is a vocabulary-authority/binding-placement defect, blocking only for a checker that binds canonical F0 literally with no alias resolution (including A0-HF-02 as written). |
| F-088-2 | **SUB-BLOCK-KEY-IDENTICAL + ONE NESTED LEAF DIFF / IMPLICATION-INCOMPLETE.** All 10 `data_class` sub-block keys and the `regularity_class` values match, but the full nested key paths do not: F2b carries `adm_mass.hypotheses_reconciliation` and `adm_mass.locator` differs. The separation locus also includes `class_components.regularity_token` and `regularity.extension_regularity` (C2 vs C0); canonical F0's own `disjointness` entry for this pair names `decisive_axes=[regularity_token, conclusion_type]`, so `data_class` is not a decisive axis. Shared data class is a G-FORM single-frozen-data-class question, not a C2/C0 merge. |

## Method (moving-target safe)

The two findings were filed against pinned hashes that were **republished (rev12) between task
scoping and measurement**. The adjudication therefore runs twice:

- **PRIMARY** — the exact claim-filing bytes, read from on-disk snapshots whose sha256 is
  verified against the pinned values (`276009f4f63d`, `b6123750b37d`, `1bb78ce9b357`).
  Sources: `artifacts/worker-020/f2a_independent_verdict/snapshots/f0_taxonomy_276009f4f63d.yaml`,
  `artifacts/worker-047/d0_cross_class/snapshot/af_scc_c2_vacuum.yaml.b6123750b37d`,
  `artifacts/worker-047/d0_cross_class/snapshot/af_scc_c0_vacuum.yaml.1bb78ce9b357`.
- **LIVE** — the current canonical paths at measurement time, reported as a delta only.

Sensitivity controls (all pass): baseline canonical schemas produce 0 `class_separation.py`
findings; an injected merge assertion and an injected unknown class token are each detected; a
synthetic non-vocabulary token is rejected; alias resolution keeps C2/C0 distinct. One probe
(C4) records that `class_separation.py` does not flag a swapped C0/C2 conclusion token — that
conformance axis belongs to `check_class_schema`/A0-HF-02.

## Falsifier

Falsified if, at the verified claim-hash snapshots: either schema token is a literal member of
canonical F0's allowed list, or canonical F0 contains an alias registry/canonical tokens; or the
two tokens resolve to the same canonical token; or the `data_class` sub-block key sets are not
equal / `regularity_class` values differ; or F0's C2/C0 `decisive_axes` include `data_class`; or
the controls fail; or a snapshot hash mismatches. Any live-input drift voids only the live delta.

## Reproduction

```bash
python3 artifacts/worker-045/run_f2_vocab_separation_adjudication.py
```

Writes exactly one artifact: `artifacts/worker-045/f2_vocab_separation_adjudication.json`.
Read-only otherwise; no node status, `validation_status=passed`, or gate verdict is claimed.
