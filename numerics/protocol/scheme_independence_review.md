# Scheme-independence review: N0 energy-drift thresholds

| field | value |
|---|---|
| assignment | `astra-adj2-03-assignment` (2026-09-11T23:24:47+08:00), protocol review, **not code**; completion task `astra-numfix-03` (23:40:52) — final hash-cited verdict in §10 |
| node / gate / class | `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH` (**provisional**) |
| deliverable | this review (canonical path), evidence in `numerics/protocol/scheme_independence_evidence.json` |
| scope lock | `numerics_lock` LOCKED; no self-gravity, no N1, no `numerics/spherical_solver/` |
| status | **unverified review** — no node status, no gate verdict, no completion claim |
| edits to other workers' artifacts | **none** (read-only imports of `numerics/tests/flat_wave_replication.py`) |
| claims not made | no claim that N0 passes or fails; no physics claim; no cosmic-censorship claim |

Assignment task: *"Address the scheme-specific invariant finding and the 6.6e-8 vs
3.4e-15 drift gap."* Acceptance: review of the candidate's energy-drift
threshold and of the scheme-dependence finding, stating what the protocol must
require from an independent scheme (scheme-appropriate functional, order fit
method, uncertainty). Adjudication under review:
`runtime/state/controller_verification/N0_adjudication.md`
(sha256 `d3177fafbd235230…`).

---

## 1. Verdict in one paragraph

The adjudication is directionally right that a **single fixed absolute
drift threshold cannot be applied across schemes**, but its stated evidence and
scope are wrong in two checkable ways. First, the pinned cnfd "own energy" was
**algebraically the leapfrog staggered energy**, not a CN invariant (identity gap
2.07e-15), so the reported `own drift = 6.59e-8` was the *same test* as the
harness functional, not evidence that cnfd fails to conserve its own energy.
Second, cnfd's harness-functional drift `6.59e-8` is **below** the harness's
`drift_tol = 1e-6` and the pinned run itself records
`harness_gate_would_pass = True` for cnfd; therefore the adjudication's own
falsifier — "a non-leapfrog scheme passes the leapfrog-functional gate on the
same configuration" — is **already triggered**. The defensible residual claim is
narrower: the **candidate's** `G3` threshold of `1e-8` rejects cnfd while
admitting lffd, and that pass/fail **flips to PASS at dr = 0.025 with no change
to the scheme** (4.17e-9). The fix is not a new magic number; it is a
functional-aware, resolution-aware criterion (§5).

## 2. Evidence provenance (a stale pin must be recorded)

| source | sha256 (prefix) | note |
|---|---|---|
| `runtime/state/controller_verification/n0_replication_astra_run.json` | `7adab492c8a582d1…` | pinned controller run, generated 23:24:03; `script_sha256 = 07e5a39b…` |
| `numerics/tests/flat_wave_replication.py` (current) | `8ade1cdc163ea420…` | **does not match the pinned run's script hash**; the file was edited after the run |
| `numerics/tests/flat_wave.py` (candidate) | `743c73e4e68e3a52…` | G3 threshold under review |
| `numerics/results/flat_wave_convergence.json` | `e9e124227c4d2932…` | current revision, generated 23:36:43 by `8b52014d…`; the 23:24 adjudication quoted an earlier revision no longer on disk. Snapshot: `artifacts/worker-14/candidate_results_snapshot_e9e124227c4d2932.json` |
| `runtime/state/controller_verification/N0_adjudication.md` | `d3177fafbd235230…` | adjudication text |
| `numerics/protocol/scheme_independence_check.py` | `6711f4ed31dda7b4…` | my read-only verification driver |
| `numerics/protocol/scheme_independence_evidence.json` | `a36f05d863ef44e5…` | raw evidence for every number below |

At pin time cnfd's `own_energy_kind` is recorded as *"symplectic form
1/2|v|^2 - 1/2 <A psi_new, psi_old>"*; the current source labels it
*"average-acceleration invariant 1/2|V|^2 - 1/4<A psi_new,psi_new> -
1/4<A psi_old,psi_old>"*. Worker 13 changed the functional after the controller
run. **All adjudication evidence must be re-pinned at the current file hash
before G-NUM is decided.**

## 3. The pinned "own" functional was the harness functional

On the harness configuration (`dr = 0.05`, `cfl = 0.5`, `r_max = 30`,
`t_end = 6`, 60 samples) I evaluated, on identical trajectories:

- `E_leap` — the harness leapfrog staggered energy (`leapfrog_energy`);
- `E_sym` — the pinned "symplectic form" `½|v|² − ½⟨Aψ_new, ψ_old⟩`;
- `E_aa` — the current average-acceleration invariant.

`E_sym` and `E_leap` agree to **2.07e-15 relative** for both schemes: they are
the same quadratic form (summation by parts, Dirichlet ends). The pinned run's
"cnfd own energy" was therefore the leapfrog functional applied to a CN
trajectory, which is exactly why pinned `own drift` and `harness drift` agree to
five digits (`6.593605593939868e-08` vs `6.59360555635273e-08`).

This contradicts the finding's sentence *"Both independent second-order schemes
conserve their own discrete energies to ~1e-13 or better"*: at the pin, only
lffd conserved to 1e-13 (`3.38e-15`); cnfd was `6.59e-8` and cnfem `1.01e+1`.

## 4. The 6.6e-8 vs 3.4e-15 gap, resolved

Drift of each functional on each scheme's trajectory, `dr = 0.05`, identical
configuration:

| scheme | leapfrog functional | average-acceleration functional |
|---|---:|---:|
| lffd (leapfrog + 3-pt FD) | **3.38e-15** | 3.55e-08 |
| cnfd (Crank–Nicolson-family + 3-pt FD) | 6.59e-08 | **1.11e-14** |

The matrix is symmetric: each scheme conserves **its own** functional to
roundoff and shows an `O(h⁴)`-converging mismatch against the other's.

Cross-functional mismatch under refinement (fixed `cfl = 0.5`):

| dr | cnfd × leapfrog-fn | lffd × avg-accel-fn |
|---|---:|---:|
| 0.2 | 1.369e-05 | 7.457e-06 |
| 0.1 | 1.012e-06 | 5.466e-07 |
| 0.05 | 6.594e-08 | 3.553e-08 |
| 0.025 | **4.170e-09** | 1.77e-09 |
| measured order | 3.76, 3.94, 3.98 | 3.77, 3.94, 3.98 |

Therefore:

1. `3.4e-15` is a **structural zero** of the pair (leapfrog, staggered energy),
   not an accuracy statement about lffd;
2. `6.6e-8` is a **consistency mismatch** of a different pair
   (cnfd, leapfrog energy), not a solver error;
3. requiring `3.4e-15`-class drift from cnfd is requiring cnfd to be leapfrog.

**The candidate's G3 threshold is resolution-arbitrary.** With the leapfrog
functional held fixed, cnfd fails the candidate's `1e-8` at `dr = 0.05`
(`6.59e-8 > 1e-8`) and **passes at `dr = 0.025`** (`4.17e-9 < 1e-8`). A
pass/fail that changes under one refinement is not a property of the scheme.

**The candidate's G3 threshold was unreachable at the pre-23:22:52 revision; the
current revision fixes it.** At the revision quoted in the 23:24 adjudication the
standing order-2 study ran at `t_end = 0.5` with drifts `2.41e-03 … 9.41e-06`
(order ≈ 2, finest ≈ 940× above `1e-8`) and `G1_standing_order2` read false;
that configuration and its mechanism are documented in `convergence_protocol.md`
§9 and reproduced by E1/E6. At the current pinned revision
(`numerics/results/flat_wave_convergence.json` sha256 `e9e124227c4d2932`,
generated 23:36:43, generator `8b52014dac47f996`) the standing study runs at
`t_end = 0.37` and the drift series is `2.83e-10 → 1.62e-14` (order ≈ 5);
`G1`, `G3` and `G9` now read true. The diagnostic dependence is unchanged and
still measured: the same RK4 run gives order ≈ 5 with an adjoint-consistent
discrete gradient and order 2 with `np.gradient` (demo E5). The revision
resolved the instance; G3's pass/fail still measures the diagnostic.

## 5. What the protocol must require from an independent scheme

These requirements are the operational answer to the acceptance item; they are
adopted in §4/§5 of `convergence_protocol.md`.

- **R1 — declare the functional.** Every report carries `energy_functional`:
  name, formula, quadrature, boundary treatment, `structural_class` ∈
  {`exact_discrete`, `convergent`, `consistency_only`}, and `solver_tolerance`
  for implicit/iterative solves.
- **R2 — exact discrete conservation.** If `structural_class = exact_discrete`:
  drift ≤ `max(1e-12, 10 × solver_tolerance)`. Under R1, lffd (`3.38e-15`) and
  cnfd (`1.11e-14`) both pass; no scheme is asked to conserve another's
  functional.
- **R3 — convergent diagnostics.** Otherwise: drift must decrease at order
  ≥ `p_decl − 0.5` across at least three rungs **and** the finest rung must be
  ≤ `1e-6`. A fixed absolute threshold at a single coarse rung (candidate G3's
  `1e-8` at n = 64) is not admissible.
- **R4 — no cross-scheme functional gates.** Scheme A's functional must never be
  a pass/fail criterion for scheme B. Cross-functional evaluation is allowed
  only as a labelled *mismatch diagnostic*; it converges to zero but says
  nothing about solver quality.
- **R5 — order with uncertainty.** Report `p ± δ`,
  `δ = max(pair-spread half-range, least-squares standard error)`. Two schemes
  agree when `|p_A − p_B| ≤ max(0.25, sqrt(δ_A² + δ_B²))`. Measured:
  lffd `1.9958 ± 6.05e-04`, cnfd `1.9935 ± 1.82e-03`, `|Δ| = 0.0023` → agree
  under the 0.25 floor. With three points the strict statistical combination
  (`1.9e-03`) is marginally exceeded, so the floor must be stated explicitly;
  it exists to avoid over-tight agreement claims from three-point fits.
- **R6 — thresholds are frozen with the report.** The functional definition and
  every tolerance are part of the hashed submission. Changing a threshold
  requires a new report plus a written rationale; moving a threshold to pass is
  a gate-integrity violation (adjudication item 5).

### 5.1 End-to-end check on the real replication schemes

`numerics/protocol/build_gate_reports.py` builds a `n0-convergence-report/v1`
report for each replication scheme (read-only import of the solvers) and runs
the reference audit:

| scheme | functional reported (R1) | fitted order | δ | finest drift | audit |
|---|---|---:|---:|---:|---|
| lffd | leapfrog staggered energy | 1.9977 | 4.2e-05 | 3.19e-15 | PASS C0–C9 |
| cnfd | average-acceleration invariant | 1.9948 | 1.21e-03 | 1.22e-14 | PASS C0–C9 |

Cross-scheme agreement (R5): `|Δp| = 0.00286 ≤ max(0.25, sqrt(δ₁² + δ₂²))` →
agree. Both schemes pass **because each reports its own structural invariant**;
the same pair fails under a single fixed functional (cnfd `6.59e-8` at
`dr = 0.05` against the candidate's `1e-8`). This is the concrete acceptance
test for R1–R4 and it is reproducible in 0.3 s.

The same protocol applied to the candidate's current published results
(`audit_candidate_results.py`, pinned snapshot `e9e124227c4d2932`): the pulse
study audits **PASS C0–C9** (order 1.98–2.00, drift order ≈ 5), while the
single-mode standing study fails **C2 only** — by V2, a single-mode study at one
time is supporting evidence, not standalone order certification. Its order,
residual, Richardson and invariant checks all pass; the protocol rejects the
*configuration*, not the scheme.

The fits above use the L∞ error series computed by the builder. Refitting the
published integral-L2 series gives lffd `1.9958` and cnfd `1.9935`
(`artifacts/flash-12/n0/replication_recheck.json`), within `0.003` of the table
— the same agreement, different norm; nothing here contradicts the replication
report.

## 6. Falsifier test requested by the adjudication

> "The scheme-dependence finding is falsified if a non-leapfrog scheme passes
> the leapfrog-functional gate on the same configuration."

**Result: falsified as written.** cnfd is not leapfrog; its harness-functional
drift is `6.594e-08 ≤ drift_tol = 1e-6`; the pinned JSON records
`harness_gate_would_pass = true` for cnfd, and my independent reproduction
confirms it. The finding's sentence *"their harness-functional drift is far
above drift_tol=1e-6"* is false for cnfd.

The residual, defensible claim is:

> At the candidate's `1e-8` threshold applied to the leapfrog functional, lffd
> passes (`3.38e-15`) and cnfd fails (`6.59e-08`); at `1e-12` both non-leapfrog
> pairings fail. Scheme discrimination is real **for a fixed tight threshold on
> a fixed functional**, and disappears at `1e-6` or under one refinement of the
> grid.

## 7. Recommended dispositions (owners are other agents; no edits made here)

1. **Re-pin** the replication run against the current
   `flat_wave_replication.py` hash and re-run before the adjudication is used.
2. **Adjudication text correction**: withdraw "far above drift_tol=1e-6" and
   "own energies to ~1e-13 or better"; record that the pinned cnfd functional
   was the leapfrog form, and that the falsifier is triggered at the harness
   threshold.
3. **Replication harness**: replace the invariant pass/fail with R1–R4; keep
   the leapfrog functional only as a labelled cross-check diagnostic.
4. **Candidate `flat_wave.py` G3**: adopt R1/R3 — report the staggered energy
   (exact differences) for the leapfrog-family scheme, at a reachable budget,
   or report the `np.gradient` diagnostic's order and drop the unreachable
   `1e-8`.
5. **cnfem**: the pinned adjudication's cnfem failure (order −0.0773, drift
   1.0e+01) is reported fixed at the current revision `8ade1cdc…` by the
   independent recheck `artifacts/flash-12/n0/replication_recheck.json`
   (cnfem order `1.9863`, selftest pass). This review does not re-adjudicate
   cnfem; the claim is recorded as a peer recheck, not as this worker's
   measurement.

## 8. Falsifiers for this review

- F1: the identity claim is falsified if `E_sym` and `E_leap` differ by more
  than `1e-12` relative on the pinned trajectory — measured gap `2.07e-15`.
- F2: the "threshold flip" claim is falsified if cnfd's leapfrog-functional
  drift at `dr = 0.025` exceeds `1e-8` — measured `4.170e-09`, so it passes.
- F3: R4 is falsified if a single functional is exactly conserved (≤ 1e-12) by
  two schemes from different families under this configuration.
- F4: the whole review is falsified if the pinned run can be reproduced from the
  recorded `script_sha256 = 07e5a39b…`, i.e. if the current file hash
  `8ade1cdc…` is not a post-run edit.

## 9. Reproduction

```bash
python3 numerics/protocol/scheme_independence_check.py
python3 numerics/protocol/build_gate_reports.py     # writes report_lffd.json, report_cnfd.json
python3 numerics/protocol/audit_convergence_report.py --root . numerics/protocol/report_cnfd.json
python3 numerics/protocol/audit_convergence_report.py --compare numerics/protocol/report_lffd.json numerics/protocol/report_cnfd.json
```

Deterministic, no network, no randomness, < 1 s on one core; read-only with
respect to every file owned by another worker. Environment: Python 3.10.12,
NumPy 2.2.6, Linux x86_64.

## 10. Final verdict for `astra-numfix-03` (FIXED replication, re-pinned)

Assignment `astra-numfix-03` (2026-09-11T23:40:52+08:00) asks two questions about
`runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json`
(sha256 `6542db93eebc5095…`, pinned in the map's G-NUM `evidence_refs`) and asks
for a hash-cited verdict, no gate self-pass. Verifier:
`numerics/protocol/verify_fixed_scheme_independence.py` (sha256
`a0daf1271bfb556d…`); raw output `numerics/protocol/fixed_replication_verdict.json`
(sha256 `dcad962324e3be15…`), run 2026-09-12T00:05+08:00.

**Re-pin status (closes §2/§7.1).** The FIXED run's recorded hashes match the
on-disk files exactly: `script_sha256 = 8ade1cdc163ea420…` (= current
`flat_wave_replication.py`), `n0_harness_sha256 = 0646de3f75bd4335…` (=
`artifacts/flash-04/n0_acceptance/harness.py`), `f0_taxonomy_sha256 =
66bf917bd368ebd9…`. The stale-pin objection to the 23:24 adjudication no longer
applies to this run, and the FIXED run is the only replication pinned in the
G-NUM evidence list.

### Q1 — is the invariant functional now scheme-appropriate?

**Yes for the per-scheme R1/R2 criterion; no for the harness gate taken alone.**
The FIXED run now reports a distinct `own_energy_kind` per scheme, and this
verification re-measured each one independently at the pinned script hash:

| scheme | own functional (R1) | own drift (R2) | re-measured | R2 ≤ 1e-12 | harness-functional drift | harness / own |
|---|---|---:|---:|---|---:|---:|
| lffd | leapfrog staggered energy (= harness functional) | 3.383e-15 | 3.383e-15 | PASS | 3.383e-15 | 1.0 |
| cnfd | average-acceleration invariant `½|V|² − ¼⟨Aψ₁,ψ₁⟩ − ¼⟨Aψ₀,ψ₀⟩` | 1.109e-14 | 1.109e-14 | PASS | 6.594e-08 | 5.95e6 |
| cnfem | P1-FEM discrete energy `½VᵀMV + ¼ψ₁ᵀKψ₁ + ¼ψ₀ᵀKψ₀` | 2.044e-14 | 2.044e-14 | PASS | 8.482e-09 | 4.15e5 |

- Each scheme is now judged by **its own** structural functional, so no scheme is
  asked to conserve another family's invariant (R1/R2/R4 substantively met).
- The harness invariant gate itself is still **not scheme-appropriate**: it
  evaluates the leapfrog staggered energy on every trajectory, and its
  `drift_tol = 1e-6` passes cnfd (`6.594e-08`) and cnfem (`8.482e-09`) although
  each is 10⁵–10⁶ × above its own drift. A harness `invariant_status = PASS`
  therefore bounds the *leapfrog* functional and is **not** evidence that a
  non-leapfrog solver conserves its own invariant. It must stay a labelled
  cross-check diagnostic (R4), which is exactly the residual noted in
  `what_remains_true` of the FIXED file.

### Q2 — does the order fit method carry an uncertainty?

**No in the run as submitted.** The FIXED run reports `fit_order` (an
`np.polyfit` slope on three log-log points), `pair_orders`, and a fixed
`|p − 2| ≤ 0.3` tolerance; it carries no covariance, standard error, or δ. Per
R5, δ is `max(pair-spread half-range, least-squares standard error)`:

| scheme | p (3-point LSQ) | standard error | pair half-range | δ | re-measured p | re-measured δ |
|---|---:|---:|---:|---:|---:|---:|
| lffd | 1.995770 | 6.05e-04 | 1.05e-03 | 1.05e-03 | 1.995770 | 1.05e-03 |
| cnfd | 1.993478 | 1.82e-03 | 3.15e-03 | 3.15e-03 | 1.993478 | 3.15e-03 |
| cnfem | 1.986324 | 1.59e-03 | 2.75e-03 | 2.75e-03 | 1.986324 | 2.75e-03 |

R5 cross-scheme agreement (`floor = 0.25`, all pairs, published and re-measured):
`|Δp| = 2.29e-03` (cnfd–lffd), `7.15e-03` (cnfd–cnfem), `9.45e-03` (cnfem–lffd),
all `≤ max(0.25, sqrt(δ_A² + δ_B²))` → **agree**. The independent re-measurement
reproduces every published `fit_order` to `< 1e-3` (printed values identical) and
every δ. Note δ is norm-dependent: the L∞ series in §5.1 gives lffd `4.2e-05`,
cnfd `1.21e-03`, whereas the published L2 rows give `1.05e-03`/`3.15e-03` — same
verdict, but a report must name the norm it fitted (added as R5a below).

### Verdict sentence (input to G-NUM; no gate self-pass)

Scheme independence of the measured order-2 result is **established for this
configuration** by three independent discretisations (lffd reference-family
control, cnfd 3-point FD + Crank–Nicolson, cnfem P1 FEM + Crank–Nicolson):
`p = 1.9958/1.9935/1.9863` agree within their R5 uncertainty, and each scheme
conserves a family-appropriate discrete functional to ≤ 2.1e-14. The FIXED
evidence satisfies R1/R2/R4 in substance. Two **format/protocol conditions**
remain, neither of which changes a measured number: (i) the run output must carry
δ in the fit record (R5), currently supplied only by this post-hoc verification;
(ii) the acceptance text must demote the harness leapfrog functional to a labelled
cross-check (R4) rather than a scheme-independent conservation gate. This is a
worker-level technical verdict for lead-numerics/Astra; it does not set G-NUM,
does not mark N0 done, and does not serve as the independent A1 audit.

Protocol amendment adopted here:

- **R5a — name the norm.** Every order fit reports the error norm (L2 integral,
  L∞, …), the rung set, the fit method, and δ. Agreement verdicts compare δ from
  the same norm; cross-norm comparisons are diagnostics only.

### Falsifiers for this section

- **F5 (Q1):** a scheme whose declared `own_energy_kind` is not family-appropriate
  or whose own drift exceeds `1e-12` — measured 3.4e-15/1.1e-14/2.0e-14, so F5 is
  not triggered.
- **F6 (Q2):** a recomputation in which δ exceeds `0.25` while `|Δp|` still passes
  the floor, or `|Δp| > max(0.25, sqrt(δ_A²+δ_B²))` — measured max `|Δp| =
  9.45e-03`, max δ `3.15e-03`; not triggered.
- **F7 (harness appropriateness):** a non-leapfrog scheme whose
  harness-functional drift is `≤` its own drift (which would make the harness
  functional scheme-appropriate after all) — measured ratios 5.95e6 (cnfd) and
  4.15e5 (cnfem); not triggered.
- **Whole-section falsifier:** re-running `verify_fixed_scheme_independence.py`
  against a FIXED file whose hash differs from `6542db93eebc5095…` reproduces
  nothing above; the verdict is bound to that hash only.

### Reproduction

```bash
python3 numerics/protocol/verify_fixed_scheme_independence.py
# writes numerics/protocol/fixed_replication_verdict.json
```
