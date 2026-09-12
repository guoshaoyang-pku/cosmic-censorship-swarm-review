# W099-SCALAR-LOCATOR-READINESS-01 — AF-WCC-SCALAR-SPH locator resolvability at frozen L1

Bounded execution worker `worker-099` (recycled instance). Node **L1**, gate **G-LIT**,
class **`AF-WCC-SCALAR-SPH`**.

This completes the BL-4 decision support for the **fourth** frozen class. `worker-050` covered
`AF-WCC-VAC-GEN` (12 rows, `wcc_locator_resolution/`) and every SCC-bound row (34 rows,
`scc_locator_readiness/`); the 10 rows whose `class_mapping` is exactly `AF-WCC-SCALAR-SPH`
carry no SCC token and are not `AF-WCC-VAC-GEN`, so they were in neither scope. 8 of the 10
carry a weak `exact_locator` (INSPIRE/arXiv search query or `...` elision).

The task, population rule, proposal rule, thresholds, controls, verdict vocabulary, budget and
falsifiers were frozen in `PREREGISTRATION.json` **before any fetch** (sha256 `9ab9e8563cf0…`).

## Result (ledger pinned at `315c1914`, measured 2026-09-12 00:50–00:51 +08:00)

| rows in class | direct locator | weak locator | replacement proposed | live 200 + title match | unique | confirmed | failed | unverified |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 2 | 8 | 8 | **8** | **8** | **8** | 0 | 0 |

- **All 8 weak cells** (`SRC-013/016/044/045/046/075/076/077`, rows 13/16/44/45/46/75/76/77)
  have a proposed single-record replacement (`evidence_url` in every case) that was fetched
  **twice independently**, returned HTTP 200 both times, and matched the ledger title
  (7× `EXACT`, and all 8 unique across every row's locator columns).
- **Both direct cells** (`SRC-067` crossref works URL, `SRC-094` arXiv abs page) re-fetched
  HTTP 200 in both passes and matched (`CONTAINMENT` / `EXACT`); corroboration only, no repair
  claimed for them.
- **Stability:** 10/10 rows identical across pass 1 and pass 2 (same status, same normalised
  title). 28 live requests total (2 passes × (10 rows + 4 controls)).
- **Ledger did not move:** `315c19145065…` before and after.

Aggregate under the two BL-4 readings, for this class only:

| reading | status at `315c1914` |
|---|---|
| strict per-row (`exact_locator` must resolve) | **UNMET for 8/10** pure-class cells |
| query-provenance (`evidence_url` is the locator column) | all 10 rows carry a resolving `evidence_url` |

This is decision support, **not** a ruling: the criterion cannot pass silently under both, exactly
as `astra-lead-literature` filed in BL-4. Applying the 8 replacements would move the L1 hash and
void the current qualifying spot checks (BL-4 option ii).

## Controls (each run in both passes; 8/8 PASS)

| control | expectation | observation |
|---|---|---|
| C1 Penrose 1965 DOI `10.1103/PhysRevLett.14.57` | match | HTTP 200, title matched |
| C2 mutant DOI `10.4007/annals.2025.202.2.9999` | no match | HTTP 404, no record |
| C3 `SRC-075` arXiv abs + journal DOI | both match | both HTTP 200, both matched |

C1/C3 prove the matcher can accept, C2 proves it can reject; no ledger defect can hide behind an
always-accepting instrument.

## Per-row verdicts

| row | id | weak class | proposal | pass1 / pass2 | verdict |
|---:|---|---|---|---|---|
| 13 | SRC-013 | truncated | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 16 | SRC-016 | truncated | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 44 | SRC-044 | truncated | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 45 | SRC-045 | search_query | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 46 | SRC-046 | search_query | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 67 | SRC-067 | direct | `evidence_url` | 200 / 200 CONTAINMENT | DIRECT_OK |
| 75 | SRC-075 | truncated | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 76 | SRC-076 | truncated | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 77 | SRC-077 | truncated | `evidence_url` | 200 / 200 EXACT | REPAIR_CONFIRMED |
| 94 | SRC-094 | direct | `url` | 200 / 200 EXACT | DIRECT_OK |

## Files (sha256 measured on disk at 00:51:41 +08:00)

| file | role | sha256 |
|---|---|---|
| `PREREGISTRATION.json` | frozen task definition | `9ab9e8563cf0…` |
| `run_scalar_locators.py` | pinned-hash runner, 2 passes + controls | `a7cea3e062c2…` |
| `fetch_evidence.pass1.json` | pass-1 observations + controls | `3dfa130f50be…` |
| `fetch_evidence.pass2.json` | pass-2 observations + controls | `a2e79cb0fa00…` |
| `readiness.json` | **the readiness map** (per-row verdicts) | `297477689ec6…` |
| `raw/pass1/*.bin`, `raw/pass2/*.bin` | 28 raw bodies, hash-pinned | per-row in `readiness.json` |
| `run.log` | runner stdout | `608cabf54f98…` |

Inputs: `ledger/citation_audit.csv` = `315c19145065…` (pinned, unchanged before/after);
`ledger/theorems.jsonl` = `a1674f094979…` (read-only context, not consumed).

## Falsifiers

- **F1** any `REPAIR_CONFIRMED` proposal that does not resolve to the cited work (title mismatch)
  voids that row's confirmed verdict.
- **F2** a weak-classified row whose `exact_locator` is in fact a single-record resolvable locator
  voids that classification.
- **F3** any change to `ledger/citation_audit.csv` away from `315c19145065…` voids the whole table;
  the runner exits 3 and fetches nothing.
- **F4** a pass-2 observation differing from pass 1 in status or returned record voids the row's
  stability claim until re-fetched (measured: 0 such rows).
- **F5** a proposal colliding with another row's `exact_locator`/`evidence_url`/`url` voids the
  per-row uniqueness reading (measured: 0 collisions).
- **F6** control C1 failing to match or C2 matching would void the instrument, not the ledger
  (measured: 8/8 controls PASS).

## Authority and scope limits

Worker evidence only. This is **not** a ledger edit, **not** a G-LIT gate verdict, **not** an
L1-node completion, and **not** a `validation_status`. The canonical ledger is owned by
`astra-lead-literature`; a lead or the controller must merge any repair, and applying it moves the
L1 hash. Only the `exact_locator` field is under test — quoted evidence, `verdict`, `reviewer`,
`assessment` and mathematical content are not re-adjudicated. The 2 direct rows were re-fetched as
corroboration only; no repair is claimed for them.

## Re-run

```bash
python3 artifacts/worker-099/scalar_locator_readiness/run_scalar_locators.py
```

Exit 0 = emitted against the pinned ledger; exit 3 = ledger hash moved, table stale.
The runner overwrites the evidence/readiness files in place; `sha256sum -c *.sha256` from this
directory checks the pinned outputs.
