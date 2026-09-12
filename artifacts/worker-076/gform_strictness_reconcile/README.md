# W076-GFORM-STRICTNESS-RECONCILE-06

Bounded class-bound task taken by `worker-076` with no inbox card (`comms/inbox/worker-076.jsonl`
does not exist). Class **AF-WCC-VAC-GEN**, node **F1**, gate **G-FORM**. Read-only: no canonical or
shared file was modified; no gate verdict or node completion is claimed.

## Revision note (important)

The task started at F1 **rev12** `cce9c60146d6`. Mid-task, at 00:53:20, the formulation lead
published **rev13** `d9cebb9404b2` via `astra-life05-evidence-binding-repair`, which corrected both
strictness directions and cites this task (`W076-GFORM-STRICTNESS-RECONCILE-06` T1; T2/T3/T4).
This artifact's T1-T4 results are revision-independent order theory; its anchor checks are run at
the **live** file hash and verify the rev13 corrections. The rev12 line numbers are kept only in
the historical status table.

## Why this task

Two live worker records adjudicate "the two readings" in the F1 visibility section:

- `worker-040` `W040-F1-STRICTNESS-ADJ-04` (`artifacts/worker-040/f1_strictness_adjudication/report.json`,
  sha256 `86596838ff30…`): the rev12 sentence "Whole-curve containment … is strictly STRONGER" is
  **false** — for a causal geodesic in a transitive causal structure, tail and whole containment in
  a **single** `J^-(q)` are equivalent (0/355 preorders on 4 points separate them).
- `worker-076` `W076-GFORM-VIS-STRENGTH-03` (`artifacts/worker-076/gform_vis_strength/probe_result.json`,
  sha256 `96a52c2297ee…`): the rev12 sentence "variant SET is strictly STRONGER" is **inverted** —
  the canonical single-q tail predicate entails the union reading, and the converse fails on an
  omega-chain.

Read carelessly these look contradictory (one says "equivalent", the other "not equivalent").
They are about **different predicate pairs**. This probe machine-checks both pairs and states the
joint result so an A1 reviewer does not have to reconstruct it.

## Predicates (located by content, so line shifts do not matter)

| name | definition |
|---|---|
| `P_whole(q)` | `gamma([0,T)) subset J^-(q)` for one exhibited `q` (D5 definition) |
| `P_tail(q)` | `exists t0: gamma([t0,T)) subset J^-(q)` (canonical, visibility.definition) |
| `P_set` | `gamma([0,T)) subset UNION_{q in I+} J^-(q)` (variant SET, class_identity_variants) |

## Machine-checked results

- **T1** `P_whole(q) <=> P_tail(q)` for causal `gamma` in a reflexive transitive structure with
  `J^-` past-closed (proof: `gamma(0) <= gamma(t0) <= q`). **0 violations** in 663,680 predicate
  cases over all 355 preorders on 4 points (plus n=2,3; a non-transitive control fires).
  => rev12's "strictly STRONGER" for the fixed-q pair was false; the misclassification example was
  a non-sequitur.
- **T2** `P_tail(q) => P_set` always. **0 violations** over the same census.
- **T3** If `gamma` has a maximum element or `I+` is finite, then `P_set => exists q: P_whole(q)`
  (finite case: the covering index set of each `q` is a prefix, and finitely many prefixes cover
  `N`). **0 violations**; `P_set and not-P_tail` count **0** on every finite model. worker-040's
  0/355 is therefore structural, not a sampling artifact.
- **T4** With `I+` infinite and `gamma` maximum-free, `P_set and not-P_tail` is realizable:
  `x_i <= q_j iff i <= j`, `gamma = (x_i)`, `I+ = {q_j}`. Verified by transitive-closure equality
  on prefixes `N = 8, 24, 64`, P_set true, and for every `j < N` and every `t0` the in-prefix
  witness `i = max(j+1, t0)` shows no `q_j` sees a tail. **Certificate caveat:** on any finite
  prefix the top member `q_N` dominates the whole prefix (confirmed), so the prefix alone does not
  separate — this is T3 again; the infinite model's no-top-member step is the symbolic
  `j -> x_{j+1}` argument recorded in the result.

## Correction of a prior worker-076 note (honest bookkeeping)

`W076-GFORM-VIS-STRENGTH-03`'s `next_falsifier` named **down-directedness** of the witnessing
family as the deciding hypothesis. That is wrong: the omega-chain family `{J^-(q_j)}` **is**
down-directed (a nested chain has its smaller member inside every pairwise intersection) and still
separates the predicates. The deciding criterion is T3: a maximum of `gamma`, or finiteness of
`I+`, or one member whose past contains the union.

## Rev13 repair check (at `d9cebb94`, anchors located by content)

| item | rev12 | rev13 | probe |
|---|---|---|---|
| D5 whole-vs-tail | "strictly STRONGER" | "EQUIVALENT … NOT a weakening", cites T1 + worker-040 | verified |
| visibility.definition | misclassification example | example removed as non-sequitur | verified |
| variant SET relation | "strictly STRONGER" | "strictly WEAKER", cites T2/T3/T4 | verified |
| B-containment claim | "strictly stronger" | retained | TRUE, keep |
| variant SET falsifier | "show the two readings equivalent" | unchanged | unachievable as written for this class under T4 (non-blocking precision item) |

## Files

- `probe_strictness_reconcile.py` — deterministic checker (preorders n<=4, controls, omega-chain prefixes with the corrected certificate, content-located anchors incl. forbidden-token checks, pre/post pin drift).
- `probe_result.json` — full result, hashed in `SHA256SUMS.txt`.
- `SHA256SUMS.txt` — file hashes.

## Falsifier

FALSE if (a) any pinned input sha256 differs between pre and post scan (verdict must read
UNMEASURED); (b) a finite transitive preorder with causal `gamma`, finite or infinite `I+`, and
`P_set + not-P_tail` is exhibited; (c) the omega-chain model violates transitivity/reflexivity, or
`P_set` fails, or some `q_j` (j<N) sees a tail; (d) T1 fails on any enumerated preorder; (e) the
content-located anchors are missing or carry a forbidden token at the pinned hash.

Re-run after any F1 revision: a new sha256 voids this snapshot.
