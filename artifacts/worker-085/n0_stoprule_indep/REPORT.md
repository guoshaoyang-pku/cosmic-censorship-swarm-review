# W085-N0-STOPRULE-INDEP-01 — independent re-measurement of the N0 stop-rule closure

- **worker**: worker-085 (breadth executor, no gate authority)
- **class**: `AF-WCC-SCALAR-SPH` · **node**: N0 · **gate**: G-NUM
- **target**: `numerics/results/flat_wave_convergence_rev3.json` at `da7c360719950f7e`
- **closure claim under test**: accepted gate event `lnum-gate-86e9d96aea678ff2106e`
  (astra-lead-numerics, 2026-09-12T01:18:07): items (1) four-rung fixed-dt order,
  (2) F0 re-bind, (3) independent replication.
- **verdict**: `reviews/N0-stoprule-independent-085.json` — worker-level **accept 4.5**,
  0 hard failures, 5 findings.
- **method**: independently written least-squares re-derivation from the target's own
  per-rung error tables + full declared-hash resolution from live bytes. Read-only:
  no solver executed, no numerics process started, no canonical artifact written.

## Results

| stop-rule item | measurement | status |
|---|---|---|
| (1) order | 3 schemes × 4 rungs at dt = 1e-4 exactly; recomputed LS order equals declared to ≤ 4.44e-16 (lffd 1.999943173893314, cnfd 1.999863592724020, cnfem 1.999916307987489); pair orders identical; SE agrees to ≤ 3.4e-21; monotone; \|p−2\| ≤ 0.3; cross-scheme \|dp\| = 7.958e-05 ≤ 0.25 | **MET** |
| (2) F0 re-bind | canonical taxonomy `0abb9ed8a961` + companion `d7419b4e8963`, class `AF-WCC-SCALAR-SPH` present in both; target's declared binding hash equals measured | **MET** |
| (3) replication | 3/3 verdict disk hashes resolve to the values the target records; 3/3 bind the declared frozen module `8ade1cdc` and protocol `1e6cdf04`; 18/18 fixed-dt order and delta_R5 values reproduce exactly | **MET with a wording correction (F-085N0-01)** |

Probe: 54/54 checks pass, zero drift, exit 0. Full machine record:
`artifacts/worker-085/n0_stoprule_indep/probe.json`; re-runnable via
`python3 artifacts/worker-085/n0_stoprule_indep/probe_n0_stoprule.py`.

## Findings

1. **F-085N0-01 (medium, wording)** — the gate event calls W046/W057/W081 “hash-matched
   verdicts … at frozen run hash da7c36071995”. The three verdicts were written
   00:39:49 / 00:40:40 / 00:41:21, *before* rev3 existed (00:44:23), and 0/3 names that
   hash. They are pinned to the same inputs and reproduce the same numbers, so the
   substance holds; the word “at” overstates the literal binding. Restatement suggested
   in the verdict file.
2. **F-085N0-02 (low, registration)** — the three replication verdict artifacts are not in
   `runtime/state/artifact_hashes.json` (module, protocol, cert basis and rev3 report are).
   Controller registration step, pass 09.
3. **F-085N0-03 (informational)** — `delta_R5`/`pair_half_range` is half the pairwise-order
   spread; all four artifacts use that definition consistently.
4. **F-085N0-04 (informational)** — protocol preamble still cites superseded pins
   `66bf917b`/`565a6e50`; the target records this and correctly declines to rewrite bytes
   that every verdict is pinned to.
5. **F-085N0-05 (informational)** — the live map's G-NUM text was replaced by the
   01:22:04 cycle; cite the claiming text by accepted-stream event id.

## Scope / authority

No gate verdict, no node status, no `validation_status=passed`, no numerics-lock or freeze
change. The N0 node verdict remains lead-audit-owned (`astra-life04-n0-verify`, 03:00).
Any byte move in the nine pinned paths voids this verdict for the new bytes.
