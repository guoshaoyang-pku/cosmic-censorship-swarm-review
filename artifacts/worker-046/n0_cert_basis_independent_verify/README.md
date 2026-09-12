# W046-N0-CERTBASIS-INDEP-01 — independent verification of the current G-NUM certification basis

**Worker:** worker-046 (bounded execution worker, slot 046 — fifth lifecycle)
**Node / gate / class:** `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH`
**Target:** `numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920`
**Verdict:** `SUPPORTED` — 10/10 primary criteria, 6/6 controls, 0 failed criteria
**Authority:** worker-level evidence only. No gate verdict, no node transition, no canonical write, no self-pass.

## Why this task

No `comms/inbox/worker-046.jsonl` card exists, so the task was claimed from the live controller reason
for G-NUM (`runtime/state/controller_verification/lifecycle_20260912-003718.json`): the N0 stop-rule
items (4th resolution / F0 re-bind / independent replication verdict) are the open requirement. The
numerics lead re-based the certification onto the protocol-section-3.4-exact fixed-`dt` ladder
(`numerics/protocol/n0_fixed_dt_certification.json`, generated 00:35:15) and then exited. That artifact
is now the basis of the G-NUM claim, and it had no independent check **at its own hash**: the existing
worker-level checks either re-derived its arithmetic from its embedded rows (worker-057) or re-ran the
protocol ladder against the older published artifact (worker-046 lifecycles 2–4).

This lifecycle supplies the two missing legs at the pinned hash: a **full independent re-execution of
all 12 fixed-`dt` rungs against the hash-guarded frozen module**, and a **hash-anchored class-binding
check to F0 rev5** using the canonical class-separation detector.

## Method (read-only on every canonical path; writes only in this directory)

1. **Pins.** Measure SHA-256 of the certification, frozen module, protocol, published 4-rung artifact
   and F0 taxonomy; require frozen module `8ade1cdc…`, protocol `1e6cdf04…`, F0 rev5 `0abb9ed8…`.
2. **Arithmetic re-derivation.** From the artifact's own `(dr, l2_error)` rows, refit with an
   independently implemented OLS (normal equations, residual-based slope SE — not `np.polyfit`):
   order, slope SE, pair orders, pair half-range, `delta_R5 = max(half-range, SE)`, residuals.
3. **Cross-scheme R5.** Recompute pairwise `|dp|` from the independently derived orders vs bound 0.25.
4. **Re-execution.** Import the frozen module under a hash guard and re-run the full 3 schemes × 4 rungs
   at `dt = 1e-4` (`dr = 0.2/0.1/0.05/0.025`, 60,000 steps per rung); compare every `l2_error` row and
   the refit orders to the artifact.
5. **Class binding.** F0 rev5 `classes["AF-WCC-SCALAR-SPH"]` present; certification declares
   `conclusion_type: numerical_evidence` (not the class conclusion `weak_cosmic_censorship`); canonical
   `class_separation.findings()` clean; all class-conclusion phrases exempted as negation/`not_claimed`;
   explicit flat-space discretisation scoping.
6. **Controls C1–C6** (below), plus a no-write drift canary over the five canonical paths.

## Result

| scheme | declared p | refit p (independent) | re-executed p (12/12 rows bitwise equal) | pair orders in 2.0±0.3 | ΔR5 |
|---|---|---|---|---|---|
| lffd | 1.999943173893314 | 1.999943173893314 | 1.999943173893314 | yes | 8.4437e-05 |
| cnfd | 1.9998635927240203 | 1.9998635927240203 | 1.9998635927240203 | yes | 9.3177e-05 |
| cnfem | 1.9999163079874884 | 1.9999163079874884 | 1.9999163079874884 | yes | 2.4644e-04 |

- All 12 re-executed `l2_error` rows are **bitwise equal** to the certification rows; the refit orders
  from the fresh rows equal the declared orders exactly.
- `delta_R5 == max(pair half-range, slope SE)` holds for all three schemes; max pairwise `|dp|` is
  7.958e-05 against the R5 bound 0.25.
- The constant-CFL ladder is present only as a relabelled mixed-order control (`dt != 1e-4`, order
  reproduced, fixed-`dt` R5 deltas strictly smaller): the certification is not a relabel of the
  superseded basis.
- Class binding: F0 rev5 contains `AF-WCC-SCALAR-SPH`; the artifact asserts `numerical_evidence` and no
  class conclusion; canonical classsep regression `17 leaks / 10 controls / VERDICT: PASS` (C6).

### Controls

| id | control | observed | pass |
|---|---|---|---|
| C1 | +1% tamper on one cnfem row must move the refit order | detected | ✅ |
| C2 | dropping one lffd rung must fail the 4-rung rule | detected | ✅ |
| C3 | `dt = 2e-4` on one cnfd row must fail the fixed-`dt` rule | detected | ✅ |
| C4 | two refits of the same rows bitwise equal | equal | ✅ |
| C5 | no-write drift canary over 5 canonical paths | no drift | ✅ |
| C6 | canonical `runtime/bin/classsep_regression.py` | 17/17, 10/10, PASS | ✅ |

### Findings

- **F-1 (soft, documentation).** The certification carries no F0 taxonomy hash, so its class binding is
  not hash-pinned inside the artifact. This check supplies the anchor at read time: F0 rev5
  `0abb9ed8a961…` (match = true). Owner for an in-artifact pin: astra-lead-numerics / controller
  checkpoint registration. No effect on the measured orders.

### Overlap disclosure (honest)

- **worker-057** (`W057-N0-FIXEDDT-VERIFY-01`, `artifacts/worker-057/n0_fixeddt_verify/report.json#b906445878f3`)
  independently re-derived the same artifact from its embedded rows: `REPRODUCED`, 67/67 checks, advisory
  review `accept 4.0`. That check did **not** re-execute the frozen module and did **not** bind to F0.
  This lifecycle's arithmetic leg independently corroborates it; the re-execution and F0-anchor legs are
  net-new here.
- **worker-071** (`n0_rev3_verify`, `report.json#6bbc2d4918`) re-verifies the rev-3 convergence artifact
  at adjacent pins; different target.
- **worker-046 lifecycles 2–4** re-executed the protocol / published-4-rung ladder
  (`n0_4rung_independent`, `n0_independent_replication`, `n0_fixed_dt_independent`) but not this
  certification artifact, which did not exist at their start.

## Falsifier

Withdraw if any of: (a) any pinned input hash changes at re-check time (frozen module `8ade1cdc`,
protocol `1e6cdf04`, F0 rev5 `0abb9ed8`, certification `1677822ceb9c`) — a mismatch voids the
comparison, fail closed; (b) a re-execution of the frozen module at any fixed-`dt` rung disagrees with
the certification row by more than 1e-12 relative; (c) an independent fit places any scheme's order
outside 2.0 ± 0.3 or a pairwise `|dp|` above the R5 bound 0.25; (d) the certification is shown to
assert the `AF-WCC-SCALAR-SPH` class conclusion; (e) the constant-CFL ladder is shown to be the actual
certification basis.

## Scope limits

Worker-level evidence only: no gate verdict, no node completion (N0 stays active/unverified),
`numerics_lock` stays LOCKED, no self-gravity / N1 / WCC / SCC claim, no statement that the
certification's evidence is sufficient for a G-NUM pass. The check is deterministic (no RNG) and
read-only on canonical paths; the drift canary confirmed no canonical bytes changed across the cycle.

## Files

- `verify_cert_basis.py` — checker (independent OLS + re-execution + binding + controls)
- `results.json` — machine results (criteria, per-scheme arithmetic, re-execution, binding, controls)
- `verification.json` — verdict package (+ evidence refs, concurrent-verification disclosure)
- `run.log` — stdout of the checker run
- `MANIFEST.json` — SHA-256 of every file above and of the pinned inputs
- `CHECKPOINT.json` — compact lifecycle checkpoint (mirrored to `runtime/state/`)
