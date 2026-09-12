# W069-GFORM-T1-GUARD-REV13-01 — T1 guards re-measured at the rev13 / FROZEN rev29 pins

**Worker** `worker-069` · **gate context** `G-FORM` · **nodes** F2a, F2b (F1 context only) ·
**classes** `AF-SCC-C0-VAC-GEN` -> `AF-SCC-C2-VAC-GEN` · **measurement time**
2026-09-12T01:00–01:04+08:00.

**Measurement only.** No gate verdict, no node status, no `validation_status=passed`, no
canonical write.

## Verdict

**`T1_NOT_LICENSED_AT_PINS`** — at the FROZEN rev29 pins, transfer rule T1
(`AF-SCC-C0-VAC-GEN -> AF-SCC-C2-VAC-GEN`) does not pass its own three guards:

| guard | reading | verdict | binding? |
|---|---|---|---|
| G1 data_class exact match | literal, every leaf | **FAIL** | yes |
| G1 core tuple (secondary) | 15 pre-registered core keys, T3-normalized | PASS | no |
| G2 genericity fields | literal `genericity_kind` / `genericity_topology` | **UNEVALUABLE_AS_WRITTEN** | yes |
| G2 mapped (secondary) | `genericity.kind` / `genericity.topology_or_measure` | PASS | no |
| G3 source claim binding | literal: artifact_refs + reviewer verdict | PASS | yes |
| **T1 licensed** | `G1 AND G2 AND G3` literal | **False** | — |

`UNEVALUABLE_AS_WRITTEN` counts as NOT PASS by the pre-registered decision rule.

This is the same per-guard verdict as the prior measurement `W071-T1-GUARD-EVAL-01`
(worker-071, rev12 pins). That measurement is **void by its own falsifier** because all
schema input hashes changed at the rev13 publication; this artifact is the required re-run
at the new pins, with an independently written instrument.

**Why the C0=>C2 transfer stays unlicensed:** G1 literal fails on exactly two
annotation-only `adm_mass` paths, and G2 fails because the F0 guard names two fields that do
not exist in either frozen schema:

| # | guard | path | F2a (target) | F2b (source) |
|---|---|---|---|---|
| 1 | G1 | `data_class.adm_mass.hypotheses_reconciliation` | \<missing\> | present (source line 140) |
| 2 | G1 | `data_class.adm_mass.locator` | `to be supplied by L1` (line 139) | `to be supplied by L1 (Schoen-Yau / Witten); the sign is used only to exclude negative-mass data from the ambient space` (line 140) |
| 3 | G2 | `genericity_kind` | does not resolve | does not resolve |
| 4 | G2 | `genericity_topology` | does not resolve | does not resolve |

The pre-registered core tuple (matter, Lambda, equations, constraints, regularity
`(s > 5/2, delta in (1/2,1))`, decay rates, parity, symmetry, `adm_mass.exists/sign`) is
**strictly equal** between F2a and F2b. So the T1 blocker is carried by an annotation-only
exact-match criterion plus a field-name defect in the F0 guard text — not by any divergence
in the mathematical data class. A gate owner can falsify this reading only by declaring a
normalization/annotation-exclusion rule (not currently declared in F0) or by repairing the
G2 field names; the mapped G2 reading already passes.

G3 literal passes, but the two bound C0-class claims do not assert C0 future-inextendibility
(`strengthened_qualifying_count = 0`), so G3's literal pass does not carry the C0 conclusion.
Population at the pinned map snapshot: 171 C0-class claims, 2 bound, 0 strengthened.

**F1 context (not part of T1, reported for the gate's joint wording):** F1 vs F2b has 9
strict data_class witnesses, **2 of them on core keys**
(`asymptotic_decay.parity_conditions`, `regularity_class.sobolev_variant.spaces`). The joint
F1/F2a/F2b wording of the G-FORM unmet item is therefore driven partly by F1, not only by the
F2b->F2a pair.

## Pins (binding; snapshot copies in `snapshot/`)

| role | path | sha256 |
|---|---|---|
| T1 source F2b | `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` (rev29 manifest) |
| T1 target F2a | `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` (rev29 manifest) |
| T1 rule / F0 | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` |
| F1 context | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` (rev29 manifest) |
| FROZEN manifest | `artifacts/formulation/FROZEN.json` | `815e08079aefbc16` (rev 29, 50 files, frozen 00:57:26) |
| consistency evidence | `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |
| map (G3 population) | `research_map/research_map.json` | `262da69798578d77` (`updated_at` 00:55:13) |

`selftest`/binding support: `check_frozen_binding.py` re-verified every live canonical input
against its pin, the FROZEN rev29 manifest entries against the same pins, and the
`artifacts/formulation/schemas/` mirrors against canonical bytes — `FROZEN_BINDING_INTACT`,
0 binding errors, mirrors identical, 2/2 negative controls discriminate. Live inputs did not
drift across the run window (`window.status = STABLE`, all `live_matches_pin_at_exit = true`).

## Controls and reproducibility

- **8/8 pre-registered controls pass**: positive/negative G1 (self-equality, parity mutant
  with exactly one witness path), missing-key G1, positive/negative G2, positive/negative G3,
  plus source-vs-self. Two further controls in `check_frozen_binding.py` (corrupted manifest
  entry, flipped pin) discriminate exactly the intended path.
- **Byte-deterministic**: two full runs produce identical stable views, digest
  `fe1feab1c06636671a12a3b176bdca11e3543b539bfb67f37990a51711b488b7`
  (SHA-256 over the report excluding `generated_at`).
- **Independent instrument**: `eval_t1_guards_rev13.py` is clean-room from the pre-registered
  rules; it does not import or execute worker-071's `eval_t1_guards.py` (hashed in
  `PREREGISTRATION.json` as a reference only).

## Files

| file | role |
|---|---|
| `PREREGISTRATION.json` | rules, core keys, controls, decision rule — written before the run |
| `eval_t1_guards_rev13.py` | independent evaluator |
| `report.json`, `raw/guard_eval.json`, `raw/guard_eval_run2.json` | results (run 1 / run 2) |
| `check_frozen_binding.py`, `raw/frozen_binding.json` | pin/manifest/mirror binding support check |
| `snapshot/` | hash-pinned input copies |
| `CHECKPOINT.json` | bounded-lifecycle checkpoint record |
| `SHA256SUMS` | hashes of all files in this directory (excluding itself) |

## Falsifier

Re-run `eval_t1_guards_rev13.py` at these pins: this measurement is falsified if any guard
evaluates PASS contrary to the recorded verdicts (all three PASS would license T1 and refute
the G-FORM unmet item at the full strength of the transfer rule), if the witness set or the
G3 population changes, or if a control stops discriminating. Any input sha256 change voids the
measurement at the changed path and requires a re-run at the new pins; live map mutations
after the pinned snapshot do not change the G3 population measured here.
