# W061-F1-REV12-GATE-03 -- F1 independent repair audit at cce9c601

- target: `schemas/af_wcc_vacuum.yaml`  
- reviewed_sha256: `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` (revision 12)  
- verdict: **accept** (score 4.5), hard failures: none  
- proposed rule verdict at this hash: **pass**  
- binding gate verdict at this hash (manifest 014e2d30): **pass**

## Findings

**F-01 [positive] HF-06 visibility predicate (rev11 hard failure)** -- REPAIRED at cce9c601. visibility.definition is the single-q TAIL predicate; quantifiers.formal binds 'not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M'; domains.D5 defines the (q,t0) tail pairs and explicitly repudiates whole-curve containment as strictly stronger; quantifiers.negation negates the tail predicate and visibility.negation_conclusion carries 'for every q in I+ and every t0'.

**F-02 [positive] dangling AF_{I+} (rev11 hard failure)** -- REPAIRED: conclusion.predicate_abbreviation defines AF_{I+} and binds it to i_plus.definition with no additional assumption; statement_formal calls it by name.

**F-03 [positive] YAML strictness / duplicate keys (rev11 hard failure)** -- REPAIRED: yaml.compose finds 0 duplicate mapping keys at cce9c601 (rev11 had 7 duplicate revised_at keys plus 2 revised_at_unused); revision history moved into a revision_history list.

**F-04 [positive] class-contract pointer resolution (rev11 hard failure)** -- REPAIRED: class_contract_pointer now targets research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN, which resolves (classes.AF-WCC-VAC-GEN present at taxonomy 0abb9ed8); the authoring-tree supplement is a separately named field (class_contract_supplement_pointer) so the declared taxonomy and the supplement cannot be conflated.

**F-05 [positive] freeze hash binding** -- FROZEN rev28 (self 2f358f67) declares F1 = cce9c601 and the measured canonical F1 equals it; f0_binding.declared_f0_sha256 equals the measured canonical taxonomy 0abb9ed8. All five pinned canonical files match FROZEN rev28.

**F-06 [advisory] D0 residual (tagged-union reading)** -- The rev11 ill-typedness hard failure is repaired: the first binder is the single tagged index r and all quantified objects are r-indexed. Residual for lead adjudication: D0 remains a tagged disjoint union whose definition contains 'smooth ... or ... (sobolev,s,delta)', so the G-FORM item 'no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b' (W037-F5) is restructured rather than removed. The exact-prefix criterion is met at prefix level ('forall r in D0'); whether the tagged-index formulation satisfies the single-data-class criterion is a scope call, not a schema-level hard failure.

**F-07 [finding-control] binding-gate blindness on the predicate-identity axis (continuity of W061 F-06)** -- CONFIRMED at rev12. With the current manifest (014e2d30, FROZEN rev28) the binding gate check_class_schema.py (000e09e4, rule_spec 40f9bb9e) returns pass/failed_rules [] on all four semantic substitutions: M0 formal B-containment, M1 variant-SET predicate in visibility.definition, M2 stale whole-curve D5, M4 whole-curve negation - as well as on the key-hygiene control and the cosmetic control. Under the pre-fix manifest (fce91948, FROZEN rev27) the same four mutants also pass; only the unfixed canonical POS trips R22 (unknown keys). The proposed rule W061-PREDICATE-CONSISTENCY-V1 detects 4/4 mutants (R3/R4/R5/R6/R7), passes POS/keyfix/cosmetic and returns not_applicable for the F2a/F2b siblings.

**F-08 [process-resolved] freeze -> tool-manifest binding in the rev27 window** -- FROZEN rev27 (self 2554e276, 00:32:59) declared KEY_MANIFEST fce91948, which did not whitelist the rev12 keys, so F1/F2a/F2b returned fail R22 between ~00:33 and ~00:34; the manifest was edited in place to 014e2d30 and FROZEN bumped to rev28 (self 2f358f67, 00:35:08), after which the same schema bytes pass. Reproduced with the frozen tool bytes in gate_replay/. No standing failure at emission time; recorded because G-FORM verification reads the freeze/manifest pair.

**F-09 [advisory] canonical vs authoring taxonomy divergence (CF-13 residual)** -- Canonical taxonomy 0abb9ed8 and authoring mirror d7419b4e still differ. F1's class_contract_pointer now resolves in the canonical tree, so F1 is unaffected; the supplement pointer intentionally targets the authoring mirror. CF-13 remains partially open at the taxonomy level.

## Proposed control

`W061-PREDICATE-CONSISTENCY-V1` closes the predicate-identity axis the binding gate does not police: R3 canonical predicate tail form, R4 formal expansion, R5 not-exists domain, R6 negation, R7 variant-not-assertive. 4/4 NEG mutants detected; all POS/CTL controls pass; F2a/F2b N/A.

## Next falsifier

Re-measure schemas/af_wcc_vacuum.yaml; any change voids this accept. On cce9c601 the accept is falsified by any of: (a) the proposed rule returning fail on cce9c601; (b) any of M0/M1/M2/M4 returning pass under the rule (sensitivity broken); (c) the canonical gate gaining a predicate-axis rule that flags cce9c601; (d) FROZEN declaring any hash other than cce9c601 for F1; (e) visibility.definition, quantifiers.formal, D5 or quantifiers.negation losing the t0 tail binder; (f) the class_contract_pointer failing to resolve in the canonical taxonomy.
