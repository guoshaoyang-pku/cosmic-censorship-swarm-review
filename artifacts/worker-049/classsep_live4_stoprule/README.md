# W049-CLASSSEP-LIVE4-STOPRULE-03 — live-detector drift endpoint + adjudication stop-rule determination

**Worker 049, node A1, gate G-AUDIT, classes `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`.**
Read-only evidence packet; no gate verdict, no node status, no `validation_status=passed`.
Companion to `astra-life06-classsep-detector-adjudication` (astra-lead-audit, deadline 02:30).

## Why this exists

That card (issued 2026-09-12T01:00:35+08:00) names exactly three detector hashes
(`a8c04fc31e4a` applied, `c266dbceca87` recovered, `e2d24b927ee8` staged) and carries the
stop rule: *"Stop if the live detector moves again or the recovered c266dbec copy fails hash
verification; record the contest as unresolved rather than shipping a patch."*

## Measured: the live detector moved inside the card window

| time (+08:00) | `research_map/class_separation.py` | evidence |
|---|---|---|
| 01:00:35 | card pins applied = `a8c04fc31e4a` | `comms/inbox/astra-lead-audit.jsonl` card |
| ~01:06–01:08:14 | **`e36b0d644ca7`** (third hash, not in card) | controller blocker `astra-detector-patch-result-0112`; fail-closed pin check of this runner at 01:07 |
| 01:08:14 (mtime) | restored to `a8c04fc31e4a` | `stat`; re-pin + census run at 01:08:38 |
| measurement start = end | `a8c04fc31e4a` | `results.json.stop_rule_determination` |

**Determination: `LIVE_MOVED_AND_REVERTED__INSTRUMENT_UNSTABLE__RECORD_UNRESOLVED`.**
Condition 1 of the stop rule is satisfied (the live path moved after the card). Condition 2 is
not: `artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py`
re-verifies byte-exact at `c266dbceca87` (the rollback path is intact).

## Measured: the drift revision is behaviourally identical to the applied revision

Census on the three pre-registered adversarial corpora (34 genuine C0/C2 merge assertions,
each with a cue-stripped twin; corpus hashes pinned in `pre_registration.json`). Harness
functions imported unmodified from `W049-CLASSSEP-SUCCESSOR-AUDIT-02`
(`run_successor_audit_049.py`). Drift revision measured from an independent hash-verified
pinned copy (`artifacts/worker-045/classsep_e36_arm/pinned/class_separation_e36b0d644ca.py`).

| detector | v1 cueFN | v2 cueFN | v3 cueFN | total cueFN (HIGH) | mention FP v1/v2/v3 | declDiff vs c266 | worker-07 |
|---|---:|---:|---:|---:|---|---:|---|
| `recovered_c266` (baseline) | 0 | 1 | 0 | **1** (1) | 6/4/3 | 0 | 17/0/10/0 PASS |
| `applied_a8c04fc3` (card, live at measure) | 1 | 9 | 0 | **10** (10) | 6/0/2 | 1/13/1 | 17/0/10/0 PASS |
| `staged_e2d24b92` (card) | 0 | 1 | 0 | **1** (1) | 6/4/3 | 0 | 17/0/10/0 PASS |
| `drift_e36b0d644ca7` (was live ~01:06) | 1 | 9 | 0 | **10** (10) | 6/0/2 | 1/13/1 | 17/0/10/0 PASS |

**`e36b0d644ca7` is not a fix and not a regression on this fixture set: every per-fixture flag,
every aggregate, and every declaration-mode diff equals `a8c04fc31e4a`.** It inherits the
standing over-suppression blocker (10/34 cue-carrying genuine assertions cleared, all HIGH
confidence); it does not discharge the worker-098 FP probes either (6 mention FPs remain on v1).

## Falsifier

Re-run `run_live4_audit_049.py` at the pins in `pre_registration.json`: any per-fixture flag or
cue-FN count differing from `results.json`, any panel/corpus hash mismatch, a non-deterministic
double run, or a stop-rule determination not reproducible from the recorded observations
falsifies this packet. The oscillation record is falsified if the live path is shown never to
have held `e36b0d644ca7` after 01:00:35.

## Files

- `results.json` — full per-fixture census, pins, drift check, stop-rule determination
- `pre_registration.json` — endpoint, panel, decision rule (amended once before any census)
- `run_live4_audit_049.py` — runner (fail-closed on pins; double-run deterministic)
- checkpoint: `runtime/state/w049_live4_stoprule_checkpoint.json`
