# Audit tick 20260912T001816

- elapsed since swarm start: 3785.7s
- map sha256: `4d8291c9a9ae44558a4dea49106b525ed7b5c8a2b25cc003a5a754ddb3507306`
- rubric sha256: `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885`
- corpus: {'files': 770, 'claims': 53, 'artifacts': 580, 'citations': 218, 'results': 0, 'records': 250}
- violations: 20 (critical 9) {'HF-02': 8, 'HF-06': 1, 'HF-13': 9, 'HF-03': 1, 'HF-14': 1}
- citations: n=218 score=0.6078 unresolved=4
- duplication: n=45 cluster_rate=0.1333 mean_novelty=0.7904555555555555
- gates: {'G-FORM': 'pending', 'G-LIT': 'fail', 'G-AUDIT': 'fail', 'G-NUM': 'pending'}

## Violations
- **HF-02** (critical) `flash02-rebind-claim-0006-20260912T0010`: class_id 'AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH' is not in the frozen class registry
- **HF-02** (critical) `flash02-opencase-claim-0010b-20260912T0015`: class_id 'AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH' is not in the frozen class registry
- **HF-02** (critical) `w07-hf01-claim-repair-20260912T0018`: class_id 'AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH' is not in the frozen class registry
- **HF-06** (major) `lit-20260911-016`: statement uses a smallness/nearness hypothesis absent from assumptions
- **HF-02** (critical) `w03-20260912T000930-claim-binding`: statement mentions a second frozen class AF-SCC-C2-VAC-GEN
- **HF-02** (critical) `w03-20260912T000930-claim-binding`: statement mentions a second frozen class AF-SCC-C0-VAC-GEN
- **HF-02** (critical) `ledger:class-token`: invented class token 'AF-SCC-OTHER-MODELS' used by 6 ledger entries: not in the frozen taxonomy; open a class via direction_update or re-label as an evidence family
- **HF-02** (critical) `ledger:class-token`: invented class token 'AF-WCC-VAC-BH-FORM' used by 2 ledger entries: not in the frozen taxonomy; open a class via direction_update or re-label as an evidence family
- **HF-02** (critical) `ledger:class-token`: invented class token 'AF-WCC-VAC-NS-CONSTR' used by 4 ledger entries: not in the frozen taxonomy; open a class via direction_update or re-label as an evidence family
- **HF-13** (minor) `artifacts/flash-04/n0_acceptance/SPEC.md`: base-project token 'funsearch' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/flash-11/f1_aux_class_binding/corpus/w06/neg10_cross_domain_contamination.json`: base-project token 'cubic graph' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/flash-11/f1_aux_class_binding/corpus/w06/neg10_cross_domain_contamination.json`: base-project token 'minimum degree' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/worker-06/fixtures/neg10_cross_domain_contamination.json`: base-project token 'cubic graph' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/worker-06/fixtures/neg10_cross_domain_contamination.json`: base-project token 'minimum degree' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/worker-06/make_fixtures.py`: base-project token 'cubic graph' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/worker-16/a0_rubric/evaluation_rubric.extended.yaml`: base-project token 'cubic graph' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/worker-16/a0_rubric/evaluation_rubric.extended.yaml`: base-project token 'minimum degree' inside a cosmic-censorship artifact
- **HF-13** (minor) `artifacts/worker-16/a0_rubric/evaluation_rubric.extended.yaml`: base-project token 'cap set' inside a cosmic-censorship artifact
- **HF-03** (major) `HF-03:systemic`: 218 affected records across 15 ledger files (artifacts/literature/archive/batch-10.pre-L2-20260912T000752.jsonl, artifacts/literature/incoming/w07-sources.jsonl, artifacts/literature/registry.jsonl, artifacts/literature/sources/batch-01.jsonl, artifacts/literature/sources/batch-02.jsonl...)
- **HF-14** (critical) `HF-14:systemic`: 226 affected records across 14 ledger files (artifacts/literature/archive/batch-01.pre-L2-20260912T000830.jsonl, artifacts/literature/incoming/w07-theorems.jsonl, artifacts/literature/theorems/batch-01.jsonl, artifacts/literature/theorems/batch-02.jsonl, artifacts/literature/theorems/batch-03.jsonl...)
