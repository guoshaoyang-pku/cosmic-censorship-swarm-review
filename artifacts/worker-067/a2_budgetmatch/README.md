# W067-A2-BUDGETMATCH-01 — A2 budget-matching audit at the map pin

Worker-067, one bounded class-bound task (A2 spans `AF-WCC-VAC-GEN`,
`AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`). Read-only on every
canonical path; writes only inside this directory plus one review file.

## Question

At the map-declared A2 pin `evaluation/ablation.csv` (sha256 `ee3aa6cb97d0…`), generated
by `evaluation/ablation_harness.py#df878e97bf6e` from the frozen design
`evaluation/ablation_design.yaml#1b2a83ef670b`: is the reported matched-budget claim
(`budget_check.matched = true`, `primary_comparison_valid = true`) a faithful
implementation of the design's pre-registered matching rule — **tokens and wall-clock
within ±2%** (HF-11)?

Prior state that matters: the only two A2 reviews on disk (`A2-review-022`,
`A2-review-18`) bind the *design* and the older *dry-run* artifacts, not the map pin.
The controller's hash-bound A2 coverage was therefore empty; the map pin had **zero**
hash-bound reviews before this one.

## Result — verdict `REVISE_HF11_AT_PIN`

| check | result |
|---|---|
| T1 CSV ↔ report agreement | PASS — 5 rows × 20 fields, `per_class_coverage` included |
| T2 arithmetic identities | PASS — rates, cost/accept, calls = attempts×samples, per-class n/15 |
| T3 reproduce pinned harness | PASS — in-process re-run equals the report on every leaf except `generated_at`; CLI-equivalent arm runs reproduce the CSV |
| T4 design tolerance conformance | **FAIL (finding)** — pin records `token_tolerance = 0.15`, design pre-registers ±2% (0.02); no design override/reference recorded |
| T5 wall-clock matching test present | **FAIL (finding)** — AST scan of pinned `check_matched_budgets`: no max/min over `wall_consumed`; only overspend and `wall_clock` stop-reason tests |
| T6 `primary_comparison_valid` stability | PASS under the envelope reading; **void under the consumption reading** |
| C1 mutation control | PASS — +100 tokens on one arm is caught by the cost identity |
| C2 tolerance materiality | PASS — a 5% spread passes 0.15 and fails 0.02 |
| C3 fail-closed on drift | PASS — a wrong pin exits 2 before any measurement |
| C4 no-write canary | PASS — all four pinned inputs re-hash identically after the run |

Measured at the pin (four primary arms, all token-budget-limited, identical caps
20 000 tokens / 60 s):

```
tokens consumed  [20000.0, 20000.0, 19800.0, 19840.0]   spread 1.00% of budget
wall consumed    [   30.0,    30.0,   24.75,    24.8 ]   spread 17.5% of max
                                                          (8.75% of the 60 s envelope)
```

## Findings (owner actions, not gate verdicts)

- **F1 / HF-11 (major, open at pin).** The design's H-design pre-registers token *and*
  wall-clock matching at ±2%; the pinned checker tests tokens only. Under the consumption
  reading the design's own falsifier fires (17.5% > 2%) and the pin's
  `primary_comparison_valid = true` is void. Under the envelope reading (identical 60 s
  caps) the clause is satisfied trivially — the design text does not say which is meant.
  Owner: disambiguate the design, then implement the wall-clock test (or drop the
  consumption clause by a versioned design amendment).
- **F2 / HF-11 (major, open at pin).** The pin ran with the harness default
  `token_tolerance = 0.15` (7.5× the pre-registered 2%) and records no design reference.
  The boolean happens to agree (1% passes both), but the recorded check does not
  implement the rule it is cited for. Owner: record `design_ref`/`design_sha256` and run
  at the design tolerance, or amend the design with a reason.
- **F3 / HF-08 (minor, note).** The pin is reproducible from the pinned harness +
  recorded config (T3), but the report itself records no command/exit code.

## Controls

C1 mutation, C2 tolerance materiality, C3 fail-closed pin drift, C4 no-write canary — all
pass. `--report` writes `report.json` here; nothing else is written.

## Falsifier

Withdrawn if any of the four pinned input hashes moves; or a re-run of the pinned harness
does not reproduce the pinned report/CSV; or `check_matched_budgets` is shown (AST or
execution) to test wall-clock consumption spread; or the design text is amended to an
envelope-only reading at a new hash that voids this pin.

## Replay

```bash
cd artifacts/worker-067/a2_budgetmatch
python3 check_a2_budgetmatch.py            # exit 0; rewrites report.json
python3 check_a2_budgetmatch.py --report /tmp/w067_a2.json   # no local write
```

## Authority

Worker-level artifact/checker evidence only. Not a gate verdict, not an A2 node
transition, no canonical-path write, no model call, no numerics work. The design and
harness are owned by the audit lead (`evaluation/ablation_design.yaml`,
`evaluation/ablation_harness.py`); this packet is an independent input to
`astra-life04-verify-a0` / G-AUDIT coverage, nothing more.
