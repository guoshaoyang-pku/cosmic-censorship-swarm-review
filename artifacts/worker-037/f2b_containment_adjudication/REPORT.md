# W037-F2B-CONTAINMENT-ADJUDICATION-01 — live intra-artifact contradictions in the frozen F2b schema

**Worker:** worker-037 (self-selected class-bound task; no inbox card existed for this slot)
**Node / gate:** F2b / G-FORM (class `AF-SCC-C0-VAC-GEN`); calibration evidence for G-AUDIT A1
**Pins (T0 = T1, measured):**

| path | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |

## Question

At the frozen rev29 pins, does the C0 schema contradict its own declared extension-class
containment, and do the F2b **accept** verdicts at that pin dispose the named carriers?

## Result — revise (scoped to the two carriers)

**W037-CT-01 (content-level, self-contradiction).** `schemas/af_scc_c0_vacuum.yaml:152`
(`regularity.must_not_conflate[0]`) says *"No containment with C2 or C0 is asserted here"*.
The same file at `:239` declares `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`,
and at `:241–242` declares `E_H2loc subset of E_C0` and `E_C2 subset of E_H2loc`. The denial
contradicts the file's own ledger, including the very nesting the C2 sibling records as the
R2-major repair.

**W037-CT-02 (content-level, inverted premise; operative direction correct).**
`schemas/af_scc_c0_vacuum.yaml:246` (`implication_ledger.forbidden_transfers[0].reason`) says
*"C2 is a strictly larger extension class"*. The file's own chain makes `E_C2` the
**innermost/smallest** set. The operative content of the row is nevertheless correct
(`from: no proper future C2 extension`, `to: this class`, conclusion "strictly weaker",
consistent with `subsumption_note`: "runs C0 => H2loc => C2, never the reverse"), so the defect
is the stated premise, not the licensed transfer.

**W037-CT-03 (corroboration, not class leakage).** The C2 sibling at `e9a27996dfd3`
(`:152`–`:155`) carries the corrected wording and explicitly records the C0 sentence as wrong
(*"the earlier 'no containment with C2 is asserted' was wrong"*), while keeping the two classes
as separate tokens with nested extension sets. The defect is therefore **intra-file consistency**,
not a C0/C2 class merge.

**Normativity.** FORM-RULE-SPEC v1.2 R06 requires a non-empty `must_not_conflate` and R16 requires
the `implication_ledger` containment plus the forbidden converse — both carriers are required
slots of the frozen class contract, not advisory prose.

## Gate calibration (audited-positive fixture)

| instrument | live C0 `b2ab6acb2bbe` |
|---|---|
| `check_class_schema.py` (R01–R16, structural) | **pass**, 0 failed rules |
| `spec_conformance_audit.py` (semantic stage) | **accept**, 0 failed rules (SEM-1..3 undecided) |
| `run_acceptance.py` (two-stage pipeline) | **exit 3 PREFLIGHT FAIL** — rebased corpus still binds rev11 C0 `1bb78ce9b357`, current base `b2ab6acb2bbe` |

Both canonical stages are blind to W037-CT-01/02 (mutation controls M1/M2 confirm neither stage
flips when either carrier is repaired). Proposed rule **R-CT** (implemented in the checker, *not
adopted*): (a) flags a `must_not_conflate` clause denying a containment pair the file's own
ledger declares; (b) flags a `forbidden_transfers` reason whose size ordering is the reverse of
the declared chain. R-CT fires exactly twice on the live fixture (lines 152, 246), zero times on
the C2 sibling, the WCC/F1 schema, and the corrected-both mutant M3. An injected `C0 or C2` merge
leak (M4) is invisible to R-CT and to the structural gate — that leak class belongs to the
class-separation detector, not to this rule (scope note, not a coverage claim).

## Accept-verdict disposition at the same pin (pre-registered needle test)

| verdict | reviewer | 152 denial | 246 inversion |
|---|---|---|---|
| accept 4.0 | worker-052 | NOT_ADDRESSED | NOT_ADDRESSED |
| accept 4 | worker-071 | NOT_ADDRESSED | NOT_ADDRESSED |
| accept 4.0 | worker-072 | NOT_ADDRESSED | NOT_ADDRESSED |
| accept 4.0 | worker-090 | NOT_ADDRESSED | NOT_ADDRESSED |
| revise 3.5 | worker-085 | DISPOSED | NOT_ADDRESSED |
| revise 3.5 | worker-053 | NOT_ADDRESSED | DISPOSED |
| revise 3.5 | worker-075 | NOT_ADDRESSED | DISPOSED |
| revise 2.5 | worker-066 | DISPOSED | DISPOSED |

All four accepts at `b2ab6acb2bbe` leave both live carriers undisposed; the finding register
exists on the revise side. This is the r3 round's own falsifier ("an accept that ignores a named
hard finding still visible at that hash").

## Scope / does not claim

Read-only; no canonical, owner or third-party file was written (mutations ran on temp copies).
No gate verdict, no node status, no `validation_status` promotion, no claim of physical truth,
no claim that F2b is unacceptable overall — only the two carriers are adjudicated. R-CT is a
proposal; adoption is the audit lead's decision.

## Falsifier

Re-run at the same pins: falsified if (a) the C0 chain does not declare `E_H2loc ⊆ E_C0` and
`E_C2 ⊆ E_H2loc`, (b) line 152 does not deny containment of C2/C0, (c) line 246 does not call C2
strictly larger, (d) any of the four accept verdicts is shown to dispose both carriers, (e) R-CT
fires on the corrected M1/M2/M3 mutants or on the C2 sibling / F1 schema, or (f) T1 ≠ T0 (drift
voids the run rather than falsifying it).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-037/f2b_containment_adjudication/check_f2b_containment.py
# exit 0 = pins stable + 8/8 controls; writes report.json
```
