# W094-GENERICITY-CONSISTENCY-01 — declared checker for CF-21

**Agent:** worker-094 (bounded execution worker) · **Gate scope:** G-F0 / G-FORM (advisory evidence only)
**Class binding:** `AF-WCC-SCALAR-SPH` (primary); `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (checked)
**Node:** F0 · **Created:** 2026-09-12T00:5x+08:00

## Why

Controller finding **CF-21** (pass 05, 2026-09-12T00:48:44+08:00) records:

> `AF-WCC-SCALAR-SPH` `axes.genericity_kind` is `unresolved` / `genericity_value_status`
> `unresolved_pending_L1` while its rev5 conclusion explicitly quantifies over "a comeager set G of
> data". Four reviewers split: three non-blocking, one major. **No declared checker compares the
> field, so the suites pass either way.**

This task supplies that declared checker. It is the successor of worker-094's own F0 review finding
HF-094-F0-2 and it decides the **D3 discharge record** (`research_map/formulation_taxonomy.yaml:81`,
"confirmed discharged for ALL FOUR classes, including AF-WCC-SCALAR-SPH") against the
machine-readable fields.

## What was measured (frozen hashes; the finding binds these bytes)

| input | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev12) | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |

`report.json.inputs` re-measures these before and after the run; `drift_after_run` must stay empty.

## Declared rules

| rule | severity | statement |
|---|---|---|
| G1 | hard | every class declares `axes.genericity_kind` from the taxonomy's own `field_vocabulary.genericity_kind.allowed` list (or a `VOCAB_ALIASES.json` alias) |
| G1b | soft | the taxonomy's own rule requires a generic-quantified claim to name `genericity_topology` too; F0 carries no per-class topology (the three owned classes discharge it in their schemas; the fourth does not) |
| G2 | hard | a class whose canonical kind is `unresolved` may not carry a specific-quantifier conclusion without an explicit machine-readable provisional/blocked marker |
| G3 | hard | the quantifier family asserted in the conclusion must equal the family of the declared kind |
| G4 | hard | bare `generic data/set` wording is not machine-readable (taxonomy rule) |
| G5 | hard | an `unresolved: true` hypothesis stating the notion "must be named before any claim is filed" requires a machine-readable claim block, not just prose |
| G6 | hard | every non-`unresolved` kind must be discharged by exactly one binding F-node schema resolving to the same canonical kind (alias-aware) |
| S1–S4 | hard/soft | schema-side kind presence, class-id membership, agreement with the taxonomy axis, topology naming |

Aliases are resolved through `VOCAB_ALIASES.json`; `provisional_baire_residual` → `residual_comeager`,
so the three owned classes' provisional tokens are correctly discharged by their rev12 schemas.

## Result at the measured hashes

`report.json.baseline.verdict = FAIL`, with **exactly two hard failures, both on
`AF-WCC-SCALAR-SPH`**:

- **G2** — `axes.genericity_kind: "unresolved"` (line 393) but `conclusion.text` asserts
  `residual_comeager` (line 414); `conclusion` has no `provisional`/`claim_status` marker.
- **G5** — hypothesis `H4` (line 407) is flagged `unresolved: true` and says the genericity notion
  "must be named before any claim is filed", yet the class carries a specific-quantifier conclusion.

The other three classes are **PASS** (hard), with one shared soft finding G1b. `AF-WCC-SCALAR-SPH`
has no binding schema in the current map (`owned_by: "L0/L1 (no F-node owns this class…)"`), so
there is no path by which its genericity value is discharged.

This is a **declaration-level consistency** verdict, not a mathematical theorem and not a claim that
the class is false. It says the class's own machine-readable axis and its own hypothesis block
contradict the quantifier in its conclusion, and that the D3 record of discharge is unsupported for
this class.

## Controls (fail-closed self-test)

7 labeled in-memory mutants, each with a pre-registered expected verdict; no frozen byte is written.
`report.json.controls.verdict = PASS` (7/7):

| id | mutant | expected | observed |
|---|---|---|---|
| C01 | real repair: named kind + H4 flag cleared + binding schema | PASS | PASS |
| C02 | cosmetic rename of the axis only (H4 still unresolved, still unowned) | FAIL G5+G6 | FAIL G5+G6 |
| C03 | F1 conclusion changed to "full measure" against a `residual_comeager` axis/schema | FAIL G3 | FAIL G3 |
| C04 | `axes.genericity_kind` deleted (C2 class) | FAIL G1 | FAIL G1, no crash |
| C05 | F2b conclusion uses bare "generic data" | FAIL G4 | FAIL G4 |
| C06 | empty taxonomy document | FAIL G0 | FAIL G0, no crash |
| C07 | F2a schema kind set to `full_measure` | FAIL S3+G6 | FAIL S3+G6 |

Exit code: `0` = baseline measured and every control behaved as declared; `2` = control deviation;
`3` = input drift during the run. Baseline FAIL is a *result*, not an execution failure.

## Falsifier

Re-run the checker after the formulation owner repins the taxonomy. If `AF-WCC-SCALAR-SPH` declares
a concrete/provisional kind with a binding schema (or an explicit provisional/blocked marker on the
conclusion) and the baseline becomes PASS with all controls still behaving as declared, this finding
is void. **A file rewrite alone is not a falsifier**: the finding binds the sha256 values in
`report.json.inputs` and must be re-run against any new bytes.

## Authority

Worker evidence only. No gate verdict, no node `status=done`, no `validation_status=passed`, and no
frozen artifact was modified. `reviews/CF21-genericity-consistency-094.json` is advisory and marked
`counts_as_full_schema_verdict: false`.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-094/genericity_consistency/check_genericity_consistency.py \
  --out artifacts/worker-094/genericity_consistency/run/report.json
```

## Files

- `check_genericity_consistency.py` — the checker (deterministic, offline, read-only on inputs)
- `run/report.json` — baseline findings, per-class verdicts, controls, measured input hashes
- `run/manifest.json` — sha256 manifest of this task's deliverables and pinned inputs
- `README.md` — this file
