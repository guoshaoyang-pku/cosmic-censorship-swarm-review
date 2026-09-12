# Cosmic censorship: formulation record (F1, F2a, F2b)

Formulation group lead — `astra-lead-formulation`. Companion to the machine-readable schemas in
`artifacts/formulation/schemas/`. This document states the three classes in words and formulas,
records the decisions that fixed them, and lists what remains open. **It asserts no theorem, no
refutation, and no known-status claim**; status signals from the literature ledger are quoted with
their scope caveats and are owned by L1. Frozen hashes: `FROZEN.json` (revision 13+), verifiable
with `python3 artifacts/formulation/tools/verify_frozen.py`.

---

## 0. Common machinery

**Ambient theory.** Four-dimensional Einstein vacuum equations, `Ric(g) = 0`, `Λ = 0`, classical
solutions. No matter, no cosmological constant.

**Initial data.** A triple `(Σ, h, K)`: `Σ` connected, oriented, complete, diffeomorphic to `R³`
(exactly one asymptotically flat end); `h` a Riemannian metric, `K` a symmetric 2-tensor; both
satisfy the vacuum constraints

```
R(h) − K_ij K^ij + (tr_h K)² = 0 ,        D^j (K_ij − (tr_h K) h_ij) = 0 .
```

Default regularity: smooth with decay, `h_ij − δ_ij = O(r⁻¹)`, `|d^k h| = O(r^{−1−k})`,
`K_ij = O(r⁻²)`, `|d^k K| = O(r^{−2−k})`. Registered Sobolev variant: `h − δ ∈ H^s_δ`,
`K ∈ H^{s−1}_{δ+1}`, `s > 5/2`, `δ ∈ (1/2, 1)`. Thresholds are widely used but **unanchored** —
L1 has not located a source; treated as a class parameter, not a fact.

**Development.** `(M, g)` is the maximal globally hyperbolic development (MGHD) of the data,
unique up to isometry, with `Σ` a Cauchy surface. "Maximal" means maximal among globally
hyperbolic developments — this is **not** inextendibility, which is a separate property.

**Future null infinity `I⁺`.** A conformal completion with `Ω > 0` on `M`, `Ω = 0`, `dΩ ≠ 0` on
`I⁺`, `g̃ = Ω²g` extending with the assumed `C^k` regularity, `I⁺` null and diffeomorphic to
`R × S²`. `k` is a class parameter, part of the assumption. Asymptotic simplicity is **not**
assumed for F1.

**Genericity.** All three classes quantify over a comeager (residual) set `G` in the *subspace
topology on the constraint manifold* `X^{s,δ}_vac(AF)` induced from the weighted Sobolev product.
`X_vac` is a closed subset of a Banach space, hence a Baire space, so `G` is non-empty and
comeagerness is not vacuous. (Reading the topology on the unconstrained product would make
`X_vac` itself meager and destroy the notion.) The quotient by asymptotically-identity
diffeomorphisms is **not** used to define comeagerness; all predicates here are diffeomorphism
invariant, and the quotient construction remains an open technical gap.

**Membership is set-level.** The schema does not decide whether an individual datum lies in `G`.
Symmetric/stationary data are *expected* to lie outside `G` in the vacuum classes, but that is a
proof obligation, not a schema field.

---

## 1. F1 — AF-WCC-VAC-GEN

### Statement

> For generic asymptotically flat vacuum initial data, the maximal development is asymptotically
> flat at `I⁺`, `I⁺` is complete, and no future-incomplete causal geodesic is visible from `I⁺`.

### Quantifiers (exact, in order)

```
∀(s, δ) ∈ D0  ∃ G_{s,δ} ⊆ X^{s,δ}_vac(AF) comeager  ∀(Σ, h, K) ∈ G_{s,δ}
    ∃ conformal completion (M̃, g̃, Ω) :
        (i)  I⁺ null, I⁺ ≅ R × S²,
        (ii) every null generator of I⁺ is future-complete,
    ∀ future-inextendible causal geodesics γ of finite affine length:
        ¬∃ q ∈ I⁺ with the tail of γ contained in J⁻(q) ∩ M .
```

The generic set is chosen **before and independently of** the data. Swapping the first two
quantifiers gives a trivial statement; that is why `order_matters` is true and why gate rule R27
checks it.

Negation (what a refutation must exhibit): the set of data whose development either fails to admit
such a completion, or has an incomplete generator of `I⁺`, or has a finite-affine-length causal
geodesic visible from `I⁺`, is **non-meager**.

### Visibility

A future-inextendible causal geodesic `γ: [0,T) → M` with `T < ∞` in affine parameter is
**visible from `I⁺`** iff there are `q ∈ I⁺` and `t₀ ∈ [0,T)` such that the **tail**
`γ([t₀,T)) ⊆ J⁻(q) ∩ M`. The tail formulation is essential: a geodesic that begins in the
exterior and ends inside the black-hole region is not visible, yet it is not contained in
`M ∖ J⁻(I⁺)` either. The formal negation is "for every `q` and every `t₀`, the tail is not
contained in `J⁻(q)`" — **not** "`γ` lies in the black-hole region", which is strictly stronger.

### Non-vacuity

The class must be applied to data whose development is future geodesically **incomplete**;
otherwise the visibility clause has no content and dispersion satisfies it trivially. Requiring
the black-hole region to be non-empty is a *different* statement (black-hole formation) and is
explicitly not part of this class.

### Falsifiers

- **Tier 1 (refutes the class):** show the failure set is **non-meager**. One datum with a visible
  singularity is not enough in general, because `G` is existentially quantified and individual
  membership is undecided. If the class is *instantiated* with an explicit generic set `G*`, then a
  single datum in `G*` with a visible singularity refutes the instantiation.
- **Tier 2 (refutes only "for all data"):** one datum with a visible incomplete causal geodesic,
  labelled `refutes_strengthening_only`.

### Status signals (L1-owned, verified ledger)

| id | what it is | scope caveat |
|---|---|---|
| D-001 | statement of record for WCC; open conjecture | wording quoted from a 2025 review; Penrose 1969 metadata-only |
| T-204 | rigorous WCC-type result for near-Schwarzschild data | codimension-3 restricted data; not generic |
| T-208 | peer-reviewed naked-singularity exterior | non-generic/self-similar → tier-2 only |
| T-209 | preprint interior + gluing for T-208 | genericity and MGHD status depend on the unrefereed gluing |

No ledger entry proves or refutes F1 for generic AF data.

---

## 2. F2a — AF-SCC-C2-VAC-GEN

### Statement

> For generic asymptotically flat vacuum initial data, the maximal development admits no proper
> **future** extension that is a `C²` Lorentzian solution of the vacuum equations.

### Quantifiers

```
∀(s, δ) ∈ D0  ∃ G_{s,δ} comeager  ∀(Σ, h, K) ∈ G_{s,δ} :
    ¬∃ (M′, g′, ι)  a proper future C² vacuum extension of the MGHD.
```

### The extension predicate (frozen)

`(M′, g′, ι)` is a proper future `C²` vacuum extension iff

- **(a)** `ι: M → M′` is an isometric embedding;
- **(b)** `ι(M)` is an open, proper subset of `M′`;
- **(c)** `M′` is a smooth connected time-orientable 4-manifold whose orientation restricts;
- **(d)** `g′` is a `C²` Lorentzian metric (signature `(−,+,+,+)`);
- **(e)** `Ric(g′) = 0` holds classically on all of `M′`;
- **(f)** the extension adds points to the future: `int(M′ ∖ ι(M)) ≠ ∅` and there are `q ∈ ι(M)`,
  `p ∈ int(M′ ∖ ι(M))` with `p ∈ I⁺(q; g′)`.

Decisions frozen here: **future** (not two-sided), `C²` exactly (not `C^{1,1}`, `C¹`, `H²_loc`, or
smooth-only), equations required, `M′` need not be globally hyperbolic, `ι` is `C^∞`.

### Non-vacuity

The class must be applied to data whose development is not future geodesically complete. The
expectation that a future-complete development admits no future extension is a **proof obligation,
not an elementary fact** (the one-line argument needs a causality step in `M′`, which is not assumed
globally hyperbolic). No counterexample is known in the frozen class.

### Status signals

| id | what it is | scope caveat |
|---|---|---|
| T-401 | no peer-reviewed `C²`-inextendibility theorem for generic AF vacuum Cauchy data located as of 2026-09-11 | absence of evidence, not impossibility |
| T-305 | conditional Lipschitz-inextendibility near `i⁺` | preprint; conditional on a Price-law estimate; only the piece near `i⁺` |
| T-402 | revised SCC picture: `C⁰`-extendible but generically `C²`-singular | the authors' interpretation, not a theorem |
| T-514, T-520 | model-class `C²` results (spherical EM-scalar; `T³`-Gowdy) | different data classes; do not transfer |

---

## 3. F2b — AF-SCC-C0-VAC-GEN

### Statement (frozen, broad form)

> For generic asymptotically flat vacuum initial data, the maximal development admits no proper
> **future** extension whose metric is merely continuous (`C⁰`) and Lorentzian.

Extension predicate: as above with `g′` continuous and nondegenerate, `M′` still a **smooth**
manifold (the category in which a metric is a tensor field), and **no equation required**;
`int(M′ ∖ ι(M)) ≠ ∅` and a chronological-future witness as in (f), with a recorded caveat that for
degenerate `C⁰` causal structure the witness must instead be a timelike curve (Grant et al.
arXiv:1901.07996, unverified). Two variants are registered separately and must not be substituted:
`scc_c0_distributional_vacuum` (requires `Ric = 0` distributionally; strictly weaker statement) and
`scc_l2loc_vacuum` (`H²_loc` curvature; intermediate).

### Class-identity warning (the most important scope finding)

L1's verified entry **D-002** records the `C⁰` formulation as inextendibility **across the Cauchy
horizon**. The frozen class here is **broader**: no proper future extension at *any* future
boundary. These are different statements.

L1's **T-301** states a *conditional refutation* of the horizon-localized formulation: for data
posed **inside the black-hole interior**, if the Kerr exterior is dynamically stable, the maximal
evolution extends across a non-trivial piece of Cauchy horizon with continuous metric. The
antecedent is claimed at **preprint level** for the full subextremal range (T-515/T-528).

**This does not refute the frozen class**, because (i) T-301 uses interior data, not AF Cauchy
data; (ii) L1 records that retrieval of the interior-data assumptions from event-horizon asymptotics
was not located; (iii) T-301's own "does not imply" list excludes the AF class. The refutation
candidate is therefore quarantined to the candidate variant **AF-SCC-C0-CH-VAC-GEN**. Conversely,
the frozen class must not be credited with T-302 (exact-Schwarzschild `C⁰`-inextendibility), which
is an exact-solution result with no inner horizon.

### Falsifiers

Tier 1: show the set of data admitting a proper future `C⁰` extension is non-meager (general route),
or exhibit a datum in an instantiated `G*`. Tier 2: one extendible datum, labelled
`refutes_strengthening_only`. A visible singularity is a **WCC** falsifier and is not the falsifier
of this class.

---

## 4. Separation ledger and forbidden conflations

**C2 vs C0.** Extension sets are nested:

```
E_{C²}  ⊆  E_{C^{1,1}}  ⊆  E_{H²_loc}  ⊆  E_{C⁰}
```

so statement strength runs the other way: `C⁰`-inextendibility ⇒ `H²_loc`-inextendibility ⇒
`C^{1,1}`-inextendibility ⇒ `C²`-inextendibility, and **never** the converse. This ordering was
wrong in an earlier revision and was corrected after independent review R2; the gate now enforces
the direction in the implication ledger (R16) and forbids foreign regularity content in assertive
fields (R31).

**Forbidden:** the phrase "C0 or C2" as a class name; binding a `C²` result to the `C⁰` class or
vice versa; deriving visibility, `I⁺` completeness, or asymptotic predictability from an SCC class;
deriving inextendibility or black-hole formation from F1; using a bare metric extension as a
counterexample to the `C²` class (equations are required there); using a curvature hypothesis in the
`C⁰` class (curvature invariants are undefined for merely continuous metrics).

---

## 5. Decisions log (with provenance)

| # | decision | why | source |
|---|---|---|---|
| 1 | WCC conclusion = `I⁺` complete ∧ no visible incomplete causal geodesic | standard formulation; avoids assuming what is concluded | D-001 |
| 2 | Visibility is a **tail** predicate | whole-geodesic containment misclassifies a geodesic ending in the black-hole region | R1 F02 |
| 3 | Genericity = comeager in the **subspace** topology on the constraint manifold | product topology makes `X_vac` meager; quotient is unbuilt | R1 F04 |
| 4 | Falsifier tier 1 requires **non-meagerness**, not a single datum | `G` is existentially quantified; membership is set-level | R1 F01 (supersedes an earlier reading) |
| 5 | `open_dense_escape` is **stronger** than comeager, not weaker | a dense open set is comeager (constant intersection) | flash-15 |
| 6 | SCC is **future** inextendibility | one-ended AF data can extend to the past into a white hole without failing future determinism | R2 |
| 7 | SCC extension predicates freeze direction, regularity, equation requirement, `ι` regularity | each is a separate axis; unfrozen axes produced scope errors | R2 |
| 8 | `H²_loc` ordered **inside** `C^{1,1}`–`C⁰` chain | `C²` metrics have locally bounded curvature | R2 major |
| 9 | `C⁰` frozen as **broad**, horizon-localized variant separated | prevents both over-claiming T-301 and under-claiming T-302 | D-002, T-301 |
| 10 | Non-vacuity on future-incompleteness, never on black-hole formation | black-hole formation is a separate statement | worker-16 F1-16-03 |
| 11 | `C²` vacuity argument recorded as an **unverified obligation** | `M′` is not assumed globally hyperbolic | R2 major |
| 12 | `extensions:` is a key-allowlist escape hatch only, never a content exemption | four held-out leaks hid inside it | FORM-HELDOUT-07 |

---

## 6. Open obligations and blockers

1. **Map wiring (Astra).** The map still points F1/F2 at worker drafts; the frozen canonical
   artifacts are under `artifacts/formulation/schemas/`. Patch `FORM-MAP-PATCH-002` dry-runs clean.
2. **L1 anchoring (literature).** Unanchored: the Sobolev thresholds and weight range; the positive
   mass theorem statement used for `m_ADM ≥ 0`; the future-asymptotic-predictability equivalence;
   Grant et al. arXiv:1901.07996; Rendall gr-qc/0503112.
3. **Human-scale formulation.** Meagerness of the excluded families; the diffeomorphism quotient;
   non-vacuity witness membership; the `C²` vacuity derivation; clause (f) under degenerate `C⁰`
   causal structure; the class-identity adjudication of the horizon-localized variant.
4. **Verification layer.** One held-out escape remains (WCC content rephrased inside the exempt
   `visibility.reason` field); a second independent held-out round (FORM-HELDOUT-08) is running.

## 7. How to verify

```bash
python3 artifacts/formulation/tools/verify_frozen.py          # manifest vs disk
python3 artifacts/formulation/tools/run_gate_tests.py         # structural gate + controls + mutants
python3 artifacts/formulation/tools/measure_semantic_escape.py # regenerate the re-based corpus
python3 artifacts/formulation/tools/run_acceptance.py         # two-stage acceptance (union criterion)
python3 artifacts/formulation/tools/check_taxonomy_consistency.py
python3 artifacts/formulation/tools/apply_map_proposal.py     # map patch dry run (Astra applies)
```
