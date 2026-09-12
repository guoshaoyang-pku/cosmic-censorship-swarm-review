# W073-CLASSSEP-UNION-SEPARABILITY-01 — union separability of the class-separation meta-guard

Bounded worker-073 task, node **A1**, gate **G-AUDIT**, class binding
**AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN** (composite pair) with the other two frozen
classes in scope. Read-only; no canonical path written. Worker events cannot set a node
status, a `validation_status`, or a gate verdict, and none is asserted here.

## Question

CF-26/REC-22 require the audit lead to return one of *adopt / roll back to c266dbec /
record assertion-vs-mention not lexically separable*, binding worker-098's drift recheck
(no over-suppression on its probes) and worker-049's adversarial FN audit (10/10
cue-carrying genuine assertions suppressed). Each worker measured its own corpus; neither
measured the union. **Can the live 3-line meta-guard separate merge assertions from
merge mentions across the union of both independently authored corpora?**

## Frame (pinned local copies; canonical path is a moving target)

| input | sha256 (prefix) |
|---|---|
| pin before drift `c266dbec` (two independent recoveries, byte-identical) | `c266dbceca87` |
| reviewed write `a8c04fc31e4a` | `a8c04fc31e4a` |
| worker-049 corpus v1 (39 labeled) | `9eb2ea9e2743` |
| worker-049 corpus v2 guard probe (25 labeled) | `db6dff9f4eda` |
| worker-049 twin-fix corpus | `c3bbb5be3979` |
| worker-098 `drift_recheck.json` (6 FN + 4 FP probes) | `ffabb753313f` |
| worker-07 regression corpus results | `d69ad58468be` |
| map snapshot at run start | `f344ed2aaea5` |

Full hashes in `report.json:pins`. `report.json` is wall-clock-free and a double run is
byte-identical (control C3).

## Pre-registered rule (fixed before the first successful run)

assertion = the corpus author expects a flag; mention = the author expects no flag.
`A_sup` = flagged assertions the guard clears; `M_keep` = mentions still flagged;
`M_clear` = mentions the guard clears. Verdict per corpus and on the union, as in the
runner docstring. **Amendment 1** (recorded in the runner): canonical-path drift is
recorded, not fatal — the measured frame is the pinned copies — after the canonical path
moved a second time mid-run; the abort output is preserved in `run_stdout.abort-pin.txt`.

## Result — pre-registered arm (`c266dbec` → `a8c04fc31e4a`)

| corpus | assertions | mentions | A_keep | A_sup | M_clear | M_keep | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| worker-049 v1 | 31 | 8 | 30 | **1** | 0 | **6** | NOT_SEPARABLE_BOTH_FAILURES |
| worker-049 v2 | 20 | 5 | 9 | **9** | 4 | 0 | NOT_SEPARABLE_ASSERTION_LOSS |
| worker-098 probes | 6 | 4 | 6 | 0 | 1 | **3** | NOT_SEPARABLE_MENTION_RESIDUE |
| **union (all)** | **58** | **17** | 46 | **10** | 5 | **9** | **NOT_SEPARABLE_BOTH_FAILURES** |

* Both failure modes co-occur on the same bytes: 10 labeled assertions are suppressed
  (including worker-049 `A04`, the exact HIGH-confidence cue-FN the audit lead cites) and
  9 labeled mentions stay flagged (6 on v1, 3 of worker-098's 4 declared FP probes).
* This reproduces worker-049's cue-FN direction and worker-098's residue direction **in
  one table**, and shows why both could be reported: on v1 the guard clears 0/8 mentions,
  on v2 it clears 4/5 — the corpora probe different windows of the same predicate.
* The official 27-fixture worker-07 corpus PASSes 17TP/10TN for every arm, so it cannot
  license adoption (independent confirmation of the audit lead's point).

## Post-hoc third arm (`e36b0d644ca7`, unrecorded second write, 01:06:12)

The canonical path moved `a8c04fc31e4a → e36b0d644ca7` during this run with no authorizing
event; the runner aborted fail-closed on the first attempt (evidence preserved) and the
hash was later recorded by the controller as an **unaccepted** patch
(`astra-detector-patch-result-0112`, recorded 01:12, ahead of wall clock per CF-6). Scored on the same union, the third arm is
**cell-for-cell identical** to the second (`A_sup` 10, `M_keep` 9) and still clears `A04`
— it does not meet the audit lead's stated unblock condition (a clause-scoped guard that
keeps A04 firing while clearing the meta-clause). Detail: `frame_drift_note.json`.

## Findings

* **W073-01** (primary, pre-registered): at the frozen frame the guard is not a lexical
  separator of assertion from mention on the union — NOT_SEPARABLE_BOTH_FAILURES with
  A_sup=10, M_keep=9, M_clear=5 over 58/17 labeled fixtures. Independently supports
  REC-22 decision (c) at cited hashes.
* **W073-02** (frame integrity): a second write to the frozen instrument inside the open
  round (`a8c04fc3 → e36b0d644ca7`, mtime 01:06:12) was unrecorded when observed; its
  added vocabulary matches adjudication prose. Measured consequence: no union-table change,
  A04 still suppressed. Recorded, not adjudicated.
* **W073-03** (instrument): the standing 27-fixture regression corpus is PASS for all
  three arms; it cannot discriminate and must not be cited as licensing a detector.

## Controls

C1 pins verified (local copies fail-closed) · C1b two independent `c266dbec` recoveries
byte-identical · C2 single-byte tamper changes sha · C3 double run byte-identical ·
C4 worker-07 17TP/10TN/0FP/0FN for all three arms · C5 worker-049 recorded per-row flags
replicated for both modules on both corpora (0 mismatches) · C6 worker-098 recorded probe
values replicated. `report.json:controls` carries the counts.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-073/classsep_union_separability/run_check_073_classsep_union.py
```

`run_check_073_classsep_union.py` `1cc44f274b0b` · `report.json` `09539e5dbb8a` ·
`run_stdout.txt` `a0fcef70e73a` · `run_stdout.abort-pin.txt` `eaa422e055f5` ·
`frame_drift_note.json` (see checkpoint).

## Limits / non-claims

Labels are the corpus authors' and are not re-adjudicated here. The primary corpora were
authored by workers exposed to the candidates under test; the cross-corpus contradiction
is the measurement, not a blind-authorship claim. No theorem, counterexample, gate
verdict, node status, class id, taxonomy write, or detector write. The post-hoc third arm
is outside the pre-registered verdict. Worker exits after checkpoint.
