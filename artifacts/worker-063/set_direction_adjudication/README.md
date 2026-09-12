# W063-SET-DIRECTION-ADJ-01 — two-level adjudication of the AF-WCC-VAC-GEN variant-SET strength relation

**Worker:** worker-063  **Node:** F1  **Class:** `AF-WCC-VAC-GEN`  **Gate:** G-FORM
**Type:** worker measurement (no gate verdict, no node status, no `validation_status`)
**Instance:** `worker-063-20260912T005730-968807`  **Measured:** 2026-09-12T01:01+08:00

## Question

The G-F0-passed canonical taxonomy and the F1 rev13 class schema disagree about the
strength of the registered `SET` variant of `AF-WCC-VAC-GEN`:

| carrier | hash | line | says |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` (canonical, **G-F0 passed**) | `0abb9ed8a961` | 199–200 | the set-based reading "(gamma contained in the union of J^-(q) over all q in I+) **is strictly stronger**" |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2` | 235 | variant SET is "**strictly WEAKER** than this class's single-q tail predicate"; "non-containment in the union implies no single q sees a tail of gamma, but not conversely" |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` | — | SET strength "**strictly weaker** than AF-WCC-VAC-GEN" |
| `…AF-WCC-VAC-GEN.variant-SET.delta.json` | `64b8d6394a04` | — | SET strength "strictly weaker"; negation "There is NO such visible singularity … **This is strictly stronger** than the single-q negation" |
| `artifacts/formulation/formulation_taxonomy.yaml` (companion, D1 row) | `d7419b4e8963` | 176 | `f0_reading: "… outside J^-(I+) as a SET (strictly stronger)"`, `relation: "F0 was stronger; (b) implies (c) but not conversely"` |

## Result — the two levels resolve the disagreement; F0 canonical is the defective carrier

Let `S` = single-q tail predicate (∃ q, ∃ t0: tail ⊆ J⁻(q)) and `U` = set/union
reading (tail ⊆ ⋃_q J⁻(q)).

1. **Predicate level (machine-checked, exhaustive finite models n ∈ {3,4}, |I⁺| = 2):
   `S ⇒ U` with 0 counterexamples; the converse fails** — witness `tail = {0,1}`,
   `J⁻(q0) = {0}`, `J⁻(q1) = {1}`: `U` holds, `S` fails. Therefore `S` is strictly
   stronger and `U` strictly weaker. **F1 rev13, the registry and the SET delta are
   correct at this level.**
2. **Class-assertion (negation) level:** `¬U ⇒ ¬S`, and the same witness has `¬S`
   true with `¬U` false, so `¬S` does not entail `¬U`. **`¬U` (the variant SET
   conclusion) is strictly stronger than `¬S` (the parent class conclusion).** The
   SET delta negation clause and the companion D1 row are correct at this level.
3. **Defect (1 conflict, predicate level):** `research_map/formulation_taxonomy.yaml
   @0abb9ed8a961` L199–200 applies the predicate-level label "strictly stronger" to
   the set-based *reading*. L1 contradicts that label. It is the only live frozen
   carrier that is inverted. It is **G-F0-passed bytes**: per `ASTRA_HANDOFF.md`,
   any write to this path voids G-F0, so this cannot be repaired by a worker edit —
   it needs a controller erratum / coordinated re-freeze decision.
4. **Consequence for F1:** no schema change is warranted on this axis. A blind
   reviewer who treats `0abb9ed8a961` as the normative binding target will read a
   contradiction (this independently reproduces worker-018 `HF-W018-F1-1`, 00:57:25);
   the repair belongs to F0/controller, and an F1 accept should carry this finding
   as an erratum pointer rather than as an F1 defect.

## Falsifier

Show a derivation that `U ⇒ S` under the class's standing assumptions (which would make
L1 false and the F0 label correct), or show the L199–200 sentence has a live referent
other than the set-based visibility reading, or show any pinned input has drifted
(which voids the binding).

## Reproduction

```bash
python3 artifacts/worker-063/set_direction_adjudication/run_set_direction_063.py \
        --out artifacts/worker-063/set_direction_adjudication/report.json
```

Stdlib-only, fail-closed: exit 3 on any pin drift (report not written), exit 2 on any
control failure. Pins: F0 canonical `0abb9ed8a961`, F0 companion `d7419b4e8963`,
F1 canonical + mirror `d9cebb9404b2`, registry `6bac9adea19e`, SET delta `64b8d6394a04`,
FROZEN rev29 `815e08079aef`, consistency evidence `9e335e9ba1bf`.

Controls (all pass): K1 extraction non-vacuous (7 carriers, 1 conflict),
K2 flipping the F0 label clears the conflict, K3 flipping the F1 label is detected,
K4 determinism, K5 fail-closed on pin drift, K6 CH variant (extension-class axis)
stays out of the visibility-predicate conflict set.

## Non-claims

- No gate verdict, no node status, no `validation_status`; worker events cannot move those.
- The finite witness is a set-theoretic strictness obligation only; GR-realizability of
  the separation is the cited omega-chain result `W076-GFORM-STRICTNESS-RECONCILE-06 T4`,
  not re-derived here.
- No canonical artifact was edited.
