# W011-F1-VIS-STRICT-01 — F1 rev12 visibility strictness adjudication

Worker-011, 2026-09-12. Class-bound task on `AF-WCC-VAC-GEN`, node `F1`, gate `G-FORM`.
No assignment card existed in `comms/inbox/worker-011.jsonl`; the task was self-selected
because two accepts at the frozen hash (`worker-061` 4.5, `worker-088` 4.0) cite the
sentence under test as a *repair*, while `worker-040` (HF-040-04) and `worker-037` record
it as false / a non-sequitur.

## Question

At `schemas/af_wcc_vacuum.yaml#cce9c60146d6` (rev12), is it true that whole-curve single-q
containment `gamma([0,T)) subset J^-(q)` is **strictly STRONGER** than the class's tail
predicate `exists t0: gamma([t0,T)) subset J^-(q)` (L72), and that the whole-curve reading
"would misclassify a geodesic that starts in the exterior and ends inside the black-hole
region" (L213)?

## Answer

**No.** Under the schema's declared standard causal past (past-closed by definition) the two
single-q readings are *equivalent*: tail ⇒ whole because `gamma([0,t0]) subset J^-(q)`
whenever `gamma(t0) in J^-(q)` (LEMMA-W011-1). Neither is strictly stronger and the
misclassification scenario is impossible.

Evidence:

| check | result |
|---|---|
| exact sentences present at the pinned hash | yes (L72, L213) |
| exhaustive preorders on ≤5 labelled points (OEIS A000798: 1,4,29,355,6942) | 7331 models / 534214 tail-q evaluations / **0 divergences** |
| fixed-seed sampled preorders n=6,7,8 | 6200 models / 4105578 evaluations / **0 divergences** |
| control: cover-reachability `J^-` (non-past-closed) | 56046 divergences → checker has teeth |
| control: non-causal sequences | 29400 divergences → causality matters |
| recorded strictness witness (from the withdrawn W037V2-F1) | violates past-closure; disappears under the standard past |
| cited support "independently confirmed by worker-037 W037V2-F1" | stale: worker-037 withdrew W037V2-F1 |

## Deliverable

- `run_adjudication.py` — deterministic checker (pins, lemma, exhaustive + sampled models,
  controls, witness audit, citation audit, drift guard). Writes only `report.json`.
- `report.json` — 10/10 checks pass; full machine evidence and the minimal fix.
- `emit_events.py` — builds `reviews/F1-review-011-visibility-strictness.json`, validates
  every event against `research_map/schemas.py`, then appends them to
  `comms/outbox/worker-011.jsonl` and writes the checkpoint (only with `--emit`).

Verdict: **revise 3.5** — hard failure `HF-011-01` (false strictness claim, blocking);
major `F-011-02` (withdrawn citation); advisories `F-011-03` (SET-variant strictness is an
unproven obligation, not machine-settleable by finite chains) and `F-011-04` (accepting
reviews' coverage gap). The operative tail predicate itself is sound; the fix is to state
the equivalence and drop the withdrawn citation.

Authority: worker evidence only — not a gate verdict, not a node status, not one of the
two accepts a gate requires. No canonical artifact was modified.

Reproduce: `python3 run_adjudication.py && python3 emit_events.py` (add `--emit` to write).
