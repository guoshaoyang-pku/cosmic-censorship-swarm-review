# W014-GNUM-CARRIER-VERIFY-01 — independent verification of the N0 class-binding authority record

**Verdict: `CARRIER_RECORD_VERIFIED`** (worker-level; exit 0). Target:
`numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419`,
authored by `astra-lead-numerics`, which itself requests independent review and is the declared
discharge condition for `HF-042-N0-1` (worker-042) and `HF-081-PS-1` (worker-081).

Node / gate / class: `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH`. Read-only: no canonical artifact was
written; no solver was imported, built, or run; `numerics_lock` stayed LOCKED.

## What was measured (all at the reviewed hashes)

| Claim | Result |
|---|---|
| Record identity | `effd20b0ea09…` measured, matches its event |
| 8 declared `(path, sha256)` pins in the record (carrier, binding, protocol ×2, 4 basis-evidence prefixes) | 8/8 match disk, 0 mismatched, 0 missing |
| Carrier declares F0 rev5 | `class_binding.sha256 == 0abb9ed8a961…`, `declared_revision == 5`, `class_id == AF-WCC-SCALAR-SPH`, `stop_rule_closures.f0_rebind` names rev5 |
| Live taxonomy at the binding pin | `revision: 5`, contains `AF-WCC-SCALAR-SPH` |
| Protocol byte-preservation | `1e6cdf04d7a2…` unchanged; still cites `66bf917bd368` (line 7) and `565a6e50` (line 159); the record's locations (line 7; 157–160) cover both |
| Single carrier | exactly one class-binding carrier path named across the reviewed evidence set: `numerics/results/flat_wave_convergence_rev3.json` |
| Materiality | `n0_fixed_dt_certification.json` has **0** taxonomy-string hits; an independent log–log LSQ refit from the raw rungs reproduces all three declared fit orders to **0.0e+00** (cnfd 1.999863593, cnfem 1.999916308, lffd 1.999943174) and all pair orders exactly |
| Drift-audit reproduction | the lead's read-only `audit_registration_drift.py#5031ffb3024f` re-run (redirected to scratch) exits 0, verdict `CLEAN`, `pin_summary` identical to the filed audit (13 declared, 10 registry matches, 3 unregistered), refit schemes identical, A1–A5 true, A6 false by design |
| Lock guard | `numerics_lock.state == "locked"`, `numerics/spherical_solver/` absent, `numerics/gates.py` → `N1_BLOCKED`, `production_allowed == false` |
| Controls | 7/7 behaved as declared (carrier-hash corruption caught, one-hex basis-prefix corruption caught, missing path detected, taxonomy revision mutation caught, 5 % rung perturbation pushed the refit beyond 1e-6, drift guard self-test detected a mutation, canonical tree unchanged) |
| Determinism | two full runs byte-identical after removing the advisory clock block; all canonical input hashes identical before and after the run |

## Honest run history (failures recorded, not hidden)

The **first** instrument run exited 2 with five failing checks. All five were **instrument
defects, not record defects**, and were repaired before the recorded run:

1. `basis_evidence` entries carry a trailing annotation (`#def37cffb7db (revise; …)`) that the
   parser folded into the declared hash → parse only the leading hex run.
2. the F0-rev5 check demanded the full 64-hex hash while the carrier cites the 12-hex prefix →
   accept prefix or full.
3. the LSQ convention had the wrong sign (`e ~ dr^p` slope is positive as filed) → fixed.
4. the drift-audit re-run wrote to a scratch directory that did not yet exist → create it first.
5. the lock-guard check returned `ok` but no `pass` key → fixed.

The first failing report is superseded; only `report.json` (sha256 below) is the verification of
record. No prediction in `PRE_REGISTRATION.md` was re-labelled; every one now holds as declared.

## Residual notes (do not affect the verdict)

- **N1 (advisory, non-load-bearing):** the record's `published_at` (`01:02:00`) is ahead of its
  own file mtime (`01:00:07`) and of the lead's artifact event (`01:00:54`) — the known
  clock-discipline pattern (CF-6/CF-14). It changes no hash and no claim; annotation is the
  author's/controller's call.
- **N2 (for the audit lead, not mine to adjudicate):** the drift-audit re-run at ~01:05 sees
  **five** contesting revise reviews (`w067` ×2, `w081` F1′, `w042`, `w081` pin-split) against
  two accepts, where the filed audit recorded two. The reproducibility claim above compares
  `pin_summary` and `verdict`, which match; the C8 contest itself is unchanged in kind and
  remains `astra-life05-gnum-protocol-adjudication` territory.
- **N3:** this task deliberately does **not** review the carrier record's *authority* to bind
  (controller ratification) nor the C8 supersession semantics; both are outside worker scope.

## Reproduce

```bash
cd artifacts/worker-14/carrier_verify
python3 verify_carrier.py --out report.json   # exit 0 == CARRIER_RECORD_VERIFIED
```

Artifact hashes: `report.json#e67fdaafc999c80f` (full
`e67fdaafc999c80f491da290198163fd5c066a92d7765da388ef6176e6d0aabd`),
`verify_carrier.py#ce59c3025933f68400a58717ffba6bafc19b6849d4dcf3d5db930c9ae8eac803`,
`PRE_REGISTRATION.md#c183a89518a9111a07379f2aa29016a0e71b6c4561874907a3744d43cdf25db5`.
Checkpoint: `runtime/state/w014_carrier_verify_checkpoint.json`.

## Does not claim

Not a G-NUM gate verdict and no gate self-pass (Astra / lead-audit authority); not controller
ratification of the record; not an N0 node completion or status transition; not an adjudication
of the C8 protocol-review contest; no physics / self-gravity / WCC / SCC claim. `numerics_lock`
stays LOCKED and N1 stays queued.
