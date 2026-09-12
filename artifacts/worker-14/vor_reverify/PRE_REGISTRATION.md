# W014-GNUM-VOR-REVERIFY-01 — pre-registration (written before the instrument ran)

Task: independent, read-only verification of the **re-issued** N0 gate-proposal verification
of record

- target: `numerics/protocol/n0_gate_proposal_leadverify.json` (re-issued 2026-09-12T00:52:21+08:00)
- against: `numerics/tests/n0_gate_proposal.json#b4192221ff7d`
- supersedes the audit in `artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#13600a5d4130`
  whose findings BA-1 (verification of record stale) and BA-5 (declared mutable registry
  snapshot unreproducible) were raised against the previous record `e0f9ef9f329d`.

Class binding: `AF-WCC-SCALAR-SPH` (node N0 / gate G-NUM). Read-only: no canonical path, no
gate verdict, no node status, no ledger/schema, no protocol file is written. Outputs live only
under `artifacts/worker-14/vor_reverify/` plus a worker checkpoint.

## Predictions (pre-registered, before `verify_vor.py` was run)

- **P1** The re-issued record binds the current proposal bytes: `proposal_verified.sha256` equals
  the measured sha256 of `numerics/tests/n0_gate_proposal.json`, and the named artifact event
  `lnum-artifact-1789144642810-0d42bd` exists in `research_map/events.jsonl` with the same
  path+sha256. ⇒ BA-1 **closed** by the re-issue.
- **P2** All 23 evidence-chain rows re-measure `match`; 0 stale, 0 missing. The proposal's own
  `evidence_hashes` (also 23 entries) agree with the chain on path→sha256.
- **P3** The record's own mutable-registry snapshot (`sha256_prefix_measured`
  `17369f2bb10d76cf…`) equals the measured full-file sha256 of
  `runtime/state/artifact_hashes.json`, i.e. reproducible at the measurement instant.
- **P4** The **proposal's** declared mutable snapshot (`d69b62dc93e5336e5109`, measured_at
  2026-09-12T01:06) still matches neither the full-file sha256 nor the registry-section digest
  of the registry on disk, and its declared instant is in the future. BA-5 therefore persists
  as a **non-load-bearing annotation defect** (the proposal itself classifies that field
  `snapshot-pin-of-mutable-registry` / "not as a pin"), not as a binding gap.
- **P5** The recorded gate-evaluator reproduction re-runs: `python3 -m numerics.gates --check`
  exits 3, verdict `N1_BLOCKED`, `production_allowed=false`, lock `locked`, and every dissenter
  the record lists is present in the fresh run (the fresh run may contain more dissenters).
- **P6** An independent least-squares refit of the four fixed-dt rungs reproduces each declared
  `fit_order` to < 1e-6 and the declared `least_squares_se` to < 1e-6, and all three schemes
  stay inside |p−2| ≤ 0.3 with pairwise |Δp| ≤ 0.25.
- **P7** Lock guard: `numerics_lock.state == "locked"`, `numerics/spherical_solver` absent,
  `production_allowed=false`; no N1 artifact exists.
- **P8** All planted controls behave as declared; a tamper control proves the classifier reads
  bytes rather than trusting the record.

## Falsifier (declared before measurement)

The verdict is falsified if: (a) any row this report calls `match` has a different measured
sha256; (b) the re-issued record is shown not to bind the current proposal bytes, or the named
artifact event is absent/mismatched; (c) any control behaves differently from its declared
expectation; (d) the refit disagreement exceeds the stated tolerance; or (e) any load-bearing
fact recorded `ok` is shown false. A moved proposal, record, registry or certification hash
voids the corresponding verdict for the new bytes.

## Not claimed

No gate verdict, no N0 completion, no protocol review (this worker may not review its own
artifacts and is not the C8 reviewer), no physics claim, and no claim beyond the hashes and
files named in the report.
