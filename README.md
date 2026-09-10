# ai4math-swarm

A goal-directed multi-agent search framework for open mathematical problems, plus the
measurements that determined its design.

Built on the skeleton of the `swarm-work/data/gen1` experiment (36 agents, three model
families, shared board, citation ledger, reaper/resurrect), redirected from open-ended social
simulation to verifier-gated search.

## Why the design looks like this

Every structural choice below was forced by a measurement in this repo, not chosen on taste.
Several of them overturned what I believed at the start, in both directions.

**The archive admits only machine-verified artifacts.** What an agent claims, argues, or
reasons never enters the store — only objects that a verifier ran and accepted. FunSearch gets
this right and it is the reason it has no error-propagation problem at all.

**The proposer is the main lever; orchestration is not.** Two runs of a three-arm experiment
with a real LLM proposer (2 seeds, then 5 seeds, 840 calls total) found the ceiling identical
across arms — no-memory sampling 0.8701, FunSearch-style parents 0.8713 — while swapping the
proposer moved the ceiling from 0.824 to 0.870. What orchestration *does* buy is a higher mean
(+3.0%) at the cost of coverage (−19%) and valid output (−11%). So the pool is heterogeneous by
default, accounts per family, and every mixed run is paired with a single-family control.

**Heterogeneity is not free.** Offline, prior diversity was worth 37% of useful coverage. With
real models, mixing in a family that is weaker *at the task* lost on every axis (valid output
27/40 vs 31/40). Neither result generalises, which is exactly why the framework measures it per
run instead of assuming a direction.

**Dead ends are broadcast; winners are not.** Two generations of systems — FunSearch (2023) and
the AlphaEvolve lineage (2025-26) — broadcast only the best program and nothing about failure.
Broadcasting winners is what drives premature convergence; broadcasting refuted regions prunes
without steering. An A/B here cut island redundancy ~17% without improving the score, so the
channel exists and is instrumented rather than assumed to help.

**Everything is instrumented.** Coverage, island redundancy, and late-growth (new behaviours
found in the last third minus the first third) are the difference between "exploring" and
"collapsed forty minutes ago". No open implementation measures any of them.

**Run the null first.** An earlier version of the offline lab produced a clean, monotone,
publishable-looking result that a five-minute iid-random control destroyed. No FunSearch-family
paper I found reports a random-sampling control at matched budget.

## Layout

| path | what |
|---|---|
| `framework/core.py` | task protocol, verified-only archive, retractable ledger, dead-end channel, metrics |
| `framework/pool.py` | heterogeneous proposer pool over MASO's providers, per-family accounting |
| `framework/tasks/` | one file per problem: `prompt` / `parse` / `verify` / `deadend_key` |
| `framework/run.py` | main loop, with a built-in single-family control |
| `erdos64/` | audited cycle counter and a local-search baseline for Erdős #64 |
| `data/` | validated candidate pool: Erdős problems cross-checked against two databases |
| `runs/` | per-run ledger, dead ends, metrics |

`repro/` (gitignored) holds third-party clones read during this work: `google-deepmind/funsearch`,
`algorithmicsuperintelligence/openevolve`, `google-deepmind/formal-conjectures`,
`teorth/erdosproblems`, `mrconter1/vibemathed`.

## Adding a problem

Subclass `Task` and implement four methods. The only hard requirement is on `verify`: it must
be deterministic, machine-checkable, and cheap **in human hours**. If a person has to read the
output to know whether it is right, the problem does not belong in this framework — that is the
entry criterion, and at $100k of budget it buys roughly 800 human hours against 74 billion
tokens, so human attention is the scarce resource, not compute.

## Current task: Erdős #64

The Erdős–Gyárfás conjecture ($1000, open, Lean-formalised in `formal-conjectures`, no AI
solution on record in the 664-problem VibeMathed database): does every finite graph with
minimum degree ≥ 3 contain a cycle of length 2^k for some k ≥ 2?

The verifier counts cycles by explicit path enumeration with a canonical representative, rather
than any algebraic shortcut that could silently count closed walks, and self-tests against three
graphs with published cycle spectra (K4, K_{3,3}, Petersen) before every run.

Local-search baseline, 540 restarts in 797 s, all results independently re-verified as connected
and strictly 3-regular:

| n | 4-cycles | 8-cycles | 16-cycles |
|---|---|---|---|
| 14–22 | 0 | 7 → 6 → 3 → 2 → 2 | — |
| 24 | 0 | **0** | 207 |
| 26 | 0 | **0** | 161 |
| 28 | 0 | **0** | 208 |
| 30 | 0 | **0** | 210 |

There is a transition at n = 24 where connected cubic graphs can avoid 4- and 8-cycles
simultaneously; it is also where the search gets hard (60/60 restarts reach the floor at n ≤ 22,
only 3–11/60 at n ≥ 24). Killing one power of two immediately surfaces the next. At n = 30 a
graph with no 4-, 8-, or 16-cycle would be a complete counterexample, since 32 > 30.

Baseline score on the swarm's lexicographic metric: **−5.71e10**.
