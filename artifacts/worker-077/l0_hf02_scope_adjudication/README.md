# W077-L0-HF02-SCOPE-01 — scope adjudication of A0 HF-02 against ledger rows

**Worker:** worker-077 (bounded execution worker) · **Node:** L0 · **Gate:** G-LIT · **Scope token:** GLOBAL
**Target:** the 8-row finding `W097-L0R3-F1` at `ledger/theorems.jsonl` sha256 `a1674f094979…`
(D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528)
**Status:** worker evidence only — no gate verdict, no ledger write, no node promotion.

## Why this task

The literature lead's HOLD (`lit-l6-20260912-006`) says L0 needs two independent accepts but both
verdicts binding `a1674f094979` are `revise` on the same finding: 8 rows "disjoin two frozen class
ids" under A0 `HF-02` (`evaluation_rubric.yaml:175-180`). Worker-097 declared its own void-condition:

> "…or a sentence in A0 HF-02/HF-14 whose scope excludes ledger rows (which would void W097-L0R3-F1)."

That is the question this instrument answers, from the frozen bytes only.

## Method (deterministic, read-only)

`adjudicate_hf02_scope.py` pins 10 inputs at T0, re-hashes at T1, and runs:

| check | what it measures |
|---|---|
| S-A | the rubric's own field vocabulary: HF-01 is `claim.`-prefixed, HF-14 explicitly says "ledger or claim record", `metrics.class_binding` is defined over "claims whose `class_id` is frozen, **singular**", taxonomy guard G1 binds claims |
| S-B | canonical implementation routing: `audit_run.py` sends ledger rows to `records`; `audit_lib.check_class_binding` reads `claim.get("class_id")` and never `class_ids`; the only ledger-scoped HF-02 branch implemented is invented-class-token membership; `build_literature.py` declares `class_ids` a list restricted to the four frozen classes (extension labels go to `ledger_tags`) |
| S-C | substantive re-check of the 8 rows against the real anti-merge rule (G3 merged-regularity regex, copied from `artifacts/worker-01/validate_taxonomy.py`) + frozen-token membership |
| S-D | the ledger-scoped branch that *is* in scope: all 62 rows' class tokens ∈ four frozen classes |
| S-E | canonical-checker oracle on synthetic claims (clean / second-class mention / merged C0-or-C2 / ledger-shaped record) |

Controls: merged-regularity mutant fires; invented-token mutant fires; clean row stays clean;
oracle agrees on all 5 synthetic cases; two runs give identical digests.

## Result

* **Ruling.** In operation the HF-02 disjunction branch is **claim-scoped**. The class_binding
  metric, guard G1, `PROTOCOL.md` rule 1, the canonical checker and the ledger builder contract all
  treat `class_id` singular as the claim field and `class_ids` as a designed list whose only hard
  rule is membership in the four frozen classes. Applying the branch to a ledger row's plural
  `class_ids` list is a category error; **`W097-L0R3-F1` is void on its stated basis**.
* **Tension, stated honestly.** The HF-02 phrase itself says "disjunction of class_ids" (plural) and
  does not name claims, so the phrase alone does not settle scope. The ruling rests on the metric
  definition + implementation routing + builder contract. A one-line rubric clarification would
  remove the ambiguity (documentation change, not a ledger repair).
* **Even under the literal arity reading** (`len(class_ids) > 1`), the 8 named rows are not
  substantive disjunctions: 4 intermediate-regularity relations, 2 intermediate-regularity
  definitions, 2 shared antecedents; **0/8** match the merged `C0/C2` pattern, **0/8** carry a
  non-frozen token.
* **Residual.** The rows bind two classes because their subject matter sits between C0 and C2
  (Lipschitz / L² / C^{0,1} regularities) or is an antecedent shared by WCC and SCC (Kerr
  stability). The taxonomy has no intermediate-regularity class (new ids deferred to Human PI;
  variants registered instead) and ledger rows have no explicit relation field. If strict
  single-class rows are wanted that is a schema/documentation extension, not a content repair.
* **Advisory (out of ruling scope).** The canonical `audit_lib` merged-regularity regex does not
  normalize braces (`C^0 or C^2` is missed), while taxonomy guard G3 requires copying worker-01's
  normalization; recorded by the S-E braced-spelling case.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-077/l0_hf02_scope_adjudication/adjudicate_hf02_scope.py   # exit 0 = instrument ok
```

Outputs: `report.json` (full check tree, controls, pins, drift, verdict) and `entry_hashes.json`.
Exit 10 means an input drifted during the run and the ruling is void.

## Falsifier

A rubric sentence applying the disjunction detector to ledger records or to the plural field
`class_ids`; any of the 8 rows whose `statement_exact` asserts a merged C0/C2 regularity or a
disjunctive class conclusion; any ledger class token outside the frozen four; or drift of any pinned
input during the run.
