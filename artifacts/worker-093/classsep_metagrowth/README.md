# W093-CLASSSEP-METAGROWTH-01 — the class-separation hard list grows with the audit, not with class leakage

**Worker:** `worker-093` · **Node:** `A1` · **Gate:** `G-AUDIT` ·
**Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (the C0/C2 composite route) ·
**Created:** 2026-09-12T00:57+08:00 · **Verdict:** `PASS` (11/11 pre-registered checks)

**Question.** The controller's CLASSSEP hard-failure list went from **10** entries at pass-04
(`lifecycle_20260912-003718.json`, map `3d45be59`) to **17** at pass-05
(`lifecycle_20260912-004308.json`, map `11311ab3`). Is that growth first-order class-leakage
assertion, formulation-context mention, or the swarm's own verification prose?

**Answer measured at the pinned bytes.** All 7 new entries come from three claims ingested
*after* the CF-16 false-positive adjudication — `claims[180]` (worker-044), `claims[187]`
(worker-085), `claims[192]` (worker-035) — which quote or describe the detector's own output.
Under the pre-registered rule, **0 of 17 findings is an assertion that C0 and C2 are one class**,
and **7/7 of the growth is audit-apparatus (META) prose**. Quoting a canonical CLASSSEP finding
string inside a claim is sufficient to mint a new hard entry (self-reproduction control). The
hard count is therefore **monotone in verification traffic, not in class leakage**.

## Result table

| # | check | result |
|---|---|---|
| E1a | pass-05 canonical findings == pass-05 lifecycle CLASSSEP list (17) | PASS |
| E1b | pass-04 canonical findings == pass-04 lifecycle CLASSSEP list (10) | PASS |
| E1c | span-carrying re-implementation reproduces the canonical list exactly | PASS |
| E2 | delta == exactly 7 findings rooted at claims 180, 187, 192; nothing removed | PASS |
| E3 | `ASSERTION = 0` across all 17 findings | PASS |
| E4 | delta labels: `META = 7`, `ASSERTION = 0` | PASS |
| E5 | 14 labeled controls (4 META / 6 mention / 4 assertion-shaped) classify as labeled | PASS |
| E6 | external agreement: 10/10 findings adjudicated `NON_ASSERTIVE` by worker-035 are non-`ASSERTION`; statement hashes match | PASS |
| E7 | self-reproduction: a synthetic claim quoting the claims[36] finding is itself flagged | PASS |
| E8 | self-application: the statement this task emits as its own `claim` is flagged — **3 predicted new hard entries** | PASS |
| E9 | no pinned input drifted during the run | PASS |

Growth: pass-04 = 10, pass-05 = 17, added = 7 (`claims[180]`×1, `claims[187]`×1, `claims[192]`×5),
removed = 0, `META` share of the delta = **1.0**.

## Method (read-only; no canonical file written)

Frozen pins (all hashed before the run; drift fails closed):
detector `research_map/class_separation.py` `c266dbceca87…`, pass-05 map `11311ab3…`, pass-04 map
`3d45be59…` (origin: worker-035's snapshot), pass-04/pass-05 lifecycle reports
`dae3e6fbda02…` / `2aa847cc2865…`, worker-035 adjudication report `47f0c15834e6…`.

Findings are enumerated by a span-carrying re-implementation that must reproduce
`class_separation.findings_for_map(map)` exactly (E1c). Each finding's trigger (the `_MERGE_PAT`
match), its detector ±60-char window, and its clause are recovered; the claim statement is then
labeled by the rule pre-registered in `PREREGISTRATION.md` **before any live claim was
classified**:

1. **META** — statement contains audit/apparatus vocabulary (`CLASSSEP`, `class_separation`,
   detector, checker, audit, false positive, hard failure, regex, `findings_for_map`, regression
   corpus, flag, scan);
2. **MENTION** — otherwise, the trigger occurrence is quoted / negated / a case label / separated
   from the merge word by a clause boundary;
3. **ASSERTION** — otherwise: a first-order statement that C0 and C2 are one class.

`ASSERTION` is the only label that should be a hard class-separation failure. 14 labeled controls
(E5) and the independent worker-035 adjudication of the original 10 (E6) anchor the rule.

## What this means for G-AUDIT

The audit pipeline routes *every* non-`CLASSSEP-SOFT:` finding to `hard`
(`research_map/audit_evidence.py:106-108`) and scans claim `statement` text in prose mode with no
quotation/metalinguistic channel. Claims whose subject *is* the audit therefore feed the gate's
hard count: worker-085's and worker-035's own verification reports became entries 11–17, and this
task's own claim is predicted to add three more (`E8`). A bare CLASSSEP hard count is not a
measure of class leakage and cannot converge to zero while verification traffic continues. The
detector owner (CF-4: only the audit lead/controller applies checker changes) has the measured
basis for routing quoted/meta occurrences to a soft channel; this task proposes no rule edit.

## Limitations (stated, not hidden)

- The pre-registered META marker test is deliberately broad and, at statement scope, labels all
  17 findings META (these claims are all measurement reports). The decisive, pre-registered
  claims are only **E3/E4: 0 first-order assertions and 7/7 non-assertion growth**.
- A secondary, non-pre-registered window-scope diagnostic (marker must sit inside the detector's
  own ±60-char window) splits the 17 as META 6 / MENTION 10 / ASSERTION 1. The single ASSERTION
  flag is `claims[187]`, whose trigger sits inside a straight-quote span (`'... merged C0/C2 ...'`)
  and is therefore a quoted mention; the diagnostic's clause split at the ellipsis inside the
  quotation. Recorded as an observation in `report.json`; the pre-registered result stands.
- `claims[180]`, `[187]`, `[192]` have not been independently adjudicated by another worker; this
  report is the first measurement of them (worker-021 and worker-035 adjudicated the original 10).
- Pass-05 is a frozen snapshot. The live map has continued to move; E9 records the live hash at
  read and drift is reported, never hidden.

## Run history (instrument fixes only; no rule or expectation was changed)

1. First run: E6 FAIL — worker-035 has two adjudications at `claim_index 112` and the harness
   keyed them by claim index (9 rows). Fixed by pairing on the exact canonical finding string.
2. Second run: the window-scope diagnostic fell back to the statement-scope label, so its split
   was uninformative. Fixed to re-evaluate the marker inside the window.
3. Final run: 11/11 PASS. Neither fix touched the pre-registered rule, the expectations E1–E9,
   the fixtures, or the detector under test.

## Artifacts

| path | role |
|---|---|
| `verify_metagrowth.py` | instrument (read-only, fail-closed, exit 0 iff 11/11) |
| `report.json` | machine evidence: pins, 11 checks, per-finding labels with clause text, growth, observation |
| `PREREGISTRATION.md` | rule + expectations E1–E8, frozen before the run (one amendment, timestamped, pre-run) |
| `preregistered_fixtures.jsonl` | 14 labeled controls |
| `self_claim_statement.txt` | the exact statement emitted as this task's own `claim` (E8) |
| `pinned/`, `snapshot/` | frozen inputs with declared origins |
| `manifest.json` | per-artifact sha256 |

## Falsifier

FALSIFIED if any of E1–E9 fails, if any of the 17 findings is independently a first-order
assertion that C0 and C2 are one class, if a pinned input drifts, or if the span enumeration does
not reproduce the canonical list. A detector-rule edit after seeing these results voids the run.

## Non-claims

No canonical file was modified. No gate verdict, node status, `validation_status=passed`, theorem,
counterexample or numerical result is claimed. The META/MENTION/ASSERTION labels are this
instrument's pre-registered rule, reported with the clause text, not a substitute for the audit
lead's adjudication.

**Reproduce:** `python3 artifacts/worker-093/classsep_metagrowth/verify_metagrowth.py`
