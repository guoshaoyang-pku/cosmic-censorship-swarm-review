# W024-CLASSSEP-RUNNER-VACUITY-01 — class-separation gate runner fails open on an incomplete corpus

| field | value |
|---|---|
| worker / node / gate | `worker-024` / `A1` / `G-AUDIT` |
| classes bound | `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH` |
| instrument audited | `runtime/bin/classsep_regression.py` (sha256 `9f1cf9c3…`) |
| detector under it | `research_map/class_separation.py` (sha256 `c266dbce…`) |
| ground truth | `artifacts/worker-07/class_separation_falsification/results.json` (sha256 `d69ad584…`) |
| verdict | **`FAIL_OPEN_ON_EMPTY_OR_TRUNCATED_CORPUS`** (instrument-level) |
| authority | no gate verdict, no `status=done`, no `validation_status=passed` |

## Why this instrument

Controller finding CF-3 froze the class-separation regression — "17/17 leaks + 10/10 controls,
0 FP/FN" — as the standing evidence that the four frozen classes stay separated. The runner's
PASS condition is `fn == 0 and fp == 0` over whatever fixtures it could read. This audit asks the
null question the runner does not ask itself: **can it certify a corpus it did not actually
read?**

## Method

`drive_vacuity.py` copies the pinned runner and detector byte-identically into six sandboxes
(`sandbox/cases/<case>/`) with the exact layout the runner expects, then executes the runner as
a subprocess and records exit code + stdout in `logs/`. It also calls the detector's module-level
`regression(corpus_dir=…)` through an isolated import. It then applies `proposed_patch.diff` to
copies under `sandbox/patched/` and re-runs every case.

| case | corpus state | unpatched runner | patched runner |
|---|---|---|---|
| `T0_real` | untouched 27-fixture corpus | **PASS**, 17/17 leaks, 10/10 controls, exit 0 | **PASS**, same counts, exit 0 |
| `T1_empty_list` | summary intact, `fixtures: []` | **PASS**, 0/0 and 0/0, exit 0 | exit 1, 3 REASONs |
| `T2_missing_paths` | 27 listed, every path unreachable | **PASS**, 27 `MISSING` rows, 0/0 and 0/0, exit 0 | exit 1, missing-file REASON |
| `T3_leaks_dropped` | 17 leak fixtures removed from the list | **PASS**, 10/10 controls, exit 0 | exit 1, size + leak-count REASONs |
| `T4_truth_flipped` | all 27 labels set `is_class_merge=False` | exit 1 incidentally (17 FP) | exit 1 with count REASONs |
| `T5_partial_missing` | 3 control files deleted, list untouched | exit 1 incidentally (1 FN via `L16`) | exit 1, missing-file + count REASONs |

`T0` is the positive control: the standing evidence reproduces exactly as CF-3 reports it.
`T1`–`T3` are the finding: an empty, unreachable, or leak-truncated corpus is still certified
PASS with exit 0. `T4`/`T5` are recorded as *incidental* detections — the runner exits 1 only
because detector output disagreed with the damaged corpus, not because it asserted corpus
integrity; it still cannot say that fixtures are missing.

## Mechanism

The runner never compares scored counts against `results.json.summary`
(`fixtures_total=27`, `leaks_total=17`, `controls_total=10`), records `MISSING` and continues,
and does not pin the truth-file hash. `class_separation.regression()` has the same shape:
`if not fpth.exists(): continue`. The evidence is therefore necessary but not sufficient: it
certifies detector behaviour only for the corpus it read, and cannot distinguish "detector
clean" from "corpus empty".

## Proposed fix

`proposed_patch.diff` adds three assertions before PASS is reachable, in both entry points:
corpus list size equals the declared total; no fixture path is missing; scored leaks/controls
equal the declared totals, with each failure printed as `REASON:`. The patch is verified in
`sandbox/patched/`: `T0` still PASSes at 17/17 + 10/10 and `T1`–`T5` all exit 1 with an explicit
reason. Applying it to the canonical paths is an owner decision.

Residual risk after the patch: the truth file is still not hash-pinned, so a semantically
consistent relabel that preserves the declared TP/FP/FN counts would not be caught.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-024/classsep_runner_vacuity/drive_vacuity.py
```

Deterministic; exit 0 asserts positive control + 3 vacuous cases + 5 patched closures. Inputs
re-measured after the run in `exit_hashes.json`; `entry_hashes.json` holds the start pins.

## Falsifier

Re-run the driver at runner sha256 `9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091`.
**Falsified** if any of `T1_empty_list`, `T2_missing_paths`, `T3_leaks_dropped` returns exit ≠ 0
or prints `VERDICT: DEFECTIVE` under the unpatched runner, or if `T0_real` fails to reproduce
17/17 leaks + 10/10 controls, or if any patched sandbox passes an incomplete corpus. `T4`/`T5`
are explicitly excluded from the fail-open claim.

## Next falsifier (for the owner / audit lead)

Apply `proposed_patch.diff` at the canonical path, add an emptied-corpus case to the standing A1
regression, and run it inside the gate evidence collection. The defect is closed only if every
incomplete corpus exits 1 with a printed REASON while `T0_real` still exits 0 at 17/17 and 10/10.
