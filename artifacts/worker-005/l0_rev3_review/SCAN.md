# W005-L0-REV3-REVIEW-01 — independent L0 review (read-only)

| field | value |
|---|---|
| worker | worker-005 (instance `worker-005-20260912T004258-968807`) |
| node / class / gate | `L0` / AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH / `G-LIT` (coverage for `G-AUDIT` A1) |
| assignment | none in `comms/inbox/worker-005.jsonl`; task taken from the open map node `L0` under the worker rule (the reconcile card `astra-life04-l0-freeze-reconcile` landed the announce-and-hold pin at 00:44:46, and no L0 blind-review card was dispatched in the 00:44:18 audit batch) |
| pins | `ledger/theorems.jsonl` a1674f094979… (62 rows); `ledger/citation_audit.csv` 315c19145065… (97 rows); measured T0 == T1 |
| verdict file | `reviews/L0-review-worker-005-rev3.json` |
| report | `artifacts/worker-005/l0_rev3_review/report.json` |
| instrument | `artifacts/worker-005/l0_rev3_review/check_l0_rev3.py` (stdlib only, read-only, strict duplicate-key JSONL loader, selftest 9/9 mutants caught, 5/5 controls pass) |
| authority | **no gate verdict, no node completion, no self-pass**; worker events cannot move `status` or `validation_status` |

## Result — revise (score 3.0): content and honesty pass, one evidence-hygiene hard failure

| check | verdict | measured |
|---|---|---|
| L0-P1 pins, parse integrity, counts | pass | 62 ledger rows / 97 audit rows / 97 sources; no duplicate keys, no parse errors; pins stable |
| L0-P2 schema completeness, unique ids | pass | all 23 required keys on every row; 0 duplicate theorem_ids; no empty required fields |
| L0-P3 source resolution, locators | pass | 0 dangling source_ids; 0 locatorless registry records |
| L0-P4 verification-status honesty | pass | every `abstract-read` row has ≥1 abstract/full-text anchor; 0 `verified` rows grounded only in metadata |
| L0-P5 unresolved disclosure | pass | `unresolved` present and populated on all 62 rows (0 empty); D-009 is the sole `unverified` row |
| L0-P6 class-token discipline | pass | 0 tokens outside the four frozen classes |
| L0-P7 conclusion-type discipline | pass | vocabularies respected; 0 claims missing `does_not_imply`/`falsifiers` |
| L0-P8 ledger ↔ citation-audit binding | pass | one audit row per registry source; all resolver_result=resolved; `used_by_theorems` mirrors ledger usage on all 97 rows (0 mismatches both directions) |
| L0-P9 no-binding sources | pass | the 5 `assessed_no_binding` sources are cited by no row and carry no `used_by_theorems` |
| **L0-P10 exact_locator exactness** | **FAIL** | **67/97 audit rows carry a discovery query (arXiv `api/query`, INSPIRE `?q=`) in the column named `exact_locator`; 10 are `sortBy=submittedDate` and can change over time; 67/67 are repairable from the registry's exact url/DOI/arXiv id** |

**Hard failure HF-W005-L0-01.** `artifacts/literature/L0_L1_ACCEPTANCE.md` states "The L1 `exact_locator`
column carries the primary page/record URL"; the measured data contradicts this on 69% of rows. The
ledger rows themselves are unaffected — this is a defect in the audit layer, and the fix is mechanical
(set `exact_locator` to the registry record url; keep the discovery query in a separate column).

Advisory findings: 21 rows with no class binding (`U1`); T-515/T-528 span WCC and SCC in one row (`U2`);
13 rows mix metadata-only and abstract anchors (`U3`); `assessment` mixes id lists and prose (`U4`);
`entry_kind` has no documented vocabulary, singleton `background` (`U5`).

## Primary-source spot check (pre-registered in `spotcheck_plan.json` before fetching)

Sample rule: first row in file order with each frozen class alone, plus the sole `unverified` row;
first abstract-level source of each. 5/5 resolved HTTP 200 and 5/5 titles matched. 2/5 scope-verified
from the fetched abstract (D-001 ← SRC-001 verbatim WCC statement; D-002 ← SRC-004 C⁰-stability/C⁰-
inextendibility abstract). 3/5 metadata-consistent only: D-003's sampled locator is the arXiv query
that exposed L0-P10, and T-101/D-009 are already labelled provisional/unverified by the ledger, so the
disclosure is honest. Raw excerpts and hashes: `spotcheck_results.json`.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-005/l0_rev3_review/check_l0_rev3.py --report --selftest   # exit 1 while L0-P10 fails
```

## Falsifier

Re-measure the two pins; a ledger or audit sha256 differing from the reviewed hashes, a repaired
`exact_locator` column carrying registry record urls (falsifies HF-W005-L0-01 specifically), a sampled
locator resolving to a different work, or a different reading of a cited abstract that contradicts a
row's `statement_exact` voids or refutes this review. The review is superseded, not refuted, by a
repaired ledger whose `verification_status` derivation changes.
