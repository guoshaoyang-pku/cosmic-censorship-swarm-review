# W05-T1 proposal — Flash-pool intent-overlap and assignment-gap snapshot

- **Worker:** deepseek-flash-05 (DeepSeek Flash breadth executor)
- **Node binding:** A1 (independent review queue) as audit-support input to A2 (strong-vs-cheap ablation)
- **Class binding:** cross-class meta-audit over AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN,
  AF-WCC-SCALAR-SPH; per-worker class mentions are recorded, **no mathematical class is redefined**
- **Status:** PROPOSED, not assigned by a group lead; **no node is claimed complete**
- **Created:** 2026-09-11T23:20+08:00

## Why this task

At 2026-09-11T23:15+08:00 `comms/inbox/` was empty: no group lead had issued a class-bound
assignment, while `runtime/state/processes` lists 20 DeepSeek Flash executors and `comms/outbox/`
was empty (0/20 workers had emitted a contract event). The immediate queue in
`research_map/ASTRA_HANDOFF.md` has 7 items (F1, F2, L0/L1, A1, N0, A2) for 20 breadth workers,
so self-selection is the only selector currently operating. That is a measurable coordination
failure mode, and ARCHITECTURE.md names duplication as a first-class metric.

This task measures it from the only available evidence (the live worker logs), at a declared
snapshot time, with a re-runnable script, instead of asserting it.

## Artifact(s)

| path | content |
|---|---|
| `artifacts/worker-05/flash_pool_overlap.py` | stdlib-only scanner with `--selftest` control and `--scan` |
| `artifacts/worker-05/flash_pool_overlap.json` | machine-readable snapshot: per-worker intents, aggregates, findings, log hashes |
| `artifacts/worker-05/flash_pool_overlap.md` | human-readable report with evidence refs and limitations |

## Acceptance test (self-checkable)

1. `python3 artifacts/worker-05/flash_pool_overlap.py --selftest` exits 0 and detects a planted
   2-worker overlap plus a zero-overlap control, and rejects `F10`/`AAF1` false-positive node matches.
2. `--scan` writes JSON + MD; every aggregate count can be recomputed from the per-worker records.
3. Every finding carries `evidence_refs` of the form `runtime/logs/<file>.log:<line>`.
4. Log snapshot SHA256 hashes are recorded so a re-run can detect that the evidence moved.

## Scope and exclusions

- **In scope:** intent overlap across the 20 Flash logs, immediate-queue coverage gaps, sanctioned
  channel usage (`comms/outbox`), and the machine-checkability of class binding in
  `research_map.json`.
- **Out of scope:** mathematical review of any draft; verification of F1/F2 content; claims about
  theorem scope; edits to `research_map.json`; creating `schemas/`, `ledger/`, `reviews/` or
  `numerics/` artifacts owned by other nodes.
- **Confound stated up front:** logs capture reasoning-in-progress, not final actions. This is a
  *predictive* snapshot of duplication, not a post-hoc audit of delivered artifacts.

## Expected information gain

- Quantifies wasted Flash breadth (duplicate drafts per node) before the fleet scales past 20,
  which ARCHITECTURE.md flags as the scaling bottleneck.
- Gives Astra/lead-audit a falsifiable number for the A2 duplication metric, plus the list of
  queue items with zero workers on them.
- Tests whether the "class-bound assignment" protocol is operating at all in its first minutes.

## Next falsifier

Re-run `--scan` after a lead posts explicit `assignment` events in `comms/outbox`. If per-node
worker concentration drops to its assigned owner(s) and every immediate-queue item has a named
assignee, the duplication/assignment-gap finding is **refuted** for that window. If the scan's
own log snapshot hashes have changed, the earlier snapshot must be re-taken before comparison.

## Reference (this proposal is itself a first observation)

- 20 Flash workers listed: `runtime/state/processes`
- Empty inbox/outbox: `comms/inbox/`, `comms/outbox/`
- Immediate queue: `research_map/ASTRA_HANDOFF.md:36-43`
- Duplication named as a metric: `research_map/ARCHITECTURE.md:52`
