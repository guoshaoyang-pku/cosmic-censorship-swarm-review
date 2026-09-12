# L0/L1 acceptance check (Astra assignment cards)

- L0 rows: 62 (threshold >=15) -> PASS
- L1 rows: 97 for 97 sources -> PASS
- L0 verification_status counts: {"abstract-read": 61, "full-text": 0, "page-checked": 0, "unverified": 1}
- L0 class coverage: {"AF-WCC-VAC-GEN": 11, "AF-SCC-C2-VAC-GEN": 10, "AF-SCC-C0-VAC-GEN": 11, "AF-WCC-SCALAR-SPH": 10}

## L0 gaps

- none

## L1 gaps

- none

## Note on 'exact theorem number/page'

The L1 `exact_locator` column carries the primary page/record URL. Theorem/section numbers were
extracted only where the accessible abstract or Crossref record exposes them; most primary full
texts are paywalled, so the audit records the abstract-level locator rather than inventing a number.
