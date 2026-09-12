# W002-F0-DUALSOURCE-01 -- canonical vs supplement class-contract agreement

- actor: `worker-002` | node `F0` | gate `G-F0` | measured: 2026-09-12T00:36:27+08:00
- class binding: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- canonical declared-F0: `research_map/formulation_taxonomy.yaml` rev 5 sha256 `0abb9ed8a961`
- supplement (pointer target): `artifacts/formulation/formulation_taxonomy.yaml` rev 9 sha256 `d7419b4e8963`
- controls: 12/12 pass | live bytes stable during run: True

## Reading (data-driven)

- Decidable class-identity probes agree on 22 rows (four identical class ids; conclusion_type agrees on all four classes, SCC via the declared VOCAB_ALIASES map; regularity tokens consistent; genericity axes agree under declared aliases on all four; variant registry identical).
- All three schemas' class_contract_pointer now resolves inside the canonical declared-F0 (research_map/formulation_taxonomy.yaml#classes.<ID>) and the fragment class exists there; the supplement is declared separately via f0_binding.
- Duplicate top-level YAML keys in the two surfaces: 0. No content timestamp runs past written_at on either surface.
- Residual non-hard differences: 3 row(s) (tension, underspecified). These are restatement-granularity / underspecification findings, not class-identity contradictions, unless a row is marked conflict_candidate.

## Decidable probe matrix

| class | conclusion_type | regularity | visibility | genericity |
|---|---|---|---|---|
| `AF-WCC-VAC-GEN` | alias_agree | agree | underspecified | agree |
| `AF-SCC-C2-VAC-GEN` | alias_agree | agree | agree | agree |
| `AF-SCC-C0-VAC-GEN` | alias_agree | agree | agree | agree |
| `AF-WCC-SCALAR-SPH` | alias_agree | agree | underspecified | agree |

## Restatement coverage (informational, not equivalence)

| class | canonical items covered by supplement | supplement items covered by canonical |
|---|---|---|
| `AF-WCC-VAC-GEN` | 3/9 | 2/9 |
| `AF-SCC-C2-VAC-GEN` | 1/8 | 1/7 |
| `AF-SCC-C0-VAC-GEN` | 2/8 | 1/8 |
| `AF-WCC-SCALAR-SPH` | 2/8 | 2/4 |

## Residual rows

| class | probe | status | detail |
|---|---|---|---|
| `AF-WCC-VAC-GEN` | P4.visibility_predicate | underspecified | canonical names the visibility reading explicitly; the supplement predicate says only 'visible from I+' and does not name the single-q TAIL predicate or the comeager quantifier |
| `AF-WCC-SCALAR-SPH` | P4.visibility_predicate | underspecified | canonical names the visibility reading explicitly; the supplement predicate says only 'visible from I+' and does not name the single-q TAIL predicate or the comeager quantifier |
| `AF-WCC-SCALAR-SPH` | P6.genericity.canonical_internal | tension | canonical conclusion quantifies over a comeager set while the class genericity_kind/status is unresolved; reader adjudicates whether the conclusion may name a notion the axis leaves open |

## Pointer surfaces (schemas -> class contract)

| node | pointer | canonical top key present | fragment class in canonical |
|---|---|---|---|
| F1 | `research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN` | True | True |
| F2a | `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN` | True | True |
| F2b | `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN` | True | True |

## Machine hygiene

| surface | revision | duplicate top-level keys | content ts after written_at |
|---|---|---|---|
| canonical | 5 | 0 | False |
| supplement | 9 | 0 | False |

## Limits

- Decidable probes are token/regex rules over primary text; aliases come only from
  the declared `VOCAB_ALIASES.json`, printed per row. Read `report.json` before using
  any row.
- `conflict_candidate` is a token-level machine finding under declared project
  vocabularies, not a physics claim and not a gate verdict.
- The hypotheses/exclusions probe is a coverage inventory at a declared threshold
  with a sweep; different restatement granularity is expected and is not equivalence
  or contradiction evidence by itself.

## Falsifier

REJECT the reading if (a) a frozen snapshot does not hash to its sha256_scan_pin; (b) a row marked conflict_candidate is shown to be bridged by a declared alias in VOCAB_ALIASES.json; (c) a row marked agree is shown to assert different class identity on the two surfaces (different class id set, regularity token, or conclusion type); (d) a class_contract_pointer is shown to resolve outside the canonical classes.<ID>; or (e) live canonical/supplement bytes moved after the scan pins and the re-measure.

Reproduce: `python3 artifacts/worker-002/f0-dual-source-contract/check_dual_source_contract.py --expect-live`
