# W088-REV13-DELTA-SCOPE-01 — rev12 → rev13 delta and FROZEN rev29 pin audit

**Worker** `worker-088` (bounded execution worker, independent_supervisor_100 lifecycle) ·
**nodes** F1, F2a, F2b · **classes** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
· **gate context** G-FORM · **task source** G-FORM immediate queue; no card was issued for
worker-088 in this lifecycle

**Authority.** Worker measurement only. No gate verdict, node status, `validation_status` or
theorem is claimed. No canonical path was written; all inputs were read and all outputs written
under `artifacts/worker-088/rev13_delta_scope/` and `runtime/state/`.

**Question.** Is the landed rev13 delta of the three class schemas confined to the scope declared
by `astra-life05-evidence-binding-repair`, do the refreshed bindings resolve byte-exactly, and do
the FROZEN rev29 pins match disk — at one measured hash set?

## Measured pins (end state, 2026-09-12T00:59+08:00)

| item | sha256 (12) | note |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` | rev13, F1; stable across the run |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3` | rev13, F2a; stable across the run |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe` | rev13, F2b; stable across the run |
| rev12 baselines (pinned copies) | `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda` | verified against the declared rev12 hashes |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` | revision 29, `frozen_at` 00:57:26, 0 pin problems at end |
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff` | 36/36 data rows + meta rebound to F0 rev5 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | F0 declared, untouched |
| `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963` | F0 supplement, untouched |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` | live consistency evidence, `consistent: true` |

## Verdict

`SCOPE_COMPLIANT_WITH_CARRIED_RESIDUAL` — 0 hard findings, 0 errors, 2 major recorded findings.

| check | result |
|---|---|
| rev12 baseline pin integrity | pass (3/3 pinned copies equal the declared rev12 hashes) |
| changed leaves rev12 → rev13 | F1 9, F2a 6, F2b 6; **0 out-of-scope leaves** |
| declared-scope classes | revision bump, `revised_at`, `revision_history` append, `f0_binding` refresh, F1 `[rev13:]` strictness text |
| protected-leaf guard (class id / axes / hypotheses / conclusion / quantifiers / topology / data class / exclusions) | 1 advisory hit: `quantifiers.domains.D5.definition` changed as part of the declared F1 strictness repair (recorded, not a defect) |
| `f0_binding` resolution (all 3) | pass: declared F0 = measured `0abb9ed8`; consistency evidence = measured `9e335e9b` and `consistent: true`; supplement pointer resolves |
| top-level `class_contract_pointer` (all 3) | pass: resolves to the matching class node in the canonical taxonomy |
| canonical vs authoring mirror | pass: byte-identical for all three |
| F1 strictness field checks | pass: variant SET relation asserts `strictly WEAKER`; D5 and `visibility.definition` state EQUIVALENT; no asserted inverted direction in the visibility fields |
| case corpus | pass: 36/36 data rows bound to `0abb9ed8a961`; meta `taxonomy_ref.sha256` matches |
| FROZEN rev29 end-state pins | pass: 50 files, 0 mismatches (`verify_frozen.py` rc 0 independently) |
| declared structural checker (`check_class_schema.py`) | pass 3/3 (cross-check, author tool) |
| `classsep_regression.py` | PASS, 17/17 leaks, 10/10 controls, 0 FP, 0 FN (cross-check) |

## Findings (major, carried — none blocks the rev13 delta itself)

1. **`W088-R13-FREEZE-DRIFT-TRANSIENT` — the 00:55:02 FROZEN rev29 manifest was 4-pin
   inconsistent during the audit window.** Measured at ~00:56:5x: declared pins for
   `artifacts/formulation/VARIANT_REGISTRY.json` (`5eb42f9a384a` vs disk `6bac9adea19e`),
   `artifacts/formulation/evidence/variant_delta_check.json` (`fc6ee058dd96` vs disk `0b23f0b2…`),
   `artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json` (`c28795b0fdfc` vs disk
   `7c165a9063c6`) and `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json`
   (`45b9b6a8d192` vs disk `64b8d6394a04`) did not match disk; the files were rewritten at
   00:57:02 (delta check re-run 00:57:15). The lead re-froze FROZEN.json at **00:57:26** (still
   revision 29, sha `815e08079aef`); the end-state manifest is clean (50 files, 0 problems) and the
   independent `verify_frozen.py` cross-check returns 0. **Consequence for the r3 round:** accept
   verdicts must bind the `815e08079aef` (00:57:26) manifest, not the `3d9e3d77` (00:55:02) one.
2. **`W088-R13-LFORM03-CARRIED` — the declared L-FORM-03 residual is measured at 2 asserted lines,
   not 4.** The rev29_delta note lists four locations; at the measured bytes only the two
   F0-frozen paths still *assert* the inverted direction:
   `research_map/formulation_taxonomy.yaml:200` ("the set-based reading … is strictly stronger")
   and `artifacts/formulation/formulation_taxonomy.yaml:176` (D1 ledger, "as a SET (strictly
   stronger)"). In `artifacts/formulation/VARIANT_REGISTRY.json:57` and
   `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json:11` the asserted relation
   was corrected to `strictly weaker`; the remaining uppercase `STRONGER` tokens there are
   metalinguistic mentions ("corrected from 'strictly STRONGER'") or the unrelated CH
   past-extension relation at `VARIANT_REGISTRY.json:112` (a different claim, checked correct by
   the author, out of scope for this audit). The two surviving locations are G-F0-frozen, so the
   residual cannot be repaired without voiding G-F0 (`0abb9ed8a961`) and re-running the F0 round —
   it is carried, not introduced by rev13.

## Method / independence

The instrument re-implements the pin check, the structural leaf diff, the scope classifier, the
binding resolution and the residual search from the pinned bytes (`audit_rev13_delta.py`,
sha256 `cd1dc3edc164` at first execution, re-hashed in the manifest). It imports no formulation
checker and uses no author verdict as an input; `check_class_schema.py`, `verify_frozen.py` and
`classsep_regression.py` are run only as recorded cross-checks. The rev12 baselines are the pinned
copies already on disk under `artifacts/worker-088/{f1,f2a,f2b}_review/pinned/`, re-verified
against the declared rev12 hashes before use. Reconnaissance had already read the lead's rev29
delta note, so this is a **scope-conformance test against the declaration, not a blind
open-ended search**; that deviation is disclosed in `report.json#instrument.pre_registration_note`.

The instrument was corrected twice for check bugs found during the audit (a top-level vs nested
`class_contract_pointer` lookup, the `class_identity_variants` key shape, a case-sensitive
residual regex, and `revised_at` bookkeeping classification). The first-run report is preserved as
`report.run1_prerefreeze.json`, which is also the primary evidence for finding 1.

## Falsifier

- a write to any measured rev13 schema or to FROZEN.json after this measurement, or a FROZEN pin
  that no longer matches disk;
- a changed leaf outside revision bookkeeping / `f0_binding` / the `[rev13:]`-annotated F1
  strictness text in the rev12 → rev13 delta;
- `class_contract_pointer` / `class_contract_supplement_pointer` failing to resolve, or
  `consistency_evidence_sha256` ceasing to equal the measured evidence file;
- L-FORM-03 no longer present as an assertion in the two frozen paths;
- a G-FORM r3 verdict bound to the 00:55:02 manifest (`3d9e3d77`) rather than the 00:57:26
  re-freeze (`815e08079aef`).

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-088/rev13_delta_scope/audit_rev13_delta.py   # writes report.json
python3 artifacts/formulation/tools/verify_frozen.py                  # cross-check, expect rc 0
python3 artifacts/formulation/tools/check_class_schema.py --json schemas/af_wcc_vacuum.yaml
```

## Not claimed

No gate verdict, node status, `validation_status` or theorem. No class-semantics judgement beyond
the mechanical protected-leaf guard; the r3 reviewers own the semantics. No claim that L-FORM-03
voids G-FORM — it is carried by two F0-frozen documents, and it is recorded here so the gate
record can cite it at a hash.
