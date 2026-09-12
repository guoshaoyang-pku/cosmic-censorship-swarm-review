# Handoff — swarm measurement discipline & known traps

Distilled from the measurement campaign run on `main` between 2026-09-09 and 2026-09-11
(FunSearch-family tasks: cap-set and an Erdős problem). The full period narrative lives in
`main`'s `HANDOFF.md` (commit `a0a018c`) and in git history; the Erdős task material itself
(`erdos64/`, `data/`, `runs/`, `framework/tasks/erdos64.py`) has been **removed from this
branch** — the cosmic-censorship swarm does not depend on any of it.

One consequence worth stating explicitly: because that material was removed, any Erdős /
cap-set / graph-search token showing up in this branch's *new* artifacts is a contamination
signal — detector `HF-13` in `evaluation_rubric.yaml`. (Erdős mentions inside the frozen
evidence chain under `artifacts/`, `runtime/`, `reviews/` are historical bytes, including
the contamination-detection fixtures themselves; they stay.)

---

## 1. Ground rules

**Every claim is labelled with how strongly it is established.** Roughly a third of what the
project believed at various points turned out to be wrong, and almost all of it was caught by
a control rather than by thinking harder.

**Process rules that carried forward:**
- Run the null first. A five-minute iid-random control destroyed a clean, monotone,
  publishable-looking result. No FunSearch-family paper found reports a random baseline at
  matched budget — always be the one who does.
- Add seeds before believing a max-statistic. Two separate killed hypotheses were the same
  error: reading a result off too few seeds.
- If a person must read the output to know whether it is right, the problem does not belong
  in a verifier-gated framework.

---

## 2. What was measured (established, replicated)

| Finding | Evidence |
|---|---|
| **iid random sampling beats the full orchestration architecture on best score** when the proposer is uninformed (0.8240 vs 0.8150) | offline lab, 3 seeds + mutation-step sweep |
| **The architecture buys coverage, not optimum.** Tuned evolutionary coverage 149–151 vs random 143.7, while losing on best | step sweep, 6 step sizes |
| **Shared-prior cost is measurable and monotone.** K = independent → 16 → 8 → 4 gives coverage 144.7 → 132.0 → 119.3 → 100.7 | offline, 3 seeds, clean dose-response |
| **With a real LLM proposer, orchestration raises the mean (+3.0%) and costs coverage (−19%) and valid output (−11%)** | 2 seeds, replicated at 5 |
| **Single-family beats mixed-family on every axis** when the added family is weaker at the task | matched budget, single variable |
| **On a real open problem, a dumb local search beat the LLM swarm** | 540 restarts / 797 s vs 200 LLM calls |

Suggestive but *not* established (kept as open threads, do not cite as fact): orchestration's
advantage may appear only above a budget threshold (~100 calls) — shape of the curve supports
it, seed count does not; broadcasting dead ends cut island redundancy ~17% consistently but
never converted into better scores.

## 3. Landscape facts

- Neither FunSearch (2023) nor the openevolve/AlphaEvolve lineage (2025-26) shares failure
  information — both broadcast only the best program. **This design point is unoccupied.**
- FunSearch's behaviour descriptor is *semantic* (score vector); openevolve's default is
  *syntactic* (code length + edit distance), which is a step backwards.
- Nine "independent" LLM judges have a **Kish effective sample size of ~2.2**. Two models
  that are both wrong pick the same wrong answer 42–60% of the time against a 12.7–33% random
  baseline — across vendors and architectures.
- Ten agents debating three rounds: the pool contained a correct answer 53% of the time; the
  team's final answer was correct **20.7%** of the time, at 2.1–3.4× the tokens.
- **No audited intervention has ever been shown to restore statistical independence between
  LLM errors** — not vendor, architecture, prompt, temperature, persona, tooling, or LoRA.
  Heterogeneity buys complementarity, never independence.
- Verification costs more than search: Schur-5 was 14 CPU-years to solve and **36 to check**;
  FunSearch runs 140 evaluators against 15 samplers.

---

## 4. Hypotheses the project held and then killed

Kept because the pattern matters more than any single item: **the refutations came from
controls, not from reasoning.**

1. Feedback-controlled temperature maintains diversity → **harmful** (best 0.8305 → 0.7980-scale regression).
2. Broadcasting negative results improves search → **no effect on any primary metric**
   (mechanism confirmed — redundancy fell — benefit never materialised).
3. Rescuing unique cells at island reset is useless → **wrong, it is task-dependent**; worth
   +8% coverage on the hard task and the only mechanism keeping late-stage growth positive.
4. Heterogeneity restores error independence → **refuted by the literature** (see §3).
5. Heterogeneity improves output → **refuted five times**; mixing in a family weaker *at the
   task* loses on every axis.
6. "The ceiling is model-determined, orchestration cannot move it" → measured at 40 calls,
   **below the threshold where the difference appears**. Overstated.
7. A scoring metric that looked lexicographic was a **weighted sum with a 100:1 ratio while
   counts reached 210** — which inverted the ranking between two competing methods. It also
   summed across problem sizes when it should have taken the best single size. **Lesson: audit
   the metric before believing any comparison it produced.**
8. A clean, monotone, publishable-looking offline result → **destroyed by a five-minute
   iid-random control.**

---

## 5. Traps already paid for

- **Reasoning models silently return empty content.** Without an explicit reasoning-effort
  setting, or with too small a token budget, the model spends its entire completion allowance
  on hidden reasoning and returns `""` with `finish_reason: length`. This looks identical to
  "had nothing to say". It cost 36 wasted calls once, then an entire factorial arm later,
  where the main-effect table read it as "high effort is worse". Count `truncated` /
  `timeout` / `empty` separately — they look the same downstream and need opposite fixes.
  High effort costs ~6× the tokens of low (12842 vs 2137 on the same prompt), so **a
  factorial over effort must equalise token budget, not call count**, or the effort axis
  silently becomes the depth axis.
- **~5% of LLM-generated code is pathological enough to wedge the evaluator.** There is no
  way to bound arbitrary Python from inside the same process; the timeout must live at the
  process boundary. Both legacy task files fork a child.
- **macOS defaults to `spawn`**, which re-imports the main module. Any driver script needs an
  `if __name__ == '__main__':` guard or it fork-bombs. This killed one run and wrote a garbage
  seed into the results.
- **Gateway concurrency has a hard ceiling.** Measured: 8 → all succeed, 16 → all succeed,
  24 → 2 fail, 32 → **15 of 32 fail**. Scaling past ~16 needs a different channel, not more
  threads. Measure the ceiling per provider; never assume it.

---

## 6. The legacy framework (control layer)

This branch's live architecture is `research_map/` + `runtime/` + `comms/` + `harness/`
(see `README.md`). `framework/` is kept as the inherited verifier-gated search layer, with
`capset` as the remaining control task:

```bash
export SWARM_PROVIDERS=/path/to/model-providers.yaml   # not in the repo: holds keys
cd framework
python3 run.py capset --calls 200 --families sol --policy islands
python3 run.py capset --calls 200 --families sol,qwenmax --policy islands   # always pair
python3 factorial.py capset --calls 100 --seeds 3
```

Adding a problem: subclass `Task`, implement `prompt` / `parse` / `verify` / `deadend_key`.
The only hard requirement is on `verify` — deterministic, machine-checkable, cheap in *human*
hours.

**Design choices and what forced them** are documented at the top of each module. They are
not style preferences; each one is a measurement.
