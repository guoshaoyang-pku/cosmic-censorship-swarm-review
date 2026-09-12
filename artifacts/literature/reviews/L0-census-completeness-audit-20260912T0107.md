# L0 census completeness audit — independent cross-check from the accepted event stream

- **Actor:** `astra-lead-literature` (group `literature`, canonical owner of L0/L1)
- **At:** 2026-09-12T01:10+08:00 · **Gate:** G-LIT · **Node:** L0 (companion L1)
- **Target (frozen, re-measured at read time):**
  `ledger/theorems.jsonl` `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
  (151521 B, 62 rows, mtime 00:39:11) ·
  `ledger/citation_audit.csv` `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
  (102771 B, 97 rows). **Freeze held; no ledger or build-input write.**
- **Method (independent of the lead census):** read-only scan of the **accepted event stream**
  `research_map/events.jsonl` (the controller's own authoritative ingest), not the
  `comms/outbox/**` tree used by the census. Deterministic scanner
  `artifacts/literature/reviews/l0_census_completeness_audit.py`; machine record
  `L0-census-completeness-audit-20260912T0107.json`.
- **Authority:** measurement and review input only. Not an accept, not a gate verdict, not a node
  status; `counts_toward_gate_accept=false`. Fluent text is never promoted.

## 1. Census confirmation (record A vs accepted stream)

| quantity | census (00:57, outbox-scoped) | this audit (01:10, accepted stream) |
|---|---:|---:|
| ledger-whole content verdicts | 12 | **12** |
| accept / revise / reject / inconclusive | 2 / 9 / 0 / 1 | **2 / 9 / 0 / 1** |
| distinct reviewers | 12 | **12** (sets identical) |
| full-ledger accepts | worker-072 (4.5), worker-075 (4.0) | **same** |
| new content verdicts after the census | — | **none** |

Every one of the 29 review events in the accepted stream that binds the frozen hash is accounted for:
12 ledger-whole content verdicts, 1 ledger-scope static-census+sample accept (worker-050), 16
reviews of other objects that merely cite the hash (predicate-scope difference, not a content gap;
all pre-census ones are in the census's `out_of_scope_reviews`, the rest post-date it).

**Census verdict: CONFIRMED.** Its 12-row content set, reviewer set and accept set reproduce exactly
from a different data source, and no further L0 content verdict arrived between 00:57 and 01:10.
The census's own falsifier clause (b) is not triggered.

**One scope-imprecision (minor, no gate effect):** the census excludes worker-050 as a "sample spot
check", but `artifacts/worker-050/l0_independent_spotcheck/static_report.json` runs a **62/62 static
census (C1–C6)** plus an 8/62 live re-fetch sample (C7). The exclusion decision is defensible only
for C7; at ledger scope the static census is a third independent accept. Adjudication of whether it
counts belongs to the audit lead, not the ledger author.

## 2. The controller's L0 review scan — quantified gap (BL-10)

Reproduced literally from `research_map/astra_lifecycle.py:review_coverage` (path-scoped
`reviews/*.json`; requires a top-level `verdict` key; target must be the alias `L0`; explicit string
pin must carry the measured hash). The 01:00:44 report
(`lifecycle_20260912-010044.json`) matches the reproduction.

| record | reviewers seen | accepts seen |
|---|---:|---:|
| controller scan (literal) | 7 / 12 | 1 / 2 full-ledger (1 / 3 incl. sample scope) |
| accepted stream (this audit) | 12 / 12 | 2 / 2 (3 / 3) |

Six ledger-level verdicts are invisible to the scan; each miss has a mechanical reason:

| reviewer | verdict | miss reason |
|---|---|---|
| worker-072 | **accept 4.5** | reviews/ records exist but target F1/F2a; event target is `ledger/theorems.jsonl#a1674f…` (not an alias) and no scanned pin key carries the hash |
| worker-050 | accept 4.0 (sample scope) | no `reviews/` record; target is `ledger/theorems.jsonl` (not an alias) |
| worker-097 | revise 1.75 | no `reviews/` record (verdict lives under `artifacts/worker-097/l0_rev4_review/`) |
| worker-023 | revise 3.5 | no `reviews/` record; hash bound only via `evidence_refs` |
| worker-037 | revise 4.0 | no `reviews/` record; target `L0:ledger/theorems.jsonl#…`; hash via `evidence_refs` |
| worker-029 | revise 3.5 | `reviews/F1-suite-rebind-worker-029.json` exists but targets F1 |

A minimal repaired predicate — verdict kind + subject normalizes to the L0 ledger as a whole
(`L0` / `L0:…` / `ledger/theorems.jsonl[#hash]`) + hash bound by explicit pin **or** `evidence_refs`
— recovers 12/12 reviewers and both full-ledger accepts (simulated in the audit JSON,
`record_B_controller_scan.repair_simulation`). If the scan must stay file-scoped, worker-072's
verdict file additionally uses the key `verdict_recommendation`, not `verdict`.

**Gate consequence:** the map's "1 distinct accept" is a scan-scope artifact, not a missing verdict.
At the unchanged bytes the L0 half of G-LIT is **ruling-bound, not reviewer-latency-bound** (BL-7:
does HF-02 class-disjunction apply to ledger records?). This audit does not pass the gate and does
not resolve BL-7; both accepts remain conditional on that reading.

## 3. Queue and blockers at this lifecycle

- Inbox `comms/inbox/astra-lead-literature.jsonl` unchanged since 00:37:13 — no new downward card;
  nothing literature-owned is outstanding except what the controller owns.
- Predecessor `lit-l7-*`/`lit-l8-*` events are ingested (verified in `events.jsonl`).
- **BL-7** (HF-02 ledger scope) — OPEN, gate-deciding, controller/A0. Unchanged.
- **BL-9** (HF-14 renamed-vocabulary scope) — OPEN, A0/rubric owner. Unchanged.
- **BL-10** (controller scan undercount) — OPEN; this audit supplies the mechanism, the per-miss
  reasons and a repair predicate. Predecessor's count of 2 accepts is confirmed (2 full-ledger + 1
  sample-scope).
- **BL-11** (formulation anchors `s>5/2`, `δ∈(1/2,1)`, PMT, predictability) — OPEN, formulation-owned.
- **BL-12** (`lit-l5-20260912-022`, 3.0 h, two blind L0 reviewers) — still unconsumed and redundant
  with the audit-owned `astra-life05-verify-l0-final`; request stands to re-point or close it.

## 4. Falsifiers

Any L0/L1 hash movement voids this audit. A ledger-level review event at the frozen hash not listed
here voids completeness. A listed verdict that does not bind the hash, or is by the ledger author,
voids that row. A further `reviews/*.json` verdict at the hash unseen by the reproduced scan voids
the BL-10 mechanism claim.

## 5. Not claimed

Gate verdict · node completion · accept of L0 · that BL-7/BL-9/BL-11 are resolved · that the 8
two-class rows are compliant · that worker-050's static census is a full-schema accept · that the
repaired scan changes any gate on its own.
