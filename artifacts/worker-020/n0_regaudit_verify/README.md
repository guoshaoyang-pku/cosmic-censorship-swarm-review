# W020-N0-REGAUDIT-VERIFY-01 — independent non-author verification of the N0 registration-drift audit

**Slot** `worker-020` · **Class** `AF-WCC-SCALAR-SPH` · **Node** `N0` · **Gate** `G-NUM`
**Target under review** `numerics/protocol/n0_registration_drift_audit.json#22edbcc61df7`
(astra-lead-numerics, lifecycle 06, `verdict: CLEAN`)
**Companion under review** `numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea09`
(same author; its own `review_request` asks for independent review at that hash)
**Verdict** `REGAUDIT_CENSUS_AND_ORDER_REFIT_INDEPENDENTLY_REPRODUCED` · **review** `accept` 4.0 · no hard failures
**N1 lock** `numerics_lock.state == "locked"` throughout; `numerics/spherical_solver/` absent and never written or proposed.

## Why this task

The audit landed at 01:00:54 with no independent verdict, and its falsifiers are executable.
Its own blocker asks the controller to register three replication verdicts before any N0 `done`
claim. Worker-020 is a non-author of the audit, the companion record, the certification, the
frozen module and the three replication verdicts, so it can re-measure the census and re-derive
the order claim from raw rows without importing the audit generator.

## Method (read-only outside `artifacts/worker-020/`)

1. **Freeze** byte-identical snapshots of the target, the companion, the certification, the
   protocol, the rev-3 closure, the taxonomy, the registry and the map (`snapshots/`), with a
   byte-identity assert after each copy.
2. **Re-measure all 13 declared pins** against disk and against
   `runtime/state/artifact_hashes.json` (union of its `hashes` and `registry` maps) with this
   script's own hashing and registry code — no import of `audit_registration_drift.py`.
3. **Re-derive the whole order claim** from the raw `dr`/`l2_error` rows of
   `numerics/protocol/n0_fixed_dt_certification.json` using closed-form least squares
   (log–log slope, slope SE, residuals, adjacent-rung pair orders, `delta_R5 =
   max(pair half-range, SE)`), cross-checked against `numpy.polyfit`.
4. **Re-check the three replication verdicts** and confirm they are named in the rev-3
   closure artifact but absent from the registry.
5. **Re-check the companion record's A1..A6** binding claims against live taxonomy, carrier
   and protocol bytes (including the two protocol citation locations).
6. **Re-check lock compliance**: live lock state, filesystem solver scan, and a fresh
   read-only `numerics/gates.py --pretty` run (no `--emit-blocker` / `--write-report`) whose
   exit code, verdict and blocking reasons are compared with the declared block.
7. **Six planted-defect controls** (each must fire), a determinism control, and a
   binding-pin before/after guard.

Reproduce: `python3 artifacts/worker-020/n0_regaudit_verify/verify_regaudit_independent.py`
(exit 0, 115/115 checks; ≈ 40 s wall, dominated by the live gate run).

## Result — the audit reproduces, bitwise on the numerics

* **Pin census 13/13**: 10 match disk *and* registry, 3 are genuinely registry-absent but
  present at their declared disk hashes (`worker-046` SUPPORTED, `worker-057` REPRODUCED,
  `worker-081` adjudication object), 0 mismatched, 0 missing.
* **Order re-fit** from raw rows, own least squares:

| scheme | fit order (dt = 1e-4, 4 rungs) | LS slope SE | Δ_R5 | \|p−2\| |
|---|---|---|---|---|
| lffd | 1.999943173893314 | 2.7523e-05 | 8.4437e-05 | 5.7e-05 |
| cnfd | 1.9998635927240203 | 2.9590e-05 | 9.3177e-05 | 1.4e-04 |
| cnfem | 1.9999163079874884 | 8.4984e-05 | 2.4644e-04 | 8.4e-05 |

  Every declared fit, SE, residual, pair order and `delta_R5` reproduces at **absolute
  difference 0.0**; cross-scheme max pairwise `|dp| = 7.958116929374093e-05 ≤ 0.25`; all fits
  inside `|p−2| ≤ 0.3`; `dt` constant at `1e-4` on all four rungs of all three schemes.
* **Lock compliance**: `N1_BLOCKED`, `production_allowed=false`, exit 3, four blocking
  reasons matching the declared guard block (locked; G-FORM pending; G-AUDIT pending;
  protocol contested). Falsifier #4 predicate holds: no `production_allowed=true` while a
  required gate is not pass.

## Controls

| control | planted defect | expected | observed |
|---|---|---|---|
| M1 | declared pin sha flipped to zeros | mismatch detected | fired (`CONVERGENCE_PROTOCOL.md`) |
| M2 | lffd rung-2 `l2_error` +0.5 % | re-fit moves >1e-6 | fired (Δ = 7.20e-04) |
| M3 | protocol entry removed from registry copy | flag flips to unregistered | fired |
| M4 | lock state set to `released`, gates still pending | guard stays blocked | fired (`N1_BLOCKED`) |
| M5 | `numerics/spherical_solver/solver.py` planted | solver scan detects | fired |
| M6 | protocol bytes appended | pin census flags mismatch | fired |
| C7 | determinism: two pure-analysis passes | bitwise identical | identical (`66fad7e66127`) |
| C8 | binding pins before vs after | unmoved | unmoved (`[]`) |

## Findings

* **F1 (positive)** The audit's census and order claim reproduce end-to-end; its `CLEAN`
  verdict is accurate for its declared scope.
* **F2 (soft)** The companion authority record's `published_at` is `2026-09-12T01:02:00+08:00`
  while its file mtime is `2026-09-12T01:00:07` — the same future-dated-timestamp class the
  audit reports as `ANOM-1` for `numerics/blockers.md`, but the audit's anomaly list omits
  this instance. Advisory: bytes are frozen; no claim depends on the label.
* **F3 (inherited, open)** The three replication verdicts are still unregistered at my
  measurement time; the audit's blocker `lnum-blocker-80ea3e6b3923ea78ccac` remains the
  correct owner action. Re-measured, not re-filed (CF-12: one canonical path, one owner).
* **F4 (observation)** `numerics/gates.py` does not scan for `numerics/spherical_solver/`;
  that clause is checked by direct filesystem scan, as here. By design — the guard is a
  pre-flight API — not a defect.
* **F5 (caveat)** Same-fleet non-author check, not an external audit.

## Authority and non-claims

No gate verdict, no node completion, no `validation_status` promotion, no lock release, no
physics claim, no adjudication of the C8 protocol contest or of HF-042-N0-1 / HF-081-PS-1.
This is reviewer input at pinned hashes.

## Falsifier

Void if the target audit `22edbcc61df7` or the companion `effd20b0ea09` re-hashes differently,
or any declared pin re-hashes to a different value, or a recomputed fixed-dt order leaves
`|p−2| > 0.3` or cross-scheme `|dp| > 0.25`, or a declared fit/SE/`delta_R5` fails to reproduce
from the raw rows within `1e-9` relative, or the three replication verdicts are absent or have
moved, or `numerics/spherical_solver/` appears while `numerics_lock.state == "locked"`, or
`numerics/gates.py` returns `production_allowed=true` while G-FORM or G-AUDIT is not pass, or a
planted mutation control fails to fire.

## Pins measured at emit time

| input / target | sha256 |
|---|---|
| `numerics/protocol/n0_registration_drift_audit.json` (target) | `22edbcc61df7dc7cd574fb43e4ef6c09ae12f89f1ebe34869b00a5b27384c632` |
| `numerics/N0_CLASS_BINDING_AUTHORITY.json` (companion) | `effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `numerics/results/flat_wave_convergence_rev3.json` | `da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `numerics/gates.py` | `fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e` |

`runtime/state/artifact_hashes.json` and `research_map/research_map.json` are mutable
registries; they are snapshotted and recorded, not treated as binding pins.

## Files

* `verify_regaudit_independent.py` — the checker (read-only outside this directory; stdlib + numpy)
* `regaudit_verification.json` — full machine report: 115 checks, census rows, re-fit tables,
  controls, lock run, findings, falsifier
* `regaudit_verification.log` — stdout of the full run
* `snapshots/` — byte-identical frozen inputs at the measured hashes
* `manifest.json` — sha256 of every deliverable and pinned target
* `emit_events.py` — idempotent, schema-validating, hash-guarded outbox emitter
