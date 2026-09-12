# Semantic contract tests

Canonical home for the W06 semantic class-leakage corpus, routed here by assignment
`astra-w06-01` (Astra, 2026-09-11T23:41+08:00). This suite is **calibration evidence folded
into `G-AUDIT`**; it defines **no gate id** and does not move any map verdict. `G-CLASSBIND`
was not adopted as a separate gate (controller adjudication, same assignment).

## Layout

| path | what |
|---|---|
| `manifest.json` | contract registry: every fixture → rule(s) tested, expected verdict, observed verdict, adjudication status |
| `observed_verdicts.json` | raw output of the last run: per-fixture per-stage verdicts, fired rules, summary, validity |
| `run_contract_tests.py` | runner (both repo stages + the proposed hardened auditor) |
| `fixtures/` | 32 leak mutants, byte-identical copies of `artifacts/worker-06/semantic_fixtures/` |
| `fixtures/controls/` | 3 frozen controls from the same corpus |

Provenance: source manifest `artifacts/worker-06/semantic_fixtures/manifest.json` sha256
`c102445df3971109…`; fixture copies are hash-verified on every run. The originals are retained
because prior reports and event `evidence_refs` are hash-bound to them — "move" was implemented
as relocate-with-provenance rather than delete.

## Run

```bash
python3 schemas/semantic_contract_tests/run_contract_tests.py                  # write observed_verdicts.json
python3 schemas/semantic_contract_tests/run_contract_tests.py --update-manifest  # also refresh manifest.observed
```

Stages:

| stage | tool | role |
|---|---|---|
| structural | `artifacts/formulation/tools/check_class_schema.py --json <f>` | binding frozen class-schema gate |
| semantic baseline | `artifacts/worker-06/spec_conformance_audit.py <f> --json <o>` | worker semantic auditor, as first written |
| semantic hardened | same + `--hardened` | worker-proposed H01–H17 repairs, **not adopted** |

Exit codes: `0` valid; `2` integrity failure; `3` integrity ok but a control is rejected
(suite must not be used as current-revision calibration evidence until the named adjudication
item is resolved).

## Current measurement

Run `2026-09-12T00:14:40+08:00`; stages structural `000e09e46b2f`, semantic `c79d8ab8440a`.

| stage | mutants caught | escape |
|---|---:|---:|
| structural (binding gate) | 32/32 | 0.0000 |
| semantic baseline | 11/32 | 0.6562 |
| semantic hardened (proposed) | 32/32 | 0.0000 |

32 mutants, 20 rephrased, 32 distinct leak-family descriptions. No mutant escapes both adopted
stages; no mutant is caught only by the proposed hardened set (the structural gate currently
catches every family, including `struct12_i_plus_completeness_lexical`, which escaped the
previous gate revision `ea3deb8c42b5`).

## Controls and validity — one open blocker

- 3 current canonical schemas (`schemas/af_scc_{c0,c2,wcc}_vacuum.yaml`): **accepted by all
  three stages**.
- 3 frozen corpus controls: **rejected by the structural stage, on R28 only**, accepted by both
  semantic stages. The controls embed the corpus base layout (`92406957234f`), where
  `finite_codimension_complement → residual_comeager` sat in `transfer_failures`; the current
  canonical C0 places that transfer row in `transfer_holds`, and R28's truth table rejects the
  misplacement. So R28 is consistent with the current canonical schema and the **controls are
  stale**, not the rule.

Because a control basis must pass both stages, `validity.valid_for_calibration = false` and the
runner exits `3`. Adjudication item `ADJ-CONTROL-STALENESS` asks the lead to either rebase the
control layouts to the current canonical (mutants stay frozen — that changes only controls) or
pin the gate revision used for calibration.

## Which rules need lead adjudication

| item | owner | what is needed |
|---|---|---|
| `ADJ-CONTROL-STALENESS` | lead-formulation | rebase controls to the current canonical layout, or pin the calibration gate revision |
| `ADJ-H01` … `ADJ-H17` | lead-formulation | adopt or reject each proposed hardened delta; each carries its `maps_to_spec_rule`, example fixtures and the 0/5-conforming-schema false-positive note (see `manifest.json`) |
| `ADJ-SEM-1` | lead-formulation | non-meagerness of the extendible set is not machine-checkable |
| `ADJ-SEM-2` | lead-formulation | whether a wording leak changes the mathematical class is not machine-checkable |
| `ADJ-SEM-3` | lead-audit | truth / non-vacuity / physical correctness are outside every structural gate |

## Limits and falsifier

A structural contract test decides shape, not mathematical correctness, non-vacuity, or truth.
A YAML comment is invisible to any parser (documented control). The mutant corpus is
worker-authored and synthetic.

Falsifier for the validity conclusion: a run in which the three frozen controls are all accepted
by the structural stage at the current gate revision, or a current canonical C0 whose
`transfer_holds` places `finite_codimension_complement → residual_comeager` in
`transfer_failures`. Falsifier for the measurements: any stage hash change invalidates the
numbers above until re-run.
