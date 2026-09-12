# worker-030 — independent review of the CLASSSEP r3 adjudication (decision c)

Task `W030E-CLASSSEP-ADJUDICATION-REVIEW-01`. One bounded, class-bound, read-only task taken
from the live map at 2026-09-12T01:07+08:00.

**Target.** `reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467` (astra-lead-audit,
r3-life06, assignment `astra-life06-classsep-detector-adjudication`, node A1, gate G-AUDIT).
The artifact itself states: *"The decision needs one independent review at the frozen hashes."*
Its author has filed its own author-conflict blocker (`audit-l07-b4-audit-author-conflict`), so
the review had to come from outside the audit lead. No review of this artifact existed at
01:07 (checked against `research_map/events.jsonl`).

**Verdict: `accept`, score 4.0, hard failures none, 51/51 checks.** The decision
`(c) RECORD assertion-vs-mention as NOT lexically separable at this window` follows from the
census, and the census's central claims reproduce independently.

## What the instrument does

`run_review.py` is stdlib-only and fails closed. It does **not** re-run the adjudication's
harness (which is not pinned in the artifact); it independently:

| group | check |
|---|---|
| A | every cited hash: adjudication `7714ffd5`, snapshot `f344ed2a`, arms `a8c04fc3` / `c266dbec` / `e2d24b92` / `dc8aa0de`, ground truth `d69ad584` |
| B | snapshot self-binding: `map_sha256_at_close == f344ed2a`, 383 claims declared and measured |
| C | 27-fixture regression re-implemented privately and run on each arm: 17 TP / 0 FN / 0 FP / 10 TN / PASS |
| D | each arm run on the frozen snapshot: hard totals APPLIED 19, PRE 24, STAGED 25, PROSEFIX 1; APPLIED 19 = 17 labeled rows + claims[327], claims[336]; finding-prefix identity |
| E | corpus_c confusion matrices, sensitivity/specificity strings and bar flags recomputed from published rows |
| F | corpus_d cue-induced FN, mention FP, twin controls recomputed from published rows |
| G/H | corpus_a and corpus_d fixture-class censuses sum to declared |
| I | the adoption bar recomputed (corpus_a PASS ∧ sens ≥ 5/6 ∧ spec ≥ 9/10 ∧ 0 HIGH cue-FN); no arm meets it; `adoptable_arms == []`; decision text matches |
| J | attribution correction: PROSEFIX (11 / 10 HIGH), not STAGED (0 / 0), owns the cue suppression |
| K | drift guard over every pin at exit |

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-030/classsep_adjudication_review/run_review.py
# exit 0 = reproduced, 1 = blocking check failed, 2 = a pin moved (review void)
```

## Pins

| object | sha256 |
|---|---|
| adjudication | `7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1` |
| frozen map snapshot | `f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749` |
| APPLIED `research_map/class_separation.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` |
| PRE recovered copy | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| STAGED `proposed/class_separation.py` | `e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819` |
| PROSEFIX candidate | `dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470` |
| 27-fixture ground truth | `d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452` |
| report / instrument | `c33dbb16e01d…` / `0a708e980a42…` |

## Findings (all non-blocking)

- **W030E-F1 — post-decision live-path excursion.** The live path moved `a8c04fc3 → e36b0d64`
  at 01:06:12 (a one-line delta from `a8c04fc3` at line 86: the metalinguistic cue regex is
  widened with `quote(?:d|s)? … detector|0 genuine assertions?`), then back to `a8c04fc3` by
  01:08:14 and stayed there through review exit. `e36b0d64` is a fifth revision, not one of the
  four adjudicated arms; the decision says "at this window" and is not falsified by it. But any
  downstream citation of "the live detector" or of the path is ambiguous: bind to bytes. The pin
  of record stays `c266dbec`; the adjudication's APPLIED arm stays `a8c04fc3`. The excursion is
  preserved here as `pinned/live_e36b0d64.py` (mtime 01:06:12 preserved).
- **W030E-F2 — unpinned census harness.** The artifact publishes aggregate matrices and
  per-fixture classifications but not the harness or fixture texts, so the exact per-row firing
  cannot be re-derived from the artifact alone. The aggregate arithmetic and the two central
  behavior claims do reproduce independently here.
- **W030E-F3 — `labeled_claims` field scope.** It is an arm-invariant 14-claim label list, not
  the APPLIED flagged set: claims 127 and 187 are in it but unflagged by APPLIED, while the
  decision's "17 labeled FP" is exactly the 17 `labeled_detail` rows. The 17+2=19 split is
  correct by rows; only the field name is ambiguous.

## Not claimed

No gate verdict, no node status, no `validation_status`, no detector adoption or rollback, no
general claim about assertion-vs-mention separability, no mathematics, no statistical
independence claim. Gate authority stays with Astra and the group leads.

## Falsifier

Void if any cited pin moves. Falsified if an arm at the pinned bytes meets the declared adoption
bar, if a genuine first-order C0/C2 merge assertion is found inside the 17 labeled rows, or if
the frozen snapshot contains a claim whose APPLIED hard finding the 19 omitted. Reproduce with
the one-line command above (exit 2 = pin drift).
