# Addendum 001 — W081 CLASSSEP clause-scope candidate

Parent `report.md` is immutable; this addendum corrects two wordings and records one
additional control.

## 1. Precise delta vs the frozen pin (supersedes "insertion-only" wording)

`diff artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py
artifacts/worker-081/classsep_clause_candidate/class_separation_clause.py`:
**270 added lines, 11 removed lines**. All 11 removed lines are non-executable: 10 lines
of the old module docstring and 1 comment line (`# tokens that make a slash/and legitimate
even without an explicit split word`). No executable line of the frozen pin is removed:
the new `_clause_verdict` dispatch is inserted ahead of the canonical `_scan_composite`
fallback, and that fallback (plus R2/R3/R4 and `findings` / `findings_for_map` /
`findings_for_text` / `regression`) is textually retained.

Correct formulation: **insertion-only in executable code; module docstring and one
comment rewritten.** The r1→r2 delta adds the negation-over-report-noun pattern and the
conditional-antecedent rule only.

## 2. Determinism control

- `run_bar_eval.py` executed twice on the frozen r2 bytes: both outputs
  `sha256 4cb72b064961f732051232a304403b7656f1b953722a2dee109f4478e5bafcc6`, byte-identical
  to the stored `full_bar_results_r2.json`.
- `run_v5_heldout.py` re-executed: `heldout_v5_results.json` unchanged at
  `17ccbccd6984f65a476658946c3e84dfc7e27dbfb4922d620e197d4b9e670d9b`.

## 3. Manifest

`SHA256SUMS` and `checkpoint.json` are regenerated after this addendum; the artifact
events emitted for their earlier hashes are superseded by the events accompanying this
addendum. Every other measured file hash is unchanged.
