# Enforced metrics — definitions and current values

Owner: lead-audit. Machine implementation: `artifacts/audit/audit_lib.py`, run by
`artifacts/audit/audit_run.py`. Rubric: `evaluation_rubric.yaml` (A0). Values below are from
checkpoint 2 (23:35); every number is reproducible from the named report.

## 1. Class binding

**Definition.** A claim is class-bound iff it carries exactly one `class_id` from the frozen
registry {AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH}, its
conclusion type is admissible for that class, its evidence does not import a different matter
model / Λ / dimension / symmetry / formulation without a `transfer_argument`, and it carries a
falsifier. Process scope (`GLOBAL`) is allowed only on audit/process nodes for non-mathematical
conclusions.

**Current value.** 3 critical violations, all in the ledger: invented class tokens
`AF-SCC-OTHER-MODELS` (50 entries), `AF-WCC-VAC-BH-FORM` (8), `AF-WCC-VAC-NS-CONSTR` (8).
Formulation claims: 0 class-binding violations after false-positive adjudication.
Evidence: `artifacts/audit/reports/LATEST.json`.

## 2. Citation support

**Definition.** Σ weight(status)/n with verified_primary = 1.0, verified_secondary = 0.5,
partial = 0.25, unresolved = 0, contradicted = −1 (floored at 0). Ledger spellings are
normalised (`verified-primary` → 1.0, `verified-api` → 0.5 because an API metadata check is not
a scope check). A claim citing a contradicted or unresolved source is a critical failure.

**Current value.** n = 152, score = 0.592. The deficit is entirely `verified-api` weighting and
missing scope metadata, not bad entries: an independent 8-of-152 re-fetch by lead-audit found
8/8 titles, authors, years and abstract quotes exact
(`artifacts/audit/reports/citation_spotcheck.json`). Required for G-LIT: `source_meta`
(matter_model, cosmological_constant, dimension, symmetry, formulation) on every entry; 119
entries currently lack it (`artifacts/audit/reports/ledger_audit.json`).

## 3. Hard failures

**Definition.** 14 binary defects HF-01..HF-14 (`evaluation_rubric.yaml`), each with a detector.
Any critical HF blocks acceptance regardless of other merits. Rate = affected records / reviewed
records.

**Current value.** 30 violations, 11 critical: HF-14 self-certified acceptance (8 ledger files,
96+ records), HF-02 invented class tokens (3 aggregated), HF-03 missing scope metadata (9 files),
HF-13 contamination (9, adjudicated mostly guard lists/fixtures), HF-06 (1).
Formulation artifacts: F0 1 major, F1 2, F2a 0 (accept), F2b 2, N0 1.

## 4. Duplication and effective sample size

**Definition.** Duplication = 1 − mean pairwise novelty, novelty = 1 − max 5-gram Jaccard against
any other accepted text; duplicate pairs reported at ≥ 0.60. Reviewer independence is reported as
Kish ESS = (Σw)²/Σw² over distinct reviewer templates/authors, never nominal n.

**Current values.**
- Claims: 12 current claims, duplicate cluster rate 0.0, mean novelty 0.988.
- Ledger: ≥ 8 duplicate title pairs across the five ledger files (`W07-SRC-01`≡`SRC-014`,
  `W07-SRC-02`≡`SRC-041`≡`SRC-054`, …): duplication is a ledger-merge defect, not a content defect.
- Independent class-binding checkers: 4 scored, nominal 4, **Kish ESS 4.0** on verdict vectors —
  but cross-acceptance shows the disagreement is layout-driven, so ESS ≈ number of distinct
  artifact schemas (4), not number of independent semantic checks.
- Reviewers per target: lead-audit + one worker = 2 distinct templates (ESS 2); for F2a there are
  three (lead-audit, flash-15, flash-18), ESS 3.

## 5. Information gain

**Definition.** IG = H_before − H_after over class-status entropy (weights: open 4, conditional 2,
refuted-candidate 1, refuted/settled 0), counted only for gate-accepted artifacts; cost-normalised
per 10³ tokens and per agent-hour. Report IG as a vector over classes, not a single score.

**Current values (measured, not modelled).** The four classes all remain unresolved at the class
level: class-status IG = 0.0 bits. The run's realised gain is process IG, reported explicitly:
- locations of gate-blocking defects: 5 (data-class split, F2a conclusion vocabulary, F1/F0
  conclusion divergence, invented class tokens, self-certified ledger acceptance);
- findings resolved by revision during the run: 5 of 8 lead-audit findings on F0/F2a/F2b;
- review agreement: 3 targets independently returned revise/3.0 by worker reviewers;
- A2 design unblocked to the point where one missing config is the only blocker.
This is the honest accounting: no class-status entropy was consumed, because no class claim was
accepted or refuted.

**Per-class literature coverage (self-assessed by the literature group, `ledger/class_coverage.csv`).**
77 sources × 4 classes = 308 assessments: AF-SCC-C0 covered 13 / partial 13; AF-SCC-C2 covered 6 /
partial 13; AF-WCC-SCALAR-SPH covered 9 / partial 6; AF-WCC-VAC-GEN covered 8 / partial 11; the rest
`none` or `unassessed`. This is a coverage *claim*, not verified coverage: without `source_meta`
scope fields it cannot be checked mechanically, so by the rubric it counts as expected IG only.

## 6. Gates

| Gate | Verdict | Deciding measurement |
|---|---|---|
| G-F0 | fail | F0 rev3 fixes HF-02; HF-06 open (descriptor-level disjointness, re-review pending) |
| G-FORM | fail | F2a accept (conditional); F1 revise; F2b revise; no frozen data class; gate tooling unusable (ESS/layout) |
| G-LIT | fail | 119 missing scope metadata; 96+ self-certified records; invented class tokens; duplicate ledger files |
| G-AUDIT | pending | A0 rubric written and self-tested; A1 queue has lead-audit verdicts; second verdicts arriving |
| G-NUM | pending | N0 passes order/invariant/control checks at 3 resolutions; 4th resolution + F0 re-bind needed |

## 7. Reproduction

```bash
python3 artifacts/audit/audit_run.py                 # refresh LATEST.json + LATEST.md, emit events
python3 artifacts/audit/checker_agreement.py         # checker cross-acceptance, kappa, ESS
python3 artifacts/audit/track_revisions.py           # stale-review detection against pins
python3 artifacts/audit/ablation_harness.py --dry-run
python3 artifacts/audit/checkpoint_loop.sh 15 900    # 15-minute checkpoints (already running)
```
