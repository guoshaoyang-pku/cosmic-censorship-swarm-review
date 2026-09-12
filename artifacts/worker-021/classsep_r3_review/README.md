# W021-CLASSSEP-R3-REVIEW-01 — independent non-author review (A1 / G-AUDIT)

Bounded substitute review for card `astra-life07-classsep-adjudication-review`
(`comms/inbox/worker-075.jsonl`), whose named artifact
`reviews/CLASSSEP-calibration-adjudication-review.json` is still absent
(blocker `audit-l09-b5-classsep-review-missing-20260912T011904`). The named path was
**not** written (another worker's card); the verdict is delivered at
`reviews/CLASSSEP-calibration-adjudication-review-021.json`.

## Target

`reviews/CLASSSEP-calibration-adjudication.json` sha256 `7714ffd5b467…` (r3-life06),
map snapshot `artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json`
`f344ed2aaea5…`.

## Verdict

`accept`, score 4.0, no hard failures. The card's items (i)–(v) reproduce exactly:
**127/127 compared blocks match**, **11/11 controls pass**, 0 pin drift, all four arms
loaded from sha256-verified source bytes, and the void revision `e36b0d644ca7` excluded.

| arm | corpus A | live hard | corpus C sens/spec | corpus D HIGH cue-FN | battery | bar |
|---|---|---|---|---|---|---|
| APPLIED `a8c04fc31e4a` | PASS 17/0/10/0 | 19 | 4/6 · 3/10 | 1/12 | 13/23 | no |
| PRE `c266dbceca87` | PASS 17/0/10/0 | 24 | 4/6 · 1/10 | 0/12 | 11/23 | no |
| STAGED `e2d24b927ee8` | PASS 17/0/10/0 | 25 | 5/6 · 1/10 | 0/12 | 11/23 | no |
| PROSEFIX `dc8aa0de3869` | PASS 17/0/10/0 | 1 | 4/6 · 10/10 | **10/12** | 23/23 | no |

Decision (c) is mechanically re-derived; the attribution correction is confirmed
(10 HIGH cue-induced FN belong to PROSEFIX `dc8aa0de`, not STAGED `e2d24b92`).

## Files

| file | role |
|---|---|
| `PRE_REGISTRATION.md` | pre-registered method, controls, verdict rule |
| `verify_classsep_r3.py` | independent instrument (imports no author aggregation code) |
| `census.json` | full per-fixture TP/FP/FN census, all four arms, four corpora |
| `controls.json` | K1–K11 controls (pin drift, bare/quoted assertion, determinism, label mutation, void revision, snapshot identity, label audit, no-write) |
| `comparison.json` | 127 field comparisons vs the adjudication, 0 mismatches |
| `report.json` | review report with findings N21-CS-01…06 and disclosure |

## Re-run

```bash
python3 artifacts/worker-021/classsep_r3_review/verify_classsep_r3.py   # exits 0 (3 on mismatch/control failure)
python3 artifacts/worker-021/classsep_r3_review/make_review_artifact.py
```

Falsifier: any of the 127 compared blocks flips, any K1–K11 control fails, a genuine
first-order C0/C2 merge assertion appears among the claims labeled FP, or an arm meets the
adoption bar; VOID on drift of any pinned hash or of the adjudication/snapshot.

## Non-claims / open items

No gate verdict, no node status, no `validation_status=passed`, no detector-of-record, no
canonical write. Prior review worker-017's blocking process finding B17-CS-01 (detector
write/rollback during the round) is recorded but **not** discharged here; the
detector-of-record question (recorded pin `c266dbec` vs operative `a8c04fc3`) remains
controller-owned and G-AUDIT stays pending.
