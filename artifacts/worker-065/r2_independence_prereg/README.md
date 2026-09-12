# W065-R2-INDEP-PREREG-01 -- pre-registered independence census of the r2 review fleet

Class-bound: nodes F0/F1/F2a/F2b/N0/A0; classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH; gate G-AUDIT. Worker-level measurement only.

## Question

The `audit-r2-*` cards (first batch 2026-09-12T00:44:18+08:00) require the reviewer to be
neither an author of the target nor previously exposed to another reviewer's verdict on it.
That is self-certified in each card. This tool freezes the pre-card evidence classification
**before** any r2 verdict is admitted.

## Result (frozen card set: 17 cards, 10 distinct reviewer/target pairs)

| reviewer | node | class | classification |
|---|---|---|---|
| worker-012 | N0 | AF-WCC-SCALAR-SPH | A_ASSIGNED+R2_MULTI_CARD_SAME_PAIR |
| worker-012 | N0 | AF-WCC-SCALAR-SPH | A_ASSIGNED+R2_MULTI_CARD_SAME_PAIR |
| worker-015 | F2b | AF-SCC-C0-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-015 | F2b | AF-SCC-C0-VAC-GEN | R2_MULTI_CARD_SAME_PAIR+B_PRIOR_ALIAS_AMBIGUOUS |
| worker-035 | F2b | AF-SCC-C0-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-035 | F2b | AF-SCC-C0-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-041 | F0 | GLOBAL | CLEAN_PRE_CARD |
| worker-046 | F2a | AF-SCC-C2-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-046 | F2a | AF-SCC-C2-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-052 | F0 | GLOBAL | CLEAN_PRE_CARD |
| worker-071 | F1 | AF-WCC-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-071 | F1 | AF-WCC-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-085 | F1 | AF-WCC-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-085 | F1 | AF-WCC-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-089 | A0 | GLOBAL | CLEAN_PRE_CARD |
| worker-091 | F2a | AF-SCC-C2-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |
| worker-091 | F2a | AF-SCC-C2-VAC-GEN | R2_MULTI_CARD_SAME_PAIR |

Summary: 3 clean, 14 flagged; controls 4/4; window stable=True.

## What the flags mean (and do not mean)

- `A_ASSIGNED` -- a strictly pre-card map assignment on the same node under the reviewer's
  id **or an alias form**. worker-012/N0 matches legacy assignment
  `asg-2026-09-11-N0-deepseek-flash-12-21`; this is also the strongest available evidence that
  `worker-012` and `deepseek-flash-12` are the same executor.
- `B_PRIOR_ALIAS_AMBIGUOUS` -- a pre-card review document on the same target under an alias id
  form (worker-015/F2b: `reviews/F2b-f0-binding-w015.json` by `deepseek-flash-15`, verdict revise).
  Identity is not asserted; the row is flagged rather than silently counted clean.
- `R2_MULTI_CARD_SAME_PAIR` -- more than one r2 card for the same reviewer and node (the
  00:46:18/00:47:58 bindchain cards). A second card to the same reviewer is not a second
  independent reviewer; G-AUDIT's per-target accept count must deduplicate by reviewer.
- Direct exposure to another reviewer's verdict document in the reviewer's own pre-card tree:
  **0 rows**. References found inside copies of the map/target are classified incidental and
  reported in `prereg.json` under `C_incidental_references`.

Flags are **pre-card involvement indicators, not proof of bias and not gate failures**. No
verdict on any schema or any r2 review is expressed here.

## Same-executor caveat

`research_map.json` registers only the leads and `flash-pool` (executor_pool, model
deepseek-flash); individual worker ids are not registered. All ten r2 reviewers are the same
executor pool, so "two independent verdicts" can only mean procedural independence
(different context/harness), not statistical independence of judges.

## Method

Deterministic stdlib-only scan; `classify()` is exercised by four planted controls
(author event, clean reviewer, prior verdict, alias-form prior verdict) and all four must fire.
Evidence cutoff is per card: file mtime < that card's `created_at`; r2 verdicts written after
dispatch are excluded by construction. Frozen copies of the cards, map, FROZEN.json, target
schemas and events.jsonl are under `snapshot/`.

## Falsifier

Re-run on the frozen snapshot. Falsified if any row classified `CLEAN_PRE_CARD` has, in the
pre-card evidence base, a target-path artifact event by that reviewer, a prior review document
on the same target under any id form, or a direct reference to another reviewer's verdict
document for that target; or if a planted control fails to fire; or if the pre/post window
hashes differ.

## Reproduction

```bash
python3 artifacts/worker-065/r2_independence_prereg/prereg.py
```

## Pins at freeze time

| node | path | sha256 (live = FROZEN rev28) |
|---|---|---|
| F0 | research_map/formulation_taxonomy.yaml | 0abb9ed8a96135c9 |
| F1 | schemas/af_wcc_vacuum.yaml | cce9c60146d6a907 |
| F2a | schemas/af_scc_c2_vacuum.yaml | 5476a3f2c6bc7196 |
| F2b | schemas/af_scc_c0_vacuum.yaml | 55d0a1ea9bda96b8 |
| N0 | numerics/CONVERGENCE_PROTOCOL.md | 1e6cdf04d7a24313 |
| A0 | evaluation_rubric.yaml | d748a9e3574ebe0c |
