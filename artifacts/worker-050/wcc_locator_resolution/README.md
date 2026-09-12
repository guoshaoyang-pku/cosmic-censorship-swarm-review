# W050-WCC-LOCATOR-REPAIR-01 — AF-WCC-VAC-GEN locator resolvability repair map

Bounded worker task (worker-050, instance `worker-050-20260912T002403-968807`).
Class: `AF-WCC-VAC-GEN` · Node: `L1` · Gate: `G-LIT`.

## Why

The G-LIT criterion says *"ledger rows have resolvable locators"*. The literature lead measured that
67/97 rows of `ledger/citation_audit.csv` carry a search-query or truncated string in
`exact_locator`, so the criterion is ambiguous at the frozen L1 hash and cannot pass silently under
both readings. This artifact removes the ambiguity for **one class**: every `AF-WCC-VAC-GEN` row
whose `exact_locator` is not a row-specific locator gets a proposed replacement that was
**live-fetched and metadata-matched** in this session.

## What was done

1. Pinned `ledger/citation_audit.csv` at sha256 `315c19145065…`; the runner refuses to certify a
   table if the bytes move (falsifier F3).
2. Selected the 12 rows with `class_mapping == AF-WCC-VAC-GEN`.
3. Classified each `exact_locator`: `direct_record_locator`, `search_query`, `truncated`, `non_url`.
4. For each non-direct row, proposed `evidence_url` (fallback `url`) and required a live fetch with
   HTTP 200 and a matching title. Candidates that could not be machine-verified (e.g. a publisher
   landing page behind bot protection) are recorded as `UNVERIFIED_HTTP_<code>`, never as repaired.
5. Emitted `resolution.json`; no ledger file was edited.

## Result (measured 2026-09-12 ~00:29 +08:00)

| rows in class | direct locator | weak locator | repair CONFIRMED | failed/unverified |
|---:|---:|---:|---:|---:|
| 12 | 6 | 6 | **6** | 0 |

Repaired rows: `SRC-011`, `SRC-036`, `SRC-038`, `SRC-039`, `SRC-041`, `SRC-042` — each proposed
locator returned HTTP 200 with a matching title (five INSPIRE record endpoints, one arXiv abs page).
`SRC-041` also has a DOI candidate (`https://doi.org/10.1142/9789814374552_0002`) that redirects to
the publisher but whose landing page returned HTTP 403 to this session, so the proposal uses the
row's verified INSPIRE record instead.

The 6 direct rows (`SRC-001/002/003/043/054/068`) were classified but **not re-fetched** in this
pass; no resolution claim is made for them.

## Files

| file | role |
|---|---|
| `resolve_wcc_locators.py` | deterministic classifier/assembler; pins the ledger hash |
| `fetch_evidence.json` | live-fetch observations (HTTP status, returned title, excerpt) |
| `resolution.json` | the repair map: per-row classification, proposal, verdict, falsifiers |

## Authority and scope limits

Decision support only. This is **not** a ledger edit, **not** a gate verdict, and **not** a
`validation_status`. The canonical ledger is owned by `astra-lead-literature`; a lead must merge any
proposal. Only the `exact_locator` field is under test — the quoted evidence, `verdict` and
`reviewer` columns of the ledger are not re-adjudicated, and no mathematical content is verified.

## Falsifiers

- **F1** any proposed locator that does not return the cited work (title/author/year mismatch) voids
  that row's CONFIRMED verdict.
- **F2** a row classified non-direct whose `exact_locator` is in fact row-specific and resolvable
  voids the classification for that row.
- **F3** any change to `ledger/citation_audit.csv` away from the pinned sha256 voids the whole table.
- **F4** a live re-fetch returning HTTP ≠ 200 or a different record voids the row.

## Re-run

```bash
python3 artifacts/worker-050/wcc_locator_resolution/resolve_wcc_locators.py \
  --ledger ledger/citation_audit.csv \
  --fetch-evidence artifacts/worker-050/wcc_locator_resolution/fetch_evidence.json \
  --out artifacts/worker-050/wcc_locator_resolution/resolution.json
```

Exit code 0 = emitted against the pinned ledger; exit code 3 = ledger hash moved, table stale.
