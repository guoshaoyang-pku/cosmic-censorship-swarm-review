# W015-N1-GUARD-FAILCLOSED-01 — lock-guard fail-open verification + staged fail-closed repair

- **Class**: `AF-WCC-SCALAR-SPH` · **Node**: `N1` · **Gate**: `G-NUM`
- **Worker**: `deepseek-flash-15` (supervisor slot `worker-015`, instance started 2026-09-12T00:30:49+08:00)
- **Task taken**: no unclaimed assignment card existed for this slot; picked one bounded task from
  the live N1/G-NUM queue — the repair half of **W074-F3** (worker-074 audit: lock guard fails open
  on missing/miscased `numerics_lock.state`), which had no repair or independent re-verification.
- **Verdict**: `battery_verdict = PASS`. Revision 1 of the canonical guard reproduces the fail-open
  defect on **7/12** fixtures; the staged revision 2 satisfies all 12 required semantics; both
  revisions return `PASS`/exit 0 on the live tree with `numerics/spherical_solver/` absent.

## What was measured

Canonical target: `numerics/tests/selfgravity_lock_guard.py`
sha256 `7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5` (revision 1, unchanged by
this task). Fixtures are built in throwaway temp roots; no repository file outside
`artifacts/flash-15/` and `comms/outbox/deepseek-flash-15.jsonl` is written.

| fixture | rev1 (canonical) | rev2 (staged) | required |
|---|---|---|---|
| A locked + planted `numerics/spherical_solver/` | FAIL 1 | FAIL 1 | FAIL |
| B locked + declared N2 artifact present | FAIL 1 | FAIL 1 | FAIL |
| C locked + clean (N0 artifact only) | PASS 0 | PASS 0 | PASS |
| D released + planted solver | PASS 0 | PASS 0 | PASS |
| E `state:""` + planted solver | **PASS 0** | ERROR 2 | ERROR |
| F `state:"Locked"` + planted solver | **PASS 0** | FAIL 1 | FAIL |
| G no `numerics_lock` block + planted solver | **PASS 0** | ERROR 2 | ERROR |
| H `state:"frozen"` + planted solver | **PASS 0** | ERROR 2 | ERROR |
| I malformed map JSON | ERROR 2 | ERROR 2 | ERROR |
| J locked, `locked_nodes:[]` + declared N2 artifact | **PASS 0** | ERROR 2 | ERROR |
| K locked, `locked_nodes:[]`, clean | **PASS 0** | ERROR 2 | ERROR |
| L `state:"LOCKED"` + planted solver | **PASS 0** | FAIL 1 | FAIL |
| live tree (read-only) | PASS 0 | PASS 0 | PASS |

Bold = revision-1 fail-open: the guard returns `PASS`/exit 0 while a self-gravitating artifact is
present (in E/F/G/H/L the violation is even listed in its own `violations` array).

## Findings

- **HF-15-G1 (blocking)** — rev1 fails open whenever `numerics_lock.state` is not the exact
  lower-case `"locked"`: absent block, `""`, `"Locked"`, `"LOCKED"`, unknown token. Falsifier:
  run rev1 on a temp root with a planted solver and such a state; void if it does not exit 0/PASS.
- **HF-15-G2 (blocking)** — rev1 certifies a vacuous lock (`state:"locked"`, `locked_nodes:[]`):
  the blocked set is empty, so declared N1+ artifacts reachable through `depends_on` are never
  checked. Falsifier: same with `numerics/results/n2.json` planted; void if rev1 exits non-zero.
- **HF-15-G3 (advisory)** — rev1 `main()` maps any non-`FAIL` verdict to exit 0, so a future
  `ERROR` verdict returned (not raised) would silently pass. Rev2 maps `ERROR → 2`.
- **HF-15-G4 (positive)** — rev2 satisfies all 12 fixtures and the live run; its release semantics
  are preserved and made explicit (`lock_enforced:false`). Falsifier: re-run
  `guard_fixtures.py`; void if any rev2 `(verdict, exit)` differs from the table above.

## Repair

`repaired_proposal.selfgravity_lock_guard.py` — **STAGED, NOT APPLIED** (canonical `numerics/`
paths are lead-owned; this worker will not move a reviewed hash unilaterally). Changes vs rev1:
state normalization + explicit `LOCKED_STATES`/`RELEASED_STATES` allowlists; `ERROR`/exit 2 for an
absent block, empty state, unknown token, or a locked lock with no locked nodes; `main()` maps
`ERROR → 2`; `--self-test` extended accordingly. Live-tree behavior is unchanged
(`PASS`/exit 0).

## Authority and non-claims

Not a gate verdict, not a node transition, not a mathematics or physics claim. Validation status
is `unverified` pending an independent re-run by a non-author. No self-gravitating work was
started; `numerics_lock` remains `locked`.

Rerun: `cd <repo> && python3 artifacts/flash-15/n1_guard_failclosed/guard_fixtures.py`
