# H01–H17 — hardened rule deltas for FORM-RULE-SPEC 1.0

Owner: worker-06 (deepseek-flash-06) · assignment `assign-FORM-LEAK-03-20260911T2331`
Status: worker-authored repair proposals; **not merged into the binding gate** (the lead's
instruction was to measure them, not merge). Every row names the rule it extends, the
fixture that demonstrates the gap, and the false-positive control that keeps it honest.

Implementation: `artifacts/worker-06/spec_conformance_audit.py --hardened`
Measurement: `artifacts/worker-06/blindspot_report.json` (baseline vs hardened vs both gates)

## Baseline vs hardened on the frozen-base corpus

| run | corpus | caught | escape |
|---|---|---:|---:|
| W06 baseline auditor (R01–R16 decidable parts, pre-repair) | 32 mutants | 11 | 0.6563 |
| binding frozen gate `eef3f43f` | 32 mutants | 13 | 0.5938 |
| independent flash-13 gate (sha pinned in `canonical_gate_run.json`) | 32 mutants | 13 | 0.5938 |
| W06 baseline ∪ both gates (any implementation catches) | 32 mutants | 18 | 0.4375 |
| **W06 hardened H01–H17** | 32 mutants | **32** | **0.0000** |

False-positive control: H01–H17 reject **0 of 5** conforming schemas (canonical C0/C2/WCC at
the FROZEN revision-5 hashes, `schemas/af_scc_c0_vacuum.yaml` rev5, and the deliberately
conforming control), and accept the comment-only-composite control.

## The deltas

| id | extends | condition (all are additive; none replaces a spec rule) | fixture evidence | FP control |
|---|---|---|---|---|
| H01 | R02 | `class_contract_pointer` must resolve to this `class_id` | `sem11_contract_pointer_c2` | canonical schemas end at their own class id |
| H02 | R06 | SCC classes must declare `extension_predicate.{frozen_regularity, frozen_equation_concept, frozen_direction}` | `struct10_equation_requirement_omitted` | all three present in canonical SCC schemas |
| H03 | R06 | no extra key under `regularity` may name another differentiability class | `sem01_smuggled_smoothness_key` | canonical `regularity` blocks carry only the declared slots |
| H04 | R06 | `extension_predicate.frozen_regularity` == class regularity token | `sem10_h2loc_extension_class` | C0 schema freezes C0 |
| H05 | R06 | `extension_predicate.frozen_direction` == `future` for this class | `sem09_two_sided_direction` | canonical SCC schemas freeze `future` |
| H06 | R06 | `regularity.extension_solution_concept` == `extension_predicate.frozen_equation_concept` | `sem08_extension_solution_concept_swap` | both `none` in the bare-metric classes |
| H07 | R07 | `genericity.kind == none` ⇒ `is_part_of_class == false` and no comeager binder in `quantifiers.ordered` | `sem04_all_data_strengthening` | canonical kind is `residual_comeager` |
| H08 | R07 | `kind == residual_comeager` ⇒ `generic_set` expressed as an intersection/meager-complement condition | `sem03_genericity_open_dense_swap`, `sem20_prose_genericity_set` | canonical `generic_set` is a countable intersection with meager complement |
| H09 | R07 | `kind == full_measure` ⇒ measure wording, and no comeager wording (non-transferable) | `sem13_comeager_to_full_measure` | canonical kind is not `full_measure` |
| H10 | R08 | vacuous `witness_type` values (`none`, `none required`, `trivial`, …) rejected | `struct09_nonvacuity_vacuous` | canonical witnesses name trapped surfaces/families |
| H11 | R08 | `non_vacuity.condition` must name an incompleteness/trapped-surface/irregular-boundary marker | `sem15_vacuous_nonvacuity`, `sem19_prose_nonvacuity_condition` | C0 “boundary that is not regular”, C2 “not future geodesically complete”, WCC “future geodesically incomplete” all match |
| H12 | R08 | curvature-invariant hypotheses banned anywhere in a C0 schema | `sem05_curvature_hypothesis` | canonical schemas mention curvature only in exclusion lists (exempt paths) |
| H13 | R09 | the whole `i_plus` block is scanned for conclusion import, including `completeness_definition` | `sem07_i_plus_used_in_conclusion`, `sem17_i_plus_completeness_definition` | canonical SCC `i_plus` keeps I+ out of the conclusion; its `forbidden` list is exempt |
| H14 | R11 | no sibling-class id or twice-differentiable paraphrase inside `conclusion` | `sem02_inherited_sibling_conclusion`, `sem14_c2_result_cited_as_c0` | canonical `conclusion` names the sibling only inside `forbidden_strengthenings` (exempt) |
| H15 | R12 | visibility paraphrase tokens (“seen by an observer at infinity”, …) in SCC `conclusion`/`falsifier` | `sem06_visibility_falsifier_rephrased` | canonical SCC falsifiers are extension witnesses |
| H16 | R15 | source role/note prose claiming to establish/prove/settle the class conclusion | `sem18_provenance_overclaim` | canonical sources are `unresolved` with a no-decisive-use rule |
| H17 | R16 | `one_way_entailments` may not contain the converse C2 ⇒ C0 or a WCC transfer | `sem16_converse_implication` | canonical ledgers put those in `forbidden_transfers` |

## Known residual blind spots (documented, not fixed)

- A composite regularity phrase that appears **only in a YAML comment** is invisible to any
  YAML-parsing gate. Recorded in `control_comment_only_composite.yaml`; lead instruction was
  to document, not fix.
- SEM-1: non-meagerness of the extendible set is explicitly non-machine-checkable (R14).
- SEM-3: structural conformance is not mathematical correctness, non-vacuity, or truth.
- H01–H17 are heuristics derived from one class family and validated on five conforming
  schemas; a legitimate formulation outside that control set could in principle trip one.
