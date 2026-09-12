# AF-SCC-OTHER-MODELS

*Strong cosmic censorship in matter/cosmological models used as evidence for the vacuum classes*

Working status: 24 accepted, 4 provisional/unresolved.

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

## T-104 — Christodoulou 1984: open set of dust data violates cosmic censorship [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For an open subset of initial density distributions of an inhomogeneous spherically symmetric dust cloud, the first singular event (at the centre of symmetry) is the vertex of infinitely many future null geodesic cones that intersect future null infinity; the light rays are infinitely redshifted.

**Assumptions.** Spherically symmetric inhomogeneous dust (not vacuum); Open subset of initial density distributions; Dust energy conditions / standard dust model

**Conclusion type.** `counterexample`

**Sources.** SRC-015

**Scope caveats.** Matter model = dust; this is NOT a vacuum counterexample and must never be cited as one.; Infinitely redshifted rays: visibility from infinity is not the same as a physically observable signal.

**Does not imply.** Does not refute AF-WCC-VAC-GEN.; Does not transfer to scalar-field or vacuum models.

**Unresolved.** Exact topology on density distributions in the 1984 paper (C^k? weighted?) not extracted.

**Falsifiers.**

- Show the singular event is censored in a more careful notion of visibility (e.g. only infinitely redshifted, non-observable radiation), which would demote the counterexample to a weaker 'violation'.

## T-106 — An-Wu 2026: non-spherical Einstein-scalar naked singularities with singular inner Cauchy horizon [provisional]

**Evidence level (derived).** `preprint`

**Exact statement.** There exist non-spherically-symmetric solutions of the 3+1-dimensional Einstein-scalar field system with incomplete future null infinity and a singular inner Cauchy horizon, obtained by prescribing non-spherical data along incoming and outgoing null hypersurfaces; the solutions satisfy C^{1,kappa/(1-kappa)+} inextendibility at the inner Cauchy horizon for self-similar parameter kappa in (0,1/3).

**Assumptions.** Einstein-scalar field system (not vacuum); Characteristic initial data on two transversely intersecting null hypersurfaces; No symmetry assumed; constructed from a generalisation of Christodoulou's self-similar solution

**Conclusion type.** `counterexample`

**Sources.** SRC-045

**Scope caveats.** Preprint (v1, July 2026, 116 pages); not peer-reviewed.; Matter model is a scalar field, not vacuum.; Failure of WCC here is 'in its strict formulation' for constructed, non-generic data.

**Does not imply.** Does not refute generic WCC.; Does not give a vacuum naked singularity.

**Unresolved.** Refereeing status.; Whether the construction has an open neighbourhood of data with the same behaviour.

**Falsifiers.**

- Find a gap in the global existence/inextendibility proof (preprint, unreviewed).
- Show the constructed spacetimes are C^{1,...}-extendible across the inner horizon.

## T-207 — Hintz-Vasy 2018: nonlinear stability of Kerr-de Sitter (Lambda > 0) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Full global non-linear stability of the Kerr-de Sitter family of black holes as solutions of the initial value problem for the Einstein vacuum equations with positive cosmological constant, for small angular momenta and without symmetry assumptions on the initial data.

**Assumptions.** Einstein vacuum equations with Lambda > 0; Small angular momenta; No symmetry assumptions

**Conclusion type.** `stability_result`

**Sources.** SRC-035

**Scope caveats.** Lambda > 0; NOT the asymptotically flat class.; Stability of the exterior; does not by itself decide the C^0/C^2 SCC formulation in the interior (see the RNdS literature for the opposite tendency).

**Does not imply.** Does not prove WCC or SCC for AF data.; Does not transfer the RNdS SCC-violation results to Kerr-dS (Miguel 2021 shows the relevant mode coincidence does not occur there).

**Unresolved.** Interior structure of the stable Kerr-dS solutions is not addressed in the verified abstract.

**Falsifiers.**

- Find an error in the proof (no retraction found).
- Show the small-angular-momentum restriction is essential in a way that changes the SCC picture.

## T-304 — Cameron-Sbierski 2026: L^s_loc-connection inextendibility of spherical weak null singularities [provisional]

**Evidence level (derived).** `preprint`

**Exact statement.** Spherically symmetric weak null singularities are inextendible as spherically symmetric Lorentzian manifolds with continuous metric and Christoffel symbols in L^s_loc for s > 1, assuming a blow-up condition on the derivative of the area-radius function transverse to the singularity plus a rigidity result on continuous spherically symmetric extensions. The assumptions are satisfied by Reissner-Nordstrom-Vaidya and by a class of spacetimes arising from small and generic spherically symmetric perturbations of subextremal Reissner-Nordstrom under the Einstein-Maxwell-scalar field system.

**Assumptions.** Spherical symmetry of the extension (the theorem is restricted to spherically symmetric extensions); Continuous metric; Christoffel symbols in L^s_loc, s>1; Blow-up condition on the transverse derivative of the area radius; Rigidity of continuous spherically symmetric extensions from Cameron-Sbierski 2025

**Conclusion type.** `conditional_theorem`

**Sources.** SRC-048, SRC-049, SRC-024

**Scope caveats.** Preprint (Sep 2026), not peer-reviewed.; Restricted to extensions preserving spherical symmetry; non-symmetric extensions are not excluded.; Matter model is EM-scalar, not vacuum.

**Does not imply.** Does not prove C^2 SCC in vacuum.; Does not exclude Lipschitz or C^2 extensions outside the spherically symmetric class.

**Unresolved.** Whether the spherical-symmetry restriction on the extension can be removed.; Refereeing status.

**Falsifiers.**

- Construct a spherically symmetric continuous extension with Christoffel symbols in L^s_loc for some s>1 of the RN-Vaidya spacetime (would refute the theorem).
- Show the blow-up condition fails for the claimed generic perturbations.

## T-501 — Dafermos 2005: mass inflation for spherical EM-scalar with Price-law data (C^0 extendible, C^1 inextendible) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For a spherically symmetric double-characteristic initial value problem for the Einstein-Maxwell-scalar field equations with Price-law decay on the outgoing initial characteristic, the maximal future development has a future boundary over which the spacetime is extendible as a C^0 metric but along which the Hawking mass blows up identically; the spacetime is inextendible as a C^1 metric. Under Christodoulou's C^0 formulation, strong cosmic censorship is false for this system.

**Assumptions.** Spherical symmetry; Einstein-Maxwell-(real)-scalar field system; Price-law decay of the data on the outgoing characteristic (widely believed for collapse from AF data); with Dafermos-Rodnianski the result applies to compactly supported scalar hair

**Conclusion type.** `theorem`

**Sources.** SRC-021, SRC-060, SRC-056, SRC-061

**Scope caveats.** Matter model is EM-scalar, not vacuum.; This is the canonical result behind the statement 'C^0 SCC fails for charged spherical collapse'.; Dafermos 2003 (SRC-020) is metadata-only in this ledger and underlies the stability-of-radius input; its own DOI is unverified.

**Does not imply.** Does not imply the same for vacuum with angular momentum (T-301 supplies that, conditionally).; Does not distinguish C^1 from C^2: since there is no C^1 extension, there is no C^2 extension either for this class.

**Unresolved.** The precise Price-law exponent needed.; SRC-020 (Dafermos 2003 Ann. Math.) is now anchored by the Crossref record SRC-060; no further verification gap for this entry.

**Falsifiers.**

- Find an error in the mass-inflation argument (none found; the result is widely cited and refined by T-505, T-506).
- Show the constructed extension fails to be C^0 across the boundary.

## T-502 — Costa-Girao-Natario-Silva 2017: RNdS scalar field admits continuous extensions with L^2 Christoffel symbols [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For spherically symmetric characteristic data for the Einstein-Maxwell-scalar field system with positive cosmological constant whose data on the outgoing null hypersurface is a subextremal Reissner-Nordstrom black-hole event horizon, mass inflation may or may not occur depending on the decay rate; when the mass is controlled there are continuous extensions of the metric across the Cauchy horizon with square-integrable Christoffel symbols, and under slightly stronger conditions there are non-isometric extensions that are classical solutions of the Einstein equations. The results provide evidence against SCC when Lambda > 0.

**Assumptions.** Spherical symmetry; characteristic initial data; Einstein-Maxwell-scalar with Lambda > 0; Subextremal RN-dS event-horizon data; Exponential Price-law decay rate as the parameter

**Conclusion type.** `theorem`

**Sources.** SRC-028, SRC-026, SRC-027

**Scope caveats.** Matter model EM-scalar; Lambda > 0; NOT asymptotically flat vacuum.; Classical extension under stronger conditions is a genuine violation of the L^2-connection version (D-004).

**Does not imply.** Does not imply SCC violation for asymptotically flat vacuum.; Does not decide the C^0 formulation (an even stronger violation).

**Unresolved.** Whether the extensions satisfy the vacuum equations (they do not; charged matter is present).

**Falsifiers.**

- Find an error in Parts 1-3 (no retraction found).
- Show the constructed extensions are isometric to the original development (then they would be trivial).

## T-503 — Costa-Girao-Natario-Silva 2018: open sets of data violating the Christodoulou-Chrusciel version (Lambda > 0) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the Einstein-Maxwell-scalar field system with positive cosmological constant in the black-hole interior, assuming an exponential Price law along the event horizon, there are open sets of characteristic data converging exponentially to a reference Reissner-Nordstrom black hole at infinity for which mass inflation may or may not occur depending on the decay rate; in the no-mass-inflation decay regime (and not for the open sets as such) the solution extends across the Cauchy horizon with continuous metric and Christoffel symbols in L^2_loc, violating the Christodoulou-Chrusciel version of strong cosmic censorship.

**Assumptions.** Spherical symmetry; characteristic data; Lambda > 0; subextremal RN reference at infinity; Exponential Price law along the event horizon; Open sets of characteristic data

**Conclusion type.** `counterexample`

**Sources.** SRC-029

**Scope caveats.** Matter model EM-scalar; Lambda > 0; NOT vacuum and NOT asymptotically flat.; CORRECTED after adversarial review B: the L^2-Christoffel extension is restricted to the no-mass-inflation decay regime ('in the latter case' in the source abstract), not to the open sets as such.; The 'Christodoulou-Chrusciel version' attribution is itself an open item (D-004).

**Does not imply.** Does not refute AF-SCC-C2-VAC-GEN.; Does not refute the C^2 formulation, since the extensions here are not C^2.

**Unresolved.** Identify the intended Chrusciel reference.; Whether the open-set statement survives without the exponential Price-law assumption.

**Falsifiers.**

- Show the constructed extensions are not solutions of the system in the stated regularity.
- Show the data sets are not open in the stated topology.

## T-504 — Luk-Oh 2017: generic linear instability of the RN Cauchy horizon [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** On a fixed subextremal Reissner-Nordstrom spacetime with non-vanishing charge, generic smooth and compactly supported initial data on a Cauchy hypersurface give rise to solutions of the linear scalar wave equation with infinite non-degenerate energy near the Cauchy horizon; in particular the solution generically does not belong to W^{1,2}_loc. Price's law decay is generically sharp along the event horizon.

**Assumptions.** Fixed subextremal RN background (nonlinear backreaction absent); Linear massless scalar wave equation; Generic smooth compactly supported initial data

**Conclusion type.** `theorem`

**Sources.** SRC-023

**Scope caveats.** Linear equation on a fixed background: it is evidence for, not a proof of, the nonlinear statement.; The word 'generic' here is with respect to smooth compactly supported data on a Cauchy surface.

**Does not imply.** Does not imply nonlinear mass inflation (see T-510 for the conditional nonlinear statement).; Does not decide C^0 vs C^2 formulations.

**Unresolved.** None specific to the linear statement.

**Falsifiers.**

- Find an error in the energy blow-up proof (no retraction found).
- Show the exceptional set is larger than meagre in the stated topology.

## T-505 — Van de Moortel 2020: C^2-inextendibility for spherical EM-Klein-Gordon under expected decay [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the Einstein-Maxwell-Klein-Gordon system in spherical symmetry, assuming sufficiently slow decay of the charged scalar field on the event horizon, the Cauchy horizon emanating from timelike infinity splits into a dynamical set (Hawking mass blows up) and a static set isometric to a Reissner-Nordstrom Cauchy horizon, and is globally C^2-inextendible; in particular two-ended asymptotically flat spacetimes are C^2-future-inextendible, i.e. C^2 strong cosmic censorship holds for this system under the decay assumption.

**Assumptions.** Spherical symmetry; Einstein-Maxwell-Klein-Gordon (charged scalar); Assumption: sufficiently slow decay of the charged scalar field on the event horizon (expected rate); Two-ended (and one-ended near i+) settings

**Conclusion type.** `conditional_theorem`

**Sources.** SRC-025

**Scope caveats.** Matter model EM-KG; not vacuum.; The mass-inflation dichotomy is proved, but 'we do not directly show mass inflation' for all cases (abstract).

**Does not imply.** Does not prove C^2 SCC for vacuum.; Does not decide C^0 (no continuous extension statement).

**Unresolved.** Whether the decay assumption is now a theorem (see T-511 and Gautam 2024).

**Falsifiers.**

- Show the decay assumption fails for an open set of admissible data.
- Find a C^2 extension of the constructed spacetimes.

## T-506 — Sbierski 2020: C^{0,1}_loc-inextendibility of spherical weak null singularities [accepted]

**Evidence level (derived).** `accepted-in-press`

**Exact statement.** Using an unbounded local holonomy, spherically symmetric weak null singularities arising at the Cauchy horizon in black-hole interiors are C^{0,1}_loc-inextendible; the theorem does not presuppose mass inflation and applies to Reissner-Nordstrom-Vaidya and to spacetimes from small generic spherically symmetric perturbations of two-ended subextremal RN data for the Einstein-Maxwell-scalar system, improving the Luk-Oh C^2 formulation to a C^{0,1}_loc formulation.

**Assumptions.** Spherical symmetry; Continuous metric (C^{0,1}_loc = locally Lipschitz) extension class; Applies to the stated RN-Vaidya and perturbed RN classes

**Conclusion type.** `theorem`

**Sources.** SRC-024, SRC-023, SRC-087

**Scope caveats.** Preprint accepted by Duke Math. J. per the arXiv comment; publication metadata not machine-confirmed.; Matter model EM-scalar for the perturbation class.; Does not cover vacuum without symmetry.

**Does not imply.** Does not prove C^{0,1}_loc-inextendibility for Kerr.; Does not settle C^0.

**Unresolved.** Duke Math. J. 171(14) (2022), DOI 10.1215/00127094-2022-0040 now verified via Crossref (SRC-087); volume page range not shown in the Crossref record.

**Falsifiers.**

- Construct a locally Lipschitz extension of the relevant weak null singularity (would refute the holonomy argument).

## T-507 — Numerical/QNM cluster: SCC violation in near-extremal RN-dS (2018-2023) [accepted]

**Evidence level (derived).** `numerical`

**Exact statement.** Linear and nonlinear numerical studies of massless scalar fields and of coupled gravitational-electromagnetic perturbations on near-extremal Reissner-Nordstrom-de Sitter backgrounds indicate that generic perturbations from smooth initial data have finite energy at the Cauchy horizon, and for coupled perturbations can be extended through it arbitrarily smoothly; the coincidence of interior and exterior quasinormal frequencies that could have invalidated this conclusion does not occur for RNdS or Kerr-dS.

**Assumptions.** Fixed RNdS/Kerr-dS background for the linear results; Near-extremal regime; Numerical computation of quasinormal modes / nonlinear spherical evolution for the nonlinear result

**Conclusion type.** `numerical_evidence`

**Sources.** SRC-031, SRC-032, SRC-030, SRC-034, SRC-053

**Scope caveats.** Numerical evidence; not a theorem.; Lambda > 0 and near-extremal; does not transfer to asymptotically flat vacuum.; SRC-053 is a 2025 review of the debate and is review-level evidence.

**Does not imply.** Does not refute SCC in the intended C^2 formulation for AF vacuum.; Does not prove that SCC is false in general.

**Unresolved.** Rigorous nonlinear version of the smooth-data violation (CGNS give rigorous results for a related characteristic problem, but the smooth-data statement remains numerical).

**Falsifiers.**

- A rigorous computation showing the relevant QNM decay rates differ from the numerics, restoring the blow-up.

## T-508 — Dafermos-Shlapentokh-Rothman 2018: rough data restores blue-shift blow-up on Lambda > 0 black holes [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the wave equation on Reissner-Nordstrom-de Sitter and Kerr-Newman-de Sitter spacetimes with Lambda > 0, slightly relaxing the smoothness assumption on initial data yields the analogue of the Christodoulou statement in the affirmative: for generic data in the allowed (rougher) class, local energy blows up at the Cauchy horizon for all subextremal parameter ranges, while the data remain regular enough to ensure stability, decay, boundedness and continuous extendibility beyond the Cauchy horizon.

**Assumptions.** Wave equation on fixed RN-dS/KN-dS backgrounds; Lambda > 0; Enlarged (rougher) data class, still regular enough for decay/stability; Two independent proofs: mode construction and time-translation-invariance of scattering maps

**Conclusion type.** `theorem`

**Sources.** SRC-033

**Scope caveats.** This is the cleanest primary statement that the SCC verdict depends on the data regularity class (D-006).; Lambda > 0; linear wave equation.

**Does not imply.** Does not prove nonlinear SCC for these backgrounds.; Does not transfer to AF vacuum.

**Unresolved.** Whether the 'correct' class for genericity can be pinned down canonically (the paper suggests its class may be it).

**Falsifiers.**

- Show the rough data class is not preserved by the nonlinear evolution (in the nonlinear setting).
- Construct rough generic data with bounded local energy at the Cauchy horizon.

## T-509 — Moncrief-Isenberg: analytic vacuum with compact non-degenerate Cauchy horizon forces symmetry [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** An analytic vacuum (or electrovacuum) spacetime containing a compact null hypersurface ruled by closed null generators has a non-trivial Killing symmetry; the non-degenerate such null surfaces are always Cauchy horizons across which the Killing fields change from spacelike (globally hyperbolic regions) to timelike (acausal analytic extensions). The LPB condition can be dropped, and for non-closed generators densely filling a 2-torus (non-ergodic case) the spacetime admits at least two independent commuting Killing fields, one combination horizon-generating.

**Assumptions.** Analytic category; Vacuum or electrovacuum Einstein equations; Compact null hypersurface / compact non-degenerate Cauchy horizon; Closed generators (1983/1985) or non-ergodic non-closed generators (2019)

**Conclusion type.** `theorem`

**Sources.** SRC-017, SRC-018, SRC-019

**Scope caveats.** Analyticity is essential; the smooth case is not covered.; 'Compact Cauchy horizon implies symmetry' is not by itself a proof that SCC holds.

**Does not imply.** Does not prove SCC in C^0 or C^2 form.; Does not cover non-compact Cauchy horizons (e.g. the Kerr interior).

**Unresolved.** Smooth (non-analytic) analogues: no verified result located.

**Falsifiers.**

- Construct a smooth vacuum spacetime with a compact non-degenerate Cauchy horizon and no Killing symmetry, which would show analyticity is essential.

## T-510 — Luk-Oh-Shlapentokh-Rothman 2022: generic class with C^2-future-inextendibility and conditional mass inflation [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the spherically symmetric Einstein-Maxwell-real-scalar field system there is a generic class G of Cauchy data whose maximal globally hyperbolic future developments are C^2-future-inextendible; if a conjectural improved exterior decay result holds, then for data in G the Hawking mass blows up identically on the Cauchy horizon (mass inflation). The scattering-map analysis also gives a new proof of linear instability of the RN Cauchy horizon.

**Assumptions.** Spherical symmetry; Einstein-Maxwell-real-scalar; Generic class G of Cauchy data (defined via the earlier Luk-Oh work); Improved exterior decay conjecture for the conditional mass-inflation conclusion

**Conclusion type.** `conditional_theorem`

**Sources.** SRC-050, SRC-052, SRC-057, SRC-058

**Scope caveats.** Matter model EM-scalar; not vacuum.; The generic class G is inherited from Luk-Oh arXiv:1702.05715/1702.05716, which are NOT yet verified in this ledger (see unresolved).

**Does not imply.** Does not prove C^2 SCC for vacuum.; Mass inflation is conditional.

**Unresolved.** The generic class G is inherited from Luk-Oh arXiv:1702.05715/1702.05716; these are verified (SRC-057/SRC-058), with published venues Ann. Math. 190(1) 1-111 (Part I, SRC-086) and Ann. PDE 5 (2019) no. 1 paper 6 (Part II, from a Crossref reference list, not separately verified).; Status of the improved exterior decay conjecture (Gautam 2024, SRC-052).

**Falsifiers.**

- Show class G is not generic in the intended topology.
- Construct a C^2 extension for data in G.

## T-511 — Ma-Zhang 2023: precise interior late-time asymptotics and H^1_loc-inextendibility of the Kerr Cauchy horizon (linear) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Precise late-time asymptotics are computed for the scalar field in the interior of a non-static subextremal Kerr black hole, giving a new proof of the generic H^1_loc-inextendibility of the Kerr Cauchy horizon against scalar perturbations (first shown by Luk-Sbierski, J. Funct. Anal. 2016).

**Assumptions.** Fixed non-static subextremal Kerr background; Linear scalar wave equation; Generic perturbations

**Conclusion type.** `theorem`

**Sources.** SRC-051, SRC-066, SRC-089

**Scope caveats.** Linear scalar test field on a fixed Kerr background; H^1_loc non-extendibility does NOT imply C^0 metric inextendibility (Dafermos-Luk show continuous extensions can exist). The AF-SCC-C0-VAC-GEN tag was removed after adversarial review B.; Journal reference: J. Funct. Anal. 271(7), 1948-1995 (2016), DOI 10.1016/j.jfa.2016.06.013 (SRC-089) - the earlier note in SRC-066 said 2189-2235, which was wrong.

**Does not imply.** Does not prove nonlinear C^0/C^2 SCC.; H^1_loc failure does not imply failure of C^0 extendibility (Dafermos-Luk show continuous extensions can exist).

**Unresolved.** Luk-Sbierski publication data now verified via Crossref (SRC-089).

**Falsifiers.**

- Find an error in the asymptotics or in the passage to H^1_loc blow-up.

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

## T-513 — Strong cosmic censorship in T^3-Gowdy spacetimes (Ringstrom 2009 Annals; metadata verified, statement unresolved) [rejected]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** Candidate entry: strong cosmic censorship is proved for T^3-Gowdy symmetric vacuum spacetimes (a spatially compact, symmetric class), cited as H. Ringstrom, 'Strong cosmic censorship in T^3-Gowdy spacetimes', Annals of Mathematics 170(3) (2009) 1181-1240, DOI 10.4007/annals.2009.170.1181 (title, author, volume, pages, year and DOI now verified via Crossref).

**Assumptions.** T^3-Gowdy symmetry; Vacuum Einstein equations; Compact spatial topology

**Conclusion type.** `theorem`

**Sources.** SRC-059, SRC-069

**Scope caveats.** PARTIALLY VERIFIED: bibliographic metadata now confirmed via Crossref (SRC-059); the theorem statement, formulation, and genericity quantifier are NOT verified, and no abstract was retrievable (Annals HTML fetch failed, zbMATH 403).; Must not be cited as established scope until the statement is retrieved.

**Does not imply.** Must not be used in any dossier as an accepted theorem yet.

**Unresolved.** Retrieve the abstract/statement (Annals page, zbMATH review, or author's page).; Confirm whether the conclusion is C^0 inextendibility, C^2 inextendibility, or silence/future completeness.

**Falsifiers.**

- If the theorem exists as cited, verify and promote; if the title/venue differ, record the correction rather than silently substituting.

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

## T-514 — Luk-Oh 2017/2019 two-part proof: C^2 SCC holds and C^0 SCC fails for spherical EM-scalar two-ended AF data [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the Einstein-Maxwell-(real)-scalar-field system in spherical symmetry with two-ended asymptotically flat admissible Cauchy data: (a) the maximal globally hyperbolic future development always possesses a non-empty Cauchy horizon across which the spacetime is C^0-future-extendible, so the C^0 formulation of SCC is false for this model; (b) for a generic class of such data - open in a weighted C^1 topology and dense in a weighted C^infinity topology - the spacetime is C^2-future-inextendible, proving the C^2 formulation of SCC for this model. Part I proves C^2-inextendibility conditional on an L^2-averaged polynomial lower bound for the scalar field along each event horizon; Part II proves that bound holds for the generic class.

**Assumptions.** Einstein-Maxwell-(real)-scalar field system; Spherical symmetry; Two-ended asymptotically flat admissible Cauchy data; Genericity = open in weighted C^1 topology and dense in weighted C^infinity topology (Part II)

**Conclusion type.** `theorem`

**Sources.** SRC-057, SRC-058, SRC-056

**Scope caveats.** Matter model is Einstein-Maxwell-real-scalar, NOT vacuum.; Spherical symmetry is essential; no angular momentum analogue is proved.; Two-ended data: one-ended collapse is a different problem (partially treated by Van de Moortel 2020, SRC-025).; This is the benchmark that any claimed vacuum C^2 result must be compared against; it does NOT prove anything for vacuum.

**Does not imply.** Does not imply C^2 SCC for vacuum (the angular-momentum analogue is exactly the open problem).; Does not imply that the C^0 formulation is false in general, only for this model.; Does not imply mass inflation in all cases (Van de Moortel's dichotomy is the refined statement).

**Unresolved.** Publication venue of the two-part series (arXiv says 'version accepted for publication'; journal not shown on the arXiv pages).; Whether the two-ended restriction can be dropped.

**Falsifiers.**

- Find an error in Part I or Part II (no retraction found).
- Show the generic set is not open/dense in the stated topologies, contradicting Part II's main claim.
- Construct a C^2 extension for data in the generic class, contradicting Part I.

## T-516 — Dafermos-Rodnianski 2005: Price's law (upper bound) for self-gravitating scalar collapse [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** A well-defined upper-bound formulation of Price's law is proved for the collapse of a self-gravitating scalar field with spherically symmetric initial data, optionally with an additional gravitationally coupled Maxwell field; the result supplies the decay input assumed in the interior analysis of charged black holes, and hence applies to the strong cosmic censorship conjecture for the Einstein-Maxwell-real-scalar system with complete spacelike asymptotically flat spherically symmetric initial data, where under Christodoulou's C^0 formulation the conjecture is proved false.

**Assumptions.** Spherical symmetry; Self-gravitating scalar field; optional Maxwell field; Complete spacelike asymptotically flat initial data (for the SCC application); Upper-bound formulation of Price's law (not the sharp lower bound)

**Conclusion type.** `theorem`

**Sources.** SRC-061, SRC-056, SRC-057

**Scope caveats.** Matter model is scalar + optional Maxwell; not vacuum.; Provides the decay input that turns Dafermos 2005 into an unconditional statement for compactly supported scalar hair.; Third primary source (with SRC-056 and SRC-021) naming 'Christodoulou's C^0 formulation'.

**Does not imply.** Does not prove SCC or its failure by itself; it is an input.; Does not apply to vacuum without symmetry.

**Unresolved.** The sharp lower-bound (genericity) Price law is treated in later works (e.g. Luk-Oh Part II, SRC-058).

**Falsifiers.**

- Find an error in the decay estimates (none found; widely used).
- Show the upper bound is too weak to imply the mass-inflation input for the stated data class.

## T-517 — Chrusciel-Isenberg-Moncrief 1990: SCC in polarized Gowdy spacetimes (open dense inextendibility) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** In the space of Cauchy data for polarized Gowdy spacetimes there is an open dense subset for which the maximal globally hyperbolic development is inextendible; among the extendible polarized Gowdy spacetimes, some admit countably infinitely many inequivalent classes of extensions, and a polarized Gowdy spacetime (T^3 or S^2 x S^1) can be extended as a solution of the Einstein equations with the Gowdy isometries across a compact Cauchy horizon only if it is analytic.

**Assumptions.** Polarized Gowdy symmetry; Vacuum Einstein equations; Compact spatial topology (T^3 or S^2 x S^1); Extension class: solutions preserving the Gowdy isometries; Analyticity for the extendibility-across-a-compact-Cauchy-horizon statement

**Conclusion type.** `theorem`

**Sources.** SRC-069, SRC-059

**Scope caveats.** Symmetric (polarized Gowdy) and spatially compact: not asymptotically flat, not generic vacuum.; The extension notion is restricted to solutions preserving the Gowdy isometries; a larger extension class could change the verdict.; Non-analytic extendible examples are excluded in the stated isometry-preserving class.

**Does not imply.** Does not prove SCC for asymptotically flat vacuum data.; Does not decide the C^0 vs C^2 formulation (the extension class is restricted by symmetry).

**Unresolved.** Relation to the later Ringstrom T^3-Gowdy theorem (SRC-059, statement not yet verified); the modern result likely supersedes the genericity statement for T^3.; Exact definition of 'inextendible' (C^0? analytic? isometry-preserving?) in the 1990 paper.

**Falsifiers.**

- Construct a non-analytic polarized Gowdy spacetime extendible across a compact Cauchy horizon while preserving the Gowdy isometries, contradicting the theorem.
- Show the open dense subset is empty.

## T-518 — Luk-Sbierski 2016: conditional instability of the Kerr Cauchy horizon for linear waves [accepted]

**Evidence level (derived).** `preprint`

**Exact statement.** A large class of smooth solutions of the linear wave equation on subextremal rotating Kerr spacetimes that are regular and decaying along the event horizon become singular at the Cauchy horizon: assuming appropriate upper and lower bounds on the energy along the event horizon, the solution has infinite non-degenerate energy on any spacelike hypersurface intersecting the Cauchy horizon transversally. The assumed bounds are conjectured to hold for solutions from generic smooth compactly supported initial data.

**Assumptions.** Fixed subextremal rotating Kerr background; Linear wave equation; Upper and lower energy bounds along the event horizon (assumed, conjectured generic)

**Conclusion type.** `conditional_theorem`

**Sources.** SRC-066, SRC-051

**Scope caveats.** Linear equation on a fixed background.; Conditional in 2016; later works (Ma-Zhang 2023, SRC-051) provide a proof of generic H^1_loc-inextendibility.; Matter: linear scalar waves, not vacuum perturbations.

**Does not imply.** Does not prove nonlinear instability of the Kerr Cauchy horizon.; Does not decide C^0 vs C^2 formulations.

**Unresolved.** Journal reference (J. Funct. Anal. 271 (2016) 2189-2235) not machine-confirmed on the arXiv record.

**Falsifiers.**

- Show the energy bounds fail for an open set of data, which would restrict the theorem to a non-generic class.

## T-519 — Rossetti 2025: C^0 extensions and L^2 Christoffel / H^1 extensions for charged massive KG on RN-dS [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For the spherically symmetric Einstein-Maxwell-charged-Klein-Gordon system with positive cosmological constant in a characteristic initial value problem whose outgoing data approach a fixed subextremal Reissner-Nordstrom-de Sitter solution with an exponential Price-law upper bound for the charged scalar field: a Cauchy horizon CH^+ exists; there are C^0 spacetime extensions beyond CH^+; and if the scalar field decays sufficiently fast along the event horizon (a no-mass-inflation scenario that includes near-extremal solutions), the renormalized Hawking mass remains bounded and the spacetime extends across the Cauchy horizon with continuous metric, Christoffel symbols in L^2_loc, and scalar field in H^1_loc. The results reveal a potential failure of the Christodoulou-Chrusciel version of SCC in spherical symmetry.

**Assumptions.** Spherical symmetry; characteristic initial data on an outgoing null hypersurface (event horizon); Einstein-Maxwell-charged-Klein-Gordon system with Lambda > 0; Subextremal RN-dS asymptotic reference; exponential Price-law upper bound for the charged scalar; Fast-decay/no-mass-inflation regime for the stronger extension conclusion

**Conclusion type.** `theorem`

**Sources.** SRC-070, SRC-029, SRC-028

**Scope caveats.** Matter model is charged massive Klein-Gordon with Lambda > 0; NOT vacuum and NOT asymptotically flat.; Extends the known parameter range for preventing mass inflation up to the threshold suggested by Costa-Franzen and Hintz-Vasy.; The phrase 'potential failure of the Christodoulou-Chrusciel version' is the author's; the version itself still lacks an identified defining primary text in this ledger (D-004).

**Does not imply.** Does not prove SCC failure in vacuum.; Does not decide the C^2 formulation.

**Unresolved.** Exact topology/genericity quantification of the 'large set' of initial data.; The defining Chrusciel reference for the version named.

**Falsifiers.**

- Show the extensions fail to be solutions in the stated regularity (continuous metric, L^2 Christoffel, H^1 scalar).
- Show mass inflation occurs on an open set of the claimed fast-decay regime, contradicting the bounded-mass conclusion.

## T-520 — Ringstrom 2009: C^2 strong cosmic censorship for T^3-Gowdy spacetimes (open in C^1, dense in C^infinity) [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For T^3-Gowdy symmetric vacuum spacetimes, the set of initial data whose maximal globally hyperbolic development is C^2-inextendible is open in a C^1 topology and dense in a C^infinity topology; for these solutions every causal geodesic is either complete or has unbounded Kretschmann scalar along it. The 2009 Annals paper proves the density statement (the openness and the C^2-inextendibility properties were established in a previous paper by the same author).

**Assumptions.** T^3-Gowdy symmetry; Vacuum Einstein equations; Compact spatial topology T^3; Genericity: open in C^1-topology and dense in C^infinity-topology

**Conclusion type.** `theorem`

**Sources.** SRC-059, SRC-071

**Scope caveats.** Symmetric (Gowdy), spatially compact class: NOT asymptotically flat and NOT generic vacuum.; The 2009 paper's contribution is the density statement; the C^2-inextendibility and openness come from the author's previous paper (not yet individually verified in this ledger).; Abstract evidence is an OpenAlex machine reconstruction with bracketed gaps (SRC-071); exact statement still needs the published page.

**Does not imply.** Does not prove C^2 SCC in vacuum without symmetry, nor in asymptotically flat settings.; Does not decide the C^0 formulation.

**Unresolved.** Verify the 'previous paper' that supplies openness and C^2-inextendibility (likely Ringstrom 2008).; Verify the exact topology names and the theorem numbering from the published article.

**Falsifiers.**

- Construct T^3-Gowdy data in the claimed open set whose MGHD admits a C^2 extension, contradicting C^2-inextendibility.
- Show the dense set is not dense in the stated topology.

## T-521 — Dafermos 2003: open set of spherical EM-scalar characteristic data with continuous extension across a curvature-blow-up boundary [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** For a trapped characteristic initial value problem for the spherically symmetric Einstein-Maxwell-scalar field equations, there is an open set of initial data whose closure contains Reissner-Nordstrom data such that the future boundary of the maximal domain of development is a light-like surface along which the curvature blows up, and yet the metric can be continuously extended beyond it.

**Assumptions.** Spherical symmetry; Einstein-Maxwell-scalar field equations; Characteristic initial data; open set whose closure contains RN data

**Conclusion type.** `theorem`

**Sources.** SRC-020, SRC-060, SRC-072, SRC-056

**Scope caveats.** Abstract evidence is an OpenAlex machine reconstruction (SRC-072), anchored by Crossref metadata (SRC-060) and the follow-up paper's restatement (SRC-056).; Matter model is EM-scalar; not vacuum.; This is the pre-cursor of the mass-inflation result T-501; the 2005 paper adds the Hawking-mass blow-up and the C^1 inextendibility.

**Does not imply.** Does not imply C^0 SCC failure for vacuum.; Does not establish C^1 inextendibility (that is T-501).

**Unresolved.** Exact topology of the open set and the meaning of 'trapped characteristic initial value problem' from the full text.

**Falsifiers.**

- Find an error in the extension construction, or show the boundary curvature does not blow up.

## T-522 — Guo-Hadzic-Jang 2023: asymptotically flat isolated naked singularity in the Einstein-Euler system from smooth data [accepted]

**Evidence level (derived).** `peer-reviewed`

**Exact statement.** The radially symmetric Einstein-Euler system admits asymptotically flat spacetimes with an isolated naked singularity formed dynamically from smooth initial data: the relativistic Larson-Penston self-similar solutions are constructed rigorously and flattened in double-null gauge to obtain an asymptotically flat spacetime with an isolated naked singularity.

**Assumptions.** Radial symmetry; Einstein-Euler (perfect fluid) system; Self-similar relativistic Larson-Penston profile; flattening in double-null gauge; Smooth initial data

**Conclusion type.** `counterexample`

**Sources.** SRC-074

**Scope caveats.** Matter model is a perfect fluid (Einstein-Euler), NOT scalar field and NOT vacuum.; Isolated naked singularity; visibility and genericity are not claimed.; Do not cite as a vacuum or scalar-field result.

**Does not imply.** Does not refute generic WCC in any class.; Does not transfer to vacuum.

**Unresolved.** Whether the family sits in an open set of data for the Einstein-Euler system.

**Falsifiers.**

- Find a gap in the self-similar construction or in the flattening to asymptotic flatness.
- Show the singularity is not visible from infinity under the paper's definition.

