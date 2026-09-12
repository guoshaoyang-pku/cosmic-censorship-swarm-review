# W062 — SCC-side locator live re-fetch (repair validation)

- **Task:** W062-SCC-LOCATOR-REFETCH-01 (worker-062, bounded class-bound task; no inbox card existed for this slot)
- **Node / gate / class:** L1 / G-LIT / `AF-SCC-C0-VAC-GEN` (SCC-side scope)
- **Pins:** `ledger/citation_audit.csv` sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`; repair table `resolution.json` sha256 `2a093033370fa2ec04de2330be6a16b4a4f5cb458007d0e7c79fc491cc8d1669`
- **Started / finished:** 2026-09-12T00:48:16+08:00 / 2026-09-12T00:51:26+08:00 (190.4 s, 69 HTTP requests, budget 90)
- **Table verdict:** **PARTIAL** (all controls pass: True)
- **Rules:** `PREREGISTRATION.json` schema `w062-prereg-2`. Its amendment block records that a 13-row v1 pilot was stopped after the pilot itself falsified the v1 comparator (arXiv `<published>` is the preprint year, not the journal year) and that all pilot bodies are quarantined under `pilot_v1_superseded/` and excluded from every count below.

## What was re-fetched

| target | outcome | count |
|---|---|---:|
| current `exact_locator` (34 rows) | `MULTI_RECORD` | 24 |
| current `exact_locator` (34 rows) | `SINGLE_RECORD_MATCH` | 10 |
| proposed replacement (26 weak rows) | `NOT_APPLICABLE` | 8 |
| proposed replacement (26 weak rows) | `VERIFIED_MATCH` | 26 |

- **Published ledger state:** 24 current locators return a multi-record query feed, 10 return exactly the cited work. The published `exact_locator` column is therefore still not a per-row record locator for the weak rows: the repair has been validated, not applied.
- **Repair validation:** 26/26 proposed replacements resolve to the cited work at the frozen hash; 0 row(s) did not reach VERIFIED_MATCH.
- **Direct rows:** 8/8 existing direct record locators re-resolve to the cited work.

## Adjudication notes (read with the table verdict)

- **Literal PASS rule vs coded check.** The frozen text says PASS needs all 26 replacements VERIFIED_MATCH and all 8 direct locators SINGLE_RECORD_MATCH. All 8 direct rows did match (SRC-004, SRC-014, SRC-056, SRC-057, SRC-058, SRC-061, SRC-072, SRC-080); the coded check additionally required the *total* current matches to equal 8, and 2 weak query endpoint(s) also returned exactly one record (SRC-037, SRC-079), so the coded table verdict is PARTIAL. The repair table is fully validated under both readings; the published-column failure below is unaffected. No amendment was made after seeing this: the frozen coded verdict is reported as-is and flagged here.
- **F1 instances (advisory).** For SRC-037, SRC-079 the *published* `exact_locator` is a dynamic query endpoint that happened to return exactly one matching record at fetch time. That does not reclassify the cell as a record locator (a query is not a stable identity), but it is the closest live counterexample to the weak classification and is recorded rather than hidden. Both rows' proposed replacements also verify.
- **Year advisory.** 1 replacement judgement(s) matched on title with an arXiv year outside +/-1 of the ledger year (SRC-005); arXiv years are preprint/version years under the v2 rule. SRC-005 is corroborated by the Crossref publication year in control C3.
- **Single-attempt repairs.** 26/26 verified replacements resolved from the routed primary source on the first attempt; no replacement needed the fallback chain.

## Controls (all must pass; run exits 4 otherwise)

- C1 positive (Crossref, Penrose 1965): PASS
- C2 negative mutants (bad DOI + nonexistent arXiv id): PASS
- C3 cross-source (arXiv vs Crossref on the 3 lowest-id SCC rows with both ids): 3/3 PASS
- C4 hash-guard teeth (byte-mutated ledger -> exit 3): PASS
- C5 scope/disjointness (34 rows, disjoint from worker-050's WCC exact set): PASS
- C6 replay determinism (verdicts recomputed from raw bytes on disk): PASS (60 raw bodies re-checked)

## Evidence layout

- `raw/` + `raw/INDEX.json`: every fetched body with sha256, HTTP status, attempts and per-source evaluation (60 fetches). Re-derivable offline: `python3 refetch_scc_locators.py --replay`.
- `PREREGISTRATION.json`: rules, thresholds, routing, controls and falsifiers frozen before the first fetch (sha256 recorded in `MANIFEST.json`: a8294d3280fe).

## Falsifiers

- F1: any current exact_locator classified MULTI_RECORD/ZERO_RECORD that in fact resolves to exactly one record matching the cited work voids the weak classification of that row.
- F2: any proposed replacement classified VERIFIED_MISMATCH or FETCH_FAILED falsifies that repair proposal; one VERIFIED_MISMATCH turns the table verdict to FAIL.
- F3: any drift of ledger/citation_audit.csv away from the pinned sha256 voids the whole table.
- F4: any control C1-C6 failing invalidates the instrument and voids the table verdict.
- F5: an offline replay that produces different verdicts from the same raw bodies falsifies determinism.
- F6: an independent comparator applied to the retained raw bodies that disagrees on a row verdict falsifies that row's verdict.

- Apply the verified replacements only after a controller freeze decision; then re-run this re-fetch and the frozen-hash spot checks against the new L1 hash.

Authority: worker evidence only — not a ledger edit, not a gate verdict, not a node completion, not a `validation_status`.
