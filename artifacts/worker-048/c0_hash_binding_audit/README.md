# W48-C0-BIND-01 - C0 hash-binding snapshot audit

- worker: `worker-048`  class: `AF-SCC-C0-VAC-GEN` (node F2b)  snapshot_at: `2026-09-12T00:22:42+08:00`
- verdict: **BINDING_DEFECT_PRESENT_AT_SNAPSHOT**  controls: **PASS**
- bindings: 16 (aligned 16, drifted 0, missing 0)
- checks failed: ['B7::schema-class-contract-pointer-resolves-in-canonical', 'B7::canonical-and-authoring-taxonomy-byte-identical', 'B7::c0-contract-equivalent-across-trees']
- C0 variant refs unresolved: 0/14
- report sha256: `f4e2070be0a9b393769147ae9a28525bb63e2bd24c773683912b2a56dbb5b659`
- script sha256: `3e2f27cbdb691d5c028bd9229615a479dbde793be1c3e8d24cfb22815a7a9106`

## Drifted bindings

- none at snapshot

## Failed checks

- `B7::schema-class-contract-pointer-resolves-in-canonical`: pointer anchor class_contracts.AF-SCC-C0-VAC-GEN vs canonical research_map/formulation_taxonomy.yaml: anchor segment 'class_contracts' not found; canonical exposes the class under classes.AF-SCC-C0-VAC-GEN (present=True)
- `B7::canonical-and-authoring-taxonomy-byte-identical`: research_map/formulation_taxonomy.yaml 276009f4f63d vs artifacts/formulation/formulation_taxonomy.yaml c8e979a1eb48 (controller canonical-path policy requires byte-identical publication before verdicts bind)
- `B7::c0-contract-equivalent-across-trees`: canonical classes.AF-SCC-C0-VAC-GEN keys=['axes', 'conclusion', 'exclusions', 'genericity_value_status', 'hypotheses', 'known_obstruction', 'label', 'provenance', 'test_cases']; authoring class_contracts.AF-SCC-C0-VAC-GEN keys=['ambient_theory', 'class_identity_variants', 'components', 'conclusion_predicate', 'conclusion_type', 'data_class_freeze', 'exclusions', 'hypotheses', 'negative_test_case', 'node_id', 'non_goals', 'positive_test_case']; unified-diff lines=134

## Reproduce

```bash
python3 artifacts/worker-048/c0_hash_binding_audit/audit_c0_bindings.py
```

Read-only over audited paths; a later write by the lead does not falsify the snapshot.
