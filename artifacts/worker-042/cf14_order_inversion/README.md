# W042-ORDER-INVERSION-03 — arrival order vs created_at order in the accepted event stream

Worker: `worker-042` · node `A1` · classes `AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH`
Task taken: no assignment card existed in `comms/inbox/worker-042.jsonl`; this is one bounded,
self-claimed, class-bound evidence task. **Worker-level evidence only: no node status, no
validation_status, no gate verdict, no publication change.**

## Question

`research_map/apply_events.py` consumes `research_map/events.jsonl` in file (arrival) order and
overwrites per-key state last-write-wins (node `status`, node canonical `artifact` sha/status,
authority `gate` verdicts, `kill`/`revive`, group direction). CF-14 says created_at is often ahead
of wall clock. At one pinned snapshot: for every overwrite key, does the arrival-order winner equal
the created_at-order winner; where they differ, is the *recorded state* different; and does the
pinned map match the arrival-order winner?

## Pinned inputs (read-only; checker fails closed on drift)

| input | sha256 (prefix) | note |
|---|---|---|
| `snapshot/events_e6c24026c0cc.jsonl` | `e6c24026c0cc` | 2586 lines, byte copy of `research_map/events.jsonl` at 00:36:09 |
| `snapshot/map_3ec4f4427c13.json` | `3ec4f4427c13` | byte copy of `research_map/research_map.json` (updated_at 00:36:03) |
| `snapshot/apply_events_16820bf206b7.py` | `16820bf206b7` | the applier whose overwrite semantics are re-implemented |
| `snapshot/manifest.json` | `98660c50976a` | per-file pins, `pinned_at` 2026-09-12T00:36:09+08:00 |

Tool: `audit_order_inversion.py#8db7f0cb0b5f`. Report: `report.json#2511c2363e15`.
Rerun: `python3 artifacts/worker-042/cf14_order_inversion/audit_order_inversion.py --snapshot artifacts/worker-042/cf14_order_inversion/snapshot --out artifacts/worker-042/cf14_order_inversion/report.json`

## Headline (pinned)

- **CF-14 refreshed:** 192 / 1739 events with an ingest stamp carry `created_at` after
  `_received_at` (max skew 3099 s); 57 are still future-dated at the pin, max `02:00:00`.
  847 events predate ingest stamping and cannot be checked this way.
- **22 state-changing order inversions** among 134 multi-event overwrite keys (933 keys total):
  artifact=15, status=6, direction=1.
- **12 touch a pinned map node**: 7 canonical-artifact (L0, L1, F0, F1, F2a, F2b, N0) and
  5 node-status (A1, F1, F2b, L0, L1). The 7 remaining artifact inversions are on the
  `artifacts/formulation/` authoring tree (drift copies, not `schemas/`).
  Representative: `L0 ledger/theorems.jsonl` — arrival `3e3d35531421` (unverified) vs
  created_at-order `7f6213166ca7` (`lead-literature`, **passed**, stamp 00:52:10, line 368);
  `F1 schemas/af_wcc_vacuum.yaml` — arrival `cce9c60146d6` vs created_at-order `9a8bd4c96800`
  (stamp 00:44:00, line 1237); `N0 numerics/tests/flat_wave.py` — same sha, arrival `unverified`
  vs created_at-order `passed` (`astra-lead-numerics`).
- **Gate verdicts are not order-sensitive at this pin:** all 36 gate events are `pending`
  (28 authority), so 0 gate inversions.
- **The pinned map is arrival-ordered** as designed (CF-6): arrival-order winners equal the map on
  5/5 gate keys, 10/12 node canonical artifacts (2 nodes have no artifact events for their assigned
  path) and 12/12 node statuses.

**Interpretation:** the map's current state is a function of append order, not of agent-stamped
time; that is the documented policy. The risk measured here is *replay fidelity*: any rebuild that
re-orders the accepted events by `created_at` (or by outbox filename) changes canonical artifact
hashes, several validation statuses (including authority `passed`), node statuses and one group
direction — so a rebuild must preserve the append order of `events.jsonl`.

## Controls (9/9 pass; exit 0, fail-closed otherwise)

C1 inversion detected; C2 monotone timestamps → none; C3 equal stamps → deterministic line tiebreak,
not an inversion; C4 identical payload → order-only, not state-changing; C5 append-only types carry
no overwrite key; C6 one undated event → key excluded, no crash; C7 authority gate verdict change →
inversion; C8 `AUTHORITY` constant equals the set in the pinned applier bytes; C9 real-result
invariants (stamp winner arrived earlier, later stamp, different payload). A second run on the same
snapshot reproduces every field except the report timestamp.

## Scope / limits

- "Arrival order" = line order of the append-only `events.jsonl`; first `event_id` wins, matching
  `applied_event_ids` dedup.
- Only overwrite keys are audited; `claim`/`review`/`blocker`/`resource_request`/`assignment`/
  `budget` are append-only and order-insensitive. Resource-request *decisions* and the approval
  matcher are a separate task (W032/W085) and are not re-audited here.
- The report compares payload fields the applier overwrites. It does not replay the whole map, and
  it does not adjudicate whether any inverted event is correct.
- Counts are snapshot-bound; the live stream keeps growing (the pinned bytes are what the falsifier
  re-runs against).
