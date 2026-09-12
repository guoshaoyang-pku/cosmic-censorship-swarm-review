# Superseded pilot — W062-SCC-LOCATOR-REFETCH-01 attempt 1 (prereg v1)

- **Run window:** 2026-09-12T00:43–00:45; 13 of 34 rows, 26 fetches.
- **Frozen rules then:** `PREREGISTRATION.v1.json`
  (sha256 `75d0640a3aef5537878ee4509db33b5c90cc140a7a93eae442372531e9f5527c`).
- **Why stopped:** the pilot falsified its own comparator. arXiv Atom `<published>` is the v1 preprint year,
  while the ledger `year` is the journal publication year, so SRC-004 (title containment 1.0, arXiv 2017 vs
  ledger 2025) was scored PARTIAL, and SRC-024's replacement (containment 1.0, arXiv 2020 vs ledger 2022)
  likewise. The v1 code also deviated from the v1 text in not forcing MISMATCH for a >2 year delta.
- **Successor:** `../PREREGISTRATION.json` schema `w062-prereg-2`, whose `amendment` block records the fix:
  arXiv years are advisory (preprint/version years); Crossref/OpenAlex/INSPIRE publication years stay decisive.
- **Evidence handling:** `raw/` here (26 bodies) and `refetch.partial.json` are retained for audit only.
  No pilot body is copied into the reported run's `../raw/`, and no pilot fetch appears in any v2 count,
  control or verdict.
