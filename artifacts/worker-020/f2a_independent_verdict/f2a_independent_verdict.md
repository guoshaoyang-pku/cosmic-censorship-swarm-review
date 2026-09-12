# W020 / F2a independent verdict — revise (score 2)

- worker: `worker-020`; node `F2a`; class `AF-SCC-C2-VAC-GEN`
- frozen target: `schemas/af_scc_c2_vacuum.yaml` sha256 `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
- snapshot: `artifacts/worker-020/f2a_independent_verdict/snapshots/f2a_b6123750b37d.yaml`
- T1 re-measure: `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` (changed=False)
- declared-F0: `276009f4f63d` vs measured canonical `276009f4f63d` (authoring `c8e979a1eb48`, divergent=True)
- canonical gate `000e09e46b2f`: exit 0 verdict pass failed_rules []
- class-separation `c266dbceca87`: hard=0 soft=0; detector regression PASS
- rationale: hard failure(s) on the frozen snapshot: C15

## Hard failures

- `C15` (F0 contract-pointer resolvability): class_contract_pointer fragment 'class_contracts.AF-SCC-C2-VAC-GEN' resolves in declared canonical F0 276009f4f63d: False; resolves in authoring tree c8e979a1eb48: True. Canonical top-level keys=['artifact_type', 'authored_by', 'authored_role', 'claims_theorem_status', 'class_ids', 'class_scope_adjudication', 'classes', 'coverage_gaps', 'created_at', 'disjointness', 'disjointness_overlap_note', 'disjointness_scope', 'field_vocabulary', 'gate', 'guards', 'node_id', 'open_questions', 'provenance', 'reconstruction_note', 'revision', 'revision_note', 'revision_note_rev3', 'revision_note_rev4', 'schema_version', 'scope_statement', 'status', 'timestamp_provenance', 'transfer_rules', 'variants', 'written_at']

## Non-passing checks

- `C13` (canonical-path policy): class_contract_pointer='artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN' (canonical path expected; authoring tree is not authoritative)
- `C14` (schema hygiene): duplicate YAML mapping keys: [{'key': 'revised_at', 'line': 10}, {'key': 'revised_at', 'line': 12}, {'key': 'revised_at', 'line': 14}, {'key': 'revised_at', 'line': 16}, {'key': 'revised_at', 'line': 18}, {'key': 'revised_at', 'line': 21}, {'key': 'revised_at', 'line': 23}]
- `C15` (F0 contract-pointer resolvability): class_contract_pointer fragment 'class_contracts.AF-SCC-C2-VAC-GEN' resolves in declared canonical F0 276009f4f63d: False; resolves in authoring tree c8e979a1eb48: True. Canonical top-level keys=['artifact_type', 'authored_by', 'authored_role', 'claims_theorem_status', 'class_ids', 'class_scope_adjudication', 'classes', 'coverage_gaps', 'created_at', 'disjointness', 'disjointness_overlap_note', 'disjointness_scope', 'field_vocabulary', 'gate', 'guards', 'node_id', 'open_questions', 'provenance', 'reconstruction_note', 'revision', 'revision_note', 'revision_note_rev3', 'revision_note_rev4', 'schema_version', 'scope_statement', 'status', 'timestamp_provenance', 'transfer_rules', 'variants', 'written_at']
- `C16` (consistency-evidence hash binding): consistency_evidence 'artifacts/formulation/evidence/taxonomy_consistency.json' exists=True, records an input sha256 matching the measured canonical/authoring hashes=False
- `C17` (canonical publication): F0 canonical 276009f4f63d vs authoring c8e979a1eb48: divergent=True

evidence sha256: `90e9d26e8142df756a906abde86e74b4fd079b5930f4bad21c5948c31f55a321`

