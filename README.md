# Cosmic Censorship Swarm Review

<p align="center"><img src="assets/swarm-dag.svg" alt="Research plan DAG" width="100%"></p>

<p align="center"><img src="assets/progress-timeline.svg" alt="Swarm progress timeline" width="100%"></p>

> **Frozen collaborator review snapshot · 2026-09-15** The remote swarm is stopped. This repository preserves the evidence map, pilot traces, reviews, validation artifacts, and mathematical claim boundaries for a human collaborator. No WCC or SCC theorem has been promoted.

## Start here

1. Read the [初步 blog](docs/cosmic-censorship-swarm-review-20260915.html) for a visual, self-contained account of what the swarm learned and what it did not prove.
2. Open the [interactive review dashboard](docs/cosmic_censorship/pilot/review_dashboard.html).
3. Read the [mathematical progress explainer](docs/cosmic_censorship/pilot/mathematical_progress_explained_20260913.md) and the [Astra progress paper](docs/cosmic_censorship/pilot/astra_progress_paper_20260913.md).
4. Inspect the [evaluation report](docs/cosmic_censorship/pilot/evaluation_report.md), [gate checklist](docs/cosmic_censorship/pilot/gate_checklist.md), [role outputs](docs/cosmic_censorship/pilot/runs/), and [independent reviews](docs/cosmic_censorship/pilot/reviews/).
5. For provenance and integration details, read the [ai4math integration snapshot](docs/cosmic_censorship/pilot/ai4math_integration_snapshot_20260914.md).

## Current disposition

| Signal | Frozen value | Interpretation |
|---|---:|---|
| Recorded events | **9,367** | Last accepted event count in the project checkpoint |
| Registered artifacts | **656** | Files or evidence objects in the registry; not theorem count |
| Map validator | **VALID** | Research-map schema and references pass validation |
| Active remote sessions | **0** | No controller, supervisor, or worker is running |
| N1 self-gravitating numerics | **LOCKED** | Calibration is allowed; production search is gated |
| Promoted theorem | **0** | No WCC/SCC claim passed the scientific gates |

The remote run ended at the last checkpoint on 2026-09-14 22:59:46 +0800. There is no automatic refill, provider failover, or automatic push. Historical artifacts remain available for audit.

## What the swarm has done

- Split cosmic censorship into auditable classes: AF-WCC vacuum, AF-SCC-C2/C0, low-regularity extensions, spherical Einstein–scalar calibration, Kerr/Cauchy-horizon, charged, de Sitter, AdS, and higher-dimensional variants.
- Frozen the formulation fields: equations, dimension/topology, initial-data space, asymptotics, gauge, singularity, visibility, extension regularity, genericity, conclusion type, reproducibility, and evidence grade.
- Defined the research teams and dependency DAG: formulation, literature, geometry/PDE, numerics, counterexamples, symbolic/formal work, and reproducibility/review.
- Completed the first five-role DeepSeek Flash pilot (5/5), followed by four independent review roles (4/4).
- Rejected the first fluent formulation because it conflated WCC/SCC and C0/C2 and lacked sufficiently specified genericity, visibility, and citations.
- Recorded 592 finished group instances: formulation 145, literature 148, numerics 150, audit 149. These are execution traces, not accepted theorems.
- Captured the DeepSeek quota stop, quota circuit, stale-metadata correction, project namespace filtering, and recovery-probe hardening.

The old DeepSeek runners are retained only as historical reproducibility artifacts; they are not active launchers.

## Mathematical claim boundary

The useful output is a research map and an evidence protocol. It identifies which statement is being discussed, under which regularity and asymptotic assumptions, and what observation would count as evidence. It does not settle the conjecture. In particular:

- a visible causal boundary is not automatically a curvature blow-up;
- a C0 extension question is not a C2 inextendibility theorem;
- a spherical calibration is not evidence for generic 3+1 behavior;
- a numerical trend is not a proof without convergence, invariant diagnostics, and an independent rerun.

The 27-fixture regression suite is a software check, not a physical theorem. Its frozen result is TP=17, FP=0, TN=10, FN=0 for the fixed fixtures only.

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

This repository does not claim a proof or refutation of cosmic censorship. Counts such as 9,367 events, 656 artifacts, 592 historical instances, 5/5 roles, and 4/4 reviewers describe execution and review records; they do not replace theorem verification, citation checks, invariant diagnostics, convergence tests, or independent reproduction.
