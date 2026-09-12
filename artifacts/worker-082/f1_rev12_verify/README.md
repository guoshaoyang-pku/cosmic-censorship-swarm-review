# W082-F1-REV12-VERIFY-01 — independent machine verification of F1 rev12

- **worker**: worker-082 (bounded execution worker; instance of the `worker-*` fleet)
- **node / class / gate**: F1 / `AF-WCC-VAC-GEN` / G-FORM
- **target**: `schemas/af_wcc_vacuum.yaml` at measured sha256
  `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` (36014 bytes,
  mtime `2026-09-12T00:32:02+08:00`), authoring mirror byte-identical
- **measurement window**: `2026-09-12T00:36:32+08:00` … `2026-09-12T00:36:45+08:00`
- **verdict**: `revise` — **all six worker-082 rev11 machine defects are closed**, but four
  hash-binding/provenance defects exist in the published rev12 set at the measured instant
- **scope guard**: machine data-integrity and hash binding only. This is **not** a full
  schema/semantic verdict and must not be counted as a G-FORM accept, a `done` status, or a
  `validation_status: passed`.

## 1. Task

`astra-life03-close-findings` published rev12 of the three G-FORM schemas at `00:32:02` and
re-froze FROZEN to revision 28. No review binds the new F1 hash yet. This task independently
re-measures the published bytes and tests (a) closure of the six blocking machine defects
worker-082 reported at rev11 / `9a8bd4c96800` (task `W082-F1-MACHINE-DEFECT-VERIFY-01`), and
(b) whether F1's declared evidence bindings resolve to the files actually on disk.

## 2. Method (reproducible)

```
python3 artifacts/worker-082/f1_rev12_verify/check_f1_rev12.py \
        --out artifacts/worker-082/f1_rev12_verify/evidence.json
```

The checker (`check_f1_rev12.py`, sha256 `0b2263e52b6e8cb7…`) is self-contained and read-only:
it does not import or run any lead-owned tool. It uses a duplicate-key-rejecting YAML loader,
re-measures every input at run time, and includes a negative control on the frozen rev11 bytes
(`artifacts/worker-082/f1_machine_defect/frozen_f1_9a8bd4c96800.yaml`, sha256 `9a8bd4c9…`).
The checker's own no-side-effect guard confirms no input hash changes across the run.

## 3. Results — 18/22 checks pass

### 3.1 Rev11 machine defects: all six closed (positive control)

| rev11 defect (W082) | rev12 observation | status |
|---|---|---|
| W082M-02 duplicate top-level `revised_at` ×7 | one `revised_at` + `revision_history` of 10 entries; strict loader parses clean | **closed** |
| W082M-03 PyYAML last-wins discards 6 stamps | all 9 rev11 stamps preserved verbatim, in order, in `revision_history[1..9]` | **closed** |
| W082M-04 duplicated/dead `revised_at_unused` ×2 | former unused stamps retained as entries with `unused: true`; no `revised_at_unused` key | **closed** |
| W082M-05 future-dated `revised_at` / `checked_at` | `revised_at = checked_at = 2026-09-12T00:31:41+08:00`, ≤ file mtime `00:32:02` and ≤ wall clock | **closed** |
| W082M-06 contract pointer outside canonical tree | `class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN`; fragment resolves in canonical F0 `0abb9ed8…` | **closed** |
| W082M-07 `review_status` stale vs hash-bound verdicts | `independent_reviewers: []` is now accurate (no verdict exists at `cce9c601`); re-review required, not a defect | **closed by hash change** |

Also verified: `AF_{I+}` now has a definition (`i_plus.predicate_abbreviation`, one use in
`conclusion.statement_formal`); the visibility clause is the single-q tail predicate
(`not exists q in I+ and t0 in [0,T)`, D5 binds `(q,t0)`); D0 is retyped as a tagged regularity
index `r` with no `(s,delta)` / `X^{s,delta}_vac` / `G_{s,delta}` residue; class identity
`AF-WCC-VAC-GEN` / node `F1` intact; `f0_binding.declared_f0_sha256` matches the measured
canonical F0 `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`; the
supplement pointer resolves in `artifacts/formulation/formulation_taxonomy.yaml` `d7419b4e…`.

Negative control: the same checker flags **7/7** expected defect classes on the frozen rev11
bytes (`DUP-001, UNUSED-001, CLOCK-001, POINTER-001, AFIP-001, TAIL-001, D0-001`), so the
passes above are discriminating, not vacuous.

### 3.2 Hard findings at the measured instant (four)

1. **`REV12-CONS-001` — stale consistency-evidence binding.**
   F1 declares `f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37…`; the file on disk
   is `9e335e9ba1bfcf77…` (495 bytes, mtime `00:36:36`). The declared hash no longer names the
   published evidence bytes. F2a (`5476a3f2…`) and F2b (`55d0a1ea…`) declare the same stale
   `675a99d0` (measured here as context; no verdict attached to F2 by this record).

2. **`REV12-CONS-002` — the evidence file lost the tree-hash bindings.**
   The measured `taxonomy_consistency.json` keys are
   `alias_policy, classes_compared, consistent, contract_divergences, errors, lead_contract,
   map_taxonomy, notes` — it carries **no** `map_taxonomy_sha256` / `lead_contract_sha256`.
   This is the exact rev12 finding (e) ("evidence not hash-bound") that the repair claimed to
   close; at the current disk state it is not closed.

3. **`REV12-CONS-003` — FROZEN rev28 and the schemas disagree about the evidence hash.**
   FROZEN revision 28 (`2f358f67…`, frozen_at `00:35:08`) records
   `taxonomy_consistency.json = 9e335e9b…`, while all three schemas declare `675a99d0…`.

4. **`REV12-REPORT-001` — the FROZEN-bound apply report does not describe the published bytes.**
   `artifacts/formulation/evidence/close_findings_rev27_report.json` (`dab1d49b…`, bound by
   FROZEN rev28) records F1 as `b474fbc49cdd1ee9…` with `at 00:31:41`; the published F1 is
   `cce9c60146d6a907…`.

**Likely cause (observed, not assumed):** two lead-side writers target the same evidence path —
`close_findings_rev27.py` writes hash-bound evidence (728-byte shape with the two tree hashes),
and `check_taxonomy_consistency.py` (line 79–80) overwrites it with the 495-byte report shape and
no tree hashes. The overwrite happened at least twice (`00:33:16`, `00:34:55`, `00:36:36`), after
the schemas were sealed at `00:32:02`. All four findings are one-event artifacts of that writer
conflict plus the report/schema publish order, not class-semantics defects.

## 4. Falsifier

This record is falsified if, at a re-measurement of the same paths, **any** of the following
holds for F1 and the consistency evidence:

1. `sha256(artifacts/formulation/evidence/taxonomy_consistency.json)` equals F1's declared
   `f0_binding.consistency_evidence_sha256` **and** the file contains
   `map_taxonomy_sha256 == sha256(research_map/formulation_taxonomy.yaml)` and
   `lead_contract_sha256 == sha256(artifacts/formulation/formulation_taxonomy.yaml)`;
2. the FROZEN manifest consistency entry equals that declared hash; and
3. the FROZEN-bound `close_findings_rev27_report.json` records
   `schemas/af_wcc_vacuum.yaml == sha256(schemas/af_wcc_vacuum.yaml)`.

If all three hold at a new published hash, the four hard findings are void and this verification
must be re-run at that hash. If instead the frozen rev11 copy no longer reproduces the 7-defect
negative control, the checker itself is void. Independently: if the published F1 is republished
at a hash other than `cce9c60146d6a907…`, the closure half of this record applies only to
`cce9c60146d6a907…` and must be re-run.

## 5. Authority note

worker-082 cannot set `status=done`, `validation_status=passed`, or any gate verdict. This is
advisory evidence for the F1 owner (lead-formulation) and the G-FORM verifier (lead-audit).
No F0/schema/evidence file was modified by this task.

## 6. Artifacts

| path | sha256 (first 16) |
|---|---|
| `artifacts/worker-082/f1_rev12_verify/check_f1_rev12.py` | `0b2263e52b6e8cb7` |
| `artifacts/worker-082/f1_rev12_verify/evidence.json` | `517a71b0deeb8134` |
| `artifacts/worker-082/f1_rev12_verify/REVIEW-F1-rev12-082.json` | `ddb1571cf0b8137d` |
| `runtime/state/w082_f1_rev12_checkpoint.json` | recorded in the checkpoint |
