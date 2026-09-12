# W013-F2B-BINDING-CENSUS-01 — PRE-REGISTRATION (written before the census ran)

- **task_id**: `W013-F2B-BINDING-CENSUS-01`
- **worker**: `worker-013`
- **node_id**: `F2b`
- **class_id**: `AF-SCC-C0-VAC-GEN`
- **gate**: `G-FORM` (read-only measurement; this worker sets no gate verdict and no node status)
- **target**: the live `schemas/af_scc_c0_vacuum.yaml` as measured at run time (expected
  `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` per FROZEN rev29), plus
  controller finding **CF-31 / REC-39**: the hash-bound scan reports 4 full accepts at the F2b
  pin while the formulation lead's per-file census reports 0 accept / 7 revise.
- **why this task**: no assignment card exists for slot `worker-013`. CF-31 is the open blocker
  for any G-FORM movement ("No G-FORM movement until the binding table resolves the count") and
  both published methods disagree. An independent third census from bytes is the cheapest
  falsifiable way to resolve it. It is read-only and duplicates no canonical path.

## Deliverables (all under `artifacts/worker-013/f2b_binding_census/`)

1. `census_f2b_binding.py` — self-contained stdlib read-only census.
2. `corpus_snapshot_t0.json`, `corpus_snapshot_t1.json` — `reviews/*.json` file → sha256/mtime
   before and after the run, plus the live/FROZEN schema hashes at both times.
3. `binding_table.json` — one row per F2b review candidate with: file sha256, reviewer, verdict,
   explicit declared pins, exact/prefix match to the live hash, full-schema scope claim,
   hard failures and blocking flags, reviewer-latest flag, mtimes, D1/D2 carrier coverage.
4. `report.json` — counts under pre-registered rules **S**, **B**, **B2** (below), the revise-live
   set, the drift check, and the CF-31 adjudication.
5. `README.md`.

## Pre-registered rules (fixed before execution; no post-hoc tuning)

- **Rule S (controller scan rule, re-implemented)**: `verdict == accept` AND
  `counts_as_full_schema_verdict is not False` AND some explicitly declared pin prefix-matches
  the live hash (`live[:12]` either way). Counted per distinct reviewer.
- **Rule B (strict binding rule)**: `verdict == accept` AND an explicit declared pin equals the
  live hash **exactly** (64 hex) AND full-schema scope is **explicitly claimed**
  (`counts_as_full_schema_verdict is True`, or an explicit full-schema scope statement) AND the
  file is that reviewer's latest F2b verdict AND it carries no blocking hard failure.
- **Rule B2 (defect-aware binding)**: Rule B AND the file's own text addresses at least one of
  the two confirmed live defects W075R-D1 / W075R-D2 (carriers below). Reported as a separate,
  clearly labelled variant; it is the rule that matters for "does any accept cover the bytes as
  they stand", but it is a scope judgement, not a gate verdict.
- **Rule L (the other side)**: `verdict == revise` at an exact or prefix-bound live pin,
  per distinct reviewer, for comparison with the formulation lead's 7-file census.

Defect carriers in the live bytes (independently located before registration):

- **W075R-D1** — `implication_ledger.forbidden_transfers[*].reason` contains
  `"C2 is a strictly larger extension class"` while line 239 asserts
  `"E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"`.
- **W075R-D2** — `regularity.must_not_conflate[0]` contains
  `"No containment with C2 or C0 is asserted here"` while the same file asserts the containment
  at line 239. (Confirmed independently by worker-066/017/035/075/018/053 revise files and by
  worker-072's self-supersession note.)

## Acceptance tests (self-imposed)

- **A1** — Rule S reproduces the controller scan's accept set at the same corpus snapshot, or
  every divergence is explained row-by-row with the file bytes that cause it.
- **A2** — every `reviews/*.json` F2b candidate appears in the table with its own file sha256,
  so each classification is re-checkable from pinned bytes (no name-only citations).
- **A3** — Rule S / B / B2 counts and the revise-live set are computed mechanically by the
  script; the report claims nothing the table does not show.
- **A4** — the live schema hash is re-measured at t0 and t1; corpus drift is reported; the
  script writes only inside its own task directory.
- **A5** — exit 0; `report.json` carries the sha256 of `binding_table.json` and of the script;
  no gate verdict, no `validation_status: passed`, no node completion is claimed.

## Falsifier (pre-registered)

At the same corpus snapshot: any file that Rule S counts as an accept whose explicit declared
hash differs from the live schema hash, or any row whose verdict/scope/pin changes on a second
read of the same bytes, or unreported drift between the t0/t1 schema or corpus hashes, or a Rule
B accept set equal to the Rule S set (in which case the default-full/scope explanation of CF-31
is wrong and this report is falsified). Re-run `census_f2b_binding.py` at the cited pins: any
count differing from the report flips the census.

## Stop rule

One run. Report disagreements rather than forcing agreement. Stop at 1.5 agent-hours or at the
first clean run, whichever comes first. No canonical, frozen, or pinned byte is written.
