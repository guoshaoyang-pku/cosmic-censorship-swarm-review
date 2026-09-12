# W097-REJECT-STREAM-AUDIT-01 — rejected-stream evidence-loss audit (worker-097)

**Question.** `comms/rejected.jsonl` is the ingester's reject record (143 rows at the measured
instant). Do its rows represent class-bound evidence that never entered the accepted stream — i.e.
silent loss the gates should know about — or transient bookkeeping?

**Answer (measured, pinned).** **No evidence loss found.** Every one of the 143 rejected `event_id`s
is present in the accepted stream (`research_map/events.jsonl`, 108) or in the ingester's seen-set
(`runtime/state/ingested_ids.json`, 24) or both; 11 rows' source events could no longer be relocated
in their recorded source file but their ids are seen-set members. 0 rows replay as "would be accepted
today but are not in the stream"; 0 rows are unrecoverable-and-unaccepted. `lost_class_bound_rows = 0`
for all four frozen classes.

## Method (read-only)

- Pins: `research_map/comms.py#7e905012ad6b`, `research_map/schemas.py#75214a75353b`,
  `comms/rejected.jsonl` (hash in `report.json.pins`), `research_map/events.jsonl`, map,
  `runtime/state/ingested_ids.json`. Fail-closed on drift (exit 3).
- For each reject row: relocate the original event in its recorded `source` by `event_id` using the
  pinned `_json_objects` extractor, then replay `normalize_event` + `validate_event`.
- Classify: `ACCEPTED_LATER` (id in accepted stream) / `ACCEPTED_ID_ONLY` (id in seen-set only) /
  `SOURCE_NOT_FOUND_ACCEPTED` / `REPLAY_VALID` (not accepted, pipeline accepts now) /
  `REPLAY_INVALID` (not accepted, still fails) / `SOURCE_NOT_FOUND_NOT_ACCEPTED`.
- Content comparison where the stored 600-char `raw` is still fully parseable: 77 rows differ from
  the accepted copy **in the `status` field only** (normalizer maps a raw status onto the enum);
  31 rows are raw-truncated (uncomparable); 6 rows accepted but source gone; 29 uncomparable
  (race: the accepted stream grew during the run).

## Mechanism worth recording (latent hazard, not a present loss)

The pinned ingester does `seen.add(eid)` **on reject as well as on accept** (`comms.py` ingest loop).
A rejected unique `event_id` is therefore never retried by a later ingest run even if the pipeline is
repaired. Today every rejected id also exists in the seen-set/accepted stream, so no evidence is
currently stranded; the hazard is that a *future* reject whose only emission is rejected is permanent,
and `rejected.jsonl` must not be treated as a retry queue (no backfill happens automatically).

## Controls (all pass; see `controls.json`)

- C1: 40 accepted events sampled from `events.jsonl` replay through the pinned pipeline → 40/40 pass.
- C2a: synthetic artifact without `node_id` → rejected (expected).
- C2b: bare status event → accepted by the pinned pipeline (expectation pre-registered; documents the
  permissive defaulting that made most historical status rejects non-reproducible).
- C3: two classification passes byte-identical.
- C4: all pins re-measured equal after the run.

## Limits

- Counts are instant-bound: `rejected.jsonl` gained rows during the run (controller ingesting
  concurrently), so the audit binds the hash in `report.json.pins`, not the live file.
- Source files are often rewritten after rejection; `source_mutated = 122/143` records that, and the
  replay is from the *current* source bytes.
- Worker measurement only: no ingest, no gate verdict, no node status, no `validation_status=passed`,
  no canonical file written. Backfill, if ever wanted, is a controller action.

## Falsifier

Re-run `audit.py` at the same pins and find a row that is neither in the accepted stream nor in the
seen-set, or a `REPLAY_VALID` row the pipeline rejects, or an accepted C1 sample the pipeline rejects.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-097/reject_audit/audit.py   # exit 0 = controls pass
```
