# W022-A2-VERDICT-02 — second independent verdict on A2 (four-arm matched-budget ablation)

Bounded worker task by `worker-022`, class `GLOBAL`, gate `G-AUDIT`, node `A2`.
Self-issued: no assignment card existed in `comms/inbox/worker-022.jsonl`, and only one
independent A2 verdict was on disk (`reviews/A2-review-18.json`) while the audit lead's
00:08 blocker requires two (`audit-blocker-20260912T0009-a2`).

## Verdict

**revise, score 3.0, hard failure HF-11 (budget_laundering).** The design is well-formed
(four primary arms + mandatory NULL, ±2% token/wall-clock rule, 8 seeds, no universal
scalar score, execution honestly blocked) but three blocking defects are reproduced at
the pinned bytes:

| id | defect | key evidence |
|---|---|---|
| B1 | wall-clock matching is vacuous — `wall_clock_s=14400` is written as a constant on every row, so the design's own wall-clock falsifier cannot fire | `evaluation/ablation_dryrun_report.json#e1860fa1c6ce`, `evaluation/ablation_dryrun.csv#bda738fff675` (1 distinct value), `artifacts/audit/ablation_harness.py#ee0d87a14848:82`, control C1 |
| B2 | two of the four declared `matched_fields` (`verifier_calls_per_accepted_artifact`, `human_review_minutes`) are never measured or emitted | `evaluation/ablation_design.yaml#1b2a83ef670b:49,58`, `artifacts/audit/ablation_harness.py#ee0d87a14848:42-43`, check D4 |
| B3 | two harness copies enforce different tolerances — canonical `audit_lib.check_budget_match` at ±2%, `evaluation/ablation_harness.py` at `token_tolerance=0.15`, and the pinned design does not override it | control C2 (5% spread rejected by canonical, accepted by the copy), control C3 (effective tolerance 0.15) |

Non-blocking: N1 no `--execute` guard in the second copy; N2 no harness provenance in the
dry-run report; N3 metric-name drift (`information_gain`); N4 NULL arm honestly declared as
not the iid candidate-pool draw; N5 the canonical harness defaults `--outdir evaluation/`,
so a review rerun can mutate canonical dry-run files; N6 `id: NULL` is a YAML null literal.

## What is new relative to `reviews/A2-review-18.json`

This verdict was produced without reading review-18's text first, from the pinned bytes.
It adds three adversarial controls the first review did not run:

* **C1** — the canonical HF-11 checker *does* fire on a 10× wall-clock divergence when the
  data varies, so B1 is a data-generation defect, not a blind checker;
* **C2/C3** — the B3 tolerance divergence is confirmed *operationally* (a 5% token spread
  passes the second copy and fails the canonical rule; loading the pinned design leaves the
  copy at 0.15);
* **R1/R2** — a fresh canonical-harness dry-run in a scratch outdir reproduces every per-arm
  accept rate and token total, and the canonical `evaluation/ablation_dryrun*` files were
  verified byte-identical before and after (no review-time mutation).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-022/a2_second_verdict/run_a2_verdict_022.py
# -> verdict JSON + controls/ + repro/canonical_rerun/, read-only for canonical artifacts
```

Deterministic, no network, no model calls. Pins checked at run time:
design `1b2a83ef670b`, dry-run report `e1860fa1c6ce`, CSV `bda738fff675`, canonical harness
`ee0d87a14848`, second copy `df878e97bf6e`, `audit_lib` `ae573db84631`.

## Files

| file | what |
|---|---|
| `run_a2_verdict_022.py` | checker (read-only for canonicals; writes only under this dir) |
| `a2_verdict_022.json` | machine-readable verdict, checks, pins, findings, falsifier |
| `a2_verdict_022.json.sha256` | artifact hash |
| `controls/budget_controls_022.json` | C1/C2/C3 adversarial controls + R1/R2 reproduction |
| `pins.json` | measured sha256 of the six pinned inputs |
| `repro/canonical_rerun/` | fresh dry-run written to scratch (not evaluation/) |
| `SHA256SUMS` | manifest of every file in this directory |

## Non-claims

No A2 node completion, no G-AUDIT gate verdict (worker authority), no model budget spent,
no real arm result, and no statement about the four physics classes beyond the design's
task suite T1–T4.
