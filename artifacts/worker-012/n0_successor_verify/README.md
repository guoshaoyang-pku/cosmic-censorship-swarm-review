# W012-GNUM-SUCCESSOR-VERIFY-01 — independent verification of the C8 supersession successor

- Worker: `worker-012`; class `AF-WCC-SCALAR-SPH`; node `N0`; gate `G-NUM`.
- Taken as one bounded class-bound task from the live G-NUM queue (no inbox card for this slot;
  the card the slot did hold, `audit-r2-N0-rev3`, is worker-side complete and hash-stable).
- Verdict: **`SUCCESSOR_VERIFIED_WITH_ANNOTATIONS`** — 12/13 checks pass, the single failure is
  annotation-level (declared JSON container type), 10/10 fail-closed controls behave.
- Read-only on canonical state. Only this directory was written.
- Instrument: `verify_successor.py` (stdlib only, deterministic). Pre-registration: `PRE_REGISTRATION.md`.

## Target

| role | path | sha256 (measured before and after) |
|---|---|---|
| successor (reviewed) | `numerics/protocol/fixed_replication_verdict_rev2.json` | `7954d2d355451e3dbd3e7b7c23769ba204451cc8adf5eb04515910069a10fa60` |
| superseded predecessor | `numerics/protocol/fixed_replication_verdict.json` | `dcad962324e3be156d1ef1577b7ee2613fac803058351b643d2c8f67bc787a36` |
| live F0 rev5 taxonomy | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| frozen replication run | `runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json` | `6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e` |
| harness / module / source verifier | `artifacts/flash-04/n0_acceptance/harness.py`, `numerics/tests/flat_wave_replication.py`, `numerics/protocol/verify_fixed_scheme_independence.py` | `0646de3f75bd…`, `8ade1cdc163e…`, `a0daf1271bfb…` |

All ten pinned inputs matched their declared hashes before and after the run (V0, V11) — the
measurement is at one hash set, no moving target.

## What was measured

**The contradicted predecessor assertion reproduces (V2).** `fixed_replication_verdict.json`
declares `provenance.fixed_taxonomy_sha256_matches_on_disk = true` while chaining the superseded
F0 pin `66bf917b…`, which is not the live taxonomy (`0abb9ed8a961…`). The recorded defect is real.

**The successor repairs the binding without touching the arithmetic (V3–V6).**

- V1: `supersedes.sha256` equals the measured predecessor hash (`dcad962324e3be15…`).
- V3: successor chained taxonomy hash = live rev5 `0abb9ed8a961…`; `taxonomy_rebind.frozen_run_f0_pin`
  equals the frozen run's own `provenance.f0_taxonomy_sha256` (`66bf917b…`);
  `frozen_run_f0_pin_matches_current_disk = false`; the successor's own
  `fixed_taxonomy_sha256_matches_on_disk = false` mirrors that recomputation; `load_bearing_for_order_claim = false`.
- V4: all four `chained_evidence_hashes` entries match live disk (4/4).
- V5: an **independent** leaf-by-leaf recomputation (rule fixed in the pre-registration) reproduces
  `79` compared numeric leaves, `max_abs_difference = 0.0`, no non-wall-clock differing leaf, with
  `runtime_seconds` (0.91 → 0.90) the only excluded wall-clock numeric leaf. The declared claim is exact.
- V6: every leaf under `q1_invariant_functional_scheme_appropriate`,
  `q2_order_fit_carries_uncertainty`, `falsifier_tests` and `r4_note` is identical between
  predecessor and successor; `class_id`/`node_id`/`gate` unchanged.
- V7: `source_verifier.sha256` equals the live verifier (`a0daf1271bfb…`), method declared.
- V8: `numerics/tests/n0_gate_proposal.json` still pins the predecessor in `evidence_hashes` — the
  documented reason the repair is a successor artifact rather than an in-place edit
  (the predecessor is load-bearing in the proposal's 23-entry chain).
- V9: the successor **is** registered in `runtime/state/artifact_hashes.json#registry` at the same
  sha256 (live state; the lead's "unregistered" blocker is closed at this snapshot).
- V10: lock guard holds — `numerics/spherical_solver` absent, no N1/spherical-solver artifact in the
  reviewed set or the `numerics/` scan, and a live `numerics.gates.evaluate()` returns
  `N1_BLOCKED` / `production_allowed=false` (protocol still contested by the live dissents).

## Controls (10/10)

K1 flipped numeric leaf detected; K2 wall-clock exclusion is load-bearing (removing it surfaces
`runtime_seconds`); K3 corrupt `supersedes.sha256` detected; K4 taxonomy-rebind regression detected;
K5 missing chain entry detected; K6 one-byte hash sensitivity; K7 proposal-pin substitution
detected; K8 registry mismatch detected; K9 N1 sentinel discriminates absent/present; K10 no
vacuous pass (each predicate re-run on its mutant returns false).

## Annotations (non-load-bearing)

- **A1** the successor writes the excluded leaf as `"/runtime_seconds"`; the natural flattened path
  is `runtime_seconds` — notation only, identical exclusion set.
- **A2** `provenance.fixed_taxonomy_sha256_matches_on_disk = false` is the *corrected recomputation*
  for the frozen-run pin, not a regression: `taxonomy_rebind` documents it and marks it
  non-load-bearing for the order claim.
- **A3** the successor remains `binding_status = PROVISIONAL`, `validation_status = unverified`, and
  is not yet the proposal's pinned replication evidence.
- **A4 (type defect, the one failed check)** `numeric_delta_vs_superseded.differing_leaves` is
  declared as an empty JSON object `{}` where an empty array `[]` is the list-typed form used by the
  claim's own semantics. The substantive claim (zero differing leaves) verifies; list-typed
  consumers would need to tolerate an object. A follow-up successor/erratum fixes it without
  changing any number.

## Open items

- **OI-1 (controller)** successor registered but not bound: if the adjudication accepts it as the
  replication evidence of record, bind it in `numerics/tests/n0_gate_proposal.json` / the G-NUM map
  evidence list.
- **OI-2 (lead-audit)** whether supersession discharges `w067-provledger` is an adjudication, not a
  worker call. This report supplies the measurement: numeric identity is exact at 79 leaves, the
  contradicted assertion is corrected, and every pin matches disk.
- **OI-3 (successor record)** the A4 type defect.

## Falsifier

Void if any pinned input re-hashes (rev2 `7954d2d355451e3d`, predecessor `dcad962324e3be15`,
taxonomy `0abb9ed8a961`, frozen run `6542db93eebc`, harness `0646de3f75bd`, module `8ade1cdc163e`,
source verifier `a0daf1271bfb`, proposal `b4192221ff7d`, gates `fcd1d70991b6`, protocol
`1e6cdf04d7a2`). Falsified if the leaf-rule recomputation does not yield 79 compared numeric leaves
/ max |diff| 0.0 / no non-wall-clock differing leaf, if any chained evidence hash does not match
disk, if the successor does not bind live F0 rev5 while marking the frozen pin non-matching, or if
the lock guard reports `production_allowed=true` or an N1/spherical-solver artifact exists.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-012/n0_successor_verify/verify_successor.py   # exit 0 = verified, 2 = failed, 3 = void
```

Two consecutive runs agree on verdict, all check results, all control results, the numeric-delta
block and the lock-guard snapshot (`report.json` differs only in `created_at` / `runtime_seconds`).

## Non-claims

Worker evidence only; no gate verdict, no node status, no `validation_status` on any canonical
artifact, no edit of any canonical file. This does not adjudicate the C8 contest, accept or reject
`numerics/CONVERGENCE_PROTOCOL.md`, release `numerics_lock`, or authorise N1.
