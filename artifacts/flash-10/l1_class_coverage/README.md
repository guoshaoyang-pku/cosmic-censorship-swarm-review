# L1 class-coverage matrix — `ledger/class_coverage.csv`

**Worker:** flash-10 (execution worker 10, DeepSeek Flash breadth)
**Assignments:** astra `asg-2026-09-11-L1-deepseek-flash-10-19` (coverage matrix, node L1, gate G-LIT)
and astra `astra-glit-00` (independent G-LIT spot check, artifact `reviews/L1-spotcheck-10.json`)
**Status:** DRAFT / `validation_status = unverified`. **No completion is claimed**; only
lead-literature and reviewers 17–19 may accept this artifact or move L1/L0.

## 0. Re-run `2026-09-12T00:05+08:00` — supersedes §3 headline numbers

Falsifiers **F1 (staleness)** and **F4 (mapping gap)** were executed against the current L0
ledger. Inputs were byte-identical before and after the run:

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `7d78d2850b55…` |
| `ledger/citation_audit.csv` | `0b72b4190667…` |
| `artifacts/literature/registry.jsonl` | `72562908267a…` |

Re-run: `build_ledger_class_coverage.py` → `ledger/class_coverage.csv` `a7b1c976a3cf…`,
`coverage_summary.json` `e00c408e36f1…`. Validator `VALID` (380 rows, 95 sources),
self-test 8/8 mutants caught.

| class | covered | partial | none | unassessed | covered sources |
|---|---:|---:|---:|---:|---|
| `AF-WCC-VAC-GEN` | 7 | 15 | 70 | 3 | SRC-002/003/041/042/043/054/068 |
| `AF-SCC-C2-VAC-GEN` | 3 | 17 | 72 | 3 | SRC-022/080/081 |
| `AF-SCC-C0-VAC-GEN` | 3 | 25 | 64 | 3 | SRC-005/006/022 |
| `AF-WCC-SCALAR-SPH` | 8 | 6 | 78 | 3 | SRC-014/044/056/057/061/067/075/076 |

Coverage totals: covered 21, partial 63, none 284, unassessed 12 rows (3 sources:
`SRC-090`, `SRC-092`, `SRC-093` — the same three the L1 P4 queue names). 11 of the 12
previously unmapped sources are now bound in L0; the unassessed count fell 48 → 12 rows.

**Two changes matter, and both are ledger-side, not matrix-side:**

1. **C2 covered 8 → 3, C0 covered 9 → 3.** In this ledger revision `T-501`, `T-510`, `T-514`,
   `T-517`, `T-520`, `T-521` carry **empty `class_ids`**, so the Gowdy (`SRC-059/071`),
   matter-model (`SRC-056/057/058`) and mixed (`SRC-020/060/072`) entries no longer bind to the
   SCC classes at all — they land in `none` (the explicit leakage control). The surviving C2
   covered set is exactly `T-303` (SRC-022, weak-null-singularity structure) and `T-526`/`T-527`
   (SRC-080/081, C^{0,1}_loc weak-null result). **The §3 headline finding is therefore
   strengthened, not weakened:** with the matter/Gowdy entries class-unbound, no covered
   `AF-SCC-C2-VAC-GEN` cell is even a candidate generic AF **vacuum** C²-inextendibility theorem.
2. **`AF-WCC-VAC-GEN` covered 6 → 7** (`SRC-054`, `T-201`).

Everything below §0 (including the §3 tables and §4 queue counts) describes the superseded
snapshot `8fd4d7aa` and is retained only as the pre-re-run record.

## 1. Deliverables

| file | sha256 | role |
|---|---|---|
| `ledger/class_coverage.csv` | see the latest `comms/outbox/flash-10_artifact_class_coverage_*.json` (hash changes with the live ledger; recorded in every event) | assigned artifact: one row per ledger source × frozen class (snapshot `8fd4d7aa`: 364 rows = 91 sources × 4) |
| `artifacts/flash-10/l1_class_coverage/coverage_summary.json` | idem | counts, input hashes, empty cells, scope-flag review queue |
| `reviews/L1-spotcheck-10.json` | `d1ca86fad3a0863f3958624b186b5995980a740f9b4326a0c3b32fed563648ea` | independent re-fetch spot check, 6/6 rows match |
| `artifacts/flash-10/l1_class_coverage/build_ledger_class_coverage.py` | `935753d2…` (+ scope-flag patch) | deterministic generator |
| `artifacts/flash-10/l1_class_coverage/validate_class_coverage.py` | `eb098c34…` (+ scope-flag check) | acceptance checker + 8-mutant self-test |
| `artifacts/flash-10/l1_class_coverage/spotcheck_l1.py` | generator of the spot check | re-fetches from each row's own locator |

**Input snapshot** (recorded in `coverage_summary.json.inputs`): `ledger/theorems.jsonl`
`8fd4d7aacb74…`, `ledger/citation_audit.csv` `6f1f3a6c4305…`, `artifacts/literature/registry.jsonl`
`d3dc81636239…`. The ledger is **live** (it grew 52→60 entries and 77→91 sources during this run; `coverage_summary.json` always holds the current counts);
every emitted event carries the hash of the snapshot it was built from, and the generator must be
re-run before any gate decision.

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/flash-10/l1_class_coverage/build_ledger_class_coverage.py
python3 artifacts/flash-10/l1_class_coverage/validate_class_coverage.py            # VALID, structural completeness
python3 artifacts/flash-10/l1_class_coverage/validate_class_coverage.py --self-test # 8/8 mutants caught
python3 artifacts/flash-10/l1_class_coverage/spotcheck_l1.py                        # G-LIT spot check
```

## 2. Coverage rule (exact)

Rows inherit the class binding **from the L0 ledger**; this matrix does not re-adjudicate
`class_ids` (that is A1's job). Given source `S` and frozen class `C`:

- **covered** — ∃ accepted entry `E` with `S ∈ E.source_ids`, `C ∈ E.class_ids`,
  `E.entry_kind ∈ {theorem, counterexample_candidate}` and
  `E.conclusion_type ∈ {theorem, counterexample}`. The row carries `E.statement_exact` verbatim
  and `E.theorem_id`.
- **partial** — `S` is bound to `C`, but only through conjecture / definition / review /
  numerical evidence / stability / conditional / preprint / provisional entries.
- **none** — `S` is in the ledger registry but no entry binds it to `C`. Includes sources bound
  only to the non-frozen classes (`DEFINITIONS`, `AF-SCC-OTHER-MODELS`, `AF-WCC-VAC-BH-FORM`,
  `AF-WCC-VAC-NS-CONSTR`) — the explicit class-leakage controls.
- **unassessed** (declared extension) — `S` has **zero** ledger entries, so no assessment is
  possible. Writing `none` here would assert a negative that was never checked. 12 sources:
  `SRC-007, SRC-008, SRC-009, SRC-010, SRC-012, SRC-036, SRC-054, SRC-055, SRC-084, SRC-086,
  SRC-088, SRC-090` (48 rows), each with the next falsifier *"map this source to at least one
  ledger entry and re-run"*.

## 3. Headline matrix (snapshot `8fd4d7aa`; live counts in `coverage_summary.json`)

| class | covered | partial | none | unassessed | covered sources |
|---|---:|---:|---:|---:|---|
| `AF-WCC-VAC-GEN` | 6 | 14 | 59 | 12 | SRC-002/003/041/042/043/068 |
| `AF-SCC-C2-VAC-GEN` | 8 | 14 | 57 | 12 | SRC-022/056/057/058/059/071/080/081 |
| `AF-SCC-C0-VAC-GEN` | 9 | 23 | 47 | 12 | SRC-005/006/020/022/056/057/058/060/072 |
| `AF-WCC-SCALAR-SPH` | 8 | 7 | 64 | 12 | SRC-014/044/056/057/061/067/075/076 |

**"Covered" is not "proved".** It means the ledger contains a theorem-strength binding to the
class; the binding's own scope can still be narrower than the class. The decisive decomposition:

- `AF-SCC-C2-VAC-GEN` (8 covered) decomposes into four disjoint kinds:
  (a) **non-asymptotically-flat vacuum** — T³-Gowdy `T-520` (SRC-059/071), an unconditional
  generic C²-inextendibility theorem but on compact Gowdy symmetry;
  (b) **matter models** — spherical Einstein–Maxwell–real-scalar `T-514` (SRC-056/057/058);
  (c) **vacuum weak-null-singularity structure** — `T-303` (SRC-022), not a generic
  initial-data theorem;
  (d) **Lipschitz-type weak-null result** — `T-526/T-527` (SRC-080/081), C^{0,1}_loc
  inextendibility without symmetry, conditional on the assumed curvature blow-up.
  **No generic asymptotically flat vacuum C²-inextendibility theorem appears in any covered
  cell.** This independently corroborates the ledger's provisional `T-401` ("no theorem
  located…") by a second route, and it is the strongest single finding of this matrix. Falsifier:
  an accepted `AF-SCC-C2-VAC-GEN` entry that is generic AF **vacuum** and concludes
  C²-inextendibility.
- `AF-SCC-C0-VAC-GEN` (9 covered): exact Schwarzschild (`T-301/302`), static/matter-model C⁰
  results, and the conditional Dafermos–Luk interior statement that makes the *generic* C⁰
  formulation expected false. No unconditional generic AF vacuum C⁰ theorem.
- `AF-WCC-VAC-GEN` (6 covered): 3 falsifier cells (SRC-002/003/068 — vacuum naked singularities,
  non-generic) and 3 supporting collapse/trapped-surface results (SRC-041/042/043). No WCC theorem.
- `AF-WCC-SCALAR-SPH` (8 covered): Christodoulou-type instability/codimension results, a robust
  a priori estimate (SRC-014/075/076) and Price-law decay — still not completeness of future
  null infinity.

Empty cells (the assignment's "interesting output"): **227 `none` + 48 `unassessed` of 364 rows**.

## 4. Scope-flag review queue (for A1)

Because class bindings are inherited, the matrix flags every covered/partial cell whose strongest
entry's own scope mentions spherical symmetry, charge/Maxwell, a cosmological constant, extra
matter, or linearity. `coverage_summary.json.scope_flag_review_queue` holds the current review rows (19 at snapshot `8fd4d7aa`)
(e.g. SRC-020/060/072 covered for `AF-SCC-C0-VAC-GEN` while the theorem is spherical EM-scalar).
This is a review target list, not a verdict: either the ledger binding is justified, or the
binding — not this matrix — must change.

## 5. G-LIT independent spot check (`reviews/L1-spotcheck-10.json`)

Re-fetched 6 of the first 20 ledger rows from **their own locators** (arXiv API `id_list`, INSPIRE
API), quoted the fetched text, and compared it verbatim with the ledger `evidence_excerpt`:

| source | locator | verdict |
|---|---|---|
| SRC-002 | arXiv:1912.08478 | match_verbatim_with_elisions (token coverage 0.982) |
| SRC-004 | arXiv:1710.01722 | match_verbatim_with_elisions (0.987) |
| SRC-006 | arXiv:1711.11380 | match_light_edit (1.000) |
| SRC-009 | arXiv:2606.25755 | match_verbatim_with_elisions (1.000) |
| SRC-014 | arXiv:math/9901147 | match_exact_substring (1.000) |
| SRC-011 | INSPIRE 54979 (Penrose 1969) | match_metadata_fields (title/author/DOI identical) |

**0 mismatches, 0 hard failures**; ledger left unmodified. Verdict: `accept` (score 5). Note that
"match_verbatim_with_elisions" means the excerpt is a verbatim composite of the fetched abstract
with sentences elided — content is supported, not a contiguous quotation. The two rows that first
read as `partial` under a crude token metric (SRC-014's trailing journal-ref suffix; SRC-011's
metadata rendering) were comparator artifacts and are documented as such in the JSON.

## 6. Failures and limitations (reported, not hidden)

1. **`web_search` tool unavailable.** All three searches failed with
   `TypeError: fetch failed` against `https://api.deepseek.com/anthropic/v1/messages`. Workaround:
   direct HTTPS (arXiv API) from Python/curl; **plain HTTP port 80 times out**.
2. **Live-ledger drift.** The ledger changed repeatedly during this run (52→60 entries,
   77→91 sources). The matrix is a snapshot; the generator is deterministic, writes atomically and
   is re-runnable, and every event records its input hashes. A watcher re-runs it when the ledger
   stabilises.
3. **No adjudication** of L0 class bindings, and no claim about theorem correctness — A1's job.
4. **Companion registry matrix** (`class_coverage.registry_based.csv`, 120 rows / 30 sources,
   built from the flash-10 verified arXiv registry with 34 raw XML responses) is retained for
   triangulation; three auto-selector mismatches were manually rejected (`overrides.json`).
5. Method limitation: the matrix can only see the ledger. A class whose anchor source is not yet
   in L0 shows as `unassessed`/`none`, not as "open" in the mathematical sense.

## 7. Next falsifiers

- **F1 (staleness):** re-run the generator against the frozen L0 hash; if any covered cell changes
  class or strength, §3 must be re-derived.
- **F2 (C2 gap):** produce one accepted ledger entry with `AF-SCC-C2-VAC-GEN` that is a generic
  asymptotically flat **vacuum** C²-inextendibility theorem (not Gowdy, not matter, not
  weak-null/Lipschitz structure). If it exists, §3's headline finding and `T-401` are falsified.
- **F3 (leakage):** A1 adjudicates any row in `scope_flag_review_queue`; a single rejected binding
  changes that class's covered count.
- **F4 (mapping gap):** map the 12 unmapped sources; if any is a class anchor, `unassessed` drops
  and a class's coverage may strengthen.
- **F5 (spot check):** re-fetch any matched row and find the excerpt absent or the locator
  resolving to a different work; the `accept` verdict then flips to `revise`.
