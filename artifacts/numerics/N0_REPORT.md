# N0 — flat-space scalar-wave calibration: lead report

Node: **N0** (`numerics/tests/flat_wave.py`) · Group: numerics · Lead: `astra-lead-numerics`
Class binding: `AF-WCC-SCALAR-SPH` (**provisional** — F0 taxonomy committed but G-F0 review pending)
Date: 2026-09-11 · Run: `run-2026-09-11T23:15+08:00` · Deadline: 2026-09-12T03:15:11+08:00

Scope discipline: **flat space only.** No self-gravitating solver code was written or run;
`numerics/spherical_solver/` does not exist; N1 remains locked (`numerics/blockers.md`).

## 1. Bottom line

Three independently written discretisations of the flat-space massless scalar wave equation
measure **second-order convergence on closed-form solutions** and agree:

| implementation | method | primary measured order | gates |
|---|---|---:|---|
| canonical (`flat_wave.py` rev `8b52014d`) | MOL RK4, reduced variable `v = r·u`, central FD orders 2/4 | **2.0000** (8 samples) | 11/11 pass |
| replication (`flat_wave_replication.py` rev `8ade1cdc`) | implicit Crank–Nicolson + 3-pt FD, and CN + P1 FEM | **1.9935 / 1.9863** | self-test pass, verdict ORDER REPRODUCED |
| lead reference (`lead_calibration.py` rev `dc369e3d`) | staggered finite-volume SBP spherical scheme + periodic Cartesian 2/4/6 | **2.0006** (6 samples) | 10/10 pass |

Maximum disagreement **0.0101**, tolerance 0.35. Invariant diagnostics: SBP semi-discrete
energy identity residual **7e-18** (machine precision), constraint preserved to <1e-13,
boundary-flux closure order **2.00**, dispersion symbol match **4e-16**, complex U(1) charge
drift **1.5e-13**, spectral energy drift **9e-13**.

This is `conclusion_type: numerical_evidence` about discretisations. It is not a theorem, and
it makes no statement about weak/strong cosmic censorship, collapse, horizons, or critical
behaviour.

## 2. What was measured

Canonical artifact, `--all` on rev `8b52014d` (lead re-ran it; stdout archived by worker 12):

| study | resolutions | pair orders (L2) |
|---|---|---|
| standing, order 2, `t=0.37` | 64…1024 | 2.006, 2.003, 2.001, 2.001 |
| Gaussian pulse, order 2 | 64…1024 | 1.987, 2.000, 2.001, 2.001 |
| standing, order 4 | 32…512 | 4.312, 4.218, 4.032, 3.983 |

Negative controls all rejected: frozen-in-time solver (order 0), sign-flipped Laplacian
(unbounded), CFL=1.5 (growth 3.2e5), while CFL=0.25 is accepted. Temporal-error control: at
n=256, halving CFL moves the L2 error by <2%, so the measured order is spatial, not temporal.

Lead reference invariants (Cartesian periodic, orders 2/4/6; spherical staggered SBP):

| diagnostic | result |
|---|---|
| spherical MMS order | 2.000 (fit) |
| SBP identity `dE/dt = A_N Φ_N Π_{N-1}` | residual 0 / 7e-18 |
| constraint `Φ_f − (ψ_f−ψ_{f−1})/h` | max < 1e-13, preserved exactly |
| outgoing-pulse boundary-flux closure vs continuum | order 1.998–2.000 |
| pulse energy left behind after crossing R | 1.2e-4 (finest), decreasing as h² |
| dispersion: measured ω vs exact symbol | rel. diff < 1e-6 (RK4 floor) |
| phase-speed error order | 2.00 / 4.00 / 6.00 for stencil orders 2/4/6 |
| gradient–spectral energy defect order | 2.00 / 3.99 / 5.99 (the two quadratic forms differ at O(h^p)) |
| non-SBP collocated control | full residual O(h), volume defect O(1) vs SBP 7e-18 (>1e15×) |

## 3. Defects found and fixed during calibration

Calibration caught its own errors; each is recorded rather than hidden.

1. **Eigenfunction trap (canonical draft).** A single Fourier mode is an exact eigenfunction
   of the central second-derivative stencil, so the order-2 study measured 4.00 — pure RK4
   time error masquerading as spatial order. Fixed by using a generic time `t=0.37`
   (documented: `t=0.5` is half a period where the leading O(h²) term cancels) and a
   temporal-error control gate (G9).
2. **Drift tolerance at the coarsest grid (canonical draft).** Pulse energy drift was bounded
   by 1e-6 at n=64, where the integrator legitimately has larger error; replaced by
   finest-resolution bound plus monotone decrease.
3. **Determinism check compared `wall_seconds`** — not physics; excluded.
4. **Zero-mean momentum normalisation (lead).** A standing wave has P ≡ 0, so relative drift
   divided by zero. Switched to a travelling-wave state and max-|value| scale.
5. **Wrong order-2 expectation for the energy defect (lead).** `−D1ᵀD1 ≠ D2` (their stencils
   differ at O(h²)); the defect scales as O(h^p) for every p. Protocol corrected.
6. **Collocated control expectation (lead).** With r² weights, centred D1 is not its own SBP
   adjoint; the volume defect accumulates to O(1), worse than the assumed O(h²). Control
   re-stated at the measured orders; this strengthens the SBP choice.
7. **Near-zero normalisation in the pulse energy check (lead).** After the pulse leaves the
   domain the exact interior energy is ~0; replaced by the absolute remaining fraction.
8. **Missing acceptance item (canonical draft).** The first `--all`-passing revision had no
   N1 lock guard. Revision requested and delivered: `lock_guard()` delegating to
   `numerics.gates`, `--lock-guard` CLI, gate `G11_n1_lock_guard`.

## 4. Gate and lock status

* `G-NUM` (owner: lead-numerics): **pending**. Criteria: order measured ✓, replicated ✓
  (delta 0.0101), protocol reviewed ✗, lock guard ✓.
* Outstanding N0 requirement: an **independent audit review** of
  `numerics/CONVERGENCE_PROTOCOL.md` (resource request
  `lnum-resource-request-89be785d412886d5fff6`).
* `numerics_lock`: **locked** (since 23:15:11). Blocking reasons from
  `python3 -m numerics.gates --check` (exit 3): lock state, G-FORM pending, G-AUDIT pending,
  protocol review missing.
* N1 blocker contract: `numerics/blockers.md` (rev `e0b6ca74`) — checklist 1:1 with the map,
  explicit non-conditions, guard tests, and the post-release procedure.

## 5. Evidence chain

All events were validated by `research_map/comms.py ingest --dry-run` and accept cleanly
(17 events, no rejects). Primary stream: `comms/outbox/astra-lead-numerics.jsonl`.
Mirrors: `artifacts/numerics/{artifacts,reviews,claims,blockers,status}.jsonl`.

| artifact | sha256 (16) |
|---|---|
| `numerics/tests/flat_wave.py` | `8b52014dac47f996` |
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420` |
| `numerics/tests/lead_calibration.py` | `dc369e3dc8d0b0b9` |
| `numerics/results/flat_wave_convergence.json` | `e9e124227c4d2932` |
| `numerics/results/flat_wave_replication.json` | `298a4d921c2264e6` |
| `artifacts/numerics/n0/lead_calibration_report.json` | `3272934c7b0873ab` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `01b2072434cd0783` |
| `numerics/blockers.md` | `e0b6ca74e5cb4543` |
| `numerics/gates.py` | `907a88b141bf4394` |

Checkpoints: `artifacts/numerics/CHECKPOINTS.jsonl` / `CHECKPOINTS.md`, 15-minute cadence
from 23:31 to the 03:15 deadline (`numerics/checkpoint.py --daemon`).

## 6. Not claimed

* No claim that N0 is complete: the protocol review is outstanding and the class binding is
  provisional.
* No claim about self-gravity, collapse, apparent horizons, critical phenomena, or
  outgoing radiation at I+.
* No claim about WCC or SCC. Nothing here may be promoted above `numerical_evidence`.
* The replication shares the *equation* and the closed-form references; its independence is
  in the discretisation and time integration, not in the problem definition.

## 7. Next falsifiers

1. An audit reviewer rejects `numerics/CONVERGENCE_PROTOCOL.md` — then the order protocol,
   not the code, is wrong and N0 must be re-scoped.
2. A fourth implementation measures a primary order outside 2 ± 0.35.
3. The canonical `--all` fails at the pinned sha `8b52014d` on re-run.
4. G-FORM passes with a taxonomy whose class definitions differ from the provisional binding
   used here — then the class-bound framing of these results must be revised.

## 8. Class-binding assessment against the F0 taxonomy (added 2026-09-11T23:40+08:00)

The F0 artifact `research_map/formulation_taxonomy.yaml` (sha256 `66bf917bd368ebd9…`) now
exists on disk. Checked against it, the provisional binding must be stated precisely:

* class `AF-WCC-SCALAR-SPH` has **H1**: "3+1 dimensional; Lambda = 0; Einstein equations
  coupled to a massless scalar field", and **H3**: asymptotically flat data with an MGHD.
* N0 exercises **neither**: the background is fixed Minkowski (no Einstein coupling), there
  is no I+/MGHD, and the outer boundary is a reflecting/outgoing calibration wall, not null
  infinity.

Therefore the defensible binding is: **N0 is the test-field (flat-space) calibration
sub-case of the class's matter sector**, not an instance of `AF-WCC-SCALAR-SPH`. It
calibrates the scalar wave operator, the discrete origin regularity condition, and the
invariant diagnostics that a later coupled solver must inherit. Passing G-NUM discharges no
formulation obligation.

The taxonomy itself records (line 465) that `AF-WCC-SCALAR-SPH` has **no schema node** in the
current map: F1/F2 cover only the three vacuum classes. If the scalar class is to be used
downstream, formulation should either add a schema node for it or point F-schemas at this
test-field sub-case explicitly. No numeric result here should be read as covering the
coupled class.

