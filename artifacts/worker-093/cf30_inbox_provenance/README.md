# W093-CF30-INBOX-PROVENANCE-01 — systematic inbox provenance census

- actor `worker-093` · node `A1` · gate `G-AUDIT` · classes `AF-WCC-VAC-GEN`,
  `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- 2026-09-12 ~01:15 +08:00 · **read-only** · worker-level completion only
- verdict: `PROVENANCE_CENSUS_PASS` · digest `1e8c67dc7218` · 11/11 controls, 5/5 real expectations
- reproduce: `python3 artifacts/worker-093/cf30_inbox_provenance/inbox_provenance_census.py` (exit 0)

## Question

CF-30 (`astra-life07-notice-injection`) found three controller-attributed cards with no
accepted-stream emission and no controller lifecycle record in two inbox files, and stated the
next falsifier: *"A card in any inbox whose event_id never appears in the accepted stream."*
This census sweeps **all 45 `comms/inbox/*.jsonl`** at pinned bytes and tests it systematically.

## Method (pre-registered in `PREREGISTRATION.md` before the run)

Backing test, fail-closed and non-circular:

1. `ACCEPTED_BACKED` — `event_id` present in the accepted stream `research_map/events.jsonl`;
2. else `EMITTER_BACKED` — the controller emitter declares it, i.e. the syntactic form
   `"event_id": "<id>"` occurs in `research_map/astra_lifecycle*.py`. A quoted mention inside a
   summary/evidence string (how the quarantine notice cites the injected ids) is **not** backing;
3. else a controller-authority card is `UNBACKED_CONTROLLER`; lead/worker downward cards
   (`DOWNWARD_LEAD`/`DOWNWARD_WORKER`) are expected to be absent from the accepted stream by design.

Authority is attacker-controlled, so it is corroborated by S2–S6: malformed controller prefix,
duplicate id, within-file timestamp inversion, missing `event_id`, and class-axis membership.
`mtime_delta_s` (claimed `created_at` minus containing-file last write, +120 s tolerance) is
recorded as **context only** — forward clock skew is fleet-wide and the signal fires on legitimate
fan-out cards too.

## Result at T0 (209 cards, 45 files)

| classification | instances |
|---|---:|
| ACCEPTED_BACKED | 162 |
| DOWNWARD_LEAD | 41 |
| **UNBACKED_CONTROLLER** | **6 (4 distinct ids)** |

The three CF-30 ids are reproduced exactly — `human-pi-detector-fix-20260912T0100` (`astra-lead-audit.jsonl:24`),
`astra-detector-fix-0105` (`:25`), `astra-detector-patch-result-0112` (`:27`, and `astra.jsonl:3`) —
each quarantined, each only *mentioned* (never emitted) in lifecycle sources.

### New candidate found by the sweep: `astra-classsep-stabilize-0118`

| | |
|---|---|
| instances | `astra.jsonl:4`, `astra-lead-audit.jsonl:31` (`actor: astra`, `assignment`, `created_at 01:18:00`) |
| accepted stream | absent |
| emitter backing | absent (no `"event_id": "astra-classsep-stabilize-0118"` anywhere in `astra_lifecycle*.py`) |
| controller records | not mentioned (`record_mentioned = false`), not quarantined |
| duplication | exactly the same two controller inboxes as the 0112 injection (the only two `controller_inboxes_only` duplicates) |
| file mtime | both files last written `01:12:31`, i.e. cards written ~5.5 min **before** their claimed time |

This census does **not** assert forgery. It reports that at the pinned T0 bytes the card fails the
same backing test as the three quarantined CF-30 cards and carries the same corroborating pattern;
adjudication belongs to the controller (CF-30/REC-31).

### Context signals (reported, not treated as proof)

- **future-dated vs file mtime, 6 cards**: the two `stabilize-0118` instances (+328/+329 s) and four
  *legitimate* accepted fan-out cards (`flash-08/11/13/15.jsonl:1`, +577 s) — which is why the
  signal is context, not a verdict.
- **duplicate ids, 9**: 0 within-file; 2 controller-inbox-only (`0112`, `stabilize-0118`); 7 are
  normal multi-recipient fan-out.
- **timestamp inversions, 7**: 2 in `astra-lead-audit.jsonl` (25→26, 27→28) and 5 identical
  fan-out-ordering inversions in `deepseek-flash-{06,08,11,13,15}.jsonl` (2→3).
- **malformed controller prefix, 1**: `astra.jsonl:2` (`human-pi-overnight-20260912T0042n` prefix +
  `human-pi-detector-fix-20260912T0100` payload) — the CF-28 line, still quarantined.
- **non-event object, 1**: `astra-lead-literature.jsonl:8` is a worker report payload
  (`{from, key_findings, merge_command, ...}`), not a protocol event.
- **class axis, 0 violations** after splitting semicolon-joined id lists; no card binds a class
  outside the four frozen classes.

## What is not claimed

Not a gate verdict, node status, review verdict, adoption or rollback. No canonical, inbox or
quarantine byte was written; no detector write. `actor`/`authority` is attacker-controlled, so S1
is corroboration, not proof of authorship. The residual (no unbacked card beyond the four ids) is a
statement about the pinned T0 bytes only, not about future writes. No review verdict on any agent.

## Falsifier

Withdrawn if at the pinned T0 hashes: (a) any legitimate controller card that is accepted-stream or
emitter-backed is classified `UNBACKED_CONTROLLER`; (b) any `ACCEPTED_BACKED` card lacks its id in
the accepted stream; (c) any of C1–C11 or R1–R5 misses; (d) the three CF-30 ids are not reproduced
by S1+S2+S3; (e) any pinned input hash differs T0 vs T1 or the two passes differ in digest.

## Artifacts

| path | sha256 (12) |
|---|---|
| `inbox_provenance_census.py` | `601c9900e73a` |
| `census.json` | `868f5d7b2f46` |
| `PREREGISTRATION.md` | `7d43937802da` |
| `CHECKPOINT.json` | see manifest |
| `manifest.json` | see file |

Machine output: 209 card rows, 11 controls, 5 real expectations, input pins for 45 inbox files +
`events.jsonl` + 30 lifecycle sources + 3 quarantine files, digest `1e8c67dc7218`, `T0 == T1`.
