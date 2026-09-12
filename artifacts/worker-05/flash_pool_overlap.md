# W05-T1 — Flash-pool intent-overlap and assignment-gap snapshot

- **Worker:** deepseek-flash-05 (execution worker (DeepSeek Flash breadth) — artifact-backed support to A1/A2, no node claimed complete)
- **Snapshot:** 2026-09-11T23:19:28+08:00
- **Logs scanned:** 20 (empty: none)
- **Self-test control:** PASS — planted overlap detected; zero-overlap control clean; F10/AAFN0 rejected
- **research_map.json sha256:** `82b96a7d8085d82c95c93a7f82d9ffafa085e20287df536215cb7e0550139d71`
- **ASTRA_HANDOFF.md sha256:** `80568e1f9606973383369949a39b39e0faabb6e23bb13872b86c52a6edbdb7f1`

## Findings

| id | severity | statement | evidence |
|---|---|---|---|
| `no-assignment-channel` | observation | comms/inbox holds 24 file(s) at scan time; the task protocol requires a class-bound lead assignment before execution agents act. | comms/inbox/ (24 files)<br>research_map/ASTRA_HANDOFF.md:47 |
| `no-contract-events` | observation | comms/outbox holds 6 contract event(s) from 20 Flash workers at scan time; no worker output is auditable through the sanctioned channel yet. | comms/outbox/ (6 events)<br>research_map/schemas.py:13 |
| `node-concentration` | hard_failure | highest self-selected node concentration: F1 mentioned by 20 workers (deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20); the map assigns each node to one group, not to a fleet. | runtime/logs/deepseek-flash-01.log:23<br>runtime/logs/deepseek-flash-02.log:41<br>runtime/logs/deepseek-flash-03.log:18<br>runtime/logs/deepseek-flash-04.log:14<br>runtime/logs/deepseek-flash-05.log:22<br>runtime/logs/deepseek-flash-06.log:20<br>… |
| `queue-coverage-gap` | observation | immediate-queue nodes with zero Flash mention: none (queue parsed as ['F1', 'F2', 'L0', 'L1', 'A1', 'N0', 'A2']). | research_map/ASTRA_HANDOFF.md:36-43 |
| `class-binding-unmachine-checkable` | warning | research_map.json carries no structured class_id field on any of its 10 nodes (0 with class_id/class_ids); class IDs exist only inside human-readable node labels, so the validator cannot detect cross-class leakage. | research_map/research_map.json:26-28<br>research_map/validate_map.py:12-40<br>research_map/ARCHITECTURE.md:63 |
| `declared-artifacts-absent` | hard_failure | 10/10 declared node artifacts are absent from disk (including done/passed nodes): {'F0': 'research_map/formulation_taxonomy.yaml', 'F1': 'schemas/af_wcc_vacuum.yaml', 'F2': 'schemas/af_scc_regularities.yaml', 'L0': 'ledger/theorems.jsonl', 'L1': 'ledger/citation_audit.csv', 'N0': 'numerics/tests/flat_wave.py', 'N1': 'numerics/spherical_solver/', 'A0': 'evaluation_rubric.yaml', 'A1': 'reviews/', 'A2': 'evaluation/ablation.csv'}. validate_map.py returns VALID because it never touches the filesystem. | research_map/research_map.json:26-56<br>research_map/validate_map.py:23-26 |

## Node concentration (worker mentions, primary metric)

| node | group | workers | worker list |
|---|---|---:|---|
| A1 | audit | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| A2 | audit | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| F1 | formulation | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| F2 | formulation | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| L0 | literature | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| L1 | literature | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| N0 | numerics | 20 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| F0 | formulation | 19 | deepseek-flash-01, deepseek-flash-02, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| A0 | audit | 18 | deepseek-flash-01, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-07, deepseek-flash-08, deepseek-flash-09, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| N1 | numerics | 13 | deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-08, deepseek-flash-09, deepseek-flash-11, deepseek-flash-14, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |

## Duplicated artifact paths (secondary)

| path | workers |
|---|---:|
| `schemas/af_wcc_vacuum.yaml` | 17 — deepseek-flash-01, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-08, deepseek-flash-10, deepseek-flash-11, deepseek-flash-12, deepseek-flash-13, deepseek-flash-14, deepseek-flash-15, deepseek-flash-16, deepseek-flash-17, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| `ledger/theorems.jsonl` | 13 — deepseek-flash-01, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-06, deepseek-flash-08, deepseek-flash-09, deepseek-flash-10, deepseek-flash-15, deepseek-flash-16, deepseek-flash-18, deepseek-flash-19, deepseek-flash-20 |
| `numerics/tests/flat_wave.py` | 10 — deepseek-flash-01, deepseek-flash-03, deepseek-flash-04, deepseek-flash-05, deepseek-flash-08, deepseek-flash-09, deepseek-flash-11, deepseek-flash-12, deepseek-flash-18, deepseek-flash-20 |
| `artifacts/worker-01/artifact_integrity_recon.json` | 7 — deepseek-flash-01, deepseek-flash-07, deepseek-flash-09, deepseek-flash-10, deepseek-flash-14, deepseek-flash-16, deepseek-flash-17 |
| `artifacts/audit` | 6 — deepseek-flash-01, deepseek-flash-03, deepseek-flash-05, deepseek-flash-07, deepseek-flash-13, deepseek-flash-19 |
| `schemas/af_scc_regularities.yaml` | 6 — deepseek-flash-05, deepseek-flash-06, deepseek-flash-08, deepseek-flash-09, deepseek-flash-12, deepseek-flash-16 |
| `artifacts/worker-06/class_binding_rules.json` | 5 — deepseek-flash-06, deepseek-flash-10, deepseek-flash-12, deepseek-flash-16, deepseek-flash-18 |
| `evaluation/ablation.csv` | 5 — deepseek-flash-05, deepseek-flash-08, deepseek-flash-09, deepseek-flash-16, deepseek-flash-19 |
| `ledger/citation_audit.csv` | 5 — deepseek-flash-03, deepseek-flash-05, deepseek-flash-07, deepseek-flash-08, deepseek-flash-15 |
| `artifacts/flash-03` | 4 — deepseek-flash-03, deepseek-flash-06, deepseek-flash-12, deepseek-flash-16 |
| `artifacts/formulation` | 4 — deepseek-flash-10, deepseek-flash-12, deepseek-flash-13, deepseek-flash-19 |
| `artifacts/worker-01` | 4 — deepseek-flash-01, deepseek-flash-05, deepseek-flash-06, deepseek-flash-16 |
| `artifacts/flash-03/CHECKPOINTS.md` | 3 — deepseek-flash-03, deepseek-flash-07, deepseek-flash-10 |
| `artifacts/flash-11/f1_aux_class_binding/check_schema.py` | 3 — deepseek-flash-10, deepseek-flash-12, deepseek-flash-18 |
| `artifacts/flash-13/f1_gate/check_schema.py` | 3 — deepseek-flash-10, deepseek-flash-13, deepseek-flash-18 |
| `artifacts/formulation/evidence/map_artifact_audit.txt` | 3 — deepseek-flash-12, deepseek-flash-16, deepseek-flash-18 |
| `artifacts/literature` | 3 — deepseek-flash-05, deepseek-flash-18, deepseek-flash-19 |
| `artifacts/worker-05/proposal_W05-T1_flash_pool_overlap.md` | 3 — deepseek-flash-05, deepseek-flash-10, deepseek-flash-18 |
| `artifacts/worker08` | 3 — deepseek-flash-05, deepseek-flash-08, deepseek-flash-16 |
| `artifacts/worker08/proposal_E08_F2a.md` | 3 — deepseek-flash-08, deepseek-flash-10, deepseek-flash-18 |
| `numerics/spherical_solver` | 3 — deepseek-flash-08, deepseek-flash-16, deepseek-flash-19 |
| `artifacts/audit/artifact_provenance_report.json` | 2 — deepseek-flash-05, deepseek-flash-19 |
| `artifacts/audit/evaluation_rubric.yaml` | 2 — deepseek-flash-10, deepseek-flash-18 |
| `artifacts/flash-02/af_wcc_scalar_sph_anchor.json` | 2 — deepseek-flash-02, deepseek-flash-20 |
| `artifacts/flash-02/sources` | 2 — deepseek-flash-02, deepseek-flash-10 |
| `artifacts/flash-04` | 2 — deepseek-flash-04, deepseek-flash-05 |
| `artifacts/flash-04/n0_acceptance` | 2 — deepseek-flash-04, deepseek-flash-10 |
| `artifacts/flash-04/n0_acceptance/harness.py` | 2 — deepseek-flash-04, deepseek-flash-20 |
| `artifacts/flash-04/n0_acceptance/reference_solutions.py` | 2 — deepseek-flash-04, deepseek-flash-18 |
| `artifacts/flash-11` | 2 — deepseek-flash-11, deepseek-flash-12 |
| `artifacts/flash-11/f1_aux_class_binding` | 2 — deepseek-flash-10, deepseek-flash-11 |
| `artifacts/flash-15` | 2 — deepseek-flash-15, deepseek-flash-16 |
| `artifacts/flash-15/PROPOSAL.md` | 2 — deepseek-flash-10, deepseek-flash-18 |
| `artifacts/flash-15/l1_breadth` | 2 — deepseek-flash-10, deepseek-flash-15 |
| `artifacts/formulation/assignments` | 2 — deepseek-flash-09, deepseek-flash-10 |
| `artifacts/formulation/class_binding_checklist.yaml` | 2 — deepseek-flash-05, deepseek-flash-19 |
| `artifacts/numerics` | 2 — deepseek-flash-05, deepseek-flash-19 |
| `artifacts/proposals` | 2 — deepseek-flash-16, deepseek-flash-18 |
| `artifacts/w06` | 2 — deepseek-flash-05, deepseek-flash-06 |
| `artifacts/worker08/check_map_artifacts.py` | 2 — deepseek-flash-07, deepseek-flash-08 |
| `artifacts/worker08/preflight_F0_A0_artifact_audit.json` | 2 — deepseek-flash-05, deepseek-flash-08 |
| `artifacts/worker08/proposal_E08_F2a.json` | 2 — deepseek-flash-08, deepseek-flash-10 |
| `artifacts/worker18` | 2 — deepseek-flash-18, deepseek-flash-20 |
| `artifacts/worker18/n0_gate` | 2 — deepseek-flash-18, deepseek-flash-20 |
| `artifacts/worker18/n0_gate/n0_gate.py` | 2 — deepseek-flash-18, deepseek-flash-20 |
| `schemas/af_wcc_vacuum_draft_flash17.yaml` | 2 — deepseek-flash-05, deepseek-flash-17 |

## Channel state

- comms/inbox files: ['astra-lead-audit.jsonl', 'astra-lead-formulation.jsonl', 'astra-lead-literature.jsonl', 'astra-lead-numerics.jsonl', 'deepseek-flash-01.jsonl', 'deepseek-flash-02.jsonl', 'deepseek-flash-03.jsonl', 'deepseek-flash-04.jsonl', 'deepseek-flash-05.jsonl', 'deepseek-flash-06.jsonl', 'deepseek-flash-07.jsonl', 'deepseek-flash-08.jsonl', 'deepseek-flash-09.jsonl', 'deepseek-flash-10.jsonl', 'deepseek-flash-11.jsonl', 'deepseek-flash-12.jsonl', 'deepseek-flash-13.jsonl', 'deepseek-flash-14.jsonl', 'deepseek-flash-15.jsonl', 'deepseek-flash-16.jsonl', 'deepseek-flash-17.jsonl', 'deepseek-flash-18.jsonl', 'deepseek-flash-19.jsonl', 'deepseek-flash-20.jsonl']
- comms/outbox files: ['deepseek-flash-01.jsonl', 'deepseek-flash-12.jsonl', 'e08_artifact_map_gate.event.json', 'e08_blocker_f0_a0.msg.json', 'e08_claim_f2a.event.json', 'e08_resource_request_f2a.event.json', 'e08_status.msg.json', 'flash-15-status.jsonl', 'flash-17_20260911T231840_status.json', 'worker-06.jsonl']
- contract events parsed: [{'file': 'e08_artifact_map_gate.event.json', 'event_type': 'artifact', 'actor': 'deepseek-flash-08'}, {'file': 'e08_resource_request_f2a.event.json', 'event_type': 'resource_request', 'actor': 'deepseek-flash-08'}, {'file': 'e08_status.msg.json', 'event_type': 'status', 'actor': 'deepseek-flash-08'}, {'file': 'flash-17_20260911T231840_status.json', 'event_type': 'status', 'actor': 'flash-17'}, {'file': 'e08_blocker_f0_a0.msg.json', 'event_type': 'blocker', 'actor': 'deepseek-flash-08'}, {'file': 'e08_claim_f2a.event.json', 'event_type': 'claim', 'actor': 'deepseek-flash-08'}]
- zero-coverage queue nodes: none
- unclaimed map nodes: none
- nodes with structured class_id: NONE

## Declared artifacts vs disk

| node | group | declared path | exists |
|---|---|---|---|
| F0 | formulation | `research_map/formulation_taxonomy.yaml` | **NO** |
| F1 | formulation | `schemas/af_wcc_vacuum.yaml` | **NO** |
| F2 | formulation | `schemas/af_scc_regularities.yaml` | **NO** |
| L0 | literature | `ledger/theorems.jsonl` | **NO** |
| L1 | literature | `ledger/citation_audit.csv` | **NO** |
| N0 | numerics | `numerics/tests/flat_wave.py` | **NO** |
| N1 | numerics | `numerics/spherical_solver/` | **NO** |
| A0 | audit | `evaluation_rubric.yaml` | **NO** |
| A1 | audit | `reviews/` | **NO** |
| A2 | audit | `evaluation/ablation.csv` | **NO** |

## Per-worker snapshot

| worker | lines | sha256 (first 12) | primary node | nodes mentioned | classes | intended paths |
|---|---:|---|---|---|---|---|
| deepseek-flash-01 | 522 | `94f6b11f0017` | A1 | A0×15, A1×49, A2×5, F0×34, F1×44, F2×12, L0×8, L1×7, N0×9 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit`, `artifacts/schemas`, `artifacts/worker-01`, `artifacts/worker-01/a1_metrics_probe.py` (+15) |
| deepseek-flash-02 | 430 | `87e25a240fd5` | F1 | A1×5, A2×4, F0×11, F1×41, F2×25, L0×15, L1×13, N0×7 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-02`, `artifacts/flash-02/ANCHOR_REPORT.md`, `artifacts/flash-02/CHECKPOINT.md`, `artifacts/flash-02/af_wcc_scalar_sph_anchor.json` (+7) |
| deepseek-flash-03 | 493 | `acd747a57e97` | F0 | A0×12, A1×7, A2×5, F0×43, F1×18, F2×6, L0×12, L1×20, N0×33, N1×3 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/E3-T1_flat_wave_evidence.json`, `artifacts/audit`, `artifacts/e3`, `artifacts/flash-03` (+10) |
| deepseek-flash-04 | 975 | `6448a6ca3d9d` | N0 | A0×7, A1×17, A2×3, F0×20, F1×12, F2×6, L0×8, L1×5, N0×57, N1×3 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-04`, `artifacts/flash-04/n0_acceptance`, `artifacts/flash-04/n0_acceptance/external_echo_solver.py`, `artifacts/flash-04/n0_acceptance/harness.py` (+10) |
| deepseek-flash-05 | 565 | `2d9badef8366` | F1 | A0×14, A1×54, A2×23, F0×44, F1×56, F2×17, L0×21, L1×12, N0×40, N1×5 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit`, `artifacts/audit/artifact_provenance_report.json`, `artifacts/audit/flash_pool_intent_overlap.json`, `artifacts/flash-04` (+27) |
| deepseek-flash-06 | 628 | `7dd294d04c0a` | F1 | A0×6, A1×23, A2×4, F0×20, F1×52, F2×39, L0×5, L1×4, N0×6, N1×1 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-03`, `artifacts/w06`, `artifacts/w06/README.md`, `artifacts/w06/check_class_binding.py` (+19) |
| deepseek-flash-07 | 653 | `b25aebe25281` | F2 | A0×10, A1×39, A2×7, F0×35, F1×37, F2×48, L0×9, L1×8, N0×7 | AF-SCC-C0-VAC-GEN, AF-SCC-C02-VAC-GEN, AF-SCC-C0C2-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C2-VAC-GEN-EXTRA, AF-SCC-REG-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit`, `artifacts/audit/class_binding_linter.py`, `artifacts/audit/class_binding_linter_report.json`, `artifacts/audit/class_binding_linter_report.md` (+12) |
| deepseek-flash-08 | 625 | `ae543328ae18` | F0 | A0×31, A1×16, A2×7, F0×79, F1×63, F2×62, L0×9, L1×18, N0×6, N1×1 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/evidence`, `artifacts/worker08`, `artifacts/worker08/check_artifacts.py`, `artifacts/worker08/check_map_artifacts.py` (+17) |
| deepseek-flash-09 | 367 | `876f5235e1ca` | F2 | A0×3, A1×26, A2×21, F0×9, F1×38, F2×45, L0×19, L1×19, N0×19, N1×1 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-09`, `artifacts/flash-09/af_scc_c2_c0_sources.yaml`, `artifacts/flash-09/check_class_separation.py`, `artifacts/formulation/assignments` (+17) |
| deepseek-flash-10 | 447 | `93bedf9b7788` | F1 | A1×5, A2×3, F1×38, F2×32, L0×7, L1×12, N0×3 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit/evaluation_rubric.yaml`, `artifacts/flash-02/sources`, `artifacts/flash-02/sources/christodoulou1999.pdf`, `artifacts/flash-03/CHECKPOINTS.md` (+24) |
| deepseek-flash-11 | 578 | `b4b8f8656fc5` | F0 | A0×7, A1×19, A2×1, F0×26, F1×21, F2×7, L0×2, L1×1, N0×7, N1×1 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN, AF-WCC-VAC-GEN-EXTRA | `artifacts/flash-11`, `artifacts/flash-11/class_binding`, `artifacts/flash-11/f1_aux_class_binding`, `artifacts/flash-11/f1_aux_class_binding/evidence` (+2) |
| deepseek-flash-12 | 692 | `5ccbe5086b44` | F2 | A0×4, A1×10, A2×4, F0×30, F1×28, F2×99, L0×4, L1×9, N0×8 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-03`, `artifacts/flash-11`, `artifacts/flash-11/f1_aux_class_binding/check_schema.py`, `artifacts/flash-12/CHECKPOINTS.md` (+19) |
| deepseek-flash-13 | 661 | `e8bf3f1972e3` | F1 | A0×4, A1×10, A2×3, F0×21, F1×55, F2×3, L0×5, L1×8, N0×7 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit`, `artifacts/flash-13`, `artifacts/flash-13/CHECKPOINT.md`, `artifacts/flash-13/PROPOSAL-wp-f1-schema-gate.yaml` (+9) |
| deepseek-flash-14 | 454 | `f32a3e033e37` | F1 | A0×9, A1×42, A2×7, F0×17, F1×52, F2×33, L0×7, L1×11, N0×6, N1×1 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/w14`, `artifacts/w14/class_binding_checker.py`, `artifacts/w14/fixtures`, `artifacts/w14/proposed_task.md` (+5) |
| deepseek-flash-15 | 548 | `e337b431e22b` | L1 | A0×2, A1×7, A2×8, F0×8, F1×15, F2×13, L0×12, L1×35, N0×8 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-15`, `artifacts/flash-15/checkpoints`, `artifacts/flash-15/l1_breadth`, `artifacts/flash-15/l1_breadth/README.md` (+7) |
| deepseek-flash-16 | 694 | `fe9020ca97e4` | A1 | A0×12, A1×45, A2×19, F0×26, F1×39, F2×34, L0×12, L1×16, N0×10, N1×7 | AF-SCC-C0-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C2-VAC-GEN-TYPO, AF-SCC-C2-VAC-GEN-X, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-03`, `artifacts/flash-15`, `artifacts/formulation/evidence/map_artifact_audit.txt`, `artifacts/proposals` (+33) |
| deepseek-flash-17 | 1311 | `87de3c0e4ddc` | F1 | A0×16, A1×15, A2×6, F0×32, F1×66, F2×39, L0×15, L1×9, N0×16, N1×2 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit/flash17_node_evidence_audit.json`, `artifacts/formulation/flash17`, `artifacts/formulation/flash17/PROPOSAL.md`, `artifacts/formulation/flash17/af_wcc_vacuum_gate.py` (+16) |
| deepseek-flash-18 | 554 | `c554796fa04d` | N0 | A0×4, A1×45, A2×7, F0×30, F1×39, F2×30, L0×21, L1×12, N0×67, N1×8 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit/class_leakage_lint.py`, `artifacts/audit/evaluation_rubric.yaml`, `artifacts/audit/map_artifact_integrity.json`, `artifacts/flash-04/n0_acceptance/reference_solutions.py` (+30) |
| deepseek-flash-19 | 512 | `ae786b43451e` | F0 | A0×18, A1×29, A2×7, F0×92, F1×79, F2×27, L0×18, L1×7, N0×12, N1×8 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/audit`, `artifacts/audit/README.md`, `artifacts/audit/T19-01_proposal.json`, `artifacts/audit/artifact_provenance_report.json` (+23) |
| deepseek-flash-20 | 668 | `caf660334a6a` | N0 | A0×9, A1×6, A2×3, F0×28, F1×15, F2×9, L0×6, L1×6, N0×95, N1×2 | AF-SCC-C0-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-WCC-SCALAR-SPH, AF-WCC-VAC-GEN | `artifacts/flash-02/af_wcc_scalar_sph_anchor.json`, `artifacts/flash-04/n0_acceptance/harness.py`, `artifacts/numerics/N0_flat_wave_convergence.json`, `artifacts/worker18` (+16) |

## Limitations

- Logs capture reasoning-in-progress, not final actions; mentions are intents, not assignments or deliverables.
- Snapshot is frozen at generated_at with per-log SHA256; a later re-run with different hashes invalidates direct comparison.
- Only deepseek-flash-*.log is scanned; group-lead (astra-*) logs are excluded by design.
- Primary-node attribution is a mention-count heuristic and is flagged when ties occur.
- Presence of a file at a mentioned path is NOT verified here; declared-artifact existence is checked only against the map.

## Next falsifier

Post explicit lead assignments in comms/outbox and re-scan: if node concentration collapses to assigned owners and zero_coverage_queue_nodes becomes empty while outbox_events > 0, the duplication/assignment-gap finding is refuted for that window.
