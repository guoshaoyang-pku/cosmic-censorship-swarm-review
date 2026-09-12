# F2a rev13 full-schema verdict — W047-F2A-REV13-VERDICT-01

**Reviewer:** worker-047 (independent; did not author F2a, F0, F1, F2b or any earlier F2a verdict)
**Target:** `schemas/af_scc_c2_vacuum.yaml` — class `AF-SCC-C2-VAC-GEN`, node `F2a`
**Reviewed pin:** `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` (revision 13, FROZEN rev29)
**Verdict:** `revise` — score 3.5 — `counts_as_full_schema_verdict: true`
**Instrument:** `check_f2a_rev13_verdict.py` — 39 criteria, 16/16 mutation controls, byte-deterministic, read-only outside this task directory, exit 1 on hard failure / 2 on pin drift / 3 on control failure.

## Why this verdict exists

worker-091's F2a review (`reviews/F2a-review-rev27-b.json`, 00:54:07) is bound to the
**superseded** rev12 pin `5476a3f2c6bc` and explicitly declares
`counts_as_coverage_for_live_revision: false` with the instruction *"Fresh independent verdict at
live pin e9a27996: accept only if HF-091-02 is repaired (M' category and iota regularity frozen);
otherwise revise."* No verdict bound to the live rev13 pin existed when this task was taken.

## Method

1. Pin the eight inputs, verify all content pins before and after the run (exit 2 on any move).
2. Run 39 criteria over the whole class surface: identity, F0 contract, quantifiers, conclusion,
   extension predicate, implication ledger, genericity, topology, data class, I+/visibility,
   falsifier, anti-scope, status honesty, vocabulary.
3. Run 16 mutation controls (14 targeted + duplicate-key + future-date) plus one positive control
   that injects the missing M' category / iota regularity and requires G23+G24 to flip to pass.
4. Corroborate class identity with the canonical `research_map/class_separation.py`
   (`evidence/classsep_f2a.json`: 0 findings; regression 17 TP / 10 TN / 0 FN / 0 FP, corpus 27).
5. Report only; no canonical artifact was written or edited.

## Result: 35/39 pass, 4 hard failures on two axes

### HF-047-01 — extension predicate under-frozen (G23, G24) — blocking

The extension predicate is the load-bearing definition of the class, yet it does not fix:

* **(G23) the differentiable category of M'.** The only clause naming M' as a manifold is
  `topology.extension_topology`: *"M' is a connected 4-manifold containing iota(M) as an open
  proper subset"* — no smoothness/C^k qualifier. `extension_predicate` clause (c) adds only
  connected + time-orientable.
* **(G24) the regularity of the embedding iota.** Clause (a) says *"iota: M -> M' is an isometric
  embedding"* with no differentiability class attached.

This is not a stylistic gap; the sibling proves the authoring convention. **F2b fixes it:**
`schemas/af_scc_c0_vacuum.yaml` clause (c) reads *"M' is a SMOOTH (C-infinity) connected
4-manifold ... the smooth structure is the category in which the metric is a tensor field, while
the metric itself is only continuous (worker-16 F2b-16-03 accepted: a merely topological M' cannot
carry a classical Lorentzian tensor field)"* (measured by the same instrument:
`sibling_comparison.f2b_mprime_category_frozen = true`, `f2a = false`).

Consequence: the containment ledger `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` and the tier-1 falsifier
step *"the extension map iota is an isometry onto an open proper subset"* are only well-typed if
M' carries a differentiable structure at least C^2 and iota has a differentiability class. With
both unfrozen, a reader can instantiate the "same" C2 class with a different extension set, which
is exactly what the containment/transfer claims must exclude. This independently reproduces
worker-091's HF-091-02 in a sharper, sibling-anchored form.

### HF-047-02 — cross-artifact vocabulary authority unresolved (G39, G40) — blocking

The schema's class-defining vocabulary uses the `VOCAB_ALIASES.json` **canonical** tokens while
F0's allowed lists contain only their **aliases**:

| field | F2a value | F0 allowed list | classification |
|---|---|---|---|
| `conclusion.conclusion_type` | `scc_c2_future_inextendibility` | `weak_cosmic_censorship`, `strong_cosmic_censorship_C2`, `strong_cosmic_censorship_C0` | alias-inverted |
| `genericity.kind` | `residual_comeager` | `baire_residual`, `dense_open`, `measure_one`, `provisional_baire_residual`, `unresolved` | alias-inverted |

Under exact-membership conformance, F2a's axis tokens are not members of the F0 contract they
point at; under alias-aware conformance they are equivalent, but **F2a declares no
`VOCAB_ALIASES.json` pointer** (G40), so its own reading depends on an unstated registry. F0 is a
party to the inversion (its own `classes[*].axes` carry alias tokens), so the repair may be
F0-side — but until the authority is single-sourced and recorded, F2a cannot be cleanly accepted.
Independently re-measures worker-090's `W090-VOCAB-01`/`W090-VOCAB-04` at rev13 inside a
full-schema verdict.

## Closed at rev13 (verified here)

* **G06 passes:** `f0_binding.consistency_evidence_sha256` resolves to the live
  `artifacts/formulation/evidence/taxonomy_consistency.json` `9e335e9ba1bf` and the evidence
  reports `consistent: true` over all four classes. worker-091's HF-091-01 and worker-090's
  W090-F2A-01 (stale consistency hash) are **fixed by rev13**.
* All 33 other criteria pass: identity and single C2 token; pointer resolution in the declared F0
  (`0abb9ed8a961`); FROZEN rev29 pin; no duplicate keys; clock discipline; quantifier order and
  correct negation; D0 tagged disjoint union; conclusion family/obstruction/forbidden
  strengthenings and weakenings; extension clauses (a)–(f), frozen equation/direction,
  must-not-conflate; containment chain in all three locations; entailment and forbidden-transfer
  ledgers; genericity kind/ambient space/transfer directions/variants; topology and data class;
  I+ and visibility roles; tiered falsifier; anti-scope; open-problem status honesty; non-vacuity
  proof obligation.
* Canonical class separation: 0 findings; regression PASS.

## Non-claims

* Not a gate verdict and not a node completion; worker events cannot set `status=done`,
  `validation_status=passed` or a gate verdict.
* Physics, quantifier truth and the mathematical conjecture are **not** adjudicated; this is a
  schema-level review of class binding, exactness and evidence hygiene.
* The vocabulary failure does not decide whether F0 or the registry should win.

## Falsifier

At the pins in `snapshot/SHA256SUMS`, this revise verdict is falsified if (a) any content pin
differs on re-measure; (b) a repaired F2a freezes the differentiable category of M' and the
regularity of iota and G23/G24 re-run PASS; (c) F2a's `conclusion_type` and `genericity_kind`
become exact members of the F0 allowed lists (or the controller records an alias-equivalence
ruling *and* the schema declares the alias registry) and G39/G40 re-run PASS; or (d) any of the
16 controls stops discriminating. A later file write at a different hash voids this verdict; it
does not falsify it.

## Reproduction

```bash
cd artifacts/worker-047/f2a_rev13_verdict
python3 check_f2a_rev13_verdict.py    # exit 1 = revise; report.json rewritten deterministically
```
