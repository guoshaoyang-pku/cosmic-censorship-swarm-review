# W081-N0-C8-ADJ2-03 — rev-3 protocol review contest, adjudicated against the re-based evidence

**Question (named condition #1 of `numerics/tests/n0_gate_proposal.json#b4192221ff7d96db`).**
Two `revise` verdicts sit at `numerics/CONVERGENCE_PROTOCOL.md` sha256 `1e6cdf04d7a24313` —
worker-067 finding **F1** and worker-081 finding **F1'** — alongside a binding audit `accept`.
The certified spatial-order evidence has since been replaced by
`numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8` (fixed `dt = 1e-4` on every
rung). *Do F1 and F1' still block?*

**Answer: no — both are discharged by supersession, by measurement, not by assertion.**

| field | value |
|---|---|
| task | `W081-N0-C8-ADJ2-03` (bounded class-bound task, taken per the W081/W020/W046 pattern) |
| actor / instance | `worker-081` · `worker-081-20260912T002948-968807` |
| class / node / gate | `AF-WCC-SCALAR-SPH` · `N0` · `G-NUM` |
| instrument | `artifacts/worker-081/n0_c8_adjudication_rev2/adjudicate_review_contest.py` |
| runtime | 0.12 s, CPU only, read-only on all canonical paths |
| validation_status | `unverified` (worker evidence; not a gate verdict, not a node completion) |

## Checks (all hash-pinned; declared before running; pins re-measured unchanged after)

| # | check | result |
|---|---|---|
| **B** | §3.4 fixed-`dt` clause and "`dt ∝ h` … never quoted as spatial" clause present, line 58; all 12 certification rows have `dt == 1e-4` exactly; rungs `0.2/0.1/0.05/0.025`; 60 000 steps | **pass** |
| **C** | independent recomputation, own arithmetic, of fit order, pair orders, half-range, least-squares SE, residuals, `delta_R5 = max(half-range, SE)`, monotonicity, band, and all three cross-scheme `|Δp|` against the R5 rule | **pass** (max rel. err **2.96e-12**) |
| **D** | proposal certified orders equal the certification orders; `certified_study` / `certified_driver` refs bind to the measured hashes; the constant-CFL study `c88146a1375c50f0` is cited only under mixed-order / control / supersedes / registry paths (4/4 labelled) | **pass** |
| **E** | F1′ falsifier predicate: filed constant-`dt ≤ 1e-3` ladders with ≥ 3 rungs — **9 found** (3 × `dt=1e-4`, 6 × `dt=1e-3/5e-4`), each 4 rungs; F1's premise ("certified claim uses `dt ∝ h`") is now false; both dissent records present in the proposal | **pass** |
| **F** | `numerics/gates.py::_protocol_review` read-only tally at the current hash | accept present; **contest still mechanically true** (see finding 2) |
| **P** | all 8 input pins re-measured before and after | **unchanged** |

Recomputed fixed-`dt` orders: **lffd 1.999943173893314 / cnfd 1.9998635927240203 /
cnfem 1.9999163079874884**; `delta_R5` 8.44e-05 / 9.32e-05 / 2.46e-04; max pairwise `|Δp|`
**7.958116929396297e-05** vs the 0.25 R5 floor (filed 7.958116929374093e-05; rel. diff 2.8e-12).

## Disposition

**`F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION`.** Both dissents were objections to the *evidence
basis* (the certified claim used constant-CFL runs that §3.4 excludes), not to the protocol
text. The evidence basis now satisfies §3.4 exactly; the dissents' factual predicate is cured.
The standing audit `accept` at `1e6cdf04d7a2` is the operative protocol verdict. The dissents
remain on the record as historically valid — this adjudication deletes nothing.

In particular, **W081's own F1′ review is closed by its own published falsifier**: that falsifier
states the finding "is falsified if a filed study with constant `dt ≤ 1e-3` across ≥ 3 rungs
exists". Nine such ladders now exist (E, above). The measurement behind F1′ was correct at its
time; the remedy has landed, so the blocking force of that verdict is spent. The author records
this rather than leaving a stale dissent standing.

## Findings for the controller (condition #1 closure)

1. **Discharge is evidenced, not asserted.** All structural, arithmetic and binding checks pass
   at the pinned hashes; the certification rows are `dt = 1e-4` exactly, and its internal
   statistics reproduce to ≤ 3e-12 relative. (Row-level numerical re-run of the certification
   ladder is a separate task, `worker-046`'s independent replication — not claimed here.)
2. **The guard cannot mechanically clear the contest.** `_protocol_review` counts *every* review
   event: it lists both W081 verdicts (the withdrawn `accept` and the later `revise`), plus
   worker-067's `revise`, so `contest = true` remains even though F1/F1′ are discharged. A later
   `accept` from a dissent author does not rescind the earlier `revise`. To close G-NUM's
   condition #1, Astra needs either an explicit disposition the guard consumes, or a guard rule
   that supersedes earlier verdicts by `(reviewer, target)` at the same protocol hash. This
   adjudication supplies the evidence for that disposition; it cannot perform it.
3. **The superseded constant-CFL study is correctly relabelled.** It appears in the proposal only
   under `relabelled_mixed_order_control`, `also_available_but_mixed_order`, a mixed-order
   criterion context, and the hash registry — never as the certification basis.
4. **Scope limits.** No gate verdict, no node completion, no canonical file edited,
   `numerics_lock` stays `LOCKED`, `numerics/spherical_solver` remains absent.

## Falsifier (binds this adjudication)

Re-measure the pins: if `numerics/CONVERGENCE_PROTOCOL.md` is not `1e6cdf04d7a24313` or
`numerics/protocol/n0_fixed_dt_certification.json` is not `1677822ceb9c81e8`, this adjudication
does not bind. It is falsified if any certification row has `dt ≠ 1e-4`, if the recomputed
statistics disagree with the certification beyond 1e-9 relative, if the certified claim again
cites a constant-CFL study as its basis, or if no filed constant-`dt ≤ 1e-3` ladder with ≥ 3
rungs exists (then F1′'s falsifier predicate is unmet and the dissent stands).

## Files

| file | role |
|---|---|
| `adjudicate_review_contest.py` | harness: pins, B/C/D/E/F checks, verdict rule |
| `adjudication.json` | full machine-readable result, guard tally, falsifier |
| `checkpoint.json` | worker checkpoint: artifact hashes, pins, disposition, next falsifier |
| `finalize_rev2.py` | checkpoint writer + schema-validated event emitter |
| `README.md` | this file |

Related (not superseded): `artifacts/worker-081/n0_c8_adjudication/` (the F1′ measurement, 00:29);
`artifacts/worker-081/n0_fixed_dt_certification/` (an earlier plan of this slot whose pin guard
aborted when `n0_gate_proposal.json` moved `58a175b52fbe → b4192221`; `fixed_dt_study.json`
records `status: input_moved`).
