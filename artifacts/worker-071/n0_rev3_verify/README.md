# W071-N0-REV3-VERIFY-01 — independent verification of the N0 rev-3 convergence report

**Node** N0 · **class** `AF-WCC-SCALAR-SPH` · **gate** G-NUM · **worker** worker-071
**Verdict: `VERIFIED_AT_PIN`** — 12/12 preregistered checks pass, 5/5 controls fire, no pin
drift during the run. **This is a measurement, not a gate verdict.**

Target: `numerics/results/flat_wave_convergence_rev3.json` at
`sha256 da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3`
(generated 2026-09-12T00:44:23+08:00 by astra-lead-numerics). Verification instant 00:46–00:47.

## What was done

`verify_rev3.py` (stdlib only; imports no builder and no solver) re-derives the certified
numbers from the **raw rung errors** rather than trusting the report's summary fields:

1. **P1–P2 pins** — all 8 preregistered inputs and all 20 embedded `(path, sha256)` pairs in
   the report resolve on disk at the declared hashes (canonical F0 `0abb9ed8a961`, protocol
   `1e6cdf04d7a2`, the 4-rung corpus `c88146a1375c`, the temporal control `334f5b71e0d5`,
   the frozen solver modules).
2. **P3 rungs** — every certified scheme has exactly 4 rungs at `dr = 0.2/0.1/0.05/0.025`
   with `dt = 1e-4` constant and constant step counts (60 000 each).
3. **P4–P6 recomputation** — least-squares order in log–log space re-derived independently
   from cert rows and again from the report's own `l2_error_by_dr` map. Identity to ≤ 1e-15
   against the declared `fit_order` for all three schemes. Pair orders reproduce; the R5
   uncertainty equals `max(pair half-range, least-squares SE)` exactly.

   | scheme | recomputed order | declared | Δ | R5 `delta_R5` |
   |---|---|---|---|---|
   | cnfd | 1.999863592724020 | 1.999863592724020 | 0 | 9.32e-05 |
   | cnfem | 1.999916307987488 | 1.999916307987488 | 0 | 2.46e-04 |
   | lffd | 1.999943173893314 | 1.999943173893314 | 0 | 8.44e-05 |

4. **P7** cross-scheme max |Δp| = 7.958e-05 vs declared 7.958e-05 (bound 0.25); every order
   inside `2.0 ± 0.3`; all ladders monotone.
5. **P8** the certified ladders are the **fixed-dt** ladders; the constant-CFL addendum is
   marked supporting-only and cnfd's constant-CFL ladder is marked inadmissible-as-spatial
   per the temporal control — the report does not quote the inadmissible ladder as spatial.
6. **P9–P12** stop-rule closures are backed on disk: 4 rungs per scheme, F0 rebind resolves to
   canonical rev5, both independent-replication verdicts have resolvable evidence; solver
   absent, lock held, `production_allowed=false`; 58/58 internal checks green; declared
   surface (`numerical_evidence`, G-NUM, `AF-WCC-SCALAR-SPH`, non-empty `claims_not_made`)
   consistent.

**Controls.** K1/K2: synthetic pure-power ladders return p = 2.000000000000000 and
1.000000000000000 exactly. K3: a +20 % perturbation of any single rung error moves the order
by ≥ 2.63e-02, so the declared-vs-recomputed identity check is sensitive. K4: recomputation is
deterministic. K5: all pins re-hashed unchanged at end of run.

The first control run failed (K1/K2 returned 2.0749/1.0749) because the synthetic ladder
carried a non-power-law `(1+d)` factor; that is recorded here because it shows the controls
are load-bearing, and it is why the estimator is asserted only against pure power laws. The
real rung errors reproduce a pure power law to identity.

## Findings (INFO; none blocks the arithmetic)

- **F-071-N0-1 (INFO, scope).** `provenance.solver_rerun = false` and the certification
  generator was not imported by the builder. This verification therefore binds the report's
  arithmetic and pin consistency against the frozen certification artifact — it is **not** a
  fresh numerical run and does not substitute for one.
- **F-071-N0-2 (INFO, registration).** The report's own `registration_state` shows 6
  unregistered paths and 3 registry mismatches (worker-046/057/081 outputs,
  `flat_wave_convergence.json`, `gates.py`). That is a controller-registry step, not an
  arithmetic defect; every pin the report itself declares resolves.
- **F-071-N0-3 (INFO, adjudication, not arithmetic).** The report's caveat that the
  replication verdicts are worker-local and the protocol-review contest (3 accepts vs 2
  dissents, with one withdrawn accept still counted by `numerics/gates.py`) are live
  adjudication items for the controller/lead. This verification does not resolve them and must
  not be cited as doing so.

## Limits and falsifier

Read-only on every canonical path; writes only under `artifacts/worker-071/n0_rev3_verify/`.
No status=done, no `validation_status=passed`, no gate verdict, no self-gravitating claim.
Verdict binds only the listed pins; any write to a pinned path voids it at that pin.

**Falsifier:** re-run `verify_rev3.py` at the pinned hashes — any P check FAIL, any control
not firing, or any pinned-hash change falsifies or voids this verification.

## Files

| file | role |
|---|---|
| `PREREGISTRATION.json` | checks, controls, tolerances and verdict rule, written before the run |
| `verify_rev3.py` | independent verifier (stdlib only) |
| `report.json` | machine-readable per-check results and measured values |
| `snapshot/` | byte copies of the two certified inputs at the pinned hashes |
| `SHA256SUMS` | hashes of the above |
