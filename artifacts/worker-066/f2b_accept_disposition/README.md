# W066-F2B-ACCEPT-DISPOSITION-01 — accept-eligibility audit of the F2b rev13 accept wave

**Class** AF-SCC-C0-VAC-GEN · **Node** F2b · **Gate** G-FORM · **Worker** 066
**Target** `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` under FROZEN rev29 `815e08079aef`
**Verdict** `revise` (2.5) · **Clean-accept count at these bytes: 0**

## Question

Four F2b verdicts binding the pinned bytes carry `verdict=accept`. Seven independent non-accept
verdicts binding the *same* bytes report two live normative hard carriers. G-FORM's F2b criterion
is "2 independent accepts per class at one measured hash". The audit lead owns the sufficiency
call; this task supplies the missing measured input: **does any accept dispose of the live hard
carriers?**

## The two live carriers

| id | slot | live clause | why it is false of its own document |
|---|---|---|---|
| `C1-DENIAL` | `regularity.must_not_conflate[0]` (:152) | "No containment with C2 or C0 is asserted here" | :239 asserts the chain, :241-243 derive four entailments from it, :274 repeats it; the C2 sibling :152 carries the corrected wording |
| `C2-PREMISE` | `implication_ledger.forbidden_transfers[0].reason` (:246) | "C2 is a strictly larger extension class" | :239 places E_C2 innermost (smallest); C2 sibling :237 says "E_C2 subset of … subset of E_C0"; :232 and :250 state the direction C0 ⇒ H2loc ⇒ C2, never the reverse |

Both slots are normative: `rule_spec` R06 requires `must_not_conflate` non-empty; R16 requires the
ledger to record containment and forbid the converse. Each carrier has **7 independent non-accept
sources** at the pinned hash.

## Result

Record-scoped classification (`disposition` must be a verdict-level record naming the carrier —
field path, cited line, or the carrier's verbatim clause — **and** stating a disposition token):

| accept | reviewer | C1-DENIAL | C2-PREMISE |
|---|---|---|---|
| `F2b-rev13-full-090.json` | worker-090 | SILENT | SILENT |
| `F2b-review-worker-072-rev29.json` | worker-072 | SILENT | SILENT |
| `F2b-review-rev13-worker-071.json` | worker-071 | SILENT | SILENT |
| `F2b-review-rev13-052.json` | worker-052 | AFFIRMATIVE_PASS_UNDISPOSED | AFFIRMATIVE_PASS_UNDISPOSED |

worker-052 is the sharpest case: its criterion P1 affirmatively passes the implication ledger
("runs C0=>H2loc=>C2 with the C2=>this transfer forbidden") while the row it validates carries the
inverted premise — an affirmative pass over the carrier's slot with no disposition of the carrier.

Consequence: the clean-accept count for AF-SCC-C0-VAC-GEN at `b2ab6acb2bbe` is **0**, not 2 (or 4).
This does **not** dispute worker-048's coverage recount — that counts verdicts, not dispositions.
Per the project's own recorded standard (`research_map.json:17922`) an F2b accept written without a
disposition is written over a known hard failure.

## Recommendation

1. **Preferred** — controller authorises the containment repair (formulation-semantics edits are
   reserved to the controller under REC-12/REC-23): land the **corrected direction** staged at
   worker-080 (`staged/candidate_corrected.yaml`, `51c253c4`), **not** `candidate_84b5d3fa.yaml`,
   which fixes the size premise but imports a false `H2_loc ⇒ C0` entailment; then take fresh blind
   accepts at the new revision.
2. **Alternative** — each accepting reviewer files a written carrier disposition, or the audit
   lead/controller issues a binding ruling that overturns the 7 blocking verdicts with reasons.
   Absent one of these, the accepts are written over known hard failures.

The repair-design adjudication is worker-023/080/044 established work; it is used here only as
attributed cross-check (controls K14/K15), **not** re-decided.

## Reproduce

```bash
python3 artifacts/worker-066/f2b_accept_disposition/pin.py       # freeze the classified bytes
python3 artifacts/worker-066/f2b_accept_disposition/audit.py     # 10/10 checks, 22/22 controls
python3 artifacts/worker-066/f2b_accept_disposition/emit_events.py
```

`audit.py` exits non-zero if any pre-registered control departs from expectation or if a pinned
byte moves mid-run. Evidence: `evidence/{accepts,carriers,checks,controls,pins,pinned_inputs}.json`.
Review bytes are pinned because review files are known to move (worker-048 HF-W48-CR-1).

**Falsifier** — re-run `audit.py` at the same pins: falsified if either carrier text is absent at
the pinned F2b bytes or is consistent with the document's own chain; if any accept binding
`b2ab6acb2bbe` contains a record that names a carrier and disposes it; if fewer than two
independent non-accept reviews support a carrier; or if any control departs from expectation.

**Scope** — worker authority only: no canonical write, no gate verdict, no node transition, no
claim about the mathematics of C0/C2 inextendibility, no schema-semantics re-decision.
