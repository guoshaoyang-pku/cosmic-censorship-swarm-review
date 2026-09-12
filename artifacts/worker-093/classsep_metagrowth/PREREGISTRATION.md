# W093-CLASSSEP-METAGROWTH-01 — pre-registration (written before any live-claim classification)

**Worker:** `worker-093` · **Node:** `A1` · **Gate:** `G-AUDIT` ·
**Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (the C0/C2 composite route) ·
**Created:** 2026-09-12T00:50+08:00

**Question.** Between controller pass-04 (`lifecycle_20260912-003718.json`, 10 CLASSSEP hard
failures, map `3d45be59`) and pass-05 (`lifecycle_20260912-004308.json`, 17 CLASSSEP hard
failures, map `11311ab3`), the audit's class-separation hard list grew by 7. Is the growth
first-order class-leakage assertion, formulation-context mention, or meta-traffic about the
audit itself?

## Frozen inputs (hashed before the run; drift at read = fail closed)

| input | sha256 | role |
|---|---|---|
| `research_map/class_separation.py` (`pinned/class_separation.c266dbce.py`) | `c266dbceca87fb99…` | detector under test |
| `research_map/research_map.json` (`snapshot/map.pass05.json`) | `11311ab3600514c…` | pass-05 map |
| pass-04 map (`pinned/map.pass04.worker-035.json`, origin worker-035 snapshot) | `3d45be5969ec388e…` | pass-04 map |
| `runtime/state/controller_verification/lifecycle_20260912-003718.json` | `dae3e6fbda02…` | pass-04 hard list |
| `runtime/state/controller_verification/lifecycle_20260912-004308.json` | `2aa847cc2865…` | pass-05 hard list |
| `artifacts/worker-035/classsep_hardfail_adjudication/report.json` | `47f0c15834e6…` | external adjudication of the 10 |

## Classification rule (fixed now; no edits after results are seen)

Findings are enumerated by a re-implementation that must reproduce the canonical
`findings_for_map(map)` claim-surface list exactly (equivalence control). For each finding the
trigger occurrence is the `_MERGE_PAT` match in the claim statement, the window is the detector's
own ±60 characters, and the clause is the text between the nearest `; . ! ? — \n` boundary before
the trigger and the nearest such boundary after the trigger.

Labels, first match wins:

1. **META** — the *claim statement* (not only the clause) matches `CLASSSEP |
   class[_\s-]?separation | detector | checker | audit | false positive | hard[_\s-]?failure |
   regex | findings_for_map | regression corpus | flag(s|ged) | scan(s|ned)`.

   *Amendment 2026-09-12T00:52+08:00, before any live-claim classification was executed:* the
   marker test was widened from "the ±60-char clause" to "the claim statement", because in
   claim 192 the apparatus marker sits in the same statement but outside the detector's window.
   Wording and expectations E1–E8 are otherwise unchanged. No live-claim label had been computed
   at the time of this amendment.
2. **QUOTED** — trigger lies inside an unclosed straight-quote span of the clause.
3. **NEGATED** — clause matches `\b(no|not|never|without|zero|absent|nor)\b | non- | rather than |
   instead of`.
4. **CASE_LABEL** — a `TC-|FX-|CASE-|ROW-|FIXTURE-` id appears in the clause before the trigger.
5. **CROSS_CLAUSE** — a clause boundary lies between the `_MERGE_ASSERT` match that fired the
   finding and the trigger.
6. **ASSERTION** — none of the above: a first-order statement that C0 and C2 are one class.

`ASSERTION` is the only label that should be a hard class-separation failure.

## Pre-registered expectations

- **E1** pass-05 CLASSSEP hard set == the 17 CLASSSEP entries in the pass-05 lifecycle list;
  pass-04 == the 10 in the pass-04 list.
- **E2** delta pass-04 → pass-05 has exactly 7 findings, rooted at claims `180`, `187`, `192`.
- **E3** among all 17 findings: `ASSERTION = 0`.
- **E4** among the 7 delta findings: `META = 7`, `ASSERTION = 0`.
- **E5** labeled controls (14: 4 META, 4 ASSERTION, 6 mention-shaped) classify exactly as
  labeled; any mismatch fails the run.
- **E6** external agreement: all 10 findings adjudicated `NON_ASSERTIVE` by worker-035 are
  non-`ASSERTION` under this rule (10/10).
- **E7** self-reproduction: a synthetic claim that quotes a canonical CLASSSEP finding string is
  itself flagged by the canonical detector (≥1 finding), so quoting the audit output mints a new
  hard entry.
- **E8** self-application: the exact statement this task will emit as its own `claim` event
  (stored now in `self_claim_statement.txt`) is flagged by the canonical detector (≥1 finding);
  the measured count is recorded as a prediction, not hidden.

## Falsifier

FALSIFIED if E1–E8 do not hold, or if any of the 17 findings is independently a first-order
assertion that C0 and C2 are one class, or if any pinned input drifts during the run, or if the
enumeration does not reproduce the canonical claim list. A detector-rule change after seeing
these results would void the run.

## Stop rule

One run of the harness; no rule edits after results; no canonical file written; worker-level
evidence only — no gate verdict, no node completion, no detector edit.
