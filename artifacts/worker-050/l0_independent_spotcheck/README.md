# W050-L0-INDEPENDENT-SPOTCHECK-04 — independent L0 re-fetch spot check

Actor: `worker-050` (bounded execution worker; no inbox card exists for this slot, so this is a
self-scoped, class-bound task taken from the overnight plan item "literature scope verification").

Node `L0`, gate `G-LIT`, classes `AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH`.

## What was measured

Frozen pins (measured start and end of every run; any drift exits non-zero):

| artifact | sha256 |
|---|---|
| `ledger/theorems.jsonl` (L0) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (L1) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |

Static census over all 62 L0 rows (`verify_l0.py` → `static_report.json`):

- C1 pins stable across the run — pass.
- C2 all 62 rows' `source_ids` resolve to exactly one L1 `citation_id` — pass (0 unresolved).
- C3 every cited L1 row's `used_by_theorems` back-reference names the citing L0 `theorem_id` — pass.
- C4 `verification_status` vocabulary honoured and no row overstates reading depth relative to the
  deepest `evidence_type` among its cited L1 rows — pass (61 `abstract-read`, 1 `unverified`, 0 out
  of vocabulary, 0 overstated).
- C5 `unresolved` non-empty for every row and every metadata-only row flags a statement-retrieval
  gap — pass.
- C6 class coverage: 11 / 10 / 11 / 10 rows for WCC-vacuum, SCC-C2, SCC-C0, scalar-spherical — pass.
- C7 deterministic class-stratified sample: 2 rows per class, one per-record locator each — pass.

Live two-pass re-fetch of the deterministic sample (`fetch_l0_sample.py --pass 1|2` →
`fetch_evidence.json`, `fetch_evidence_recheck.json`; `compare_rechecks.py` → `recheck_summary.json`):

- 8 / 8 sampled rows resolved with a live HTTP 200 record whose title matches the pinned L1 title,
  in both passes (9 locator attempts; one row needed its fallback locator).
- 8 / 8 rows stable between passes; L0/L1 pins held at compare time.

## Findings carried to the review event

- **W050-L0-B1 (B, hygiene):** `SRC-041`'s L1 `evidence_url` is a publisher DOI
  (`10.1142/9789814374552_0002`) that returns HTTP 403 to a non-browser client in both passes; the
  machine-resolvable per-record locator is the `url` field
  (`https://inspirehep.net/api/literature/786592`), which returned HTTP 200 with a matching title.
  The row should state which field is the locator of record, or demote the DOI to a human field.
  This reproduces the same publisher-403 observation recorded in
  `artifacts/worker-050/wcc_locator_resolution/fetch_evidence.json`.
- **W050-L0-N1 (N, honesty context):** all 97 L1 rows carry `verdict: verified` and
  `reviewer: lead-literature`/`astra-lead-literature` (the author). The L0 `acceptance_authority`
  field states this self-assessment explicitly, so no row overstates independence, but the G-LIT
  "verification_status honest" reading should treat the L1 verdict column as author self-report.
- **W050-L0-N2 (N, locator hygiene context):** 67/97 L1 `exact_locator` values are search-query
  strings; the sample deliberately used per-record `evidence_url`/`url` instead. This is the known
  BL-4 issue already covered by `W050-WCC-LOCATOR-REPAIR-01` and `W050-SCC-LOCATOR-READINESS-02`.

## Limits / falsifiers

- Sample, not full census: 8 of 62 L0 rows (2 per class). No mathematics is re-derived and no L0 or
  L1 file is edited.
- Binds only to the two pinned hashes. `F1`: any re-fetch that returns a different status or a
  non-matching title voids the affected row. `F2`: any L0/L1 hash movement voids the whole table.
  `F3`: an ordered 1:1 reproduction failing voids the measurement.
- The L0 rewrite at 00:35:19 (CF-19) is out of scope: this measurement only shows the bytes present
  at read time are internally consistent and their cited records resolve; it says nothing about who
  wrote them or why the artifact event is missing.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-050/l0_independent_spotcheck/verify_l0.py
python3 artifacts/worker-050/l0_independent_spotcheck/fetch_l0_sample.py --pass 1
python3 artifacts/worker-050/l0_independent_spotcheck/fetch_l0_sample.py --pass 2
python3 artifacts/worker-050/l0_independent_spotcheck/compare_rechecks.py
```

`verify_l0.py` exits 3 on pin drift; the fetch passes exit 1 if any sampled row is unresolved;
`compare_rechecks.py` exits 1 on any unstable row or pin movement.

Authority: worker measurement and review input only. No gate verdict, no `validation_status=passed`,
no node completion, no ledger edit.
