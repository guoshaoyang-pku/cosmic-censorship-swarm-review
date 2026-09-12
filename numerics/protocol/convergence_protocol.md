# N0 convergence protocol and audit spec

| field | value |
|---|---|
| node | `N0` — flat-space scalar-wave calibration |
| gate | `G-NUM` |
| class | `AF-WCC-SCALAR-SPH` (**provisional** — F0 taxonomy artifact missing on disk) |
| assignment | `asg-2026-09-11-N0-deepseek-flash-14-23`, actor `astra`, 2026-09-11T23:19:12+08:00, deadline 2026-09-12T03:15+08:00 |
| scope lock | `numerics_lock` LOCKED: no self-gravitating solver, no N1 work, no `numerics/spherical_solver/` |
| deliverable | this protocol + worked synthetic example |
| validation status | **unverified** — no map node is claimed by this file |
| claims not made | no claim that N0 is complete or accepted; no claim about self-gravity, collapse, horizons, critical behaviour, radiation at I+, or cosmic censorship (WCC/SCC) in any form |

This document is a *protocol and audit specification*, not a result. It defines
what an N0 convergence claim must contain for the G-NUM gate to be evaluable,
and it demonstrates every criterion on synthetic (manufactured) data. The
concrete N0 implementations are `numerics/tests/flat_wave.py` (worker 12 /
numerics lead) and `numerics/tests/flat_wave_replication.py` (worker 13,
independent method); this protocol does not replace either.

---

## 1. Deliverable contract

1. Each implementation submits a machine-readable report in schema
   `n0-convergence-report/v1` (§7) plus the script that produced it.
2. The numerics lead runs
   `python3 numerics/protocol/audit_convergence_report.py REPORT.json`; the
   audit tool recomputes every criterion from the raw arrays and never trusts a
   self-declared verdict.
3. Gate G-NUM reads: `PASS` iff checks C0–C9 of §5 all pass for the submitted
   scheme, **and** the two independent implementations agree:
   `|p_A − p_B| ≤ max(0.25, sqrt(δ_A² + δ_B²))`, where `δ` is the reported
   order uncertainty (R5 of `scheme_independence_review.md`).
4. N0 node closure additionally needs the class-binding review of the audit
   group (node A1). This protocol does not close N0.
5. Disagreement between implementations is a **finding** to be reported, not a
   number to be averaged.

## 2. Definitions (fixed, so two reports are comparable)

| symbol | definition |
|---|---|
| `R` | outer calibration radius; reflecting Dirichlet wall `v(t,R) = 0` unless a test states otherwise |
| `n` | number of cells; `h = R/n`; grid `r_j = j·h`, `j = 0..n` |
| `λ` | `Δt/h`, held **fixed** across every rung of a ladder |
| `p_decl` | declared global order = `min(p_space, p_time)`; both components are reported separately |
| `p_space` | formal order of the spatial stencil (2 for central D2, 4 for the 5-point stencil) |
| `p_time` | order of the time integrator (4 for classical RK4, 1 for backward Euler) |
| `e_∞` | `max_j |v_num(t*,r_j) − v_exact(t*,r_j)|` over interior points |
| `e_2` | RMS `sqrt(mean_j(e_j²))` over the same points (this is the convention in `numerics/tests/flat_wave.py`; it is an RMS, not `sqrt(hΣe²)`) |
| `p_i` | `log(e_i/e_{i+1}) / log(h_i/h_{i+1})`, ladders ordered coarse → fine, ratio 2 |
| `p_fit` | least-squares slope of `log e` against `log h` |
| `p_res` | order of the spatial truncation residual `R_h = v_tt^exact − D2_h v^exact` at a generic time |
| `p_R` | three-grid Richardson order `log2(‖u_h − u_2h‖ / ‖u_2h − u_4h‖)` on the common mid grid |
| `u_R` | Richardson extrapolation `u_h + (u_h − u_2h)/(2^{p_R} − 1)` |
| `δ` | order uncertainty: `max(pair-spread half-range, least-squares standard error)` of the fit (R5, `scheme_independence_review.md`) |

## 3. Measurement validity conditions (V1–V6)

A number is not order evidence unless all of V1–V6 hold. These conditions exist
because E1 (§8) shows that an invalid measurement can be wrong by a factor of
two in the reported order while every individual run looks healthy.

- **V1 — broadband family.** The exact solution used for order certification has
  at least three spatial modes with amplitude ≥ 1e-3 of the peak, or is a pulse
  whose discrete spectrum satisfies the same condition. A single-mode test is a
  *dispersion diagnostic only*.
- **V2 — generic measurement time.** At least one measurement time `t*` has the
  projection of `∂_t v_exact` at `t*` at ≥ 20 % of its maximum over the
  measurement window, for every mode of the family. For the standing family
  with `k_m = mπ/R` this is `min_m |sin(k_m t*)| ≥ 0.2`. If a single-mode
  measurement is nevertheless reported, at least three distinct times are
  required and their orders must agree within 0.15.
- **V3 — asymptotic regime.** At least four rungs; the two finest pair orders
  agree within 0.15 and lie within tolerance of `p_decl`. With three rungs all
  pairs must lie within tolerance.
- **V4 — simultaneous refinement.** `λ` fixed, both `h` and `Δt` refined by the
  same ratio. Refining only one of them changes the meaning of `p_decl`.
- **V5 — stability margin.** Declared `λ` below the scheme's linear stability
  bound with ≥ 10 % margin; the run reports a growth-factor control
  (perturbation amplitude growth < 10 over the run). Non-finite values or
  amplitudes above 1e6 are an immediate rejection.
- **V6 — same path at every rung.** Same operator, integrator, `λ`, final time
  and initial-data family at every rung. The exact solution is *sampled* on each
  grid, never interpolated from a coarser rung.

## 4. Required tests

| id | test | passes when |
|---|---|---|
| T1 | exact-solution convergence, broadband family, V2-valid time(s) | `e_∞`, `e_2` → 0 with pair orders, fit within tolerance of `p_decl` |
| T2 | truncation-residual order of the spatial stencil at a generic time | `p_res ≥ p_space − 0.30` |
| T3 | Richardson three-grid self-convergence without an exact solution | `|p_R − p_decl| ≤ 0.30`; extrapolated `u_R` error ≤ finest `e_∞` |
| T4a | energy drift with a **scheme-appropriate, named** functional (R1–R4 below) | `exact_discrete`: drift ≤ `max(1e-12, 10·solver_tolerance)`; otherwise drift order ≥ `p_decl − 0.5` over ≥3 rungs **and** finest drift ≤ 1e-6 |
| T4b | static identity `H_v = E_u/(4π)` (u = v/r) on a resolved regular profile | relative difference ≤ 1e-3 at n ≥ 256, with its own convergence reported |
| T4c | optional dispersion check: single-mode phase error against `numerics.fd.symbol_d2` | measured/analytic ratio O(1) |
| T5 | negative controls must be rejected | frozen-in-time (order 0), off-by-one stencil (unstable), stable wrong-order scheme (~1), wrong-sign Laplacian, CFL above the stability bound, turning-point-only measurement (V2-invalid) |
| T6 | determinism | two runs of the same rung agree bitwise or within 1e-12 relative |
| T7 | order uncertainty | report `p ± δ`, `δ = max(pair-spread half-range, least-squares standard error)`, `δ ≤ 0.15` |

**Scheme-appropriate invariants (R1–R4, from
`numerics/protocol/scheme_independence_review.md`).** Drift magnitudes are not
comparable across `(scheme, functional)` pairs: in the measured example the
leapfrog staggered energy drifts `3.4e-15` on a leapfrog trajectory and
`6.6e-8` on a Crank–Nicolson trajectory, while the CN average-acceleration
invariant drifts `1.1e-14` on the CN trajectory and `3.6e-8` on the leapfrog
trajectory; both cross-functional mismatches converge at ≈4th order and flip
below `1e-8` after one refinement. Therefore:

- **R1** every report declares `energy_functional` (name, formula, quadrature,
  boundary treatment, `structural_class`, `solver_tolerance`);
- **R2** exact-discrete functionals use the roundoff criterion above;
- **R3** other functionals use the convergence criterion above — never a fixed
  absolute threshold at a single coarse rung;
- **R4** scheme A's functional is never a pass/fail criterion for scheme B;
  cross-functional evaluation is a labelled mismatch diagnostic only.

**Constraint diagnostics in fixed Minkowski.** There is no Hamiltonian or
momentum constraint to monitor on a fixed flat background. For N0 the phrase
means exactly T2 + T4a + T4b + T4c, and self-gravity constraint language must
not be imported into this node.

## 5. Failure criteria and audit mapping

The reference audit tool `numerics/protocol/audit_convergence_report.py`
implements exactly these criteria; its check ids are listed so a report reader
can map a failure to a rule.

| id | audit check | failure condition |
|---|---|---|
| FC0 | C0 completeness | required schema fields missing, or array lengths inconsistent |
| FC1 | C1 stability | `stable != true`, CFL above margin, non-finite or non-positive errors |
| FC2 | C2 non-degeneracy | no measurement time declared; single-mode with fewer than two times; no attestation |
| FC3 | C3 monotone | some rung fails `e_{i+1} ≤ e_i / 2^{p_decl − 0.5}` |
| FC4 | C4 order | finest two pair orders **or** fitted slope outside `p_decl ± 0.30` |
| FC5 | C5 residual | some `p_res < p_space − 0.30` |
| FC6 | C6 Richardson | `|p_R − p_decl| > 0.30` |
| FC7 | C7 invariant | functional not declared; `exact_discrete` above the roundoff criterion; or convergent functional above the 1e-6 budget; or, when the finest drift is above the 1e-12 roundoff floor, no convergence at `p_decl − 0.5` over the pairs above that floor |
| FC8 | C8 provenance | implementation path or sha256 missing; hash mismatch when the file exists |
| FC9 | C9 uncertainty | `order_uncertainty` missing, or `δ > 0.15` |

`PASS` requires C0–C9 all true. Exit codes: 0 = PASS, 1 = FAIL.

## 6. Resolution ladder and run matrix

| family | R | t* | λ | rungs | purpose |
|---|---|---|---|---|---|
| two-mode standing `(2,1.0),(5,0.5)` | 1 | 0.35 | 0.25 | 64, 128, 256, 512, 1024 | primary order certification (V1/V2) |
| pulse, smooth odd data | 40 | 8.0 | 0.25 | 64 … 1024 | broadband far-field control |
| single mode `(2,1.0)` | 1 | 0.35 | 0.25 | 64 … 512 | T4c dispersion diagnostic only |
| single mode `(2,1.0)` | 1 | 0.50 | 0.25 | 64 … 512 | **V2-invalid; retained as a negative control (E1)** |

## 7. Reporting table and canonical report

Required human-readable table columns:

`scheme_id | integrator | p_space | p_time | family | t* | n | h | Δt | λ | e_∞ | e_2 | p_pair(∞) | p_fit | p_res | p_R | drift | stable | wall_s | verdict`

Example, filled from the worked example's passing report (E2, standard central
D2 + RK4, declared order 2):

| n | h | e_∞ | e_2 | pair order (∞) |
|---|---|---|---|---|
| 64 | 1.5625e-02 | 4.210e-04 | 2.370e-04 | — |
| 128 | 7.8125e-03 | 1.049e-04 | 5.878e-05 | 2.005 |
| 256 | 3.9063e-03 | 2.620e-05 | 1.465e-05 | 2.001 |
| 512 | 1.9531e-03 | 6.548e-06 | 3.658e-06 | 2.000 |

with `p_fit = 2.002`, `p_res = 1.998–1.999`, `p_R = 2.002`,
Richardson-extrapolated error `7.56e-09` (≈ 10³ smaller than the finest raw
error), and pulse energy-drift order ≈ 5 with the adjoint-consistent discrete
gradient. Full table and provenance: `numerics/protocol/demo_output.json`.

Machine-readable report, schema `n0-convergence-report/v1`:

| field | type | required | meaning |
|---|---|---|---|
| `schema` | string | yes | must equal `n0-convergence-report/v1` |
| `node_id`, `class_id` | string | yes | `N0`, `AF-WCC-SCALAR-SPH` |
| `scheme_id` | string | yes | stable identifier of the scheme, not of the run |
| `implementation`, `script_sha256` | string | yes | path + hash of the generating script |
| `declared_order`, `cfl` | number | yes | `p_decl`, `λ` |
| `exact_family`, `measurement_times` | string, list | yes | V1/V2 declarations |
| `resolutions`, `linf_errors` | list | yes | ladder and `e_∞`, coarse → fine |
| `l2_errors` | list | recommended | RMS errors |
| `residual_orders` | list | recommended | T2 |
| `richardson_order` | number | recommended | T3 |
| `energy_drift`, `energy_diagnostic` | list, string | recommended | T4a; the diagnostic must be named exactly |
| `energy_functional` | object | yes (adopted 2026-09-11) | R1: `name`, `structural_class` ∈ {`exact_discrete`, `convergent`, `consistency_only`}, `solver_tolerance` |
| `order_uncertainty` | object | yes (adopted 2026-09-11) | R5/T7: `fit_order`, `standard_error`, `pair_spread_half_range` |
| `stable`, `non_degeneracy` | bool, object | yes | V5, V2 attestation |
| `fitted_order`, `wall_seconds`, `notes` | any | optional | reporting |

## 8. Worked synthetic example

Command: `python3 numerics/protocol/convergence_demo.py`
Output: `numerics/protocol/demo_output.json` (+ two canonical reports).
The script is self-contained (central D2 + RK4; backward Euler + Thomas; both
under the scope lock) and cross-checks the peers' candidate implementation at
the end. Numbers below are from the actual run, not illustrative.

### E1 — turning-point degeneracy vs broadband immunity

Standard central D2 + RK4, declared order 2, λ = 0.25, L∞ pair orders over
64 → 512:

| family | t* | pair orders | finest \|e\|_∞ |
|---|---|---|---|
| single mode | 0.35 | 2.00, 2.00, 2.00 | 1.78e-06 |
| single mode | **0.50** | **4.00, 4.00, 4.00** | 3.09e-11 |
| two modes | 0.50 | 2.00, 2.00, 2.00 | 9.80e-06 |
| two modes | 0.35 | 2.00, 2.00, 2.00 | 6.55e-06 |

Mechanism: for a single Fourier mode the leading error is a phase error
proportional to `sin(k t*)`; at a turning point (`sin(2π·0.5) = 0`) it vanishes
and the first surviving term is O(h⁴). A two-mode family has no common turning
point, so the same scheme reads 2.00 at the same time. **Consequence:** a
single-mode, single-time order measurement is not order evidence (V1/V2).

### E2 — certification at a generic time (two modes, t* = 0.35)

| estimator | value | criterion |
|---|---|---|
| pair orders (L∞) | 2.005, 2.001, 2.000 | within ±0.30 of 2 |
| fitted slope | 2.002 | within ±0.30 of 2 |
| truncation residual order | 1.998, 1.999, 1.999 | ≥ 1.70 |
| Richardson order | 2.002 | within ±0.30 of 2 |
| Richardson-extrapolated error | 7.56e-09 | ≤ finest raw error 6.55e-06 |

### E3 — off-by-one stencil: rejected on stability

The shifted stencil `(v[j+2] − 2v[j+1] + v[j])/h²` is non-normal with growing
modes: `max|v|` = 3.3e13, 8.3e31, 5.8e69, 3.2e146 over the ladder, all rungs
flagged unstable. The protocol must run FC1 before reading any order from such a
run; the order numbers themselves are meaningless.

### E4 — stable wrong-order control: rejected on order

Backward Euler in time + central D2 (stable, `p_time = 1`, declared order 2):

| measurement | pair orders | fit |
|---|---|---|
| generic t* = 0.35 | 1.018, 1.008, 1.005 | 1.010 |
| turning t* = 0.50 | 1.047, 1.030, 1.016 | — |

The audit tool rejects this report on C3/C4/C6/C7 (exit 1) while C5 residual
still passes at 1.998 — the spatial stencil is correct and only the time order
is wrong. **This falsifies the assignment's falsifier "protocol cannot detect a
wrong order" for this control**: the protocol does detect it, on the order
criterion, without relying on the residual test.

### E5 — invariant diagnostics are diagnostic-dependent

Same pulse run, two energy functionals:

| diagnostic | drift 64 → 512 | drift order |
|---|---|---|
| discrete gradient `h/2 Σw² + h/2 Σ(Dv)²` | 6.93e-07 → 2.51e-11 | 4.79, 4.97, 4.99 |
| `np.gradient` quadrature for `v_r` | 2.42e-02 → 3.74e-04 | 2.01, 2.00, 2.00 |

The RK4 solver is identical; the measured drift order is set by the diagnostic.
Any invariant criterion must name the functional, the resolution and the
diagnostic's own convergence. Static identity at n = 256:
`|H_v − E_u/(4π)| / H_v = 1.58e-04`.

### E6 — in-situ cross-check

`numerics/tests/flat_wave.py` (peers' candidate, single-mode family, λ = 0.25):

| measurement time | L∞ pair orders | finest e_2 |
|---|---|---|
| t = 0.40 | 2.000, 2.000, 2.000 | 1.04e-06 |
| t = 0.50 | **4.00, 4.00, 4.00** | 2.19e-11 |

Scheme agreement at n = 256, t = 0.40: `max|Δv| = 0.0`, bitwise equal — the
shared central-D2 + RK4 path is being stepped identically by two independent
drivers.

## 9. In-situ finding: `G1_standing_order2: false` is a false negative

`numerics/results/flat_wave_convergence.json` (study `family="standing"`,
`order_scheme=2`, `cfl=0.25`, `t_end=0.5`) reported
`order_l2 = [4.006, 4.003, 4.001, 4.001]`, so its band check 1.8–2.2 failed and
`gates.G1_standing_order2 = false`. E1 and E6 reproduce this exactly with the
peers' own `solve_case` (direct measurements with the current code):

- at `t_end = 0.40` the same code and family give **2.00**;
- at `t_end = 0.50` they give **4.00**;
- `sin(2π·0.5) = 0`: 0.50 is the turning point of the single mode used.

**Revision note (checkpoint CP6).** The `G1 = false` observation was the
pre-23:22:52 revision of the results file. The current pinned revision
(`e9e124227c4d2932`, generated 23:36:43 by candidate `8b52014d…`) moves the
standing study to `t_end = 0.37` and reports drift `2.83e-10 → 1.62e-14`
(order ≈ 5); `G1`, `G3`, `G9` and all other candidate gates now read true. The
finding below therefore documents the earlier revision and the mechanism that
forced the change; the protocol's V2 rule and the E1/E6 controls remain the
reason a single-mode measurement at `t_end = 0.5` cannot be used as order
evidence.

Therefore G1's failure is a **test-design degeneracy (false negative)**, not a
scheme-order defect. It is also a latent false-positive risk: any scheme whose
error is dominated by a phase error would be accepted as order 4 by the same
measurement. Recommended remediation (owner: numerics lead, not this worker):

1. do not use the single-mode `t_end = 0.5` measurement as order evidence;
2. use the two-mode family, or the pulse family (already measuring 2.0), or a
   generic time such as `t_end = 0.4`;
3. add T2 (truncation residual) as the primary order certificate, since it does
   not involve the numerical solution and cannot be fooled by phase
   cancellation;
4. record the remediation in the gate so a future reader does not "fix" a
   correct stencil.

This is a reported finding with reproducible evidence; it changes no file owned
by another agent and claims no node.

### 9.1 Scheme-specific invariants (review `astra-adj2-03`)

`numerics/protocol/scheme_independence_review.md` resolves the replication
disagreement's invariant gap with the following measured facts, now encoded as
R1–R4 (§4) and FC7 (§5):

- the pinned cnfd "own energy" was algebraically the leapfrog staggered energy
  (identity gap 2.07e-15), so its `6.6e-8` drift was the harness test, not a CN
  invariant;
- each scheme conserves its own functional to roundoff (lffd 3.38e-15, cnfd
  1.11e-14) and shows a ≈4th-order-converging mismatch against the other's;
- the candidate's G3 `1e-8` threshold flips from FAIL to PASS for cnfd between
  `dr = 0.05` (6.59e-8) and `dr = 0.025` (4.17e-9), so it is not a scheme
  property; it is also unreachable with the candidate's own `np.gradient`
  diagnostic (finest drift 9.41e-06);
- the adjudication's own falsifier is triggered at the harness threshold:
  cnfd passes `drift_tol = 1e-6`.

## 10. What this protocol does and does not establish

Establishes (evidence: §8, reproducible command in §8):

- the protocol's criteria separate a correct order-2 scheme (E2: all estimators
  2.00, audit PASS) from a stable wrong-order scheme (E4: audit FAIL on order);
- an unstable order-defective operator is rejected before its order is read
  (E3);
- the turning-point degeneracy is real, reproducible, and caught by V1/V2 (E1,
  E6);
- invariant criteria are only meaningful with a named diagnostic (E5).

Does **not** establish:

- that N0 passes — the N0 artifacts belong to other assignments and are
  `unverified`;
- any statement about self-gravity, collapse, horizons, critical behaviour,
  radiation at I+, WCC or SCC;
- that `AF-WCC-SCALAR-SPH` binding is frozen — the F0 taxonomy artifact
  `research_map/formulation_taxonomy.yaml` is absent on disk, so the binding
  remains provisional;
- that a passing report certifies scheme *identity*: the protocol measures the
  observed order of the submitted code path, not that the code implements the
  scheme it names. The remaining falsifier is a stable scheme with a plausible
  residual order and a compensating error that passes every V2-valid time; no
  such control is constructed here.

## 11. Reproduction and provenance

```bash
python3 numerics/protocol/convergence_demo.py
python3 numerics/protocol/audit_convergence_report.py --root . numerics/protocol/demo_report_standard.json      # exit 0
python3 numerics/protocol/audit_convergence_report.py --root . numerics/protocol/demo_report_wrong_order.json  # exit 1
python3 numerics/protocol/build_gate_reports.py                                                                 # real schemes, PASS + agree
```

Artifacts (hashes recorded in the corresponding `comms/outbox` artifact event,
computed after the final write):

| artifact | role |
|---|---|
| `numerics/protocol/convergence_protocol.md` | this spec (deliverable) |
| `numerics/protocol/convergence_demo.py` | worked synthetic example generator |
| `numerics/protocol/demo_output.json` | full worked-example output |
| `numerics/protocol/demo_report_standard.json` | canonical report, audit PASS |
| `numerics/protocol/demo_report_wrong_order.json` | canonical report, audit FAIL |
| `numerics/protocol/audit_convergence_report.py` | reference enforcement of FC0–FC9 |
| `numerics/protocol/scheme_independence_review.md` | review `astra-adj2-03`: functional-aware thresholds and order uncertainty |
| `numerics/protocol/scheme_independence_check.py` | read-only evidence driver for the review |
| `numerics/protocol/scheme_independence_evidence.json` | raw evidence for the review |
| `numerics/protocol/build_gate_reports.py` | builds `n0-convergence-report/v1` reports for the two real replication schemes |
| `numerics/protocol/report_lffd.json`, `report_cnfd.json` | real-scheme reports, both audit PASS C0–C9 |
| `numerics/protocol/gate_reports_summary.json` | end-to-end audit + cross-scheme agreement summary |

Environment: Python 3.10.12, NumPy 2.2.6, Linux x86_64; demo runtime ≈ 2.4 s on
one core; deterministic, no network, no randomness.
