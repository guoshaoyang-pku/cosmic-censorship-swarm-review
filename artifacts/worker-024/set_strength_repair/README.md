# W024-SET-STRENGTH-REPAIR-01 — unfrozen candidate repair, SET variant strength label

Worker-024, 2026-09-12. One class-bound task: the `AF-WCC-VAC-GEN` variant `SET` strength
declaration is level-inconsistent at the FROZEN rev29 pins, and the owner checker that guards
it passes only on a bracket note. This directory holds an **unfrozen candidate** that fixes both,
verified against independent anchors. **No canonical byte was written.**

## The defect (measured, not inferred)

`VARIANT_REGISTRY.json` variants[SET].strength compares the **variant to its parent class** but
carries the **predicate-level** label:

> "strictly weaker than AF-WCC-VAC-GEN (the parent's single-q tail predicate entails the union reading; …)"

The justification in the same sentence is the class-level argument for **stronger**
(`not-S` entails `not-P`, not conversely). Two levels, one label.

At the predicate level the live label is right: with `P` = single-q tail predicate and `S` =
set-based predicate, `P ⟹ S` and the omega-chain witness gives `S` while denying `P`, so
`S` is the weaker predicate. At the class/statement level it is inverted: the variant's
conclusion is `∀γ ¬S`, the parent's is `∀γ ¬P`, and `P ⟹ S` gives `¬S ⟹ ¬P`, so
**the SET variant is strictly stronger as a class statement**.

The live label also contradicts two frozen, independently reviewed siblings:

| site | level | text | agrees with candidate? |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml:94` (F0 canonical) | class | "Strictly stronger than the parent class: gamma outside the union implies no single q sees a tail of gamma, but not conversely." | yes |
| `schemas/af_wcc_vacuum.yaml:235` (F1 rev13) | predicate | "strictly WEAKER than this class's single-q tail predicate" | yes |
| `VARIANT_REGISTRY.json:57` (live) | class subject, predicate label | "strictly weaker than AF-WCC-VAC-GEN" | **no** |
| `…variant-SET.delta.json:11` (live) | same mixed form | "strictly weaker than AF-WCC-VAC-GEN" | **no** |

`check_variant_registry.py:89-91` asserts only `"STRONGER" in strength`. That substring occurs
exactly once, inside the bracket provenance note `[rev13 direction corrected from 'strictly
STRONGER']`. Strip the note and the tool is INVALID; with the note it prints VALID. This
reproduces worker-094 `F0V-SETDIR-CHECKER` first-hand (V1/V2 below).

## The candidate (unfrozen — owner applies and re-pins)

| file | live sha256 | candidate sha256 |
|---|---|---|
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` | `5c05a8cc7ea2` |
| `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json` | `64b8d6394a04` | `7a1f6212ad70` |
| `artifacts/formulation/tools/check_variant_registry.py` | `c471da4b7be9` | `8b15f43e843d` |
| combined `repair.patch` | — | `9fb0c6674849` |

The new label is **one byte-identical level-qualified string in both artifacts**:

> "strictly STRONGER than AF-WCC-VAC-GEN as a class statement (not-S entails not-P: …), while the
> SET predicate S is strictly WEAKER than the parent's single-q tail predicate P (P entails S; …)"

Both positive assertions sit outside any bracket note. The checker change strips bracket
provenance notes before asserting and requires three things: the class-level `STRONGER than
AF-WCC-VAC-GEN` claim, the `class statement` qualifier, and the predicate-level `WEAKER than the
parent's single-q tail predicate` record. Candidate checker on live bytes → INVALID/exit 1;
on candidate bytes → VALID/exit 0. Original checker still passes on candidate bytes.

Every changed site is proven minimal by line-diff: registry line 57 only, delta line 11 only,
checker SET clause only; all other bytes identical (P2/P3/P4).

## Verification — 21/21 assertions, exit 0

`python3 verify_set_strength_repair_024.py`

- **Pins**: 6/6 canonical inputs match pre-registered hashes at entry and exit; fail-closed
  exit 2 on drift. `research_map/formulation_taxonomy.yaml` stays `0abb9ed8a961` (G-F0 untouched).
- **Level model (independent instrument)**: explicit 2-point/3-geodesic witness model. `P ⟹ S`,
  `¬S ⟹ ¬P`, `S ⇏ P` (witness `g2`, the omega-chain shape), and by exhaustive enumeration over
  all `P ⊆ S` configurations, `(∀γ ¬S) ⟹ (∀γ ¬P)` — variant strictly stronger.
- **Checker contrast (sandboxed)**: V1 original/live VALID; V2 note-stripped original/live
  INVALID; V3 candidate/live INVALID; V4 candidate/candidate VALID; V5 original/candidate VALID.
- **No regression**: `check_variant_deltas.py` VALID and `check_taxonomy_consistency.py`
  CONSISTENT on the candidate tree.
- **Patch**: `patch -p1 --dry-run` clean; applied patch reproduces all three candidates
  byte-for-byte.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-024/set_strength_repair/build_candidate.py      # deterministic rebuild
python3 artifacts/worker-024/set_strength_repair/verify_set_strength_repair_024.py
```

The verifier rebuilds its own sandboxes and deletes them is not required — they are written under
this directory and are safe to remove. `verify_results.json` holds every check's status.

## Falsifier

Re-run `verify_set_strength_repair_024.py` at unchanged pins. The claim is falsified if any of:
(a) a canonical pin differs from the pre-registered hashes (exit 2); (b) a candidate differs from
live outside the three declared sites; (c) the finite level model fails to derive
variant-stronger, or the live label is shown to be governed by a declared predicate-level
convention making "weaker than AF-WCC-VAC-GEN" correct as written; (d) V1-V5 do not reproduce;
(e) `check_variant_deltas.py` or `check_taxonomy_consistency.py` regress on the candidate tree;
(f) `repair.patch` does not apply cleanly or does not reproduce the candidates.

## Residual / not done here

1. **Applying and re-pinning is the gate owner's action (CF-4).** All three targets are FROZEN
   rev29 members, so adoption moves `FROZEN.json` (`815e08079aef` → new revision) and re-pins
   `evidence/variant_registry_check.json` + `evidence/variant_delta_check.json`. This artifact is
   an unfrozen candidate; it sets no `validation_status`, gate verdict or node status.
2. **F0:199 two-reading dispute left open.** Worker-094 reads `research_map/formulation_taxonomy.yaml:199`
   ("The set-based reading … is strictly stronger") as a predicate-level inversion (F0V-SETDIR-01,
   major); astra-lead-formulation lifecycle-07 measurement_6 reads it as class-level and internally
   correct. This candidate does **not** touch F0 — any write to that file voids G-F0. The registry/
   delta labels now carry both levels explicitly, so they are correct under either reading; the
   owner may fold a predicate-level clarification of F0:199 into the same authorized revision if
   the gate owner adopts worker-094's reading.
3. **Sibling sites not repaired here**: `artifacts/formulation/formulation_taxonomy.yaml:176`
   (supplement, same dispute) and the `f1_falsifier_tests.jsonl` re-stamp (lead recommendation f)
   are outside this task's three-site scope.
4. Live pins are measured at 2026-09-12T01:1x; traffic continues. Re-measure before citing.

## Files

`build_candidate.py` (deterministic builder) · `verify_set_strength_repair_024.py` (independent
verifier) · `verify_results.json` (21/21) · `CANDIDATE_*` (3) · `.patch` (3 + combined) ·
`entry_hashes.json` · `exit_hashes.json` · `report.json` · `checkpoint_note_024.md`.
Sandbox trees are rebuilt by the verifier and were removed after the run.
