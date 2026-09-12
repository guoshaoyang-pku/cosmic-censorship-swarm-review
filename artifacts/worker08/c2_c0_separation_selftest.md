# FORM-SEP-04 audit self-test (v3)

Generated 2026-09-12T00:23:06+08:00. Two known canonical-C0 baseline defects (legacy H1 converse, rev18 ledger containment inversion) are patched in fixture copies so that each case's own mutation is what is measured; the `canonical` case is left unrepaired and must show the rev18 defect.

- controls pass (no false positives): **yes**
- canonical pair behaves as expected (FAIL on the rev18 ledger defect): **yes**
- in-scope mutant/probe caught: **4** (mutant_m12_composite_regularity, mutant_m27_prose_converse, mutant_m28_prose_converse_follows_from, probe_p03_c2_schema_c0_meaning)
- in-scope mutant/probe missed: **0** (none)
- family-scope probes missed (expected, documented): **2** (probe_p01_scc_schema_wcc_meaning, probe_p05_scc_i_plus_completeness)

| case | kind | verdict | observed | meets expectation |
|---|---|---|---|---|
| canonical_pair | canonical | FAIL | containment_inversion_in_ledger | True |
| repaired_pair | control | PASS | no hard failure | True |
| control_reordered_C2_vs_null_C0 | control | PASS | no hard failure | True |
| control_old_C2_vs_extra_key_C0 | control | PASS | no hard failure | True |
| mutant_m12_composite_regularity | mutant | FAIL | foreign_regularity_unjustified, composite_regularity | True |
| mutant_m27_prose_converse | probe | FAIL | converse_implication_asserted | True |
| mutant_m28_prose_converse_follows_from | probe | FAIL | foreign_regularity_unjustified, converse_implication_asserted | True |
| probe_p03_c2_schema_c0_meaning | probe | FAIL | conclusion_regularity_axis_violation | True |
| probe_p01_scc_schema_wcc_meaning | probe_out_of_scope | PASS | no hard failure | None |
| probe_p05_scc_i_plus_completeness | probe_out_of_scope | PASS | no hard failure | None |

## Residual blind spots

- family leakage (WCC content inside an SCC schema, or I+ completeness in an SCC conclusion) is not detected by this regularity-separation audit; p01/p05 pass and remain the lead gate's / worker-06's responsibility.
- sentence-level lexical scan cannot see a leak expressed without any regularity token in a non-assertive field.
- the audit does not verify that the mathematics inside a definition is correct.
