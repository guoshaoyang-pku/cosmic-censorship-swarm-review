# W057-N0-CANONTEMPORAL-VERIFY-01 — independent verification report

- **Worker:** `worker-057` (bounded execution worker; no inbox card existed, task self-selected
  from the live map: no prior independent check of this artifact)
- **Class binding:** `AF-WCC-SCALAR-SPH` (exactly one class; node `N0`, gate `G-NUM`)
- **Object under verification:** `numerics/protocol/canonical_temporal_control.json`
  (schema `n0-canonical-temporal-control/v1`, lead-numerics, generated 2026-09-12T00:30+08:00,
  sha256 `6b339cb876612929357150d809f05bf1518a7cff446f5457209a6de283be4460`)
- **Claim under test (as recorded in that file):** the three canonical `flat_wave.py`
  convergence studies are *spatial-dominated at the baseline cfl* under the file's pre-stated
  rule — temporal excess at the coarsest resolution ≤ 0.05 **and** fitted-order move ≤ 0.05.
- **Verdict: `RECOMPUTED`** — 22/22 checks pass, 6/6 fail-closed controls fire, 4 advisories
  (documentation/non-reproducible fields only, no defect).

## Evidence (sha256)

| artifact | sha256 |
|---|---|
| `numerics/protocol/canonical_temporal_control.json` (input) | `6b339cb876612929357150d809f05bf1518a7cff446f5457209a6de283be4460` |
| `artifacts/worker-057/n0_canon_temporal_verify/verify_canonical_temporal_control.py` | `31bd647f7eb01ca5e5b2f3af674ef3e4508bdd2f28b72dcc81891990b4bbcc3c` |
| `artifacts/worker-057/n0_canon_temporal_verify/report.json` | `59a278f0bc2c2cb9c122228980115dc364955a3bffd997e050058e2552d19475` |
| `artifacts/worker-057/n0_canon_temporal_verify/replay_canonical_temporal_control.py` | `0076e9c6f9d9334d1cf1886fe3ca6871e016a17f4d790adcaa912e5857e5cefb` |
| `artifacts/worker-057/n0_canon_temporal_verify/replay_report.json` | `04cebb4c1ba0e4d41997a8bfa9076b8f2198fc8644b1a02ecb51a786d114f0c6` |
| pinned canonical `numerics/tests/flat_wave.py` | `8b52014dac47f99663c8bf46fb2e65a80db399860d586d63cd73dd1db1454a6c` |
| pinned generator `numerics/protocol/canonical_temporal_control.py` | `00a41cfd47088df9432bdc0aba6540cc3c6a69cd1bf88722b228819274adfa0f` |

## Method A — recomputation from the embedded rows (no import of the lead generator)

Pure-Python arithmetic over the control's own `rows`, plus the hash-pinned study config
(`t_end` 0.37 / 8.0 / 0.37, `R` 1.0 / 40.0 / 1.0, transcribed from the pinned generator and
checked as literal fragments in its source). Recomputed and matched:

- **`dt` for all 20 rows** equals the constant-CFL ceil quantisation
  `dt = t_end / ceil(t_end/(cfl·R/n))` with **relative difference 0.0** (bitwise), confirming
  the ladder is the constant-CFL family the control analyses and not an ad-hoc dt list.
- **`order_l2`** reproduces `log(e_i/e_{i+1}) / log(n_{i+1}/n_i)` to ≤ 1e-12 relative.
- **`fit_order`** reproduces a pure-Python OLS slope on `log n` vs `log l2_error` to ≤ 1e-12
  relative (the control uses numpy `polyfit` on `log dx`; OLS agrees to that level).
- **`temporal_excess_at_baseline`** reproduces `e(baseline)/e(plateau) − 1` to ≤ 1e-15
  absolute at every resolution.
- **`excess_coarsest` / `excess_finest` / `order_move` / `spatial_admissible` / `verdict`
  strings / the `overall` reduction**: all reproduce (order_move compared at 1e-9 absolute —
  it is the cancellation-prone difference of two nearly equal fitted orders ≈ 2–4).

| study | baseline cfl | excess coarsest | max excess | order move | p baseline | p plateau | admissible |
|---|---|---|---|---|---|---|---|
| order2_pulse | 0.25 | 3.8906e-04 | 3.8906e-04 | 1.285e-04 | 1.9978904 | 1.9977619 | true |
| order2_standing | 0.25 | 7.5711e-06 | 7.5711e-06 | 2.430e-06 | 2.0026602 | 2.0026578 | true |
| order4_standing | 0.1 | 4.7812e-05 | 1.5376e-04 | 3.976e-05 | 4.1339880 | 4.1340278 | true |

Additional checks:

- **Plateau is a genuine limit.** Successive cfl increments collapse at every resolution:
  pulse 3.88e-04 → 6.97e-07 → 1.12e-09; standing 7.56e-06 → 1.20e-08 → 2.52e-10;
  order4 1.54e-04 → 2.53e-07 → 3.30e-08 (final ≤ 3.3e-08 ≤ 1e-6, monotone decreasing).
- **Rule-shape robustness.** Under a stricter *max-excess over all resolutions* reading
  (instead of coarsest-only) all three studies remain admissible, so the verdict does not
  depend on the lenient choice of the coarsest row.
- **Unchanged verdict.** All three `spatial_admissible` values and verdict strings match the
  stored ones; `overall.all_spatial_admissible = true` is the correct reduction.

## Method B — replay of the pinned canonical artifact (cross-check, not an independence claim)

A separate script re-imported `numerics/tests/flat_wave.py` **only after** its sha256 matched
the declared hash, re-ran all 3 studies × 4 cfl ladders with the transcribed configs, and
compared fresh rows against the embedded ones:

- **60/60 rows and 12/12 fitted orders reproduce at relative difference 0.0 (bitwise)**,
  worst case 0.0, in 85.56 s. No replay mismatch anywhere.
- The study kwargs are not embedded in the control JSON (advisory A2); the replay binds its
  transcription to the pinned generator hash `00a41cfd4708…`, whose `STUDIES` table it checks
  literally.

This establishes that the embedded numbers are a faithful record of the pinned artifact's
behaviour. It does **not** establish the solver's mathematical correctness, which is the N0
gate chain's job.

## Fail-closed controls (6/6 detected)

| id | control | detected |
|---|---|---|
| E1 | scale plateau coarsest error ×0.9 (excess → 0.1115 > 0.05) | rule flips to inadmissible / MIXED-ORDER |
| E2 | lift baseline coarsest error ×1.3 (order move → 0.0758 > 0.05) | rule flips to inadmissible |
| E3 | reverse plateau rows (n alignment broken) | resolution-list mismatch detected |
| E4 | tamper finest plateau row by 1e-3 relative | 5 derived-number mismatches detected |
| E5 | change one plateau `n` | resolution-list mismatch detected |
| E6 | one-byte edit of the control JSON | sha256 binding rejects the new bytes |

## Advisories (non-blocking)

- **A1 (documentation):** `pre_stated_rule.criterion` does not define "excess" as relative;
  the stored numbers are `e(baseline)/e(plateau) − 1` and reproduce exactly. An absolute
  reading would make the rule vacuous (~1e-9 ≪ 0.05), so the relative reading is the only
  non-degenerate one.
- **A2 (documentation):** study kwargs (`order/family/t_end/R/r0/sigma/modes`) live only in the
  hash-pinned generator, not in the control JSON; the artifact is not self-describing. This
  verifier binds its transcription to the pinned generator hash.
- **A3 (non-reproducible field):** `canonical_artifact.edited=false` and
  `overall.runtime_seconds` are assertions. `edited=false` is independently supported here by
  hash equality (registry + map) and by mtime ordering (canonical 23:35:38 < control 00:30:00);
  `runtime_seconds` is environment-dependent.
- **A4 (rule shape):** for `order4_standing` the relative excess *grows* with resolution
  (4.78e-05 coarsest → 1.54e-04 finest) while remaining far below tolerance; the verdict is
  unchanged under the max-excess reading (see above).

## Falsifier

Re-hash `numerics/protocol/canonical_temporal_control.json` and re-run
`verify_canonical_temporal_control.py`: this report is falsified for the recorded control
sha256 if any declared derived number fails to reproduce from the embedded rows, if any check
flips, or if any of E1–E6 stops being detected. A moved control hash voids this report for the
new bytes; a moved canonical `flat_wave.py` hash voids the control's own premise. The replay
result is additionally falsified if a fresh run of the pinned canonical artifact disagrees with
any embedded row beyond 1e-10 relative.

## Not claimed

No gate verdict, no node completion, no `validation_status=passed`, no `numerics_lock`/N1
release, no physics claim, no solver-correctness claim, no edit to any canonical artifact. A
worker event cannot set node status or a gate verdict; this is evidence for the N0/G-NUM chain
only.
