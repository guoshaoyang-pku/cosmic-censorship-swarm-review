# Superseded pre-assignment messages (worker 08)

Moved here 2026-09-11T23:24+08:00.

- `e08_status.msg.json` — claimed "no assignment exists" at 23:23 (timestamp), but the
  assignment `asg-2026-09-11-L1-deepseek-flash-08-17` had landed in
  `comms/inbox/deepseek-flash-08.jsonl` at 23:19:12. The file was schema-invalid at the
  time (status was not yet in EVENT_TYPES) and is recorded in `comms/rejected.jsonl`.
  Superseded by `comms/outbox/deepseek-flash-08.jsonl` event
  `e08-status-20260911T2324-l1-ack`.
- `e08_blocker_f0_a0.msg.json` — contained the same F0/A0 artifact-existence finding;
  superseded by `e08-blocker-20260911T2324-f0-artifact-pointer`, which adds the
  F0.artifact pointer side effect.

Kept for the audit trail; not intended for ingest.
