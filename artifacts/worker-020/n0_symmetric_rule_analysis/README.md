# W020-N0-SYMRULE-01 — symmetric temporal-excess sensitivity analysis (N0)

**Class:** `AF-WCC-SCALAR-SPH` (flat-space massless-scalar-wave calibration; no self-gravity).
**Node:** `N0`. **Gate:** `G-NUM`. **Worker:** `deepseek-flash-20`.
**Authority:** worker evidence only — no gate verdict, no node completion, no canonical-path edit,
`numerics_lock` stays LOCKED, `numerics/spherical_solver/` untouched.

## Why this task

The lead's N0 admissibility control
`numerics/protocol/temporal_subdominance_control.json#334f5b71e0d5` (generator `ee14a3caf086`)
decides whether the **constant-CFL ladder A** may be quoted as *spatial* evidence. Its
pre-registered rule (generator lines 224–229) is **one-sided**:

```
rule_b:  e(dt_cfl)/e_plateau - 1  <=  0.05        # max() of the SIGNED excess
```

A negative excess means the temporal error *cancels* part of the spatial error. Cancellation
is not subdominance: it can distort the measured order in either direction. This task
re-analyses the **same filed sweep data** under the natural two-sided reading
`|excess| <= 0.05`, without touching the canonical rule, and asks which ladder carries the
order-2 claim. No solver is re-run; the script is a hash-pinned re-analysis of filed rows.
The gap was flagged as RB1 by `W020-N0-FIXEDDT-VERIFY-01` (00:34) and had no owner.

## Method

1. Hash-pin target JSON `334f5b71e0d5…`, generator `ee14a3caf086…`, frozen instrument
   `8ade1cdc163e…`; refuse to run if any moved.
2. Recompute every derived sweep statistic from the target's raw rows (excess, plateau,
   monotonicity, halving grid, steps) and cross-check against the filed values; recompute all
   A/B ladder order fits with an independent least-squares estimator.
3. Apply the one-sided and two-sided readings at the target's own tolerance (0.05, declared
   immovable).
4. Leave-one-out sensitivity of the A-ladder order fit (drop the finest rung dr=0.025; drop
   the swept rung dr=0.05).
5. Conservative bound on ladder-B temporal contamination at dt=1e-3 and 5e-4 from each filed
   sweep, scaling with `q = min(2, measured local order)` (never faster than measured).
6. Controls: sign-flip mutation of the excess, vacuous-input guard, determinism re-run,
   filed-value cross-checks.

## Findings

**SR-1 (the verdict is one-sided).** Of the 6 swept `(scheme, dr)` points, **4 pass the
one-sided rule and 0 pass the two-sided rule.**

| scheme | dr | excess | one-sided | two-sided |
|---|---|---|---|---|
| lffd | 0.2 | −0.235931 | pass | **fail** |
| lffd | 0.05 | −0.231686 | pass | **fail** |
| cnfem | 0.2 | −0.723349 | pass | **fail** |
| cnfem | 0.05 | −0.718041 | pass | **fail** |
| cnfd | 0.2 | +1.238220 | fail | fail |
| cnfd | 0.05 | +1.258230 | fail | fail |

The two schemes the control declares admissible (`lffd`, `cnfem`) are exactly the two with
**negative** excess: their constant-CFL error is 23 % / 72 % *below* the spatial plateau.
The control's own `monotone_to_plateau` flag is `False` for all four of those points.

**SR-2 (mechanism confirmed by mutation).** Reflecting the excess about the plateau flips the
one-sided verdicts (lffd/cnfem pass→fail, cnfd fail→pass) while the two-sided verdict is
invariant (fail, 6/6 mutations detected). The one-sided verdict is therefore decided by the
*sign* of temporal–spatial cancellation, not by the magnitude of the temporal error.

**SR-3 (ladder-A coverage).** Only dr ∈ {0.2, 0.05} were swept (`config.temporal_dr`); the
Rungs dr = 0.1 and 0.025 have **no temporal sweep filed at all**. Under the two-sided reading
the A-ladder has **0 / 4** rungs with positive temporal-subdominance evidence.

**SR-4 (honest limit — the fitted number does not move).** Leave-one-out refits of the A
ladder shift the order by at most **0.0026** (lffd 0.00086, cnfd 0.00187, cnfem 0.00254).
So SR-1 is an **evidential/admissibility** defect, *not* a demonstration that the A-ladder
order-2 value would change if re-measured. No such stronger claim is made.

**SR-5 (positive — ladder B is the admissible carrier).** For the fixed-dt ladders at
dt=1e-3 and 5e-4, at both swept dr, the conservative temporal-contamination bound is
6.1e-6 … 1.52e-3 relative to the plateau — **12/12 cells pass `|excess| <= 0.05`**, worst
margin ≈ 33×. The B-ladder order fits recompute to
lffd 2.000626 / 2.000109, cnfd 1.996292 / 1.999013, cnfem 2.003704 / 2.000945
(dt=1e-3 / 5e-4), all within `|p−2| <= 0.3`, with 4 rungs each.

**Consequence.** Any disposition that licenses quoting the constant-CFL ladder A as a spatial
measurement — or that uses `p_cfl` in the rule_a comparison as if it were one — is unsupported
under the two-sided reading. The certified order-2 conclusion survives via **ladder B**
(and the pending fixed-dt study `W081-N0-FDT-02`), not via ladder A.

## Controls / cross-checks

| control | result |
|---|---|
| pins match filed hashes | 3/3 |
| one-sided recomputation reproduces filed excess/rule_b/admissible | all pass |
| A/B ladder order refits vs filed | all pass (1e-9 rel) |
| halving grid + steps = t_end/dt | all pass |
| two core runs byte-identical | pass |
| sign-flip mutation detected | 6/6 |
| vacuous input (empty sweeps) not silently accepted | pass |

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-020/n0_symmetric_rule_analysis/analyze_symmetric_rule.py
# exit 0; rewrites symmetric_rule_analysis.json / .log
```

## Falsifier

Void if: (i) any pinned input re-hashes differently; (ii) the one-sided recomputation does not
reproduce the filed excess / `rule_b_pass` / `admissible_as_spatial` values; (iii) a filed
sweep point is missing or non-halving; (iv) the sign-flip mutation is not detected; or (v) two
core runs are not byte-identical. The physics-level falsifier: a restated canonical rule that
is two-sided and re-verified at its new hash, or a filed fixed-dt B ladder that fails
`|p−2| <= 0.3` on independent re-run.

## Not claimed

No gate verdict or self-pass; no node completion; no physics claim beyond flat-space
discretisation evidence; no statement that the canonical rule is wrong or must change; no
claim about dr = 0.1 / 0.025 (unswept); no re-measurement of the PDE.

## Files

- `analyze_symmetric_rule.py` — the re-analysis + controls (reads canonical paths only).
- `symmetric_rule_analysis.json` — full machine-readable result.
- `symmetric_rule_analysis.log` — run log.
- `emit_events.py` — outbox emitter (event ids, evidence hashes, falsifier).
