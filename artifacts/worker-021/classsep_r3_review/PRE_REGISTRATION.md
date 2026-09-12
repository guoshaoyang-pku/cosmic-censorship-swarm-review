# W021-CLASSSEP-R3-REVIEW-01 — pre-registration

- task_id: `W021-CLASSSEP-R3-REVIEW-01`
- worker: worker-021 (slot recycled; previous checkpoint `W021-N0-REV3-INDEP-01`)
- node: A1 · gate: G-AUDIT · class_id: `GLOBAL` (per the card's own class binding;
  the detector corpora are class-bound to `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN`)
- card served: `comms/inbox/worker-075.jsonl#astra-life07-classsep-adjudication-review`
  (named to worker-075, artifact `reviews/CLASSSEP-calibration-adjudication-review.json`).
  That artifact does not exist and the audit lead filed the queue gap at
  `comms/outbox/astra-lead-audit.jsonl` (blocker `audit-l09-b5-classsep-review-missing-20260912T011904`,
  01:19:46): *"either the named artifact delivered by a non-author at a cited detector hash, or a
  controller re-dispatch naming the substitute reviewers whose verdicts count"*.
  I take it as a bounded substitute review and do **not** overwrite the named path
  (another worker's card). Substitute deliverable:
  `reviews/CLASSSEP-calibration-adjudication-review-021.json`.
- budget: 1.5 agent-hours, one verdict, one checkpoint, then exit.

## Target (frozen)

`reviews/CLASSSEP-calibration-adjudication.json`
sha256 `7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1` (r3-life06,
`astra-life06-classsep-detector-adjudication`), with frozen map snapshot
`artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json`
sha256 `f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749`.

## Arms (all four, exact hashes; prefix match must hold before and after)

| arm | path | sha256 prefix |
|---|---|---|
| APPLIED | `research_map/class_separation.py` | `a8c04fc31e4a` |
| PRE | `artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py` | `c266dbceca87` |
| STAGED | `proposed/class_separation.py` | `e2d24b927ee8` |
| PROSEFIX | `artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py` | `dc8aa0de3869` |

Void revision `e36b0d644ca7` must not be loaded, cited or present among the arm bytes (CF-29).

## Method (independent re-implementation)

I re-implement the census from the pinned data; I import **no** author aggregation code
(`artifacts/audit/classsep_calibration.py` and
`artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py` are read as *data sources only*:
`LIVE_LABELS` and `ASSERTION_MENTION_FIXTURES` are extracted with `ast.literal_eval`; the
worker-049 aggregation semantics are re-coded from its documented rules). The four detector
modules are the objects under test and are loaded as-is (hash-pinned).

Reproduce, in card order:

- (i) corpus A, worker-07 27-fixture falsification corpus (registered runner semantics,
  `results.json` `d69ad58468be`): per-fixture TP/FN/FP/TN; each arm must be PASS 17/0/10/0.
- (ii) corpus B, APPLIED live census at snapshot `f344ed2aaea5`: hard = 19, of which 17 labeled
  metalinguistic FP (LIVE_LABELS) + 2 unlabeled; each unlabeled finding's automatic mechanism
  tag must be `DETECTOR_SELF`, and no labeled-FP finding may be a first-order assertion.
- (iii) corpus C, 16-fixture assertion-vs-mention set (extracted from the pinned adjudication
  instrument): per-arm sens/spec; must be APPLIED 4/6-3/10, PRE 4/6-1/10, STAGED 5/6-1/10,
  PROSEFIX 4/6-10/10; no arm meets sens>=5/6 AND spec>=9/10 AND 27-fixture PASS AND 0 HIGH cue-FN.
- (iv) corpus D, worker-049 39-fixture adversarial corpus (`9eb2ea9e2743`) + worker-035
  23-control battery (`ef881c3a`): per-arm cue-induced FN (HIGH count) and battery score; the
  10/10 suppression must attach to PROSEFIX `dc8aa0de3869`, not STAGED `e2d24b92`.
- (v) arm bytes before == after; `e36b0d644ca7` absent; no write to any canonical/proposed path.

## Controls (controls.json; pre-registered)

- K1 pin-drift detection: a deliberately mutated copy of a pinned file must be rejected.
- K2 bare first-order assertion `C0 and C2 are one class in the frozen registry.` must fire in
  all four arms.
- K3 the same sentence inside quotation marks must be judged a mention by my detector-independent
  `first_order_flag` heuristic (validates the label set, not the detector).
- K4 double-run determinism: the census payload must be byte-identical across two runs.
- K5 label-mutation control: flipping fixture A1's truth label in an in-memory copy must move
  corpus-C sensitivity (proves the instrument reads labels rather than hardcoding the table).
- K6 APPLIED byte identity excludes the void revision: APPLIED sha == `a8c04fc3…` and !=
  `e36b0d644ca…`.
- K7 snapshot control: `claims_in_map` == 383 and snapshot sha == `f344ed2aaea5…`.

## Verdict rule

`accept` iff every card item (i)–(v) reproduces exactly at the pins and K1–K7 pass.
`revise` iff the adjudication's numbers are wrong but the direction/decision still holds.
`reject` iff the decision's premise fails (e.g. a genuine first-order C0/C2 merge assertion is
found among the claims labeled FP, or an arm secretly meets the adoption bar).
`inconclusive` if any cited pin fails to reproduce (fail closed, no repair attempted).

## Non-claims

No gate verdict, no node status, no `validation_status=passed`, no detector/schema/claim edit,
no write to the named worker-075 artifact path, no ratification of the detector-of-record.
