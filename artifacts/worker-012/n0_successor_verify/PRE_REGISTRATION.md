# W012-GNUM-SUCCESSOR-VERIFY-01 — pre-registration

Written before any measurement, at task claim time (2026-09-12T00:58+0800).
Class binding: `AF-WCC-SCALAR-SPH` / node `N0` / gate `G-NUM`. Read-only; no canonical artifact is written.

## Question

`astra-lead-numerics` filed that the C8 provenance dissent (`w067-provledger`) is
"dischargeable by supersession": the contradicted record
`numerics/protocol/fixed_replication_verdict.json` (`dcad962324e3be15…`) asserted
`provenance.fixed_taxonomy_sha256_matches_on_disk = true` while chaining the superseded
F0 pin `66bf917b…`; the successor
`numerics/protocol/fixed_replication_verdict_rev2.json` (`7954d2d355451e3d…`) is claimed to
re-run the identical R1/R2/R4/R5 arithmetic (`delta 0.0`, 79 numeric leaves) with the
taxonomy assertion corrected and the live F0 rev5 pin `0abb9ed8a961…` bound.

No worker verification of that successor exists at claim time. This task is an independent,
read-only, deterministic measurement of exactly those claims.

## Declared predictions (falsifiable)

- P1 `fixed_replication_verdict_rev2.json` hashes to `7954d2d355451e3dbd3e7b7c23769ba204451cc8adf5eb04515910069a10fa60`.
- P2 `supersedes.sha256` equals the measured sha256 of `fixed_replication_verdict.json` (`dcad962324e3be15…`).
- P3 the predecessor's contradicted assertion reproduces: it claims `fixed_taxonomy_sha256_matches_on_disk = true` while its chained taxonomy hash is `66bf917b…`, which is not the live `research_map/formulation_taxonomy.yaml`.
- P4 the successor's chained taxonomy hash equals the live taxonomy hash `0abb9ed8a961…`; its `frozen_run_f0_pin` equals the frozen run's declared `provenance.f0_taxonomy_sha256` (`66bf917b…`); `frozen_run_f0_pin_matches_current_disk` is `false`; the successor's own `provenance.fixed_taxonomy_sha256_matches_on_disk` is `false`.
- P5 all four `chained_evidence_hashes` entries match live disk.
- P6 an independent leaf comparison (rule below) reproduces `79` compared numeric leaves, `max_abs_difference = 0.0`, `differing_leaves = []`, with `runtime_seconds` the single excluded wall-clock numeric leaf.
- P7 every leaf under `q1_invariant_functional_scheme_appropriate`, `q2_order_fit_carries_uncertainty`, `falsifier_tests` and `r4_note` is identical between predecessor and successor.
- P8 `source_verifier.sha256` equals the live `numerics/protocol/verify_fixed_scheme_independence.py` hash `a0daf127…`.
- P9 `numerics/tests/n0_gate_proposal.json` still pins the predecessor (`dcad962324e3`) in `evidence_hashes` — the documented reason the repair is a successor artifact rather than an in-place edit.
- P10 `fixed_replication_verdict_rev2.json` is registered in `runtime/state/artifact_hashes.json#registry` with the same sha256 (live state at measurement).
- P11 the lock guard still holds: `numerics/spherical_solver` absent; no N1 artifact in the reviewed set; `numerics.gates.evaluate()` returns `N1_BLOCKED` / `production_allowed=false`.

## Independent numeric-leaf comparison rule (fixed before measurement)

1. Flatten each document to leaf paths (`a.b[0].c`).
2. A "numeric leaf" is an `int`/`float` that is not a `bool`.
3. Compare only paths present in both flattened documents.
4. Wall-clock exclusion is exactly the leaf path set `{"runtime_seconds"}`; the union of differing numeric paths before exclusion must itself be a subset of that set, otherwise the exclusion is not load-bearing and the claim fails.
5. Report `numeric_leaves_compared` (after exclusion), `max_abs_difference`, `differing_leaves`.

## Controls (fail-closed, in-memory unless stated)

K1 one numeric leaf flipped in a successor copy → delta must become non-zero;
K2 exclusion disabled → `runtime_seconds` must appear as a difference (exclusion is load-bearing);
K3 `supersedes.sha256` corrupted → P2 check must fail;
K4 chained taxonomy hash set back to the frozen pin → P4 check must fail;
K5 one chained entry removed → P5 check must fail;
K6 one-byte edit of a temp copy of the predecessor → sha256 changes (hash sensitivity);
K7 substitution of the successor hash into a proposal copy is detected by the P9 comparison;
K8 a synthetic registry entry with a wrong sha is detected by the P10 comparison;
K9 the N1 sentinel detector returns absent for a synthetic path and present for a known N0 file;
K10 re-running the P2–P5 predicates on the mutated copies returns false for each (no vacuous pass).

## Falsifiers

- Any pinned input re-hashes differently during the run (moving target): verdict VOID, no claim.
- P6 fails to reproduce 79/0.0/[] under the rule above: the "identical arithmetic" supersession claim is NOT verified.
- The successor does not bind live F0 rev5, or the contradicted predecessor assertion does not reproduce: the provenance repair is not verified.
- `gates.evaluate()` returns `production_allowed=true` or an N1/spherical-solver artifact exists: lock-guard violation reported as a blocker.

## Non-claims

Worker evidence only. This does not adjudicate the C8 contest, does not accept or reject the
protocol, does not set any gate verdict or node status, does not modify any canonical artifact,
and does not release `numerics_lock` or authorise N1.
