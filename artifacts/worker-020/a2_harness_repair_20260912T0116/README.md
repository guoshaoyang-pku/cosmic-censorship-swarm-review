# A2 harness repair — worker-020 (slot of `deepseek-flash-20`)

Assignment: `asg-2026-09-11-A2-deepseek-flash-20-29` (node `A2`, class `GLOBAL`, gate `G-AUDIT`).
Canonical artifact owned: `evaluation/ablation_harness.py`. Stop rule respected: synthetic
dry-run only, zero model calls, provider path absent.

## What changed

`evaluation/ablation_harness.py` `df878e97bf6ede6c` (v0.1.0-draft) -> `0fae94bf01903ec7`
(v0.2.0-repair), closing the blocking findings of four independent reviews
(`review-a2-w18`, `w022-20260912T003206-a2-review`, `w067-a2bm-20260912T0110-10-review`,
`w019-a2-review-20260912T011117`):

| Finding | Disposition |
|---|---|
| wall-clock matching vacuous (constant `wall_clock_s`) | checker now tests wall **consumption** spread; synthetic latencies are proportional to token cost (declared 666.67 tok/s placeholder); slowed-arm control fires (spread 0.485) |
| tolerance 0.15 vs pre-registered +/-2% | defaults `token_tolerance=0.02`, `wall_tolerance=0.02`, both reported |
| `verifier_calls_per_accepted_artifact`, `human_review_minutes` never measured | measured per arm, spread-checked, emitted; unmatched fields flagged |
| envelope vs consumption ambiguity (w067-N3) | both readings computed; `wall_match_basis` selects the validity reading (default consumption) |
| dry run mistakable for a real result | `simulated`/`run_mode`/`disclaimer` in report; `simulated,run_mode,harness_sha256` leading CSV columns; unmarked output names refused (exit 2) |
| unquoted `- id: NULL` | design loader normalises to string `NULL`, normalisation reported |
| guardrail not applied before contrasts | `apply_guardrail` runs first; endpoint contrasts use guardrail-applied counts |
| unreliable exit status | 0 valid dry run, 2 guard refusal, 3 `--execute` refusal |
| two harness copies | canonical generator hash binds the live bytes; divergence from the design-named audit copy is recorded as a design-owner item |

## Evidence in this directory

| path | role |
|---|---|
| `prev/ablation_harness.df878e97.py` | preserved pinned draft bytes |
| `out/ablation_dryrun_designbound_report.json` | repaired dry run bound to `evaluation/ablation_design.yaml` (`1b2a83ef670b`) |
| `out/ablation_dryrun_designbound.csv` | same run, marked per row |
| `run.log` | self-test, dry run, guard probe, execute probe with exit codes |
| `check_a2_repair.py` + `checker_report.json` | author closure checker, 12/12 |
| `manifest.json` | hashes/sizes of every file above |

## Key dry-run numbers (simulated placeholders, not a real result)

* token spread `0.0101` <= 0.02, wall consumption spread `0.0101` <= 0.02, `budget_check.matched = true`
* per-arm wall seconds `30.0 / 30.0 / 29.7 / 29.76` (non-constant, unlike the pinned draft)
* `primary_comparison_valid = true`; no primary arm wall-limited
* declared matched fields: tokens/wall matched; `verifier_calls_per_accepted_artifact` (spread 1.074)
  and `human_review_minutes` (spread 3.547) unmatched — recorded as `design_deviations` for
  astra-lead-audit (a token-matched budget cannot equalise them across arms of different accuracy)

## Reproduce

```bash
python3 evaluation/ablation_harness.py --self-test                      # 21/21
python3 evaluation/ablation_harness.py --design evaluation/ablation_design.yaml \
    --outdir artifacts/worker-020/a2_harness_repair_20260912T0116/out
python3 artifacts/worker-020/a2_harness_repair_20260912T0116/check_a2_repair.py \
    --repo . --report artifacts/worker-020/a2_harness_repair_20260912T0116/out/ablation_dryrun_designbound_report.json \
    --csv artifacts/worker-020/a2_harness_repair_20260912T0116/out/ablation_dryrun_designbound.csv \
    --old-harness artifacts/worker-020/a2_harness_repair_20260912T0116/prev/ablation_harness.df878e97.py \
    --log artifacts/worker-020/a2_harness_repair_20260912T0116/run.log \
    --out artifacts/worker-020/a2_harness_repair_20260912T0116/checker_report.json
```

## Authority and residue

Worker self-check only: no node status, `validation_status=passed`, or gate verdict is claimed.
The pinned canonical dry-run outputs (`evaluation/ablation.csv`, `evaluation/ablation_dryrun.csv`,
their reports) still bind the old harness hash and were **not** rewritten; regenerating them at
the new pin is the owner's call (CF-12: one canonical path, one owner). Residue for
astra-lead-audit: design line 172 names the audit harness copy rather than the canonical path;
declared matched-field equalisation; NULL candidate-pool semantics.

Next falsifier: any byte change of `evaluation/ablation_harness.py`; a fresh
`--dry-run --design evaluation/ablation_design.yaml` at the cited hash reporting
`budget_check.matched=false`, a missing/constant wall-consumption spread, an unmeasured declared
matched field, an unmarked dry-run output, a guard allowing a canonical output name, `--execute`
exiting 0, or a no-output run mutating the pinned canonical dry-run files.
