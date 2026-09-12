# W078-F1-REPAIR-VERIFY-01 — independent verification of the F1 rev12 repair

**Worker:** worker-078 (authored no F0/F1/F2a/F2b artifact and no part of the repair under test)
**Node / class / gate:** F1 / `AF-WCC-VAC-GEN` / G-FORM
**Pin (pinned snapshot, never re-read):**
`cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3`
(`schemas/af_wcc_vacuum.yaml` rev12, written 2026-09-12T00:32:02+08:00; snapshot at
`snapshot/af_wcc_vacuum.cce9c60146d6.yaml`)

## Why this task

F1 rev12 landed at 00:32 and was unreviewed. It claims to close the hash-bound findings of
`astra-life03-close-findings`, including **HF-06 / HF-15-1**, the critical quantifier defect this
worker independently confirmed at the superseded hash `9a8bd4c96800`
(`artifacts/worker-078/f1_quantifier_adjudication/`, verdict revise): `quantifiers.formal` and D5
used whole-curve single-q containment while the class's canonical visibility predicate is
tail-based, so the formal statement was strictly weaker than the conclusion it expands.

## Method

Pin → byte-exact snapshot → 21 deterministic checks → end-of-run drift re-measure → test-retest.
The verdict binds to the **snapshot**; live canonical and authoring mirror are re-measured at the
end of the run and drift voids the binding to the live path, not the verdict on pinned bytes.

The decisive feature is the **positive control (R18)**: the same core predicates are run against
the archived defective snapshot `9a8bd4c96800`. They must classify it DEFECT (no tail form,
whole-curve form present). Without that discrimination the repair verdict is void. The control
initially exposed three detector-regex bugs (bare `gamma subset J^-(q)` in the old bytes, the
"is [NOT] contained in" phrasing, and case); the detectors were corrected against both documents
and the control now discriminates. The reported run is the post-fix run; the incident is recorded
in the checkpoint `detector_provenance` block.

## Result — verdict `revise`, score 3.0, 20/21 checks pass

Verified as repaired at the pinned bytes:

| repair | check | evidence |
|---|---|---|
| `quantifiers.formal` negative clause is single-q **tail** containment, no whole-curve clause | R06 PASS | `schemas/af_wcc_vacuum.yaml:47` |
| D5 is the `(q,t0)` tail predicate and explicitly excludes whole-curve containment | R07 PASS | `:71-73` |
| `quantifiers.negation` negates the tail predicate ("has a tail visible from I+") | R08 PASS | `:80` |
| canonical visibility definition + negation both tail-based, whole-curve warning retained | R09 PASS | `:213-215` |
| `conclusion.statement_formal` expands the tail-predicate negation | R10 PASS | `:244` |
| ordered prefix `not_exists` over the D5 pair `(q,t0)` | R11 PASS | `:54` |
| duplicate `revised_at` keys collapsed into `revision_history` | R03 PASS | strict `yaml.compose` walk, 0 duplicates |
| no future-dated machine timestamp | R04 PASS | revised_at `00:31:41` ≤ measurement clock |
| `class_contract_pointer` → canonical `classes.…` + separate supplement pointer | R15/R16 PASS | both resolve at measured F0 hashes |
| `AF_{I+}` defined in-schema | R12 PASS | `:193 predicate_abbreviation` |
| D0 retyped as a tagged regularity index; no `(s,delta)` binder survives | R13 PASS | `:56-57`, 0 occurrences |
| declared F0 hash equals the measured canonical taxonomy hash and F0 was stable across the window | R14/R19 PASS | `0abb9ed8a961…` |
| single class id, no composite C0/C2 merge, canonical class-separation helper clean | R05 PASS | `class_separation.findings_for_text` → 0 findings |

**The one hard failure (why this is not an accept):**

- **R17 — declared consistency evidence hash no longer resolves.**
  `f0_binding.consistency_evidence_sha256 = 675a99d0d25b…` but
  `artifacts/formulation/evidence/taxonomy_consistency.json` now measures `9e335e9ba1bf…`
  (file mtime 00:34:55, i.e. regenerated **after** F1 rev12 was written at 00:31:41; observed
  rewritten twice during the window). The schema's own binding rule requires the consistency
  check to be re-run and the binding refreshed before any gate verdict. Repair is a one-line
  hash refresh / re-run, not a re-repair of the quantifiers.

## Control

`R18 PASS` — on `9a8bd4c96800` the same detectors return `tail=False whole=True d5_tail=False
neg_tail=False` (DEFECT), and on `cce9c60146d6` they return the repaired profile. The detectors
therefore separate the two revisions; the repair is not an artifact of a detector that always
passes.

## Retest

`report.json` (run 1) and `report_rerun.json` (run 2) have identical check statuses, identical
labels/evidence and identical verdict `revise`; `retest_compare.json` records the comparison.
Determinism is at the check level; wall-clock fields differ by design.

## Evidence hashes

- pin / snapshot: `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3`
- `verify_f1_repair.py`: see the artifact event (hash recorded there and in the checkpoint)
- `report.json`, `report_rerun.json`, `retest_compare.json`, `README.md`: hashes recorded in the
  emitted artifact events and in `runtime/state/w078_checkpoint_3_f1_repair_verify.json`
- canonical F0 at verification: `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`
- superseded defective baseline: `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503`

## Limits (non-claims)

Structural / contract / semantic-form verification at one pinned hash only. No truth,
non-vacuity, physical-correctness or citation-support verdict. The residual
`schemas/f1_falsifier_tests.jsonl` rebinding (worker-15 F-15-5) and the UNVERIFIED
`class_identity_variants` SET-equivalence remain open and are not assessed here. This is a worker
review: it sets no gate verdict and no node status.

## Falsifiers

1. Re-measure `schemas/af_wcc_vacuum.yaml`: a sha256 other than the pin voids the binding (a
   later revision supersedes, does not refute, this verdict).
2. At the pinned bytes: exhibit a whole-curve clause in `quantifiers.formal`/D5, or show the
   formal no longer expands `not exists visible_singularity_from_I_plus`, or show R18
   non-discriminating on `9a8bd4c96800` — any of these falsifies the repair verdict.
3. Refresh `consistency_evidence_sha256` and re-measure: a new revision whose declared evidence
   hash resolves falsifies the sole hard failure R17 and clears the path to re-review.
