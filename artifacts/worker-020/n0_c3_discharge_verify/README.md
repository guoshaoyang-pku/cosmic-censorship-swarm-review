# W020-N0-C3-DISCHARGE-VERIFY-01 — independent non-author verification of the C3 discharge

**Slot** `worker-020` · **Class** `AF-WCC-SCALAR-SPH` · **Node** `N0` · **Gate** `G-NUM`
**Target under review** `W012-N0-C3-DISCHARGE-01` (deepseek-flash-12), report
`artifacts/worker-012/n0/c3_discharge/raw/report.json#67fb7f0f5b2f`
**Verdict** `C3_DISCHARGE_REPRODUCED_AND_REDERIVED_NO_DEFECT` · **review** `accept` 4.0 · no hard failures
**N1 lock** `numerics_lock.state == "locked"` throughout; `numerics/spherical_solver/` never created or proposed.

## The question this verifies

worker-012 asked, in its own `next_actions`:

> Independent non-author: re-run `verify_c3_discharge.py` (exit 0 expected) or falsify per the
> report falsifier.

Its claim was that the re-based fixed-dt certification
`numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c` discharges the two major
`revise` findings on `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2` (worker-067 F1,
worker-081 F1′) while two minor text findings (w067-F2, w067-F3) stay literally open;
verdict `accept` 4.0, reviewer input only. This task is an independent third-slot check of
that claim at its own pinned bytes.

## Method (read-only; no other agent's artifact was rewritten)

1. **Pin** every binding input and every target byte before and after the run.
2. **Own re-derivation** of every declared fit, pair order, residual, least-squares SE,
   pair half-range, `delta_R5` and R5 pair from the raw `dr`,`l2_error` rows, using this
   script's own least-squares code (cross-checked against `numpy.polyfit`). No import of the
   certification generator.
3. **Sandbox reproduction** of the target checker: a byte-identical copy placed at the same
   repo depth (`tmp/w020_c3_repro/sandbox/c3copy/`) so its `REPO` still resolves, with
   `--json-out` and its `fresh_rerun.json` redirected into the sandbox. The original target
   files were re-hashed afterwards and did **not** move.
4. **Own frozen-module re-execution** along a different call path than the target
   (`make_factory` / `run_case` / `l2_error` directly, 60,000 steps each, `dt = 1e-4`,
   4 rung-solves: lffd dr = 0.2 / 0.025, cnfd dr = 0.2, cnfem dr = 0.2).
5. **Protocol-text audit** at the pinned hash for the clauses the dispositions rely on
   (lines 58, 60, 110, 142, 145; `solver_tolerance` count).
6. **Six mutation controls** (each must fire) plus determinism and pin-write guards.

Reproduce: `python3 artifacts/worker-020/n0_c3_discharge_verify/verify_c3_discharge_independent.py`
(exit 0, 129/129 checks, ≈ 160 s wall dominated by the sandbox reproduction).

## Result

**129/129 machine checks pass, 0 fail.** Certified orders recomputed from the raw rows:

| scheme | fit order (dt = 1e-4) | Δ_R5 | cross-scheme R5 |
|---|---|---|---|
| lffd | 1.999943173893314 | 8.44e-05 | max pairwise \|Δp\| **7.958e-05** ≤ 0.25 |
| cnfd | 1.9998635927240203 | 9.32e-05 | all three pairs agree |
| cnfem | 1.9999163079874884 | 2.46e-04 | |

* **Sandbox reproduction**: target checker exit 0, **81/81** checks, identical check-id set;
  its fresh rows reproduce the filed `fresh_rerun.json` on 8 rows at **0.0** relative
  deviation (bitwise).
* **Independent re-execution**: my own 4 rung-solves reproduce the filed `l2_error` rows at
  **0.0** relative deviation.
* **Fresh vs certification**: worker-012's filed fresh rows match the certification's filed
  rows on 8 rows at **0.0** relative deviation.
* **Cross-checks re-read independently**: flash-13 (`1e-4` and `1e-3`) and worker-046
  order values match the certification to ≤ 1e-9; worker-046 verdict `SUPPORTED`.
* **Disposition audit**: all seven dispositions carry a basis; the two machine-checkable
  major discharges are supported (the certification uses `dt = 1e-4` fixed on all four
  rungs for all three schemes, and the protocol already required exactly that at lines
  58–60), the mixed cfl = 0.5 ladder is retained and relabelled, and the two minor text
  findings are confirmed still present at the pinned hash and disclosed as non-blocking.

## Controls

| control | planted defect | expected | observed |
|---|---|---|---|
| M1 | `l2_error` perturbed +0.5 % | detected | fired |
| M2 | declared `fit_order` moved +0.01 | detected | fired |
| M3 | frozen-module hash flipped | detected | fired |
| M4 | fixed-rung `dt` changed to 2e-4 | detected | fired |
| M5 | protocol fixed-`dt` clause removed | detected | fired |
| M6 | declared R5 pair diff flipped to 0.5 | detected | fired |
| C7 | determinism: two pure-analysis runs | identical | identical |
| C8 | binding pins before vs after | unmoved | unmoved (`moved=[]`) |

## Findings

* **F1** The target's core claim reproduces end-to-end: sandbox 81/81, fresh rows bitwise
  identical, my own re-execution bitwise identical, all fits/R5 re-derived independently.
* **F2** The two minor text findings (R2 `solver_tolerance` null branch absent;
  stale section-6 “agree within 0.35 absolute” sentence at line 142 superseded in-file by
  the rev-2 amendment at line 145) are real and correctly disclosed as still open. Their
  disposition is the controller's, not a worker's.
* **F3** The target's `research_map` / `events_stream` pins are measured-only mutable
  snapshots and must not be cited as frozen evidence.
* **F4** Independence caveat: this is a same-fleet third-slot check by a non-author
  (worker-020 did not author the protocol, certification, frozen module, published 4-rung
  control or the target report). It is not an external audit.

## Authority and non-claims

No gate verdict, no node completion, no `validation_status` promotion, no numerics-lock
release, no physics claim, and no replacement of the controller's disposition of the C3
contest. This is reviewer input at a pinned hash.

## Falsifier

Void if any binding pin re-hashes differently (protocol `1e6cdf04`, certification
`1677822ceb9c`, generator `3c7c9087`, frozen module `8ade1cdc`, published 4-rung
`c88146a1`), or the target bytes move, or a declared fit/R5 number fails to reproduce from
the raw rows within `1e-9`, or the sandboxed worker-012 checker does not return 81/81, or
its fresh rows do not reproduce the filed ones within `1e-9` relative, or my own
frozen-module re-execution does not reproduce the filed `l2_error` rows within `1e-12`
relative, or a mutation control fails to fire.

## Pins measured at emit time

| input / target | sha256 |
|---|---|
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920` |
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422` |
| `numerics/tests/n0_order_4rung.json` | `c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a` |
| target checker `verify_c3_discharge.py` | `d2930155f7a857a0cf69c6b3bb02094c302b942f82263025a4b4042e9e31af2f` |
| target `raw/report.json` | `67fb7f0f5b2fa63158c958adaa13f61577f14e1c983ce77a46071d829da2bc19` |
| target `raw/fresh_rerun.json` | `65d459eb3359ad4e2b813efb8d231fcf56614002bb4241f18d49e9463dfa9c98` |

## Files

* `verify_c3_discharge_independent.py` — the checker (read-only; stdlib + numpy)
* `c3_discharge_verification.json` — full machine report: 129 checks, recomputed tables,
  controls, cross-checks, findings, falsifier
* `c3_discharge_verification.log` — stdout of the full run
* `manifest.json` — sha256 of every deliverable and pinned target
* `emit_events.py` — idempotent, hash-guarded outbox event emitter
