# W012-N0-C3-DISCHARGE-01 — C3 protocol-contest adjudication support

**Slot** `worker-012` (`deepseek-flash-12`) · **Class** `AF-WCC-SCALAR-SPH` · **Node** `N0` · **Gate** `G-NUM`
**Verdict filed** review `accept`, score 4.0, no hard failures — **adjudication support only, not a gate verdict**
**N1 lock**: `numerics_lock.state == "locked"` throughout; `numerics/spherical_solver/` never created or proposed.

## The open question this closes

`numerics/blockers.md` row 5 and the lead-numerics closeout blocker
(`lnum-blocker-1789144642811-4cb5c2`) left one item for a reviewer/controller:

> Two `revise` verdicts sit at protocol hash `1e6cdf04d7a2` while one independent `accept`
> also sits there. Numerics re-based the certified order claim onto a fixed-dt study after the
> revise findings. Does the re-based evidence discharge them, or does the protocol text need a
> revision 4?

The contestants, all binding the **same** protocol hash `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274`:

| verdict | reviewer | score | core finding |
|---|---|---|---|
| `revise` | worker-067 | 4.0 | **F1 major**: certified spatial claim used constant-CFL (`dt = 0.5·dr`) runs while §3.4 bars `dt ∝ h` as spatial; F2/F3 minor text issues |
| `revise` | worker-081 | 3.5 | **F1′ major**: confirms F1 with a stronger measurement; remedy = file the fixed-dt study as certification evidence, demote cfl=0.5 to a labelled control |
| `accept` | astra-lead-audit | 4.5 | `reviews/G-NUM-protocol-review.json#8137f18f1a3b` |

## Method (read-only; no canonical file written)

1. Re-measured every pinned input (§ Pins below).
2. Machine-audited the **protocol text** at `1e6cdf04` for the exact clauses the findings name.
3. Machine-audited the **re-based certification** `1677822ceb9c`: four rungs, one fixed dt,
   three schemes, monotone, in band, R5 agreement, frozen-module guard, mixed-order relabel,
   and a positive control against the published constant-CFL rows.
4. **Independently recomputed** every declared fit from the raw `dr`/`l2_error` rows with a
   plain least-squares of my own (not the artifact's `fit()`), tolerance `1e-9`.
5. **Fresh bounded re-execution** of the frozen instrument `8ade1cdc` through its own
   `order_study()` entry point at `dt = 1e-4`: lffd all four rungs, cnfd/cnfem endpoints.
6. Cross-checked the three independent reproductions already in the tree (flash-13, worker-046,
   worker-020).

Reproduce: `python3 artifacts/worker-012/n0/c3_discharge/verify_c3_discharge.py`
(exit 0; 81/81 checks; ≈150 s dominated by the fresh cnfd/cnfem endpoint solves).

## Result

**81/81 machine checks pass, 0 fail.** Certified orders recomputed from raw rows:

| scheme | fit order (dt=1e-4) | Δ_R5 | cross-scheme R5 |
|---|---|---|---|
| lffd | 1.999943173893314 | 8.44e-05 | max pairwise \|Δp\| **7.958e-05** ≤ 0.25 |
| cnfd | 1.9998635927240203 | 9.32e-05 | all three pairs agree |
| cnfem | 1.9999163079874884 | 2.46e-04 | |

Fresh re-execution reproduced every filed `l2_error` row (lffd ×4, cnfd ×2, cnfem ×2; 60 000 steps
per rung) to ≤ 1e-12 relative. Cross-study agreement was exact: worker-046's fixed-dt orders
match the certification to `0.0`; worker-020's dt = 1e-3 / 5e-4 ladders match flash-13's to `0.0`.

## Per-finding disposition

| finding | severity | disposition | why |
|---|---|---|---|
| w067-F1 | **major** | **DISCHARGED** by re-based evidence | The certification now uses `dt = 1e-4` fixed on all four rungs. §3.4 of the *unchanged* text already required exactly that (lines 58–60), so text and claim no longer conflict; no rev 4 is needed to reconcile them. |
| w081-F1′ | **major** | **DISCHARGED** | The named remedy is implemented literally: four fixed-dt rungs × three schemes, and the cfl=0.5 ladder retained as `constant_cfl_mixed_order_control` with an explicit mixed-order relabel. |
| w081-F1′-quant | major evidence | **DISCHARGED** (retained as justification) | The 22–143 % temporal-refinement effect is a measurement about the *old* ladder; the certification records the same effect (+126 % cnfd at dr=0.05) as its reason for re-basing. |
| w081-F1′-mitigation-refuted | **major** | **DISCHARGED** by supersession | The refuted "no number changes" mitigation is no longer load-bearing: the new numbers do change (cnfd 1.99535 → 1.99986). |
| w067-F2 | minor | **NOT discharged — text remains** | R2 `max(1e-12, 10 × solver_tolerance)` still has no defined null branch (line 110; `solver_tolerance` appears once, null-definition hits 0). Evidence re-basing cannot close a text finding. Non-blocking: all measured drifts pass the 1e-12 floor (3.38e-15 / 1.11e-14 / 2.04e-14). |
| w067-F3 | minor | **NOT discharged — but self-amended in-file** | The stale “agree within 0.35 absolute” sentence remains at line 142, while revision-2 amendment (a) at line 145 explicitly replaces the agreement test with R5. A one-line rev-4 deletion closes it. |
| w081-WITHDRAWAL | procedural | **STANDS** | A withdrawn author verdict is not dischargeable by new evidence and is not a finding against the protocol text. |

**Bottom line.** The only *blocking* findings were about the evidence basis, not the protocol
text, and the re-based certification removes the text/claim conflict. Two minor text-hygiene
findings remain literally open at `1e6cdf04`; they are non-blocking and closable by a one-line
rev-4 cleanup, which would move the hash and require a fresh review. Controller's call whether
to accept now with the minors noted (this review), or scope a rev 4.

## Independence and authority

* I did not author `numerics/CONVERGENCE_PROTOCOL.md`, `n0_fixed_dt_certification.{py,json}`,
  `numerics/gates.py`, or `numerics/tests/flat_wave_replication.py`. I did author parts of
  `numerics/tests/flat_wave.py` and several N0 reviews, none of which is this target.
* This is **reviewer input**, not a gate verdict: `not_a_gate_verdict = true`,
  `counts_as_g_num_protocol_accept = false`. G-NUM, N0 status and the lock stay controller/
  audit-lead authority. No `validation_status` is promoted.

## Falsifier

Void if any pinned input re-hashes (protocol `1e6cdf04`, certification `1677822c`, frozen module
`8ade1cdc`, published 4-rung `c88146a1`, generator `3c7c9087`); or a declared fit does not
reproduce from its raw rows within `1e-9`; or a fresh re-execution of the frozen instrument at
`dt = 1e-4` fails to reproduce the filed `l2_error` rows; or any major finding has a residue in
the current evidence; or the protocol is revised to a new hash, in which case this verdict binds
only `1e6cdf04`.

## Pins measured at emit time

| input | sha256 |
|---|---|
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920` |
| `numerics/protocol/n0_fixed_dt_certification.py` (measured-only) | `3c7c908783844604…` |
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422` |
| `numerics/tests/n0_order_4rung.json` | `c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a` |
| `reviews/G-NUM-protocol-review.json` (measured-only) | `8137f18f1a3b2b01…` |

## Files

* `verify_c3_discharge.py` — the checker (read-only; stdlib + numpy)
* `raw/report.json` — full machine report: pins, text audit, recomputed ladders, checks, dispositions
* `raw/fresh_rerun.json` — fresh frozen-module rows and runtime
* `raw/run.log` — stdout of the full run
* `checkpoint.json` — checkpoint with artifact hashes
* `emit_events.py` — idempotent, schema-validated event emitter
