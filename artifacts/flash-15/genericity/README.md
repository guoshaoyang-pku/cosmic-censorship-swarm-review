# FORM-GEN-05 — genericity-notion separation matrix

**Status: unverified proposal. No node completion, no theorem, no physics result.**
Owner for binding: `astra-lead-formulation` (node F1, gate G-CLASSBIND). Everything here is
structural: definitions, transfer states, and constructed set-theoretic witnesses. Physical
claims about cosmic censorship are **not** made; the class conclusions stay with the schemas.

Assignment: `assign-FORM-GEN-05-20260911T2331`.

## Files

| file | role |
|---|---|
| `genericity_matrix.json` | the deliverable: 4 notion definitions, 12 ordered-pair transfer rows, R07-shaped per-class sections, 6 witnesses, 7 citation records |
| `build_matrix.py` | re-runnable generator; asserts all 12 ordered pairs are emitted |
| `check_matrix.py` | N1–N5 structural acceptance checker |
| `acceptance_run.txt` | captured build + checker transcript (10/10 PASS) |

## Why this artifact exists

`artifacts/formulation/rule_spec.json` R07 makes the genericity notion a *part* of each class
schema and demands `genericity.ambient_space`, `genericity.topology_or_measure`,
`genericity.generic_set`, `genericity.excluded_set`, `genericity.transfer_failures`, and a
statement that changing the notion yields a different class. The vocabulary is
`residual_comeager`, `full_measure`, `open_dense_escape`, `finite_codimension_complement`,
`none`. This artifact supplies the definitions and — the load-bearing part — the
non-implications between them, each with an explicit witness.

## The three slots a genericity notion must fix

1. **Ambient space** — genericity is a property of a set inside a declared space. For the AF
   classes the candidate is the vacuum constraint set
   `D = {(h,K) ∈ H^s_δ(Σ) × H^{s-1}_{δ+1}(Σ) : constraints}`, but `D` is *not* open in the
   product, so Baire/manifold structure must be declared (slice/Fredholm), not assumed.
2. **Topology or measure** — a norm/index for Baire notions, a named measure class for
   `full_measure`. No single topology or measure is canonical here.
3. **Shape of the generic set** — countable intersection of open dense sets (comeager),
   measure-one set, one open dense set, or complement of a closed finite-codimension
   submanifold.

## Transfer semantics

`X → Y holds` means: for every property P, if P holds on all data of some X-generic set, then
P holds on all data of some Y-generic set (equivalently, every X-generic set contains a
Y-generic set). This is statement-level transfer; it is not a claim that generic sets coincide.

## Transfer matrix

| from \ to | residual | full_measure | open_dense | finite_codim |
|---|---|---|---|---|
| **residual_comeager** | — | fails (W1) | fails (W3) | fails (W3) |
| **full_measure** | fails (W2) | — | fails (W3) | fails (W5) |
| **open_dense_escape** | **holds** | fails (W4) | — | fails (W4) |
| **finite_codimension_complement** | **holds** | **open** (W6) | **holds** | — |

The three `holds` are definitional: an open dense set is comeager; a closed proper
finite-codimension submanifold has empty interior, so its complement is open dense and hence
comeager. The `fails` entries are constructive; the one `open` entry is open precisely because
it needs a declared measure class, and no canonical measure exists on the AF constraint set.

## Witnesses (all self-contained, no citation)

- **W1** `[0,1]` has a comeager Lebesgue-null set: thicken an enumeration of ℚ into open dense
  `U_n` of measure ≤ 2^(−n); `G = ∩ U_n`.
- **W2** complement of W1: meager with full Lebesgue measure.
- **W3** irrationals in `[0,1]`: comeager *and* full measure, empty interior — kills both
  `→ open_dense` directions and `residual → finite_codim`.
- **W4** complement of the Smith–Volterra–Cantor set: open dense, measure < 1 — kills
  `open_dense → full_measure` and `open_dense → finite_codim`.
- **W5** complement of the middle-thirds Cantor set: full measure; in a 1-manifold every closed
  codim ≥ 1 submanifold is finite and cannot contain the Cantor set — kills
  `full_measure → finite_codim`.
- **W6** `μ = δ₀` on `[0,1]`, `Z = {0}`: `μ(Z) = 1` — shows the one open row really is
  measure-class-dependent.

## Per-class recommendation (recommendation only; schema owner binds)

- **Primary `kind`: `residual_comeager`** for all three classes. It is the only notion in the
  vocabulary that is well-defined without inventing a measure on a nonlinear constraint set,
  and it is the notion the literature normally means by "generic AF data".
- **Secondary: `finite_codimension_complement`** only if the schema also declares the manifold
  structure and states codimension *in D* (not in the ambient product). Note the trap in
  `C3_dhrt_2104.08222`: there "codimension-3 submanifold" is a **constraint the data are
  required to lie on**, not an excluded set. The token must not be reused for both roles.
- **Not recommended:** `full_measure` (no canonical measure class; unresolved),
  `open_dense_escape` (stronger than needed and typically unverifiable for symmetry/critical
  excluded sets).
- Keep the notion **identical** across the C2 and C0 schemas so R16's implication ledger
  (C2-extension ⊂ C0-extension; C0-inextendibility ⇒ C2-inextendibility) is not confounded by
  a notion change.
- Each `per_class_genericity_section` carries `paste_target` (the schema path from gate G-FORM's
  evidence list) and `r07_keys_present`, so the section can be pasted into the schema verbatim.

## Strength order — why the direction words matter

Under the coverage reading ("P holds on a generic set"), implications go:

```
finite_codimension_complement  ⇒  open_dense_escape  ⇒  residual_comeager
```

Each arrow is strict; the converse fails (W3 and the 1-manifold argument). `full_measure` is
incomparable with all three in general, and its relation to `finite_codimension_complement` is
open without a declared measure class.

**Consequence for the drafts:** an open-dense claim is *stronger* than a residual claim, not
weaker. Any sentence saying the open-dense reading "weakens the conjecture" or is "strictly
weaker" is inverted under the coverage reading; either fix the direction or state an explicit
non-coverage ("holds only on") semantics. See `strength_adjudication.json` (ADJ-2).

## Independent review of this artifact

A fresh-context reviewer (separate agent, no shared conversation) was asked to falsify every
row. Result saved at `review_genericity_matrix.json`: all 12 row states, the four definitions,
the strength order and W1–W6 were confirmed (12/12 agree; no counterexample found to any
state). Two false sub-claims in explanatory prose were found and fixed in revision 5:

- RC→FCC prose claimed every closed codim≥1 submanifold of R is finite — false, the integers
  are an infinite closed discrete 0-dimensional embedded submanifold. Corrected to the
  closedness+density argument; the row verdict is unchanged.
- FCC→RC prose claimed a non-closed immersed Z breaks the comeager transfer — false, such a Z
  is meager, so its complement is comeager. Closedness is load-bearing only for the open-dense
  target.

Two loose "repair" remarks and the second falsifier of the proposed vocabulary extension were
also corrected. `state`, the four definitions and W1–W6 are unchanged. Details:
`adversarial_review_response.json`.

## Citation honesty (N4)

Verified by fetch + verbatim quote: RSR `arXiv:1912.08478`, Christodoulou 1999
`arXiv:math/9901147`, DHRT `arXiv:2104.08222`, Dafermos–Luk `arXiv:1710.01722`, CGNS
`arXiv:1406.7261`, Isenberg `arXiv:1505.06390`, plus the local `rule_spec.json`.

Four flags the schema owner must not paper over:

1. **Christodoulou 1999 "codimension one" is NOT in the fetched abstract.** The recurring
   claim that naked-singularity data form a codimension-one set is marked `unresolved` until a
   body-text quote is fetched. Do not bind `finite_codimension_complement` to it.
2. **Dafermos–Luk use "generically" with no ambient space and no topology/measure** in the
   fetched abstract. Recorded as `genericity_undefined_in_source`; it cannot be bound to any of
   the four notions without a further source.
3. **RSR `1912.08478` does not state asymptotic flatness or genericity** in the fetched
   abstract; it constructs exterior naked-singularity solutions via a new *self-similarity*,
   which is a non-genericity signal. It cannot be used as a generic counterexample to WCC.
4. **CGNS is a foreign class** (Λ > 0, spherical, Einstein–Maxwell–scalar) — anti-scope only.

## Proposed vocabulary extension (owner approval required)

`schemas/af_scc_c2_vacuum.yaml` declares its generic set **open in a weighted C1 topology and
dense in a weighted C∞ topology**. No single `genericity_kind` token expresses that hybrid.
`genericity_matrix.json` therefore carries a `proposed_vocabulary_extension` (not part of the
12-row matrix) defining `open_in_A_dense_in_B`, its transfer to `open_dense_escape` (holds only
if A is finer than B, with a 3-point counterexample otherwise), and the decision the owner must
make: declare both topologies under an existing token, or extend the vocabulary.

## Next falsifier

Fetch a body-text sentence from Christodoulou 1999 (or a source quoting it) that states a
genericity quantifier; if it names a notion outside this vocabulary, the matrix's claim that
the four notions cover the AF usage is falsified and the vocabulary must be extended by the
schema owner. Second falsifier: exhibit a measure class on AF data for which the intended
excluded set has measure zero *and* is comeager-null in the opposite direction, which would
force `full_measure` back into the class.

## What this artifact does not do

It does not select a class conclusion, does not assert any theorem, does not claim that any
named source proves a class conclusion, and does not modify any schema. Gate G-CLASSBIND is for
the lead to run.
