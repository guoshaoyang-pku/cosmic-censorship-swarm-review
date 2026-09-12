# W017-VOCAB-SOURCE-01 — vocabulary-source adjudication (G-FORM, F2a/F2b blocker)

**Worker:** worker-017 (bounded execution worker) · **Class-bound:** `AF-WCC-VAC-GEN`,
`AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM · **Nodes:** F1, F2a, F2b
**Verdict:** revise (binding-source conflict; a controller single-sourcing ruling is required)
**Canonical files modified:** none. All outputs are under `artifacts/worker-017/`.

## The conflict, in one paragraph

Two frozen canonical sources disagree about the canonical spelling of the conclusion and
genericity tokens, and the three class schemas cannot satisfy both:

| source | conclusion_type for C2/C0 | genericity_kind |
|---|---|---|
| `research_map/formulation_taxonomy.yaml` (`field_vocabulary` + `axes`) | `strong_cosmic_censorship_C2/_C0` | `provisional_baire_residual` |
| `artifacts/formulation/rule_spec.json` (`vocabularies`, enforced by gate R11/R07) | `scc_c2_/scc_c0_future_inextendibility` | `residual_comeager`, … (no `provisional_*`) |
| `artifacts/formulation/VOCAB_ALIASES.json` | **keys** = `scc_*`; the taxonomy strings are **aliases**, and the policy says aliases "must never appear in a new canonical artifact" | **key** = `residual_comeager` |
| the three canonical schemas | `scc_*` (canonical keys) | `residual_comeager` |
| `check_taxonomy_consistency.py` `canon()` | returns the **alias-map key**, i.e. `scc_*` | returns `residual_comeager` |

So the binding chain (rule_spec R11 + alias-policy canonical direction + the consistency
checker's own `canon()`) makes the **schemas conformant and the F0 `field_vocabulary.allowed`
list / `axes` values the inconsistent source**. Reviewers who charged literal membership in the
F0 list as a hard failure (HF-088-F2a-VOC, W090-F2A-02, worker-005 P4/P5) tested the wrong
source; but only a controller/Astra single-sourcing finding can say so, because no worker may
rank two frozen canonical artifacts.

## Mechanical evidence (reproducible)

Run `python3 artifacts/worker-017/vocab_source_adjudication/adjudicate_vocab.py` from the repo
root. It pins 13 snapshots by sha256 at entry, then:

* frozen structural gate on the three canonical schemas → **pass / pass / pass**;
* control substituting the F0 literal into F2a (`strong_cosmic_censorship_C2`) → **fail R11** —
  proving repair direction D-C (retokenise the schemas to the F0 literals) is invalid under the
  frozen gate, and also violates the alias policy;
* control substituting the F0 genericity literal → **fail R07, R21**;
* control putting an SCC token on the WCC schema → **fail R11, R12**;
* repair direction D-B (stage an F0 taxonomy aligned to the rule_spec vocabulary) run through
  the frozen consistency checker in a sandbox → **CONSISTENT**, staged F0 hash
  `c310e86106b3…`; because the schemas' own `f0_binding` rule requires a re-bind whenever the
  declared F0 hash moves, D-B voids the G-F0 accepts at `0abb9ed8a961` **and** every F1/F2a/F2b
  verdict at the current hashes.

## Repair directions

* **D-A (recommended, zero artifact churn):** Astra/lead-audit single-source the schema
  vocabulary to `rule_spec.vocabularies` + `VOCAB_ALIASES` canonical keys, record that the F0
  `field_vocabulary.allowed` list and `axes` values are documentation lag, and disposition the
  literal-membership hard failures as source-selection errors. No frozen hash moves; every
  current review stays valid.
* **D-B:** revise F0 to the rule_spec vocabulary (mechanically demonstrated here). Correct but
  moves F0 → all three schemas → FROZEN, voiding all current accept/revise verdicts and forcing
  a full re-review round.
* **D-C:** retokenise the schemas to the F0 literals. **Invalid** under the frozen gate (R11)
  and under the alias policy.

## Scope / non-claims

Not a full-schema acceptance verdict; quantifiers, physics and the separate `f0_binding`
evidence-hash defect (`675a99d0` vs measured `9e335e9b`) are out of scope. No gate verdict, no
node completion, no theorem, no canonical write. The D-A recommendation belongs to the
controller and audit lead, who own the ruling.
