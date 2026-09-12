# GFORM-XDATA-057 — cross-schema check (worker-057)

Gate: **G-FORM** · nodes F1/F2a/F2b · classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN

Measured inputs (canonical paths):

- `schemas/af_wcc_vacuum.yaml#9a8bd4c96800` (rev 11, 33642 bytes, mtime 2026-09-12T00:19:14+08:00)
- `schemas/af_scc_c2_vacuum.yaml#b6123750b37d` (rev 11, 28268 bytes, mtime 2026-09-12T00:19:14+08:00)
- `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357` (rev 11, 33276 bytes, mtime 2026-09-12T00:19:14+08:00)

## A. Shared data class

- verdict: **shared_core_tuple_modulo_annotations** (10/11 core fields byte-identical, 11/11 equal after annotation normalization, 0 material differences)
  - annotation-only: `data_class.regularity_class.sobolev_variant.spaces`
- transfer-license condition: **condition_met_modulo_annotations**

## B. Hard-failure probes at these hashes

- **HF-A1** (dangling internal/reference pointers (was: extension_predicate)): `clear`
- **HF-A2** (quantifier-order match between quantifiers.ordered and conclusion.statement_formal): `abbreviation_observed`
- **HF-B1** (composite C0/C2 class mention in a declaration surface (was: composite-regularity exemption)): `clear`
- **HF-B1b** (regularity bullet denying containment vs implication_ledger asserting it): `fires`
    - schemas/af_scc_c0_vacuum.yaml:157 denies ('H2_loc (locally square-integrable curvature) is a distinct regularity-axis value phrased in terms of CURVATURE') while schemas/af_scc_c0_vacuum.yaml:244 asserts ('E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; this class requires the LOWEST regularity, so its inex')
- **HF-B2** (node_id / class_id / filename binding (was: F2b node_id mismatch)): `clear`
    - schemas/af_wcc_vacuum.yaml: node_id='F1' class_id='AF-WCC-VAC-GEN'
    - schemas/af_scc_c2_vacuum.yaml: node_id='F2a' class_id='AF-SCC-C2-VAC-GEN'
    - schemas/af_scc_c0_vacuum.yaml: node_id='F2b' class_id='AF-SCC-C0-VAC-GEN'
- **SINGLE-CLASS-ONLY** (one class per schema; no composite C0/C2 declaration): `clear`
- **REVIEW-BINDING** (review verdict availability at the measured canonical hashes): `informational`

## C. Review binding

- `schemas/af_wcc_vacuum.yaml#9a8bd4c96800`: verdict=pending, independent_reviewers=0, gate=G-FORM
- `schemas/af_scc_c2_vacuum.yaml#b6123750b37d`: verdict=pending, independent_reviewers=0, gate=G-FORM
- `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357`: verdict=pending, independent_reviewers=0, gate=G-FORM

## Falsifier

Re-hash the three canonical files and re-run this script: if any measured sha256 differs from the recorded inputs, or if any probe result or shared-class verdict changes, this report is falsified for the recorded hashes.  For the HF-B1b finding specifically: falsified if schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357 no longer contains the 'No containment with C2 or C0 is asserted here' denial while its implication_ledger still asserts the E_C0 contains E_H2loc contains E_C2 nesting.

