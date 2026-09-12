# W078-REC12-PREACCEPT-01 — independent acceptance measurement of the REC-12 evidence-binding repair

Worker `worker-078`, node `F1,F2a,F2b`, gate `G-FORM`, classes
`AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN`. Read-only on every canonical path;
all writes are under this directory plus `runtime/state/w078_checkpoint_6_rec12_preaccept.json`,
`reviews/W078-REC12-acceptance-078.json` and the worker's own outbox. No gate verdict, no node
status, no `validation_status=passed`.

## One bounded class-bound task

The controller card `astra-life05-evidence-binding-repair` (Astra pass-05, REC-12) repairs the
three rev12 class schemas and publishes FROZEN rev29. This worker built a deterministic harness
for the card's four acceptance items, then executed it against the bytes that landed at
`00:53:20–00:55:02`. The check definitions come from the card text and worker-076's machine-checked
strictness probe (`artifacts/worker-076/gform_strictness_reconcile/probe_result.json#ae1740ac0b15`);
they were authored while the repair was landing, so the rev29 measurement is **retrospective for
items 1/2/4** and the pre-repair firing pattern is shown explicitly by projecting the same kernels
through a recovered rev12/rev28 baseline (worker-086's independent pinned copies and worker-074's
rev28 sandbox copy; both re-hashed here before use).

## Result at the measured rev13 / rev29 pins

| pin | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| `research_map/formulation_taxonomy.yaml` (F0, must not move) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |

**Verdict: `CARD_ITEMS_MET_AT_REV29` — 20 PASS / 2 WARN / 0 FAIL, 15/15 controls, byte-pinned
test–retest identical (`50453de0981d…`), zero drift inside the run.**

| card item | status | machine evidence |
|---|---|---|
| 1 corpus rebind + checker re-run | PASS | 36/36 rows `bound_taxonomy_sha_0abb9ed8a961`, meta binds live F0; checker exit 0, PASS, 11/11 controls; repo report `artifacts/flash-02/taxonomy_cases_check_report.json` binds the live corpus hash `ccf7041b…` at mtime ≥ corpus |
| 2 consistency-evidence refresh | PASS (WARN residual) | all three schemas declare `9e335e9b…` == measured live evidence; isolated canonical-checker mirror reproduces the live bytes byte-for-byte (CONSISTENT, 4 classes, 0 divergences). WARN: the evidence document still records input **paths only** (no `map_taxonomy_sha256` / `lead_contract_sha256`), residual CF-20 / worker-047 CB-2 |
| 3 F1 strictness direction | PASS (WARN residual) | D5 and `visibility.definition` now state tail↔whole **EQUIVALENT**; SET relation now **strictly WEAKER**; the true "B-containment is strictly stronger" sentence survives; registry + delta SET labels now "strictly weaker" (the surviving "strictly STRONGER" is a bracketed historical mention — mention-aware leading-label check). WARN: the SET falsifier is unchanged and still lacks worker-076's finiteness/dominating-member hypothesis; adjudicated as a wording residual, not an inverted direction |
| 4 FROZEN rev29 publication | PASS | revision 29; 52/52 manifest pins match live bytes; all three moved schemas pinned; artifact events carrying the new hashes are in the accepted stream (`A4e`) and the rev29 manifest hash is in the accepted stream (`A4g`); a before/after machine report exists |
| card falsifier | PASS | F0 bytes unchanged vs the pinned baseline; no forbidden class-definition / hypothesis / conclusion-predicate / axis change vs rev12; declared class-id sets unchanged |

## Instrument discrimination (baseline projection)

The recovered rev12/rev28 bytes were pushed through the same kernels:

| check | rev12 baseline | rev13/rev29 | interpretation |
|---|---|---|---|
| `A2a-F1/F2a/F2b` | FAIL (declared `675a99d0`) | PASS | item 2 actually changed the bytes |
| `A3a` | FAIL (inverted direction) | PASS | item 3 actually changed the bytes |
| `A4a` | FAIL (rev28) | PASS | item 4 published |
| `A5b` | PASS (identity) | PASS | no forbidden semantic change introduced |
| `A5c` | PASS (identity) | PASS | class-id sets preserved |

## Controls (15/15)

Seeded defects must trip the responsible kernel, and corrected input must clear it: wrong evidence
pin (C1), un-anchored evidence (C2) and anchored evidence (C2b), F0 write (C3), class-id mutation
(C4/C4b), conclusion-predicate mutation (C5), rev29 manifest with one wrong pin (C6), rev12 F1
direction (C7) and direction-corrected F1 (C7b), stale corpus row binding (C8), seeded inverted
registry/delta labels (C9) and the live corrected labels with a historical mention (C9b),
superseded FROZEN revision (C10), moved path without an event (C11).

## Residuals / falsifiers carried forward

1. `S1` F2b `:245` `forbidden_transfers[0].reason` still says "C2 is a strictly larger extension
   class" while the file's own chain at `:238` places `E_C2` smallest. It is a hard failure reported
   independently by worker-066 / worker-060 / worker-008 and is **not among the four authorized
   repair items**; the r3 F2b round is expected to reject unless it is repaired or dispositioned.
2. `S4` input-anchoring of `taxonomy_consistency.json` (item 2 closes the pointer, not the binding).
3. `S2` the retained SET falsifier wording (direction is correct).
4. `A3c`'s failure mode is mention-sensitive by design: only the leading strength label is judged.

Re-run after any byte move: a new sha256 voids this measurement, not the check definitions.
`python3 artifacts/worker-078/rec12_preaccept/verify_rec12_preaccept.py` (add `--snapshot` to
re-pin the snapshot directory).

## Files

| file | role |
|---|---|
| `verify_rec12_preaccept.py` | deterministic harness (checks + controls + baseline projection) |
| `report.json` / `report_rerun.json` | primary measurement / byte-pinned test–retest |
| `controls.json` | 15 seeded-control results |
| `snapshot/` (+ `SHA256SUMS.txt`) | pinned copies of the measured inputs |
| `CHECKPOINT.json` | worker checkpoint (also at `runtime/state/w078_checkpoint_6_rec12_preaccept.json`) |
| `SHA256SUMS.txt` | hashes of this directory's deliverables |
| `emit_w078_events.py` | idempotent outbox emitter |

Authority note: worker verdict only. `counts_as_full_schema_verdict=false`,
`counts_toward_gate_accept=false` — this measures the repair card, not the class semantics.
