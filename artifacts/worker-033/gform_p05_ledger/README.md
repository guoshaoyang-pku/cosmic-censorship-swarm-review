# W033-GFORM-P05-LEDGER-02 — operative G-FORM accept sets at the pass-05 quote

Bounded, class-bound worker task by `worker-033`. Scope is **accept-set bookkeeping
only** — no gate verdict, no node completion, no theorem, no physics. This is the
pass-05 continuation of `W033-GFORM-R12-LEDGER-01`
(`artifacts/worker-033/gform_r12_ledger/`, tool sha `4e8c7e16dc4e`), reusing its
fixed rules.

## Question

The controller gate audit for `G-FORM` at `checked_at = 2026-09-12T00:51:24`
(astra-lifecycle pass 05, pinned map sha256 `ed28b714464e…`) states:

```
F1 [1 distinct accept reviewer(s) ['worker-088']], F2a [0 distinct accept reviewer(s)],
F2b [1 distinct accept reviewer(s) ['worker-098']]
```

Are those sets reproducible from the pinned two-channel corpus (`reviews/*.json`
files + accepted `research_map/events.jsonl`) once every record must (a) bind the
quoted epoch hash, (b) be full-schema, (c) be non-author, and (d) still be
operative under supersession? And under the controller's *own* counting rule —
the one published in the G-F0 pass reason at 00:48:43 ("5 distinct accept
reviewers") — which classes already meet the two-distinct-accept criterion?

Epoch (rev12): F1 `cce9c60146d6…`, F2a `5476a3f2c6bc…`, F2b `55d0a1ea9bda…`.

The quote under review is frozen from its controller report
`runtime/state/controller_verification/lifecycle_20260912-005124.json`
(`astra-lifecycle-05-final2`, file sha256 `45b72957bc52…`, map after
`ed28b714464e…`); the G-FORM reason string hashes to
`1b0c7df205a74b31…` and the G-AUDIT reason to `a73662fbc1b0…`, both asserted at
extraction against constants (control C16).

## Answer (measured, 17/17 controls)

| class | quoted @00:51:24 | file-only scan | two-channel full-schema | two-channel gate-accept | quote reproducible? |
|---|---|---|---|---|---|
| F1 | `worker-088` | `worker-088` | **`worker-061`** | `worker-061` | **no** (either view) |
| F2a | *(none)* | *(none)* | `worker-089` | *(none)* | gate view only |
| F2b | `worker-098` | `worker-098` | **`worker-089`, `worker-098`** | `worker-098` | gate view only |

Criterion reading (same rule as the G-F0 pass): full-schema accept reviewers
bound to the measured hash → F1 1, F2a 1, F2b **2**. **F2b already meets the
two-distinct-accept criterion at `55d0a1ea9bda`; the file-only scan reports 1.**

- **F1 wrong in both views.** The quoted `worker-088` accept was retired at the
  quote instant by the same reviewer's amended review at the same hash (file
  `reviews/F1-review-088-rev12-amended.json` 00:38:49; event
  `w088-20260912T003902-review-f1-rev12-amended` 00:39:02, verdict `revise`, S1
  `supersedes` on the accept file, and S2 same-reviewer-later). The operative F1
  full/gate accept is `worker-061` (event `w061-rev12-20260912T0040-review`,
  00:37:58, `artifact_sha256 = cce9c601…`), which no `reviews/*.json` carries.
- **F2b material delta vs pass 04.** At pass 04 (00:43:08) F2b had one accept
  (`worker-098`). At 00:48:09 `worker-089` published an independent, full-schema
  accept bound to `55d0a1ea9bda` (`w089-20260912T004809-review`, controls
  M1–M14 all caught, baseline passed). It sets `counts_as_gate_accept=false`
  (scope excludes the stale consistency-evidence pointer, OBS-089-2), so the
  gate-accept view stays at 1 while the full-schema view reaches 2. Whether that
  flag blocks the count is a lead-audit decision, not a worker call; the
  controller's published code does not consult it.
- **F2a split by reading.** Quoted `{}` is reproducible under the gate-accept
  view; the full-schema view has `worker-089` (`w089-20260912T003959-review`,
  00:39:59, `counts_as_gate_accept=false`, explicitly excludes the
  consistency-evidence axis) — still one accept.
- **Mechanism (pass-05 recurrence of W033-VL-01…06).**
  `astra_lifecycle.review_coverage()` (`research_map/astra_lifecycle.py:176`)
  reads `reviews/*.json` only and at face value, so the reason still emits a
  stale positive (withdrawn F1 accept) and an event-only blind spot (worker-061
  F1; worker-089 F2a/F2b). A supersession-aware two-channel ledger is required
  before the next gate reason is quoted.
- **Secondary cross-check (reproduces HF-086-R1, no new claim).** The three
  rev12 schemas declare `f0_binding.consistency_evidence_sha256 = 675a99d0d25b…`,
  which resolves nowhere; `artifacts/formulation/evidence/taxonomy_consistency.json`
  and `FROZEN.json` pin `9e335e9ba1bf…`.
- **Epoch delta after the quote (no claim about the new epoch).** By
  `checked_at = 2026-09-12T00:55:13` the measured canonical hashes moved to rev13
  (F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`) and the live scan
  reports 0 accepts for all three. The rev12 findings above are historical for the
  00:51:24 quote; this report makes no rev13 coverage claim, and the two-channel
  ledger would need a fresh binding pass at the new hashes.

## Files

| file | what |
|---|---|
| `ledger.py` | deterministic extractor + checker; `--extract` pins the corpus, default verifies manifest, runs controls, writes report/controls; fail-closed (exit 2 control failure, 3 manifest drift) |
| `report.json` | per-class quoted vs file-only vs two-channel sets at 00:43:08, 00:51:24 and latest; operative/retired records; criterion counts; epoch-move delta; findings |
| `controls.json` | 17 synthetic controls (channels, S1/S2, binding, as-of, author, flags, dedup, F2b flip, manifest tamper, frozen-quote provenance, live-delta presence) |
| `review.json` | worker-level `revise` verdict on `G-FORM-ledger#p05` (hard failures P05-HF-01/02/03) |
| `pinned/` | immutable snapshot: `records.json` (all relevant review records from both channels), `quoted.json` (frozen pass-05 quote + provenance + live-map quote), `sources.json`, `MANIFEST.json` (self-hashes, source hashes, quote assertions) |
| `SHA256SUMS` | hashes of every published file |

Run: `python3 ledger.py --extract && python3 ledger.py`.

## Rules used (fixed before measurement)

- **Binding**: a whitelisted target-pin field (`artifact_sha256`, `reviewed_sha256`,
  `subject_snapshot_sha256`, …) carries the epoch hash with ≥12-hex prefix;
  `evidence_refs` never bind; context pins (e.g. `cross_artifact.F2a.sha256`) never bind.
- **Full**: `counts_as_full_schema_verdict` is not `False`. **Independent**: reviewer
  ∉ {astra-lead-formulation, lead-formulation, deepseek-flash-01}. **Gate accept**:
  `counts_as_gate_accept` is not `False` (reported; the controller's distinct-accept
  count does not consult it).
- **S1**: a record named by a later record's `supersedes` is retired. **S2**: within
  (target, epoch, reviewer) the latest `created_at` (ties by record id) retires
  earlier differing verdicts. **Duplicate**: same reviewer+target+epoch+verdict+time
  over two channels is one record with channel provenance.
- **As-of**: `created_at <= instant`; a file record without `created_at` uses its true
  source mtime recorded at extraction, else unknown-time (included, flagged).

## Not claimed

No gate verdict, no `status=done`, no `validation_status=passed`, no theorem, no
physics, no adjudication of substantive F1/F2a/F2b findings, and no review of schema
semantics. Worker events cannot move gates; this is evidence for the controller, the
gate owner and lead-audit.

## Falsifier

Re-run `ledger.py` on a pinned snapshot (controls fail-closed). The report is
falsified if any of: worker-061's F1 accept is withdrawn or a binding
`reviews/*.json` accept at `cce9c601…` supersedes it; worker-088 re-issues an
operative F1 accept at `cce9c601…` after 00:39:02; worker-089's F2b accept at
`55d0a1ea…` is superseded/withdrawn, is shown not to bind that hash, or its
`counts_as_full_schema_verdict` is corrected to false; worker-098's F2b accept is
superseded; the quoted G-FORM reason is corrected to the two-channel sets; or any
schema moves off the three epoch hashes.
