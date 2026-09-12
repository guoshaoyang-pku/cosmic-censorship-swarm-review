#!/usr/bin/env python3
"""Build artifacts/flash-15/l1_breadth/anchors.jsonl -- proposal-support packet for L1.

NOT an L1 node completion. It is the per-class role mapping of primary sources fetched during
this session, emitted as supporting evidence for FORM-GEN-05's N4 citation-honesty checks.
Every row is bound to exactly one frozen class. Scope claims are verbatim from the fetched
page or explicitly marked unresolved.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "anchors.jsonl"
FETCHED = "2026-09-11T23:20:00+08:00"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def row(i, cid, role, concl, reg, gen, cit, ids, fetched, quote, match, assumptions, falsifier, status, notes):
    return {
        "row_id": f"L1B-{i:04d}", "node_id": "L1", "class_id": cid, "result_role": role,
        "conclusion_type": concl, "regularity": reg, "genericity": gen,
        "citation": cit, "identifiers": ids, "fetched": fetched,
        "scope_quote": quote, "scope_match": match, "assumptions": assumptions,
        "falsifier": falsifier, "verification_status": status, "notes": notes,
    }


ROWS = [
    row(1, "AF-WCC-VAC-GEN", "boundary_case", "open_problem", "C^inf", "self_similarity__not_generic",
        "Rodnianski, Shlapentokh-Rothman, Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution, arXiv:1912.08478v2 (2022)",
        {"arxiv": "1912.08478", "url": "https://arxiv.org/abs/1912.08478"},
        {"url": "https://arxiv.org/abs/1912.08478", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution"},
        "In this work we initiate the mathematical study of naked singularities for the Einstein vacuum equations in 3+1 dimensions by constructing solutions which correspond to the exterior region of a naked singularity. A key element is our introduction of a new type of self-similarity for the Einstein vacuum equations.",
        "narrower",
        ["3+1 vacuum Einstein equations", "self-similar ansatz"],
        "Fetch a sentence stating whether the data are asymptotically flat and whether they arise from an open set. If an open AF set is produced, AF-WCC-VAC-GEN's generic reading is refuted; the abstract alone does not do this.",
        "verified_primary",
        "Existence of a vacuum naked-singularity exterior; NOT a generic counterexample. Self-similarity is a non-genericity signal. AF property unverified from abstract."),
    row(2, "AF-WCC-VAC-GEN", "supporting", "conditional_theorem", "C^inf", "none_stated__codim3_constraint",
        "Dafermos, Holzegel, Rodnianski, Taylor, The non-linear stability of the Schwarzschild family of black holes, arXiv:2104.08222 (2021)",
        {"arxiv": "2104.08222", "url": "https://arxiv.org/abs/2104.08222"},
        {"url": "https://arxiv.org/abs/2104.08222", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "The non-linear stability of the Schwarzschild family of black holes"},
        "general vacuum initial data, with no symmetry assumed, sufficiently close to Schwarzschild data evolve to a vacuum spacetime which (i) possesses a complete future null infinity I+ ... provided that the data are themselves constrained to lie on a teleologically constructed codimension-3 \"submanifold\" of moduli space.",
        "narrower",
        ["data close to Schwarzschild", "constrained to a codimension-3 submanifold of moduli space", "no symmetry assumed"],
        "Exhibit a datum in the perturbative class whose I+ is incomplete; or show the codimension-3 constraint is meager so the result is not generic.",
        "verified_primary",
        "Strongest WCC support in the packet, but perturbative. 'codimension-3' here is an admissibility constraint, not an excluded set."),
    row(3, "AF-WCC-SCALAR-SPH", "supporting", "open_problem", "C^inf", "not_stated_in_abstract",
        "D. Christodoulou, The instability of naked singularities in the gravitational collapse of a scalar field, Ann. of Math. (2) 149 (1999) 183-217",
        {"arxiv": "math/9901147", "doi": "10.2307/121023", "url": "https://arxiv.org/abs/math/9901147"},
        {"url": "https://arxiv.org/abs/math/9901147", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "The instability of naked singularities in the gravitational collapse of a scalar field"},
        "The present paper, which is a continuation previous work, addresses this question in the context of the spherical gravitational collapse of a scalar field.",
        "narrower",
        ["spherical symmetry", "self-gravitating massless scalar field"],
        "Fetch the body-text main theorem. If it does not carry a genericity quantifier, the class's GEN token is unsupported for this anchor.",
        "verified_primary",
        "Bibliographic identity and topic fully verified. The commonly cited 'codimension one' genericity claim is ABSENT from the abstract: unresolved."),
    row(4, "AF-WCC-SCALAR-SPH", "boundary_case", "counterexample", "C^inf", "unresolved",
        "D. Christodoulou, Examples of Naked Singularity Formation in the Gravitational Collapse of a Scalar Field, Ann. of Math. 140 (1994) 607",
        {"doi": "10.2307/2118619", "url": "https://doi.org/10.2307/2118619"},
        {"url": "https://api.crossref.org/works?query.bibliographic=Examples+of+naked+singularity+formation", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "Examples of Naked Singularity Formation in the Gravitational Collapse of a Scalar Field"},
        "(Crossref record) title/author/venue/year/volume/page verified; no abstract text retrieved.",
        "narrower",
        ["spherical symmetry", "scalar field", "constructed family, genericity unknown"],
        "Fetch the paper body: if the examples are an open set of data, the scalar class GEN token is refuted; if a measure-zero family, it is a boundary_case only.",
        "partial",
        "Crossref-only. Existence of examples is bibliographically verified; the mathematical content is NOT."),
    row(5, "AF-WCC-SCALAR-SPH", "boundary_case", "numerical_evidence", "n/a", "critical_point_only__numerical",
        "M. W. Choptuik, Universality and scaling in gravitational collapse of a massless scalar field, Phys. Rev. Lett. 70 (1993) 9-12",
        {"doi": "10.1103/PhysRevLett.70.9", "url": "https://doi.org/10.1103/PhysRevLett.70.9"},
        {"url": "https://api.crossref.org/works/10.1103/PhysRevLett.70.9", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "Universality and scaling in gravitational collapse of a massless scalar field"},
        "(Crossref record) title/author/venue/year/volume/pages verified; abstract not retrieved.",
        "narrower",
        ["numerical, not rigorous", "massless scalar field"],
        "If critical collapse produced naked singularities on an open set rather than at a critical point, genericity claims would need re-examination; this is a numerical boundary case only.",
        "partial",
        "Numerical evidence class; must never be used as a rigorous anchor. Genericity field unresolved."),
    row(6, "AF-SCC-C0-VAC-GEN", "supporting", "conditional_theorem", "C0", "fixed_background__not_generic",
        "J. Sbierski, The C0-inextendibility of the Schwarzschild spacetime and the spacelike diameter in Lorentzian Geometry, arXiv:1507.00601 (2015/2016)",
        {"arxiv": "1507.00601", "url": "https://arxiv.org/abs/1507.00601"},
        {"url": "https://arxiv.org/abs/1507.00601", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "The C^0-inextendibility of the Schwarzschild spacetime and the spacelike diameter in Lorentzian Geometry"},
        "The maximal analytic Schwarzschild spacetime is manifestly inextendible as a Lorentzian manifold with a twice continuously differentiable metric. In this paper, we prove the stronger statement that it is even inextendible as a Lorentzian manifold with a continuous metric.",
        "narrower",
        ["maximal analytic Schwarzschild, not a generic AF data set"],
        "Exhibit a continuous extension of the maximal analytic Schwarzschild development; or produce a generic-AF version of the argument.",
        "verified_primary",
        "Supports the C0 reading for one exact solution. Does NOT establish C0-inextendibility for generic AF vacuum data."),
    row(7, "AF-SCC-C0-VAC-GEN", "supporting", "conditional_theorem", "C0", "fixed_background__not_generic",
        "J. Sbierski, On the proof of the C0-inextendibility of the Schwarzschild spacetime, arXiv:1711.11380 (2018)",
        {"arxiv": "1711.11380", "url": "https://arxiv.org/abs/1711.11380"},
        {"url": "https://arxiv.org/abs/1711.11380", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "On the proof of the C^0-inextendibility of the Schwarzschild spacetime"},
        "This article presents a streamlined version of the author's original proof of the C0-inextendibility of the maximal analytic Schwarzschild spacetime.",
        "narrower",
        ["maximal analytic Schwarzschild"],
        "Same falsifier as row 6; this row adds no genericity content.",
        "verified_primary",
        "Proof-organization paper; same fixed-background scope."),
    row(8, "AF-SCC-C0-VAC-GEN", "falsifier", "conditional_theorem", "C0", "genericity_undefined_in_source",
        "Dafermos, Luk, The interior of dynamical vacuum black holes I: The C0-stability of the Kerr Cauchy horizon, arXiv:1710.01722; Ann. of Math. 202(2) (2025) 309-630",
        {"arxiv": "1710.01722", "doi": "10.4007/annals.2025.202.2.1", "url": "https://arxiv.org/abs/1710.01722"},
        {"url": "https://arxiv.org/abs/1710.01722", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "The interior of dynamical vacuum black holes I: The C^0-stability of the Kerr Cauchy horizon"},
        "if the exterior region of the Kerr family is proven to be dynamically stable---as is widely expected---then it will follow that the C^0-inextendibility formulation of Penrose's celebrated strong cosmic censorship conjecture is in fact false. The proof suggests, however, that the C^0-metric Cauchy horizons thus arising are generically singular in an essential way, representing so-called \"weak null singularities\".",
        "narrower",
        ["interior Cauchy data", "conditional on Kerr exterior stability", "'generically' used with no ambient space/topology/measure"],
        "Show Kerr exterior stability fails; or show the interior-data assumption cannot be retrieved from an open set of AF data.",
        "verified_primary",
        "SCOPE-CRITICAL: the literal class AF-SCC-C0-VAC-GEN is expected FALSE (modulo Kerr stability), not open. The word 'generically' in the source carries no defined notion."),
    row(9, "AF-SCC-C0-VAC-GEN", "falsifier", "open_problem", "C0", "unresolved",
        "M. Dafermos, Stability and instability of the Cauchy horizon for the spherically symmetric Einstein-Maxwell-scalar field equations, Ann. of Math. 158 (2003) 875-928",
        {"doi": "10.4007/annals.2003.158.875", "url": "https://doi.org/10.4007/annals.2003.158.875"},
        {"url": "https://api.crossref.org/works?query.bibliographic=Stability+and+instability+of+the+Cauchy+horizon", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "Stability and instability of the Cauchy horizon for the spherically symmetric Einstein-Maxwell-scalar field equations"},
        "(Crossref record) title/author/venue/year/volume/page verified; abstract not retrieved.",
        "mismatch",
        ["spherical symmetry", "Einstein-Maxwell-scalar, not vacuum"],
        "Fetch the body text to determine whether the extendibility is C0 or stronger and for which data set; without it this row cannot falsify the vacuum class.",
        "partial",
        "Bibliographic verification only. Charged matter class: anti-scope for VAC classes until body text is read."),
    row(10, "AF-SCC-C2-VAC-GEN", "falsifier", "conditional_theorem", "C2", "decay_rate_dependent__not_generic",
        "Costa, Girao, Natario, Silva, On the global uniqueness for the Einstein-Maxwell-scalar field system with a cosmological constant. Part 3, Ann. PDE 3:8 (2017); arXiv:1406.7261",
        {"arxiv": "1406.7261", "doi": "10.1007/s40818-017-0028-6", "url": "https://arxiv.org/abs/1406.7261"},
        {"url": "https://arxiv.org/abs/1406.7261", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "On the global uniqueness for the Einstein-Maxwell-scalar field system with a cosmological constant. Part 3"},
        "Our results provide evidence against the validity of the strong cosmic censorship conjecture when Lambda>0.",
        "mismatch",
        ["Lambda > 0", "spherical symmetry", "Einstein-Maxwell-scalar", "characteristic data on a subextremal Reissner-Nordstrom horizon"],
        "Import only as a warning: it does not touch AF vacuum classes. To falsify AF-SCC-C2-VAC-GEN one needs a C^2 extension of a generic AF vacuum development.",
        "verified_primary",
        "ANTI-SCOPE anchor. Any schema row citing this for a VAC class is a class-leakage hard failure."),
    row(11, "AF-SCC-C2-VAC-GEN", "open", "open_problem", "C2", "unresolved",
        "D. Christodoulou, The Formation of Black Holes in General Relativity, EMS Monographs in Mathematics (2009)",
        {"doi": "10.4171/068", "isbn": "9783037190685", "url": "https://doi.org/10.4171/068"},
        {"url": "https://api.crossref.org/works/10.4171/068", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "The Formation of Black Holes in General Relativity (EMS Monographs in Mathematics)"},
        "(Crossref record) title/author/publisher/year/ISBN/DOI verified; no abstract or theorem text retrieved.",
        "narrower",
        ["monograph, scope not verified in this run"],
        "Fetch the introduction and check whether it states the C2 formulation of SCC; if not, the C2 formulation anchor remains unresolved.",
        "partial",
        "Bibliographic verification only. Do NOT cite as a C2-SCC theorem for AF vacuum without reading it."),
    row(12, "AF-WCC-VAC-GEN", "open", "open_problem", "C^inf", "generic_used_without_definition",
        "J. Isenberg, On Strong Cosmic Censorship, Surveys in Differential Geometry 20 (2015); arXiv:1505.06390",
        {"arxiv": "1505.06390", "url": "https://arxiv.org/abs/1505.06390"},
        {"url": "https://arxiv.org/abs/1505.06390", "retrieved_at": FETCHED, "http_status": 200,
         "page_title_line": "On Strong Cosmic Censorship"},
        "We focus in particular on model versions of SCC which have been proven for restricted families of spacetimes (e.g., the Gowdy spacetimes), and the role played by the generic presence of Asymptotically Velocity Term Dominated behavior in these solutions.",
        "mismatch",
        ["secondary survey", "Gowdy/cosmological models are not asymptotically flat"],
        "If the survey's notion of generic differs from the four in the matrix, the vocabulary is incomplete; check its definitions section.",
        "verified_primary",
        "SECONDARY source, used only to locate primaries and to show 'generic' is used loosely across the field. Not a primary anchor."),
]


def main() -> int:
    with OUT.open("w") as f:
        for r in ROWS:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print(f"wrote {OUT} rows={len(ROWS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
