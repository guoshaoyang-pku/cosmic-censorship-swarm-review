# W057-N0-FIXEDDT-VERIFY-01 — independent re-analysis of the N0 fixed-dt certification

Worker `worker-057` (bounded execution slot). Class `AF-WCC-SCALAR-SPH`. Node `N0`.
Gate touched: `G-NUM`. Task self-selected (no card in `comms/inbox/worker-057.jsonl`).

**Authority note.** This is a worker-local re-analysis artifact. It sets no gate verdict,
no node status and no `validation_status`; it does not release `numerics_lock` or N1.
Binding decisions remain with the controller, `astra-lead-numerics` and `astra-lead-audit`.

## Question

Does the lead-numerics fixed-dt certification
`numerics/protocol/n0_fixed_dt_certification.json` reproduce, **from its own embedded
per-rung `(dr, l2_error)` rows**, under independent estimators and the protocol's own
consistency rules?

## Inputs (pinned, measured)

| path | sha256 | note |
|---|---|---|
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8…` | 24 rungs total (3 schemes × 4 fixed-dt + 3 × 4 constant-CFL control) |
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420…` | frozen module named by the certificate; hash guard reproduced |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a24313…` | section 3 items 2/3/4 and R5/R5a checked |

The certificate hash was measured before and after the run: **stable** (no drift).

## Method (independent of the lead's generator)

The generator `n0_fixed_dt_certification.py` was **not imported or executed**. Every derived
number was recomputed from the published rows with:

- least-squares slope of `ln(l2_error)` vs `ln(dr)` (order `p`);
- pairwise orders `p_i = ln(e_i/e_{i+1}) / ln(dr_i/dr_{i+1})`;
- a robust median-of-all-pairwise-slopes estimator (Theil–Sen style);
- `SE = sqrt( SSR/(n−2) / Sxx )` and `delta_R5 = max(pair half-range, SE)`;
- internal invariants: `dt` constant per fixed-dt block, `cfl = dt/dr`, `steps = t_end/dt`,
  strictly decreasing error ladder, refinement ratio 2, ≥4 rungs;
- the exact protocol agreement rule `|p_A − p_B| ≤ max(0.25, sqrt(δ_A² + δ_B²))`.

Control battery (fail-closed, 6/6 pass): exact second-order ladder → `p=2`; third-order
ladder → `p=3`; first-order ladder → leaves the R5 band; large multiplicative constant →
slope unchanged; +1 % tamper on the finest rung → detected against the declared fit;
non-monotone ladder → detected.

## Result: `REPRODUCED` — 67/67 checks pass, 0 findings, 6/6 controls

| scheme | recomputed `p` (LS) | robust `p` | `delta_R5` | declared `p` reproduced |
|---|---:|---:|---:|---|
| lffd | 1.999943173893314 | 1.9999557609360572 | 8.4437e-05 | yes (1e-12) |
| cnfd | 1.9998635927240203 | 1.9998584754600324 | 9.3177e-05 | yes (1e-12) |
| cnfem | 1.9999163079874884 | 1.9999802339208996 | 2.4644e-04 | yes (1e-12) |

All declared `fit_order`, `pair_orders`, `least_squares_se`, `lsq_residuals` (one documented
sign convention), `pair_half_range`, `delta_R5`, `order_shift_vs_mixed`, `cross_scheme_R5`
and `verdict` fields reproduce exactly from the raw rows. All three fixed-dt ladders are
monotone, `dt = 1e-4` on every rung, `cfl_effective = dt/dr`, `steps = 60000`, ratio 2, 4
rungs. Cross-scheme `max |Δp| = 7.958e-05`, far inside the 0.25 R5 floor; the exact protocol
bound is 0.25 for every pair by the same floor.

The constant-CFL blocks are correctly relabelled as mixed-order controls: they are
constant-CFL (`dt/dr = 0.5`), their orders (1.99662 / 1.99535 / 1.98886 for
lffd / cnfd / cnfem) are *not* used as spatial claims, and the declared shifts match the
recomputed fixed − mixed differences.

## Advisories (2, non-blocking; recorded, not findings)

1. **A4b** — the citation token `section 3.4` does not occur literally in
   `CONVERGENCE_PROTOCOL.md`; the named rule is section 3, item 4 (line 58). The citation
   resolves by section+item convention but is not a literal heading.
2. **A6** — R5a asks an order claim to name the fitted error norm; the certificate names it
   only through the JSON key `l2_error` (no explicit “L2 integral” token). Unambiguous, but
   not explicit in the claim text.

Both are documentation-precision items for `astra-lead-numerics`; neither affects the
reproduction of the numbers.

## What this does not establish

- No physics claim, no solver re-run: the embedded `l2_error` values are taken as published
  rows. The frozen module is hash-guarded, but this instrument cannot confirm the rows were
  produced by it.
- No gate verdict, no node completion, no N1 release; `numerics_lock` remains LOCKED.
- The shared axes (psi = r·phi, Dirichlet box, Taylor start, Gaussian-pulse family) are not
  shown independent here.

## Falsifier / reproduce

```bash
python3 artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py
```

Falsified for the recorded `cert` sha256 if any declared derived number fails to reproduce
from the embedded rows (tolerance 1e-12), if any check flips to fail, or if any control in
E1–E6 stops behaving as specified. A moved certificate hash voids this report for the new
bytes.

Artifacts: `verify_fixed_dt_certification.py#ff5ab64f07e6`,
`report.json#b906445878f3`, this file.
