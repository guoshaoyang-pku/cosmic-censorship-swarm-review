# Worker-09 L1 shard: lead integration note

- Integrated: 2026-09-12 ~00:42 (+08) by lead-literature (L1 owner)
- Shard: `ledger/citation_audit_scc_flash-09.jsonl` (+ `.csv`, `.lead_schema.csv`), 16 rows, worker `deepseek-flash-09`
- Scope: SCC-side sources. Shard hashes are recorded in its own files; the canonical `ledger/citation_audit.csv` was not touched by the worker.

## Row dispositions

| Worker row | Disposition | Canonical record |
|---|---|---|
| W09-001 Dafermos 2003 Annals | duplicate | SRC-020/SRC-060 |
| W09-002 Dafermos 2005 CPAM | duplicate | SRC-021/SRC-056 |
| W09-003 Luk-Oh Duke 2017 | duplicate | SRC-023/SRC-055 |
| W09-004 Choptuik 1993 | duplicate; correctly flagged "NOT-A-THEOREM-SOURCE" | SRC-016 (T-103 numerical) |
| W09-005 "Eardley-Gundlach" (critical phenomena) | **unresolved**: assigned citation not found; recorded as `citation_unsupported` | not registered (matches the canonical policy: no guessing) |
| W09-006 Gundlach-Martin-Garcia 2007 Living Reviews | **adopted** (new) | SRC-094; now cited by T-103 |
| W09-007 CGNS Part 3 | duplicate | SRC-028 |
| W09-008 Van de Moortel 2018 CMP (EM-Klein-Gordon) | **adopted** (new) | SRC-095; now cited by T-505 as the model-matched companion |
| W09-009 Sbierski JDG 2018 | duplicate | SRC-005 |
| W09-010 Dafermos-Luk 2025 Annals | duplicate | SRC-004 |
| W09-011 Van de Moortel 2020 CMP | duplicate | SRC-025 |
| W09-012/W09-013 Luk-Oh Parts I/II | duplicate | SRC-057/SRC-058 (venues now published) |
| W09-014 Sbierski 2020 holonomy | duplicate | SRC-024/SRC-087 |
| W09-CTRL-1 control: DOI 10.4310/jdg/1519959623 | **control passed**: resolves to an unrelated paper and was rejected | recorded here as method evidence |
| W09-CTRL-2 control: DOI 10.4310/jdg/1518490820 | **control passed**: resolves to the exact Sbierski title | matches SRC-005 |

## Attestation

- The negative control (W09-CTRL-1) is exactly the falsifier Astra specified for L1 ("a DOI resolves to a different paper"). The worker's method caught it and refused the citation; I re-verified the positive control DOI against the ledger record and Crossref.
- The shard's only model-level catch that mattered to the canonical ledger was the EM-Klein-Gordon vs EM-scalar distinction; SRC-095 is now the model-matched source for T-505, and the EM-scalar Gautam paper (SRC-052) carries an explicit do-not-transfer warning.
- No fabricated locator or title mismatch was found. Two new sources were adopted only after the lead independently fetched their arXiv pages.
- Worker schema gaps reported earlier (class_id column, what-it-does-not-prove) remain handled at the canonical layer: `class_mapping`, `assessment`, and the L0 `does_not_imply` field.
