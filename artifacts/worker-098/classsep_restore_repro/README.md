# W098-CLASSSEP-RESTORE-REPRO-01

- **Task**: W098-CLASSSEP-RESTORE-REPRO-01 (node A1, gate G-AUDIT, class AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN)
- **Question**: after CF-29 (unauthorized detector write) and the controller restore, do the worker-098
  drift-recheck figures that `research_map.json` binds for `astra-life06-classsep-detector-adjudication`
  still reproduce at the adjudicated bytes?
- **Verdict**: `REPRODUCED` -- 12/12 pre-registered expectations PASS.

## Restore verification (E1)

| source | sha256 |
|---|---|
| cf29_forensics_restored_sha256 | `a8c04fc31e4afa1b...` |
| live | `a8c04fc31e4afa1b...` |
| worker032_applied_pin | `a8c04fc31e4afa1b...` |
| worker073_restore_source | `a8c04fc31e4afa1b...` |

All four equal `a8c04fc31e4a...`; the voided `e36b0d644ca` bytes are preserved and distinct.

## Bound figures reproduce (RESTORED arm)

| bound claim | expected | measured | match |
|---|---|---|---|
| corpus PASS | PASS | PASS | PASS |
| 3/4 declared FP probes firing | 3 fire / 1 clean | 3 fire / 1 clean | PASS |
| growth 3 | 3 | 3 | PASS |
| no over-suppression | 0/6 suppressed | 0/6 suppressed | PASS |
| TP probes intact | 2/2 fire | 2/2 fire | PASS |

## Three-arm census

| battery | RESTORED a8c04fc3 | VOID e36b0d64 | PRE c266dbec |
|---|---|---|---|
| corpus (worker-07) | PASS 17/0/0/10 | PASS 17/0/0/10 | PASS 17/0/0/10 |
| declared FP firing | 3/4 | 3/4 | 4/4 |
| declared TP firing | 2/2 | 2/2 | 2/2 |
| over-suppression | 0/6 | 0/6 | 0/6 |
| growth total | 3 | 3 | 3 |
| hard on f344ed2aaea5 (adj. snapshot) | 19 | 16 | 24 |
| hard on 6d3f0f2792a2 (w098 snapshot) | 13 | 13 | 17 |
| hard on live map (liveness) | 23 | 20 | 30 |

Adjudication cross-check: APPLIED 19 / PRE 24 / VOID 16 on `f344ed2aaea5` all reproduce; pass-2 snapshot line
PRE 17 / RESTORED 13 reproduces. Live residual 23 hard binds map `66ada65f6027` (498 claims) only.

## Falsifier

Re-run `python3 artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py` at the pins in
`pre_registration.json`: falsified if any of E1-E12 fails. A later detector write is not a falsifier; it voids the rebase.

## Non-claims

- not a gate verdict, not a node completion, no status=done
- no adoption, no rollback, no canonical write, no claim retirement
- the 27-fixture corpus (corpus_a) is cited from the adjudication as stage evidence, not re-run here
- structural detection rates only; not a physics verdict and not an endorsement of cited theorems

## Files

- `artifacts/worker-098/classsep_restore_repro/pre_registration.json` -- sha256 `3f2ef0408b36a26101f127ec001d0ac7d37755f766ce633ed806651cee5f4831`
- `artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py` -- sha256 `ed2f9bb4fba5aeffb1147cb779523b383b8d4260076dab13fe99815882b34836`
- `artifacts/worker-098/classsep_restore_repro/raw/restore_repro.json` -- sha256 `e2b124352c8545a36d2ebb3b35cf3415a5e6e0621e35652a5a9508bc24b5be4f`
- `artifacts/worker-098/classsep_restore_repro/write_report.py` -- sha256 `5c25489adcbf57948de20bdf2ce85ce447339f30200ad1d41b182b19c3273386`

Rerun: `python3 artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py && python3 artifacts/worker-098/classsep_restore_repro/write_report.py`
