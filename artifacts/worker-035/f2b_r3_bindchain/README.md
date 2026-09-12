# worker-035 F2b r3 bind-chain verification

Fresh independent G-FORM verdict on F2b (`schemas/af_scc_c0_vacuum.yaml`) at the live
post-repair revision 13 `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`, plus the f0_binding hash-chain addendum requested by
`audit-r2-F2b-bindchain-worker-035`. The r2 pin `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` (rev12) was a moving target and is
superseded; no verdict is issued at it.

- `measurements.json` -- every declared/measured hash and the bind-chain resolution
- `classsep_regression_stdout.txt` -- independent re-run, 17/17 leaks, 10/10 controls
- `check_class_schema_stdout.json` -- canonical structural check, pass 0 failed rules
- `taxonomy_cases_check_report.json` -- corpus re-check, 16/20, 11/11 controls
- `entry_hashes_audit.json` -- collateral stale declared-hash audit (9/12 mismatch)

Verdict: **revise** (score 3.0), one hard failure: the stale "No containment with C2 or C0"
bullet at `regularity.must_not_conflate[0]` contradicts the same file's implication ledger,
the C2 sibling's corrected wording, and VARIANT_REGISTRY H2LOC strength. No shared artifact
was edited; worker events cannot move gates or status.
