# A0 rubric merge candidate (worker-16)

**Assignment:** `asg-2026-09-11-A0-deepseek-flash-16-25` — main author of `evaluation_rubric.yaml`;
acceptance: per-task-type verifiers, hard failures, evidence requirements, no universal scalar score;
"every acceptance line must name its evidence type"; submit with sha256; gate G-AUDIT.

**Status:** draft delivered as a merge candidate. `validation_status=unverified`. The canonical path
`evaluation_rubric.yaml` remains owned by lead-audit; this directory is not a completion claim for A0.

## Files

| file | role | sha256 (prefix) |
|---|---|---|
| `evaluation_rubric.extended.yaml` | merge candidate: owner revision + per-task-type acceptance lines | `0fda6c21d2afcd75` |
| `check_rubric.py` | structural validator V1–V7 | `e292c47bc784de414` |
| `validator_report.json` | report for the merge candidate | `ff9a5a07360d3714` |
| `validator_report.root_revision.json` | report for the owner's canonical revision | `fe68939d79ee4e06` |

## Provenance and the write race (recorded because it affects provenance)

1. 23:20 — owner staged a rubric at `artifacts/audit/evaluation_rubric.yaml`.
2. ~23:22 — this worker read that revision (sha256 `fa4aa6c79c53ec7f`) and wrote an extended
   revision to the canonical path `evaluation_rubric.yaml`, then began validating.
3. ~23:24 — the owner published their own revision to the canonical path, replacing the write.
   The canonical revision at merge time is `25808142ed60e885` (32 structural gaps, below).
4. This worker did **not** re-write the canonical path. The extension is submitted here for the
   owner to merge or reject.

## What the merge candidate adds (all owner content is preserved)

- `evidence_types` catalog (14 named types, each marked machine-checkable or reviewer-required).
- `task_types` T-SCHEMA / T-LIT / T-NUM / T-FORMAL, mapping the owner's `verifiers` block to
  33 acceptance lines (`S1–S8`, `L1–L7`, `N1–N8`, `F1–F5`); every line names `evidence_type`,
  `check`, `pass_condition`, `hard_failure_if` and `machine_checkable`.
- `gate -> task_type` mapping, and `G-FORMAL` promoted from "future" to a first-class pending gate.
- `HF-14 universal_scalar_score`, `HF-15 unnamed_evidence`, `HF-16 numerics_lock_violation`,
  `HF-17 missing_null_control` (owner's HF-01…HF-13 kept verbatim).
- Metric evidence bindings: `evidence_type`, `granularity`, `aggregation_across_classes: forbidden`,
  `accept_reject_role: diagnostic_only` on all seven owner metrics.
- `no_universal_scalar_score` converted from a prose string to a machine-checkable mapping with
  `enforced: true` and `forbidden_uses` (the owner's wording is preserved inside `statement`).
- `validation.structural_validator` contract (V1–V7).

## Validation evidence

| revision | validator result | evidence |
|---|---|---|
| merge candidate `0fda6c21` | **PASS** V1–V7 | `validator_report.json` |
| owner canonical `25808142` | **FAIL**, 32 errors | `validator_report.root_revision.json` |

Owner-revision gap categories (exact list in the report): missing `owner`/`status` (2), no
`task_types`/acceptance lines (4), `no_universal_scalar_score` not machine-checkable (1), seven
metrics without evidence binding / aggregation ban (21), four gates without `task_type` (4).

## Acceptance mapping

| assignment requirement | where satisfied |
|---|---|
| per-task-type verifiers | `task_types.*.verifier` + `verifiers` (owner's) |
| hard failures | `hard_failures` HF-01…HF-17 |
| evidence requirements | `evidence_types` + `evidence_rule` + `validation.structural_checks` |
| no universal scalar score | `no_universal_scalar_score` + HF-14 + V5 |
| every acceptance line names its evidence type | 33/33 lines have `evidence_type`; V3 |
| submit with sha256 | artifact event `w16-20260911T2327-a0-rubric-merge-candidate` |

## Next falsifier

Run `check_rubric.py` on the canonical file after the owner merges. Falsified if (a) the merge
candidate's PASS depends on weakening an owner line (diff the frozen revisions), or (b) a domain
reviewer shows an acceptance line's evidence type is not actually checkable by machine or by a
reviewer with named evidence, or (c) any composite scalar is used to accept/rank a node.

## Non-claims

Not an A0 completion, not a gate verdict, not a physics claim. `G-AUDIT` promotion requires the
owner's review and two independent reviewer verdicts with cited sha256.
