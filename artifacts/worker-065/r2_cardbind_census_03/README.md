# W065-R2-CARDBIND-CENSUS-03 — r2 wave closure re-census at the next cutoff

Class-bound: gate `G-AUDIT`, node `A1`; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`; targets F0/F1/F2a/F2b/N0/A0.
**Worker-level measurement only** — this file sets no gate verdict, no node status and no
`validation_status=passed`, and edits no reviewed artifact.

This is the run named as the *next falsifier* by `W065-R2-CARDBIND-CENSUS-02`
(`artifacts/worker-065/r2_cardbind_census/README.md`, report sha256 `37b68aac7262…`):
*"Re-run census.py at a later cutoff and check whether F2a gained a second reviewer without a
path overwrite."* It re-runs the same frozen tool at cutoff `2026-09-12T00:57:00+08:00`
instead of `00:55:00`, which is late enough to include the first verdicts that landed just
after the census-02 cutoff — `reviews/F2b-review-rev27-b.json` (mtime `00:55:40`) and
`reviews/N0-review-worker-012.json` (mtime `00:55:26`) — and early enough to exclude the
verdicts still being written at `00:59+`.

## Method change: census on a frozen input snapshot

The tree is live: between two otherwise identical invocations at the same cutoff, a first
attempt changed because `reviews/F1-review-worker-045.json` was rewritten at `00:59:50` and
`reviews/F2a-review-rev13-047.json` landed at `00:59:57` (both excluded by the cutoff, but
their recorded mtime/sha in the exclusion list moved). To make the report byte-reproducible
on pinned bytes, this run executes the same `census.py` (sha256 `70c5abfc68ab…`, unchanged
from census-02) against a scratch snapshot of `reviews/` + `research_map/research_map.json`,
pinned by `input_manifest.json` (179 entries, sha256 `a3adfdb06756…`). The snapshot is a copy;
the manifest hashes are the durable pins.

## Reproduce

```bash
cd <swarm-root>
python3 artifacts/worker-065/r2_cardbind_census/census.py \
  --repo <manifest-pinned snapshot> \
  --prereg $PWD/artifacts/worker-065/r2_independence_prereg/prereg.json \
  --cutoff 2026-09-12T00:57:00+08:00 \
  --generated-at 2026-09-12T00:58:00+08:00 \
  --out artifacts/worker-065/r2_cardbind_census_03/report.json
```

Two back-to-back runs on the frozen snapshot were byte-identical (`cmp`), and the delivered
`report.json` is byte-identical to those runs (the report carries no `--out` field).

## Result at cutoff 2026-09-12T00:57:00+08:00

Map sha256 `262da6979857…` (same 17 `audit-r2-*` card *definitions* as census-02 — no card
added, removed or re-pointed; `card_inventory.same_ids = true`), prereg sha256
`023d18b4cfb6…` (pinned match). Scanned 158 review files, 164 exclusion records, controls 6/6,
status `MEASURED`.

**9 card-bound verdicts (was 7), 4 path collisions (unchanged), 1 third-party replication
(unchanged), 6 unlanded card deliverables (was 7).**

### Per-target card-bound census (dedup by reviewer, pin-citing, prereg-filtered)

| target | live pin | card-bound reviewers | independent verdicts | independent accepts | ≥2 indep verdicts citing pin? |
|---|---|---|---|---|---|
| F0 | 0abb9ed8a961 | 041, 052 | 041, 052 | **041, 052 (accept)** | yes |
| F1 | cce9c60146d6 | 071, 085 | 071, 085 | none (both revise) | yes (verdicts), no accepts |
| F2a | 5476a3f2c6bc | 091 | 091 | none (revise) | no — 046 unlanded, `-a` missing |
| F2b | 55d0a1ea9bda | 015, 035 | 035 | none (revise) | no — 015 excluded, see below |
| N0 | da7c36071995 (artifact pin) | 012 | 012 | **012 (accept)** | no — single verdict, not pin-keyed |
| A0 | d748a9e3574e | 089 | 089 | none (revise) | no — single verdict |

The N0 row appears under the review's own target id
`numerics/results/flat_wave_convergence_rev3.json#da7c36071995…` rather than node id `N0`;
`target_summary` therefore has both the empty `N0` key and the populated artifact-pin key.
That is a target-key change, not a coverage regression. F2b's landed reviewer 015 is still
excluded as `B_PRIOR_ALIAS_AMBIGUOUS` (conservative; if the alias hypothesis were false,
F2b would have one independent verdict and still not two).

## Findings

- **F-065-CB-1 (F2a swapped pair) — hazard still live, no overwrite yet.** At the cutoff
  `reviews/F2a-review-rev27-a.json` is still missing and `reviews/F2a-review-rev27-b.json`
  is still byte-identical to its census-02 value (sha256 `fc2d94bbd54c…`, mtime `00:53:56`).
  `audit-r2-F2a-bindchain-worker-046` still declares `-b` and
  `audit-r2-F2a-bindchain-worker-091` still declares `-a`; F2a card-bound coverage is still
  one reviewer. `swap_pair_probe.verdict = no_overwrite_at_census_03_cutoff`. The r2 deadline
  is `02:15`, so the hazard is unresolved, not closed.
- **F-065-CB-3 (F2b cross-assignee collision) — did not materialise on disk.** Worker-035
  wrote its own base path `reviews/F2b-review-rev27-b.json` at `00:55:40` (`declared_path_honored
  = true`, classification `single_card`) instead of the addendum's declared `-a` path, so no
  verdict was overwritten and `audit-r2-F2b-b` is resolved. The map text of
  `audit-r2-F2b-bindchain-worker-035` still names `-a`, so the card text remains wrong; only
  the controller may repoint it (CF-12). F-065-CB-2 (F1, worker-085) is unchanged and also
  landed on the reviewer's own path.
- **F-065-CB-6 (new coverage).** The two post-census-02 landings add exactly:
  `reviews/F2b-review-rev27-b.json` (worker-035, revise, bound to `audit-r2-F2b-b`) and
  `reviews/N0-review-worker-012.json` (worker-012, accept, bound to `audit-r2-N0-rev3`,
  target pin `da7c36071995…`). F2b moves 0 → 1 independent pin-citing verdict; N0 moves
  0 → 1 independent accept. No other card-bound file changed hash or verdict
  (`changed_same_key = []`).
- **F-065-CB-7 (new, counting hazard).** `reviews/F2a-review-rev27-c.json` (worker-092, task
  `W092-F2A-CLASSBIND-REVIEW-01`, verdict revise) cites the live F2a pin and is a real review
  of the same target, but it is bound to no `audit-r2-*` card (`exclusion =
  not_bound_to_an_audit-r2-card`). A naive "any review file for F2a" count would report F2a
  at two independent reviewers and wrongly suggest the G-AUDIT threshold is reachable on
  F2a. This generalises F-065-CB-4 (worker-088 on F2b) to self-commissioned reviews.
- **Arithmetic consequence.** At this cutoff only F0 has two independent pin-citing accepts.
  F1 has two independent pin-citing verdicts but both are `revise`; F2a/F2b/A0 have one
  card-bound independent verdict each (all `revise`); N0 has one accept against the pinned
  result artifact. This is coverage arithmetic, not a gate verdict.

## Falsifier

Falsified if, at this cutoff, (a) any path classified `swapped_pair` or
`cross_assignee_collision` resolves to one card or one assignee on re-reading
`map.assignments` at map sha256 `262da6979857…`; or (b) any reviewer counted in
`independent_*` carries `A_ASSIGNED`/`B_PRIOR_ALIAS_AMBIGUOUS` for that target in prereg
`023d18b4cfb6…`; or (c) any reviewer listed in an `independent_*_citing_live_pin` field lacks
its target's live pin sha256 in its cited hashes; or (d) re-running `census.py` on the bytes
pinned by `input_manifest.json` at cutoff `2026-09-12T00:57:00+08:00` and generated-at
`2026-09-12T00:58:00+08:00` does not reproduce `report.json`; or (e)
`reviews/F2a-review-rev27-b.json` in the snapshot does not hash to `fc2d94bbd54c…` while
`swap_pair_probe.verdict` says `no_overwrite_at_census_03_cutoff`.

**Next falsifier (after the 02:15 r2 deadline):** re-run at a later cutoff and check whether
`reviews/F2a-review-rev27-a.json` appeared (046 landed) or `-b` changed hash (overwrite); and
whether any second *card-bound* F2a/F2b/A0 verdict landed without a path collision.

## Files

| file | sha256 | note |
|---|---|---|
| `report.json` | `32a37296b6fb…` | full census measurement on the frozen snapshot, controls 6/6 |
| `diff_vs_02.json` | `61c34ada7010…` | machine diff against census-02 (11 delta sections) |
| `input_manifest.json` | `a3adfdb06756…` | 179 pinned input bytes (reviews + map), prereg and tool hashes |
| `freeze_inputs.py` | `2b3ac7c59950…` | deterministic manifest generator (stdlib only) |
| `diff_reports.py` | `b87a08b65fa8…` | deterministic diff generator (stdlib only) |
| `census.py` (census-02 dir) | `70c5abfc68ab…` | unchanged frozen tool, sha pinned in manifest |
| `checkpoint.json` | see file | artifact hashes + inputs + falsifier |
| `runtime/state/worker-065_r2_cardbind_census_03_checkpoint.json` | see file | same checkpoint in the shared state dir |

## Non-claims

- Worker-level measurement only: no gate verdict, no node status, no `validation_status`, and
  no edit to any reviewed artifact.
- `counts_as_independent` is the prereg's procedural pre-card involvement test, not proof of
  bias and not a verdict on any review.
- Path-collision classes describe the **map assignment text** at the recorded map sha256,
  except `declared_path_not_honored`, which compares map text with on-disk behaviour.
- The tool does not read or rank the substance of any verdict; `accept`/`revise` strings are
  copied from the review files.
- `astra-life05-verify-gform-r3` supersedes the eight `audit-r2-*-bindchain` cards, so this
  census is an r2-wave closure measurement, not the current G-FORM review path.
