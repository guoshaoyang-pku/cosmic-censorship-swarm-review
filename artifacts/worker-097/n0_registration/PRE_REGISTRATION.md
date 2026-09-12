# W097-N0-REGISTRATION-01 — pre-registration (written before the census ran)

Task: independent measurement (read-only) of the PROTOCOL rule-2 registration coverage for
review-cited evidence, focused on the six paths named by blocking item B-N0-R2-1 in
`reviews/N0-review-final-verify.json` (audit lead, 2026-09-12T00:50:20+08:00).

Class binding: `AF-WCC-SCALAR-SPH` (node N0 / gate G-NUM). No canonical path is written; no gate
verdict, no node status and no ledger/schema is touched. Outputs live only under
`artifacts/worker-097/n0_registration/`, plus a worker checkpoint under `runtime/state/`.

Measurement object: `runtime/state/artifact_hashes.json` (`hashes` = node/gate artifacts,
`registry` = key-deliverable scan), measured by re-hashing the on-disk bytes.

## Predictions (pre-registered, before running `measure.py`)

- **P1** Of the six B-N0-R2-1 paths, exactly 3 are registered after the pass-05 registry-root
  repair (`numerics/CONVERGENCE_PROTOCOL.md`, `numerics/results/flat_wave_convergence.json`,
  `numerics/gates.py`) and exactly 3 are absent (`artifacts/worker-046/n0_fixed_dt_independent/verification.json`,
  `artifacts/worker-057/n0_fixeddt_verify/report.json`,
  `artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json`).
- **P2** All 3 absent paths exist on disk with non-zero bytes, and 0 registry keys carry the
  prefix `artifacts/worker-` while files on disk under `artifacts/worker-*` number >1000.
- **P3** Global census: at least 50 resolved review-cited file paths are unregistered by the
  current registry, and at least 80% of them resolve under `artifacts/worker-*`.
- **P4** Among refs that cite a full 64-hex sha256 on a resolvable file: 0 dangling, 0 mismatch
  against measured bytes.
- **P5** All six declared controls PASS.

## Falsifier (declared before measurement)

A cited review evidence path that resolves on disk and is covered by an existing scan root while
this report calls it unregistered; or a cited 64-hex hash that equals measured bytes while this
report calls it a mismatch; or a dangling ref this report marks resolved; or a re-run of
`measure.py` at the same pin that disagrees with the first run. Any of these falsifies the census
and it must be withdrawn.

## Not claimed

No gate verdict, no node completion, no claim that registering these bytes makes N0 correct, and
no claim about the numerics content itself. Registration is bookkeeping for reproducibility.
