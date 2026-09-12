# W097-N0-REGISTRATION-01 — findings (worker-097, bounded measurement)

Node N0 / gate G-NUM / class `AF-WCC-SCALAR-SPH`. Read-only census; no canonical path, map, gate,
node status or ledger was written. Artifacts:
`report.json`, `controls.json`, `measure.py`, `PRE_REGISTRATION.md`, `snapshot/artifact_hashes.<pin>.json`.

## Headline

At registry pin `5c29fba23f3a` (independently re-hashed from
`runtime/state/artifact_hashes.json`, snapshot saved and pinned in `report.json`):

- **B-N0-R2-1 residual is exactly 3 paths, not 6.** The pass-05 scan-root repair registered
  `numerics/CONVERGENCE_PROTOCOL.md` (`1e6cdf04d7a2`), `numerics/results/flat_wave_convergence.json`
  (`e9e124227c4d`) and `numerics/gates.py` (`fcd1d70991b6`). The three N0 *independent-replication*
  artifacts still resolve on disk but are absent from both `hashes` and `registry`:
  | path | measured sha256 | bytes |
  |---|---|---|
  | `artifacts/worker-046/n0_fixed_dt_independent/verification.json` | `814452111bc8912b…` | 7409 |
  | `artifacts/worker-057/n0_fixeddt_verify/report.json` | `b906445878f3130d…` | 25786 |
  | `artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json` | `65ae766d9e4c2057…` | 15507 |
  These are the three files `reviews/N0-review-final-verify.json:55` cites as the closed
  "one independent replication verdict" stop-rule item. PROTOCOL rule 2 cannot be satisfied for
  them under the current registry rule.
- **Cause, measured:** the final registry holds **0 keys** with prefix `artifacts/worker-` while
  **11 823 files** exist under `artifacts/worker-*` (control C6). `audit_evidence.py` registers
  only the fixed scan roots `schemas, ledger, numerics, reviews, evaluation, artifacts/numerics,
  runtime/state/controller_verification`; worker evidence dirs are structurally out of scope.
- **Global context (informational):** of 393 resolvable review-cited refs (152 review files,
  manifest-pinned), 379 are files: 79 registered, 294 unregistered, 8 excluded as mutable
  `runtime/state/` registries, 12 dangling refs, 9 files carry a 64-hex pin that no longer matches
  current bytes. Out-of-root citations are *not* automatically rule-2 violations; B-N0-R2-1 is the
  actionable subset. The 9 non-matching pins are advisory only and were not adjudicated here.

## Proposed repair (not applied; `audit_evidence.py` is controller-owned)

- **Option A (bounded):** add `artifacts/worker-046`, `artifacts/worker-057`, `artifacts/worker-081`
  to the scan roots — measured effect: 630 files registered, closing the 3 focus paths.
- **Option B (general rule):** after the current roots, register every on-disk file cited by a
  review `evidence_refs`/`artifact_refs` and not under `runtime/state/` — measured effect: 294 new
  entries (217 under `artifacts/worker-*`). Minimal sketch in `report.json.proposed_repair`.

## Pre-registered predictions vs measured

| id | prediction | outcome |
|---|---|---|
| P1 | 3/6 focus paths registered, 3/6 absent | CONFIRMED |
| P2 | absent paths non-empty; 0 worker registry keys; >1000 worker files | CONFIRMED |
| P3 | ≥50 unregistered files and ≥80 % under `artifacts/worker-*` | **DISCONFIRMED** — 294 unregistered, worker share 73.8 % |
| P4 | 0 stale/mismatched 64-hex citations | **DISCONFIRMED** — 9 stale pins, incl. canonical schemas rewritten by the in-flight rev13 repair |
| P5 | all declared controls PASS | CONFIRMED (C1–C6) |

## Controls (all PASS at the pin)

C1 focus-hash stability (registry pin identical across run); C2 positive registered control
`numerics/CONVERGENCE_PROTOCOL.md` hash-agrees; C3 negative control (3 focus paths exist and are
unregistered); C4 classifier self-test + invariant; C5 parser floor (152 review files, 393 refs);
C6 scan-root attribution. Registry drift during the run: none; a later pin is a new measurement.

## Falsifier / not claimed

**Falsifier:** a cited path that resolves and is covered by an existing scan root while this report
calls it unregistered; a cited 64-hex equal to measured bytes called stale; a dangling ref called
resolved; or a re-run against the pinned snapshot that disagrees. **Not claimed:** no gate verdict,
no node completion, no claim that registration fixes N0, no numerics content claim, no adjudication
of the in-flight F1/F2a/F2b rev13 repair. Worker measurement only.
