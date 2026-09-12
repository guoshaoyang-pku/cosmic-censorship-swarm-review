# W055-N0-RK4-INDEP-01 — independent-method replication of the N0 flat-space order claim

- **Worker**: worker-055
- **Node / gate / class**: N0 / G-NUM / `AF-WCC-SCALAR-SPH`
- **Task origin**: no assignment in `comms/inbox/worker-055.jsonl`; class-bound task taken under the
  open map node N0 (worker rule: propose one artifact-backed task, do not claim completion).
- **Claim of record being replicated**: `numerics/tests/n0_order_4rung.json#c88146a1` —
  "order 2 measured at four rungs for three schemes; all within p = 2.0 ± 0.3" with R5 pairwise
  agreement, for the Gaussian pulse r0=10, sigma=1.5, r ∈ [0,30], t_end=6,
  dr ∈ {0.2, 0.1, 0.05, 0.025}, dt = 0.5·dr.
- **Frozen replication**: `numerics/tests/flat_wave_replication.py#8ade1cdc` (lffd / cnfd / cnfem).

## Why this file exists

The frozen replication declares its own **known shared axes** with the reference: the ψ = r·φ
reduction, the ψ(0)=ψ(R)=0 Dirichlet condition, the Taylor start, and the Gaussian family
(module docstring, "KNOWN SHARED AXES"). This artifact independently replicates the same order
claim along the axes that were **not** covered:

| axis | frozen replication | this replication (rk4fd) |
|---|---|---|
| dependent variable | ψ = r·φ | φ evolved directly; ψ = r·φ never formed in the solver |
| origin closure | ψ(0)=0 Dirichlet | l'Hôpital limit φ_tt(0) = 3·φ_rr(0) with even ghost point |
| time integration | leapfrog / Crank–Nicolson, Taylor start | classical RK4 method-of-lines, exact initial data, no Taylor start |
| spatial operator | 3-point Laplacian on ψ | centred 2nd-order d²/dr² + (2/r)d/dr on φ |
| error-norm plumbing | reference implementation | independent implementation of the same ℓ2 rule |

Unavoidably shared (they are the claim's own definition, not a shortcut): the PDE
ψ_tt = ψ_rr, the Gaussian-pulse family, the outer truncation at r=30, the ℓ2 metric formula,
and the four-rung configuration.

## Controls (both driven by `independent_replication.py`)

1. **Wiring control `lffd_reimpl`** — a from-scratch reimplementation of the ψ leapfrog family.
   It shares the reference axes on purpose. If it did not reproduce the recorded lffd order
   `1.996624864320` within R5, the grid/dt/t_end/norm plumbing of this file would be indicted and
   the rk4fd reading void. Measured: `2.000911283167`, |Δ| = 0.004286 < R5 bound 0.25 — **passes**.
   *(This control earned its place: its first version had the older/newer leapfrog levels reversed
   and reported order 0.0002, which is how the bug was found.)*
2. **Failure-detection control `upwind1`** — same RK4 integrator with a first-order one-sided
   radial derivative. A pipeline that cannot see a wrong-order scheme would report ≈2 here.
   Measured: `1.054540243364`, outside 2.0 ± 0.3 — **fires as required**.
3. **Determinism control** — the primary study is run twice; the two result blobs are bitwise
   equal; no RNG is used — **passes**.
4. **Anti-drift hash guard** — refuses to run unless
   `flat_wave_replication.py = 8ade1cdc…` and `n0_order_4rung.json = c88146a1…`; re-measures both
   after the run. Both stable during the run.

## Result

`report.json#db85c6e3` (wall-clock-independent `content_sha256 = 783c04be237552025a45299c792be19406949de7d8c8bbfe2fdaefea6329f5f0`)
— verdict `all_checks_pass = true`. The file-level hash moves between runs only because
`created_at` / `runtime.seconds` are recorded; every numeric section and the `content_sha256`
are bitwise stable across re-runs (checked).

| scheme | role | fit order | Δ (R5) | monotone | within 2.0±0.3 |
|---|---|---:|---:|:--:|:--:|
| `rk4fd` | primary independent method | **2.000273612678** | 0.000297 | yes | yes |
| `lffd_reimpl` | wiring control | 2.000911283167 | 0.001017 | yes | yes |
| `upwind1` | failure-detection control | 1.054540243364 | 0.034703 | yes | **no** (intended) |

R5 comparison of the primary result against every recorded scheme: |Δp| = 0.00365 (lffd),
0.00492 (cnfd), 0.01141 (cnfem), all ≤ the 0.25 R5 floor — agrees.

The φ-metric error (secondary diagnostic, `l2_error_phi` rows) also converges at order ≈ 2
(4.775e-4 → 1.192e-4 → 2.978e-5 → 7.440e-6), so the result is not an artifact of forming ψ = r·φ
for the comparison.

## Falsifier

Re-run `independent_replication.py` at the pinned input hashes. The replication is falsified if
any of: (a) `flat_wave_replication.py ≠ 8ade1cdc` or `n0_order_4rung.json ≠ c88146a1` (the run
refuses rather than binding a superseded revision); (b) `rk4fd` is non-monotone, leaves
2.0 ± 0.3, or disagrees with any recorded scheme beyond the R5 bound; (c) the wiring control
fails to reproduce the recorded lffd order within R5; (d) the failure-detection control measures
order inside 2.0 ± 0.3; (e) the pinned inputs change mid-run (reported unstable, no verdict).

## Not claimed

- No gate verdict, no gate self-pass; this is supporting evidence for G-NUM only.
- No node completion; N0 stays active and `numerics_lock` stays **LOCKED**.
- No judgement on the C8 protocol review or on the candidate `numerics/tests/flat_wave.py`.
- No physics claim; flat-space calibration sub-case only, no self-gravity.
- No claim that the shared axes above are error-free — only the independence axes are tested.

`numerics_lock` respected: no N1 work, no `numerics/spherical_solver/` created or touched.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-055/n0_rk4_independent/independent_replication.py
# (~0.2 s; writes report.json; exits 0 only if every check passes)
```
