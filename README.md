# Cosmic Censorship Swarm Review

<p align="center"><img src="assets/swarm-dag.svg" alt="Research plan DAG" width="100%"></p>

<p align="center"><img src="assets/progress-timeline.svg" alt="Swarm progress timeline" width="100%"></p>

> **Review status · 2026-09-12** Evidence-first review snapshot of the cosmic-censorship research swarm. The map, pilot, independent reviews, runtime evidence, and handoff risks are archived here. It is ready for a capped supervised collaborator pilot; it is not yet an unattended multi-provider production service.

## Start here

1. Open the [interactive review dashboard](docs/cosmic_censorship/pilot/review_dashboard.html).
2. Read the [partner-scale readiness note](docs/cosmic_censorship/pilot/partner_scale_readiness_20260912.md).
3. Verify the [evaluation report](docs/cosmic_censorship/pilot/evaluation_report.md), [gate checklist](docs/cosmic_censorship/pilot/gate_checklist.md), [role outputs](docs/cosmic_censorship/pilot/runs/), and [independent reviews](docs/cosmic_censorship/pilot/reviews/).
4. Read the [legacy swarm evidence audit](docs/cosmic_censorship/pilot/legacy_swarm_evidence_audit_20260913.md) for the honest classification of what is worth showing and what remains blocked.

## What the swarm has done

- Split cosmic censorship into auditable classes: AF-WCC vacuum, AF-SCC-C2/C0, low-regularity extensions, spherical Einstein–scalar calibration, Kerr/Cauchy-horizon, charged, de Sitter, AdS, and higher-dimensional variants.
- Frozen the formulation fields: equations, dimension/topology, initial-data space, asymptotics, gauge, singularity, visibility, extension regularity, genericity, conclusion type, reproducibility, and evidence grade.
- Defined the research teams and dependency DAG: formulation, literature, geometry/PDE, numerics, counterexamples, symbolic/formal work, and reproducibility/review.
- Completed the first five-role DeepSeek Flash pilot (5/5), followed by four independent review roles (4/4).
- Rejected the first fluent formulation because it conflated WCC/SCC and C0/C2 and lacked sufficiently specified genericity, visibility, and citations.
- Recorded 592 finished group instances: formulation 145, literature 148, numerics 150, audit 149. These are execution traces, not accepted theorems.
- Captured the DeepSeek quota stop, quota circuit, stale-metadata correction, project namespace filtering, and recovery-probe hardening.

## Current scientific and operational state

| Area | State | Review meaning |
|---|---|---|
| Formulation taxonomy | Established | Classes, fields, versions, and dependencies are reviewable |
| Scientific review | Working | Fluent but invalid scope was rejected |
| Literature/citations | Continuing | Primary-source verification remains required |
| Flat-space numerics | Calibration only | Self-gravitating production remains locked |
| Runtime lifecycle | Real evidence, needs hardening | Independent instances and trajectories are recorded |
| Multi-provider failover | Not complete | Adapter, account rotation, retry ledger, and drills remain |
| Unattended scale | No-go | First pass provider A→B and 5xx/timeout drills |

## Next research path

WP0 freezes terminology and formulation. WP1 builds the theorem ledger with source locations. WP2–WP3 complete spherical calibration, geometry, visibility, and convergence checks. WP4 handles low-regularity extension questions. WP5–WP6 begin axisymmetric/3D candidates only after formulation, literature, and audit gates are green. WP7–WP8 cover formalization, independent reruns, synthesis, and go/no-go.

## Evidence boundary

This repository does not claim a proof or refutation of cosmic censorship. Counts such as 592, 5/5, and 4/4 describe execution and review records; they do not replace theorem verification, citation checks, invariant diagnostics, convergence tests, or independent reproduction.
