# W067-A2-HF19-ADJUDICATE-01 — independent adjudication of `reviews/A2-review-19.json`

**Worker:** worker-067 · **Node:** A2 · **Gate:** G-AUDIT · **Class:** GLOBAL
(`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`)
**Status:** COMPLETE at worker level (advisory; no node done, no `validation_status=passed`,
no gate verdict). **Canonical writes: 0.**

## What this is

`reviews/A2-review-19.json` (deepseek-flash-19, sha256 `36edeff97014…`) returned three hard
failures against the A2 design `evaluation/ablation_design.yaml#1b2a83ef670b`. This task
re-derived each HF **from the pinned bytes only** with an independently written probe
(`check_a2_hf19.py`), not from the review text and not from the review author's instrument.

| HF | Claim | Adjudication |
|---|---|---|
| HF-A2-19-01 | The node-registered artifact `evaluation/ablation.csv#ee3aa6cb` is an unmarked synthetic dry-run; the design inventory names only `*_dryrun.*` | **CONFIRMED** |
| HF-A2-19-02 | Two byte-different harnesses; ±2% token+wall rule not single-sourced or enforced (0.15 vs 0.02, no wall spread test, 2/4 matched fields unemitted) | **CONFIRMED** |
| HF-A2-19-03 | `- id: NULL` yields `None` under `yaml.safe_load`, so the mandatory control arm is not addressable | **CONFIRMED** |

Secondary probes (moderate findings): A2-19-04 NULL is a declared-rate placeholder in the
design-named harness (`SIM["NULL"] = {p_accept: 0.06, …}`), A2-19-05 the registered NULL run
stopped `episodes_exhausted` at 3000/20000 tokens — both CONFIRMED.

## Key measurements at the pin

- CSV `evaluation/ablation.csv`: 23 columns, **no** machine-readable provenance column; report
  `generator_sha256 = df878e97…` with assignment text `"synthetic dry-run only, no model calls"`;
  design `artifacts.harness = artifacts/audit/ablation_harness.py#ee0d87a1`, inventory names only
  `evaluation/ablation_dryrun.csv#bda738ff`.
- `evaluation/ablation_harness.py#df878e97` `DEFAULTS["token_tolerance"] = 0.15`;
  `artifacts/audit/audit_lib.py#ae573db8` `check_budget_match(tol=0.02)`. The two harnesses differ.
- `check_matched_budgets` (big harness, lines 384–422) computes a spread **only for tokens**; its
  wall lines are per-arm `wall_consumed > wall_budget` overspend and `stop_reason=="wall_clock"`
  confound checks — no max/min wall spread against any tolerance (`wall_spread_lines = []`).
- `matched_fields` = `[total_completion_tokens, wall_clock_s, verifier_calls_per_accepted_artifact,
  human_review_minutes]`; 3 of 4 never appear in any CSV/report output.
- `yaml.safe_load(design)` arm ids: `['S','SC','IC','ICC', None]`.

## Controls (all pass)

- **C1 mutation** — quoting `- id: "NULL"` parses as the string `"NULL"`: the probe is sensitive.
- **C2 provenance detector** — fires on a marked header, silent on an unmarked one.
- **C3 fail-closed drift** — a mutated pin entry reports `match=false` and refuses verdicts.
- **C4 no-write canary** — all 9 pinned canonical inputs byte-identical before/after.

## Falsifier

Withdrawn if any pinned input hash moves, if an independent re-run of `check_a2_hf19.py` does not
reproduce `hard_failure_adjudication`, or if any HF verdict here is shown to bind bytes other than
the pinned ones.

## Files

- `check_a2_hf19.py` — independent read-only probe (fail-closed on drift).
- `report.json` — full measurements, pins before/after, controls, verdicts.
- `README.md` — this note.
- `reviews/A2-hf19-adjudication-worker-067.json` — advisory review of `A2-review-19` (accept of
  its three HFs at the pin), emitted with the comms events.
