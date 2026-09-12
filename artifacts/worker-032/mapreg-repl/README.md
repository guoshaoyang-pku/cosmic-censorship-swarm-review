# W032-MAPREG-REPL-01 — independent replication of W036-MAPREG-01

Bounded worker-032 lifecycle (instance `worker-032-20260912T002242-968807`), node `A1`,
`class_ids` = the four frozen classes (`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`). **No gate verdict, no node completion, no
shared artifact modified.**

## Question

At the pinned revision, do the map's declared/measured artifact hashes, the checkpoint
hash registry, the frozen artifacts and the accepted artifact-event digests equal the
bytes on disk — and is `W036-MAPREG-01` confirmed, superseded, or refuted?

## Method

- Independent, stdlib-only reimplementation (`scan_mapreg.py`, sha256 `fe167cd038ef0ab3…`).
  It does **not** import or execute `artifacts/worker-036/map_hash_registry_audit.py`.
- Digest semantics taken from the canonical spec, `research_map/astra_lifecycle.py:56-74`:
  file → `sha256(bytes)`; directory → `sha256` over sorted `"<relpath>\0<filesha>\n"` lines,
  files named `._*` skipped.
- Format classifier distinguishes a genuine `full64` digest from a `zero_padded_prefix`
  (16 hex + 48 zeros), which **passes a naive `^[0-9a-f]{64}$` test** — the exact defect
  W036 reported.
- 8 positive/negative controls: `python3 scan_mapreg.py --selftest` → `SELFTEST PASS`.
- Snapshot pinned by sha256; map/event streams re-hashed at the end of the scan
  (`snapshot_stability` in the report). The scan is point-in-time and read-only.

## Pinned snapshot

| object | sha256 |
|---|---|
| `research_map/research_map.json` (`updated_at` 2026-09-12T00:25:10+08:00) | `4fd40d4d1e4fc3602192eb8533e9a9f5075aa63ac644bd5c2dab30357f68db6b` |
| `research_map/events.jsonl` | `fc36f1a774c0645b0fd6cf6c0891a3745fa2523c0abd3c905a20deb08f1fe273` |
| `runtime/state/artifact_hashes.json` | see `report.json.snapshot` |
| `runtime/state/ingested_ids.json` | see `report.json.snapshot` |
| this report (`report.json`) | `78df4737b98b599e7c6102c7f79f2a1f4599598d5c15cd77b6b7ec045d05a6af` |

Map and events did not move during the scan (`map_moved_during_scan=false`,
`events_moved_during_scan=false`).

## Results at the pinned revision

**Node binding (12 nodes): 10 `bound`, 1 `declared_measured_mismatch` (`A1`, live
`reviews/` directory), 1 `absent` (`N1`, queued). 0 declared-malformed, 0
flag-inconsistent, 0 active-frozen mismatches.**

Repair since W036 (confirmed, `W032R-F8`):

| node | W036 recorded declared (map `a8a73f98`) | current declared (map `4fd40d4d`) |
|---|---|---|
| F0 | `0fcc6a1928fd40b0` + 48 zeros | `276009f4f63dbf83…` = fresh |
| F1 | `68392dd820505fbb` + 48 zeros | `9a8bd4c9680042a4…` = fresh |
| F2a | `4f97273ef4404126` + 48 zeros | `b6123750b37d8bee…` = fresh |
| F2b | `a2aef5ac7fe377a8` + 48 zeros | `1bb78ce9b3572cda…` = fresh |

**Still live from W036 (`W032R-F5`, hard): 11 accepted artifact events carry a
non-digest `sha256`** — 9 `zero_padded_prefix` from `astra-lead-formulation`
(`leadform-artifact-0082-r10` … `-0090`) and 2 `short_hex_len20` from
`deepseek-flash-16`. All 11 were present in W036's snapshot; none resolved, none new.

- 9 of the 11 have an outbox correction with the **same `event_id`** and a full digest;
  ingest dedup keys on `event_id` (`research_map/comms.py:346`), so those corrections can
  never enter `events.jsonl`.
- 6 of the 9 are superseded *for the map* by later full-digest events with **new**
  `event_id`s; 3 (`DELIVERABLE_SUMMARY.md`, `BN_TRIAGE.md`, `KEY_MANIFEST.json`) and the
  2 flash-16 truncations have no later full-digest event for the same path.

**Registry:** 220 entries, 0 malformed formats, 2 stale — `reviews/` (live directory,
`A1`) and `reviews/F1-quantifier-adjudication-078.json` (edited after the registry
snapshot). Both are liveness/time-skew, not digest-format defects (`W032R-F6`, soft).

**Frozen:** 2 active entries, 0 mismatches, 0 malformed (`W032R-F7` not raised).

## Verdict on W036-MAPREG-01

**accept, score 4.0, no hard failures** (`verdict_on_w036` in `report.json`).

- Corroborated: every recorded value and classification reproduces against the current
  bytes and is consistent with the lifecycle-03 record of the `a8a73f98 → 7f8792f8`
  transition (`runtime/state/controller_verification/lifecycle_20260912-002155.json`).
- Limitation (not a hard failure): the `a8a73f98` bytes are not archived, so the
  snapshot-side finding is corroborated but not byte-reproducible on demand; W036's
  own recorded values were used.
- Superseded portion: the F0/F1/F2a/F2b declared-value defect is repaired at the
  current revision.
- Still-live portion: the event-stream digest defects and their dedup-blocked
  corrections.

## Findings

| id | severity | statement |
|---|---|---|
| W032R-F2 | soft | declared ≠ measured for `A1` (live directory) |
| W032R-F4 | soft | measured hash stale vs fresh for `A1` (live directory) |
| W032R-F5 | hard | 11 accepted artifact events with non-digest `sha256`; 9 dedup-blocked corrections |
| W032R-F6 | soft | 2 stale registry entries, both live/time-skewed |
| W032R-F8 | info | declared-value repair confirmed for F0/F1/F2a/F2b |

Each carries its own falsifier in `report.json.findings`.

## Falsifier (whole task)

Re-run `scan_mapreg.py` against `research_map.json#4fd40d4d1e4f` and
`events.jsonl#fc36f1a774c0`. Falsified if (a) any node listed as declared-malformed has a
full64 declared value; (b) any mismatch/flag-inconsistency node is consistent; (c) any of
the 11 defect events has a full64 `sha256` at the pinned events hash; (d) any listed
dedup-blocked `event_id` is absent from `ingested_ids.json` or its outbox copy lacks a
full digest; (e) any active frozen entry fails to match fresh bytes; or (f) W036's
recorded declared values are not 16-hex + 48 zeros.

## Reproduce

```bash
cd artifacts/worker-032/mapreg-repl
python3 scan_mapreg.py --selftest
python3 scan_mapreg.py --out report.json
```

## Non-claims

Not a gate verdict; does not change any node status; does not certify artifact content,
only byte-level digest agreement; point-in-time only; does not modify the map, events,
registry, ledger or schemas; not a code review of worker-036's scanner.
