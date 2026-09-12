# W034 — F1 repair-candidate adjudication (AF-WCC-VAC-GEN / F1 / G-FORM)

Task: cross-adjudicate the two independently produced F1 falsifier-corpus repair
lineages at the FROZEN rev29 pins. Read-only on all canonical paths.

Pins: corpus 56bcb4b3234bc86c; F1 rev13 d9cebb9404b2e79e; F1 rev12 cce9c60146d6a907;
F0 rev5 0abb9ed8a96135c9; FROZEN rev29 815e08079aefbc16. All pins re-measured: True.

## Verdict: `TRUTHFUL_NOT_FREEZE_READY`

| candidate | sha256 | changed ptrs | required | freeze-ready | controls |
|---|---|---|---|---|---|
| cand_w031_tierA | `e172020ccda52b60` | 53 | PASS | no | all caught |
| cand_w031_tierB | `785e6a4e53d64377` | 84 | PASS | no | all caught |
| cand_w077_mechanical | `306480f5f45acc50` | 206 | FAIL | no | all caught |
| cand_w077_f0refresh | `739d5b40dc97111d` | 207 | PASS | no | all caught |

Changed-pointer scope per candidate:

- **cand_w031_tierA**: {'row_binding_or_provenance': 50, 'cross_artifact_binding': 1, 'probe_expectation': 2}
- **cand_w031_tierB**: {'row_binding_or_provenance': 78, 'cross_artifact_binding': 1, 'citation': 1, 'probe_expectation': 2, 'observation': 2}
- **cand_w077_mechanical**: {'historical_provenance': 100, 'row_binding_or_provenance': 75, 'historical_delta': 25, 'observation': 4, 'probe_outcome': 2}
- **cand_w077_f0refresh**: {'historical_provenance': 100, 'row_binding_or_provenance': 75, 'historical_delta': 25, 'observation': 4, 'cross_artifact_binding': 1, 'probe_expectation': 2}

Per-candidate required-check status:

- **cand_w031_tierA**
  - C1-LOAD-25-ROWS-ORDER: PASS — rows=25, test_id order identical=True
  - C1b-CLASS-BINDING: PASS — all rows class_id=AF-WCC-VAC-GEN node_id=F1
  - C2-ROW-BINDING-REV13: PASS — rows not bound to F1 rev13 d9cebb9404b2: none
  - C3-PROBES-84-84-AT-REV13: PASS — probes=84, measured-fail=0 []
  - C6-EXCERPT-FIDELITY-REV13: FAIL — recorded excerpts not a truncation-tolerant match of rev13: 4 [{'test_id': 'F1-AMB-09', 'path': 'genericity.ambient_space', 'recorded': '"the constraint manifold X^{s,delta}_vac(AF) of one-ended asymptotically flat VACUUM initial data in the declared regula'}, {'test_id': 'F1-AMB-21', 'path': 'f0_binding.declared_f0_sha256', 'recorded': '"276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"'}, {'test_id': 'F1-AMB-25', 'path': 'f0_binding.declared_f0_sha256', 'recorded': '"276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"'}, {'test_id': 'F1-AMB-25', 'path': 'f0_binding.binding_note', 'recorded': '"refreshed to the rev4 declared-F0 hash after the astra-classscope-02 amendment (was 66bf917b); consistency re-run CONSI'}]
  - C4-PROBE-IDENTITY: PASS — probe path/kind/role changes: 0 []
  - C4b-EXPECTATION-CHANGE-SCOPE: PASS — 2 expectation change(s), all in the two declared L-FORM-04 probes=True
  - C5a-P1-ANCHOR-LIVE-F0: PASS — P1 expected == live F0 rev5 sha256: True (0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3)
  - C5b-P4-ANCHOR-REVISION-SPECIFIC: PASS — P4 anchor len>=20 and present in rev13 note but absent from the authoring-rev11 note: True ('rev13: consistency_evidence_sha256 refreshed to the live taxonomy_consistency.json 9e335e9ba1bf')
  - C7-PROVENANCE-COMPLETE: FAIL — provenance gaps: 75 ['F1-AMB-01: binding_frozen_revision_schema=12', 'F1-AMB-01: binding_frozen_revision=27', 'F1-AMB-01: rebound_at unchanged', 'F1-AMB-02: binding_frozen_revision_schema=12', 'F1-AMB-02: binding_frozen_revision=27'] (by field: {'binding_frozen_revision_schema!=13': 25, 'binding_frozen_revision<29': 25, 'rebound_at unchanged': 25, 'rebound_at not ISO': 0, 'cross_artifact sha != live F0': 0})
  - C8-HISTORY-PRESERVED: PASS — historical provenance fields rewritten: 0 []
- **cand_w031_tierB**
  - C1-LOAD-25-ROWS-ORDER: PASS — rows=25, test_id order identical=True
  - C1b-CLASS-BINDING: PASS — all rows class_id=AF-WCC-VAC-GEN node_id=F1
  - C2-ROW-BINDING-REV13: PASS — rows not bound to F1 rev13 d9cebb9404b2: none
  - C3-PROBES-84-84-AT-REV13: PASS — probes=84, measured-fail=0 []
  - C6-EXCERPT-FIDELITY-REV13: FAIL — recorded excerpts not a truncation-tolerant match of rev13: 2 [{'test_id': 'F1-AMB-09', 'path': 'genericity.ambient_space', 'recorded': '"the constraint manifold X^{s,delta}_vac(AF) of one-ended asymptotically flat VACUUM initial data in the declared regula'}, {'test_id': 'F1-AMB-21', 'path': 'f0_binding.declared_f0_sha256', 'recorded': '"276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"'}]
  - C4-PROBE-IDENTITY: PASS — probe path/kind/role changes: 0 []
  - C4b-EXPECTATION-CHANGE-SCOPE: PASS — 2 expectation change(s), all in the two declared L-FORM-04 probes=True
  - C5a-P1-ANCHOR-LIVE-F0: PASS — P1 expected == live F0 rev5 sha256: True (0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3)
  - C5b-P4-ANCHOR-REVISION-SPECIFIC: PASS — P4 anchor len>=20 and present in rev13 note but absent from the authoring-rev11 note: True ('rev13: consistency_evidence_sha256 refreshed to the live taxonomy_consistency.json 9e335e9ba1bf')
  - C7-PROVENANCE-COMPLETE: FAIL — provenance gaps: 48 ['F1-AMB-01: binding_frozen_revision_schema=12', 'F1-AMB-01: rebound_at unchanged', 'F1-AMB-02: binding_frozen_revision_schema=12', 'F1-AMB-02: rebound_at unchanged', 'F1-AMB-03: binding_frozen_revision_schema=12'] (by field: {'binding_frozen_revision_schema!=13': 24, 'binding_frozen_revision<29': 0, 'rebound_at unchanged': 24, 'rebound_at not ISO': 0, 'cross_artifact sha != live F0': 0})
  - C8-HISTORY-PRESERVED: PASS — historical provenance fields rewritten: 0 []
- **cand_w077_mechanical**
  - C1-LOAD-25-ROWS-ORDER: PASS — rows=25, test_id order identical=True
  - C1b-CLASS-BINDING: PASS — all rows class_id=AF-WCC-VAC-GEN node_id=F1
  - C2-ROW-BINDING-REV13: PASS — rows not bound to F1 rev13 d9cebb9404b2: none
  - C3-PROBES-84-84-AT-REV13: FAIL — probes=84, measured-fail=2 [{'test_id': 'F1-AMB-25', 'path': 'f0_binding.declared_f0_sha256', 'kind': 'equals', 'expected': '276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc'}, {'test_id': 'F1-AMB-25', 'path': 'f0_binding.binding_note', 'kind': 'contains', 'expected': 'astra-classscope-02'}]
  - C6-EXCERPT-FIDELITY-REV13: PASS — recorded excerpts not a truncation-tolerant match of rev13: 0 []
  - C4-PROBE-IDENTITY: PASS — probe path/kind/role changes: 0 []
  - C4b-EXPECTATION-CHANGE-SCOPE: PASS — 0 expectation change(s), all in the two declared L-FORM-04 probes=True
  - C5a-P1-ANCHOR-LIVE-F0: FAIL — P1 expected == live F0 rev5 sha256: False (276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc)
  - C5b-P4-ANCHOR-REVISION-SPECIFIC: FAIL — P4 anchor len>=20 and present in rev13 note but absent from the authoring-rev11 note: False ('astra-classscope-02')
  - C7-PROVENANCE-COMPLETE: FAIL — provenance gaps: 51 ['F1-AMB-01: binding_frozen_revision_schema=12', 'F1-AMB-01: rebound_at unchanged', 'F1-AMB-02: binding_frozen_revision_schema=12', 'F1-AMB-02: rebound_at unchanged', 'F1-AMB-03: binding_frozen_revision_schema=12'] (by field: {'binding_frozen_revision_schema!=13': 25, 'binding_frozen_revision<29': 0, 'rebound_at unchanged': 25, 'rebound_at not ISO': 0, 'cross_artifact sha != live F0': 1})
  - C8-HISTORY-PRESERVED: FAIL — historical provenance fields rewritten: 100 [{'test_id': 'F1-AMB-01', 'field': 'binding_at_authoring', 'before': 'schemas/af_wcc_vacuum.yaml#sha256:9a8bd4c9680042a4', 'after': 'schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2e79e'}, {'test_id': 'F1-AMB-01', 'field': 'prior_binding_at_authoring', 'before': 'artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:b65fcc0f0118980f', 'after': 'schemas/af_wcc_vacuum.yaml#sha256:9a8bd4c9680042a4'}, {'test_id': 'F1-AMB-01', 'field': 'prior_binding_ref', 'before': 'schemas/af_wcc_vacuum.yaml#sha256:b65fcc0f0118980f', 'after': 'schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6a907'}, {'test_id': 'F1-AMB-01', 'field': 'prior_binding_sha256', 'before': 'b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94', 'after': 'cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3'}]
- **cand_w077_f0refresh**
  - C1-LOAD-25-ROWS-ORDER: PASS — rows=25, test_id order identical=True
  - C1b-CLASS-BINDING: PASS — all rows class_id=AF-WCC-VAC-GEN node_id=F1
  - C2-ROW-BINDING-REV13: PASS — rows not bound to F1 rev13 d9cebb9404b2: none
  - C3-PROBES-84-84-AT-REV13: PASS — probes=84, measured-fail=0 []
  - C6-EXCERPT-FIDELITY-REV13: PASS — recorded excerpts not a truncation-tolerant match of rev13: 0 []
  - C4-PROBE-IDENTITY: PASS — probe path/kind/role changes: 0 []
  - C4b-EXPECTATION-CHANGE-SCOPE: PASS — 2 expectation change(s), all in the two declared L-FORM-04 probes=True
  - C5a-P1-ANCHOR-LIVE-F0: PASS — P1 expected == live F0 rev5 sha256: True (0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3)
  - C5b-P4-ANCHOR-REVISION-SPECIFIC: PASS — P4 anchor len>=20 and present in rev13 note but absent from the authoring-rev11 note: True ('refreshed to the rev5 declared-F0 hash')
  - C7-PROVENANCE-COMPLETE: FAIL — provenance gaps: 50 ['F1-AMB-01: binding_frozen_revision_schema=12', 'F1-AMB-01: rebound_at unchanged', 'F1-AMB-02: binding_frozen_revision_schema=12', 'F1-AMB-02: rebound_at unchanged', 'F1-AMB-03: binding_frozen_revision_schema=12'] (by field: {'binding_frozen_revision_schema!=13': 25, 'binding_frozen_revision<29': 0, 'rebound_at unchanged': 25, 'rebound_at not ISO': 0, 'cross_artifact sha != live F0': 0})
  - C8-HISTORY-PRESERVED: FAIL — historical provenance fields rewritten: 100 [{'test_id': 'F1-AMB-01', 'field': 'binding_at_authoring', 'before': 'schemas/af_wcc_vacuum.yaml#sha256:9a8bd4c9680042a4', 'after': 'schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2e79e'}, {'test_id': 'F1-AMB-01', 'field': 'prior_binding_at_authoring', 'before': 'artifacts/formulation/schemas/af_wcc_vacuum.yaml#sha256:b65fcc0f0118980f', 'after': 'schemas/af_wcc_vacuum.yaml#sha256:9a8bd4c9680042a4'}, {'test_id': 'F1-AMB-01', 'field': 'prior_binding_ref', 'before': 'schemas/af_wcc_vacuum.yaml#sha256:b65fcc0f0118980f', 'after': 'schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6a907'}, {'test_id': 'F1-AMB-01', 'field': 'prior_binding_sha256', 'before': 'b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94', 'after': 'cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3'}]

## Derived owner write set (no canonical write performed here)

- recommended base: **cand_w031_tierB** (`785e6a4e53d64377`)
- residual excerpt refreshes from **cand_w077_mechanical**: [('F1-AMB-09', 'genericity.ambient_space'), ('F1-AMB-21', 'f0_binding.declared_f0_sha256')]
- provenance fields the owner must still set: `{'binding_frozen_revision_schema!=13': 24, 'binding_frozen_revision<29': 0, 'rebound_at unchanged': 24, 'rebound_at not ISO': 0, 'cross_artifact sha != live F0': 0}`

Policy divergence between the lineages: w077 rewrites binding_at_authoring/prior_binding_* to the new bindings on all 25 rows; w031 preserves the original record. The owner must choose a policy; preserving history and adding a new field is the audit-safe option.

Pairwise divergent JSON pointers between candidate lineages: `{'cand_w031_tierA__vs__cand_w031_tierB': 31, 'cand_w031_tierA__vs__cand_w077_mechanical': 159, 'cand_w031_tierA__vs__cand_w077_f0refresh': 155, 'cand_w031_tierB__vs__cand_w077_mechanical': 137, 'cand_w031_tierB__vs__cand_w077_f0refresh': 133, 'cand_w077_mechanical__vs__cand_w077_f0refresh': 5}`.

Machine-readable detail is in `evidence.json` (`divergent_pointer_table`, per-candidate `checks`, `controls`).

## Falsifier

any pinned input hash moving, any candidate re-measured to a different sha256, a probe whose rev13 evaluation disagrees with this run, or a candidate accepted here that a re-run shows failing C2/C3/C4/C5

## Next falsifier

the owner's applied corpus: re-run this battery on the bytes that actually land in schemas/f1_falsifier_tests.jsonl and on FROZEN rev30's per-file pin; the applied bytes must equal one adjudicated candidate hash

## Scope note

This adjudicates only truthfulness, probe-identity, anchor specificity,
excerpt fidelity and provenance of the staged candidates. It does not choose a
canonical writer and does not apply any patch. If the verdict is
`MULTIPLE_FREEZE_READY_DIVERGENT`, the owner must pick exactly one candidate byte
set before re-freezing; see `evidence.json:divergent_pointer_table`.

