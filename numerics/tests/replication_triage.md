# N0 replication triage — root cause of the cnfem defect

| field | value |
|---|---|
| assignment | `astra-adj2-02-assignment` (Astra, 2026-09-11T23:24:47+08:00) |
| node / gate / class | N0 / G-NUM / AF-WCC-SCALAR-SPH |
| trigger | controller reproduced an `ORDER DISAGREES` verdict from an intermediate revision: cnfem order ≈ −0.077, own/harness energy drift ≈ 1.0e+01 |
| deliverable | `numerics/tests/replication_triage.md` (this file) |
| clean re-run | `numerics/results/flat_wave_replication.json`, sha256 `298a4d921c2264e6ef305274592dba62b2d3ef4bee456d56844d74bf0369fd33` |
| implementation | `numerics/tests/flat_wave_replication.py`, sha256 `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422` |
| status | root cause found and fixed; **scheme not deleted, gate not relaxed**; unverified pending review |

## Root cause (implementation defect, not a harness defect)

`CrankNicolsonFEM` assembled the recurrence for `M psi'' = -K psi` as

```
(M + cK) psi^{n+1} = 2 M psi^n - (M - cK) psi^{n-1},   c = dt^2/2      # WRONG
```

The CN/trapezoidal rule moves the *same* operator to the left of both levels:

```
M (psi^{n+1} - 2 psi^n + psi^{n-1}) / dt^2 = -K (psi^{n+1} + psi^{n-1}) / 2
  =>  (M + cK) psi^{n+1} = 2 M psi^n - (M + cK) psi^{n-1}              # correct
```

With `M - cK` on the right-hand side the scheme is no longer the trapezoidal rule. The
resulting amplification factor has one root with |rho| > 1 for every generalized eigenmode, and
the excess grows secularly. Because the perturbation source is the initial-data region, the
error is a stationary bump near `r ≈ r0` growing roughly linearly in time: measured amplitude
1.15 → 2.52 between t=1 and t=6 at dr=0.2, with a 0.0045 relative error in the initial
acceleration already present at t=0.

Minimal reproduction (before the fix):

```python
from flat_wave_replication import PulseExact, grid, CrankNicolsonFEM   # pre-fix revision
r = grid(30.0, 0.2); p = PulseExact(); psi0, pt0, ptt0 = p.initial_data(r)
s = CrankNicolsonFEM(r, 0.1, psi0, pt0, ptt0)
for _ in range(60): s.step()
# observed: max|psi| ≈ 2.52 at t=6 against exact max 1.0; fit order over dr 0.2/0.1/0.05 = -0.077
```

The FD sibling `CrankNicolsonFD` was already correct (operator `A` negative definite, so the
sign of the `cA` term differs); that asymmetry is what made the FEM branch look plausible.

## Fix

One line: use `B = M + cK` on the right-hand side. After the fix, measured at the N0 harness
configuration (Gaussian pulse, r in [0,30], t_end=6, dr 0.2/0.1/0.05, cfl=0.5):

| scheme | order (harness) | harness energy drift | own invariant drift | harness verdict |
|---|---|---|---|---|
| lffd (reference-family control) | 1.9958 | 3.38e-15 | 3.38e-15 | PASS |
| cnfd (independent, implicit CN + FD) | 1.9935 | 6.59e-08 | 1.11e-14 | PASS |
| cnfem (independent, implicit CN + P1 FEM) | 1.9863 | 8.48e-09 | 2.04e-14 | PASS |

Reference `radial_leapfrog` order re-measured by this worker with the provided harness:
1.9957695044715191.

## Invariant check made scheme-appropriate (not relaxed)

The harness functional is the leapfrog staggered energy, which is *not* the exact invariant of
the three-level CN scheme. Rather than relax `drift_tol`, the replication now reports two
quantities and labels them:

* `harness_leapfrog_energy_drift` — the gate's functional, unchanged tolerance 1e-6;
* `own_energy_drift` — the exact average-acceleration invariant of the CN scheme,
  `1/2|V|^2 - 1/4<A psi_new,psi_new> - 1/4<A psi_old,psi_old>` (FD) and its mass/stiffness
  analogue `1/2 V^T M V + 1/4 psi_new^T K psi_new + 1/4 psi_old^T K psi_old` (FEM).

The exact form was identified by elimination over four candidate quadratic forms on a 240-step
run (`E1` leapfrog staggered 6.7e-08, `E2` midpoint 3.3e-08, `E3` central-velocity 1.0e-07,
`E4` average-acceleration **1.3e-14**), then verified for both schemes.

## Hypothesis this triage killed

Before the fix this worker hypothesised that the N0 invariant gate admits only leapfrog-family
schemes. The corrected measurements falsify that: both independent schemes pass the gate
(6.6e-08 and 8.5e-09 versus `drift_tol` 1e-6) while conserving their own invariants to ~1e-14.
What remains true is weaker and recorded in the report: the gate's tolerance does not
discriminate exact from near conservation (reference drift is ~7 orders of magnitude smaller),
so an invariant PASS bounds the leapfrog functional, not the solver's own invariant.

## Clean re-run provenance

* `numerics/results/flat_wave_replication.json` — sha256 `298a4d92…`, contains order studies,
  invariant studies, stability, controls, determinism, provided-harness verdicts and the
  gate-calibration finding.
* `numerics/tests/flat_wave_replication.py` — sha256 `8ade1cdc…`.
* Candidate snapshot pinned for comparison: `artifacts/flash-13/n0_replication/evidence/`
  `candidate_flat_wave_snapshot.py` (sha256 `743c73e4…`, selftest pass) — the candidate at
  revision `6af64b20…` failed its own `odd-cubic sign convention` check at 23:22; the author
  revised it before this triage ran, so that transient is recorded as an observation only and
  is not reproducible from the repository.

## Residual risk (falsifier unchanged)

The replication shares with the candidate/harness the `psi = r*phi` reduction, Dirichlet walls,
the Taylor start, and the Gaussian-pulse methodology. A bug in any shared axis is **not**
detected. The assignment's falsifier — "replication shares the same discretization bug as
worker 12" — is therefore only partially addressed: independence is along time integration,
spatial discretisation and energy functional; it is none along the reduction and start.

## No deletion, no relaxation

The FEM scheme is retained and passes; the invariant gate was not modified; no node completion
is claimed. Controller adjudication of this triage is requested.
