# Handoff — agent swarm × AI4math

Everything found between 2026-09-09 and 2026-09-11, written so another session can pick it up
cold. Read this file first; `README.md` covers the code, this one covers the *judgements* and
what they rest on.

Ground rule used throughout, and worth keeping: **every claim below is labelled with how
strongly it is established.** Roughly a third of what this project believed at various points
turned out to be wrong, and almost all of it was caught by a control rather than by thinking
harder.

---

## 1. The strategic conclusion

**You cannot win by building a cleverer swarm architecture.**

This was not a prior, it is what the measurements kept saying. Orchestration — islands,
migration, broadcast, aggregation policy — contributes little. Proposer quality sets the
ceiling. FunSearch's and AlphaEvolve's real advantage is the underlying model plus call volume,
not the bookkeeping around it. The strongest models are not ours.

So the leverage is elsewhere, in three places that all route *around* a model-quality contest:

**(a) Problem selection and verifier design.** Half of FunSearch's contribution is translating
"cap set" into "write a priority function". That translation is human, domain-specific, and
does not scale — which is exactly why it is valuable when compute is cheap and human hours are
not. At $100k, the budget buys roughly **800 human hours against 74 billion tokens**. Human
judgement is the scarce input. The 32-problem shortlist in `data/` is raw material for this.

**(b) The verification layer, which is a vacuum.** AI-solved maths problems went from ~1/month
to ~223/month; **63% have never been checked**, the proportion is *worse* for high-value
results (66% unchecked), and three have already been retracted. Nobody is building the
checking/dedup/provenance layer. It needs engineering and judgement, not frontier models — and
it gets *more* valuable as the big labs get stronger, which makes it the only position where a
competitor's progress helps you.

**(c) Depth-vs-breadth as an empirical question.** The "nobody lets them run long enough"
argument is about depth. Everything measured here is breadth. Done properly this is a
methodology contribution that competes on insight rather than on GPUs.

**Recommendation:** attack (a), let (b) accumulate as moat, take (c) as a by-product.
Concrete next step: pick 3 problems from the shortlist of different types, write a verifier
and search for each, and see whether verifier design actually generalises. #64 is already done
and its answer was *no, the dumb local search won* — which is itself a result.

---

## 2. What was measured

### Established, replicated

| Finding | Evidence |
|---|---|
| **iid random sampling beats the full FunSearch architecture on best score** when the proposer is uninformed (0.8240 vs 0.8150) | offline lab, 3 seeds, plus a mutation-step sweep confirming it is not a tuning artifact |
| **The architecture buys coverage, not optimum.** Tuned evolutionary coverage 149–151 vs random 143.7, while losing on best | step sweep, 6 step sizes |
| **Shared-prior cost is measurable and monotone.** K = independent → 16 → 8 → 4 gives coverage 144.7 → 132.0 → 119.3 → 100.7 | offline, 3 seeds, clean dose-response |
| **With a real LLM proposer, orchestration raises the mean (+3.0%) and costs coverage (−19%) and valid output (−11%)** | 2 seeds then replicated at 5; the first run read +4.8% and shrank to +3.0% with more seeds |
| **Single-family beats mixed-family on every axis.** best −4.0e10 vs −6.0e10, verified 117/200 vs 52/200, coverage 9 vs 6, redundancy 0.556 vs 0.833 | Erdős #64, matched budget, single variable |
| **On a real open problem, a dumb local search beat the LLM swarm.** Local search reached 0 eight-cycles at n≥24; the swarm never did at any n | 540 restarts / 797 s vs 200 LLM calls, under a corrected lexicographic metric |

### Suggestive, not established

| Claim | Why it is not settled |
|---|---|
| Orchestration's advantage appears only above a budget threshold (~100 calls) | At 200 calls B beat A 0.8905 vs 0.8727, but that is 1.0 sd with 3 seeds and driven by one lucky seed (0.9153 against 0.8825 and 0.8737); B's worst seed lost to A's best. The *shape* is better evidence than the level: A stopped improving at call 100, B was still climbing at 200. **Needs ~8 seeds; the run to do it is `repro/funsearch_lab/more_seeds.py`.** |
| Broadcasting dead ends instead of winners helps | It does what it says — island redundancy fell ~17%, consistently across both prior conditions — but did not convert into better scores. Mechanism confirmed, benefit not. |

### Facts about the landscape

- Neither FunSearch (2023) nor the openevolve/AlphaEvolve lineage (2025-26) shares failure
  information. `grep failure|negative|dead_end` over both: zero hits. Both broadcast only the
  best program. **This design point is unoccupied**, and three independent lines of reasoning
  point at it.
- FunSearch's behaviour descriptor is *semantic* (score vector on tests) and emerges for free.
  openevolve's default is *syntactic* (code length + edit distance), which is a step backwards:
  two structurally different programs of similar length land in the same cell.
- Nine "independent" LLM judges have a **Kish effective sample size of ~2.2**. Two models that
  are both wrong pick the *same* wrong answer 42–60% of the time against a 12.7–33% random
  baseline, and this holds **across vendors and architectures**.
- Ten agents debating for three rounds: the pool contained a correct answer 53% of the time,
  the team's final answer was correct **20.7%** of the time, at 2.1–3.4× the tokens.
- **No audited intervention has ever been shown to restore statistical independence** between
  LLM errors — not vendor, architecture, prompt, temperature, persona, tooling, or LoRA.
- Verification costs more than search: Schur-5 was 14 CPU-years to solve and **36 to check**;
  FunSearch runs 140 evaluators against 15 samplers.

---

## 3. Hypotheses this project held and then killed

Kept because the pattern matters more than any single item: **the refutations came from
controls, not from reasoning.** Anything below marked "mine" was proposed here and then
destroyed by its own experiment.

1. *(mine)* Feedback-controlled temperature maintains diversity → **harmful**, best 0.8030 → 0.7980.
2. *(mine)* Broadcasting negative results improves search → **no effect on any primary metric**.
3. *(mine)* Rescuing unique cells at island reset is useless → **wrong, it is task-dependent**;
   worth +8% coverage on the hard task and the only mechanism that keeps late-stage growth positive.
4. *(mine)* Heterogeneity restores error independence → **refuted by the literature**; it buys
   complementarity, never independence.
5. *(mine)* Heterogeneity improves output → **refuted five times**; mixing in a family that is
   weaker *at the task* loses on every axis.
6. *(mine)* "The ceiling is model-determined, orchestration cannot move it" → measured at 40
   calls, which is **below the threshold where the difference appears**. Overstated.
7. *(mine)* The #64 score was lexicographic → it was a **weighted sum with a 100:1 ratio while
   counts reached 210**, which inverted the ranking between local search and the swarm. Also it
   summed across n when it should take the best single n, since a counterexample at *any* n settles it.
8. A clean, monotone, publishable-looking offline result → **destroyed by a five-minute iid-random
   control.** No FunSearch-family paper found reports a random baseline at matched budget.

**Process rule worth carrying forward: run the null first, and add seeds before believing a
max-statistic.** Two of the errors above are the same error — reading a result off too few seeds.

---

## 4. The problem shortlist

`data/erdos_validated.json`, `data/candidates_full.json`, `data/formalization_check.json`.

Built by three filters, each run here rather than taken on trust:

1. Parse all 1217 problems in `teorth/erdosproblems`, keep those the community labels
   `falsifiable` / `decidable` / `verifiable` — i.e. a finite witness settles them. **41 problems.**
2. Full-text cross-check against the 664 AI-solved problems in `mrconter1/vibemathed`.
   **Only 1 of the 41 has been solved**; #7 carries a `retracted/contested` record.
3. Cross-check against `google-deepmind/formal-conjectures` (671 Erdős problems in Lean).
   **32 of the remaining 40 already have a Lean formalisation** — meaning *the verifier already exists*.

That third filter is the one that matters, and it is the only hard evidence available for the
entry criterion "cheap to verify in human hours": a candidate counterexample can be fed
straight to Lean without a person reading it.

**This also corrected an earlier exclusion list** that dropped #64, #107, #167 and #506 citing
three fabricated GitHub URLs. Full-text search of the actual data: all four are clean.

Sharpest subgroup — falsifiable *and* a finite-graph search (what compute is actually good at):
**#64, #128, #23, #617, #628, #583, #1020.**

**Caveat that must travel with the list:** absence from VibeMathed means no *published*
AI-assisted solution, not that nobody is working on it. Re-check on the day you commit.

---

## 5. Erdős #64 — current state

Erdős–Gyárfás conjecture, $1000, open, Lean-formalised, absent from VibeMathed.
*Does every finite graph with minimum degree ≥ 3 contain a cycle of length 2^k for some k ≥ 2?*

A counterexample has min degree ≥ 3 and no cycle of length 4, 8, 16, 32, … (C3 is allowed).

**Verifier** (`erdos64/search.py`): counts cycles by explicit path enumeration with a canonical
representative, not by any algebraic shortcut that could silently count closed walks.
Self-tests against K4, K_{3,3} and Petersen before every run.

**Local-search baseline** — 540 restarts, 797 s, every result independently re-verified as
connected and strictly 3-regular:

| n | C4 | C8 | C16 |
|---|---|---|---|
| 14–22 | 0 | 7 → 6 → 3 → 2 → 2 | — |
| 24 | 0 | **0** | 207 |
| 26 | 0 | **0** | 161 |
| 28 | 0 | **0** | 208 |
| 30 | 0 | **0** | 210 |

**There is a transition at n = 24** where connected cubic graphs can avoid 4- and 8-cycles
simultaneously. It is also where search gets hard: 60/60 restarts reach the floor at n ≤ 22,
only 3–11/60 at n ≥ 24. Killing one power of two immediately surfaces the next.

At n = 30 a graph with no 4-, 8- or 16-cycle would be a **complete counterexample**, since
32 > 30. Local search gets C16 to 210; not close.

**Open threads on this problem:** the scoring needs the two fixes in §3 item 7 (true
lexicographic ordering, and best-single-n instead of sum) before any further swarm run means
anything. The descriptor is also too coarse — 6–9 occupied cells total, which degenerates
MAP-Elites into ordinary ranking.

---

## 6. The code

See `README.md` for layout. Quick start:

```bash
export SWARM_PROVIDERS=/path/to/model-providers.yaml   # not in the repo: holds keys
cd framework
python3 run.py capset --calls 200 --families sol --policy islands
python3 run.py capset --calls 200 --families sol,qwenmax --policy islands   # always pair
python3 factorial.py capset --calls 100 --seeds 3
```

Adding a problem: subclass `Task`, implement `prompt` / `parse` / `verify` / `deadend_key`.
The only hard requirement is on `verify` — deterministic, machine-checkable, cheap in *human*
hours. If a person must read the output to know whether it is right, the problem does not
belong in this framework.

**Design choices and what forced them** are documented at the top of each module. They are not
style preferences; each one is a measurement.

### Traps already paid for

- **Reasoning models silently return empty content.** Without an explicit `reasoning_effort`,
  or with too small a token budget, the model spends its entire completion allowance on hidden
  reasoning and returns `""` with `finish_reason: length`. This looks identical to "had nothing
  to say". It cost 36 wasted calls once, then an entire factorial arm (0/8 in all four
  high-effort cells) later, where the main-effect table read it as "high effort is worse".
  `Pool.EFFORT_TOKENS` now derives the budget from effort, and `truncated` / `timeout` / `empty`
  are counted separately because they look the same downstream and need opposite fixes.
  High effort costs ~6× the tokens of low (12842 vs 2137 on the same prompt) — **so a factorial
  over effort must equalise token budget, not call count**, or the effort axis silently becomes
  the depth axis.
- **~5% of LLM-generated code is pathological enough to wedge the evaluator.** There is no way
  to bound arbitrary Python from inside the same process; the timeout must live at the process
  boundary. Both task files fork a child.
- **macOS defaults to `spawn`**, which re-imports the main module. Any driver script must have
  an `if __name__ == '__main__':` guard or it fork-bombs. This killed one run and wrote a
  garbage seed into the results, which then had to be cleaned out.
- **Gateway concurrency has a hard ceiling.** Measured: 8 → all succeed, 16 → all succeed,
  24 → 2 fail, 32 → **15 of 32 fail**. Scaling past ~16 needs a different channel, not more threads.

---

## 7. Infrastructure notes

- **Provider channels.** Three genuinely distinct families were reachable through a MASO-style
  config (`sol` / `qwenmax` / `o50`). Two others (Gemini tiers) were quota-exhausted; the
  free OpenRouter tier is down to one working model at ~50 calls/day, which cannot support
  even a scaled-down run.
- **GPU.** Nine H20 workers were acquired and are running a heartbeat-only bootstrap
  (`w_boot.sh` on the shared disk). **They have no real work assigned.** Idle cards at ≤30%
  utilisation for three hours get reaped by the platform, so either give them work or release
  them. Nothing in the current experiments needs a GPU.
- **The ChinaTalk model weights are gone** — they lived on per-container `/tmp`, which is wiped,
  and the eval script deleted caches as it went. What survives on the shared disk is ~12 small
  *base* models (0.5B–2.8B, plus one 13B fine-tune), which will not follow an instruction to
  write a function. Any multi-model experiment needs a fresh download (~12 models × 30GB,
  roughly 2 hours at 6 repos in parallel).
- **SSH config was stale** and has been rewritten: the old jump-proxy route died 2026-08-10,
  and its failure mode (`Connection closed by UNKNOWN port 65535`) is indistinguishable from an
  expired Kerberos ticket, which sends you to `kinit` for nothing. Direct connection needs no
  ticket. Backup at `~/.ssh/config.bak.20260910-041141`.

---

## 8. What is *not* done

- The 2×2×2 factorial (history × depth × effort) — designed, smoke-tested, **never run for
  real**. Depth and effort have never been measured. Effort was pinned to `low` for all ~1400
  calls by a bugfix, which is the most dangerous kind of uncontrolled variable because nothing
  in the logs looks wrong.
- The budget-threshold question (§2, "suggestive") needs ~8 seeds per arm.
- #64 scoring fixes, and a descriptor with actual resolution.
- Verifiers for a second and third problem from the shortlist — the test of whether
  verifier design generalises, which is the core of recommendation (a).

---

## 9. Where this started

A three-body-problem conjecture (Sun 2018, generalised Kepler's third law) that had stood
unrefuted for eight years and was disproved overnight by a model, with two counterexamples: an
analytic one from Lagrange's 1772 equilateral solution, and the figure-eight orbit combined
with a published computer-assisted existence proof. Independently re-verified here, including
re-deriving the interval data the argument depends on.

The lesson that carried into everything after: **the refutation needed no supercomputer, only a
250-year-old exact solution and a suspicion about which of two mass-symmetric branches was
right.** Falsification was never short of data. It was short of someone putting two known facts
side by side.
