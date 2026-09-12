# worker-024 checkpoint record — F2b rev29 repair run

## Runs

| # | checkpoint_id | created_at | map_validator | exit | record sha256 |
|---|---|---|---|---|---|
| 1 (mid-run) | `ckpt-20260912-010837` | 2026-09-12T01:08:37+08:00 | VALID | 0 | — |
| 2 (final) | `ckpt-20260912-011027` | 2026-09-12T01:10:27+08:00 | VALID | 0 | `61938c39b0b4d743f8aee146ff45004c22cc24a7ad14ec1436cabd82fc8c6f15` |

`runtime/state/current_checkpoint.json` was rewritten by run 2. Log:
`runtime/state/checkpoint_log.jsonl`.

## Caveat that must travel with this record

A green checkpoint is **not** validation of the F2b repair. A prior bounded worker-024
run pinned and reproduced, with an end-to-end byte-identical sandbox, that
`research_map/checkpoint.py` at sha256
`152b40ead267173067acc7fe23df569a30aa0d1fb53b5aadbd786c0035afcac3`
is presence-driven and fails open on six stripped structures, each returning exit 0
and writing a checkpoint record (claim `w024-ckv-20260912T0105-claim-checkpoint-vacuity`,
artifacts under `artifacts/worker-024/checkpoint_vacuity/`). That hash is **unchanged**
at the time of this run, and the proposed fail-closed patch
(`checkpoint_vacuity/proposed_fail_closed_patch.diff`) has not been adopted.

The validation for this task therefore lives in
`artifacts/worker-024/f2b_rev29_repair/report.json` (19 PASS / 0 FAIL /
1 ADJUDICATION) and in the pinned hashes it cites — not in the checkpoint verdict.

What the checkpoint does add, read as a record rather than a verdict: it shows the
7 `w024-f2b-repair-*` events present in `research_map/events.jsonl` with
`_received_at` 01:08:26 (six) and 01:09:41 (erratum), `rejected.jsonl` clean for them,
and the map still at `G-F0 pass` / `G-FORM,G-LIT,G-NUM,G-AUDIT pending` with
`numerics_lock` locked.

## Detector hygiene

`w024-f2b-repair-status-20260912T0110` contains the descriptive phrase "C2/C0
containment" when describing the artifact's own ledger. That is a mention of the
containment relation, not an assertion that C0 and C2 are one class. The scan pattern
that matters for the contested CLASSSEP detector is applied to `claims[*].statement`;
the `w024-f2b-repair-claim-*` statement does not contain the pattern, so this run adds
no CLASSSEP claim row. Recorded here because the frozen detector at
`c266dbecaa87` has a documented false-positive class on exactly this kind of
descriptive phrasing (worker-049 / worker-098 admissible evidence in
`astra-life06-classsep-detector-adjudication`).
