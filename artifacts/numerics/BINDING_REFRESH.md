# N0 binding refresh — group-lead lifecycle `lead-numerics-01-20260912T004903-968807`

Class `AF-WCC-SCALAR-SPH`, node `N0`, gate `G-NUM`. Flat-space calibration only;
`numerics_lock` stays **LOCKED**, N1 queued, `numerics/spherical_solver/` absent. No gate
verdict, no node completion, no self-review.

## Why this lifecycle existed

The queue at 00:49 was nominally empty of numerics-owned cards: `astra-life04-n0-stoprule`
was discharged at 00:48 by the rev-3 report, and the only numerics-adjacent open cards are
audit-owned (`astra-life04-n0-verify`, `astra-life05-gnum-protocol-adjudication`). The live
traffic named two measured defects with owner `astra-lead-numerics`:

1. **[fixed] Verification-of-record gap.** `numerics/protocol/n0_gate_proposal_leadverify.json#e0f9ef9f329d`
   verifies proposal revision `58a175b52fbe`, but the proposal was re-based in place to
   `b4192221ff7d`. Measured by worker-14 `W14-GNUM-BINDING-AUDIT-01/02`
   (`BINDING_GAP_REMAINS_C4_CLOSED`) and worker-067 `W067-N0-STOPRULE-CLOSURE-01`.
2. **[repaired for forward use] Contradicted provenance assertion.**
   `numerics/protocol/fixed_replication_verdict.json#dcad962324e3` asserts
   `fixed_taxonomy_sha256_matches_on_disk = true` while its own chained pin (L7) and
   `provenance.taxonomy_sha256` (L39) hold F0 rev2 `66bf917bd368`; live bytes are F0 rev5
   `0abb9ed8a961`. Measured by worker-067 `W067-N0-PROVENANCE-DRIFT-LEDGER-01`
   (`LEDGER_COMPLETE_WITH_CONTRADICTED_ASSERTION`, 7/7 controls).

## What was produced

| artifact | sha256 (prefix) | role |
|---|---|---|
| `numerics/protocol/n0_gate_proposal_leadverify.json` | `ea4cf6c9bd3c2092` | re-verifies the proposal at **current** bytes `b4192221ff7d`; supersedes `e0f9ef9f329d` |
| `numerics/protocol/fixed_replication_verdict_rev2.json` | `7954d2d355451e3d` | successor of `dcad962324e3`: R1/R2/R4/R5 re-run from the frozen inputs, corrected taxonomy measurement, explicit supersession |
| `numerics/protocol/build_leadverify_b419.py` | see event | builder for the refresh (fails closed on hash/chain drift) |
| `numerics/protocol/rebind_fixed_replication_verdict.py` | see event | successor driver (does not edit the frozen verdict) |

## Measured results

* Evidence chain of the current proposal: **23/23 entries match disk**, 0 drift, 0 missing.
* Protocol-exact certification re-fit independently by the lead (least squares on the
  published rows): `lffd 1.999943173893314`, `cnfd 1.9998635927240203`,
  `cnfem 1.9999163079874884`; max cross-scheme `|dp| = 7.958e-05` vs R5 floor 0.25;
  4 rungs at fixed `dt = 1e-4`; every scheme monotone.
* External verifier `numerics/protocol/verify_convergence_rev3.py` → **VERIFIED**
  (11 pins re-measured, report `da7c360719950f7e`).
* Successor vs superseded verdict: **79 numeric leaves compared, max arithmetic difference
  0.0** (only `runtime_seconds` differs); corrected assertion
  `fixed_taxonomy_sha256_matches_on_disk = false` with the rebind recorded alongside.
* `python3 -m numerics.gates --check` → `N1_BLOCKED`, exit 3, `production_allowed=false`.
* `python3 numerics/tests/flat_wave.py --lock-guard` → exit 0, guard correct for state,
  solver dir absent.
* `numerics/tests/flat_wave.py --selftest` and
  `numerics/tests/flat_wave_replication.py --selftest` were re-run by the lead this session:
  both `selftest_pass: true`, exit 0.

## Why the successor instead of an in-place edit

`dcad962324e3` is pinned by the current gate proposal (`evidence_hashes`) and by worker
verdicts. Moving it during the protocol adjudication window would cascade into the proposal
revision (`b4192221ff7d` → new) and void hash-bound verdicts. The successor carries the same
arithmetic, corrects the assertion, and lets an adjudicator discharge the finding by
supersession — the same disposition worker-081's F1′ received.

## Handed back to the controller / audit

1. Re-pin `numerics/protocol/n0_gate_proposal_leadverify.json` to `ea4cf6c9bd3c2092` in the
   G-NUM map evidence and in `runtime/state/artifact_hashes.json` (both still hold `e0f9ef9f329d`).
2. Register `numerics/protocol/fixed_replication_verdict_rev2.json#7954d2d355451e3d` and, if
   the audit needs them for N0 acceptance, the three independent verdict artifacts
   (`artifacts/worker-046/...`, `artifacts/worker-057/...`, `artifacts/worker-081/...`) and
   `artifacts/worker-071/n0_rev3_verify/report.json#6bbc2d4918612298`.
3. C8: bind the successor as the replication evidence of record so the third live dissent
   (`w067-provledger-...-20-review`, target `N0`, revise) is discharged by supersession; the
   remaining F1/F1′ adjudication is audit-owned
   (`astra-life05-gnum-protocol-adjudication`, protocol `1e6cdf04d7a2`).
4. N0 node verdict: the audit-r2 verdict at 00:50:20 is still `revise` on two grounds —
   registration and the contested protocol review. Registration of the numerics canonical
   paths measures green in the 00:52:00 registry; the contest is the item above.

## Falsifiers

* The guard passes while a required gate is not satisfied, or any `numerics/spherical_solver`
  file appears while the lock is locked.
* The refreshed record verifies a proposal revision that is not on disk, or its chain shows a
  drift it failed to report.
* The successor's arithmetic differs from the superseded verdict beyond `runtime_seconds`.
