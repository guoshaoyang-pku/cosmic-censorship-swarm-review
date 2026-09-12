# Comms protocol (controller-enforced)

Global state is `research_map/research_map.json`. Nothing else is authoritative.
A message is not a result; a result is an artifact + gate evidence referenced by hash.

## Channels

| direction | path | writer |
|---|---|---|
| downward | `comms/inbox/<agent>.jsonl` | Astra (and leads to their workers) |
| upward | `comms/outbox/<agent>.jsonl` | any agent |
| accepted stream | `research_map/events.jsonl` | `research_map/comms.py ingest` only |
| rejects | `comms/rejected.jsonl` | `research_map/comms.py ingest` only |

Agent ids: `astra`, `astra-lead-formulation`, `astra-lead-literature`,
`astra-lead-numerics`, `astra-lead-audit`, `deepseek-flash-01` … `deepseek-flash-20`.

Write one JSON object per line. Markdown files with a single fenced ```json block are
also ingested. Every event needs `event_id`, `event_type`, `created_at`, `actor`.

## Upward message types

- `status` — node_id, status (queued|active|blocked|done|rejected|killed), hours,
  summary, evidence_refs, next_falsifier
- `claim` — class_id, statement, conclusion_type, assumptions, falsifier,
  evidence_refs, artifact_refs (required for `theorem`)
- `artifact` — node_id, artifact_type, path, sha256, validation_status
- `blocker` — node_id, description, needed_to_unblock, evidence_refs
- `direction_update` — group_id, old_direction, new_direction, reason, evidence_refs,
  budget_delta_agent_hours
- `resource_request` — group_id, requested_agents, requested_agent_hours, justification,
  expected_information_gain, stop_rule
- `review` — target_id, reviewer, verdict (accept|revise|reject|inconclusive), score 0–5,
  hard_failures, findings

## Downward message types

- `assignment` — node_id, assignee, artifact, gate, evidence_refs, falsifier
- `budget` — group_id, delta_agent_hours, reason
- `gate` — gate_id, scope, verdict (pass|fail|pending), criteria, evidence_refs
- `priority_change` — scope, old_priority, new_priority, reason
- `kill` / `revive` — target_id, reason

## Rules

1. `conclusion_type: theorem` without `artifact_refs` is auto-rejected.
2. A node is `done` only when its declared artifact exists on disk, carries a sha256 in
   `runtime/state/artifact_hashes.json`, and has a reviewer verdict. Fluent text is never
   promoted.
3. Self-gravitating numerics are locked (`numerics_lock` in the map). N1 and anything
   downstream may not start until gates `G-FORM` and `G-AUDIT` are `pass`. Work on N0
   (flat-space) is allowed.
4. Cite evidence as `path#sha256-prefix` or `path:line`. Prefer primary sources.
5. Reject your own output before sending: does the artifact exist? does the falsifier
   actually falsify? does the class id match the file?

## Controller commands

```bash
python3 research_map/comms.py ingest          # pull outbox -> events.jsonl
python3 research_map/validate_map.py          # DAG + event schema
python3 research_map/audit_evidence.py        # done-node artifact/evidence audit
python3 research_map/checkpoint.py            # full 15-min checkpoint snapshot
python3 research_map/comms.py send <agent> '<json>'   # downward message
```
