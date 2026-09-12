# worker-024 — F2b rev29 minimal repair candidate (class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM)

## Why this task

`G-FORM` coverage at pass-06 was F1 4 accepts / F2a 3 / **F2b 0**. F2b is the only
remaining coverage gap on the formulation critical path. Two independent reviewers
reached `revise` on the same frozen bytes and named the same two mechanical carriers:

| carrier | reviewer evidence |
|---|---|
| `regularity.must_not_conflate[0]` (line 152) denies any C2/C0 containment while the artifact's own `implication_ledger` asserts one | `reviews/F2b-review-worker-018-rev13.json` W018-R13-F2B-B1; `reviews/F2b-review-rev29-075.json` |
| `implication_ledger.forbidden_transfers[0].reason` (line 246) calls C2 "a strictly larger extension class" while its own chain makes `E_C2` the smallest extension set | `reviews/F2b-review-worker-018-rev13.json` W018-R13-F2B-B2; `reviews/F2b-review-rev29-075.json` HF-075-F2b-LARGER |

A third flag — `HF-075-F2b-VOCAB`, the conclusion token not being in F0's allowed
list — is **not** F2b-specific: the accepted F2a sibling carries the identical
conflict at its current pin. That one needs a gate-wide adjudication, not a schema edit.

## What is here

| file | what it is |
|---|---|
| `build_candidate.py` | rebuilds the candidate from the frozen rev29 bytes; aborts if the source hash or either carrier line has moved |
| `CANDIDATE_schemas_af_scc_c0_vacuum.yaml` | the repair candidate, sha256 `679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9`, **unfrozen / not applied** |
| `repair.patch` | unified diff; exactly lines 152 and 246 change |
| `verify_f2b_repair_024.py` | independent verifier; re-derives both carriers from the artifact's own containment string, checks the candidate corrects (not deletes) them, and enforces invariance |
| `report.json` | machine-readable results, pins, residual blocker set, full falsifier |
| `vocab_token_conflict_024.json` | D3 adjudication brief with both admissible resolutions |
| `rerun_w018_checker_on_candidate.py` | generated adaptation of worker-018's checker (TARGET/MIRROR/EXPECTED_SHA/outpath repointed; body unchanged) |
| `w018_checker_on_candidate.results.json` | that checker's raw output on the candidate |
| `emit_events_024.py` | emits the 6 task events + 1 timestamp erratum to `comms/outbox/worker-024.jsonl`, each validated with `research_map.schemas.validate_event` first |
| `outbox_events_snapshot_024.jsonl` | verbatim snapshot of the 6 task events as ingested, sha256 `941a326d5420` |
| `checkpoint_note_024.md` | checkpoint ids, hashes, and the fail-open caveat that stops a green checkpoint from being read as validation |

## Result

Live bytes at `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`
(FROZEN rev29 manifest `815e08079aefbc`) reproduce both contradictions. The
candidate clears them and changes nothing else:

- exactly lines **152** and **246** differ; 335 lines before and after
- `class_id`, `node_id`, `conclusion`, quantifier order, containment string and all
  four `one_way_entailments` unchanged
- no alias token (`strong_cosmic_censorship_C0`) injected; no `C0 or C2` composite introduced
- adapted worker-018 checker on the candidate: **C17-CHAIN-DENIAL PASS,
  C18-TRANSFER-REASON PASS**, 21 PASS / 1 FAIL where the single FAIL is
  `C10-FROZEN-PIN`, expected because the candidate is deliberately unfrozen

Residual F2b blocker set after repair: `D3-VOCAB-CONFLICT-ADJUDICATION` only.

## Emission and checkpoint

Six task events plus one timestamp erratum were emitted to
`comms/outbox/worker-024.jsonl`; all seven are in `research_map/events.jsonl`
(`_received_at` 01:08:26 for the six, 01:09:41 for the erratum) with zero entries in
`comms/rejected.jsonl`. Final checkpoint `ckpt-20260912-011027`
(2026-09-12T01:10:27+08:00, `map_validator=VALID`, exit 0).

**The checkpoint is a record, not a verdict here.** `checkpoint.py` at
`152b40ead267` is unchanged from a prior pinned worker-024 finding that it is
presence-driven and fails open on six stripped structures
(`w024-ckv-20260912T0105-claim-checkpoint-vacuity`). Validation for this task is
`report.json` and the hashes it pins. Details in `checkpoint_note_024.md`.

## What is deliberately NOT done

- No canonical artifact was written. `artifacts/formulation/FROZEN.json`,
  `artifacts/formulation/schemas/*.yaml`, `research_map/formulation_taxonomy.yaml`
  and `schemas/*.yaml` are untouched.
- No node status, `validation_status`, or gate verdict is claimed. Applying the
  candidate, bumping the revision and re-pinning is the formulation lead's action;
  re-review is required afterwards.
- D3 is not patched: a one-sided re-stamp would desynchronise F2b from the accepted
  F2a and would move frozen bytes.

## Reproduction

```bash
cd <repo root>
python3 artifacts/worker-024/f2b_rev29_repair/build_candidate.py       # exit 0, prints both hashes
python3 artifacts/worker-024/f2b_rev29_repair/verify_f2b_repair_024.py # exit 0, 19 PASS / 0 FAIL / 1 ADJUDICATION
python3 artifacts/worker-024/f2b_rev29_repair/emit_events_024.py      # idempotent; skips event_ids already in the outbox
```

## Falsifier

Any of: (a) live F2b no longer measures `b2ab6acb2bbe`; (b) the containment string no
longer parses to `E_C0 > E_H2loc > E_{C^1,1} > E_C2`; (c) a re-run shows a third line
changed by the patch; (d) C17 or C18 fails on the candidate bytes
`679ab7bc8746` under an independent instrument; (e) the lead shows line 152 or 246 is
normative text that must be retained as written.
