# W053-REV29-BINDING-VERIFY-01

Worker-053, bounded class-bound task, 2026-09-12 00:55–00:59 (+08:00).
Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` (nodes F1 / F2a / F2b), gate `G-FORM`.

## Question

Did the CF-20 evidence-binding repair (`astra-life05-evidence-binding-repair`, rev13 schemas + rev29
manifest) actually land, and is the resulting FROZEN rev29 pin set self-consistent and live?

## Method

`check_rev29_binding.py` — deterministic, read-only, hash-pinned, two-pass:

* C1 `verify_frozen.py` exit 0 · C2 FROZEN revision ≥ 29 · C3 four repaired paths pinned at live bytes
* C4 schemas declare the **live** `consistency_evidence_sha256` (the CF-20 defect)
* C5 schemas declare live F0 and FROZEN pins it (G-F0 bytes untouched)
* C6 36/36 `taxonomy_cases` rows + meta bound to live F0, 0 stale `66bf917b` tokens, canonical cases checker PASS with controls
* C7 canonical structural gate exit 0 on all three schemas
* C8 `schemas/` ↔ `artifacts/formulation/schemas/` byte-identical
* C9 `class_contract_supplement_pointer` resolves; supplement pin live
* C10 staged re-run of `check_taxonomy_consistency.py` reproduces the canonical evidence bytes (canonical never written)
* C12 registered variant deltas resolve against the live schema bases; variant delta/registry evidence valid and reproduced by staged re-runs
* C11 drift guard: every measured input re-hashed at T1 == T0
* 9 mutation controls (K1–K9), each expected to be caught by a named check

## Result — two passes

| pass | window (+08:00) | FROZEN | verdict |
|---|---|---|---|
| 1 | 00:56:25–00:56:35 | rev29 `3d9e3d77fd87` (00:55:02, 48 pins) | **FAIL** — C1 |
| 2 | 00:58:20–00:58:30 | rev29 `815e08079aef` (00:57:26, 50 pins) | **PASS** — 12/12 checks, 9/9 controls |

Pass-1 observation (`report_pass1.json`):

```
FROZEN revision 29 frozen_at 2026-09-12T00:55:02: 48 files, 1 problems
  DRIFT artifacts/formulation/evidence/variant_delta_check.json: manifest fc6ee058dd96 disk 0b23f0b29232
```

### W053-RV29-01 (major, closed)

FROZEN rev29 generation 1 pinned `variant_delta_check.json` at `fc6ee058` (`valid: true`) while the
live file was `0b23f0b2` — `valid: false` with `CH: base hash drift (55d0a1ea9bda -> b2ab6acb2bbe)`
and `SET: base hash drift (cce9c60146d6 -> d9cebb9404b2)`. Root cause: the rev13 repair moved the
three schemas at 00:53:20 but did **not** rebase the two registered variant delta files, whose
`base.sha256` still named the rev12 bases; a post-freeze checker run at 00:56:03 rewrote the
evidence, leaving the manifest pin stale and its frozen `valid: true` value false at the pinned
schema bytes. The owner then landed `variant_rebase_rev29.py` at 00:57:02 (SET delta
`45b9b6a8d192 → 64b8d6394a04`, CH delta `c28795b0fdfc → 7c165a9063c6`, VARIANT_REGISTRY
`5eb42f9a384a → 6bac9adea19e`) and re-emitted FROZEN at 00:57:26. Pass 2 verifies closure:
C1 exit 0, C12 both delta bases live, both variant evidences valid and reproduced byte-identically.

### W053-RV29-02 (minor, open)

FROZEN was re-emitted **twice under the same revision number 29** with different bytes
(`3d9e3d77`, 48 pins, 00:55:02 → `815e0807`, 50 pins, 00:57:26), while the manifest's own change
protocol says any canonical change bumps the revision. "rev29" is therefore ambiguous; a verdict
must bind the FROZEN **sha256**, never the revision label. Repair: bump the revision on
re-emission (or mark superseded generations).

## Falsifier

Re-measure at the pins above: any of C1–C12 failing, a staged consistency/variant re-run that does
not reproduce the canonical evidence bytes, a case row bound to a superseded taxonomy hash, a
schema whose declared evidence pin is not the live file, or any measured input drifting between T0
and T1 falsifies the pass-2 PASS. A declared hash resolving only at a reconstruction outside the
declared path does not satisfy C4/C10/C12.

## Non-claims

No gate verdict and no node transition (worker events cannot set `done`/`passed`); no adjudication
of class semantics, mathematics or physics; the D2/D3 contract-text divergences reported by the
consistency checker are re-produced, not adjudicated; mirrors are compared to each other, not
re-derived. Pass-1/2 measurements were taken after the repair landed (not blind).

## Evidence

`hashes.txt` pins every deliverable; `controls.json` records the 9 mutation controls;
`runtime/state/w053_rev29_binding_verify_checkpoint.json` is the worker-local checkpoint.
Related independent work: worker-074 `rev29_landing_guard` (P6 FREEZE, same pin mismatch),
worker-007 `rev29_preflight` (pre-repair census + rev29 acceptance predicate),
worker-083 `rev13_repair_packet` / `rev29_postapply_integrity`.
