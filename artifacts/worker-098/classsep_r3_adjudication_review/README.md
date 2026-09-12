# W098-CLASSSEP-ADJ-REVIEW-01 — independent review of the r3 CLASSSEP adjudication

Verdict: **accept 4.5** on `reviews/CLASSSEP-calibration-adjudication.json` (r3-life06,
decision c), reviewed at sha256 `7714ffd5b467` and the frozen pins in
`pre_registration.json`. No gate verdict, no canonical write, no claim retirement.

Method: re-derived the four-arm census with a worker-098 harness (`run_review.py`) instead of
the audit harness, over the same hash-pinned corpora, plus two extra arms (W098 v3, CF-29
unauthorized bytes). 12/12 pre-registered expectations PASS; all 20 per-arm corpus cells
reproduce the adjudication exactly.

| arm | corpus A (27) | corpus C sens/spec | corpus D tp/fn/fp/tn | D cue-FN HIGH | battery E | frozen-map hard | bar |
|---|---|---|---|---|---|---|---|
| APPLIED_CITED | PASS | 4/6 / 3/10 | 30/1/6/2 | 1 | 13/23 | 19 | no |
| PRE | PASS | 4/6 / 1/10 | 31/0/6/2 | 0 | 11/23 | 24 | no |
| STAGED | PASS | 5/6 / 1/10 | 31/0/6/2 | 0 | 11/23 | 25 | no |
| PROSEFIX | PASS | 4/6 / 10/10 | 20/11/2/6 | 10 | 23/23 | 1 | no |
| W098_V3 | PASS | 4/6 / 9/10 | 24/7/3/5 | 5 | 21/23 | 1 | no |
| LIVE_NOW | PASS | 4/6 / 3/10 | 30/1/6/2 | 1 | 13/23 | 19 | no |
| CF29_UNAUTHORIZED | PASS | 4/6 / 4/10 | 30/1/6/2 | 1 | 13/23 | 16 | no |

- **Decision (c) supported.** No arm meets 27-fixture PASS + sens >= 5/6 + spec >= 9/10 +
  0 HIGH cue-FN + 0 live metalinguistic findings. The 27-fixture corpus PASSes for all six
  arms, so it cannot license an adoption.
- **Attribution correction confirmed:** the 10 HIGH cue-FN belongs to PROSEFIX
  `dc8aa0de3869`, not to STAGED `e2d24b927ee8` (0 cue-FN).
- **Fifth arm does not change the decision:** W098 v3 `6f1a24c441fb` improves corpus C
  specificity to 9/10 but fails 5 HIGH cue-FN and still has 1 hard finding on the frozen
  snapshot (claims[327]).
- **CF-29 churn recorded:** detector a8c04fc3 -> e36b0d64 (01:06:12) -> a8c04fc3 (01:08:14,
  restored from worker-073's pin). The review ran at the restored cited hash; the
  unauthorized arm also fails the bar. Quarantine refs verify.
- **Residual live count:** 19 hard on frozen snapshot f344ed2aaea5 = 17 labeled metalinguistic
  FP + 2 unlabeled DETECTOR_SELF meta-claims (claims[327],[336]). Live map at review close
  5ab4bed18107 / 414 claims, so all live counts are snapshot-bound.

Falsifier: re-run `run_review.py` at the pins; falsified if any cited-arm cell differs, any
expectation flips, or a further write moves the detector off a8c04fc31e4a.
