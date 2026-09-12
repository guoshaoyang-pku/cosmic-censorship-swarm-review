# W032-L1-FULL-INDEPENDENT-REVIEW-01 — README

**Worker:** worker-032 (bounded execution worker; not an author of the target, not a G-LIT owner)
**Node / gate / classes:** L1 / G-LIT / AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH
**Target pin:** `ledger/citation_audit.csv` sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 rows)
**Companion pin:** `ledger/theorems.jsonl` sha256 `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` (62 rows)
**Verdict:** `accept`, score 4.0, hard_failures `[]` — bounded to the decidable axes and to the pinned bytes.

## Why this task

The controller's own coverage scan (`runtime/state/controller_verification/lifecycle_20260912-011239.json`)
records L1 `two_distinct_accepts: False` at the frozen pin: L1 carried only spot-check verdicts and a
locator-scoped `revise`, and the literature lead's adjudication itself notes L1 has no assigned
adjudicator (`L11-L1-F4`). This review supplies one full independent (non-author) verdict at the pin.

## Method

One independently written stdlib-only checker (`check_l1_full_032.py`) that imports no prior
scanner. It implements a pre-registered defect list B1–B9 (`preregistration.json`), a 13-control
battery K0–K9, and one published post-hoc amendment A1
(`preregistration_amendment_A1.json`) that reclassifies a single strict-predicate false positive.
Run: `python3 artifacts/worker-032/l1_full_review/check_l1_full_032.py`.

## Results at the pin

| axis | measurement | result |
|---|---|---|
| shape / ids | 97 rows, 97 unique ids and bibkeys, no missing column | PASS |
| B1 foreign class token | 0/97 (all tokens inside the frozen four) | PASS |
| B2 record anchor | 0/97 without a DOI/arXiv/url/evidence_url anchor | PASS |
| B3 resolution/verdict | 0/97 (all `resolved`, all `verified-*`) | PASS |
| B4 dangling theorem ref | 0/97 (all refs resolve in L0 at a1674f09) | PASS |
| B5 cross-surface class conflict | 0/97 (tokens intersect referenced theorems' class_ids) | PASS |
| B6 status overstatement | 0/97 (no verified-primary on metadata-only evidence) | PASS |
| B7 duplicate annotation (amended A1) | 11 components, each exactly one primary, all `mirror_of` in-component | PASS |
| B9 assessment vs used_by | 0/97 | PASS |
| manifest pin chain | MANIFEST declares the live L1 hash | PASS |
| duplicate_cluster_rate | 11/97 = 0.1134 (G-AUDIT criterion <= 0.25) | PASS |
| controls | 13/13 including blast-radius K9 | PASS |

`measurement_digest = 4fe279aa942218c8f6414b9518ac4f725dc3b70ff4a9300e32a9c4c31c0e8e46`
(identical over two consecutive runs; `generated_at` excluded). No pin drifted during the run.

## Reported but not decided (ruling-bound, BL-7-consolidated)

- 41/97 rows carry `(evidence/tag only)` and 26/97 carry >1 class token — whether rubric-literal
  HF-02 applies to ledger rows is the standing controller+A0 question (**REFERRED**).
- `exact_locator` is 18/97 record-shaped under this reviewer's own predicate (the lead counts
  30/97; the boundary differs on metadata endpoints) and the acceptance note's universal claim
  about that column is falsified — REC-6 locator-column reading (**REFERRED**).

## Advisory

- Self-certification: `reviewer` is the ledger author for 97/97 rows (92 lead-literature, 5
  astra-lead-literature); independent evidence lives only in the separate review trail.
- Status/method naming asymmetry (under-claiming): SRC-043, SRC-070, SRC-096, SRC-097.
- Method finding M1: the pre-registered strict B7 fired once on {SRC-060, SRC-072} because the
  DOI-less primary SRC-020 and the provenance-suffixed mirror titles split the component; manual
  identity check shows the annotation is correct. Strict result (3) is preserved in `report.json`;
  amendment A1 changes only that component (control K9).
- Method finding M2: four weak predicates were tested and rejected as non-defects because they
  fire on legitimate records (DOI/arXiv string absence from URLs; arXiv-year skew; bibkey-surname).

## Authority

Worker verdict only: no gate verdict, no node completion, no `validation_status=passed`; no
canonical path was written. This accept is void on any byte change of the pinned files, and is
returned to `revise` without re-running if BL-7 rules the referred axes to be binding defects.
