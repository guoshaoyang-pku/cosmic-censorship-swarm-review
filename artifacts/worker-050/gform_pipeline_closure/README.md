# W050-GFORM-PIPELINE-CLOSURE-06 — acceptance-pipeline instrument closure at FROZEN rev29

**Worker:** worker-050 · **Node:** F1,F2a,F2b · **Gate:** G-FORM (measurement only, no verdict)
**Class:** AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN
**Question:** is the two-stage acceptance verdict (`artifacts/formulation/tools/run_acceptance.py`)
a function of the FROZEN-rev29 pinned bytes alone?

The formulation lead reported this gap statically (blocker `lead-form-20260912T011509-123`:
`artifacts/worker-06/spec_conformance_audit.py` has zero occurrences in
`artifacts/formulation/FROZEN.json`). This task measures the consequence and the run-time closure
of the pipeline. It assigns no gate verdict and writes no canonical file.

## Pinned subjects (all re-measured stable across the run; `subjects.json`)

| subject | sha256 (prefix) |
|---|---|
| artifacts/formulation/FROZEN.json | 815e08079aef |
| artifacts/formulation/tools/run_acceptance.py | e544c36d2d16 |
| artifacts/formulation/tools/check_class_schema.py | 000e09e46b2f |
| artifacts/worker-06/spec_conformance_audit.py | c79d8ab8440a |
| artifacts/formulation/rule_spec.json | 40f9bb9e657b |
| artifacts/formulation/evidence/semantic_escape_rebased.json | 7e44de0e3906 |
| artifacts/formulation/evidence/acceptance_pipeline_report.json | 9b7d6c8208d3 |
| schemas/af_wcc_vacuum.yaml / af_scc_c2 / af_scc_c0 | d9cebb9404b2 / e9a27996dfd3 / b2ab6acb2bbe |

## Result 1 — the pinned report is not reproducible from live subjects

`entrypoint_repro.json`: the pinned entrypoint run in a copy-only sandbox mirror **exits 3** on its
own preflight (`corpus base 1bb78ce9bc…` vs live C0 `b2ab6acb2bbe…`) and writes no report. This
mechanically reproduces CF-32/REC-36 (i).

Bypassing the preflight by invoking the two pinned stages directly with the entrypoint's own argv
(`results_control.json`) still does not reproduce the pinned report:

| row | pinned report 9b7d6c82 | measured on live subjects |
|---|---|---|
| canonicals | 3/3 ok | F1 stage-2 **reject** (R03), F2a/C0 accept |
| controls | 2/2 ok | both **fail stage 1 on R22** (`revised_at_unused` stale key) |
| mutants structural | 30/31 | 31/31 |
| mutants semantic | 11/31 | 11/31 (exact) |
| union | 31/31 | 31/31 |
| overall | PASS | **FAIL** |

The mutant semantic count and the per-row semantic verdicts reproduce the corpus record exactly
(`port_validation.json`: stage-2 agreement **31/31**); the structural and control differences are
live subject drift (the rebased corpus is stale against the rev29 `KEY_MANIFEST.json`), not an
aggregation error (stage-1 verdict agreement 30/31, the one disagreement being `struct12`, the row
the pinned report itself records as its only structural escape).

## Result 2 — executed files that FROZEN rev29 does not pin

`closure_census.json` (strace of one stage-1 and one stage-2 invocation) plus the manifest check:

- `artifacts/worker-06/spec_conformance_audit.py` — executed by the pinned entrypoint
  (`SEM` constant), **not** in `FROZEN.json files{}`; its hash is declared in the pinned corpus
  record (`semantic_escape_rebased.json.w06_sha256`) but **no run-time check enforces it**
  (`declared_but_not_enforced`).
- `artifacts/formulation/evidence/rebased_fixtures/*.yaml` — the mutant population is read from a
  globbed directory; the files are content-addressed nowhere (`corpus_record_declares_per_fixture_hashes: false`).
- Pinned and enforced at run time: `run_acceptance.py`, `check_class_schema.py`, `rule_spec.json`,
  `KEY_MANIFEST.json`, the three canonical schemas.

## Result 3 — consequence control (pre-registered battery)

With every FROZEN-declared hash identical, substituting only the sandbox stage-2 engine bytes
changes row verdicts (`mutation_deltas.json`):

| treatment | rows changed | notable flips |
|---|---|---|
| M1 always-accept | 12 | canonical F1 reject→accept; the 11 semantic catches removed |
| M2 accept `struct12` only | 1 | struct12 stage-2 reject→accept |
| M3 drop failed R03 | 1 | canonical F1 reject→accept |

The aggregate PASS/FAIL does **not** flip, because on this stale corpus stage 1 fails the controls
in every phase; the demonstrated dependency is therefore **row-level, not aggregate-level**, and no
aggregate-level consequence is claimed.

Pre-registered predictions: P1 partially met (baseline premise stale), P2 falsified (no structural
escape exists on live subjects), P3 met (F1 flips under M3), P4 met via its second branch (pinned
report non-reproducible). Falsifiers F1–F4 do not fire (see `report.json`).

## Falsifiers

- **F1** every executed/read file content-addressed by FROZEN rev29 → gap void. Measured false.
- **F2** all mutations leave every verdict identical → missing pin inert. Measured false (12/1/1 rows change).
- **F3** any subject hash drift during the run → measurement void. No drift.
- **F4** B0 disagrees with the pinned report because of the aggregation port → harness invalid.
  Measured false: the port reproduces the corpus record's own stage-2 verdicts 31/31.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-050/gform_pipeline_closure/closure_check.py   # exit 0; exit 3 on subject drift
```

Outputs are rewritten in place and are byte-stable except `subjects.json`/`report.json`/`manifest.json`
timestamps. `preregistration.json` was written before the first treatment run and is not modified.

## Scope limits

Instrument closure of the acceptance pipeline at FROZEN rev29 only. No schema-content, class-binding,
or mathematical claim; no gate verdict; no node transition. The mutation wrappers are sandbox
substitutes, not proposed repairs. The census covers only paths open to strace during two traced
invocations. No canonical file was written: the sandbox is a copy-only mirror under
`artifacts/worker-050/gform_pipeline_closure/sandbox/`.
