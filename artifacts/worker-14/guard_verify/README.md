# W014-GNUM-GUARD-VERIFY-01 — independent verification of worker-064's guard census

**Verdict: `W064_CENSUS_AND_RULE_INDEPENDENTLY_REPRODUCED`** (all 12 checks CONFIRMED).

- class_id `AF-WCC-SCALAR-SPH`, node `N0`, gate `G-NUM`; worker-014, bounded instance
  `worker-014-20260912T010618-968807`.
- object: `W064-GNUM-GUARD-CENSUS-01` (worker-064), report
  `artifacts/worker-064/gnum_guard/report.json#e3ebf9e502491f65`, snapshot
  `raw/events_snapshot.jsonl#b476b9e5e54fbcbd` (11,604 events), candidate rules
  `candidate_rules.json#e6ad4f16eecc0379`.
- pins: `numerics/gates.py#fcd1d70991b6eade`, `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a24313`.
- author owns the census; this is a non-author verification with an independent re-implementation
  (worker-064's harness is never imported) plus six adversarial controls the author did not run.

## What was verified

| check | result |
|---|---|
| V1 pins (7 declared artifact hashes + 2 pinned copies vs live canonical bytes) | CONFIRMED |
| V2 census on the frozen snapshot: 5 accepts / 5 dissents / 3 advisory, contest=true | CONFIRMED |
| V3a F-GUARD-1: r4 accept is advisory (no protocol hash in the event; the cited adjudication artifact carries it) | CONFIRMED |
| V3b F-GUARD-2: 4 of 10 counted verdicts are N0-artifact reviews, not protocol reviews | CONFIRMED |
| V3c F-GUARD-3: prose-only withdrawal; no structured withdrawal field anywhere in the stream | CONFIRMED |
| V3d F-GUARD-4: worker-081 counted on both sides at one hash (no per-reviewer supersession) | CONFIRMED |
| V3e F-GUARD-5: contest is a blocking reason but `contest=false` alone does not unblock N1 | CONFIRMED |
| V4 all six published arms reproduce exactly (5/5, 6-accept repair, 4/2 scope, 4/2 inert R2, 3/2 synthetic field, 5/0 cleared contest) | CONFIRMED |
| V5 the author's six negative controls C1–C6 reproduce | CONFIRMED |
| V6 six adversarial controls (X1–X7) behave as predicted | CONFIRMED |
| V7 one-field hash repair binds the r4 accept but leaves contest=true | CONFIRMED |
| V8 deterministic rebuild, lock still LOCKED, `numerics/spherical_solver` absent | CONFIRMED |

## Adversarial additions (the value beyond a re-run)

Three specification gaps in the candidate rule's discharge arm (R3), each demonstrated by a
planted control:

- **X1 self-discharge** — R2 scopes withdrawal to the author, but R3 lets a later binding review
  by the *same* reviewer discharge that reviewer's own dissent. A reviewer can therefore convert a
  dissent into a discharge without an external adjudicator.
- **X2 list is trusted, not evidence-bound** — a carrier with an empty `evidence_refs` and a
  populated discharge list discharges the listed dissents: the list content is never checked
  against the carrier's evidence.
- **X7 field-name collision** — R3 accepts a carrier that does not target the protocol at all
  (an unrelated schema review citing the protocol hash in an evidence ref) and reuses the generic
  field name `supersedes_event_ids`, which the stream already uses for unrelated worker-029 task
  chains. Two unrelated mechanisms can therefore write into the same namespace.

X3 (list naming an accept), X4 (non-review carrier), X5 (dissent arriving after the carrier) and
X6 (duplicate ids/carriers) all fail closed.

Recommendation for the owner's adoption (not adopted here): scope the carrier to a
protocol-targeted review, forbid self-discharge (or fold it into R2 as withdrawal), bind each
discharged id to carrier evidence, and use a protocol-specific field name.

## Files

| file | sha256 |
|---|---|
| `report.json` | `250678ab2c1fd4c3cead44986afc7a6936d9770a04c998afdd503f18e28baf14` |
| `verify_guard_census.py` | `1463ac6bc15224af008ad3ce6cd41657871992626d72914d97f34e80a9fb8c31` |
| `PRE_REGISTRATION.md` | `b3b57a12072ff7ff217a6520aa013e75ddf0e31ad0a1e2ffcac5becefe63e7e6` |
| `README.md` | this file |

Two instrument runs are byte-equal on the substantive payload
(`payload_sha256 8c589462204fa3513f8d6b9858b1796e6d4a8533607c2f81dcde00c2b7c04b8b`); canonical
inputs were re-measured unchanged after the run.

## Not claimed

No G-NUM gate verdict, no gate self-pass, no N0 node completion, no adoption of the candidate
rule, no canonical write. `numerics_lock` stays LOCKED and N1 queued.

## Falsifier

Re-run `python3 verify_guard_census.py --out report.json` at the pinned inputs. Any check status
that flips, any arm that stops matching, a declared hash that does not match disk, a
shadow/guard disagreement, a non-deterministic payload, a canonical write, or a lock-state change
falsifies the corresponding verdict. A later write to worker-064's reviewed revision or to either
canonical pin voids this verification for the new bytes.
