# Instrument amendments — W050-F2B-REPAIR-CANDIDATE-INDEPENDENT-VERIFY-06

Two defects in the *instrument* (not in the candidate, not in the pre-registered predicates) were
found on the first run, disclosed here, fixed, and the run repeated. The first run is preserved
byte-for-byte as `report.run1.json` / `per_check.run1.jsonl`; the final run is `report.json` /
`per_check.jsonl`. Pin guard, pre-registered predicate semantics and control set are unchanged.

## Run 1 (01:13, exit 2, `CANDIDATE_REJECTED`, controls 6/6 fired)

| check | run-1 result | cause |
|---|---|---|
| C4 `D2_direction_corrected` | false failure | `DIR_RE` captured the object token as `E_C0,` (trailing comma); the rank lookup uses `C0`, so the direction could not be parsed |
| C6 `no_residual_adverse_carriers` | false failure | raw substring `strictly between` matched the candidate's line 152, where the phrase appears only **inside quotes as a prohibited phrase** — which the base file itself mandates |
| C7 `cross_sibling_agreement` | false failure | dependent on C4's `dir_ok` |

## Amendments

**A1 (check C4).** `tok_of()` now strips trailing `,.;:` before removing the `E_` prefix. The
predicate is unchanged: subject `smaller` object ⇒ subject must be the smaller extension set.
Run-1 cause removed; no candidate property was involved.

**A2 (check C6).** `strictly between` is counted only when unquoted
(`(?<!["'])\bstrictly between\b(?!["'])`). The two D1/D2 carriers are still raw-substring checks.
This matches the pre-registration's VF3 (an actual denial/ordering claim), which a quoted
prohibition is not.

## Run 2 (final, exit 0, controls 6/6, all 9 checks pass)

`CANDIDATE_VERIFIED_MINIMAL_FIX`: D1 and D2 carriers are removed by exactly the two declared 1-for-1
line replacements (152 and 246), the replacement line 246 direction is mechanically consistent with
the file's own chain `C0 ⊃ H2loc ⊃ C^1,1 ⊃ C2`, the replacement line 152 defers containment to
`implication_ledger.extension_class_containment`, and no structural invariant moved. D3 is unchanged
by the candidate and is classified as a global, F2a-symmetric F0/VOCAB representation divergence
(`W050-R1-D3`), outside the candidate's declared scope.

## Why this is disclosed rather than silently fixed

The pre-registration was frozen before either run; amending a frozen instrument after seeing its
output is exactly the move that can launder a desired result. Both amendments are recorded with
before/after text, both narrow the failure set (run 1 → run 2), and both are traceable to a concrete
parsing artifact reproducible from `report.run1.json`. Neither touches the candidate bytes, the pin
list, or any predicate threshold. An independent reader can re-apply A1/A2 in reverse to
`verify_repair_candidate.py` and recover the run-1 behaviour.
