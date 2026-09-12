# W48-GFORM-COVERAGE-DRIFT-RECOUNT-01 (worker-048)

One bounded class-bound task, read-only outside this directory plus `reviews/` and `comms/outbox/`.

**Class binding:** F1 = `AF-WCC-VAC-GEN`, F2a = `AF-SCC-C2-VAC-GEN`, F2b = `AF-SCC-C0-VAC-GEN`
(schemas `schemas/af_wcc_vacuum.yaml#d9cebb9404b2`, `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3`,
`schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`; FROZEN `artifacts/formulation/FROZEN.json#815e08079aef`).

## Question

The published G-FORM gate reason is "coverage F1 4 accepts, F2a 3, F2b 0"
(`ASTRA_HANDOFF.md` pass 06; computed by `astra_lifecycle.review_coverage` at
`lifecycle_20260912-010117.json`). Two things can make that number wrong: the scan rule, and the
fact that `reviews/*.json` are mutable files that agents rewrite in place. This task re-implements
the scan, re-runs it at a pinned instant, and reconciles every pass-06 entry against live bytes.

## Result — snapshot `2026-09-12T01:11:00+08:00`

Corpus: 202 review files, digest `e16661b084ddf3b9…`; instrument
`research_map/astra_lifecycle.py#957c61e3eb0e5002`; report `53faf0cccd1de589…`.

| target | pass-06 full accepts | live R1 (controller-equivalent) | live R2 (extended binding) | reproducible? |
|---|---|---|---|---|
| F1 | 4 (045, 072, 075, 085) | 4 (052, 072, 075, 085) | **5** (+089) | count stable, **membership not** |
| F2a | 3 (017, 072, 075) | **2** (017, 072) | 2 | **no — 3 is stale** |
| F2b | 0 | **2** (090, 072) | **2** (090, 072) | **no — 0 is stale** |

1. **The published gate reason is stale in both directions inside ~10 minutes.**
   - `reviews/F2a-review-rev29-075.json` moved accept → revise at `01:03:36`, after the pass-06
     report was finalised at `01:01:17`. F2a is **2**, not 3.
   - `reviews/F2b-rev13-full-090.json` (worker-090, `01:08:56`) and
     `reviews/F2b-review-worker-072-rev29.json` (worker-072, `01:09:13`) are full accepts pinned to
     `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` with `hard_failures: []` and exact 64-hex
     target-bound pins. F2b is **2**, not 0. The pass-06 blocker "F2b ≥ 2" is discharged at live
     bytes; the decision-instant recount must confirm it (see caveats below).
   - F1 kept the count 4 only by coincidence: `F1-review-worker-045.json` moved accept → revise at
     `01:01:46` and `F1-review-rev13-052.json` (accept) landed at `01:01:45`.
   Review files carry no pin, so a coverage number is valid only at the instant it is measured and
   must travel with the review-corpus digest.
2. **Target-normalization blind spot (instrument defect, CF-9 family).**
   `_targets_in_review` only recognises exact node aliases (`F1`, `F2a`, `F2b`, `AF-*-VAC-GEN`).
   Reviews that name their target as `path#sha256` — the form the protocol itself asks for — are
   dropped: `reviews/F1-review-worker-089.json` (accept, target
   `schemas/af_wcc_vacuum.yaml#d9cebb9404b2`, `01:01:36`) is invisible to the controller, so it
   reports F1 4 where the extended rule reports 5. Symmetrically, the controller's F2b verdict
   census holds 2 entries where the extended rule finds 10 (all other 8 revise).
   `_explicit_pins` also drops dict-valued `reviewed_sha256` (control C2).
3. **Caveats carried with the F2b result (for the audit lead, not decided here).**
   worker-072 declares `blind: true`, `reviewer_role: independent non-author (authored no F2b
   artifact)`. worker-090 declares `blind: false` with disclosure (read the map review index and
   worker-061's scoped event before the verdict; no full-schema F2b body read), `counts_as_full_
   schema_verdict: true`, `reviewer_role: non-author of F0/F0R/F1/F2a/F2b`. worker-072's review
   omits `counts_as_full_schema_verdict`, which the controller rule treats as full — an explicit
   flag is advisable. Author independence and blind-status sufficiency are review-quality
   adjudications reserved to the audit lead.
4. **No over-counting found.** The extended rule adds no F2a/F2b accepts beyond the controller's,
   and only the one F1 accept backed by an exact 64-hex, target-bound pin.

## Method

`recount_coverage.py` (see file header):
- **R1** is a line-faithful re-implementation of `astra_lifecycle._targets_in_review` /
  `_explicit_pins` / prefix-12 match; control **C8** imports the controller's own
  `review_coverage` at the pinned instrument bytes and requires identical per-target full-accept
  and verdict file sets. It agrees (F1 4 / F2a 2 / F2b 2).
- **R2** adds, as a closed documented rule: target normalization via class id, node alias and
  artifact path (`path#hash`, `alias@hash`, comma/plus lists, dict targets), and pin extraction
  from a closed set of explicit binding keys including dict-valued `reviewed_sha256` and fragment
  hashes in target strings. **Prose is never harvested** (control C4 shows the naive full-text rule
  would count a mention with a mismatched pin).
- **R2e** additionally counts `evidence_refs` path#sha256 citations (sensitivity only; no delta).
- 10 controls, all flip as declared (C1–C8 semantic, C7 corpus stability, C8 controller oracle).
- Two runs at the same `--now` are byte-identical: `report.json` = `report_run2.json` =
  `53faf0cccd1de589…`.
- Instrument drift observed during the task: `astra_lifecycle.py` moved
  `032d4afcb061` → `e096b14beb6a` → `957c61e3eb0e`; an earlier snapshot at `e096b14beb6a` reported
  F2b 0 because the two F2b accepts had not yet landed. The oracle control was re-run at the final
  pinned bytes; the earlier snapshot is superseded, not deleted (see `../f1_rev13_closure_rerun/`
  for the prior task chain).

## Reproduce

```bash
python3 artifacts/worker-048/gform_coverage_recount/recount_coverage.py \
  --now 2026-09-12T01:11:00+0800 --out report.json
python3 artifacts/worker-048/gform_coverage_recount/recount_coverage.py \
  --now 2026-09-12T01:11:00+0800 --out report_run2.json
```

## Authority and limits

No gate verdict, no node transition, `validation_status=passed`, or canonical write. This is an
audit of an advisory controller scan, not a schema semantics review
(`counts_as_full_schema_verdict=false` in the review record). Author independence is reported as
distinct reviewer ids only. A later write to any review file is a new revision to re-run against,
not a falsifier of this snapshot.
