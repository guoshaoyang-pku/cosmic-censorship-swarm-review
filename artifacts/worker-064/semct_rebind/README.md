# W064-SEMCT-REBIND-01 — semantic contract suite: rebind audit at rev25

Bounded class-bound task taken by `worker-064` (instance `worker-064-20260912T002404-968807`)
without an inbox card. Target: `schemas/semantic_contract_tests/` (calibration evidence routed
to **G-AUDIT**, node **A1**; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`).
No canonical artifact was modified; the shared suite directory was never written to.

## Question

The suite's README records a run at `2026-09-12T00:14:40+08:00` whose numbers are invalidated by
its own falsifier ("any stage hash change invalidates the numbers"). The canonical schemas were
republished at `00:19:14`, *after* that run. Does the suite still run, and do the recorded numbers
hold at the frozen rev25 bytes?

## Method

1. `semct_rebind_audit.py` copies the fixture tree byte-for-byte into `suite_copy/`, loads the
   canonical runner `schemas/semantic_contract_tests/run_contract_tests.py` as a module, and
   redirects only `MANIFEST` / `OBSERVED` / `HERE` / `REPO`.
2. **Run A** (`original_run.json`): canonical manifest, unmodified.
3. **Rebind** (`rebind_patch.json`, `manifest_rebound.json`): the three
   `conforming_canonical_controls[].sha256` pins only are replaced by the measured rev25 hashes.
4. **Run B** (`rebound_observed.json`, `rebound_run.json`): full 38-target suite.
5. **Determinism control** (`determinism_check.py`, `determinism_check.json`): independent second
   run of the rebound manifest, compared per test id.

## Results (rev25: F0 taxonomy `276009f4f63d`, C0 `1bb78ce9b357`, C2 `b6123750b37d`, F1 `9a8bd4c96800`)

| measurement | value |
|---|---|
| fixture integrity at canonical pins | 32/32 mutants, 3/3 frozen controls intact; **3/3 canonical pins stale** |
| run A, unmodified manifest | **exit 2 — INTEGRITY_FAILURE**, exactly 3 sha-mismatch errors (C0/C2/F1 pins), no `observed_verdicts.json` written |
| run B, rebound manifest | **exit 3 — integrity ok, validity false** |
| mutants caught | structural **32/32**, semantic baseline **11/32**, hardened (proposed) **32/32** |
| escapes of adopted stages / hardened-only catches | **0 / 0** |
| frozen controls accepted by both adopted stages | **0/3** — all rejected by the structural gate on **R28 only** |
| current canonical schemas accepted by all three stages | **3/3** (K01/K02/K03) |
| determinism (second run, 38 test ids) | **0 differences** |

Every `run_record.summary` number from `00:14:40` is reproduced exactly; the stage tools are
unchanged (`check_class_schema.py` `000e09e46b2f`, `spec_conformance_audit.py` `c79d8ab8440a`).
What has changed is only the canonical schema bytes the suite is pinned to.

## Findings (each with its falsifier)

- **F-SEMCT-1** — the unmodified suite cannot run at all: exit 2, 3 integrity errors.
  *Falsifier:* a re-run with exit ≠ 2, an intact canonical pin, or a fixture/control mismatch.
- **F-SEMCT-2** — the repair is exactly three sha256 pins; no rule, fixture, control, or expected
  verdict needs to change. *Falsifier:* any additional diff between `manifest_rebound.json` and the
  canonical manifest beyond those pins and the `worker_rebind` record.
- **F-SEMCT-3** — all `00:14:40` mutant-catch numbers reproduce at rev25 (32/32, 11/32, 32/32).
  *Falsifier:* any stage count differing from `run_record.summary`, or any escape/hardened-only id.
- **F-SEMCT-4** — `ADJ-CONTROL-STALENESS` persists at rev25: the three frozen controls are all
  rejected by structural **R28** while the three current canonical schemas pass all three stages,
  so `validity.valid_for_calibration=false` and the suite still cannot be used as current-revision
  calibration evidence. *Falsifier:* a run in which every frozen control passes both adopted
  stages, or a current canonical schema is rejected by any stage.

## For the lead (owner `astra-lead-formulation`)

1. Apply `rebind_patch.json` (3 pin replacements) so the suite is executable again — without it,
   `run_contract_tests.py` exits 2 and produces no calibration output.
2. Resolve `ADJ-CONTROL-STALENESS` (rebase the three frozen controls to the current canonical
   layout, or pin the calibration gate revision) — the mutated corpus is intact and need not change.
3. After (1)+(2), a re-run should exit 0 with `valid_for_calibration=true`; this audit's harness can
   certify that window.

## Limits / not claimed

`semct_rebind_audit.py` measures shape and calibration mechanics, not mathematical correctness,
non-vacuity, or truth (see the suite's own limits). No gate verdict, no node completion, no
modification of any canonical artifact, and no claim about bytes outside the measured rev25
snapshot is made here. Worker events cannot set `done`, `passed`, or a gate verdict.

## Files

| file | what |
|---|---|
| `semct_rebind_audit.py` | audit harness (runs A and B, writes the report) |
| `determinism_check.py` | second-run control |
| `report.json` | full structured report, findings, falsifiers |
| `original_run.json` / `rebound_run.json` / `rebound_observed.json` | raw run records and per-fixture verdicts |
| `manifest_rebound.json` / `rebind_patch.json` | worker-local repaired manifest and the minimal patch |
| `determinism_check.json` | second-run comparison |
| `manifest.sha256` | hashes of the deliverables |
