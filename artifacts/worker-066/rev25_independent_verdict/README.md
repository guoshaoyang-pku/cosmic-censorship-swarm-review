# W066-REV25-VERDICT-01 — independent verdict on the rev25 class artifacts

Worker-066, 2026-09-12T00:27:34+08:00. Bound to the pinned byte set in `pinned_manifest.json` (FROZEN revision
25). No canonical artifact was written by this task.

## What was measured

* **Acceptance replication (PASS).** A re-implementation of the two-stage pipeline
  (`run_replica.py`, deliberately not `run_acceptance.py`, which rewrites a frozen evidence file)
  run on pinned copies: 3/3 canonical schemas pass both stages, 2/2 controls pass, union catches
  31/31 mutants (structural 30/31, semantic 11/31). It agrees exactly with
  `artifacts/formulation/evidence/acceptance_pipeline_report.json` at 9b7d6c82.
* **Frozen-manifest audit (PASS).** All 40 files declared by FROZEN
  match disk (0 mismatches) at the pinned revision.
* **Independent cross-checks (4 FAIL).** `crosschecks.py` finds duplicate YAML keys in all three
  schemas (W066-B1), a :157/:244 containment contradiction in F2b (W066-B2), 14 gate-enforced rules
  (R17–R25, R27–R31) missing from the frozen rule spec (W066-B3), alias conclusion tokens plus a
  2-vs-7 variant-set divergence in the declared F0 (W066-B4/B5).

## Verdicts at the pinned hashes

| target | sha256 | verdict | score | hard failures |
|---|---|---|---|---|
| schemas/af_wcc_vacuum.yaml | 9a8bd4c9 | revise | 2.5 | W066-B1 |
| schemas/af_scc_c2_vacuum.yaml | b6123750 | revise | 2.5 | W066-B1 |
| schemas/af_scc_c0_vacuum.yaml | 1bb78ce9 | revise | 2.0 | W066-B1, W066-B2 |
| research_map/formulation_taxonomy.yaml | 276009f4 | revise | 2.5 | W066-B4, W066-B5 |
| artifacts/formulation/rule_spec.json | 40f9bb9e | revise | 1.5 | W066-B3 |

Significance: earlier reviewers of the same artifacts (F1/F2a/F2b-review-22) returned
`inconclusive` because the bytes moved inside their windows. This review binds a byte set that
did not move, so these are the first decisive verdicts at the current hashes.

## Falsifiers

Each finding and verdict carries its own falsifier in `report.json`. The replication claim is
falsified by re-running `run_replica.py` on the same pins and getting a different union-caught
count or a control failure; W066-B1 by `yaml.compose` returning no duplicates; W066-B2 by F2b :157
no longer denying containment; W066-B3 by a v1.3 rule spec declaring R17–R31; W066-B4/B5 by the
canonical F0 carrying canonical tokens and the full 7-variant set.
