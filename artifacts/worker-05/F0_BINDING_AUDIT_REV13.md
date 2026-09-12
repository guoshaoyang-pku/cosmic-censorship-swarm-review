# Worker 05 — class-bound F0-binding / evidence-integrity re-pin at rev13

Task taken (one class-bound task): independent re-verification of the F0 cross-artifact binding of
class **AF-SCC-C2-VAC-GEN** (F2a) at the canonical revision published 2026-09-12T00:53:20+08:00,
with the sibling class schemas **AF-SCC-C0-VAC-GEN** (F2b) and **AF-WCC-VAC-GEN** (F1) run as
cross-class controls. No canonical path was written; no gate verdict is set; no completion claimed.

## Pinned instant

| artifact | sha256 (prefix) | note |
|---|---|---|
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` | rev13, F2a, gate PASS R01–R16 |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` | rev13, F2b, gate PASS R01–R16 |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` | rev13, F1, gate PASS R01–R16 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | canonical F0 rev5 (frozen) |
| `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` | class-contract supplement (companion, by design) |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` | the cited consistency evidence, 495 bytes |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc16` | FROZEN rev29, 50 files, `verify_frozen.py` exit 0 |
| `artifacts/worker-05/verify/f0_binding_drift_report_rev13.json` | `241e01042df4` | checker report, measured `2026-09-12T01:02:26+08:00` |

Checker: `artifacts/worker-05/verify/check_class_binding_drift.py#bde270d3886a`; selftest PASS
(null control clean, 3/3 planted binding defects caught). Exit 1 at this instant.

## Result per check (all three class schemas)

| check | result | detail |
|---|---|---|
| B1 declared F0 hash == canonical | **pass** | all three declare `0abb9ed8a961` and the canonical bytes measure `0abb9ed8a961` |
| B2 declared == supplement | info-fail | canonical `0abb9ed8` vs supplement `d7419b4e`; these are declared **companion** artifacts in `publication_status` (distinct logical artifacts, consistency-checked, not byte-identical), so this is by design, **not a defect** |
| B3 pointer file exists | **pass** | `research_map/formulation_taxonomy.yaml` |
| B4 pointer anchor resolves canonically | **pass** | `#classes.<class_id>` resolves in canonical F0 (the rev12/rev13 repoint closed the old `class_contracts.<id>` layout drift) |
| B5 anchor resolves in supplement | pass | all three |
| B6 evidence file exists | **pass** | `taxonomy_consistency.json` |
| B7 evidence is hash-bound to the declared revision | **FAIL (hard, all three)** | `taxonomy_consistency.json#9e335e9ba1bf` records `map_taxonomy` + `lead_contract` paths and `consistent: true`, but **no sha256 of either compared file**; `check_taxonomy_consistency.py#de356d999ea3` contains no hash-emission code. The record is therefore revision-independent. |

## Finding (independent of the in-flight repair claim)

The rev13 repair (`astra-life05-evidence-binding-repair`, report `evidence_binding_repair_rev29_report.json#…`)
refreshed `f0_binding.consistency_evidence_sha256` `675a99d0d25b` → `9e335e9ba1bf` and re-ran the
consistency checker. That fixes the **stale pointer** but does not close review finding **HF-B1**
(evidence is not hash-bound to the compared revisions): the pointer now names live bytes, while the
named bytes still cannot show *which* F0 revision pair was compared. `FROZEN` rev29 pinning the
evidence file at `9e335e9b` ties the evidence bytes to the rev29 manifest, but the class schema's
own `f0_binding.rule` ("if the declared F0 artifact changes hash, this binding must be refreshed and
the consistency check re-run before any gate verdict") is discharged by the evidence record alone,
and that record is revision-independent. The canonical gate R01–R16 passes all three schemas at
these hashes, so the gate does not encode B7 — the same blind spot reported at rev12.

Residual (non-blocking here): nothing else fails; B4 warnings from the 00:18 run are closed.

## Falsifier

Regenerate `artifacts/formulation/evidence/taxonomy_consistency.json` (or a named successor) so that
it records the measured sha256 of **both** compared files (`map_taxonomy` and `lead_contract`) and
re-run `check_class_binding_drift.py` to all-hard-checks-pass; or change
`research_map/formulation_taxonomy.yaml` and observe the evidence file's bytes are unchanged, which
would confirm revision-independence. Both are executable without reading any further prose.

## Independence and authority

Declared conflict: worker-05 authored F2a revisions 1–3 and wrote the checker; this is an adversarial
delta audit, **not** the independent second verdict G-FORM needs. No write to `schemas/`, no
`research_map/comms.py ingest`, no gate verdict, no node-status change.
