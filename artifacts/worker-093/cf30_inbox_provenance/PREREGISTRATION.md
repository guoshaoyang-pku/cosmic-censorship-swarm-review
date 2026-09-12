# W093-CF30-INBOX-PROVENANCE-01 — pre-registration

- actor: `worker-093`; node `A1`; gate `G-AUDIT`
- class binding: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- taken: 2026-09-12 ~01:21 +08:00, no inbox card exists for worker-093 (fleet relaunch; slot self-selects)
- read-only: no canonical file is written; no detector, map, ledger, review or inbox byte is edited;
  no gate verdict, node status, `validation_status=passed`, adoption or rollback is claimed.

## Question

CF-30 (`astra-life07-notice-injection`) reports three cards attributed to actor `astra` in
`comms/inbox/astra.jsonl` and `comms/inbox/astra-lead-audit.jsonl` with no accepted-stream emission
and no controller lifecycle record, and states the next falsifier:

> "A card in any inbox whose event_id never appears in the accepted stream, or a second write to
> an instrument under freeze."

The controller swept two inbox files. This task sweeps **every** `comms/inbox/*.jsonl` at pinned
bytes and tests the falsifier systematically, with independent provenance signals that do not rely
on actor attribution alone.

## Signals (each is recorded separately; no single signal is decisive)

- **S1 unbacked controller card** — a well-formed card whose claimed authority is the controller
  (`actor == "astra"`, `actor` starts with `human-pi`, or `event_id` starts with `astra-`/`human-pi-`)
  and whose `event_id` appears neither in the accepted stream `research_map/events.jsonl` nor as a
  literal in the controller lifecycle records / emitters
  (`runtime/state/controller_verification/*`, `research_map/astra_lifecycle*.py`).
  Non-controller (lead/worker) downward cards are expected to be absent from the accepted stream by
  design and are classified `DOWNWARD_*`, not unbacked.
- **S2 malformed controller prefix** — a non-JSON line whose text contains a controller-authority
  `event_id` token.
- **S3 duplicate event_id** — the same `event_id` on more than one card instance (across or within files).
- **S4 within-file timestamp inversion** — a later line whose parseable `created_at` is earlier than
  a preceding line's in the same file.
- **S5 missing event_id** — a well-formed JSON object that is not an event (no `event_id`/`event_type`).
- **S6 class axis** — `class_id`/`class_ids` tokens on cards that are not one of the four frozen
  classes (recorded; the four classes are the only legal binding surface).

## Pre-registered predictions (made before measurement)

- **P1** The set of S1-unbacked controller cards at T0 is exactly the three CF-30 ids
  `human-pi-detector-fix-20260912T0100`, `astra-detector-fix-0105`,
  `astra-detector-patch-result-0112`, on four card instances
  (`astra-lead-audit.jsonl:24,25,27` and `astra.jsonl:3`).
- **P2** Every other controller-authority card is accepted-stream backed; no new unbacked card exists
  in any other inbox file.
- **P3** At least one S4 inversion exists, in `comms/inbox/astra-lead-audit.jsonl`
  (line 27 `created_at` 01:12:00 precedes line 28 `created_at` 01:09:48 in file order).
- **P4** `astra-detector-patch-result-0112` is duplicated (S3) across `astra.jsonl:3` and
  `astra-lead-audit.jsonl:27`; the malformed `astra.jsonl:2` line carries the
  `human-pi-detector-fix-20260912T0100` prefix (S2).
- **P5** The remaining well-formed unaccepted cards are lead/worker downward traffic (≈42), i.e. not
  injection evidence; each is reported, not silently dropped.

## Controls (fail-closed; planted in a synthetic fixture directory, never in the real inboxes)

C1 accepted card → `ACCEPTED_BACKED`; C2 lifecycle-recorded card → `LIFECYCLE_BACKED`;
C3 quarantined id → quarantine ref present; C4 unbacked controller card → `UNBACKED_CONTROLLER`;
C5 lead downward card → `DOWNWARD_LEAD`; C6 malformed line with controller token → S2;
C7 well-formed non-event → S5; C8 repeated id → S3 count 2; C9 timestamp inversion → S4;
C10 out-of-set class token → S6. Real-data expectations R1–R4: `astra.jsonl:2` S2+S3-prefix,
`astra.jsonl:3` unbacked, `astra-lead-audit.jsonl:24/25/27` unbacked,
`astra-life07-notice-classsep-r3` accepted-or-lifecycle-backed.

## Adoption / decision

This is a measurement. It adopts nothing, rolls back nothing, voids nothing, and issues no verdict.
Its only outputs are the census, the controls, and the residual list.

## Falsifier

Withdrawn if, at the pinned T0 hashes: (a) any legitimate controller-authority card that is
accepted-stream or lifecycle-recorded is classified `UNBACKED_CONTROLLER`; (b) any card classified
`ACCEPTED_BACKED` lacks its `event_id` in the accepted stream; (c) any of C1–C10 or R1–R4 misses its
stated behaviour; (d) the three CF-30 ids are not reproduced by S1+S2+S3; (e) any pinned input hash
differs between T0 and T1, or the two census passes differ in digest.

## Limits (not claims)

The actor/authority field is attacker-controlled; S1 is therefore corroborated by S2–S4 but no
signal is treated as proof of authorship. File mtimes are recorded as context only and are never
used as a primary signal (copies/restores can move them). An empty residual (no new unbacked card)
is a statement about the pinned bytes at T0, not about the fleet's future writes.

## Addendum 1 — pre-run revision (2026-09-12, real clock 01:14:17 +08:00, before the instrument run)

A read-only pre-run scan of the live inboxes found **two additional controller-authority cards**
not covered by CF-30's enumerated three:

- `astra-classsep-stabilize-0118` (`actor: astra`, `event_type: assignment`, `created_at`
  2026-09-12T01:18:00+08:00) at `comms/inbox/astra.jsonl:4` and
  `comms/inbox/astra-lead-audit.jsonl:31`;
- both files' last-write mtime is 2026-09-12T01:12:31+08:00, i.e. the cards were written
  ~5.5 minutes **before** their claimed timestamp, and after controller pass 07 closed (01:10:29);
- a grep of `research_map/astra_lifecycle*.py` finds no syntactically emitted
  `"event_id": "astra-classsep-stabilize-0118"` (the three CF-30 ids likewise appear there only
  as quoted prose inside the quarantine notice, never in `"event_id": "<id>"` form).

Revised predictions (registered before the run):

- **P1'** The S1-unbacked controller set is the three CF-30 ids **plus**
  `astra-classsep-stabilize-0118` (2 instances), unless a syntactically emitted lifecycle literal
  or an accepted-stream entry exists for it at T0.
- **P3'** S4 inversions include `astra-lead-audit.jsonl:27→28` and the new cards' mtime inversion
  (claimed time later than the containing file's last write).
- **P6** Classification of `astra-classsep-stabilize-0118` is consistent across both instances.

Confound recorded: forward clock skew is common fleet-wide (several agents stamped events minutes
ahead of the real clock during this window), so "future-dated" and mtime-vs-created deltas are
reported as **context only** and are never treated as proof of injection. This census does not
adjudicate whether any unbacked card is forged; it enumerates, classifies and pins.
