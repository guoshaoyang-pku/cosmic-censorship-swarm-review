# F1 notes -- AF-WCC-VAC-GEN draft (deepseek-flash-03)

Assignment: `asg-2026-09-11-F1-deepseek-flash-03-12` (comms/inbox/deepseek-flash-03.jsonl)
Node: F1 | Class: AF-WCC-VAC-GEN | Gate: G-FORM | Owner of record: lead-formulation
Artifact: `schemas/af_wcc_vacuum.yaml`
Revision 3 sha256: `7a3e1f93f77c382195224a27e701f30d9e40032ce1ab4ea43c01b38c404fe9c4` (543 lines, structured to FORM-RULE-SPEC R01-R15)
Revision 2 sha256: `f15ea52380d260509826a1bb6da42e81a3c497da77592d776587119002160189` (superseded)
Revision 1 sha256: `eb0d69fab32be640d40032fc8258a0760d068399d7ca0039a2676a1be86dbdc7` (superseded, already in `research_map/events.jsonl`)
Status: **draft, unverified, completion NOT claimed.** A1 review pending.

## What was produced

A machine-parseable formulation schema for the asymptotically flat, vacuum, generic-data
weak-cosmic-censorship class, with the lead's acceptance fields addressed explicitly:
exact quantifiers, topology, weighted data class, genericity, I+, visibility, conclusion type.
Every field that could not be pinned down is listed under `unresolved` in the YAML
(the assignment's stop rule), with what would resolve it.

## Revision 3 (FORM-RULE-SPEC conformance, 2026-09-11T23:34+08:00)

Trigger: the formulation lead published `artifacts/formulation/rule_spec.json`
(FORM-RULE-SPEC R01-R16) and flash-04 ran a 16-probe ambiguity suite whose deciding
leaves did not exist in revision 2. Revision 3 restructures the artifact to the contract:

- all 42 contract leaves required by R01-R15 resolve non-empty (R16 is SCC-only);
- `class_components` decomposes the class id; `quantifiers.ordered` plus `quantifiers.domains`
  replace the free-form quantifier block; `topology.conformal_boundary` and `topology.forbidden`
  are added;
- `data_class` carries numeric decay rates per derivative order, Sobolev index `s = 4` and
  weight `delta = 1/2 + epsilon` as reviewable F1 proposals;
- `regularity` separates data, solution and I+ regularities and sets `extension_regularity: null`
  by rule for the WCC family;
- `genericity` names kind, ambient space, topology/measure, generic set (Baire formula),
  excluded set and transfer failures, and marks the clause as part of the class;
- `non_vacuity`, `i_plus.role`/`completeness_definition`/`in_conclusion`,
  `visibility.role`/`predicate`/`negation_conclusion`, `conclusion.conclusion_type` plus
  `epistemic_status` (dual-key convention), falsifier tiers, and provenance citation status
  are all explicit;
- the F0-equivalent phrasing that trips the foreign-token scan lives in the tagged
  `variants` block (R12 exemption).

Class decisions made under F1 ownership (pinned; A1 review required): the slice topology admits
any connected complete one-ended asymptotically flat slice, not only `R^3`; ADM mass is causal
with only `E = 0` excluded from the dense set; visibility is geodesic and single-point; the
completion boundary is the conformal boundary. Literature-dependent facts remain `unresolved`:
the residual-genericity theorem, the provenance of the `(s, delta)` pair, the non-vacuity
witness, and the F0 review state. Four unresolved fields remain in total.

Self-run results:
- flash-11 class-binding linter: 11/12, only `FILENAME_CLASS` (map path versus linter rule).
- flash-04 ambiguity runner: 42/42 contract leaves, 15/16 determinate, 1 open (F1-AMB-15,
  equivalence unverified), 10 expectation mismatches recorded in the artifact's
  `adjudication_queue` for A1. Determinacy means the schema commits to a reading, not that the
  physics is settled.

## Revision 2 (F0 alignment, 2026-09-11T23:26+08:00)

Trigger: controller notice `astra-notice-2323-deepseek-flash-03` and the F0 taxonomy draft
published by worker-01 at `research_map/formulation_taxonomy.yaml`
(sha256 `a82f249c67250380a971d0c9e7683434ecb201a80c1cb5b65423990bb3500ff5`, status
`draft_unverified`). F0 delegates the genericity topology and the weighted spaces `(s, delta)`
to F1, so revision 2 makes reviewable proposals instead of leaving them blank:

- `class_axes` added in the F0 slot vocabulary; all six axes plus `regularity_token: null`
  verified against F0's class table.
- `genericity_kind: baire_residual` and `genericity_topology: named_by_F1`, with the norm
  topology of `H^4_{1/2+epsilon}` named as the proposal; alternatives and residuals recorded.
- `data_class.weighted_norm`: F1 proposal `(s, delta) = (4, 1/2 + epsilon)`, alternatives
  (Bartnik, Christodoulou-Klainerman) recorded.
- `i_plus.visibility.curve_class`: adopted the F0 geodesic-completeness reading as the proposal;
  causal-curve variant recorded as non-equivalent.
- `f0_consistency` block: hypotheses H1-H5 checked, divergent items DIV-1 (curve class) and
  DIV-2 (inextendibility token) recorded.
- `vocabulary_alignment`: F0 uses `conclusion_type` for the conclusion family
  (`weak_cosmic_censorship`), while the map/claim vocabulary uses it for the epistemic type
  (`open_problem`). Both are recorded in different keys and never merged.

## Findings produced by the cross-checks

1. **G-FORM-FILENAME** -- `check_schema.py` rule 12 (`FILENAME_CLASS`) rejects the map's own
   declared F1 artifact path: it requires `af_wcc_vac_gen` in the filename, but the map and the
   assignment declare `schemas/af_wcc_vacuum.yaml`. All 11 other linter checks pass on both
   revisions. Resolution is a lead decision: relax the rule or rename the map path.
2. **G-FORM-TOKEN** -- the same linter treats any occurrence of the regularity word
   "inextendible" as a strong-censorship-only token in `conclusion.statement`, yet F0's own WCC
   conclusion uses "every future-inextendible causal geodesic contained in J^-(I+) is complete".
   Keeping `statement` linter-clean required moving that phrasing into
   `conclusion.f0_equivalent_form`; the equivalence of the two phrasings is unverified.
   A linter that blocks the taxonomy's own WCC wording cannot be the G-FORM acceptance test
   without amendment.
3. **Auditor compatibility** -- `research_map/audit_evidence.py` scans artifact text for a
   composite-regularity merge pattern with a negation guard; revision 3 contains no such
   pattern (checked with the auditor's regex).
4. **G-FORM-CONTRACT** -- revision 2 predated FORM-RULE-SPEC and lacked its slot names; the
   flash-04 runner bound only 4/15 probes. Revision 3 supplies all 42 R01-R15 leaves and the
   runner now resolves 15/16 probes. Ten expectation mismatches remain and are recorded as
   `adjudication_queue` in the artifact: the suite marked those probes ambiguous when the
   schema was absent, while revision 3 decides them through explicit class choices. They are
   review items, not silent passes.

## Fields that could not be pinned down (stop-rule list, revision 2)

1. `genericity.kind_and_topology` -- proposal made; no verified theorem shows the RSR self-similar
   data are meagre in that topology.
2. `data_class.weighted_norm` -- proposal `(4, 1/2+epsilon)`; not fixed by a verified source.
3. `data_class.topology` -- `Sigma = R^3` vs general one-ended asymptotically flat 3-manifold.
4. `i_plus.visibility.curve_class` -- geodesic vs causal-curve completeness.
5. `i_plus.visibility.set_vs_point` -- single boundary point vs open set of boundary points.
6. `premise.future_boundary` -- causal boundary vs conformal boundary construction.
7. `premise.regularity_of_development` -- regularity at which "maximal" is declared.
8. `data_class.mass` -- whether strict ADM positivity belongs to the class or the generic subset.
9. `dependencies.F0` -- F0 is a draft awaiting two independent reviews; revision 2 is bound to
   F0 sha256 `a82f249c` and must be re-derived if F0 changes.

## Primary-source evidence (all verified by fetch on 2026-09-11, not recalled)

| id | source | verified via | role / scope |
|---|---|---|---|
| penrose1965 | Penrose, PRL 14 (1965) 57-59, doi:10.1103/PhysRevLett.14.57 | INSPIRE record 9038 | origin of visibility heuristic; not a theorem |
| wald1997 | Wald, arXiv:gr-qc/9710068 | arXiv API entry | review: singularities hidden, naked singularities expected non-generic |
| christodoulou1999 | Christodoulou, Ann. Math. 149 (1999) 183-217, arXiv:math/9901147 | arXiv API entry (journal_ref) | scalar-field model where naked singularities are non-generic |
| christodoulou2008 | Christodoulou, arXiv:0805.3880 | arXiv API entry | black-hole formation without symmetry; constructed data family |
| rsp2019 | Rodnianski-Shlapentokh-Rothman, arXiv:1912.08478 | arXiv abstract page | vacuum naked-singularity exterior from self-similar data; genericity not established |
| dhr2013 | Dafermos-Holzegel-Rodnianski, arXiv:1306.5364, JDG 126(2) 2024 | arXiv API entry (journal_ref) | dynamical vacuum black holes settling to Kerr/Schwarzschild |
| dhrt2021 | Dafermos-Holzegel-Rodnianski-Taylor, arXiv:2104.08222 | arXiv API entry | exterior Schwarzschild stability; codimension-3 data caveat in abstract |

Scope-excluded (recorded in the YAML so they are not imported into F1):
Cardoso et al. arXiv:1711.10502 (positive Lambda, not asymptotically flat);
Luk-Oh arXiv:1702.05715 / 1702.05716 (Einstein-Maxwell-scalar, strong censorship);
Dafermos-Luk arXiv:1710.01722 (horizon-interior stability, strong censorship).

## Claim boundary

No theorem, no counterexample, no completion is claimed. The artifact is a draft schema.
`conclusion.type` is `open_problem`; `asserted_conclusion_type_if_proved` is `theorem`;
the F0 class-axis `conclusion_type` is `weak_cosmic_censorship`. The next falsifier for the
schema itself is two independent A1 readers reconstructing non-equivalent quantifier orders
or visibility relations from this file alone.

## Checkpoints

- 2026-09-11T23:17 +08:00 -- recon: no assignment in inbox; map read; F0/A0 artifacts confirmed missing.
- 2026-09-11T23:19 +08:00 -- assignment `asg-...-F1-deepseek-flash-03-12` received; F1 accepted.
- 2026-09-11T23:22 +08:00 -- revision 1 written; linter + vague-term + merge-pattern checks run.
- 2026-09-11T23:23 +08:00 -- revision 1 notes and 4 outbox events emitted (all ingested).
- 2026-09-11T23:26 +08:00 -- F0 draft published; revision 2 written, F0-aligned and re-checked; findings G-FORM-FILENAME and G-FORM-TOKEN recorded.
- 2026-09-11T23:28 +08:00 -- FORM-RULE-SPEC (R01-R16) discovered; revision 3 written to the contract slots; all 42 leaves present; ambiguity suite 15/16 determinate; 10 mismatches queued for A1; linter 11/12; hash `7a3e1f93`.
- 2026-09-11T23:29 +08:00 -- revision 3 notes and superseding outbox events emitted; awaiting A1 review and gate G-FORM verdict from the checker owner (flash-13).
