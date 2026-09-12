# W070-L1-LOCATOR-LIVE-02 — live re-resolution of the `arxiv-api-query` locator family

- **Task**: w070-l1-locator-live-02 (node L1, gate G-LIT, group literature)
- **Question**: At pinned ledger sha256, does each arxiv-api-query `exact_locator` re-resolve as recorded to the work its row claims?
- **Ledger pin**: `ledger/citation_audit.csv` sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
- **Frame**: `frame.json` sha256 `c9e655bfeb35c52072393be573b9347435df51f716d4b5b21bbf14fd246ee1d4` — written and hashed before the first live fetch
- **Instrument**: `run_live070.py` sha256 `2e9dfb86a98bfbede04c3e8d65fe2e6128717e87cba3a0809e33f69d56d09f7d` (revision 2)
- **Status**: `COMPLETE`; corpus_valid=True; ledger drift=False
- **Created**: 2026-09-12T00:51:10+08:00 → 2026-09-12T00:54:07+08:00

## Result

38 rows in the family, one fetch each of the URL as recorded:

| verdict | rows | meaning |
|---|---:|---|
| TOP_HIT_MATCH | 10 | claimed `arxiv_id` is entry rank 1 |
| HIT_IN_PAGE_NOT_TOP | 22 | claimed id present at rank 2–10 |
| NOT_IN_RETURNED_PAGE | 6 | claimed id absent from the returned page |
| FETCH_FAILED / PARSE_ERROR | 0 / 0 | no usable body |

As-recorded re-resolution rate to the claimed work at rank 1: **10/38 = 0.2632**. Top-hit rows: SRC-006, SRC-029, SRC-037, SRC-040, SRC-048, SRC-062, SRC-066, SRC-070, SRC-079, SRC-082.

Of 16 distinct locator strings, 9 are shared by 31 of the 38 rows (max 7 rows on one query). A query shared by k rows cannot be the exact locator of more than one of them.

### Per class (rows may carry more than one tag)

| class | rows | top | non-top | not in page |
|---|---:|---:|---:|---:|
| (evidence/tag only) | 13 | 2 | 9 | 2 |
| AF-SCC-C0-VAC-GEN | 20 | 8 | 9 | 3 |
| AF-SCC-C2-VAC-GEN | 13 | 4 | 7 | 2 |
| AF-WCC-SCALAR-SPH | 2 | 0 | 1 | 1 |
| AF-WCC-VAC-GEN | 10 | 4 | 5 | 1 |

### Rows that do not re-resolve to the claimed work at rank 1 as recorded

| row | id | class | rank | hits | verdict |
|---|---|---|---:|---:|---|
| 5 | SRC-005 | AF-SCC-C0-VAC-GEN | 2 | 6 | HIT_IN_PAGE_NOT_TOP |
| 7 | SRC-007 | (evidence/tag only) | 3 | 6 | HIT_IN_PAGE_NOT_TOP |
| 8 | SRC-008 | (evidence/tag only) | 4 | 6 | HIT_IN_PAGE_NOT_TOP |
| 9 | SRC-009 | (evidence/tag only) | 5 | 6 | HIT_IN_PAGE_NOT_TOP |
| 24 | SRC-024 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN | 6 | 10 | HIT_IN_PAGE_NOT_TOP |
| 25 | SRC-025 | AF-SCC-C2-VAC-GEN | 5 | 10 | HIT_IN_PAGE_NOT_TOP |
| 26 | SRC-026 | (evidence/tag only) | 2 | 6 | HIT_IN_PAGE_NOT_TOP |
| 27 | SRC-027 | (evidence/tag only) | 1 | 6 | HIT_IN_PAGE_NOT_TOP |
| 28 | SRC-028 | (evidence/tag only) | 3 | 6 | HIT_IN_PAGE_NOT_TOP |
| 30 | SRC-030 | (evidence/tag only) | 4 | 6 | HIT_IN_PAGE_NOT_TOP |
| 39 | SRC-039 | AF-WCC-VAC-GEN | 1 | 2 | HIT_IN_PAGE_NOT_TOP |
| 45 | SRC-045 | AF-WCC-SCALAR-SPH | 5 | 10 | HIT_IN_PAGE_NOT_TOP |
| 46 | SRC-046 | AF-WCC-SCALAR-SPH | — | 10 | NOT_IN_RETURNED_PAGE |
| 47 | SRC-047 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN | — | 10 | NOT_IN_RETURNED_PAGE |
| 49 | SRC-049 | (evidence/tag only) | 8 | 10 | HIT_IN_PAGE_NOT_TOP |
| 50 | SRC-050 | AF-SCC-C2-VAC-GEN | 3 | 10 | HIT_IN_PAGE_NOT_TOP |
| 51 | SRC-051 | (evidence/tag only) | 9 | 10 | HIT_IN_PAGE_NOT_TOP |
| 52 | SRC-052 | (evidence/tag only) | — | 10 | NOT_IN_RETURNED_PAGE |
| 53 | SRC-053 | (evidence/tag only) | — | 10 | NOT_IN_RETURNED_PAGE |
| 63 | SRC-063 | AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN | 8 | 10 | HIT_IN_PAGE_NOT_TOP |
| 64 | SRC-064 | AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN | — | 10 | NOT_IN_RETURNED_PAGE |
| 65 | SRC-065 | AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN | 7 | 10 | HIT_IN_PAGE_NOT_TOP |
| 78 | SRC-078 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-WCC-VAC-GEN | 1 | 6 | HIT_IN_PAGE_NOT_TOP |
| 81 | SRC-081 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN | — | 10 | NOT_IN_RETURNED_PAGE |
| 83 | SRC-083 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN | 4 | 9 | HIT_IN_PAGE_NOT_TOP |
| 84 | SRC-084 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN | 3 | 9 | HIT_IN_PAGE_NOT_TOP |
| 85 | SRC-085 | AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN | 6 | 9 | HIT_IN_PAGE_NOT_TOP |
| 91 | SRC-091 | AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN | 2 | 10 | HIT_IN_PAGE_NOT_TOP |

## Findings

- **locator_not_work_specific** (major): 9 distinct locator strings in the arxiv-api-query family are shared by 31 rows (max sharing 7); a shared query cannot top-resolve every row that cites it.
- **locator_does_not_reresolve_as_recorded** (major): 28/38 arxiv-api-query rows do not re-resolve, as recorded, to the claimed work at rank 1 (of which 6 return the target not at all in the page; 0 fetch failures; 22 present but not top).

## Controls (all must pass)

- offline Atom parser rank fixture: PASS
- live positive `recorded_title_query_finds_SRC-062` (target 2104.11857): PASS (n_hits=1, ids=['2104.11857'])
- live positive `recorded_title_query_finds_SRC-078` (target 2606.28253): PASS (n_hits=1, ids=['2606.28253'])
- live negative nonsense query: PASS (n_hits=0)
- idempotence refetch SRC-005: PASS (HIT_IN_PAGE_NOT_TOP vs HIT_IN_PAGE_NOT_TOP)
- predecessor TOP_HIT_MATCH row SRC-006 still top: PASS
- classification agreement vs predecessor census: 97/97

Re-execution of the predecessor's three live rows (verdict names normalized): SRC-005: QUERY_HIT_MATCH_NOT_TOP → HIT_IN_PAGE_NOT_TOP (agree); SRC-006: QUERY_TOP_HIT_MATCH → TOP_HIT_MATCH (agree); SRC-007: QUERY_HIT_MATCH_NOT_TOP → HIT_IN_PAGE_NOT_TOP (agree)

## Limits and authority

- One fetch per row at one ledger hash; arXiv ranking can change over time, so a rank is a measurement at the recorded time, not a permanent property. The falsifier covers re-runs.
- No ledger edit was made; the literature lead owns `ledger/citation_audit.csv`.
- Worker evidence only: no gate verdict, no node completion, no `validation_status=passed`, no mathematical claim.

## Falsifier

Re-run this instrument at the same pinned ledger hash. Falsified if any TOP_HIT_MATCH row re-runs as non-top, or if a row reported NOT_IN_RETURNED_PAGE appears at rank 1 on re-fetch, or if any control re-runs false. A ledger sha256 change away from the pin voids the run rather than falsifying it. Findings about locator specificity are falsified by editing the locator column so each row carries a work-specific locator (e.g. its own abs URL or id_list query) and re-running to TOP_HIT_MATCH on all rows.

## Raw evidence

- `raw/` holds the 38 fetched response bodies, one per row, hashed in `report.json`.
- `frame.json` + `frame.sha256.txt`: pre-registered frame and registration time.
- `superseded/report.rev1-reexec-name-defect.json` sha256 `7ccfcf560e8058d50adc5155c1bff72b433cbf4f5a5bc408adbffbd2da91b69f`: rev1 compared raw predecessor verdict names (QUERY_*) to this run's names, reporting agree=false on three semantically agreeing rows; normalization fixed, no measurement or verdict changed.
