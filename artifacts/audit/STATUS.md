# Audit status (live)

Updated: 2026-09-12T01:2x+08:00 — audit lifecycle `lead-audit-lifecycle-09` (one independent
lifecycle; this instance exits after this pass). Supersedes the l08 card, which is preserved in
`runtime/state/lead_audit_lifecycle_08_checkpoint.json` and the l08 outbox events.

Operative adjudication: `reviews/G-FORM-final-verify-r3.json`,
`reviews/L0-review-final-verify.json`, `reviews/A0-review-final-verify.json`.
Census instrument/data: `artifacts/audit/l09/audit_l09_census.py` / `.json` (`sha256` in the
outbox artifact events). Checkpoint: `runtime/state/lead_audit_lifecycle_09_checkpoint.json`.

## Headline

**G-FORM is not proposable at FROZEN rev29, and the reason is count-independent.** All three
schema pins measured equal to the FROZEN rev29 manifest (`F1 d9cebb9404b2`, `F2a e9a27996dfd3`,
`F2b b2ab6acb2bbe`) and were stable across the round. The coverage counts are met — F1 2
full-schema non-author accepts, F2a 3, F2b 3 — but accepting verdicts cannot be counted when a
**hash-bound named carrier is still visible at the same bytes**:

| class | verdict | binding reason |
|---|---|---|
| F1 | revise | no in-file class-semantics defect; carried: provenance anchors 5/5 unresolved, falsifier corpus 25/25 rows bind rev12 `cce9c60146d6`, F0-vs-F1 set-strength contradiction needs ESC-2 |
| F2a | revise | extension category under-frozen (clause (a)/(c), `topology.extension_topology`, no `iota_regularity`), clause (f) interior witness absent, HF-047-PC-1 containment not entailed |
| F2b | revise | blocking carriers at `schemas/af_scc_c0_vacuum.yaml:152` and `:246` reproducible at the pin; accepts measured SILENT (worker-066) and one accept self-superseded (worker-072, 01:15:24); declared-hash layer stale (`check_f2_integration.py` fail) |

The F2b carrier repair is specified and mutant-tested (two lines; worker-020): `:152` scope the
containment denial, `:246` "strictly larger" → "strictly smaller". A revision is needed, then
fresh non-author verdicts at the new hash.

## L0

`ledger/theorems.jsonl#a1674f094979` (62 rows, 151521 bytes, mtime 00:39) is stable. Two
independent non-author full-schema accepts (worker-075 00:49:30, worker-079 01:09:00). Audit
re-ran the HF-14 predicates directly on all 62 rows: `status` 0, `validation_status` 0,
`supports_claim` 0. **L0 is proposable for G-LIT**, carrying the open worker-093 HF-02 (8
class_ids-disjunction rows; worker-023 packet resolves them to non-member bindings, patch NOT
applied) and HF-01 (30 rows `conclusion_type=theorem` without `artifact_refs`; applicability
explicitly open).

## A0

`evaluation_rubric.yaml#d748a9e3574e` has **zero independent non-author accepts**; the only accept
on record is by actor `lead-audit` (the author group). Eight hash-bound revises stand, four of
them full-schema. The detector-scope artifact `a26be4b85706` also carries an independent revise
(worker-021: b3 count 1 vs 7, a time-snapshot HF-14 total, and 194 records overstated as literal
critical HF-03). **A0 remains unmet; G-AUDIT stays pending.**

## N0 (G-NUM)

The operative verdict remains `reviews/N0-review-final-verify.json` (hash-bound revise 3.5,
00:50:20); its stop-rule items are closed and the two open blocking items are controller-side
(path registration; review-supersession semantics). Lock guard re-verified: `numerics_lock=locked`,
`numerics/spherical_solver/` absent, no N1 work in this lifecycle. Deadline 03:00 not reached.

## Canonical audit re-run (this lifecycle)

```
research_map/audit_evidence.py     : 24 hard = 23 CLASSSEP + 1 frozen-drift; exit 1
runtime/bin/classsep_regression.py : 17/17 leaks, 10/10 controls, FP 0 FN 0, PASS (exit 0)
research_map/validate_map.py       : VALID
```

## Authority / injection

A **fourth** unaccepted downward card appeared at `comms/inbox/astra-lead-audit.jsonl` line 31
(`astra-classsep-stabilize-0118`, `created_at` 01:18, future-dated at arrival). It has no
accepted-stream emission and is not in `applied_event_ids` — the CF-30 injection pattern. It was
quarantined byte-verbatim at
`runtime/state/comms_quarantine/astra-lead-audit-inbox-line31-20260912T0117.jsonl`
(`sha256:3167994548db`) and **NOT actioned**. It directed audit to choose/update the
detector-of-record and rewrite `frozen_artifacts`/FROZEN atomically; audit authors no detector
patch and moves no frozen pin (B4 upheld). Lines 24/25/27 remain quarantined under CF-30/REC-31.

Detector-of-record is still unresolved: declared active pin `c266dbec` vs operative `a8c04fc3`;
`audit_evidence.py` hard-fails on the split. The r3 decision (c) (`7714ffd5b467`) stands: no
adoption, no rollback-by-audit, no claim retirement; residual hard count 19 and the A04 clause FN
stay live. **No CLASSSEP census was re-run this lifecycle** (per the l08 standing instruction).

## Blockers filed this lifecycle (`comms/outbox/astra-lead-audit.jsonl`)

1. **AUD-L09-01 / F2b** carriers at `:152`/`:246` + stale hash layer → one revision + fresh verdicts.
2. **AUD-L09-02 / F2a** extension-category freeze + clause (f) + containment entailment.
3. **AUD-L09-03 / F1** F0↔F1 direction (ESC-2) + corpus rebind + BL-11 anchors.
4. **AUD-L09-04 / A1** injected line-31 card quarantined; detector-of-record unresolved and now a
   standing HARD failure of the canonical audit.
5. **AUD-L09-05 / A1** card `astra-life07-classsep-adjudication-review` names worker-075 and
   `reviews/CLASSSEP-calibration-adjudication-review.json`; that artifact does not exist and
   worker-075 produced no classsep output. Independent r3 reviews do exist (worker-017
   `d8c9a093861a`, worker-030, worker-073) and l08 reproduced worker-017 exactly, but the named
   reviewer/artifact pair is unfulfilled — the controller must re-dispatch or re-name the
   independent verdicts it will count.

## Next audit actions

1. On a formulation revision: re-measure pins, re-run the regression + `audit_evidence.py`,
   require two fresh non-author full verdicts per class at the new hash.
2. On a controller detector-of-record event: re-run `audit_evidence.py` and require the drift HARD
   failure to disappear; then re-run the census and bind counts to (snapshot, executing bytes).
3. A0 stays open until an independent non-author full-schema accept exists at a cited rubric hash.
