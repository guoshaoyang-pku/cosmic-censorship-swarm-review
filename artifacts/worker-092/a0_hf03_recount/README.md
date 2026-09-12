# W092-A0-HF03-STAGING-RECOUNT-01 (worker-092, bounded class-bound task)

**One-line result.** At `evaluation/A0_detector_scope_adjudication.json#a26be4b85706` and
`evaluation_rubric.yaml#d748a9e3574e`, an independent stdlib recount reproduces every declared
HF-03 per-file count exactly (15/15 files; 218 before / 194 kept-live / 17 excluded / 7 staging)
with all 15 affected file pins stable — and confirms that the audit lead's blocker card
`audit-l06-b3-staging-20260912T005926` states **1 HF-03 record** for the worker-07 staging batch
where the measured value is **7** (the artifact's own `staging_unresolved` says 7). The
rubric-literal HF-03 reading fires on **0 of the 194** kept-live rows, independently reproducing
the audit-lead-side discrepancy worker-021 measured.

## Why this task

No `comms/inbox/worker-092.jsonl` card exists. The open critical-path item is the A0 verdict
(`astra-life04-verify-a0`, lead-audit, deadline 02:00) whose evidence base is this adjudication
artifact. Two live claims about it disagree on a decisive number:

| source | claim |
|---|---|
| `comms/outbox/astra-lead-audit.jsonl#audit-l06-b3-staging-20260912T005926` | staging batch carries **1** HF-03 record (and 12 HF-14) |
| artifact `measured.hf03.staging_unresolved` | `batch-w07-sources.jsonl`: **7** records |
| `comms/outbox/worker-021.jsonl` (W021-A0-HF03-REPL-01) | measured **7**; b3 wrong |

This task is a third, independently written count, read-only on every canonical path.

## Method (no author code imported)

`recount_a0_hf03.py` re-implements both readings from their public text:

* **implementation reading** (what the canonical scan does): a record is a citation iff it has
  (`resolution_status` or `status`) and (`cite_key` or `source_id`); it fires HF-03 iff
  `source_meta` lacks any of `matter_model / cosmological_constant / dimension / symmetry`, or
  neither `source_meta.formulation` nor `record.formulation` is truthy.
* **rubric-literal reading** (`evaluation_rubric.yaml` HF-03): `resolution_status in
  {unresolved, contradicted}` or class-metadata mismatch against a claim class carried on the
  row.

The script parses `.json`/`.jsonl` with stdlib only, tags `_source` by repo-relative path, and
compares against the artifact's declared maps without using them as the predicate.

## Measured

| quantity | measured | declared | match |
|---|---:|---:|---|
| HF-03 before, 15 files | 218 | 218 | yes |
| HF-03 kept-live, 12 files (implementation) | 194 | 194 | yes |
| HF-03 excluded (historical/snapshot), 2 files | 17 | 17 | yes |
| HF-03 staging, `batch-w07-sources.jsonl` | 7 | 7 | yes |
| HF-14 staging, `batch-w07-theorems.jsonl` | 12 | (b3: 12) | yes |
| rubric-literal HF-03 on the 194 kept-live rows | **0** | not declared | — |
| per-file reproduction | 15/15 | — | yes |
| 15/15 affected file pins vs live bytes | stable | — | yes |

`b3` adjudication: `b3_text_defect_confirmed_7_not_1` — the "12 HF-14" half of the card is
correct; the "1 HF-03" half is not.

## What this does and does not claim

* It is an artifact/checker measurement, not a mathematics claim and not a gate verdict.
* It does **not** move node A0, `G-AUDIT`, `validation_status`, or any gate.
* It does **not** repair `b3` (owner: audit lead) or the artifact (owner: audit lead).
* The residual A0/rubric question remains a ruling, not a count: the surviving 194 are hits
  under a **major**-severity implementation predicate (absence of scope metadata), while the
  rubric's HF-03 branch is **critical** and predicate-different. That axis belongs to the
  rubric owner; this artifact only fixes the arithmetic on both sides of it.

## Falsifier

Re-run `recount_a0_hf03.py` at the same pins: falsified if any of the 15 per-file HF-03 counts
differs from the declared map, if the totals are not 218/194/17/7, if the staging source file
does not measure 7, if the staging theorems file does not measure 12, or if any of the 15 file
pins differs from the live bytes. Any write to
`evaluation/A0_detector_scope_adjudication.json` or `evaluation_rubric.yaml` voids the binding
(re-run against the new revision instead).

## Files

* `recount_a0_hf03.py` — independent re-implementation (stdlib only).
* `report.json` — full machine record: per-file counts, hashes, b3 quote and verdict.
* `../../reviews/A0-hf03-recount-worker-092.json` — scoped review of the b3 count axis.
* `../../../runtime/state/worker-092_A0_hf03_recount_checkpoint.json` — checkpoint.
