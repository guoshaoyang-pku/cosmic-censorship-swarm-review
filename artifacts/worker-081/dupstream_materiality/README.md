# W081-DUPSTREAM-MATERIALITY-01 — duplicate-event materialisation census

worker-081, bounded read-only task, 2026-09-12 ~01:22–01:25 (+08:00).
Node F0,F1,F2a,F2b,N0,L1 · gate G-FORM (G-NUM/G-LIT as probe surfaces only) ·
classes AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH.

No inbox card existed for slot worker-081 (fleet instance 2026-09-12T01:19); the task was
self-selected from the live queue after reading `research_map/ASTRA_HANDOFF.md` (pass 08),
`comms/PROTOCOL.md` and the live map. No canonical file was written; `numerics_lock` stays
LOCKED; no node status, validation status or gate verdict is set.

## Question

Does content-duplicate upward-event emission (same payload modulo
`event_id`/`created_at`/`_received_at`) materialise as duplicate state inside
`research_map.json`, and does it contaminate gate-relevant counts?

Why now: at 01:15:54 the formulation lead self-reported one duplicate emitter batch and at
01:17:14 measured its impact as *"ledger bookkeeping over content-identical payloads, not
duplicated map state"*, recommending no rollback. That containment claim had been checked by
its author only, for its own batch only.

## Method (deterministic, stdlib only, read-only)

1. **Pin** sha256 of `research_map/events.jsonl`, `research_map/research_map.json`,
   `comms/rejected.jsonl`, `comms/outbox/astra-lead-formulation.jsonl`, `numerics/gates.py`,
   `numerics/CONVERGENCE_PROTOCOL.md`; snapshot the two corpora into `pinned/` so the report
   is re-runnable. Census binds to the snapshot bytes; live drift after the run is recorded.
2. **Fingerprint** every accepted-stream event as
   `sha256(json.dumps(body, sort_keys=True, separators=(',',':')))` with
   `{event_id, created_at, _received_at}` removed (emission/ingest metadata). Secondary strict
   arm removes only `{event_id, created_at}`.
3. **Materialisation**: scan every list-valued top-level map section for dict entries carrying
   a top-level `event_id`; map `event_id -> [{section,index}]`.
4. A duplicate group is **DOUBLED** iff ≥2 distinct member ids are materialised, or one id is
   materialised twice (`apply_events` idempotency failure).
5. **Adjudicate** the lead's batch against its own falsifier.
6. **Probe** the CF-31 named F2b reviewers (worker-052/071/072/090) for duplicate membership.
7. **Probe** `numerics/gates.py::_protocol_review` on a pinned byte-copy under live
   event_id dedup vs content-fingerprint dedup (first-wins and last-wins).
8. **Eight controls** (synthetic positive/negative, single-char mutation, ledger-only,
   determinism, malformed line, empty stream, pinned-gates module control). 8/8 PASS.

## Headline measurements (pinned corpus)

| quantity | value |
|---|---|
| accepted-stream events | 8122 |
| content-duplicate groups (declared fingerprint) | **133** (311 ids) |
| groups with ≥2 materialised members (**doubled map entries**) | **15** (34 materialised ids) |
| — by event type | claim 6, review 8, resource_request 1 |
| — by node | F2a 4, F0 1, F1 1, F1/F2a/F2b 1, F2b 1, N0 1, L1 1, none 5 |
| same `event_id` repeated inside the stream | 8 ids (`w094f-cf21rev13-20260912T011015-*`, ×2) — these did **not** double-materialise (apply dedups by id) |
| strict-fingerprint sensitivity arm | 61 groups / 150 ids / 7 doubled |

Doubled groups include, e.g.: `claims[229]/[230]` (w040 F1), `claims[272]/[273]/[281]` (w037),
`claims[263]/[271]` + `reviews[403]/[412]` (w035 F2a), `claims[382]/[386]` + `reviews[524]/[530]`
(w092 F2a), `reviews[312]/[324]/[327]` (w038 F0 accept ×3), `reviews[414]/[415]` (w082 F0
accept), `reviews[514]/[515]` (w067 N0 accept), `reviews[121]/[125]/[129]` (w090 F1 review ×3),
`resource_requests[10]/[11]/[13]` (flash-10), `claims[476]/[482]` (w001 F2b).

## Verdicts

- **V1 — the formulation lead's batch is contained: CONFIRMED.** 14/14 accepted ids in
  `applied_event_ids`; 0 entry-level materialisations; all 7 pairs body-identical. The only
  reference outside the ledger is the disclosed textual mention in
  `claims[531].supersedes_rejected` naming both rejected `-122` ids.
- **V2 — the generalisation "duplication is ledger bookkeeping, not duplicated map state":
  REFUTED for the population.** 15 groups / 34 ids are materialised as distinct map entries
  with distinct `event_id`s. Distinct ids are exactly what the `event_id`-keyed idempotency
  ledger cannot catch.
- **V3 — duplicate emission does NOT explain the CF-31 F2b accept/revise divergence.**
  0 of the four named reviewers' F2b-targeted review ids are duplicate-group members.
- **V4 — the `_protocol_review` headline is invariant under content dedup** (reviewed=true,
  contest=true, 5 accepting / 5 dissenting under live, first-wins and last-wins dedup). The
  dedup key is nevertheless defeated in principle by distinct-id re-emission; the known
  duplicate review pair (`reviews[514]/[515]`) targets a different N0 artifact, not the protocol.
- **V5 — a named CF-31 reviewer (worker-090) does carry a tripled review elsewhere**: three
  materialised F1 reviews (`reviews[121]/[125]/[129]`, 00:21:03/00:21:37/00:22:12) with one body.
  Any F1 review-coverage counter that counts review ids rather than distinct bodies is inflated
  by this group.

## Falsifier / reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-081/dupstream_materiality/census_dupstream_081.py --from-pinned
cat artifacts/worker-081/dupstream_materiality/replay_check.json   # replay_matches_primary: true
```

FALSIFIED if (a) the recorded `corpus_pins` do not re-hash, (b) any recomputed
duplicate-group / doubled-group / materialised-member count differs, (c) any member of a listed
doubled group is not body-identical to its siblings under the declared fingerprint, (d) any
CF-31 F2b-targeted review id is a duplicate-group member, or (e) the lead batch has an
entry-level materialisation outside `applied_event_ids[]`.

## Limits

- Binds to the pinned corpus bytes; the map and stream keep moving (`live_drift_after_run`).
- "Materialised twice" = two map list entries with one payload; it is not a gate verdict.
- Duplicate grouping is an equivalence under the declared fingerprint, not an intent finding.
- Worker evidence only: no node status, no `validation_status`, no gate verdict, no canonical edit.

## Files

`prereg.json` · `census_dupstream_081.py` · `report.json` (primary) · `report_replay.json` ·
`replay_check.json` · `README.md` · `SHA256SUMS` · `pinned/` (events, map, gates.py byte-copies).
