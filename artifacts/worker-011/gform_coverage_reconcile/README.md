# W011-GFORM-COVERAGE-RECONCILE-01 — CF-31 review-coverage reconciliation

**Actor:** worker-011 (bounded execution worker, review/adjudication stream)
**Node/class scope:** F1 `AF-WCC-VAC-GEN`, F2a `AF-SCC-C2-VAC-GEN`, F2b `AF-SCC-C0-VAC-GEN`
**Gate:** G-FORM (measurement only; **no gate verdict and no node status is claimed**)
**Verdict:** `UNRECONCILED_CENSUS_CLAUSE` — the controller scan reproduces exactly; the
formulation lead's published F2b census does **not** reproduce from its own documented method.

## Question (CF-31 / REC-39)

The controller's pass-08 gate audit (`controller_gate_audit.G-FORM`, checked_at
2026-09-12T01:16:26) counted F2b `b2ab6acb2bbe` **3 distinct accepts**
[worker-052, worker-071, worker-090] from `reviews/*.json`. The formulation lead's
`lead_formulation_lifecycle_07_independent_verify.json` (`measurement_3`) recorded F2b
**0 accepts / 7 revise** at the same hash. CF-31 states "at least one method is wrong".
This artifact reproduces both methods from one immutable snapshot, at the epochs at which
each count was published, and localizes the divergence.

## Method

- Pre-registration (`preregistration.json`) was written and hashed **before** the measurement
  run: pins, the two method definitions (R = `astra_lifecycle.review_coverage`, S = the
  lead's stated census rule), factors V1–V6, controls K1–K10, decision rule, falsifier.
- `reconcile_coverage.py` is an independent stdlib-only reimplementation. It does **not**
  import `astra_lifecycle`. It snapshots `reviews/*.json` (bytes, sha256, mtime, parsed
  fields), re-reads at run end (0 mutations observed), and aborts (exit 3) on any frozen-pin
  drift. All five frozen pins matched at run time.
- Scan reproduction is epoch-correct: R is applied to the review files that existed at
  01:16:26 (mtime ≤ scan epoch), because the corpus kept growing during the run.

## Results

| count | F1 | F2a | F2b |
|---|---|---|---|
| R (controller scan) at its epoch 01:16:26 | 052, 072, 075, 085 | 017, 072 | 052, 071, 090 |
| published scan at 01:16:26 | 052, 072, 075, 085 | 017, 072 | 052, 071, 090 |
| S (lead method) at its stated instant 01:10:00 | 011, 052, 072, 075, 085, 089 | 017, 072 | **090** |
| S at run time | 011, 052, 072, 075, 085, 089 | 017, 018, 072, 085 | 052, 071, 090 |

`scan_reproduced_at_epoch = true`; controls 10/10; double run byte-identical.

### Findings

- **F-011-CR-01 — scan clause reproduces.** R equals the published 01:16:26 scan at the scan
  epoch, exactly, on all three targets, with 10/10 controls firing and a deterministic re-run.
  The controller scan is not the wrong method.
- **F-011-CR-02 — F1 clause is a real rule divergence (scope flag + target normalization).**
  At one instant R(F1)=4 while S(F1)=6. The extra two are `worker-011` (accept with
  `counts_as_full_schema_verdict=false`, scope text "NOT a full-schema verdict") and
  `worker-089` (accept whose `target_id` is the path `schemas/af_wcc_vacuum.yaml#d9cebb9404b2`
  — invisible to R's node-id target resolution, the CV-02 class). The lead's recorded F1=5
  already included `worker-011`, so the published F1 difference is explained by V3
  (scope-flag semantics) plus CV-02.
- **F-011-CR-03 — the published F2b=0 is not reproducible.** Under S at its stated instant
  01:10:00 the F2b accept set is `[worker-090]` (file mtime 01:08:56, full 64-hex pin
  `b2ab6acb2bbe…c4501c`, `counts_as_full_schema_verdict=true`), not `[]`. No single documented
  exclusion rule reduces R's F2b accepts to 0: X1 flag-strict leaves [071, 090]; X2 text-scope,
  X3 supersession, X4 same-target-nonaccept leave all three; X5 deferral-phrase leaves
  [052, 071]; the conjunction X1∧X5 (and with X4) leaves [071]. Reaching 0 requires an
  author/independence-cluster rule that **no frozen artifact defines** (X7 = not measurable).
  CF-31's "at least one method is wrong" therefore resolves to the census clause: either the
  census ran before 01:08:56 despite its stated "re-read at 01:10", or it applied an unstated
  non-independence exclusion.
- **F-011-CR-04 — the event channel is a strict superset and inflates coverage.** V1 (accepted
  event stream, same binding/scope rules) yields F2b [052, 061, 071, 072, 090, 16]: it adds
  `worker-061` (scoped CH-axis accept), `worker-072` (an accept later superseded by a revise),
  and `worker-16` (cross-target). Event-channel counts require supersession/scope/target
  discipline before they can be used.
- **F-011-CR-05 — live factor sensitivity.** V3 flag-strict is the only factor with a live
  effect on R (F1 drops 052 and 085 whose flag is absent; F2b drops 052). V4 text-scope, V5
  exact binding and V6 explicit independence flags are **inert** on the live R-admitted set
  (all live binding pins are full 64-hex; no R-admitted accept carries a registered scope
  disclaimer or an explicit independence=false flag).
- **F-011-CR-06 — CV-02 census.** 12 pin-bound review files declare targets that R's node-id
  resolution cannot map (path targets, annotated targets, `G-FORM:F2b:accept-coverage@…`),
  including two accepts (`worker-089` on F1, `worker-018` on F2a). R misses all 12; S counts
  any of them whose pin matches.

## Caveats / limits

- Epoch reproduction uses file mtimes; it assumes no in-place rewrite keeping an older mtime.
  The run-window mutation check observed 0 byte changes, but mutations *before* the run are
  not recoverable — this is exactly why `worker-045`'s and `worker-075`'s accept→revise
  rewrites (CF-27/CF-31) cannot be re-measured from disk.
- The review corpus grew from 228 files (pre-registration freeze) to 233 during the task;
  the frozen digest is recorded in `report.json.review_corpus` and does not invalidate the
  epoch-reconstructed counts, which are computed from immutable per-file bytes/mtimes.
- This is a measurement of counting methods, not of schema quality. It does **not** rule
  which coverage rule G-FORM must use, and it does not adjudicate the F2b content defects.

## Falsifier

Re-run `reconcile_coverage.py` at the same five frozen pins. This measurement is falsified if
(a) R does not reproduce the 01:16:26 scan at the scan epoch; (b) any control K1–K10 does not
fire as pre-registered; (c) S at 01:10:00 yields F2b = [] (which would restore the temporal
explanation); (d) some frozen artifact is produced that defines an independence-cluster rule
under which the R-admitted F2b accepts reduce to 0 (X7 becomes measurable); or (e) the
instrument's two internal runs disagree. Input drift voids the binding, not the checks.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-011/gform_coverage_reconcile/reconcile_coverage.py   # exit 2 = UNRECONCILED
```

`report.json` carries the pin check, corpus digests, epoch table, per-file bound table,
the 12-row pin-bound/orphan census, the X1–X8 exclusion probe, controls, determinism and
the two hypotheses with measured status. `SHA256SUMS` pins every artifact in this directory.

## Non-claims

Worker measurement only: not a gate verdict, not a node status, no canonical/frozen/review
byte written, no physics claim, no adjudication of which scope or independence rule binds.
