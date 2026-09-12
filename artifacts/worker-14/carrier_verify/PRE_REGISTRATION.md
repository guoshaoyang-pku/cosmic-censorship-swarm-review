# Pre-registration — W014-GNUM-CARRIER-VERIFY-01

Task: independent, read-only verification of `numerics/N0_CLASS_BINDING_AUTHORITY.json`
(published by `astra-lead-numerics`, claimed sha256 `effd20b0ea094a8dfd4f686e62c49b1667622337efd6a7c154f7fadae0b98419`),
the group-lead authority record that names a single N0 class-binding carrier and is the
declared discharge condition for `HF-042-N0-1` (worker-042) and `HF-081-PS-1` (worker-081).

Node/gate/class: `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH`. Read-only: no canonical file is written;
no solver is imported, built, or run; `numerics_lock` stays LOCKED and no N1 work is performed.

## Declared predictions (before the verification instrument is run)

- **P1** The record measures to `effd20b0ea09…` on disk and its internal `carrier.sha256`
  equals the measured sha256 of `numerics/results/flat_wave_convergence_rev3.json`.
- **P2** Every `(path, sha256)` pin in the record — carrier, binding, protocol, and each
  `basis_evidence` 12-hex prefix — resolves to the bytes on disk (0 mismatches, 0 missing).
- **P3** The carrier `flat_wave_convergence_rev3.json` declares F0 rev5
  `research_map/formulation_taxonomy.yaml#0abb9ed8a961…` in both `class_binding.sha256` and
  `stop_rule_closures.f0_rebind`.
- **P4** The live taxonomy at `0abb9ed8a961…` declares `revision: 5` and contains the class id
  `AF-WCC-SCALAR-SPH`; it does not contain either superseded pin as its own hash.
- **P5** `numerics/CONVERGENCE_PROTOCOL.md` is byte-unchanged at `1e6cdf04d7a2…` and still cites
  the superseded pins `66bf917bd368` (line 7) and `565a6e50` (line 159); the record's declared
  locations (line 7; lines 157–160) cover both citations.
- **P6** The record names exactly one `class_binding_carrier`; no other document in the reviewed
  evidence set asserts itself as the N0 class-binding carrier.
- **P7** Materiality is testable and holds: `numerics/protocol/n0_fixed_dt_certification.json`
  contains no taxonomy string (0 hits for `taxonomy`, `66bf917b`, `565a6e50`, `0abb9ed8`), and an
  independent log–log least-squares refit from the raw rungs reproduces every declared
  `fit_order` to within 1e-6.
- **P8** Re-running the lead's read-only `numerics/protocol/audit_registration_drift.py`
  (`5031ffb3024f…`) with `--out` redirected to scratch reproduces the filed
  `n0_registration_drift_audit.json` (`22edbcc61df7…`) classification counts
  (13 declared pins; 10 registry matches; 3 unregistered) and verdict `CLEAN`.
- **P9** Lock guard holds: `research_map.json#numerics_lock.state == "locked"`,
  `numerics/spherical_solver/` is absent, no N1 artifact is cited, and `numerics/gates.py`
  still evaluates `N1_BLOCKED` / `production_allowed == false`.
- **P10** (advisory, non-load-bearing) The record's `published_at` (`01:02:00`) is ahead of its
  own file mtime (`01:00:07`) and of the lead's artifact event (`01:00:54`), the known
  clock-discipline pattern (CF-6/CF-14); it changes no hash and no claim.
- **P11** No `(reviewer, target, hash)` supersession and no C8 contest disposition is claimed or
  performed by this task; the record's `non_claims` are accurate on that point.

## Falsifier (declared now)

This verification is **falsified** if any of the following is observed:

1. any pinned or cited sha256 in the record differs from the bytes on disk, or a cited path is
   missing;
2. the record names zero or more than one class-binding carrier, or the carrier does not declare
   the F0 rev5 binding `0abb9ed8a961`;
3. the live taxonomy at that pin is not `revision: 5` or does not contain `AF-WCC-SCALAR-SPH`;
4. the protocol hash has moved from `1e6cdf04d7a2…`, or the superseded pins are absent from the
   declared locations, or the record edits/voids any artifact or verdict bound to that hash;
5. the independent refit disagrees with a declared `fit_order` by more than 1e-6, or the
   certification basis is shown to depend on taxonomy content;
6. the control set does not behave as declared (a planted corruption is not caught, or a
   canonical input hash drifts during the run);
7. any lock-guard check fails (`numerics/spherical_solver/` present, lock not `locked`, or the
   guard reporting `production_allowed == true`).

A falsified prediction is reported as such with the measured counter-value; it is not
re-labelled. Passing this verification is **worker-level evidence only**: it is not a gate
verdict, not controller ratification of the carrier record, not an N0 node completion, and not
an adjudication of the C8 protocol-review contest.
