#!/usr/bin/env python3
"""Builder for the L1 assignment artifact `ledger/counterexamples.jsonl`.

Assignment: asg-2026-09-11-L1-deepseek-flash-11-20 (Astra, node L1, class GLOBAL,
gate G-LIT). Task: "Collect hypothesis-violating examples (negative mass, non-AF,
non-generic data, etc.)"; acceptance: ">=6 known solutions/spacetimes that show
genericity or hypothesis necessity; each with source, which hypothesis it
violates, which class it bounds."

Discipline applied here (project rules: no claim from fluent text alone):
  * every bibliography entry was resolved through INSPIRE-HEP API, Crossref API,
    the arXiv abstract page, or OSTI, and the API URL is recorded for re-fetch;
  * `source_verification.abstract_retrieved` records whether a verbatim abstract
    was obtained; where not, `claim_scope` says so explicitly;
  * `class_status_at_creation` records that F1/F2 schemas were still unfrozen when
    this ledger was written, so every class binding is provisional;
  * no entry is marked reviewed; `review_status = unreviewed` throughout.

Run:  python3 build_counterexamples.py   (writes ../../../ledger/counterexamples.jsonl)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "ledger" / "counterexamples.jsonl"
META = REPO / "ledger" / "counterexamples.meta.json"

F1_STATUS = "unfrozen at creation (F1/F2 drafts exist; no canonical schema hash recorded)"
RETRIEVED = "2026-09-11T23:25:00+08:00"


def S(authors, title, venue, year, pages, doi=None, arxiv=None, url=None, api_url=None):
    return {
        "authors": authors,
        "title": title,
        "venue": venue,
        "year": year,
        "pages": pages,
        "doi": doi,
        "arxiv": arxiv,
        "url": url or (f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else None)),
        "resolver_api": api_url,
    }


def V(method, abstract_retrieved, quote=None, note=None, claim_scope=None):
    return {
        "method": method,
        "retrieved_at": RETRIEVED,
        "abstract_retrieved": abstract_retrieved,
        "abstract_quote": quote,
        "note": note,
        "claim_scope": claim_scope,
    }


ENTRIES = [
    {
        "entry_id": "ce-01",
        "name": "Negative-mass Schwarzschild spacetime",
        "record_kind": "exact_solution",
        "bounds_class": "AF-WCC-VAC-GEN",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "positive ADM mass (and the dominant-energy/positive-mass input that yields it); the exact solution is also spherically symmetric, i.e. non-generic",
        "hypothesis_required_by_class": "The WCC formulation class for AF vacuum data is stated for data satisfying the dominant energy condition / non-negative ADM mass; a negative-mass member is the standard probe of that hypothesis.",
        "binding_check": "Hypothesis is inside the class statement, not an external decoration: if the frozen F1 schema instead imposes only regularity+AF and no mass sign, this entry must be re-bound (and re-scored) rather than silently kept.",
        "conclusion_failure": "For M<0 the Schwarzschild metric has no event horizon and a timelike curvature singularity at r=0 that is visible; the configuration is also perturbatively unstable (Gleiser-Dotti).",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Gleiser, Reinaldo J.", "Dotti, Gustavo"],
            "Instability of the negative mass Schwarzschild naked singularity",
            "Classical and Quantum Gravity",
            2006,
            "5063-5078",
            doi="10.1088/0264-9381/23/15/021",
            arxiv="gr-qc/0604021",
            api_url="https://arxiv.org/abs/gr-qc/0604021",
        ),
        "source_verification": V(
            "arxiv_abstract_page",
            True,
            "We study the negative mass Schwarzschild spacetime, which has a naked singularity, and show that it is perturbatively unstable.",
            "Journal reference on the arXiv page: Class.Quant.Grav. 23 (2006) 5063-5078.",
            "abstract-supported for nakedness and instability; the exact metric is classical (Schwarzschild 1916) and not re-derived here",
        ),
        "uncertainties": [
            "static exact solution, not a development of regular asymptotically flat initial data in the WCC dynamical sense",
            "violates genericity at the same time as the mass sign, so it is not a single-hypothesis isolation experiment",
            "binding presupposes that the frozen F1 schema retains a mass-sign/energy-condition hypothesis",
        ],
        "falsifier": "Frozen F1 schema contains no positive-mass/energy-condition hypothesis: then this entry violates a hypothesis the class does not impose and must be dropped (the assignment's stated falsifier).",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-02",
        "name": "Super-extremal Reissner-Nordstrom spacetime (|Q| > M)",
        "record_kind": "exact_solution",
        "bounds_class": "GLOBAL (electrovacuum extension of AF-WCC-VAC-GEN; not one of the four frozen classes)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "vacuum matter content (Q=0) and sub-extremality |Q| <= M",
        "hypothesis_required_by_class": "The frozen classes are stated for vacuum matter; the natural charged extension inherits a sub-extremality hypothesis. Removing Q=0 and |Q|<=M is exactly what exposes the naked singularity.",
        "binding_check": "This entry does NOT bind AF-WCC-VAC-GEN directly: a charged solution is outside the vacuum class. It is recorded to bound the electrovacuum extension and is flagged as out-of-frozen-scope.",
        "conclusion_failure": "For |Q| > M the Reissner-Nordstrom metric has no event horizon; the r=0 timelike singularity is visible from infinity.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Qadir, A.", "Siddiqui, A. A."],
            "The cosmic censorship hypothesis and the naked Reissner-Nordstrom singularity",
            "Mathematical Physics (conference volume)",
            2005,
            "conference chapter",
            doi="10.1142/9789812701862_0031",
            api_url="https://api.crossref.org/works?query.bibliographic=naked%20singularity%20overcharged%20Reissner-Nordstrom",
        ),
        "source_verification": V(
            "crossref_search",
            False,
            None,
            "Crossref returned this chapter as the top bibliographic match for 'naked singularity overcharged Reissner-Nordstrom'; metadata (title, authors, year, container) matched the query.",
            "metadata-level only; no abstract retrieved, so the exact theorem scope is title-level and needs reviewer confirmation",
        ),
        "uncertainties": [
            "not a vacuum solution, so it cannot bound AF-WCC-VAC-GEN directly",
            "the standard statement (timelike naked singularity for |Q|>M) is textbook-level (Hawking-Ellis 1973); the fetched source is a conference chapter, not the original derivation",
            "needs lead/audit review before any class claim uses it",
        ],
        "falsifier": "Lead rules electrovacuum out of scope for L1: the entry is then a scope note, not a class-bounding counterexample.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-03",
        "name": "Choptuik critical collapse of a massless scalar field",
        "record_kind": "numerical_solution",
        "bounds_class": "AF-WCC-SCALAR-SPH (and the SCC genericity hypothesis for scalar classes)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "genericity of the initial data: the naked-singularity-bearing critical solution is a codimension-one (threshold) set, not an open set",
        "hypothesis_required_by_class": "The class conclusion is asserted for generic data in the class; the critical solution sits exactly on the boundary between dispersion and black-hole formation, so it tests whether 'generic' is doing work.",
        "binding_check": "The genericity hypothesis is part of the class statement as drafted; removing it would let the threshold solution be counted as a counterexample to the class conclusion.",
        "conclusion_failure": "At the critical parameter value p*, the strong-field evolution is universal and generates structure on arbitrarily small spatiotemporal scales; the critical solution's singularity is standardly described as naked, while p>p* forms black holes with M_BH ~ |p-p*|^gamma.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Choptuik, Matthew W."],
            "Universality and scaling in gravitational collapse of a massless scalar field",
            "Physical Review Letters",
            1993,
            "9-12",
            doi="10.1103/PhysRevLett.70.9",
            api_url="https://inspirehep.net/api/literature/33714?fields=titles,abstracts",
        ),
        "source_verification": V(
            "inspire_api_abstract",
            True,
            "I present evidence in support of conjectures that (1) the strong-field evolution in the p->p* limit is universal and generates structure on arbitrarily small spatiotemporal scales and (2) the masses of black holes which form satisfy a power law M_BH ~ ||p-p*||^gamma, where gamma ~= 0.37 is a universal exponent.",
            "INSPIRE record 33714; no arXiv eprint on the record.",
            "abstract-supported for universality/scaling; the naked-singularity reading of the critical solution comes from the review literature, not verbatim from the 1993 abstract",
        ),
        "uncertainties": [
            "the 1993 abstract does not use the words 'naked singularity'; the critical solution is standardly so described (see the Gundlach-Martin-Garcia review)",
            "codimension-one quantification of the critical set comes from the review, not from the letter",
        ],
        "secondary_source": S(
            ["Gundlach, Carsten", "Martin-Garcia, Jose M."],
            "Critical phenomena in gravitational collapse",
            "Living Reviews in Relativity",
            2007,
            "5",
            doi="10.12942/lrr-2007-5",
            arxiv="0711.4620",
            api_url="https://inspirehep.net/api/literature?q=t%20Critical%20phenomena%20in%20gravitational%20collapse",
        ),
        "falsifier": "A reviewer shows the critical solution is not naked (or that the threshold set is open): the entry stops bounding the genericity hypothesis.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-04",
        "name": "Christodoulou's constructed scalar-field naked-singularity examples",
        "record_kind": "constructed_solution_family",
        "bounds_class": "AF-WCC-SCALAR-SPH (genericity hypothesis)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "the class conclusion cannot be asserted for all data: explicit non-generic data forming naked singularities exist",
        "hypothesis_required_by_class": "The class conclusion is restricted to generic data; these examples show the restriction is not cosmetic.",
        "binding_check": "The genericity restriction appears in the drafted class statement; this entry shows why it is needed.",
        "conclusion_failure": "Explicit examples of naked singularity formation in the spherically symmetric collapse of a scalar field.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Christodoulou, Demetrios"],
            "Examples of naked singularity formation in the gravitational collapse of a scalar field",
            "Annals of Mathematics",
            1994,
            "607-653",
            doi="10.2307/2118619",
            api_url="https://inspirehep.net/api/literature/391017?fields=titles,abstracts",
        ),
        "source_verification": V(
            "inspire_api",
            False,
            None,
            "INSPIRE record 391017: metadata exact (Ann. Math. 140 (1994) 607-653, DOI 10.2307/2118619); no abstract in the record.",
            "metadata + title-level only; the detailed scope of the examples was NOT read from the paper",
        ),
        "uncertainties": [
            "no abstract retrieved; content claim rests on the title and on the follow-up 1999 paper by the same author",
            "the 'which hypothesis' binding (genericity) is inferred from the 1999 instability result, not from this paper's abstract",
        ],
        "falsifier": "Reviewer finds the 1994 examples are generic (open set): the entry would instead be a counterexample to the class conclusion, changing its role from hypothesis-necessity to class-refutation.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-05",
        "name": "Instability of naked singularities in scalar-field collapse",
        "record_kind": "theorem_about_solutions",
        "bounds_class": "AF-WCC-SCALAR-SPH / SCC scalar classes (genericity hypothesis)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "genericity is necessary: naked-singularity formation is unstable, so it is not a positive-probability phenomenon for generic data",
        "hypothesis_required_by_class": "The class conclusion is stated for generic data; this result is the sharpest known justification that the genericity restriction is required rather than convenient.",
        "binding_check": "Genericity is part of the drafted class statement; the theorem quantifies over data families and separates generic from exceptional behaviour.",
        "conclusion_failure": "Naked singularities form only for exceptional (unstable) data; generic spherical scalar-field data are censored as far as this theorem goes.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Christodoulou, Demetrios"],
            "The instability of naked singularities in the gravitational collapse of a scalar field",
            "Annals of Mathematics",
            1999,
            "183-217",
            doi="10.2307/121023",
            arxiv="math/9901147",
            api_url="https://inspirehep.net/api/literature/2946377?fields=titles,abstracts",
        ),
        "source_verification": V(
            "inspire_api_abstract",
            True,
            "One of the fundamental unanswered questions in the general theory of relativity is whether 'naked' singularities, that is singular events which are visible from infinity, may form with positive probability in the process of gravitational collapse. The conjecture that the answer to this question is in the negative has been called 'cosmic censorship'. The present paper ... addresses this question in the context of the spherical gravitational collapse of a scalar field.",
            "INSPIRE record 2946377; arXiv:math/9901147.",
            "abstract-supported for the problem setting; the instability conclusion itself is title-level in the abstract",
        ),
        "uncertainties": [
            "the abstract poses the question but does not state the instability theorem verbatim",
            "reviewer should confirm the precise genericity quantifier used (measure vs category)",
        ],
        "falsifier": "Reviewer shows the instability statement is conditional on hypotheses not present in the drafted class: the entry would then bound those extra hypotheses instead.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-06",
        "name": "Naked singularity in inhomogeneous dust collapse (LTB)",
        "record_kind": "theorem_about_solutions",
        "bounds_class": "GLOBAL (pressureless-dust analogue; bounds the vacuum/matter hypothesis of AF-WCC-VAC-GEN)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "vacuum matter content (dust has matter) and any blanket 'generic data are censored' claim for dust: the naked set is open in the analysed density distributions",
        "hypothesis_required_by_class": "The frozen vacuum classes require vacuum matter; dust is a different matter model. This entry records that WCC-type censorship is matter-model dependent, so the matter hypothesis cannot be treated as a harmless technicality.",
        "binding_check": "Clearly labelled as out-of-frozen-class: it bounds the dust analogue, not AF-WCC-VAC-GEN itself. No claim of direct vacuum-class refutation is made.",
        "conclusion_failure": "For an open subset of initial density distributions the first singular event is the vertex of infinitely many future null geodesic cones intersecting future null infinity (naked, up to infinite redshift).",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Christodoulou, Demetrios"],
            "Violation of cosmic censorship in the gravitational collapse of a dust cloud",
            "Communications in Mathematical Physics",
            1984,
            "171-195",
            doi="10.1007/BF01223743",
            api_url="https://inspirehep.net/api/literature/211917?fields=titles,abstracts",
        ),
        "source_verification": V(
            "inspire_api_abstract",
            True,
            "It is shown that, for an open subset of initial density distributions, the first singular event, which occurs at the center of symmetry, is the vertex of an infinity of future null geodesic cones which intersect future null infinity. The frequency of the corresponding light rays is infinitely redshifted.",
            "INSPIRE record 211917; DOI confirmed as 10.1007/BF01223743 (an earlier search-result guess of BF01212252 was wrong and is not used).",
            "abstract-supported",
        ),
        "uncertainties": [
            "dust (pressureless matter) is not a frozen class; direct binding to AF-WCC-VAC-GEN is invalid",
            "infinite redshift of the escaping rays may be argued to weaken the physical visibility; reviewer judgement required",
        ],
        "secondary_source": S(
            ["Eardley, Douglas M.", "Smarr, Larry"],
            "Time functions in numerical relativity: Marginally bound dust collapse",
            "Physical Review D",
            1979,
            "2239-2259",
            doi="10.1103/PhysRevD.19.2239",
            api_url="https://api.crossref.org/works/10.1103/PhysRevD.19.2239",
        ),
        "falsifier": "Reviewer shows the open-set statement is about shell-crossing singularities that are not visible to infinity: the entry would lose its nakedness claim.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-07",
        "name": "Higher-dimensional vacuum naked singularity formation (An-Zhang)",
        "record_kind": "constructed_solution_family",
        "bounds_class": "AF-WCC-VAC-GEN (dimension-4 hypothesis)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "spacetime dimension = 4 (their examples are 5+1-dimensional); the data are also only asymptotically locally flat (topology R^{3+1} x S^2), so standard asymptotic flatness is not satisfied",
        "hypothesis_required_by_class": "The frozen class names four-dimensional asymptotically flat vacuum data; this entry tests the dimension hypothesis directly.",
        "binding_check": "The dimension hypothesis is explicit in the class name/statement. The simultaneous ALF (rather than AF) violation is recorded so the entry is not used to isolate dimension alone.",
        "conclusion_failure": "The 5+1-dimensional vacuum Einstein equations admit solutions describing naked singularity formation in gravitational collapse from nonsingular asymptotically locally flat initial data that contain no trapped surface.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["An, Xinliang", "Zhang, Xuefeng"],
            "Examples of naked singularity formation in higher-dimensional Einstein-vacuum spacetimes",
            "Annales Henri Poincare",
            2018,
            "619-651",
            doi="10.1007/s00023-017-0631-9",
            arxiv="1509.07956",
            api_url="https://inspirehep.net/api/literature?q=t%20Examples%20of%20Naked%20Singularity%20Formation%20in%20Higher-Dimensional%20Einstein-Vacuum%20Spacetimes",
        ),
        "source_verification": V(
            "inspire_api_abstract",
            True,
            "The vacuum Einstein equations in 5+1 dimensions are shown to admit solutions describing naked singularity formation in gravitational collapse from nonsingular asymptotically locally flat initial data that contain no trapped surface.",
            "INSPIRE record 1395073; journal ref Ann. Henri Poincare 19 (2018) 619-651; arXiv:1509.07956.",
            "abstract-supported",
        ),
        "uncertainties": [
            "violates two hypotheses at once (dimension and asymptotic flatness); cannot isolate the dimension hypothesis by itself",
            "asymptotically locally flat (Kaluza-Klein R^{3+1} x S^2) is not asymptotically flat in the standard 4D sense",
        ],
        "falsifier": "Reviewer shows the constructed data are not asymptotically flat in any accepted sense and the lead rules ALF out of scope: the entry remains a dimension hint, not a class-bounding counterexample.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-08",
        "name": "Axially symmetric asymptotically flat vacuum metric with a naked singularity (Sarma-Ahmed-Patgiri)",
        "record_kind": "exact_solution",
        "bounds_class": "AF-WCC-VAC-GEN (regularity / maximal-development hypothesis)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "the setting is not a maximal development of regular initial data: it is an exact stationary-type vacuum solution whose singularity sits on the axis, and it also develops closed timelike curves",
        "hypothesis_required_by_class": "The class conclusion is about the maximal development of regular data; an exact solution with a naked singularity that is not produced by such an evolution does not refute the class conclusion, but it does show why the regularity/initial-data hypothesis must be stated explicitly.",
        "binding_check": "Recorded as a regularity-hypothesis probe, NOT as a refutation of the class conclusion. If the drafted class omits a regularity/maximal-development clause, the binding is invalid and must be reported.",
        "conclusion_failure": "An axially symmetric, asymptotically flat, empty-space solution with a true curvature singularity on the symmetry axis (no horizon), plus closed timelike curves evolving from a CTC-free slice.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Sarma, Debojit", "Ahmed, Faizuddin", "Patgiri, Mahadev"],
            "Axially symmetric, asymptotically flat vacuum metric with a naked singularity and closed timelike curves",
            "Advances in High Energy Physics",
            2016,
            "2546186",
            doi="10.1155/2016/2546186",
            arxiv="1611.05989",
            api_url="https://inspirehep.net/api/literature?q=t%20Axially%20Symmetric%20Asymptotically%20Flat%20Vacuum%20Metric%20with%20a%20Naked%20Singularity",
        ),
        "source_verification": V(
            "inspire_api_abstract",
            True,
            "We present an axially symmetric, asymptotically flat empty space solution of the Einstein field equations containing a naked singularity. The spacetime is regular everywhere except on the symmetry axis where it possesses a true curvature singularity. ... the spacetime also shows the evolution of closed timelike curves (CTCs) from an initial hypersurface free from CTCs.",
            "INSPIRE record 1499038; arXiv:1611.05989.",
            "abstract-supported for the solution's properties",
        ),
        "uncertainties": [
            "not established (from the abstract) to be the maximal development of regular initial data; the abstract does not state how the solution is generated",
            "presence of CTCs means the example also violates causality assumptions, confounding the regularity hypothesis",
        ],
        "falsifier": "Reviewer shows the solution is not asymptotically flat at I+ in the class's sense, or is a known member of an already-excluded family: then it cannot probe the regularity hypothesis.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-09",
        "name": "C0-stability of the Kerr Cauchy horizon (Dafermos-Luk)",
        "record_kind": "theorem_about_solutions",
        "bounds_class": "AF-SCC-C0-VAC-GEN (class conclusion appears false under genericity, conditional on Kerr stability)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "none of the class hypotheses is violated; rather the C0-inextendibility CONCLUSION fails for generic dynamical vacuum black-hole interiors",
        "hypothesis_required_by_class": "This is the one entry that attacks a class conclusion rather than a hypothesis. It is the reason the C0 and C2 SCC classes must be kept separate.",
        "binding_check": "Bound to AF-SCC-C0-VAC-GEN because the class conclusion is exactly C0-inextendibility; the abstract states the C0 formulation of SCC would be false if Kerr exterior stability holds. Verdict is conditional, not unconditional.",
        "conclusion_failure": "The maximal Cauchy evolution of data inside a rotating vacuum black hole extends across a non-trivial piece of Cauchy horizon as a Lorentzian manifold with continuous (C0) metric; the resulting weak null singularities motivate a revised SCC.",
        "entry_role": "class_conclusion_counterexample",
        "source": S(
            ["Dafermos, Mihalis", "Luk, Jonathan"],
            "The interior of dynamical vacuum black holes I: The C0-stability of the Kerr Cauchy horizon",
            "Annals of Mathematics",
            2025,
            "309-630",
            doi="10.4007/annals.2025.202.2.1",
            arxiv="1710.01722",
            api_url="https://arxiv.org/abs/1710.01722",
        ),
        "source_verification": V(
            "arxiv_abstract_page",
            True,
            "We prove that for all such data, the maximal Cauchy evolution can be extended across a non-trivial piece of Cauchy horizon as a Lorentzian manifold with continuous metric. ... if the exterior region of the Kerr family is proven to be dynamically stable ... then it will follow that the C0-inextendibility formulation of Penrose's celebrated strong cosmic censorship conjecture is in fact false.",
            "arXiv:1710.01722; journal reference Ann. of Math. (2) 202(2):309-630 (September 2025).",
            "abstract-supported; the falsity statement is explicitly conditional on Kerr exterior stability in the abstract",
        ),
        "uncertainties": [
            "conditional on Kerr dynamical stability (widely expected; not proved in the abstract)",
            "the theorem starts from Cauchy data prescribed already inside the black-hole interior; retrieval of the exterior assumptions is future work announced in the abstract",
            "a C0 extension of a merely continuous metric is not a solution of the vacuum equations in a classical sense; this is exactly the reason C0 and C2 classes differ",
        ],
        "falsifier": "Reviewer shows the class's C0-inextendibility is defined as C0-inextendibility *among vacuum solutions* rather than among continuous Lorentzian manifolds: the Dafermos-Luk extension would then not refute it.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-10",
        "name": "C0-inextendibility of the exact Schwarzschild spacetime (Sbierski) -- contrast case",
        "record_kind": "contrast_theorem",
        "bounds_class": "AF-SCC-C0-VAC-GEN (contrast: shows the C0 conclusion is not uniformly false)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "none; this is the control for ce-09",
        "hypothesis_required_by_class": "The class conclusion holds for the exact (non-rotating) member while failing for generic rotating interiors, so the class's genericity hypothesis is doing work in the opposite direction from ce-03..ce-05.",
        "binding_check": "Recorded as contrast so ce-09 is not over-generalised into 'C0 SCC is false'. Both entries must be reviewed together.",
        "conclusion_failure": "No failure recorded: maximal analytic Schwarzschild is C0-inextendible, i.e. the C0 conclusion holds in this case.",
        "entry_role": "contrast",
        "source": S(
            ["Sbierski, Jan"],
            "The C0-inextendibility of the Schwarzschild spacetime and the spacelike diameter in Lorentzian geometry",
            "Journal of Differential Geometry",
            2018,
            None,  # page range NOT verifiable: Crossref record for this DOI has none; see note
            doi="10.4310/jdg/1518490820",
            arxiv="1507.00601",
            api_url="https://arxiv.org/abs/1507.00601",
        ),
        "source_verification": V(
            "arxiv_abstract_page",
            True,
            "In this paper, we prove the stronger statement that it is even inextendible as a Lorentzian manifold with a continuous metric.",
            "arXiv:1507.00601; Crossref confirms J. Differential Geom. 108(2), 2018-02-01, DOI 10.4310/jdg/1518490820, but the Crossref record carries NO page range. An earlier draft of this ledger said 285-316 from memory; that value was wrong and has been withdrawn. A secondary reference list (Van de Moortel, CMP 382:1263-1341) cites 319-378 for the same DOI, which is recorded here as secondary, not verified.",
            "abstract-supported",
        ),
        "uncertainties": [
            "page range unresolved: the DOI record has none; an earlier memory value (285-316) was withdrawn as unsupported",
            "the explanation of the contrast (degenerate Schwarzschild horizon vs non-degenerate Kerr Cauchy horizon) is standard but is an interpretation not asserted in either abstract",
            "ce-09's counterexample is conditional; this control does not make the C0 class true, only not uniformly false",
        ],
        "falsifier": "Reviewer shows the Schwarzschild result does not apply to the maximal development in the class's sense: the contrast would need re-binding.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-11",
        "name": "Cylindrical dust-shell collapse to a naked singularity (Nakao-Morisawa)",
        "record_kind": "approximate_solution",
        "bounds_class": "GLOBAL (non-asymptotically-flat / cylindrical hypothesis of the class family)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "asymptotic flatness and standard I+ structure (cylindrical symmetry has a different asymptotic structure); the construction also assumes dust and high collapse speed",
        "hypothesis_required_by_class": "The frozen classes require asymptotically flat slices with I+ = R x S^2; this entry probes what happens to the visibility question when that asymptotic hypothesis is removed.",
        "binding_check": "Labelled out-of-frozen-class (GLOBAL): it bounds the asymptotic-flatness hypothesis by exhibiting a different asymptotic setting with a naked singularity; it does NOT refute the AF class.",
        "conclusion_failure": "Approximate solution describing gravitational emission from a naked singularity formed by the collapse of a cylindrical thick dust shell at large collapse speed; the final singularity is argued to be conical.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Nakao, Ken-ichi", "Morisawa, Yoshiyuki"],
            "Gravitational radiation from a cylindrical naked singularity",
            "Physical Review D",
            2005,
            "124007",
            doi="10.1103/PhysRevD.71.124007",
            api_url="https://www.osti.gov/biblio/20709551",
        ),
        "source_verification": V(
            "osti_abstract_page",
            True,
            "We construct an approximate solution which describes the gravitational emission from a naked singularity formed by the gravitational collapse of a cylindrical thick shell composed of dust. ... the final singularity will be a conical one.",
            "OSTI record 20709551; journal metadata PRD 71, 124007 (2005), DOI confirmed.",
            "abstract-supported for the construction; the naked singularity is part of the assumed background (Morgan solution), not proved to form by this paper",
        ),
        "uncertainties": [
            "formation of the naked singularity is an input (background Morgan solution), not an output of this paper",
            "the solution is approximate (linear perturbation analysis) and assumes high collapse speed",
        ],
        "falsifier": "Reviewer identifies a theorem excluding naked singularities in cylindrical dust collapse: the entry loses its hypothesis-necessity role.",
        "review_status": "unreviewed",
    },
    {
        "entry_id": "ce-12",
        "name": "Mass inflation and the weak null Cauchy-horizon singularity (Poisson-Israel)",
        "record_kind": "theorem_about_solutions",
        "bounds_class": "AF-SCC-C2-VAC-GEN vs AF-SCC-C0-VAC-GEN (regularity of the extension)",
        "class_status_at_creation": F1_STATUS,
        "hypothesis_violated": "C2 regularity of the extension: the Cauchy horizon is a weak null singularity, so the maximal development is not extendible with C2 metric although lower-regularity extension is the relevant question",
        "hypothesis_required_by_class": "The C2 and C0 SCC classes differ exactly in the regularity demanded of the extension; this entry is the standard evidence that the two classes are not interchangeable.",
        "binding_check": "Bound to the C2/C0 distinction. The original analysis is for charged black holes (Reissner-Nordstrom), so the binding to the *vacuum* C2 class is by analogy only and is flagged.",
        "conclusion_failure": "On the Cauchy horizon the mass function inflates and curvature diverges (weak null singularity); the extension is not C2-regular.",
        "entry_role": "hypothesis_necessity",
        "source": S(
            ["Poisson, Eric", "Israel, Werner"],
            "Internal structure of black holes",
            "Physical Review D",
            1990,
            "1796-1809",
            doi="10.1103/PhysRevD.41.1796",
            api_url="https://api.crossref.org/works/10.1103/PhysRevD.41.1796",
        ),
        "source_verification": V(
            "crossref_api",
            False,
            None,
            "Crossref metadata exact: PRD 41, 1796-1809 (1990), authors Poisson and Israel, DOI 10.1103/PhysRevD.41.1796.",
            "metadata-level only; no abstract retrieved, the mass-inflation statement is textbook-level and needs reviewer confirmation",
        ),
        "uncertainties": [
            "charged (electrovacuum) analysis, not vacuum; vacuum analogue is the weak null singularity in Dafermos-Luk (ce-09)",
            "no abstract retrieved; content claim is standard but unquoted",
        ],
        "falsifier": "Reviewer shows the C2 class's extension_regularity is not C2-metric regularity: the entry would bound a different hypothesis.",
        "review_status": "unreviewed",
    },
]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, ensure_ascii=False, sort_keys=True) for e in ENTRIES]
    payload = "\n".join(lines) + "\n"
    OUT.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    (OUT.with_suffix(".jsonl.sha256")).write_text(f"{digest}  ledger/counterexamples.jsonl\n", encoding="utf-8")

    meta = {
        "artifact": "ledger/counterexamples.jsonl",
        "assignment_event_id": "asg-2026-09-11-L1-deepseek-flash-11-20",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "worker": "deepseek-flash-11",
        "created_at": "2026-09-11T23:27:00+08:00",
        "entries": len(ENTRIES),
        "sha256": digest,
        "class_status_at_creation": F1_STATUS,
        "verified_metadata": sum(1 for e in ENTRIES if e["source_verification"]["method"]),
        "abstracts_retrieved": sum(1 for e in ENTRIES if e["source_verification"]["abstract_retrieved"]),
        "review_status": "all entries unreviewed; gate G-LIT not claimed passed",
        "known_gaps": [
            "no frozen F1/F2 schema hash existed at creation time, so class bindings are provisional",
            "vacuum-4D genericity hypothesis: no counterexample found (empty cell)",
            "C2-vacuum genericity: no direct example found; only charged analogue (ce-12) and C0 contrast (ce-09/ce-10)",
            "ce-02, ce-04, ce-06, ce-11, ce-12 deliberately bound non-frozen or non-vacuum classes and are labelled GLOBAL",
            "CORRECTION 2026-09-11T23:45: ce-10 page range withdrawn: an initial value 285-316 came from memory and is unsupported; Crossref has no page range for 10.4310/jdg/1518490820 and a secondary reference cites 319-378",
        ],
    }
    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(ENTRIES)} entries, sha256={digest[:16]}...)")
    print(f"wrote {META}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
