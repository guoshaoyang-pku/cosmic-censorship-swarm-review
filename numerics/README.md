# numerics/ — N0 flat-space scalar-wave calibration

Group: numerics (`astra-lead-numerics`).  Node: **N0** only.  Class binding
`AF-WCC-SCALAR-SPH` (provisional until F0 is hash-pinned).

**N1 (self-gravitating) is locked.**  See [`blockers.md`](blockers.md).  No
self-gravitating solver code exists in this package, and `numerics/gates.py` refuses to
release N1 until `research_map.json#numerics_lock` is satisfied.

## What is here

| path | role |
|---|---|
| `tests/flat_wave.py` | **canonical N0 artifact** (worker 12): reduced variable `v = r*u`, central stencils orders 2/4, manufactured standing/pulse solutions, self-tests and negative controls |
| `tests/flat_wave_replication.py` | **independent replication** (worker 13): Crank–Nicolson + 3-pt FD and P1 FEM |
| `tests/lead_calibration.py` | **lead reference** (third family): staggered finite-volume SBP spherical scheme + periodic Cartesian stencils orders 2/4/6; dispersion, flux, constraint and lock-guard diagnostics |
| `tests/selfgravity_lock_guard.py` | standalone lock guard (worker 15): fails if N1+ artifacts exist while locked |
| `CONVERGENCE_PROTOCOL.md` | the convergence/invariant protocol G-NUM requires audit to review |
| `blockers.md` | N1 blocker/unblock contract, 1:1 with `numerics_lock` |
| `gates.py` | machine-checkable gate evaluation and the fail-closed N1 guard |
| `fd.py`, `grids.py`, `cartesian.py`, `spherical.py`, `exact.py`, `integrate.py`, `convergence.py`, `invariants.py` | lead reference implementation (FD stencils, SBP spherical scheme, exact solutions, RK4, order fitting, invariant diagnostics) |
| `events.py` | protocol-conformant upward events (`comms/outbox/astra-lead-numerics.jsonl`) |
| `checkpoint.py` | 15-minute numerics checkpoints for the 4-hour run |

## Run it

```bash
# canonical artifact
python3 numerics/tests/flat_wave.py --selftest
python3 numerics/tests/flat_wave.py --all --json-out numerics/results/flat_wave_convergence.json
python3 numerics/tests/flat_wave.py --lock-guard

# independent replication
python3 numerics/tests/flat_wave_replication.py --all --json-out numerics/results/flat_wave_replication.json

# lead reference calibration (slower, ~minutes)
python3 numerics/tests/lead_calibration.py --selftest
python3 numerics/tests/lead_calibration.py --all --json-out artifacts/numerics/n0/lead_calibration_report.json

# lock / gate state
python3 -m numerics.gates --check --write-report

# checkpoints
python3 numerics/checkpoint.py --once
python3 numerics/checkpoint.py --daemon --interval 900
```

## Claim ladder

Everything produced here is `conclusion_type: numerical_evidence` about a discretisation of
the flat-space massless scalar wave equation.  Nothing here is a theorem, and nothing here
bears on weak or strong cosmic censorship.  A node is complete only with the artifact on
disk, its sha256 registered, and a reviewer verdict (PROTOCOL.md rule 2).

## Result status (lead review, 2026-09-12)

* canonical implementation (rev `8b52014d…`) passes **11/11** gates including
  `G11_n1_lock_guard`; measured order 2.006/2.003/2.001/2.001 (standing) and
  1.987/2.000/2.001/2.001 (pulse), order 4: 4.312/4.218/4.032/3.983; lead-verified;
* replication (independent CN-FD 1.993478, CN-FEM 1.986324, reference-family lffd
  1.995770) — `ORDER REPRODUCED`; the CN-FEM order ≈ 0 defect was root-caused (wrong
  sign on the implicit level, `numerics/tests/replication_triage.md`), fixed at
  `8ade1cdc…`, and re-verified by the lead; scheme not excluded, gate not relaxed;
* lead 4-rung re-run adds `dr = 0.025`
  (`artifacts/numerics/n0/lead_4rung_replication.json`, driver
  `numerics/protocol/lead_4rung_replication.py`): p = 1.9966/1.9954/1.9889 with
  `delta <= 5.2e-3`, all pairs agreeing under R5;
* lead reference (staggered SBP spherical + Cartesian 2/4/6) passes **10/10** gates:
  spherical MMS order 2.000, SBP semi-discrete energy identity residual 0 to machine
  precision (7e-18), constraint residual < 1e-13, flux closure order 2.00, dispersion
  symbol match to 4e-16, and the non-SBP collocated control rejected by >1e15 margin;
* each scheme now reports its own structural invariant (<= 2.04e-14); the harness
  leapfrog functional is a labelled cross-check, not a scheme-independent gate
  (protocol rev 2, rules R1–R5a).

`numerics/tests/n0_gate_proposal.json` (lead adjudication) records G-NUM as
`pass_conditional`: all measured criteria C1–C7 are satisfied; the only unmet item is an
independent reviewer verdict on `numerics/CONVERGENCE_PROTOCOL.md` rev 2
(sha256 `3345e17d2be3…`), which the lead cannot self-review. N1 remains locked.
