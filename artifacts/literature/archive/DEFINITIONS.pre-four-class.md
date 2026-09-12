# DEFINITIONS

*Definitions, formulations and background theorems used to bind the classes*

Working status: 9 accepted, 2 provisional/unresolved.

## D-001 — Weak cosmic censorship (WCC), statement of record [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Generically, all singularities in General Relativity arising from regular asymptotically flat initial data should have a complete future null infinity.

**Assumptions.** Einstein field equations (stated for asymptotically flat initial data); A genericity notion must be supplied separately (topology on the data space); the conjecture as quoted does not fix it; Regular initial data

**Conclusion type.** `open_problem`

**Sources.** SRC-001, SRC-011

**Scope caveats.** This is an open conjecture, not a theorem.; SRC-011 (Penrose 1969) is metadata-verified only; the wording quoted is from the peer-reviewed 2025 review SRC-001.

**Does not imply.** Nothing about strong cosmic censorship.; No statement about non-asymptotically-flat (AdS, compact, or cosmological) settings.

**Unresolved.** Exact original wording in Penrose 1969 not machine-retrieved (paywalled, no arXiv).; No canonical genericity topology agreed in the literature.

**Falsifiers.**

- Construct a generic family (open set, or positive measure in an explicitly fixed topology) of asymptotically flat initial data satisfying the constraints whose maximal globally hyperbolic development has incomplete future null infinity.
- Prove that no such genericity notion can make the conjecture true while keeping the known non-generic naked-singularity examples excluded.

## D-002 — C^0-inextendibility formulation of SCC (attribution disputed) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Strong cosmic censorship in C^0 form: the maximal Cauchy development is inextendible as a Lorentzian manifold with merely continuous metric across its Cauchy horizon.

**Assumptions.** A maximal globally hyperbolic development (MGHD) is fixed.; 'Extension' means a non-trivial isometric embedding into a larger C^0 Lorentzian manifold (the embedding may be required to be C^0 or smoother; formulations differ).; Genericity of the initial data must be supplied separately.

**Conclusion type.** `open_problem`

**Sources.** SRC-004, SRC-021, SRC-056, SRC-061, SRC-072

**Scope caveats.** Attribution split on the accessible primary quotes: THREE independent Dafermos-side sources say 'Christodoulou's C^0 formulation' (Dafermos 2005 CPAM; Dafermos-Rodnianski 2005 Invent. Math.; Dafermos 2003 abstract says 'the strong cosmic censorship conjecture of Roger Penrose'), while Dafermos-Luk 2025 says 'the C^0-inextendibility formulation of Penrose's celebrated ... conjecture' (ambiguous possessive). The name is not settled.; CORRECTED after adversarial review B: an earlier draft said the question 'whether C^0 extensions exist at all' was resolved negatively. That was wrong: C^0 extensions DO exist (Dafermos 2003/2005; Dafermos-Luk 2025). What fails is C^0-inextendibility, i.e. the non-existence of a non-trivial continuous extension.; The 'Penrose 1974 lecture' pointer in the earlier draft was removed: it was not supported by any verified quote.

**Does not imply.** Does not demand C^2 or Lipschitz inextendibility.; Does not imply WCC.

**Unresolved.** Which text first stated the C^0 formulation precisely (Penrose 1969/1974 vs Christodoulou 2009 introduction) is unresolved; the origin texts were not retrieved.; Whether the embedding in the definition is required to be C^0 or may be rougher is not uniform across papers.; The attribution count above is over accessible abstract-level quotes only, not a scholarly consensus.

**Falsifiers.**

- Exhibit a generic family of data whose MGHD admits a non-trivial continuous isometric extension (this is exactly what Dafermos-Luk produce for Kerr-like interior data, conditional on Kerr exterior stability).
- Show the formulation is vacuous because every MGHD has a continuous extension.

## D-003 — C^2 (and C^k) inextendibility formulation of SCC [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Strong cosmic censorship in C^2 form: the maximal globally hyperbolic development is future-inextendible as a Lorentzian manifold whose metric is twice continuously differentiable, for generic initial data.

**Assumptions.** MGHD fixed.; Extension = non-trivial isometric embedding into a larger C^2 Lorentzian manifold.; Genericity supplied separately.

**Conclusion type.** `open_problem`

**Sources.** SRC-024, SRC-025, SRC-050

**Scope caveats.** The literature names 'the C^2-formulation' / 'C^2 Strong Cosmic Censorship Conjecture' (Sbierski 2020; Van de Moortel 2020; Luk-Oh-Shlapentokh-Rothman 2022), but the primary text that first isolated the C^2 formulation was not retrieved.; C^2-inextendibility is strictly weaker than C^0-inextendibility: a spacetime can be C^0-extendible but not C^2-extendible.

**Does not imply.** Does not imply C^0-inextendibility.; A C^2-inextendibility result in a matter model says nothing directly about vacuum.

**Unresolved.** Primary attribution of the C^2 formulation (Christodoulou 2009 book introduction) not machine-verified; book DOI 10.4171/068 appears only in a secondary bibliography.; Whether the intended class is C^2 metrics or C^2 with additional fall-off is not uniform.

**Falsifiers.**

- Construct generic data whose MGHD admits a C^2 isometric extension across the Cauchy horizon (for the RNdS model with smooth data, Dias-Reall-Santos report exactly this in the linear coupled setting).
- Exhibit a C^2-inextendibility proof in the model and show its hypotheses fail on an open set.

## D-004 — 'Christodoulou-Chrusciel version' (continuous metric, L^2 Christoffel symbols) [provisional]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** A version of SCC in which the forbidden extension is one with continuous metric and Christoffel symbols in L^2_loc; failure means the solution can be extended across the Cauchy horizon with continuous metric and square-integrable Christoffel symbols.

**Assumptions.** MGHD fixed; Extension class = C^0 metric with connection in L^2_loc

**Conclusion type.** `open_problem`

**Sources.** SRC-029

**Scope caveats.** The name is quoted verbatim from Costa-Girao-Natario-Silva 2018: 'thus violating the Christodoulou-Chrusciel version of strong cosmic censorship'.; The Chrusciel reference intended by that name has not yet been identified in the primary literature; the naming is therefore recorded as a literature usage, not as an established attribution.

**Does not imply.** Not the C^2 formulation (L^2 connection is weaker than C^1, hence much weaker than C^2).; Not the C^0 formulation (which forbids even continuous extensions).

**Unresolved.** Identify the Chrusciel paper that defines this version.; Check whether 'L^2_loc Christoffel' or 'H^1_loc metric' is the intended class.

**Falsifiers.**

- Locate a primary text defining the Christodoulou-Chrusciel version differently, which would make the quoted usage non-standard and force a rename.
- Show that L^2_loc Christoffel extensions exist for generic vacuum data, which would decide the version negatively.

## D-005 — Lipschitz / C^{0,1}_loc and L^s_loc-connection formulations (2020-2026) [accepted]

**Evidence level (derived).** `accepted-in-press`

**Exact statement.** A family of intermediate inextendibility requirements: the MGHD is not extendible as a Lorentzian manifold in a class where the metric is Lipschitz (C^{0,1}_loc), or where the metric is continuous and the Christoffel symbols lie in L^s_loc for s>1.

**Assumptions.** MGHD fixed; Extension class fixed by the exponent s or by Lipschitz regularity of the metric

**Conclusion type.** `open_problem`

**Sources.** SRC-024, SRC-047, SRC-048

**Scope caveats.** These formulations are strictly between the C^0 and C^2 formulations in strength.; Results are recent preprints (2020-2026); the 2026 papers are not peer-reviewed in the verified set.

**Does not imply.** C^{0,1}_loc-inextendibility does not imply C^2-inextendibility (a C^{0,1} extension could exist even if no C^2 one does).; None of these results settles the C^0 formulation.

**Unresolved.** No uniform definition of 'Lipschitz extension' across the 2026 papers (embedding regularity vs metric regularity).; Publication status of Sbierski 2020 (Duke, per arXiv comment) not machine-confirmed.

**Falsifiers.**

- Produce a Lipschitz extension of a Kerr Cauchy horizon for generic data, which would falsify the Lipschitz version.
- Show the L^s_loc blow-up condition of Cameron-Sbierski 2026 fails on an open set of spherical EM-scalar data.

## D-006 — [LEAD SYNTHESIS, not a primary theorem] The verdict on SCC/WCC is genericity-class and regularity-class dependent [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Across the verified primary literature, changing the topology/regularity class in which initial data are perturbed (smooth vs rough; localized Holder vs BV vs energy space) changes whether naked singularities or Cauchy-horizon extensions are generic, without changing the underlying equations or background solutions.

**Assumptions.** Same background solution family; only the perturbation class/topology changes

**Conclusion type.** `formal_model`

**Sources.** SRC-033, SRC-032, SRC-046

**Scope caveats.** THIS IS A SYNTHESIS BY THE LEAD, not a theorem in any cited paper; it generalizes across independent model problems.; Evidence is assembled from independent model problems (spherical Einstein-scalar; RNdS wave equation), not from one theorem.; The 2026 Zheng preprint is not peer-reviewed.; CORRECTED after adversarial review B: SRC-014 (Christodoulou 1999) was removed as a source; its abstract says nothing about perturbation class or functional framework. It is context for the 1994 family, not evidence for topology-dependence.

**Does not imply.** Does not say WCC/SCC are ill-posed; it says scope statements are meaningless without the data topology.; Does not privilege one class as 'the right one'.

**Unresolved.** No consensus canonical topology in the literature.; Quantitative comparison of the topologies used across the cited works has not been done.

**Falsifiers.**

- Prove that two of the cited perturbation classes induce the same genericity verdict for the same background family and observable, which would weaken the claim to model-dependence.
- Find a formulation whose verdict is invariant across all reasonable topologies.

## T-306 — Cameron-Sbierski 2025: continuous extensions are not unique in 1+1 dimensions [provisional]

**Evidence level (derived).** `preprint`

**Exact statement.** In 1+1-dimensional Lorentzian manifolds admitting a continuous spacetime extension across a null boundary v=0, the C^0-structure of the extension is in general not uniquely determined by continuous extendibility of the metric; however, a local-global relation makes the C^0-structure rigid for strongly spherically symmetric continuous extensions across the Reissner-Nordstrom Cauchy horizon. Continuous extensions with the same C^0-structure but inequivalent C^1-structures are constructed; the construction carries over to weak null singularities in 3+1 dimensions.

**Assumptions.** 1+1-dimensional model for the uniqueness analysis; Continuous metric extension across a null boundary; Spherical symmetry for the rigidity statement

**Conclusion type.** `theorem`

**Sources.** SRC-049

**Scope caveats.** Preprint (v2 June 2026).; Model calculation; does not by itself establish non-uniqueness in the 3+1 vacuum Kerr interior.; Important methodological point: 'the' continuous extension may not be canonical, so statements about it need care.

**Does not imply.** Does not refute T-301; Dafermos-Luk exhibit one extension, which suffices to falsify C^0-inextendibility.

**Unresolved.** Whether non-uniqueness persists in 3+1 without symmetry.; Refereeing status.

**Falsifiers.**

- Prove uniqueness of continuous extensions for the 3+1 Kerr weak null singularity, contradicting the carry-over claim.

## T-512 — Chrysostomou et al. 2025: review of SCC formulations and RNdS violations [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Several strong cosmic censorship conjectures of varying strengths have been formulated in the rigorous literature; for Kerr-Newman-type black holes, SCC preservation hinges on inextendibility past the Cauchy horizon due to blue-shift instability, while in RNdS the positive cosmological constant invites a competing red-shift effect; the parameter space where SCC violations are consistently observed is illustrated.

**Assumptions.** Review-level synthesis

**Conclusion type.** `formal_model`

**Sources.** SRC-053

**Scope caveats.** Review-level evidence; useful for enumerating formulations, not for proving any of them.; Published in CQG 42 (2025) 107001 per arXiv journal-ref.

**Does not imply.** Nothing about AF vacuum directly.

**Unresolved.** Extract its formulation taxonomy into D-002/D-003/D-004/D-005 as cross-check (partially done).

**Falsifiers.**

- Find an error in the review's taxonomy; then the class dossiers must be corrected.

## D-007 — Genericity quantifier: the standard used by the C^2 SCC proof (open + dense in specified weighted topologies) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the C^2 formulation of strong cosmic censorship in the two-ended asymptotically flat Einstein-Maxwell-real-scalar model, 'generic' is made precise as: the exceptional/good set of Cauchy data is open with respect to a weighted C^1 topology and dense with respect to a weighted C^infinity topology.

**Assumptions.** Two-ended asymptotically flat Cauchy data; Einstein-Maxwell-real-scalar system in spherical symmetry; The topologies are weighted (weights fixed in Part II of the cited work)

**Conclusion type.** `formal_model`

**Sources.** SRC-057, SRC-058, SRC-033, SRC-014

**Scope caveats.** This is the only fully explicit genericity quantifier in the verified set. Other works use: 'open set' (Christodoulou 1984 dust; Klainerman-Rodnianski 2012), 'open and dense' informally, 'positive probability' (Christodoulou 1999 abstract), 'generic data in an allowed rough class' (Dafermos-Shlapentokh-Rothman 2018), or leave it implicit.; The topologies are model-specific; they cannot be transplanted to vacuum without proof.; No canonical topology exists across the literature (D-006).

**Does not imply.** Does not define genericity for the vacuum classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN.; Does not assert that 'open + dense' is the right notion for the conjecture.

**Unresolved.** F1/F2 must either adopt this standard explicitly or declare a different one; until then the map's 'GEN' suffix is under-specified.; Whether the weighted topologies have a natural analogue for Einstein-vacuum constraint data is not addressed in the verified set.

**Falsifiers.**

- Show that under this genericity standard the C^2 result becomes vacuous (e.g. the good set is empty or the topology trivial), which would force a different quantifier.
- Exhibit two reasonable topologies giving opposite verdicts for the same model, which would show the standard is not canonical.

## D-008 — Maximal globally hyperbolic development (MGHD): existence and uniqueness-up-to-isometry [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Given any set of initial data for Einstein's equations satisfying the constraint conditions, there exists a development that is maximal in the sense that it is an extension of every other development; these maximal developments form a well-defined class of solutions, and any solution with a Cauchy surface embeds in exactly one such maximal development.

**Assumptions.** Initial data satisfying the Einstein constraint equations; Development = solution containing an embedding of the data with the data as a Cauchy surface

**Conclusion type.** `theorem`

**Sources.** SRC-073

**Scope caveats.** This theorem defines the object 'MGHD' that the WCC/SCC statements quantify over; it says nothing about whether the MGHD is extendible.; Uniqueness is up to isometry, not up to concrete extension.

**Does not imply.** Does not imply any censorship statement.; Does not say the MGHD is inextendible.

**Unresolved.** Exact regularity class in the original theorem (smooth data assumed; low-regularity versions are separate results).

**Falsifiers.**

- Find constraint-satisfying data with two non-isometric maximal developments, contradicting the theorem.

## T-527 — Sbierski 2024/2025: C^{0,1}_loc-inextendibility of weak null singularities from curvature blow-up, no symmetry [accepted]

**Evidence level (derived).** `accepted-in-press`

**Exact statement.** Weak null singularities are C^{0,1}_loc-inextendible without any symmetry assumptions, via a new strategy inferring C^{0,1}_loc-inextendibility from the blow-up of curvature. The assumed blow-up is expected to hold for weak null singularities in the interior of generic rotating black holes, so the result is expected to contribute directly to the C^{0,1}_loc formulation of SCC in a neighbourhood of subextremal Kerr.

**Assumptions.** A curvature blow-up condition at the weak null singularity (the theorem's hypothesis); No symmetry assumptions

**Conclusion type.** `theorem`

**Sources.** SRC-081, SRC-080

**Scope caveats.** Accepted for publication in Inventiones Mathematicae per the arXiv comment; final volume/pages not yet machine-confirmed.; The curvature blow-up hypothesis is supplied for characteristic data by T-526 (preprint).; Non-Lipschitz-extendibility implies non-C^2-extendibility by regularity inclusion (ledger inference).

**Does not imply.** By itself does not identify a data class where the hypothesis holds (that is T-526).; Does not prove C^0-inextendibility.

**Unresolved.** Confirm the Inventiones publication details.; Whether the criterion applies to the full Kerr interior beyond characteristic data.

**Falsifiers.**

- Construct a Lipschitz extension of a weak null singularity with curvature blow-up.
- Show the curvature blow-up hypothesis fails for generic rotating interiors.

