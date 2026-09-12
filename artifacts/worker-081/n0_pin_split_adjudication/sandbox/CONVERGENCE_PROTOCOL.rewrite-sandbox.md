# Numerical convergence and invariant protocol (N0, flat space)

Owner: `astra-lead-numerics`.  Status: **draft for independent review** (G-NUM requires the
protocol to be reviewed by audit).  Class binding: `AF-WCC-SCALAR-SPH`, **calibration
sub-case** (test field, fixed Minkowski; N0 does not exercise the Einstein-coupled class).
The F0 taxonomy artifact now exists and is hash-pinned at
`research_map/formulation_taxonomy.yaml#0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`; G-F0 is still pending, so the binding
stays provisional.  Revision 2 (2026-09-12) adopts the scheme-appropriate invariant and
order-uncertainty rules R1–R5a from the independent scheme-independence review
(`numerics/protocol/scheme_independence_review.md`); revision 3 requires `>= 4` rungs for an
order-certification claim and closes audit finding C2.  See the revision log at the end.

## 1. Scope

This protocol governs **flat-space scalar-wave calibration only**: massless real (and, for one
invariant, complex) scalar field on a fixed Minkowski background.  It defines how a measured
convergence order is produced, what must be invariant, and which controls must fail.  It does
not define, authorise, or prepare any self-gravitating evolution; see `numerics/blockers.md`.

Equations and conventions:

* spherical, l = 0: `psi_tt = psi_rr + (2/r) psi_r`, regular at `r = 0` (`psi_r(t,0) = 0`);
* reduced variable `u = r*psi` (worker artefacts use the letter `v`): `u_tt = u_rr`,
  `u(t,0) = 0`;
* first-order reduction: `psi_t = Pi`, `Pi_t = L[psi] + S`, `Phi = psi_r`;
* Cartesian periodic control: `psi_tt = psi_xx + S`.

## 2. Discretisations under test

| id | scheme | role |
|---|---|---|
| A | reduced-variable central stencils, orders 2 and 4, Dirichlet at both walls | canonical artifact `numerics/tests/flat_wave.py` |
| B | independent scheme, different stencil/method | replication `numerics/tests/flat_wave_replication.py` |
| C | staggered finite-volume SBP in `psi` (`Pi` at centres, `Phi` at faces, zero flux at origin) | lead reference `numerics/tests/lead_calibration.py` |
| D | collocated naive `D2 + (2/r)D1` | **non-SBP control** (must leak energy at O(h²)) |
| E | periodic Cartesian central stencils, orders 2/4/6 | dispersion and invariant controls |

Scheme C satisfies summation by parts with respect to
`E = 1/2 sum_i V_i Pi_i^2 + 1/2 h sum_f A_f Phi_f^2`, so its semi-discrete energy law is
exactly `dE/dt = A_N Phi_N Pi_{N-1}` (boundary flux only).  This is used as a *measured*
identity, not assumed.

## 3. Convergence methodology

1. **Closed-form comparison.** Every measured order comes from comparing the numerical
   solution to an exact solution evaluated at the same time: manufactured solutions
   (`CartesianMMS`, `SphericalMMS`) and the exact regular d'Alembert pulse
   `psi = [F(t-r) - F(t+r)]/r`.
2. **At least four resolutions for an order-certification claim**, refinement ratio 2, errors in
   a weighted L2 norm (`sum V_i e_i^2 / sum V_i`) and L-infinity. A three-resolution study is
   admissible only as a *supporting diagnostic* and must carry the R5 uncertainty below; on its
   own it does not certify an order. (Revision 3 closes audit finding C2: the A0 rubric's G-NUM
   criterion requires >= 4 resolutions, and the replication order claim is carried at four rungs
   in `numerics/tests/n0_order_4rung.json`.)
3. **Observed order** `p_i = log(e_i/e_{i+1}) / log(h_i/h_{i+1})`, plus a least-squares fit
   of `log e` vs `log h` over all resolutions.  Order claims use the fit; a single lucky
   pair is not evidence.
4. **Temporal/spatial separation.** Spatial order is measured with a fixed, small `dt`
   (`1e-4`) so RK4 error is negligible; temporal order is measured separately by fixing `h`
   and refining `dt` (`dt ∝ h` runs are reported as mixed-order and never quoted as spatial).
5. **Eigenfunction trap.** A single Fourier mode is an exact eigenfunction of the central
   second-derivative stencil, so its error is pure RK4 time error and masquerades as
   `p = 4` for a second-order scheme.  Manufactured data must contain at least two modes
   not all resolved exactly by the stencil (defect found in worker 12's first draft,
   recorded in `artifacts/numerics/reviews.jsonl`).
6. **Acceptance band.** Measured order must lie within `|p - p_design| <= 0.3` for the
   canonical studies and `<= 0.35` for the reference studies.  Failing the band is a
   finding: it must be reported as a blocker, not smoothed over.
7. **Determinism.** Repeated runs must agree bitwise on field data; wall-clock fields are
   excluded from equality tests (they are not physics).
8. **Order carries an uncertainty (R5).** Every order claim reports `p ± delta` with
   `delta = max(pair-spread half-range, least-squares standard error)` over the fitted rungs,
   and names the error norm (L2 integral or L-infinity) that was fitted (R5a). Two schemes
   agree when `|p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2))`. The 0.25 floor is
   explicit: it prevents over-tight agreement claims from short log-log fits. A three-rung
   fit is admissible only as a *supporting diagnostic* with this uncertainty recorded;
   **four or more rungs are required for an order-certification claim** (the canonical artifact
   uses five rungs per study and the lead 4-rung replication driver
   `numerics/protocol/lead_4rung_replication.py` adds `dr = 0.025` to the harness set).

## 4. Invariant diagnostics (all measured, with resolution scaling)

| invariant | definition | expected behaviour |
|---|---|---|
| SBP energy identity | `dE/dt - (A_N Phi_N Pi_{N-1})` on the scheme-C operators | 0 to machine precision |
| energy budget | `E(T) - E(0) - integral(flux dt)` | residual -> 0 with `dt` (RK4 order) |
| continuum flux closure | numeric flux integral vs `A_N Pi_ex(R,t) Phi_ex(R,t)` | convergence order >= 1.5 |
| spectral energy | `h/2 sum(Pi^2 - psi D2 psi)` (periodic) | exactly conserved; drift ~ `dt^4` |
| gradient energy defect | `|E_grad - E_spectral| / E` | O(h^p): the two quadratic forms differ by an O(h^p) operator for every order p (measured: 2, 4, 6) |
| momentum | `h sum Pi D1 psi` (periodic) | conserved to integrator order |
| U(1) charge | `h sum Im(conj(psi) Pi)` (complex field) | conserved to integrator order |
| constraint | `max_f |Phi_f - (psi_f - psi_{f-1})/h|` | preserved to roundoff; init defect O(h^p) |
| origin regularity | face-0 flux identically zero; `psi(0)` error convergence | no blow-up; order p |
| dispersion | measured frequency vs exact symbol `sqrt(-symbol_d2(k,h))` | agree to integrator order; phase-speed error -> 0 at order p |

Transport thresholds used by the lead reference gates: spectral-energy, momentum and charge
relative drift `< 1e-9`; SBP identity and constraint `< 1e-12`; budget residual `< 1e-5`
relative.

### 4.1 Scheme-appropriate invariants (R1–R4, revision 2)

A discrete functional is a property of a (scheme, stencil, quadrature) triple, not of the
PDE alone.  The following rules replace any single fixed functional used as a pass/fail gate
for every scheme:

* **R1 — declare the functional.** Every report carries `energy_functional`: name, formula,
  quadrature, boundary treatment, and `structural_class` in
  {`exact_discrete`, `convergent`, `consistency_only`}.
* **R2 — exact discrete conservation.** If `structural_class = exact_discrete`, drift must be
  `<= max(1e-12, 10 x solver_tolerance)`.  Measured under this rule: leapfrog staggered
  energy `3.38e-15`, CN-FD average-acceleration invariant `1.11e-14`, CN-FEM discrete energy
  `2.04e-14` — all pass, each on its own functional.
* **R3 — convergent diagnostics.** Otherwise drift must decrease at order
  `>= p_decl - 0.5` across at least three rungs and the finest rung must be `<= 1e-6`.
  A fixed absolute threshold at a single coarse rung is not admissible.
* **R4 — no cross-scheme functional gate.** Scheme A's functional must never be a pass/fail
  criterion for scheme B.  Evaluating the leapfrog staggered energy on a Crank–Nicolson
  trajectory is allowed only as a labelled *mismatch diagnostic*: it converges to zero
  (measured order ~3.8–4.0 under refinement) but says nothing about the other solver's
  conservation.  The harness's `drift_tol = 1e-6` is therefore a diagnostic threshold, not a
  scheme-independent conservation gate.  Falsifier (F7): a non-leapfrog scheme whose
  harness-functional drift is `<=` its own drift — not observed (ratios 5.95e6 cnfd, 4.15e5
  cnfem at `dr = 0.05`).

## 5. Negative controls (must fail)

* **frozen-in-time solver** — order ~ 0, must be rejected;
* **sign-flipped Laplacian** — unbounded growth, must be rejected;
* **CFL violation** (`cfl = 1.5`, `max|lambda| dt > 2.828` for RK4) — growth > 10x, must be
  rejected, while `cfl = 0.25` must not be flagged;
* **naive collocated scheme (D)** — converges but its semi-discrete energy residual must be
  many orders larger than the SBP scheme's: measured O(h) full residual (boundary-closure
  dominated) and O(1) volume defect, because the centred D1 is not the weighted SBP adjoint
  of itself for r² weights; the SBP scheme's identity is exact to machine precision.

A calibration run that accepts any control is invalid regardless of its orders.

## 6. Replication rule (G-NUM)

Worker 12 produces scheme A; worker 13 must reproduce the measured order with a *different*
discretisation (scheme B), documenting differences.  The two reported primary orders must
agree within `0.35` absolute.  Disagreement is a first-class finding and blocks G-NUM until
resolved.  The lead reference (scheme C) is a third check and is reported alongside.

**Revision 2 amendments.** (a) The agreement test is the R5 rule
`|p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2))`, with both fits using the same norm.
(b) Each scheme is judged on its own declared invariant (R1/R2/R4); the harness functional is
reported separately as a cross-check.  (c) A replication that fails an order gate is not
excluded for disagreeing: it needs a shown root cause and either a fix at a new hash or a
formal exclusion with evidence (precedent: the CN-FEM sign error, root cause and fix recorded
in `numerics/tests/replication_triage.md`).  (d) The replication evidence must be re-pinned
at the current script, harness, and taxonomy hashes before it is used in a gate proposal.

**Revision 3 amendment.** (e) An order-certification claim requires `>= 4` rungs per scheme
(§3.2). The controller's 3-rung replication run is supporting evidence; the certified fit is the
4-rung addendum `numerics/tests/n0_order_4rung.json`, which extends the frozen run without
editing it. This resolves audit finding C2 by amending the protocol of record rather than the
rubric, and it is recorded here rather than applied silently. The F0 taxonomy pin cited in the
controller run (`66bf917b…`) is superseded on disk by `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3…`; the class binding stays
**provisional** and is not load-bearing for the order claim.

## 7. Evidence and artifact schema

Every study writes machine-readable JSON containing: `study`, `order_scheme`, `rows`
(resolution, step, errors, invariants), `orders`, `fitted_order`, `gates`.  Reports are
hash-registered through `artifact` events (`comms/outbox/astra-lead-numerics.jsonl`).
A node is not complete on fluent text; it needs the artifact on disk, its sha256 in
`runtime/state/artifact_hashes.json`, and a reviewer verdict (PROTOCOL.md rule 2).

## 8. What this protocol does not establish

Numerical convergence at a measured order is **numerical evidence about a discretisation**.
It is not a theorem, not a statement about weak or strong cosmic censorship, and not evidence
about collapse, horizon formation, or critical behaviour.  No result here may be promoted
above `conclusion_type: numerical_evidence`.

## Revision log

* **rev 3 — 2026-09-12, `astra-lead-numerics`.** §3.2 now requires `>= 4` resolutions for an
  order-certification claim (three rungs = supporting diagnostic only); §3.8 and §6 carry the
  same rule as amendment (e).  Reason: audit review `reviews/G-NUM-protocol-review.json`
  (verdict `revise`, no hard failures) finding **C2** — the A0 rubric requires `>= 4`
  resolutions while this protocol required `>= 3`, and the controller run used three.  The
  4-rung evidence already exists (`numerics/tests/n0_order_4rung.json#c88146a1375c50f0`);
  this revision makes the protocol text agree with it instead of amending the rubric.
  No measured number changed; the flat-space scope and the N1 lock are unchanged.  The
  superseded revision-2 hash is `3345e17d2be3e403…` and the audit pin
  `01b2072434cd0783…` predates revision 2, so no accepting verdict is invalidated by this
  write (there was none).
* **rev 2 — 2026-09-12, `astra-lead-numerics`.** Adopted R1–R5a from the independent
  scheme-independence review (`numerics/protocol/scheme_independence_review.md`,
  `numerics/protocol/fixed_replication_verdict.json`): per-scheme structural invariants
  (R1/R2), convergent-diagnostic rule (R3), harness functional demoted to a labelled
  cross-check (R4), order uncertainty and agreement rule (R5), named norm (R5a), 4-rung
  preference.  Reason: the 23:24 controller adjudication applied one scheme's functional to
  another and treated a 3-point fit as an order claim.  No measured number changed; the
  flat-space scope and the N1 lock are unchanged.
* **rev 1 — 2026-09-11, `astra-lead-numerics`.** Initial protocol for G-NUM review.
