# W082-A1-XTARGET-ERRATUM-AUDIT-01

- Task: `W082-A1-XTARGET-ERRATUM-AUDIT-01` (node A1, gate G-AUDIT)
- Classes: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
- Created: 2026-09-12T01:18:38+08:00
- Verdict: **revise** 3.5/5

## Checks

| check | status | measured |
|---|---|---|
| stale_set_exact | pass | listed=19 accepted_stale=19 sym_diff=0 |
| current_batch_intact | pass | 10 ids, applied=10 |
| hash_binding | pass | report.json=9651c42845c0, REVIEW-A1-XTARGET-082.json=be66be532602, harvest_a1_xtarget_census.py=2e3d12aa0bb6 |
| map_liveness | unretired | stale live: 2 claims + 6 reviews; retired markers=0 |
| erratum_reason_batch_b_dedup | contradicted | batch B reviews present=3 |
| corpus_archive_replayability | gap | snapshot files=3; corpus manifest=False; new binding reviews since window=6 |

## Findings

### W082-EA-01 (medium) — Stale census entries are live and unretired in the canonical map

map.claims carries 2 stale census claim(s) and map.reviews carries 6 stale coverage review(s); map.applied_event_ids still holds all 19/19 stale ids and no stale entry carries superseded_by/retired. The erratum is a status event only, so a consumer counting map claims/reviews by task_id sees 3 claims and 9 reviews for one census instead of 1 and 3.

Falsifier: A map record or accepted event that retires or supersedes the six stale reviews and two stale claims.

### W082-EA-02 (low) — Erratum's stated reason for batch B is contradicted by the accepted stream

The erratum says batch B (ccf3ac5f77f3) review events were deduped away because their ids lacked the report digest. Measured: all three ccf3ac5f77f3 coverage reviews are in events.jsonl, in applied_event_ids and live in map.reviews. The digest-less review ids belong to batch A. The stale set itself is correct; only the published reason is wrong.

Falsifier: A re-ingest or map snapshot showing the three ccf3ac5f77f3 coverage reviews absent.

### W082-EA-03 (low) — Corpus-dependent counts are not exactly replayable from the archived snapshots

snapshots/ archives only the three canonical schema bytes (plus the FROZEN pin set); the harvested review corpus (reviews/, artifacts/**, comms/**, events.jsonl) was not archived, so the published falsifier can re-check byte binding but not reproduce per-target counts. The census discloses corpus liveness in report.limits.

Falsifier: An archived corpus manifest for the 2026-09-12T01:10:18..01:12:08 window.

### W082-EA-04 (info) — Verified: stale-set enumeration and hash binding are exact

Erratum lists exactly the 19 accepted-stream ids outside the final batch; all 10 final ids are applied once; report/review/instrument bytes match the live event sha256s (report 9651c42845c0, review be66be532602, instrument 2e3d12aa0bb6); snapshot bytes re-hash to their declared pins.

Falsifier: Any hash mismatch at re-measurement.

## Repair recommendation (controller-side)

- Stale claims to retire: w082-a1xt-4f94a458b823-claim-coverage, w082-a1xt-ccf3ac5f77f3-claim-coverage
- Stale reviews to retire: w082-a1xt-ccf3ac5f77f3-f1-d9cebb9404b2-coverage-review, w082-a1xt-ccf3ac5f77f3-f2a-e9a27996dfd3-coverage-review, w082-a1xt-ccf3ac5f77f3-f2b-b2ab6acb2bbe-coverage-review, w082-a1xt-f1-d9cebb9404b2-coverage-review, w082-a1xt-f2a-e9a27996dfd3-coverage-review, w082-a1xt-f2b-b2ab6acb2bbe-coverage-review
- Authority: worker evidence only; no gate verdict, no node status, no validation_status, no map edit

## Falsifier

Re-run this instrument: a listed stale id that was never ingested, a current-batch id missing or duplicated, a measured sha256 that differs from the live event pin, a stale entry that turns out to carry a retirement marker, or an archived corpus manifest for the observation window (which voids W082-EA-03) falsifies the corresponding check.
