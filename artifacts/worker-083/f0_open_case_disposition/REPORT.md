# W083-F0-OPENCASE-DISPOSITION-01 — independent disposition analysis of the 9 open G-F0 taxonomy cases

- **Actor:** worker-083 (bounded execution worker, DeepSeek Flash breadth executor)
- **Node / gate:** F0 / G-F0
- **Class binding:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH` (the frozen four only; no new class id created or proposed)
- **Measured at:** 2026-09-12T00:25:21+08:00 (one instant; all inputs hashed in that run)
- **Reproduce:** `python3 artifacts/worker-083/f0_open_case_disposition/disposition.py`
- **Status of this artifact:** `unverified` — a proposal for the F0 lead to adjudicate. It moves no gate and no node status.

## Why this task

The map's G-F0 gate lists, among its unmet criteria:

> “9 taxonomy cases remain open (new class vs split) and were never dispositioned by the lead”
> — `research_map/research_map.json#4fd40d4d1e4f:gates[0].unmet[3]`
> (same item at the earlier snapshot `#46ae09f0c32c:controller_gate_audit.G-F0.unmet`)

`schemas/taxonomy_cases.jsonl` has exactly nine records with `open == true` (N01, N02, N04, N09,
N10, N11, N14, N15, N16). Every one is a rejection case: either a coverage-gap claim that no frozen
class accepts, or a record that merges two conclusions. This artifact re-derives, from the current
canonical bytes and under the current class-scope policy, what the disposition of each must be —
as a decision-ready proposal for the lead.

### Prior art and independence

`deepseek-flash-02` (the corpus author) produced the first disposition matrix at
`artifacts/flash-02/open_case_disposition.json` (00:12:57, claim ingested 00:14:39), pinned to
taxonomy **rev 3** `565a6e50…`. This worker's artifact is an **independent reproduction and
extension at the current canonical revision** `276009f4…`:

| check | deepseek-flash-02 (00:12) | worker-083 (this artifact) |
|---|---|---|
| open cases covered | 9/9 | 9/9 |
| disposition result | 7 deferred new-class, 1 split (C0/C2), 1 split + bridge (WCC/SCC) | 7 `NEW_CLASS_REQUIRED`, 2 `SPLIT_REQUIRED` |
| bound taxonomy | rev 3 `565a6e50…` | rev 4 `276009f4…` (current canonical) |
| variant-registry supersession check | not performed | performed: no registered variant closes any of the 9 |
| stale per-case binding flagged | corpus hash only | per-case `66bf917bd368…` = the artifact rev 4 supersedes |
| control battery | checker on own matrix (8 controls) | 16/16 positives, 20/20 negatives, 4/4 planted branches, differential parse |

The two derivations agree on all nine dispositions. That is convergent evidence, not independent
mathematics: both read the same descriptors. The added value here is the current-hash re-binding,
the variant-path elimination, the stale-binding finding, and the control battery.

One ambiguity is recorded rather than hidden: **TC-F0-N11** (“Schwarzschild vacuum data are used as
the working example, conclusion filed under AF-WCC-SCALAR-SPH”). If the claim's descriptor is
spherical vacuum, no frozen class accepts it (this artifact's reading, `NEW_CLASS_REQUIRED`); if the
descriptor is generic non-symmetric vacuum, it re-files to `AF-WCC-VAC-GEN`. flash-02 records both
candidate parents for that row. Both readings reject the scalar filing; the lead should pin the
scope when dispositioning N11.

## Inputs (measured single instant)

| artifact | sha256 |
|---|---|
| `schemas/taxonomy_cases.jsonl` | `b9699119bbabf01489f851b6dfa0c05a56f457c031e4e69992b8f57c30c489a2` |
| `research_map/formulation_taxonomy.yaml` (rev 4, current canonical) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `artifacts/formulation/VARIANT_REGISTRY.json` (v2.0) | `5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b` |
| `schemas/af_{wcc,scc_c2,scc_c0}_vacuum.yaml` (context only, moving target) | analysis-instant hashes in `dispositions.json.frozen_schema_hashes`; C0 has since moved `a2aef5ac7fe3…` → `1bb78ce9b357…` |
| `research_map/research_map.json` (cited map snapshot) | `46ae09f0c32cda709886fb9c000e07b4bf6eb6688839a1a323d5787d9e1fbfdf` (live map has since moved) |

## Finding 1 — the open cases are bound to a hash the taxonomy explicitly supersedes

Every one of the nine records carries `binding_status: bound_taxonomy_sha_66bf917bd368`. That is
the pre-amendment artifact named by rev 4 itself:

```yaml
class_scope_adjudication:
  supersedes:
    wcc_text_sha256_before: "66bf917bd368ebd96ee46baa31fb435df106cb4e10152fa0baee8bdd51dfc232"
```

The corpus meta record is older still (`taxonomy_ref.sha256: 565a6e505188…`, rev 3), and the current
canonical taxonomy is `276009f4f63d…`. **No review verdict or lead disposition can bind to these
nine records until their binding hash is advanced to the current canonical revision.** This is a
hygiene blocker on the G-F0 item, independent of what each disposition turns out to be.

## Finding 2 — the rev-4 variant mechanism does not close any of the nine

`astra-classscope-02` (taxonomy rev 4) rejects new class ids pending Human PI and registers
non-frozen *readings* as variants. The registry v2.0 holds seven variants (SET, CH, DISTRIBUTIONAL,
H2LOC, TWOSIDED, L2CONN, LIP). Machine checks in this run:

- all variant `parent_class` values are among the frozen four;
- no variant id appears in any case's `class_id`/`class_ids` field;
- the two variants with machine delta files change only
  `class_id`, `visibility.*`, and `conclusion.*` paths — **no path touches
  `family`, `matter_model`, `symmetry`, `asymptotics`, or `regularity_token`**;
- no registry entry declares a change of the data class.

Each of the nine open cases deviates on at least one descriptor axis (matter model, symmetry,
asymptotics, family, or regularity token), so it is outside the registered-variant surface. The
variant mechanism is not a path to closing them; the choice is **new class (Human PI)** or **split
into existing classes**.

## Finding 3 — dispositions (proposal)

| case | filed under | recovered deviation | disposition | escalation |
|---|---|---|---|---|
| TC-F0-N01 | AF-WCC-VAC-GEN | matter_model → massless scalar, no symmetry | `NEW_CLASS_REQUIRED` (CG2) | Human PI |
| TC-F0-N02 | AF-WCC-VAC-GEN | symmetry → spherical (vacuum) | `NEW_CLASS_REQUIRED` (CG2) | Human PI |
| TC-F0-N04 | AF-SCC-C2-VAC-GEN | matter_model → electrovacuum | `NEW_CLASS_REQUIRED` (CG2) | Human PI |
| TC-F0-N09 | AF-SCC-C0-VAC-GEN | matter_model → massless scalar; symmetry → spherical | `NEW_CLASS_REQUIRED` (CG2) | Human PI |
| TC-F0-N10 | AF-WCC-SCALAR-SPH | symmetry → none_assumed (symmetry release, X3) | `NEW_CLASS_REQUIRED` (CG2) | Human PI |
| TC-F0-N11 | AF-WCC-SCALAR-SPH | matter_model → vacuum (spherical Schwarzschild) | `NEW_CLASS_REQUIRED` (CG2) | Human PI |
| TC-F0-N14 | COMPOSITE_C0_C2 | merged regularity token (C0 or C2) | `SPLIT_REQUIRED` → AF-SCC-C2-VAC-GEN + AF-SCC-C0-VAC-GEN (X5/G3) | F0 lead |
| TC-F0-N15 | COMPOSITE_WCC_SCC | merged family (WCC and SCC) | `SPLIT_REQUIRED` → AF-WCC-VAC-GEN + AF-SCC-C2-VAC-GEN, bridge artifact required (X4) | F0 lead |
| TC-F0-N16 | AF-SCC-C0-VAC-GEN | asymptotics → de Sitter / Lambda > 0 | `NEW_CLASS_REQUIRED` (CG2) | Human PI |

Result: **7 reject-and-escalate (CG2 coverage gap, Human PI), 2 split-required (repairable now with
two filings each).** All nine agree with the corpus's authored `expected_resolution`; the analysis
re-derives them from the current canonical taxonomy rather than copying the expectation field.

## Controls and honest limits

- 16/16 positive cases resolve to exactly their filed frozen class.
- 20/20 negative cases fail to resolve cleanly to their filed class (no false accept).
- 4/4 planted controls land on the intended branch (new class, split, in-class, variant registration).
- The taxonomy is parsed twice (hand-rolled indentation parser and PyYAML); the two parses agree on
  class ids, class axes, variants, and coverage gaps.
- Disposition vocabulary agrees with the corpus on 35/36 records. TC-F0-N13 agrees on rejection and
  refines the repair to a split (`agrees_repair_refined`). TC-F0-N19's axis vector matches its filed
  class, so this analyzer rejects it as a leak (`REJECT_LEAK_ONLY`, rule `REGULARITY-SMUGGLE-EXT-CLASS`)
  and additionally records the rev-4 repair path `(AF-SCC-C0-VAC-GEN, H2LOC)`; the pre-rev-4 corpus
  could not express that path.
- Keyword extraction is a lower-precision path: it is applied to negative/open records only, and
  explicit `axis=value` literals in a record always outrank it. Positive records are never
  reclassified by keyword extraction; a text conflict there is reported, not applied.
- The taxonomy is a moving target (canonical hash moved from `0fcc6a19…` to `276009f4…` during this
  work). Every hash above was measured in the single run recorded in `dispositions.json`; a later
  taxonomy revision requires a re-run. The three determinant inputs (corpus `b9699119…`, taxonomy
  `276009f4…`, variant registry `5eb42f9a…`) were re-measured after emission and still match the
  binding exactly; the auxiliary frozen-schema hashes moved (`a2aef5ac…` → `1bb78ce9…` for C0) and
  are not used by the disposition logic. The dispositions depend only on the four class descriptor
  axis vectors and the coverage-gap/transfer rules, which are unchanged at the bound hash.

## Falsifier

Any of the following falsifies a claim in this artifact:

1. **NEW_CLASS_REQUIRED** — exhibit a frozen descriptor whose axes accept the case's recovered axis
   vector, or a registered variant whose delta absorbs that case's descriptor-axis deviation without
   changing the parent's data class.
2. **SPLIT_REQUIRED** — exhibit a single frozen class whose `conclusion_type` covers both merged
   readings without a bridge artifact.
3. **Finding 1** — exhibit a canonical taxonomy revision whose bytes hash to `66bf917bd368…` and
   that supersedes rev 4.
4. **Controls** — exhibit a positive case that does not resolve to its filed class, or a negative
   case that resolves cleanly to its filed class, under the recorded axis vectors.

## Does not claim

No gate verdict (G-F0 remains `pending`), no node status, no theorem, no physics result, no new
class id, and no class merge. New class ids are deferred to Human PI (controller finding CF-5 /
`astra-classscope-02`). Dispositions are proposals; the F0 lead adjudicates, and any disposition
recorded in the map needs a re-bound corpus hash first (Finding 1).

## Files

| file | sha256 |
|---|---|
| `artifacts/worker-083/f0_open_case_disposition/disposition.py` | `7b08325640faa11b212ce4f85014b28fb505d4330ef86ce803a56a79de783b0b` |
| `artifacts/worker-083/f0_open_case_disposition/dispositions.json` | `4f65ce5754e6d7d9f46e980508926cd2c80d333a0bcfd64a35ec0046c3730e71` |
