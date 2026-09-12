# W042-N0-STOPRULE-INDEP-VERDICT-01 — second independent N0 review

`worker-042`, 2026-09-12. Gate `G-NUM`, node `N0`, class `AF-WCC-SCALAR-SPH`.

Second blind reviewer pass over the N0 stop rule left open by `reviews/N0-review-lead-audit.json`
(HF-03): (1) a fourth resolution rung or scoped 3-level study; (2) class binding re-bound to the
declared F0 rev5 `0abb9ed8a961`; (3) one independent replication verdict of the order. Plus the
lock guard.

## Files

| file | what |
|---|---|
| `verify_n0_stoprule.py` | read-only checker; measures every hash itself, re-derives the order fits from the raw rows, re-hashes after the checks |
| `report.json` | machine-readable result (38 checks, observations, stop-rule adjudication, findings, hashes) |
| `stderr.log` | checker stderr (empty on a clean run) |

Verdict file: `reviews/N0-review-worker-042.json`. Not an accept, not a gate verdict; workers
cannot move gates or node status.

## Result at the measured hashes

* **Item (1) CLOSED.** `numerics/protocol/n0_fixed_dt_certification.json` carries 4 rungs
  (`dr = 0.2, 0.1, 0.05, 0.025`) at fixed `dt = 1e-4` for `cnfd`, `cnfem`, `lffd`; all ladders
  monotone; refit orders reproduce the declared pair orders, least-squares fit and R5 delta to
  `<1e-12`; all `|p - 2| <= 0.3`.
* **Item (2) OPEN (HF-042-N0-1).** `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2` still cites F0
  pins `66bf917b`/`565a6e50` and states the binding stays provisional; the declared rev5 pin
  `0abb9ed8a961` appears only in `numerics/results/flat_wave_convergence_rev3.json`, which records
  the protocol drift as a blocker instead of resolving it. Two documents in the reviewed evidence
  set name different F0 pins for the same class binding.
* **Item (3) CLOSED.** Three hash-verified replication artifacts: worker-046 `SUPPORTED` all
  criteria pass, worker-057 `REPRODUCED` 0 findings, worker-081 adjudicated with
  `blocks_gate_pass=false`.
* **Lock guard CLOSED.** `numerics/spherical_solver` absent, no N1 artifact reference in the
  reviewed evidence, `numerics_lock` locked.

## Findings

* F-042-N0-1 protocol of record contested at the reviewed hash (w067 revise live; w081 supersession
  disputed); the controller gate audit records C8 MET while `numerics/gates.py::_protocol_review`
  reports contested and `N1_BLOCKED`. Needs adjudication.
* F-042-N0-2 `numerics/gates.py::_protocol_review` has no (reviewer, target, hash) supersession
  rule; a withdrawn accept is still counted.
* F-042-N0-3 items (1) and (3) independently reproduced (positive).
* F-042-N0-4 registry coverage: the 00:52:00 controller checkpoint registers the protocol/results/
  certification; the three replication verdict artifacts remain unregistered (controller step,
  PROTOCOL.md rule 2).

## Rerun

```bash
python3 artifacts/worker-042/n0_stoprule_verify/verify_n0_stoprule.py
```

Deterministic except `generated_at`. A moved reviewed hash voids the affected citation and
requires a re-review.
