# W047-F2A-EXT-FREEZE-SPEC-02 — F2a extension-predicate freeze repair specification

**Class** `AF-SCC-C2-VAC-GEN` · **Node** F2a · **Gate** G-FORM · **Actor** worker-047
**Pins** F2a `e9a27996dfd3…` (= FROZEN rev29) · F2b `b2ab6acb2bbe…` · F0 `0abb9ed8a961…`
**Verdict of this deliverable** `spec_ready_awaiting_owner_apply` — a repair specification and a
read-only instrument. It is **not** a review verdict, **not** a gate verdict, and it does **not**
edit `schemas/af_scc_c2_vacuum.yaml`.

## Why this artifact exists

`reviews/F2a-review-rev13-047.json` (HF-047-01) and the independent `reviews/F2a-review-rev29-b.json`
(HF-091-02, *persists at rev29, not repaired by rev13*) both report that the F2a
`extension_predicate` is under-frozen on three axes while its accepted F2b sibling is exact:

| axis | F2a at `e9a27996` | F2b at `b2ab6acb` (accepted precedent) |
|---|---|---|
| manifold category of `M'` | clause (c) says only “connected and time-orientable”; `topology.extension_topology` says “connected 4-manifold” | clause (c) “SMOOTH (C-infinity) connected 4-manifold” + `extension_topology` propagation (worker-16 F2b-16-03 accepted) |
| differentiability of `iota` | clause (a) “isometric embedding”, class unspecified | `falsifier.tier_1.witness_type` “C-infinity isometric embedding iota” |
| clause (f) future-point requirement | `p in M' minus iota(M)` | `int(M' minus iota(M))` non-empty **and** `p in int(M' minus iota(M))` (R2 major: clause (f) was escapable) |

Consequence: two careful readers can disagree about which extensions the C2 class actually forbids,
and a machine-checked witness is under-specified in exactly the same three axes. The F2b repair
template already exists at the same gate; this spec ports it to F2a rather than inventing a new rule.

## Deliverables

| file | purpose |
|---|---|
| `repair_spec.json` | five sites S1–S5 with exact `old_text` / proposed `new_text`, option A (recommended, sibling-aligned smooth category) and option B fallback per site, precedent with hashes, post-repair invariants, owner actions, falsifier |
| `check_f2a_ext_freeze_047.py` | read-only instrument: six axis detectors, sandbox apply, structural-diff bound, invariants, six single-axis mutants, degenerate controls, pin stability |
| `report.json` | full run output (baseline 0/6 resolved, repaired 6/6, 6/6 mutants discriminating, 0 problems) |
| `sandbox/af_scc_c2_vacuum.repair.patch` | unified diff of the proposed repair, applied only to a sandbox copy |
| `sandbox/root/schemas/af_scc_c2_vacuum.yaml` | patched sandbox bytes (never the canonical file) |
| `MANIFEST.json`, `checkpoint.json` | hash-pinned deliverable manifest and worker checkpoint |

## Repair summary (option A)

- **S1** clause (a): `iota` is a **C-infinity** isometric embedding; the class is frozen, not conventional.
- **S2** clause (c): `M'` is a **SMOOTH (C-infinity)** connected 4-manifold — the category in which the
  metric is a tensor field, while the metric itself is only C2.
- **S3** clause (f): `int(M' minus iota(M))` is non-empty **and** `p in int(M' minus iota(M))`;
  `I^+` named as the chronological future. The C0 sibling’s degenerate-causality caveat is explicitly
  *not* imported, because a C2 metric has an open, curve-class-independent chronological future.
- **S4** `topology.extension_topology`: names the same SMOOTH category (the block a machine consumer
  reads for `M'`).
- **S5** `falsifier.tier_1.witness_type`: a witness must now exhibit a SMOOTH `M'`, a C2 nondegenerate
  metric `g'`, a C-infinity isometric embedding `iota`, and an interior future point as in clause (f).

Option B (C2 manifold category and C2 `iota`) is recorded per site. It is internally sufficient for a
C2 metric but would leave F2a and F2b in different categories, so it is not the recommendation.

## What the instrument asserts (all pass at the pins)

- **P1** F2a/F2b/F0 start pins equal the declared pins; **P2** the live FROZEN manifest still pins F2a
  at the measured bytes; **P3** canonical targets byte-stable across the run (read-only guarantee).
- **C0** baseline: all six axes unresolved.
- **C1** sandbox repair (option A): all six axes resolved (A6 = F2a/F2b category uniformity).
- **C2** structural diff touches exactly three YAML leaves (`extension_predicate.definition`,
  `topology.extension_topology`, `falsifier.tier_1.witness_type`) — no other field moves.
- **C3** invariants: `frozen_regularity` stays C2, the equation stays `classical_ricci`, clause (d)
  stays C2 Lorentzian, `conclusion_type` stays `scc_c2_future_inextendibility`, `genericity.kind`
  stays `residual_comeager`, the containment chain is unchanged, no WCC/I+ predicate enters the
  conclusion, and the `C0 or C2` composite token remains confined to `anti_scope`.
- **C4** six planted single-axis mutants; each axis has a mutant that flips it (A1’s mutant
  necessarily co-fails A6, since A6 is the sibling-consistency of the A1 token — recorded).
- **C5** degenerate always-resolve / always-unresolve detectors differ from the live results.

## Owner actions (astra-lead-formulation)

1. Apply option A (or record a different ruling) to `schemas/af_scc_c2_vacuum.yaml`; bump the revision.
2. Re-emit the artifact event with the new sha256 and refresh the FROZEN manifest revision.
3. Re-run `artifacts/formulation/tools/check_class_schema.py` and the gate tests at the new bytes.
4. Commission a fresh independent verdict at the new hash — the r3 F2a cards pinned to `e9a27996`
   are void for the new revision.

Optional hardening not included in the five sites: add a `topology.forbidden` entry forbidding a merely
topological `M'`. Clause (c) + `extension_topology` already exclude it; the extra entry would mirror
the F2b `topology.forbidden` propagation and is left to the owner as a churn/benefit call.

## Falsifier

At the pins recorded in `report.json`: this spec is falsified if (a) any hard pin differs on re-measure
or the live FROZEN manifest no longer pins F2a at the measured bytes; (b) a repaired F2a still leaves
any of S1–S5 unresolved under the instrument; (c) the sandbox patch changes a YAML path other than the
three listed leaves; (d) any invariant fails on the patched copy; or (e) any planted single-axis mutant
stops discriminating. A repair applied at a different hash does not falsify the spec; it voids the pins
and requires a re-run.

## Authority and non-claims

Worker events cannot set `status=done`, `validation_status=passed`, or a gate verdict; none is claimed
here. No mathematics is decided: this is a definitional sharpening of an extension predicate, not a
statement about cosmic censorship. The class token remains C2 and the conclusion token is untouched.
