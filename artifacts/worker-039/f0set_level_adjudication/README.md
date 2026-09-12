# W039-F0SET-LEVEL-ADJ-01 — is the F0 canonical "SET is strictly stronger" sentence inverted, or level-underspecified?

**Worker:** worker-039 · **Node:** F1 · **Class:** `AF-WCC-VAC-GEN` · **Gate:** G-FORM
**Type:** worker measurement (no gate verdict, no node status, no `validation_status`, no canonical edit)
**Instance:** `worker-039-20260912T010114-968807` · **Measured:** 2026-09-12T01:07+08:00

## Why this task

Two independent workers read the same live contradiction on the SET/union reading of
`AF-WCC-VAC-GEN` and classified it differently:

| record | F0 canonical `research_map/formulation_taxonomy.yaml#0abb9ed8a961` L199–200 | F1 rev13 `schemas/af_wcc_vacuum.yaml#d9cebb9404b2` L235 |
|---|---|---|
| worker-099 census `P2-SET-STRONGER` | `INVERTED` | — |
| worker-063 `W063-SET-DIRECTION-ADJ-01` | `INVERTED` (level assigned: *predicate*) | correct (`strictly WEAKER`, predicate) |
| worker-039 check K (rev13 bindchain) | live divergence vs F1 | — |

worker-063 named the decisive falsifier for its own verdict:

> “show F0 L199-200 refers to the class-negation statement rather than the set-based reading
> (would clear HF-W063-SETDIR-1 as an erratum)”

This artifact runs that falsifier. The question is not *what* the strength relation is — that is
settled — but *at which level* the F0 sentence speaks, and therefore whether its truth value is
false (`INVERTED`) or level-underspecified.

## Model and result

Structure: a **preorder** `(X, <=)`; `J^-(q) = {x : x <= q}` (past-closed by construction);
`gamma` a **chain** in causal order; `U = union_{q in I+} J^-(q)`.

| id | statement | status |
|---|---|---|
| **T1** | whole-curve and tail containment in the *same* `J^-(q)` are **EQUIVALENT** (past-closedness) | proved |
| **T2** | `S => V`: a tail in one `J^-(q)` forces the whole chain into `U` (complement of `U` is future-closed along chains) | proved |
| **T3** | **no finite chain separates `V` from `S`**: a finite chain has a maximum, which dominates the rest | proved + machine-checked |
| **T4** | finite `I+` collapses `V` and `S` even for infinite `gamma` (finite cover by down-sets in `t`) | proved (matches W076 T3) |
| **T5** | the **omega-chain** (`x_1<=x_2<=...`, `x_i <= q_j iff i<=j`) satisfies `V` and no `S` | proved + window certificates N=8/24/64 |
| **T6** | `S` strictly stronger than `V` as predicates ⇔ `not-V` strictly stronger than `not-S` as class conclusions | proved |

Machine checks (stdlib-only, deterministic, fail-closed on canonical pin drift):
**60,561 predicate cases over all 384 labelled preorders on n=3,4 (355 on n=4), 4,135 chains,
all `I+` subsets — 0 violations** of `S→V`, `V→S`, `S→V_tail`, `V_tail→S`. This is the finite
collapse: on any finite chain all three readings coincide, exactly because the chain has a
maximum. The separation therefore **requires the infinite omega-chain**; it cannot be shown on a
finite causal model.

## The answer to worker-063's falsifier: PARTIALLY CONFIRMED

The F0 canonical carrier has **two live referents**, and they are at different levels:

1. `L90–94` (variants block): “replaces the single-q tail predicate by the set-based condition
   … **Strictly stronger than the parent class** …”. The comparison object is named: *the parent
   class*. This carrier is unambiguously **class-level, and true** (T6: the variant class
   conclusion `not-V` is strictly stronger than the parent `not-S`).
2. `L199–200` (conclusion block): “The set-based reading (gamma contained in the union …) **is
   strictly stronger**; it is registered as variant `SET` of this class in the `variants:` block
   below …”. No level is named; the sentence's own continuation points at the variants block,
   whose carrier names the class.

So the class-level referent is document-internal and live, which makes the class-level reading
**true**; it does **not** make the predicate-level reading true (there, `V` is strictly weaker,
per F1/registry/delta). The defect is therefore **level-underspecification**, not inversion:

> `INVERTED` → **`SCOPE_AMBIGUOUS` (level-underspecified): true at class level, false at
> predicate level.** F0 bytes unchanged. A blind flip to “strictly weaker” would introduce a
> **new class-level falsehood** and contradict the SET delta negation clause (`L27`) and the
> registry's own consequence clause.

## Carriers (9, all hash-pinned; report.json has quotes and line numbers)

| file | line | level | token | verdict |
|---|---|---|---|---|
| F0 canonical | 94 | class_conclusion | stronger | CORRECT_AT_CLASS_LEVEL |
| F0 canonical | 199 | **level_underspecified** | stronger | **SCOPE_AMBIGUOUS** |
| F0 supplement D1 row | 176 | class_conclusion_historical | stronger | CORRECT (historical ledger row) |
| F1 rev13 D5 | 73 | predicate_same_q_pair | equivalent | CORRECT (different pair; HF-06 hazard) |
| F1 rev13 variant SET | 235 | predicate | weaker | CORRECT_AT_PREDICATE_LEVEL |
| VARIANT_REGISTRY | 57 | predicate | weaker | CORRECT_AT_PREDICATE_LEVEL |
| SET delta negation clause | 27 | class_conclusion | stronger | CORRECT_AT_CLASS_LEVEL |
| SET delta visibility clause | 22 | predicate | weaker | CORRECT_AT_PREDICATE_LEVEL |
| F1 rev13 negation_conclusion | 216 | hiddenness_condition | stronger | CORRECT |

## Peer-artifact finding (support-invalid, direction unaffected)

`artifacts/worker-063/set_direction_adjudication/report.json#logic_core.L2_converse_fails`
offers the finite witness `tail=[0,1]`, `J(q0)={0}`, `J(q1)={1}`. **It is not realizable in any
preorder**: `0<=1` and `1<=q1` force `0<=q1`, hence `0 in J(q1)`, so `J(q1)` contains the whole
tail and `S` holds. Exhaustive search: the witness is realizable in **non-transitive** reflexive
relations (found) and in **0** transitive ones. Its L1/L2 census runs over arbitrary set systems
(`_models`), not causal structures. The correct separator is the infinite omega-chain (W076 T4,
independently reconstructed here). worker-063's *direction* conclusion (F1 correct at predicate
level) is unaffected; only the finite-witness support and the F0 level assignment are.

## Recommendation (decision options in report.json)

**Option A (recommended):** R3 records the F0 L199–200 carrier as CLASS-LEVEL CORRECT /
PREDICATE-LEVEL INVERTED (level-underspecified prose), carries `HF-W063-SETDIR-1` as an F0
erratum pointer, and requests a controller vocabulary ruling: *a variant/reading strength token
denotes class-conclusion strength unless it explicitly names a predicate*. No F0 edit; G-F0 stays
passed. Materiality to G-FORM is vocabulary hygiene only: variant `SET` is
`registered_variant_not_written`, and no F1/F2a/F2b conclusion uses the union reading.

Options B (F0 erratum → voids G-F0) and C (flip to "weaker" → rejected) are recorded in the
report.

## Falsifier

(i) a derivation of `V => S` in the declared preorder structure; (ii) a **finite**
preorder+chain witness with `V` and `not S` (would falsify T3); (iii) evidence that F0 L199–200
has no live class-level referent (then the classification collapses to `INVERTED`); (iv) drift of
any pinned input (voids the measurement).

## Reproduction

```bash
python3 artifacts/worker-039/f0set_level_adjudication/run_f0set_level_039.py
# exit 0; exit 3 on canonical pin drift; exit 2 on control failure; writes report.json
```

Canonical pins at entry and exit: F0 `0abb9ed8a961`, supplement `d7419b4e8963`, F1
`d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, registry `6bac9adea19e`, SET delta
`64b8d6394a04`, FROZEN rev29 `815e08079aef`, consistency evidence `9e335e9ba1bf` — 0 drift.
Peer artifact `worker-076/gform_strictness_reconcile` was revised inside the window
(`ae1740ac` → `8db31353`); its T3/T4 corroborate this result. No canonical artifact was edited.

## Non-claims

No gate verdict, no node status, no `validation_status`; no claim that variant SET is
GR-realizable (the omega-chain is an order-theoretic witness at the declared causal-structure
level); no resolution of D1 beyond the level analysis.
