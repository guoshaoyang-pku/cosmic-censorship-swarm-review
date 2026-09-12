# Pre-registration — W012-GNUM-ERRFIELD-VERIFY-01

**Actor:** worker-012. **Self-selected** (no inbox card exists for worker-012; the two cards on
record — `audit-r2-N0` and `audit-r2-N0-rev3` — were closed by the prior worker-012 instance at
00:55:39, verdict `reviews/N0-review-worker-012.json#827399bc7dd3`).

**Node / gate / class:** `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH` (flat-space calibration sub-case).
**Budget:** <= 1 agent-hour. **Stop rule:** one report at pinned hashes plus one checkpoint, then exit.

## Question

`numerics/protocol/error_field_orthogonality_check.json#1b2d3162b0715d9b` is cited in
`numerics/tests/n0_gate_proposal.json#b4192221ff7d` criterion
`independently-replicated-within-tolerance` as the evidence that the three-scheme order agreement
"is not a shared-error artifact". No artifact on disk independently recomputes it (grep for
`shared_error_artifact` / `sign_agreement_mass_fraction` returns no verification artifact).

Two things are checked:

1. **Reproduction** of the declared check at its own configurations (`dr = 0.2, 0.1`,
   `dt = 1e-3`, `r_max = 30`, `t_end = 6`, Gaussian-pulse exact solution, L2-integral error).
2. **Extension to the certified regime:** the certified order claim
   (`numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8`) is measured at
   **fixed `dt = 1e-4`** on four rungs. The orthogonality evidence was filed at `dt = 1e-3`, i.e.
   one decade coarser than the regime it is quoted to support. Recompute the structure at
   `dt = 1e-4` for `dr = 0.2, 0.1, 0.05`.

## Pins (measured before and after the run; a mismatch voids the report)

| path | sha256 |
|---|---|
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422` |
| `numerics/protocol/error_field_orthogonality_check.json` | `1b2d3162b0715d9b7dd3c304248c88ccd55b686ea81b401ed3f5baa60ede5945` |
| `numerics/protocol/error_field_orthogonality_check.py` | `4562331fb73d6fd60ebcf4a50e9f88613db72f8d4aca4e1e340fddf7fb2f0dc2` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920` |

The frozen module is imported from a byte-identical **snapshot inside this artifact directory**
(sha256 re-checked against the pin); the canonical path is only read for hashing, never imported,
and `sys.dont_write_bytecode = True` is set so no `__pycache__` is deposited in `numerics/`.

## Declared predictions (fixed before the measurement run)

- **P1 — reproduction.** At `(dr, dt) = (0.2, 1e-3)` and `(0.1, 1e-3)`: recomputed
  `l2_error` per scheme matches the declared values to `<= 1e-9` relative; pairwise `corr` to
  `<= 1e-6` absolute; `sign_agreement_mass_fraction` and `norm_ratio` to `<= 1e-6`.
  (Implementation: my own `corr` via `np.corrcoef`, my own sign-mass and norm-ratio code; the
  generator script is **not** imported or executed.)
- **P2 — declared-regime structure.** At both declared cases: `corr(cnfd, cnfem) < -0.5`,
  `corr(lffd, cnfd) > 0.9`, `sign_agreement_mass_fraction(cnfd, cnfem) < 0.01`,
  `shared_error_artifact` reading `false` by the artifact's own threshold (`corr <= 0.5`).
- **P3 — mechanism.** The discrete spatial-operator symbols satisfy
  `(symbol/(-k^2) - 1)/theta^2 -> -1/12` for the 3-point FD operator and `-> +1/12` for the
  consistent-mass P1 FEM operator as `theta -> 0`; fitted slope over `theta in [0.02, 0.2]` within
  `1e-3` of the declared `-1/12` / `+1/12` (FD symbol `-4 sin^2(theta/2)/h^2`; FEM symbol
  `-6(1-cos theta)/(h^2 (2+cos theta))`). This is the claimed equal-magnitude opposite-sign
  leading coefficient; if it fails, the artifact's stated mechanism is wrong.
- **P4 — certified-regime extension.** At fixed `dt = 1e-4` for `dr = 0.2, 0.1, 0.05`:
  `corr(cnfd, cnfem) < -0.9`, `sign_agreement_mass_fraction(cnfd, cnfem) < 0.01`,
  `corr(lffd, cnfd) > 0.99`, and `spread_relative < 0.01`. If this fails while P1/P2 pass, the
  shared-error exclusion is established one decade away from the certified regime and must be
  reported as a scope gap, not silently inherited.
- **P5 — negative control (non-vacuity).** A planted shared field (the `lffd` field and a
  deterministic `1e-12`-relative perturbation of it) yields `corr > 0.999999` and
  `sign_agreement_mass_fraction > 0.999`; self-correlation is exactly `1.0`. The detector must
  separate this plant from the FD/FEM pair, or the test is vacuous.
- **P6 — determinism.** Re-running each declared `dt = 1e-3` case a second time in the same
  process reproduces the final field bitwise (`np.array_equal`) and the statistics to 0.

## Falsifier of this report

Any pinned input re-hashing before vs after; P1 reproduction outside tolerance (declared artifact
not reproducible from the frozen module); P3 slope outside `1e-3` (mechanism claim wrong);
P4 failing (the "not a shared-error artifact" reading is not established at the certified
`dt = 1e-4` and becomes an open item for the N0 dossier); P5 failing (the check cannot detect a
shared field); or any canonical/published file being written by this run.

## Not claimed

No gate verdict, no node status, no disposition of the C8 protocol contest, no numerics-lock
release, no physics claim beyond the flat-space discretisation error structure. `numerics_lock`
stays LOCKED, `numerics/spherical_solver` stays absent, no N1 work. The reviewed artifact is not
edited. Worker events cannot move gates or status.

## Hindsight disclosure

Task selection used a reconnaissance read of the frozen module, the orthogonality generator and
the guard/proposal citations; no error-field value was recomputed before this file was written.
The predictions above are functions of the artifact's declared mechanism and configs, not of a
measurement.
