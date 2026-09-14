# Early findings from DeepSeek Flash pilot

This report summarizes the five-role run completed on 2026-09-11. Raw model drafts remain in `runs/`; they are not theorem proofs.

## Findings that survived first audit

1. The formulation is a family, not one binary question. The most consequential free fields are the singularity notion, horizon notion, target of visibility (`I+` versus finite-radius observers), initial-data/genericity class, and extension regularity.
2. A numerical naked-singularity signal is insufficient. The minimum discriminator must combine an invariant curvature diagnostic, an apparent/event-horizon analysis, causal-ray propagation toward the declared asymptotic boundary, resolution convergence, gauge cross-checks, and perturbation/stability tests.
3. The spherical Einstein–scalar problem is a calibration model only. It can test the pipeline and reproduce dispersion/black-hole/critical regimes, but it cannot by itself support or refute 4D asymptotically-flat vacuum WCC.
4. The smallest useful computational loop is parameter bisection around a critical amplitude, with observables including `2m/r`, null expansions, horizon radius, curvature invariant, constraint residuals, energy balance, and escaping null rays.
5. Swarm failure modes are mainly epistemic: simulation-to-theorem conflation, treating absence of a detected horizon as a naked singularity, confusing coordinate blow-up with curvature blow-up, and overgeneralizing a symmetry-restricted matter model.

## Corrections applied to model drafts

- Some drafts incorrectly bundled weak and strong censorship and inserted contradictory claims such as “generic data are future incomplete” as part of the strong statement. These are removed from the canonical formulation.
- “Dominant energy condition” is not a substitute for the exact vacuum initial-data and asymptotic hypotheses. The ledger must retain the constraint equations and weighted function spaces.
- `C0` inextendibility, `C2` inextendibility, and weak-Einstein extendibility are separate SCC variants; no single result may be cited for all three.
- The PG relation `dr/dt = alpha - beta` and `g^{rr}=0` are coordinate/model-specific diagnostics, not universal definitions of visibility or event horizons.

## Current evidence grade

The run itself is grade **D** as evidence about cosmic censorship and grade **C** as research-planning input: it generated a coherent checklist and pilot design, but no new theorem, verified citation ledger, or numerical evolution was performed.

## Next concrete actions

- F1: human/agent referee rewrites weak and strong statements with exact quantifiers and a declared weighted Sobolev topology.
- L1: verify every bibliographic entry against primary papers before importing it into `research/knowledge`.
- N1: implement flat-space scalar-wave and constraint tests before self-gravity.
- A1: make G1–G8 a machine-readable gate and reject any response that lacks scope or provenance.
- S1: schedule a 90-day program only after M1 formulation consistency passes.
