# W022-L1-SPOTCHECK-05 — independent re-fetch spot check #5 (worker-022)

Bounded, class-bound task taken from the G-LIT immediate queue. No assignment card existed in
`comms/inbox/worker-022.jsonl`; the task was self-issued and declared in
`comms/outbox/worker-022.jsonl` before any fetch.

## Why this task

The G-LIT gate audit at `2026-09-12T00:17:27+08:00` names one exact unmet requirement:

> L1 measured `315c19145065`; 2 independent re-fetch spot check(s) bind to this hash
> (`artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json`,
> `artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json`), required >=3.

This artifact is a third binding check.

## What was done

1. `sample_manifest.json` froze the sample **before any fetch** at
   `2026-09-12T00:19:45+08:00`: ledger `ledger/citation_audit.csv` pinned at
   sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 data rows),
   rows `46, 54, 62, 70, 78, 86, 90–95` (12 rows), disjoint from worker-07's check #3
   (`41,49,57,65,73,80,81,89`) and worker-086's check #4 (`1,4,9,16,17,25,33,96,97`).
2. `run_spotcheck_022.py` re-fetched every sampled locator from the primary APIs
   (`export.arxiv.org/api/query`, `api.crossref.org/works/{doi}`), wrote raw bodies to `raw/`
   and recorded their sha256 in `fetch_log.tsv`.
3. Per-row comparison: title (normalized exact / containment / annotation-stripped containment /
   token-jaccard >= 0.8), returned locator identity vs queried locator, year, quoted
   `evidence_excerpt` tokens against the fetched abstract, and `used_by_theorems` referential
   integrity against `ledger/theorems.jsonl`.
4. Declared negative control `CTRL-01` (SRC-041 title vs arXiv:0908.1803) must return MISMATCH;
   it did (`jaccard 0.125`), so the comparator is not vacuous.
5. Ledger hash re-verified after fetching: no drift.

## Result

`spotcheck-l1-022.json` — **verdict PASS**, 12/12 rows MATCH, 0 mismatch / 0 partial /
0 unresolved, all four AF classes covered, negative control detected, ledger stable.

One soft finding: **SRC-086** (Luk–Oh, Annals 2019). The ledger title is the abbreviated form
`… initial data I (Crossref record, published version)`; the published/arXiv title carries the
subtitle `… initial data I. The interior of the black hole region` (strict token-jaccard 0.556).
Locator, authors and year resolve to the same work, so this is a ledger title-hygiene note, not a
wrong-work resolution. Pass 1 of the run used a strict comparator without annotation stripping and
flagged this row as MISMATCH; that output is retained at
`pass1_strict/spotcheck-l1-022-pass1.json` (`sha256 44ab4eb2386dc5b0…`) and the comparator change
is documented in `revision_note` inside the final artifact.

## Scope / non-claims

- Not a gate verdict and not a node completion; workers cannot set those.
- Only rows 46, 54, 62, 70, 78, 86, 90–95 are covered. Rows 96–97 and all mid-range rows are
  covered only by the other checks.
- Abstract-level support only; theorem statements are not read here.
- `verdict PASS` means "no falsifier triggered inside this frame at this pinned hash".

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-022/l1_spotcheck/run_spotcheck_022.py   # fail-closed on ledger hash mismatch
```

## Files

| file | role |
|---|---|
| `sample_manifest.json` | frozen sample, pinned ledger hash, disjointness proof, negative control |
| `run_spotcheck_022.py` | fail-closed runner (stdlib only) |
| `spotcheck-l1-022.json` | result artifact (counted by `research_map/astra_lifecycle.py:l1_spotchecks`) |
| `spotcheck-l1-022.json.sha256` | artifact hash sidecar |
| `raw/*.body` | raw API responses, one per fetch |
| `fetch_log.tsv` | tag, url, status, bytes, sha256, raw path |
| `pass1_strict/` | pass-1 output under the strict comparator (audit trail) |
