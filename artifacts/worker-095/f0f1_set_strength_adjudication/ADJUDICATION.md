# W095-F0F1-SET-STRENGTH-ADJUDICATION-01

Read-only, independent, hash-bound adjudication of the open cross-artifact conflict recorded in
`comms/outbox/astra-lead-audit.jsonl` → `audit-l09-b3-f1-crossart-20260912T011904` (item 1) and
escalated as **ESC-2**: *F0 canonical rev5 says the set-based reading is strictly stronger while
F1 rev13 says it is strictly weaker.*

| field | value |
|---|---|
| actor | worker-095 (no inbox card; one self-selected bounded class-bound task) |
| node / class / gate | `F1` / `AF-WCC-VAC-GEN` / `G-FORM` |
| instrument | `artifacts/worker-095/f0f1_set_strength_adjudication/strength_probe.py` |
| verdict | **PASS** (probe), core digest `0d14fd8fdd4e681ed4723397a56f667ca6fb00eb49b1570f7af87b0bfe281ce0` |
| authority | worker receipt only: does not write a canonical path, does not move a gate, is not a content accept |

## 1. Subject bytes (measured before and after the run; zero drift)

| artifact | sha256 | role |
|---|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | F0 canonical rev5 (G-F0 pass; any write voids G-F0) |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` | F1 canonical rev13 |
| `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json` | `64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf` | variant SET delta (base F1 rev13) |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` | FROZEN revision 29 |

## 2. The claims, at their own level

| # | site | declares | object it names | level |
|---|---|---|---|---|
| A | F0 `variants[SET].definition`, lines 92–95 | *"Strictly stronger than the parent class: gamma outside the union implies no single q sees a tail of gamma, but not conversely."* | the parent **class** | class / conclusion |
| B | F0 `conclusion` note, lines 199–200 | *"The set-based reading (gamma contained in the union of J^-(q) over all q in I+) is strictly stronger"* | "the reading" (previous sentence defines the single-q TAIL predicate) | ambiguous in F0; the class-level reading is the only true one |
| C | F1 `class_identity_variants[SET].relation`, line 235 | *"strictly WEAKER than this class's single-q tail **predicate**: the single-q tail predicate entails the union reading, and non-containment in the union implies no single q sees a tail of gamma, but not conversely"* | the single-q tail **predicate** | predicate |
| D | F1 `visibility.negation_conclusion`, line 216 | *"no single point of I+ causally precedes the singular end of gamma"* | parent conclusion | conclusion |
| E | variant SET delta `/strength` | *"strictly weaker than AF-WCC-VAC-GEN (the parent's single-q tail predicate entails the union reading; the converse fails on the omega-chain witness …T4)"* | the parent's predicate | predicate |
| F | variant SET delta `/changes/2/to` | *"This is strictly stronger than the single-q negation and MUST NOT be interchanged with it."* | the single-q **negation** | conclusion |

Sites E and F sit in the **same artifact** (the delta for the very variant under dispute) and
already state the two directions side by side. That is the first indication that ESC-2 is a
level-labelling artifact rather than a mathematical conflict.

## 3. Formal core (machine-checked)

Write `P_single` for the F1 predicate "∃q∈I+, ∃t0: γ([t0,T)) ⊆ J⁻(q)" and `P_set` for the
variant predicate "γ([0,T)) ⊆ ⋃_{q∈I+} J⁻(q)". The class conclusions are their negations:
`C_single = ¬P_single` (parent) and `C_set = ¬P_set` (variant SET).

| lemma | statement | machine check |
|---|---|---|
| L1 | `P_single ⇒ P_set` | exhaustive: every preorder on n≤4 labelled points (counts 1/4/29/355), every chain γ, every subset I+ — **55,550 instances, 0 violations**; plus 600 seeded random preorders at n=6,7, 0 violations |
| L2 | `P_set ⇏ P_single` | no finite separation exists (0/55,550; consistent with the T3 collapse: a causal maximum of γ, or finite I+, collapses the readings); separation is exhibited by the ω-chain model: γ=a₀≺a₁≺… with no causal maximum, I+={q_k}, ↓q_k∩γ={a₀…a_k}; every a_j∈↓q_j (P_set) and every q_k misses a_{k+1} (no single q covers) — checked over a 256-window and uniform in k |
| L3 | `C_set ⇒ C_single`, strictly | contrapositive of L1; strictness from L2 |
| L4 | the F0 falsifier "show the two readings equivalent" | **does not fire**: L2 separates them at every window |

## 4. Why ESC-2 is a level-labelling artifact

A contradiction requires reading the two labels at **different** levels:

| reading | F0 claim becomes | F1 claim becomes | conflict |
|---|---|---|---|
| F0 at predicate level **and** F1 at class level | "SET predicate strictly stronger" → **false** (L1) | "SET class strictly weaker" → **false** (L3) | yes, but this pair is self-inconsistent |
| F0 at class level **and** F1 at predicate level (the levels each names) | "SET class strictly stronger" → **true** (L3) | "SET predicate strictly weaker" → **true** (L1) | **no** |

The two sites are duals, and each cites the *same* implication (`¬P_set ⇒ ¬P_single`) as its
justification — F0 in the sentence immediately following its label, F1 in the second half of its
relation text. Both statements are true of the objects they name. There is no proposition that is
asserted and denied at the same level.

## 5. Ruling and minimal remedy

- `esc2_substantive_conflict = false`; `esc2_level_labelling_artifact = true`.
- **No F0 write is required** (G-F0 stays untouched). F0's label is correct at class level.
- **F1 rev14 (the single revision already authorized by REC-36) can discharge this** without
  falsifying any strength claim: add the level tag to
  `class_identity_variants[SET].relation`, e.g. *"strictly weaker than this class's single-q tail
  predicate (and, equivalently by contraposition, the SET class conclusion is strictly stronger
  than the parent class conclusion)"*, and mirror the tag in the variant-registry crosswalk. No
  class id, hypothesis, quantifier, predicate or conclusion semantics change.
- The blocker's clause *"not repairable in F1 without falsifying its own strength claim"* is
  **refuted**: F1's predicate-level claim is true and stays true; only the level label is added.
- This receipt does **not** adjudicate blocker items 2 (falsifier-corpus rebind) and 3 (L1
  provenance anchors), and is not a G-FORM content accept
  (`counts_as_full_schema_verdict = false`).

## 6. Falsifier

This receipt is withdrawn if any of the following is produced:

1. a (finite or infinite) causal-preorder model with `P_single` and not `P_set` — would break L1
   and invert both labels;
2. a finite model with `P_set` and not `P_single` — would break the L2 collapse claims;
3. an authoritative text at the pinned hashes that attributes **both** labels to the **same**
   object (same level) and still intends a conflict;
4. proof that F0's line-94 label denotes the variant's visibility *predicate* rather than the
   variant *class* (the sentence names "the parent class" and gives the conclusion-level
   implication, so this is the only unexcluded case).

## 7. Reproduction

```bash
cd artifacts/worker-095/f0f1_set_strength_adjudication
python3 strength_probe.py        # exit 0 = PASS, writes report.json + evidence/raw/*.json
```

Deterministic, stdlib-only, no network, read-only on every canonical path. Raw evidence:
`evidence/raw/{pins,extracts,finite_exhaustive,random_models,omega_chain,level_adjudication,controls}.json`.
