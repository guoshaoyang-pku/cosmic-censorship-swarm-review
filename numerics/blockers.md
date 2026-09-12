# N1 blocker / unblock contract (numerics group)

Node: **N1 — self-gravitating reduced solver** (`numerics/spherical_solver/`, NOT created).
Status: **blocked by controller lock** — `research_map/research_map.json#numerics_lock`.
Owner of record: `astra-lead-numerics`. Release authority: `astra`. Escalation: `human-pi`.

This file is the auditable form of Astra hard decision #2 (*do not launch self-gravitating
numerics until formulation and audit gates pass*). It contains no solver design, no
self-gravity equations, and no run proposal.

## Statement of scope compliance

No self-gravitating code has been written or run by the numerics group.

* `numerics/spherical_solver/` does not exist (machine-checked by
  `numerics/tests/lead_calibration.py::study_lock_guard` and
  `numerics/tests/flat_wave.py --lock-guard`).
* Every numerical artifact produced this run is a flat-space scalar-wave calibration:
  fixed Minkowski background, massless scalar field, no coupling to geometry.
* The only code that reads the lock is `numerics/gates.py`, which *refuses* work; it
  cannot start any solver.

## Unblock checklist — 1:1 with the map

Source of truth is `research_map/research_map.json#numerics_lock`; this table must not add,
drop, or weaken a condition.

| # | condition (map key) | how it is machine-checked | current state |
|---|---|---|---|
| 1 | `required_gates` contains `G-FORM` and verdict is `pass` with evidence | `numerics.gates.evaluate()` reads `gates[].verdict` and `evidence_refs`; `python3 -m numerics.gates --check` | **pending** (map verdict `pending`) |
| 2 | `required_gates` contains `G-AUDIT` and verdict is `pass` with evidence | same | **pending** (map verdict `pending`) |
| 3 | `additional_requirements`: N0 convergence order **measured** | passing `artifact` event for `numerics/tests/flat_wave.py` with matching sha256 + report `numerics/results/flat_wave_convergence.json`; certified at `>= 4` rungs per protocol rev 3 §3.2 | **satisfied** — 4-rung fit order 2.0000 for three schemes at dt fixed = 1e-4, the study §3.4 prescribes (`numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8`: lffd 1.999943 / cnfd 1.999864 / cnfem 1.999916). The earlier constant-CFL 4-rung study (`numerics/tests/n0_order_4rung.json#c88146a1`) is **relabelled mixed-order** after review findings F1/F1' and is no longer the certification basis. Canonical artifact event `lnum-artifact-1175353e16a5249a11ab`; consolidated rev-3 report `numerics/results/flat_wave_convergence_rev3.json#da7c360719950f7e` (four rungs per scheme, fixed dt = 1e-4, F0 rev5 binding, independent verdicts) |
| 4 | `additional_requirements`: N0 order **independently replicated** within tolerance | passing `artifact` event for `numerics/tests/flat_wave_replication.py` + `numerics/results/flat_wave_replication.json`; `numerics.gates` | **satisfied** — at fixed dt = 1e-4, max pairwise \|dp\| **7.958e-05** ≤ R5 bound 0.25 (3000x inside); error-field structure check `numerics/protocol/error_field_orthogonality_check.json#1b2d3162b0715d9b` shows corr(cnfd,cnfem) = −0.9996, i.e. each scheme's own truncation error (opposite-sign ±1/12 phase errors), not a shared error. Gate evaluator `order_agreement: agreed=true`, delta 0.0101 ≤ 0.35. **Independent replication verdicts at the frozen basis** (pinned, all by other agents): worker-046 `artifacts/worker-046/n0_fixed_dt_independent/verification.json#814452111bc8912b` — from-scratch re-execution of the frozen module, `SUPPORTED`, 8/8 criteria, orders lffd 1.999943 / cnfd 1.999864 / cnfem 1.999916; worker-057 `artifacts/worker-057/n0_fixeddt_verify/report.json#b906445878f3130d` — independent re-analysis of the filed rows (generator not imported), `REPRODUCED`, 67 checks / 65 pass / 2 documentation advisories / **0 findings**, certification hash stable across the run; worker-081 `artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json#65ae766d9e4c2057` with review `w081-20260912T0042050800-adj2-review` — `accept` at protocol `1e6cdf04`, disposition `F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION`. Consolidated rev-3 report: `numerics/results/flat_wave_convergence_rev3.json#da7c360719950f7e`, independently re-verified by `numerics/protocol/verify_convergence_rev3.py` (11 pins re-measured, VERIFIED) |
| 5 | `additional_requirements`: numerical protocol **reviewed by audit** | `review` event targeting `numerics/CONVERGENCE_PROTOCOL.md` (or `G-NUM-protocol` / `N0`) with `verdict=accept`, reviewer ≠ `astra-lead-numerics`, cited hash = the protocol on disk | **accept exists, currently CONTESTED** — protocol is at rev 3 (`1e6cdf04d7a2…`). Binding accepts at that hash: `audit-review-gnum-protocol-final-20260912T0027` (astra-lead-audit, score 4.5, no hard failures) and `w081-20260912T0042050800-adj2-review` (worker-081, `accept`, score 4.0, disposition `F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION`). Live dissents at the same hash: `w067-review-gnum-protocol-r3-20260912T002256` (revise F1) and `w081-2026-09-12T00:29:19+0800-f1-review` (revise F1′, since closed by its own falsifier). `numerics.gates` reports `reviewed=true, contest=true`. **Guard defect (measured, reported 2026-09-12T00:44):** `_protocol_review` still counts the withdrawn accept `w081-20260912T002140-c8-review`; a later accept by the same reviewer at the same hash does not rescind the earlier revise. Disposition is a controller/reviewer call (withdrawal semantics or a guard supersession rule); numerics may not self-adjudicate. Protocol preamble also cites superseded F0 pins `66bf917b`/`565a6e50`; the class binding in the rev-3 report is re-derived against F0 rev5 `0abb9ed8a961`, and the preamble text is left frozen so the verdicts bound to `1e6cdf04` stay valid |
| 6 | `numerics_lock.state` released by `astra` | `numerics.gates` reads `state`; releases only via a controller map update | **locked** (since 2026-09-11T23:15:11+08:00) |

`numerics.gates.evaluate()` is fail-closed: an absent, unreadable, or hash-mismatched
artifact, an unparsable order report, or a missing independent review all keep
`production_allowed = False`. While any row above is unsatisfied,
`ensure_n1_allowed()` raises `ProductionLocked`.

## Explicit non-conditions (do not treat as release)

* elapsed wall-clock time in this 4 h session;
* idle worker capacity or unused `budget_agent_hours`;
* agreement between agents, agent confidence, or fluent-text summaries;
* N0 passing alone: N0 is a *flat-space calibration* and implies nothing about the
  self-gravitating initial-boundary value problem;
* a low measured order being "close enough" — order tolerance is an N0 (G-NUM) question,
  not a lock-release condition.

## Guard tests (must fail closed)

```bash
python3 -m numerics.gates --check          # exit 3 while locked; exit 0 only when released
python3 numerics/tests/lead_calibration.py --selftest     # check 6: lock guard fails closed
python3 numerics/tests/flat_wave.py --lock-guard          # canonical N0 artifact guard (G11)
python3 numerics/protocol/verify_convergence_rev3.py      # exit 0 = VERIFIED (re-measures 11 pins)
```

All are exercised on the current map: they report `N1_BLOCKED` with the reasons above, the
canonical artifact's `--all` gate `G11_n1_lock_guard` passes, and the rev-3 report verifier
returns `VERIFIED` against `numerics/results/flat_wave_convergence_rev3.json#da7c360719950f7e`.

A guard that returns success while any checklist row is unsatisfied is itself a defect:
the falsifier for this file is *the guard passes while a required gate is not actually
satisfied*, or *this file proposes a self-gravity run*.

**Guard-binding fix (2026-09-12T01:00, lead-numerics).** `numerics/gates.py` had a real defect:
`_protocol_review` matched review target_ids only against
`{numerics/CONVERGENCE_PROTOCOL.md, flat_wave.py, flat_wave_replication.py, N0}`, while every
review in this run uses `target_id: G-NUM-protocol` or carries a `#<hash>` pin. No accepting
review could ever be seen and `reviewed` was permanently `false`. Fixed
(`907a88b141bf4394` → `fcd1d70991b6eade`): the target set now includes `G-NUM-protocol`, a
verdict binds only when a cited hash (explicit field **or** an `evidence_ref` of the form
`numerics/CONVERGENCE_PROTOCOL.md#<hash>`) prefix-matches the protocol on disk, the protocol
author is excluded, duplicate copies across the accepted stream and outbox are deduplicated,
and live dissents are reported so a contest is visible instead of silently green. The change is
**stricter**, not looser. The map still cites the superseded `gates.py#907a88b141bf4394`; a
re-pin is requested from the controller.

## Procedure when the lock is released

1. Astra applies the `G-FORM` and `G-AUDIT` pass verdicts and flips
   `numerics_lock.state` (release authority only; escalation to `human-pi` if contested).
2. Re-run `python3 -m numerics.gates --check` and record the report as the release
   evidence (`artifacts/numerics/gate_report.json`).
3. Only then may an N1 design be drafted, and it must consume the frozen, hash-pinned
   `schemas/af_wcc_vacuum.yaml`, `schemas/af_scc_*_vacuum.yaml` and `ledger/theorems.jsonl`
   artifacts rather than prose.
4. N1's first deliverable is a *convergence and constraint protocol*, not a production
   run; matched-budget baselines and a null test are required before any physical claim.
