# W056-L1-SPOTCHECK-05 — independent live re-fetch spot check of the L1 citation ledger

**Actor:** worker-056 (no assignment card existed for this slot; task self-declared at 00:19:30
and claimed in `comms/outbox/worker-056.jsonl`).
**Node/gate:** L1 / G-LIT. **Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN,
AF-WCC-SCALAR-SPH.
**Purpose:** G-LIT records *2 independent re-fetch spot checks; required >= 3*. This is an
independent third check binding to the frozen L1 hash
`ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
(verified before and after the fetch window; no drift).

## Artifacts

| file | role | sha256 |
|---|---|---|
| `run_spotcheck_056.py` | deterministic stdlib-only runner (raw bodies cached under `raw/`) | see outbox event `w056-...-artifact-runner` |
| `spotcheck-l1-056.json` | hash-pinned result record, per-row evidence and verdicts | see outbox event `w056-...-artifact-spotcheck` |
| `raw/*.body` | raw fetched bodies (arXiv Atom / Crossref JSON / arXiv abs HTML) | each sha256 recorded in the JSON |

Re-run: `python3 artifacts/worker-056/l1_spotcheck/run_spotcheck_056.py` (fail-closed exit 2 if
the ledger hash is not the frozen pin or the file drifts mid-run).

## Sample (declared before fetch)

* **S1** rows 45,53,61,69,77,85,93 — frame 41–95, stride 8 offset 4, *disjoint* from check #3
  (flash-07: 41,49,57,65,73,80,81,89).
* **S2** row 40 — 1–40/41–95 frame boundary, unsampled by #3/#4.
* **S3** rows 4,25,33 — independent re-test of check #4's (worker-086) three MISMATCH hard failures.
* **S4** row 1 — instrument control (check #4 MATCH).
* **S5** row 96 — terminal frame.
* 13 rows; ledger text was never used as evidence. `export.arxiv.org` rate-limited (429) during the
  run; affected rows fell back to the live `arxiv.org/abs/<id>` primary page after 3 retries, and
  the source actually used is recorded per row in `fetched[].source`.

## Verdict rule (declared before fetch)

MATCH = title exact ∧ first-author surname present ∧ a fetched year equals the ledger year ∧ exact
locator ∧ no topical-summary quote. PARTIAL = any of: title not exact, year off by one, locator is
a search query, quote scores < 0.6 against the fetched abstract. MISMATCH = title/author/year
failure. FETCH_FAILED = no live source. A quote with no fetched abstract to compare against is
recorded `no-fetch-abstract` and is **not** escalated.

## Results — 13/13 fetched, **0 MISMATCH**

| verdict | n | rows |
|---|---:|---|
| MATCH | 3 | 1, 93, 96 |
| PARTIAL | 10 | 4, 25, 33, 40, 45, 53, 61, 69, 77, 85 |
| MISMATCH | 0 | — |
| FETCH_FAILED | 0 | — |

Every sampled row's **title matched exactly** and **first author matched**; every ledger year was
reproduced by a fetched year candidate. PARTIAL verdicts are all hygiene signals, not identity
failures:

* **search-query locators (8 rows):** SRC-025, 033, 040, 045, 053, 069, 077, 085 carry API/query
  URLs in `exact_locator` rather than a specific work page. The works resolve, but a query URL is
  not a locator (a later index change can silently repoint it).
* **quote not verbatim (5 rows):** SRC-004 (0.033), 025 (0.013), 040 (0.423), 053 (0.010),
  061 (0.022) — the ledger excerpt is a topical paraphrase, not the fetched abstract text.
  SRC-045 is near (0.670); SRC-085/093/096 are verbatim (0.973/0.973/0.963). SRC-001/033/069/077
  could not be quote-assessed (the fetched registry record carries no abstract).

## Re-test of check #4's hard failures (the substantive finding)

| row | citation | check #4 | check #5 | check #5 core states |
|---|---|---|---|---|
| 1 | SRC-001 | MATCH | MATCH | title exact, author match, year match |
| 4 | SRC-004 | MISMATCH | PARTIAL | title exact, author match, year match (2017 arXiv / 2025 Annals both fetched) |
| 25 | SRC-025 | MISMATCH | PARTIAL | title exact, author match, year match (2020 arXiv / 2021 CMP both fetched) |
| 33 | SRC-033 | MISMATCH | PARTIAL | title exact, author match, year match |

**None of check #4's three MISMATCH verdicts reproduces.** In all three the bibliographic identity
(title, first author, year) is reproduced from live sources; the check-#4 failures trace to (a)
comparing the ledger's *journal* year against the *arXiv v1* year, and (b) escalating
non-verbatim quotes to hard failure. Under the rule declared here, those three rows are PARTIAL at
worst. This does not by itself clear the ledger: it narrows the outstanding L1 issues to locator
quality and quote fidelity.

## Non-claims and falsifiers

* No gate verdict, no node completion, no ledger edit; G-LIT remains pending with the controller.
  A worker event cannot move a gate.
* Verdicts bind only to ledger sha `315c19145065`; drift voids the check and forces a re-pin.
* Falsified by: any sampled row whose title/author/year is not reproducible from a live fetch at
  the frozen hash; ledger drift during the window; or a re-fetch that contradicts a recorded
  retest verdict (e.g. showing row 4/25/33 genuinely fail identity).
* Quote similarity is a fidelity signal only; class mapping was read for topical consistency and
  is not a scope verdict.
