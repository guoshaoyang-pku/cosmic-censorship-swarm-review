# W046-N0-FIXEDDT-INDEP-01 — protocol-§3.4-exact fixed-dt N0 order study (worker-046)

**Task.** One bounded, class-bound task selected by worker-046 (no assignment card existed in
`comms/inbox/worker-046.jsonl`): node **N0**, gate **G-NUM**, class **AF-WCC-SCALAR-SPH**.

**Verdict: `SUPPORTED`** — 8/8 pre-registered criteria pass, no hash-guard mismatch, protocol hash
stable during the run. Worker evidence only: this is **not** a gate verdict, not node completion,
and does not touch `numerics_lock`.

## Why this study exists

The independent C8 review by worker-067 (`artifacts/worker-067/g_num_protocol_review/review.json`,
finding **F1**, major, blocks accept), confirmed independently by worker-081, established that the
certified N0 order evidence was carried by **constant-CFL** ladders (`cfl = 0.5`, `dt = 0.5·dr`),
while `numerics/CONVERGENCE_PROTOCOL.md` §3.4 requires:

> "Spatial order is measured with a fixed, small `dt` (`1e-4`) so RK4 error is negligible; …
> (`dt ∝ h` runs are reported as mixed-order and never quoted as spatial)."

Worker-067's F1 falsifier is exact: *"A 4-rung order-certification study at fixed dt=1e-4 for
schemes A/B exists at the pinned protocol hash, or the pinned protocol text does not contain the
quoted section 3.4 sentence → F1 is withdrawn."*

This artifact supplies that missing study, independently of the numerics lead's in-flight
`numerics/protocol/n0_fixed_dt_certification.py` (created 00:31, no output when this worker
started). It re-executes the **frozen module** under a hash guard and re-derives every statistic
with this worker's own arithmetic (closed-form OLS on log e vs log h; the module's own fit is
recorded but not relied on).

## Result at the pinned inputs

Pinned and re-measured at run time (all matched):

| input | sha256 |
|---|---|
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420…` |
| `numerics/tests/n0_order_4rung.json` | `c88146a1375c50f0…` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a24313…` (unchanged during the run) |

Four rungs `dr = 0.2, 0.1, 0.05, 0.025`, `dt = 1e-4` fixed on **every** rung (60 000 steps per
rung), `r_max = 30`, `t_end = 6`, norm = the module's integral L2 error.

| scheme | fixed-dt fit order (this run) | R5 δ | published cfl=0.5 order | \|Δp\| | R5 bound | agree |
|---|---|---|---|---|---|---|
| lffd | **1.999943 ± 0.000084** | 0.000084 | 1.996625 | 0.003318 | 0.25 | yes |
| cnfd | **1.999864 ± 0.000093** | 0.000093 | 1.995351 | 0.004513 | 0.25 | yes |
| cnfem | **1.999916 ± 0.000246** | 0.000246 | 1.988860 | 0.011056 | 0.25 | yes |

All ladders monotone; per-rung errors agree across the three schemes to ~4 significant figures
(spatial error dominates at this `dt`), e.g. `dr = 0.025`: lffd `1.039969e-4`,
cnfd `1.040135e-4`, cnfem `1.040272e-4`.

## Controls (A8)

| id | control | result |
|---|---|---|
| C1 | same 4-rung ladder at `cfl = 0.5` reproduces the published orders | lffd/cnfd/cnfem reproduce to < 1e-9 relative — the runner is the published object |
| C2 | contamination ladder `dt = dr^0.5` (4 rungs) | cnfd p = **0.9878**, cnfem p = **0.9567** — temporal contamination is detectable, so the fixed-dt result is discriminative |
| C3 | determinism: repeat coarsest-rung ladder | `l2_error` bitwise equal |

## Pre-registered criteria

`A1` guards, `A2` published-hash guard, `A3` 4 rungs & `dt = 1e-4` on every rung, `A4`
monotonicity, `A5` in-band `|p − 2| ≤ 0.3`, `A6` R5 agreement with the published CFL order,
`A7` F1 falsifier clause triggered (fixed-dt in-band ladder for lffd **and** cnfd), `A8` controls
C1–C3. Verdict rule: REFUTED if A1–A4 fail; SUPPORTED if A1–A8 pass; PARTIAL otherwise.

`A7 = true`: the evidence worker-067's F1 said was missing now exists and is in band. Whether F1
is withdrawn is a reviewer/controller decision, not this worker's — see `not_claimed`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-046/n0_fixed_dt_independent/independent_fixed_dt.py --out results.json
python3 artifacts/worker-046/n0_fixed_dt_independent/build_verification.py
```

`results.json` holds every raw row, both fit paths, all controls and the criteria outcomes.
`verification.json` is the hash-bound record; `MANIFEST.json` pins the directory;
`CHECKPOINT.json` carries the manifest hash.

## Falsifier

Re-run after any change to the script or to the three pinned inputs: a scheme outside
`p = 2.0 ± 0.3`, non-monotone errors, `dt ≠ 1e-4` on any rung, an A8 control failing, an R5
disagreement with the published order, or any hash-guard mismatch falsifies or voids the result
(hash mismatch exits 2 fail-closed). If the protocol hash at review time is not `1e6cdf04d7a2`,
the §3.4 binding of this study is void even if the numbers reproduce.

## Scope limits / not claimed

- Worker evidence only: **no gate verdict, no node completion, `numerics_lock` stays LOCKED, no
  self-gravity and no physics claim.**
- The study shares the PDE, pulse, domain, rung set and error norm with the object under test
  (this is deliberate: it tests §3.4 compliance of the certified evidence, not a new
  discretisation — worker-046's prior lifecycle covered the independent-discretisation axis at
  `artifacts/worker-046/n0_independent_replication/`).
- `dt = 1e-4` is the value named in §3.4; the temporal-subdominance bounds at this `dt` are
  carried by the lead's companion controls, independently verified in flight by worker-020.
