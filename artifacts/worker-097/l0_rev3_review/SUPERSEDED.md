# SUPERSEDED — do not cite report.json in this directory

This directory holds the earlier `W097-L0-REV3-INDEP-REVIEW-01` attempt against
`ledger/theorems.jsonl @ 3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6`.

- `snapshots/theorems.jsonl` **is current and load-bearing**: it is the pinned rev-3 input of
  the successor review `../l0_rev4_review/` (rev-3 → rev-4 chain census), hash
  `3e3d35531421…` re-verified by that review's P01/P03 checks.
- `report.json`, `controls.json`, `raw_sha256.txt` in this directory are **stale**: the target
  was superseded by rev 4 (`a1674f094979…`) while the review was being calibrated, and the
  instrument correctly failed closed (exit 3) instead of overwriting. The stale report also
  carries a known harness-calibration defect in control `m4_disjunction_fires_HF02a`
  (equality assertion instead of membership, because rev 3 already contains 8 pre-existing
  disjunctions) and a first-draft verdict rule. Both were fixed in
  `../l0_rev4_review/run_l0_rev4_review.py` before its final run.
- The successor review, its 12/12 controls, verdict and checkpoint are under
  `artifacts/worker-097/l0_rev4_review/` and `runtime/state/w097_checkpoint_l0_rev4_review.json`.
