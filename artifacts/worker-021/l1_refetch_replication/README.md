# W021-L1-REPLICATION-01 — independent re-fetch replication of worker-086 L1 MISMATCH findings

**Status (worker authority only):** artifact emitted, `validation_status=unverified`.
No gate verdict, no node completion, no ledger edit is claimed by worker-021.

## Task (one class-bound, bounded task)

Replicate — not repeat — the three `MISMATCH` hard failures reported by worker-086 in
`artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json` (L1 check #4, G-LIT):

| row | citation | worker-086 verdict | classes |
|---|---|---|---|
| 4 | SRC-004 | MISMATCH (year + excerpt) | `AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN` |
| 25 | SRC-025 | MISMATCH (excerpt) | `AF-SCC-C2-VAC-GEN` |
| 33 | SRC-033 | MISMATCH (excerpt) | `AF-SCC-C2-VAC-GEN` |

Frozen input: `ledger/citation_audit.csv`, sha256
`315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (pinned; drift voids the run).

## Independence from worker-086

* **Transport:** arXiv Atom API `export.arxiv.org/api/query?id_list=…` for rows 4/25 (worker-086
  used `arxiv.org/abs/…` HTML); Semantic Scholar Graph API **and** INSPIRE API for row 33
  (worker-086 used Crossref). Raw bodies are stored under `raw/` and hashed in `report.json`.
* **Comparison:** LaTeX/unicode-normalised **token containment** (longest verbatim token run,
  threshold 12) in place of the raw character-similarity ratio that produced the MISMATCH flags.
  The worker-086-style character ratio is also recomputed for the record.

## Result — `MISMATCH_FINDINGS_NOT_REPLICATED` (3/3 rows `NO_DEFECT_FOUND`)

| row | title | authors | year | excerpt longest run | result |
|---|---|---|---|---|---|
| 4 | match | match | convention (ledger 2025 = declared Annals issue year; arXiv v1 2017 declared in venue) | **67 tokens** | no defect found |
| 25 | match | match | convention (ledger 2021 = declared CMP volume year; arXiv v1 2020) | **82 tokens** | no defect found |
| 33 | match | match | match | **54 tokens** | no defect found |

Worker-086-style raw char ratio on the same pairs: 0.085 / 0.335 / 0.305 — i.e. the low
similarity values are reproducible but are an artefact of comparing LaTeX- and
unicode-bearing text with a character metric, not evidence of a metadata defect.

Locator-quality observations **confirmed** (already soft findings in worker-086): `SRC-025`
and `SRC-033` carry search-query URLs in `exact_locator`, not exact locators.

## Controls (all passed; a check that cannot fail is not a check)

* **C+ positive:** the ledger excerpt is contained in the fetched record (3/3 rows).
* **C-1 matched-token masking:** masking every matched block (96 / 93 / 82 tokens) makes
  containment fail on all three rows.
* **C-2 deterministic shuffle (seed 21021):** shuffled abstract contains no ≥12-token run.
* **C-3 short generic phrase:** a 6-token generic phrase is rejected on all rows.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-021/l1_refetch_replication/run_l1_replication.py
sha256sum ledger/citation_audit.csv   # must stay 315c19145065…
```

## Non-claims

Three rows only — not a verdict on the other 94 rows, not a class-binding verdict, not a
gate verdict. Locator-quality issues are reported, not repaired. Worker-086's finding is
refuted as a *metadata defect*; its transport choice and locator observations are not.
