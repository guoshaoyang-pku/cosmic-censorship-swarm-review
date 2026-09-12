# W044-CF31-CROSSCHECK-01 — independent verification of the two CF-31 reconciliations

**Worker** `worker-044` · **node** F2b · **class** `AF-SCC-C0-VAC-GEN` · **gate** G-FORM ·
**created** 2026-09-12 ~01:48 +08:00 · **authority**: worker measurement only.

## What this is

CF-31 / REC-39 recorded that the controller's F2b coverage scan and the formulation lead's
census disagreed completely (4 full accepts vs 0 accept / 7 revise) at pin
`schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`.

This task is **not a third census**. While the pilot instrument below was running, two other
workers published reconciliations of CF-31:

- `reviews/CF31-F2b-binding-table-worker-017.json` (`worker-017`, 01:22:20)
- `reviews/F2b-coverage-census-018.json` (`worker-018`, 01:19:15)

CF-12 forbids duplicating an owned measurement, so this task re-scoped to an **adversarial
cross-check of the two published reconciliations**, including the falsifiers they declared.
The pilot run (executed before either artifact was read) is retained as independent corroboration.

## Method

1. `PILOT_report.json` — an independently written instrument (`recon.py`) that re-implements the
   controller's `astra_lifecycle.review_coverage` predicate, compares it to the live function,
   and measures file mutation. All 8 controls pass (K1–K5, K7–K9), including exact agreement with
   the live controller function.
2. `CROSSCHECK_PREREGISTRATION.json` — claims and classification rules, written before the
   cross-check script ran.
3. `crosscheck.py` / `crosscheck_report.json` — 10 tests (T1–T10) against the two artifacts,
   plus 5 controls (C1–C5). All controls pass; no inspected file changed during the run.

## Results

| test | claim under test | verdict |
|---|---|---|
| T1 | live pin-bound full-accept set is `{052, 071, 090}` | CONFIRMED |
| T2 | no pin-bound full accept exists outside that set | CONFIRMED |
| T3 | each listed accept is bound, accept, not scoped out | CONFIRMED_WITH_CAVEAT |
| T4 | `artifact_sha256`-keyed → 0 accepts; `reviewed_sha256`-keyed → 3 | CONFIRMED |
| T5 | key policy alone reproduces the lead's 0-accept/7-revise file set | **CORRECTION** |
| T6 | worker-072 accept→revise in place at 01:14:54, `created_at` preserved | CONFIRMED |
| T7 | every worker-017 table row matches its cited bytes (18/18) | CONFIRMED |
| T8 | worker-018 "no drift within run" (retrospective) | UNVERIFIABLE |
| T9 | no pin-bound accept added since the two censuses | CONFIRMED |
| T10 | pilot predicate agrees with both censuses | CONFIRMED |

### The correction (T5)

Worker-017's F3 says the artifact_sha256-keyed corpus "reproduces the 0-accept reading" of the
lead's census. The 0-accept *count* is explained (all three accepts bind through
`reviewed_sha256` only), but the artifact-keyed *file set* is not the lead's 7-file set: it omits
`reviews/F2b-bindchain-rev13-worker-035.json` and
`reviews/F2b-rev29-containment-rebase-worker-066.json`, both of which bind by `reviewed_sha256`
and are named in the lead's census. The lead's file selection therefore needs a second,
undeclared rule (target/scope), not key policy alone.

### The caveat (T3)

The accept count is 3 only under the controller's default-full rule
(`counts_as_full_schema_verdict is not False`). `reviews/F2b-review-rev13-052.json` carries no
explicit flag and no scope-out, so an explicit-`true` policy yields `{071, 090}`. Worker-017's
table discloses this as `default_full_flag_absent`; any gate text should keep the convention
attached to the count.

### The durable mechanism

`reviews/F2b-review-worker-072-rev29.json` was counted as a full accept in the 01:12:39
controller report and as a revise in the 01:16:26 report under the same filename; the live file
reads `revise`, mtime 01:14:54, `created_at` still 01:10:13, sha256 `5db91bb0781d`. A coverage
count is only valid at a named decision instant with per-file hashes, and the
corpus/predicate/flag-default terms must be declared with it.

## Deliverables (hashes in `CHECKPOINT.json` and the outbox artifact events)

- `PILOT_PREREGISTRATION.json`, `recon.py`, `PILOT_report.json`, `PILOT_record_matrix.json`, `PILOT_snapshot_pre.json`, `PILOT_stdout.txt`
- `CROSSCHECK_PREREGISTRATION.json`, `crosscheck.py`, `crosscheck_report.json`, `crosscheck_stdout.txt`
- this `README.md`

Cross-check digest: `de9e4b468484b43ee881a2c1cfac4874d9692d7a8c23ba21f584eab730052e79`
Pilot digest: `ff1b11fe62bddf8c6d7c2fd392c20a2b5ead317873f0e77b0fcabaed907ffc42`

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-044/cf31_f2b_recon/recon.py
python3 artifacts/worker-044/cf31_f2b_recon/crosscheck.py
```

## Falsifiers

- cross-check: a re-run at the same file hashes yielding a different digest or verdict; any
  inspected file changing hash during the run; a pin-bound full accept found outside
  `{052, 071, 090}`; or a worker-017 table row reported matching while its cited bytes differ.
- pilot: disagreement with the live `review_coverage` function; a record claimed invisible to the
  exact-alias term that normalizes to `F2b`; or the cited 072 accept entry missing from the
  01:12:39 report.
- all counts are void once F2b bytes move (rev14/rev30 is authorized); re-run at the new pin.

## Non-claims

No gate verdict, no node transition, no `validation_status=passed`, no adjudication of which
coverage count the r3 verifier must adopt. No schema, review, ledger, taxonomy, map or pinned
path was written. Credit for the two reconciliations belongs to `worker-017` and `worker-018`;
this task verifies them and corrects one sub-claim.
