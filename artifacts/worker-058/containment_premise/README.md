# W058-CONTAIN-01 — containment-premise audit of the frozen SCC ledger pair

**Worker** `worker-058` (slot 058) · **task** W058-CONTAIN-01 · **node** F2b ·
**classes** `AF-SCC-C0-VAC-GEN`, `AF-SCC-C2-VAC-GEN` · generated 2026-09-12T00:2x+08:00

**Verdict: FAIL — 1 hard failure, 23 statements checked, sensitivity self-test 6/6.**

## Scope declaration

Audits the *internal logical consistency* of extension-class containment, class-size
and statement-strength premises declared inside the frozen canonical SCC ledgers, plus
concordance of the C2 and C0 declarations. It does **not** audit physical truth,
data-class regularity, citation scope, or definitional correctness. It claims **no node
completion and no gate verdict**; interpretation is owned by `astra-lead-formulation`.
Read-only: no canonical file is written.

## Binding

| input | path | sha256 (live = frozen) |
|---|---|---|
| C0 schema | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| C2 schema | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| WCC schema | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |
| manifest | `artifacts/formulation/FROZEN.json` | `af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b` (revision 25) |

All three canonical files were **byte-identical to the authoring tree** at run time and
matched their manifest hashes. Verdicts bind to the hashes above, not to the revision
number: the formulation tree is being re-frozen continuously, so re-run with

```bash
python3 artifacts/worker-058/containment_premise/check_containment_premise.py --root .
```

## Reference order (parsed, not assumed)

Both schemas declare, and the checker parses:

```
E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0
rank (smallest extension set first):  C2 = 0,  C^1,1 = 1,  H2_loc = 2,  C0 = 3
```

Derived rule: higher rank = larger extension set = **stronger** "no proper future
extension" statement. Therefore an entailment must run high-rank → low-rank, and a
forbidden transfer must run low-rank → high-rank. The two declarations are concordant.

## Hard failure

**F1 · `class_size_premise_inverted` · `AF-SCC-C0-VAC-GEN` · line 251**

```yaml
forbidden_transfers:
  - {from: "no proper future C2 extension", to: "this class",
     reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
```

- The class-size **antecedent is false**: with `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0`,
  C2 is the strictly **smaller** extension class than C0, not larger.
- The **consequent is true** (`C2-inextendibility` is strictly weaker than
  C0-inextendibility) and the **transfer direction is correct** (weaker → stronger is
  exactly what must not be licensed). The defect is confined to the one-word antecedent.
- **Exact repair (wording only, no re-derivation required):**
  `"C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker"`

## What passed (23 statements, so the FAIL is not a blanket rejection)

- 6/6 declaration edges across both files match the reference order.
- 14/14 entailment rows (`one_way_entailments`) run high-rank → low-rank, including the
  rows that were corrected in earlier revisions.
- Both `forbidden_transfers` direction tables are correctly oriented, including the row
  that carries the defective reason.
- All containment edges quoted in reason prose match the declared order.
- The comparative `H2_loc-inextendibility is stronger than this class` (C2) is true.

## Relation to worker-08 FORM-SEP-04

`deepseek-flash-08` recorded this same defect as a blocker at the live C0 hash
`a8d899d2…` (rev18/rev20 era, event `2026-09-12T00:11:04+08:00`). This audit is an
**independent implementation** (different tokenizer, order derivation and direction
tables; it does not import or read worker-08's scanner) and shows the sentence is
**unchanged at the rev25 freeze `1bb78ce9…`**. Factual consequence: a recorded blocker
did not gate the rev25 freeze. This artifact is the re-measurement; the freeze/publication
task owns the publication decision.

## Independence and sensitivity (falsifier actually falsifies)

`run_sensitivity_selftest.py` builds mutants in a scratch root and asserts
pre-registered outcomes; result `all_expectations_met = true`:

| case | mutation | expected | observed |
|---|---|---|---|
| M0 | canonical | FAIL, exactly 1 `class_size_premise_inverted`, ≥20 statements checked | FAIL, 1, 23 |
| M1 | apply the proposed repair (`larger`→`smaller`) | PASS, 0 failures | PASS, 0 |
| M2 | swap a C2 entailment row to weaker→stronger | FAIL `entailment_runs_weaker_to_stronger` | caught |
| M3 | reorder the C2 chain so C2/C0 disagree | FAIL chain-concordance / declaration edge | caught |
| M4 | plant an inverted size claim in `subsumption_note` | FAIL `class_size_premise_inverted` | caught |
| M5 | byte-identical copy | identical verdict to M0 | identical |

## Assumptions and limitations

1. The checker treats the `extension_class_containment` declaration as the axiom and
   audits every other premise against it. A *consistently* inverted declaration in both
   files would evade this check by construction; M3 demonstrates it is caught when the
   two files disagree, not when they agree on a wrong order. The declared order is not
   re-derived from the definitions of C0/C2 regularity here.
2. Lexical scans cannot see semantic leaks expressed without regularity tokens; this
   audit does not claim to.
3. Statements outside `implication_ledger` (e.g. `anti_scope`, variants) are not swept
   except where they carry an `E_… subset/contains` edge inside the ledger prose fields.

## Next falsifier

Re-run at the next canonical revision. This audit is falsified if (a) it reports PASS at
the hashes above, (b) a reviewer exhibits a size/strength premise it accepts that
contradicts the declared order, (c) after the one-word repair it still reports
`class_size_premise_inverted` (repair insufficiency), or (d) it reports PASS while the C2
and C0 declarations disagree.

## Artifacts

| path | role |
|---|---|
| `check_containment_premise.py` | independent checker (read-only) |
| `containment_premise_audit.json` | machine-readable findings, binding, falsifier |
| `run_sensitivity_selftest.py` | mutant harness |
| `sensitivity_selftest.json` | pre-registered expectations vs observed |
| `README.md` | this report |
