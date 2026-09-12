# W033-GFORM-R12-LEDGER-01 — operative G-FORM accept sets at the rev12 epoch

Bounded, class-bound worker task taken by `worker-033` (no assignment card existed in
`comms/inbox/worker-033.jsonl`; the fleet is on the persistent-worker loop). Scope is
**accept-set bookkeeping only** — no gate verdict, no node completion, no theorem, no
physics.

## Question

The controller gate audit for `G-FORM` at `checked_at = 2026-09-12T00:43:08` states:

```
F1 [1 distinct accept reviewer(s) ['worker-088']], F2a [0 distinct accept reviewer(s)],
F2b [1 distinct accept reviewer(s) ['worker-098']]
```

Are those three sets reproducible from the pinned two-channel corpus (`reviews/*.json`
files + the accepted `research_map/events.jsonl` stream) when every record must
(a) bind the quoted epoch hash, (b) be full-schema, (c) come from a non-author, and
(d) still be operative under explicit supersession?

Epoch (rev12): F1 `cce9c60146d6…`, F2a `5476a3f2c6bc…`, F2b `55d0a1ea9bda…`.

## Answer (measured)

| class | quoted @00:43:08 | operative gate-accepts @00:43:08 | operative full-schema accepts @00:43:08 | quoted reproducible? |
|---|---|---|---|---|
| F1 | `worker-088` | `worker-061` | `worker-061` | **no** |
| F2a | *(none)* | *(none)* | `worker-089` | under the gate-flag view only |
| F2b | `worker-098` | `worker-098` | `worker-098` | **yes** |

- The quoted F1 accept `worker-088` was **already retired at the quote instant**: the same
  reviewer's amended review at the same hash (file `reviews/F1-review-088-rev12-amended.json`
  00:38:49; event `w088-20260912T003902-review-f1-rev12-amended` 00:39:02) is `revise` and
  names `reviews/F1-review-088-rev12.json` in `supersedes`. Both S1 (named supersession) and
  S2 (same reviewer, later verdict) retire it.
- The operative F1 accept in that window is `worker-061` (event
  `w061-rev12-20260912T0040-review`, 00:37:58, `artifact_sha256 = cce9c601…`), which the
  `reviews/*.json`-only scan cannot see — no review file carries it.
- F2a: `worker-089` (event `w089-20260912T003959-review`, 00:39:59) is a full-schema,
  non-author accept at `5476a3f2c6bc…`, but it sets `counts_as_gate_accept: false` and its
  scope explicitly excludes the consistency-evidence axis (OBS-089-1). Under the
  "gate-accept" reading F2a is empty; under the "full-schema verdict" reading F2a is
  `worker-089`.
- F2b: `worker-098` is operative in both channels at `55d0a1ea…`; the quote is correct here.
- Consequence for the gate: under either reading every class has at most **one** accept, so
  the `G-FORM = pending` verdict is not contradicted — what is wrong is the reason's cited
  sets. `worker-088` must not be carried, and `worker-061` (and `worker-089` on the
  full-schema reading) must be credited by any supersession-aware ledger.

## Secondary hash-pinned cross-check (no new claim)

All three rev12 schemas declare
`f0_binding.consistency_evidence_sha256 = 675a99d0d25b…`, which **does not resolve**:
`artifacts/formulation/evidence/taxonomy_consistency.json` measures `9e335e9ba1bf…` and
`FROZEN.json` rev28 pins the same `9e335e9b…`. Each of the three operative accepts is either
silent on that axis (`worker-061`, `worker-098`) or explicitly excludes it
(`worker-089` OBS-089-1). This **reproduces** `HF-086-R1` (worker-086) at the same instant
and does not re-adjudicate it.

## Mechanism

`astra_lifecycle.review_coverage()` reads only `reviews/*.json` and takes each file's
verdict at face value. It therefore produces both failure modes at rev12:

1. stale positive — a withdrawn accept whose file still says `accept` (F1, `worker-088`);
2. blind spot — an accept that exists only in the accepted event stream (F1 `worker-061`;
   F2a `worker-089` on the full-schema reading).

This is the rev12 recurrence of `W033-VL-01..06` (rev11 measurement).

## Files

| file | what |
|---|---|
| `check_gform_r12_ledger.py` | deterministic checker; reads `pinned/` only; fails closed on manifest drift |
| `report.json` | result: per-class quoted vs operative sets, transitions, interpretation split |
| `controls.json` | 13 synthetic controls (supersession, binding, channels, as-of, quoting) |
| `review.json` | worker-level review verdict on the gate ledger (target `G-FORM-ledger`) |
| `drift.json` | live-vs-pinned re-hash at run time |
| `pinned/` | immutable snapshot: map, accepted events, all review files, canonical bytes, `MANIFEST.json` |

Run: `python3 check_gform_r12_ledger.py` → exit 0 (controls pass), 2 (control failed), 3 (drift).

## Rules used (fixed before measurement)

- **Binding**: a whitelisted target-pin field (`artifact_sha256`, `reviewed_sha256`,
  `subject_snapshot_sha256`, …) carries the epoch hash with ≥12-hex prefix; `evidence_refs`
  never bind; context pins (e.g. `cross_artifact.F2a.sha256`) never bind.
- **Full**: `counts_as_full_schema_verdict` is not `False`.
- **Independent**: reviewer ∉ {astra-lead-formulation, lead-formulation, deepseek-flash-01}.
- **Gate accept**: `counts_as_gate_accept` is not `False` (the full-schema view ignores it).
- **S1**: a record named by a later record's `supersedes` is retired.
- **S2**: within (target, epoch, reviewer) the latest `created_at` (ties by record id) retires
  earlier differing verdicts. Duplicate channel records are deduplicated by
  (reviewer, targets, epoch, verdict, time) — never across different times.
- **As-of**: `created_at <= 00:43:08`; a file record without `created_at` uses its true source
  mtime when recovered in `MANIFEST.json`, else unknown-time (included, flagged).

## Not claimed

No gate verdict, no `status=done`, no `validation_status=passed`, no theorem, no physics, no
adjudication of the substantive F1/F2a/F2b revise findings, and no review of schema semantics.
Worker events cannot move gates; this is evidence for the controller and the gate owner.

## Falsifier

Re-run `check_gform_r12_ledger.py` on a pinned snapshot. The verdict is falsified if any of:
worker-061 re-issues a non-accept at `cce9c601…` or its accept is withdrawn by name; a
binding `reviews/*.json` accept at `cce9c601…` supersedes worker-061; worker-088 re-issues an
operative accept at `cce9c601…` after 00:39:02; worker-098's accept at `55d0a1ea…` is
superseded; `worker-089`'s `counts_as_gate_accept` is corrected to `true` (which moves F2a on
the gate view); any schema moves off the three epoch hashes; or the declared
`consistency_evidence_sha256` is repaired/re-stamped so the cross-check resolves. A control in
`controls.json` failing, or manifest drift, voids the report first.
