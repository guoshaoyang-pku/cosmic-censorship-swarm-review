# N0 acceptance harness (draft)

Solver-agnostic acceptance tests for the flat-space scalar-wave equation in
spherical symmetry (`psi = r*phi`, `psi_tt = psi_rr`, `psi(0,t)=0`).

**Status: draft / unverified.** Class `AF-WCC-SCALAR-SPH`, map node `N0`.
This is a worker-namespaced copy (`artifacts/flash-04/n0_acceptance/`); the
map-declared canonical artifact for N0 is `numerics/tests/flat_wave.py`. Merge
requires `lead-numerics` (scope) and `lead-audit` (control battery) gates.
See `SPEC.md` for scope, thresholds, evidence refs and next falsifiers.

## Quick start

```bash
cd artifacts/flash-04/n0_acceptance

python3 test_harness.py -v                                  # 15 self-tests (null controls)
python3 run_harness.py --controls --json acceptance_report.json
python3 run_harness.py --solver radial_leapfrog             # exit 0 = PASS
python3 run_harness.py --solver mock_order1                 # exit 1 = FAIL (order)
python3 run_harness.py --solver mock_leaky                  # exit 1 = FAIL (energy drift)
python3 run_harness.py --solver mock_hidden_invariant       # exit 2 = INCONCLUSIVE
python3 run_harness.py --solver-cmd 'python3 external_echo_solver.py' --timeout 30
python3 run_harness.py --solver-cmd 'python3 external_hang_solver.py' --timeout 2
```

Exit codes: `0` PASS, `1` FAIL, `2` INCONCLUSIVE, `3` configuration error.
`INCONCLUSIVE` (missing evidence) is never reported as PASS.

## Files

| file | role |
|---|---|
| `SPEC.md` | scope, class binding, thresholds, acceptance tests, falsifiers |
| `harness.py` | gates: convergence order, discrete-energy drift, CFL stability, verdict combination |
| `reference_solutions.py` | exact method-of-images pulse and standing mode (pure functions) |
| `solvers.py` | reference leapfrog, null-control mocks, external subprocess bridge |
| `run_harness.py` | CLI; `--controls` battery; `--solver-cmd` external protocol |
| `test_harness.py` | 15 self-tests, including one adversarial arm per gate |
| `external_echo_solver.py` | example external solver (reference leapfrog over the JSON protocol) |
| `external_hang_solver.py` | pathological solver used to test the hard timeout |
| `acceptance_report.json` | control-battery evidence bundle (generated) |
| `test_output.txt` | unittest transcript (generated) |
| `MANIFEST.sha256` | per-file hashes (generated) |

## External solver protocol

Request (stdin): `{"r", "dt", "t_end", "sample_every": 1, "psi0", "psi_t0"}`.
Response (stdout): `{"t": [...], "psi": [[...], ...], "psi_prev": [[...], ...]}`
with **every step** sampled from `t=0` to `t_end`; `psi_prev` optional (omitting
it makes the invariant gate INCONCLUSIVE).

## Known limitations

- acceptance gate for honest integrators; it cannot detect a solver that returns
  exact reference states (see SPEC.md falsifier 5);
- no boundary-closure defect control yet (falsifier 3);
- last-sample/t_end mismatch is not asserted (falsifier 6).
