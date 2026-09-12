# W078-F0-SET-STRENGTH-ADJ-01 — SET-variant strength direction in the frozen F0 taxonomy

**Worker:** worker-078 (bounded execution worker; evidence only)
**Class:** `AF-WCC-VAC-GEN` · **Node:** F0 (interface F1) · **Gate:** G-F0
**Verdict:** `revise` — the canonical F0 taxonomy asserts the inverted strength direction in two
operative clauses and is internally self-contradictory in the first of them.
**Controls:** 4/4 fixtures + entailment controls · **Determinism:** byte-identical rerun
**Binding:** all pins stable across the run (`any_drift: false`)

## Why this task

`W099-FORM-DIRECTION-CENSUS-01` flagged `research_map/formulation_taxonomy.yaml:200` as a live
`INVERTED` direction claim and left it unadjudicated. That file is the **G-F0-passed, frozen**
taxonomy (`0abb9ed8a961`), and two independent threads had already corrected the same direction
elsewhere: F1 rev13's registered `SET` delta and `VARIANT_REGISTRY.json` say **SET is strictly
weaker**, and `W076-GFORM-STRICTNESS-RECONCILE-06` established the separating witness. The
canonical F0 clauses `:94–95` and `:200` were never updated and were not covered by any prior
adjudication (worker-076 targeted F1 rev12's variant block; this worker's own
`W078-REC12-PREACCEPT-01` checked the *delta* file, not canonical F0). This run adjudicates them
and quantifies the G-F0 consequence.

## What was decided, and how

The two readings, exactly as the artifacts define them:

- `SINGLEQ(γ)` — single-q **tail** predicate: `∃q∈I⁺, ∃t₀: ∀t≥t₀, γ(t) ≤ q` (F1 rev13's class predicate).
- `SET(γ)` — union reading: `∀t ∃q∈I⁺: γ(t) ≤ q`, i.e. γ lies in `⋃_{q∈I⁺} J⁻(q)` (variant `SET`).

From the artifacts' own declared axioms (`≤` reflexive/transitive; `J⁻(q) = {x : x ≤ q}`;
γ a causal chain):

| lemma | statement | method | result |
|---|---|---|---|
| L1 | `SINGLEQ ⇒ SET` unconditionally | chain + transitivity: for `t<t₀`, `γ(t) ≤ γ(t₀) ≤ q` | **0 violations** (38 664 models, 388 preorders on ≤4 points) |
| L2 | `SET ⇒ SINGLEQ` for finite chains | exhaustive over all preorders ≤4 points, all non-empty I⁺, all chains | **0 violations** |
| L3 | converse fails in general | ω-chain `x_i ≤ q_j ⇔ i ≤ j`: `SET` holds, `J⁻(q_j)∩γ = {x₀..x_j}` finite so no tail is covered | **separated** (240/240 escape cases; stable at N=8/16/32) |

**Therefore `SINGLEQ` is strictly stronger and the `SET`/union reading is strictly weaker** —
exactly the direction F1 rev13, the registry and the registered delta all state.

### Clause census (mention-aware, contiguous hits merged)

| file | lines | strength @ | class |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` | 92–96 | 94 | **ASSERTIVE_INVERTED** |
| `research_map/formulation_taxonomy.yaml` | 198–202 | 200 | **ASSERTIVE_INVERTED** |
| `artifacts/formulation/formulation_taxonomy.yaml` | 174–178 | 176 | MENTION_HISTORICAL (D1 ledger, `status: resolved`) |

`:94–95` is worse than a wrong label: the clause's own gloss — *"gamma outside the union implies
no single q sees a tail of gamma, but not conversely"* — is the contrapositive of L1, i.e. it
**proves SET is weaker** while the label says "Strictly stronger". The clause is internally
self-contradictory, so it cannot be defended as a naming convention. `:200` asserts the same
inverted direction in the class `conclusion.text` itself.

## G-F0 consequence (decision input, not a verdict)

The G-F0 pass binds `research_map/formulation_taxonomy.yaml#0abb9ed8a961`, and the controller's
recorded rule is that **any write to that file voids G-F0**. Two options are costed in
`report.json → gate_impact`:

- **OPT-A erratum** — record a finding, keep the freeze; hash unchanged; the frozen taxonomy keeps
  asserting a false strength relation for a registered variant.
- **OPT-B repair** — rewrite `:94–95` and `:200` to "strictly weaker" (minimal text provided);
  canonical F0 moves off `0abb9ed8a961`; FROZEN rev30 and a re-accepted G-F0 are required.

This worker records the defect and the true direction; the disposition belongs to the controller.

## Files

| file | role |
|---|---|
| `adjudicate_f0_set_strength.py` | deterministic instrument (pins, entailment engine, census, controls) |
| `report.json` | primary evidence; `report_rerun.json` byte-identical |
| `controls.json` | fixture controls + entailment control summary |
| `snapshot/` | byte-exact pinned copies + `SHA256SUMS.txt` |

Reproduce:

```bash
python3 artifacts/worker-078/f0_set_strength_adjudication/adjudicate_f0_set_strength.py \
  --generated-at 2026-09-12T01:06:00+08:00 \
  --out artifacts/worker-078/f0_set_strength_adjudication/report.json
```

## Falsifier

Falsified if, at the pinned hashes: (a) a model satisfies `SET` and fails `SINGLEQ` (L1 violation);
(b) a finite chain satisfies `SET` and fails `SINGLEQ` (L2 violation); (c) the ω-chain escape check
fails; (d) either canonical clause is shown non-assertive; (e) F1 rev13 / registry / delta is shown
to state the opposite direction; or (f) any pinned input drifts (voids the binding).

## Limits (non-claims)

Not a gate verdict, node status or `validation_status=passed`; no canonical file was modified or
repaired; G-F0 is not re-opened here; the physical admissibility of the ω-chain family in an
admissible conformal completion is **not** decided (it is worker-076's open obligation); SCC/F2b
classes are untouched; worker-level advisory evidence only.
