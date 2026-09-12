# W066-F2B-REV29-CONTAINMENT-01 — containment defects re-based onto FROZEN rev29

Independent, hash-bound re-base of worker-066's F2b (`AF-SCC-C0-VAC-GEN`) containment
adjudication onto the **current** pins. All prior F2b verdicts in this thread bind the
superseded rev12 (`55d0a1ea`) or the first two rev29 writes (`ca80d134`, `3d9e3d77`); the
live bytes are rev13 `b2ab6acb` and the live manifest is the third rev29 write `815e0807`
(frozen_at 2026-09-12T00:57:26+08:00).

## Method

`pin.py` copies nine inputs to `pinned/` and fails closed on any hash mismatch.
`rebind.py` is a fresh order-relative checker (not a re-run of the predecessor harness): it
derives the reference containment order from the document's own
`implication_ledger.extension_class_containment` sentence and fires only when a
`forbidden_transfers` reason contradicts that order, and it ignores containment denials
that sit inside bracketed (withdrawn) corrections. 13 checks and 8 pre-registered controls
ran on the pinned copies; pins were re-measured at exit.

## Result — verdict `revise` 2.5 at `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe`

| # | check | result |
|---|---|---|
| C1 | canonical ≡ mirror (`b2ab6acb`) | PASS |
| C2 | live rev13 still yields exactly H1+H2 | PASS |
| C3 | both clauses byte-identical to rev12 `55d0a1ea` (carried over, not introduced) | PASS |
| C4 | the 2-edit repair is absent at live bytes | PASS |
| C5 | live + 2 reference edits → finding-free rebased candidate `84b5d3fa29a6` | PASS |
| C6 | worker-008 candidate `98f9ec83` finding-free | PASS |
| C7 | rev12→rev13 delta commutes with the repair (same changed leaf paths) | PASS |
| C8 | no rev13 delta path lies in the two repair subtrees | PASS |
| C9/C10 | sibling C2 `e9a27996`, F1 `d9cebb94` carry neither defect kind | PASS |
| C11 | FROZEN rev29 `815e0807` declares exactly the measured canonical+mirror hashes | PASS |
| C12 | manifest is revision 29, frozen_at 00:57:26 | PASS |
| C13 | declared F0 `0abb9ed8` and consistency evidence `9e335e9b` both resolve live | PASS |

Live defects (both normative carriers — rule_spec R06/R16 — per
`reviews/F2b-containment-normativity-worker-066.json`):

- **H1 `size_premise_inverted`** — `implication_ledger.forbidden_transfers[0].reason` (:246):
  *"C2 is a strictly larger extension class"*. The file's own chain is
  `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`, so E_C2 is the strictly **smaller** extension set.
- **H2 `false_containment_denial`** — `regularity.must_not_conflate[0]` (:152):
  *"No containment with C2 or C0 is asserted here"*, denied in a file that asserts exactly
  that containment at :238, :242-243 and :274 (the sibling C2 rev13 carries the corrected
  nesting wording at the same slot).

Controls: 8/8 matched (single-edit reverts, bare denial, bracketed withdrawn denial,
reversed-chain order-relative probe, denial removed). No pinned byte moved during the run.
`evidence/checks.json`, `evidence/controls.json`, `evidence/freeze_binding.json`.

## Consequence for the pending G-FORM r3 review

FROZEN rev29 `815e0807` freeze-binds the two defective clauses. The evidence-binding repair
(astra-life05) was explicitly bounded against class-semantics changes, so a G-FORM r3
`accept` at these bytes would freeze a normative defect; the ready repair is
`artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff` (semantics of `98f9ec83`,
rebased here to `84b5d3fa`), and it must be folded in **before** the freeze is treated as
final or explicitly ruled non-normative by a reviewer, which this task does not do.

## Falsifier

Re-run `rebind.py` on the same pins. Falsified if: live C0 ≠ `b2ab6acb`; either clause is
absent/changed at rev13; FROZEN rev29 does not declare the measured hashes; the rebased
live+2-edit text is not finding-free; a sibling carries either defect kind at its pin; any
control departs from its expectation; or a reviewer shows the two clauses non-normative at
the bound hash.

## Limits

Machine-checker and text-consistency result at pinned bytes only. Not a claim about the
mathematics of C0/C2 inextendibility, not a gate verdict, not a node status. Verdict binds
`b2ab6acb` and `815e0807` only and is void on any hash move.
