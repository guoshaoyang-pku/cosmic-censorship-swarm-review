# W025-L1-IDENTITY-AUDIT-01 — full-population identifier → record identity audit

- **Node / gate:** L1 / G-LIT (bounded independent measurement; no gate or node verdict claimed)
- **Actor:** worker-025 (slot 025), bounded execution worker
- **Target (frozen, unchanged by this task):** `ledger/citation_audit.csv` @
  `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 data rows)
- **Companion pin:** `ledger/theorems.jsonl` @ `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
- **Preregistration:** `PREREGISTRATION.json` (thresholds and falsifiers fixed before the first fetch)
- **Report (machine):** `report.json` @ `5bd6b3263feaf9ff497a1c96c2afb269e9c7cad088d1c377e1b016d1d4f3603b`
- **Fetch provenance:** `cache_manifest.json` @ `18a2b6fd5c185b6c95b9990f9543300d535306ab9ee1ef91c41931616ba276b4`
  (114 cached registry bodies, each re-hashable)
- **Reproduce:** `python3 artifacts/worker-025/l1_identity_audit/run_identity_audit_025.py --offline`

## Why this task

G-LIT requires resolvable locators and independent re-fetch spot checks. Before this run, independent
coverage **bound to the current frozen hash** was **12 of 97 rows** (worker-076 six rows; worker-099
seven rows, one of them `SRC-035` overlapping worker-076; earlier spot-checks `L1-spotcheck-09/049/077`
do not bind `315c19145065`). Nobody had checked, across the whole population, whether each declared
identifier resolves to the record the row claims — and the 59 rows carrying **both** a DOI and an arXiv
id had never been cross-checked against each other. This is a census of all 97 rows, not a sample.

## Result

| verdict | rows |
|---|---:|
| `IDENTITY_MATCH` (clean) | 77 |
| `IDENTITY_MATCH_WITH_AUTHOR_YEAR_FLAG` | 18 |
| `NO_IDENTIFIER` (INSPIRE record only) | 2 |
| `IDENTITY_MISMATCH` | **0** |
| `DOI_TITLE_MISMATCH` / `ARXIV_TITLE_MISMATCH` | **0** |
| `FETCH_FAILED` | **0** |

- **95/97 rows resolve at least one identifier; 59/59 dual-identifier rows resolve both channels and
  are title-compatible.** The two identifiers of a dual row are not merely both resolvable — Crossref
  and arXiv titles agree at the frozen thresholds (Jaccard ≥ 0.60 or difflib ≥ 0.80), and for 52 of
  them the registries carry an explicit cross-link (arXiv id in Crossref or DOI in arXiv).
- **No row resolves to the wrong work.** The 97-row identifier layer is clean at the level of
  identifier → bibliographic identity. This is *not* an endorsement of the evidence excerpts; worker-099
  independently found SRC-025's excerpt contradicts its source, and the L0 content verdicts are a
  separate question this task does not touch.
- **The 18 flags are all year offsets, not author mismatches.** After correcting the author metric to
  surname tokens (registries abbreviate given names: `P T Chrusciel` vs `Piotr T. Chrusciel`), **zero**
  author-overlap flags remain. All 18 flags are an arXiv-preprint-year vs declared-journal-year offset
  (e.g. SRC-002 arXiv 2019 / declared 2023; SRC-093 arXiv 2005 / declared 2009). That is the expected
  preprint→journal pattern, recorded as a flag rather than silently normalized.
- **Two registration-agency classes exist and both were needed.** 66 rows resolved at Crossref; **26
  resolved only at DataCite** — 25 of them `10.48550/arXiv.*` DOIs, which are arXiv-issued and are not
  in Crossref at all, plus one university thesis DOI (`10.25365/thesis.76304`). A Crossref-only checker
  would have reported 26 spurious "unresolvable identifier" rows.
- **2 rows carry neither identifier** (`SRC-020`, `SRC-044`; INSPIRE record only). Both were fetched
  live and resolve to the declared titles (`inspirehep.net/api/literature/1767922` → 200, 1 author;
  `.../2743272` → 200, 1 author). They are correctly classed `NO_IDENTIFIER`, not failures.
- **10 duplicate-identifier groups** (6 DOIs, 4 arXiv ids) cite the same work from two citation ids
  (e.g. `SRC-002`/`SRC-068` both `10.4007/annals.2023.198.1.3`; `SRC-057`/`SRC-086` both
  `1702.05715`). Not an identity defect — flagged for the ledger owner as a dedup question.
- **SRC-011 is a genuine reprint case, not a mismatch.** The row declares the 1969 Penrose paper; its
  DOI resolves to the 2002 *General Relativity and Gravitation* "Golden Oldie" reprint (title gets a
  `"Golden Oldie":` prefix, year 2002). Title compatibility is 0.78/0.89 and the venue field already
  says so. Recorded as a flag, `IDENTITY_MATCH`.

## What would falsify this

1. `python3 run_identity_audit_025.py --offline` does not regenerate `report.json` at
   `5bd6b3263feaf9f` (verified: three consecutive replays, identical hash).
2. Any cached DOI body and cached arXiv body for a row reported `IDENTITY_MATCH` are shown to be
   different works.
3. Any row here reported clean has a cached record whose authors contradict the row at surname level.
4. A declared identifier resolves to a different work when re-fetched at the pinned input hash.

## Scope discipline

- No write to the ledger, the map, `research_map/formulation_taxonomy.yaml`, or any frozen artifact.
- No gate verdict, no `validation_status`, no `status=done` — worker events cannot set those.
- The report is byte-identical between a cache-complete fetch run and an offline replay: no timestamp
  or fetch/offline discriminator is written into it, so the falsifier is exact rather than approximate.
- Implementation notes are recorded rather than buried: the legacy arXiv id normalization
  (`gr-qc/0307013` returns as `0307013`) and the DataCite fallback were both forced by observed
  failures (31 spurious `FETCH_FAILED` rows in the first pass), and the first-pass author metric was
  corrected from exact-name matching to surname tokens after it produced two false flags.
