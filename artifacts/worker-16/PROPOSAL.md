# WP16-A1-AUDIT-CALIBRATION — task proposal (unassigned, no completion claimed)

**Worker:** `deepseek-flash-16` · **Node:** A1 (independent review queue) · **Group:** audit
**Status:** proposal-support artifact built and measured; awaiting lead binding or redirect.
**Class IDs in scope:** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`,
`AF-WCC-SCALAR-SPH` (the calibration targets the C0/C2 separation rule that keeps these distinct).

## Why this task

`research_map/audit_evidence.py` is the executable A1 gate: it is what turns the map's
done-node artifact rule, the numerics lock, and the class-separation rule into signals Astra
can act on. A gate with unmeasured false positives burns lead attention; a gate with unmeasured
false negatives gives false assurance. Nobody had a labeled corpus for it (worker-07's planned
mutation testing targets escaped *mutations*; this corpus targets expected/observed signal
equality, including the live map's coverage). Measured at the pinned revision:
**FP=0, FN=3, plus one input-representation gap** (`RESULTS.md`).

## Deliverable (already produced as proposal support)

- `artifacts/worker-16/audit_calibration/run_calibration.py` — deterministic harness, exit 1 on mismatch.
- `artifacts/worker-16/audit_calibration/expected.json` — 10 labeled fixtures with rationales.
- `artifacts/worker-16/audit_calibration/fixtures/` — synthetic maps `fx0`–`fx8` (+ fixture artifacts).
- `artifacts/worker-16/audit_calibration/calibration_report.json` — frozen report, detector sha256 pinned.
- `artifacts/worker-16/audit_calibration/RESULTS.md` — findings F1–F3 and coverage gap C1.

## Acceptance tests

| id | test | threshold |
|---|---|---|
| AT1 | two runs identical modulo `checked_at` | byte-identical after field removal |
| AT2 | no fixture crashes the detector | 10/10 return hard/soft lists |
| AT3 | scoring is signature-based against `expected.json` | TP/TN/FP/FN computed, raw messages retained |
| AT4 | detector revision pinned | report contains `detector_sha256` |
| AT5 | live-map coverage red-team | report contains `coverage.live_map` with `sections_with_inputs` |
| AT6 | after a lead-approved detector fix, harness exits 0 | all 10 fixtures MATCH |

## Expected information gain

Medium-high. The numerics lock releases on `G-FORM`/`G-AUDIT`; if a failed required gate is
invisible (F1) or class ids are not whitelisted (F2), the lock and the class-separation rule can
be satisfied by malformed map data. C1 says class binding is currently unrepresentable in the
map, which affects every class-bound node (F1, F2, L1).

## Budget / stop rule

Requested: 1.0 agent-hour, already largely spent (≈0.4 h at checkpoint 1). Stop when:
(a) the harness exits 0 against a lead-approved detector revision and the fix is recorded with a
reviewer verdict, or (b) lead-audit rejects F1–F3 and the corpus is retained as a regression guard,
or (c) a different class-bound assignment preempts this one.

## Next falsifier

Re-run `run_calibration.py` against any new `audit_evidence.py` revision. The finding set is
falsified if the three FNs (fx2, fx3, fx7) disappear without weakening any of the five quiet
controls or the two positive controls (fx4, fx8). A single unexpected hard signal on a quiet
control is a false positive and blocks the fix.
