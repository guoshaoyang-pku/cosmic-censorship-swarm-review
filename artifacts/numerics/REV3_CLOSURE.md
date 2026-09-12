# N0 rev-3 closure — numerics lead lifecycle 2026-09-12T00:38–00:47 (+08:00)

Scope: **N0 flat-space calibration only**. `numerics_lock` stays **LOCKED**, N1 stays **queued**,
`numerics/spherical_solver/` absent. No gate verdict is set here.

## Card consumed

`astra-life04-n0-stoprule` (comms/inbox/astra-lead-numerics.jsonl, 2026-09-12T00:36:01+08:00),
closing the stop rule of `reviews/N0-review-lead-audit.json#revise`:
add a fourth resolution rung (or scope with tolerance), re-bind the class to F0 rev5, supply one
independent replication verdict of the order at the frozen run hash, and report the order even if
it degrades.

## Outcome — all three predicates closed

1. **Fourth rung, not scoping.** Certification basis =
   `numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8`:
   4 rungs per scheme (`dr = 0.2, 0.1, 0.05, 0.025`), `dt = 1e-4` fixed on every rung,
   3 schemes. Measured spatial order (integral L2):

   | scheme | p | δ_R5 |
   |---|---:|---:|
   | lffd | 1.999943 | 8.44e-05 |
   | cnfd | 1.999864 | 9.32e-05 |
   | cnfem | 1.999916 | 2.46e-04 |

   max cross-scheme |Δp| = **7.958e-05** vs R5 floor 0.25. **The order did not degrade** — it is
   tighter than the constant-CFL mixed-order values it replaces (which are retained only as
   labelled diagnostics; the temporal-admissibility control marks cnfd's constant-CFL ladder
   inadmissible as spatial evidence).
2. **F0 rev5 binding.** `research_map/formulation_taxonomy.yaml#0abb9ed8a961`, revision 5 on disk.
   The protocol preamble still cites the superseded `66bf917b`/`565a6e50` pins; that citation is
   not load-bearing and is reported rather than rewritten (a rewrite would invalidate every
   verdict bound to `1e6cdf04`).
3. **Independent replication verdicts** (all authored by other agents, hash-pinned):
   - worker-046 `artifacts/worker-046/n0_fixed_dt_independent/verification.json#814452111bc8912b`
     — from-scratch re-execution of the frozen module, `SUPPORTED`, 8/8 criteria.
   - worker-057 `artifacts/worker-057/n0_fixeddt_verify/report.json#b906445878f3130d`
     — independent re-analysis of the filed rows, `REPRODUCED`, 67 checks / 65 pass /
     2 documentation advisories / **0 findings**, certification hash stable.
   - worker-081 `artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json#65ae766d9e4c2057`
     — review `w081-20260912T0042050800-adj2-review`, `accept`, disposition
     `F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION`.

## Deliverable

`numerics/results/flat_wave_convergence_rev3.json#da7c360719950f7e`
— builder `numerics/protocol/build_convergence_rev3.py#87f0c6f22f0265bc` (58/58 internal checks),
verifier `numerics/protocol/verify_convergence_rev3.py#b3c487114d295e3f` → `VERIFIED`
(11 pins re-measured independently of the builder).

## Open items handed back (not numerics-side)

1. **C4 registration**: `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04`, the rev-3 report,
   `numerics/gates.py#fcd1d709`, and the three independent verdict artifacts are not registered in
   `runtime/state/artifact_hashes.json`.
2. **Stale G-NUM map pins**: `evidence_refs` cite `numerics/gates.py#907a88b141bf4394` and
   `numerics/tests/n0_gate_proposal.json#22d984781cee/#58a175b52fbe`; the unmet list predates the
   fixed-dt certification and the independent verdicts.
3. **Protocol review contest**: 2 accepts vs 2 live revise dissents at `1e6cdf04`; the binder
   still counts the withdrawn accept `w081-20260912T002140-c8-review` and has no
   (reviewer, target)-at-one-hash supersession rule. Needs controller/reviewer disposition.
4. **N0 node-status mis-transition**: the map currently reads `N0.status == 'rejected'`, applied
   at 00:43:08 from worker-081's *task* withdrawal `w081-20260912T0042190800-fdt02-withdrawn`
   (its fixed-dt ladder became redundant once the certification was filed). The withdrawal's own
   falsifier says a new ladder is needed only if the certification is withdrawn or moves; it has
   not moved, and the stop-rule evidence is unchanged on disk. Node status should be re-derived
   from node-scoped acceptance state, and `N0` restored to active/unverified pending adjudication.

Consequence: `numerics.gates` reports `N1_BLOCKED` (exit 3). N1 release still requires G-FORM and
G-AUDIT pass plus the controller's map update; nothing in this lifecycle touches that authority.
