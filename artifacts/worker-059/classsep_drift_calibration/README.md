# W059-CLASSSEP-DRIFT-CALIBRATION-01 — detector drift `c266dbceca87 → a8c04fc31e4a`

Worker: `worker-059` (fleet instance `worker-059-20260912T0059`, no assignment card existed in
`comms/inbox/worker-059.jsonl`; self-selected per the standing worker pattern, one bounded
class-bound task). Node: `A1` (audit). Gate: `G-AUDIT`. Class scope tokens:
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
(detector-calibration measurement, not a class-semantics claim).

## Why this task

`runtime/state/checkpoint_log.jsonl` carries, at every checkpoint since 00:52,
`"frozen artifact drifted during review: research_map/class_separation.py c266dbceca87 ->
a8c04fc31e4a"`. The 20 CLASSSEP hard findings that hold `G-AUDIT` open, and several frozen
review pins, were measured at the old revision. Two concurrent workers cover adjacent ground
(`worker-052/classsep_calibration_census` re-runs the staged/live/pinned revisions;
`worker-056/classsep_holdout` extends the fixture corpus). Neither answers the *direction and
verdict impact* of the drift. This artifact does, on frozen inputs only.

## Pins (all re-measured after the run; 6/6 unchanged)

| input | sha256 |
|---|---|
| `snapshot/class_separation.pinned_c266dbce.py` | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| `snapshot/class_separation.live_a8c04fc3.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` |
| `snapshot/class_separation.staged_e2d24b92.py` | `e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819` |
| `snapshot/research_map.262da6979857.json` | `262da69798578d7741e1d66dec3ed977d05c4bef296974c36063cb255bee628c` |
| `snapshot/worker07_results.json` | `d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452` |

Harness `verify_classsep_drift_059.py` sha256 `e2507f5f73c452aa825a6f3a8c75521c6f594525fb2ffd793305d30d192f956b`;
report `report.json` sha256 `b6d55ea3113df279a42f29eef9a16f5f0c5fc23e1ce73965c11aa839fece79a4`
(deterministic: identical hash on re-run). The harness reads only the staged snapshot copies
and the frozen map; it never reads or writes the live `research_map/class_separation.py` or
the live map, and no canonical file is modified.

## Result

**The live revision `a8c04fc3` is the pinned revision `c266dbce` plus one added guard** (3 lines)
in `_scan_composite`, immediately after the `_MERGE_ASSERT` hit:

```python
if re.search(r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|"
             r"detector\s+(?:finding|flag)|quote(?:d|s)?\s+(?:the\s+)?detector", ctx, re.I):
    continue
```

Measured on the frozen map `262da6979857` (320 claims), same bytes for both revisions:

| revision | hard findings | relation |
|---|---:|---|
| pinned `c266dbce` | **21** | superset |
| live `a8c04fc3` | **17** | strict subset, adds 0 |
| staged candidate `e2d24b92` | **22** | = live + 4 re-instated drops + 1 new flag |

The 4 dropped findings are exactly `claims[127] x1`, `claims[187] x1`, `claims[192] x2`. Every
one carries a carve-out attribution token, and every parent claim lies in the set the project
itself already adjudicated as mention-level (`{127, 187, 192, 276, 306}`; worker-035/052/085/
worker-306 adjudications). Example: `claims[127]` "…independent C0/C2 non-merge…" and
`claims[192]` "…are detector false positives: 0 genuine assertions that C0 and C2 are one class."

Across **5 independently frozen snapshots** (4 authored by other workers + the live-map
snapshot) the live set is a subset of the pinned set with **0 live-only findings in aggregate**.
The drift is therefore one-directional: it can only *remove* findings, never invent them, so
the 20→? CLASSSEP hard count that holds `G-AUDIT` open can only fall, not rise, if the
audit is re-run at the live revision. (The count in the live map is controller state and moves
with traffic; this artifact claims only the detector effect at the pinned instant.)

## The one way this could have gone the other way (and did not)

The carve-out is a lexical over-approximation, so it can suppress a **genuine** merge
declaration that happens to share its 120-char context window with a meta token. Probe P4
demonstrates this on both live and staged:

> `"The two C0/C2 rows are merged into one class; this is not a detector flag but a real merge."`
> → live suppresses (0 findings); pinned and staged flag it (1).

That is a real false-negative surface, and the standing 27-fixture regression does **not**
exercise it: all three revisions PASS the worker-07 corpus (17/17 leaks, 10/10 controls). The
project should add a fixture for it before treating the corpus as coverage.

On the frozen map, however, no dropped finding is of that shape (all 4 are mention-level), so
the drift does not silently lose a real merge at this snapshot.

## The staged candidate `e2d24b92` (adjacent finding, not adopted)

`proposed/class_separation.py` differs from live by *removing* the carve-out and *adding*
`_NEG_SPLIT` before `_PROHIBIT` (line 94 vs 96). Being ordered first, it is reachable and
overriding: on the frozen map it fires **once**, on `claims[187]`'s
`"…R2-2 newly flags 'do not split: C0 or C2' (S3)…"`, and emits
`CLASSSEP: composite C0/C2 asserted as one class` for a sentence that *prohibits* a merge.
`_PROHIBIT` also matches that context, so the ordering — not the regex — converts a suppression
into a flag. This is a concrete example of the class of false positive that the live carve-out
was written to remove; if the candidate is ever proposed for adoption, this surface should be
adjudicated explicitly. Not a recommendation, not a gate verdict.

## Pre-registration disclosure

A v1 harness preregistered the drift direction backwards (assumed the live revision *removed*
the guard, expected live ≥ pinned) and failed 5/8. Direction was then read off the byte diff,
and v2 re-registered all eight expectations before the passing run. The v1 failure list is
reproduced in this README's history by the v1 docstring revision only; the corrected v2
expectations and results are what `report.json` records. Nothing in v2 was tuned to an
observation without being re-derived from the diff first.

## Falsifier

Re-run `verify_classsep_drift_059.py` against the same six pins: falsified if any pin
re-hashes differently; if the live map-level set is not a strict subset of the pinned set with
adds 0; if any dropped finding lacks a carve-out attribution token or its claim leaves
`{127,187,192,276,306}`; if any of the 5 frozen snapshots shows a live-only finding; if a
genuine first-order merge declaration exists among the drops on the frozen map; if the
worker-07 regression no longer PASSes on any of the three revisions; or if the staged
`_NEG_SPLIT` line is not before `_PROHIBIT` or fires zero times on the frozen map.

## Non-claims

No gate verdict, no node status, no `validation_status=passed`, no claim about the four
classes' mathematics. Worker verdicts are advisory evidence only. The live
`research_map/class_separation.py` and `research_map/research_map.json` were not modified.
