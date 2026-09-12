#!/usr/bin/env python3
"""Build artifacts/flash-15/genericity/genericity_matrix.json  (FORM-GEN-05).

Re-runnable: every ordered pair of the four notions is emitted programmatically, so a missing
pair is impossible. All content is structural (definitions, transfer states, constructed
witnesses) or verbatim-quoted fetched abstracts; no theorem is claimed. Assignment:
assign-FORM-GEN-05-20260911T2331 (astra-lead-formulation, node F1, gate G-CLASSBIND).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "genericity_matrix.json"

RETRIEVED = "2026-09-11T23:20:00+08:00"  # session fetch window 23:20-23:22 CST, minute precision

NOTION_IDS = ["residual_comeager", "full_measure", "open_dense_escape", "finite_codimension_complement"]

CITATIONS = {
    "C1_rsr_1912.08478": {
        "citation_status": "verified",
        "url": "https://arxiv.org/abs/1912.08478",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "Rodnianski, Shlapentokh-Rothman, 'Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution', arXiv:1912.08478v2 (2019-12-18, rev. 2022-10-19)",
        "fetched_quote": "In this work we initiate the mathematical study of naked singularities for the Einstein vacuum equations in $3+1$ dimensions by constructing solutions which correspond to the exterior region of a naked singularity. A key element is our introduction of a new type of self-similarity for the Einstein vacuum equations.",
        "scope_limit": "The fetched abstract states a construction via a new self-similarity and does NOT state asymptotic flatness of the data, nor that the construction arises from an open/comeager/full-measure set. Any schema use as a 'generic counterexample to WCC' is therefore NOT supported by this source; self-similarity is a non-genericity signal, not a genericity proof."
    },
    "C2_christodoulou_1999": {
        "citation_status": "verified",
        "url": "https://arxiv.org/abs/math/9901147",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "D. Christodoulou, 'The instability of naked singularities in the gravitational collapse of a scalar field', Ann. of Math. (2) 149 (1999) 183-217; arXiv:math/9901147",
        "fetched_quote": "The present paper, which is a continuation previous work, addresses this question in the context of the spherical gravitational collapse of a scalar field.",
        "scope_limit": "The fetched abstract contains NO genericity quantifier and NO 'codimension one' statement. The widely repeated phrase that the naked-singularity data form a set of codimension one is therefore UNRESOLVED for schema use until a body-text quote is fetched. This is a live N4 flag, not a rejection of the paper."
    },
    "C3_dhrt_2104.08222": {
        "citation_status": "verified",
        "url": "https://arxiv.org/abs/2104.08222",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "Dafermos, Holzegel, Rodnianski, Taylor, 'The non-linear stability of the Schwarzschild family of black holes', arXiv:2104.08222 (2021)",
        "fetched_quote": "general vacuum initial data, with no symmetry assumed, sufficiently close to Schwarzschild data evolve to a vacuum spacetime which (i) possesses a complete future null infinity $\\mathcal{I}^+$ ... provided that the data are themselves constrained to lie on a teleologically constructed codimension-$3$ \"submanifold\" of moduli space.",
        "scope_limit": "Supports a perturbative, codimension-3-constrained class, not a generic-in-data-space statement. Note the word 'codimension' here names a CONSTRAINT on admissible data, not an excluded set; the schema must not reuse the codimension token for genericity without saying which role it plays."
    },
    "C4_dafermos_luk_1710.01722": {
        "citation_status": "verified",
        "url": "https://arxiv.org/abs/1710.01722",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "Dafermos, Luk, 'The interior of dynamical vacuum black holes I: The C^0-stability of the Kerr Cauchy horizon', arXiv:1710.01722; Ann. of Math. (2) 202(2):309-630 (2025)",
        "fetched_quote": "We prove that for all such data, the maximal Cauchy evolution can be extended across a non-trivial piece of Cauchy horizon as a Lorentzian manifold with continuous metric. ... if the exterior region of the Kerr family is proven to be dynamically stable---as is widely expected---then it will follow that the $C^0$-inextendibility formulation of Penrose's celebrated strong cosmic censorship conjecture is in fact false. The proof suggests, however, that the $C^0$-metric Cauchy horizons thus arising are generically singular in an essential way, representing so-called \"weak null singularities\", and thus that a revised version of strong cosmic censorship holds.",
        "scope_limit": "Two flags. (a) The failure of C^0-inextendibility is conditional on Kerr stability and stated for interior data. (b) The source uses the word 'generically' with NO ambient space and NO topology/measure: for schema purposes this occurrence must be recorded as 'genericity_undefined_in_source' and may not be bound to any of the four notions without a further source."
    },
    "C5_cgns_1406.7261": {
        "citation_status": "verified",
        "url": "https://arxiv.org/abs/1406.7261",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "Costa, Girao, Natario, Silva, 'On the global uniqueness for the Einstein-Maxwell-scalar field system with a cosmological constant. Part 3', Ann. PDE 3:8 (2017); arXiv:1406.7261",
        "fetched_quote": "Our results provide evidence against the validity of the strong cosmic censorship conjecture when $\\Lambda>0$.",
        "scope_limit": "Different class: Lambda>0, spherical symmetry, Einstein-Maxwell-scalar, characteristic data on a subextremal Reissner-Nordstrom horizon. Carries a FOREIGN asymptotic structure for all three target classes; usable only as an anti-scope example."
    },
    "C6isenberg_1505.06390": {
        "citation_status": "verified",
        "url": "https://arxiv.org/abs/1505.06390",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "J. Isenberg, 'On Strong Cosmic Censorship', Surveys in Differential Geometry 20 (2015); arXiv:1505.06390",
        "fetched_quote": "We focus in particular on model versions of SCC which have been proven for restricted families of spacetimes (e.g., the Gowdy spacetimes), and the role played by the generic presence of Asymptotically Velocity Term Dominated behavior in these solutions.",
        "scope_limit": "SECONDARY survey. May be used to locate primary sources and to show that 'generic' is used across SCC model problems, but may not be cited as establishing any class conclusion."
    },
    "C7_rule_spec": {
        "citation_status": "verified",
        "url": "artifacts/formulation/rule_spec.json",
        "retrieved_at": RETRIEVED, "retrieval_precision": "session_minute",
        "identity": "FORM-RULE-SPEC v1.0, owner astra-lead-formulation; R07 fixes the genericity key names; R14 fixes falsifier tiers; R16 fixes the C2/C0 implication ledger",
        "fetched_quote": "R07 ... genericity.kind in vocabulary; genericity.ambient_space and genericity.topology_or_measure named; genericity.generic_set defined as a set-builder or Baire formula; genericity.excluded_set present; genericity.transfer_failures non-empty; genericity.is_part_of_class=true with a statement that changing the notion yields a different class",
        "scope_limit": "Local spec, not a mathematical source."
    },
}

NOTIONS = {
    "residual_comeager": {
        "definition": "G is residual (comeager) in D iff G contains a countable intersection of open dense subsets of D. Equivalently D\\G is meager (a countable union of nowhere dense sets).",
        "ambient_space_requirement": "A topological space D. For the notion to be non-vacuous (residual sets nonempty, and in fact dense) D must be a Baire space, e.g. complete metric or locally compact Hausdorff; for AF data the standard candidate is a weighted Sobolev constraint manifold (Banach manifold).",
        "topology_or_measure_requirement": "A declared topology only. No measure needed. The topology must be named by norm/index: e.g. H^s_delta x H^{s-1}_{delta+1} with the schema's own (s,delta); a topology change changes the meager sets.",
        "quantifier_form": "exists G subseteq D, G comeager: forall d in G, P(d).",
        "generic_set_template": "G = { d in D : d avoids Q } with G ⊇ ∩_{n in N} U_n, U_n open dense in D; or directly G = D \\ M, M meager.",
        "excluded_set_template": "M = countable union of nowhere dense sets (meager). Typical intended M: data with a Killing symmetry, data on the critical/self-similar set, data whose development admits a visible incomplete causal geodesic.",
        "non_vacuity_requirement": "D Baire; otherwise ∩ U_n may be empty and the notion degenerates.",
        "falsifier": "Exhibit a meager set M whose complement fails P with a witness (i.e. the claim is false on a comeager set) — that refutes the residual-genericity claim; or exhibit D not Baire, which makes the quantifier vacuous."
    },
    "full_measure": {
        "definition": "G is full-measure in D iff G is measurable and mu(D\\G)=0 for a declared Borel measure mu on D (for a probability measure: mu(G)=1).",
        "ambient_space_requirement": "A measurable space D with a specified measure mu. On nonlinear constraint sets there is no canonical mu; the schema must name the measure class (e.g. a Gaussian measure induced by a declared covariance on a linearised slice, or a finite-dimensional approximation) or the notion is not well-defined.",
        "topology_or_measure_requirement": "A measure (or measure class) only. Topology optional; 'a.e.' does not imply 'open dense'.",
        "quantifier_form": "exists G subseteq D measurable, mu(G)=1: forall d in G, P(d).",
        "generic_set_template": "G = D \\ N with N measurable and mu(N)=0.",
        "excluded_set_template": "N, a mu-null set; its content depends entirely on the declared measure class.",
        "non_vacuity_requirement": "mu must be specified; changing mu changes N and can change the truth of P-a.e.",
        "falsifier": "Exhibit two admissible measure classes mu1, mu2 with mu1(N)=0 but mu2(N)=1 for the excluded set N — this shows the statement is measure-class-dependent and cannot be bound without naming mu."
    },
    "open_dense_escape": {
        "definition": "G is an open-dense-escape set iff G itself is open and dense in D (not merely containing a dense G_delta).",
        "ambient_space_requirement": "A topological space D with the declared topology. No completeness needed for the definition, but non-vacuity of statements about it is immediate (open dense sets are nonempty if D is nonempty).",
        "topology_or_measure_requirement": "A declared topology only.",
        "quantifier_form": "exists U subseteq D, U open and dense: forall d in U, P(d).",
        "generic_set_template": "U = D \\ Z with Z closed and nowhere dense (equivalently, int(cl Z)=empty).",
        "excluded_set_template": "Z closed nowhere dense; e.g. the set of data satisfying an extra closed constraint (symmetry, or a critical-surface equation).",
        "non_vacuity_requirement": "Z must be nowhere dense and proper; Z = D would make U empty.",
        "falsifier": "Exhibit a closed nowhere dense excluded set Z whose complement still admits a witness violating P — falsifies the open-dense reading; or show every admissible Z has empty interior in a way that forces U = D (statement becomes vacuous)."
    },
    "finite_codimension_complement": {
        "definition": "G = D \\ Z where Z is a closed embedded submanifold of D (or a finite union of such) with codimension >= 1 and Z != D. Non-degeneracy: codim Z >= 1.",
        "ambient_space_requirement": "D must carry a differentiable structure (Banach/Frechet manifold, or finite-dimensional manifold) in which 'codimension' is defined. For constraint sets this requires a slice/Fredholm structure; 'codimension in the ambient product' and 'codimension in the constraint set' are different numbers and the schema must say which.",
        "topology_or_measure_requirement": "Differentiable (C^1 at least) structure plus the norm topology. No measure needed for the definition.",
        "quantifier_form": "exists Z subseteq D closed embedded submanifold, 1 <= codim(Z) < infinity: forall d in D\\Z, P(d).",
        "generic_set_template": "G = D \\ Z, Z = { d in D : F(d)=0 } for a declared F with surjective differential (submersion) so that Z is a codimension-dim(target) submanifold.",
        "excluded_set_template": "Z as above; typical intended Z: data satisfying a finite number of scalar conditions (e.g. an exact self-similarity condition, an exact symmetry, a critical-mass equation).",
        "non_vacuity_requirement": "Z must be a genuine closed submanifold of the declared D with codim >= 1; an immersed non-closed Z makes the complement non-open.",
        "falsifier": "Exhibit an intended excluded set Z that is not a finite union of closed finite-codimension submanifolds of D (e.g. a Cantor-type set, or a countable union of submanifolds) — this refutes the finite-codimension reading in that ambient space."
    },
}

# Ordered-pair transfer results. Semantics fixed in `transfer_semantics` below.
P = {
    ("residual_comeager", "full_measure"): dict(
        state="fails",
        witness_or_source="W1: in D=[0,1] with Lebesgue measure, G = intersection_n U_n where U_n is an open dense union of intervals of total length 2^(1-n) around an enumeration of Q is comeager and lambda(G)=0. Taking P='x in G' gives a residual property that is not full-measure.",
        extra_hypothesis=None,
        falsifier="Not repairable by an equivalent measure: mu(G)=0 for every mu absolutely continuous with respect to Lebesgue. Independent review (2026-09-11) gives the stronger statement: for every Borel probability mu on [0,1] there is a comeager mu-null set (atomic case: remove an atom; atomless case: cover a countable dense set by mu-small open intervals). A claimed repair must therefore exhibit a space and a declared mu for which the transfer genuinely holds."),
    ("residual_comeager", "open_dense_escape"): dict(
        state="fails",
        witness_or_source="W3: the irrationals in [0,1] are comeager but have empty interior, so they contain no nonempty open subset. Hence 'P on a comeager set' does not yield 'P on an open dense set'.",
        extra_hypothesis=None,
        falsifier="Any nonempty open interval meets Q, so the witness has empty interior; a claimed repair must add residual-plus-open hypotheses not present in the notion."),
    ("residual_comeager", "finite_codimension_complement"): dict(
        state="fails",
        witness_or_source="W3 in D=R: the irrationals are comeager. Let Z be closed with codim>=1 and suppose R\\Z were contained in the irrationals; then Z contains Q. Since Z is closed and Q is dense in R, Z=R, contradicting Z != D and codim>=1. So no finite-codimension-complement set is contained in the irrationals and the transfer fails. Compact variant: in D=[0,1] every closed codim>=1 submanifold is finite and cannot contain the uncountable complement of the irrationals, giving the same conclusion. CAUTION (independent review 2026-09-11): 'finite' is a [0,1]-only shortcut; in R the integers are an infinite closed discrete 0-dimensional embedded submanifold, so the closedness+density argument is the correct one.",
        extra_hypothesis=None,
        falsifier="A repair would need every comeager set to contain the complement of a closed finite-codimension submanifold. Meagerness of the complement does not imply that (Q is meager but is not a finite union of submanifolds), and if the closed excluded set is dense then Z=D, which the non-degeneracy clause forbids."),
    ("full_measure", "residual_comeager"): dict(
        state="fails",
        witness_or_source="W2: the complement of W1's comeager null set G is meager and has full Lebesgue measure. So a full-measure set can be topologically negligible.",
        extra_hypothesis=None,
        falsifier="The witness is explicit. The suggested repair hypothesis (mu positive on every open set plus a zero-one law) does NOT repair it: by the covering/atom argument above, for every Borel probability mu on [0,1] there is a comeager set with no mu-full-measure subset (independent review, 2026-09-11). A repair must restrict the measure class explicitly and prove the transfer inside it."),
    ("full_measure", "open_dense_escape"): dict(
        state="fails",
        witness_or_source="W3: the irrationals in [0,1] have full Lebesgue measure and empty interior; no open dense subset is contained in them.",
        extra_hypothesis=None,
        falsifier="Nothing weaker than 'the full-measure set contains an open dense subset' repairs this; that is not a consequence of measure alone."),
    ("full_measure", "finite_codimension_complement"): dict(
        state="fails",
        witness_or_source="W5: in D=[0,1], C = the middle-thirds Cantor set has measure 0, so G = D\\C has full measure. Any closed finite-codimension (codim>=1) submanifold of the 1-manifold [0,1] is a finite set, and no complement of a finite set is contained in G.",
        extra_hypothesis=None,
        falsifier="A repair must assume the measure is transverse to finite-codim submanifolds (mu(Z)=0 for all such Z), which is exactly the extra hypothesis that the reverse direction needs."),
    ("open_dense_escape", "residual_comeager"): dict(
        state="holds",
        witness_or_source="Definitional: an open dense U is itself a countable intersection of open dense sets (the one-set intersection), hence comeager. No citation needed.",
        extra_hypothesis="None for the set inclusion. Additional hypothesis for non-vacuity: D Baire, otherwise a comeager set may be empty while U is nonempty (the inclusion U ⊆ U still holds, but the residual quantifier may be vacuous).",
        falsifier="Would require an open dense set that is not comeager — impossible by the definition of comeager as containing a countable intersection of open dense sets."),
    ("open_dense_escape", "full_measure"): dict(
        state="fails",
        witness_or_source="W4: in D=[0,1], U = complement of the Smith-Volterra-Cantor (fat Cantor) set is open and dense with lambda(U) = 1 - lambda(C) < 1. No full-measure subset of U exists.",
        extra_hypothesis=None,
        falsifier="The witness has positive-measure complement; the transfer would hold only under an extra hypothesis that every open dense set has full measure, which is false for Lebesgue measure and for any nondegenerate Gaussian measure with an open null-complement example."),
    ("open_dense_escape", "finite_codimension_complement"): dict(
        state="fails",
        witness_or_source="W4: U = complement of a fat Cantor set is open dense, but its complement Z is a Cantor set, not a finite union of closed finite-codimension submanifolds of [0,1]. No complement of such a Z is contained in U (a codim>=1 closed submanifold of [0,1] is finite and cannot contain Z).",
        extra_hypothesis=None,
        falsifier="Repair requires the excluded closed nowhere dense set to be a finite union of submanifolds; Cantor-type excluded sets violate it."),
    ("finite_codimension_complement", "residual_comeager"): dict(
        state="holds",
        witness_or_source="Definitional under the stated non-degeneracy (Z closed, codim>=1, Z != D): a closed set with empty interior is nowhere dense, so D\\Z is open dense; by the open_dense -> residual row it is comeager.",
        extra_hypothesis="Z closed, proper, codim>=1. Closedness is used here only to conclude that D\\Z is open (hence comeager via the open-dense row). It is NOT needed for the comeager conclusion itself: a second-countable finite-codimension immersed submanifold is locally a graph, hence a countable union of nowhere-dense pieces, hence meager, so its complement is comeager. Closedness is load-bearing for the open_dense target, where D\\Z must be open.",
        falsifier="For the comeager target no counterexample is available: any finite-codimension immersed submanifold (closed or not) is meager, so its complement is comeager; a dense immersed line in the torus has comeager complement, not 'neither open-dense nor comeager' (corrected after independent review 2026-09-11). To break the open_dense target instead, take Z with nonempty interior (codim 0), e.g. a closed ball: D\\Z is open but not dense."),
    ("finite_codimension_complement", "full_measure"): dict(
        state="open",
        witness_or_source="No general implication. Failure witness W6: D=[0,1], Z={0}, mu=delta_0 gives mu(Z)=1>0, so D\\Z is not full-measure. Success case: a nondegenerate Gaussian measure on a separable Banach space charges proper closed hyperplanes with 0 under injective covariance (needs a source, currently UNRESOLVED).",
        extra_hypothesis="mu(Z)=0 for the declared measure class. Without naming mu and verifying this, the transfer is undefined, which is the honest state for AF data spaces where no canonical mu exists.",
        falsifier="Exhibit any declared measure class mu with mu(Z)>0 (delta measures, or measures supported on a symmetry stratum) to show the transfer fails for that class; exhibit a Gaussian class with mu(Z)=0 to show it holds there. The row is open because both occur and no canonical mu is fixed."),
    ("finite_codimension_complement", "open_dense_escape"): dict(
        state="holds",
        witness_or_source="Definitional: Z closed with empty interior (codim>=1) implies D\\Z is open and dense. The complement is the open-dense-escape set itself.",
        extra_hypothesis="Z closed, proper, and with empty interior. If codim Z = 0 (Z has nonempty interior) the complement is not dense.",
        falsifier="Exhibit Z with nonempty interior (codim 0): e.g. Z = a closed ball, whose complement is open but not dense. That is excluded by the notion's codim>=1 clause, so the clause is load-bearing."),
}

# Sanity: every ordered pair present exactly once.
missing = [pair for pair in ((a, b) for a in NOTION_IDS for b in NOTION_IDS if a != b) if pair not in P]
assert not missing, f"missing ordered pairs: {missing}"

TRANSFER = []
for (a, b), v in P.items():
    TRANSFER.append({
        "from": a, "to": b, "state": v["state"],
        "witness_or_source": v["witness_or_source"],
        "extra_hypothesis": v["extra_hypothesis"],
        "falsifier": v["falsifier"],
    })

WITNESSES = {
    "W1_comeager_null": {
        "statement": "In D=[0,1] with the Euclidean topology and Lebesgue measure lambda, there is a comeager G with lambda(G)=0.",
        "construction": "Enumerate Q cap [0,1] = {q_k}. For n in N let U_n = union_k (q_k - 2^{-(n+k+2)}, q_k + 2^{-(n+k+2)}). Each U_n is open and dense; lambda(U_n) <= sum_k 2^{-(n+k+1)} = 2^{-n}. Let G = intersection_n U_n. G is a dense G_delta (comeager) and lambda(G) <= lambda(U_n) <= 2^{-n} for every n, so lambda(G)=0.",
        "used_by": ["residual_comeager->full_measure"]
    },
    "W2_meager_full_measure": {
        "statement": "D=[0,1] has a meager set of full Lebesgue measure.",
        "construction": "Take D\\G for G as in W1. D\\G is meager (complement of comeager) and lambda(D\\G)=1.",
        "used_by": ["full_measure->residual_comeager"]
    },
    "W3_comeager_empty_interior": {
        "statement": "D=[0,1] has a comeager (indeed full-measure) set with empty interior, hence containing no nonempty open subset.",
        "construction": "The irrationals in [0,1]. Their complement Q cap [0,1] is countable, hence meager; every nonempty open interval contains a rational, so the irrationals have empty interior. Lebesgue measure 1.",
        "used_by": ["residual_comeager->open_dense_escape", "residual_comeager->finite_codimension_complement", "full_measure->open_dense_escape"]
    },
    "W4_open_dense_not_full_measure": {
        "statement": "D=[0,1] has an open dense set U with lambda(U)<1.",
        "construction": "Let C be the Smith-Volterra-Cantor set (fat Cantor set): closed, nowhere dense, lambda(C)>0. Put U=[0,1]\\C. U is open (complement of closed) and dense (C has empty interior), with lambda(U)=1-lambda(C)<1.",
        "used_by": ["open_dense_escape->full_measure", "open_dense_escape->finite_codimension_complement"]
    },
    "W5_full_measure_not_finite_codim": {
        "statement": "D=[0,1] has a full-measure set whose complement is not a finite union of closed finite-codimension submanifolds.",
        "construction": "Let C be the middle-thirds Cantor set (lambda(C)=0), G=[0,1]\\C. Any closed submanifold of the 1-manifold [0,1] of codimension >=1 is a closed discrete subset of a compact space, hence finite; a finite set cannot contain the uncountable C; so G contains no complement of such a Z.",
        "caution": "The 'finite' step uses compactness of [0,1] and FAILS in R, where the integers are an infinite closed discrete 0-dimensional embedded submanifold (independent review, 2026-09-11). The witness is safe only because it lives in [0,1].",
        "used_by": ["full_measure->finite_codimension_complement"]
    },
    "W6_measure_charging_Z": {
        "statement": "Finite-codimension-complement does not transfer to full-measure without a hypothesis on the measure.",
        "construction": "D=[0,1], Z={0} (a codimension-1 closed submanifold), mu=delta_0. Then mu(Z)=1, so D\\Z has mu-measure 0 and is not full-measure.",
        "used_by": ["finite_codimension_complement->full_measure"]
    },
}

AMB_BASE = ("D = {(h,K) in H^s_delta(Sigma) x H^{s-1}_{delta+1}(Sigma) : vacuum constraint equations hold}, "
            "Sigma a fixed connected complete one-ended asymptotically flat 3-manifold, s and delta the schema's declared indices. "
            "Slice/quotient structure must be declared so that D is a Banach manifold; s>3/2 and delta>1/2 are the usual conventions but are "
            "NOT asserted here as a theorem (threshold_status=convention_pending_lead_binding).")
TOPO_BASE = ("Subspace topology induced by the weighted Sobolev norm. Baire non-vacuity on D requires the local manifold structure "
             "(constraint map Fredholm/slice); if D is treated only as a closed subset of the product, comeagerness must be stated relative to D explicitly.")

def class_section(class_id: str, family: str, kind: str, i_plus_note: str) -> dict:
    if family == "WCC":
        concl = "a visible incomplete causal geodesic (tier_1 per R14) with a robustness/genericity requirement"
    else:
        tok = "C2" if "C2" in class_id else "C0"
        concl = f"an extension of the maximal development across a Cauchy horizon in regularity {tok} (tier_1 extension witness per R14, R16)"
    paste = {"AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
             "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
             "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml"}[class_id]
    return {
        "kind": kind,
        "paste_target": paste,
        "r07_keys_present": ["kind", "ambient_space", "topology_or_measure", "generic_set",
                             "excluded_set", "transfer_failures", "is_part_of_class",
                             "changing_notion_statement"],
        "recommendation_status": "recommendation_only__schema_owner_binds__no_theorem_claim",
        "ambient_space": AMB_BASE,
        "topology_or_measure": TOPO_BASE,
        "generic_set": ("G = { d in D : P(d) }, where G contains the countable intersection of a declared sequence of open dense sets U_n "
                        "(set-builder form: G = { d in D : forall n, d in U_n }); P is the class conclusion predicate."
                        if kind == "residual_comeager" else
                        "G = { d in D : d avoids Q } defined by the declared notion " + kind + " (see genericity_notions)."),
        "excluded_set": ("M = union_n (D \\ U_n), a meager set; intended content: data with a Killing field, data on the critical/self-similar set, "
                         "and data whose development has a visible incomplete causal geodesic."),
        "transfer_failures": [
            "residual_comeager -> full_measure: fails (W1/W2)",
            "full_measure -> residual_comeager: fails (W2/W3)",
            "residual_comeager -> open_dense_escape: fails (W3)",
            "open_dense_escape -> full_measure: fails (W4)",
            "full_measure -> finite_codimension_complement: fails (W5)",
            "finite_codimension_complement -> full_measure: open (W6; needs a declared measure class)"
        ],
        "is_part_of_class": True,
        "changing_notion_statement": ("Changing the notion yields a different class: the four generic sets need not coincide (W1-W6), so a "
                                      "statement quantified 'for comeager data' is not the statement quantified 'for mu-a.e. data'. The "
                                      "class_id must therefore be read together with genericity.kind."),
        "regularity_separation_note": ("Genericity notion and extension-regularity token are independent slots: the genericity notion concerns the "
                                       "data space/topology, the regularity token concerns the conclusion. For the SCC pair, keep the genericity notion "
                                       "identical across the C2 and C0 schemas so R16's implication ledger (C2 extension subset C0 extension; "
                                       "C0-inextendibility entails C2-inextendibility) is not confounded by a notion change."),
        "i_plus_note": i_plus_note,
        "falsifier": f"tier_1: exhibit a generic set (under the declared notion) of {class_id} data whose development contains {concl}.",
        "citation_status": "structural_proposal__citations_unresolved_except_C1_C7",
    }

MATRIX = {
    "artifact_kind": "genericity_notion_matrix",
    "task_id": "FORM-GEN-05",
    "assignment_ref": "assign-FORM-GEN-05-20260911T2331",
    "node_id": "F1",
    "gate": "G-CLASSBIND",
    "owner_for_binding": "astra-lead-formulation",
    "claim_status": "unverified_proposal__no_theorem__no_physics_result",
    "no_theorem_claim": True,
    "class_scope": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "transfer_semantics": ("'X -> Y holds' means: for every property P, if P holds on all data of some X-generic set then P holds on all data of "
                           "some Y-generic set. Equivalently (one-line set argument; not a mathematical theorem claim about physics): every "
                           "X-generic set contains a Y-generic set. Rows marked 'open' have no general answer and the missing datum is named."),
    "genericity_notions": NOTIONS,
    "transfer_matrix": TRANSFER,
    "strength_partial_order": {
        "reading": ("Under the coverage reading ('P holds on a generic set'), S_X entails S_Y iff X -> Y holds. "
                    "This is the reading used by the canonical schemas' conclusion statements."),
        "strict_implications": [
            ["finite_codimension_complement", "open_dense_escape"],
            ["finite_codimension_complement", "residual_comeager"],
            ["open_dense_escape", "residual_comeager"]
        ],
        "incomparable_or_conditional": [
            ["residual_comeager", "full_measure"], ["full_measure", "residual_comeager"],
            ["open_dense_escape", "full_measure"], ["full_measure", "open_dense_escape"],
            ["residual_comeager", "finite_codimension_complement"],
            ["full_measure", "finite_codimension_complement"],
            ["finite_codimension_complement", "full_measure"]
        ],
        "strict_converse_failures": [
            ["open_dense_escape", "finite_codimension_complement"],
            ["residual_comeager", "finite_codimension_complement"],
            ["residual_comeager", "open_dense_escape"]
        ],
        "note": ("'strict' means the listed implication holds and its converse fails (see transfer_matrix); the three "
                 "converses are listed explicitly under strict_converse_failures. Consequence: open_dense_escape is "
                 "STRONGER than residual_comeager, not weaker; the reverse phrasing in the earlier drafts was an "
                 "inversion under the coverage reading (adjudication ADJ-2, accepted by the schema owner).")
    },
    "per_class_genericity_section": {
        "AF-WCC-VAC-GEN": class_section(
            "AF-WCC-VAC-GEN", "WCC", "residual_comeager",
            "I+ completeness is the WCC conclusion (R09); the genericity notion governs which data the conclusion is asserted for."),
        "AF-SCC-C2-VAC-GEN": class_section(
            "AF-SCC-C2-VAC-GEN", "SCC", "residual_comeager",
            "I+ is not in the SCC conclusion (R09); a visible-singularity falsifier belongs to WCC (R10)."),
        "AF-SCC-C0-VAC-GEN": class_section(
            "AF-SCC-C0-VAC-GEN", "SCC", "residual_comeager",
            "I+ is not in the SCC conclusion (R09); the C0 token is the extension regularity, not the genericity notion."),
    },
    "witnesses": WITNESSES,
    "citations": CITATIONS,
    "unresolved": [
        {"item": "Christodoulou 1999 codimension-one genericity statement", "why": "not present in the fetched abstract (C2); body text not fetched", "status": "unresolved", "next_step": "fetch a quotable body-text sentence or a review that quotes it; do not bind into a schema before then"},
        {"item": "Baire/Banach-manifold structure of the vacuum constraint set for the declared (s,delta)", "why": "the schema must pick a slice/gauge; no primary source fetched in this run", "status": "unresolved", "next_step": "literature lead to fetch a constraint-manifold slice theorem source"},
        {"item": "Canonical measure class on AF vacuum data", "why": "no canonical Gaussian/Borel measure exists on the nonlinear constraint set without extra structure", "status": "unresolved", "next_step": "if full_measure is ever used, the measure must be constructed and named; otherwise keep full_measure out of the class"},
        {"item": "Gaussian measure charging proper closed hyperplanes with zero", "why": "needed to settle finite_codimension_complement -> full_measure; not fetched", "status": "unresolved", "next_step": "fetch a Gaussian-measure source or restrict the claim to the declared measure class"},
        {"item": "Ringstrom T^3-Gowdy SCC anchor", "why": "not returned by arXiv search and not in scope (cosmological, not asymptotically flat)", "status": "unresolved", "next_step": "record as boundary_case only; do not import into AF classes"},
        {"item": "Dafermos-Luk use of 'generically'", "why": "source uses the word with no ambient space/topology/measure (C4)", "status": "unresolved", "next_step": "quote a body-text definition of the genericity used, or tag as genericity_undefined_in_source"},
    ],
    "proposed_vocabulary_extension": {
        "status": "proposal_only__owner_must_approve__not_in_vocabulary_and_not_in_the_12_row_matrix",
        "why": ("schemas/af_scc_c2_vacuum.yaml declares its generic set open in a weighted C1 topology and dense in a "
                "weighted C-infinity topology; no single genericity_kind token expresses a hybrid openness/density pair, "
                "so either the schema declares both topologies inside topology_or_measure under one existing token, or the "
                "vocabulary gains this composite notion."),
        "notion_id": "open_in_A_dense_in_B",
        "definition": "G is generic iff G is open in a declared topology A on D and dense in a declared topology B on D; A and B are named separately.",
        "quantifier_form": "exists G subseteq D: (G open in A) and (G dense in B) and forall d in G, P(d).",
        "generic_set_template": "G = D \\ Z with Z closed in A and nowhere dense in B.",
        "relation_to_existing": [
            {"pair": ["open_in_A_dense_in_B", "open_dense_escape"],
             "state": "holds_with_hypothesis",
             "extra_hypothesis": "A finer than B (every A-open set is B-open) and B is the topology used by open_dense_escape; then G is B-open and B-dense.",
             "falsifier": ("3-point witness: X={a,b,c}, B={empty,{a},X}, A={empty,{a,b},X}. The set {a,b} is A-open and "
                           "B-dense (its B-closure is X) but not B-open, so without 'A finer than B' the transfer fails.")},
            {"pair": ["open_in_A_dense_in_B", "residual_comeager"],
             "state": "holds_with_hypothesis",
             "extra_hypothesis": "A finer than B and B Baire; then compose with open_dense_escape -> residual_comeager.",
             "falsifier": ("A = discrete topology, B = Euclidean topology on [0,1], G = Q cap [0,1]: G is A-open and "
                           "B-dense but B-meager, hence not comeager in B. The 3-point witness used for the "
                           "open_dense target does not work here: there {a,b} is comeager in B even though it is not "
                           "B-open (corrected after independent review 2026-09-11).")}
        ],
        "decision_needed_from_owner": ("(i) bind the C2 block to open_dense_escape but declare both topologies in "
                                       "topology_or_measure and state explicitly that openness and density use different "
                                       "topologies, or (ii) add open_in_A_dense_in_B to genericity_kind. Option (i) keeps the "
                                       "four-term vocabulary and is cheaper; option (ii) is more honest if hybrid statements recur.")
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(MATRIX, indent=2, sort_keys=False) + "\n")
print(f"wrote {OUT}")
print(f"notions={len(NOTIONS)} transfers={len(TRANSFER)} sha256={hashlib.sha256(OUT.read_bytes()).hexdigest()}")
