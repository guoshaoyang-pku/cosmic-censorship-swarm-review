# W014-GNUM-GUARD-VERIFY-01 — pre-registration (independent non-author verification)

- worker: worker-014 (slot 014, instance 2026-09-12T010618-968807)
- class_id: AF-WCC-SCALAR-SPH | node: N0 | gate: G-NUM
- object under review: `W064-GNUM-GUARD-CENSUS-01` (worker-064), report
  `artifacts/worker-064/gnum_guard/report.json#e3ebf9e502491f65`, census
  `census.jsonl#ff3ad3eb6d481e9a`, candidate rules `candidate_rules.json#e6ad4f16eecc0379`,
  frozen snapshot `raw/events_snapshot.jsonl#b476b9e5e54fbcbd` (11,604 events), harness
  `w064_gnum_guard_census.py#1db0e4f09b697d25`, prereg `prereg.json#57a64cb6451ea7a1`.
- pins: `numerics/gates.py#fcd1d70991b6eade`,
  `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313`.
- why: worker-064's census/rule is fresh (01:06–01:09), unverified, and is the evidence the
  owner disposition on blocker `lnum-blocker-e9e939acc0856fa77127` / audit card `astra-life06-b4`
  will rest on. Independent non-author verification is the missing step. Not a re-run of the
  author's harness: this instrument re-implements the guard semantics and the R1–R3 rule from the
  published spec and adds controls the author did not run.
- scope: read-only on all canonical paths and on all of worker-064's artifacts. Writes only under
  `artifacts/worker-14/guard_verify/` and `runtime/state/w014_*`. No gate verdict, no node
  completion, no canonical write, no adoption of the candidate rule.

## Predictions (declared before this instrument was implemented or run)

- **V1 pins** all seven declared gnum_guard artifact hashes match disk; the pinned gates/protocol
  copies equal the live canonical bytes at the two pins.
- **V2 census** the frozen-snapshot census is exactly 5 accepts / 5 dissents / 3 advisory with
  `contest=true`, `reviewed=true`; my independent re-implementation equals both the live guard
  `numerics.gates._protocol_review` and worker-064's `guard_verdict` on the same snapshot.
- **V3 findings** F-GUARD-1 (r4 accept advisory), F-GUARD-2 (N0 target conflation: 4 of 10 counted
  verdicts), F-GUARD-3 (prose-only withdrawal; no structured withdrawal field anywhere in the
  snapshot), F-GUARD-4 (worker-081 counted on both sides at one hash) and F-GUARD-5 (contest is a
  blocking reason but contest=false alone does not unblock N1) all reproduce.
- **V4 arms** all six published arms reproduce exactly under my implementation: arm0 5/5,
  hash-repair-only 6 accepts / contest true, scope 4/2, scope+withdrawal 4/2 (R2 inert on prose),
  scope+withdrawal+synthetic-field 3/2, scope+withdrawal+discharge 5 accepts / 0 dissents /
  contest false.
- **V5 author controls** the six negative controls C1–C6 reproduce under my implementation.
- **V6 adversarial extension** (new controls, not in the author's set): X1 a later same-reviewer
  binding review that discharges the reviewer's own dissent **does** discharge under the rule as
  specified (specification gap: discharge is not author-scoped the way withdrawal is); X2 a
  binding carrier with an empty evidence list but a populated discharge field **does** discharge
  (specification gap: the list is trusted, not evidence-bound); X3 a list naming an accept is
  ignored; X4 a list carried by a non-review event does not discharge; X5 a dissent arriving after
  the carrier still contests; X6 duplicate ids/carriers are idempotent. X3–X6 fail closed.
- **V7 minimal repair** re-emitting only `audit-l06-review-gnum-r4-20260912T005926` with
  `reviewed_sha256=1e6cdf04d7a2` makes it bind (6 accepts) and leaves `contest=true`; the
  event-layer repair is necessary but not sufficient.
- **V8 determinism/lock** two runs of this instrument agree on the substantive payload; calling
  `numerics.gates.evaluate()` stays read-only, returns `N1_BLOCKED`, and `numerics/spherical_solver`
  stays absent.

## Falsifier

Re-run `python3 verify_guard_census.py --out report.json` at the pinned inputs. Any claim
verdict that flips, any arm/control row that differs, a declared hash that does not match disk, a
shadow/guard disagreement, a non-deterministic payload, a canonical write, or a lock-state change
falsifies the corresponding verdict. A later write to the reviewed worker-064 revision or to either
canonical pin voids this verification for the new bytes.
