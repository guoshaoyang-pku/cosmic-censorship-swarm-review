# W020-F2A-REV12-CLOSURE-01 — closure receipt

- class: `AF-SCC-C2-VAC-GEN`  node: `F2a`  gate: `G-FORM`
- reviewed pin: `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce`
- declared canonical F0 pin: `research_map/formulation_taxonomy.yaml#0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
- prior blocker: `w020-20260912T0024-f2a-blocker` / finding `C15` at `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
- closure result: **C15_CLOSED_NO_NEW_OWNED_HARD_FINDING**
- hard checks failed: none
- instrument: `verify_c15_closure.py` (self-contained, no canonical imports)

## Closure delta (before -> after)

- rev11 `b6123750b37d`: pointer = `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN`; resolves in old canonical F0 `276009f4f63d` = `False`; duplicate keys = `['/revised_at x2', '/revised_at x3', '/revised_at x4', '/revised_at x5', '/revised_at x6', '/revised_at x7', '/revised_at x8']`
- rev12 `5476a3f2c6bc`: pointer = `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN`; resolves in canonical F0 `0abb9ed8a961` = `True`

## Checks

- `C01` [PASS] strict YAML: F2a rev12 has no duplicate mapping keys
- `C02` [PASS] identity: class_id/node_id match the reviewed target
- `C03` [PASS] class_contract_pointer resolves in the DECLARED CANONICAL F0 (research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN)
- `C04` [PASS] canonical F0 exposes class content under `classes` and has no `class_contracts` key (the shape of the rev11 defect)
- `C05` [PASS] class_contract_supplement_pointer resolves in the COMPANION supplement (artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C2-VAC-GEN)
- `C06` [PASS] f0_binding.declared_f0_sha256 equals the measured canonical F0 rev5 hash
- `C07` [PASS] f0_binding.declared_f0_artifact is the canonical taxonomy path
- `C08` [PASS] both declared pointers name the artifacts declared in f0_binding
- `C09` [PASS] canonical classes.<id> and supplement class_contracts.<id> denote the same C2 class contract on the fixed comparison fields (alias-normalized conclusion_type, class-identity axes, components, comeager quantifier, mutual C0 exclusion)
- `C10` [PASS] prior finding C15 is CLOSED at the rev12 pin: pointer now resolves in the declared canonical F0, supplement pointer resolves in the companion, and the declared F0 hash equals the measured one
- `C11` [OBSERVED-FAIL] (exact-observation check; expected `FAIL`; informational, not a closure failure) inherited cross-cutting item: f0_binding.consistency_evidence_sha256 resolves at the declared path (family-wide rev12 defect, not owned by this task; reported as observation)
- `C12` [PASS] drift window: every reviewed canonical path measured equal to its pin at the start, middle and end of the run

## Controls (planted defects)

- `K1_duplicate_key_detector`: expected `['/a x2', '/b/c x2']` observed `['/a x2', '/b/c x2']` fires=True
- `K2_pointer_retarget_fails_resolution`: expected `False` observed `False` fires=True
- `K3_missing_supplement_key_fails_resolution`: expected `False` observed `False` fires=True
- `K4_hash_flip_detected`: expected `False` observed `False` fires=True
- `K5_alias_normalization_discriminates`: expected `UNMAPPED` observed `UNMAPPED` fires=True

## Residual findings

- `HF-020-R12-1` (hard-cross-cutting-inherited): schemas/af_scc_c2_vacuum.yaml f0_binding.consistency_evidence_sha256 declares 675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48, but the file at the declared path measures 9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b. Independently re-measured here; the disposition/repair is already tracked by worker-086/092/045/078/041/005 and is not re-filed as a new blocker.

## Scope / non-claims

- This is a worker-level closure receipt, not a gate verdict, not a node completion, and not a mathematical theorem.
- No canonical artifact was edited; all writes are under `artifacts/worker-020/f2a_rev12_closure/`.
- The cross-cutting consistency-evidence mismatch is re-measured but not re-filed; it is already tracked by the fleet.
