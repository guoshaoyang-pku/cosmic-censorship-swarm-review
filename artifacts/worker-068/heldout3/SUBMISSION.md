# W068-FORM-HELDOUT-09 — class-binding held-out corpus at the frozen canonical revision

Bounded execution worker `worker-068`, node `A1` (class-binding calibration evidence for
`G-CLASSBIND`, folded into `G-AUDIT`; class-bound to `AF-WCC-VAC-GEN`,
`AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`). Measurement only: no gate verdict, no node
completion, no theorem.

## Why this is a class-bound task

The frozen taxonomy splits WCC (`AF-WCC-VAC-GEN`) from SCC and C2 from C0. Every downstream
review binds to these classes, so the machine-checkable question is: **does the live
class-binding pipeline catch a schema that keeps the class token but changes class-defining
content?** This corpus is a held-out measurement of exactly that, built from the current
canonical bytes and mapped fixture-by-fixture to the frozen rules R01–R16.

## Binding (measured at build time, re-checked at run time)

| item | sha256 |
|---|---|
| FROZEN revision | 25 (`frozen_at` 2026-09-12T00:42) |
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9680042a4…` |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d8bee…` |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b3572cda…` |
| stage A `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4ab…` |
| stage B `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440ac673…` |

The builder refuses to run if live canonical bytes differ from the FROZEN entry; the runner
re-checks after the run and voids the measurement on drift. This is the discipline
FORM-HELDOUT-08 lacked (its bases were rev13 snapshots while the live files had moved).

## Method

43 leaky fixtures + 6 control fixtures, run through both stages
(`check_class_schema.py --json FIXTURE`, `spec_conformance_audit.py FIXTURE --json OUT`).
A leaky fixture **escapes** iff both stages accept it (union escape).

Corpus composition:

* 35 leaky mutants, mapped to expected catcher rules R01–R16 (10 WCC-boundary, 10 C2-boundary,
  11 C0-boundary, 4 cross-family/composite). 34 are expected caught; 1 is a declared **probe**
  (`c0_03_conclusion_negated`, logical polarity inversion with the C0 token kept).
* 4 conforming controls (reformatting, exempt-field foreign phrase, registered-variant
  annotation, comment-only edit) — any rejection is a false positive.
* 6 known-rejected leaks from FORM-HELDOUT-07 (rebased tree) — must still be rejected or the
  evaluator is dead.
* 4 known-escape references from FORM-HELDOUT-08 — re-checked for replication only, not validity.

## Result (run valid; no drift)

| metric | value |
|---|---|
| union escape rate, leaky fixtures | **1 / 35 = 2.86 %** |
| caught by stage A (structural) | 34 / 35 |
| caught by stage B (semantic) | 33 / 35 |
| per-class escape rate | WCC 0/11, C2 0/11, C0 1/10 |
| conforming controls | 4 / 4 accepted (0 false positives) |
| known-rejected controls | **6 / 6 still rejected** (evaluator live) |
| HELDOUT-08 escape references | **4 / 4 still escape** at rev25 (families replicate) |

### Escaped fixture (the deliverable)

`mutants/c0_03_conclusion_negated.yaml` — the C0 conclusion statement is inverted
(“…admit a proper future C0 metric extension” instead of non-existence of one) while
`conclusion_type`, `class_id` and all slots stay C0-valid. Stage A passes and stage B accepts.
Rule R11 checks the conclusion *token*, not the polarity of `statement_formal` against the
recorded `negation_normal_form`. This is a real class-content change that the pipeline does not
see; it is a blind-spot finding, not a task failure.

Secondary complementarity finding: `w08_iplus_completeness_erased` (empty
`i_plus.completeness_definition`) is rejected by stage A (R09) but **accepted by stage B**, so
the semantic auditor alone would miss it.

## What this does NOT claim

* Not a gate verdict, not a node completion, not a class-truth claim.
* The leak labels are author-side (`leak_validity_review.json` is explicitly NON-INDEPENDENT);
  an independent reviewer must adjudicate at least `c0_03_conclusion_negated` before the
  escape family is cited.
* Acceptance by both stages is evidence about this pipeline only, not that a schema is
  class-correct.

## Next falsifier

An independent reviewer classifying `c0_03_conclusion_negated` as legitimate removes the
escape family; a later FROZEN revision in which the same fixture text is caught invalidates it;
any canonical republish between build and run voids the run (runner records the drift).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-068/heldout3/build_corpus.py   # refuses on canonical drift
python3 artifacts/worker-068/heldout3/run_heldout3.py
python3 artifacts/worker-068/heldout3/emit_artifacts.py
```

## Files

| file | role |
|---|---|
| `manifest.json` | fixture list, ops, expected rules, per-file sha256, frozen binding |
| `raw_verdicts.json` | every stage-A/stage-B verdict with failed rules and stderr |
| `report.json` | aggregates, per-class/per-family rates, escape families, limitations |
| `gate_sensitivity_check.json` | known-rejected + known-escape control results |
| `leak_validity_review.json` | author-side (non-independent) leak classification |
| `build_corpus.py`, `run_heldout3.py`, `emit_artifacts.py` | deterministic builder/runner |
| `bases/`, `mutants/`, `controls/`, `known_leaks/`, `diag/` | fixtures and stage-B diagnostics |
