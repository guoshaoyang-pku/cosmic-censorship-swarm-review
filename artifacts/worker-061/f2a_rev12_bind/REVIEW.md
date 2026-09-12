# W061-F2A-REV12-BIND-04 — F2a (AF-SCC-C2-VAC-GEN) rev12 binding review (revised)

- target: `schemas/af_scc_c2_vacuum.yaml` @ `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce`
- verdict: **revise** (score 3.0)
- reviewer: worker-061; first emission 2026-09-12T00:46:27+08:00, erratum 2026-09-12T00:48:01+08:00

## Errata

- ERR-W061-F2AB-01: finding F-W061-F2AB-08 only: the first emission said neither F1 nor F2b names VOCAB_ALIASES.json; the measurement is F1 genericity.vocabulary_aliases_ref = artifacts/formulation/VOCAB_ALIASES.json (line 149), F2a/F2b none. Verdict, score, hard failures, probes and adjudications are unchanged.

## Hard failures
### HF-W061-F2AB-01 — F0 vocabulary binding: conclusion_type

F2a declares conclusion.conclusion_type='scc_c2_future_inextendibility'. At the bound canonical F0 taxonomy (research_map/formulation_taxonomy.yaml 0abb9ed8a961), field_vocabulary.conclusion_type.allowed is ['weak_cosmic_censorship','strong_cosmic_censorship_C2','strong_cosmic_censorship_C0'], so the declared token is NOT literally allowed, and the same class contract's axes.conclusion_type is 'strong_cosmic_censorship_C2'. The token does match rule_spec.json#vocabularies.class_conclusion_type.AF-SCC-C2-VAC-GEN and is the canonical key of VOCAB_ALIASES.conclusion_type (members include the F0 token), but F2a carries vocabulary_aliases_ref=null and never names VOCAB_ALIASES.json, so the alias equivalence is unbound at artifact level. Root cause is a canonical-vocabulary conflict (F0 field_vocabulary vs rule_spec vs the alias registry's direction), not a class-semantics change: exactly one class token, family SCC, no C0/WCC content (P1/P13 pass). Reproduces worker-059 HF-059-F2A-01 and worker-005's F2b vocab audit (P4/P5/P6) on F2a.

Falsifier: An F0 revision whose field_vocabulary.conclusion_type.allowed contains the F2a token, or an F2a revision that binds the alias registry (vocabulary_aliases_ref), or a controller decision recorded in research_map/research_map.json that alias-equivalence satisfies the G-FORM class-binding criterion for this axis.

### HF-W061-F2AB-02 — F0 vocabulary binding: genericity_kind

F2a declares genericity.kind='residual_comeager'. At the bound canonical F0 taxonomy 0abb9ed8a961, field_vocabulary.genericity_kind.allowed is ['baire_residual','dense_open','measure_one','provisional_baire_residual','unresolved'], so the declared token is NOT literally allowed; the class contract's axes.genericity_kind is 'provisional_baire_residual'. The token matches rule_spec.json#vocabularies.genericity_kind and is the canonical key of VOCAB_ALIASES.genericity_kind (members include baire_residual and provisional_baire_residual), but the artifact binds no alias reference (same root cause as HF-W061-F2AB-01). Reproduces worker-005's F2b P5 on F2a.

Falsifier: An F0 revision whose field_vocabulary.genericity_kind.allowed contains residual_comeager, or an F2a revision that binds the alias registry, or a controller decision that alias-equivalence satisfies the G-FORM class-binding criterion for this axis.

### HF-W061-F2AB-03 — binding-hash freshness: consistency evidence

F2a f0_binding.consistency_evidence_sha256 declares 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48, while the evidence file artifacts/formulation/evidence/taxonomy_consistency.json measures 9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b and FROZEN rev28 (2f358f6722d9) pins that same 9e335e9b hash. The declared F0 taxonomy hash is fresh (0abb9ed8a961 == measured). Reproduces worker-059 HF-059-F2A-02, worker-039 S8 (F1), worker-005 P9 (F2b): the declaration is one evidence regeneration behind.

Falsifier: A revision whose f0_binding.consistency_evidence_sha256 equals the measured and FROZEN-pinned evidence bytes, at the same F2a sha256.

### HF-W061-F2AB-04 — citation scope: l1_ledger_refs vs frozen ledger

Four of the five l1_ledger_refs rows assert citation_status='verified_by_L1' (T-401, T-402, T-514, T-520), while ledger/theorems.jsonl records verification_status='abstract-read' and review_status='not_independently_reviewed' for every one of them. This holds both at the current ledger hash a1674f094979 and at the worker-029 pinned snapshot 3e3d35531421, and the token 'verified_by_L1' occurs 0 times in both ledger texts. The remaining row T-305 is 'unresolved' and is consistent with its abstract-read ledger row. Additionally the artifact's l1_status='accepted' (T-402/T-514/T-520) has no defined mapping to the ledger vocabulary. Independent reproduction of worker-029 HF-29-02 at the pinned F2a hash.

Falsifier: Any l1_ledger_refs row with a verified citation_status backed by a ledger row whose verification_status or review_status records independent verification, or a revision that demotes the four rows to the ledger's vocabulary ('abstract-read' / 'unresolved').

## Findings

### F-W061-F2AB-01 (positive)

Identity and class binding clean at 5476a3f2c6bc: exactly one class_id AF-SCC-C2-VAC-GEN, node_id F2a, class_components censorship=SCC / regularity_token=C2, conclusion family SCC. Probe P1 pass.

### F-W061-F2AB-02 (positive)

The rev11->rev12 repair set is independently verified at the pinned bytes: strict YAML census finds 0 duplicate mapping keys in F2a/F1/F2b; class_contract_pointer resolves inside canonical research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN; D0 is re-typed as a tagged disjoint union over the bare index r and quantifiers.formal binds 'forall r in D0'; revision_history indices are monotone 1..10; revised_at 00:31:41 is behind the file mtime 00:32:02 and the wall clock; extension_predicate 'proper_future_extension_in_class' is present and D3.definition_ref resolves to it. Probes P9/P10 pass. The worker-096 BEFORE-01/02/03 and worker-005 F2-01/02/03 rev11 defect classes are therefore closed at rev12.

### F-W061-F2AB-03 (positive)

R22 adjudication (worker-096 W096-F2A-AFTER-01 + worker-005 HF-W005-F2D-01): the claim is FALSIFIED at the current manifest. The canonical gate tool (000e09e46b2f, rule_spec 40f9bb9e) returns verdict=pass failed_rules=[] exit=0 on the pinned bytes under KEY_MANIFEST 014e2d301978 (rev28); replaying the same tool against the rev27 manifest fce91948ba3a in a shadow tree reproduces verdict=fail failed_rules=['R22'] for exactly the six rev12 keys. The finding was manifest-staleness, not a schema defect; its own falsifier is met.

### F-W061-F2AB-04 (positive)

Standing structural controls pass at the pinned triple: canonical gate verdict=pass; class_separation.py finds nothing on the pinned text and the frozen regression corpus scores leaks 17/17, controls 10/10, FP 0, FN 0; F1/F2a/F2b agree on all 12 restricting data-class paths (2 residual differences are gloss-only); the conclusion surface carries no WCC/visibility content and asserts no C0 token. Probes P11/P12/P13 pass.

### F-W061-F2AB-05 (soft)

review_status drift (worker-096 W096-F2A-AFTER-02): F2a declares independent_reviewers=[] and verdict=pending while the live map ledger at the pinned hash records 11 verdict(s), including 10 revise and 1 accept (worker-089). Classified SOFT/process, not a hard failure: the field is an authoring-time snapshot taken before any rev12 review existed, and the authoritative review state is research_map/research_map.json#reviews. Recommendation: refresh the field at the next revision or record explicitly that the map ledger dominates it.

### F-W061-F2AB-06 (soft)

Index pin staleness (worker-005 HF-W005-F2D-02): schemas/af_scc_regularities.yaml (94562101a816) still pins components C2 -> b6123750b37d and C0 -> 1bb78ce9b357, both superseded rev11 hashes; live bytes are 5476a3f2c6bc / 55d0a1ea9bda and FROZEN rev28 pins both. This is a defect of the index file, not of F2a; the index must be re-pinned before it can be used as a binding surface.

### F-W061-F2AB-07 (advisory)

Non-vacuity branch coverage (worker-059 F-059-F2A-02): genericity.ambient_space justifies non-emptiness with 'X_vac is a closed subset of a Banach space, hence Baire', which covers the Sobolev branch r=(sobolev,s,delta) only; D0 also contains the Frechet smooth-with-decay branch (declared in genericity.topology_or_measure). No semantic change is implied; a branchwise Baire statement is needed before non-vacuity can be read for all r in D0.

### F-W061-F2AB-08 (cross-class-measured)

The same binding axes recur across the family, with one correction to the first emission of this finding. Measured at the pinned triple: F1 and F2b both declare f0_binding.consistency_evidence_sha256=675a99d0d25b (stale; measured 9e335e9ba1bf); F1's conclusion token weak_cosmic_censorship is literally in the F0 allowed list, but its genericity.kind residual_comeager is not, and F1 binds the registry at the axis level (genericity.vocabulary_aliases_ref = artifacts/formulation/VOCAB_ALIASES.json, line 149), which F2a and F2b do not have anywhere in their text; F2b's conclusion token scc_c0_future_inextendibility and genericity.kind residual_comeager both need the same alias adjudication as F2a and F2b names VOCAB_ALIASES.json nowhere. This is recorded as a measured fact for the controller, not as a verdict on F1/F2b; a single F0 / alias-registry repair may be cheaper than three per-schema edits.

## Adjudications of open claims

- **W096-F2A-AFTER-01, HF-W005-F2D-01** — FALSIFIED at the current manifest: gate verdict=pass failed_rules=[] exit=0; REPRODUCED in the rev27-manifest shadow (verdict=fail failed_rules=['R22']). The claim was manifest-dependent, not a defect of the schema bytes.
- **W096-F2A-AFTER-02** — REPRODUCED as a fact, classified SOFT/process: the field is an authoring-time snapshot; the authoritative review state is the map ledger, which now records 11 verdict(s) at this hash ({'revise': ['worker-005', 'worker-096', 'astra-lead-audit', 'worker-059', 'worker-034', 'worker-047', 'worker-069', 'worker-048', 'worker-041', 'worker-043'], 'accept': ['worker-089']}). No semantic or binding content in the field.
- **HF-W005-F2D-02** — REPRODUCED as a fact, but it is a defect of schemas/af_scc_regularities.yaml (the index), not of F2a at 5476a3f2c6bc. FROZEN rev28 pins F2a at 5476a3f2c6bc in both trees, so hash-bound verdicts can cite the artifact directly; the index must be repinned or it cannot be used as a binding surface.

## Probe matrix

| probe | status | hard |
|---|---|---|
| P1-IDENTITY-CLASS-BINDING | pass | True |
| P2-F0-VOCAB-CONCLUSION-BINDING | fail | True |
| P3-F0-VOCAB-GENERICITY-BINDING | fail | True |
| P4-EVIDENCE-BINDING-FRESHNESS | fail | True |
| P5-CITATION-SCOPE-BINDING | fail | True |
| P6-R22-MANIFEST-ADJUDICATION | pass | False |
| P7-REVIEW-STATUS-LEDGER | fail | False |
| P8-INDEX-PIN-ADJUDICATION | fail | False |
| P9-REV11-REPAIRS-AT-REV12 | pass | True |
| P10-F0-HASH-BINDING | pass | True |
| P11-CLASS-SEPARATION | pass | True |
| P12-SIBLING-DATA-CLASS | pass | True |
| P13-CONCLUSION-DIRECTION | pass | True |
| P14-NONVACUITY-BRANCHWISE | fail | False |
| P15-DRIFT-CONTROL | pass | True |

## Authority

Worker evidence only. No canonical artifact outside artifacts/worker-061/f2a_rev12_bind/ was modified; the canonical files were copied read-only into pinned/ and the rev27 manifest was replayed in a shadow tree.
