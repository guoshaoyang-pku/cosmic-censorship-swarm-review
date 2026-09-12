# W037-F1-VISIBILITY-03 — adjudication: `W037V2-F1` (critical) vs `LEMMA-W026-1`

**Actor:** worker-037 · **Class:** AF-WCC-VAC-GEN · **Node:** F1 · **Gate:** G-FORM
**Pins (T0 == T1, stable):** `schemas/af_wcc_vacuum.yaml` `9a8bd4c96800`,
`research_map/formulation_taxonomy.yaml` `276009f4f63d`,
`artifacts/formulation/FROZEN.json` `2554e276a0db`,
prior report `c3f84a43aae7`, worker-026 report `0f1558939481`.

## Question

At the measured F1 bytes, is the prior worker-037 finding **W037V2-F1** right that
`quantifiers.formal` / `D5` (whole-curve containment `gamma subset J^-(q) intersect M`) is
**strictly weaker** than `visibility.definition` / `negation_conclusion` (tail containment
`gamma([t0,T)) subset J^-(q) intersect M`), so that formal and negation are not exact
negations? Or is **LEMMA-W026-1** right that they are equivalent?

## Result

**LEMMA-W026-1 is CONFIRMED. W037V2-F1's mathematical claim is REFUTED.**
The textual premise is reproduced (the two clauses really are worded differently), but the
inference to a different class extension is false.

The load-bearing hypothesis is the one the schema's own notation presupposes:

> **(H)** causal precedence in the conformal completion is transitive; hence
> `J^-(q) = {p : p precedes q}` is **past-closed** (if `p'` precedes `p` and `p` is in
> `J^-(q)`, then `p'` is in `J^-(q)`).

Under (H), for a future-directed causal `gamma` (exactly what D4 admits):

* whole-curve containment makes the tail clause true with `t0 = 0` (trivial);
* if some tail `gamma([t0,T))` lies in `J^-(q)`, then for any `t < t0` the segment
  `gamma|[t,t0]` is causal, so `gamma(t)` precedes `gamma(t0)` precedes `q`; by (H)
  `gamma(t)` is in `J^-(q)`.

Hence `exists q (whole in J^-(q)) <=> exists q exists t0 (tail in J^-(q))`, and negating both
sides gives that `quantifiers.formal` and `visibility.negation_conclusion` are **exact
negations** at the measured bytes. The class extension is unchanged by the whole/tail wording.

## Why the prior finding looked right

`W037V2-F1` used a strictness witness with universe `{a,b}`, `J^-(q1) = {b}`,
`gamma = [a,b]`: whole-containment false, tail-containment true. That "model" violates (H):
`a` precedes `b` and `b` is in `J^-(q1)`, but `a` is not. It is not a model of the declared
causal structure, so it does not exhibit a difference for D4 geodesics. The only other route
to a strictness witness is a curve with a **non-causal** step, which D4 excludes.

## Controls run (machine)

| test | result |
|---|---|
| T1 text binding at the measured bytes (4 exact clauses) | pass |
| T2 exhaustive over **all 389 reflexive+transitive relations** on ≤4 points, 4082 causal chains, 16138 predicate evaluations | `tail_without_whole = 0`, `whole_without_tail = 0` → EQUIVALENT |
| T3 rebuild of the recorded witness arithmetically | reproduced (`P_whole=false, P_tail=true`) |
| T3 same witness under the standard past-closed `J^-` | `P_whole=true` → no longer a witness |
| T4 past-closedness violation of the recorded witness | explicit: `a -> b in J^-(q)`, `a not in J^-(q)` |
| T5 non-causal control (drop causality, keep transitivity) | strictness witness reappears → causality is the load-bearing hypothesis |
| T6 proof-step audit | only non-machine-checkable premise is (H), a standard property of causal precedence |

## Scope and consequences

* **Prior blocker `w037-20260912T002818-blocker-f1-visibility` is WITHDRAWN as a critical
  blocker.** Its own stated falsifier fired ("a reviewer rebuttal naming the definitional
  bridge that makes line 55 the tail predicate falsifies W037V2-F1 instead"); the bridge is
  `J^-` past-closedness.
* **Surviving, non-blocking documentation defect** at `schemas/af_wcc_vacuum.yaml:220`: the
  sentence *"requiring the whole geodesic to lie in J^-(q) would misclassify a geodesic that
  starts in the exterior and ends inside the black-hole region"* is a non-sequitur (for that
  example both readings classify the geodesic as not visible), and the schema never states the
  (H) equivalence lemma — an omission that demonstrably misled reviewer-19 and a prior
  worker-037 slot, and that touches the schema's own `schema_falsifiers` entry about
  reader disagreement. Recommended fix: replace that sentence with the equivalence statement.
* **Not touched / out of scope:** D0 disjunction and the single-frozen-data-class criterion,
  the dangling `AF_{I+}(M_D)` at line 251, duplicate `revised_at` keys, and the
  `class_contract_pointer` / F0-mirror divergence. This adjudication does not by itself make
  F1 acceptable.
* **Authority:** worker evidence only — no gate verdict, no node status, no canonical edit, no
  claim to be one of the two required accepts. The controller/lead decides what a worker
  verdict is worth.

## Falsifier (of this adjudication)

At the same five pins: exhibit a model of the schema's declared causal structure in which
D4's hypotheses hold (gamma future-directed causal; `J^-(q)` the standard causal past, hence
past-closed) and the tail clause holds while the whole-curve clause fails; **or** show the
schema's own bytes define `J^-(q)` as non-past-closed or admit non-causal gamma in D4; **or**
show the measured hashes differ from the pins. Any of these reinstates W037V2-F1 at critical
severity.

## Reproduce

```bash
python3 artifacts/worker-037/f1_visibility_equivalence_adjudication/adjudicate_visibility_equivalence.py
# exit 0 and pins_stable=True; report payload sha256 8090ba9bc5eea1dc938e1f7883e8affd8602c95945814a97b9c8e47f568d0e92
```
