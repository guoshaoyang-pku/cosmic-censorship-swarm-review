# W074-L1-L11-SCOPE-VERIFY-01 — independent verification of the L11 L1 locator-scope record

Worker: `worker-074` (self-selected; no `comms/inbox/worker-074.jsonl` card existed).
Node: `L1` (also touches `L0`), gate `G-LIT`, classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`. **Worker measurement only:** no gate verdict, no node
status, no `validation_status=passed`, no ledger/map/canonical write. The one canonical-adjacent
thing this task does is read.

## Question

The literature lead's L11 lifecycle (01:15:30) landed a scope adjudication:
under controller ruling **REC-6** ("evidence_url is the locator column"), L1 evidence binding is
MET at `ledger/citation_audit.csv#315c19145065`, and the 67/97 non-record `exact_locator` values
are a documentation defect on a non-binding column. It is supported by an L11 machine record
(`artifacts/literature/reviews/L1-locator-scope-L11-machine.json#2a9f73b223ec`) that reproduces
worker-025's revise with a 4-row predicate difference.

This task independently checks (a) the machine record's per-row measurement, (b) the residual
4-row reconciliation against worker-025, and (c) the ruling basis the adjudication cites.

## Method

Deterministic, offline, stdlib only. `verify_l11_scope_074.py` pins eight inputs by sha256,
reimplements the declared record-locator predicate from URL semantics (it does **not** import or
execute the lead's scanner — that script rewrites the lead's own machine-record path, which the
freeze forbids), reclassifies all 97 ledger rows on both columns, and compares per row and per
count against the machine record. It then resolves the cited REC ids, measures the worker-025
residual row-by-row, and checks the HF-03 resolution axis. T0==T1 over all eight inputs.

Reproduce: `python3 artifacts/worker-074/l11_scope_verify/verify_l11_scope_074.py`
Exit 0 iff every binding check passes. Exit 3 here is expected: one provenance check fails by
design, because the finding is real.

## Result

27/27 measurement checks PASS, 1/1 provenance check FAIL. Machine-record measurement
**reproduced exactly**:

| quantity | machine record | this worker |
|---|---|---|
| rows | 97 | 97 |
| `exact_locator` record / non-record | 30 / 67 | 30 / 67 |
| `exact_locator` breakdown | 40 discovery + 27 truncated + 20 page + 10 endpoint | identical |
| `evidence_url` record / absent / non-record | 95 / 2 / 0 | 95 / 2 / 0 |
| rows with >=1 record anchor | 97 | 97 |
| per-row class diffs | — | 0 on both columns |

`normalized_sha256` (report with the volatile `created_at` removed) is identical across two runs:
`b97c3c9a672afa8b…`.

## Findings

* **W074-L11-F1 (moderate, provenance-binding).** The adjudication binds its ruling to
  `runtime/state/controller_verification/astra-lifecycle-07-decisions.json#REC-6`. That file holds
  REC-29…REC-35 only; REC-6 is not in it. The operative text
  ("evidence_url is the locator column; exact_locator is query-provenance") is **REC-6 in
  `astra-lifecycle-04-decisions.json`**, where it is confirmed verbatim (including the clause
  forbidding a metadata-only rewrite of the 67 cells while verdicts are in flight). Substance
  confirmed, citation does not resolve.
* **W074-L11-F2 (moderate, attribution).** The adjudication explains the 4-row difference with
  worker-025 as "a predicate call on `inspirehep.net/api/literature/<id>`". Measured: **0/97
  `exact_locator` values are inspirehep record endpoints** (the 27 inspirehep `api/literature?q=…`
  values are truncated and both sides class them TRUNCATED). The four rows are `SRC-087` and
  `SRC-089` (`api.crossref.org/works/<DOI>`), `SRC-090` (institutional PDF with a § locator) and
  `SRC-092` (`api.openalex.org/works/doi:<DOI>`). The 30-vs-26 count reproduces; the stated reason
  is wrong.
* **W074-L11-F3 (minor, scope-extension).** The MET conclusion is computed on
  `any_record_anchor` = evidence_url OR url/doi/arxiv_id. REC-6 reads the criterion "per-row
  against evidence_url"; under that literal reading 2/97 rows (`SRC-094`, `SRC-095`) have an empty
  `evidence_url`. Both carry record-shaped `url`/`doi` fallbacks, so the conclusion holds under the
  extension — but the extension is not in REC-6's text and should be recorded as an explicit rule.
* **W074-L11-F4 (info, independence).** The machine record and the adjudication are authored by the
  same actor, and the adjudication itself declares it is not an independent verdict. The L11 pair
  is owner measurement; non-author independence for the L1 half must come from the worker
  re-fetch/spot-check stream (worker-025/062/070/075/079/009), not from L11.
* **W074-L11-F5 (positive, reproduction).** The machine record's counts and per-row classes
  reproduce exactly and the worker-025 residual reconciles count-wise (26+4 = 30).

## Verdict on the target

`revise` (3.5) on `reviews/L1-gate-adjudication-lead-literature-L11.json#6d8e86e360c9`:
measurement reproduced, one binding ref wrong (`REC-6`), one attribution wrong (the 4-row
residual), one scope extension unstated. `hard_failures: []` — these are binding/hygiene defects,
not rubric HF-03 (all 97 rows are `resolver_result=resolved`; the class-metadata half of the HF-03
detector is outside the L11 predicate and is not adjudicated here). The machine record itself is
reproduced, not revised.

## Falsifier

FALSIFIED IF any pinned input fails to re-hash to its recorded sha256, or a re-run on the same
tree state yields a different per-row classification, count table, finding set, normalized digest,
or exit code; or if an `exact_locator` value of the form `inspirehep.net/api/literature/<id>` is
produced; or if REC-6 is produced inside `astra-lifecycle-07-decisions.json`.
