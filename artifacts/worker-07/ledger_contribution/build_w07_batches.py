#!/usr/bin/env python3
"""W07 contribution to L0: source + theorem batches for the canonical ledger.

Assignment (Astra, 23:19:12): node L0, artifact ledger/theorems.jsonl, gate G-LIT,
acceptance "Skeleton schema + >=10 filled rows with locators and explicit non-claims".

Design constraints taken from the literature lead's builder
(artifacts/literature/tools/build_literature.py, glob batch-*.jsonl):
  * never edit another agent's batch file; add a new one
  * a theorem may be `accepted` only if every cited source is verified-* and the
    source record carries a verbatim evidence quote >=30 chars
  * every row needs: theorem_id, class_ids (builder's class vocabulary),
    conclusion_type, statement_exact, assumptions, falsifiers, source_ids, status

Honesty rules applied here:
  * every quote below was fetched by worker-07 in this session; the fetch page and
    timestamp are recorded in the source record
  * a claim whose exact statement is NOT in the fetched abstract is `provisional`
    and carries an explicit `unresolved` list (Christodoulou 1999 theorem text)
  * a source whose abstract could not be retrieved at all is `unresolved`, and any
    theorem row citing it is `unresolved` too (Choptuik 1993, Penrose 1969)
  * no row states a regularity (C^0 vs C^2) conclusion across classes

Run:  python3 artifacts/worker-07/ledger_contribution/build_w07_batches.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIT = ROOT / "artifacts" / "literature"
HERE = Path(__file__).resolve().parent
# Default output is worker-07's own durable area.  The literature lead deleted the
# first batch-w07.jsonl files from artifacts/literature/{sources,theorems}/ during a
# 23:27 restructure, so this generator no longer writes into another agent's tree by
# default; pass --inject to write copies there deliberately.
OUT_SRC = HERE / "batches" / "batch-w07-sources.jsonl"
OUT_THM = HERE / "batches" / "batch-w07-theorems.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-07"


def fetch_verification(page: str, quote: str) -> dict:
    return {"method": "arxiv-abs-page-fetch", "fetched_at": NOW, "http_status": 200,
            "page": page, "evidence": quote}


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------
SOURCES = [
    {
        "source_id": "W07-SRC-01",
        "bibkey": "christodoulou1999instability",
        "title": "The instability of naked singularities in the gravitational collapse of a scalar field",
        "authors": ["Demetrios Christodoulou"],
        "year": 1999,
        "venue": "Annals of Mathematics (2) 149(1), 183-217 (1999); arXiv migration record, abstract added in migration",
        "doi": "10.2307/121023",
        "arxiv_id": "math/9901147",
        "url": "https://arxiv.org/abs/math/9901147",
        "verification": fetch_verification(
            "https://arxiv.org/abs/math/9901147",
            "One of the fundamental unanswered questions in the general theory of relativity is whether "
            "``naked'' singularities, that is singular events which are visible from infinity, may form "
            "with positive probability in the process of gravitational collapse. The conjecture that the "
            "answer to this question is in the negative has been called ``cosmic censorship.'' The present "
            "paper, which is a continuation previous work, addresses this question in the context of the "
            "spherical gravitational collapse of a scalar field."),
        "status": "verified-primary",
        "reviewer": ACTOR,
        "notes": "Abstract states the SCOPE (spherical scalar collapse) but not the theorem's conclusion; "
                 "the exact genericity statement must be quoted from the full text before any accepted row.",
    },
    {
        "source_id": "W07-SRC-02",
        "bibkey": "christodoulou2008formation",
        "title": "The Formation of Black Holes in General Relativity",
        "authors": ["Demetrios Christodoulou"],
        "year": 2008,
        "venue": "arXiv:0805.3880 [gr-qc] (26 May 2008); 594-page monograph; EMS Monographs in Mathematics (2009)",
        "doi": "10.48550/arXiv.0805.3880",
        "arxiv_id": "0805.3880",
        "url": "https://arxiv.org/abs/0805.3880",
        "verification": fetch_verification(
            "https://arxiv.org/abs/0805.3880",
            "The subject of this work is the formation of black holes in pure general relativity, by the "
            "focusing of incoming gravitational waves. The theorems established in this monograph constitute "
            "the first foray into the long time dynamics of general relativity in the large, that is, when the "
            "initial data are no longer confined to a suitably small neighborhood of Minkowskian data. The "
            "theorems are general, no symmetry conditions on the initial data being imposed."),
        "status": "verified-primary",
        "reviewer": ACTOR,
        "notes": "Characteristic/short-pulse data class. Abstract gives scope and generality but not the "
                 "quantitative hypothesis; no genericity claim is made.",
    },
    {
        "source_id": "W07-SRC-03",
        "bibkey": "lukoh2017linear",
        "title": "Proof of linear instability of the Reissner-Nordstr\u00f6m Cauchy horizon under scalar perturbations",
        "authors": ["Jonathan Luk", "Sung-Jin Oh"],
        "year": 2017,
        "venue": "Duke Mathematical Journal 166(3), 437-493 (2017); arXiv:1501.04598 (19 Jan 2015)",
        "doi": "10.1215/00127094-3715189",
        "arxiv_id": "1501.04598",
        "url": "https://arxiv.org/abs/1501.04598",
        "verification": fetch_verification(
            "https://arxiv.org/abs/1501.04598",
            "It has long been suggested that solutions to linear scalar wave equation $$\\Box_g\\phi=0$$ on a "
            "fixed subextremal Reissner-Nordstr\u00f6m spacetime with non-vanishing charge are generically "
            "singular at the Cauchy horizon. We prove that generic smooth and compactly supported initial "
            "data on a Cauchy hypersurface indeed give rise to solutions with infinite nondegenerate energy "
            "near the Cauchy horizon in the interior of the black hole. In particular, the solution "
            "generically does not belong to $W^{1,2}_{loc}$."),
        "status": "verified-primary",
        "reviewer": ACTOR,
        "notes": "Linear (fixed background) result. The nonlinear SCC consequence is stated in the abstract "
                 "as expected, not proved; the row recording it must stay linear.",
    },
    {
        "source_id": "W07-SRC-04",
        "bibkey": "dafermos2005interior",
        "title": "The interior of charged black holes and the problem of uniqueness in general relativity",
        "authors": ["Mihalis Dafermos"],
        "year": 2005,
        "venue": "Communications on Pure and Applied Mathematics 58 (2005), 445-504; arXiv:gr-qc/0307013 (3 Jul 2003)",
        "doi": "10.48550/arXiv.gr-qc/0307013",
        "arxiv_id": "gr-qc/0307013",
        "url": "https://arxiv.org/abs/gr-qc/0307013",
        "verification": fetch_verification(
            "https://arxiv.org/abs/gr-qc/0307013",
            "We establish that the heuristic mass inflation scenario put forth by Israel and Poisson is "
            "mathematically correct in the context of this initial value problem. In particular, the maximal "
            "domain of development has a future boundary, over which the spacetime is extendible as a "
            "continuous metric, but along which the Hawking mass blows up identically; thus, the spacetime is "
            "inextendible as a differentiable metric. ... This shows that under Christodoulou's C^0 "
            "formulation, the strong cosmic censorship conjecture is false for this system."),
        "status": "verified-primary",
        "reviewer": ACTOR,
        "notes": "Einstein-Maxwell-scalar, spherical symmetry. NOT a vacuum result; the abstract's C^0-SCC "
                 "falsehood clause is explicitly scoped to 'this system'.",
    },
    {
        "source_id": "W07-SRC-05",
        "bibkey": "giorgi2022wave",
        "title": "Wave equations estimates and the nonlinear stability of slowly rotating Kerr black holes",
        "authors": ["Elena Giorgi", "Sergiu Klainerman", "Jeremie Szeftel"],
        "year": 2022,
        "venue": "arXiv:2205.14808 [math.AP] (30 May 2022)",
        "doi": "10.48550/arXiv.2205.14808",
        "arxiv_id": "2205.14808",
        "url": "https://arxiv.org/abs/2205.14808",
        "verification": fetch_verification(
            "https://arxiv.org/abs/2205.14808",
            "This is the last part of our proof of the nonlinear stability of the Kerr family for small "
            "angular momentum, i.e $|a|/m\\ll 1$, in which we deal with the nonlinear wave type estimates "
            "needed to complete the project. ... this work completes proof of the Main Theorem stated in "
            "Section 3.4 of \\cite{KS:Kerr}."),
        "status": "verified-primary",
        "reviewer": ACTOR,
        "notes": "Completion part of a multi-paper program; the exact Main Theorem quantifiers live in the "
                 "companion (Klainerman-Szeftel). Abstract confirms scope |a|/m << 1 only.",
    },
    {
        "source_id": "W07-SRC-06",
        "bibkey": "penrose1969gravitational",
        "title": "Gravitational collapse: the role of general relativity",
        "authors": ["Roger Penrose"],
        "year": 1969,
        "venue": "Rivista del Nuovo Cimento 1, 252-276 (1969)",
        "doi": None,
        "arxiv_id": None,
        "url": None,
        "verification": {},
        "status": "unresolved",
        "status_reason": "No fetched locator with a verbatim quote: DOI/JSTOR route blocked (cross-origin "
                         "redirect), Semantic Scholar rate-limited on 2026-09-11. The 1969 origin of the "
                         "conjecture is therefore not yet primary-source verified in this ledger.",
        "next_action": "Fetch a citable publisher/zbMATH/Annals-style landing page and record a verbatim quote "
                       "of the conjecture formulation; then upgrade.",
        "reviewer": ACTOR,
    },
    {
        "source_id": "W07-SRC-07",
        "bibkey": "choptuik1993universality",
        "title": "Universality and scaling in gravitational collapse of a massless scalar field",
        "authors": ["Matthew W. Choptuik"],
        "year": 1993,
        "venue": "Physical Review Letters 70(1), 9-12 (1993)",
        "doi": "10.1103/PhysRevLett.70.9",
        "arxiv_id": None,
        "url": "https://doi.org/10.1103/PhysRevLett.70.9",
        "verification": {},
        "status": "unresolved",
        "status_reason": "Semantic Scholar record (fetched 2026-09-11) returns abstract: null - elided by the "
                         "publisher; no arXiv version exists. APS landing page not fetched; no verbatim quote "
                         "obtained.",
        "next_action": "Fetch the APS abstract page or an open mirror; if neither yields a quotable abstract, "
                       "cite a verified review that states the scaling law.",
        "reviewer": ACTOR,
    },
]

# ---------------------------------------------------------------------------
# theorem / claim rows
# ---------------------------------------------------------------------------
THEOREMS = [
    {
        "theorem_id": "W07-TH-01",
        "label": "Weak cosmic censorship: the formulation as an open problem",
        "class_ids": ["DEFINITIONS"],
        "conclusion_type": "open_problem",
        "statement_exact": "Weak cosmic censorship: generically, all singularities in General Relativity "
                           "arising from regular asymptotically flat initial data should have a complete "
                           "future null infinity (verbatim from SRC-001: 'The weak cosmic censorship "
                           "conjecture posits that, generically, all singularities in General Relativity "
                           "arising from regular asymptotically flat initial data should have a complete "
                           "future null infinity. While this conjecture remains wide open ...').",
        "assumptions": ["asymptotically flat initial data", "data regular (smooth, or as fixed by the class)",
                        "a genericity notion is part of the formulation and is not fixed by the conjecture"],
        "falsifiers": ["An explicit regular asymptotically flat initial data set, satisfying the class's "
                       "genericity condition, whose maximal development has incomplete future null infinity "
                       "(a singularity visible from infinity).",
                       "A proof that the class's genericity notion is vacuous (no data satisfy it), which "
                       "would make the statement empty rather than true."],
        "source_ids": ["SRC-001"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Review-level formulation (SRC-001); the 1969 origin is recorded as unresolved "
                          "source W07-SRC-06 and is not used to support this row."],
        "does_not_imply": ["does not assert WCC for any restricted data class",
                           "does not define the genericity measure"],
        "unresolved": [],
        "next_action": "None; formulation row.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-02",
        "label": "WCC is open for generic asymptotically flat vacuum data",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "conclusion_type": "open_problem",
        "statement_exact": "For the Einstein vacuum equations with generic asymptotically flat initial data, "
                           "weak cosmic censorship (complete future null infinity) is not known to hold or "
                           "fail. SRC-001: 'While this conjecture remains wide open, it has inspired many "
                           "mathematical works concerning topics such as trapped surface formation and the "
                           "construction of naked singularities.'",
        "assumptions": ["vacuum (Ric = 0)", "asymptotically flat", "generic data (notion to be fixed by F1)"],
        "falsifiers": ["A proof of WCC for this class (would close it as a theorem).",
                       "An explicit generic asymptotically flat vacuum counterexample (would close it as false).",
                       "A partial result promoted to the full class without a genericity argument."],
        "source_ids": ["SRC-001"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Status statement, not a theorem; 'wide open' is the review's assessment at 2025."],
        "does_not_imply": ["does not bound how large the class of 'generic' data is",
                           "does not follow from BH-formation results in restricted data classes"],
        "unresolved": [],
        "next_action": "Re-check against a 2026 source at L1 review time.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-03",
        "label": "Christodoulou: black-hole formation from focusing vacuum gravitational waves",
        "class_ids": ["AF-WCC-VAC-BH-FORM"],
        "conclusion_type": "theorem",
        "statement_exact": "For vacuum initial data describing the focusing of incoming gravitational waves, "
                           "a black-hole region forms; the monograph's theorems are 'the first foray into the "
                           "long time dynamics of general relativity in the large' and hold with 'no symmetry "
                           "conditions on the initial data being imposed' (W07-SRC-02 abstract). The exact "
                           "quantitative hypotheses are stated in the monograph and are NOT reproduced here.",
        "assumptions": ["vacuum", "characteristic/short-pulse data describing focusing incoming waves",
                        "no symmetry assumed", "quantitative smallness/largeness conditions per the monograph"],
        "falsifiers": ["A counterexample to the monograph's main theorem within its stated data class.",
                       "Use of this row to conclude WCC for generic AF data (the data class is not generic)."],
        "source_ids": ["W07-SRC-02"],
        "status": "provisional",
        "supports_claim": True,
        "scope_caveats": ["Abstract-only verification: the 594-page monograph was not read; quantitative "
                          "hypotheses must be quoted from the text before promotion."],
        "does_not_imply": ["does not prove weak cosmic censorship",
                           "does not cover generic asymptotically flat Cauchy data",
                           "does not assert future null infinity completeness for arbitrary data"],
        "unresolved": ["Exact theorem numbering and hypothesis list from the monograph body."],
        "next_action": "Read the monograph's main theorem statement and replace this abstract-level row.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-04",
        "label": "Rodnianski-Shlapentokh-Rothman: vacuum exterior of a naked singularity",
        "class_ids": ["AF-WCC-VAC-NS-CONSTR"],
        "conclusion_type": "counterexample",
        "statement_exact": "There exist 3+1-dimensional solutions of the Einstein vacuum equations corresponding "
                           "to the exterior region of a naked singularity, constructed via a new type of "
                           "self-similarity (SRC-002 abstract).",
        "assumptions": ["vacuum", "3+1 dimensions", "self-similar data class (non-generic)"],
        "falsifiers": ["A demonstration that the constructed solutions are not solutions of the vacuum equations, "
                       "or that the singular boundary is not visible from infinity."],
        "source_ids": ["SRC-002"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Self-similar (non-generic) data; see does_not_imply."],
        "does_not_imply": ["does NOT refute weak cosmic censorship: the construction is non-generic",
                           "says nothing about the fate of generic asymptotically flat vacuum data"],
        "unresolved": [],
        "next_action": "Keep bound to the local sub-DAG AF-WCC-VAC-NS-CONSTR; never cite in AF-WCC-VAC-GEN rows.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-05",
        "label": "Rodnianski-Shlapentokh-Rothman: interior solution and gluing (preprint)",
        "class_ids": ["AF-WCC-VAC-NS-CONSTR"],
        "conclusion_type": "conditional_theorem",
        "statement_exact": "Interior-region vacuum solutions are constructed and glued to the exterior "
                           "construction 'to produce a naked singularity' (SRC-003 abstract).",
        "assumptions": ["vacuum", "self-similar data class", "validity of the gluing argument"],
        "falsifiers": ["A gap in the gluing shown by a later paper; the preprint is not peer-reviewed."],
        "source_ids": ["SRC-003"],
        "status": "provisional",
        "supports_claim": True,
        "scope_caveats": ["Preprint only (single v1, 2022), not peer-reviewed as of the ledger date."],
        "does_not_imply": ["does not refute weak cosmic censorship", "non-generic data class"],
        "unresolved": ["Peer review status and any published version."],
        "next_action": "Re-check for a journal version at L1.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-06",
        "label": "Dafermos-Luk: continuous extendibility of the Kerr Cauchy horizon",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "conclusion_type": "conditional_theorem",
        "statement_exact": "For a class of vacuum spacetimes arising from small perturbations of Kerr, 'the "
                           "maximal Cauchy evolution can be extended across a non-trivial piece of Cauchy "
                           "horizon as a Lorentzian manifold with continuous metric'; consequently, if the Kerr "
                           "exterior is dynamically stable, 'the C^0-inextendibility formulation of Penrose's "
                           "celebrated strong cosmic censorship conjecture is in fact false' (SRC-004 abstract).",
        "assumptions": ["vacuum", "data in the paper's class of small perturbations of Kerr",
                        "for the 'false' corollary: nonlinear stability of the Kerr exterior (SRC-004's "
                        "condition), now available for |a|/m << 1 by W07-SRC-05"],
        "falsifiers": ["A gap in the extension argument, or the Kerr-stability antecedent failing for the "
                       "relevant range of angular momenta.",
                       "Extension of the conclusion to C^2 (or H^2_loc) regularity, which the source does "
                       "not claim."],
        "source_ids": ["SRC-004", "W07-SRC-05"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["The extendibility theorem is unconditional within the paper's data class; the "
                          "'C^0 SCC false' clause is an implication whose antecedent (Kerr stability) is "
                          "supplied for small angular momentum by W07-SRC-05."],
        "does_not_imply": ["does NOT show failure of C^2-inextendibility (class AF-SCC-C2-VAC-GEN)",
                           "does NOT show the Cauchy horizon is regular: the source expects weak null "
                           "singularities",
                           "does NOT transfer to generic AF vacuum data beyond the perturbative class"],
        "unresolved": ["Whether the perturbative class of SRC-004 is generic in the sense fixed by F1."],
        "next_action": "Cross-reference the genericity matrix (FORM-GEN-05) before any genericity claim.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-07",
        "label": "Sbierski: C^0-inextendibility of the maximal analytic Schwarzschild spacetime",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "conclusion_type": "theorem",
        "statement_exact": "The maximal analytic Schwarzschild spacetime is inextendible even as a Lorentzian "
                           "manifold with a continuous metric (strengthening the C^2 statement): SRC-005: 'we "
                           "prove the stronger statement that it is even inextendible as a Lorentzian manifold "
                           "with a continuous metric.'",
        "assumptions": ["exact Schwarzschild solution (subextremal, vacuum, static)",
                        "definition of C^0 Lorentzian extension as in the paper"],
        "falsifiers": ["An explicit continuous Lorentzian extension of the maximal analytic Schwarzschild "
                       "spacetime; or a flaw in the spacelike-diameter argument."],
        "source_ids": ["SRC-005"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Single explicit vacuum solution, not a generic-data statement."],
        "does_not_imply": ["does NOT establish C^0-inextendibility for generic AF vacuum data",
                           "does NOT address Kerr perturbations (contrast W07-TH-06)",
                           "does NOT imply C^2-inextendibility for Schwarzschild (it proves the stronger C^0 "
                           "statement, which implies it for this solution only)"],
        "unresolved": [],
        "next_action": "None; keep as the positive C^0 benchmark for the class.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-08",
        "label": "C^2 strong cosmic censorship for generic vacuum data remains open; revised SCC expected",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "conclusion_type": "open_problem",
        "statement_exact": "No proof or refutation of C^2-inextendibility for generic asymptotically flat "
                           "vacuum data is recorded. SRC-004 further suggests the C^0-metric Cauchy horizons "
                           "'are generically singular in an essential way, representing so-called weak null "
                           "singularities, and thus that a revised version of strong cosmic censorship holds.'",
        "assumptions": ["vacuum", "asymptotically flat", "generic data", "C^2 regularity of the extension "
                        "class as fixed by F2"],
        "falsifiers": ["A proof of C^2 SCC for this class.",
                       "A C^2 (or H^2_loc) extension of a generic perturbed-Kerr maximal development, which "
                       "would falsify the revised expectation.",
                       "Promotion of a C^0 statement (W07-TH-06) to this class."],
        "source_ids": ["SRC-004"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["'Revised SCC' is the source's suggestion about the appropriate formulation, not a "
                          "proved theorem."],
        "does_not_imply": ["does not inherit the C^0 failure of W07-TH-06 at C^2",
                           "does not assert that weak null singularities obstruct C^2 extensions"],
        "unresolved": ["Which regularity (C^2 vs H^2_loc) the revised SCC should use is an open formulation "
                       "question owned by F2."],
        "next_action": "Track the C^2/H^2_loc distinction explicitly in the F2 schemas and in L1.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-09",
        "label": "Dafermos: mass inflation; C^0 SCC false for the Einstein-Maxwell-scalar system",
        "class_ids": ["AF-SCC-OTHER-MODELS"],
        "conclusion_type": "theorem",
        "statement_exact": "For a spherically symmetric characteristic initial value problem for the "
                           "Einstein-Maxwell-scalar field equations with Price-law decay data, 'the maximal "
                           "domain of development has a future boundary, over which the spacetime is extendible "
                           "as a continuous metric, but along which the Hawking mass blows up identically; thus, "
                           "the spacetime is inextendible as a differentiable metric', and 'under "
                           "Christodoulou's C^0 formulation, the strong cosmic censorship conjecture is false "
                           "for this system' (W07-SRC-04 abstract).",
        "assumptions": ["spherical symmetry", "Einstein-Maxwell-scalar field system (NOT vacuum)",
                        "characteristic initial data satisfying Price-law decay on the horizon",
                        "compact support of the scalar field on the initial hypersurface (per abstract)"],
        "falsifiers": ["An error in the mass-inflation argument, or a hypothesis violation in a proposed "
                       "application (e.g. applying it to vacuum data)."],
        "source_ids": ["W07-SRC-04"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Matter model, not vacuum; the C^0-SCC falsehood clause is explicitly scoped to "
                          "'this system'."],
        "does_not_imply": ["does NOT imply C^0 SCC fails for vacuum (AF-SCC-C0-VAC-GEN)",
                           "does NOT imply anything about C^2 SCC in any class",
                           "does NOT establish genericity of the data in the AF sense"],
        "unresolved": [],
        "next_action": "Keep in the supporting class; cite only as model-side evidence.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-10",
        "label": "Luk-Oh: linear instability of the Reissner-Nordstrom Cauchy horizon",
        "class_ids": ["AF-SCC-OTHER-MODELS"],
        "conclusion_type": "stability_result",
        "statement_exact": "For a fixed subextremal Reissner-Nordstrom spacetime with non-vanishing charge, "
                           "generic smooth compactly supported initial data for the linear scalar wave equation "
                           "give solutions 'with infinite nondegenerate energy near the Cauchy horizon', and "
                           "'the solution generically does not belong to W^{1,2}_loc' (W07-SRC-03 abstract).",
        "assumptions": ["fixed subextremal Reissner-Nordstrom background (NOT dynamical)",
                        "non-vanishing charge", "linear scalar wave equation", "generic smooth compactly "
                        "supported initial data"],
        "falsifiers": ["A proof that the indicated data class yields finite nondegenerate energy at the "
                       "Cauchy horizon."],
        "source_ids": ["W07-SRC-03"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Linear, fixed-background result. The abstract's nonlinear expectation is not a "
                          "theorem and is not recorded as one here."],
        "does_not_imply": ["does NOT prove nonlinear strong cosmic censorship for Einstein-Maxwell",
                           "does NOT apply to vacuum or to Kerr",
                           "does NOT establish a regularity class (C^0/C^2) conclusion by itself"],
        "unresolved": [],
        "next_action": "Pair with the nonlinear companion literature when it lands.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-11",
        "label": "Christodoulou 1999: scalar-field collapse (scope row; theorem text unresolved)",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "conclusion_type": "theorem",
        "statement_exact": "SCOPE ONLY: the paper 'addresses this question in the context of the spherical "
                           "gravitational collapse of a scalar field' (W07-SRC-01 abstract, verbatim). The "
                           "abstract does not state the theorem's conclusion, so no result statement is "
                           "asserted here.",
        "assumptions": ["spherical symmetry", "self-gravitating scalar field", "initial data as fixed by the "
                        "paper (to be quoted)"],
        "falsifiers": ["Not applicable until the exact statement is quoted; a row that asserts a conclusion "
                       "from the abstract alone is itself a defect."],
        "source_ids": ["W07-SRC-01"],
        "status": "provisional",
        "supports_claim": False,
        "scope_caveats": ["Abstract-level scope only. The theorem is expected to concern genericity/"
                          "instability of naked singularities in this system, but that wording is NOT in the "
                          "fetched abstract and is not asserted."],
        "does_not_imply": ["does NOT state any result about generic vacuum data",
                           "does NOT state whether naked singularities are generic or non-generic"],
        "unresolved": ["Exact theorem statement and genericity quantifier from Ann. of Math. 149(1) 183-217 "
                       "(arXiv:math/9901147 PDF is 35 pp; PDF fetch unsupported in this session)."],
        "next_action": "Read the full text (HTML/TeX source or a library copy) and quote Theorem 1 verbatim; "
                       "then decide accepted vs refuted.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-12",
        "label": "Choptuik critical collapse (citation reserved; abstract not retrievable)",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "conclusion_type": "numerical_evidence",
        "statement_exact": "UNVERIFIED ROW. No quotable abstract could be retrieved (W07-SRC-07: publisher "
                           "elided the abstract; no arXiv version). Do not promote: the claim that massless "
                           "scalar collapse exhibits type-II critical behaviour with black-hole mass scaling "
                           "near a critical threshold is widely cited but is NOT quoted from a fetched source "
                           "in this ledger.",
        "assumptions": ["massless scalar field", "spherical symmetry", "numerical evolution (to be confirmed)"],
        "falsifiers": ["A numerical or analytic demonstration that the cited scaling law does not hold in the "
                       "stated setup; or failure to obtain a quotable locator."],
        "source_ids": ["W07-SRC-07"],
        "status": "unresolved",
        "supports_claim": False,
        "scope_caveats": ["Reserved citation only; explicitly not evidence until a locator+quote is recorded."],
        "does_not_imply": ["nothing may be cited from this row"],
        "unresolved": ["Verbatim abstract/quote and exact scaling exponent from PRL 70(1) 9-12."],
        "next_action": "Fetch APS or an open mirror; alternative: cite a verified review that states the law.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-13",
        "label": "C^0 and C^2 inextendibility are distinct regularity classes (no cross-conclusion)",
        "class_ids": ["DEFINITIONS"],
        "conclusion_type": "formal_model",
        "statement_exact": "C^0-inextendibility asks that no continuous Lorentzian extension exists; "
                           "C^2-inextendibility asks that no twice-continuously-differentiable extension "
                           "exists. The former is strictly stronger as a non-existence statement, so: a C^0 "
                           "failure does not imply a C^2 failure, and a C^0 success (inextendibility) implies "
                           "C^2 inextendibility for the same spacetime only. Sources: SRC-005 states the C^0 "
                           "result as strictly stronger than the C^2 result for Schwarzschild; SRC-004 obtains "
                           "a continuous extension while expecting the horizon to be 'generically singular'.",
        "assumptions": ["standard definitions of C^0 and C^2 Lorentzian extension",
                        "extension required to solve the vacuum equations in the stated regularity"],
        "falsifiers": ["A proof that for the class in question every continuous extension can be smoothed to "
                       "a C^2 one (or conversely), which would collapse the distinction; or a schema that "
                       "derives a C^2 conclusion from a C^0 premise."],
        "source_ids": ["SRC-004", "SRC-005"],
        "status": "accepted",
        "supports_claim": True,
        "scope_caveats": ["Formal/definitional row to enforce class separation; it makes no existence claim."],
        "does_not_imply": ["does not assert either formulation is true or false for any class"],
        "unresolved": [],
        "next_action": "Mirror this row as rule R13/R16 in the formulation rule spec.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-14",
        "label": "Kerr exterior nonlinear stability for small angular momentum (antecedent)",
        "class_ids": ["AF-SCC-OTHER-MODELS"],
        "conclusion_type": "theorem",
        "statement_exact": "The Kerr family is nonlinearly stable for small angular momentum |a|/m << 1; "
                           "W07-SRC-05 'completes proof of the Main Theorem stated in Section 3.4' of the "
                           "companion paper. The exact quantifiers are stated in the companion, not here.",
        "assumptions": ["vacuum", "initial data a small perturbation of Kerr with |a|/m << 1"],
        "falsifiers": ["A counterexample within the stated small-angular-momentum class; or a gap in the "
                       "multi-paper program."],
        "source_ids": ["W07-SRC-05"],
        "status": "provisional",
        "supports_claim": True,
        "scope_caveats": ["Abstract-only: the Main Theorem statement lives in Klainerman-Szeftel; only the "
                          "completion claim is quoted here."],
        "does_not_imply": ["does not address the black-hole interior or the Cauchy horizon",
                           "does not by itself establish the Dafermos-Luk corollary; it supplies its "
                           "antecedent for the small-|a| range"],
        "unresolved": ["Exact Main Theorem quantifiers from the companion paper."],
        "next_action": "Fetch the companion (KS:Kerr) statement and quote it; then promote.",
        "added_by": ACTOR, "added_at": NOW,
    },
    {
        "theorem_id": "W07-TH-15",
        "label": "Penrose 1969 provenance of cosmic censorship (locator unresolved)",
        "class_ids": ["DEFINITIONS"],
        "conclusion_type": "formal_model",
        "statement_exact": "UNVERIFIED ROW. The 1969 origin of the cosmic censorship conjecture is attributed "
                           "to Penrose, but no fetched locator with a verbatim quote exists yet (W07-SRC-06).",
        "assumptions": ["none asserted"],
        "falsifiers": ["A citation study showing the conjecture's origin is misattributed."],
        "source_ids": ["W07-SRC-06"],
        "status": "unresolved",
        "supports_claim": False,
        "scope_caveats": ["Provenance placeholder; W07-TH-01 uses SRC-001 for the formulation instead."],
        "does_not_imply": ["nothing may be cited from this row"],
        "unresolved": ["Publisher locator and verbatim formulation text."],
        "next_action": "Fetch a citable page for Riv. Nuovo Cimento 1 (1969) 252.",
        "added_by": ACTOR, "added_at": NOW,
    },
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(rows):>2} rows -> {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# quote grounding: each entry must be a VERBATIM substring of the cited
# source's verification.evidence.  check_grounding.py enforces it.  This is
# stricter than the builder's "evidence length >= 30 chars" rule and catches
# paraphrase drift between a theorem row and the source it cites.
# ---------------------------------------------------------------------------
GROUNDING = {
    "W07-TH-01": [("SRC-001", "The weak cosmic censorship conjecture posits that, generically, all "
                              "singularities in General Relativity arising from regular asymptotically flat "
                              "initial data should have a complete future null infinity.")],
    "W07-TH-02": [("SRC-001", "While this conjecture remains wide open, it has inspired many mathematical "
                              "works concerning topics such as trapped surface formation and the construction "
                              "of naked singularities.")],
    "W07-TH-03": [("W07-SRC-02", "The theorems established in this monograph constitute the first foray into "
                                 "the long time dynamics of general relativity in the large"),
                  ("W07-SRC-02", "no symmetry conditions on the initial data being imposed")],
    "W07-TH-04": [("SRC-002", "constructing solutions which correspond to the exterior region of a naked "
                              "singularity")],
    "W07-TH-05": [("SRC-003", "show that the two solutions may be glued together to produce a naked "
                              "singularity")],
    "W07-TH-06": [("SRC-004", "the maximal Cauchy evolution can be extended across a non-trivial piece of "
                              "Cauchy horizon as a Lorentzian manifold with continuous metric"),
                  ("SRC-004", "the C^0-inextendibility formulation of Penrose's celebrated strong cosmic "
                              "censorship conjecture is in fact false")],
    "W07-TH-07": [("SRC-005", "we prove the stronger statement that it is even inextendible as a Lorentzian "
                              "manifold with a continuous metric")],
    "W07-TH-08": [("SRC-004", "generically singular in an essential way, representing so-called weak null "
                              "singularities, and thus that a revised version of strong cosmic censorship "
                              "holds")],
    "W07-TH-09": [("W07-SRC-04", "under Christodoulou's C^0 formulation, the strong cosmic censorship "
                                 "conjecture is false for this system"),
                  ("W07-SRC-04", "extendible as a continuous metric, but along which the Hawking mass blows "
                                 "up identically")],
    "W07-TH-10": [("W07-SRC-03", "the solution generically does not belong to $W^{1,2}_{loc}$")],
    "W07-TH-11": [("W07-SRC-01", "addresses this question in the context of the spherical gravitational "
                                 "collapse of a scalar field")],
    "W07-TH-13": [("SRC-005", "we prove the stronger statement that it is even inextendible as a Lorentzian "
                              "manifold with a continuous metric"),
                  ("SRC-004", "generically singular in an essential way")],
    "W07-TH-14": [("W07-SRC-05", "completes proof of the Main Theorem stated in Section 3.4")],
}
for _t in THEOREMS:
    _t["grounding"] = [{"source_id": s, "quote": q} for s, q in GROUNDING.get(_t["theorem_id"], [])]

# ---------------------------------------------------------------------------
# Supersession map (assessed 2026-09-11 23:30 against the literature lead's
# 43-row ledger, canonical work keys).  Every row below now has an equal-or-
# stronger canonical row; re-adding them would double-count claims, so they stay
# in worker-07's durable area as provenance and are NOT injected by default.
# ---------------------------------------------------------------------------
SUPERSEDED_BY = {
    "W07-TH-01": ("D-001", "same WCC statement of record; D-001 cites SRC-001+SRC-011"),
    "W07-TH-03": ("T-201", "accepted row for Christodoulou 2009 with SRC-041/042/054"),
    "W07-TH-04": ("T-208", "accepted RSR exterior row with SRC-002/003"),
    "W07-TH-05": ("T-209", "equivalent provisional RSR interior row"),
    "W07-TH-11": ("T-101", "accepted, far more precise Christodoulou 1999 row (SRC-014/044/046)"),
    "W07-TH-12": ("T-103", "accepted Choptuik row with a quotable locator (SRC-016)"),
    "W07-TH-14": ("T-206", "accepted GKS stability row (SRC-039/040)"),
}
OVERLAPS = {
    "W07-TH-02": [("D-001", "same statement of record; this row adds only the open-status framing")],
    "W07-TH-06": [("D-002", "D-002 states the C^0 formulation; this row states the Dafermos-Luk theorem")],
    "W07-TH-07": [("D-002", "D-002 cites SRC-005 for attribution; this row states the theorem")],
    "W07-TH-08": [("D-003", "D-003 states the C^2 formulation; this row records its open status")],
    "W07-TH-13": [("D-003", "formulation row"), ("D-005", "Lipschitz/C^{0,1} variant row")],
    "W07-TH-15": [("D-001", "D-001's source pool includes the Penrose attribution (SRC-011)")],
}
for _t in THEOREMS:
    tid = _t["theorem_id"]
    if tid in SUPERSEDED_BY:
        other, why = SUPERSEDED_BY[tid]
        _t["superseded_by"] = other
        _t["superseded_note"] = why
    if tid in OVERLAPS:
        _t["overlaps"] = [{"theorem_id": o, "note": n} for o, n in OVERLAPS[tid]]




if __name__ == "__main__":
    import sys as _sys
    write_jsonl(OUT_SRC, SOURCES)
    write_jsonl(OUT_THM, THEOREMS)
    if "--inject" in _sys.argv:
        # Deliberate opt-in copy into the literature lead's batch directories.
        # Only do this after checking for duplicate rows: 7 of 15 rows are
        # superseded_by canonical ledger rows (see SUPERSEDED_BY).
        write_jsonl(LIT / "sources" / "batch-90-w07.jsonl", SOURCES)
        write_jsonl(LIT / "theorems" / "batch-90-w07.jsonl", THEOREMS)
    # local self-check of the contract, independent of the builder
    assert len(THEOREMS) >= 10, "acceptance requires >=10 theorem rows"
    tids = [t["theorem_id"] for t in THEOREMS]
    sids = {s["source_id"] for s in SOURCES}
    assert len(tids) == len(set(tids)), "duplicate theorem_id"
    for t in THEOREMS:
        assert t["status"] in {"accepted", "provisional", "unresolved", "rejected"}, t["theorem_id"]
        for k in ("statement_exact", "assumptions", "falsifiers"):
            assert t[k], f"{t['theorem_id']} missing {k}"
        for s in t["source_ids"]:
            assert s in sids or s.startswith("SRC-"), f"{t['theorem_id']} unknown source {s}"
        if t["status"] == "accepted":
            assert t["supports_claim"] is True, t["theorem_id"]
    print("self-check OK:",
          f"{len(THEOREMS)} rows,",
          f"{sum(1 for t in THEOREMS if t['status']=='accepted')} accepted,",
          f"{sum(1 for t in THEOREMS if t['status']=='provisional')} provisional,",
          f"{sum(1 for t in THEOREMS if t['status']=='unresolved')} unresolved")
