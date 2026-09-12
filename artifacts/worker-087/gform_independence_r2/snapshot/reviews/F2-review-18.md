# F2 review 18 — adversarial class-collapse review

- assignment: asg-2026-09-11-A1-deepseek-flash-18-27
- collapse attempt result: **not_supported**
- C2 sha256: `23fec0e9cd68bc99d42f2fa2228f343391df70d802ae50ba368c1e70d96e0f9d`
- C0 sha256: `e6b1af2bd6925f27cdae60d57939e434adca53703cb938f0a4133f3a9f29245b`

## AF-SCC-C2-VAC-GEN — verdict: **revise** (score 2/5)

C2 boundary not collapsed, but the submitted C2 document is not yet a well-formed class definition: hard failures [M-C2-1, M-C2-4, S6-C2, S7-C2] leave the C2 side dependent on fields it does not itself supply.

hard failures: ['M-C2-1', 'M-C2-4', 'S6-C2', 'S7-C2']
warnings: none

- [hard/pass] S3-C2: required fields present
- [hard/pass] S4-C2: regularity declares C2 (matched ['c2', 'twicecontinuouslydifferentiab']): 'data_regularity the single frozen weighted sobolev class: h - delta_euclidean in h^4_{1/2+epsilon}, k in h^3_{1/2+epsilon}, delta = 1/2 + ep'
- [hard/pass] S5-C2: no merged token (0 separation mention(s))
- [hard/fail] S6-C2: regularity-pair binder residue found: 'forall (s,delta)'; the artifact is a family of statements, not one class
- [hard/fail] S7-C2: 'extension_predicate' referenced 4 time(s) but no such block is defined in this document (dangling reference to the class core)
- [hard/pass] K9-C2: anti_scope excludes AF-SCC-C0-VAC-GEN: explicit_id=True synonym='c0' negation=True; text='no conclusion about class af-scc-c0-vac-gen may be derived from this file; that class has its own artifact and its own c'
- [hard/pass] K1: regularity C2='data_regularity the single frozen weighted sobolev class: h - delta_eu' C0='data_regularity smooth-with-decay class as frozen in data_class.regula'
- [hard/pass] K2: conclusion_type C2='scc_c2_future_inextendibility' C0='scc_c0_future_inextendibility', text jaccard=0.43
- [warn/pass] K10b: C2 conclusion does not assert C0-inextendibility
- [hard/pass] K4: obstructions differ (jaccard=0.16)
- [warn/pass] K11-C2: status token 'open_problem' coincides with peer but the obstruction records no refutation of the class statement (only, at most, of an unqualified strengthening)
- [warn/pass] K6b: hypotheses jaccard=0.07
- [warn/na] K7: test-case fields absent (C2=False, C0=False)
- [warn/pass] K8: whole-section token jaccard=0.52
- [hard/fail] M-C2-1: The reviewed revision fails the canonical binding gate: python3 artifacts/formulation/tools/check_class_schema.py schemas/af_scc_c2_vacuum.yaml returns FAIL R17/R18/R19/R22. R17/R18 because extension_predicate (clauses a-f) is referenced at lines 75/76/209 but not defined; R19 class_contract_pointer does not name the class; R22 unknown keys R01-R06. Machine detectors: probe S7-C2 (dangling extension_predicate) and probe S6-C2 (forall (s,delta) in D0 residue at line 209 vs single-class quantifiers.formal at line 52).
- [info/pass] M-C2-2: Genericity topology and weighted indices remain proposed_pending_A1 with unresolved citations for the Sobolev thresholds and meagreness, declared by the schema itself. No conclusion inflation: forbidden_strengthenings blocks C0/H2_loc/two-sided/all-data/WCC.
- [info/pass] M-C2-3: Separation from the sibling is substantive: extension regularity C2 vs C0, distinct conclusion_type, obstruction jaccard 0.14, conclusion predicate jaccard 0.21 after stripping regularity tokens; anti_scope (line 234) names AF-SCC-C0-VAC-GEN explicitly. Primary sources PS-1..PS-4 verified at abstract level.
- [hard/fail] M-C2-4: Cross-schema data class mismatch: line 133 requires F2b to adopt the H^4_{1/2+epsilon} block verbatim and records that F2b freezes smooth-with-decay instead; line 424 repeats it as unresolved. G-FORM's one-frozen-data-class criterion is unmet until the freeze decision lands.

## AF-SCC-C0-VAC-GEN — verdict: **revise** (score 2/5)

The C0 document is separable from C2 in principle, but hard failures [M-C0-1, M-C0-5] mean it does not yet pin its own regularity, obstruction, or anti-scope, so it cannot be frozen as a distinct class.

hard failures: ['M-C0-1', 'M-C0-5']
warnings: none

- [hard/pass] K12-C0: sidecar af_scc_c0_vacuum.yaml.sha256 claims e6b1af2bd6925f27..., file hashes e6b1af2bd6925f27...
- [hard/pass] S3-C0: required fields present
- [hard/pass] S4-C0: regularity declares C0 (matched ['c0', 'continuous', 'nodifferentiab']): 'data_regularity smooth-with-decay class as frozen in data_class.regularity_class.default solution_regularity g of class c^infinity(m) for th'
- [hard/pass] S5-C0: no merged token (0 separation mention(s))
- [hard/pass] S6-C0: no regularity-pair binder residue
- [hard/pass] S7-C0: extension predicate defined
- [hard/pass] K9-C0: anti_scope excludes AF-SCC-C2-VAC-GEN: explicit_id=True synonym='c2' negation=True; text='not_this_class class_id af-scc-c2-vac-gen why different (weaker) statement; the containment c0 implies c2 runs one way o'
- [hard/pass] K1: regularity C2='data_regularity the single frozen weighted sobolev class: h - delta_eu' C0='data_regularity smooth-with-decay class as frozen in data_class.regula'
- [hard/pass] K2: conclusion_type C2='scc_c2_future_inextendibility' C0='scc_c0_future_inextendibility', text jaccard=0.43
- [hard/pass] K3: C0-vs-C2 conclusion jaccard after regularity stripping = 0.43; C2_pred='conclusion_type scc__future_inextendibility epistemic_status open_problem family scc statement_natural_language for gene'; C0_pred='conclusion_type scc__future_inextendibility epistemic_status open_problem family scc statement_natural_language generic '
- [hard/pass] K10a: C0 conclusion does not assert C2-inextendibility
- [hard/pass] K4: obstructions differ (jaccard=0.16)
- [warn/pass] K11-C0: status token 'open_problem' coincides with peer but the obstruction records no refutation of the class statement (only, at most, of an unqualified strengthening)
- [hard/pass] K5: C0 obstruction anchor=True extendibility=True continuous-metric=True; primary source arXiv:1710.01722
- [hard/pass] K6: no non-negated C2-regularity assumption in C0 hypotheses
- [warn/pass] K6b: hypotheses jaccard=0.07
- [warn/na] K7: test-case fields absent (C2=False, C0=False)
- [warn/pass] K8: whole-section token jaccard=0.52
- [hard/fail] M-C0-1: The artifact's composite_regularity_lint.exemption (line 327) states that no merged-class pattern occurs outside the lint block, but line 5 (YAML comment) contains 'C0 or C2'. The artifact's own declared leakage test cannot pass on this revision. Either remove/reword line 5 or amend the exemption.
- [info/pass] M-C0-2: Status/obstruction wording is scoped correctly: known_obstruction (lines 257-262) refutes only the unqualified all-data statement and delegates the C0 literature to L1, so the shared open_problem token no longer conflates the classes (probe K11 passes).
- [info/pass] M-C0-3: No C2 inheritance: hypotheses/conclusion/obstruction jaccards 0.25/0.21/0.14; anti_scope names AF-SCC-C2-VAC-GEN (line 313); implication ledger runs C0 => C2 one way; the disjunctive data domain is removed (lines 71-74, 160-167, 273, 318). Canonical binding gate PASS.
- [warn/warn] M-C0-4: tier_1.machine_checkable_steps (line 299) overstates machine-checkability: only constraint residuals are directly checkable; sampled continuity, isometry onto an open proper subset and future-point addition are numerical/proof obligations. non_machine_checkable_step names only non-meagerness.
- [hard/fail] M-C0-5: Node identity mismatch: node_id F2b (line 15) while the w06 gate's declared_artifact_matches reports map_node 'F2b' != declared 'F2'. Cross-artifact: aggregator pins are stale (C2 21df6f7f / C0 cb897b29 vs disk 23fec0e9 / e6b1af2b), so w05 A3/C6 fail on drift.

## Limitations

- Probes are structural/lexical; they detect merged-class tokens, conclusion inheritance, identical obstructions, and C2-assumption leakage, but they cannot prove two schemas define different solution sets.
- K5 anchors the C0 obstruction to arXiv:1710.01722 (Dafermos-Luk); that anchor itself was fetched from the arXiv abstract page, not from the published Annals version.
- Artifact correctness beyond separation is out of scope for this review; a separate content review of each schema is required before freeze.

## Discrimination witness (answer to the collapse question)

**Witness type:** a generic asymptotically flat vacuum datum whose maximal development admits a proper future extension with continuous (C^0) metric but no proper future C^2 extension (weak-null-singularity Cauchy horizon).

- falsifies: AF-SCC-C0-VAC-GEN conclusion (a continuous extension exists)
- leaves intact: AF-SCC-C2-VAC-GEN conclusion (the existing extension is not C^2)
- why valid: the two schemas' own implication ledger runs C0-inextendibility => C2-inextendibility one way only; a model of C2-inextendibility that is not a model of C0-inextendibility shows the classes are not the same statement
- status: conditional_expected, not verified: Dafermos-Luk (arXiv:1710.01722) prove the continuous extension and predict generically singular C^0-metric horizons, conditional on Kerr exterior stability; no generic AF vacuum witness is constructed in this repository
- what would collapse the classes: if no generic datum admits a C^0-but-not-C^2 extension, every datum satisfies both conclusions or neither, and the two classes would be only nominally distinct (different regularity demanded, same truth value on all data)

## Aggregator addendum (schemas/af_scc_regularities.yaml)

- aggregator sha256: `c6bfda2bf3f528d3380ec02dddbd9d76a75a1b65de3b6d140e87852ddb7c834e`
- pin check: `artifacts/worker18/f2_review/aggregator_pin_check.json` (pass)
- P1: pass ['AF-SCC-C2-VAC-GEN', 'AF-SCC-C0-VAC-GEN']
- P2-AF-SCC-C2-VAC-GEN: pass schemas/af_scc_c2_vacuum.yaml
- P3-AF-SCC-C2-VAC-GEN: pass {'pinned': '21df6f7fc4a6c049', 'actual': '21df6f7fc4a6c049'}
- P2-AF-SCC-C0-VAC-GEN: pass schemas/af_scc_c0_vacuum.yaml
- P3-AF-SCC-C0-VAC-GEN: pass {'pinned': '0150bfdf671b1452', 'actual': '0150bfdf671b1452'}
- P4: pass []
- P5: pass []

## Cross-instrument addendum

| instrument | C2 | C0 |
|---|---|---|
| worker-18 structural probe (this review) | pass | pass on separation; hard on sidecar |
| worker-05 integration lint | pass | **fail** (C7-shared-data-class, C6-revision-pins) |
| worker-06 sibling gate (declared by the C0 schema) | pass | **fail** |

both failing lints are polarity-blind/raw-text-based; the C0 occurrences are separation statements, so the semantic content is not merged. But G-FORM's stop rule requires the machine lint to pass, so the artifact must be revised (rename exclusion keys, drop the task-quote comment, rephrase the must_not_conflate line) or the w05/w06 rules amended with polarity handling and an anti-scope whitelist. Reviewer 18 has no authority to amend another worker's gate; this is escalated to lead-formulation/Astra.

