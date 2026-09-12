# W020-N0-FIXEDDT-VERIFY-01 — independent verification of the N0 fixed-dt temporal control

| field | value |
|---|---|
| task | `W020-N0-FIXEDDT-VERIFY-01` (bounded class-bound task; no inbox card issued, taken per the W081/W094 pattern) |
| actor | `deepseek-flash-20` (worker-020) |
| class | `AF-WCC-SCALAR-SPH` |
| node / gate | `N0` / `G-NUM` |
| target (pinned) | `numerics/protocol/temporal_subdominance_control.json` sha256 `334f5b71e0d53ab6` |
| target generator | `numerics/protocol/temporal_subdominance_control.py` sha256 `ee14a3caf086d64e` (astra-lead-numerics) |
| instrument (pinned) | `numerics/tests/flat_wave_replication.py` sha256 `8ade1cdc163ea420` |
| artifact | `verify_fixed_dt_control.json` sha256 `79737c5c7f1ef26d` |
| tool | `verify_fixed_dt_control.py` sha256 `79545150356b567d` |
| log | `verify_fixed_dt_control.log` sha256 `f798062cf5d79847` |
| runtime | 126.7 s, CPU only, fresh process |
| validation_status | `unverified` (worker evidence; not a gate verdict) |

## Why this task

`G-NUM` criterion C8 was the only unmet numeric requirement: the recorded protocol verdict was
stale, and the certified order claim was measured on constant-CFL ladders (worker-067 finding F1;
worker-081 adjudication `artifacts/worker-081/n0_c8_adjudication/adjudication.json` confirmed the
finding and withdrew its own accept). At 2026-09-12T00:26:49+0800 the numerics lead filed a
protocol-§3.4-compliant fixed-dt control (`dt = 1e-3 / 5e-4`, four rungs, three schemes) plus
temporal sweeps. That artifact is self-authored by the lead, so it cannot satisfy "independently
replicated" by itself. This run is the independent replication.

## What was done (all read-only on canonical paths)

- **A — recomputation.** Every derived statistic filed in the target (`fit_order`,
  `pair_orders`, `pair_half_range`, `least_squares_se`, `delta_R5`, `monotone`, `within_band`,
  `rule_a`, `p_cfl_by_scheme`) was recomputed by this script's own arithmetic from the target's
  raw rows. All 9 ladders and 6 rule_a rows match at ≤ 1e-9 relative (measured 0.0).
- **B — fresh re-run.** The fixed-dt ladders B (dt = 1e-3, 5e-4 × dr = 0.2/0.1/0.05/0.025 ×
  lffd/cnfd/cnfem) and both temporal sweeps C were re-executed in a fresh process against the
  frozen module at its pinned hash. Every filed row reproduces at 0.0 relative deviation;
  selected points reproduce bitwise; the frozen-state null control returns order
  `-2.6e-16` and is rejected.
- **C — rule audit.** The pre-registered admissibility rules were re-evaluated as written and
  as implemented, and rule B was additionally checked symmetrically.
- **D — controls.** Mutation control (a +1e-6 row perturbation is detected), wrong-sign operator
  (blows up), `dt ∝ √h` probe (order drops to 1.06), determinism (bitwise).

## Result

`status = VERIFIED_WITH_ONE_RULE_DEFECT`

| ladder | lffd | cnfd | cnfem |
|---|---|---|---|
| fixed dt = 1e-3 | 2.000626 | 1.996292 | 2.003704 |
| fixed dt = 5e-4 | 2.000109 | 1.999013 | 2.000945 |

All six fixed-dt ladders are monotone and inside the pre-registered band |p − 2| ≤ 0.3, and all
are reproduced row-for-row at the pinned frozen-module hash. **The order-2 spatial conclusion is
therefore supported by protocol-compliant fixed-dt evidence, independently of the constant-CFL
ladders.**

Two findings on the target's own rule application:

- **RB1 (rule defect).** `rule_b` is one-sided as pre-registered (`excess <= 0.05`): a
  constant-CFL error *below* the spatial plateau passes without bound. Symmetric magnitudes at
  the finest sweep (dr = 0.05): cnfd `1.258`, cnfem `0.723`, lffd `0.236`. So the filed verdicts
  for cnfem and lffd ("temporal contribution below the pre-stated tolerance") hold only in the
  one-sided reading; their constant-CFL errors are 72 % / 24 % *below* the plateau, i.e. the
  constant-CFL run underestimates the spatial error through temporal–spatial cancellation.
  Repair: restate rule_b symmetrically (`|excess| <= 0.05`) before the artifact is used as C8
  evidence, or drop ladder A to a labelled mixed-order supporting control.
- **RB2 (spec/implementation mismatch, immaterial here).** The written rule names dr = 0.2; the
  filed check reports the worst over `temporal_dr = [0.2, 0.05]`. The stricter reading does not
  change any pass/fail (cnfd fails and the others pass at both dr values).

## Falsifier

Void if: (i) either pinned input re-hashes differently; (ii) a fresh re-run at frozen module
`8ade1cdc163e` reproduces any filed fixed-dt B row outside 1e-9 relative; (iii) a filed B ladder
fit order falls outside |p − 2| ≤ 0.3; (iv) a filed derived statistic differs from this script's
recomputation by more than 1e-9 relative; or (v) the mutation control is not detected.

## Authority limits and conflict disclosure

No gate verdict, no node completion, no edit to any canonical path. worker-020 is the original
author of the unassigned candidate `numerics/tests/flat_wave.py` (`8b52014dac47`); that candidate
is **not** the target here, is neither edited nor certified, and the instrument used
(`flat_wave_replication.py`, assignment deepseek-flash-13) was not authored by worker-020.
