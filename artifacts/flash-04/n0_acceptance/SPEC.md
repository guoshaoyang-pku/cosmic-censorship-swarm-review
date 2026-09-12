# N0 acceptance harness — flat-space scalar-wave (DRAFT, UNVERIFIED)

| field | value |
|---|---|
| status | **draft / unverified** — not an accepted node artifact, no completion claim |
| author | `deepseek-flash-04` (execution worker, DeepSeek Flash breadth) |
| created | 2026-09-11T23:2x+08:00 |
| class binding | `AF-WCC-SCALAR-SPH` — flat-space **test-field** scalar, fixed Minkowski background |
| node | `N0` "Flat-space scalar-wave test" (status `queued`, `depends_on: ["F0"]`) |
| map-declared canonical artifact | `numerics/tests/flat_wave.py` (`research_map/research_map.json` N0) |
| this draft lives at | `artifacts/flash-04/n0_acceptance/` (worker namespace; **not** the canonical path) |
| proposal event | `comms/outbox/flash-04-resource-request.json` |
| artifact event | `comms/outbox/flash-04-artifact-unverified.json` (`validation_status: unverified`) |
| gate needed before canonical merge | `lead-numerics` accepts scope + artifact schema; `lead-audit` reviews control battery |

## 1. Why this task, and why it is only proposed

`comms/inbox` was empty at 2026-09-11T23:15–23:25+08:00, so no group lead has
bound this worker to a task. Per the execution-worker contract, this worker does
not claim unassigned work as complete. The immediate queue in
`research_map/ASTRA_HANDOFF.md` was inspected; the only entry that is (a)
class-bound, (b) not blocked by the software gates, and (c) appropriate for
cheap breadth work is **N0**: `AF-SCC`/self-gravitating numerics are explicitly
gated (`ASTRA_HANDOFF.md` hard decision 2), while N0 depends only on `F0`.

The proposed deliverable is therefore the **verification half** of N0: a
solver-agnostic acceptance harness that can be pointed at any candidate
flat-space scalar-wave integrator. This matches the project's stated leverage:
"Verification costs more than search ... FunSearch runs 140 evaluators against 15
samplers" (`HANDOFF.md` §2). Implementing an actual PDE solver would duplicate
`lead-numerics`' own work and would need a class-bound prompt from that lead.

## 2. Exact scope

The harness measures a solver's convergence for the regular radial reduction of

    d_t^2 phi = d_r^2 phi + (2/r) d_r phi        (flat space, spherical symmetry)
    psi := r * phi,   psi(0, t) = 0              (regularity)
    d_t^2 psi = d_r^2 psi

on a uniform radial grid `r in [0, r_max]` with Dirichlet endpoints.

**In scope**

- spatial+temoral convergence order of `psi` under joint refinement `dr`, `dt = cfl*dr`;
- conservation of the leapfrog discrete energy recomputed by the harness from
  the solver's own `psi`/`psi_prev` states;
- CFL stability (finite state, bounded amplitude growth);
- rejection of defective solvers via a builtin null-control battery;
- a hard process-boundary timeout for external solvers.

**Out of scope (not measured, not claimed)**

- self-gravity, backreaction, black-hole formation, critical collapse, any
  cosmic-censorship statement (those belong to `AF-SCC-*` / N1, currently gated);
- reconstruction of the physical field `phi = psi/r` near the origin;
- outgoing-radiation boundary conditions (the test pulse never reaches `r_max`);
- convergence of a specific production solver (none exists yet);
- resistance to a solver that deliberately returns the exact reference solution.

## 3. Gate definitions and thresholds

| gate | measurement | PASS | notes |
|---|---|---|---|
| order | least-squares slope of `log L2_error` vs `log dr` over `dr = 0.2, 0.1, 0.05`, `cfl = 0.5` | `|p − 2.0| <= 0.3` **and** errors strictly decreasing | 3 levels; slope tolerance allows mild nonlinearity |
| invariant | max relative drift of harness-recomputed discrete energy, sampled every 4 steps | `drift <= 1e-6` | reference leapfrog measures `3.4e-15`; a 30 % inconsistent `psi_prev` measures `5.9e-05` |
| stability | finest grid at `cfl ∈ {0.25, 0.5, 0.8}` | finite state and `max|psi|/max|psi(0)| <= 50` | reference growth ≈ 1 |
| verdict | combination | any FAIL → FAIL; else any INCONCLUSIVE → INCONCLUSIVE; else PASS | **missing evidence is never PASS** |

Test problem: method-of-images outgoing Gaussian pulse,
`psi(r,t) = F(r−t) − F(−r−t)`, `F(s) = exp(−(s−10)^2 / 4.5)` (`r0=10`, `sigma=1.5`),
`r_max = 30`, `t_end = 6`, `cfl = 0.5`. The pulse peaks at `r = 16` at `t_end`, so
the fixed outer boundary is never reached; the image term is `< 1e-10` on the grid.

## 4. Acceptance tests (all currently pass)

Run from `artifacts/flash-04/n0_acceptance/`.

| id | command | expected |
|---|---|---|
| AT1 | `python3 test_harness.py -v` | `Ran 15 tests ... OK` (≈4 s) |
| AT2 | `python3 run_harness.py --controls --json acceptance_report.json` | exit 0; all 7 controls equal their expected verdict |
| AT3 | `python3 run_harness.py --solver radial_leapfrog` | exit 0 (PASS); order `1.996`, drift `3.4e-15` |
| AT4 | `python3 run_harness.py --solver mock_order1` | exit 1; order gate FAIL, measured `1.001` |
| AT5 | `python3 run_harness.py --solver mock_leaky` | exit 1; order PASS `2.000`, invariant FAIL drift `5.9e-05` |
| AT6 | `python3 run_harness.py --solver mock_hidden_invariant` | exit 2 (INCONCLUSIVE); order PASS, invariant INCONCLUSIVE |
| AT7 | `python3 run_harness.py --solver-cmd 'python3 external_echo_solver.py' --timeout 30` | exit 0 (PASS) |
| AT8 | `python3 run_harness.py --solver-cmd 'python3 external_hang_solver.py' --timeout 2` | exit 1; reason contains `SolverTimeout` (process-boundary kill, no hang) |
| AT9 | two runs of any command produce identical `report_digest` | enforced by `test_same_run_same_digest` |

Control battery (declared config, from `acceptance_report.json`):

```
radial_leapfrog        PASS          order 1.996  drift 3.383e-15
mock_order2            PASS          order 2.000  drift 3.300e-15
mock_order1            FAIL (order)  order 1.001
mock_order0            FAIL (order)  order 0.001
mock_leaky             FAIL (inv.)   order 2.000  drift 5.898e-05
mock_unstable          FAIL (stab.)  order 0.123  drift 1.776e+10
mock_hidden_invariant  INCONCLUSIVE  order 2.000  invariant not measurable
```

Exit codes: `0` PASS, `1` FAIL, `2` INCONCLUSIVE, `3` configuration error.

## 5. External solver protocol

`--solver-cmd` runs `CMD` under `subprocess.run(..., shell=True, timeout=T)`.
Request on stdin (one JSON object):

```json
{"r": [...], "dt": 0.025, "t_end": 6.0, "sample_every": 1,
 "psi0": [...], "psi_t0": [...]}
```

Response on stdout (one JSON object, **every step** sampled, `t` from 0 to `t_end`):

```json
{"t": [...], "psi": [[...], ...], "psi_prev": [[...], ...]}
```

`psi_prev` is optional; omitting it forces the invariant gate to INCONCLUSIVE.

## 6. Evidence refs

- `HANDOFF.md` §2 (verification cost; evaluator/sampler ratio), §6 (process-boundary
  timeout; spawn guard), §1(a) (verifier design is the leverage).
- `README.md` "Adding a problem": `verify` must be deterministic, machine-checkable,
  cheap in human hours.
- `research_map/ARCHITECTURE.md` lines 44–46 (task-specific gates, evidence graph,
  no universal scalar score).
- `research_map/ASTRA_HANDOFF.md`: hard decision 2 (no self-gravitating numerics yet),
  immediate queue N0, definition of useful progress.
- `research_map/research_map.json`: node `N0` (`queued`, `depends_on ["F0"]`), node
  `F0` (`done`, `validation_status passed`).
- `research_map/events.schema.json`, `research_map/schemas.py` (event contract).
- `acceptance_report.json`, `test_output.txt`, `MANIFEST.sha256` (in this directory).

## 7. Next falsifiers (in priority order)

1. **Metric falsifier.** An independent reimplementation of the discrete-energy
   functional must reproduce `~1e-15` drift for `radial_leapfrog` and order `≈2`.
   If it does not, the harness metric — not the solver — is wrong.
2. **Class-binding falsifier.** `lead-numerics`/`lead-formulation` must confirm that
   a flat-space test-field scalar belongs to `AF-WCC-SCALAR-SPH` and that
   `psi`-convergence is an admissible N0 gate. If not, kill the task.
3. **Boundary-closure control.** Build a solver that is second-order in the interior
   but first-order at the `r=0` closure; the order gate must reject it (`p <= 1.5`).
   Not yet implemented — currently the control battery has no boundary-defect arm.
4. **Threshold falsifier.** Find a scheme whose energy drift is `< 1e-6` yet whose
   solution is physically wrong; then the invariant threshold is too loose.
5. **Cheat falsifier.** A solver that returns the exact reference states passes every
   gate. The harness is an acceptance gate for honest integrators, not a
   cheat-proof verifier; closing this needs residual/self-consistency evidence.
6. **Protocol falsifier.** A solver returning a trajectory that skips `t_end`
   (last sample short of `t_end` within one `dt`) is accepted silently; `ReplaySolver`
   should assert `|t[-1] - t_end| <= dt`. (Known gap.)
