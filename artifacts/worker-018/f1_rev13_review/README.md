# W018-F1-REV13-REVIEW-01 — independent at-pin review of F1 (AF-WCC-VAC-GEN)

Bounded worker task, self-selected: no `comms/inbox/worker-018.jsonl` card existed for this
fleet batch, so one class-bound task was taken from the live G-FORM blocking item
(`G-FORM-final-verify-r2.json` B-GFORM-R2-1/R2-2/R2-5): an independent, hash-pinned verdict
on the repaired F1 schema at the FROZEN rev29 pin.

## Result

| item | value |
|---|---|
| target | F1 / AF-WCC-VAC-GEN, revision 13 |
| pin | `artifacts/formulation/schemas/af_wcc_vacuum.yaml` = `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| freeze | `artifacts/formulation/FROZEN.json` = `3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833` (rev29) |
| verdict | **revise 4.0** — 24 PASS / 1 DEFECT / 2 ADVISORY |
| hard failure | `HF-W018-F1-1`: variant-SET direction contradiction between F1 rev13 and its own binding target F0-declared `0abb9ed8a961` (L200) and `VARIANT_REGISTRY.json` `5eb42f9a` |
| repairs verified | B-GFORM-R2-1 (consistency pointer refreshed, measured), B-GFORM-R2-2 (strictness corrected; finite-model check 0/30640 violations, 1804-violation non-past-closed control), FROZEN rev29 pins the reviewed bytes |

Full verdict: `REVIEW.json`, mirrored at `reviews/F1-review-worker-018.json`.
Machine output: `results.json`. Harness: `check_f1_rev13.py` (stdlib + PyYAML; no author code
imported or executed; exits 3 on pin drift, 4 if the bytes move during the review).

## Why revise and not accept

F1 rev13 corrected its own text, but F1's `f0_binding.declared_f0_sha256` still points at the
frozen declared taxonomy `0abb9ed8a961`, and that artifact asserts the opposite direction for
F1's registered variant SET ("strictly stronger", L200). `VARIANT_REGISTRY.json` carries the
same inverted label. Under the schema's own definitions (causal geodesic, past-closed `J^-(q)`),
single-q tail containment implies whole-curve containment, so the single-q predicate is strictly
stronger and variant SET strictly weaker. The owner's `FROZEN` rev29 delta discloses this
residual as not repaired in its bounded card; this review confirms it independently and bounds
it to those artifacts.

## Hash-move forensics (fail-closed guard fired twice)

Measured inside one ~4-minute worker lifecycle: F1 `cce9c601` (rev12) → `bf0c28fa` (intermediate
rev13 write) → `d9cebb94` (rev13 final); FROZEN `2f358f67` (rev28) → `e1a8aaa3` (rev29) →
`3d9e3d77` (rev29 rewrite, two distinct bytes under one revision id in 31 s). The first two
harness runs refused to issue a verdict against a moving pin; details in `drift_log.json`.
The landed verdict cites the review-time pins above and re-measures them at exit.

## Non-claims

Worker evidence only: no gate verdict, no node status, no canonical artifact edited, no theorem
or counterexample claimed. The semantics check is a finite-model corroboration on 4 points plus
the transitivity argument, not a general proof in Lorentzian geometry. The review is not blind;
blindness is not claimed.
