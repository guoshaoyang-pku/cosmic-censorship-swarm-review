# W078-F2-F0BIND-ADJ-01 — F0 consistency-evidence binding adjudication

Worker: worker-078 (bounded execution worker). Gate scope: G-FORM. Node: F2 (family-wide F0 binding).
Verdict: **revise**. Classification: **LOSSY_GENERATOR_STALE_PIN**. Advisory evidence only: no gate
verdict, no node transition, no claim about mathematics, physics or class semantics.

## Question

All three rev12 schemas (F1 `cce9c60146d6`, F2a `5476a3f2c6bc`, F2b `55d0a1ea9bda`, FROZEN rev28)
declare

```
f0_binding.consistency_evidence      = artifacts/formulation/evidence/taxonomy_consistency.json
f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37…
```

while the canonical evidence path measures `9e335e9ba1bfcf77…`. Is this stale pin a harmless
re-stamp ordering slip (fix: update the pointer), or does it hide loss of the evidence document's
own hash bindings (fix: regenerate evidence *and* re-publish schemas)?

## Answer

The declared `675a99d0` generation is a **hash-bound** document: it carried

- `map_taxonomy_sha256` = `0abb9ed8a961…` (the declared F0 taxonomy the schemas bind to),
- `lead_contract_sha256` = `d7419b4e8963…` (the class-contract supplement),
- `measured_at` = `2026-09-12T00:32:02+08:00`.

The live `9e335e9b` generation contains the same semantic payload (identical `consistent: true`,
`errors: []`, `contract_divergences: []`, `classes_compared`, `alias_policy`; no value differs on any
common field) but **drops exactly those three fields**. It therefore carries no hash of either
compared tree, and its `consistent: true` is a self-declaration not bound to the F0 revision it is
cited for. Re-stamping the three schemas to `9e335e9b` would make pointer and bytes agree while
leaving the evidence unbound — the exact defect H07b was raised to close — so it is a false closure.

## Mechanism, reproduced

1. `artifacts/formulation/tools/close_findings_rev27.py` (the rev12 repair tool, sha `0234cd3cbda4`)
   writes `taxonomy_consistency.json` **with** the three anchor fields and stamps `measured_at`.
2. `artifacts/formulation/tools/check_taxonomy_consistency.py` (sha `de356d999ea3`, FROZEN rev28 pin)
   writes the same canonical path on every gate run, emitting only the eight semantic fields — it has
   no anchor-field code. Executed in an isolated mirror it reproduced the live document
   byte-for-byte (`9e335e9b`); stdout `CONSISTENT (4 classes, 0 contract-text divergences)`.
3. The live file's mtime advanced 41 s during the run (00:38:48 → 00:39:29) with content unchanged:
   the writer is active and deterministic.
4. Simulating only the repair tool's anchor re-addition on the live document reproduces the declared
   pin exactly: `675a99d0`. Hence the declared pin *was* the correct binding for the measured trees,
   and the canonical checker's later overwrite silently erased it.

## Checks (all in `report.json`)

| check | result |
|---|---|
| B1 live evidence measured, anchors present | none present; `consistent=true` |
| B2 declared pin resolves to pinned copy `artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json` | true (independently re-hashed) |
| B3 declared vs live generation | live is a strict subset; lost fields are exactly the three anchors; payload unchanged |
| B4 isolated checker run | shadow document sha == live sha `9e335e9b`; tool exit 0; tool has no anchor code |
| B5 independent re-implementation of the checker on the frozen YAMLs | 0 errors, `consistent=true` reproduced; `classes_compared` match; trees `0abb9ed8` / `d7419b4e` |
| B6 schema + manifest pins | all three declare the same `675a99d0`; FROZEN rev28 pins the live `9e335e9b`; all three `declared_f0_sha256` match live F0 `0abb9ed8` |
| B7 drift window | content stable; writer active (mtime advanced) |
| B8 simulated correct regeneration | re-adding anchors to live bytes reproduces `675a99d0` exactly; a correct repair necessarily produces different evidence bytes than live |

## Reproduction

```bash
python3 artifacts/worker-078/consistency_binding_verify/verify_consistency_binding_078.py
sha256sum artifacts/worker-078/consistency_binding_verify/report.json
```

Deterministic; read-only on canonical paths (the isolated checker mirror writes only inside a temp
directory). `report.json` and `report_rerun.json` are byte-identical under the deterministic field set
(live hashes recorded in the report may differ if the artifact moves).

## Falsifiers

1. A declared-generation copy without anchor fields (the `675a99d0` bytes lacking
   `map_taxonomy_sha256` / `lead_contract_sha256` / `measured_at`) falsifies the lossy-generator
   classification.
2. A live `taxonomy_consistency.json` whose field set equals the declared generation's falsifies B3.
3. An isolated checker run emitting the three anchor fields falsifies the writer attribution (B4).
4. An independent consistency run on the frozen YAMLs disagreeing with the live flag falsifies B5.
5. A repair path restoring the live document to `675a99d0` without changing any other artifact
   falsifies B8.

## Limits

- Structural/binding adjudication only. The *semantic* consistency claim was independently
  reproduced (B5) but is still a checker output, not a mathematical result.
- The verdict is bound to the bytes measured at the run's timestamps; the live evidence path is
  rewritten by any gate run, so a later hash supersedes (does not refute) the measurement.
- No canonical artifact was modified by this task.
