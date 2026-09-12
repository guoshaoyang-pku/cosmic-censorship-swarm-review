# W16-F0-INDEP-REVIEW-01 — independent F0 review at `276009f4f63d`

- **Worker / actor:** `worker-16` (deepseek-flash-16), bounded execution worker
- **Node / gate:** F0 / G-F0
- **Target:** `research_map/formulation_taxonomy.yaml`
- **Bound hash:** `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` (revision 4)
- **Hash cross-checks:** equals `artifacts/formulation/FROZEN.json` revision 25 entry and
  `runtime/state/artifact_hashes.json` F0 entry; stable across two reads; no duplicate YAML keys
- **Verdict:** `revise`, score 3.5
- **Canonical review artifact:** `reviews/F0-review-16.json`
- **Independence:** reviewer authored no part of F0; method is a fail-closed checker plus line-cited
  semantic review. This is a review, not a gate verdict.

## Why this task

The controller gate audit at `2026-09-12T00:19:58+08:00` records for G-F0: *"canonical taxonomy
276009f4f63d; review scan at this hash: 0 distinct accept reviewer(s) [none]; criterion needs two
distinct independent accepts."* No worker in the 00:12/00:16 fleet had claimed an independent
full-schema F0 review (F0 open-case dispositions and index reconciliation are different tasks), so
this task is class-bound, unclaimed, and directly on the gate's critical path.

## Result: 13 PASS / 3 FAIL / 2 NOTE (18 deterministic checks)

Failing checks (blocking findings; exact text quoted in `reviews/F0-review-16.json`):

| id | defect | pinned evidence |
|---|---|---|
| B-16F0-1 | `AF-WCC-SCALAR-SPH` conclusion still uses the set-based `J-(I+)` visibility reading that D1 demoted to variant `SET` and forbade as a second predicate | line 406 vs lines 75, 63-65 |
| B-16F0-2 | D3 records the comeager quantifier as explicit "in each class conclusion text" but the scalar class says only "For generic data in the class" | line 72 vs line 405 |
| B-16F0-3 | C2/C0 `schema_owner` point at `schemas/af_scc_regularities.yaml`, which the map records in `legacy_artifacts` as a non-class aggregator, under the superseded node name `F2` | lines 305, 374 |

Passing checks include: exactly the four frozen class ids; 7/7 axes vocabulary-legal for 4/4
classes; guard G2; 6/6 disjointness pairs with all decisive axes actually differing; conclusion
types never merged; T1 the only allowed transfer and correctly directed C0->C2; guards G1-G7; hash
integrity and timestamp sanity.

Non-blocking notes: `genericity_topology` never instantiated on an axis; `conclusion_type`
identifier overloaded between protocol claims and class vocabulary; `written_at` still dates the
pre-rev4 write.

## Controls (run before believing the FAILs)

- **P1 positive sensitivity** — patching exactly the three defects in a fixture of the pinned bytes
  yields 0 FAIL (16 PASS / 2 NOTE), so the FAILs are attributable to the defects, not over-firing.
- **N1 negative fail-closed** — the checker with a wrong `--pin` exits 2 and writes no results.

Artifacts: `check_f0.py`, `check_results.json`, `controls.json`, `run_controls.py`,
`control_fixture_repaired.yaml` — all under `artifacts/worker-16/f0_review/`.

## Falsifier

Any of B-16F0-1/2/3 is refuted by quoting the pinned bytes to show the attributed reading is absent,
or by showing the `schema_owner` target is canonical (not in map `legacy_artifacts`). The checker is
refuted by a drift-controlled re-run that reports FAIL on the repaired fixture.

## Next bounded step

The formulation lead disposes B-16F0-1/2/3 in one revision, then re-runs `check_f0.py` to 0 FAIL and
requests two accepts at the new hash. Any write to the taxonomy voids this review.
