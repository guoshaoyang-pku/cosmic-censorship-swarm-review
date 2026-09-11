# Research-map swarm architecture

## Current base

This project is based on `swarm-research/ai4math-swarm`. The base already has a useful verifier-gated search loop, heterogeneous proposer pool, dead-end ledger, reaper/resurrect behavior, per-family accounting, and run metrics. The new layer adds a persistent research map for open-ended problems where there is no single cheap verifier.

## Control hierarchy

`Human PI → Astra controller → group leads → execution agents`

The hierarchy is deliberately adaptive. Astra owns the global map, dependency consistency, portfolio allocation, and escalation to the Human PI. A group lead receives a fuzzy direction rather than a fixed task list. The lead can refine, split, merge, pause, or kill sub-directions, but every change is recorded as a versioned map event. Execution agents are cheap and parallel; they produce drafts, code, retrieval notes, tests, and replications.

Group leads should run at Astra-level reasoning when the decision is architectural or mathematical. DeepSeek Flash is appropriate for breadth work only after the lead has supplied a class-bound prompt, acceptance tests, and artifact schema.

## Research map as a DAG

The map has two layers:

1. a cross-group DAG connecting formulation, literature, numerics, audit, and synthesis;
2. a local sub-DAG per group, which can be rendered alone or embedded as a compound node in the global view.

Nodes are claims, hypotheses, experiments, proofs, datasets, code artifacts, or review gates. Edges express `depends_on`, `scope`, `calibration`, `evidence`, `refutes`, `supports`, or `blocks`. A node cannot be marked complete merely because an agent returned text; it requires the declared artifact and gate evidence.

Each group and node tracks:

- active agents and model tier;
- planned and spent agent-hours;
- wall-clock start and ETA interval;
- status and confidence;
- files, lines of code, Lean lines, datasets, and verified claims produced;
- unresolved blockers and next falsifier;
- provenance and reviewer decisions.

## Fuzzy directions and bidirectional communication

A direction is a portfolio hypothesis: a short statement, current confidence, expected information gain, stopping rule, and resource envelope. It is intentionally not a fixed specification. The group lead may submit `direction_update` events with the old statement, new statement, evidence that caused the update, budget delta, and dependency changes. Astra accepts routine changes, asks another lead to review high-impact changes, and escalates irreversible scope changes to the Human PI.

Communication is structured rather than transcript-based:

- upward: `status`, `claim`, `artifact`, `blocker`, `direction_update`, `resource_request`;
- downward: `assignment`, `budget`, `gate`, `priority_change`, `kill`, `revive`;
- sideways: distilled evidence packets between groups, with class IDs and provenance.

## Verification by task type

No-free-lunch means the verifier is task-specific. For Lean/Perelman-style formalization, the hard gate is the kernel plus build reproducibility; progress is unresolved lemma count, dependency depth, and checked lines. For cosmic censorship, the gate is an evidence graph: exact formulation class, primary-source verification, invariant diagnostics, numerical convergence, causal visibility, perturbation stability, and independent reproduction. A universal scalar score is forbidden.

## Parallelism and scaling

The first pilot should use 10–20 execution agents and 3–5 leads. Production should target 100+ agents. At 1000 agents, the bottleneck becomes coordination and verification, not model calls. The scheduler should therefore allocate by marginal value of information, not by filling a fixed concurrency quota. It should run a strong-model baseline, a cheap-agent arm, and a coordinator arm at matched token and wall-clock budgets.

The minimum scaling experiment compares one strong model, self-consistency, independent cheap agents, and cheap agents plus coordinator. Metrics are accepted-claim rate, hard-failure rate, citation support, duplication, reviewer agreement, novel accepted coverage, cost per accepted claim, and per-class coverage.

## ETA and artifact accounting

ETA is derived from the DAG critical path plus measured throughput. A group reports agent-hours separately from wall-clock time. Artifact quantity is not a success metric by itself; it is paired with validation status. For example, 500 generated lines with no passing test count less than 80 checked Lean lines or one independently reproduced theorem entry.

The dashboard reads `research_map.json`, so both the Human PI and Astra see the same state. The HTML view supports global DAG, group filters, progress bars, selected-node detail, and sub-DAG drill-down.

## Immediate next implementation steps

1. Add schemas for `direction_update`, `claim`, `artifact`, `review`, and `resource_request`.
2. Add a map validator that rejects cycles, unknown dependencies, cross-class leakage, and completed nodes without gate evidence.
3. Connect the existing `framework/run.py` run ledger to map node IDs and artifact hashes.
4. Add a local HTTP server or static export for the dashboard.
5. Run the four-arm swarm ablation before increasing parallelism beyond 20.
