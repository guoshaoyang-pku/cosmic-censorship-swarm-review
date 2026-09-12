# W021-N0-REV3-INDEP-01 — independent verification of the N0 post-stoprule closure

**Worker:** worker-021 (bounded execution slot) · **Node:** N0 · **Gate:** G-NUM
**Class:** AF-WCC-SCALAR-SPH · **Verdict:** `ACCEPT_WITH_OPEN_ITEMS` (10/10 checks, 4/4 controls)

Read-only. No canonical file written; no gate verdict; no node completion; no `numerics_lock`
release. Not a substitute for the card verdict `audit-r2-N0-rev3` owned by worker-012 (slot
inactive since 01:01; card deadline 03:00) — this is an independent second measurement under
worker-021's own id.

## Object under test

| item | sha256 (measured at run) |
|---|---|
| `numerics/results/flat_wave_convergence_rev3.json` (target) | `da7c360719950f7ef6be2624391dee464f8c818a0be74ec44f0f8c70d2b28ac3` |
| `numerics/protocol/n0_fixed_dt_certification.json` (raw basis) | `1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920` |
| `numerics/CONVERGENCE_PROTOCOL.md` (reviewed protocol) | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |

## Axes (card `audit-r2-N0-rev3`)

| id | axis | result |
|---|---|---|
| A1 | target byte-stable across the review (T0==T1, all 9 pinned inputs) | PASS — 0 drift |
| A2 | 4 rungs per scheme at fixed dt=1e-4 for 3 schemes | PASS — cnfd/cnfem/lffd, dr `[0.2,0.1,0.05,0.025]` |
| A3 | independent log-log least squares re-derives the orders from the raw ladders | PASS — declared `fit_order` reproduced to <1e-15; all monotone; `|p-2| ≤ 0.3`; cross-scheme max diff `7.96e-05 ≤ 0.25` |
| A4 | raw certification rows reproduce the closure ladders and fits | PASS — 4/4 rows per scheme, all `dt=1e-4`, 1e-15 ladder match, fit/pair/delta identical |
| A5 | `class_binding` pin equals live F0 rev5 | PASS — `0abb9ed8a961` (declared rev 5, `AF-WCC-SCALAR-SPH`) |
| A6 | stop-rule items `four_rungs_or_scoped` / `f0_rebind` / `independent_replication_verdict` closed and consistent | PASS |
| A7 | the 3 cited replication verdicts hash-pinned on disk | PASS — worker-046 `814452111bc8`, worker-057 `b906445878f3`, worker-081 `65ae766d9e4c` all match |
| A8 | lock guard: map + artifact `locked`, `production_allowed=false`, no `numerics/spherical_solver`, no N1 artifact | PASS |
| A9 | declared registration gap (6 paths absent from `runtime/state/artifact_hashes.json`) | REPRODUCED exactly |
| A10 | protocol review contest = 2 dissent revises at `1e6cdf04d7a2`; withdrawn-accept guard | PASS — both dissent events found in the accepted stream; `numerics/gates.py` contains no withdrawal/supersession filter |

## Controls

K1 fit sensitivity (20% perturbation of one rung shifts the order by 0.0789 → detected);
K2 wrong-hash detection; K3 solver-absence probe (2 negatives + 1 positive);
K4 determinism (re-hash and refit identical). All 4/4 detected.

## Open items (none are worker-writable)

1. **Registration gap** (rule-2 step, controller): `numerics/CONVERGENCE_PROTOCOL.md`,
   `numerics/results/flat_wave_convergence.json`, `numerics/gates.py`, and the three replication
   verdicts above are absent from `runtime/state/artifact_hashes.json`; the reviewed target itself
   is also unregistered (N0 is not done, so this is prospective, not a breach).
2. **Protocol review contest unresolved**: 3 accepts vs 2 revise verdicts at `1e6cdf04d7a2`;
   `numerics/gates.py` still counts the withdrawn accept `w081-20260912T002140-c8-review`. Needs
   controller adjudication or an explicit supersession rule.
3. **Protocol preamble stale pins** (`66bf917bd368`, `565a6e50`) recorded in
   `class_binding.note`; not load-bearing for the order claim.

## Falsifier

Re-run `python3 verify_n0_rev3.py --base <repo>` at the same pins: falsified if any A-check flips,
if any K1–K4 control fails to detect, or if a recomputed order leaves `|p-2| ≤ 0.3` or the 0.25
cross-scheme bound; **VOID** on drift of any T0/T1 hash or of the reviewed target hash.
`report.json`/`results.json`/`controls.json` are byte-deterministic (no wall-clock fields);
`measurement_digest = e467698991aed885a02f3726a19501e531750d6f52544765fb10a9a5f5a7ca9b`.

## Files

`verify_n0_rev3.py` (instrument) · `report.json` (verdict) · `results.json` (raw measurements) ·
`controls.json` · `README.md`
