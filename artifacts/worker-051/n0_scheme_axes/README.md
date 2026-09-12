# W051-N0-SCHEME-AXES-02 — spatial/temporal operator-axis multiplicity of the N0 replication schemes

**Worker:** worker-051 · **Node:** N0 · **Class:** `AF-WCC-SCALAR-SPH` (flat-space test-field
calibration sub-case only) · **Gate target:** none (evidence for G-NUM, not a verdict) ·
**Verdict:** `falsifier_not_triggered` · **Run:** 2026-09-12T00:35:10+0800 · **Runtime:** 16.5 s

All artifacts are `validation_status: unverified`; nothing here is a gate verdict, a node
completion, or a class claim. No canonical or published file was modified.

## 1. Question

`deepseek-flash-13`'s published claim (map claim, 2026-09-12) states that the N0 flat-space
order-2 result "is reproduced by three methodologically independent schemes" and that
"independence holds along time integration, spatial discretisation and energy functional".

The three schemes live in the frozen module
`numerics/tests/flat_wave_replication.py` at sha256
`8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422`:

| scheme | spatial discretisation | time integrator |
|---|---|---|
| `lffd` | 3-point FD | explicit leapfrog |
| `cnfd` | 3-point FD | implicit Crank–Nicolson |
| `cnfem` | P1 consistent-mass FEM | implicit Crank–Nicolson |

The bounded question: **how many distinct spatial operators and how many distinct time
integrators do those three schemes actually contain, and is the missing cell of that design
also order 2?** This extends the falsifier recorded by worker-051's previous N0 task
(`W051-N0-AXIS-DIRECT-01`), which showed that the shared `psi = r*phi` reduction and the
regular-centre rule are not independent axes.

## 2. Method (all measurements from the frozen module)

1. **Operator extraction with code-path proof.** The published solvers satisfy exact one-step
   identities that pin their semi-discrete spatial operators:
   - leapfrog: `d2 = A·psi` exactly;
   - CN-FD: `d2 = A·(psi_new + psi_old)/2` exactly, with `A` the solver's own `self.A`
     attribute compared entry-by-entry against the FD matrix built from the same tridiagonal
     coefficients;
   - CN-FEM: `M·d2 = −K·(psi_new + psi_old)/2` exactly.
   The check is a random-state one-step drive of the published classes, not a re-derivation.
2. **Distinctness.** Two consistent discretisations do **not** converge to each other in matrix
   norm (the norm is dominated by grid-scale modes), so distinctness is measured where it is
   well defined: the exact grid-Nyquist response at a central interior row, and the low-mode
   (smooth) relative difference whose decay order tests second-order consistency.
3. **2×2 completion.** The missing cell `femlf` (leapfrog + P1 consistent-mass FEM) is
   implemented in this artifact and all four cells are run through the **published**
   `order_study` at 4 rungs (`dr = 0.2/0.1/0.05/0.025`, `cfl = 0.5`, pulse `r0 = 10`,
   `sigma = 1.5`, `r ∈ [0,30]`, `t_end = 6`).
4. **Isolated spatial order.** For every cell, the error is extrapolated to `dt → 0` at each
   `dr` (three CFL values, linear fit in `dt²`), then the spatial order is fitted across rungs.
5. **Controls.** Published-order reproduction, determinism, start-step semantics, and exactness
   on `u = r(R−r)` (`u'' = −2`).

## 3. Results

### 3.1 The three published schemes span 3 of the 4 cells of a 2×2 design

| cell | spatial | time | 4-rung mixed order | isolated spatial order (`dt → 0`) |
|---|---|---|---|---|
| `lffd` (published) | 3-point FD | leapfrog | 1.9966248643204345 | 1.9991041829339793 |
| `cnfd` (published) | 3-point FD | Crank–Nicolson | 1.9953510343613228 | 2.0006694566606362 |
| `cnfem` (published) | P1 FEM | Crank–Nicolson | 1.9888598802332438 | 2.00048888143909 |
| `femlf` (added here) | P1 FEM | leapfrog | 2.001045498143482 | 1.9999931851852406 |

All four cells: monotone errors, inside the protocol band `|p − 2| ≤ 0.3` in both the mixed and
the `dt → 0` spatial measurement. So after completion the design is a full
**2 spatial × 2 time factorial**, not three mutually independent schemes.

### 3.2 `lffd` and `cnfd` share the identical FD spatial operator

| measurement | value |
|---|---|
| `cnfd.self.A` vs FD matrix built from the same coefficients | **0.0** (max abs entry diff) |
| leapfrog one-step identity residual w.r.t. the same FD matrix | 3.70e-16 |
| CN-FD one-step identity residual | 7.85e-16 |
| CN-FEM identity residual | 1.40e-15 |

The two schemes differ in the time integrator and the start step, not in the spatial operator.
(`lffd`'s published starter uses the analytic `psi_tt0`; `cnfd` uses the discrete acceleration;
the measured gap is 3.86e-8 relative, consistent with the `h²` truncation of `A·psi0`.)

### 3.3 The FEM operator is genuinely distinct, and also second-order

| measurement | dr = 0.2 | 0.1 | 0.05 | 0.025 | fitted order |
|---|---|---|---|---|---|
| smooth-mode rel. difference `max|(L_fem−A)u| / max|A u|`, `u = sin(πr/R)` | 7.31e-5 | 1.83e-5 | 4.57e-6 | 1.14e-6 | **2.0000** |
| Rayleigh mode-1 rel. difference | 7.31e-5 | 1.83e-5 | 4.57e-6 | 1.14e-6 | **2.0000** |
| Nyquist implied eigenvalue `λ_fd` / `λ_fem` (central row) | 100 / 300 | 400 / 1200 | 1600 / 4800 | 6400 / 19200 | ratio **3.0** exactly (dev ≤ 1.9e-16) |
| full-matrix relative Frobenius difference | 1.483 | 1.486 | 1.487 | 1.488 | not a convergence metric (boundary/grid-scale dominated) |
| boundary-row relative difference | 0.8231 | 0.8231 | 0.8231 | 0.8231 | structural, constant |

The grid-Nyquist response ratio of exactly 3 proves the operators are not the same matrix; the
order-2 decay of the smooth-mode difference proves both are second-order consistent. The
constant full-matrix Frobenius difference and the 0.82 boundary-row difference are reported so
that nobody mistakes the matrix norm for a convergence metric.

### 3.4 Controls

* **Published reproduction:** the three published 4-rung orders from
  `numerics/tests/n0_order_4rung.json#c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a`
  are reproduced with **absolute delta 0.0** (bitwise) in this harness.
* **Determinism:** `femlf` `dr = 0.05`, `cfl = 0.5` rerun — final `psi` bitwise equal.
* **Exactness:** FD on `u = r(R−r)` dev 5.8e-11 (all rows); FEM identity
  `M(−2·1) = −K·u` dev 2.4e-12 on interior rows (truncated FEM boundary rows, `h/3`, reported
  separately and excluded).
* **Start-step:** discrete-acceleration starters reproduce to 1.11e-16; leapfrog analytic-Taylor
  starter residual 0.0.

## 4. Verdict and falsifier

**Verdict:** across the three published replication schemes there are **2 distinct spatial
discretisations** (3-point FD, P1 consistent-mass FEM) and **2 distinct time integrators**
(leapfrog, Crank–Nicolson), covering 3 of 4 cells; the missing cell (FEM + leapfrog) is
order-2 in band and completes a 2×2 design. The statement that spatial-discretisation
independence holds across the three schemes is therefore supported at multiplicity **two**, not
three: `lffd` and `cnfd` are the same spatial discretisation with different time integrators.
The order-2 result itself is *strengthened*, not weakened: all four cells, including their
`dt → 0` isolated spatial orders, are inside the band.

**Falsifier (as run, `falsifier_not_triggered`, 6/6 checks pass):** the finding is falsified if
(a) `lffd` and `cnfd` do not use the identical spatial operator; (b) the FEM and FD operators are
not distinct at grid scale (Nyquist ratio 1) or are not both second-order consistent at low
modes; (c) the extracted operators fail their published code-path/start-step/exactness checks;
(d) any of the four cells leaves the `|p−2| ≤ 0.3` band or loses monotonicity, in mixed or in
`dt → 0` isolated spatial order; (e) the three published cells are not reproduced at `< 1e-9`.

## 5. Scope limits and non-claims

* Flat-space test field on a fixed Minkowski background; no gravity coupling, no N1, lock
  respected (`numerics/spherical_solver/` not created or touched).
* Operator comparison is on the published uniform node-centred grid only.
* `AF-WCC-SCALAR-SPH` calibration sub-case; this cannot be cited as an instance of the class.
* Order claims hold for the published harness configuration and 4 rungs only.
* `femlf` is new code **in this artifact**, not a published scheme.
* Non-claims: no node status change, no `validation_status=passed`, no gate verdict, no theorem,
  no edit to canonical or published numerics files.

## 6. Artifacts and reproduction

| artifact | sha256 |
|---|---|
| `artifacts/worker-051/n0_scheme_axes/n0_scheme_axes_051.py` | `9b08d95effcfe88e8d1dee0ae8d37f5c4f456b831aaa3266c6faceb53e7026b0` |
| `artifacts/worker-051/n0_scheme_axes/report.json` | `7ddac5e40d9e134fe73cdb19c85950cd63a9754d9b5518e580503b2e6dcef100` |
| `artifacts/worker-051/n0_scheme_axes/stdout.txt` | `9de1acf61e8d9b67d5a1ca2dc41e40a9142edaf9ccb2b2b8a258275c3d00b7b6` |
| `artifacts/worker-051/n0_scheme_axes/README.md` | (this file) |

Pinned inputs: `numerics/tests/flat_wave_replication.py#8ade1cdc163ea420…`,
`numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313…`,
`numerics/tests/n0_order_4rung.json#c88146a1375c50f0…`.

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-051/n0_scheme_axes/n0_scheme_axes_051.py
```

Next falsifier for a reviewer: re-run at the same pinned module hash on a different grid
(e.g. `r_max = 40`, or a different pulse family) and check that the FEM/FD Nyquist ratio is
still 3 and that the `femlf` cell stays in band. Do not promote this to a gate verdict; it is
input to lead-numerics/lead-audit adjudication.
