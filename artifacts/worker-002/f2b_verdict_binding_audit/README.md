# F2b verdict-binding ledger — W002-F2B-VERDICT-BINDING-AUDIT

Bounded, read-only forensic produced by `worker-002` / `deepseek-flash-02` for the audit
lead's `astra-life05-verify-gform-r3` adjudication (node F2b, class `AF-SCC-C0-VAC-GEN`,
gate `G-FORM`).

## What it is

`audit_f2b_bindings.py` scans every review event in `comms/outbox/**/*.jsonl` plus the
accepted stream in `research_map/research_map.json` for the round window that started when
the r3 card was issued (`2026-09-12T00:48:41+08:00`), keeps the events that target F2b, and
records for each: verdict, actor, timestamp, target classification, whether it cites the
live F2b hash `b2ab6acb2bbe…`, whether it names a specific field, whether it mentions the
two independently reported carriers, and its hard-failure / gate-blocking counts.

Live-bound accepts are tiered exactly against the card's acceptance text:

| tier | rule |
|---|---|
| A | live-bound + canonical `schemas/af_scc_c0_vacuum.yaml` target + self-declared `counts_as_full_schema_verdict` |
| B | live-bound + canonical target, no ancillary marker, not self-declared |
| C | live-bound but ancillary marker (coverage/candidate/repair/publication/…) or non-canonical target |
| D | not live-bound |
| E | row cites F2b but the verdict is about another node |

The report also records two mechanical adjudication signals that do not require reading prose:
`same_actor_flips` (an actor emitted a live-bound accept and later a live-bound revise at the
same hash) and `explicit_supersedes_rows` (events that name a superseded event id).

## What it is not

* Not a gate verdict, not a completion claim, not a merits judgement of any verdict.
* Not a replacement for the two independent reviewer verdicts the card requires; it only
  says which of the already-emitted verdicts are hash-bound to the live bytes.
* No canonical file is written. Detection of class leakage is **not** performed here; if a
  CLASSSEP measurement were made it must cite the detector hash it used (live restored
  `a8c04fc31e4a…`, frozen pin `c266dbecaa87…` — unresolved drift, CF-26/CF-29).

## Files

* `audit_f2b_bindings.py` — instrument (deterministic; ledger digest recorded in `report.json`)
* `ledger.json` — one row per F2b-targeting review event, with source file/line pointers
* `report.json` — counts, tiers, cross-check, method rules, falsifier
* `REPORT.md` — human-readable summary
* `CHECKPOINT.json` — task-level checkpoint
* `SHA256SUMS`

## How to falsify

Re-run the instrument (it is deterministic over the ledger rows) and check the falsifier
listed in `report.json`: live pin drift, an F2b-targeting event missing from the ledger, a
mis-classified binding/tier, a revise claimed field-naming with no field, or a non-empty
`map_primary_window_ids_not_in_ledger`. Any of these voids the corresponding count.
