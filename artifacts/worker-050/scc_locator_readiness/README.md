# W050-SCC-LOCATOR-READINESS-02 — SCC-class locator readiness map at frozen L1

Bounded worker task (worker-050, instance `worker-050-20260912T003109-968807`).
Class: `AF-SCC-C2-VAC-GEN` + `AF-SCC-C0-VAC-GEN` · Node: `L1` · Gate: `G-LIT`.
Gate criterion under test: *"ledger rows have resolvable locators"* — the half left
ambiguous by blocker **BL-4** (`exact_locator` column semantics at L1 `315c1914`).

## Why this task

`astra-lead-literature` filed BL-4 at 00:25:28: 67 of 97 `ledger/citation_audit.csv` rows carry a
search-query or truncated string in `exact_locator`, so the G-LIT criterion cannot pass silently
under both readings. Two controller options are open:

- **(i)** rule that `exact_locator` is query-provenance and `evidence_url` is the locator column; or
- **(ii)** authorize a bounded metadata-only patch rewriting the 67 cells, accepting an L1 hash move
  and re-running the spot checks at the new hash.

This artifact is decision support for that ruling, **for the two SCC classes only**. The sibling
task `W050-WCC-LOCATOR-REPAIR-01` already covered the 12 `AF-WCC-VAC-GEN` rows (6 weak, 6/6
repaired). Nothing here re-opens those rows.

## Method (read-only; the ledger is never edited)

1. Pin `ledger/citation_audit.csv` at sha256 `315c19145065…`; both scripts exit 3 if the bytes move.
2. Select every row whose `class_mapping` contains `AF-SCC-C2-VAC-GEN` or `AF-SCC-C0-VAC-GEN`
   (**34 rows**: 8 direct, 26 weak).
3. Propose the replacement from the ledger's own columns, in order
   `evidence_url` → `url` → `doi` → `arxiv_id`, accepting only a single-record locator
   (rejects search endpoints and `...` elisions).
4. Live-fetch the proposal: accept only HTTP 200 **and** a normalised title match
   (exact normalised equality, normalised containment, or token-F1 ≥ 0.75).
5. Certify the proposal is globally unique across all 97 rows' `exact_locator`/`evidence_url`/`url`;
   a collision is emitted as `FAIL_PROPOSAL_COLLISION`, never hidden.
6. Re-fetch every proposal in a second independent pass and compare observations.

`assemble_readiness.py` is deterministic given the ledger and the fetch-evidence file; its
`--selftest` exercises the classifier, collision detection, fail-closed verdicts and uniqueness on
synthetic rows.

## Result (measured 2026-09-12 ~00:35–00:40 +08:00, ledger `315c1914`)

| scope | rows | direct | weak | replacement proposed | live 200 + title match | unique | failed | unverified |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all SCC-bound | 34 | 8 | 26 | 26 | **26** | **26** | 0 | 0 |

Per class composition (weak rows):

| bucket | rows | weak | confirmed | failed/unverified |
|---|---:|---:|---:|---:|
| `SCC-both-pure` (C0+C2) | 12 | 10 | 10 | 0 |
| `SCC-both+mixed` (C0+C2+WCC) | 2 | 2 | 2 | 0 |
| `SCC-C2-only` | 4 | 3 | 3 | 0 |
| `SCC-C0-only` | 4 | 3 | 3 | 0 |
| `SCC+mixed` (SCC+WCC or +Scalar) | 12 | 8 | 8 | 0 |

Independent cross-checks of the BL-4 measurement, recomputed here:

- whole table: 67 weak `exact_locator` cells over **43** distinct strings, 10 strings shared by >1
  row, maximum share 7 — this reproduces the lead's count exactly;
- SCC scope: 26 weak cells over 17 distinct strings; **17 of the 26** appear verbatim as another
  row's `exact_locator` in the full table (15 of them shared inside the SCC weak set);
- replacement candidates: `evidence_url` is non-empty for 95/97 rows and **all 95 values are
  distinct**, so the option-(ii) rewrite cannot introduce a new per-row collision;
- fetch stability: two independent passes, **34/34 observations identical** (HTTP 200, same
  normalised returned title), 0 mismatches (`recheck_summary.json`).

Everything 26/26 confirmed means, concretely: each of the 26 weak SCC rows has a proposed
replacement that (a) is a single-record locator, (b) was fetched twice with HTTP 200 and a matching
title, and (c) collides with no other row's `exact_locator`/`evidence_url`/`url`. It does **not**
mean the ledger has been patched, nor that the criterion is currently satisfied at `315c1914` —
under the strict per-row reading it is still unmet for these 26 cells.

## Files (sha256 measured on disk at 00:41 +08:00)

| file | role | sha256 |
|---|---|---|
| `fetch_locators.py` | live-fetch pass (network) | `aa1c5cc093e4…` |
| `assemble_readiness.py` | deterministic assembler + selftest | `5437ee6ff91b…` |
| `compare_rechecks.py` | two-pass stability comparison | `6109b02f4c2a…` |
| `fetch_evidence.json` | fetch pass 1 (34 observations) | `4168ccbef5b1…` |
| `fetch_evidence_recheck.json` | fetch pass 2 (34 observations) | `b4b2c7bb6e16…` |
| `readiness.json` | **the readiness map** (34 rows, per-row verdicts) | `0beea174ca29…` |
| `recheck_summary.json` | 34/34 stable, 0 mismatches | `b4a7bfe8b01b…` |

Inputs: `ledger/citation_audit.csv` = `315c19145065…` (pinned, unchanged through the task);
`ledger/theorems.jsonl` = `a1674f094979…` (read-only context, not consumed).

## Falsifiers

- **F1** any proposed locator that does not return the cited work (title/author mismatch) voids
  that row's CONFIRMED verdict.
- **F2** a row classified weak whose `exact_locator` is in fact a row-specific resolvable locator
  voids the classification for that row.
- **F3** any change to `ledger/citation_audit.csv` away from `315c19145065…` voids the whole table;
  re-run `fetch_locators.py` then `assemble_readiness.py` against the new bytes.
- **F4** a live re-fetch of a proposed locator returning HTTP ≠ 200 or a different record voids the
  row. Two passes already agree; a third that disagrees voids the row until re-fetched.
- **F5** a proposed replacement that collides with another row's locator voids the per-row reading
  for that proposal. Measured: 0 collisions.

## Authority and scope limits

Decision support only. This is **not** a ledger edit, **not** a gate verdict, and **not** a
`validation_status`. The canonical ledger is owned by `astra-lead-literature`; a lead or the
controller must merge any patch, and applying it moves the L1 hash and voids the current spot
checks (BL-4 option ii). Only the `exact_locator` field is under test — quoted evidence, `verdict`,
`reviewer` and the mathematical content are not re-adjudicated. The 8 direct SCC rows were fetched
as corroboration but need no repair and are not claimed as repaired.

## Re-run

```bash
python3 artifacts/worker-050/scc_locator_readiness/fetch_locators.py \
  --ledger ledger/citation_audit.csv \
  --out artifacts/worker-050/scc_locator_readiness/fetch_evidence.json
python3 artifacts/worker-050/scc_locator_readiness/assemble_readiness.py --selftest
python3 artifacts/worker-050/scc_locator_readiness/assemble_readiness.py \
  --ledger ledger/citation_audit.csv \
  --fetch-evidence artifacts/worker-050/scc_locator_readiness/fetch_evidence.json \
  --out artifacts/worker-050/scc_locator_readiness/readiness.json
python3 artifacts/worker-050/scc_locator_readiness/compare_rechecks.py \
  --first .../fetch_evidence.json --second .../fetch_evidence_recheck.json \
  --ledger ledger/citation_audit.csv --out .../recheck_summary.json
```

Exit 0 = emitted against the pinned ledger; exit 3 = ledger hash moved, table stale.
