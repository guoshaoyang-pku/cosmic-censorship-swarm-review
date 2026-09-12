# worker-049 L1 spot check — status

**Task:** `astra-life02-l1-spotcheck` (G-LIT, deadline 01:30) — independent re-fetch spot check of
`ledger/citation_audit.csv` pinned at `sha256:315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`.

**Result:** spot check #5 at this hash (3rd at this hash after worker-07 #3 and worker-086 #4).
12 data rows never previously re-fetched at this hash, covering all four frozen classes, re-fetched
live from primary APIs: **12 MATCH / 0 PARTIAL / 0 MISMATCH / 0 FETCH_FAILED**, ledger hash stable
across the fetch window (before = after = `315c19145065`).

## Files

| file | role |
|---|---|
| `sample_freeze.json` | sample frozen **before** any fetch; rule + excluded covered set |
| `run_spotcheck_049.py` | stdlib re-fetch/compare harness (self-contained, re-runnable) |
| `spotcheck-l1-049.json` | full evidence artifact + sidecar `.sha256` |
| `fetch_log.tsv` | every fetch: timestamp, status, bytes, raw file, raw sha256, locator |
| `raw/` | 23 raw response bodies, hashed on receipt (never re-typed) |
| `../../reviews/L1-spotcheck-049.json` | review verdict (inconclusive, 4.0) emitted to the lead |

## Provenance note

`sample_manifest.json` (00:15:47) is an **orphaned pre-fetch freeze** written by the earlier instance
`worker-049-20260912T001230-897883`, which was killed before it fetched anything (no raw bodies, no
artifact). It is superseded by `spotcheck-l1-049.json`; its sample overlapped SRC-056 and SRC-091,
both of which this artifact re-fetched live.

## Findings handed up (not a gate verdict)

1. No mismatch in the 12 sampled rows; this does **not** accept the other 85 rows.
2. Check #4 (`worker-086`) recorded MISMATCH on **SRC-004, SRC-025, SRC-033** at this same hash —
   still open ledger defects, outside this sample.
3. Locator hygiene: 8/12 sampled rows carry a search-query `exact_locator` (each still has a
   record-level anchor via `arxiv_id`/`doi`/`evidence_url`).
4. **SRC-066** lacks a DOI and is marked "per secondary citation"; a declared OpenAlex title search
   resolves `10.1016/j.jfa.2016.06.013` (J. Funct. Anal. 2016), confirming the ledger year.
5. SRC-055 / SRC-056 excerpts carry trailing labelled "Journal reference…" addenda; their abstract
   cores are 100% covered, but the addenda are ledger annotations, not source text.
6. Gate-wise, the controller at 00:37:18 already counts 22 independent spot checks at this hash, so
   the L1 `>=3` criterion is satisfied; the remaining G-LIT blocker is **L0**.

## Authority

Worker output only: no gate verdict, no node status, no `validation_status=passed`, no mathematical
or class-separation claim. `numerics_lock` respected (no numerics work).
