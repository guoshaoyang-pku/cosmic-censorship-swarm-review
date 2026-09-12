# W052-A1-CLASSSEP-VACUITY-REPL-01 — independent replication: the class-separation gate runner fails open

| field | value |
|---|---|
| worker / node / gate | `worker-052` / `A1` / `G-AUDIT` |
| classes bound | `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH` |
| target finding | `W024-CLASSSEP-RUNNER-VACUITY-01` (worker-024), `artifacts/worker-024/classsep_runner_vacuity/report.json` |
| instrument audited | `runtime/bin/classsep_regression.py` sha256 `9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091` |
| detector under it | `research_map/class_separation.py` sha256 `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| ground truth | `artifacts/worker-07/class_separation_falsification/results.json` sha256 `d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452` |
| proposed patch | `artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff` sha256 `1a9a2f214a81503d27b798e96c3dc879480ce0fa8c11cc5039acd23ab4d740f9` |
| verdict | **`REPLICATED`** — fail-open confirmed on five incomplete-corpus states; proposed patch closes all five while the real corpus still PASSes |
| authority | no gate verdict, no `status=done`, no `validation_status=passed` |

## Question

CF-3 froze the class-separation regression ("17/17 leaks + 10/10 controls, 0 FP/FN") as the
standing evidence that the four frozen classes stay separated. The runner's pass condition is
`fn == 0 and fp == 0` over whatever fixtures it could read. This task independently replicates
worker-024's finding that the instrument can certify a corpus it did not read, using a separate
harness, and then independently validates their proposed fix — including one case that bounds
what the fix actually guarantees.

## Method (independent of worker-024's driver)

`replicate_classsep_vacuity_052.py`:

1. Pins the four inputs by sha256 and **aborts if any pin moves**; re-measures at the end and
   requires the pins to be stable (they are).
2. `S0_in_situ` runs the canonical runner in the real repo (positive anchor; the runner writes
   only an empty `runtime/state/classsep_regression/` directory).
3. Builds one byte-identical sandbox template and copies it per case; each case mutates only the
   **sandbox copy** of `results.json` (and, for `R6`, removes it), then executes the pinned runner
   as a subprocess.
4. Repeats every case on fresh copies with worker-024's `proposed_patch.diff` applied via
   `patch -p0` — note: `-p0` is required; the diff carries no `a/`/`b/` prefixes, so `-p1` skips
   both files (observed in the first run).
5. Also exercises the detector's own `class_separation.regression()` entry point directly.

No canonical repo file is modified. Expectations are pre-registered in the script; the harness
exits 0 only when all of them hold (`all_expectations_met: true`).

## Results

| case | corpus state | unpatched runner | patched runner |
|---|---|---|---|
| `S0_in_situ` | real repo, canonical paths | **PASS**, 17/17 + 10/10, exit 0 | — |
| `R0_real` / `P0_patched_real` | untouched 27-fixture corpus | **PASS**, 17/17 + 10/10, exit 0 | **PASS**, 17/17 + 10/10, exit 0 |
| `R1_empty` / `P1_patched_empty` | `fixtures: []`, summary intact | **PASS**, 0/0 + 0/0, exit 0 | exit 1, 3 REASONs |
| `R2_missing_all` / `P2_…` | all 27 paths unreachable | **PASS**, 27 `MISSING` rows, 0/0 + 0/0, exit 0 | exit 1, 3 REASONs |
| `R3_leaks_removed` / `P3_…` | 17 leak fixtures removed | **PASS**, 0/0 + 10/10, exit 0 | exit 1, 2 REASONs |
| `R4_summary_zeroed` / `P4_…` **(new)** | 27 fixtures intact, declared totals zeroed | **PASS**, 17/17 + 10/10, exit 0 | exit 1, 3 REASONs |
| `R5_controls_removed` / `P5_…` **(new)** | 10 control fixtures removed | **PASS**, 17/17 + 0/0, exit 0 | exit 1, 2 REASONs |
| `R6_results_absent` | truth file deleted | exit 1 (traceback; **not** fail-open) | — |
| `R7_replaced_corpus` / `P7_…` **(new)** | corpus replaced by 1 genuine control, self-consistent summary | **PASS**, 0/0 + 1/1, exit 0 | **PASS**, 0/0 + 1/1, exit 0 |
| `R0_real.detector_regression` | detector entry point, real corpus | `PASS`, `corpus_size 27` | `PASS`, `corpus_size 27` |
| `R1_empty.detector_regression` | detector entry point, empty corpus | `PASS`, `corpus_size 0` | `DEFECTIVE`, 3 problems |

`fail_open_confirmed: true`, `patch_closes_fail_open: true`,
`patch_scope_limit_confirmed: true`, `pins.stable: true`.

## Mechanism

`runtime/bin/classsep_regression.py`: a missing fixture is recorded `MISSING` and skipped
(line 34); the pass condition is `fn == 0 and fp == 0` (line 57); `results.json.summary`
(`fixtures_total=27`, `leaks_total=17`, `controls_total=10`) is never compared against what was
actually scored, and the truth file is not hash-pinned. `class_separation.regression()` has the
same shape (`if not fpth.exists(): continue`, `verdict: "PASS" if fn == 0 and fp == 0`). An empty
or unreachable corpus therefore scores 0/0 and 0/0 and is certified PASS with exit 0.

## Scope of the proposed fix

The patch adds declared-total, missing-file and scored-count assertions in both entry points.
It makes **accidental** truncation loud (all five cases now exit 1 with printed `REASON:` lines)
and preserves the real-corpus PASS in both entry points. It does **not** bind the corpus to the
pinned 27/17/10 ground truth: `R7`/`P7` show that a replaced corpus carrying a single genuine
control and a matching self-declared summary is still certified PASS. Closing that residual
requires pinning `results.json`'s sha256 (and ideally the fixture hashes already recorded per
fixture) inside the instrument.

## Why this matters (context, not a verdict)

Several issued reviews and the pass-03 lifecycle cite this runner's `VERDICT: PASS` as a control
(`reviews/F1-review-034.json:61`, `reviews/F1-review-025.json:64`, `reviews/F2a-review-019.json:31`,
`reviews/F2a-review-022.json:26`, `reviews/F2a-review-088.json:69`, `reviews/F2b-review-034.json:85`,
`runtime/state/controller_verification/astra-lifecycle-03.md:21`). Most of those reviews already
scope-limit the claim ("scores the checker, not the absence of merges"). The audit-relevant point
is instrument-level: a `PASS` from this runner is not by itself distinguishable from "the corpus
was not read", so it cannot carry a gate criterion on its own until the patch (or an equivalent
integrity check) is installed at the canonical path.

## Falsifier

Re-run `replicate_classsep_vacuity_052.py` at the pins above. **Falsified** if any of
`R1`, `R2`, `R3`, `R4`, `R5` exits nonzero or prints `DEFECTIVE` under the unpatched runner, if
`R0_real`/`S0_in_situ` fail to reproduce 17/17 + 10/10 PASS, if any patched `P1`–`P5` passes an
incomplete corpus, if `R6` unexpectedly exits 0, or if the pins are not stable across the run.

**Next falsifier (owner / audit lead):** install the patch at the canonical path plus a
truth-file hash pin, then re-run: closed only if every incomplete corpus exits 1 with a printed
`REASON:`, `R0` still exits 0 at 17/17 + 10/10, and a replaced-corpus case (`R7`) exits 1.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-052/classsep_vacuity_replication/replicate_classsep_vacuity_052.py
```

Deterministic; exit 0 iff `all_expectations_met`. Raw stdout/stderr/exit codes per case are in
`logs/`; the machine-readable record is `report.json`.
