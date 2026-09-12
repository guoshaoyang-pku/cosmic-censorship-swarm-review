# W005-T2 — cross-schema class-contract binding conformance (bounded worker scan)

**Slot:** worker-005 · **Node:** F1 (primary), F2a/F2b (cross-artifact) · **Gate:** G-FORM
**Classes:** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
**Measured at:** 2026-09-12T00:24:59+08:00 · **No gate verdict, no canonical writes.**

## Why this task

G-FORM is blocked with F1 at three revise verdicts and no accept. All three schemas declare
`class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<ID>`,
while `f0_binding.declared_f0_artifact` names `research_map/formulation_taxonomy.yaml`. Reviewers
disagreed on the disposition — `F2b-review-030` PTR-01 = **N**, `convergence-15-rev11` N4 = **N**,
`F2b-review-034` F-034-2 = **hard**, `F1-review-090` HF090-01 = **major**. The measurement that
decides the semantic half of that disagreement had not been run: *is the contract the pointer
reaches the same class contract as the frozen canonical one?*

## Method

`check_contract_binding.py` (independent implementation, self-test **PASS**: 3 controls + 5
mutants, each planted defect detected, clean control clean) reads the live artifacts and measures
per schema: pointer canonicality and fragment resolution in both trees; hash-pin presence;
class-identity axis equivalence under a **declared** vocabulary map; duplicate top-level YAML keys;
future-dated machine timestamps; live F0-binding match; composite-conclusion check. The declared
normalizations are printed in the report so a reader can reject them and re-read the result.

## Result (pins: canonical `276009f4f63d`, authoring `c8e979a1eb48`, F1 `9a8bd4c96800`, F2a `b6123750b37d`, F2b `1bb78ce9b357`)

| axis | F1 | F2a | F2b |
|---|---|---|---|
| pointer resolves on canonical `classes.<ID>` | **FAIL** | **FAIL** | **FAIL** |
| pointer resolves in authoring `class_contracts.<ID>` | pass | pass | pass |
| pointer carries a sha256 pin | **FAIL** | **FAIL** | **FAIL** |
| identity axes agree (declared normalization) | pass | pass | pass |
| schema hygiene (dup keys / future timestamps) | **FAIL** | **FAIL** | **FAIL** |
| f0_binding == live canonical hash | pass | pass | pass |
| conclusion not composite / no C0-C2 merge | pass | pass | pass |

- **Uniform, not F1-specific:** all three schemas carry the same defect (`X1_pointer_defect_uniform`).
- **Semantically non-divergent:** measured identity axes (`family`, `matter_model`, `asymptotics`,
  `regularity_token`, `conclusion_type`) agree. This is evidence for the **N** reading on class
  semantics, and against any class-merge or conclusion-inflation alarm.
- **Binding is still unresolved:** the pointer has no pin and does not resolve on the authoritative
  tree, so it is a **B** defect on the *evidence-binding* axis: verdicts that resolve it against the
  authoring supplement (`verify_f2a_pass2.py:92-95`, `run_review.py:375-397` H12) validated a target
  that is neither the declared artifact nor byte-identical to it.
- **Cured since F1-review-090:** `schemas/f1_falsifier_tests.jsonl` now binds the reviewed F1 bytes
  (`9a8bd4c96800`, 25/25 rows); F090-04 no longer applies at this revision.
- **Bounded repair:** repoint to `research_map/formulation_taxonomy.yaml#classes.<ID>`, add a hash
  pin, delete duplicate `revised_at*` keys, correct the future-dated timestamps.

## Artifacts

| file | sha256 (12) |
|---|---|
| `check_contract_binding.py` | `bdd97297a436` |
| `binding_report.json` | `4d1d836d5a7e` |
| `review.json` (advisory, F1 only) | `1f197147583b` |

Falsifier and scope limits are in `review.json`. Verdicts are advisory; worker events cannot set
node status, validation status, or gate verdicts.
