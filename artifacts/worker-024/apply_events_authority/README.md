# W024-APPLY-EVENTS-AUTHORITY-01 — authority-enforcement matrix for `research_map/apply_events.py`

- **task_id** `W024-APPLY-EVENTS-AUTHORITY-01` · **node** `A1` · **gate** `G-AUDIT`
- **class_ids** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`
- **actor** `worker-024` · **created** 2026-09-12 (CST)
- **authority note** worker report only: no gate verdict, no node transition, no
  `validation_status=passed`, no canonical file written. The patch below is a **proposal**
  verified on sandbox copies only.

## Revision pins

| artifact | sha256 (measured) |
|---|---|
| `research_map/apply_events.py` | `42d04bd3d5ff769a00a1fed65dda0604363ef1efc526c76fcce0f5b933167572` |
| `research_map/comms.py` | `7e905012ad6b8007f7fc2131a2ce0f35abae13d4205f15f8acd00ad9ff3ce724` |
| `research_map/schemas.py` | `75214a75353b9cd16952958c4711896a46f1f1bda1529622441f14eacf04003b` |
| `research_map/validate_map.py` | `aa4bd61c55cbb0361f56626888bfd722a03d0cb98addec8b63d67114b91ed211` |
| `research_map/research_map.json` | `f06d40a8226a1f5f5a1262bb60b97028a62db4b3766f0b3c3dee565879b0fe1f` |

The live controller repaired `apply_events.py` **during this audit** (`16820bf206b7` →
`42d04bd3d5ff`, pass-05 CF-25). Both revisions were measured; all inputs were re-hashed after
the matrix and `pins_stable=true`, `revision_drift_during_run=false` for the final run.

- prior-revision report: `report.rev-16820bf206b7.json`
  (sha256 `90214323a14a3045b52854f82f112b47f0069f1bc9ad013c5f0dc7d59f4f8b26`)

## Claim (instrument claim, not a class-semantics claim)

At `research_map/apply_events.py#42d04bd3d5ff`, **authority is a self-declared string**. The
only test is `actor in AUTHORITY` (`apply_events.py:27`); `comms.ingest` merely *defaults*
`actor` to the outbox filename when absent (`comms.py:307`) and never binds a declared actor to
its source. Therefore any process able to write a file under `comms/outbox/` can:

1. **forge** authority by declaring `"actor": "astra"` / `"astra-lead-audit"` in its own
   `worker-*` outbox file (F1, F2, F3, F12);
2. move state on event types that have **no actor check at all** — resource-request decisions,
   `kill`/`revive`, `budget`, `direction_update`, `assignment` (F4–F8);
3. write **arbitrary status** on any node that is not `done` (F10; the `done` case F9 is
   repaired by the live CF-25 guard, see below);
4. have `apply_events` **write a map that its own `validate_map` calls invalid** (F11, F13):
   `errs` is computed at `apply_events.py:407` and ignored before the atomic write at
   `:424`.

Measured at the current revision: **12 of 13 authority probes reproduce** (F9 clean), **5 of 5
controls behave**, no harness rejections. At the prior revision `16820bf206b7` **13 of 13
reproduced**.

## Method

Every case runs the real production pipeline end-to-end inside a disposable sandbox under this
directory:

```
comms/outbox/<source>.jsonl      # the attacker's own file (e.g. worker-024.jsonl)
  -> python3 research_map/comms.py ingest
  -> research_map/events.jsonl
  -> python3 research_map/apply_events.py
  -> sandbox research_map.json     # inspected per case
```

The sandbox is a byte-identical copy of the five canonical modules plus the canonical map;
`schemas/ ledger/ numerics/ reviews/ evaluation/` are read-only symlinks so on-disk artifact
checks resolve. **The canonical tree is never written.** Each case is isolated by rebuilding
the sandbox from `sandbox_pristine/`.

Controls calibrate the matrix: C1–C3 are raw undeclared-worker probes that the existing guards
*do* stop; C4 is the intended authority path on a properly provisioned node; H1 is a no-event
healthy run. A case is only counted as a finding if its event was schema-accepted and applied
through the real pipeline (`harness_rejected_events: []`).

## Results at `apply_events.py#42d04bd3d5ff`

| id | kind | authority moved? | observed |
|---|---|---|---|
| F1 | forged_authority | **YES** | `F1.status=done` (source `worker-024.jsonl`, declared actor `astra`) |
| F2 | forged_authority | **YES** | `G-FORM.verdict=pass` |
| F3 | forged_authority | **YES** | `F1.validation_status=passed` |
| F4 | unchecked_event | **YES** | resource request self-approved; `decision_by` hardcoded `astra` |
| F5 | unchecked_event | **YES** | `N0.status=killed` by a worker |
| F6 | unchecked_event | **YES** | `numerics.budget` 320 → 420 by a worker |
| F7 | unchecked_event | **YES** | `audit.direction` rewritten by a worker |
| F8 | unchecked_event | **YES** | worker self-assignment appended |
| F9 | status_scope | no | `F1.status=done` — **repaired by live CF-25 guard** (`:260`); was YES at `16820bf206b7` |
| F10 | status_scope | **YES** | `L0.status=blocked` by a worker (no ownership, no terminal-state guard) |
| F11 | write_integrity | **YES** | duplicate-node map: `rc=0`, `map_errors=1`, event applied and written |
| F12 | provenance | **YES** | well-formed forged event carries **no `_source_file`** (canonical `comms.py:282-284` records it only when normalization filled a field) |
| F13 | write_integrity | **YES** | authority `status=done` leaves `done node has no evidence_refs`; map still written (`rc=0`) |
| C1 | control_guard | no | raw worker `done` → `F1.status=active` + completion claim |
| C2 | control_guard | no | raw worker gate → `G-FORM.verdict=pending` + proposal |
| C3 | control_guard | no | raw worker `passed` → `F1.validation_status=unverified` |
| C4 | control_happy | no | `astra.jsonl`/`astra` on a backed node → `F1.status=done` |
| H1 | control_healthy | no | no events → `rc=0`, no map errors, no demotions |

## Mechanism (current revision)

- `apply_events.py:27` — `AUTHORITY` is a set of name strings; the only authority test.
- `comms.py:307` — `doc.setdefault("actor", path.stem)`: a *default*, not a binding.
- `comms.py:282-284` — `_source_file` is written only `if filled` (F12 blind spot).
- `apply_events.py:241,249` — `done` promotion keyed on the actor string.
- `apply_events.py:279` — resource-request decisions keyed on a **summary substring**, no actor
  check, `decision_by="astra"` hardcoded.
- `apply_events.py:341/353/363/368/375` — `gate`, `direction_update`, `budget`, `assignment`,
  `kill`/`revive` have **no actor check**.
- `apply_events.py:407,424` — `validate_map` errors are reported but do not block the write.

## Live CF-25 repair (noted, not claimed as mine)

The pass-05 controller inserted `apply_events.py:256-264`: a non-authority status event can no
longer demote a node whose status is `done`. This closes F9 on the live revision. It does not
close F1–F3 or F10 (the guard is keyed on the node being `done` and still trusts the actor
string), nor any of F4–F8, F11–F13.

## Proposed patch (proposal only)

`proposed_authority_patch.diff` (195 lines, 10 hunks) + verified copies in `patched/`:

1. `comms.ingest` binds `actor` to the source file stem (or an explicit controller-registered
   alias); a mismatch is preserved as `actor_claimed`, the effective actor is downgraded to
   `unattributed:<stem>`, and `_source_file` is **always** recorded.
2. `apply_events` gains `is_authority(ev)` = actor ∈ AUTHORITY **and** a matching source role
   **and** no `actor_claimed`. It gates `done`/`passed`, gate verdicts, resource-request
   decisions, `kill`/`revive`, `budget`, `direction_update`, `assignment`.
3. Status writes require authority or assignee; terminal nodes are protected (CF-25 retained).
4. `main()` **refuses to write** when `validate_map` reports errors, exits non-zero, and adds
   `--force` as the explicit override.

Verified on sandbox copies at the pinned revision: **all 12 open probes close, C1–C4/H1 still
behave** (`patch_verification.still_violated: []`, `controls_ok: true`). The F13 refusal also
fixes the "promotion produces an invalid map" pathway.

## Falsifier

Re-run `python3 drive_authority_matrix.py` (fresh sandbox) at
`apply_events.py#42d04bd3d5ff`:

- the claim is **falsified** if any of F1–F8, F10–F13 fails to reproduce (no authority-state
  move) or if any control C1–C4/H1 deviates;
- the patch claim is **falsified** if any non-control case still violates, or any control
  breaks, under `patched/`.

If the live revision moves again, the run re-pins and (on mid-run drift) re-measures and records
both pins under `drift_recheck`.

## Reproduction

```bash
cd artifacts/worker-024/apply_events_authority
python3 drive_authority_matrix.py            # ~8 s; writes report.json
python3 -c "import json;r=json.load(open('report.json'));print(r['summary'], r['patch_verification'])"
```

## Limits / residual risk

- The sandbox writes the outbox file directly, then uses the real `comms.py ingest` and
  `apply_events.py`; it does not exercise an OS-level write-permission boundary (there is none
  in the swarm: every agent writes its own outbox file).
- The alias map in the patch (`lead-literature.events`) is illustrative; the controller must
  decide the authoritative source list before adopting it.
- `apply_events.py` is a moving target (patched twice today); the claim is bound to the two
  measured hashes above.
- No class-semantics claim is made, and no gate verdict is asserted.
