# W078-F2A-INDEP-VERIFY-01 -- independent hash-bound verification of F2a

- **worker**: worker-078 (bounded execution worker, fleet batch 2026-09-12T00:16:57+08:00)
- **class**: `AF-SCC-C2-VAC-GEN` (node `F2a`), gate context `G-FORM`
- **canonical artifact**: `schemas/af_scc_c2_vacuum.yaml`
- **snapshot sha256**: `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2`
- **verdict**: `accept` -- bound to the snapshot (11/11 checks pass; pinned re-run reproduces every
  check status). Verdict is a *structural/contract* verification, not a truth or non-vacuity claim.
- **written**: 2026-09-12T00:21:09+0800

## Why the task is non-duplicative

`worker-059` claimed F1 (`AF-WCC-VAC-GEN`); this task is F2a. Prior F2a reviews in `reviews/` cite
superseded revisions or carry no `cited_sha256`, which is why the controller's gate audit counts
`F2a [0 distinct accept reviewer(s)]` at the measured hash. This report binds a verdict to one
immutable sha256 and re-measures the live path before and after.

## Method (deterministic, stdlib + PyYAML)

`verify_f2a.py` polls the canonical path until its sha256 is unchanged for 30 s, snapshots the bytes
byte-exactly, then runs:

| check | what it establishes |
|---|---|
| V01 SNAPSHOT | bytes pinned to an immutable snapshot; drift log kept |
| V02 PARSE | snapshot parses as a YAML mapping |
| V03 IDENTITY | `class_id=AF-SCC-C2-VAC-GEN`, `node_id=F2a`, `artifact_kind=class_schema` |
| V04 CONTRACT_FIELDS | 22 required class-contract fields present and non-empty; `conclusion_type` set |
| V05 NO_C0_C2_MERGE | `regularity_token=C2`; C0 named in `anti_scope.not_this_class`; `sibling_disjoint_from=AF-SCC-C0-VAC-GEN` |
| V06 CANONICAL_MIRROR | authoring mirror byte-identical to canonical at the same instant |
| V07 STRUCTURAL_GATE | frozen `artifacts/formulation/tools/check_class_schema.py` verdict `pass`, no failed rules |
| V08 CLASSSEP_TEXT | `research_map/class_separation.py` finds no composite-class declaration in the pinned text |
| V09 CLASSSEP_REGRESSION | frozen regression still PASS (17 leaks detected / 10 controls clean) |
| V10 F0_BINDING | `declared_f0_sha256` equals the live canonical taxonomy hash; `check_taxonomy_consistency.py` CONSISTENT (4 classes, 0 contract-text divergences) |
| V11 HASH_BINDING | canonical path still holds the pinned bytes at end of run |

## Evidence

| file | sha256 |
|---|---|
| `verify_f2a.py` | `34f41b2d996d03517bc914e6459d066c61a3cc91b9333dcf2e51f83fd8a0fa84` |
| `report.json` | `186c9df86a315188deb9220fbcd9e53303849c40a32c2ae531b369ca49e86ef7` |
| `report_rerun.json` (pinned test-retest) | `4b5872d397d88f56507204b995f28bbe4c3703b1dac9aa2d05e77503485a5b07` |
| `snapshot/af_scc_c2_vacuum.b6123750b37d.yaml` | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| `../../runtime/state/w078_checkpoint_1.json` | see checkpoint |

Tool hashes used at verification time (any later change invalidates this report for the new revision):

| tool | sha256 |
|---|---|
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |
| `research_map/class_separation.py` | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| `runtime/bin/classsep_regression.py` | `9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091` |

Sibling artifacts measured at 2026-09-12T00:21:09+0800: `schemas/af_wcc_vacuum.yaml` `9a8bd4c96800`,
`schemas/af_scc_c0_vacuum.yaml` `1bb78ce9b357`,
`research_map/formulation_taxonomy.yaml` `276009f4f63d`,
mirror `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` `b6123750b37d`.
These are observations, not pins; the canonical tree was being republished during the window.

## Reproduce

```bash
python3 artifacts/worker-078/f2a_indep_verify/verify_f2a.py \
  --pin b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2
```

Exit 0 = all checks pass and the binding held; 1 = a check failed; 2 = drift voided the binding.

## Limits

- Structural/contract only. Decides shape and declared bindings, not mathematical truth,
  non-vacuity, or physical correctness (same limit as `ADJ-SEM-3`).
- A YAML comment is invisible to any parser; no comment-level leak detection is attempted.
- The structural gate and class-separation checker are pre-existing repo tools; a revision change
  invalidates the numbers until re-run.
- This report sets no gate verdict and claims no node completion (worker authority limit).

## Falsifiers

1. Re-running `verify_f2a.py --pin b6123750...` and getting any failed check (test-retest falsifier).
2. Any change to the gate/checker hashes above; the report is then invalid for the new revision.
3. A named reviewer exhibiting a semantic class leak on the pinned bytes that the frozen gates miss
   (this tool cannot certify absence of every semantic leak).
4. Canonical sha256 moving away from `b6123750b37d` -- the accept then binds only to the snapshot and
   is advisory at the live hash.
