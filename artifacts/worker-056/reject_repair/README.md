# W056-REJECT-REPAIR-01 — reject-stream loss: repair bundle + pre-flight gate

Bounded execution worker **worker-056**, node **A1** (audit / evidence integrity), gate
**G-AUDIT**, class bound **AF-WCC-VAC-GEN** (modal class among net-lost events; all four frozen
classes are affected — see `report.json.census.net_lost_by_class`).

Read-only with respect to every canonical path. Nothing here was ingested, applied, or promoted.

## The finding

`research_map/comms.py::ingest` adds a rejected `event_id` to the `seen` set at line 313
("one reject per unique message; avoids re-rejecting every cycle"). Because `seen` is consulted
before validation (line 303), **rejection is terminal**: the same event can never be accepted
even after the validator is fixed. The emitted content is silently lost — the worker that sent it
is never notified. The only stored copy of the payload is truncated to 600 chars (line 316).

At snapshot `raw/rejected.snapshot.jsonl` sha256 `40ca972cf942…` (185 reject rows, 80 distinct
rejected events):

| classification | distinct events | meaning |
|---|---:|---|
| `NET_LOST_STILL_INVALID` | 54 | terminally suppressed **and** still fails the current validator |
| `NET_LOST_NOW_VALID` | 8 | terminally suppressed but the current validator would accept it |
| `EVENTUALLY_ACCEPTED` | 6 | the author re-emitted it later under a new id |
| `UNRECOVERABLE` | 12 | source file no longer contains the id; stored `raw` truncated |

Of the 54 still-invalid, **48 are `claim` events rejected for exactly one reason**: an
out-of-vocabulary `conclusion_type`. `schemas.py:46` allows seven values; workers invented 23
others (`empirical` ×7, `observation` ×5, `measurement` ×5, `artifact_measurement` ×4, …). The
claims themselves are intact — only the label is wrong. This is live, not historical: rejects
arrived throughout this run (`w031-e36-20260912T011230-claim`, `w049-live4-20260912T0111-claim`).

Affected nodes include A1 (14), F1 (10), F2b (8), F1/F2a/F2b (7), N0 (7), F2a (5) — i.e. the
loss lands on the same nodes whose accepted coverage the pending gates are waiting for.

## What this instrument adds

`artifacts/worker-097/reject_audit/` (00:45–00:48) already **measured** the reject stream and
pre-registered "read-only; no ingest, no canonical writes". This task does not repeat that
measurement as its contribution; it re-measures at its own pins for the repair window and adds
the half that was explicitly out of scope:

| file | role |
|---|---|
| `run_reject_repair_056.py` | the instrument: pins inputs, classifies, repairs, controls |
| `preflight_event.py` | **reusable gate** — runs the ingester's own functions on a file before you emit |
| `repair_map.json` | explicit invalid → allowed `conclusion_type` table with per-token rationale |
| `recovery_bundle.jsonl` | 48 repaired events, each round-trip validated against the real validator |
| `reemission_manifest.json` | 8 verbatim-valid but terminally suppressed events |
| `PATCH_PROPOSAL.md` | proposed (NOT applied) ingest fix for terminal rejection |
| `raw/rejected.snapshot.jsonl` | byte copy of the pinned reject log |
| `report.json` | census, controls, pins, drift |

## Invariants

* **I1 — no conclusion inflation.** Every repair targets `numerical_evidence` or `open_problem`
  only; targets are never `theorem` / `conditional_theorem` / `stability_result` /
  `counterexample` / `formal_model`. Control C4 enforces this.
* **I2 — no canonical writes.** All output is under this directory.
* **I3 — pin discipline.** Inputs hashed before and after; a move is reported as `drift`, not hidden.
  Recovery reads byte-copies of the outbox sources and of `events.jsonl` (`raw/sources/`,
  `raw/events.snapshot.jsonl`), because those files are live: reading them directly made the
  census move between two runs at an unchanged reject snapshot. `--check` reproduces from the
  pins alone.
* **I4 — round-trip.** No candidate ships unless the *real* `normalize_event` + `validate_event`
  accepts it. Control C5 enforces this.

## Controls (all pass; `report.json.controls`)

| id | control | result |
|---|---|---|
| C1 | every 60th accepted event from `events.jsonl` replayed → 0 false positives | PASS |
| C2 | pre-flight flags 100% of recovered still-invalid originals | PASS |
| C3 | classification re-derived from the pinned bytes, 80/80 identical | PASS |
| C4 | no repair targets a strong conclusion type (I1) | PASS |
| C5 | all 48 candidates pass the real validator (I4) | PASS |
| C6 | source-mutation probe: 1 recovered original no longer prefix-matches stored `raw` | reported (1) |
| C7 | live outbox divergence from pins (0/45 sources moved during the run) | reported (0) |
| — | `preflight_event.py --self-test` (4/4 incl. theorem-without-artifact_refs guard) | PASS |

## Falsifier

This work is **FALSE** if any of:

1. a repaired candidate in `recovery_bundle.jsonl` is rejected by `research_map/schemas.py::validate_event`
   at the pinned hash, or is accepted but changes a claim's asserted strength (a target in the
   strong set of I1);
2. any event sampled from `research_map/events.jsonl` is flagged by `preflight_event.py`
   (a false positive would make the gate unusable);
3. re-running `run_reject_repair_056.py` at the pinned snapshot produces a different
   classification, or `--check` returns FAIL;
4. a pinned input hash moves without a `drift` entry in `report.json`;
5. the claimed terminal loss is shown not to be terminal — i.e. some `event_id` classified
   `NET_LOST_*` is later accepted under that same id without re-emission (the `seen` guard at
   `comms.py:303` is the mechanism claimed);
6. any file under a canonical path is shown to have been written by this task.

Counterexample to any one voids the corresponding claim. The census is a measurement at one
snapshot; the reject log is append-only and still growing, so counts are pinned, not timeless.

## Reproduce

```bash
cd artifacts/worker-056/reject_repair
python3 preflight_event.py --self-test          # 4/4 controls
python3 run_reject_repair_056.py                # re-pin, re-derive, rewrite artifacts
python3 run_reject_repair_056.py --check        # verify existing report against a fresh snapshot
```

## Authority

Measurement, artifact, and proposal only. This worker does **not** set node status `done`,
`validation_status: passed`, or any gate verdict, and does not ingest, apply, or edit
`comms/rejected.jsonl`, `research_map/events.jsonl`, `research_map/research_map.json`,
`research_map/comms.py`, or `research_map/schemas.py`. Re-emission of recovered events is left to
the original actor or the controller because re-emitting another actor's claim under this worker's
id would misattribute authorship.
