# W021-REV29-BINDING-VERIFY-01

Actor: worker-021. Nodes: F1, F2a, F2b, F0. Gate: G-FORM (worker measurement only).
Class ids: AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN.

## Question

Is the FROZEN rev29 evidence-binding repair (astra-life05-evidence-binding-repair)
internally consistent on live bytes: do all declared pins resolve, do the three schemas
bind the live consistency evidence, are the 36 taxonomy-case rows bound to F0 rev5, are
the F1 visibility strictness directions corrected, and are the F0 canonical bytes
untouched?

## Verdict

`BINDING_VERIFIED_AT_REV29` at the measured instant:

* FROZEN manifest sha256 `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`
  (revision 29, frozen_at 2026-09-12T00:57:26+08:00)
* 59/59 checks PASS, 0 failed; 6/6 planted controls detected; 0 pin drift during the run.
* I1 `schemas/taxonomy_cases.jsonl` `ccf7041bd0ff`: 36/36 rows + meta bound to F0 rev5
  `0abb9ed8a961`; 0 rows bound elsewhere.
* I2 all three schemas (`d9cebb9404b2`, `e9a27996dfd3`, `b2ab6acb2bbe`) declare
  `f0_binding.consistency_evidence_sha256 = 9e335e9ba1bf` = live
  `artifacts/formulation/evidence/taxonomy_consistency.json`, and the declared F0 hash
  resolves to `0abb9ed8a961`.
* I3 F1 rev13 D5 reads EQUIVALENT (no live `strictly STRONGER` assertion), the rev12
  misclassification example is removed, and variant SET reads `strictly WEAKER`.
* I4 every path in FROZEN `files{}` (50 pins) and `logical_artifacts{}` matches its
  declared sha256 on disk; rev29_delta names all four repair items.
* F0 canonical `0abb9ed8a961` and supplement `d7419b4e8963` untouched.

## Measured cross-manifest observation (recorded, not a re-discovery)

During this worker's window the artifact named "FROZEN revision 29" existed as two
distinct byte sets:

| manifest sha256 | frozen_at | state at that instant |
|---|---|---|
| `3d9e3d77fd87` | 00:55:02 | 4 declared pins did not resolve to live bytes: VARIANT_REGISTRY `5eb42f9a`→`6bac9ade`, CH delta `c28795b0`→`7c165a90`, SET delta `45b9b6a8`→`64b8d639`, variant_delta_check `fc6ee058`→`0b23f0b2` (live set was mid-repair) |
| `815e08079aef` | 00:57:26 | every declared pin resolves; this is the verified manifest above |

The revision counter did not advance across the regeneration. Bind reviewers to the
manifest **sha256**, not to the label "rev29". Independent confirmation of the same move
is in worker-018's erratum (00:57:42) and worker-095's r3 hold probe (00:57:46); this
measurement adds the exact stale-pin set at `3d9e3d77` and the clean pin set at
`815e0807`.

## L-FORM-03 residual after the 00:57 repair (assertion level)

2 of the 5 rev29_delta-named locations still assert the inverted SET direction, both
inside F0-frozen artifacts that the repair card did not touch:

* `research_map/formulation_taxonomy.yaml:200` (canonical F0 `0abb9ed8a961`) - "strictly stronger"
* `artifacts/formulation/formulation_taxonomy.yaml:176` (supplement `d7419b4e8963`) - "strictly stronger"

The VARIANT_REGISTRY and both variant deltas were corrected to "strictly weaker" at
00:57:02; historical `[rev13 ...]` notes quoting the old wording are excluded.

## Falsifier

Re-run the instrument at the same pins: falsified if any I1-I4/F0 check fails, if any
planted control goes undetected, or if the reviewer's declared acceptance predicate is
not the one in `FROZEN.json#rev29_delta`. A manifest/pin move during the run yields VOID
(exit 3), a superseded revision yields VOID (exit 4) - neither is a falsification.

## Reproduction

```bash
python3 artifacts/worker-021/rev29_binding_verify/verify_rev29_binding.py \
  --out artifacts/worker-021/rev29_binding_verify/run3
```

Exit codes: 0 verified, 1 binding failed, 2 control failure, 3 pin drift (void),
4 revision superseded (void). Two independent runs (`run3`, `run4`) are byte-identical
for `results.json`, `report.json`, `controls.json`.

## Non-claims

No gate verdict, no node transition, no full-schema review, no class-semantics verdict,
no canonical write, and no claim that the F0-side L-FORM-03 residual is repaired.
`run1/` is a SUPERSEDED pre-regeneration snapshot kept as historical evidence only.
