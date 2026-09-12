# W072-E — independent CF-19 / L0 reconciliation re-derivation (worker-072)

Bounded execution-worker task. One class-bound task, one artifact set, one checkpoint, exit.
No node completion, no gate verdict, no theorem.

- **Task id:** W072-E
- **Node / gate:** L0 (+L1 cross-check) / G-LIT
- **Class binding:** `AF-WCC-VAC-GEN` primary; `class_ids = [AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH]` — the ledger is the shared literature inventory for the four frozen classes.
- **Question:** Is the live canonical L0 ledger a claim-preserving, HF-14-compliant, deterministic re-emission of its declared sources, and is the literature lead's reconciliation evidence reproducible by an independent implementation?

## Why this task

Controller finding **CF-19** records that `ledger/theorems.jsonl` was rewritten at 00:35:19 to
`a1674f094979` after the owner's announced exit revision `3e3d35531421`, without an artifact event.
The literature lead then filed `artifacts/literature/reviews/L0-freeze-reconciliation-evidence.json`
(C1–C8, `all_pass: true`, including a byte-identity rebuild claim and a content-preservation claim).
G-LIT has no accept at the reconciled hash and the reconciliation had not been independently
reproduced. This task re-derives the load-bearing claims with a second implementation that does not
call the owner's `tools/build_literature.py` or `tools/l0_freeze_reconcile_check.py`.

## Pins (verified before and after the run; drift aborts rc=2)

| path | sha256 |
|---|---|
| `ledger/theorems.jsonl` (live) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (L1) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |
| `artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl` | `3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5, class set) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/literature/reviews/L0-freeze-reconciliation-evidence.json` (reviewed) | `b7b984ae05952ab7624bb38e4c1dba54df941927bda2436d08321c0310d7de5c` |

## Method (independent second implementation, stdlib only)

- **R1 rebuild:** re-emit the canonical ledger from `artifacts/literature/theorems/batch-*.jsonl`
  with sources from `artifacts/literature/sources/batch-*.jsonl`, re-implementing the declared
  `evidence_level` / `verification_status` derivations and the HF-14 content/review split.
- **R2 diff:** full-field diff of the live rows against both archives, splitting claim-bearing
  fields (18) from status-axis fields and reporting every changed field with counts.
- **R3 invariants:** re-check the builder's fail-closed rules on the live bytes (frozen-four class
  tokens only; allowed `conclusion_type`/`content_status`; forbidden keys `status`,
  `validation_status`, `supports_claim` absent; statement/assumptions/falsifiers present; sources
  resolve; `content_status=verified` ⇒ all cited sources verified, ≥1 non-metadata, and
  `author_asserts_supports=true`).
- **R4 review axis:** `review_status` and `acceptance_authority` honesty on every row.
- **R5 class census:** per-class row counts, rows with no class, and the multi-class rows (the A0
  HF-02 "disjunction of class_ids" shape) — measured, not adjudicated.
- **R6 provenance:** control-plane scan restricted to real binding records: `event_type=artifact`
  with `path=ledger/theorems.jsonl` and matching hash, or a hash-registry entry keyed by that path.
  Hash mentions inside other events' `evidence_refs` are counted separately and not treated as
  provenance.
- **R7 L1 cross-consistency:** recompute `used_by_theorems` and `class_mapping` for every used
  source from the L0 rows and compare with the live `citation_audit.csv`.
- **R8 owner-evidence agreement matrix:** compare the owner's C1/C3/C4 numbers with the
  independently measured values (no trust transfer).

Controls: **P1** rebuild determinism (two emissions identical); **P2** byte-drift detection;
**M1** claim-field mutation caught by the diff; **M2** foreign class token caught; **M3**
`verified` from metadata-only sources caught; **M4** re-inserted HF-14 forbidden key caught;
**M5** review-axis overstatement caught; **M6** missing falsifier caught.

## Result (report.json, deterministic `result_digest`)

`result_digest = c2bf5ce732cf6dbe8bdab3ef24dafa0c799a80f1163e690fb628005837caf2d7`
(sha256 over the pin-stable checks only — pins, rebuild, both diffs, invariants, review axis,
class census, L1 cross-consistency, controls — because the live control-plane event stream moves
continuously; two consecutive runs produced the same digest. All 8 controls pass; all five pins
stable across the run.)

- **R1:** independent rebuild is **byte-identical** to the live ledger
  (`a1674f…`, 151521 bytes, 62 rows).
- **R2:** vs pre-rev3 and vs rev3-handpatch: row set and order preserved (62/62), **zero changes in
  all 18 claim-bearing fields**; the entire change set is the HF-14 status/review axis
  (`status → content_status`, `author_asserts_supports`, `supports_claim* → review_status` /
  `acceptance_authority`, `status_note` dropped, `evidence_level`/`verification_status` derived).
- **R3/R4:** invariant check and review-axis check both **clean**: 0 forbidden keys, 0
  non-frozen class tokens, 0 verified rows without a verified non-metadata source, 62/62 rows
  `review_status = not_independently_reviewed` with author-level `acceptance_authority`.
- **R5:** class rows: WCC-VAC-GEN 11, SCC-C0 11, SCC-C2 10, SCALAR-SPH 10; 20 rows carry no class
  (evidence/tag only); **8 rows carry two class_ids** (`D-004 D-005 T-303 T-305 T-402 T-515 T-526
  T-528`) — the A0 HF-02 shape, recorded not adjudicated.
- **R6:** **2 artifact events** now bind `ledger/theorems.jsonl` to `a1674f094979`
  (astra-lead-literature, 00:44:00 and 00:45:47) and the hash-registry entry matches
  (`hashes/ledger/theorems.jsonl`, active). The ledger mtime (00:39:11) precedes those events.
- **R7:** L1 recomputation matches the live CSV for all 92 used sources, 0 mismatches.
- **R8:** owner reconciliation evidence agrees on every compared claim (C1 hash/bytes/rows, C3
  rebuild hash, C4 zero diffs); owner `all_pass: true` reproduced.

## Findings

| id | severity | one line |
|---|---|---|
| W072E-F1 | positive | live bytes are an independent byte-identical rebuild from the declared sources |
| W072E-F2 | positive | 62/62 rows, 18/18 claim fields unchanged vs both archives; change set is exactly the HF-14 axis |
| W072E-F3 | positive | HF-14 closure and review-axis honesty verified independently |
| W072E-F4 | info-provenance | provenance is now closed by two owner artifact events + registry entry; ordering (mtime then events) recorded |
| W072E-F5 | info-rubric-shape | 8 two-class rows (A0 HF-02 shape); no merged class token or merged conclusion |
| W072E-F6 | info-l1 | L1 `used_by_theorems`/`class_mapping` recomputation matches the live CSV |

**Worker verdict recommendation (advisory, does not set any status):** `accept` on
`ledger/theorems.jsonl#a1674f094979`, score 4.5, zero hard failures, non-blocking items W072E-F4
(now closed by owner events) and W072E-F5 (A0 owns the HF-02 reading). This is one independent
verdict at the reconciled hash; the same-hash test passed (the ledger hash did not move during the
run).

## Scope limits

- Mechanical, hash-bound measurement only; no citation-content, locator or mathematical verdict.
- The owner's builder/checker were not invoked; agreement with their C1–C8 numbers is evidence of
  reproducibility, not an endorsement of their scope.
- HF-01/HF-02 rubric adjudication and any gate/node transition remain with A0/G-LIT owners; this
  worker cannot set `status=done`, `validation_status=passed`, or a gate verdict.

## Falsifier

Re-run at the pinned hashes: any pinned-input drift, a rebuild that is not byte-identical to
`a1674f094979`, one claim-bearing field differing from either archive, an invariant violation, a row
claiming independent review, a failing control, or (for W072E-F4) a complete control-plane scan
finding no ledger artifact event and no matching registry entry.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-072/l0_cf19_rederive/rederive_l0.py   # rc=0 on all-pass; report.json rewritten
```

## Hashes

- runner: `artifacts/worker-072/l0_cf19_rederive/rederive_l0.py`
  `5c1a7b9ce984843d6315df69aa6bdd74bb79b6ef6dda62db414ba3d5cf9fcd51`
- report: `artifacts/worker-072/l0_cf19_rederive/report.json`
  `e45aca0ff81f4013068be3dea838a929023440cb26fccb4217a5650889080605`
- checkpoint: `runtime/state/w072_cf19_checkpoint_1.json`
- R8 note: the owner's reviewed reconciliation evidence is pinned at
  `b7b984ae05952ab7624bb38e4c1dba54df941927bda2436d08321c0310d7de5c` in `report.json`; it is
  reported but excluded from `result_digest` so an owner rewrite cannot silently move the digest.
- `SHA256SUMS` records the hashes of the three files in this directory.
