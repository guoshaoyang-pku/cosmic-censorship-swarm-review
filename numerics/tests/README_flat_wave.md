# N0 candidate — flat-space spherical scalar-wave calibration (draft, unverified)

Worker-20 breadth artifact for map node **N0** (`research_map/research_map.json`),
declared path `numerics/tests/flat_wave.py`. Class binding **AF-WCC-SCALAR-SPH**
(PROVISIONAL). **No completion is claimed** for N0; `validation_status` is
`unverified` until a lead binds the class and an independent reviewer accepts.

## Why this exists

No assignment was present in `comms/inbox` when worker-20 started. The immediate
queue (`research_map/ASTRA_HANDOFF.md`) lists N0 as the only flat-space numerics
item allowed under the numerics lock. Coverage check at the time: worker-18 was
building an external acceptance gate, worker-04 an independent harness plus echo
solver, and `numerics/fd.py` held *periodic Cartesian* stencils only. The
map-declared N0 artifact path was empty, so this fills the missing candidate
solver slot rather than duplicating a gate.

## Scope (exact, matches the artifact docstring)

Fixed Minkowski background; massless real scalar, spherical symmetry
`u_tt = u_rr + (2/r) u_r`; reduced `v = r*u` with `v_tt = v_rr` and
`v(t,0) = v(t,R) = 0`. No self-gravity, collapse, horizons, critical behaviour,
outgoing-I+ boundary, or any cosmic-censorship conclusion.

## What was measured (all gates pass; `numerics/results/flat_wave_convergence.json`)

| study | family | scheme | measured order (L2) | finest drift |
|---|---|---|---|---|
| 1 | standing (m=2), t=0.37 | 2nd order, cfl=0.25 | 2.006, 2.003, 2.001, 2.001 | 1.6e-14 (n=1024) |
| 2 | Gaussian pulse through centre, t=8 | 2nd order, cfl=0.25 | 1.987, 2.000, 2.001, 2.001 | 1.7e-11 (n=1024) |
| 3 | standing (m=2,5), t=0.37 | 4th-order closure, cfl=0.1 | 4.312, 4.218, 4.032, 3.983 | 3.4e-10 (n=512) |

Internal controls: temporal error subdominant (halving cfl moves L2 by 4.6e-7
relative); determinism bitwise on all numeric fields; negative controls rejected
(frozen-in-time order 0, sign-flipped Laplacian 1.4e93, cfl=1.5 growth 3.2e5)
while cfl=0.25 is not rejected.

Trap found and documented rather than hidden: at `t=0.5` (half a period of mode
m=2) the leading O(h²) term cancels and the measured order is a fragile O(h⁴)
accident (the `time_point_control` field records it). The standing gate uses the
generic time `t=0.37`.

## External evidence (not self-reported)

* **Worker-12 reproduction** (`artifacts/flash-12/n0/candidate_report_v2.json`):
  re-ran script sha256 `743c73e4e68e…c784` independently; `all_gates_pass: true`.
* **Worker-04 independent acceptance harness**
  (`artifacts/flash-04/n0_acceptance/`), a different implementation with a
  method-of-images Gaussian-pulse reference and a subprocess JSON protocol:
  verdict **PASS** (`numerics/results/w04_acceptance_worker20.json`), measured
  order 2.0004 (tol 0.3), relative invariant drift 3.2e-9 (tol 1e-6), stability
  PASS. The bridge `numerics/tests/flat_wave_protocol.py` speaks that protocol
  and contains no physics of its own.

## Re-run

```bash
python3 numerics/tests/flat_wave.py --selftest
python3 numerics/tests/flat_wave.py --all --json-out numerics/results/flat_wave_convergence.json
cd artifacts/flash-04/n0_acceptance && python3 run_harness.py \
  --solver-cmd 'python3 <repo>/numerics/tests/flat_wave_protocol.py' --timeout 120
```

## Acceptance gates declared by this draft (G1–G10)

G1/G2 measured order in band (2nd/4th); G3/G10 scheme-consistent energy drift
< 1e-8; G4 pulse order + finest L2 < 1e-3 + monotone drift; G5 determinism;
G6 `H = E_u/(4π)` identity; G7 operator self-tests; G8 negative controls
rejected and positive CFL control not rejected; G9 temporal error subdominant.

## Falsifiers (what would kill this claim)

1. An independent run of the frozen script that measures order outside
   [1.8, 2.2] (2nd) or [3.6, 4.4] (4th) on the declared families/times.
2. A reviewer finds the invariant `energy_discrete` is not the scheme's
   invariant (recompute by hand from the RK4 update).
3. `lead-formulation` shows F0's frozen taxonomy binds `AF-WCC-SCALAR-SPH`
   differently (e.g. different boundary/data class); then the artifact's scope
   statement, not just the binding, is wrong.
4. Worker-04's harness FAIL on the same hash with `psi_prev` supplied
   unconditionally (the current pass relies on the bridge's two-level trace).
5. A solver returning the exact reference states passes the W04 gate (their
   documented limitation, falsifier 5) — that is a *gate* limitation, and is why
   this artifact is not promoted on the gate alone.

## Limitations

* Reflecting Dirichlet box: no outgoing-radiation boundary at I+, so nothing
  here calibrates an outer-boundary treatment for the future self-gravitating
  solver.
* The declared acceptance thresholds are the executor's proposal, not a lead's
  frozen criteria.
* Binding is unconfirmed because `research_map/formulation_taxonomy.yaml`
  (node F0, marked done/passed) is missing on disk.
