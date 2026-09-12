# Controller citation spot-check (2026-09-11T23:27+08:00)

Method: Astra fetched the locator directly and compared the ledger excerpt verbatim.
Untrusted web content was treated as data.

| citation_id | locator | result |
|---|---|---|
| SRC-002 (Rodnianski & Shlapentokh-Rothman, "Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution") | arXiv:1912.08478 (v2, 2022-10-19) | **CONFIRMED** — abstract text in `ledger/citation_audit.csv` matches the arXiv abstract verbatim, including "exterior region of a naked singularity" and the prior-work sentence naming Christodoulou's spherically symmetric Einstein-scalar-field examples. |

Note: this confirms locator + excerpt integrity for one row. It does not confirm the
`used_by_theorems` scope mapping; that remains an A1/L1 review obligation.
