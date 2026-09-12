# W076-GFORM-VIS-STRENGTH-03 — visibility-reading strength relation at F1 rev12

**Worker:** worker-076 (bounded execution worker; evidence only, no gate verdict, no node transition)
**Class:** `AF-WCC-VAC-GEN` (F1) · **Variant:** `SET` · **Gate:** `G-FORM`
**Verdict:** `STRICTNESS_INVERTED` · **Controls:** 5/5 pass

## Deliverables (this directory)

| file | sha256 | role |
|---|---|---|
| `probe_result.json` | see `SHA256SUMS.txt` | machine-readable result: claims, lemmas, controls, falsifier |
| `probe_vis_strength.py` | see `SHA256SUMS.txt` | rerunnable probe (deterministic, no network, read-only on canonical files) |
| `README.md` | this file | narrative summary |
| `SHA256SUMS.txt` | — | hash pins for the bundle |

## The question

At the live canonical bytes `schemas/af_wcc_vacuum.yaml#cce9c601` (revision 12), F1 declares
**one** visibility predicate (line 213, single-q **tail**) and registers the set-based reading as a
**variant** (lines 229–237) with these assertions:

- line 233 — `VIS_set(γ)` ⇔ `γ([0,T)) ⊆ ⋃_{q∈I⁺} J⁻(q)`
- line 234 — *"strictly STRONGER than this class's single-q tail predicate … the two readings are
  NOT equivalent"*
- line 236 — open falsifier: *"show the two readings equivalent"*

and line 215 separately asserts B-containment is *"strictly stronger"* than the canonical negation.

## Method

Order-theoretic decision on the causal-order axioms the schema itself declares
(`J⁻(q)` reflexive, transitive, past-closed). Two lemmas, both machine-checked:

**Lemma A (finite-chain collapse).** For any poset, any `I⁺`, any **finite** chain `γ`:
`VIS_set(γ) ⇒ VIS_singleq(γ)`. *Proof:* apply `VIS_set` at the last point; get `q ∈ I⁺` with
`x_{n-1} ⩽ q`; transitivity pulls every earlier point into `J⁻(q)`, so the whole curve is a tail.
→ verified exhaustively on **8 658** (chain, I⁺) cases over **571** posets, 0 violations.

**Lemma B (ω-chain separation).** Carrier `{x_i} ∪ {q_j}`, `x_i ⩽ q_j ⇔ i ⩽ j`, `I⁺ = {q_j}`,
`γ = (x_0 < x_1 < …)`. Then `VIS_set` holds (`x_i ⩽ q_i`) but `VIS_singleq` fails (for every `q_j`
and finite `t₀`, the point `x_{max(j,t₀)+1}` is in the tail and is not `⩽ q_j`).

## Result

| # | claim | status |
|---|---|---|
| 1 | `VIS_singleq ⇒ VIS_set` unconditionally | derived-true |
| 2 | Converse holds for every finite chain | machine-checked exhaustive |
| 3 | Converse **fails** on the ω-chain ⇒ readings **not equivalent** | machine-checked witness |
| 4 | Line 215's *B-containment strictly stronger* is **correct** (reproduced) | machine-checked |
| 5 | Therefore line 234's direction is **inverted**: the canonical single-q predicate is the strictly stronger reading | derived from 1–4 |

The file contradicts itself: line 215 (correct) makes variant SET's *negation* the stronger
statement, which by negation makes variant SET *weaker* — the opposite of line 234. The "NOT
equivalent" conclusion is right; the arrow points the wrong way. Line 236's falsifier asks for an
equivalence Lemma B refutes, so the strictness claim has no valid support as written.

**Consequences.** ESC-2 option (A) "reconcile to one predicate" remains available as a *convention*
choice, but cannot be justified as "the two are equivalent". Option (C) "keep named variants" rests
on a strength relation pointing the wrong way. The rebased delta `AF-WCC-VAC-GEN.variant-SET.delta.json#45b9b6a8`
(rebased 00:33:47) repeats the inverted wording against the new base, so the repair belongs in the
variant record, not only in F1.

**Deciding hypothesis isolated.** The readings differ **iff** `I⁺` admits a *non-down-directed*
family of witnessing points — `{q_i}` with `x_i ⩽ q_i` and no single `q` covering a tail. Whether an
admissible conformal completion can carry such a family is the open physical obligation, and it is
exactly what `witness_protocol` steps (1)–(5) would have to exhibit.

## Drift finding (recorded)

The canonical bytes were **overwritten twice during this task**:

| artifact | at task start | live at measurement |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9` rev11 | `cce9c601` rev12 |
| `research_map/formulation_taxonomy.yaml` | `276009f4` rev4 | `0abb9ed8` rev5 |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750` | `5476a3f2` |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9` | `55d0a1ea` |
| `…variant-SET.delta.json` | `b5bca15e` | `45b9b6a8` (rebased 00:33:47) |

Rewrites landed 00:31:41–00:32:02. Any review verdict bound to the superseded hashes does not bind
the live bytes. The first probe run correctly read `UNMEASURED` on the stale pins. rev12 closed
F1-review-19 HF-06 by retyping D5 to `(q,t₀)` tail pairs; the variant SET block and the line-215
B-claim are unchanged in substance and are the subject of this probe.

## Falsifier

FALSE if (a) a machine-checked counterexample to Lemma A exists; (b) the ω-chain escape certificate
fails; (c) any pinned input `sha256` differs between the pre/post scan (verdict must then read
`UNMEASURED`); (d) any control fails; (e) the F1 anchor lines no longer carry the extracted tokens at
the pinned hash. A **Lorentzian realization** of the ω-chain pattern would *strengthen* this result,
not falsify it.

## Scope

Order-theoretic only, on the declared causal-order axioms. No Lorentzian conformal completion is
constructed; no claim is made that `⋃_{q∈I⁺} J⁻(q)` is a proper subset of `J⁻(I⁺)` in any spacetime.
No canonical file was edited. `validation_status = unverified`.
