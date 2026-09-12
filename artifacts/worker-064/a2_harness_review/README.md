# W064-A2-HARNESS-REPAIR-REVIEW-01 — independent review of the repaired A2 harness

**Reviewer:** worker-064 (no inbox card; one bounded class-bound task self-selected because the
author's manifest explicitly asks for an independent review at this hash).
**Node:** A2 · **Gate:** G-AUDIT · **Class:** GLOBAL · **Authority:** worker review, advisory only.

## What was reviewed

| object | pin (sha256) |
|---|---|
| `evaluation/ablation_harness.py` (v0.2.0-repair) | `0fae94bf01903ec7b8076a6b11706bc4444b19f98e6d0985e4ac2d1b2921f157` |
| `evaluation/ablation_design.yaml` | `1b2a83ef670b7e757a1a54d4849b49a597d5dc33e9205c0b5b10646d811cfb0a` |
| author design-bound report | `5b8e8b943b2ee012f6d298b69cc0d875c2af72bb0511dacabcb0bbc3b4f8b2ad` |
| author design-bound CSV | `1992f62f0c40dffe1d76ddbe60afc44efec996f0453a71d81b736ff769a4ce60` |
| prior verdicts checked for closure | `A2-review-18` `f2281713424c`, `A2-review-022` `cb0256970b1a`, `A2-review-worker-067` `f05e0424764b`, `A2-review-19` `36edeff97014`, `A2-hf19-adjudication-worker-067` `7a57c70fd315` |

The registered node-A2 artifact is still `evaluation/ablation.csv#ee3aa6cb97d0`; the design's
`artifacts.harness` entry is still `artifacts/audit/ablation_harness.py#ee0d87a14848`.

## Method

`run_review.py` (stdlib + PyYAML, deterministic, read-only on canonical paths) runs:

1. **P1** — pin every reviewed input before and after; refuse on drift.
2. **R1** — seven fresh `--self-test` runs; parse and record each check.
3. **R2** — two fresh `--dry-run --design evaluation/ablation_design.yaml` runs; CSV byte
   determinism, report determinism modulo wall-clock fields, and byte-level reproduction of the
   author's pinned design-bound report/CSV.
4. **R3** — independent recomputation of the matched-budget statistics from the raw per-arm CSV
   rows (never from the report's summary fields), under both spread conventions.
5. **R4** — dry-run provenance markers in report and every CSV row.
6. **R5** — per-finding closure table for the four prior revise verdicts at the new hash.
7. **R6** — no-network static scan, `--execute` fail-closed, unmarked-output refusal.
8. **R7/K5** — hermeticity probe of the self-test's fixed-name temp writes (sandbox squat).
9. **K1–K7** — negative controls (tampered CSV, stripped marker, forged provenance, NULL quoting
   variant, temp-path squat, flaky-determinism mechanism, 40-run flakiness rate).

## Result — verdict `revise`, score 4.0, 8/8 controls, 0 input drift

The repair closes the harness-side blockers at the new hash:

* **B1 wall-clock matching is non-vacuous** — independently recomputed wall consumption has
  3 distinct values and spread `0.010101` (= (max−min)/min), not the constant 60 s of the draft.
* **B2 tolerances** — `token_tolerance = wall_tolerance = 0.02` in config and in every declared
  matched field; the draft's 0.15 divergence is gone.
* **B3 declared matched fields measured** — all four are measured and emitted; the two that a
  token-matched budget cannot equalise (`verifier_calls_per_accepted_artifact`,
  `human_review_minutes`) are disclosed as `design_deviations`.
* **HF-A2-19-03/19-06/19-07/19-08** — the unquoted `NULL` id is normalised and recorded;
  the guardrail is applied before the primary contrasts; exit codes 0/2/3 reproduce; the CSV
  carries `simulated`/`run_mode`/`harness_sha256` on every row.
* **R2 reproduction** — two fresh runs are byte-identical (CSV) and identical modulo
  `generated_at` (report), and they reproduce the author's pinned design-bound report/CSV.

Open items (therefore `revise`, not `accept`):

* **HF-064-01** — the *registered* node-A2 artifact `evaluation/ablation.csv` still has 23
  columns and **no** simulation/provenance marker (HF-A2-19-01 is closed at the harness output
  level but not at the node pointer).
* **HF-064-02** — the pre-registration still names `artifacts/audit/ablation_harness.py`
  (`ee0d87a14848`, line 172) as *the* harness while the live canonical harness is
  `evaluation/ablation_harness.py` (`0fae94bf0190`); HF-A2-19-02 remains open.
* **HF-064-03 (new)** — `--self-test` is wall-clock-flaky. Its `deterministic_report` check drops
  only the top-level `generated_at`, so the nested `provenance.generated_at` can differ between
  the two compared runs. K6 proves the mechanism deterministically (two in-process runs 1.05 s
  apart differ only there); K7 measured **1 failing run in 40** (and 1 in the review's own 7-run
  sample, 6/7 pass). The author's "self-test 21/21" is a maximum, not a stable fact. Fix: exclude
  `provenance.generated_at` from the comparison key or inject a fixed clock.

Minor findings: the self-test writes fixed-name temp files into the canonical `evaluation/` tree
(K5 proves the write path; not concurrency-safe, crash leaves debris); `spread_fraction` uses
(max−min)/min rather than /mean (stricter, verdict-robust here, but undocumented in the design);
the two unmatched design fields are a design-owner decision, not a harness defect.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-064/a2_harness_review/run_review.py   # exit 0; rewrites report.json + raw/
```

`raw/` holds the fresh dry-run outputs, the 7-run self-test sample, the 40-run flakiness probe,
and the sandbox probe logs.

## Falsifier

Void if live `evaluation/ablation_harness.py` != `0fae94bf0190…`, or a fresh
`--dry-run --design evaluation/ablation_design.yaml` at that hash stops reproducing the author's
pinned design-bound report/CSV modulo `generated_at`, or `budget_check.matched` becomes false, or
the independently recomputed token/wall spreads leave tolerance, or any dry-run row loses its
`simulated`/`run_mode`/`harness_sha256` marker, or `--execute` returns 0, or any pinned input
drifts.

## Limits / non-claims

The synthetic proposers are placeholders: nothing here is evidence about real models, and no
swarm-advantage claim can cite this harness. The statistical model, task suite and power
arithmetic were not re-derived (same scope limit as `reviews/A2-review-19.json`). Workers cannot
set node status, `validation_status=passed`, or any gate verdict; this review is advisory and
wrote only under `artifacts/worker-064/`, `reviews/A2-harness-repair-review-worker-064.json`,
`runtime/state/w064_a2_harness_review_checkpoint.json` and `comms/outbox/worker-064.jsonl`.
