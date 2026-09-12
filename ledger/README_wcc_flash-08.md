# worker-08 WCC citation shards (node L1)

`ledger/citation_audit.csv` is owned by lead-literature and uses the schema citation_id/bibkey/.../reviewer. Worker-08 does NOT write to it.

Files here:
- `citation_audit_wcc_flash-08.jsonl` — full-fidelity rows (locator, statement, assumptions, class mapping, what it does NOT prove, verdict, falsifier, evidence ref).
- `citation_audit_wcc_flash-08.csv` — same rows, worker schema.
- `citation_audit_wcc_flash-08.lead_schema.csv` — mechanical mapping into the lead schema for merge (W08-001..W08-0NN), reviewer deepseek-flash-08. Schema gaps: no class_id / what-it-does-not-prove column, and no 'unresolved' status in the observed vocabulary; the Ringstrom-2008 row uses status/verdict 'unresolved' as an explicit extension request.

Merge rule: de-duplicate on doi/arxiv_id; prefer the worker's full-fidelity row when the locator matches.
