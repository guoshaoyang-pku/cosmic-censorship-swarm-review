# W038-F2B-REV13-COV-03 — counted-accept coverage audit, F2b @ rev29

**Worker:** worker-038 · **Class:** `AF-SCC-C0-VAC-GEN` · **Node:** F2b · **Gate:** G-FORM
**Pin:** `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (mirror byte-identical) under
FROZEN rev29 `artifacts/formulation/FROZEN.json#815e08079aef`
**Verdict:** `revise` 3.0 (advisory; cannot set a gate verdict or node status)
**Instrument:** `check_f2b_cov03.py` — 43/43 assertion checks PASS, 1 recorded finding, exit 0.

## Question

REC-33 (01:10) counted F2b coverage as **2 full-schema accepts** `{worker-072, worker-090}`.
Do those accepts — and the accepts that landed after the decision — actually cover the
implication-ledger axis on which three independent reviewers reported the inverted sentence
`implication_ledger.forbidden_transfers[0].reason`?

## Live state at run time (2026-09-12T01:3x, accepted stream)

| reviewer | verdict | score | full-schema flag | instrument ledger check | containment | reason | line-152 denial |
|---|---|---|---|---|---|---|---|
| worker-072 | **accept → revise 3.0** (self-superseded 01:15:24) | 4.0 → 3.0 | none → true | `check_f2b.py:210-219` c6 (row-level from/to) | no | no | no |
| worker-090 | accept | 4.0 | true | `check_f2b_rev13_full.py:298-305` C04 | no | no | no |
| worker-071 | accept | 4.0 | true | `review_checks.json` 26/26 token/leak scan | no | no | no |
| worker-052 | accept | 4.0 | true | `check_f2b_rev13_052.py:273-274` B8 substring | no | no | no |

- **REC-33's count is stale both ways:** worker-072 self-superseded its accept with
  `revise 3.0` at 01:15:24 on hard failures **W072-F2B-HF-01** (line-152 denial inside
  `regularity.must_not_conflate`) and **W072-F2B-HF-02** (line-246 reason vs the line-239
  containment chain); worker-071 and worker-052 landed full-schema accepts at 01:11:30.
- Live full-schema accept count = **3** = `{worker-052, worker-071, worker-090}`, not 2.

## Reproduced at the pinned bytes (scratch mirror, read-only on canonical paths)

| instrument | exit | recorded result |
|---|---|---|
| worker-072 `check_f2b.py` | 0 | `PASS`, 33/33 |
| worker-052 `check_f2b_rev13_052.py` | 0 | `VERDICT: accept` |
| worker-090 `check_f2b_rev13_full.py` | 0 | `accept`, 44 checks, 0 blocking, 8/8 controls |

All three accepts reproduce on bytes that contain both contradictions.

## Contradictions at the pinned bytes (primary bytes)

- **D1 / HF-02 / W053-F2B-REV29-01 / W038-F2b-C13a** — line 246 reason
  `"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"`
  contradicts line 239 `extension_class_containment` `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`
  (E_C2 is the *smallest* extension set). The same file's row 247 and the F2a sibling both use the
  correct wording `"the converse containment is false"`. Repair: line 246 first clause →
  `"E_C2 is a strictly smaller extension class (E_C2 subset of E_C0)"`.
- **D2 / HF-01 / W038-F2b-C13b** — line 152 `regularity.must_not_conflate` carries the live denial
  `"No containment with C2 or C0 is asserted here"` while line 239 asserts that containment.

## Coverage result

Mutant matrix (six byte variants; own detector + the three live predicates transcribed verbatim):

| variant | own detector | 072 c6 | 090 C04 | 052 B8 |
|---|---|---|---|---|
| V0 pinned | fires | pass | pass | pass |
| V1 line-246 repair | D1 cleared, D2 still fires | pass | pass | pass |
| V2 transfer-direction flip | fires | **FAIL** | pass | pass |
| V3 containment chain inverted | fires | pass | pass | pass |
| V4 line-152 denial removed | D1 still fires | pass | pass | pass |
| V5 both repaired | silent | pass | pass | pass |

- **0 of the 3 live full-schema accepts** reads `extension_class_containment` or any
  `forbidden_transfers[*].reason`; **0** tests the line-152 denial.
- Only the **superseded** worker-072 c6 checked row-level from/to direction; worker-090's C04 is
  satisfied by any C2-from row and worker-052's B8 is a substring presence test, so a row-0
  direction flip escapes both (V2).
- Therefore the accept cluster is unanimous only on axes that exclude both contradictions, and the
  gate-blocking defect at `b2ab6acb2bbe` survives every live accept unrepaired.

## Falsifier

Any of: (i) a counted accept instrument contains a check that reads `extension_class_containment`
or a `forbidden_transfers[*].reason` and fails at `b2ab6acb2bbe`; (ii) worker-071/052/090 is an
author of the schema or of the FROZEN rev29 pin; (iii) the canonical/mirror bytes or any cited
artifact hash move from the values pinned in `report.json`; (iv) line 246 already reads
`strictly smaller` or line 152 no longer carries the denial at fresh measurement; (v) the accepted
stream shows a live full-schema accept whose instrument covers the containment/reason axis.

## Files

- `check_f2b_cov03.py` — deterministic instrument (stdlib + PyYAML), writes only this directory and `tmp/w038_f2b_cov03/`
- `report.json` — full record: pins, checks, census, mutant matrix, runs, conclusion
- `raw/` — raw run logs for the three reproduced instruments plus report snapshots
