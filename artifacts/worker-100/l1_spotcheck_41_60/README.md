# worker-100 — L1 spot check #4 (SRC-041..060)

Independent re-fetch spot check of `ledger/citation_audit.csv` rows SRC-041..060 at the pinned
sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`, executed as the
worker leg of assignment `astra-life02-l1-spotcheck` (one of the two further independent checks
it requires). Reviewer `worker-100` is distinct from `deepseek-flash-07`, `flash-10` and
`flash-11`.

**Verdict set: 20 checked — 20 MATCH, 0 PARTIAL, 0 FAIL, 0 FETCH_FAILED.**

## Files

| file | role |
|---|---|
| `sample_frozen.json` | pre-registration (sample, locator priority, verdict rules, falsifier), written before any fetch |
| `spotcheck.py` | reproducible checker (method 4.2). `python3 artifacts/worker-100/l1_spotcheck_41_60/spotcheck.py` |
| `spotcheck-l1-100.json` | the report: inputs+before/after hashes, per-row sources with raw hashes, comparisons, verdicts |
| `spotcheck-l1-100.json.sha256` | report hash sidecar |
| `fetch_meta_worker100.json` | every fetch attempt (URL, status, bytes, sha256, elapsed) |
| `selftest.py` / `selftest_report.json` | instrument falsification control: 20/20 real excerpts match, 20/20 single-word mutations detected |
| `raw-worker100/` | raw fetched bodies (one per locator/row), referenced by path+sha256 in the report |
| `raw/` | earlier partial attempt from the 00:12 worker-100 leg (6 bodies + fetch_meta); kept as provenance, not used |
| `spotcheck-l1-100.v1-checkerbug.json`, `.v2.json`, `spotcheck.v2.py`, `fetch_meta_worker100.v*.json` | pre-verdict instrument snapshots (see revision note) |

## What was checked (and what was not)

Checked per row: the recorded locator resolves (HTTP 200); fetched title/authors/year are
consistent with the ledger row; and every quoted fragment of `evidence_excerpt` appears
verbatim in the fetched records (unquoted note text is checked by token coverage ≥ 0.85).
Sources were fetched from the row's DOI (Crossref), arXiv id (arXiv API), url (arXiv abs /
INSPIRE API), plus DataCite for `10.48550/*` DOIs. Both the row's `evidence_url` and
`exact_locator` were fetched; generic search-query results that do not carry the cited title are
recorded but excluded from the year/excerpt haystack.

**Not checked:** theorem statements against full texts, proofs, or any physics claim. The fetch
is metadata/abstract level, so a MATCH means the locator, bibliographic identity and quoted
abstract-level evidence are faithful — not that the paper proves what a ledger row may later be
used for.

## Class binding (frozen four)

For every sampled row the chain csv row → `used_by_theorems` → `ledger/theorems.jsonl`
`class_ids`/`informs_classes` was checked at one measured revision of the secondary input
(`a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`):

- 0 non-frozen class tokens in linked theorem rows;
- 0 missing theorem references;
- 0 csv class tokens without linked-theorem support;
- 7 rows carry the documented non-class annotation `(evidence/tag only)` in `class_mapping`
  (SRC-049, 051, 052, 053, 055, 059, 060) — recorded, not counted as a class token.

No hard failures. `ledger/citation_audit.csv` was byte-identical before and after the run.
`ledger/theorems.jsonl` was under active revision by its owner (pre-registered `ce42d205` →
`3e3d3553` → `a1674f09`); the final run read and pinned `a1674f09` for the whole chain check.

## Method revision note (why three snapshots exist)

Pre-verdict self-checks found measurement bugs, each fixed before any verdict was reported:
v1 read the arXiv feed title instead of the entry title, stopped at the first HTTP-200 locator
and mis-folded Unicode; v2 mis-split quoted text at apostrophes/`...` and did not parse arXiv
abs-page citation metadata or version history; v3's draft built the excerpt haystack without the
parsed abstracts. v4.2 adds apostrophe-aware quote scanning, LaTeX/Greek folding
(`H^1_{\text{loc}}` ≡ `H^1_loc`), per-source quote-match annotation (version divergence), and
arXiv `comment`/Crossref volume-page fields. The frozen sample and verdict rules in
`sample_frozen.json` were never changed; only the instrument was repaired. See
`selftest_report.json` for the control that the repaired instrument still fires.

## Falsifier

A later re-fetch at the same pinned csv sha256 yielding a different verdict for any sampled row
falsifies this verdict set; a csv hash change during a run invalidates that run (fail-closed).

## Status

Worker artifact only: `validation_status: unverified`. A worker cannot set `done`/`passed` or a
gate verdict, and no theorem or physics result is claimed here.
