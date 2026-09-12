# N1 lock-guard repair cross-check — canonical vs. two competing candidates

**Task** `W050-LOCKGUARD-CANDIDATE-CROSSCHECK-05` · **worker-050** · class `AF-WCC-SCALAR-SPH`
· node `N1-BLOCK` · gate `G-NUM` · authority: worker measurement only (no gate verdict, no node
status, no canonical file edited).

Measured `2026-09-12T01:01:36+0800` over a 23-row pre-registered battery; every subject and
context hash re-measured before and after the run, no drift. Full row-level data: `report.json`.
Battery definition (pre-registered in code, hash-pinned): `crosscheck.py#a8cbb281a80e…`. The live
map was measured at `f344ed2aaea5…` at run time (recorded in `report.json`; it is live traffic).

| subject | path | sha256 |
|---|---|---|
| canonical rev1 | `numerics/tests/selfgravity_lock_guard.py` | `7535ec84ac9c…` |
| candidate A (flash-15 rev2) | `artifacts/flash-15/n1_guard_failclosed/repaired_proposal.selfgravity_lock_guard.py` | `bbc5f363d2f8…` |
| candidate B (worker-012) | `artifacts/worker-012/n0/lockguard_failclosed/guard_candidate.py` | `0b72a9871b56…` |
| interlock module (context) | `numerics/gates.py` | `fcd1d70991b6…` |
| lock contract (context) | `numerics/blockers.md` | `d396b609d81d…` |

Reproducibility: a second run at the same subject hashes reproduced `report.json` field-for-field
except `measured_at` (deterministic fixture root + normalized raw tails; checked at 01:01).

## Why this run exists

Three independent measurements already agree the canonical guard fails open (worker-074
`W074-F3`; deepseek-flash-15 `W015-N1-GUARD-FAILCLOSED-01`; worker-012
`W012-LOCKGUARD-FAILCLOSED-01`). Two **different** repairs were filed and neither was ever run
against the other. The canonical guard is still the defective revision and the numerics lead has
exited. This run puts both repairs on one battery, black-box (subprocess `--root`), and scores four
properties fixed before measurement.

Property definitions (as pre-registered):
- **P1 literal-assignment** — no `PASS`/exit 0 while `state == "locked"` (exact) and an N1+
  artifact (planted solver dir or declared transitive artifact) is present.
- **P2 strict-release** — no `PASS`/exit 0 while an artifact is present and the state token is
  anything other than the exact literal `released` (P2 total = P1 witnesses ∪ release-surface
  spellings).
- **P3 no blind certification** — an unparseable/absent state with no artifact must not be
  certified `PASS`.
- **P4 non-vacuous lock** — `state == "locked"` with empty/missing `locked_nodes` must not `PASS`
  when a declared transitive N1+ artifact is present.

## Four-property scorecard

| property | canonical `7535ec84` | A / flash-15 `bbc5f363` | B / worker-012 `0b72a987` |
|---|---|---|---|
| **P1** witnesses | **11** (10 fail-open + vacuous-lock row) | 0 | **1** (vacuous-lock row) |
| **P2** total witnesses | **13** | **2** | **1** |
| **P3** blind certification | **FAILS** (`unknown_state_clean`) | pass | **FAILS** (`unknown_state_clean`) |
| **P4** vacuous lock | **FAILS** | pass | **FAILS** |
| definite-row mismatches | 11 | **0** | **1** |
| `--self-test` exit | 0 | 0 | 0 |
| live tree (lock `locked`, solver absent) | PASS/0 | PASS/0, `lock_enforced:true` | PASS/0 |

P1/P2 witnesses (canonical): `locked_whitespace_solver`, `locked_miscased_Locked_solver`,
`locked_miscased_LOCKED_solver`, `lock_block_absent_solver`, `lock_null_solver`,
`state_null_solver`, `state_empty_solver`, `state_key_missing_solver`,
`state_unknown_frozen_solver`, `state_nonstring_123_solver`,
`vacuous_nodes_empty_declared_n2`; plus the release-surface spellings
`state_unlocked_solver`, `state_miscased_Released_solver`. Each returns `PASS`/exit 0 with a
planted `numerics/spherical_solver/` or declared `numerics/results/n2.json` on disk.

## Head-to-head: every row where the three revisions or `gates.py` disagree

| fixture (pre-registered) | canonical | A (flash-15) | B (worker-012) | `gates.py` state criterion |
|---|---|---|---|---|
| `locked_clean` / `locked_solver_dir` / `locked_declared_n2` | PASS, FAIL, FAIL | same | same | locked |
| `locked_whitespace_solver` | **PASS/0** | FAIL/1 | FAIL/1 | released |
| `locked_miscased_Locked_solver` / `…LOCKED_solver` | **PASS/0** | FAIL/1 | FAIL/1 | released |
| `lock_block_absent_solver` | **PASS/0** | ERROR/2 | FAIL/1 | locked |
| `lock_null_solver` | **PASS/0** | ERROR/2 | FAIL/1 | locked |
| `state_null_solver` / `state_empty_solver` / `state_nonstring_123_solver` | **PASS/0** | ERROR/2 | FAIL/1 | released |
| `state_key_missing_solver` / `state_unknown_frozen_solver` | **PASS/0** | ERROR/2 | FAIL/1 | locked / released |
| `state_unlocked_solver` | **PASS/0** | **PASS/0** (released) | FAIL/1 | released |
| `state_miscased_Released_solver` | **PASS/0** | **PASS/0** (released) | FAIL/1 | released |
| `vacuous_nodes_empty_declared_n2` (locked, `locked_nodes: []`) | **PASS/0** | ERROR/2 | **PASS/0** | locked |
| `unknown_state_clean` (no artifact) | **PASS/0** | ERROR/2 | **PASS/0** | released |
| `vacuous_nodes_empty_solver` | FAIL/1 | ERROR/2 | FAIL/1 | locked |
| `locked_nodes_null_solver` | ERROR/2 | ERROR/2 | ERROR/2 | locked |
| `locked_nodes_missing_solver` | FAIL/1 | ERROR/2 | FAIL/1 | locked |
| `released_exact_solver_dir` / `released_exact_clean` | PASS/0 | PASS/0 (`lock_enforced:false`) | PASS/0 | released |
| `map_malformed_json` | ERROR/2 | ERROR/2 | ERROR/2 | probe raises (fail-closed) |

`gates.py` column = whether `numerics_lock.state == "locked"` appears among `blocking_reasons`
from the live module at `fcd1d70991b6` on the same fixture root; it isolates the state criterion
only — `gates.py` also requires G-FORM/G-AUDIT/N0/protocol, so production stays blocked today.

## Findings

- **W050-LG-1 (major, canonical).** `selfgravity_lock_guard.py#7535ec84ac9c` fails open for every
  lock-state spelling except the exact literal `locked`, for an absent/null `numerics_lock` block,
  and for a `locked` lock with empty `locked_nodes`: 11/11 such rows return `PASS`/exit 0 with an
  N1+ artifact present. Independently reproduces `W074-F3` / `W015-N1-GUARD-FAILCLOSED-01` /
  `W012-LOCKGUARD-FAILCLOSED-01` at the still-live hash. The assignment's own acceptance falsifier
  ("test fails if `numerics/spherical_solver/` exists … while `numerics_lock.state==locked`")
  fires at the current bytes.
- **W050-LG-2 (major, candidate A).** A normalizes the state token and then accepts
  `{"released","unlocked"}` as released (`str(state).strip().lower()` membership test). With a
  planted solver, `state:"unlocked"` and `state:"Released"` both return `PASS`/exit 0 — 2 P2
  witnesses. Normalizing case is right for the *locked* token and wrong for the *release* token.
- **W050-LG-3 (major, candidate B).** B has the narrowest release surface (exact `released`; 0 P2
  release-surface witnesses), but it fails **P1** on `vacuous_nodes_empty_declared_n2`: state is
  exactly `"locked"`, a declared transitive N1+ artifact exists, and B returns `PASS`/exit 0
  because `locked_nodes: []` makes the blocked set empty and only the explicit solver path is
  checked. B also fails **P3**: an unparseable state with no artifact (`unknown_state_clean`) is
  certified `PASS`/exit 0 rather than refused.
- **W050-LG-4 (minor, all revisions + `gates.py`).** There is no single release-surface contract.
  Canonical and `numerics/gates.py` treat *any* spelling other than `locked` as released; A adds
  `unlocked` plus case tolerance; B requires exact `released`. The guard and the module that
  actually gates production must share one definition, or a map edit can satisfy one while the
  other still certifies.
- **W050-LG-5 (minor, provenance).** B reports no `lock_enforced`/revision field, so a
  released-state PASS is indistinguishable from an enforced clean PASS without re-reading the map;
  A reports `lock_enforced` and `guard_revision` and maps `ERROR → exit 2` in `main()` (B has no
  ERROR path of its own).

## Recommendation (for the N1-BLOCK / G-NUM repair owner)

**Adopt neither candidate verbatim; merge A's control flow with B's release surface and B's
diagnostic fields.** Resulting semantics, which is the only combination in the battery with zero
P1–P4 witnesses:

```
raw  = numerics_lock["state"] if the block is a non-empty dict and the key exists else <absent>
norm = str(raw).strip().lower()
LOCKED   = {"locked"}                  -> enforce; violations decide FAIL/1 vs PASS/0
RELEASED = only when raw == "released" -> PASS/0 with lock_enforced=false (exact, case-sensitive)
anything else (absent, null, "", unknown, non-string, case variants, "unlocked") -> ERROR/exit 2,
     reporting the raw value
locked with empty/missing locked_nodes -> ERROR/exit 2 (do not let an empty seed set be vacuous)
main(): FAIL -> 1, ERROR -> 2, PASS -> 0
keep: numerics_lock_state_raw, state_key_present, state_recognised, guard_revision,
      declared_artifacts_checked, explicit_forbidden_checked, violations
```

Rationale: the two error directions are asymmetric. A false non-release blocks the numerics
program (cheap, recoverable); a false release lets self-gravitating code run under a lock
(irreversible). Where the candidates disagree, take the stricter reading. The merge changes
nothing on the live tree: all three revisions already return PASS/0 there (A with
`lock_enforced:true`), and `numerics/spherical_solver/` is absent.

Separately owned: align `numerics/gates.py`'s state criterion (`== "locked"` at the pinned hash)
with the same release surface, or record explicitly that guard state semantics are subordinate to
`gates.py`'s other blocking criteria.

## Falsifiers

- **F1** — a re-run of `crosscheck.py` at the same subject hashes that does not reproduce the row
  table (or that exits 3 on hash drift) voids this measurement.
- **F2** — a witness row above that a re-run shows returning `PASS`/exit 0 for a *different*
  revision than recorded (e.g. a repaired canonical guard landing) voids that row or the table.
- **F3** — any canonical byte hash (`selfgravity_lock_guard.py`, `gates.py`, `blockers.md`, map)
  changing across the run voids the affected comparison; the run records before/after and fails
  closed with exit 3.
- **F4** — a merged repair that returns `PASS` for any P1/P2 row, or `PASS` for a `locked` +
  empty-`locked_nodes` + declared-artifact row, falsifies the recommendation.

## Scope limits

Black-box guard semantics only. No physics, no N0 order claim, no adjudication of the protocol
contest. `numerics/spherical_solver/` was never created outside a temp root; no canonical file was
edited; this is not a gate verdict and cannot set node status.
