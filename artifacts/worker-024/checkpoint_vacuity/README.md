# W024-CHECKPOINT-VACUITY-01 — independent vacuity audit of `research_map/checkpoint.py`

**Task:** `W024-CHECKPOINT-VACUITY-01` (worker-024, node A1, gate G-AUDIT).
**Status:** worker completion claim only — no gate verdict, no node transition, no
`validation_status=passed`, no canonical file modified.

The 15-minute checkpoint (`research_map/checkpoint.py`) is the controller's standing evidence
instrument: `runtime/state/current_checkpoint.json`, `checkpoint_log.jsonl` and
`artifact_hashes.json` are what quotes like *"map VALID / 0 hard failures / classsep PASS / lock
present"* come from (ASTRA_HANDOFF "Checkpoints"). This audit asks two questions:

1. Can a checkpoint record distinguish a healthy swarm from a tree whose evidence structures
   have been removed? (vacuity)
2. Can the process boundary gate on the record it just wrote? (exit code)

Both answers are **no** at the audited revision.

## Pins (all sandbox inputs are byte-pinned; `report.json.sandbox_pins` re-verifies them)

| input | sha256 |
|---|---|
| `research_map/checkpoint.py` (audited instrument) | `152b40ead267173067acc7fe23df569a30aa0d1fb53b5aadbd786c0035afcac3` |
| `research_map/comms.py` | `7e905012ad6b8007f7fc2131a2ce0f35abae13d4205f15f8acd00ad9ff3ce724` |
| `research_map/validate_map.py` | `0bf3eb3ec4ee3513d604377b115a7b448f08813f68bc8310613ba76f995c9f1f` |
| `research_map/audit_evidence.py` | `36cf433a90b6b7a8c84596e4b36aac8796c10c82dc2c81514200f5d01135c052` |
| `research_map/schemas.py` | `75214a75353b9cd16952958c4711896a46f1f1bda1529622441f14eacf04003b` |
| `research_map/class_separation.py` (frozen revision) | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| `research_map/research_map.json` (map snapshot) | `3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005` |
| `research_map/events.jsonl` (first 200 accepted events) | `3853ef1e72f1a29b9efa3b1d33d7b170eebea4f26aa1ac2bcf0c89e10be72146` |
| `runtime/bin/classsep_regression.py` (frozen) | `9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091` |
| proposed patch (`patched/checkpoint.patched.py`) | `b1ca1e82e94336767069573b2d14112fea4a5b7384d4722978245358ca85858d` |

The live `research_map/class_separation.py` moved `c266dbceca87 → a8c04fc31e4a` at 00:56 while
the detector repair was in flight; the sandbox uses the **frozen** `c266…` revision because the
map snapshot's active `frozen_artifacts` entry pins it, so the audit's classsep numbers bind to
`c266…` only. Live canonical entry/exit hashes are recorded in `report.json`; no live canonical
file drifted during the run window.

## Method

Each case gets a fresh sandbox copy of the pinned subset (`ROOT` is derived from `__file__`, so
the tree is self-contained), mutates exactly one structure, runs `checkpoint.py` as a subprocess
from the sandbox root, and reads back the record, the on-disk registry, the log delta and the
exit code. Assertions are frozen in `drive_vacuity.py`; `report.json` carries all 73 checks.
Run logs per case are in `runs/`.

## Result — the record fails open on six stripped structures (all rc = 0)

| case | mutation | observed record | rc |
|---|---|---|---|
| C0 | none (healthy control) | VALID; corpus 27/PASS; registry 423; events 200; 5 gates; lock present | 0 |
| C1 | `research_map/events.jsonl` absent | `event_stream_errors: []`, `events_total: 0`, `events_pending_application: 0`, **VALID** | 0 |
| C2 | event stream present but corrupt (positive control) | 1 malformed line **recorded** in `event_stream_errors`, still rc 0 | 0 |
| C3 | `comms/outbox/` absent | `outbox_files_seen: 0`, `accepted: 0`, no error field | 0 |
| C4 | corpus `fixtures/` unreachable (`results.json` kept) | `classsep_regression = {0,0,0,0, verdict PASS, corpus_size 0}` embedded as PASS | 0 |
| C5 | `gates=[]`, `numerics_lock`/`frozen_artifacts`/`claims` removed | `gates: {}`, `numerics_lock: {}`, **VALID** | 0 |
| C6 | all registry roots removed | `artifact_hashes.json` **overwritten** to `{"hashes": {}, "registry": {}}` (423 → 0) | 0 |
| C7 | duplicate node id (map INVALID) | `map_validator: INVALID` **recorded**, record still written, log line still appended | 0 |
| C8 | two runs inside one second (stamp fixed) | **1** `ckpt-*.json` file for **2** log lines; second label overwrote the first | 0 |
| N1 | map file is not JSON | traceback, no record written | 1 |
| N2 | corpus `results.json` absent | traceback, no record written | 1 |

Mechanisms (line anchors in the pinned `checkpoint.py`):

- l.83 `ev_errs = validate_events(...) if comms.EVENTS.exists() else []` — an **absent** stream is
  reported as "no errors". The subtlety measured in C1/P1: `comms.ingest` (l.76) opens
  `events.jsonl` in append mode (`comms.py:321-322`), so it **re-creates the file empty** before
  the check; the patch therefore fires `EMPTY_EVENT_STREAM` rather than `MISSING_EVENT_STREAM`.
- l.85 `csr = class_separation.regression()` — inherits the module-level vacuity already measured
  in `W024-CLASSSEP-RUNNER-VACUITY-01` (`class_separation.py:230-254`: missing fixtures are
  skipped with `continue`, so an unreachable corpus returns `PASS / corpus_size 0`).
- l.103 `map_validator` is computed and recorded but never consulted; `__main__` (l.140-143) never
  exits non-zero. rc is 0 in every non-crashing case, including C7 (`INVALID`).
- l.123-133 writes `current_checkpoint.json`, the log line and **`artifact_hashes.json`
  unconditionally**, so a stripped scan clobbers the PROTOCOL rule-2 registry (C6) and a bare
  `INVALID` map still replaces the "latest" record (C7).
- l.33 second-resolution `stamp()` + l.124 `ckpt-<stamp>.json` — idempotent re-invocations within
  one wall-clock second (the controller runs several per pass) share one filename; the full record
  is lost while the log keeps both lines.
- C5's VALID verdict is inherited from `validate_map.py` presence-driven checks, measured
  independently in `W024-VALIDATE-MAP-VACUITY-01` (`validate_map` has no gates/lock invariant).

**Consequence for G-AUDIT/G-F0/G-FORM:** a "checkpoint says VALID / 0 hard failures" quote
certifies only that the structures present in the tree it read were consistent. It is not a
non-vacuity certificate, and the checkpoint process cannot be used as a guard because it exits 0
on the failures it records.

## Proposed patch (proposal only, verified on sandbox copies)

`proposed_fail_closed_patch.diff` (+ `patched/checkpoint.patched.py`, pin above) adds:

- a non-vacuity block: reasons `MISSING/EMPTY_EVENT_STREAM`, `EVENT_STREAM_ERRORS`, `MAP_INVALID`,
  `CLASSSEP_CORPUS_EMPTY`, `REGISTRY_EMPTY`, `GATES_MISSING:<ids>`, `NUMERICS_LOCK_ABSENT`, with
  `nonvacuity.verdict` recorded and `REASON <r>` lines printed;
- never clobber a non-empty `artifact_hashes.json` with an empty scan
  (`registry_source: preserved-previous (fresh scan empty)`);
- `--dry-run` performs no writes (including ingest);
- microsecond checkpoint ids so same-second runs cannot collide;
- `sys.exit(1)` when any reason fires.

Patched matrix (same driver): P0 healthy rc 0 / `nonvacuity PASS`; P1 events absent rc 1
`EMPTY_EVENT_STREAM`; P2 governance stripped rc 1 `GATES_MISSING:…` + `NUMERICS_LOCK_ABSENT`;
P3 registry roots absent rc 1 `REGISTRY_EMPTY` **and the previous non-empty registry is preserved
on disk**; P4 corpus unreachable rc 1 `CLASSSEP_CORPUS_EMPTY`; P5 INVALID map rc 1 `MAP_INVALID`;
P6 corrupt stream rc 1 `EVENT_STREAM_ERRORS`; P7 `--dry-run` rc 1 with no file/log/mutation;
patched same-second runs produce 2 distinct checkpoint files. Applying the patch to the canonical
path is an owner decision — nothing canonical was modified by this audit.

## Reproduction

```bash
cd <repo root>
python3 artifacts/worker-024/checkpoint_vacuity/drive_vacuity.py     # exit 0 iff 73/73 checks + pins stable
```

## Falsifier

Re-run `drive_vacuity.py` at the pinned hashes (a sandbox pin mismatch exits 2). This claim is
**falsified** if any of C1/C4/C5/C6/C7/C8 returns rc != 0 or deviates from the observed record
above (e.g. an absent event stream produces a non-empty `event_stream_errors` and rc != 0; an
unreachable corpus yields a non-PASS verdict or corpus_size > 0; a governance-stripped map is
INVALID; an empty registry scan leaves the previous registry intact; an INVALID map is not
written as the current checkpoint; same-second runs produce two files); or if any of C0/C2/C3/N1/
N2 deviates; or if the patched matrix no longer closes P1-P7 while leaving P0 at rc 0 and P3's
previous registry intact. Any later edit of `checkpoint.py` or of a pinned sub-instrument voids
the claim for the edited bytes; re-run and re-pin.

## Assumptions / limits

- The audited object is the checkpoint pipeline at the pinned revisions; observed live drift of
  `research_map/class_separation.py` (detector repair in flight) is recorded but not adjudicated.
- Registry content is measured live (rollups in `report.json`); the claim depends only on
  non-emptiness/clobbering, not on the exact file list.
- C8's collision is demonstrated with a fixed `stamp()` (mechanism-level, deterministic); the
  patched case uses real microsecond stamps. Both are recorded as such.
- Sandboxes live under `/tmp` and are removed unless `--keep`; `runs/` keeps each case's
  stdout/stderr. No canonical path was written by this audit, and no gate verdict is asserted.
