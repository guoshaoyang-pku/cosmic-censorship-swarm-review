# A2 ablation harness (draft, unverified)

Worker-20 deliverable for assignment `asg-2026-09-11-A2-deepseek-flash-20-29`
(`comms/inbox/deepseek-flash-20.jsonl`), map node **A2**, class GLOBAL, gate
**G-AUDIT**. Stop rule honoured: synthetic/dummy proposers only, dry-run, **no
model calls**. The audit lead owns the design (`evaluation/ablation_design.yaml`);
this harness implements and stress-tests the design's budget discipline.

## Files

| file | role |
|---|---|
| `evaluation/ablation_harness.py` | the harness (self-contained, stdlib only) |
| `evaluation/ablation_report.json` | dry-run evidence bundle: per-arm metrics, budget check, limitations |
| `evaluation/ablation.csv` | per-arm metrics table (map-declared A2 artifact) |

## What it enforces

* Five arms: `strong_single`, `self_consistency` (k=5, correlated samples),
  `independent_cheap` (5 agents with independent biases, no aggregation),
  `cheap_coordinator` (same agents + majority coordinator), and the
  `random_iid_null` control (never primary).
* Identical enforced caps `(token_budget, wall_clock_budget)` for every arm;
  a call is issued only if both caps allow it. Failed calls still cost tokens.
* `check_matched_budgets` requires: same caps, no overspend, every primary arm
  token-limited (not wall-limited), token spread within tolerance, and residual
  below one episode cost. The `--self-test` negative control runs the same arms
  with episode-count matching and requires the checker to reject it on spread.
* Eight pre-registered metrics, reported per arm, never combined:
  accepted-claim rate, hard-failure rate, citation support, duplication,
  reviewer agreement, novel accepted coverage, cost per accepted claim,
  per-class coverage.

## Reproduce

```bash
python3 evaluation/ablation_harness.py --self-test        # 14 checks, incl. negative control
python3 evaluation/ablation_harness.py --dry-run \
  --json-out evaluation/ablation_report.json --csv-out evaluation/ablation.csv
# once the audit lead publishes the design:
python3 evaluation/ablation_harness.py --design evaluation/ablation_design.yaml --dry-run
```

Current dry-run (seed 20260911, 60 episodes, 20 000 tokens, 60 s envelope):
all four primary arms token-limited, spread 0.01, `primary_comparison_valid: true`.

## Falsifiers

1. An arm can be shown to overspend either cap, or the checker accepts a run in
   which primary arms are not all token-limited.
2. The unmatched-budget control passes `check_matched_budgets` (the harness's own
   negative control would then be broken).
3. A metric is shown to be combined into a scalar, or a metric is missing for any
   arm (the A0 rubric forbids a universal scalar score).
4. The harness makes a model call on a real endpoint (it must remain synthetic
   until G-FORM and G-AUDIT pass).
5. A reviewer shows the episode-prefix confound invalidates an arm comparison
   that the report states as a result rather than a limitation.

## Limitations (also in the report JSON)

* Token matching gives multi-sample arms fewer episodes, so rates are computed
  over different episode prefixes; `episodes_attempted` and per-class coverage
  keep the confound visible.
* Synthetic proposer parameters are placeholders: nothing here is evidence about
  real models.
* The iid null arm exhausts the suite before its token budget; it is a control,
  never a primary arm.
