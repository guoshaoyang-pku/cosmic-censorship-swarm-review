# W066-F2B-CONTAINMENT-NORMATIVITY-01

Bounded class-bound worker task (class `AF-SCC-C0-VAC-GEN`, node F2b) taken by worker-066
because no assignment card exists in `comms/inbox/worker-066.jsonl`. Reviewer verdict only:
workers cannot set `done`/`passed` or a gate verdict.

## Why this task, now

`astra-life05-evidence-binding-repair` (REC-12) rewrote all three canonical schemas at
`2026-09-12T00:53:20+08:00` to refresh the stale `f0_binding` evidence hash. That repair was
bounded to evidence binding and explicitly forbade class-semantics changes. The two F2b
containment clauses that worker-008 found and `W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01`
confirmed at rev12 are **still present at the new rev13 bytes**, so the pending FROZEN rev29
and the `astra-life05-verify-gform-r3` re-review would freeze them again.

The predecessor verdict left exactly one resolution open: *"or a reviewer may rule the two
clauses non-normative prose at the bound hash, which this adjudication does not."* This task
decides that question mechanically. It does not re-run the predecessor's text checker as the
primary instrument and does not modify any canonical path.

## Target

| item | value |
|---|---|
| target | `schemas/af_scc_c0_vacuum.yaml` at `b2ab6acb2bbe7f86…` (rev 13, revised_at 00:53:20) |
| sibling | `schemas/af_scc_c2_vacuum.yaml` at `e9a27996dfd308bd…` (rev 13) |
| prior rev12 target | `55d0a1ea9bda96b8…` (predecessor pin) |
| rule basis | `artifacts/formulation/rule_spec.json#40f9bb9e657b` R06 and R16 |
| binding gate | `artifacts/formulation/tools/check_class_schema.py#000e09e46b2f` |
| candidate repair | `artifacts/worker-008/…/candidate_rev12/af_scc_c0_vacuum.yaml#98f9ec83c487` |

## Verdict: `normative_content_defect` (score 2.5, revise)

1. **(A) Normative carriers.** R06 requires a non-empty `regularity.must_not_conflate` list;
   R16 requires `implication_ledger.one_way_entailments` **and** `forbidden_transfers` and
   machine-checks their direction tokens. Both carriers are required slots of the frozen class
   contract. The document carries **no** advisory / non-normative / prose-only marker on either
   carrier (0 hits).
2. **(B) Content is not machine-enforced.** The canonical gate returns `pass` for the defective
   rev13 wording **and** for corrected, strengthened-false, empty-string and nonsense variants
   (M2/M3/M6/M7/M8/M9/M10), while the same gate *does* reject an emptied `must_not_conflate`
   (R06, M1) and an exact reversed `forbidden_transfers` direction (R16, M4). The gate's own
   docstring lists this blind spot ("only that it is present, non-vague … and class-consistent").
   A gate PASS therefore cannot certify these clauses, and cannot discharge the blocker.
3. **(C) Carried forward.** The two sentences are byte-identical at rev12 `55d0a1ea` and rev13
   `b2ab6acb`; the rev13 delta touched only `revised_at`, `revision`, the revision-history entry
   and the `f0_binding` evidence pin. The repair did not repair them.
4. **Independent findings at rev13** (order parsed from the document itself, largest set first
   `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`):
   - **W066-R13-F2B-H1** — `implication_ledger.forbidden_transfers[0].reason` (:246) says
     "C2 is a strictly larger extension class" although E_C2 is the **smallest** set in the
     declared chain. The prohibition's conclusion ("strictly weaker") is right; its stated
     premise is inverted.
   - **W066-R13-F2B-H2** — `regularity.must_not_conflate[0]` (:152) carries the live denial
     "No containment with C2 or C0 is asserted here" while the same file asserts that
     containment in `extension_class_containment` and four `one_way_entailments` rows. The
     sibling C2 rev13 carries the corrected nesting wording and records the earlier denial as
     wrong, so the sibling asymmetry persists.

## Controls (12/12 matched pre-registration)

| mutant | expected | observed |
|---|---|---|
| M0 pristine rev13 | pass | pass |
| M1 `must_not_conflate: []` | fail:R06 | fail:R06 |
| M2 H2 replaced by corrected nesting | pass | pass |
| M3 H2 replaced by false "disjoint, no containment either direction" | pass | pass |
| M4 `forbidden_transfers[0]` C0→C2 (required direction forbidden) | fail:R16 | fail:R16 |
| M4b partial reversal (from=C0, to=this class) | pass | pass |
| M5 `implication_ledger` removed | fail:R16 | fail:R16 |
| M6 `forbidden_transfers[0].reason` removed | pass | pass |
| M7 containment chain reversed | pass | pass |
| M8 H1 premise corrected | pass | pass |
| M9 H1 premise replaced by nonsense | pass | pass |
| M10 H2 empty string | pass | pass |

## Consequence for G-FORM / recommendation

- The 2-edit semantic repair is **outside REC-12's four bounded items**. Either fold it into the
  same revision before the FROZEN rev29 write, or open a separate bounded owner card. A
  gate-green F2b at rev13/rev29 that still contains these clauses is not acceptable evidence,
  because the clauses are normative and no machine check catches them.
- Acceptance for any such repair: canonical gate PASS (necessary, not sufficient) **and** an
  order-relative containment checker returning zero findings **and** single-edit revert controls
  firing exactly their own finding **and** sibling C2 unchanged at its frozen hash.
- `astra-life05-verify-gform-r3` should include a containment check, not only the canonical gate.

## Falsifier

Re-run `normativity.py` on the pins. Falsified if: the target bytes move; the document at the
bound hash marks either carrier advisory/non-normative; `rule_spec.json` drops R06/R16 or the
containment requirement; the canonical gate distinguishes corrected from defective wording; any
pre-registered control departs from its expectation; or the two sentences are absent at the
bound hash.

## Limits

Text-level rule-scope adjudication only; no claim about the mathematics of C0/C2
inextendibility. Binds the pinned bytes only; a hash move voids the verdict.
