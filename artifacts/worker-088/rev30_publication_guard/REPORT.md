# W088-REV30-PUBLICATION-GUARD-01

Verdict: **BLOCK_REHEARSED_REV30_CANDIDATE__SAFE_ALTERNATIVES_VERIFIED**

| byte state | sha256 | H1 (line 246) | H2 (must_not_conflate[0]) | contradiction |
|---|---|---|---|---|
| live C0 rev29 | `b2ab6acb2bbe` | H1_INVERTED_SIZE_PREMISE | H2_DENIAL_NO_CONTAINMENT | False |
| rehearsed 84b5d3fa | `84b5d3fa29a6` | H1_FIXED_SMALLER_PREMISE | H2_INVERTED_ENTAILMENT_DIRECTION | True |
| corrected 51c253c4 | `51c253c46306` | H1_FIXED_SMALLER_PREMISE | H2_CORRECT_DIRECTION | False |
| nesting-only 4951cc96 | `4951cc969803` | H1_FIXED_SMALLER_PREMISE | H2_AGNOSTIC_NESTING_ONLY | False |
| C2 live (own=C2 control) | `e9a27996dfd3` | H1_UNCLASSIFIED | H2_CORRECT_DIRECTION | False |

## Rehearsal acceptance-suite blindness

- battery on rehearsed candidate: `PASS`, X3c hits `[]`, hard_failures `0`, exit `0`
- dual on rehearsed candidate: `PASS`, findings `0`, exit `0`
- battery on corrected candidate: `PASS`, exit `0`

## Controls

- K1_live_c0: `H2_DENIAL_NO_CONTAINMENT` (expected `H2_DENIAL_NO_CONTAINMENT`)
- K2_rehearsed_candidate: `H2_INVERTED_ENTAILMENT_DIRECTION` (expected `H2_INVERTED_ENTAILMENT_DIRECTION`)
- K3_corrected_candidate: `H2_CORRECT_DIRECTION` (expected `H2_CORRECT_DIRECTION`)
- K4_nesting_only_candidate: `H2_AGNOSTIC_NESTING_ONLY` (expected `H2_AGNOSTIC_NESTING_ONLY`)
- K5_direction_flipped_in_memory: `H2_INVERTED_ENTAILMENT_DIRECTION` (expected `H2_INVERTED_ENTAILMENT_DIRECTION`)
- K6_live_denial_bullet_reimplanted: `H2_DENIAL_NO_CONTAINMENT` (expected `H2_DENIAL_NO_CONTAINMENT`)
- K7_c2_live_own_C2: `H2_CORRECT_DIRECTION` (expected `H2_CORRECT_DIRECTION`)

## Recommendation

- do **not** land `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml` (`84b5d3fa29a677ad`): H1 is correctly repaired, but the replacement regularity.must_not_conflate[0] asserts H2_loc-inextendibility => this class's conclusion (C0-inextendibility), the false converse of the file's own implication_ledger row 241 and a direct contradiction of the retained line 232; the rehearsal's own acceptance tools pass it, so REV30_FREEZE_REHEARSAL_READY does not certify this carrier.
- safe at candidate level: `artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml` (`51c253c463067e25`, H2 H2_CORRECT_DIRECTION) and `artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml` (`4951cc9698032996`, H2 H2_AGNOSTIC_NESTING_ONLY)
- owner condition: land one direction-correct H2 wording (or the nesting-only form), keep the H1 line-246 fix, re-freeze with a strictly increasing revision under the guard, then commission two blind full-schema F2b reviewers at the published hash.

## Falsifier

Any of: (a) a pin in `pins` does not match the declared sha256 at re-measurement; (b) the rehearsed candidate's must_not_conflate[0] is shown to entail C0-inextendibility correctly at the declared bytes; (c) the retained line 232 is shown consistent with the rehearsed candidate's H2 sentence; (d) the same sentence under own=C2 is classified inverted (class-blind checker); (e) either acceptance tool fails on the rehearsed candidate (then the rehearsal was not blind but failing); (f) the corrected candidate 51c253c4 or the nesting-only candidate 4951cc96 is shown to carry an inverted H2 direction or a failing battery; (g) any canonical byte moves during the run.

Non-claims: no canonical path was written; all reads; no gate verdict, no node status, no validation_status, no theorem or physics claim; candidate-level safety only: this is not a full-schema F2b review of the corrected candidates; no claim about which of the two safe candidates the owner should prefer
