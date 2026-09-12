# W093-CF16-CALIBRATION-01 — case-label calibration for the CLASSSEP hard failure

**Worker:** `worker-093` · **Node:** `A1` · **Classes:** `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
**Generated:** 2026-09-12T00:28:47+08:00 (file write time; machine output `report.json` 00:28:19) · **Verdict:** `PASS` (6/6 checks)
**Harness:** `verify_calibration.py` · **Machine output:** `report.json` · **Patch:** `proposed_patch.diff`

## What was asked

The controller's lifecycle-03 close (`lifecycle_20260912-002155.json`) records exactly one
`evidence_hard_failures` entry: a `CLASSSEP: composite C0/C2 asserted as one class` finding on
`claims[36].statement`. CF-16 adjudicated it a checker false positive — the statement names the
taxonomy corpus case `TC-F0-N14 C0/C2 merge`, it does not assert that C0 and C2 are one class —
but the raw count stays "until the author rephrases or the checker is calibrated" (ASTRA handoff).
This task takes the second route: **can the checker be calibrated so the false positive clears
without losing a single true positive?**

Answer measured here: **yes**, with a minimal, case-label-scoped rule.

## The calibration

A merge word is read as a **case-label mention** (not a violation) iff all three hold:

1. the matched merge word is exactly a label noun (`merge|merger|case|fixture|row|label|name|test|…`);
2. it is not predicated — no `is/are/means/adopt/require/…` follows it within two words
   (`"TC-F0-N14 C0/C2 merge is the design we adopt"` therefore **still flags**);
3. the composite sits in a case-label context — a `TC-/FX-/CASE-/ROW-/FIXTURE-` id adjacent before it,
   or a parenthesised list carrying such an id
   (`"(TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge)"`).

A finding is suppressed only when **every** merge word in the ±60-char window is such a mention;
one genuine assertion anywhere in the window keeps the violation. Declaration-mode scanning
(`class_id`, `label`, `conclusion`, …) is untouched, and `_class_tokens` is untouched.

## What was measured (read-only; no canonical file modified)

| check | question | result |
|---|---|---|
| B1 | does the pinned canonical checker reproduce the CF-16 finding on the pinned `claims[36]` statement, and does the calibrated module clear it? | **PASS** — canonical 1 finding (`asserted as one class`), calibrated 0 |
| B2 | worker-07's 27-fixture falsification corpus, canonical vs calibrated | **PASS** — both 17 leaks / 0 missed / 10 controls / 0 spurious, per-fixture classification identical |
| B3 | 16 labeled fixtures (6 positive, 4 calibration-negative, 5 standing-negative, 1 conservative residual) | **PASS** — every expectation met |
| B4 | `_class_tokens` output on 23 probes incl. 3-, 4-, 5-group and unknown tokens | **PASS** — byte-identical to canonical |
| B5 | live `research_map.json` scanned by both modules in one run | **PASS** — canonical 1 finding, calibrated 0; removed set is exactly the `claims[36]` finding, added set empty |
| B6 | `proposed_patch.diff` applies cleanly to the pinned canonical bytes, reproduces the calibrated module, and composes with worker-027's token-arity patch in either order | **PASS** — both hunks are pure insertions (no old lines rewritten, so disjoint from worker-027's rewritten line 67); composed file = calibrated + token patch |

The two known calibration-negative contexts in `claims[36]` are the parenthetical list
(`M-N02`) and the exact statement (`M-N01`). `M-R01` (`"… merge is a case label, not an
assertion."`) is deliberately **still flagged**: distinguishing a metalinguistic predicate
complement from an assertive one needs semantics this rule does not have, so the calibration errs
conservative. This is a bounded relaxation, stated in the falsifier, not a claim of general
mention detection.

## Pinned inputs

| path | sha256 (16) |
|---|---|
| `research_map/class_separation.py` (pinned copy `pinned/class_separation.c266dbce.py`) | `c266dbceca87fb99` |
| `artifacts/worker-093/cf16_calibration/calibrated_class_separation.py` | `ff58563386cf398a` |
| `artifacts/worker-093/cf16_calibration/proposed_patch.diff` | `c2a0f13fbd4417a0` |
| `pinned/claims36_snapshot.json` (statement sha) | `026cfccbd8f1c20a` |
| `artifacts/worker-07/class_separation_falsification/results.json` | `d69ad58468be1665` |
| live `research_map/research_map.json` at read | `4fd40d4d1e4fc360` |

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-093/cf16_calibration/verify_calibration.py    # exit 0 iff all 6 checks pass
```

## Falsifier

Re-run at the pinned checker sha `c266dbce`. FALSIFIED if: (a) calibrated still flags the pinned
`claims[36]` statement; (b) it clears any labeled positive `M-P01..M-P06` or any predicated control
`M-P03`/`M-P04`; (c) any cell of the worker-07 score moves off 17/0/10/0 or any fixture changes
class; (d) `_class_tokens` changes on any probe; (e) a same-run live-map scan removes any finding
other than the `claims[36]` one or adds one; (f) the patch does not apply to the pinned bytes, does
not reproduce the calibrated module, or stops composing with worker-027's patch.

## Scope limits (what this does NOT say)

- The patch is a **proposal**; no canonical file was edited. Only the controller / formulation or
  audit lead may apply it or accept the rephrase alternative.
- No gate verdict, no `status=done`, no `validation_status=passed`, and the evidence hard-failure
  count is unchanged until the patch is applied or the claim rephrased.
- The calibration is scoped to case-label mentions of the C0/C2 composite. Other metalinguistic
  shapes (e.g. `M-R01`) remain flagged on purpose.
- The map moves: B5 binds the map hash read in the same run (`4fd40d4d…`); a later rephrase of
  `claims[36]` makes that check vacuous, not false — re-run and re-pin.
