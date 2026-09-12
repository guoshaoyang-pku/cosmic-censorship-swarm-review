# W48-GFORM-VOCAB-ADJUDICATION-01 — conclusion-type / genericity token authority at the G-FORM pins

Worker: `worker-048`. Class-bound task: **AF-SCC-C2-VAC-GEN** (node `F2a`), gate **G-FORM**,
with cross-checks of F1 (`AF-WCC-VAC-GEN`), F2b (`AF-SCC-C0-VAC-GEN`) and the two F0 companion
artifacts. Read-only against snapshot copies; no canonical artifact was modified.

## The question this settles

Reviewers at the frozen rev12 pins flagged the same hard failure from two directions:
F2a's `conclusion_type` is `scc_c2_future_inextendibility`, which is **not** in
`research_map/formulation_taxonomy.yaml#field_vocabulary.conclusion_type.allowed`
(`weak_cosmic_censorship, strong_cosmic_censorship_C2, strong_cosmic_censorship_C0`)
— worker-059 `HF-059-F2A-01`, worker-063 `C08`, worker-082 `W082-F-04`.
Is F2a non-conformant, or is the allegation an artifact of F0's own vocabulary list?

## Answer (measured, hash-bound)

**F2a is conformant; the stale side is F0 rev5's vocabulary.** The frozen schemas use the
canonical tokens that `artifacts/formulation/rule_spec.json` enforces (R11) and that the
owner-declared `VOCAB_ALIASES.json` names canonical. F0 rev5's allow-list and class axes are
written in the *alias* forms, and one axis value (`unresolved`) is defined by no registry.
`VOCAB_ALIASES` says aliases "must never appear in a new canonical artifact"; F0 rev5 was
written at 00:31:41, after the registry (23:32:53). F0's own rev2 note already records the
missing designation ("Findings 1 and 3 need lead-formulation/Astra designation … one
conclusion-type vocabulary"). No gate tool detects the divergence: `check_class_schema.py`
enforces `rule_spec` (passes) and `check_taxonomy_consistency.py` is alias-aware (passes).

| registry / artifact | conclusion token(s) | form |
|---|---|---|
| `rule_spec.json#vocabularies.class_conclusion_type` | `scc_c2_future_inextendibility`, `scc_c0_future_inextendibility`, `weak_cosmic_censorship` | canonical (R11 enforced) |
| `VOCAB_ALIASES.json` | same three are the canonical keys; `strong_cosmic_censorship_C2/C0` are aliases | canonical-first policy |
| F1/F2a/F2b schemas (rev12) | same three canonical tokens | conformant |
| F0 canonical taxonomy rev5 axes | C2/C0 use `strong_cosmic_censorship_C2/C0` (aliases); `genericity_kind` = `provisional_baire_residual` ×3 and `unresolved` ×1 | alias / unregistered |
| F0 companion supplement rev9 | canonical tokens already | conformant |

## Pins (all re-measured from the snapshot; FROZEN rev28 pins match, 0 mismatches)

| artifact | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (rev9) | `d7419b4e8963` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev12) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d9` |

## Machine result

12 checks, 6 PASS / 5 FAIL / 1 DIVERGENCE, **7/7 controls flip as declared**, snapshot reproduce
guard 12/12 match. Full machine output: `report.json`.

- `V1–V3` PASS: schema tokens equal rule_spec R11 values, are canonical keys, genericity is
  `residual_comeager`.
- `V4–V7` FAIL: F0 axes/allow-lists use alias forms and the unregistered `unresolved`.
- `V8` PASS: the supplement uses canonical tokens — the two F0 companions disagree in form.
- `V9` DIVERGENCE: strict membership of the F2a token in F0's allow-list is False while
  alias-aware equality is True. This is the exact root cause of `HF-059-F2A-01` / `C08`.
- `V10–V11` PASS: the policy predates F0 rev5; F0's author recorded the designation as open.
- `V12` FAIL: F0 rev5 violates the alias policy text as a canonical artifact.

## Repair matrix (consequences derived from each artifact's own declared rule)

| path | change | declared-rule consequence | cost |
|---|---|---|---|
| **A** | revise F0 vocabulary + axes to canonical tokens | F0 rev6 → every schema's `f0_binding` rule forces an F1/F2a/F2b refresh → all rev12 verdicts void | highest, durable |
| **B** *(recommended now)* | record a controller/lead ruling that `VOCAB_ALIASES` canonical keys govern and F0's list is a descriptive legacy vocabulary | no hash moves; F2a/F2b tokens conformant; `HF-059-F2A-01`/`C08` close as alias-form artifacts of F0's stale list | lowest |
| C | rewrite schemas to F0 alias tokens | violates the alias policy text and fails rule_spec R11 | invalid |

The choice belongs to lead-formulation/Astra; this artifact only measures it.

## Verdicts emitted (worker-level, not gate verdicts)

- **F2a** `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc`: `revise`, score 3.5 — carried solely by
  the undecided token authority; **no F2a content defect found**.
- **F0** `research_map/formulation_taxonomy.yaml#0abb9ed8a961`: `revise`, score 3.0 — alias-form
  vocabulary in the canonical artifact, one unregistered token, designation still open.

## Next falsifier

A registry naming `strong_cosmic_censorship_C2/C0` as the required form for new canonical
artifacts, or a controller ruling that F0's `field_vocabulary` governs the schemas (either would
reverse `W48-VOCAB-01` and make F2a/F2b non-conformant); or an existing gate run that detects
this divergence without a human reading it.

## Reproduce

```bash
python3 artifacts/worker-048/gform_vocab_adjudication/snapshot_inputs.py
python3 artifacts/worker-048/gform_vocab_adjudication/audit_vocab.py --controls
```

Authority note: worker events cannot set `status=done`, `validation_status=passed`, or a gate
verdict. All reads are against `snapshot/` copies pinned by `snapshot_manifest.json`.
