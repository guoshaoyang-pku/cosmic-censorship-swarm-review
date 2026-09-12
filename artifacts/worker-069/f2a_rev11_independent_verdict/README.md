# W069-F2A-REV11-VERDICT-01 — independent verdict, F2a / AF-SCC-C2-VAC-GEN

Worker: `worker-069` (bounded execution worker, fleet batch 2026-09-12T00:16:57).
Node: `F2a`. Class: `AF-SCC-C2-VAC-GEN`. Gate: `G-FORM` (verdict NOT set here).
Target: `schemas/af_scc_c2_vacuum.yaml` at sha256 `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
(rev 11, FROZEN revision 25 `af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b`).

## Why this task

The formulation lead's final blocker (leadform-blocker-0006, B1/B2) records that no independent
verdict binds the final G-FORM hashes and the final declared-F0 hash. This report is one
hash-bound independent verdict for one class, taken without any assignment card (none existed
for slot 069) and without editing any formulation artifact.

## Result

**Verdict: `accept` (score 4.0), 0 hard failures, 1 advisory.**
26/27 independent criteria pass; 13/13 controls behave (unmutated positive passes, all 12
field mutations are caught by their expected check). Canonical repo tooling also passes on the
same bytes: structural gate `pass`, two-stage acceptance `PASS`, FROZEN rev25 `0 problems`,
class-separation regression `17/17 leaks, 0 FP/FN`.

| evidence | sha256 |
|---|---|
| `report.json` (verdict + all checks/controls/tools) | see `report.json.sha256` |
| `check_f2a_independent.py` (27-criteria checker + 13 controls) | see `SHA256SUMS` |
| `raw/checker_selftest.json` | see `SHA256SUMS` |
| `snapshot/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| `snapshot/formulation_taxonomy.yaml` | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |
| `snapshot/FROZEN.json` | `af24e9c396060e6bff2b2cbf781814f587d60ba0e74fc0764918fa5757ec983b` |
| `snapshot/VARIANT_REGISTRY.json` | `5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b` |

## Method

1. **Byte-exact snapshot** of the schema, the declared canonical F0, the FROZEN-pinned contract
   supplement, the variant registry and the FROZEN manifest; a pre-run check confirms each
   snapshot byte-equals its canonical path.
2. **Independent criteria checker** (`check_f2a_independent.py`, stdlib + PyYAML) transcribing the
   G-FORM criteria from `evaluation_rubric.yaml` and `gates.G-FORM`: single frozen class id;
   explicit sibling disjointness; exact `forall-exists(comeager)-forall-not_exists` prefix without
   hedging; D0-D3 domains; topology/end structure; vacuum + Lambda=0 + Ric=0 (forbidden-evidence
   list); regularity + decay; constraints; allowed genericity kind; named topology/measure;
   allowed SCC conclusion and absence of WCC/I+ predicates; forbidden strengthenings/weakenings;
   finite tier-1 falsifier with machine-checkable steps; anti-scope exclusions; one-way
   C0⇒C2 entailment with the converse forbidden; canonical class-separation scan; no
   variant-as-class token; non-vacuity; `f0_binding` matches the measured F0; contract pointer and
   axis agreement; unresolved items recorded.
3. **Mutation controls** (12): wrong class id, C0 conclusion, unknown genericity, missing
   constraint, hedged quantifier, WCC content in the conclusion, stale F0 binding, deleted
   anti-scope, deleted non-vacuity condition, C0/C2 composite assertion, empty machine-checkable
   falsifier steps, wrong `one_class_only`. Each must trip its expected check.
4. **Repo tooling re-run** on the same bytes, outputs captured under `raw/`. The driver asserts the
   acceptance evidence file stays byte-identical to its FROZEN pin after the run.
5. **Post-run drift check**: schema/F0/supplement/registry re-hashed; no drift during the run
   (`drift: false`). A later canonical revision voids this verdict.

## Findings (advisory, no hard failure)

1. **G25 conclusion-token vocabulary.** The same conclusion is spelled three ways:
   `scc_c2_future_inextendibility` (schema), `strong_cosmic_censorship_C2` (canonical F0 axes),
   `C2_inextendibility_of_maximal_development` (rubric A0 `frozen_classes`). The axis check shows
   semantic agreement, but no single machine-readable allowed-set exists for the G-FORM criterion
   “conclusion_primary chosen from the class' allowed set”. Recommend a vocabulary map.
2. **G23 contract pointer crosses trees.** `class_contract_pointer` resolves to the FROZEN-pinned
   *authoring* supplement `artifacts/formulation/formulation_taxonomy.yaml` (`c8e979a1eb48`), not the
   canonical `research_map/formulation_taxonomy.yaml` (`276009f4f63d`). Both were read and agree on
   the C2 axes; `audit_evidence.py` still reports the F0 dual-tree soft divergence at this instant,
   so CF-13 remains open at F0 level.
3. **INFO.** Canonical F0 status is `draft_unverified`; four schema `unresolved_items` are recorded
   (diffeomorphism-quotient genericity, meagreness of excluded families, non-vacuity witness
   membership, nonlinear extension regularity). Limits on what the schema supports, not G-FORM
   failures.
4. **INFO.** `audit_evidence.py` exits 1 on the known `claims[36]` prose false positive (CF-16)
   plus the F0 dual-tree soft flag; neither is against the F2a bytes.

## Falsifier

Re-run `run_verdict.py` on byte-identical inputs. Falsified if any recorded `ok=true` check fails
on those bytes, any mutation control escapes, the canonical schema/F0 hashes drift from the pins,
or the canonical tools exit non-zero / report non-pass. A reviewer showing the three G25 tokens
denote *different* conclusions forces `revise`.

## Non-claims

Not a gate verdict (G-FORM is the controller/leads' to set); not a node transition; no claim about
the truth of cosmic censorship, L1 citation support, or physical well-posedness; binds only the
pinned bytes. No formulation artifact was edited. One shared-state side effect is disclosed: the
canonical `run_acceptance.py` rewrites its own evidence file; the driver asserts its bytes remain
identical to the FROZEN pin (`9b7d6c8208d3…`), which held.
