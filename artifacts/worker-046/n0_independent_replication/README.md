# W046-N0-INDEP-REPL-01 — independent replication of the N0 order-2 evidence

**Worker:** worker-046 (bounded execution worker; no gate authority)
**Node / class:** N0 / `AF-WCC-SCALAR-SPH` (flat-space calibration sub-case only)
**Gate:** G-NUM — *supporting evidence only*, this directory cannot set a gate verdict
**Task taken from:** live queue, criterion "N0 convergence order measured AND independently
replicated" (`map.gates[G-NUM].criteria`, `map.assignments[astra-life01-n0-proposal]`); no
assignment card exists in `comms/inbox/worker-046.jsonl`, so one bounded task was taken from
the immediate queue and reported upward, per the worker charter.
**Result:** `verdict = REPRODUCED` (8/8 pre-registered criteria pass; supplementary pulse
probe passes).

## Why this directory exists

The published N0 order evidence is `numerics/tests/n0_order_4rung.json` (sha256 `c88146a1`),
carried by the frozen module `numerics/tests/flat_wave_replication.py` (sha256 `8ade1cdc`).
That module documents the axes it does **not** vary relative to the original harness:

1. the `psi = r*phi` reduction,
2. Dirichlet `psi(0) = psi(R) = 0`, i.e. the origin is never discretised in the physical field,
3. the exact Taylor start `psi^1 = psi0 + dt*psi_t0 + dt^2/2*psi_tt0`,
4. the Gaussian-pulse family.

Every replica in the swarm so far re-runs that same frozen module, so axes 1–3 have never
been exercised by a different implementation. This directory tests the order-2 claim on a
discretisation that shares **none** of axes 1–3, and additionally reports a pulse-member probe
for axis 4.

## What was run

`independent_replication.py` is self-contained (numpy + scipy only; nothing imported from
`numerics/` at solve time). Hash guards on the three pinned inputs fail closed.

| id | scheme | variable | space | time | origin | start |
|---|---|---|---|---|---|---|
| primary | SPH-FV | `phi` (unreduced spherical field) | cell-centred finite volume, flux form `3[S g]/V`, `S=r^2` | `scipy` DOP853, `rtol=1e-12` | zero flux from regularity (no Dirichlet at 0) | exact `phi(0,r)`, `phi_t(0,r)` (no Taylor bootstrap) |
| secondary | U-MOL | `u = r*phi` (published variable) | nodes, 2nd-order centred | DOP853, `rtol=1e-12` | Dirichlet `u(0)=0` | exact `u(0,r)`, `u_t(0,r)` |
| C1 control | upwind-wave | `u = p + q` | first-order upwind (`p_t+p_r=0`, `q_t-q_r=0`) | fixed-step RK4, CFL 0.5 | inflow from exact | exact components |
| C4 probe | SPH-FV | `phi` | as primary | as primary | as primary | pulse `(r0, sigma) = (9.0, 1.2)` |

Problem definition (shared with the object under test, necessarily): massless real scalar on
fixed Minkowski, `r in [0,30]`, `t_end = 6`, exact regular pulse
`phi(r,t) = [F(r-t) - F(-r-t)]/r`, `F(s) = exp(-(s-r0)^2/(2 sigma^2))`, `r0=10`, `sigma=1.5`;
rungs `dr = 0.2, 0.1, 0.05, 0.025`; error norm `sqrt(sum e_i^2 * dr)`; fit = least-squares
slope of `log e` vs `log h`; R5 uncertainty `delta = max(pair-spread half-range, slope SE)`;
agreement `|dp| <= max(0.25, sqrt(delta_A^2 + delta_B^2))` — the R5 definitions were pinned by
reproducing the published lffd row exactly (fit 1.9966248643204345, SE 0.0005631231918085,
half-range 0.0017749505081918) before this study was run.

## Headline numbers

| quantity | value |
|---|---|
| primary SPH-FV fit order | **1.998947 ± 0.001163** (pairs 1.997511, 1.999356, 1.999837) |
| secondary U-MOL fit order | **1.999936 ± 0.000077** |
| C1 first-order control | **0.886348** (norm+fit machinery is discriminative) |
| C2 exact-injection control | error exactly 0 |
| C3 time-tolerance control | relative error change 1.1e-10 at `dr=0.025` (temporal error negligible) |
| C4 pulse-member probe | **1.997752 ± 0.002460** (different pulse member) |
| published lffd / cnfd / cnfem | 1.996625 ± 0.001775 / 1.995351 ± 0.004172 / 1.988860 ± 0.005143 |
| primary vs published | `|dp|` 0.00232 / 0.00360 / 0.01009, all ≤ R5 bound 0.25 |
| secondary vs published lffd | `|dp|` 0.00331 ≤ 0.25 |

Secondary per-rung error ratio vs published lffd (same variable and stencil family, different
time integrator and start): 1.309, 1.305, 1.302, 1.300 — i.e. the published absolute errors
are reproduced up to a constant ≈1.30 factor, consistent with the leapfrog temporal error
being the only material difference at these resolutions.

## Pre-registered acceptance (fixed before the numbers were inspected)

A1 primary in band `|p-2| <= 0.3`; A2 primary monotone over 4 rungs; A3 primary R5-agrees with
published lffd; A4 secondary in band and R5-agrees with published lffd; A5 C1 measures
`0.5 <= p <= 1.5`; A6 C2 error `<= 1e-13`; A7 C3 relative change `<= 1e-3`; A8 hash guards
hold. All 8 pass. Verdict rule: any of A1/A3/A4 failing → `FALSIFIED`; all pass → `REPRODUCED`;
A1/A3/A4 pass but a control fails → `PARTIAL`.

## What this does NOT establish

* No gate verdict, no node completion, no review verdict: worker events cannot move those.
  `numerics_lock` stays LOCKED; N1 stays queued; no self-gravitating code was written or run.
* No physics, self-gravity, collapse, WCC or SCC claim. This is flat-space calibration only.
* The PDE, the pulse family, the domain and the error-norm convention are shared with the
  published evidence — they are the object under test, not independent axes.
* Absolute error values are not compared across variables: published errors are on `u=r*phi`,
  the primary study is on `phi`. Only orders and the dimensionless R5 agreement are compared.
* The class binding to `AF-WCC-SCALAR-SPH` records the taxonomy hash `66bf917bd368` only as
  provenance; G-F0 is pending, so the binding is not endorsed as frozen here.

## Falsifier

Re-run `independent_replication.py` after any change to this script or to the pinned inputs.
The order claim is falsified if the primary SPH-FV or secondary U-MOL fit falls outside
`|p-2| <= 0.3`, if either fails R5 agreement with the published lffd order, if the C1
first-order control is not measured near order 1, or if the C4 pulse probe falls outside the
band. Any hash-guard mismatch voids the comparison entirely (the script exits 2, fail closed).

## Files

| file | role |
|---|---|
| `independent_replication.py` | the self-contained implementation, controls and verdict logic |
| `results.json` | machine output of the run (all rows, fits, R5 statistics, controls) |
| `verification.json` | hash-chained verification report built from `results.json` |
| `MANIFEST.json` | sha256 of every file in this directory |
| `CHECKPOINT.json` | worker checkpoint for this one bounded lifecycle |
| `README.md` | this document |

Reproduce: `python3 independent_replication.py` from any cwd (writes `results.json` next to
itself); then `python3 build_verification.py` to re-emit the hash-chained report.
