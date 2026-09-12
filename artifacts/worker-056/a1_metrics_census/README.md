# W056-A1-METRICS-CENSUS-01 — A0 metric census over the accepted stream

**Worker:** worker-056 (no inbox card existed; one self-selected bounded class-bound task)
**Node / gate / classes:** A1 / G-AUDIT / `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
**Status:** worker-level measurement complete. **Not** an A0 rubric verdict, **not** a gate verdict, **not** a node transition. No canonical path written.

## Why this task

`evaluation_rubric.yaml` defines `metrics.class_binding` (target 1.0), `metrics.duplication`
(target <= 0.25) and `review_protocol.independence` (kappa >= 0.60, Kish ESS reported), and
G-AUDIT lists `duplicate_cluster_rate`, `hard_failure_rate`, kappa and independent replication
as criteria. At selection time the accepted stream had **0** occurrences of
`duplicate_cluster` and no measurement of any of these three definitions over the accepted
claim/review corpus (only rubric reviews quoting them). This task measures them at one pinned
snapshot, with a frozen pre-registration and fail-closed controls.

## Method (frozen before measurement)

Definitions, thresholds, controls C1–C10, exit codes and falsifiers F1–F6 are in
`PREREGISTRATION.json` (sha256 `ae615d86981a75255acf3285497f615a7f0c5d3934db037b8a4f2bb73776eb78`).
Inputs are copied to `raw/` and hash-pinned (`raw/PINS.json`); every number is re-derivable from
those bytes with `python3 run_metrics_census_056.py --check` (two consecutive `--check` runs in
this task returned identical `result_digest=78275fb47a88`).

- **Corpus**: 584 accepted claim events and 725 accepted review events in the pinned
  `events.snapshot.jsonl` (sha256 `57a00df9f9d2…`); 0 claim ids excluded by the rejected set.
- **M1** per the rubric's literal wording: tokens split on `;`; `SINGULAR_FROZEN` iff exactly one
  token and it is one of the four frozen ids.
- **M2** `novelty(text) = 1 - max shingle Jaccard`, k=5 word shingles, threshold 0.60 (HF-07).
- **M3** generalized Fleiss kappa over `(target_id, reviewed_sha256-or-_NO_HASH_)` groups with
  >= 2 distinct reviewers, plus a 2000-draw permutation chance-correction (seeded 20260912) and
  Kish ESS `n^2 / sum(n_r^2)`.

## Results (snapshot `events.snapshot.jsonl` sha256 `57a00df9f9d2…`)

| metric | value | target | verdict at this snapshot |
|---|---|---|---|
| M1 `class_binding` (frozen + singular) | **0.6849** (400/584) | 1.0 | not met |
| M1 `MULTI_FROZEN` class_id | 0.2860 (167/584) | — | reported |
| M1 `UNKNOWN` class_id (`GLOBAL`) | 0.0291 (17/584) | — | reported |
| M2 `duplication` (mean max-similarity) | **0.1022** | <= 0.25 | met |
| M2 `duplicate_cluster_rate` (>0.60) | **0.0685** (40/584) | <= 0.25 | met |
| M3 generalized Fleiss kappa | **0.2055** | >= 0.60 | not met |
| M3 hash-bound-only kappa (26 groups, robustness subset) | **0.1362** | >= 0.60 | not met |
| M3 Kish ESS (multi-review subset) vs nominal reviewers | **1.74** vs 147 | report, never nominal n | reported |
| D1 review-recorded hard-failure incidence (descriptive only) | 0.5628 (408/725) | <= 0.10 (canonical HF; see caveat) | not comparable |

M1 per singular class: `AF-WCC-VAC-GEN` 132, `AF-SCC-C0-VAC-GEN` 132,
`AF-WCC-SCALAR-SPH` 73, `AF-SCC-C2-VAC-GEN` 63.

M2 detail: 28 pairs above 0.60, 17 clusters, largest cluster 3, max similarity **1.0**
(exact-duplicate statements exist), median max-similarity 0.0223.

M3 detail: 386 distinct targets, 60 with >= 2 distinct reviewers (51.3% of all reviews),
300/725 reviews carry `reviewed_sha256`; 25/60 multi-review targets are unanimous;
`p_bar=0.6614`, `p_e=0.5739`, permutation null mean 0.5737 (sd 0.0390), `z=2.25`;
whole-corpus Kish ESS 86.6 vs 147 distinct reviewers.

## Findings (measurement, not adjudication)

- **W056-MC-F1 (major, decision-relevant).** Reviewer agreement on contested targets is far
  below the A0/G-AUDIT kappa target: 0.2055 primary, 0.1362 on the hash-bound-only subset,
  against 0.60. The permutation null confirms observed agreement is only ~2.25 sd above chance,
  and effective independence inside the contested subset is ~1.74, empirically confirming the
  rubric's own ESS warning. Any G-AUDIT claim that consensus supports a verdict needs this
  number, not nominal reviewer counts.
- **W056-MC-F2 (major).** The literal `class_binding` metric is 0.6849: 167/584 accepted claims
  declare multiple frozen classes in `class_id` and 17 declare `GLOBAL`. **Scope caveat:** many
  multi-class values are deliberate cross-class *scope* declarations, and whether they should
  count against the metric is the open BL-7-style scope ruling, which this task does **not**
  resolve. What is measured is that under the rubric's literal "frozen, singular" wording the
  metric is not 1.0.
- **W056-MC-F3 (minor).** Duplication is inside target at corpus level, but the 17 clusters above
  the HF-07 0.60 threshold (including exact-duplicate statements) are concrete HF-07 (major)
  candidates in the accepted stream, and no instrument in the accepted stream currently computes
  them (`duplicate_cluster` count in events.jsonl at selection: 0). Cluster membership is in
  `report.json` -> `results.M2.top_pairs` (top 10 pairs) and re-derivable via `--check`.
- **W056-MC-F4 (info).** 425/725 reviews (58.6%) carry no `reviewed_sha256`; revision-agnostic
  grouping can only depress agreement, which is why the hash-bound subset is reported. The
  direction of F1 survives the stricter cut.

## Controls, amendments and bring-up provenance

All 12 pre-registered controls pass (`controls.status=PASS`); C8 pin guard clean over the run.
The instrument's own controls caught three real defects during bring-up, each preserved and
fixed **before** the reported measurement, with amendments filed before each rerun:

1. `AMENDMENT-01.json` — C6 was mis-calibrated for a 10x2 design (see below); replaced by
   C6a/C6b/C6c.
2. `AMENDMENT-02.json` — C6c's single-draw central-95% rule has a 5% false-failure rate and
   fired (observed draw rank 7/2000, 0.35th percentile); replaced by a pre-declared 3-sigma
   plausibility rule. Also records the C5 order-dependence fixes (sorted verdict rendering,
   canonical permutation pool).
3. The C5 control then isolated a last-bit floating-point summation non-determinism in
   `duplication`; fixed with `math.fsum` (bit-identical under corpus reordering).

Failing bring-up reports are preserved byte-verbatim at
`evidence/bringup_controls_FAIL_report.json` (sha256 `c5bb0a149062…`) and
`evidence/bringup2_controls_FAIL_report.json` (sha256 `82e6f2b69715…`). No metric definition,
threshold or falsifier changed after the pre-registration; only instrument-internal control
calibration and determinism bugs changed.

The hash-bound-only M3 subset is a **post-measurement robustness breakdown** added after the
primary result was seen, and is labelled as such in `report.json`.

## Falsifiers

F1: re-run `--check` against the same `raw/` snapshots and get a different `result_digest`, or two
check runs disagree. F2: any `raw/` pin moves without a drift entry. F3: any control C1–C10 does
not behave as pre-registered. F4: an independent re-derivation under the frozen definitions
produces materially different M1/M2/M3. F5: a claim classified `SINGULAR_FROZEN` with a token
list length != 1, or a claimed >0.60 cluster edge measuring <= 0.60. F6: D1 is quoted as the
canonical A0 `hard_failure_rate` (it is review-recorded incidence only; `audit_run.py` owns the
canonical HF detectors).

## Reproduce

```bash
cd artifacts/worker-056/a1_metrics_census
python3 run_metrics_census_056.py --snapshot   # only if raw/ is absent
python3 run_metrics_census_056.py --check
```

## Non-claims

No theorem, no schema content verdict, no A0 rubric verdict, no gate verdict, no node status, no
BL-7 adjudication, no canonical artifact or ledger edit. Worker events cannot set `status=done`,
`validation_status=passed` or a gate verdict; this deliverable is routed to the audit lead for
`astra-life05`/A1 use as measurement input.
