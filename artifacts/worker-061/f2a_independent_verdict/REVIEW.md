# W061-F2A-INDEP-REV-01 — independent review of F2a (AF-SCC-C2-VAC-GEN)

- Reviewer: worker-061 (not an author; no formulation artifact edited)
- Emitted: 2026-09-12T00:22:18+08:00
- Verdict: **accept**, score 4.0, hard failures: none
- Reviewed artifact: `schemas/af_scc_c2_vacuum.yaml` at sha256 `4b3dfd7656bb2d1125e6ea3c64c87f933745f16083e6365c2d5120c069b8ae08`
  (pinned copy `pinned/af_scc_c2_vacuum.yaml`, revision 10)
- Canonical F0 taxonomy checked against: sha256 `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` (binding fresh)
- Siblings compared: F1 `16128b62fe08`, F2b `962f33c6d047`

## What was checked (machine evidence)

| probe | result |
|---|---|
| P1 identity/axes | pass |
| P2 extension_predicate, clauses (a)-(f), frozen axes (HF-A1) | pass — fixed at this revision |
| P3 D0/(s,delta) quantifier coherence vs canonical F0 (HF-A2) | pass at this revision |
| P4 canonical `check_class_schema.py` | pass, exit 0, no failed rules |
| P5 F0 declared-vs-measured hash binding | pass |
| P6 class-separation detector + 27-fixture regression | pass (17/17 leaks, 10/10 controls) |
| P7 F1/F2a/F2b restricting data-class concordance | pass (2 gloss-only diffs) |
| P8 conclusion direction / inflation guard | pass |

Full machine report: `probe_f2a_output.json`; gate stdout: `gate/check_class_schema_pinned.json`.

## Findings

- F-01 POSITIVE (HF-A1 resolved at this hash): extension_predicate block 'proper_future_extension_in_class' exists with frozen_direction=future, frozen_regularity=C2, frozen_equation_concept=classical_ricci and clauses (a)-(f) in its definition; quantifiers.domains.D3.definition_ref resolves to it and conclusion.statement_formal calls the same predicate. Probe P2 pass.
- F-02 POSITIVE (HF-A2 disposition, hash-bound): the D0/(s,delta) binder used by quantifiers.formal, quantifiers.negation, quantifiers.negation_normal_form and conclusion.statement_formal is now (i) defined in quantifiers.domains.D0 with a definition_ref, and (ii) the same quantifier form as the pinned canonical F0 class statement ('For every admissible (s,delta) ...'). The rev3-vintage internal contradiction (an order_note claiming exactly one frozen data class / no regularity-pair binder while the statement carried the binder) is absent from this revision. The prior HF-A2 hard failure is therefore falsified against these bytes; it would return if the canonical F0 text dropped the admissible-(s,delta) quantifier while F2a kept it. Probe P3 pass.
- F-03 POSITIVE: canonical check_class_schema.py returns pass (exit 0, failed_rules []) on the pinned bytes. Probe P4 pass.
- F-04 POSITIVE: f0_binding.declared_f0_sha256 equals the measured pinned canonical taxonomy hash 276009f4f63d (research_map/formulation_taxonomy.yaml). Probe P5 pass.
- F-05 POSITIVE: research_map/class_separation.py finds nothing on the pinned F2a text; the frozen regression corpus still scores leaks 17/17, controls 10/10, FP 0, FN 0 (VERDICT: PASS). Probe P6 pass.
- F-06 POSITIVE: F1/F2a/F2b agree on all 12 restricting data-class paths at the pinned triple (matter, Lambda, equations, both constraints, default regularity, s, delta, both decay rates, symmetry, ADM sign). The two residual textual differences are gloss-only: F1 appends ' (weighted Sobolev)' to the Sobolev spaces phrase, and F1 appends an explanatory clause after 'not imposed' for parity. Consequence: the map's G-FORM unmet item 'no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b' is NOT reproduced at the pinned triple; it should be re-measured before it is used to hold G-FORM. Probe P7 pass.
- F-07 POSITIVE: no conclusion inflation. conclusion_type is the C2 token scc_c2_future_inextendibility (family SCC); the assertive conclusion surfaces carry no WCC/visibility content and no C0 conclusion token; the C0/C1/H2_loc and two-sided readings live in forbidden_* / variant slots. Probe P8 pass.
- F-08 SOFT (not a hard failure): binder naming. conclusion.statement_formal quantifies 'forall D in G_{s,delta}' while quantifiers.ordered names the same D2 binder '(Sigma,h,K)'. Same domain, cosmetic divergence; recommend aligning the names in the next revision.
- F-09 SOFT: unresolved_items (diffeomorphism-quotient construction, meagreness of the excluded families, non-vacuity witness membership, nonlinear extension regularity) remain declared unresolved. This review does not resolve them and the accept does not extend to them.
- F-10 PROCESS / drift: between the pin (00:19+08:00) and this emission the canonical F2a moved 4f97273e -> 4b3dfd76 -> b6123750b37d (rev11), F1 -> 9a8bd4c96800, F2b -> 1bb78ce9b357. A non-binding drift control reran the same eight probes on the newest canonical copies: all pass, and the semantic delta between 4b3dfd76 and rev11 is the revision number only. The accept binds to the pinned hash; later canonical bytes are not covered by it.

## Drift control (non-binding)

The canonical file changed while this review ran. The same probe set was rerun on the newest
canonical copies (F2a `b6123750b37d` = rev11, F1 `9a8bd4c96800`,
F2b `1bb78ce9b357`) and returned **accept** with no hard failures; the semantic
delta between the pinned rev10 and rev11 is the revision number only. This control does not
extend the binding verdict.

## Scope and authority

Structure/class-binding only. Unresolved mathematical items stay unresolved. This is worker
evidence: it does not set a node status, a `validation_status`, or a gate verdict.
