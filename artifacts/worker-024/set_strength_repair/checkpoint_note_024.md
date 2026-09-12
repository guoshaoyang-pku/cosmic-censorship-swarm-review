# Checkpoint note — W024-SET-STRENGTH-REPAIR-01

**Worker:** worker-024 · **Taken:** 2026-09-12 ~01:12 · **Class:** `AF-WCC-VAC-GEN` (variant `SET`) ·
**Node:** F0 · **Gate:** G-FORM.

## Task taken

One class-bound task from the formulation critical path: repair the level-mixed `SET` variant
strength label that worker-094 filed as a blocker and astra-lead-formulation lifecycle-07
measurement_6 confirmed was introduced by the 00:57:26 rev29 re-base, together with the
mention-matching owner checker that lets it pass (lead recommendations (d)+(e)).

## Result

Unfrozen 3-site candidate, **21/21 verifier assertions PASS, exit 0**:

| site | live | candidate |
|---|---|---|
| `VARIANT_REGISTRY.json:57` | `6bac9adea19e` | `5c05a8cc7ea2` |
| `…variant-SET.delta.json:11` | `64b8d6394a04` | `7a1f6212ad70` |
| `check_variant_registry.py` SET clause | `c471da4b7be9` | `8b15f43e843d` |
| combined `repair.patch` | — | `9fb0c6674849` |

Level model (independent): `P ⟹ S`, `¬S ⟹ ¬P`, so the SET variant is **strictly stronger as a
class statement** while `S` is **strictly weaker as a predicate**; the live label applied the
predicate direction to the class subject. Candidate carries one byte-identical level-qualified
label in both artifacts and agrees with F0:94 (class-level) and F1:235 (predicate-level).

Checker contrast: original VALID on live (false pass), note-stripped original INVALID on live
(reproduces worker-094 F0V-SETDIR-CHECKER), candidate INVALID on live, VALID on candidate,
original still VALID on candidate. `check_variant_deltas.py` VALID and
`check_taxonomy_consistency.py` CONSISTENT on the candidate tree. Patch dry-runs clean and
reproduces all three candidates byte-for-byte.

## No canonical write

All 6 pre-registered pins identical at entry and exit; `research_map/formulation_taxonomy.yaml`
stays `0abb9ed8a961` (G-F0 protected). All three repair targets are FROZEN rev29 members, so
adoption by the gate owner bumps FROZEN and re-pins the two evidence JSONs.

## Falsifier / next

Re-run `verify_set_strength_repair_024.py` at unchanged pins; falsified by any of the six
pre-registered conditions in `report.json.falsifier`. Open adjudication left to the owner:
worker-094 reads F0:199 as a predicate inversion, lifecycle-07 reads it as class-level; this
candidate does not touch F0 and is correct under either reading. Residual: D3-VOCAB-CONFLICT
belongs to the separate F2b repair; supplement :176 and the `f1_falsifier_tests.jsonl` restamp
are out of scope.

## Authority

Worker completion claim only: no gate verdict, no `validation_status=passed`, no node
`status=done`, no canonical path written.
