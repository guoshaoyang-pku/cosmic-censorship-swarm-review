# W051-N0-DTSUBDOM-04 — direct temporal-subdominance bound at the N0 certification dt

Actor: `worker-051` (bounded execution worker) · Node `N0` · Gate `G-NUM` · Class `AF-WCC-SCALAR-SPH`
Conclusion type: `numerical_evidence` · Flat-space calibration sub-case only · `numerics_lock` respected
(no N1, no `numerics/spherical_solver/`, read-only on all canonical paths)

## Why this task

The current N0 order-certification basis is
`numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c` (lead-numerics): four rungs
(dr = 0.2/0.1/0.05/0.025), **dt fixed at 1e-4**, schemes lffd / cnfd / cnfem. Its temporal
subdominance at dt = 1e-4 is bounded only by the companion control's dt = 1e-3 and 5e-4 ladders —
i.e. by *extrapolation*. The lead's own falsifier F7 is "the fixed-dt ladder is shown temporally
contaminated at dt <= 1e-4". This task measures the residual temporal contribution **directly at
the certification dt** by re-running the same frozen module at dt = 1e-4 / 5e-5 / 2.5e-5 on the
same four rungs and three schemes.

No assignment card existed in `comms/inbox/worker-051.jsonl`; this is one bounded class-bound
task taken from the numerics immediate queue, as the prior W051 cards were.

## Method and pins (all measured on disk, refuses on mismatch)

| input | sha256 |
|---|---|
| `numerics/tests/flat_wave_replication.py` (frozen module, imported read-only) | `8ade1cdc163ea420…` |
| `numerics/protocol/n0_fixed_dt_certification.json` (positive control) | `1677822ceb9c81e8…` |
| `numerics/protocol/n0_fixed_dt_certification.py` | `3c7c908783844604…` |
| `numerics/CONVERGENCE_PROTOCOL.md` (rev 3) | `1e6cdf04d7a2431…` |

Pre-registered thresholds (fixed before measurement, `thresholds_movable_after_result: false`):
F3 contamination ≤ 5 % of the rung error; F4 order shift ≤ 1e-3; F5 Richardson temporal order in
[1.5, 2.5]; F6 `steps == t_end/dt` and arms differ bitwise; F7 bitwise determinism. The 1e-4 arm
is a positive control that must reproduce the published certificate to ≤ 1e-12 relative.

## Pre-registered result (literal, unchanged)

```
verdict: falsifier_triggered
falsifier_triggered: [F5, F6]
```

| check | result |
|---|---|
| F1 pins resolve | **pass** (4/4) |
| F2 1e-4 arm reproduces the certificate | **pass, bitwise** — max relative row difference 0.0, max abs fitted-order difference 0.0 (all 12 rows, 3 orders) |
| F3 temporal contamination at dt = 1e-4 (vs 5e-5) | **pass** — max relative error change **cnfd 1.49e-3, cnfem 5.25e-4, lffd 2.37e-5** (bound 5e-2) |
| F4 certified order stable under dt halving | **pass** — \|p(1e-4) − p(5e-5)\| = **cnfd 7.33e-4, cnfem 2.53e-4, lffd 5.16e-6** (bound 1e-3); all 9 fits monotone and inside \|p−2\| ≤ 0.3 |
| F5 Richardson temporal order in [1.5, 2.5] | **fail** — q ranges cnfd [−2.45, −0.95], cnfem [−5.55, 0.41], lffd [2.64, 7.80] |
| F6 steps / arms differ | **fail** — at dt = 5e-5 and 2.5e-5 the harness takes **one extra full step** (120001 / 240001; final_t = 6 + dt). `arms_differ_bitwise` is true for all three schemes |
| F7 bitwise determinism | **pass** (2 repeated cases each bitwise equal) |

Fitted orders (four rungs, own OLS, L2 norm):

| scheme | p(1e-4) | p(5e-5) | p(2.5e-5) | delta_R5(1e-4) |
|---|---|---|---|---|
| lffd | 1.999943174 | 1.999938015 | 1.999937029 | 8.44e-5 |
| cnfd | 1.999863593 | 1.999130550 | 1.995879142 | 9.32e-5 |
| cnfem | 1.999916308 | 2.000169587 | 2.000885134 | 2.46e-4 |

## Post-hoc diagnosis of F5 and F6 (labelled; no threshold moved)

**F5 is an invalid estimator on this data, not evidence of contamination.** F5 assumed the total
L2 error refines as `e_spatial + c·dt^q`. The measured dt-response is not a power law and is
non-monotone: for cnfd at dr = 0.025, `e(1e-4) = 1.0401350e-4 < e(2.5e-5) = 1.0501562e-4`, i.e.
refining dt by 4× *increases* the total error. Richardson differencing of total errors therefore
does not measure the temporal order (hence q < 0 for cnfd/cnfem and q ≫ 2 for lffd). The
decision-relevant F3/F4 comparisons are unaffected.

**F6's trigger is the frozen harness's tolerance-based stop rule.** The loop is
`while t < t_end - 1e-12`, and at dt = 5e-5 / 2.5e-5 the accumulated time after
`round(t_end/dt)` steps is still just below the threshold, so one extra full step is taken:
final_t = 6.000050 / 6.000025 instead of 6. At dt = 1e-4 the run stops at 60000 steps with
final_t = 5.999999999999355. The requested dt is applied exactly (`dt_reported` equals the
requested dt on every row). The addendum probe `matched_time_probe.json` re-runs the cnfd
dt = 5e-5 ladder and re-evaluates the error at the stored step closest to t = 6.0 (offset
−7.3e-12): the overshoot's effect on the error is a **uniform +8.22e-6 relative**, and its effect
on the fitted order is **< 1.1e-11** (uniform across rungs, so it cancels in the log-log slope).
So the F3/F4 conclusions are not final-time artifacts.

## New quantitative bound (the useful by-product)

Across dt ∈ {1e-4, 5e-5, 2.5e-5} the four-rung fitted order moves by at most

* **cnfd 3.98e-3** (42.8× its reported delta_R5 of 9.32e-5),
* **cnfem 9.69e-4** (3.9× its delta_R5 of 2.46e-4),
* **lffd 6.14e-6** (0.07× its delta_R5 of 8.44e-5).

The certificate's delta_R5 is a *within-dt* statistical uncertainty (pair spread / LS SE over the
four rungs); it does not include this *across-dt* systematic. If the certified value is quoted as
a dt → 0 spatial order, it should carry an additional temporal systematic of **≤ 4.1e-3 (cnfd)**,
or be explicitly labelled "spatial order measured at dt = 1e-4". This is a precision statement,
not a failure of the order claim: at every dt and every rung the fits are monotone and inside
|p − 2| ≤ 0.3, so the band claim and the cross-scheme agreement claim (R5 floor 0.25, 60× larger
than the worst excursion) are unaffected, and the certificate's F7 ("temporally contaminated at
dt ≤ 1e-4") is **not** triggered by this direct measurement.

## What this does and does not establish

* Establishes, by direct measurement at the certification dt, that the residual temporal
  contribution to each rung error is ≤ 0.149 % (cnfd) / ≤ 0.052 % (cnfem) / ≤ 0.0024 % (lffd) at
  dt = 1e-4, and that the fitted order moves ≤ 7.33e-4 between dt = 1e-4 and 5e-5.
* Does **not** claim a gate verdict, node completion, `validation_status=passed`, or any change
  to `numerics_lock`; worker events cannot move those.
* This is a faithful re-execution of the frozen module, not an independent discretisation;
  implementation independence is covered by workers 046/057 and is out of scope here.
* No physics claim; no claim about self-gravity, collapse, horizons, WCC or SCC. No claim about
  the shared axes (psi = r·phi reduction, Dirichlet box, Taylor start, Gaussian-pulse family).

## Files (sha256)

| file | sha256 |
|---|---|
| `n0_dt_subdominance_051.py` | `4e55dbc2a8cb881e4957906d6c79081b342dd90f95cfe1df82fb65af05521335` |
| `report.json` | `bb7133beb920c065a1521f78b5b0348ea5b856cab0eb51bb0a6c0b9e39724478` |
| `stdout.txt` | `75807f0ab6714ef876a13b5e31f9f0f6752df1a22523c9d2839efa825dda0ab0` |
| `matched_time_probe_051.py` | `28e863603061a1a1442741c86ff14a66431094d7636f25b073fdaa40cf7944e5` |
| `matched_time_probe.json` | `e3829494566d71821317b4c6a2fb832a9702aab44fb69b01ef5d6297f9ba6d86` |
| `matched_time_probe_stdout.txt` | `b9dd4ba4b9516a7af44271e267cfcaff661261e2f14620fe4f2cd0937a6410df` |
| `CHECKPOINT.json` | see `SHA256SUMS` |

Runtime: 1763 s (main) + 237 s (probe) under high shared-machine load. Python 3.10.12, numpy 2.2.6.
