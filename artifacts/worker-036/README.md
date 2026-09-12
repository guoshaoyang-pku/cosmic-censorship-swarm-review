# W036-MAPREG-01 — map hash-registry and digest-format audit

**Worker:** `worker-036` (instance `worker-036-20260912T001656-968807`)
**Node / classes:** `A1` reads; class-bound to `AF-WCC-VAC-GEN` (primary), `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH` (F0/F1/F2a/F2b/N0/N1 + GLOBAL A0/A1/A2 nodes).
**Status:** `active` — measurement only. No node completion, no gate verdict, no shared file
modified. Only `artifacts/worker-036/`, `comms/outbox/worker-036.jsonl`, and (controller-owned)
ingest of those events are touched.

## Question

Do the map's declared/measured artifact hashes and the checkpoint hash registry still equal the
bytes on disk, and what does each `declared_hash_matches_measured` flag actually mean?

## Answer (pinned to snapshot)

Pinned snapshot: `research_map/research_map.json` sha256 `a8a73f983baa…5448` (map `updated_at`
2026-09-12T00:20:07+08:00), `research_map/events.jsonl` sha256 `a1bd2c534d32…6804d`,
report generated 2026-09-12T00:21:41+08:00.

**The measured side is sound; the declared side is not.** At the pinned snapshot the controller's
`artifact_sha256_measured` equals a fresh digest for every existing node artifact, the checkpoint
registry has no malformed values, and both active `frozen_artifacts` entries match disk. The
`declared_hash_matches_measured=false` flags on **F0, F1, F2a, F2b are caused by malformed declared
values, not by artifact drift**: those four map fields are a 16-hex prefix followed by 48 zeros —
a zero-padded pseudo-digest, not a sha256. `reviews/` (A1) is a live directory whose recorded
directory hash goes stale between controller passes; it should never be a binding target.

Second defect, in the accepted event stream: 11 accepted `artifact` events carry non-digest
`sha256` values (9 zero-padded prefixes from `astra-lead-formulation`, 2 20-char truncations from
`deepseek-flash-16`). For the 9 padded events the author's outbox copy now carries the **full**
digest under the **same `event_id`**, so `comms.py` event_id dedup (`comms.py:303-305`) can never
ingest the in-place correction. Six of the nine already have a later, full-digest revision in the
accepted stream (`leadform-artifact-0092-r11` … `-0097-r25`); those revisions are the repair path.
Three (`DELIVERABLE_SUMMARY.md`, `BN_TRIAGE.md`, `KEY_MANIFEST.json`) have no later full-digest
event for the path.

## Findings (see `map_hash_registry_audit_report.json` for full statements)

| id | severity | n | claim |
|---|---|---|---|
| W036-F1 | hard | 4 | map `artifact_sha256` for F0/F1/F2a/F2b is `^[0-9a-f]{16}0{48}$` — malformed, not a digest; measured == disk at snapshot |
| W036-F5 | hard | 9 | accepted artifact events carry zero-padded `sha256`; same-event_id outbox corrections are dedup-blocked forever; 6/9 repaired by a later full-digest revision, 3/9 not |
| W036-F6 | hard | 2 | accepted artifact events from `deepseek-flash-16` carry 20-char truncated digests, no correction found |
| W036-F3 | soft | 1 | `reviews/` live-directory measured hash drifted (`d3c9266899d5` → `be68346cd337` at scan time) |
| W036-F8 | hard | 1 | one checkpoint-registry entry mismatched fresh disk at scan time (transient; registry is rewritten every checkpoint) |

Not findings: 6/12 nodes `bound`, N1 `absent` (numerics lock intact), 2/2 frozen entries clean,
0/10 registry entries malformed.

## Repair

1. Ingest: reject `sha256` fields that are not full 64-hex digests, and stop storing in-place
   rewrites of an already-ingested `event_id` — require a new `event_id` with `supersedes`.
2. Map: recompute `artifact_sha256` from the latest **valid** artifact event per node; make
   `declared_hash_matches_measured` distinguish `malformed` from `stale`.
3. F0/F1/F2a/F2b: apply the already-accepted full-digest revisions `-0092-r11`…`-0095-r4f0`.
4. A1: bind verdicts to per-file hashes under `reviews/`, never to the directory digest.
5. Worker-16: re-emit the A0 rubric and detector-patch artifact events with full digests.

## Falsifier

Re-run against the same recorded `map_sha256` / `events_sha256` (see report `snapshot`). The report
is FALSIFIED if (a) any `registry_stale`/`registry_stale_live_dir` node equals its recorded hash on
re-measure; (b) any `declared_stale` node's declared hash equals its fresh digest; (c) any `bound`
node fails either equality; (d) any `declared_malformed` node's declared field is a full 64-hex
digest without the 48-zero tail; or (e) any event with `dedup_blocks_correction=true` is absent
from `ingested_ids.json` or its outbox copy lacks a full digest. A changed map/event stream
(different snapshot sha256) voids the classification, not the method.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-036/map_hash_registry_audit.py --selftest   # PASS
python3 artifacts/worker-036/map_hash_registry_audit.py \
        --out artifacts/worker-036/map_hash_registry_audit_report.json  # exit 1 = hard findings
```

Stdlib-only; no network; reads `research_map/research_map.json`, `research_map/events.jsonl`,
`runtime/state/{artifact_hashes,ingested_ids}.json`, `comms/outbox/**`, and the node artifacts.
Fresh digests are wall-clock and the map/event stream move under an active controller, so only the
recorded snapshot hashes make a run reproducible.

## Artifacts and hashes

| artifact | sha256 |
|---|---|
| `artifacts/worker-036/map_hash_registry_audit.py` | `e8e05553fbefbb4a8dcb5ebca7fb320c4626d024af61831c5b155170ee83ac4d` |
| `artifacts/worker-036/map_hash_registry_audit_report.json` | `73d1c1a690a51f8d97443fb7c3b1324a5041ff0ac62e1cc31abf1b83751a3ae5` |

Worker-authored, `validation_status=unverified`; adjudication belongs to the audit lead /
controller. Fluent text is not evidence.
