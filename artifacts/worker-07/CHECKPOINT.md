# Worker-07 checkpoint log

| # | time (+08:00) | event |
|---|---|---|
| 0 | 23:15 | worker-07 launched; inbox empty |
| 1 | 23:16–23:20 | recon: handoff, map, queue, live logs; found ≥6 workers converging on class-binding linters and worker-01/08 duplicating artifact-integrity work → chose a non-duplicative falsification task |
| 2 | 23:20 | class-separation harness run 1: target `audit_evidence.py` drifted within 34 s of pinning; fail-closed abort (exit 2) |
| 3 | 23:22 | harness run 2 (v2 corpus, 27 fixtures) at pinned revision `c4769b99ab70`: 3/17 leaks caught, 14 missed, 1/10 controls false-flagged; snapshot preserved |
| 4 | 23:26 | **assignment found** in `comms/inbox/deepseek-flash-07.jsonl` (issued 23:19:12): node L0, `ledger/theorems.jsonl`, gate G-LIT. Pivoted to assignment; harness becomes secondary |
| 5 | 23:25–23:30 | verified 5 primary sources by arXiv abstract fetch (Christodoulou 1999/2008, Luk–Oh 2017, Dafermos 2005, Giorgi–Klainerman–Szeftel 2022); caught and discarded a wrong memorised arXiv ID (1501.04593 ≠ Luk–Oh) |
| 6 | 23:31 | wrote `batch-w07.jsonl` (7 sources) + 15 theorem rows into the lead's batch structure; ran the lead's builder → canonical `ledger/theorems.jsonl` |
| 7 | 23:33 | added machine-checkable quote grounding + `check_grounding.py`; all 30 declared quotes in 13 rows match; found 16/25 accepted lead rows declare no grounding |
| 8 | 23:35 | emitted 6 schema-valid outbox events (all accepted in dry-run ingest); delivered `REPORT.md` |

**State at checkpoint 8:** assigned task delivered, `validation_status: unverified`, no node/gate state claimed.
Canonical ledger at build: `3b104a7da767…` (will change when other batches are added; my batch files are the durable contribution).

| 9 | 23:27 | **incident:** literature lead's directory rewrite deleted the injected `batch-w07.jsonl`; canonical ledger rebuilt with 0 W07 rows. Durable generator/batches preserved under `artifacts/worker-07/`; generator changed to no-inject default |
| 10 | 23:27–23:29 | supersession audit against the lead's 43-row ledger: all 15 W07 rows have equal-or-stronger canonical equivalents → **not re-injected**; annotated mapping written to the durable batch |
| 11 | 23:29 | built `check_duplication.py` (canonical work keys, tiered): 10 actionable pairs in 5 clusters, 23 review-tier, 0 duplicate source records |
| 12 | 23:29:08 | re-ran the class-separation harness on revision `bb0522e94148`: defects identical (3/17 detected, 14 missed, 1/10 false-flagged) |
| 13 | 23:30:04 | consolidated `artifacts/worker-07/REPORT.md`; emitted final status/artifact/blocker events (nominal ids T2340); all accepted in dry-run ingest |
| 14 | 23:30:22 | live gate moved to `6873cb512431`; harness re-run: **17/17 leaks detected, 10/10 controls accepted — fix confirmed**. Lead moved the check to `research_map/class_separation.py` and adopted the corpus as `runtime/bin/classsep_regression.py` (PASS) |
| 15 | 23:30:49 | emitted retraction/confirmation events: counterexample claim retracted for the current revision, remains true for the two earlier pinned revisions; `revision_history.json` written |
| 16 | 23:31 | provenance correction: `revision_history.json` observed_at replaced with authoritative snapshot mtimes (event ids T2340/T2345 are nominal labels; `created_at` fields are accurate) |

**Outstanding inbox work:** none beyond the L0 card as of checkpoint 16 (inbox watcher running).
**Next falsifiers:** `artifacts/worker-07/REPORT.md` §E.

---

## Lifecycle 2 — 2026-09-12T00:04–00:15 (+08:00), supervisor relaunch

No new card was issued to `deepseek-flash-07`, so one class-bound task was taken from the
G-LIT immediate queue: **independent L1 re-fetch spot check #3** over the audit rows the two
prior independent spot checks did not cover (flash-10: rows 1–20; flash-11: rows 21–40).

| # | time | event |
|---|---|---|
| 17 | 00:04–00:08 | recon of restarted map (CF-5..CF-9, five new `astra-indep-1-*` assignments); found the class-token census (CF-5) already assigned to flash-19 → chose the uncovered G-LIT spot-check range instead |
| 18 | 00:06 | sampling rule frozen on `ledger/citation_audit.csv` sha `0b72b419` (S1: rows 41,49,57,65,73,81,89; S2: +row 80 declared before fetch) |
| 19 | 00:07 | **fail-closed abort**: the literature lead rebuilt the csv mid-run (sha `315c1914`); no fetch had succeeded, so the pin moved and the same 8 `source_id`s were re-verified |
| 20 | 00:08–00:11 | 8 sources re-fetched via arXiv/Crossref APIs; 7 MATCH, 1 PARTIAL (year convention only), 0 MISMATCH, 0 FETCH_FAILED; 5 declared quotes grounded token-for-token, 1 metadata record, 2 no abstract |
| 21 | 00:12 | artifact frozen at `4fba7349…`; 3 outbox events emitted (status/artifact/review); all 3 accepted into `research_map/events.jsonl` at 00:12:21, 0 rejects |
| 22 | 00:15 | checkpoint written: `runtime/state/w07_checkpoint_1.json`; no node/gate state claimed, `validation_status: unverified` |

**Outstanding inbox work:** none; L0 card remains delivered-unverified and its canonical ledger
moved again during this lifecycle (`7d78d285` → `ce42d205`, recorded in the checkpoint, not adjudicated).
**Next falsifiers:** re-run `artifacts/worker-07/l1_spotcheck/run_spotcheck.py` at the pinned csv
sha256; any verdict change falsifies the MATCH set. Rows 96–97 (added after the frame) and rows
1–40 remain outside this check.

