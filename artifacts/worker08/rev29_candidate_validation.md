# W008-FORMSEP04-CANDIDATE-VALIDATION-01

- generated: 2026-09-12T01:05:11+08:00
- node/gate/classes: F2 / G-CLASSBIND / AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN
- verdict: **CANDIDATE_CLEARS_FORMSEP04**
- live pins: C0 `b2ab6acb2bbe`, C2 `e9a27996dfd3`, FROZEN rev29 `815e08079aef` (frozen_at 2026-09-12T00:57:26+08:00)

## What was done

1. Reconstructed worker-066's announced rebased F2b repair candidate from the LIVE
   C0 bytes plus the two reference edit pairs, which were themselves derived by
   line diff of the rev12 archive `55d0a1ea` against the pinned rev12 candidate
   `98f9ec83` (not copied from worker-066's source text).
   Reconstruction hash `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40` vs announced `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`: **MATCH**.
2. Ran the full FORM-SEP-04 X1-X5 acceptance battery on the candidate and on the
   live canonical control at the same instant.
3. Ran the fail-closed dual containment checker on both, plus a wrong-expect-hash
   fail-closed control.

## Results

| check | candidate | canonical control |
|---|---|---|
| FORM-SEP-04 battery verdict | PASS | FAIL |
| hard failures | [] | [{'kind': 'containment_inversion_in_ledger', 'hits': [{'file': 'C0', 'path': 'implication_ledger.forbidden_transfers[0].reason', 'match': 'C2 is a strictly larger extension class', 'sentence': 'C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker', 'classification': 'containment_inversion', 'contradicts': 'frozen containment E_C2 subset E_H2loc subset E_C0 (extension_class_containment, rev7/rev18)'}]}] |
| X3c containment inversions | 0 | 1 |
| dual checker verdict | PASS | FAIL |
| dual findings | 0 | 3 |

Repair surface: 2 changed lines, changed leaves `['implication_ledger.forbidden_transfers[0].reason', 'regularity.must_not_conflate[0]']`, metadata moved `[]`.

## Falsifier

Any of: (a) the reconstructed candidate does not hash to 84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40; (b) a FORM-SEP-04 X1-X5 battery run on the candidate returns any expectation violation, unjustified foreign-semantics hit, converse assertion, containment inversion, composite-regularity violation or hard failure; (c) the fail-closed dual checker returns any finding on the candidate; (d) the same battery/checker pair on the unrepaired live C0 b2ab6acb2bbe does not still return exactly the two known containment defects (X3c=1, dual=3 findings/2 kinds); (e) any moved leaf outside the two named repair paths, or a moved revision/f0_binding/pointer leaf.

## Limitations

- Candidate bytes are non-canonical and were never published; the owner (astra-lead-formulation) owns any rev14 wording and re-freeze.
- The two repair fragments are the rev12 reference wording; a different owner wording would clear the same logical defects but hash differently.
- This does not re-adjudicate the normativity of the two carriers (done independently by worker-066) nor the metalinguistic scoping reading of H2.
- No gate verdict, node status or validation_status is set by this measurement.

Worker-level measurement only; no gate verdict, node status or validation_status is set.

- candidate bytes: `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml#84b5d3fa29a6`
- this bundle: `artifacts/worker08/rev29_candidate_validation.json`
