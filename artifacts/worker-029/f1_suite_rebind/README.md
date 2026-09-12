# W029-F1-SUITE-REBIND-01 — F1 falsifier suite binding vs F1 rev13

**One class-bound task.** Node `F1`, class `AF-WCC-VAC-GEN`, gate `G-FORM`.
Read-only worker measurement; no gate verdict, no node status, no canonical byte written.

## Question

`schemas/f1_falsifier_tests.jsonl#56bcb4b3234b` was last rebound at
`2026-09-12T00:32:31+08:00` to F1 **rev12** `cce9c60146d6`. At `00:57:26` FROZEN
revision 29 republished `schemas/af_wcc_vacuum.yaml` at **rev13** `d9cebb9404b2`
with the suite bytes unchanged. Does the suite's own binding still hold, do its
stored probes still re-evaluate, and is the mismatch material?

## Result (verdict: `revise` at this pin)

| check | measured |
|---|---|
| rows bound to live F1 rev13 `d9cebb9404b2` | **0 / 25** |
| rows bound to superseded F1 rev12 `cce9c60146d6` | **25 / 25** |
| `binding_ref` / `binding_frozen_revision_schema` | all `#sha256:cce9c60146d6…` / `12` |
| vendor hard check C1a (`artifacts/flash-04/f1_ambiguity/verify_freeze_current.py:171-176`) | **false** — canonical F1 `d9cebb94` ≠ suite binding `cce9c601` |
| vendor soft check C1b (FROZEN canonical F1 pin == suite binding) | false |
| stored probes re-evaluated against rev13 | 84 total, 84 stored `pass`, **2 recomputed mismatches** |
| mismatch set (identical at rev12 and rev13) | `F1-AMB-25|f0_binding.declared_f0_sha256|equals`, `F1-AMB-25|f0_binding.binding_note|contains` |
| stale `cross_artifact` declaration | 1 — `F1-AMB-25` still declares F0 rev4 `276009f4f63d`; live F0 is `0abb9ed8a961` |
| rev12→rev13 structural delta | 12 leaf paths changed, incl. probed `f0_binding.binding_note` and `visibility.definition` (a deciding field) |

The two probe mismatches pre-date rev13 (they reproduce at the rev12 snapshot and
match worker-032's `artifacts/worker-032/f1amb25/report.json` finding), so the rev13
re-pin did not cause them — but it did leave the whole suite on a superseded binding,
which is exactly what the vendor's own C1a hard check rejects.

## Method and independence

- `check_f1_suite_rebind.py` implements the probe semantics independently
  (`equals` / `contains` / `path_exists` / `nonnull` / `is_none` / `is_true`, with
  `json.dumps` flattening), then evaluates the suite against **both** the live rev13
  bytes and the rev12 snapshot.
- The vendor verifier itself was **not executed**: it rewrites
  `artifacts/flash-04/f1_ambiguity/frozen_current_verification.json`. Its C1a/C1b/C8
  semantics are reproduced here instead and cited by line.
- All inputs are hash-pinned in `pinned/` and re-measured at T1; zero drift. Five
  in-memory controls: binding responsive, probe sensitive, census idempotent,
  malformed path no-crash, unknown kind fail-closed — all pass.
- Mid-task observation (check B0): FROZEN was re-emitted at `00:57:26` **under the
  same revision label 29** with a new hash (`3d9e3d77fd87` → `815e08079aef`); the F1,
  suite and mirror entries are byte-identical across the two emissions, so this
  measurement binds to `815e08079aef`.

## Falsifier

A suite row rebound to the live rev13 sha256 `d9cebb9404b2` (makes C1a true and the
binding finding void); or a re-pin of F1/FROZEN away from the hashes above; or a rev13
probe recomputation with an empty mismatch set while the binding stays stale
(stale-but-harmless). Re-run: `python3 artifacts/worker-029/f1_suite_rebind/check_f1_suite_rebind.py`.

## Deliverables

- `check_f1_suite_rebind.py` — checker, exit 0 on complete measurement, 2 on failed expectation, 3 on pin drift
- `report.json` — full machine-readable report, `measurement_digest` `27722d0f0ce5`
- `pinned/`, `pinned.sha256` — pinned inputs
- `manifest.sha256` — deliverable hashes
