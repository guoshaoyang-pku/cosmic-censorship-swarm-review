# W051-N0-SCHEME-AXES-03 — grid/pulse transfer of the N0 scheme-axis multiplicity finding

**Worker:** worker-051 · **Node:** N0 · **Class:** `AF-WCC-SCALAR-SPH` (flat-space test-field
calibration sub-case only) · **Gate target:** none (evidence for G-NUM, not a verdict) ·
**Verdict:** `falsifier_not_triggered` (9/9 pre-registered checks) · **Run:**
2026-09-12T00:41:27–00:43:25+0800 · **Runtime:** 117.9 s

All artifacts are `validation_status: unverified`; nothing here is a gate verdict, a node
completion, or a class claim. No canonical or published file was modified; no self-gravitating
code was written or run (`numerics/spherical_solver/` untouched, `numerics_lock` respected).

## 1. Question

This is the falsifier that worker-051's previous bounded task recorded verbatim as its next
test (README of `artifacts/worker-051/n0_scheme_axes`, section 5):

> "re-run at the same pinned module hash on a different grid (e.g. `r_max = 40`, or a different
> pulse family) and check that the FEM/FD Nyquist ratio is still 3 and that the `femlf` cell
> stays in band."

The claim under test is that at the frozen module
`numerics/tests/flat_wave_replication.py#sha256:8ade1cdc163ea420…` the three published N0
schemes span only **2 spatial discretisations × 2 time integrators** (3 of 4 design cells),
`lffd` and `cnfd` share the identical 3-point FD operator, the FEM operator is distinct
(grid-Nyquist response ratio exactly 3) and second-order consistent, and the added fourth cell
`femlf` is order 2 in the protocol band `|p − 2| ≤ 0.3`.

The transfer changes **only the configuration**; everything else is imported from the two
hash-pinned modules below.

## 2. Pinned inputs (verified before measuring; drift ⇒ refuse and report)

| input | sha256 |
|---|---|
| `numerics/tests/flat_wave_replication.py` (published module) | `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `numerics/tests/n0_order_4rung.json` (published orders) | `c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a` |
| `artifacts/worker-051/n0_scheme_axes/n0_scheme_axes_051.py` (prior harness) | `9b08d95effcfe88e8d1dee0ae8d37f5c4f456b831aaa3266c6faceb53e7026b0` |
| `artifacts/worker-051/n0_scheme_axes/report.json` (prior result) | `7ddac5e40d9e134fe73cdb19c85950cd63a9754d9b5518e580503b2e6dcef100` |

All five resolved at run time (`F1` pass).

## 3. Configurations (pre-registered)

| id | kind | `r_max` | `t_end` | pulse `r0` | pulse `sigma` | outer-wall margin | outer tail at `t_end` |
|---|---|---|---|---|---|---|---|
| `C0_published_control` | control | 30 | 6 | 10.0 | 1.5 | 9.33 σ | 1.2e-19 |
| `T1_grid_r40` | transfer | **40** | **20** | 10.0 | 1.5 | 6.67 σ | 2.2e-10 |
| `T2_pulse_narrow` | transfer | 30 | 6 | **6.0** | **0.9** | 20.0 σ | 1.4e-87 |
| `T3_pulse_wide` | transfer | 30 | **5** | **8.0** | **2.5** | 6.8 σ | 9.1e-11 |

Pre-registered wall-cleanliness criterion: `r0 + t_end + 4σ < r_max` **and** outer tail
`< 1e-9`; all four configurations pass (`F3`), so the outer Dirichlet wall cannot dominate the
L2 error that drives the order fits. `T1` moves the pulse to `r = 30`, exercising the grid
region that the published `r_max = 30` run never sampled.

## 4. Method

1. **Control reproduction.** `C0` re-runs the published configuration through the pinned
   module: the three published 4-rung orders are reproduced **bitwise** (absolute delta `0.0`
   against `n0_order_4rung.json`) and the prior artifact's `femlf` mixed order is reproduced to
   `< 1e-12`. Determinism: one transfer case is re-run bitwise equal.
2. **Operator extraction.** The published solvers are driven one non-starter step from a common
   random state; exact identities pin the semi-discrete operators (`d2 = A·ψ` for leapfrog;
   `d2 = A·mid` for CN-FD including the solver's own `self.A`; `M·d2 = −K·mid` for CN-FEM;
   `M·d2 = −K·ψ` for the added `femlf`). Rebuilt matrices are compared entry-by-entry.
3. **Distinctness where it is well defined.** Grid-scale (Nyquist) response at a central
   interior row, and the low-mode relative difference `max|(L_fem − A)u| / max|A u|` for
   `u = sin(πr/r_max)`, whose decay order tests second-order consistency. The full-matrix
   Frobenius difference is not used as a convergence metric.
4. **Order studies.** Mixed 4-rung order at `cfl = 0.5` over `dr = 0.2/0.1/0.05/0.025`; and
   isolated spatial order by linear extrapolation to `dt → 0` in `dt²` over
   `cfl = 0.5/0.25/0.125` at each rung.

## 5. Results

### 5.1 Mixed and isolated orders transfer inside the band

Mixed 4-rung order `|` isolated spatial order (`dt → 0`):

| config | `lffd` | `cnfd` | `cnfem` | `femlf` |
|---|---|---|---|---|
| `C0_published_control` | 1.996625 \| 1.999104 | 1.995351 \| 2.000669 | 1.988860 \| 2.000489 | 2.001045 \| 1.999993 |
| `T1_grid_r40` | 1.999490 \| 1.999565 | 1.996165 \| 2.000325 | 1.999072 \| 1.999574 | 2.000826 \| 1.999864 |
| `T2_pulse_narrow` | 1.998031 \| 1.998792 | 1.989976 \| 2.000902 | 1.995364 \| 1.999033 | 2.002493 \| 1.999709 |
| `T3_pulse_wide` | 1.995976 \| 1.999040 | 1.996793 \| 2.000567 | 1.989150 \| 2.001054 | 2.000393 \| 2.000017 |

All 32 order fits are inside `|p − 2| ≤ 0.3` with monotone error ladders; the worst deviation
over the whole transfer is 0.0105 (`cnfd`, `T2`). So the band membership of every one of the
four cells transfers to the new grid and to both new pulse families.

### 5.2 Operator multiplicities are grid- and pulse-independent

| measurement | at `r_max = 30` | at `r_max = 40` |
|---|---|---|
| `cnfd.self.A` vs rebuilt FD matrix (max abs entry diff) | **0.0** | **0.0** |
| leapfrog one-step identity residual | 4.1e-16 | 3.0e-16 |
| CN-FD one-step identity residual | 8.8e-16 | 1.8e-15 |
| CN-FEM identity residual | 1.2e-15 | 1.2e-15 |
| `femlf` identity residual | 3.2e-16 | 1.4e-15 |
| FEM/FD grid-Nyquist response ratio (all four rungs) | 3.0000000000000004 | 3.0000000000000004 … 3.000000000000001 |
| FD Nyquist deviation from `4/h²` | 0.0 | 0.0 |
| FEM Nyquist deviation from `12/h²` | 1.9e-16 | 1.9e-16 … 3.8e-16 |
| smooth-mode difference order `max|(L_fem−A)u|/max|A u|` | **1.99999909** | **2.00001032** |

`lffd` and `cnfd` use the **identical** FD spatial operator at both grids (exactly zero matrix
difference), the FEM operator is genuinely distinct (ratio 3) and second-order consistent at
both grids. The `lffd`/`cnfd` multiplicity finding is therefore algebra, not a
configuration artifact.

## 6. Verdict and falsifier

**Verdict:** `falsifier_not_triggered` — 9/9 checks pass:

| check | result |
|---|---|
| `F1_hash_pins_resolve` | pass |
| `F2_control_published_orders_reproduced_bitwise` | pass (delta 0.0) |
| `F2b_control_prior_femlf_order_reproduced` | pass (delta 0.0) |
| `F3_all_configs_boundary_clean` | pass |
| `F4_lffd_cnfd_share_FD_operator_at_both_grids` | pass |
| `F5_fem_fd_distinct_and_second_order_at_both_grids` | pass |
| `F6_all_cells_mixed_order_in_band_all_configs` | pass |
| `F7_all_cells_isolated_spatial_order_in_band_all_configs` | pass |
| `F8_determinism_bitwise` | pass |

**Falsifier (pre-registered):** the finding is falsified if, at these pins, any pin does not
resolve; the published orders are not reproduced bitwise; an outer wall is not tail-clean;
`lffd`/`cnfd` do not share the identical FD operator; the FEM/FD Nyquist ratio leaves 3
(tol 1e-12) or the smooth-mode difference order leaves `[1.7, 2.3]`; any cell leaves the
`|p − 2| ≤ 0.3` band or loses monotonicity in mixed or `dt → 0` isolated order; or a rerun is
not bitwise deterministic.

**Effect on the parent claim:** the transfer *strengthens* the previous finding — the "2
spatial × 2 time, 3 of 4 cells" multiplicity and the order-2 band membership are not artifacts
of the published `r_max = 30`, `r0 = 10`, `sigma = 1.5` configuration.

## 7. Scope limits and non-claims

* Flat-space test field on a fixed Minkowski background; no gravity coupling, no N1, lock
  respected.
* The transfer varies grid and pulse family only; it **re-uses** the pinned operator helpers,
  so it cannot detect a bug shared by the previous harness. Implementation independence is a
  different axis, covered by workers 046/055 (direct-`φ`, RK4, l'Hôpital origin).
* Order claims hold for the four-rung ladders and the three-cfl `dt → 0` fits as configured.
* `femlf` is code in the pinned prior artifact, not a published scheme.
* Non-claims: no node status change, no `validation_status=passed`, no gate verdict, no theorem,
  no edit to canonical or published files.

## 8. Artifacts and reproduction

| artifact | sha256 |
|---|---|
| `n0_axes_transfer_051.py` | `c1ff096e6870ef7039484e13ef6a3a0ea411b51e99a28f71da9a9b672290bcfd` |
| `report.json` | `d02b76c3cad8777560effbfc0ac3c1582a3f4fb873c6daf4d6385b30e3df6300` |
| `stdout.txt` | `9bcf3c3308611373d319d2affee21d9dd6b2df7d272f82fd648f70014d0cb977` |
| `CHECKPOINT.json` | see `SHA256SUMS` |
| `README.md` | see `SHA256SUMS` |

Reproduce (≈2 min single process):

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-051/n0_scheme_axes_transfer/n0_axes_transfer_051.py
```

Events: `comms/outbox/worker-051.jsonl`, task `W051-N0-SCHEME-AXES-03`. Next falsifier left
for lead-numerics/lead-audit: adjudicate whether the replication's independence wording should
be re-labelled "2 spatial × 2 time, 3 of 4 cells, transferred to `r_max = 40` and two pulse
families", and whether this closes the `W051-N0-SCHEME-AXES-02` next-falsifier.
