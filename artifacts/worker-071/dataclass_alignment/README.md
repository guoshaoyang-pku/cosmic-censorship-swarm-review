# FORM-DC-ALIGN-071 -- data_class alignment across F1/F2a/F2b

Generated 2026-09-12T00:20:39+08:00 by `audit.py` (hash in `report.json`). Measurement only: no gate verdict, no node status.

## Verdict

- measurement_valid: **True**
- T0 raw block shared: **False**
- T1 canonical-JSON shared: **False**
- T2 pre-registered core keys, strict: **False**
- T3 core keys, declared normalization: **True**

data_class differs at T1 and at strict T2, but the pre-registered CORE_KEYS compare equal after the declared T3 normalization (parenthetical/post-semicolon text dropped). The mathematical core is shared only under that normalization; the exact-match T1 guard is not satisfied at these hashes.

## T2/T3 witness rows (unequal at T2)

| core key | F1 | F2a | F2b | equal T2 | equal T3 |
|---|---|---|---|---|---|
| `regularity_class.sobolev_variant.spaces` | h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} (weighted Sobolev) | h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} | h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} | False | True |
| `asymptotic_decay.parity_conditions` | not imposed; imposing a parity condition would shrink the class and must be declared as a different class | not imposed | not imposed | False | True |

## T1 witnesses (first 10)

- **F1_vs_F2a**: 8 differing leaf path(s); first up to 10:
  - `adm_mass.locator`: `<missing>` vs `to be supplied by L1`
  - `adm_mass.rigidity`: `m_ADM = 0 iff the data are Minkowski (vacuum case)` vs `<missing>`
  - `asymptotic_decay.parity_conditions`: `not imposed; imposing a parity condition would shrink the class and must be declared as a different class` vs `not imposed`
  - `diffeo_quotient`: `genericity is defined on data modulo diffeomorphisms that are asymptotically the identity; constructing that quotient rigorously is a declared open technical gap (see unresolved_items), not a solved step` vs `genericity is defined on data modulo asymptotically-identity diffeomorphisms; the quotient construction is a declared open technical gap (see unresolved_items)`
  - `excluded_data`: `data outside the declared generic set are non-generic; they are NOT counterexamples to this class. The schema does NOT decide individual membership (see genericity.membership_ruling), and the meagerness of the named families is unresolved - so 'outside G' may not be asserted for a named datum without a proof. [R1 minor: this field previously conflicted with membership_ruling and with falsifier.schema_falsifiers.]` vs `<missing>`
  - `gauge`: `no gauge is fixed on the data; every predicate in this schema is diffeomorphism invariant` vs `no gauge fixed on the data; all predicates are diffeomorphism invariant`
  - `regularity_class.sobolev_variant.spaces`: `h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} (weighted Sobolev)` vs `h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}`
  - `regularity_class.sobolev_variant.status`: `standard_choice; the numeric thresholds are UNVERIFIED citations, L1 owns verification` vs `standard_choice; UNVERIFIED citation`
- **F1_vs_F2b**: 9 differing leaf path(s); first up to 10:
  - `adm_mass.hypotheses_reconciliation`: `<missing>` vs `pointwise rates are the smooth-with-decay default; the Sobolev variant uses the same rates distributionally, and i_plus k >= 3 is assumed independently of both (worker-16 F2b-16-04 acknowledged, recorded not resolved)`
  - `adm_mass.locator`: `<missing>` vs `to be supplied by L1 (Schoen-Yau / Witten); the sign is used only to exclude negative-mass data from the ambient space`
  - `adm_mass.rigidity`: `m_ADM = 0 iff the data are Minkowski (vacuum case)` vs `<missing>`
  - `asymptotic_decay.parity_conditions`: `not imposed; imposing a parity condition would shrink the class and must be declared as a different class` vs `not imposed`
  - `diffeo_quotient`: `genericity is defined on data modulo diffeomorphisms that are asymptotically the identity; constructing that quotient rigorously is a declared open technical gap (see unresolved_items), not a solved step` vs `genericity is defined on data modulo asymptotically-identity diffeomorphisms; the quotient construction is a declared open technical gap (see unresolved_items)`
  - `excluded_data`: `data outside the declared generic set are non-generic; they are NOT counterexamples to this class. The schema does NOT decide individual membership (see genericity.membership_ruling), and the meagerness of the named families is unresolved - so 'outside G' may not be asserted for a named datum without a proof. [R1 minor: this field previously conflicted with membership_ruling and with falsifier.schema_falsifiers.]` vs `<missing>`
  - `gauge`: `no gauge is fixed on the data; every predicate in this schema is diffeomorphism invariant` vs `no gauge fixed on the data; all predicates are diffeomorphism invariant`
  - `regularity_class.sobolev_variant.spaces`: `h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} (weighted Sobolev)` vs `h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}`
  - `regularity_class.sobolev_variant.status`: `standard_choice; the numeric thresholds are UNVERIFIED citations, L1 owns verification` vs `standard_choice; UNVERIFIED citation`
- **F2a_vs_F2b**: 2 differing leaf path(s); first up to 10:
  - `adm_mass.hypotheses_reconciliation`: `<missing>` vs `pointwise rates are the smooth-with-decay default; the Sobolev variant uses the same rates distributionally, and i_plus k >= 3 is assumed independently of both (worker-16 F2b-16-04 acknowledged, recorded not resolved)`
  - `adm_mass.locator`: `to be supplied by L1` vs `to be supplied by L1 (Schoen-Yau / Witten); the sign is used only to exclude negative-mass data from the ambient space`

## Measured hashes

- F1 (`schemas/af_wcc_vacuum.yaml`): `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`
- F2a (`schemas/af_scc_c2_vacuum.yaml`): `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
- F2b (`schemas/af_scc_c0_vacuum.yaml`): `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`
- F0_canonical (`research_map/formulation_taxonomy.yaml`): `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc`
- F0_authoring (`artifacts/formulation/formulation_taxonomy.yaml`): `c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f`

## Falsifier

If all three canonical data_class subtrees compare equal at T1, or all CORE_KEYS compare equal at T2, then the G-FORM unmet item 'no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b' is refuted at the measured hashes and the authoring data_class_freeze claim is confirmed; the artifact must report that outcome. If any difference is found, the (path, file, line, value) witness list is the deliverable and the unmet item stands at exactly the strength of the difference found. Any change of an input sha256 across the measurement window voids the measurement at that path.

## Limitations

- T3 normalization drops parenthesized and post-semicolon text; every dropped fragment is listed in dropped_fragments so the normalization is auditable.
- Line numbers are value-node start lines from the YAML composer.
- Only F1/F2a/F2b are compared; AF-WCC-SCALAR-SPH is out of scope.
- The measurement reports strict (T1/T2) and normalized (T3) readings; it does not decide which reading transfer rule T1 should use.
- No gate verdict and no node status are asserted.
