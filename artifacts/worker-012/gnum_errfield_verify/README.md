# W012-GNUM-ERRFIELD-VERIFY-01 — independent recomputation of the N0 scheme error-field check

**Verdict: `REPRODUCED_AND_EXTENDED`** — all six pre-registered predictions pass at stable pins;
the filed artifact reproduces essentially bit-for-bit, and its `shared_error_artifact = false`
reading holds in the **certified fixed `dt = 1e-4`** regime, not only at the filed `dt = 1e-3`.

| field | value |
|---|---|
| task | `W012-GNUM-ERRFIELD-VERIFY-01` (self-selected; no inbox card for worker-012) |
| node / gate / class | `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH` |
| target | `numerics/protocol/error_field_orthogonality_check.json#1b2d3162b0715d9b` |
| report | `artifacts/worker-012/gnum_errfield_verify/report.json#e58354109da4` |
| instrument | `artifacts/worker-012/gnum_errfield_verify/verify_errfield.py#2411ed705d85` |
| prereg | `artifacts/worker-012/gnum_errfield_verify/PRE_REGISTRATION.md#e7909125c69b` |
| verdict | `REPRODUCED_AND_EXTENDED` (P1…P6 all pass, `pins_stable = true`) |
| runtime | 123 s, read-only |

## What was checked

The gate proposal criterion `independently-replicated-within-tolerance` cites this artifact as the
evidence that the three-scheme order agreement is **not a shared-error artifact**. No independent
recomputation of it existed on disk. Two gaps were closed:

1. **Reproduction** at the artifact's own configs (`dt = 1e-3`, `dr = 0.2, 0.1`).
2. **Extension to the certified regime** (`dt = 1e-4`, `dr = 0.2, 0.1, 0.05`) — the filed check
   was one decade away from the regime it is quoted to support.

Method: the frozen module `numerics/tests/flat_wave_replication.py#8ade1cdc163e` is imported from
a byte-identical snapshot inside this directory (`sys.dont_write_bytecode = True`; the canonical
path is never imported). Fields are `e_i = psi_num(r_i) - psi_exact(r_i)`; correlation is
`np.corrcoef`, sign-mass and norm-ratio are re-implemented independently. The declared generator
`error_field_orthogonality_check.py` was **not** imported or executed.

## 1. Declared regime — reproduction (`dt = 1e-3`)

| `dr` | quantity | declared | recomputed | delta |
|---|---|---|---|---|
| 0.2 | `corr(lffd,cnfd)` | 0.9999999965922115 | 0.9999999965922114 | 1.1e-16 |
| 0.2 | `corr(cnfd,cnfem)` | −0.9996258407429242 | −0.9996258407429239 | 2.2e-16 |
| 0.2 | sign-mass(cnfd,cnfem) | 1.3382834964e-18 | 1.3382834964e-18 | 0.0 |
| 0.1 | `corr(lffd,cnfd)` | 0.9999999966082539 | 0.9999999966082532 | 6.7e-16 |
| 0.1 | `corr(cnfd,cnfem)` | −0.9999768304345169 | −0.9999768304345171 | 2.2e-16 |
| 0.1 | sign-mass(cnfd,cnfem) | 1.0923702932e-05 | 1.0923702932e-05 | 0.0 |

`l2_error` and `norm_ratio` reproduce at relative `0.0`; the artifact's own `reading` flags
(`cnfd_vs_cnfem_negative`, `same_stencil_family_positive`, `shared_error_artifact=false`) match.

## 2. Certified regime — extension (`dt = 1e-4`, 60 000 steps/rung)

| `dr` | `corr(cnfd,cnfem)` | sign-mass(cnfd,cnfem) | `corr(lffd,cnfd)` | `spread_relative` | shared artifact? |
|---|---|---|---|---|---|
| 0.2 | −0.9996255931 | 1.34e-18 | 0.99999999934 | 2.09e-04 | no |
| 0.1 | −0.9999765615 | 1.06e-05 | 0.99999998457 | 5.16e-05 | no |
| 0.05 | −0.9999983446 | 1.83e-06 | 0.99999985904 | 1.39e-04 | no |

The FD-family pair (`lffd`/`cnfd`, identical 3-point stencil) stays strongly positive; the
FD/FEM pair is strongly negative with vanishing sign agreement. The exclusion of a shared error
therefore holds in the exact regime of the certified order claim.

## 3. Mechanism, negative control, determinism

- **Mechanism (P3):** fitted leading coefficients of the operator symbols vs `−k²`:
  `−0.0832336` (3-point FD; declared `−1/12`) and `+0.0834328` (consistent-mass P1 FEM;
  declared `+1/12`), both inside the pre-registered `1e-3`; residual from the declared
  coefficient `<= 4.5e-06` over `theta in [0.02, 0.2]`.
- **Negative control (P5):** a planted shared field (lffd field × `(1 + 1e-12 cos i)`) gives
  `corr = 1.0` and sign-mass `1.0`; self-correlation `1.0`. The detector separates a shared field
  from the FD/FEM pair, so the negative reading is not vacuous.
- **Determinism (P6):** both declared cases re-run in-process are bitwise equal
  (`np.array_equal`) with identical statistics.

## 4. Bonus cross-check against the certification basis

The same runs reproduce the `numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c`
fixed-`dt` `l2_error` rows **exactly (relative 0.0)** on 9 of 12 certified rows — `dr = 0.2, 0.1,
0.05` × `lffd/cnfd/cnfem`. Independent instrument, same published numbers.
(The fourth rung `dr = 0.025` was not recomputed here; see limits.)

## 5. Limits and next falsifier

- Structural evidence only: this measures the error-field structure and reproduces rows; it is
  not a gate verdict, not node completion, and not a physics claim.
- Closed on 3 of the 4 certified rungs; `dr = 0.025` and a second pulse family remain untested.
- **Next falsifier:** a fixed-`dt = 1e-4` recomputation at `dr = 0.025` or on a different pulse
  family in which `corr(cnfd,cnfem) >= -0.9`, sign-mass `>= 0.01`, or `spread_relative >= 0.01`
  voids the certified-regime extension; any pinned path re-hashing voids the report; a planted
  shared field not being detected falsifies the instrument.
- **Script revision disclosure:** rev1 (preserved at `raw/report_rev1_p3_script_bug.json`) failed
  P3 alone because the symbol fit double-divided by `theta²` — a script defect, not an artifact
  finding. Rev2 fixed the normalization and left every prediction unchanged in substance; the
  frozen inputs were stable across both runs.

## 6. Not claimed

No gate verdict; no node status; no `validation_status=passed`; no disposition of the C8
protocol contest; no `numerics_lock` release; no claim that the shared axes (`psi = r*phi`,
Dirichlet box, Taylor start, pulse family) are independent. `numerics_lock` stays LOCKED,
`numerics/spherical_solver` is absent, no N1 work. The reviewed artifact was not edited; writes
are confined to this directory plus one checkpoint and this worker's own outbox.

## Pins (measured before and after; all stable)

| path | sha256 |
|---|---|
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422` |
| `numerics/protocol/error_field_orthogonality_check.json` | `1b2d3162b0715d9b7dd3c304248c88ccd55b686ea81b401ed3f5baa60ede5945` |
| `numerics/protocol/error_field_orthogonality_check.py` | `4562331fb73d6fd60ebcf4a50e9f88613db72f8d4aca4e1e340fddf7fb2f0dc2` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8f6e48dee8360ab13edc35623c51f4be68bd6589a5fe79920` |
