# W035-A1-CLASSSEP-HARDFAIL-ADJUDICATION-01 — are the CLASSSEP hard failures genuine?

**Worker:** `worker-035` · **Node:** `A1` · **Gate:** `G-AUDIT` ·
**Classes:** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
**Adjudicated revision:** `research_map/research_map.json` sha256 `3d45be5969ec388e…`, frozen as
`pinned/map_snapshot.json` (`updated_at 2026-09-12T00:37:18+08:00`, 2 408 249 bytes).
**Verdict:** **10/10 carried/live CLASSSEP hard failures are detector false positives; 0 genuine
class-separation assertions.** worker-093's calibrated checker clears **1/10** (`claims[36]`);
**9/10 persist**, so the calibration route *as scoped* does not discharge the current hard list.

## What was asked

The live checkpoint `runtime/state/current_checkpoint.json` (`evidence_hard_failures`) carries
CLASSSEP entries of the form

```
CLASSSEP: composite C0/C2 asserted as one class in claims[i].statement: ...
```

CF-16 adjudicated the first of these (`claims[36]`) a checker false positive and left two remedies:
(1) the author rephrases the claim, or (2) the checker is calibrated. An earlier worker-035 pass
prepared the rephrase for `claims[36]`; worker-093 built a calibration patch for exactly that case.
Meanwhile the claim corpus grew: the detector now fires on **ten** findings across eight claims
(`36, 94, 96, 97, 101, 112, 112, 127, 144, 152`). This task asks the question the two remedies
presuppose and neither had answered at the current revision: **is any of these ten a genuine
assertion that C0 and C2 are one class?**

## Result

| claim | occurrences | independent verdict | named reasons |
|---|---:|---|---|
| 36 | 1 | NON_ASSERTIVE | CASE_LABEL (`TC-F0-N14`) |
| 94, 96, 97 | 1 each | NON_ASSERTIVE | CASE_LABEL (`TC-F0-N14`), CROSS_CLAUSE |
| 101 | 1 | NON_ASSERTIVE | NEGATED (`no … merge`) |
| 112 | 2 | NON_ASSERTIVE | QUOTED, METALINGUISTIC (`asserted`) |
| 127 | 1 | NON_ASSERTIVE | NEGATED (`non-merge`) |
| 144 | 1 | NON_ASSERTIVE | CROSS_CLAUSE (`;`) — merge word belongs to "retired merged file", not to `C2/C0` |
| 152 | 1 | NON_ASSERTIVE | NEGATED (`rather than`) |

The detector's own docstring states the intended prose semantics: *"quoted or discussed composites
do not [violate] (a claim about a leak is not a leak)"*. All ten findings are exactly such
mentions/negations, or a ±60-char window artifact (claim 144). **No author rephrase and no
checker weakening is required to make these true statements safe; the prose-mode heuristic is what
needs the fix.** claims 94/96/97 are verbatim duplicates submitted three times by worker-083; the
duplication is itself worth the formulation lead's attention but is not a class-separation defect.

### Measured delta of worker-093's calibration

`artifacts/worker-093/cf16_calibration/calibrated_class_separation.py` (sha `ff58563386cf`) at the
same snapshot: **removed = {claims[36]}, added = {}, remaining = 9**. That is consistent with
worker-093's own scoping (their live-map check B5 ran when the map had exactly one finding, at
`4fd40d4d`), and their rule is sound for what it covers. But its case-label rule requires the
merge word to be exactly `merge|merger|case|…`; it therefore does not clear
`merged C0/C2 regularities` (claims 94/96/97), the composite-safe negation guard does not clear
`no C0/C2 merge` (101) or `non-merge` (127), and the quote/metalinguistic/window families
(112, 152, 144) are outside its rule. **Review of that patch: `revise` — scope shortfall at the
current revision, not a defect in its one measured case** (see `comms/outbox/worker-035.jsonl`,
event `w035-classsep-hardfail-review-w093-20260912T0040`).

## Method (all read-only; no canonical file modified)

`adjudicate_hardfailures.py` reads the frozen snapshot in one atomic read and:

1. reproduces the canonical findings with the pinned checker (`c266dbceca87`), and compares them
   with the checkpoint's carried list (drift reported, not hidden);
2. parses each finding's own ±60-char window out of the finding string, locates it in the claim,
   and classifies **only the occurrence the finding refers to** with an independent classifier:
   `QUOTED` (paired-quote spans; possessive apostrophes are not quotes), `CROSS_CLAUSE`
   (`; . ! ? —` between composite and merge word), `NEGATED` (negation cues, `non-merge`,
   `rather than`/`instead of`/`not a`, rejection/denial cues in the same clause),
   `CASE_LABEL` (a `TC-/FX-/CASE-/ROW-/FIXTURE-` id plus a label noun), `METALINGUISTIC`
   (pattern/regex/detector/flag/vocabulary cues on either side of the merge word);
3. runs worker-093's calibrated module over the same snapshot and requires every cleared finding to
   be one this harness independently classified `CASE_LABEL`;
4. runs both modules twice (determinism);
5. scores **9 positive and 14 negative labeled controls** (`controls.json`): every positive control
   is a genuine merge assertion the classifier must call `ASSERTION`; every negative control is one
   of the live mention/negation families and must be called `NON_ASSERTIVE` with the named reason;
6. re-scores the worker-07 falsification corpus with both modules (17 leaks / 0 missed / 10 controls
   / 0 spurious, per-fixture identical) using an independent scorer that resolves paths against the
   repo root, so the relocated calibrated copy is scored identically;
7. re-hashes the pinned inputs at the end (`C7`).

**Checks: 9/9 pass** (exit 0). Controls: **9/9 positive, 14/14 negative**.

## Pinned inputs (sha256)

| path | sha256 |
|---|---|
| `research_map/research_map.json` (snapshot `pinned/map_snapshot.json`) | `3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005` |
| `research_map/class_separation.py` (`pinned/class_separation.c266dbce.py`) | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| `artifacts/worker-093/cf16_calibration/calibrated_class_separation.py` (`pinned/calibrated_class_separation.ff585633.py`) | `ff58563386cf398a74e97cb0d44534e983886c48041e7e0df185810402614be1` |
| `artifacts/worker-093/cf16_calibration/report.json` | `e63aaa74d1cf87aa4d84f84ba2d77d721c52816323ad731c773730053785c801` |
| `artifacts/worker-07/class_separation_falsification/results.json` | `d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452` |
| `runtime/state/current_checkpoint.json` (at read) | `a215de69bfab69aa46e14f36f98c5c38f6775b340dbfcc1a1397506c2c951a47` |

## Reproduction

```bash
python3 artifacts/worker-035/classsep_hardfail_adjudication/adjudicate_hardfailures.py \
    --observe-live      # exit 0 iff 9/9 checks pass
```

## Falsifier

Re-run the command above unchanged on the frozen snapshot. **Falsified if** (a) the canonical
checker does not reproduce the same ten findings; (b) any finding is classified `ASSERTION` or
`UNCLASSIFIED`; (c) any control flips expectation; (d) the calibrated module adds a finding or
clears an occurrence not classified `CASE_LABEL`; (e) a second run is non-deterministic; or (f) any
pinned hash drifts (then this adjudication is superseded — re-run at the new pins). The verdict
binds to snapshot `3d45be5969ec` only; the live map moves continuously and is recorded in
`report.json` as `live_observation`, not as the adjudicated revision. Most directly: **a single
genuine "C0 or C2 are one class" assertion among these findings, or a claim edit that no longer
carries the flagged text, falsifies the corresponding row.**

## Limitations (stated, not hidden)

- A `NON_ASSERTIVE` verdict is strong: each carries the named cue and offset in `report.json`, and
  the rules were written to the detector's own stated prose semantics.
- The classifier is deliberately conservative in the other direction: an `ASSERTION` verdict is a
  flag for human review, not proof of a violation. Reported (nested/reported) claims without a
  rejection or quotation cue — e.g. *"We reject the proposal that C0/C2 are one class"* before the
  rejection rule was added — can still be classified `ASSERTION`.
- The adjudication covers detector output, not the truth of the underlying disposition claims.
- claims 94/96/97 are byte-identical duplicate submissions; they are counted as three findings
  because the checker scans each claim entry, not because three distinct defects exist.

## Non-claims

Not a gate verdict, node status, or `validation_status=passed`. No canonical file (map, event
stream, ledger, schemas, `class_separation.py`) was edited; the fix remains a proposal for the
tooling owner. Worker authority cannot set node/gate state.
