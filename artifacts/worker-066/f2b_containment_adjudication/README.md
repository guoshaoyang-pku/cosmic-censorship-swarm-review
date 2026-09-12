# W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01

Independent, hash-bound adjudication of the open F2b blocker
`w008-f2b-20260912T003407+0800-blocker-rev12`, taken as one bounded class-bound task
(class `AF-SCC-C0-VAC-GEN`, node F2b) by worker-066. Reviewer verdict only: workers cannot
set a gate verdict or a node done.

## Target

| item | value |
|---|---|
| target | `schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda` (rev 12, FROZEN rev27/28 pin) |
| sibling | `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc` (rev 12) |
| claim adjudicated | worker-008: two containment inconsistencies persist at rev12; C2 already corrected |
| method | fresh checker (`adjudicate.py`), order-relative; no import of worker-008's checker; 7 pre-registered controls |

## Result: claim CONFIRMED, verdict revise 2.5

Both contested clauses are **byte-identical to the superseded rev11 bytes** (they moved
line numbers only), so rev12 carried them over rather than introducing them:

1. **W066-R12-F2B-H1** — `implication_ledger.forbidden_transfers[0].reason`, line 245:
   "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker".
   The file's own chain (line 238) is `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`,
   so E_C2 is the *smallest* extension set. The clause's conclusion ("strictly weaker") is
   correct under the chain; only the premise token is inverted, so the stated reason does not
   support the transfer prohibition as written. Fix: "strictly smaller".
2. **W066-R12-F2B-H2** — `regularity.must_not_conflate[0]`, line 151:
   "No containment with C2 or C0 is asserted here" in a file that asserts exactly that
   containment at lines 238, 242-243 and 274, and whose sibling C2 (same revision) replaced
   the same sentence with the nesting statement and recorded the earlier wording as wrong
   ("[R2 major: the earlier 'no containment with C2 is asserted' was wrong]"). Fix: state the
   nesting, as the candidate does.

Rescue reading tested and rejected: the preceding clause ("phrased in terms of CURVATURE, not
metric differentiability") does not scope the denial; the denial sentence is unqualified and the
scalar itself points at `implication_ledger`. Details in `evidence/checks.json`
(`c0_denial_rescue_reading`).

## Machine-green at the same bytes (not blocking)

- no duplicate YAML mapping keys (C0 and C2); C0/C2 chains agree; `f0_binding` hash matches the
  live declared-F0 taxonomy `0abb9ed8a961`; `class_contract_pointer` resolves in `classes.*`.
- sibling C2 passes the checker (the quotation guard suppresses its recorded-as-wrong wording),
  which is why the checker is not merely flagging every mention of containment.

## Repair candidate (worker-008, independently re-measured)

`artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml#98f9ec83c487`
changes exactly two leaf paths, leaves every binding field byte-equal, and clears both defects.
Re-run per-defect single-revert controls fire exactly one finding each. The candidate is not
published: the owner must publish, mirror, re-freeze and re-run the containment check.

## Controls (all 7 matched pre-registration)

| control | expected | observed |
|---|---|---|
| pristine canonical C0 | H1 + H2 | H1 + H2 |
| candidate 98f9ec83 | none | none |
| candidate, H1 reverted | H1 only | H1 only |
| candidate, H2 reverted | H2 only | H2 only |
| canonical, polarity flipped | H2 only | H2 only |
| canonical, chain reversed | H2 only | H2 only |
| sibling C2 rev12 | none | none |

## Falsifier

Re-run `adjudicate.py` on the pins: falsified if C0 `55d0a1ea9bda` stops yielding both
findings, if a control departs from its pre-registered expectation, if the candidate changes a
binding field or more than the two named leaf paths, or if a reviewer shows the two clauses are
non-normative prose at the bound hash.

## Limits

Text-level consistency of a formal-model artifact only; no claim about the mathematics or
physics of C0/C2 inextendibility. Verdict binds the pinned bytes; a hash move voids it.
