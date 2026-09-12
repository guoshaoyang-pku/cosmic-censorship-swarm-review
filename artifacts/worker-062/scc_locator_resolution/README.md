# W062 — SCC-side `exact_locator` resolvability map

- **Task:** W062-SCC-LOCATOR-RESOLVABILITY-01 (worker-062, bounded class-bound task; no inbox card existed for this slot)
- **Node / gate / class:** L1 / G-LIT / `AF-SCC-C0-VAC-GEN` (SCC-side scope)
- **Pin:** `ledger/citation_audit.csv` sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
- **Created:** 2026-09-12T00:36:57+08:00

## Result

| SCC-side rows | direct record locator | weak (`exact_locator` is not a record locator) |
|---|---:|---:|
| 34 | 8 | 26 |

- Weak categories: `search_or_query_endpoint` 22, `elided_or_truncated` 4; weak rows by verification method: {'arxiv-api': 22, 'inspirehep-api': 4}.
- Weak rows share 17 distinct locator strings; worst sharing 4 rows (`https://export.arxiv.org/api/query?search_query=all:%22Kerr+Cauchy+horizon%22&so` x4).
- Repair proposals: 26/26 weak rows have a replacement available from a value already in the row (`evidence_url` / `doi` / `arxiv_id` / `url`); 0 unavailable. No value was invented and no ledger cell was edited.

## Controls (all must pass; run exits 4 otherwise)

- C1 positive (7 synthetic record locators): PASS
- C2 negative mutants (7 search/truncated/empty): PASS
- C3 scope/disjointness (34 rows, disjoint from worker-050's WCC scope): PASS
- C4 hash-guard teeth (byte-mutated ledger -> exit 3): PASS
- C5 cross-instrument agreement with worker-050 on the 12 exact-match WCC rows: 12/12 PASS

## Cross-checks against published aggregates

- Strict classifier over all 97 rows: 68 weak / 29 direct, 44 distinct weak locators, worst sharing 7.
- astra-lead-literature's adjudication claims 67 weak / 30 direct, 43 distinct, worst 7.
- After stripping one trailing parenthetical annotation from each cell (the only relaxed rule): 67 weak / 30 direct / 43 distinct / worst 7 -> matches the lead aggregate: True.
- Adjudication of the single strict/relaxed difference: the single strict/relaxed difference is SRC-090, whose exact_locator is a direct PDF URL followed by a page annotation '(§1.3, p. 19)'; strict reading treats the cell as not a URL, the lead's direct-record reading treats the URL part as the locator. Both readings are defensible; the row is NOT in the SCC scope, so the SCC table is unaffected.

## Limits and falsifiers

- Only the SCC-side 34 rows were fully classified and only the exact_locator field was tested; the remaining 51 non-SCC rows enter only the aggregate global reproduction, not a per-row verdict. No fetch was performed. This is one worker artifact; it cannot move a node status or a gate.
- no live fetch attempted: an egress probe from this shell timed out before the run, so all rows are marked unfetched_no_egress and the report makes no claim that any proposed locator resolves; re-fetch is the declared next falsifier.
- F1: any SCC-side row classified direct whose exact_locator does not address exactly one record voids that row's classification.
- F2: any SCC-side row classified weak whose exact_locator does address exactly one record voids that row's classification.
- F3: a re-fetch of a proposed locator that fails to return the cited work (title/author/year mismatch, HTTP >= 400) voids that proposal.
- F4: any drift of ledger/citation_audit.csv away from sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9 voids the whole table and the global reproduction.
- F5: a rerun of classify_scc_locators.py at the pinned hash that produces different category or proposal fields falsifies reproducibility.

Authority: worker evidence only — not a ledger edit, not a gate verdict, not a node completion, not a `validation_status`.
