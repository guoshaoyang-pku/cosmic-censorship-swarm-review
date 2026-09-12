# W055-N0-4RUNG-RECOMPUTE-01 — independent worker recheck of the N0 four-rung order claim

| field | value |
|---|---|
| worker | worker-055 (instance `worker-055-20260912T002343-968807`) |
| node / class / gate | `N0` / `AF-WCC-SCALAR-SPH` / `G-NUM` |
| assignment | none in `comms/inbox/worker-055.jsonl`; task taken from the open map node N0 under the worker rule ("if none, propose one artifact-backed task") |
| started / finished | 2026-09-12T00:25+08:00 / 2026-09-12T00:28+08:00 |
| artifact | `artifacts/worker-055/n0_4rung_recompute/report.json` |
| instrument | `artifacts/worker-055/n0_4rung_recompute/recompute.py` |
| authority | **no gate verdict, no node completion, no self-pass**; G-NUM stays with Astra + lead-audit |

## What was checked

The N0 gate proposal (`numerics/tests/n0_gate_proposal.json#58a175b5`) certifies order 2 at
**four** rungs for three methodologically independent schemes, citing the addendum
`numerics/tests/n0_order_4rung.json#c88146a1` produced by
`numerics/tests/n0_order_4rung_addendum.py#fea1b771` over the frozen module
`numerics/tests/flat_wave_replication.py#8ade1cdc`. This artifact re-runs that chain in a fresh
process and recomputes every order statistic with a self-contained implementation:

1. hash-guard the pinned inputs (all six pins measured current);
2. import the frozen module read-only and re-run `order_study()` for `lffd` / `cnfd` / `cnfem`
   at `dr = 0.2, 0.1, 0.05, 0.025`, `cfl = 0.5`, `r_max = 30`, `t_end = 6`;
3. recompute log-log OLS slope, slope SE, consecutive-pair orders, pair half-range,
   `delta = max(half_range, SE)` and the R5 rule
   `|p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2))` without importing the addendum's
   helpers or `rep.pair_orders`;
4. bind the results to the addendum and to the gate proposal's `certified_order_claim`;
5. re-measure all 24 `evidence_hashes` entries of the gate proposal against disk, and record
   the on-disk C8 review and the C4 registry as hash-measured observations only.

## Result — the 4-rung claim reproduces

| scheme | 4-rung order (recomputed) | recorded | delta (recomputed) | monotone | in `2.0 ± 0.3` |
|---|---|---|---|---|---|
| lffd | 1.9966248643204345 | 1.9966248643204345 | 0.0017749505081917638 | yes | yes |
| cnfd | 1.9953510343613228 | 1.9953510343613228 | 0.004172438339596352 | yes | yes |
| cnfem | 1.9888598802332438 | 1.9888598802332438 | 0.005142648496443636 | yes | yes |

Max recomputed pairwise `|Δp|` = **0.007764984087190729** against an R5 bound of 0.25 → all
pairs agree. Every recomputed `fit_order`, `delta`, slope SE and pair order matches the recorded
addendum value to ≤ 4e-16 relative; the raw `l2_error` rows reproduce **bitwise** for `lffd` and
to ≤ 1.2e-16 relative for the implicit schemes against the independent
`numerics/protocol/report_*_4rung.json` driver. The gate proposal's certified numbers equal the
addendum's, and its declared norm (`L2 integral`) matches the data actually fitted
(`l2_error` rows). All 17 chain checks pass.

## Evidence-hash binding (measured 2026-09-12T00:28+08:00)

21 of the proposal's 24 pinned evidence hashes match disk. **No `numerics/` evidence file has
drifted.** The three drifts are live revision targets:

| path | pinned | on disk | nature |
|---|---|---|---|
| `reviews/G-NUM-protocol-review.json` | `66a905f5afef` | `8137f18f1a3b` | superseded by a **rev-3 accept** (`verdict=accept`, score 4.5, `reviewed_sha256=1e6cdf04d7a2`, supersedes `66a905f5`) |
| `research_map/formulation_taxonomy.yaml` | `565a6e505188` | `276009f4f63d` | live formulation revision; class binding stays provisional, not load-bearing for the order claim |
| `runtime/state/artifact_hashes.json` | `6751621533d2` | `11f587b6e669` | controller registry, rewritten continuously |

## Observations (not claims, not verdicts)

- **C8:** as of this run an independent accept verdict on the protocol of record exists on disk
  at `reviews/G-NUM-protocol-review.json#8137f18f`, binding exactly
  `numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2`. The gate proposal's
  `protocol-reviewed-by-audit: unmet` field and the lead-numerics blocker emitted at 00:20:46
  are therefore superseded on disk. Whether this satisfies C8 is a controller/lead-audit
  adjudication, not this worker's.
- **C4:** `runtime/state/artifact_hashes.json#11f587b6e669` still does **not** register
  `runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json#6542db93`.
- `numerics_lock` still `locked`; `numerics/spherical_solver/` absent; N0 stays
  active/unverified and G-NUM stays `pending` in the map.

## Falsifier

Re-run `recompute.py` at the recorded input hashes. This recheck is falsified if any of:
(a) `flat_wave_replication.py` ≠ `8ade1cdc` or `n0_order_4rung.json` ≠ `c88146a1`;
(b) any scheme is non-monotone, outside `2.0 ± 0.3`, or fails the R5 bound at the frozen hash;
(c) any recomputed `fit_order`/`delta`/SE differs from the addendum by > 1e-9 relative;
(d) the proposal's certified orders/deltas differ from the addendum's;
(e) `numerics/spherical_solver/` exists or `numerics_lock` is not locked;
(f) the C8 review no longer reads `accept` at `reviewed_sha256=1e6cdf04d7a2` (observation only);
(g) the C4 registry now contains `6542db93` (observation only).

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-055/n0_4rung_recompute/recompute.py   # ~1.5 s, no files outside this dir written
```
