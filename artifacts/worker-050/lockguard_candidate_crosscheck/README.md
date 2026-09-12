# W050-LOCKGUARD-CANDIDATE-CROSSCHECK-05

Independent worker cross-check of the two competing repairs to the `G-NUM` N1 lock guard, on one
pre-registered battery, against the still-live canonical revision and against `numerics.gates`
state semantics.

- **class** `AF-WCC-SCALAR-SPH` · **node** `N1-BLOCK` · **gate** `G-NUM` · **actor** `worker-050`
- **authority** worker measurement only. No canonical file edited, no gate verdict, no node
  status, `validation_status=unverified`. The repair authority is the N1-BLOCK / G-NUM owner.

## Files

| file | role |
|---|---|
| `crosscheck.py` | deterministic black-box runner; battery pre-registered in code; `--selftest`; exit 3 on subject/context hash drift |
| `fixtures.json` | extracted 23-row pre-registered battery (properties, per-row expectations, plants) |
| `report.json` | measured row-level results, scorecard, controls, context hashes, drift check |
| `comparison.md` | head-to-head table, findings W050-LG-1…5, merge recommendation, falsifiers |
| `manifest.json` | hashes of this bundle |

## Subjects (hash-pinned; refused if moved)

| subject | sha256 |
|---|---|
| `numerics/tests/selfgravity_lock_guard.py` (canonical rev1) | `7535ec84ac9ceb0b5451e4ed93ae6b03083966db47aa218eb4fba3da6627b9f5` |
| `artifacts/flash-15/n1_guard_failclosed/repaired_proposal.selfgravity_lock_guard.py` (A) | `bbc5f363d2f89317236cb7cce1784174733120342fd3111a27bf686e12a5507c` |
| `artifacts/worker-012/n0/lockguard_failclosed/guard_candidate.py` (B) | `0b72a9871b56bc4e3588261bd818b02b9373d5dd6b7e94260f6fa164813528f5` |

Context pins: `numerics/gates.py` `fcd1d70991b6…`, `numerics/blockers.md` `d396b609d81d…`.
`research_map/research_map.json` is live traffic: its hash at run time (`f344ed2aaea5…`) is
recorded in `report.json` and any within-run movement is flagged, never used to invalidate the
measurement. Measured `2026-09-12T01:01:36+0800`; a second run reproduced the report field-for-field
except `measured_at`.

## Result in one line

Canonical fails open on 11/11 lock-not-released + artifact rows; **candidate A** closes all of
them but releases on `"unlocked"`/`"Released"` (2 broad-release witnesses); **candidate B** has the
correct exact-`released` surface but still fails P1 on a `locked` lock with empty `locked_nodes`
plus a declared artifact, and certifies an unparseable state (`unknown_state_clean`). Neither is
acceptable verbatim; the recommended merge is A's control flow + B's exact-release surface + B's
diagnostic fields, which is the only combination with zero P1–P4 witnesses.

## Claims (worker-level)

1. **Instrument measurement.** At the three pinned subject hashes, the 23-row battery in
   `fixtures.json` reproduces exactly as recorded in `report.json`: per-revision verdict/exit for
   every row, `numerics.gates` state criterion per row, `--self-test` exit 0 for all three
   revisions, live-tree `PASS`/exit 0 for all three, `numerics/spherical_solver/` absent live.
2. **Defect confirmation.** Canonical `7535ec84ac9c` returns `PASS`/exit 0 with an N1+ artifact
   present for 11 state/block spellings other than exact `locked` (P1), plus 2 release-surface
   spellings (P2), and for `locked` + empty `locked_nodes` (P4). This is the assignment's own
   acceptance falsifier firing at the current bytes.
3. **Repair adjudication.** Candidate A has 0 P1, 2 P2 witnesses (`state_unlocked_solver`,
   `state_miscased_Released_solver`). Candidate B has 1 P1 witness
   (`vacuous_nodes_empty_declared_n2`), 0 P2 release-surface witnesses, and 1 P3 witness
   (`unknown_state_clean`).

## Method

Fixtures are temp roots containing only `research_map/research_map.json` and the planted files;
guards are invoked as subprocesses (`python3 <guard> --root <fixture>`), so the measurement is
black-box. `numerics.gates` is probed by importing the live module and isolating its
`numerics_lock.state` blocking reason on the same roots. All subject/context hashes are measured
before and after; any drift makes the run exit 3 without certifying. `numerics/spherical_solver/`
is created only inside temp roots and never in the repository.

## Falsifiers

- **F1** re-run does not reproduce the row table, or exits 3 on hash drift → measurement void.
- **F2** any witness row returning `PASS`/exit 0 for a different revision than recorded → row or
  table void (e.g. a repaired canonical guard landing).
- **F3** any canonical byte hash changing across the run → affected comparison void.
- **F4** a merged repair returning `PASS` on any P1/P2 row, or on `locked` + empty
  `locked_nodes` + declared artifact → the recommendation is falsified.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-050/lockguard_candidate_crosscheck/crosscheck.py --selftest
python3 artifacts/worker-050/lockguard_candidate_crosscheck/crosscheck.py
```

`report.json` is rewritten deterministically except for `measured_at`; compare `rows[].guards[]`,
`scorecard`, and `drift` to the values recorded here.

## Scope limits

Black-box guard semantics only: not a physics/numerics claim, not a re-derivation of the N0 order
claim, not an adjudication of the protocol contest. The battery covers the state/artifact paths
the guard reads, not arbitrary code paths, and `gates.py` is probed only on its isolated state
criterion (its other criteria keep production blocked today).
