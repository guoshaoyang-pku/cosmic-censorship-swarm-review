# W055-N0-BLOCKER-STALENESS-01 — independent N0 blocker recheck

Worker: `worker-055` · Node: **N0** · Gate: **G-NUM** · Class: **AF-WCC-SCALAR-SPH** (singular frozen id)
Conclusion type: `numerical_evidence` · Validation status: **unverified** (no reviewer verdict yet)

## Question

`research_map/research_map.json` carries an N0 blocker recorded **2026-09-11T23:24:47+08:00**:

> Controller-run replication: cnfem order -0.0773 (self-test false, drift 1.0e+01) yields
> top-level verdict ORDER DISAGREES …

A second entry at **23:31:57** demands that worker 13 "re-pins and re-runs the replication at
the current hash". Are these still live evidence against N0, or are they stale?

## What was done (no fluent claims; every input pinned by sha256)

1. Verified `numerics/tests/flat_wave_replication.py` on disk is `8ade1cdc…` — the revision
   named by the **later** controller run `…run2_FIXED.json` (sha `6542db93…`, generated
   23:40:37), which reads `replication_verdict: ORDER REPRODUCED`.
2. Re-ran `order_study` for `lffd | cnfd | cnfem` at the exact controller config
   (`dr=[0.2,0.1,0.05]`, `cfl=0.5`, `r_max=30.0`, `t_end=6.0`) in a fresh process.
3. Failure-detection control: `lffd` at `cfl=1.5` (explicit scheme above its CFL limit) must
   **not** produce a clean monotone order-2 fit. It does not (fit −82.29, max L2 2.9e49).
4. Classified every N0 blocker entry against the run2_FIXED timestamp and resolution fields.

## Result

| quantity | value |
|---|---|
| cnfem re-run fit order | **1.9863235066828981** (monotone, within ±0.3) |
| `n0_replication_astra_run2_FIXED.json` cnfem | 1.9863235066828981 (exact match) |
| `n0_replication_astra_run.json` (superseded) cnfem | −0.07727311173551689 |
| run1 script sha | `07e5a39b…` (not on disk) |
| run2 / current disk script sha | `8ade1cdc…` (match) |
| stale map blocker entries | **2** (23:24:47 and 23:31:57, both without `resolved_at`/`resolution`) |
| failure-detection control | detected (lffd cfl=1.5 unstable) |
| N0 status | `active` / `unverified`, G-NUM `pending`, `numerics_lock` **LOCKED** |

**Finding.** The 23:24:47 blocker's −0.0773 cnfem failure is not reproducible at the current
pinned revision; it came from the superseded script `07e5a39b`. The 23:31:57 entry's own
unblock condition (re-pin and re-run at the current hash) is satisfied by run2_FIXED
(`6542db93`, 23:40:37) and confirmed by the 00:12 adjudication addendum. Neither entry carries
a resolution marker, so both should be annotated as superseded. This does **not** promote N0:
the live 00:15:47 blockers (protocol review pinned to the pre-rev2 protocol; controller
artifact-hash registration) remain.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-055/n0_blocker_staleness/run_recheck.py
# writes artifacts/worker-055/n0_blocker_staleness/recheck.json
```

Deterministic: fixed grid, no RNG. `recheck.json` pins the map hash it read, so a later map
update does not silently retarget the finding.

## Falsifier

Re-run at the recorded hashes. The staleness finding is **false** if any of:

- (a) `numerics/tests/flat_wave_replication.py` sha256 ≠ `8ade1cdc…`;
- (b) the re-run cnfem fit is non-monotone or outside `p = 2.0 ± 0.3` at the pinned config;
- (c) `n0_replication_astra_run2_FIXED.json` (sha `6542db93`) does not read
  `replication_verdict=ORDER REPRODUCED` with script `8ade1cdc`, or is not later than the
  cited blocker entries;
- (d) the map's N0 blocker entries no longer contain the −0.0773 / ORDER DISAGREES / re-pin
  text (i.e. they were resolved by other means);
- (e) the `lffd` cfl=1.5 control returns a clean monotone order-2 fit (harness cannot detect
  an unstable scheme).

## Not claimed

No N0 completion, no G-NUM verdict, no gate self-pass; no self-gravity, no horizon, no
cosmic-censorship conclusion; no modification of any canonical artifact, map, ledger or review.
