# W089-F1-REV13-REVIEW-05 — controlled review of F1 (AF-WCC-VAC-GEN) rev13

**Verdict: accept (score 4.0) — worker evidence only, not a gate verdict.**
Task taken because the audit lead's `astra-life05-verify-gform-r3` scope (F1,F2a,F2b) needs
independent verdicts at the post-repair pins and worker-089 had no F1 verdict.

## Pins (byte-exact snapshots under `pinned/`)

| artifact | sha256 | notes |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` | stable since 00:53:40; mirror byte-identical |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` | frozen_at 2026-09-12T00:57:26+08:00 |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | untouched |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` | separate artifact, not a competing F0 |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` | consistent=true, errors=[] |
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03` | 37/37 records bound to declared F0 rev5 |

## Machine checks (16/16 pass) and controls (16/16 planted defects caught)

| check | status | detail |
|---|---|---|
| C01_duplicate_keys | pass | no duplicate top-level keys or revision-history indices |
| C02_revised_at_wall_clock | pass | revised_at is wall-clock and mtime-consistent |
| C03_revision_history | pass | revision 13 with a used, rev13-labelled history tail |
| C04_frozen_pin | pass | FROZEN rev29 pins the measured target and its byte-identical mirror |
| C05_bindchain | pass | all 50 declared files resolve; no self-reference |
| C06_class_identity | pass | class identity is AF/WCC/VAC/GEN with WCC scope |
| C07_contract_pointers | pass | canonical/supplement pointers resolve in exactly one file each |
| C08_f0_binding | pass | f0_binding resolves to live declared-F0 and consistent evidence |
| C09_quantifiers | pass | quantifier chain well-typed and ordered |
| C10_conclusion_typing | pass | conclusion is typed WCC with no SCC/all-data leakage |
| C11_equivalence_unverified | pass | predictability equivalence is marked UNVERIFIED and tracked |
| C12_strictness_repair | pass | rev13 strictness direction corrected (tail==whole; SET strictly weaker) |
| C13_genericity_alias | pass | genericity kind matches the frozen canonical token via the alias policy |
| C14_falsifier_decidable | pass | falsifier is tiered and cites decidable machine steps |
| C15_ledger_status | pass | ledger record D-001 with non-transfer warning and tier-2-only counterexamples |
| C16_class_separation | pass | antis-scope names both SCC classes and forbids composite regularity |

Controls (one planted defect per check, in-memory, baseline must pass first):
`{"C01_duplicate_keys": true, "C02_revised_at_wall_clock": true, "C03_revision_history": true, "C04_frozen_pin": true, "C05_bindchain": true, "C06_class_identity": true, "C07_contract_pointers": true, "C08_f0_binding": true, "C09_quantifiers": true, "C10_conclusion_typing": true, "C11_equivalence_unverified": true, "C12_strictness_repair": true, "C13_genericity_alias": true, "C14_falsifier_decidable": true, "C15_ledger_status": true, "C16_class_separation": true}` — plus a no-false-positive baseline: all 16 checks pass on the
pristine artifact.

## Observations

- **OBS-089-4 (binding churn, non-blocking for the pinned bytes).** FROZEN rev29 was rewritten in
  place inside the same revision (`3d9e3d77` @00:55:02 -> `815e0807` @00:57:26) and
  `evidence/variant_delta_check.json` measured `0b23f0b2` at 00:56:59 against the declared
  `fc6ee058` before being restored by 00:57:15 (see `f1_rev13_report.dryrun.json`, C05).
  `taxonomy_consistency.json` was rewritten at 00:57:00 and 00:59:25 with byte-identical content.
  Final state resolves: all 48 declared files match at the final recheck and F1 was unchanged
  across the review's own 120 s stability window (00:57:50-00:59:52). Bind the manifest hash you
  measured; a verdict citing `3d9e3d77` is void.
- **CHECKER-NOTE-089-2.** Three over-strict predicates (C02 tolerance sign, C12 substring,
  C15 literal token) were corrected after the first dry run; both dry-run reports are preserved
  and hash-registered.

## Scope limits

Mechanical cross-artifact integrity, class identity, quantifier typing, rev13 repair
verification and pin stability only. **NOT** a semantic sufficiency review of weak cosmic
censorship, **NOT** a G-FORM/G-AUDIT gate verdict, **NOT** a node-done event. Assumption
completeness was checked structurally (fields, pointers, quoted tokens), not mathematically.

## Falsifier

Any of C01-C16 flips to fail at a newer canonical hash of `schemas/af_wcc_vacuum.yaml`, or
FROZEN rev29 stops resolving F1/mirror, or a planted control stops being caught, or F1 moves off
`d9cebb9404b2`: this accept is void for the newer revision.

## Re-run

```bash
python3 artifacts/worker-089/f1_rev13_review/check_f1_rev13.py --controls \
  --stability-seconds 120 --stability-interval 10 \
  --json-out artifacts/worker-089/f1_rev13_review/f1_rev13_report.json
```

Checker sha256 `a4e40507da16aabadc68167359b4305f1e1eb276017331362d4acb1639327958`; report sha256 `811772805e653ce56197bedc324559839d46f83cf916f1d90d2cc3f3dbc283e2`;
review record sha256 `9a4bb3f3268cec2b4966a0115a5f14a6890b954e620a8a2a966996456af6a96c`.
