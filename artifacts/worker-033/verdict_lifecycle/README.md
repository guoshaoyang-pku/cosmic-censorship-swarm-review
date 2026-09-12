# W033-VERDICT-LIFECYCLE-01 — operative accept sets for the G-FORM classes

Bounded, class-bound worker task (worker-033). Classes: `AF-WCC-VAC-GEN` (F1),
`AF-SCC-C2-VAC-GEN` (F2a), `AF-SCC-C0-VAC-GEN` (F2b). Secondary observation with
the same instrument: F0 (`AF-WCC-SCALAR-SPH` among others).

**Not a gate verdict, not a node transition, not a theorem.** Worker events cannot
set `status=done`, `validation_status=passed`, or a gate verdict.

## Question

At the G-FORM canonical hashes, which reviewer verdicts (a) bind the measured
artifact hash, (b) are full-schema, (c) are independent of the artifact author,
and (d) are still **operative** — not withdrawn or superseded by a later verdict
from the same reviewer, or by an explicit supersession/correction record?

## Why the controller's scan can be wrong in both directions

`research_map/astra_lifecycle.py:review_coverage()` reads only `reviews/*.json`
and takes each file's `verdict` at face value. It has no supersession model and
cannot see verdicts written only to the accepted event stream. This bundle
measures both channels and applies three supersession rules (see the checker
docstring). Consequences measured on the pinned snapshot:

* **stale positive** — a withdrawn accept still sitting in its review file is
  counted as an accept;
* **false negative** — an accept that exists only as an event (never written to
  a review file) is invisible to the scan.

## Pinned inputs

`pinned/` holds byte copies of `research_map/events.jsonl`, `reviews/*.json`
(93 files), the four canonical artifacts, `FROZEN.json`, the two controller
lifecycle reports (`controller_lifecycle_002440.json` = the quoted 00:24:40 gate
reason; `..._003316.json` = the post-republication reason), the map's extracted
`controller_gate_audit.json`, and the worker-047 / deepseek-flash-07 outbox
records carrying the withdrawals. `SHA256SUMS` covers every pinned file
(134 entries). `report.json` is a pure function of the pinned inputs (re-running
is hash-stable); `drift.json` holds the timestamped live-census / drift
observation, which is not part of the pinned claim. Re-run:

```bash
python3 check_verdict_lifecycle.py   # reads pinned/ only; writes report.json, controls.json
```

## Headline results (pinned snapshot; rev11 = pre-republication epoch)

| target | rev11 hash | accept set quoted at 00:24:40 | operative at rev11 | current-rev12 operative |
|---|---|---|---|---|
| F1  | `9a8bd4c96800` | `{astra-lead-audit}` | `{worker-026}` (1) | `{}` |
| F2a | `b6123750b37d` | `{astra-lead-audit, worker-047}` | `{worker-050, worker-069, worker-072, worker-078, worker-098}` (5) | `{}` |
| F2b | `1bb78ce9b357` | `{astra-lead-audit, deepseek-flash-07, deepseek-flash-17, worker-030}` | `{worker-001, worker-096, deepseek-flash-17, worker-030, worker-089}` (5) | `{}` |

Current hashes at pin time: F1 `cce9c60146d6`, F2a `5476a3f2c6bc`, F2b `55d0a1ea9bda`,
F0 `0abb9ed8a961`. Live canonical hashes re-measured after the run: identical
(no target drift). Five bound verdict records exist at the current hashes — all
`revise` (worker-088 ×2 on F1; worker-096 scoped and worker-005 on F2a;
worker-005 on F2b) — so no current-epoch accept exists.

## Findings (each with its falsifier)

* **W033-VL-01 (F2a bookkeeping).** Both F2a accepts quoted in the 00:24:40 gate
  reason are withdrawn at the same hash: `astra-lead-audit` by its own
  `reviews/F2a-review-lead-audit-r2.json` (`supersedes_review`: "the accept
  written at 00:22 is withdrawn", 00:25:15), and `worker-047` by its own event
  `w047-20260912T0030-d0x-review-f2a` (`supersedes_review`: "the accept issued at
  00:22:43 at this hash is withdrawn", 00:30:19) while
  `reviews/F2a-review-047.json` still says `accept`. *Falsifier:* any pinned
  record in which either reviewer re-issues an accept at `b6123750b37d` after
  00:30:19.
* **W033-VL-02 (F2b).** Of the four quoted accepts, `deepseek-flash-07`'s accept
  is superseded by its own corrected `reviews/F2b-review-07.json`
  (`supersedes.event_id = w07-review-F2b-rev11-20260912T0024`), and
  `astra-lead-audit`'s accept is declared withdrawn by
  `reviews/F2b-review-lead-audit-r2.json`. Two survive
  (`deepseek-flash-17`, `worker-030`) plus three event-only accepts. *Falsifier:*
  a pinned record re-issuing either withdrawn accept at `1bb78ce9b357`.
* **W033-VL-03 (F1 is the real rev11 shortfall).** The single quoted F1 accept
  (`astra-lead-audit`) is withdrawn by `reviews/F1-review-lead-audit-r2.json`;
  the operative set is `{worker-026}` = 1, below the two-accept criterion.
  `worker-031`'s accept targets `schemas/f1_falsifier_tests.jsonl#c4c477adcb7a`,
  not the schema, so it does not bind. *Falsifier:* a pinned record in which
  worker-031 declares a full-schema F1 accept at `9a8bd4c96800`, or any second
  binding F1 full-schema accept at that hash.
* **W033-VL-04 (scan blind spot).** At quote time the event stream already held
  ≥4 binding F2a full-schema accepts (`worker-050`, `worker-072`, `worker-078`,
  `worker-098`; `worker-069` arrived at 00:25:00) and ≥3 F2b ones (`worker-001`,
  `worker-089`, `worker-096`) that `review_coverage()` cannot see. *Falsifier:*
  a `reviews/*.json` accept at those hashes by any of those reviewers.
* **W033-VL-05 (current epoch).** At the rev12 hashes the operative accept set is
  empty for all three classes; G-FORM must stay `pending` and no rev11 accept may
  be carried over. *Falsifier:* any review file or event created after the rev12
  republication that binds those hashes with an `accept`.
* **W033-VL-06 (mechanism).** Two independent defects in `review_coverage()`:
  no supersession model, single-channel read. *Falsifier:* a revision of
  `astra_lifecycle.py` that models supersession and reads the accepted event
  stream, after which scan A/B agree with the operative ledger — or a case where
  a claimed withdrawal is contradicted by a later same-reviewer accept.

## Controls and limits

10/10 synthetic controls pass (latest-wins retirement, declared withdrawal,
other-hash and unpinned non-binding, author exclusion, scoped exclusion, no
false supersession, event-only accept, duplicate-channel dedup, evidence_refs
non-binding); see `controls.json`. `report.json` carries the tool hash, pinned
manifest size, all bound records, retirements with rules, and per-target
reconciliation. Limits: binding uses only explicit target-pin fields (never
`evidence_refs`); scope decisions come from `counts_as_full_schema_verdict`;
findings bind the pinned hashes only. Adjacent, non-duplicative work:
`artifacts/worker-042/gate_scan_gap/` compares channel *presence* of accepts; this
bundle adds the supersession model and the operative-vs-quoted reconciliation.
