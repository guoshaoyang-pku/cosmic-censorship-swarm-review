# class_binding_gate — form-only acceptance gate for formulation schemas

Proposed by execution worker 17 (`flash-17`) under nodes **F1/F2** (formulation group).
Classes covered: `AF-WCC-VAC-GEN`, `AF-WCC-SCALAR-SPH`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.

## What it decides

Given one schema document (YAML or JSON), is it a *well-formed, class-bound
specification* for exactly one frozen class — with exact quantifiers, topology,
weighted data class, regularity, genericity, `I+`, visibility, a non-inflated
conclusion type, a witness-shaped falsifier, source refs, and **no cross-class
leakage**?

## What it does not decide

Physical correctness; truth of any conjecture; sufficiency of a formulation for a
proof; whether F1/F2 are complete. A `PASS` is a statement about *form and class
separation* only. It is a filter for the F1/F2/A1 review queue, not an oracle.

## Rule codes

| code | rejects |
|---|---|
| `R_PARSE` | malformed document, or top level is not a mapping |
| `R_CLASS` | `class_id` not exactly one frozen class (umbrella ids such as `AF-SCC-VAC-GEN` rejected) |
| `R_REQUIRED` | a required slot is missing |
| `R_EMPTY` | a required slot is present but empty |
| `R_QUANTIFIERS` | quantifier slot too short to be exact; counterexample form not witness-shaped (no data/datum) |
| `R_TOPOLOGY` | `asymptotically_flat` is not boolean true; `i_plus` too short to identify the object |
| `R_DATA_CLASS` | `data_class.space` is not a weighted Sobolev-type space (no weight/delta/fall-off) |
| `R_CONSTRAINTS` | constraint equations are not named |
| `R_REGULARITY` | disjunctive (`C0 or C2`) or too-short solution regularity |
| `R_GENERICITY` | no measure/topology notion (bare "generic" rejected) |
| `R_VISIBILITY` | WCC missing `visibility.visible_predicate`; SCC missing `visibility.cauchy_horizon` |
| `R_CONCLUSION` | invalid conclusion type; WCC asserting inextendibility; SCC not asserting it; SCC regularity mismatch with `class_id` |
| `R_FALSIFIER` | witness is not a datum in the data class; check too short |
| `R_SOURCE_REFS` | `source_refs` missing/empty or with empty entries |
| `R_MATTER` | vacuum class with non-vacuum matter model; scalar-spherical class without scalar/spherical |
| `R_NO_LEAK` | cross-class token (`AF-SCC`, `AF-WCC`, `C0`/`C2`, `inextendib*`) outside `related_classes` / `source_refs` |
| `R_DISJUNCTION` | the string "C0 or C2" anywhere in the document (hard decision 1) |

`related_classes` and `source_refs` are leakage-exempt by design: class relations and
provenance must be allowed to name other classes. A reviewer must read those two
subtrees manually.

## Measured false positives on the real F1 artifact

The gate was run unchanged on `schemas/af_wcc_vacuum.yaml` (revision 2, sha256 `f15ea523...`,
2026-09-11T23:24+08:00) as part of the reviewer-17 A1 review. It reported 22 shape violations
plus 4 leak violations, **all false positives**:

| false-positive class | cause | fix before reuse |
|---|---|---|
| 22 × `R_REQUIRED` / `R_VISIBILITY` | the gate hard-codes slot names; F1 uses `quantifiers.forall/exists`, `i_plus` at top level, `data_class.weighted_norm`, `genericity.kind`, `evidence_refs` | map fields by content, or freeze one slot vocabulary across F0/F1/F2 |
| 4 × `R_NO_LEAK` | `class_separation.frozen_class_ids` is a declaration list; evidence/citation text is not spec text; `C^2` *development* regularity is legitimate WCC content | context-aware token roles: extension-conclusion vs development-regularity vs class declaration vs citation |
| — | `C^0`/`C^2` tokens in `evidence_refs.*` | exempt evidence/citation subtrees |

Consequence: this gate is **auxiliary review tooling only** and must not be used as the canonical
G-FORM gate until the vocabulary mapping and token-role fixes land. The canonical linter is the
one maintained under the formulation group (see `artifacts/flash-11/f1_aux_class_binding/`).
The measured false-positive rate is itself a review finding: a token/format check that has not
been calibrated on a real artifact will reject good work and, worse, can pressure authors to
change formulation text to satisfy the checker.

## Run

```bash
cd artifacts/worker-17/class_binding_gate
python3 make_fixtures.py        # regenerate deterministic fixtures/
python3 selftest_gate.py        # expect: SELFTEST PASS, exit 0
python3 adversarial_probe.py    # expect: all_matched=True, exit 0
python3 class_binding_gate.py fixtures/good_af_wcc_vacuum.yaml --json
python3 class_binding_gate.py /path/to/schemas/af_wcc_vacuum.yaml
```

Exit codes: `0` all inputs pass, `1` at least one violation (or parse failure), so the
gate can be wired into a check step without parsing output.

## Files

| file | role |
|---|---|
| `class_binding_gate.py` | the gate; `check(doc)` returns violations, CLI for files |
| `make_fixtures.py` | deterministic generators for good + mutant fixtures |
| `selftest_gate.py` | proves mutants are caught and rules are covered; writes `selftest_report.json` |
| `adversarial_probe.py` | probes still-sneaky documents; writes `adversarial_probe_report.json` (declared limits) |
| `fixtures/` | 4 good fixtures + 21 mutants + `EXPECTED.json` |
| `MANIFEST.json` | sha256 of every file in this bundle |

## Verified results (this workspace)

* `selftest_gate.py`: 4/4 good fixtures pass, 21/21 mutants caught, 17/17 rule codes exercised.
* `adversarial_probe.py`: 4/4 probes behave as declared; **3 declared limits** remain
  (semantic vacuity of `visible_predicate`, cross-slot incoherence, leakage-exempt
  `source_refs`). These are limits, not bugs, and define what a human reviewer still
  has to do.

## Status

`validation_status: unverified` — this is *auxiliary reviewer tooling*, not an accepted node
artifact and not the canonical G-FORM gate. F1/F2 remain owned by the formulation lead, and the
canonical linter lives under the formulation group. See the false-positive section above before
reusing any verdict from this gate. No node status in `research_map.json` is changed by this bundle.
