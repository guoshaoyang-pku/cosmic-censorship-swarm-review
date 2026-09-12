# W036-A1-REVIEWLEDGER-SELFEVIDENCE-01 — is the review ledger byte-backed?

- **Worker:** worker-036 (bounded execution worker; one task, then exit)
- **Node / gate:** `A1` / `G-AUDIT` (measurement context; **no gate verdict, no node status,
  no `validation_status=passed`**)
- **Classes:** `GLOBAL` across `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`,
  `AF-WCC-SCALAR-SPH`
- **Taken with no inbox card** (`comms/inbox/worker-036.jsonl` does not exist). The live
  question: the map is the sole global state and gate coverage is counted from its `reviews`
  list, but the controller's own principle is that "the map scan and gate text are indexes, not
  evidence". This task measures how much of that index is byte-backed.
- **Snapshot (pinned):** `research_map/research_map.json` sha256 `45acd9d93d1e…` (735 review
  records); `research_map/events.jsonl` sha256 `9f82f36d93ce…`; corpus digest `25f714b9e8f2…`
  over 807 measured files; `snapshot_stable=true`.
- **Deliverables:** `report.json` (all 735 rows), `census_review_ledger.py` (stdlib-only,
  `--selftest` 16/16), this README, `runtime/state/worker-036_reviewledger_selfevidence_checkpoint.json`.

## Question taken

For every **accepted review record** in `research_map.json → reviews`, is there a review
artifact named by that record whose current bytes (a) resolve at a full sha256 and (b) still
carry the recorded `verdict` / `score`? Which records fail, and where do two records cite the
same file with contradictory recorded verdicts?

## Method (deterministic, stdlib only, read-only)

Every record is read once into a byte snapshot; every referenced file is hashed from that
snapshot, so all classifications bind to one instant. Self-evidence path precedence:
own `artifact` (fragment split) → `target_id` under `reviews/` → first `evidence_refs` /
`artifact_refs` entry that is a review file (`reviews/*` or basename contains `review`).
The file's `verdict`/`score` are extracted tolerantly (`verdict|decision|review_verdict|
recommendation`, `score|rating`; verdict normalised to the protocol vocabulary).

| class | meaning |
|---|---|
| `SE_VERIFIED` | declared full 64-hex digest == measured bytes **and** verdict/score match the record |
| `SE_SEMANTIC_ONLY` | no full digest declared, but verdict/score match |
| `SE_DIGEST_DRIFT_SEMANTICS_OK` | declared digest no longer matches, verdict/score still match (in-place rewrite) |
| `SE_SEMANTIC_DRIFT` | current verdict or score differs from the record (split into `verdict_drift` 21 / `score_drift` 18) |
| `SE_NO_DIGEST` | file exists, no digest and no readable verdict/score |
| `SE_NONE` | record names no review file at all (target/evidence refs only, or none) |

Controls: `--selftest` 16/16 on synthetic fixtures (match / full-digest drift / prefix digest /
verdict drift / score drift / missing / no-digest / no-review-path); map bytes re-hashed after
the scan and required identical (`snapshot_stable`); map `reviews` event_ids reconciled against
the accepted stream.

## Result at the pinned snapshot

**735 records, 246 accepts, 164 gate-scoped accepts (G-F0/G-FORM/G-LIT/G-AUDIT/G-NUM). Only
177 records (24%) are `SE_VERIFIED`; only 46 of 164 gate accepts are.**

| class | all records | accepts | gate accepts |
|---|---:|---:|---:|
| `SE_VERIFIED` | 177 | 56 | 46 |
| `SE_SEMANTIC_ONLY` | 23 | 8 | 5 |
| `SE_DIGEST_DRIFT_SEMANTICS_OK` | 29 | 10 | 6 |
| `SE_SEMANTIC_DRIFT` | 39 | 17 | 7 |
| `SE_NO_DIGEST` | 9 | 6 | 6 |
| `SE_NONE` | **458** | **149** | **94** |
| **not `SE_VERIFIED`** | **558** | **190** | **118** |

Also: 197 records declare only a short (8–16 hex) digest, so even the named bytes cannot be
re-verified to full sha256; 58 records declare no path at all; 400 of the 458 `SE_NONE` records
name some other path (their target or an auxiliary artifact) but no review file.

## Findings

1. **W036-RL-01 (major) — the review ledger is mostly not byte-addressable.** 558/735 accepted
   records (118/164 gate-scoped accepts) do not name a review artifact that resolves at a full
   digest with matching verdict/score. `SE_NONE` alone is 458 records / 94 gate accepts: the
   record exists only as a map/event entry, so no re-measurement can confirm it.
2. **W036-RL-02 (major) — 21 records' cited review file now carries a different verdict.**
   11 of them are records whose recorded verdict is `accept` while the cited bytes read
   `revise`/`reject`; 5 are gate-scoped accepts:

   | record | gate | cited file | record → current file |
   |---|---|---|---|
   | `w026-f1-20260912T0029-review-f1` | G-FORM | `reviews/F1-review-lead-audit-r2.json` | accept 4.0 → **revise 3.5** |
   | `w07-review-F2b-rev11-20260912T0024` | G-FORM | `reviews/F2b-review-07.json` | accept 4.0 → **revise 3.0** |
   | `w072-2026-09-12T01:10:13+08:00-review-f2b` | G-FORM | `reviews/F2b-review-worker-072-rev29.json` | accept 4.0 → **revise 3.0** |
   | `w088-20260912T003735-review-f1-rev12` | G-FORM | `reviews/F1-review-088.json` | accept 4.0 → **revise 2.5** |
   | `w091-20260912T0040-f0rev5-review` | **G-F0** | `reviews/G-F0-final-verify.json` | accept 4.0 → **revise 3.5** |

   Six further accept→non-accept records are outside the five gates
   (`audit-l08-review-review017-…` [self-named target `reviews/CLASSSEP-adjudication-review-017.json`,
   accept 4.0 → revise 4.0], both `leadform-review-0011/0012`, `w007-citebind-review-finding-06`,
   `w009-refetch-…-review-01`, `w060-…-review-f2b-advisory-06`). Ten records run the other way
   (recorded revise, cited bytes now accept), 7 of them gate-scoped (`w011`, `w056`×2, `w064`,
   `w067`, `w084`, `w088-…-review-f1-rev12-amended`). The `w072` instance was reported
   independently in `W036-GFORM-R3-BIND-01` (`census_gform_binding.py`) and is confirmed here at
   map level. Whether a mismatch is a defect, an aggregate-file convention, or a legitimate
   later rewrite is an adjudication for the audit lead; this census only establishes that the
   record cannot be re-derived from its cited bytes.
3. **W036-RL-03 (major) — 24 review paths are cited by records with contradictory recorded
   verdicts/scores.** The same file is evidence for mutually inconsistent records, so a coverage
   count over records that share a path is not well-defined from the map alone. Largest:
   `reviews/CLASSSEP-calibration-adjudication.json` (9 records; recorded combos accept 4.0,
   accept 4.5, revise 2.0, revise 3.0), `reviews/A1-rebind-coverage.json` (9 records;
   accept 4.0, revise 2.5), `reviews/L1-spotcheck-10.json` (8; accept 5.0, accept 4.0,
   revise 3.0), `reviews/L1-spotcheck-09.json` (5), `reviews/G-NUM-protocol-review.json` (5).
   Some of these are aggregate files legitimately cited per-row with per-row scores; the
   collision list is the adjudication queue, not a defect verdict.
4. **W036-RL-04 (minor) — 197 records pin only an 8–16-hex digest**, so the record's own bytes
   are not re-verifiable to sha256 even though a path is named (same family as
   `W036-MAPREG-01` and CF-27).
5. **W036-RL-05 (minor) — 58 records declare no path reference at all.**
6. **W036-RL-06 (control, pass) — the map ledger and the accepted stream reconcile exactly:**
   735 map review event_ids = 735 accepted `review` events in `events.jsonl`, 0 absent on either
   side. The divergence above is evidence addressability, not ingest loss.

## Authority and limits

Worker measurement only. This artifact edits no canonical file, writes no map or
`runtime/state/artifact_hashes.json`, issues no gate verdict and sets no node status. A record
classified below `SE_VERIFIED` is **not** thereby false: many reviews deliver their verdict as an
event with target evidence and never materialise a self-referencing review file, and some cited
files are aggregates. Conversely `SE_VERIFIED` is a provenance property, not a merit judgement.
The census binds to the pinned map/events hashes; the map moves every cycle and later writes are
outside this snapshot. Blindness, independence and merit stay with the audit lead.

## Falsifier

Re-run `census_review_ledger.py` with `--stamp` at the pinned hashes. The claim is
**falsified** if, on those bytes, (a) any summary count differs (record/accept/class counts,
the 24 collisions, the 21 verdict-drift rows); or (b) any row classed `SE_VERIFIED` is manually
re-measured to a different file sha256, verdict or score; or (c) any listed verdict-drift path
currently parses to the recorded verdict; or (d) any listed collision path has a single
well-defined recorded (verdict, score). A map/events hash different from the pins is a **void
window**, not a falsification — re-pin and re-run.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-036/reviewledger_selfevidence/census_review_ledger.py --selftest
python3 artifacts/worker-036/reviewledger_selfevidence/census_review_ledger.py \
    --stamp 2026-09-12T01:50:00+08:00 \
    --out artifacts/worker-036/reviewledger_selfevidence/report.json
```

Byte-identical replay on the pinned snapshot was verified (`cmp` against a second run).

## Pins

| input | sha256 |
|---|---|
| `research_map/research_map.json` (735 reviews) | `45acd9d93d1ebf85bf65a3b3a2b1b08832511c28580fd1eb27c2a18f39b37e7e` |
| `research_map/events.jsonl` | `9f82f36d93cef866aec4a89be074c5324bf62ce8448560c5477b79516c4fd4a6` |
| measured-file corpus digest (807 files) | `25f714b9e8f2e5043323f74a6939665c107dca5cd76532b82fe187eefe6607ef` |
| `report.json` | `fe17912b49ca136c5a9ca9f4ec1387ce8be6f8cd92255726e058537c6407e214` |
| `census_review_ledger.py` | `605e40f83484b6011819238c63f6259bd41d8eace0b28266ee6d156f72b90485` |
