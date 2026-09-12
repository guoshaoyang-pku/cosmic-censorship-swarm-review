# L1 independent re-fetch spot check #4 — worker-006

- **Assignment:** `astra-life02-l1-spotcheck` (node L1, gate G-LIT, class scope GLOBAL;
  sample rows bind `AF-SCC-C0-VAC-GEN` / `AF-SCC-C2-VAC-GEN`).
- **Reviewer:** `worker-006` (distinct from `deepseek-flash-07`, whose spot check #3 is
  the only prior check at the current L1 hash).
- **Binding:** `ledger/citation_audit.csv` sha256
  `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
  (re-hashed after all fetches: unchanged, `stable_during_fetch = true`).
- **Artifact:** `artifacts/worker-006/l1_spotcheck/spotcheck-006.json`
  (script `run_spotcheck_006.py`, sample freeze `sample_freeze.json`,
  raw responses under `raw/`).
- **Status:** `unverified`. This does not set a gate verdict and promotes no theorem.

## Frozen sample rule (declared before any fetch)

Rows of `ledger/citation_audit.csv` such that

1. `citation_id` is not in the covered set of spots #1–#3
   (`SRC-002,004,006,009,011,014,022,024,025,031,041,049,057,065,073,080,081,089`),
2. `class_mapping` contains `AF-SCC-C0-VAC-GEN` or `AF-SCC-C2-VAC-GEN`,
3. `used_by_theorems` intersects `{T-304, T-305, T-401, T-526, T-527}`,
4. `arxiv_id` is non-empty.

Deterministic result (8 rows): `SRC-040, SRC-047, SRC-048, SRC-078, SRC-082,
SRC-083, SRC-084, SRC-085`. Freeze time `2026-09-12T00:18:06+08:00`.

## Method

Fetch `https://arxiv.org/abs/<arxiv_id>` (the row's `evidence_url` form) with `curl`;
record the sha256 of the raw response bytes; parse title / authors / abstract / v1 date
from the arXiv abstract page; compare against the ledger row: normalized title equality,
first-author surname containment, and grounding of the ledger excerpt's leading tokens in
the fetched abstract (contiguity of the first ≤12 normalized tokens; token presence
fraction as fallback). Abstract/metadata level only — **not** a page-level proof check.

## Result

| rows checked | MATCH | PARTIAL | FAIL | fetch_failed |
|---:|---:|---:|---:|---:|
| 8 | 8 | 0 | 0 | 0 |

- All 8 locators resolve (HTTP 200) to the cited work; title and first author agree.
- All 8 declared excerpts are grounded token-for-token at the head of the fetched
  abstract (lead-12 contiguity true in 8/8; token presence 0.96–1.00).
- **Negative control:** applying `SRC-047`'s claim to the wrong locator
  `https://arxiv.org/abs/2201.12295` yields `title_match=false`,
  `first_author_match=false`, `NOT_GROUNDED`, observed verdict `FAIL` — the comparator
  can fail, so the 8 MATCH results are not format-dominated.

## Findings (info severity, for the audit/literature leads)

1. `year` column mixes journal and preprint years: `SRC-083` ledger 2025 vs arXiv v1
   2024-09-04; `SRC-085` ledger 2023 vs arXiv v1 2022-01-28. Same convention issue as
   spot check #3 finding `SPOT3-B-02`; a mechanical year comparison would produce false
   mismatches. No locator error found.
2. Scope limit: this is an independent *sample* of 8 of the 79 rows not covered by
   spots #1–#3, at abstract level. It is not a full-ledger review and does not audit
   quantifiers, regularity class, or conclusion direction.

## Falsifier

A re-fetch of any pinned locator that resolves to a different work, or an excerpt not
grounded in the fetched abstract, turns the corresponding MATCH into FAIL; a csv hash
that is not `315c19145065` voids the check; a page-level check contradicting a MATCH
also falsifies it.
