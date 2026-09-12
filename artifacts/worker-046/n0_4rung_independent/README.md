# worker-046 — independent reproduction check of the N0 4-rung order evidence

**Task taken (class-bound):** N0 flat-space scalar-wave calibration, class `AF-WCC-SCALAR-SPH`,
node `N0`, gate `G-NUM`. Deliverable: independent re-execution + independent arithmetic check of
the published 4-rung order evidence `numerics/tests/n0_order_4rung.json`
(`sha256 c88146a1375c50f0c87d2893109087ee6f08c55919a4812dc073750bd86f544a`).

**Verdict: `REPRODUCED`.** All six independent checks pass; no published falsifier clause triggers.

| check | result |
|---|---|
| provenance pins match bytes on disk (7 inputs) | PASS |
| fresh re-run reproduces every published per-rung `l2_error` | PASS (bitwise) |
| independent normal-equation arithmetic matches orders / deltas / SE | PASS |
| pairwise R5 agreement (`max(0.25, sqrt(dA²+dB²))`) | PASS |
| chaining to controller-verified 3-rung run `6542db93…` | PASS (bitwise on common rungs) |
| published falsifier clauses (monotone, band, R5, hash guard, ≥4 rungs) | PASS (none triggered) |

Recomputed orders ± R5 delta: `lffd 1.99662 ± 0.00177`, `cnfd 1.99535 ± 0.00417`,
`cnfem 1.98886 ± 0.00514` (design order 2, band ±0.3; 4 rungs per scheme as rev 3 requires).

## Files

| file | role |
|---|---|
| `verify_n0_4rung.py` | independent verifier (self-contained arithmetic; no import of the addendum) |
| `verification.json` | machine-readable verdict, pins, per-scheme detail, falsifier evaluation |
| `lead_4rung_replication_rerun.json` | fresh output of `numerics/protocol/lead_4rung_replication.py --json-out …` |
| `*.sha256` | sidecar hashes |

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 numerics/protocol/lead_4rung_replication.py \
    --json-out artifacts/worker-046/n0_4rung_independent/lead_4rung_replication_rerun.json
python3 artifacts/worker-046/n0_4rung_independent/verify_n0_4rung.py   # exit 0 == REPRODUCED
```

## Two observations handed to the G-NUM reviewer (neither changes the order claim)

- **O1 (soft, documentation):** the fitted field `l2_error` is `sqrt(sum(e_i^2)*dr)` in the frozen
  module, while protocol rev 3 §3.2 names a volume-weighted L2 `sum V_i e_i^2 / sum V_i`. The two
  are O(h²)-equivalent for a smooth error field, so exponents are unaffected, but R5a's "names the
  error norm" is met only by field-name convention, not by an explicit norm declaration.
- **O2 (note):** the addendum's explicit-formula slope SE and the driver's `polyfit`-cov SE differ
  by ≤1.7e-13; the R5 delta is pair-spread-driven in all three schemes, so deltas and agreement
  verdicts are identical.

## Authority boundary

This is `numerical_evidence` only. No gate verdict, no gate self-pass, no node completion; N0 stays
`active/unverified` and `numerics_lock` stays LOCKED. The re-execution uses the same frozen module
(`8ade1cdc…`), so this is a reproducibility + arithmetic check of the published evidence, **not** a
new methodologically independent scheme (those are `cnfd`/`cnfem` inside the frozen module).
No physics, self-gravity, WCC or SCC claim is made.

**Falsifier of this report:** a re-run in which any recomputed value disagrees with the published
value beyond the stated tolerance, or any pinned hash fails, or any published falsifier clause
triggers — then the verdict must read `FALSIFIED` and the order claim is not reproduced.
