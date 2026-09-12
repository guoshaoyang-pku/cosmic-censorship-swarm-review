# W003-SET-STRENGTH-LEVEL-AUDIT-01 — variant SET strength is level-indexed

**Worker:** worker-003 · **Node:** F1 · **Gate:** G-FORM · **Class:** `AF-WCC-VAC-GEN`
**Created:** 2026-09-12T01:01+08:00 · **Pins:** FROZEN rev29 `815e08079aef`, F1 rev13 `d9cebb9404b2`

**Authority note.** Worker measurement and adjudication only. No canonical byte was written; no
gate verdict, node status or `validation_status` is set or claimed.

## Why this task

Three events landed inside four minutes and disagree about the variant `SET` strength direction:

| when | carrier | says |
|---|---|---|
| 00:53:20 | F1 rev13 `schemas/af_wcc_vacuum.yaml:235` | SET is `strictly WEAKER` than the single-q tail predicate |
| 00:57:02 | `VARIANT_REGISTRY.json` + `AF-WCC-VAC-GEN.variant-SET.delta.json` | SET is `strictly weaker than AF-WCC-VAC-GEN` |
| 00:57:43 | lead blocker `lead-form-…-92` (L-FORM-03) | the F0 supplement D1 implication is "inverted" |
| 00:57:25 | worker-018 `HF-W018-F1-1` | F1 `WEAKER` contradicts F0/registry `stronger` |

worker-061's warning (`F-W061-VAR-01`) is the key: a *blanket* inversion of every
`strictly STRONGER` token repairs the predicate-level label and breaks the class-level one.
This probe separates the two levels, re-derives both directions from the order structure, and
classifies every live carrier at its declared level.

## The two levels (re-derived, not quoted)

Let `J^-(q)` be past-closed, `T(γ) := ∃q∈I+, ∃t0: tail γ([t0,T)) ⊆ J^-(q)`, and
`S(γ) := γ([0,T)) ⊆ ⋃_{q∈I+} J^-(q)`.

* **Predicate level.** `T ⟹ S`, and `S ⇏ T` (ω-chain: `q_n = n`, `γ(t_n) = n` — the curve lies
  in the union but no single `J^-(q_N)` contains a tail). So **S is the strictly weaker
  predicate**.
* **Class level.** The class conclusion is an inexistence statement: `C_T := ¬∃γ T`,
  `C_S := ¬∃γ S`. `T ⟹ S` is equivalent to `C_S ⟹ C_T`, so **SET is the strictly stronger
  class statement**.

Machine evidence (`audit_set_strength_levels.py`, all 355 preorders on 4 labelled points × all
15 nonempty `I+` subsets × all causal 4-chains): `T⟹S` violations **0**; finite-chain `S⟹T`
violations **0** (separation needs the ω-chain, reproduced: `S` true / `T` false); class-level
`C_S⟹C_T` violations **0** and non-vacuous (5325 frames live).

## Carrier classification

| id | carrier | declared level | direction found | state |
|---|---|---|---|---|
| C1 | `schemas/af_wcc_vacuum.yaml:235` (F1 rev13) | predicate | weaker | **CONSISTENT** |
| C2 | `artifacts/formulation/schemas/af_wcc_vacuum.yaml:235` (mirror) | predicate | weaker | **CONSISTENT** |
| C3 | `VARIANT_REGISTRY.json` SET `strength` | class ("than AF-WCC-VAC-GEN") | weaker | **LEVEL-MIXED / class head inverted** |
| C4 | `…variant-SET.delta.json` `strength` | class | weaker | **LEVEL-MIXED / class head inverted** |
| C5 | same delta, `changes[visibility.definition].to` | predicate | weaker | **CONSISTENT** |
| C6 | same delta, `changes[visibility.negation_conclusion].to` | class | stronger | **CONSISTENT** |
| C7 | `research_map/formulation_taxonomy.yaml:200` (F0-frozen) | predicate ("reading") | stronger | **INVERTED at declared level** |
| C8 | `artifacts/formulation/formulation_taxonomy.yaml:176` (D1) | class | stronger | **CONSISTENT** |

C3/C4 and C6 sit in the **same** delta JSON file: `strength` says "weaker than
AF-WCC-VAC-GEN" while `negation_conclusion` says the SET negation "is strictly stronger than
the single-q negation". Both describe the class-conclusion level, where `C_S ⟹ C_T`; the
negation sentence is the correct one and the `strength` head is inverted at class level. The
registry's `variant_schema` declares no `strength` field, so no declared level rescues it.

## Findings

- **W003-SETLEVEL-H1 (hard, live).** The 00:57:02 re-base over-corrected the class-level
  strength head in `VARIANT_REGISTRY.json` and the SET delta; the two fields of one delta file
  now contradict each other. Minimal repair: make `strength` level-explicit, e.g.
  *"predicate: strictly weaker (T ⟹ S); class statement: strictly stronger (¬S ⟹ ¬T)"*.
- **W003-SETLEVEL-H2 (hard, frozen residual).** `research_map/formulation_taxonomy.yaml:200`
  attaches `strictly stronger` to *the set-based reading* (a predicate), where `S` is strictly
  weaker. G-F0 is passed on these bytes and any write voids it, so this is a Human-PI /
  next-F0-revision item, not a lead edit.
- **W003-SETLEVEL-H3 (adjudication, falsifies L-FORM-03(b)).** `formulation_taxonomy.yaml:176`
  D1 `"F0 was stronger; (b) implies (c) but not conversely"` is the class level and is
  **correct** — it *is* the contrapositive of `T ⟹ S`. Reading it at predicate level is a
  level error; the blocker should be withdrawn, not repaired.
- **W003-SETLEVEL-M1 (minor).** FROZEN rev29 has ≥3 byte-images without a revision bump
  (`e1a8aaa394eb` ≈00:56, `3d9e3d77fd87` ≈00:57 with `frozen_at` 00:55:02, `815e08079aef`
  00:57:26). Corroborates worker-018 `A-W018-F1-3` and worker-095 `R3 FAIL`; cited so the
  review-time pin is unambiguous.
- **W003-SETLEVEL-M2 (minor, review coverage).** `HF-W018-F1-1` was measured against registry
  `5eb42f9a` (pre-rebase); the registry moved at 00:57:02. The live residue is therefore (a)
  the F0-frozen note H2 and (b) the intra-delta contradiction H1 — not F1's own text, which is
  correct at predicate level. The rebase note "direction corrected from `strictly STRONGER`" is
  over-broad: the pre-rebase class head was correct.

## Verdict

`SET_LEVEL_MIXED` — rev13's predicate-level correction is right; the class-level `strength`
head in the registry/delta is over-corrected (H1); the F0 supplement D1 line flagged as
inverted is in fact correct (H3); the F0 canonical note remains a frozen predicate-level
inversion (H2).

## Method, checks, controls

`audit_set_strength_levels.py` (stdlib only, deterministic, read-only): measures the eight
pinned inputs, fails closed (exit 3) on any drift; re-derives both directions from the order
structure; classifies each carrier by declared level; reports **22/22** declared expectations
and **7/7** planted in-memory controls (rev12 predicate inversion detected; predicate/class
accept and reject probes; ω witness; pin-drift guard). Exit 0.

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-003/set_strength_level_audit/audit_set_strength_levels.py   # exit 0
```

## Falsifiers

- Any pinned input hash moving → every carrier verdict is advisory (drift guard exits 3).
- Showing that registry/delta `strength` is *declared* predicate-level, or that the
  class-level negation sentence does not contradict it → voids H1.
- Showing the F0 sentence speaks about the class conclusion throughout → H2 becomes a
  misquote, not an inversion.
- Exhibiting a model with `T ⟹ S` where `C_S` does not imply `C_T` → voids H3 and the
  level derivation.
- Showing the three FROZEN hashes denote one byte-image or different revisions → voids M1.

## Non-claims

Not a mathematics result about cosmic censorship; the order-structure facts are elementary and
are used only to type the strength labels. Not a gate verdict, not a review of F1's physics
content, and not an edit proposal for any F0-frozen byte.
