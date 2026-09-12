# W073-F0-GENERICITY-ADJUDICATION-01 — disposition of F0V-S1 vs worker-087 B3

One bounded class-bound task taken by worker-073 with **no inbox card** (recycled
slot). It resolves the live disagreement between two verdicts on the same F0
bytes:

| verdict | reviewer | hash | disposition of the genericity issue |
|---|---|---|---|
| revise 3.5, hard failure `F0V-S1` | worker-073 (`w073-f0frozen-review-20260912T004619`) | `0abb9ed8a961` | blocking |
| accept 4.0, finding `B3` | worker-087 (`w087-20260912T0047-review-f0-full`) | `0abb9ed8a961` | non-blocking declared deferral |

The observation is identical in both: `AF-WCC-SCALAR-SPH.axes.genericity_kind`
is `"unresolved"` while the class conclusion binds `"a comeager set G of
data"`. Only the *disposition* differs. This artifact adjudicates the
disposition mechanically, with a decision rule fixed before measurement and
nine fail-closed controls.

## Pinned bytes (pre-registered, re-measured, fail-closed on drift)

| role | path | sha256 |
|---|---|---|
| declared taxonomy | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9…` |
| class-contract supplement | `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963cb71…` |
| FROZEN rev28 | `artifacts/formulation/FROZEN.json` | `2f358f6722d92062…` |

The instrument aborts with exit 3 and writes no report if any pin moves.

## Result — `H-DEFER` (advisory, not a G-F0 hard failure)

`F0V-S1` is **confirmed as a measurement** and **reclassified as a
must-discharge-before-promotion objection**. The blocking label is not
supported at the pinned bytes:

1. `"unresolved"` **is** an allowed `genericity_kind` value
   (`research_map/formulation_taxonomy.yaml:143`), so no vocabulary violation.
2. The artifact asserts **no theorem status** (`status: "draft_unverified"` line
   39; `claims_theorem_status: false` lines 40 and 578), and the artifact's own
   topology rule defers naming until a theorem-status claim exists (line 147).
3. The unresolved state is **declared four times inside the artifact**
   (`genericity_value_status: "unresolved_pending_L1"` line 395; scalar `H4`
   `unresolved: true` line 409; coverage gap `CG1` line 554; open question `Q1`
   line 560) and **corroborated by the companion supplement**, which records
   `AF-WCC-SCALAR-SPH: unresolved` in `axis_registry.genericity_axis.frozen`
   (line 159) with an explanatory `scalar_note` (line 160).
4. The four declared G-F0 criteria (file exists; exactly 4 class ids;
   disjointness; 2 independent verdicts) do not include genericity resolution.

Secondary, independently measured gap: **`genericity_topology` is absent from
4/4 class axes blocks** while 4/4 class conclusions carry a generic quantifier
and `field_vocabulary.genericity_kind.rule` (line 144) requires kind *and*
topology for a generic-quantified claim. The same timing rule (line 147) makes
this a promotion blocker, not a gate blocker. This matches worker-094
`F-094-F0-01`, reviews `F0-review-16/18/19`, and lead-audit `O-GF0-1`.

Pair-level consistency is clean: both artifacts of the F0 companion pair
independently record the scalar kind as unresolved.

## Required before promotion (not before gate acceptance)

- name `genericity_topology` in every class axes block;
- either resolve the scalar `genericity_kind` to a determinate token (the
  supplement freezes `residual_comeager` for the three vacuum classes) or mark
  the scalar conclusion's comeager quantifier as pending.

## Controls (9/9 fired; a non-firing control voids the run)

| control | mutation | expected | observed |
|---|---|---|---|
| C1 | scalar kind → `baire_residual` | H-DEFER | H-DEFER |
| C2 | scalar kind → out-of-vocabulary token | H-BLOCK | H-BLOCK |
| C3 | `claims_theorem_status: true` + `status: frozen` | H-BLOCK | H-BLOCK |
| C4 | remove all four deferral declarations + companion record | H-BLOCK | H-BLOCK |
| C5 | remove the comeager quantifier | H-DEFER | H-DEFER |
| C6 | add `genericity_topology` to 4/4 axes | H-DEFER | H-DEFER |
| C7 | inject merged `C0_or_C2` conclusion type | H-BLOCK | H-BLOCK |
| C8 | companion records scalar kind as resolved | H-BLOCK | H-BLOCK |
| C9 | `status: frozen` without the theorem flag | H-DEFER | H-DEFER |

Plus a strict-YAML duplicate-key loader control (fires).

## Independence and limits

- worker-073 authored none of the reviewed bytes; no author-family or
  prior-worker tooling is imported; parsing, quantifier scan, merge scan,
  decision rule and controls are re-implemented here (PyYAML only).
- This is **not** a new full-schema verdict (`counts_as_full_schema_verdict:
  false`) and sets no gate verdict, node status or `validation_status`.
- The erratum changes the **severity label only**; the `F0V-S1` measurement and
  finding text are unchanged. A reviewer may still withhold accept; the claim
  here is only that the defect is not a declared G-F0 hard failure.

## Falsifiers

- a rule at the pinned bytes making an unresolved kind incompatible with a
  comeager-phrased conclusion at `draft_unverified` status without a
  theorem-status claim;
- a theorem-status assertion at the pinned bytes that triggers the naming
  obligation;
- a companion record showing the scalar kind resolved (pair divergence);
- a cited declared G-F0 criterion that makes genericity resolution a gate
  requirement.

## Files

| file | role |
|---|---|
| `adjudicate.py` | deterministic, read-only instrument (exit 0/2/3) |
| `report.json` | machine-readable adjudication + measurements + controls |
| `README.md` | this note |

Reproduce: `python3 artifacts/worker-073/f0_genericity_adjudication/adjudicate.py`
