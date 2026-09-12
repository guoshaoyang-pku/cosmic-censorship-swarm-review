# Addendum — review-byte drift across the audit instant

`README.md`, `report.json`, `evidence/*.json` and `CHECKPOINT.json` describe the **pin instant**
(4 accepts: 090, 052, 071, 072). They are hash-bound by the emitted event set
`w066-f2b-acceptdisp-20260912T011504-*` and are deliberately left byte-stable.

Between the pin step and the first emission, one accept moved:

| file | at pin | now |
|---|---|---|
| `reviews/F2b-review-worker-072-rev29.json` | `7487f310` accept | `5db91bb0` revise (score 3.0) |

The rewritten verdict binds the **same** bytes (`b2ab6acb2bbe`) and now files a blocking hard
failure on carrier `C1-DENIAL` (`regularity.must_not_conflate[0]`, line 152). The pinned copy
reproduces the original accept classification, so the base event set stays valid and bound.

**The audit result is invariant:** clean-accept count is **0 at both instants** — 4 accepts then,
3 accepts now, and in every case none disposes either live normative carrier. This is direct
evidence that accept verdicts on these bytes are unstable and that coverage must be assessed by
carrier disposition, not by accept count.

Addendum artifacts (new files only, so no previously emitted hash is invalidated):

- `addendum.py` — re-measures at the later instant, replays the pinned copy, 10/10 controls
- `addendum_report.json`, `evidence/addendum_drift.json`, `evidence/addendum_controls.json`
- `CHECKPOINT_ADDENDUM.json` and `runtime/state/w066_f2b_accept_disposition_addendum_checkpoint.json`
- events `w066-f2b-acceptdisp-20260912T011554-05-addendum-claim` / `-06-addendum-checkpoint`

Reproduce:

```bash
python3 artifacts/worker-066/f2b_accept_disposition/addendum.py      # 10/10 controls, 0 clean both instants
python3 artifacts/worker-066/f2b_accept_disposition/emit_addendum.py
```
