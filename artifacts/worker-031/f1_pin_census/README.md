# W031-F1-PINCENSUS-01 — operative-pin census at the rev28 formulation freeze

Agent: `worker-031` (fleet instance 2026-09-12T00:36:53) · class `AF-WCC-VAC-GEN`
(+ F2a/F2b cross-references) · node `F1` · gate `G-FORM`
Instrument: `census_f1_pins_031.py` · Report: `report.json` · Checkpoint: `CHECKPOINT.json`

## Why this task

The prior worker-031 instance filed a hash-bound blocker that one row of
`schemas/f1_falsifier_tests.jsonl` still asserted a superseded F0 hash. This run asks the
bounded question that remained open: **at the rev28 freeze, is that the only stale
operative pin in the F1-class canonical input set, or is the defect set larger?** The answer
matters to G-FORM disposition: it decides between a 4-field re-pin and a broader re-freeze.

## Method

An operative pin is a `(path, sha256)` pair whose stated role is to decide a gate question.
The instrument censuses:

1. all 25 rows of `schemas/f1_falsifier_tests.jsonl` — `binding_ref`/`binding_sha256`,
   `cross_artifact[]`, and deciding-field hash expectations;
2. all three schemas' `f0_binding` — `declared_f0_{artifact,sha256}` and
   `consistency_evidence{,_sha256}`, plus supplement-pointer existence;
3. `schemas/taxonomy_cases.jsonl` `meta.taxonomy_ref`;
4. `artifacts/formulation/FROZEN.json` rev28 — all 44 file pins, both `logical_artifacts`
   pins, the three schema mirror pairs, and the F0 companion pair.

Hash-bearing fields that are explicitly historical (`evidence_refs`, `prior_binding_*`,
`binding_at_authoring`, `schema_snapshot`, `delta_vs_*`) are recorded as provenance and are
never counted as defects. The suite's 84 recorded probe outcomes are also recomputed against
the pinned F1 document (6 probe kinds supported).

Controls K1–K5: live pin accepted, fabricated hash rejected, byte-flip + doc-mutation
sensitivity, classification of the known F1-AMB-25 pair, and exact replay of all recorded
probe outcomes on rows whose pins are all live. All five pass.

## Result — `REVISE_REQUIRED` (measurement recommendation, not a gate verdict)

Pins: suite `56bcb4b3234b`, F1 `cce9c60146d6`, F0 `0abb9ed8a961`, F2a `5476a3f2c6bc`,
F2b `55d0a1ea9bda`, cases `f0c20b96f76d`, FROZEN rev28 `2f358f6722d9` — all stable across the
run (`inputs_stable_during_run: true`).

**5 stale operative pins in 2 classes:**

| # | where | declared | live |
|---|---|---|---|
| 1 | suite `F1-AMB-25.cross_artifact[0]` | `276009f4f63d` (F0 rev4) | `0abb9ed8a961` (F0 rev5) |
| 2 | suite `F1-AMB-25` deciding probe `f0_binding.declared_f0_sha256` | `276009f4f63d` | `0abb9ed8a961` |
| 3 | `schemas/af_wcc_vacuum.yaml` `f0_binding.consistency_evidence_sha256` | `675a99d0d25b` | `9e335e9ba1bf` |
| 4 | `schemas/af_scc_c2_vacuum.yaml` (same field) | `675a99d0d25b` | `9e335e9ba1bf` |
| 5 | `schemas/af_scc_c0_vacuum.yaml` (same field) | `675a99d0d25b` | `9e335e9ba1bf` |

Recomputed suite census: 84/84 recorded pass → **82/84** reproduce; the two failures are
F1-AMB-25's deciding equality probe and its `binding_note` corroborator. Both stale tokens
resolve to real on-disk snapshots (`276009f4` → worker-060/007/061 snapshots; `675a99d0` →
the worker-086 pinned copy), so they are superseded revisions, not typos.

**Everything else is live:** 25/25 row bindings, `taxonomy_cases.meta.taxonomy_ref`, all
three `declared_f0_sha256` (fresh), FROZEN rev28 44/44 file pins (0 drift), both logical
pins, 3/3 schema mirror pairs byte-identical, and the F0 companion pair correctly
non-identical per REC-3. The defect set is bounded to the 5 pins above.

## Prior reporting (honest crosswalk)

Both defect classes were already reported by other agents before this run —
F1-AMB-25 by the previous `worker-031` instance
(`comms/outbox/worker-031.jsonl#w031-f1-rebind-blocker-20260912T003602`), and the
consistency-evidence mismatch by reviewers 090/086/094/278/279/282/287 and map blocker
`groups[0].nodes[1].blockers[27]`. What this report adds is **independent reproduction at a
single frozen pin set plus the bound that no other operative pin is stale**, and the
confirmation that FROZEN rev28 is internally coherent while the frozen schemas it contains
carry the one-regeneration-old evidence citation.

## Falsifier

Any pinned input moving (`inputs_stable_during_run: false`), any of K1–K5 failing, or a
flagged stale pair being shown to be provenance rather than an operative binding, voids the
corresponding finding. The bound claim is void if any additional operative pin is shown to
be stale at these pins.

## Authority

Worker measurement only: no gate verdict, no node status, no `validation_status`, no edit to
any artifact under test. Replay:

```bash
python3 artifacts/worker-031/f1_pin_census/census_f1_pins_031.py
```
