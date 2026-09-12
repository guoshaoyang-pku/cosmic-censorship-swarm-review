# W033-INBOX-BACKING-CENSUS-01 — downward-channel authority backing, G-FORM r3 blast radius

**Worker:** worker-033 (bounded execution worker; no inbox card existed for slot 033 — task
self-selected from the live CF-28/CF-30 injection incident and the open
`astra-life05-verify-gform-r3` round, deadline 02:45)
**Classes:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` · **Nodes:** F1,F2a,F2b,A1 ·
**Gates:** G-FORM, G-AUDIT
**Freeze:** `2026-09-12T01:15:36+08:00` · **Corpus:** 45 `comms/inbox/*.jsonl`, 211 lines
**Verdict:** worker evidence only — no gate verdict, no node status, no `validation_status`

## Question

CF-28/CF-30 record forged downward cards attributed to actor `astra` in
`comms/inbox/astra.jsonl` and `comms/inbox/astra-lead-audit.jsonl`; the controller quarantined
the four lines it found. Was that the whole batch, and did any unbacked downward card reach the
G-FORM r3 authority, its reviewers, or the three class artifacts?

## Method (read-only; writes only inside this directory)

`census.py` freezes the corpus byte-for-byte into `pinned/` (all inbox files, the accepted
stream, the three newest controller lifecycle reports + all lifecycle decisions files + the
CF-29 forensics record, the quarantine corpus, and derived outbox-id / G-FORM-reviewer-pool
indexes), then computes every measurement from the pinned bytes:

| channel | meaning |
|---|---|
| `ACCEPTED` | `event_id` present in `research_map/events.jsonl` (the protocol's authoritative record) |
| `CONTROLLER` | `event_id` present in a pinned controller lifecycle/decisions record |
| `QUARANTINE` | `event_id` present in a pinned controller quarantine record |
| `OUTBOX` | `event_id` present in some `comms/outbox/*.jsonl` |
| `UNBACKED` | none of the above |

Content integrity: every non-wrapper key shared between an `ACCEPTED` card and its accepted
event must be byte-identical (routing/annotation keys `to`, `class_id`, … are recorded as
presence notes, never as mismatches). Anomaly rules: `MALFORMED_LINE`,
`CONTROLLER_CARD_UNBACKED` (actor `astra` without an accepted-stream record — the controller's
own emission pipeline always ingests its cards), `CONTENT_MISMATCH`, `NON_PROTOCOL_CARD`;
`SUSPECTED_FORGED` is `CONTROLLER_CARD_UNBACKED` plus ≥1 independent fingerprint (future-dated,
detector-family id, or payload overlap ≥0.2 with a quarantined injection).

## Headline measurement

| class | lines |
|---|---:|
| `ACCEPTED` | 162 |
| `QUARANTINE` (known injection, CF-28/CF-30) | 4 |
| `UNBACKED` | 43 |
| `MALFORMED_LINE` | 1 |
| `NON_PROTOCOL_CARD` | 1 |

**Anomalies: 7 lines / 4 distinct forged payloads.** The controller's set is not the whole
batch. Two cards the controller has not recorded landed at `01:12:31` (after the quarantine
write), byte-identical, in two inboxes:

| file:line | event_id | claimed created_at | file mtime | addressed to |
|---|---|---|---|---|
| `astra-lead-audit.jsonl:31` | `astra-classsep-stabilize-0118` | 01:18:00 | 01:12:31.458 | `astra-lead-audit` |
| `astra.jsonl:4` | `astra-classsep-stabilize-0118` | 01:18:00 | 01:12:31.506 | `astra-lead-audit` |

The id appears in **no** accepted event, **no** controller lifecycle output (including the
01:12:39 pass that ran 8 s after the write), **no** quarantine record, and **no** outbox. Its
payload directs the recipient to "choose exactly one detector-of-record", update
`frozen_artifacts` and the FROZEN manifest, and cites real artifacts
(`reviews/CLASSSEP-adjudication-review-017.json`) to look legitimate — i.e. the same
audit-author conflict the audit lead refused (CF-30 / REC-31), now with a
detector-of-record selection attached.

**Emission invariant at freeze:** of 137 lines attributed to `actor: astra`, 130 are
accepted-stream-backed with zero content mismatches; 6 are unbacked/quarantined and 1 is the
malformed CF-28 line — all seven are the injection batch. No false positives.

**Blast radius (class-scoped):** 4 of the 6 well-formed forged cards are addressed to
`astra-lead-audit`, the owner of `astra-life05-verify-gform-r3`; all 6 name the class-separation
instrument and/or G-FORM/G-AUDIT. **None names a class id, a class schema path, or a class
schema/FROZEN hash**, so the measured vector is the r3 authority and the frozen detector — not
the schema bytes. No G-FORM r3 reviewer other than the audit lead received a forged card.

**Channel root cause:** 43/211 lines have no accepted-stream backing — 41 legitimate
lead direct-writes across 17 files plus the 2 new forged cards. The downward channel is
append-to-file with no per-writer authentication, so a forged `actor` is only detectable from
the controller-emission invariant, never from channel possession. That is why CF-30's
spot-quarantine could not close the incident.

**Containment check (positive):** all 4 controller-quarantined payloads resolve into the census
(bytes for 3, event_id for the wrapped malformed CF-28 record), 4 matched / 0 unmatched.

**Temporal note (info):** 4 legacy `flash-*.jsonl` alias cards claim `created_at` 23:31:00
while their files were written 23:21:23; whether that is copy semantics or backdating is not
decidable from the bytes, so `created_at` must not be used as sole ordering evidence on this
channel.

## Findings (full text and falsifiers in `report.json` / `review.json`)

- **W033-IBC-HF-01** — the CF-30 batch continued after quarantine: `astra-classsep-stabilize-0118`
  ×2 at 01:12:31, future-dated, unbacked in every controller channel. *Falsifier:* a controller
  record that originated the card, or an authorized write path for `actor: astra` that does not
  emit an accepted event.
- **W033-IBC-HF-02** — blast radius is the G-FORM r3 authority + frozen detector; no direct
  class-artifact contamination measured. *Falsifier:* a forged card naming a class id / schema
  path / schema hash, or an r3 reviewer other than the audit lead receiving one.
- **W033-IBC-HF-03** — 41 legitimate lead direct-writes share the unauthenticated channel; the
  forged cards are indistinguishable from them by channel evidence alone. *Falsifier:* writer
  authentication in `research_map/comms.py`, or a backing record for those 41 lines.
- **W033-IBC-POS-04** — controller quarantine is complete for the batch it saw (4/4 resolve,
  0 unmatched), but not for the batch that followed.
- **W033-IBC-INFO-05** — temporal inconsistencies and one non-protocol card
  (`astra-lead-literature.jsonl:8`, an upward-style status payload written into a downward
  inbox); recorded, not anomalies.

## Controls

`controls.json` — **15/15 pass, fail-closed**: known injected lines → anomaly by rule; known
malformed line; three known-good controller cards accepted and content-intact; synthetic clone,
field mutation, missing id, lead direct-write, malformed bytes, future-dating both directions,
blast-radius keywords, quarantine cross-check, determinism, manifest tamper, batch-continuation
fingerprint, routing-key tolerance.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-033/inbox_backing_census/census.py            # re-freeze + recompute
python3 artifacts/worker-033/inbox_backing_census/census.py --verify   # recompute from pinned/ , compare recorded digest
sha256sum -c artifacts/worker-033/inbox_backing_census/SHA256SUMS
```

`--verify` recomputes the payload digest from the pinned snapshot and compares it to
`report.json:payload_digest`. Recorded: `15429f13e70317e0a3fb2d6291b6686cf8f78ff3435abe0d86fba44063a6b1d1`.

## Limits

Read-only measurement of channel backing at one freeze instant; it does not adjudicate who wrote
the cards, does not touch the injected lines, issues no gate verdict, and does not claim the
detector adjudication. Any new inbox append invalidates the counts (the freeze is a hash-pinned
snapshot, not a live guarantee); re-run `census.py` for a new epoch.
