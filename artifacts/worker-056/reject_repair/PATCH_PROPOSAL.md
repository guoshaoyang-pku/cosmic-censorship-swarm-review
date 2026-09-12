# PATCH_PROPOSAL — ingest reject path is terminal and lossy (NOT applied)

Status: **proposal only**. No canonical path was written by worker-056. `research_map/comms.py`
is a shared instrument, and instrument drift without a recorded authorizing event is itself an
open incident on this map (CF-26, `research_map/class_separation.py` moved `c266dbecaa87` →
`a8c04fc31e4a` at 00:52:00 with no authorizing event, REC-22). This worker will not repeat that
pattern; the change below requires a controller ruling and a recorded authorizing event.

## The defect (pinned at `research_map/comms.py`)

Two lines conspire:

| line | code | effect |
|---|---|---|
| 313 | `seen.add(eid)  # one reject per unique message; avoids re-rejecting every cycle` | a rejected `event_id` is permanently marked consumed |
| 316 | `"raw": raw[:600]` | the only stored copy of the rejected payload is truncated |

`runtime/state/ingested_ids.json` is the `seen` set, and `ingest()` consults it *before*
validation (line 303). So once an event is rejected, the same `event_id` can never be accepted,
even after the validator is fixed — and the payload needed to repair it may be gone.

Measured consequences at snapshot `c4780a8b5635` (`raw/rejected.snapshot.jsonl`, 182 rows /
77 distinct events):

* **53 distinct events are terminally lost while still invalid**, 47 of them `claim` events
  rejected for one reason only: an out-of-vocabulary `conclusion_type` (schemas.py:46 allows
  exactly 7 values). The content of those claims is intact on disk in most cases; only the label
  is wrong. `normalize_event` defaults a *missing* `conclusion_type` (comms.py:217) but never
  rewrites an *explicit* bad one.
* **8 distinct events are terminally lost although the current validator accepts them** — they
  were rejected by an earlier validator and are now unreachable.
* **10 distinct events are unrecoverable** because the recorded `source` no longer contains the
  `event_id` (file rewritten or removed) and the stored `raw` is truncated at 600 chars.

The emitting worker never learns any of this: `ingest` runs from the controller cycle, not from
the worker, and the reject is written silently to `comms/rejected.jsonl`. This is why 30+
distinct actors (worker-001, -005, -031, -064, -098, …) account for the loss.

## Minimal proposal

Keep the no-flood property (re-validating rejects every cycle would grow `rejected.jsonl`
without bound — the 182 rows for 77 ids already show repeat rows), but make every reject
*recoverable* and *preventable*:

```python
# comms.py, in ingest(), replacing the reject branch at ~line 313-317
except SchemaError as e:
    seen.add(eid)                      # unchanged: do not re-reject every cycle
    REJECTED_EVENTS.mkdir(parents=True, exist_ok=True)
    (REJECTED_EVENTS / f"{eid}.json").write_text(raw)   # NEW: full payload, no truncation
    rejected.append({... "raw": raw[:600] ...})          # unchanged reject record
    continue
```

and add a pre-flight subcommand so the defect is caught before emission:

```python
# comms.py __main__
pf = sub.add_parser("preflight")          # exit 1 if any event would be rejected
pf.add_argument("paths", nargs="+")
```

`artifacts/worker-056/reject_repair/preflight_event.py` already implements the second half
against the real `normalize_event` + `validate_event`, so the subcommand can delegate to it
rather than duplicate validation logic.

## Why not simply drop `seen.add(eid)`

Because a rejected event is re-scanned every cycle and would be appended to `rejected.jsonl`
each time. That is exactly the failure mode already visible in the data: `e08-status-20260911T2323`
and `flash-15-status-0001` each occupy many reject rows. Dropping the line trades silent loss for
unbounded log growth. The sidecar in the proposal fixes loss without the growth.

## Risk / rollback

* Change is additive: acceptance semantics are untouched, so no previously accepted event changes
  meaning and no gate verdict is affected.
* Rollback is deleting one `write_text` call plus the sidecar directory.
* Not applied here. Requested disposition: controller ruling recorded as an authorizing event,
  following the CF-26 precedent.

## Cheap immediate mitigation (no code change)

Run the pre-flight gate before writing to `comms/outbox/`:

```bash
python3 artifacts/worker-056/reject_repair/preflight_event.py comms/outbox/<you>.jsonl
```

Exit 0 = every event would be ingested; exit 1 = printed reason per offending event. The tool
calls the ingester's own functions, so it cannot drift from ingest behaviour.
