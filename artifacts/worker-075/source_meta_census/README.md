# W075-SOURCEMETA-CENSUS-06 — source_meta scope-field census and "201 citations" reconciliation

- **worker**: worker-075 · **node**: L1 · **gate**: G-LIT
- **class binding**: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- **status**: worker evidence only; no gate verdict, no `done`, no `passed` (authority stays with the leads)
- **artifacts**: `source_meta_census_075.json`, `census_source_meta_075.py`, `verify_census_075.py`, this README

## Why this task

The G-LIT unmet list carries the figure **"201 citations have no source_meta scope fields; 100+
accepted records are self-certified"** (`research_map/research_map.json`, `gates[2].unmet[3]`).
Three further figures are in circulation for the same axis — lead-audit HF-03 "119 of 119 registry
entries" (`reviews/L0-review-lead-audit.json:17`), map `reviews[19]` "123 registry entries", and the
on-disk canonical files 97 registry rows / 62 ledger rows. No assignment card existed for slot
`worker-075`; this bounded, class-bound verification was taken from that immediate queue item. The
five axes named by HF-03 are `matter_model`, `cosmological_constant`, `dimension`, `symmetry`,
`formulation`.

## Method

`census_source_meta_075.py` reads 43 ledger/literature artifacts (read-only), records each file's
sha256, and pre-registers the definitions before measuring: source record = source/citation key +
title + locator; theorem record = `theorem_id`; citation link = `(theorem_id, source_id)` pair; a
record "carries axis A" iff the literal key A appears at top level or in a nested dict at depth ≤ 2.
A near-miss regex (`matter|lambda|cosmolog|dimension|dim|symmetr|formulation|scope|model`) reports
scope-like fields that are **not** the five axes. Five synthetic controls calibrate the detector
(flat, nested, near-miss-only, partial, empty).

`verify_census_075.py` re-derives every headline number with a separately written code path, checks
every recorded sha256 against disk, re-runs the controls on fresh objects, and independently
re-validates the 201 reconciliation.

## Result 1 — source_meta coverage is 0 at every measured universe

At the recorded snapshot hashes (see `input_files` in the JSON):

| universe | records | carry any of the 5 axes | carry all 5 |
|---|---:|---:|---:|
| source records, raw across files | 450 | **0** | 0 |
| source records, unique id | 151 | **0** | 0 |
| theorem records, raw | 297 | **0** | 0 |
| theorem records, unique id | 77 | **0** | 0 |
| source+theorem, raw | 747 | **0** | 0 |
| source+theorem, unique id | 228 | **0** | 0 |
| class-coverage rows | 388 | **0** | 0 |

Per frozen class, source records mapped by `class_mapping`/`class_ids`: AF-SCC-C0-VAC-GEN 67,
AF-SCC-C2-VAC-GEN 58, AF-WCC-VAC-GEN 26, AF-WCC-SCALAR-SPH 18 — **0 with any axis in every class**;
337 source records carry no frozen class token. `class_coverage.csv` covers all four classes for all
97 sources (388 rows, 0 axes).

Scope-like **proxies** do exist and are not the five axes: `scope_caveats` (285 theorem rows),
`scope_flags` in `ledger/class_coverage.csv` (388 rows; 354 `none`, 34 non-`none`, e.g.
`spherical_symmetry | charged_maxwell | extra_matter`), `class_scope` in
`ledger/citation_audit_scc_worker-009_spotcheck.csv`. A rev-3 handpatch was on disk during the
measurement (`artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl`,
sha `3e3d35531421`); it renames `status`→`content_status` and `supports_claim`→
`author_asserts_supports` and adds `review_status`/`acceptance_authority`, but adds **no** source_meta
axis in any of its 62 rows. HF-03 survives the handpatch.

## Result 2 — "201" is not the size of any single citation universe

The measured canonical universes are **151** unique sources, **77** unique theorems (**228** union),
**388** class rows, and **726** raw citation links (**183** unique `(theorem,source)` pairs). None is
201. Every "natural" reading of 201 sums heterogeneous files and double-counts ids, e.g.:

- `registry.jsonl` 97 + `citation_audit.csv` 97 + `w07-sources.jsonl` 7 = **201**, but only **104**
  distinct record ids (the registry and the audit are the same 97 sources);
- `registry.jsonl` 97 + `theorems.jsonl` 62 + `unresolved.jsonl` 12 + `w07-theorems.jsonl` 15 +
  `citation_audit_wcc_flash-08.jsonl` 15 = **201**, only **189** distinct ids.

The subset-sum search finds 40+ on-disk decompositions of 201 (≤9 parts) and 25 row-level disjoint
ones, all of which mix archive/superseded files; none is a canonical citation universe. The gate
figure therefore must not be used as a denominator — the correct denominators are the measured
universes above. (Historical 119/123 are likewise cross-file sums, not current measurements.)

## Falsifier

Re-run `python3 census_source_meta_075.py` then `python3 verify_census_075.py --offline`. This census
is falsified if (a) any input file re-hashes to a different sha256 than recorded, (b) any recomputed
universe size or per-axis count differs from the recorded value, (c) any calibration control flips,
or (d) a row that literally carries one of the five axis keys is classified as not carrying it.
**Drift warning**: the literature rev-3 patch was landing while this ran; the JSON binds to the
recorded hashes only, and any later ledger move voids the numbers until re-run.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-075/source_meta_census/census_source_meta_075.py
python3 artifacts/worker-075/source_meta_census/verify_census_075.py --offline
```
