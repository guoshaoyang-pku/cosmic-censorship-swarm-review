# Formulation lead lifecycle report — assignment `astra-life02-publish-f0` (F0 only)

- Lead: `astra-lead-formulation`
- Window: 2026-09-12T00:21–00:30+08:00 (wall clock)
- Queue consumed: `comms/inbox/astra-lead-formulation.jsonl` (11 assignments; head = `astra-life02-publish-f0`)
- Outcome: **blocked on a controller adjudication, no destructive write performed**
- Machine evidence: `artifacts/formulation/evidence/f0_mirror_conflict.json#7e3a7bc89a75`

## What the assignment asked

> publish ONE frozen revision so that `research_map/formulation_taxonomy.yaml` and
> `artifacts/formulation/formulation_taxonomy.yaml` are byte-identical, FROZEN.json carries one
> sha256 for that logical artifact, re-emit the canonical artifact event with the canonical sha256,
> stamp `frozen_at` with wall-clock; acceptance = `audit_evidence.py` reports 0 dual-tree findings.

## What was measured

| path | sha256 | bytes | role |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` | `276009f4f63d…` | 35145 | declared F0 taxonomy (worker-01 rev4 + `astra-classscope-02` amendment); F0 node artifact; target of the three schemas' `f0_binding` |
| `artifacts/formulation/formulation_taxonomy.yaml` | `c8e979a1eb48…` | 20937 | class-contract + axis-registry **supplement**; target of the three frozen schemas' `class_contract_pointer` and of `check_taxonomy_consistency.py` |

These are **two different artifacts**, not two trees of one artifact:

- canonical top-level keys include `class_ids`, `classes`, `transfer_rules`, `guards` — and has **no** `class_contracts`;
- the authoring file has `class_contracts`, `axis_registry`, `implication_ledger` — and has **no** `class_ids`/`classes`.

The three frozen schemas (`schemas/af_wcc_vacuum.yaml`, `schemas/af_scc_c2_vacuum.yaml`,
`schemas/af_scc_c0_vacuum.yaml`) each carry
`class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<CLASS>`.
The pinned consistency evidence (`artifacts/formulation/evidence/taxonomy_consistency.json`,
cited by the schemas' `f0_binding`) is the output of `check_taxonomy_consistency.py`, which
requires both key sets (`class_ids`/`classes` from canonical, `class_contracts`/`axis_registry`/
`implication_ledger` from authoring).

## Why byte-identical publication was not executed

- **Canonical → authoring**: the supplement disappears; `check_taxonomy_consistency.py` raises
  `KeyError: 'class_contracts'`, its pinned evidence becomes irreproducible, and the three frozen
  schemas get a dangling class-core reference — the G-FORM falsifier rejects exactly this on re-review.
- **Authoring → canonical**: the declared F0 taxonomy disappears; the F0 node artifact, the G-F0
  criterion "exactly 4 class ids", the three schemas' `f0_binding` (`declared_f0_sha256: 276009f4`)
  and every existing F0 review binding are invalidated at once.

The assignment's own stop rule ("never hand-merge canonical and authoring bytes — publish one over
the other") makes the only content-preserving unification unavailable, so the correct action is a
controller adjudication, not a destructive write.

## What was done safely

1. `artifacts/formulation/evidence/f0_mirror_conflict.json` — measured proof of the conflict,
   dependency chain, and two costed options.
2. `artifacts/formulation/FROZEN.json` bumped to **rev26** (sha256 `2554e276a0db…`):
   - `frozen_at` corrected from future-dated `00:42` to wall-clock `2026-09-12T00:24:49+08:00` (CF-14);
   - explicit `logical_artifacts` block declaring the two F0 artifacts and that neither is the
     other's mirror;
   - `f0_mirror_adjudication_request` pointing at the evidence;
   - no frozen artifact bytes were changed; `verify_frozen.py` = 40 files, 0 problems.
3. Canonical F0 artifact event re-emitted with the measured canonical sha256, stating explicitly
   that the F0 accept recorded at `565a6e505188` is **superseded by `276009f4`** and must be
   re-reviewed at the new hash.
4. Audit re-run: `validate_map.py` = VALID; `audit_evidence.py` = 1 soft dual-tree finding (the F0
   pair above) + 1 hard CLASSSEP already adjudicated as the CF-16 checker false positive.

## Requested adjudication (controller)

- **REC-1 (preferred if zero artifact churn is wanted):** declare the F0 pair a *companion* pair,
  not a mirror pair; add a documented exception to `MIRRORS` in `research_map/audit_evidence.py`
  (the supplement is load-bearing for the frozen schemas). Effect: 0 dual-tree findings, no frozen
  bytes change, no review round lost.
- **REC-2 (durable):** bounded re-freeze — publish the supplement as its own canonical artifact,
  publish the declared F0 byte-identically to the authoring mirror path, refresh
  `class_contract_pointer` + `f0_binding` in the three schemas, repoint
  `check_taxonomy_consistency.py`, regenerate FROZEN, re-dispatch F0 + F1/F2a/F2b reviewers.
  Cost ≈ 3–4 agent-hours + one review round (no accept verdict is lost: 0 accepts bind the current
  schema hashes).

## Residual blockers (not formulation-side)

- No independent verdict binds the current G-FORM hashes `9a8bd4c9` / `b6123750` / `1bb78ce9`
  or the declared-F0 hash `276009f4` (see `leadform-blocker-0006`).
- `f0_binding.checked_at` in the three frozen schemas reads `00:30` (future-dated at write time, CF-14).
