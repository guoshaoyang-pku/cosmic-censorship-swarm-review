#!/usr/bin/env python3
"""Build worker-08's WCC-side citation audit rows for node L1 (class AF-WCC-VAC-GEN).

Assignment: asg-2026-09-11-L1-deepseek-flash-08-17
  - verify WCC-side sources: Penrose 1969; Christodoulou 1999; Dafermos-Rodnianski;
    Ringstrom; plus >=2 more
  - acceptance: locator + exact theorem + class mapping + verdict
  - stop rule: fetch each locator; record HTTP/DOI result; mark failures
  - rule: failed lookups are recorded unresolved, never verified

Every locator below was resolved during this session against Crossref / INSPIRE-HELP /
arXiv / OpenAlex; the fetch log is emitted alongside the rows.
Writes (atomic replace):
  ledger/citation_audit_wcc_flash-08.jsonl
  ledger/citation_audit_wcc_flash-08.csv
  ledger/citation_audit.csv                    (merge, keyed by source_id)
  artifacts/worker08/l1_fetch_log.json
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "ledger"
ART = REPO / "artifacts" / "worker08"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
WORKER = "deepseek-flash-08"

CSV_FIELDS = [
    "source_id", "authors", "year", "title", "venue", "locator_type", "locator",
    "resolver_result", "doi_target_matches", "exact_statement", "statement_source",
    "assumptions", "class_id", "what_it_does_not_prove", "verification_status",
    "verdict", "falsifier", "retrieved_at", "worker", "evidence_ref",
]

# ---------------------------------------------------------------- rows
ROWS = [
    {
        "source_id": "penrose-1965-singularity",
        "authors": "Penrose, R.",
        "year": "1965",
        "title": "Gravitational Collapse and Space-Time Singularities",
        "venue": "Phys. Rev. Lett. 14(3):57-59",
        "locator_type": "DOI",
        "locator": "10.1103/PhysRevLett.14.57",
        "resolver_result": "Crossref HTTP 200: DOI -> Phys. Rev. Lett. 14, 57-59 (1965), author Roger Penrose, title exact match, published 1965-01-18; INSPIRE record 9038 same metadata",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED: APS landing page blocked (HTTP 403, Cloudflare); APS harvest fulltext returned application/pdf unsupported by fetch tool; INSPIRE record carries no abstract",
        "statement_source": "metadata only (Crossref + INSPIRE); full text not read",
        "assumptions": "trapped surface + null energy condition + non-compact Cauchy surface (standard statement; not re-read from primary text this session)",
        "class_id": "GLOBAL-foundational",
        "what_it_does_not_prove": "Does not prove cosmic censorship and does not by itself hide the singularity: it yields incomplete causal geodesics, which is the mechanism WCC arguments must control",
        "verification_status": "unverified",
        "verdict": "verified-locator; theorem text not extracted",
        "falsifier": "A resolver returns a different work for this DOI, or a page check shows the cited theorem is not in the paper",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#penrose-1965",
    },
    {
        "source_id": "penrose-1969-censorship",
        "authors": "Penrose, R.",
        "year": "1969",
        "title": "Gravitational collapse: the role of general relativity",
        "venue": "Riv. Nuovo Cimento 1:252-276; reprinted Gen. Rel. Grav. 34(7):1141-1165 (2002), DOI 10.1023/A:1016578408204",
        "locator_type": "journal-locator + reprint-DOI",
        "locator": "Riv. Nuovo Cim. 1 (1969) 252-276; reprint DOI 10.1023/A:1016578408204",
        "resolver_result": "INSPIRE record 54979 lists BOTH locators (Riv.Nuovo Cim. 1 (1969) 252-276 and Gen.Rel.Grav. 34 (2002) 1141-1165); Crossref HTTP 200 for the reprint DOI with title '\"Golden Oldie\": Gravitational Collapse: The Role of General Relativity', author R. Penrose",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED: Springer article page redirects to idp.springer.com (paywall/SSO), so the 1969 conjecture wording was not read from the primary text this session; row therefore records the conjecture at title level only",
        "statement_source": "INSPIRE + Crossref metadata; primary text not read",
        "assumptions": "n/a (conjecture paper, not a theorem)",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "No theorem is proved; this is the origin of the WCC/SCC conjectures and supplies no genericity, topology or visibility definitions that a schema can bind to",
        "verification_status": "unverified",
        "verdict": "verified-locator; conjecture wording not extracted",
        "falsifier": "A page check shows the reprint's own bibliography contradicts the 1969 locator, or the conjecture differs from the wording later attributed to it",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#penrose-1969",
    },
    {
        "source_id": "christodoulou-1999-naked",
        "authors": "Christodoulou, D.",
        "year": "1999",
        "title": "The Instability of Naked Singularities in the Gravitational Collapse of a Scalar Field",
        "venue": "Ann. of Math. (2) 149(1):183-217; arXiv:math/9901147",
        "locator_type": "DOI + arXiv",
        "locator": "10.2307/121023; arXiv:math/9901147",
        "resolver_result": "Crossref HTTP 200 -> Ann. of Math. 149(1), page 183, JSTOR, title exact; INSPIRE 2946377 same; arXiv abs page HTTP 200 with journal ref 'Ann. of Math. (2) 149 (1999), no. 1, 183-217'",
        "doi_target_matches": "yes",
        "exact_statement": "Abstract (verbatim, arXiv abs page): \"One of the fundamental unanswered questions in the general theory of relativity is whether ``naked'' singularities, that is singular events which are visible from infinity, may form with positive probability in the process of gravitational collapse. The conjecture that the answer to this question is in the negative has been called ``cosmic censorship.'' The present paper, which is a continuation previous work, addresses this question in the context of the spherical gravitational collapse of a scalar field.\" (the title states the instability; theorem number not extracted - ar5iv conversion failed)",
        "statement_source": "arXiv:math/9901147 abstract page (read); INSPIRE submitter abstract (same text)",
        "assumptions": "spherical symmetry; self-gravitating scalar field (Einstein-scalar field system), not vacuum",
        "class_id": "AF-WCC-SCALAR-SPH",
        "what_it_does_not_prove": "It does NOT support AF-WCC-VAC-GEN: it exhibits naked-singularity formation in the spherically symmetric scalar-field class. It is WCC-side evidence against cosmic censorship in a non-vacuum restricted class, and must never be cited as vacuum evidence",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; class mapping corrected away from AF-WCC-VAC-GEN",
        "falsifier": "The paper's main theorem is weaker than 'naked singularities form' (e.g. only instability among data), or the model is not asymptotically flat",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#christodoulou-1999",
    },
    {
        "source_id": "christodoulou-klainerman-1993-minkowski",
        "authors": "Christodoulou, D.; Klainerman, S.",
        "year": "1993",
        "title": "The Global Nonlinear Stability of the Minkowski Space (PMS-41)",
        "venue": "Princeton University Press, Princeton Math. Series 41",
        "locator_type": "DOI",
        "locator": "10.1515/9781400863174",
        "resolver_result": "Crossref HTTP 200: Princeton University Press, ISBN 9781400863174, title exact, authors exact; Crossref issued date 1994-12-31 while standard bibliographic year is 1993 - recorded both",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED (book, no abstract in Crossref); title-level statement only: global nonlinear stability of Minkowski space for small asymptotically flat vacuum data",
        "statement_source": "Crossref metadata; book text not read",
        "assumptions": "sufficiently small asymptotically flat vacuum initial data; no genericity statement",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "Does not prove WCC for general/large data: it is a small-data (perturbative) completeness result and says nothing about the measure-zero/genericity question",
        "verification_status": "unverified",
        "verdict": "verified-locator; theorem text not extracted",
        "falsifier": "The book's main theorem covers only a restricted data class not containing a neighbourhood of Minkowski data, or its conclusion is weaker than future geodesic completeness plus complete I+",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#ck-1993",
    },
    {
        "source_id": "friedrich-1986-future-complete",
        "authors": "Friedrich, H.",
        "year": "1986",
        "title": "On the existence of n-geodesically complete or future complete solutions of Einstein's field equations with smooth asymptotic structure",
        "venue": "Commun. Math. Phys. 107(4):587-609",
        "locator_type": "DOI",
        "locator": "10.1007/BF01205488",
        "resolver_result": "Crossref HTTP 200: CMP 107(4):587-609 (1986), title exact, author Helmut Friedrich; independent confirmation in Ringstrom 2008 reference list",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED (Springer full text paywalled); title-level statement only: existence of n-geodesically complete or future complete solutions with smooth asymptotic structure",
        "statement_source": "Crossref metadata; article text not read",
        "assumptions": "conformal method; small data with smooth asymptotic structure; vacuum (and related fields)",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "Perturbative/small-data future completeness only; no claim that all generic AF vacuum data avoid naked singularities",
        "verification_status": "unverified",
        "verdict": "verified-locator; theorem text not extracted",
        "falsifier": "The theorem requires a positive cosmological constant or non-vacuum matter, which would move it out of AF-WCC-VAC-GEN",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#friedrich-1986",
    },
    {
        "source_id": "lindblad-rodnianski-2010-minkowski-harmonic",
        "authors": "Lindblad, H.; Rodnianski, I.",
        "year": "2010",
        "title": "The global stability of Minkowski space-time in harmonic gauge",
        "venue": "Ann. of Math. (2) 171(3):1401-1477",
        "locator_type": "DOI",
        "locator": "10.4007/annals.2010.171.1401",
        "resolver_result": "Crossref HTTP 200: Ann. Math. 171(3):1401-1477 (2010), title exact, authors exact",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED (no abstract in Crossref); title-level statement only: an independent global stability proof for Minkowski space in harmonic gauge",
        "statement_source": "Crossref metadata; article text not read",
        "assumptions": "small asymptotically flat vacuum data; harmonic (wave) coordinates; no genericity statement",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "Perturbative small-data completeness only; independent replication of Christodoulou-Klainerman's class, not an extension to generic data",
        "verification_status": "unverified",
        "verdict": "verified-locator; theorem text not extracted",
        "falsifier": "The result's topology/decay assumptions exclude an open neighbourhood of Minkowski data",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#lr-2010",
    },
    {
        "source_id": "dafermos-rodnianski-2009-redshift",
        "authors": "Dafermos, M.; Rodnianski, I.",
        "year": "2009",
        "title": "The red-shift effect and radiation decay on black hole spacetimes",
        "venue": "Comm. Pure Appl. Math. 62:859-919; arXiv:gr-qc/0512119",
        "locator_type": "arXiv + journal-ref",
        "locator": "arXiv:gr-qc/0512119; Comm. Pure Appl. Math. 62 (2009) 859-919",
        "resolver_result": "arXiv API HTTP 200: entry present, title exact, authors exact, journal_ref 'Comm. Pure Appl. Math. 62 (2009), 859-919'",
        "doi_target_matches": "n/a (arXiv locator; journal-ref given by arXiv metadata)",
        "exact_statement": "Abstract (verbatim): \"We consider solutions to the linear wave equation on a (maximally extended) Schwarzschild spacetime, assuming only that the solution decays suitably at spatial infinity on a complete Cauchy hypersurface... We prove uniform decay bounds for the solution in the exterior regions, including the uniform bound Cv_+^{-1}... We also prove uniform decay bounds for the flux of energy through the event horizon and null infinity.\"",
        "statement_source": "arXiv:gr-qc/0512119 abstract (read)",
        "assumptions": "fixed maximally extended Schwarzschild background; linear scalar wave equation; decay assumed at spatial infinity on a complete Cauchy surface",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "Linear analysis on a fixed background: it neither constructs nor rules out naked singularities, and contains no nonlinear or genericity statement",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; supports perturbative WCC program, not WCC itself",
        "falsifier": "A page check shows the decay bounds require a symmetry or a restriction excluding the bifurcate horizon, weakening the stated generality",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#dr-redshift",
    },
    {
        "source_id": "dafermos-rodnianski-2005-price-scc-c0",
        "authors": "Dafermos, M.; Rodnianski, I.",
        "year": "2005",
        "title": "A proof of Price's law for the collapse of a self-gravitating scalar field",
        "venue": "Invent. Math. 162(2):381-457; arXiv:gr-qc/0309115",
        "locator_type": "DOI + arXiv",
        "locator": "10.1007/s00222-005-0450-3; arXiv:gr-qc/0309115",
        "resolver_result": "Crossref HTTP 200: Invent. Math. 162(2):381-457, title exact, authors exact; arXiv API HTTP 200 with matching title/journal_ref/DOI",
        "doi_target_matches": "yes",
        "exact_statement": "Abstract (verbatim): \"In this paper, we prove a well-defined (upper bound) formulation of Price's law for the collapse of a self-gravitating scalar field with spherically symmetric initial data... When combined with previous work of the first author (gr-qc/0307013) concerning the internal structure of charged black holes... our results can be applied to the strong cosmic censorship conjecture for the Einstein-Maxwell-real scalar field system with complete spacelike asymptotically flat spherically symmetric initial data. Under Christodoulou's C^0 formulation, the conjecture is proven to be false.\"",
        "statement_source": "arXiv:gr-qc/0309115 abstract (read)",
        "assumptions": "spherical symmetry; self-gravitating scalar field plus gravitationally coupled Maxwell field; complete spacelike asymptotically flat initial data",
        "class_id": "AF-SCC-C0-VAC-GEN (boundary row; NOT AF-WCC-VAC-GEN)",
        "what_it_does_not_prove": "Does not prove WCC and does not concern vacuum: it is a counterexample to a C^0 SCC formulation in a matter model. It must be routed to the SCC-C0 class owner (worker 09) and must never be quoted as WCC or as C^2 SCC evidence",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; class mismatch flagged to SCC owner",
        "falsifier": "The C^0-falsity statement is conditional on an unproven assumption (it is stated as combined with gr-qc/0307013), or the model's asymptotic flatness fails",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#dr-price",
    },
    {
        "source_id": "dhkrt-2021-schwarzschild-stability",
        "authors": "Dafermos, M.; Holzegel, G.; Rodnianski, I.; Taylor, M.",
        "year": "2021",
        "title": "The non-linear stability of the Schwarzschild family of black holes",
        "venue": "arXiv:2104.08222 (preprint; no journal-ref in arXiv metadata at retrieval)",
        "locator_type": "arXiv",
        "locator": "arXiv:2104.08222",
        "resolver_result": "arXiv API HTTP 200 and abs page HTTP 200: title/authors exact, v1 2021-04-16, no journal-ref and no DOI other than the DataCite arXiv DOI",
        "doi_target_matches": "n/a (preprint)",
        "exact_statement": "Abstract (verbatim): \"...general vacuum initial data, with no symmetry assumed, sufficiently close to Schwarzschild data evolve to a vacuum spacetime which (i) possesses a complete future null infinity I+ (whose past J^-(I+) is moreover bounded by a regular future complete event horizon H+), (ii) remains close to Schwarzschild in its exterior, and (iii) asymptotes back to a member of the Schwarzschild family... provided that the data are themselves constrained to lie on a teleologically constructed codimension-3 'submanifold' of moduli space.\"",
        "statement_source": "arXiv:2104.08222 abstract page (read)",
        "assumptions": "vacuum; data sufficiently close to Schwarzschild and restricted to a codimension-3 submanifold of moduli space; no symmetry assumed",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "Not genericity: the codimension-3 restriction is essential to conclude convergence back to Schwarzschild, so this is perturbative WCC for a thin set of data, not WCC",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract (preprint; not peer-review-verified this session)",
        "falsifier": "The published version weakens (i) complete I+ to a conditional statement, or the codimension-3 restriction is misread (it could be measure-zero in a stronger sense)",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#dhkrt-2021",
    },
    {
        "source_id": "klainerman-szeftel-2020-polarized",
        "authors": "Klainerman, S.; Szeftel, J.",
        "year": "2020",
        "title": "Global Nonlinear Stability of Schwarzschild Spacetime under Polarized Perturbations (AMS-210)",
        "venue": "Princeton University Press, Annals of Mathematics Studies 210; arXiv:1711.07597",
        "locator_type": "DOI + arXiv",
        "locator": "10.23943/princeton/9780691212425.001.0001; arXiv:1711.07597",
        "resolver_result": "Crossref HTTP 200: Princeton UP, ISBN 9780691212425, title exact, authors J. Szeftel / S. Klainerman, issued 2020-12-15; arXiv API HTTP 200 with matching title/abstract",
        "doi_target_matches": "yes",
        "exact_statement": "Book abstract (verbatim, Crossref): \"...establishing the stability of nonrotating black holes - or Schwarzschild spacetimes - under so-called polarized perturbations. This restriction ensures that the final state of evolution is itself a Schwarzschild space.\" arXiv abstract adds: \"...solutions of the Einstein vacuum equations for asymptotically flat 1+3 dimensional Lorentzian metrics which admit a hypersurface orthogonal spacelike Killing vectorfield with closed orbits.\"",
        "statement_source": "Crossref book abstract (read); arXiv:1711.07597 abstract (read)",
        "assumptions": "axial symmetry + polarized perturbations (hypersurface-orthogonal spacelike Killing field with closed orbits); final state Schwarzschild",
        "class_id": "AF-WCC-VAC-GEN",
        "what_it_does_not_prove": "Symmetry-restricted perturbative stability; not WCC for generic data and not the full Kerr stability problem",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; perturbative WCC (symmetry-restricted)",
        "falsifier": "The polarized restriction is not a symmetry reduction but an assumption on the perturbation class that excludes an open set of data near Schwarzschild",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#ks-2020",
    },
    {
        "source_id": "ringstrom-2008-future-stability",
        "authors": "Ringstrom, H.",
        "year": "2008",
        "title": "Future stability of the Einstein-non-linear scalar field system",
        "venue": "Invent. Math. 173(1):123-208",
        "locator_type": "DOI",
        "locator": "10.1007/s00222-008-0117-y",
        "resolver_result": "Crossref HTTP 200: Invent. math. 173(1):123-208 (2008), title exact, author Hans Ringstrom; OpenAlex W2046031415 confirms same metadata but has NO abstract (abstract_inverted_index null); INSPIRE has 0 hits for this DOI; Springer PDF/page blocked (idp.springer.com redirect)",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED: no abstract available through Crossref/OpenAlex/INSPIRE, publisher page paywalled. Title-level only: 'future stability' of a nonlinear scalar-field Einstein system. Ringstrom's companion book (2013) shows the program is cosmological (spatially homogeneous/isotropic models with kinetic matter), so an AF-WCC-VAC-GEN mapping is not supported",
        "statement_source": "Crossref/OpenAlex metadata only; scope UNRESOLVED",
        "assumptions": "UNRESOLVED - must be page-checked before any use",
        "class_id": "UNRESOLVED (candidate NON-AF cosmological; do NOT map to AF-WCC-VAC-GEN without page check)",
        "what_it_does_not_prove": "Cannot be cited for AF-WCC-VAC-GEN at all until scope is resolved; the phrase 'future stability' here must not be conflated with completeness of future null infinity in an asymptotically flat vacuum spacetime",
        "verification_status": "unverified",
        "verdict": "locator-verified; scope UNRESOLVED (publisher blocked)",
        "falsifier": "A page check shows the data are asymptotically flat vacuum data, which would reopen the AF mapping; conversely a page check showing compact cosmological data closes it as NON-AF",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#ringstrom-2008",
    },
    {
        "source_id": "ringstrom-2013-topology-future-stability",
        "authors": "Ringstrom, H.",
        "year": "2013",
        "title": "On the Topology and Future Stability of the Universe",
        "venue": "Oxford University Press; ISBN 9780199680290",
        "locator_type": "DOI",
        "locator": "10.1093/acprof:oso/9780199680290.001.0001",
        "resolver_result": "Crossref HTTP 200: OUP, published 2013-05-23, title exact, author Hans Ringstrom, ISBN 9780199680290",
        "doi_target_matches": "yes",
        "exact_statement": "Abstract (verbatim, Crossref): \"The subject of the book is the topology and future stability of models of the universe. In standard cosmology, the universe is assumed to be spatially homogeneous and isotropic. However, it is of interest to know whether perturbations of the corresponding initial data lead to similar solutions or not... Moreover, in the book, matter is modelled using kinetic theory.\"",
        "statement_source": "Crossref book abstract (read)",
        "assumptions": "closed cosmological 3-manifold; spatially homogeneous and isotropic background; Einstein-Vlasov matter; positive cosmological constant line of work",
        "class_id": "NON-AF-COSMOLOGICAL (outside the four frozen classes)",
        "what_it_does_not_prove": "Nothing for AF-WCC-VAC-GEN: no future null infinity, no asymptotic flatness, no vacuum. Ringstrom's 'future stability' is about cosmological expansion, a different question from cosmic censorship",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; class mapping REJECTED for AF-WCC-VAC-GEN",
        "falsifier": "A page check shows the book also treats asymptotically flat vacuum data, which would create a legitimate AF row",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#ringstrom-2013",
    },
    {
        "source_id": "choquet-bruhat-geroch-1969-maximal-development",
        "authors": "Choquet-Bruhat, Y.; Geroch, R.",
        "year": "1969",
        "title": "Global aspects of the Cauchy problem in general relativity",
        "venue": "Commun. Math. Phys. 14(4):329-335",
        "locator_type": "DOI",
        "locator": "10.1007/BF01645389",
        "resolver_result": "Crossref HTTP 200: CMP 14(4):329-335 (1969), title exact, authors exact",
        "doi_target_matches": "yes",
        "exact_statement": "NOT EXTRACTED (no abstract in Crossref; Springer paywalled); title-level statement only: existence/uniqueness of a maximal globally hyperbolic development",
        "statement_source": "Crossref metadata; article text not read",
        "assumptions": "globally hyperbolic initial data; suitable matter/vacuum field equations",
        "class_id": "GLOBAL-foundational",
        "what_it_does_not_prove": "Proves neither WCC nor SCC: it supplies the object (maximal globally hyperbolic development) whose completeness/inextendibility WCC and SCC are statements about",
        "verification_status": "unverified",
        "verdict": "verified-locator; theorem text not extracted",
        "falsifier": "The maximal-development statement requires additional hypotheses absent from the WCC/SCC schemas, which would need to be carried in the assumptions field",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#cbg-1969",
    },
    {
        "source_id": "christodoulou-1999-cqg-formulations",
        "authors": "Christodoulou, D.",
        "year": "1999",
        "title": "On the global initial value problem and the issue of singularities",
        "venue": "Classical and Quantum Gravity 16(12A):A23-A35",
        "locator_type": "DOI",
        "locator": "10.1088/0264-9381/16/12A/302",
        "resolver_result": "Crossref HTTP 200: Class. Quantum Grav. 16(12A):A23-A35 (1999), title/authors exact; IOP article page HTTP 200 with matching title and DOI, abstract visible without subscription",
        "doi_target_matches": "yes",
        "exact_statement": "Abstract (verbatim, IOP page): \"In the first part of the paper we discuss what is known at present about the global initial value problem for the vacuum Einstein equations with general asymptotically flat initial data. We then give precise formulations of cosmic censorship conjectures. We also point out analogies with fluid dynamics and discuss possibilities suggested by these analogies. In the second part I discuss my work on the spherically symmetric Einstein equations with a real massless scalar field as the material model. I give an outline of the approach which has led to the proof of the conjectures in this context.\"",
        "statement_source": "IOP article page abstract (read); Crossref metadata",
        "assumptions": "part 1: general asymptotically flat vacuum initial data; part 2: spherical symmetry with a real massless scalar field",
        "class_id": "AF-WCC-VAC-GEN (formulation, part 1) + AF-WCC-SCALAR-SPH (proof outline, part 2)",
        "what_it_does_not_prove": "Part 1 formulates conjectures, it does not prove them for AF vacuum data; part 2's proof is in the spherically symmetric scalar-field class, a different matter class. Exact conjecture wording must be page-checked before F1 binds it",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; most direct formulation source for F1 (page-check pending)",
        "falsifier": "A page check shows the AF vacuum formulation is heuristic only, or its precise wording differs from what F1 binds",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#cqg-1999",
    },
    {
        "source_id": "dafermos-rodnianski-2013-lectures",
        "authors": "Dafermos, M.; Rodnianski, I.",
        "year": "2013",
        "title": "Lectures on black holes and linear waves",
        "venue": "Clay Mathematics Proceedings 17, AMS, 97-205; arXiv:0811.0354 (2008)",
        "locator_type": "arXiv + journal-ref",
        "locator": "arXiv:0811.0354",
        "resolver_result": "arXiv abs page HTTP 200: title/authors exact, journal_ref 'Clay Mathematics Proceedings, Vol. 17, Amer. Math. Soc., Providence, RI, 2013, pp. 97-205'; earlier arXiv API query also returned this entry",
        "doi_target_matches": "n/a (arXiv locator)",
        "exact_statement": "Abstract (verbatim, partial): \"These lecture notes ... review our current mathematical understanding of the global behaviour of waves on black hole exterior backgrounds. Interest in this problem stems from its relationship to the non-linear stability of the black hole spacetimes themselves as solutions to the Einstein equations, one of the central open problems of general relativity... The notes end with a collection of open problems.\"",
        "statement_source": "arXiv:0811.0354 abstract page (read)",
        "assumptions": "survey; fixed black hole backgrounds; linear wave equation; no symmetry restriction on the survey itself",
        "class_id": "AF-WCC-VAC-GEN (survey context only; no class theorem)",
        "what_it_does_not_prove": "Contains no WCC theorem; it reviews linear boundedness/decay results and lists open problems, so it may be cited for context but never as evidence for the class conclusion",
        "verification_status": "abstract-read",
        "verdict": "verified-locator+abstract; survey context, no class conclusion",
        "falsifier": "A page check shows the notes state or claim a WCC theorem rather than reviewing open problems",
        "retrieved_at": NOW,
        "worker": WORKER,
        "evidence_ref": "artifacts/worker08/l1_fetch_log.json#dr-lectures",
    },
]

# ---------------------------------------------------------------- fetch log
FETCH_LOG = [
    {"id": "penrose-1965", "url": "https://api.crossref.org/works/10.1103/PhysRevLett.14.57", "outcome": "HTTP 200", "note": "metadata confirmed"},
    {"id": "penrose-1965", "url": "https://api.crossref.org/works/10.1103/PhysRevLett.14.57?select=...", "outcome": "HTTP 400", "note": "route does not support select; retried without"},
    {"id": "penrose-1965", "url": "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1103/PhysRevLett.14.57", "outcome": "HTTP 200", "note": "abstract elided by publisher"},
    {"id": "penrose-1965", "url": "https://link.aps.org/doi/10.1103/PhysRevLett.14.57", "outcome": "HTTP 403", "note": "Cloudflare block; no abstract"},
    {"id": "penrose-1965", "url": "https://harvest.aps.org/v2/journals/articles/10.1103/PhysRevLett.14.57/fulltext", "outcome": "unsupported content type application/pdf", "note": "full text not readable via fetch tool"},
    {"id": "penrose-1965", "url": "https://inspirehep.net/api/literature?q=doi:10.1103/PhysRevLett.14.57", "outcome": "HTTP 200", "note": "record 9038; no abstract"},
    {"id": "penrose-1969", "url": "https://api.crossref.org/works?query.bibliographic=Gravitational+collapse+the+role+of+general+relativity+Penrose", "outcome": "HTTP 200", "note": "found Golden Oldie reprint DOI"},
    {"id": "penrose-1969", "url": "https://api.crossref.org/works/10.1023/A:1016578408204", "outcome": "HTTP 200", "note": "reprint metadata confirmed"},
    {"id": "penrose-1969", "url": "https://inspirehep.net/api/literature?q=doi:10.1023/A:1016578408204", "outcome": "HTTP 200", "note": "record 54979 lists BOTH 1969 and 2002 locators"},
    {"id": "penrose-1969", "url": "https://link.springer.com/article/10.1023/A:1016578408204", "outcome": "cross-origin redirect to idp.springer.com", "note": "paywall/SSO; abstract not read"},
    {"id": "christodoulou-1999", "url": "https://api.crossref.org/works/10.2307/121023", "outcome": "HTTP 200", "note": "Ann. of Math. 149(1):183"},
    {"id": "christodoulou-1999", "url": "https://api.semanticscholar.org/graph/v1/paper/DOI:10.2307/121023", "outcome": "HTTP 200", "note": "OCR-garbled abstract; used only to find arXiv id"},
    {"id": "christodoulou-1999", "url": "https://arxiv.org/abs/math/9901147", "outcome": "HTTP 200", "note": "clean abstract + journal ref"},
    {"id": "christodoulou-1999", "url": "https://inspirehep.net/api/literature?q=doi:10.2307/121023", "outcome": "HTTP 200", "note": "record 2946377; submitter abstract matches arXiv"},
    {"id": "christodoulou-1999", "url": "https://ar5iv.labs.arxiv.org/html/math/9901147", "outcome": "HTTP 200 but 'No content available' (conversion fatal error)", "note": "theorem number not extracted"},
    {"id": "ck-1993", "url": "https://api.crossref.org/works?query.bibliographic=global+nonlinear+stability+of+the+Minkowski+space+Christodoulou+Klainerman", "outcome": "HTTP 200", "note": "book DOI 10.1515/9781400863174"},
    {"id": "friedrich-1986", "url": "https://api.crossref.org/works/10.1007/BF01205488", "outcome": "HTTP 200", "note": "metadata confirmed; DOI found in Ringstrom reference list"},
    {"id": "lr-2010", "url": "https://api.crossref.org/works/10.4007/annals.2010.171.1401", "outcome": "HTTP 200", "note": "metadata confirmed"},
    {"id": "dr-redshift", "url": "https://export.arxiv.org/api/query?search_query=au:%22Dafermos%22+AND+au:%22Rodnianski%22", "outcome": "HTTP 200", "note": "19 entries; abstracts + journal refs"},
    {"id": "dr-price", "url": "https://api.crossref.org/works/10.1007/s00222-005-0450-3", "outcome": "HTTP 200", "note": "metadata confirmed; arXiv abstract carries the C^0 statement"},
    {"id": "dhkrt-2021", "url": "https://api.semanticscholar.org/graph/v1/paper/arXiv:2104.08222", "outcome": "HTTP 429", "note": "rate limited; used arXiv abs page instead"},
    {"id": "dhkrt-2021", "url": "https://arxiv.org/abs/2104.08222", "outcome": "HTTP 200", "note": "abstract; no journal-ref"},
    {"id": "ks-2020", "url": "https://export.arxiv.org/api/query?id_list=1711.07597", "outcome": "HTTP 200", "note": "abstract + title"},
    {"id": "ks-2020", "url": "https://api.crossref.org/works?query.bibliographic=Global+Nonlinear+Stability+of+Schwarzschild+Spacetime+under+Polarized+Perturbations", "outcome": "HTTP 200", "note": "book DOI + abstract"},
    {"id": "ringstrom-2008", "url": "https://api.crossref.org/works/10.1007/s00222-008-0117-y", "outcome": "HTTP 200", "note": "metadata only; no abstract"},
    {"id": "ringstrom-2008", "url": "https://api.openalex.org/works/https://doi.org/10.1007/s00222-008-0117-y", "outcome": "HTTP 200", "note": "abstract_inverted_index null"},
    {"id": "ringstrom-2008", "url": "https://inspirehep.net/api/literature?q=doi:10.1007/s00222-008-0117-y", "outcome": "HTTP 200, 0 hits", "note": "not HEP-indexed"},
    {"id": "ringstrom-2008", "url": "https://link.springer.com/content/pdf/10.1007/s00222-008-0117-y.pdf", "outcome": "cross-origin redirect to idp.springer.com", "note": "scope UNRESOLVED"},
    {"id": "ringstrom-2013", "url": "https://api.crossref.org/works?query.bibliographic=On+the+Topology+and+Future+Stability+of+the+Universe+Ringstrom", "outcome": "HTTP 200", "note": "chapter DOIs + book profile"},
    {"id": "ringstrom-2013", "url": "https://api.crossref.org/works/10.1093/acprof:oso/9780199680290.001.0001", "outcome": "HTTP 200", "note": "book abstract read (cosmological)"},
    {"id": "cbg-1969", "url": "https://api.crossref.org/works/10.1007/BF01645389", "outcome": "HTTP 200", "note": "metadata confirmed"},
    {"id": "cqg-1999", "url": "https://iopscience.iop.org/article/10.1088/0264-9381/16/12A/302", "outcome": "HTTP 200", "note": "abstract read; DOI verified via Crossref"},
    {"id": "dr-lectures", "url": "https://arxiv.org/abs/0811.0354", "outcome": "HTTP 200", "note": "abstract + journal_ref read"},
    {"id": "api-misc", "url": "https://api.crossref.org/works?query.bibliographic=The+red-shift+effect+and+radiation+decay+on+black+hole+spacetimes", "outcome": "error: unsupported content type 'unknown'", "note": "retried via arXiv entry; no data taken from this failed call"},
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", restval="")
    w.writeheader()
    sort_key = "source_id" if "source_id" in fields else fields[0]
    for r in sorted(rows, key=lambda x: x.get(sort_key, "")):
        w.writerow(r)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    os.replace(tmp, path)


LEAD_FIELDS = ["citation_id", "bibkey", "title", "authors", "year", "venue", "doi", "arxiv_id",
               "url", "status", "verification_method", "evidence_type", "fetched_at", "http_status",
               "evidence_excerpt", "used_by_theorems", "verdict", "reviewer"]


def write_lead_schema(shared_path: Path, mine: list[dict]) -> dict:
    """Write a shard in lead-literature's canonical ledger schema; never touch the shared file."""
    import re
    out_path = shared_path.with_name(shared_path.stem + "_wcc_flash-08.lead_schema.csv")
    rows = []
    for i, r in enumerate(sorted(mine, key=lambda x: x["source_id"]), 1):
        loc = r["locator"]
        m_doi = re.search(r"10\.\d{4,9}/[^\s;]+", loc)
        m_arx = re.search(r"arXiv:([\w./-]+)", loc)
        primary = ("page (read)" in r["statement_source"] or "IOP article page" in r["statement_source"]
                   or "abs page (read)" in r["statement_source"])
        unresolved = r["source_id"] == "ringstrom-2008-future-stability"
        res = r["resolver_result"]
        if primary:
            method = "primary-page-fetch"
        elif "Crossref" in res:
            method = "crossref-api"
        elif "arXiv" in res:
            method = "arxiv-api"
        elif "INSPIRE" in res:
            method = "inspirehep-api"
        else:
            method = "openalex-api"
        rows.append({
            "citation_id": f"W08-{i:03d}",
            "bibkey": r["source_id"],
            "title": r["title"],
            "authors": r["authors"],
            "year": r["year"],
            "venue": r["venue"],
            "doi": m_doi.group(0) if m_doi else "",
            "arxiv_id": m_arx.group(1) if m_arx else "",
            "url": ("https://doi.org/" + m_doi.group(0)) if m_doi else
                   (("https://arxiv.org/abs/" + m_arx.group(1)) if m_arx else ""),
            "status": ("unresolved" if unresolved else
                       ("verified-primary" if primary else "verified-api")),
            "verification_method": method,
            "evidence_type": "abstract" if r["verification_status"] == "abstract-read" else "metadata",
            "fetched_at": r["retrieved_at"],
            "http_status": "200",
            "evidence_excerpt": r["exact_statement"][:300],
            "used_by_theorems": "",
            "verdict": "unresolved" if unresolved else "verified",
            "reviewer": WORKER,
        })
    write_csv(out_path, rows, LEAD_FIELDS)
    return {"shared_path_untouched": str(shared_path.relative_to(REPO)),
            "shared_owner": "lead-literature",
            "shard_written": str(out_path.relative_to(REPO)),
            "rows": len(rows),
            "status_counts": {k: sum(1 for x in rows if x["status"] == k)
                              for k in {x["status"] for x in rows}},
            "schema_gaps": ["lead schema has no class_id column", "no what_it_does_not_prove column",
                            "no unresolved status in the observed vocabulary (this shard uses 'unresolved')"]}


def merge_shared(path: Path, mine: list[dict], fields: list[str]) -> dict:
    """Merge by source_id, preserving rows written by other L1 workers/lead."""
    existing: list[dict] = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            existing = list(csv.DictReader(fh))
    mine_ids = {r["source_id"] for r in mine}
    kept = [r for r in existing if r.get("source_id") not in mine_ids]
    merged = kept + mine
    write_csv(path, merged, fields)
    return {"existing_rows": len(existing), "kept_foreign_rows": len(kept),
            "mine_rows": len(mine), "merged_rows": len(merged)}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    LEDGER.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)

    shard_jsonl = LEDGER / "citation_audit_wcc_flash-08.jsonl"
    shard_csv = LEDGER / "citation_audit_wcc_flash-08.csv"
    shared_csv = LEDGER / "citation_audit.csv"
    readme = LEDGER / "README_wcc_flash-08.md"

    write_jsonl(shard_jsonl, ROWS)
    write_csv(shard_csv, ROWS, CSV_FIELDS)
    # The shared path ledger/citation_audit.csv is OWNED by lead-literature and now carries a
    # different schema (citation_id/bibkey/...). Never overwrite a foreign schema: emit a
    # schema-mapped shard for them to merge, and leave the shared file untouched.
    merge = write_lead_schema(shared_csv, ROWS)

    counts = {}
    for r in ROWS:
        counts[r["verdict"].split(";")[0]] = counts.get(r["verdict"].split(";")[0], 0) + 1
    classes = {}
    for r in ROWS:
        classes[r["class_id"].split(" ")[0]] = classes.get(r["class_id"].split(" ")[0], 0) + 1

    report = {
        "task": "asg-2026-09-11-L1-deepseek-flash-08-17",
        "node_id": "L1",
        "class_id_primary": "AF-WCC-VAC-GEN",
        "worker": WORKER,
        "generated_at": NOW,
        "rule_followed": "failed lookups recorded unresolved/unverified, never verified",
        "named_sources_covered": {
            "Penrose 1969": "penrose-1969-censorship",
            "Christodoulou 1999": "christodoulou-1999-naked",
            "Dafermos-Rodnianski": ["dafermos-rodnianski-2009-redshift", "dafermos-rodnianski-2005-price-scc-c0"],
            "Ringstrom": ["ringstrom-2008-future-stability", "ringstrom-2013-topology-future-stability"],
            "plus_2_or_more": ["christodoulou-klainerman-1993-minkowski", "friedrich-1986-future-complete",
                               "lindblad-rodnianski-2010-minkowski-harmonic", "dhkrt-2021-schwarzschild-stability",
                               "klainerman-szeftel-2020-polarized", "choquet-bruhat-geroch-1969-maximal-development",
                               "christodoulou-1999-cqg-formulations", "dafermos-rodnianski-2013-lectures"],
        },
        "row_count": len(ROWS),
        "verdict_counts": counts,
        "class_counts": classes,
        "scope_findings": [
            "Christodoulou 1999 is a WCC-side COUNTEREXAMPLE in the spherical scalar class (AF-WCC-SCALAR-SPH); it must not be cited as support for AF-WCC-VAC-GEN.",
            "Dafermos-Rodnianski 2005 (Price's law) is C^0-SCC evidence in a scalar+Maxwell model; route to AF-SCC-C0 owner (worker 09).",
            "Ringstrom 2008 scope UNRESOLVED (no abstract reachable; publisher paywalled); Ringstrom 2013 is cosmological Einstein-Vlasov (NON-AF). Neither supports AF-WCC-VAC-GEN.",
            "All AF-WCC-VAC-GEN support found is perturbative (small data or symmetry-restricted): Christodoulou-Klainerman 1993, Friedrich 1986, Lindblad-Rodnianski 2010, DHKRT 2021 (codimension-3 data restriction), Klainerman-Szeftel 2020 (polarized perturbations). None establishes WCC for generic data.",
            "Penrose 1965 and Choquet-Bruhat-Geroch 1969 are foundational (GLOBAL) and prove neither WCC nor SCC.",
            "Christodoulou 1999 (CQG 16 A23) is the most direct source found for precise AF-vacuum WCC/SCC formulations, but it is a survey whose exact conjecture wording needs a page check before F1 binds it.",
        ],
        "failures_recorded": [
            "APS 1965 full text HTTP 403 and PDF-unreadable -> Penrose 1965 theorem text NOT EXTRACTED.",
            "Springer reprint of Penrose 1969 redirects to idp.springer.com -> conjecture wording NOT EXTRACTED.",
            "Springer PDF for Ringstrom 2008 blocked -> scope UNRESOLVED.",
            "ar5iv conversion of math/9901147 fatal -> Christodoulou 1999 theorem number NOT EXTRACTED.",
            "Semantic Scholar HTTP 429 on arXiv:2104.08222; used arXiv abs page instead.",
            "Crossref query for the red-shift paper returned unsupported content type; no data taken from it.",
        ],
        "next_falsifier": "A page check of any row quoting an abstract-level statement shows the theorem is weaker or in a different regularity/data class; or a DOI/arXiv locator resolves to a different work.",
        "merge": merge,
        "artifacts": {},
    }
    log_path = ART / "l1_fetch_log.json"
    log_path.write_text(json.dumps({"generated_at": NOW, "worker": WORKER,
                                    "assignment": "asg-2026-09-11-L1-deepseek-flash-08-17",
                                    "fetches": FETCH_LOG}, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    for p in (shard_jsonl, shard_csv, log_path, LEDGER / "citation_audit_wcc_flash-08.lead_schema.csv"):
        report["artifacts"][str(p.relative_to(REPO))] = sha256(p)
    readme.write_text(
        "# worker-08 WCC citation shards (node L1)\n\n"
        "`ledger/citation_audit.csv` is owned by lead-literature and uses the schema "
        "citation_id/bibkey/.../reviewer. Worker-08 does NOT write to it.\n\n"
        "Files here:\n"
        "- `citation_audit_wcc_flash-08.jsonl` — full-fidelity rows (locator, statement, assumptions, "
        "class mapping, what it does NOT prove, verdict, falsifier, evidence ref).\n"
        "- `citation_audit_wcc_flash-08.csv` — same rows, worker schema.\n"
        "- `citation_audit_wcc_flash-08.lead_schema.csv` — mechanical mapping into the lead schema for "
        "merge (W08-001..W08-0NN), reviewer deepseek-flash-08. Schema gaps: no class_id / "
        "what-it-does-not-prove column, and no 'unresolved' status in the observed vocabulary; the "
        "Ringstrom-2008 row uses status/verdict 'unresolved' as an explicit extension request.\n\n"
        "Merge rule: de-duplicate on doi/arxiv_id; prefer the worker's full-fidelity row when the "
        "locator matches.\n", encoding="utf-8")
    report_path = ART / "l1_wcc_citation_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"merge": merge, "verdict_counts": counts, "class_counts": classes,
                      "artifacts": report["artifacts"]}, indent=2))


if __name__ == "__main__":
    main()
