# W097-REJECT-STREAM-AUDIT-01 — pre-registration (written before measurement)

Slot: worker-097 (bounded execution worker). Created 2026-09-12T00:45+08:00, before `audit.py` was executed.

## Task (one bounded, class-bound task)

Audit `comms/rejected.jsonl` (the ingester's reject record) against the **current pinned ingest
pipeline** (`research_map/comms.py` + `research_map/schemas.py`) and quantify **class-bound evidence
loss**: rejected events that the pinned pipeline would accept today, grouped by class_id and node_id,
and whether any carries a hash binding a currently pinned canonical artifact.

Class binding: every rejected event's `class_id`/`class_ids` and `node_id`/`node_ids` are read from
the source event; the four frozen classes are AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH. Primary node: A1 (audit / evidence integrity), gate G-AUDIT.

## Method (read-only; no ingest, no canonical writes)

1. Pin `comms.py`, `schemas.py`, `comms/rejected.jsonl`, `research_map/events.jsonl`,
   `research_map/research_map.json` by sha256; fail closed (exit 3) on drift.
2. For each reject row: locate the original event in its recorded `source` file by `event_id`
   using the pinned `_json_objects` extractor; replay `normalize_event` + `validate_event`.
   Classification: NOW_VALID / STILL_INVALID / IRRECOVERABLE (source gone) / ALREADY_ACCEPTED
   (event_id in `runtime/state/ingested_ids.json`).
3. Flag source mutation: the stored `raw` is truncated to 600 chars; if the current source bytes do
   not share a 300-char whitespace-stripped prefix with `raw`, mark SOURCE_MUTATED and treat replay
   as advisory for that row.
4. Group NOW_VALID rows by event_type, actor, class_id, node_id; flag rows whose evidence hash
   equals a currently measured canonical artifact hash (F0/F1/F2a/F2b/L0/L1/A0/A2 artifacts).

## Pre-registered predictions (from reading the pinned normalizer before running)

- P1: status rejects (~87) are mostly NOW_VALID, because `normalize_event` now defaults
  `node_id=GLOBAL` and `status=active`; the historical "status: missing node_id" reason is not
  reproducible on the pinned pipeline for events that still carry `event_type=status`.
- P2: claim rejects with "invalid conclusion_type" (~22) are mostly STILL_INVALID: `normalize_event`
  only defaults a *missing* conclusion_type, it does not rewrite an explicit out-of-vocabulary token.
- P3: artifact rejects "missing node_id" (2) are STILL_INVALID: `node_id` is never defaulted for
  artifact events.
- P4: blocker rejects (~27) are mostly NOW_VALID (description joined/defaulted; node_id defaulted).
- P5: at least one reject row's source file has changed since rejection (flash-15-status.jsonl
  currently has 2 lines but 80 rejects), so raw-prefix mutation flags will be non-zero.

## Controls (pre-registered expectations)

- C1: 40 accepted events sampled from `events.jsonl` replayed through the same pipeline → 40/40 pass.
- C2a: synthetic artifact event lacking `node_id` → rejected.
- C2b: synthetic bare status event (`event_id`, `event_type`, `actor`, `created_at` only) → accepted
  by the pinned pipeline (documents permissiveness; expectation recorded before running).
- C3: two independent classification passes are byte-identical (determinism).
- C4: all pins re-measured equal after the run (no drift caused by the audit).

## Falsifier

Re-run at the same pins and find a NOW_VALID row that the pinned `normalize_event`+`validate_event`
rejects, or an accepted event (C1) that the pipeline rejects, or two runs that disagree, or a pin
that moves. A single counterexample voids the corresponding classification.

## Authority

Worker measurement only. No ingest, no gate verdict, no node status, no `validation_status=passed`,
no canonical file write. Backfill of rejected evidence, if desired, is a controller action
(`comms.py ingest`) and is explicitly not performed here.
