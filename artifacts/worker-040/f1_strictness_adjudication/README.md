# W040-F1-STRICTNESS-ADJ-04 — independent adjudication of F1 rev12's whole-curve "strictly STRONGER" claim

**Verdict: `confirm_hf040_04` (score 4.0 on the adjudication; schema verdict `revise`).**
Bounded class-bound task, node **F1**, gate **G-FORM**, class **AF-WCC-VAC-GEN**.
Reviewer `worker-040`; not an author of any schema, taxonomy, or prior F1 review.
All shared artifacts were read-only; the only writes are this worker's own artifact
directory, its own review file, its own runtime-state checkpoint, and appends to its
own outbox.

## Question

F1 rev12 defines the class predicate as the single-q **tail** predicate
(`quantifiers.formal`, `domains.D5`): there exist `q in I+` and `t0 in [0,T)` with
`gamma([t0,T)) subset J^-(q) cap M`. The same schema asserts twice that the
**whole-curve** reading `gamma([0,T)) subset J^-(q)` is *strictly* STRONGER and not
the predicate (line 72), and that requiring it "would misclassify a geodesic that
starts in the exterior and ends inside the black-hole region" (line 213).

Two live reviews disagree at the identical target hash
`cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3`:

| source | position |
|---|---|
| `reviews/F1-review-040-rev12.json` (HF-040-04) | the strictness sentence is **false**; blocking |
| `reviews/F1-review-053.json` (P053-5, C6 PASS) | the strictness sentence is **true**; a "discriminating model separates the two readings" |
| `artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json` | same sentence is a **non-sequitur**; non-blocking documentation defect |

This task adjudicates that conflict with an executable falsifier.

## Decisive argument (H)

`J^-(q)` is the standard causal past, hence **past-closed**: `p <= r` and `r <= q`
imply `p <= q`. For a future-directed causal geodesic, `t < t0` implies
`gamma(t) <= gamma(t0)`.

> If the tail is contained in `J^-(q)`, then `gamma(t0) <= q`. For every
> `t < t0`, transitivity gives `gamma(t) <= gamma(t0) <= q`, so
> `gamma(t) in J^-(q)`. Whole-curve containment follows.
> Whole implies tail trivially (take `t0 = 0`). **The two readings are logically
> equivalent on the class's own curve family.**

The strictness sentence and the misclassification example are therefore false under
(H). The *operative* tail clauses are unaffected; the defect is the false
justification attached to them.

## Executable controls (all 11 PASS, 0 drift)

Instrument: `run_adjudication.py` (stdlib only, deterministic; `--root` optional).
Finite models are controls on the argument above, not a proof of it.

| check | result |
|---|---|
| B01 live pins == reviewed bytes (entry and exit) | PASS, 0 drift |
| B02 target is rev12 / `AF-WCC-VAC-GEN` | PASS |
| M01 no `tail ∧ ¬whole` witness over **all 355 preorders** on 4 points, all causal curves len ≤ 3, all q, all t0 | 0 witnesses (tail count 37 464 == whole count 37 464) |
| M01b same at the existential level (`∃gamma,q,t0` tail ⇒ `∃gamma,q` whole) | 0 violations / 19 320 tail-satisfying curves |
| M02 negative control: drop transitivity (35 non-past-closed relations on 3 points) | **804 witnesses** — the search has teeth; smallest: `gamma=[1,0]`, `q=2`, `t0=1`, rows `101/011/100` |
| M03 negative control: drop the causal-curve requirement | **22 witnesses** (e.g. `gamma=[0,1]`, `q=1`, `t0=1`, total order `0<1<2`) |
| M04 reviewer-053's asserted configuration (`gamma(0)` outside `J^-(q)`, tail visible) over all preorders | **0 realizations** |
| M04b the same configuration without transitivity | 528 realizations — realizable only outside the declared causal structure |
| M05 reviewer-053's "discriminating model" is a hardcoded literal dict | PASS (see below) |
| M06 strictness sentence confined to F1 | PASS — `Whole-curve containment` only at `af_wcc_vacuum.yaml:72`; `requiring the whole geodesic` only at `:213`; F2a/F2b/F0 clean |
| M07 the claim F1 cites as confirmation is refuted by its own source | PASS |

Bounded random extension: 300 random preorders on 5 points, random causal curves
len ≤ 4 → 0 `tail ∧ ¬whole`, 0 `outside_inside`.

## Why reviewer-053's C6 PASS is unsupported

`artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py` lines 244–249
(sha256 `95945acf84f6…`) are:

```python
m["discriminating_model"] = {
    "geodesic": "gamma starts outside J^-(q0), ends inside J^-(q0)",
    "canonical_tail_visible": True,
    "whole_curve_visible": False,
    "readings_agree": False,
}
```

The booleans are **literals**, not computed from any relation or curve; the
`geodesic` value is an unused string; no model is constructed or evaluated.
Moreover the asserted configuration is *unrealizable* under the schema's own
hypotheses (M04/M04b): a causal curve whose tail lies in a past-closed `J^-(q)`
cannot start outside it. The C6 "non-vacuity control" therefore has no teeth, and
P053-5 ("the discriminating model separates the two readings") states the opposite
of what the class hypotheses imply.

## Additional defect: inverted citation

Line 72 justifies the strictness sentence by citing "worker-037 W037V2-F1 …
independently confirmed". The cited source, worker-037's own report
(sha256 `61206221ff23…`), records `W037V2-F1` as **REFUTED** and its blocker as
**WITHDRAWN**, with the surviving characterization *"non-sequitur"* and the
recommended fix *"replace that sentence with the equivalence statement and cite
(H)/J^- past-closedness"*. The citation is inverted, not merely stale. This
escalates the predecessor's advisory `W040-F1-A1` to a documented hard finding
(`HF-040-04-CITE`).

## Disposition

- `HF-040-04` **confirmed** at the live hash: replace the strictness sentence with
  the (H)-equivalence statement and delete/repair the misclassification example.
- `HF-040-04-CITE` **confirmed**: the confirmation attribution must be replaced by
  the withdrawal + equivalence.
- Blocking classification is a gate-policy call owned by the controller/lead:
  worker-037 calls the same defect non-blocking documentation; this review's
  position is that an *accept* at this hash would certify a false mathematical
  assertion inside the very visibility section G-FORM checks, so the trivial
  two-sentence fix should precede an unconditional accept.
- Line-234 (`SET` variant union reading) is a **different** claim and is not
  adjudicated here (predecessor advisory `W040-F1-A2` still open).
- No node completion, no gate verdict, no `status=done`, no `validation_status=passed`.

## Falsifiers

This adjudication is void on any byte change of `schemas/af_wcc_vacuum.yaml` away
from `cce9c60146d6…`. It is refuted by:

1. a preorder with a future-directed causal curve `gamma`, `q`, `t0` such that
   `gamma([t0,T)) subset J^-(q)` and `gamma([0,T)) not subset J^-(q)`;
2. an executable discriminating model in the reviewer-053 checker whose booleans
   are computed from an actual causal structure rather than hardcoded;
3. a canonical F1 revision that states the tail/whole equivalence and removes the
   strictness sentence (this *retires* HF-040-04).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-040/f1_strictness_adjudication/run_adjudication.py
```

Outputs: `report.json`, `evidence.json`, `entry_hashes.json` (entry/exit pins and
drift). Exit code 0 only if every check passes and no pin drifts.
