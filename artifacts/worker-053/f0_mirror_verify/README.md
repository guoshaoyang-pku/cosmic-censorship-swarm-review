# W053-F0-MIRROR-VERIFY-01 — independent verification of the F0 mirror-conflict claim

**Worker** worker-053 · **Node** F0 · **Gate** G-F0 · **Classes**
`AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH`

## What was asked

The map's G-F0 unmet list and controller finding CF-13 hold G-F0 at `pending` because the
publication pair `research_map/formulation_taxonomy.yaml` (canonical declared-F0) vs
`artifacts/formulation/formulation_taxonomy.yaml` (authoring) is `divergent`, and the policy
says "the authoring tree must be published byte-identically to it before review verdicts bind."

At 00:24:42 the formulation lead filed
`artifacts/formulation/evidence/f0_mirror_conflict.json` claiming the two paths hold **two
different artifacts** and that a byte-identical publication in either direction is destructive,
with REC-1 (controller pairs-check exception) and REC-2 (bounded re-freeze) as options.

No worker had taken that evidence file. This task verifies it independently, read-only, at one
hash-pinned snapshot.

## Answer (verified)

**The claim is CONFIRMED at the pinned revision** — all 8 checks pass, all 4 planted-defect
controls are caught, input drift guard stable.

| check | result | measured fact |
|---|---|---|
| V1 identities | PASS | canonical `276009f4f63d…` (35145 B), supplement `c8e979a1eb48…` (20937 B) equal both the evidence file and FROZEN.json rev26 |
| V2 two artifacts | PASS | role-key intersection empty; canonical needs `class_ids/classes/transfer_rules/disjointness`, supplement needs `class_contracts/axis_registry/implication_ledger`; each copy direction destroys required keys |
| V3 pointers | PASS | 3/3 `class_contract_pointer` resolve into the supplement and resolve nowhere else; 3/3 `f0_binding.declared_f0_sha256` equal measured canonical bytes |
| V4 dependency proof | PASS | `check_taxonomy_consistency.py` indexes both role-key sets (source tokens verified); this independent re-implementation of its core comparisons reproduces the pinned `consistent: true`, 0 divergences |
| V5 counterfactual | PASS | supplement→canonical loses `class_ids/classes/disjointness/transfer_rules` and dangles 3 pointers; canonical→supplement loses `class_contracts/axis_registry/implication_ledger`, invalidates 3 `f0_binding` records and the 5 F0 reviews pinned to `276009f4` |
| V6 FROZEN rev26 | PASS | 40/40 `files` entries byte-exact; 2/2 `logical_artifacts` byte-exact (two listed evidence files were re-written with identical bytes at 00:29:26, after `frozen_at` 00:24:49 — hash-clean, clock-discipline note only) |
| V7 gate scan | PASS | independent target-normalised scan matches the controller record for F0/F1/F2a/F2b/L0 at the same hashes once post-pass verdict rewrites are classified (0 unexplained deltas) |
| V8 option cost | PASS | REC-1 changes 0 bytes and invalidates 0 reviews; REC-2 changes 3 schema hashes, the FROZEN revision, and invalidates 26 pinned review files |

Current bound full-schema accepts at the measured hashes at snapshot time:
**F0 0, F1 0, F2a 1 (worker-047), F2b 3 (deepseek-flash-17, worker-001, worker-030), L0 1 (worker-011).**
F0/F1 therefore still do not meet the 2-accept criterion for reasons independent of the mirror issue.

## Two findings produced by the control

1. **Controller gate-scan blind spot (falsifiable).** `research_map/astra_lifecycle.py::review_coverage`
   normalises targets only through `TARGET_ALIASES`; a review whose `target_id` is the published
   evidence format `path#sha256` (here `reviews/F2b-review-worker-001.json`, target
   `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357…`, verdict `accept`, mtime 00:20:04) is never
   attached to F2b. Re-running the controller scan in-process reproduces the miss (F2b 2 accepts
   instead of 3). Falsifier: add the path-form target to the normalisation and show the F2b count
   does not change.
2. **Gate reasons decay in minutes.** The controller pass at 00:24:40 recorded F1/F2a/F2b/L0
   accepts that no longer exist: the `astra-lead-audit-r2` reviews were rewritten `accept→revise`
   at 00:25:15 (and `F2b-review-07` at 00:26:33), while worker-011's L0 accept was re-issued at
   00:26:22. Every delta is timestamp-classified in `report.json`; none is a lost verdict.

## What this does not do

No gate verdict, no node transition, no edit to `research_map/`, `schemas/`, `ledger/` or
`artifacts/formulation/`. REC-1 vs REC-2 remains the controller's adjudication; this report only
measures which option preserves the frozen dependency graph.

## Files

| file | role |
|---|---|
| `check_f0_mirror.py` | deterministic stdlib+PyYAML checker; pins 13 inputs before/after; 4 planted-defect controls |
| `report.json` | full machine report: pins, V1–V8, controls, option table, non-claims |
| `controls.json` | planted-defect control results |
| `run.log` | verbatim stdout of the final run |
| `README.md` | this page |

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-053/f0_mirror_verify/check_f0_mirror.py
```

Falsifier (top level): re-run at the same pinned hashes; the conclusion is falsified if any of
V1–V8 fails, if a planted control is not caught, if a pinned input drifts during the run, if any
controller-counted accept at the same measured hash is absent from the independent scan without a
post-pass file mtime, or if any accept the controller scan also finds in-process is missing from
the controller's recorded gate reason.
