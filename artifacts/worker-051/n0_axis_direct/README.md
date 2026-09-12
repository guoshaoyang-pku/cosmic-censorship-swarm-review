# W051-N0-AXIS-DIRECT-01 — independent direct-variable test of the N0 shared axes

Worker: `worker-051`. Node `N0`, class sub-case `AF-WCC-SCALAR-SPH` (fixed Minkowski, test
field, spherical symmetry, massless scalar, **no self-gravity, no WCC/SCC statement**).
Task taken from the open N0 queue: the published replication
(`numerics/results/flat_wave_replication.json`) lists four axes it did **not** test —
`psi = r*phi` reduction, the Dirichlet origin condition, the Taylor start, and the
manufactured-solution method — and its own falsifier is *"a demonstration that the shared
Taylor start / psi=r\*phi reduction carries a discretization bug common to all three
schemes."* This artifact attacks exactly that falsifier.

## What was run

`n0_axis_051_direct.py` (numpy only, deterministic) evolves the **physical field `u = phi`
directly**, with no `psi = r*phi` reduction anywhere:

* `u_tt = u_rr + (2/r) u_r`, implicit Crank-Nicolson, `B = I - dt^2/2 L`;
* regular-centre rule `L u(0) = 6 (u_1 - u_0)/dr^2`;
* no Taylor start in the headline run — start is the **exact** time slice `u(., dt)`;
* same exact pulse family as the harness, `psi = F(r-t) - F(-r-t)`, `u = psi/r`;
* two cases: `pulse_far` (r0=10, sigma=1.5, the published harness case, origin quiet,
  `u(0,t) <~ 1e-9`) and `pulse_origin` (r0=2, sigma=1.0, added here, `u(0,0) ~ 0.54` so the
  origin is actually excited);
* `dr = 0.2/0.1/0.05`, `cfl = 0.5`, `r_max = 30`, `t_end = 6` (published harness config).

Controls: (i) a byte-faithful re-implementation of the published `cnfd` (wiring check);
(ii) four different origin rules — regular `6/dr^2`, `2/dr^2`, garbage `(54321 u_1 -
12345 u_0)/dr^2`, and `u(0)` pinned to 17 every step; (iii) Taylor vs exact start;
(iv) `cfl -> 0` extrapolation at fixed `dr` to separate spatial from temporal error.

## Result (all numbers in `report.json`)

| check | measured |
|---|---|
| published wiring (`cnfd` re-implementation) | fit order **1.9934777747080452** vs published **1.9934777747080437**; row errors <= 2.5e-15 relative |
| direct order, `pulse_far` | psi-L2 fit **1.991437** (pairs 1.9875, 1.9954); E_psi = 1.476e-2, 3.723e-3, 9.337e-4 |
| direct order, `pulse_origin` | psi-L2 fit **1.985789** (pairs 1.9780, 1.9935); E_psi = 4.022e-2, 1.021e-2, 2.564e-3 |
| reduction identity (direct psi vs reduced psi) | max relative difference **3.9e-13** / 2.3e-13 |
| origin decoupling (4 rules, interior) | max absolute difference **0.0 (bitwise)** in both cases, while `u(0)` differs by **>= 16.9** between rules |
| algebraic identity `r_i (L_sph u)_i = (Delta_1D (r u))_i` | `a_1 == 0.0` exactly; max relative residual **2.4e-16** |
| Taylor-start vs exact-start order delta | **<= 0.0025** (four scheme/case pairs) |
| spatial order isolated from temporal error | **1.99974** / **1.99988** from `dt -> 0` intercepts; linear-in-`dt^2` fits R^2 >= 0.9999998 |
| analytic origin-stencil check | regular rule 2nd order (fit 1.9832); `2/dr^2` rule has 66.7% relative error at `r=0` |
| determinism | bitwise equal on a repeated run |

## Interpretation

The `psi = r*phi` reduction and the origin rule are **not independent discretisation axes**
for this grid/operator pair. On the uniform node-centred grid the identity
`r_i (L_sph u)_i = (Delta_1D (r u))_i` holds algebraically on interior rows, and the first
interior row's lower coefficient is exactly zero, so the origin node never feeds the
interior — any origin rule gives the same interior evolution, and the direct scheme is the
reduced scheme in different variables. The falsifier is therefore **not triggered**; more
strongly, the two axes it names are dissolved rather than merely untested. The one
genuinely independent shared axis, the Taylor start, changes the measured order by at most
0.0025. The isolated spatial order is 2.000 to 4 decimal places, so the published order-2
number is spatial and not a spatio-temporal coincidence.

Limit: the structural identity is specific to this node-centred grid with `r_1 = dr` and
the `1/r` form. A staggered / finite-volume / non-uniform scheme, or a non-trivial origin
closure on the reduced variable, is not covered.

## Falsifier (machine-checkable, re-runnable)

CONFIRMED if a faithful rerun shows any of: (a) direct-equivalent psi departs from reduced
psi by > 1e-12 relative; (b) any origin rule moves an interior node by > 1e-12 absolute
while the rules genuinely differ at `r = 0`; (c) direct psi-L2 order leaves `[2.0 +/- 0.3]`
or Taylor-vs-exact start orders differ by > 0.05; (d) spatial order from `cfl -> 0`
intercepts leaves `[2.0 +/- 0.3]`; (e) the reduced re-implementation fails to reproduce the
published `cnfd` numbers to < 1e-6 relative.

## Reproduce

```bash
cd workdir/ai4math-swarm
python3 artifacts/worker-051/n0_axis_direct/n0_axis_051_direct.py   # ~9 s wall
```

## Provenance

Artifacts are `validation_status = unverified`: no reviewer verdict exists. The controller
and group leads own promotion; this worker claims no node completion, no gate verdict, and
no theorem.

| file | sha256 |
|---|---|
| `n0_axis_051_direct.py` | `e0028f37098b4e5394e528a12db33e3a0439ead7fe888951d377f09b407bf5c2` |
| `report.json` | `038c57576146d8e909cb123301050b975a76938db62155be8bb1c0f31ae332de` |
| `stdout.txt` | `ac9fd64e95e5f332d0def76e9efbb74bf5f595ded539a51be684d800a8148b3b` |

Inputs read (hashes of the bytes read during this run, recorded in `report.json`):
`numerics/results/flat_wave_replication.json` `298a4d921c22`,
`numerics/tests/flat_wave_replication.py` `8ade1cdc163e`,
`artifacts/flash-04/n0_acceptance/reference_solutions.py` `d38bca43bf87`,
`research_map/formulation_taxonomy.yaml` `276009f4f63d`,
`research_map/research_map.json` `7f8792f85f0c`.
