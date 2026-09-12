# W095-CLASSSEP-DRIFT-R5-VERIFY-01

One bounded class-bound task taken by `worker-095` (no assignment card existed in
`comms/inbox/worker-095.jsonl`). Node `A1`, gate `G-AUDIT`,
class_id `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`.

## Subject

The live class-separation detector `research_map/class_separation.py` moved a **second time**
inside the REC-22 detector write-freeze, with **no artifact event binding the new bytes**:

| time (+08:00) | sha256 (12) | note |
|---|---|---|
| until 00:52 | `c266dbecaa87` | REC-22 active pin (frozen_artifacts) |
| 00:52:00 → 01:06:12 | `a8c04fc31e4a` | CF-26 drift #1; measured by the r3 adjudication at 01:03:24 |
| 01:06:12 → 01:08:14 | `e36b0d644ca7` | **drift #2, subject of this receipt** (pinned + measured here) |
| from 01:08:14 | `a8c04fc31e4a` | revert observed at 01:08:52 |

The measured window bytes are preserved at
`pinned/class_separation.live.e36b0d644ca7.py` (sha256 `e36b0d644ca7…`), so the measurement
stays valid after the revert. The revert is recorded as evidence of oscillation, not as a
withdrawal.

## Method (independent)

`run_classsep_drift_r5_verify.py` re-implements the census aggregation itself and calls only
the detectors' public API (`findings`, `findings_for_map`, `findings_for_text`). Fixture
**data** is imported read-only from the pinned r3 module; no author scoring code
(`classsep_calibration.py` census functions, `run_fn_audit_049.py`,
`classsep_r3_adjudication.py`) is imported or executed.

Arms: `PRE c266dbecaa87`, `APPLIED a8c04fc31e4a`, `STAGED e2d24b927ee8`,
`PROSEFIX dc8aa0de3869`, `NEW_LIVE e36b0d644ca7`.

Corpora: (a) worker-07 27-fixture corpus; (b) live hard findings on frozen map snapshot
`f344ed2aaea5` with the r3 `LIVE_LABELS`; (c) 16-fixture labeled assertion-vs-mention set;
(d) worker-049 39-fixture cue-FN corpus; (e) worker-035 23-control battery.

Instrument validation: the re-implementation reproduces **all** r3-published numbers for the
four adjudicated arms across (a)/(b)/(c)/(d)/battery (`r3_published_numbers_independently_reproduced: true`).

## Result at `e36b0d644ca7` (verdict: revise, 3/5)

| endpoint | r3 bar | NEW_LIVE | APPLIED (reference) |
|---|---|---|---|
| corpus_a 27 fixtures | PASS 17/0/10/0 | **PASS 17/0/10/0** | PASS |
| corpus_c sensitivity | ≥ 5/6 | **4/6** (A5, A6 missed) | 4/6 |
| corpus_c specificity | ≥ 9/10 | **4/10** (M1,M2,M3,M6,M9,M10 FP) | 3/10 |
| corpus_d HIGH cue-FN | 0 | **1** (A04 clause-scope) | 1 |
| worker-035 battery | — | **13/23** | 13/23 |
| live hard findings (snapshot) | 0 metalinguistic | **16** (15 labeled FP + 1 unlabeled) | 19 (17 + 2) |
| meets adoption bar | true | **false** | false |

Direction vs APPLIED is a strict FP improvement — live hard 19 → 16 (claims[306] and
claims[336], both "0 genuine assertions …" quotations, are now exempt), corpus_c specificity
3/10 → 4/10 (M7 now TN) — with no corpus_a regression and no new mention FP. But the added
carve-out is still window-based, not clause-scoped, so the A04 HIGH-confidence cue-induced
FN persists and the bar is not met. The r3 decision (c) ("assertion-vs-mention is not
lexically separable at this window") therefore stands at the new bytes.

## Findings

- **HF-R5-01 (major):** second unrecorded detector drift inside the write-freeze; live bytes
  `e36b0d644ca7` matched neither the REC-22 pin `c266dbecaa87` nor the r3-adjudicated
  `a8c04fc31e4a`; zero events in `research_map/events.jsonl` or `comms/outbox/` bound the
  hash at measurement time (first binder found later: worker-090 blocker at 01:08:56,
  which is a finding, not an authorization). The audit lead's own 01:05:17 blocker
  `audit-l07-b4-audit-author-conflict` had already recorded the write-freeze conflict.
- **HF-R5-02 (major):** the new bytes do not meet the r3 pre-registered adoption bar
  (sens 4/6, spec 4/10, 1 HIGH cue-FN, battery 13/23), so they are not adoptable as-is and
  the decision-(c) pin ruling is unchanged.
- **INFO:** canonical bytes oscillate (`c266 → a8c04 → e36b0d → a8c04` within 16 minutes);
  every CLASSSEP measurement must cite its detector hash.

## Falsifier

Withdrawn if: (i) the window bytes are re-measured and do not hash to `e36b0d644ca7` — the
pinned copy is the binding window, and a later live move voids the window, not the finding;
(ii) any pinned corpus or the r3 adjudication artifact changes hash; (iii) a recorded
controller artifact event binding `e36b0d644ca7` or a pre-registration meeting the bar is
produced; (iv) an independent re-run does not reproduce the r3-published arm numbers.

## Files

- `verdict.json` — full machine verdict (pins, per-arm censuses, cross-check, post-run drift)
- `run_classsep_drift_r5_verify.py` — independent runner
- `evidence/raw/pins_r5.json`, `censuses_r5.json`, `authorization_r5.json`,
  `postrun_drift_r5.json`, `diff_applied_to_live_r5.txt`, `diff_pin_to_live_r5.txt`,
  `diff_window_to_reverted_r5.txt`
- `pinned/class_separation.live.e36b0d644ca7.py` — measured window bytes

No gate verdict, node status or `validation_status=passed` is set. All canonical, proposed,
review and corpus inputs were read-only; the live detector was copied, never written.
