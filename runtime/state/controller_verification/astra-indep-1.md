# Astra independent lifecycle astra-indep-1

- started 2026-09-11T23:59:33+08:00 / ended 2026-09-12T00:05:49+08:00
- report sha256 `077440ef360478358b080ce9a717bb508e283c2e4304ff54fdf78a0dca3d7ccc`
- map validation **VALID**; evidence audit **0 hard / 7 soft**; lock guard **PASS**
- numerics_lock **locked**; N1 artifact present: False

## DAG repair (CF-7)

- `F2` (merged node -> `schemas/af_scc_regularities.yaml`) split into `F2a` (`schemas/af_scc_c2_vacuum.yaml`) and `F2b` (`schemas/af_scc_c0_vacuum.yaml`).
- `schemas/af_scc_regularities.yaml` retired from service (`active=false`): it is the merged C0/C2 artifact the group direction rejects.

## Gates

- **G-F0** pending (owner lead-formulation, ETA 0.5d, 4 unmet criteria recorded)
- **G-FORM** pending (owner lead-formulation, ETA 1.5d, 5 unmet criteria recorded)
- **G-LIT** pending (owner lead-literature, ETA 1.0d, 5 unmet criteria recorded)
- **G-NUM** pending (owner lead-numerics, ETA 0.5d, 5 unmet criteria recorded)
- **G-AUDIT** pending (owner lead-audit, ETA 1.0d, 4 unmet criteria recorded)

## Validation normalized

- L0: passed -> unverified (3 revise verdicts incl. hard failures, no accept)
- L1: passed -> unverified (citation-integrity review records 4 hard failures)

## Bounded assignments issued

- `astra-indep-1-F1-F2-formulation` -> astra-lead-formulation (node F1,F2a,F2b, gate G-FORM, 8h)
- `astra-indep-1-A1-audit` -> astra-lead-audit (node A1, gate G-AUDIT, 5h)
- `astra-indep-1-L0-L1-literature` -> astra-lead-literature (node L0,L1, gate G-LIT, 6h)
- `astra-indep-1-N0-numerics` -> astra-lead-numerics (node N0, gate G-NUM, 3h)
- `astra-indep-1-CF5-ledger-verify` -> deepseek-flash-19 (node L0, gate G-LIT, 1.5h)

## Outstanding soft warnings

- soft  CLASSSEP-SOFT: unknown class token in F2b artifact schemas/af_scc_c0_vacuum.yaml: 'AF-SCC-L2LOC-VAC-GEN'
- soft  CLASSSEP-SOFT: unknown class token in F2b artifact schemas/af_scc_c0_vacuum.yaml: 'AF-SCC-C0-DISTRIBUTIONAL-VAC'
- soft  CLASSSEP-SOFT: unknown class token in L0 artifact ledger/theorems.jsonl: 'AF-WCC-VAC-BH-FORM'
- soft  dual-tree divergence: research_map/formulation_taxonomy.yaml (66bf917bd368) != artifacts/formulation/formulation_taxonomy.yaml (a7ccffa882eb); publish the frozen revision to the canonical path
- soft  dual-tree divergence: schemas/af_wcc_vacuum.yaml (7a3e1f93f77c) != artifacts/formulation/schemas/af_wcc_vacuum.yaml (f962c117ba11); publish the frozen revision to the canonical path
- soft  dual-tree divergence: schemas/af_scc_c2_vacuum.yaml (23fec0e9cd68) != artifacts/formulation/schemas/af_scc_c2_vacuum.yaml (e9fcefe6e595); publish the frozen revision to the canonical path
- soft  dual-tree divergence: schemas/af_scc_c0_vacuum.yaml (e6b1af2bd692) != artifacts/formulation/schemas/af_scc_c0_vacuum.yaml (bdb23f76b895); publish the frozen revision to the canonical path

## Exit

lifecycle complete: comms consumed, DAG repaired, gates maintained with explicit unmet criteria, bounded assignments issued, hashes/validation/ETA recorded, numerics still locked, checkpoint written. Exiting.
