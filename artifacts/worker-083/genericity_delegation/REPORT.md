# W083-F0-GENERICITY-DELEGATION-01 — are F0's delegated genericity slots actually discharged?

**Worker:** `worker-083` (bounded execution worker; no assignment card existed for this slot)
**Node / gate / classes:** `F0` / `G-F0` / `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`
**Task taken:** the `G-F0` unmet item *"the taxonomy is still labelled draft_unverified by its
author and its genericity slots are owned by F1/F2"*, narrowed to the machine-decidable half:
for each class, is the delegated genericity slot discharged by the frozen owner artifact at the
measured bytes, under the registry's own vocabulary aliases, or is it still open?
**Status of deliverable:** measured artifact + controls. **No gate verdict, no node status, no
class-id change, no theorem.** A worker event cannot move a gate.
**Reproduce:** `python3 check_genericity_delegation.py` (exit 0 iff every control passes).

---

## 1. Result

| class | F0 slot (F0 bytes) | F0 owner field | owner artifact (measured) | owner `genericity.kind` | verdict |
|---|---|---|---|---|---|
| `AF-WCC-VAC-GEN` | `provisional_baire_residual` | `provisional_owned_by_F1` | `schemas/af_wcc_vacuum.yaml` `cce9c60146d6` | `residual_comeager` + named topology | **DISCHARGED** |
| `AF-SCC-C2-VAC-GEN` | `provisional_baire_residual` | `provisional_owned_by_F2` | `schemas/af_scc_c2_vacuum.yaml` `5476a3f2c6bc` | `residual_comeager` + named topology | **DISCHARGED** |
| `AF-SCC-C0-VAC-GEN` | `provisional_baire_residual` | `provisional_owned_by_F2` | `schemas/af_scc_c0_vacuum.yaml` `55d0a1ea9bda` | `residual_comeager` + named topology | **DISCHARGED** |
| `AF-WCC-SCALAR-SPH` | `unresolved` | `unresolved_pending_L1` | none in the four-class schema set | — | **OPEN_BY_DESIGN_L1** |

So the delegation is **not** an open F1/F2 obligation at the measured bytes: all three F1/F2-owned
slots are named by their owner, and the placeholder token is alias-registered
(`provisional_baire_residual -> residual_comeager`, `VOCAB_ALIASES.json#46cd9f1eb534`). The fourth
slot is L1-owned by F0's own declaration and must not be counted against the F0/F1/F2 closure.

Two real defects remain, both in the F0 artifact rather than in the owners:

- **F-GEN-2 (major):** `field_vocabulary.genericity_kind.rule` requires a generic-quantified class
  to name **`genericity_kind` AND `genericity_topology`**, but **4/4** class `axes` blocks carry no
  `genericity_topology` value. The owners name the topology *content*
  (`genericity.topology_or_measure`); F0's own slot is empty. Minimal closure edit for the F0 lead:
  set `axes.genericity_topology` to its declared status token `named_by_F1` / `named_by_F2` (and
  `unresolved` for the scalar-spherical class), and decide whether the `provisional_*` kind token is
  flipped to the canonical allowed token `baire_residual` now that the owner value is frozen.
- **F-GEN-4 (minor):** F0 says downstream schemas "MUST reference these slot names"; the owners use
  `genericity.kind` / `genericity.topology_or_measure` instead of `genericity_kind` /
  `genericity_topology`. Values are alias-compatible, so this is a labelling divergence that a
  literal-name cross-class linter would report as a missing slot.

**Robustness across the revision move.** The formulation tree was rewritten at 00:31:41 (taxonomy)
and 00:32:02 (three schemas), i.e. after the controller's 00:24:40 audit. The same decision
function was therefore re-run on **byte-identical pinned copies of the controller-cited revision**
(F0 `276009f4f63d`, F1 `9a8bd4c96800`, F2a `b6123750b37d`, F2b `1bb78ce9b357`, all four pins
hash-verified): **all three slots are DISCHARGED there too**. The finding is not an artifact of the
rewrite.

## 2. Inputs (single instant)

| role | live path | sha256 (snapshot = live at copy) |
|---|---|---|
| F0 canonical | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9…` |
| owner F1 | `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6a907…` |
| owner F2a | `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196…` |
| owner F2b | `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b8…` |
| vocabulary registry | `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df73…` |
| previous-revision pins | `artifacts/worker-061/f1_independent_verdict/pinned/…` | four hashes match the controller-cited revisions |

The bytes were copied before analysis and re-hashed after the run: `live_equals_snapshot = true`
for all five, so the result binds one stable instant. Exact line refs are in `evidence.json`
(e.g. F0 slot `inputs/formulation_taxonomy.yaml#0abb9ed8a961:169`, owner value
`inputs/af_wcc_vacuum.yaml#cce9c60146d6:141`).

## 3. Method and controls

1. Strict parse of the four YAML artifacts with a loader that **records duplicate mapping keys**
   (the known `revised_at` class of defect) instead of silently keeping last-wins.
2. Build the alias map from `VOCAB_ALIASES.genericity_kind`; a token is accepted only if it is
   canonical or alias-registered.
3. Pure decision function `discharge_verdict(placeholder, owner_kind, owner_topology, alias_map)`,
   used identically on live data, on the previous-revision pins, and on synthetic controls.
4. Nine controls, all passing: positive discharge; owner still provisional; alias unregistered;
   owner unresolved; topology missing; token mismatch; duplicate-key recorder fires on a planted
   duplicate; the F0 topology-axis detector fires on a planted axes block without the slot; and
   determinism (two builds give the same canonical digest `f519d52e014e`).

The controls are the reason to believe a `DISCHARGED` row: each neighbouring failure mode is
exercised and produces a non-discharge verdict.

## 4. Falsifiers

- **F1:** exhibit bytes at one of the three owner hashes whose `genericity.kind` is still
  provisional/unresolved or whose `topology_or_measure` is empty → that DISCHARGED row is falsified.
- **F2:** exhibit a `VOCAB_ALIASES` revision at the cited hash that does not map
  `provisional_baire_residual` to the owner token → the alias half of the result is falsified.
- **F3:** exhibit an F0 `axes` block at the cited hash that carries `genericity_topology` →
  F-GEN-2 is falsified for that class.
- **F4:** exhibit an `AF-WCC-SCALAR-SPH` schema artifact frozen in the four-class set that the F0
  closure revision must discharge → F-GEN-3's "not F1/F2-owned" reading is falsified.
- **F5 (moving target):** a later revision whose genericity blocks differ; re-run the script and
  compare `canonical_digest_sha256`, which covers every input hash and verdict but not wall clock.

## 5. Not claimed

No gate verdict (G-F0 stays pending), no node status, no class-id creation/merge, no physics or
mathematics claim, and no claim that the current revision is the final one. The two F0 defects are
**proposals for the F0 lead**; only the lead/controller may edit the taxonomy's axes or accept the
delegation as the closure mechanism.
