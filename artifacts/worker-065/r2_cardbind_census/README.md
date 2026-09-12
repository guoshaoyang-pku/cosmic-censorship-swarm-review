# W065-R2-CARDBIND-CENSUS-02 — audit-r2 deliverable binding + per-target independence census

Class-bound: gate `G-AUDIT`, node `A1`; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`; targets F0/F1/F2a/F2b/N0/A0.
Worker-level measurement only — this file sets no gate verdict, no node status and no
`validation_status=passed`, and edits no reviewed artifact.

This is the post-verdict half of `W065-R2-INDEP-PREREG-01`
(`artifacts/worker-065/r2_independence_prereg/`, prereg sha256 `023d18b4cfb6…`, verified
equal at run time). The prereg froze the pre-card involvement classification of the 17
`audit-r2-*` cards and stated the next falsifier: *"Re-run after the r2 verdicts land and
count per-target accepts deduplicated by reviewer."* This census does that and adds the
missing half — binding each landed verdict file back to the card that commissioned it.

## Reproduce

```bash
cd <swarm-root>
python3 artifacts/worker-065/r2_cardbind_census/census.py \
  --repo . --cutoff 2026-09-12T00:55:00+08:00 \
  --generated-at 2026-09-12T00:57:00+08:00 \
  --out artifacts/worker-065/r2_cardbind_census/report.json
```

Byte-reproducible (`cmp` verified on two runs). Later cutoffs include later verdicts; the
cutoff is part of the measurement, not a convenience.

## Result at cutoff 2026-09-12T00:55:00+08:00

7 card-bound verdict files, 1 third-party replication, 4 declared-deliverable path
collisions, 1 declared path that was not used, 7 card deliverables unlanded. Controls 6/6.

### Per-target card-bound census (dedup by reviewer, pin-citing, prereg-filtered)

| target | live pin (12) | card-bound reviewers | independent verdicts | independent accepts | ≥2 indep verdicts citing pin? |
|---|---|---|---|---|---|
| F0 | 0abb9ed8a961 | 041, 052 | 041, 052 | **041, 052 (accept)** | yes |
| F1 | cce9c60146d6 | 071, 085 | 071, 085 | none (both revise) | yes (verdicts), no accepts |
| F2a | 5476a3f2c6bc | 091 | 091 | none (revise) | no — 046 unlanded |
| F2b | 55d0a1ea9bda | 015 | none (015 excluded, see below) | none | no — 035 unlanded |
| N0 | 1e6cdf04d7a2 | none | none | none | no — worker-012 unlanded |
| A0 | d748a9e3574e | 089 | 089 | none (revise) | no — single verdict |

`independent` = reviewer is the card's assignee, deduplicated per (target, reviewer), cites
the target's live pin sha256, and carries neither `A_ASSIGNED` nor `B_PRIOR_ALIAS_AMBIGUOUS`
for that target in the frozen prereg. F2b's landed reviewer (015) is excluded as
`B_PRIOR_ALIAS_AMBIGUOUS` (a pre-card `deepseek-flash-15` F2b verdict exists; identity is
ambiguous, not asserted). That is a **conservative** exclusion: if the alias hypothesis is
false, 015 would be the single independent F2b verdict and F2b still would not reach two.
`R2_MULTI_CARD_SAME_PAIR` (071, 085, 091, 015) is a card-counting hazard, not a bias flag,
and is resolved by the dedup — it does not by itself exclude anyone.

### Findings

- **F-065-CB-1 (swapped pair, F2a, live hazard).** `audit-r2-F2a-bindchain-worker-046`
  declares `reviews/F2a-review-rev27-b.json` (worker-091's base deliverable) and
  `audit-r2-F2a-bindchain-worker-091` declares `reviews/F2a-review-rev27-a.json` (046's).
  Each reviewer's addendum points at the other's file. At the cutoff only `-b` exists
  (worker-091) and `-a` is missing; if 046 obeys its addendum literally it overwrites
  091's verdict. F2a coverage must be bound by reviewer/card, never by path.
- **F-065-CB-2 (cross-assignee collision, F1).** `audit-r2-F1-bindchain-worker-085`
  declares `reviews/F1-review-rev27-a.json`, which is worker-071's base deliverable. Worker
  085 in fact wrote `reviews/F1-review-rev27-b.json` (their own base path) and named both
  cards; recorded under `declared_path_not_honored`. No overwrite occurred, but the card
  text is wrong and only the controller may repoint it (CF-12: one canonical path, one owner).
- **F-065-CB-3 (cross-assignee collision, F2b).** `audit-r2-F2b-bindchain-worker-035`
  declares `reviews/F2b-review-rev27-a.json` (worker-015's file); 035's own base deliverable
  `reviews/F2b-review-rev27-b.json` is unlanded at the cutoff. Same bind-by-reviewer rule.
- **F-065-CB-4 (third-party replication must not count).** `reviews/F2b-review-088.json`
  self-claims the F2b r2 card scope but worker-088 is not an assignee of
  `audit-r2-F2b-a/-b`. A naive "any review file for F2b" census would count 088 as a second
  independent F2b reviewer and wrongly report the G-AUDIT threshold as reachable. The tool
  classifies it `third_party_replication` and counts it toward no card.
- **F-065-CB-5 (supersede is not a collision).** `audit-r2-N0` and `audit-r2-N0-rev3` share
  assignee worker-012 and the same deliverable path; the card text says SUPERSEDES, so this
  is same-assignee sequential and yields at most one independent N0 verdict.
- **Arithmetic consequence.** At this cutoff only F0 has two independent pin-citing accepts.
  F1 has two independent pin-citing verdicts but both are `revise`; F2a/F2b/N0/A0 are at one
  or zero. This is coverage arithmetic, not a gate verdict.

## Controls (all run through the same code paths as the census)

| id | check | result |
|---|---|---|
| C1 | duplicate accept file, same reviewer+target → 1 dedup accept, duplicates=1 | pass |
| C2 | `A_ASSIGNED` reviewer accept → counted in dedup, excluded from independent | pass |
| C3 | accept+revise from one reviewer → `conflict`, not an accept | pass |
| C4 | synthetic swapped pair → both paths `swapped_pair` | pass |
| C5 | base+own-addendum on one path → `same_assignee_sequential`, not a collision | pass |
| C6 | self-claimed card by a non-assignee → filtered by the own-card filter | pass |

## Scope limits

- Cutoff-bound: `reviews/*.json` with mtime ≤ cutoff and (when present) `created_at` ≤
  cutoff. Verdicts landing after the cutoff are excluded by construction; re-run with a
  later cutoff for an updated census.
- `R2_MULTI_CARD_SAME_PAIR`, `A_ASSIGNED`, `B_PRIOR_ALIAS_AMBIGUOUS` are procedural
  pre-card involvement indicators from the frozen prereg — not proof of bias, not verdicts
  on any review, not gate failures.
- Collision classes describe the **map assignment text** at the recorded map sha256
  (`research_map/research_map.json`, measured in `report.json`); they are not claims about
  what any worker actually wrote. `declared_path_not_honored` is the one place where map
  text and on-disk behaviour are compared.
- The tool does not read or rank the substance of any verdict; `accept`/`revise` are copied
  from each file.

## Falsifier

Falsified if, at this cutoff, (a) any path classified `swapped_pair` or
`cross_assignee_collision` resolves to one card or one assignee on re-reading
`map.assignments` at the recorded map sha256; or (b) any reviewer counted in `independent_*`
carries `A_ASSIGNED`/`B_PRIOR_ALIAS_AMBIGUOUS` for that target in the frozen prereg; or
(c) any reviewer listed in an `independent_*_citing_live_pin` field lacks its target's live
pin sha256 in its cited hashes; or (d) re-running the tool at the recorded cutoff and
generated-at on unchanged bytes does not reproduce `report.json` modulo `--out`.

## Files

- `census.py` — deterministic tool (stdlib only), 6 built-in controls
- `report.json` — full measurement: cards, path binding, per-file bindings, per-target
  summary, controls, excluded files, scope limits, falsifier
- `checkpoint.json` — artifact hashes of this directory + inputs
- `runtime/state/worker-065_r2_cardbind_census_checkpoint.json` — same, in the shared state dir
