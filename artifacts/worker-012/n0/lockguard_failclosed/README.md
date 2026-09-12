# W012-LOCKGUARD-FAILCLOSED-01 — canonical N1 lock guard fails open on malformed lock state

**Worker:** deepseek-flash-12 (slot 012) · **Class:** `AF-WCC-SCALAR-SPH` · **Node:** `N1-BLOCK` · **Gate:** `G-NUM`
**Task:** independent adversarial verification of the unreplicated major finding `W074-F3`
(`artifacts/worker-074/n1_block_audit/report.json`) against `numerics/tests/selfgravity_lock_guard.py`,
plus a byte-minimal repair candidate. Worker evidence only — no gate verdict, no node completion.

## Subject and context (measured at 2026-09-12T00:35+08:00)

| file | sha256 | note |
|---|---|---|
| `numerics/tests/selfgravity_lock_guard.py` | `7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5` | subject; matches the authoring/assignment hash; unchanged by this task |
| `numerics/gates.py` | `fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e` | context; **drifted at 00:31:24** vs the map's recorded `907a88b141bf` — measured live, not assumed |
| `numerics/blockers.md` | `33dd7a21ff56c0be942e634c0a65541efd823e6645db20c92715c9cac31461bb` | "Guard tests (must fail closed)" |

The assignment's own falsifier for this artifact is: **"Guard passes while a self-gravity artifact
exists."** That falsifier fires today.

## Finding (reproduces and widens `W074-F3`, confirmed)

Canonical line 98 is `"verdict": "FAIL" if (state == "locked" and violations) else "PASS"`, and
line 69 is `state = lock.get("state", "unknown")`. Any `numerics_lock.state` that is not exactly
the string `locked` — absent, null, miscased, empty, non-string, or the missing/null
`numerics_lock` object — therefore returns **PASS / exit 0 while a planted
`numerics/spherical_solver/` is present**, with the violation listed but ignored. `numerics/gates.py`
defaults an absent state to `locked` (line 343), so the two guards disagree on malformed maps.

Independent reproduction of worker-074's five recorded fixtures: **5/5 agree** (state missing →
PASS, `LOCKED` → PASS, `locked` → FAIL, clean `locked` → PASS, unreadable map → ERROR exit 2).
The matrix adds six further fail-open witnesses: `Locked`, `" locked"`, `""`, `null`, `123`,
`"unknown"`, `"unlocked"`, and `numerics_lock` absent/null — **11 witnesses total**.

## Repair candidate (proposal only; canonical file untouched)

`guard_candidate.py` (sha256 `0b72a9871b56bc4e3588261bd818b02b9373d5dd6b7e94260f6fa164813528f5`)
changes the **state derivation only**; the verdict expression at line 98 is unchanged:

- absent / null / miscased / non-string / unrecognised state → treated as `locked` (mirrors `gates.py`);
- only the exact string `released` permits a blocked-node artifact to exist;
- output adds `numerics_lock_state_raw`, `state_key_present`, `state_recognised` so a malformed
  map is visible rather than silently normalised.

`diff_canonical_to_candidate.txt` is the exact unified diff: +5 docstring lines, −1/+7 state
derivation lines, +3 report-field lines (15 added / 1 removed total); no other change.

## Matrix result (28 rows, harness exit 0)

| row group | canonical | candidate |
|---|---|---|
| live repo map (state `locked`, no solver) | PASS | PASS |
| `locked` + planted solver (control) | FAIL | FAIL |
| `locked` + clean (control) | PASS | PASS |
| `released` + planted (release semantics preserved) | PASS | PASS |
| map unreadable (control) | ERROR exit 2 | ERROR exit 2 |
| 11 malformed/absent-state rows + planted solver | **PASS — fail-open** | **FAIL** |
| all clean rows across every state | PASS | PASS |
| `--self-test` (clean PASS / planted FAIL) | exit 0 | exit 0 |

Controls: exact canonical bytes copied into every temp fixture (hash checked per run); repository
hashes measured before and after and identical; candidate contract failures = 0.

## Reproduce

```bash
cd artifacts/worker-012/n0/lockguard_failclosed
python3 make_candidate.py     # regenerates guard_candidate.py from the pinned canonical hash
python3 guard_matrix.py       # 28-row matrix; exit 0 iff candidate clean + W074 reproduced + no writes
```

## Falsifier

Reject if any of: (a) the canonical guard at `7535ec84ac9c` fails to reproduce worker-074's five
fixtures; (b) `guard_candidate.py` at its recorded hash does not return FAIL/exit 1 for every
planted-solver fixture whose state is not exactly `released`; (c) it returns PASS for a planted
solver with a non-`released` state; (d) it breaks `--self-test` or the clean rows; (e) any
canonical byte hash changed across the run; (f) a repaired canonical guard lands whose state
handling matches the candidate and the witnesses above no longer reproduce.

**Authority:** repair authority is lead-numerics (`numerics/blockers.md` owner). The canonical
guard was not edited; `numerics/spherical_solver/` was never created in the repository.
