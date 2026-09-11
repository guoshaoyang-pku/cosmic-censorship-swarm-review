# Astra controller handoff

## Mission

Own the cosmic-censorship research map and improve epistemic quality before increasing parallelism. The map is the shared state for Human PI, Astra, group leads, and execution agents. Do not claim a theorem, counterexample, or numerical result from fluent text alone.

## Current state (2026-09-11)

- Repository: `swarm-research/ai4math-swarm`
- Branch: `codex/research-map-dashboard`
- Map: `research_map/research_map.json`
- Dashboard: `research_map/research_map.html`
- Validator: `python3 research_map/validate_map.py`
- Current map validation: `VALID`
- Remote status: no project-specific Astra or DeepSeek Flash fleet was found on `ophis-gpu`; existing remote Codex/training processes belong to other work.

## Portfolio

| group | direction | active agents | spent/budget h | ETA | status |
|---|---|---:|---:|---:|---|
| formulation | split WCC/SCC classes and prevent leakage | 6 | 38/160 | 3–6d | active |
| literature | verify theorem scope and citations | 5 | 42/220 | 5–10d | active |
| numerics | spherical Einstein–scalar calibration | 4 | 22/320 | 10–21d | active but blocked by dependencies |
| audit | score correctness, citations, hard failures, IG | 5 | 55/180 | 2–5d | active |

Current totals: 20 active agents, 157 spent agent-hours, 880 budgeted agent-hours, about 18% budget burn. The current dependency critical path is approximately 13–21 calendar days, subject to measured throughput and the numerical implementation gate.

## Hard decisions

1. Keep `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, and `AF-WCC-SCALAR-SPH` as separate classes.
2. Do not launch self-gravitating numerics until formulation and audit gates pass.
3. Treat DeepSeek Flash as a breadth executor. Group leads must review class binding, assumptions, falsifier, artifact schema, and citation scope.
4. A completed node requires an artifact and validation evidence. HTTP success, output length, or agent consensus is not completion.
5. Use matched-budget baselines before claiming swarm advantage.

## Immediate queue

- F1: rewrite AF-WCC vacuum schema with exact quantifiers, topology, weighted data class, genericity, `I+`, visibility, and conclusion type.
- F2: write separate C2 and C0 strong-censorship schemas; never use “C0 or C2”.
- L0/L1: turn the literature draft into a primary-source theorem ledger; mark every uncertain citation unresolved.
- A1: re-review F1/F2/L0 with two independent reviewers; reject class leakage and conclusion inflation.
- N0: only after its dependencies pass, implement flat-space scalar-wave test.
- A2: run four-arm equal-budget ablation: one strong model, self-consistency, independent cheap agents, cheap agents plus coordinator.

## Communication contract

Group leads send: `status`, `claim`, `artifact`, `blocker`, `direction_update`, or `resource_request`. Every message names a node ID, class ID where applicable, evidence refs, expected information gain, and next falsifier. Astra sends assignments, budget changes, gates, priority changes, kill/revive events. High-impact scope changes are escalated to the Human PI.

## Startup on a networked remote host

```bash
cd ~/ai4math-swarm
python3 research_map/validate_map.py
# Run the task-specific client after copying its prompt bundle into this repo.
DEEPSEEK_MODEL=deepseek-flash \
DEEPSEEK_ENDPOINT=https://api.deepseek.com/v1/chat/completions \
WORKERS=20 python3 research_map/run_parallel.py
```

For a new controller process, read this file, `research_map.json`, `ARCHITECTURE.md`, and the base `HANDOFF.md` before allocating work.

## Definition of useful progress

Prefer fewer accepted claims with verified scope over many drafts. Track accepted-claim rate, hard-failure rate, citation support, duplication, reviewer agreement, novel accepted coverage, cost per accepted claim, and per-class coverage. If a result fails a gate, record the failure as progress and redirect the budget.
