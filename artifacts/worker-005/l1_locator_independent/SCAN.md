# W005-L1-LOCATOR-STAGING-VALIDATION-01 — SCAN

**Classes** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH` (per-row `class_mapping` validated)
**Node** L1 · **Gate** G-LIT · **Actor** worker-005 · **Verdict** `staging_validated`
**Measured** 2026-09-12T01:18:40+08:00 (fixed run stamp; report contains no wall clock)

Independent, read-only validation of the L1 locator remediation staging map published by
worker-025 in `artifacts/worker-025/l1_locator_adj/report.json`. No canonical artifact was
written. The single file produced outside this directory is a *non-canonical* candidate patch;
the owner of record for `ledger/citation_audit.csv` remains astra-lead-literature.

## Pins at measurement

| artifact | sha256 | note |
|---|---|---|
| `ledger/citation_audit.csv` | `315c19145065…` | frozen canonical ledger, 97 rows × 25 cols |
| `ledger/theorems.jsonl` | `a1674f094979…` | report-declared pin, re-measured equal |
| `artifacts/literature/L0_L1_ACCEPTANCE.md` | `fde5600b45a5…` | report-declared pin, re-measured equal |
| `evaluation_rubric.yaml` | `d748a9e3574e…` | report-declared pin, re-measured equal |
| `artifacts/worker-025/l1_locator_adj/report.json` | `26f0071c558e…` | staging report under validation |

## Checks (11/11 pass, 0 hard failures)

| id | status | question |
|---|---|---|
| C1 | pass | every declared pinned input still measures to its declared sha256; canonical ledger untouched |
| C2 | pass | 97 report rows match the canonical rows in order and by `citation_id` |
| C3 | pass | `bibkey`/`class_mapping`/`used_by_theorems`/`evidence_url`/`exact_locator` equal canonical bytes |
| C4 | pass | independent 5-way census reproduces the counts and reconciles 67 / 71 |
| C5 | pass | all 97 staged locators are direct record locators (no query, no ellipsis, no prose) |
| C6 | pass | every staged locator is owned by the same source (present in its own url/doi/arXiv/evidence columns) |
| C7 | pass | 97 distinct staged locators; no cross-row binding or duplication |
| C8 | pass | change set is exactly 68 cells: 40 QUERY + 27 TRUNCATED + 1 ANNOTATED; no gratuitous rewrite |
| C9 | pass | `class_mapping` bytes identical for all 97 rows; tokens ⊆ the four frozen classes ∪ `(evidence/tag only)` |
| C10 | pass | candidate patch re-parses to 68 changed cells, 0 cells changed outside `exact_locator`; canonical sha unchanged before/after |
| C11 | pass | worker-025's anchor claims reproduce and bridge across the two defective-set denominators |

## Census and the 67 / 71 / 68 reconciliation

Independent classifier on the 97 canonical `exact_locator` values:

| class | n | meaning |
|---|---:|---|
| CLEAN_URL | 19 | record page / DOI / arXiv abs |
| API_RECORD | 10 | api.crossref/openalex record endpoints keyed by DOI |
| QUERY | 40 | live search query (`?q=`, `search_query=`, `/api/query`) |
| TRUNCATED | 27 | query literal elided with `...` |
| ANNOTATED | 1 | URL followed by prose (`SRC-090` " (§1.3, p. 19)") |

* **worker-005's HF-W005-L0-01 count of 67** = QUERY 40 + TRUNCATED 27. Reproduced exactly.
* **worker-025's count of 71** = 67 + 4 rows they labelled OTHER. Reproduced exactly, but see A-01:
  that OTHER set mixes 3 api.crossref/openalex record endpoints with the 1 annotated row.
* **Repair set = 68** = 67 + the annotated row. The 10 API-record rows are stable record
  endpoints and are correctly left unchanged (verified as direct by C5/C6).

## Candidate patch (non-canonical)

`artifacts/worker-005/l1_locator_independent/citation_audit.locator-repair.candidate.csv`
sha256 `7f81034614ef…` — a byte-faithful copy of the frozen canonical ledger with **exactly the
68 `exact_locator` cells** replaced by the staged values; every other cell, including all
`class_mapping` bytes, is identical. Examples: `SRC-005` arXiv query → `https://arxiv.org/abs/1507.00601`;
`SRC-010` INSPIRE query → `https://inspirehep.net/api/literature/9038`; `SRC-090` drops the
prose suffix. Owner applies; this instrument does not write the canonical path.

Cross-repair compatibility: worker-009's separate 2-cell remediation
(`ledger/citation_audit_locator_remediation_worker-009.*`, sha `0f606e1bc699…`/`b19cc2dc31f9…`)
proposes the same value for `SRC-016` (`…/literature/33714`) and, distinctly, fills
`SRC-094.evidence_url` (a column this candidate deliberately does not touch). No cell conflict;
the owner may apply both.

## Findings (advisory, none blocking)

* **A-W005-L1S-01 (census label ambiguity).** The 10 structurally identical API-record URLs are
  labelled inconsistently by worker-025: 7 DIRECT (`SRC-059/060/067/068/071/072/086`), 3 OTHER
  (`SRC-087/089/092`). Staging values equal originals in all 10, so the map is unaffected; only
  the census label is ambiguous.
* **A-W005-L1S-02 (class hygiene, out of scope).** 26/97 rows carry a disjunctive `class_mapping`
  (e.g. `AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN`). The locator repair must not and does not change
  `class_mapping`; this remains an A1 class-leakage item for the literature lead.
* **A-W005-L1S-03 (unresolved anchor).** `SRC-041`'s cached alternative anchor returned HTTP_403;
  its staged DOI locator is direct but was not re-resolved here.

## Instrument quality

`check_l1_locator_staging.py` — stdlib only, deterministic, read-only on canonical artifacts;
strict CSV/JSON handling; 11 checks. Self-test `selftest.json` sha256 `fde63ba37951…`:
10/10 planted mutants caught (row drop/reorder, cell edit, class swap, query/ellipsis/foreign/duplicate
staged values, pin drift, anchor-claim inflation), baseline reproducible, decision rule accepts an
all-pass and rejects an all-fail battery. Re-running the audit with identical arguments reproduces
`report.json` byte-for-byte (verified twice).

## Falsifier

Re-run `check_l1_locator_staging.py` with the same `--stamp` on byte-identical inputs: a different
check verdict or candidate sha256, a moved pinned input, a staged locator that is not a direct
record locator owned by the same source, a cell changed outside `exact_locator`, or any canonical
ledger write voids/refutes the corresponding check. A canonical `ledger/citation_audit.csv` whose
sha256 differs from `315c19145065…` makes this audit historical.

## Authority limits

Worker evidence only: no gate verdict, no node status, no `validation_status=passed`, no canonical
artifact written, no network re-resolution, no citation-support adjudication. Events await
controller ingest.
