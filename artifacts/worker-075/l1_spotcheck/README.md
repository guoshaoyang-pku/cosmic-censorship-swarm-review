# W075-L1-SPOTCHECK-05 — independent re-fetch spot check at frozen L1 hash

Task taken by `worker-075` (no assignment card existed for this slot). Bounded, class-bound
task on node **L1** (gate **G-LIT**), classes **AF-SCC-C2-VAC-GEN** / **AF-SCC-C0-VAC-GEN**.

## Why this task

The controller gate audit at 2026-09-12T00:17:46 reports G-LIT pending with the L1 criterion
"*>=3 independent re-fetch spot checks*" and only **2** checks bound to the frozen
`ledger/citation_audit.csv` hash `315c19145065`; that unmet item is why this task was taken.
This check adds one more independent binding one. It also independently replicates the three
`MISMATCH` hard failures that `worker-086` recorded for rows SRC-004, SRC-025, SRC-033 at the
same frozen hash.

> **Errata (2026-09-12T00:30).** The first revision of this README and the claim event
> `w075-20260912T0025-claim-spotcheck` said this was "the third binding L1 spot check". That
> was true at emission (2 were bound at 00:17:46) but the parallel 100-worker cohort produced
> many more while this check ran. The durable contribution of `W075-L1-SPOTCHECK-05` is the
> **independent replication of the worker-086 MISMATCH rows**, not the ordinal. `worker-079`
> reached the same disposition independently (its `check4_disposition`): all three check-#4
> MISMATCH verdicts are method-level, not citation-fabrication findings. `worker-079` also
> measured the population-level locator issue (67/97 `exact_locator` entries are search
> queries); this check only reports the 3 it sampled.

## Pre-registered sample (frozen before any fetch)

* frame: all 97 data rows of `ledger/citation_audit.csv` at sha256 `315c19145065…`
  (the script is fail-closed: any other hash aborts before fetching)
* adjudication set **A** = {SRC-004, SRC-025, SRC-033} — the worker-086 MISMATCH rows
* fresh set **F** = rows whose `class_mapping` contains `AF-SCC-C2-VAC-GEN`, excluding A,
  sorted by `citation_id`, publisher DOI present (`prefix != 10.48550`), **first and last**
  → SRC-014, SRC-083
* sample = A ∪ F = SRC-004, SRC-014, SRC-025, SRC-033, SRC-083

## Method

* Crossref REST `api.crossref.org/works/<doi>` for every publisher DOI; INSPIRE REST
  `inspirehep.net/api/literature/<recid>` and `/api/doi/<doi>` for the abstract source.
* Raw response bodies are stored byte-for-byte under `fetched/` and sha256-hashed in the
  artifact. Every identity/excerpt verdict is recomputed from those bodies by
  `verify_spotcheck_075.py`; the ledger CSV is not re-read during verification.
* Excerpt support = content-token coverage and 8-gram coverage of the ledger
  `evidence_excerpt` against the fetched abstract (`supported` if 8-gram ≥ 0.4 or token
  coverage ≥ 0.6). A missing abstract stays `inconclusive-no-abstract`, never upgraded.
* Year rule: the ledger year is the journal year where the venue field names one; a
  one-year gap against the registry is `off-by-one`, not silently accepted.

## Result (5 rows, 11 fetches, 0 hard failures)

| row | classes | title | author | year (ledger vs registry) | excerpt | exact_locator |
|---|---|---|---|---|---|---|
| SRC-004 | C0;C2 | exact | match | 2025 = 2025 | supported (0.92 8g) | exact |
| SRC-014 | C2;SCALAR | exact | match | 1999 = 1999 | supported (0.86 8g) | exact |
| SRC-025 | C2 | exact | match | 2021 = 2021 | supported (0.67 8g) | **search_query** |
| SRC-033 | C2 | exact | match | 2018 = 2018 | supported (0.88 8g) | **search_query** |
| SRC-083 | C0;C2 | exact | match | 2025 = 2025 | supported (0.68 8g) | **search_query** |

## Adjudication of the worker-086 hard failures

| row | worker-086 states | this check | reason |
|---|---|---|---|
| SRC-004 | year mismatch | **does-not-replicate** | 2025 is the Annals 202(2) 2025 journal year at the ledger DOI; worker-086 compared against the arXiv v1 (2017) preprint year, which the ledger venue field discloses. |
| SRC-025 | year partial, excerpt mismatch | **does-not-replicate** | DOI registers 2021 (ledger year 2021); abstract coverage against INSPIRE is 0.88 token / 0.67 8-gram. |
| SRC-033 | title prefix-45, excerpt mismatch | **does-not-replicate** | token-level title match against Crossref and INSPIRE; abstract coverage 0.96 token / 0.88 8-gram. |

The separate worker-086 **locator-hygiene** finding replicates for SRC-025, SRC-033 and
SRC-083 (`exact_locator` is a search query, not an exact citable locator); it does not apply
to SRC-004 or SRC-014. Those three rows are reported as findings `W075-F-*-LOCATOR`; this
worker does not edit the ledger.

## Falsifier

Re-run `run_spotcheck_075.py --offline` and then `verify_spotcheck_075.py`. The artifact is
falsified if (a) any stored `fetched/` body re-hashes differently, (b) any recomputed
title/author/year/excerpt verdict differs from the recorded one, or (c) a fresh fetch of a
sampled DOI resolves to a different work than the ledger title/authors. The verifier also
runs a negative control: mutating the SRC-004 registry year to 1900 must flip its year
verdict to `mismatch`.

## Files

| file | role |
|---|---|
| `spotcheck-l1-075.json` | evidence artifact (records L1 hash before/after, all fetch hashes, verdicts, adjudication) |
| `run_spotcheck_075.py` | fetch + compare script (`--offline` reproduces from cache) |
| `verify_spotcheck_075.py` | independent recomputation + negative control |
| `fetched/*.json{,.meta.json}` | raw registry bodies and fetch metadata |

**Authority note:** worker evidence only. This worker cannot set `status=done`,
`validation_status=passed`, or any gate verdict; the literature lead / controller adjudicates.
