# W005-F2B-VOCAB-BIND-01 — SCAN

**Class** `AF-SCC-C0-VAC-GEN` · **Node** F2b · **Gate** G-FORM · **Actor** worker-005
**Measured** 2026-09-12T00:41:00+08:00 · **Verdict** `literal_vocab_binding_fail__no_class_leakage`

Structural / evidence-binding audit only. Read-only on canonical artifacts. No mathematics decided,
no node status set, no gate verdict cast.

## Pins at measurement

| artifact | sha256 | note |
|---|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda…` | equals FROZEN rev28 pin |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a961…` | declared by `f0_binding` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534…` | frozen alias companion |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf…` | disk == FROZEN rev28 pin |

## Checks

| id | status | question |
|---|---|---|
| P1 | pass | measured pins equal declared pins; FROZEN rev28 pin matches; no intra-run drift |
| P2 | pass | `class_id`/`class_components` are the C0 SCC class |
| P3 | pass | conclusion token canonicalises to exactly one class, `scc_c0_future_inextendibility` |
| P4 | **fail** | conclusion token is a literal member of F0's `field_vocabulary.conclusion_type.allowed` |
| P5 | **fail** | `genericity.kind` is a literal member of F0's `field_vocabulary.genericity_kind.allowed` |
| P6 | **fail** | alias companion `VOCAB_ALIASES.json` is bound by path + sha256 somewhere in F2b |
| P7 | pass | family separation: SCC conclusion, I⁺ not in conclusion, no C2/WCC/merged token |
| P8 | pass | C0 ⇒ C2 one-way row present; no converse entailment; matches F0 T1/X1 |
| P9 | **fail** | `f0_binding` evidence pins current (`declared_f0_sha256` ok; consistency-evidence pin stale) |

## Findings (none is class leakage)

- **F-W005-F2V-P4 (major, literal).** F2b declares `scc_c0_future_inextendibility`; F0 rev5 allows only
  `strong_cosmic_censorship_C0`. `VOCAB_ALIASES.json` makes the F2b token canonical and the F0 token an
  alias, so the two are equivalent **for consistency checks only** — but a checker consuming only the two
  artifacts F2b actually binds sees an out-of-vocabulary token.
- **F-W005-F2V-P5 (minor, literal).** Same pattern for `genericity.kind`: `residual_comeager` (alias-file
  canonical) vs F0's `provisional_baire_residual`/`baire_residual`.
- **F-W005-F2V-P6 (major, binding).** F2b contains **no** reference to `artifacts/formulation/VOCAB_ALIASES.json`,
  so the equivalence that rescues P4/P5 is unbound: the declared hash of the alias file is absent from the
  schema, and no cross-artifact rule inside F2b resolves the token.
- **F-W005-F2V-P9 (minor, evidence).** `f0_binding.declared_f0_sha256` matches the measured F0 rev5 hash, but
  `consistency_evidence_sha256` cites `675a99d0d25b…` while disk and FROZEN rev28 pin `9e335e9ba1bf…`
  (independently reported by worker-092; corroborated here for the F2b half).

## Instrument quality

`check_f2b_vocab_binding.py` — stdlib + PyYAML, strict duplicate-key loader, read-only.
Null control: live baseline `{P1,P2,P3,P7,P8} pass / {P4,P5,P6,P9} fail`. 9/9 planted mutants caught,
one per check (C2 token swap, merged ambiguous token, alias binding added, F0 alias form adopted,
converse entailment injected, hash drift, regularity swap, pin refresh). Degenerate always-accept and
always-reject controls both differ from the baseline. All nine checks are discriminated.

## Falsifier

Re-run `python3 artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py --report` after any write.
Superseded if P4/P5 flip because the F0 allowed-lists gained the alias-file canonical tokens (or F2b adopted
the F0 alias forms), P6 flips because F2b binds `VOCAB_ALIASES.json` at its measured sha256, and P9 flips
because the consistency-evidence pin equals the frozen pin. If P3 or P7 instead turns fail, the
no-class-leakage half is falsified at class level.

## Authority

Worker event only: cannot set `status=done`, `validation_status=passed`, or a gate verdict. Awaiting
controller ingest and lead-formulation repair ownership.
