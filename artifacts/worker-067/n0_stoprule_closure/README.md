# W067-N0-STOPRULE-CLOSURE-01 — G-NUM stop-rule closure ledger

**Worker** worker-067 · **class** `AF-WCC-SCALAR-SPH` · **node** `N0` · **gate** `G-NUM`
**Actor authority** bounded breadth worker. This is a closure **audit**, not a gate verdict,
not a node transition, and not a `numerics_lock` change.

## Why this task

The live controller gate audit names exactly three open requirements for G-NUM:

> "the stop-rule items (4th resolution / F0 re-bind / independent replication verdict)
> are the open requirement"
> — `runtime/state/controller_verification/lifecycle_20260912-003718.json`,
> `controller_gate_audit.G-NUM.reason`, at map sha `3d45be5969ec`

Assignment `astra-life04-n0-stoprule` (lead-numerics, deadline 02:30) generated the
evidence; `astra-life04-n0-verify` (lead-audit, 03:00) owns the node verdict. No worker had
produced a single hash-bound ledger of whether each **named** item is closed, so this task
audits binding/closure of the already-filed evidence — it does **not** re-run the solver
(independent re-runs exist: worker-046, worker-055, worker-057, worker-081, deepseek-flash-20).

## Verdict

`ALL_THREE_ITEMS_ADDRESSED_WITH_ONE_RESIDUAL_AND_ONE_BINDING_DRIFT`

| item | status | measured basis |
|---|---|---|
| **I1 fourth resolution** | **MET** | `numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8` — 4 rungs (0.2/0.1/0.05/0.025), `dt = 1e-4` on every rung of all three schemes, orders 1.999943/1.999864/1.999916, all monotone, all in band; proposal re-binds the certification at the measured prefix; the old constant-CFL ladder is relabelled mixed-order (proposal headline + `supersedes_evidence_basis`). |
| **I2 F0 re-bind** | **PARTIAL_RESIDUAL** | `numerics/tests/n0_gate_proposal.json#b4192221ff7d` pins the measured canonical rev5 `research_map/formulation_taxonomy.yaml#0abb9ed8a961`. Residual: `numerics/protocol/fixed_replication_verdict.json#dcad962324e3` still carries the superseded rev2 hash `66bf917b…` in `chained_evidence_hashes` and `provenance.taxonomy_sha256`. The prior worker-067 check measured that re-bind **inert for class membership** (`artifacts/worker-067/n0_f0_rebind/rebind_check.json#22afbea8a137`, 5/5 controls), but the artifact was not repaired. |
| **I3 independent replication verdict** | **MET** | Frozen run `n0_replication_astra_run2_FIXED.json#6542db93eebc` carries a binding accept (deepseek-flash-14, 00:07, numerics-group member); the re-based certification `#1677822ceb9c81e8` carries external advisory accepts (worker-081 00:42:05, worker-057 00:42:30). **Binding drift:** no external (non-numerics) verdict binds the frozen 3-rung run, whose accept predates the re-basing to the fixed-dt basis. |

Lock state is unchanged and intact: `numerics_lock.state = locked`, `locked_nodes = ["N1"]`,
`numerics/spherical_solver` absent, guard `numerics/tests/selfgravity_lock_guard.py` present.
The N0 node verdict on disk is still `reviews/N0-review-lead-audit.json#e3c314f886be`
(revise 3.5), explicitly superseded for adjudication by `astra-life04-n0-verify`.

## Method

`check_stoprule_closure.py` measures twelve anchors before and after the run, decides each
item from machine checks only, and fails closed (exit 2) on any anchor drift or failed
control. Mutation controls operate on **in-memory copies**; no canonical path is written.

Controls (5/5 pass in `closure.json`):

- **C1** no-write canary — all twelve anchors byte-identical before/after.
- **C2** certification mutated in memory to 3 rungs → I1 flips to `NOT_MET`.
- **C3** proposal F0 pin mutated in memory to rev4 `276009f4` → I2 flips to `NOT_MET`.
- **C4** independence classifier: `astra-lead-numerics` → self, `deepseek-flash-14` →
  numerics-group member, `worker-057` → external.
- **C5** lock guard: live predicate true; in-memory `unlocked` mutation is detected.

## Falsifiers

- **I1** void if the certification at the measured hash shows <4 rungs, non-constant `dt`,
  a non-monotone scheme, an order outside `2.0 ± 0.3`, or its proposal pin stops resolving.
- **I2** void if the proposal's F0 pin no longer equals the measured canonical taxonomy hash,
  or the stale rev2 pins are shown load-bearing for the order claim (inert for class
  membership was measured; load-bearing for the order is a separate claim).
- **I3** void if no accept binds either frozen hash at re-measurement, or the frozen-run
  accept is shown to be authored by the run's own author.
- **Ledger** void for the recorded anchor hashes if any anchor moves; the script refuses.

## Reproduction

```bash
python3 artifacts/worker-067/n0_stoprule_closure/check_stoprule_closure.py \
    --root /data3/guoshaoyang/workdir/ai4math-swarm
```

## Non-claims

No gate verdict; no N0 node completion/status; no `numerics_lock` release; no solver re-run;
no adjudication of the protocol-review contest (worker-081's task); no claim that any review
dissent is formally discharged.
