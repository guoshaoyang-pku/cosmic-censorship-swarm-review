# W003-REC36-FOLD-READINESS-01 — REC-36 fold readiness census

Bounded execution worker `worker-003`, node `F1,F2a,F2b`, classes
`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`, gate `G-FORM`.

## What was asked

`REC-36` (astra-lifecycle-08, `runtime/state/controller_verification/astra-lifecycle-08-decisions.json`)
authorizes **exactly one** formulation revision (rev14 / FROZEN rev30) folding seven named
items, deadline 02:15. The owner is `astra-lead-formulation`. No worker had yet answered the
mechanical prerequisite question: *does every one of the seven items actually have a staged,
hash-pinned, independently verified candidate on disk at the live FROZEN rev29 pins, and does
the fold's canonical-path union stay inside the REC-36 write scope?*

## What was measured (read-only)

1. Nine live pins, measured at start and end; all equal (`pin_guard_start_end_equal: true`).
2. For each of the seven REC-36 items: every staged candidate named in the census table is
   hashed from disk and compared with the hash declared by its producer/adjudicator.
3. Independence: an event in `research_map/events.jsonl` counts as verification of a candidate
   only if its actor is neither the candidate's producer nor `worker-003`.
4. Forbidden-write check: no path may be `research_map/formulation_taxonomy.yaml`
   (G-F0-frozen), `research_map/class_separation.py` (frozen detector), or under `ledger/`.
5. Six mechanical controls (K1–K6), all discriminating; two runs are byte-identical.

## Result

`verdict: FOLD_NOT_READY_4_BLOCKING_ITEMS` — see `report.json`.

| item | status | blocking reason (mechanical) |
|---|---|---|
| REC36-1 F2b D1 containment denial | `STAGED_VERIFIED_NOT_LANDED` | 10/10 candidates hash-match; 7 have non-producer verification events; 3 negative controls (2 INVERTED, 1 DENIAL) present and flagged do-not-freeze |
| REC36-2 F2b D2 size inversion | `STAGED_VERIFIED_NOT_LANDED` | same candidate set as REC36-1 |
| REC36-3 F2a EXTCAT pin | `STAGED_VERIFIED_NOT_LANDED` | patched candidate `37e650ad6481` independently verified by worker-039 `W039-F2A-EXTFREEZE-VERIFY-01` |
| REC36-4 scc_*/strong_* crosswalk | `EVIDENCE_PARTIAL_NOT_PINNED` | closest staged evidence is `artifacts/worker-041/f2b_vocab_alias/report.json` (a worker report, `failures: [C5b_literal_allowed_uses_canonical_keys]`), **not** the pinned crosswalk artifact REC-37 requires |
| REC36-5 SET strength label | `STAGED_AWAITING_INDEPENDENT_VERIFICATION` | 3/3 worker-024 candidate bytes hash-match, but no non-producer verification event exists for any of them |
| REC36-6 f1_falsifier_tests rebind | `BLOCKED_NO_FREEZE_READY_CANDIDATE` | 4/4 candidate hashes re-measured on disk; `artifacts/worker-034/f1_repair_candidate_adjudication/report.json` records `freeze_ready: []` (record-fidelity/provenance gaps on all four) |
| REC36-7 acceptance-corpus rebind (CF-32) | `MISSING_REBIND_CANDIDATE` | `artifacts/formulation/evidence/semantic_escape_rebased.json` still binds base `1bb78ce9b357` (rev11 C0), not live `b2ab6acb2bbe`; no live-base candidate located |

Canonical-path union of the fold: 11 entries, 0 forbidden writes. Note the union is
**incomplete by construction** because REC36-4 has no pinned artifact and REC36-7 has no
candidate, so the fold manifest cannot yet close over all seven items.

## Not claimed

Not a gate verdict, not a node status, no `validation_status=passed`, no canonical write, no
content adjudication of any candidate and no endorsement of any candidate. Readiness is a
mechanical predicate over existence + declared hash + non-producer verification events.

## Falsifier

Re-run at the same pins. Falsified if (a) any pinned input moves (voids the run, exit 2); (b) an
item classed missing/blocked is shown to have a hash-pinned, independently verified candidate the
census failed to measure; (c) a candidate declared in the table measures a different sha256;
(d) a path classed non-forbidden is inside the REC-36 forbidden write set; (e) any control stops
discriminating.

## Reproduce

```bash
python3 artifacts/worker-003/rec36_fold_readiness/check_rec36_fold_readiness.py
```

Exit 0 = census complete; exit 2 = pin drift / abort (no readiness claim).

## Files

| file | sha256 (see SHA256SUMS) | role |
|---|---|---|
| `check_rec36_fold_readiness.py` | pinned | deterministic read-only census instrument |
| `report.json` | pinned | full machine census (items, candidates, events, controls, verdict) |
| `controls.json` | pinned | K1–K6 control results |
| `probe_stdout.txt` | pinned | verbatim run output + self-check summary |
| `emit_events.py` | pinned | deterministic outbox emitter (hashes deliverables at emission) |
| `SHA256SUMS` | — | manifest |
