# Falsifier matrix (WCC/SCC)

Generated 2026-09-12T00:39:11+08:00 by `tools/build_literature.py` from `theorems/*.jsonl`.

Every content-verified entry carries at least one explicit falsifier. A falsifier is an
observable mathematical outcome that would kill the claim as stated.

## AF-WCC-VAC-GEN

*Asymptotically flat vacuum, weak cosmic censorship, generic data (F1 schema)*

### D-001 — Weak cosmic censorship (WCC), statement of record [verified]

- Statement (exact scope): Generically, all singularities in General Relativity arising from regular asymptotically flat initial data should have a complete future null infinity.
- Assumptions: Einstein field equations (stated for asymptotically flat initial data); A genericity notion must be supplied separately (topology on the data space); the conjecture as quoted does not fix it; Regular initial data
- Conclusion type: `open_problem`
- **Falsifier:** Construct a generic family (open set, or positive measure in an explicitly fixed topology) of asymptotically flat initial data satisfying the constraints whose maximal globally hyperbolic development has incomplete future null infinity.
- **Falsifier:** Prove that no such genericity notion can make the conjecture true while keeping the known non-generic naked-singularity examples excluded.

### T-201 — Christodoulou 2009: trapped-surface formation from short-pulse vacuum data [verified]

- Statement (exact scope): For the Einstein vacuum equations in 3+1 dimensions with no symmetry assumptions, there is an open set of regular initial conditions on an outgoing null hypersurface, of short-pulse type, whose future development forms a trapped surface; the theorems are the first long-time dynamics result for data not confined to a small neighbourhood of Minkowski data.
- Assumptions: Vacuum Einstein equations; No symmetry assumed; Characteristic initial data on an outgoing null hypersurface plus incoming Minkowski data; Short-pulse (large-amplitude, small-width) incoming gravitational waves
- Conclusion type: `theorem`
- **Falsifier:** Find an error in the short-pulse mechanism (no retraction found in the verified set).
- **Falsifier:** Show the trapped surface forms but the solution still has incomplete I+ (would decouple the two notions and change the WCC evidence map).

### T-202 — Klainerman-Rodnianski 2012: simpler trapped-surface formation, enlarged data set [verified]

- Statement (exact scope): A simpler proof of finite trapped-surface formation in vacuum, enlarging the admissible set of initial conditions of Christodoulou's short-pulse result and relaxing the propagation estimates, while reducing the number of derivatives of the curvature needed from two to one.
- Assumptions: Vacuum Einstein equations; Characteristic initial data; finite problem (initial outgoing null hypersurface); No symmetry assumptions
- Conclusion type: `theorem`
- **Falsifier:** Locate an error in the relaxed estimates (no retraction found).
- **Falsifier:** Show the enlarged class fails to contain Christodoulou's, which would contradict the stated comparison.

### T-203 — Li-Yu 2015: complete AF vacuum Cauchy data free of trapped surfaces evolving to a trapped surface [verified]

- Statement (exact scope): There exists complete, asymptotically flat vacuum Cauchy initial data, free of trapped surfaces, whose future development must admit a trapped surface; the data equal a constant-time Minkowski slice inside and a constant-time Kerr slice outside.
- Assumptions: Vacuum Einstein constraint equations; Complete asymptotically flat Cauchy data; Gluing construction using Christodoulou's black-hole formation theorem and Corvino-Schoen gluing
- Conclusion type: `theorem`
- **Falsifier:** Find a gap in the gluing argument (no retraction found).
- **Falsifier:** Show the resulting development fails to be asymptotically flat, which would break the AF class binding.

### T-204 — DHRT 2021: nonlinear stability of Schwarzschild with complete future null infinity [verified]

- Statement (exact scope): General vacuum initial data with no symmetry, sufficiently close to Schwarzschild data and constrained to a teleologically constructed codimension-3 submanifold of moduli space, evolve to a vacuum spacetime that (i) possesses a complete future null infinity I+ whose past is bounded by a regular future-complete event horizon, (ii) remains close to Schwarzschild in the exterior, and (iii) asymptotes back to a member of the Schwarzschild family.
- Assumptions: Einstein vacuum equations, no symmetry; Initial data sufficiently close to Schwarzschild; Data constrained to a codimension-3 submanifold of moduli space (teleologically constructed)
- Conclusion type: `stability_result`
- **Falsifier:** Find an error in the 513-page preprint (no retraction found).
- **Falsifier:** Show the submanifold restriction is empty, making the theorem vacuous.

### T-205 — Klainerman-Szeftel 2020: nonlinear stability of Schwarzschild under polarized perturbations [verified]

- Statement (exact scope): Nonlinear stability of the Schwarzschild spacetime under axially symmetric polarized perturbations: solutions of the Einstein vacuum equations for asymptotically flat 1+3-dimensional Lorentzian metrics admitting a hypersurface-orthogonal spacelike Killing field with closed orbits.
- Assumptions: Einstein vacuum equations; Axisymmetric polarized perturbations (hypersurface-orthogonal spacelike Killing field with closed orbits)
- Conclusion type: `stability_result`
- **Falsifier:** Find an error in the proof (no retraction found).
- **Falsifier:** Show the polarized class does not contain a neighbourhood of Schwarzschild within its symmetry class, contradicting stability.

### T-206 — GKS 2022: nonlinear stability of slowly rotating Kerr [verified]

- Statement (exact scope): The nonlinear stability of the Kerr family for small angular momentum (|a|/m << 1) is proved; the paper completes the proof of the Main Theorem of the GKS programme by supplying the nonlinear wave estimates.
- Assumptions: Einstein vacuum equations; Slowly rotating Kerr: |a|/m << 1; Small perturbations of Kerr data (as set up in the GKS series)
- Conclusion type: `stability_result`
- **Falsifier:** Find an error in the GKS series (no retraction found).
- **Falsifier:** Show the small-|a| restriction cannot be removed, which would restrict the SCC-failure conclusion to slowly rotating Kerr.

### T-208 — Rodnianski-Shlapentokh-Rothman 2023: vacuum naked-singularity exterior solution [verified]

- Statement (exact scope): There exist solutions of the 3+1-dimensional Einstein vacuum equations corresponding to the exterior region of a naked singularity, constructed via a new type of self-similarity and a geometric twisting phenomenon.
- Assumptions: Einstein vacuum equations in 3+1 dimensions; Self-similar (twisted) ansatz; The construction gives the exterior region; the full maximal development requires gluing to an interior solution
- Conclusion type: `counterexample`
- **Falsifier:** Find an error in the self-similar construction.
- **Falsifier:** Show the exterior cannot be glued to any interior solution satisfying the vacuum equations, which would invalidate the naked-singularity interpretation.
- **Falsifier:** Show the resulting spacetime is not the maximal development of regular AF data.

### T-209 — Shlapentokh-Rothman 2022: vacuum naked-singularity interior solution and gluing [provisional]

- Statement (exact scope): There exist solutions of the 3+1-dimensional Einstein vacuum equations corresponding to the interior region of a naked singularity, and the interior and exterior solutions can be glued to produce a naked singularity.
- Assumptions: Einstein vacuum equations in 3+1 dimensions; Self-similar construction from the exterior paper; Gluing of interior and exterior across a null boundary
- Conclusion type: `counterexample`
- **Falsifier:** Find a gap in the gluing construction.
- **Falsifier:** Show the resulting maximal development is extendible or not AF, changing the counterexample status.

### T-515 — Kerr stability status as of 2026-09: full-subextremal nonlinear stability CLAIMED in a 2026 preprint; linear stability peer-reviewed for the full range [verified]

- Statement (exact scope): Status of the Kerr exterior stability antecedent: (a) Hintz (arXiv:2606.28253, 339 pp, Jun/Aug 2026) CLAIMS global nonlinear stability of Kerr in the full subextremal range, with companions on constraint damping (arXiv:2606.27658) and tame estimates (arXiv:2606.28008); (b) earlier unconditional nonlinear stability was established in preprints for small angular momentum |a|/m << 1 (Klainerman-Szeftel arXiv:2104.11857; GKS arXiv:2205.14808); (c) unconditional LINEAR stability is proved for the full subextremal range (Hafner-Hintz-Vasy arXiv:2506.21183, 2025); (d) for Lambda > 0, nonlinear stability of Kerr-de Sitter in the full subextremal range is conditional on mode stability (Hintz-Petersen-Vasy arXiv:2508.06620, 2025); (e) future event horizons in the nonlinear-stability spacetimes are smooth (Chen-Klainerman arXiv:2409.05700, 2024).
- Assumptions: Search performed 2026-09-11/12 via arXiv API (au:Klainerman AND ti:Kerr; ti:'stability of Kerr', sorted by date) and earlier INSPIRE/arXiv queries; Status claim, not a mathematical theorem
- Conclusion type: `open_problem`
- **Falsifier:** Find an error in arXiv:2606.28253 or its companions (would downgrade).
- **Falsifier:** Locate a peer-reviewed full-subextremal nonlinear stability proof (would upgrade clause (a)).

### T-528 — Hintz 2026: nonlinear stability of subextremal Kerr black holes in the full subextremal range [verified]

- Statement (exact scope): Spacetimes evolving from initial data close to those of a subextremal Kerr black hole as solutions of the Einstein vacuum equation Ric(g)=0 settle down to a nearby member of the Kerr family at rate O(t_*^{-2-eps}) in spatially compact regions; the initial data are required to have an arbitrary finite expansion in r^{-z}(log r)^k, z>1, plus an O(r^{-3-eps_0}) remainder.
- Assumptions: Einstein vacuum equations; Initial data close to a subextremal Kerr black hole with the stated finite asymptotic expansion and decay; Generalized wave map gauge with finite-dimensional gauge source terms; nonlinear Nash-Moser iteration
- Conclusion type: `stability_result`
- **Falsifier:** Find an error in the 339-page preprint or its companions.
- **Falsifier:** Show the required initial-data class is empty or the decay rate is not achieved.

## AF-SCC-C2-VAC-GEN

*Asymptotically flat vacuum, SCC, C^2-inextendibility of the MGHD, generic data (F2a schema)*

### D-003 — C^2 (and C^k) inextendibility formulation of SCC [verified]

- Statement (exact scope): Strong cosmic censorship in C^2 form: the maximal globally hyperbolic development is future-inextendible as a Lorentzian manifold whose metric is twice continuously differentiable, for generic initial data.
- Assumptions: MGHD fixed.; Extension = non-trivial isometric embedding into a larger C^2 Lorentzian manifold.; Genericity supplied separately.
- Conclusion type: `open_problem`
- **Falsifier:** Construct generic data whose MGHD admits a C^2 isometric extension across the Cauchy horizon (for the RNdS model with smooth data, Dias-Reall-Santos report exactly this in the linear coupled setting).
- **Falsifier:** Exhibit a C^2-inextendibility proof in the model and show its hypotheses fail on an open set.

### D-004 — 'Christodoulou-Chrusciel version' (continuous metric, L^2 Christoffel symbols) [provisional]

- Statement (exact scope): A version of SCC in which the forbidden extension is one with continuous metric and Christoffel symbols in L^2_loc; failure means the solution can be extended across the Cauchy horizon with continuous metric and square-integrable Christoffel symbols.
- Assumptions: MGHD fixed; Extension class = C^0 metric with connection in L^2_loc
- Conclusion type: `open_problem`
- **Falsifier:** Locate a primary text defining the Christodoulou-Chrusciel version differently, which would make the quoted usage non-standard and force a rename.
- **Falsifier:** Show that L^2_loc Christoffel extensions exist for generic vacuum data, which would decide the version negatively.

### D-005 — Lipschitz / C^{0,1}_loc and L^s_loc-connection formulations (2020-2026) [verified]

- Statement (exact scope): A family of intermediate inextendibility requirements: the MGHD is not extendible as a Lorentzian manifold in a class where the metric is Lipschitz (C^{0,1}_loc), or where the metric is continuous and the Christoffel symbols lie in L^s_loc for s>1.
- Assumptions: MGHD fixed; Extension class fixed by the exponent s or by Lipschitz regularity of the metric
- Conclusion type: `open_problem`
- **Falsifier:** Produce a Lipschitz extension of a Kerr Cauchy horizon for generic data, which would falsify the Lipschitz version.
- **Falsifier:** Show the L^s_loc blow-up condition of Cameron-Sbierski 2026 fails on an open set of spherical EM-scalar data.

### T-303 — Luk 2018: weak null singularities in vacuum with C^0 extension and non-L^2 connection [verified]

- Statement (exact scope): There is a class of spacetimes without symmetry satisfying the vacuum Einstein equations with singular boundaries on two null hypersurfaces intersecting in the future on a 2-sphere; the metric extends continuously beyond the singularities while the Christoffel symbols fail to be square integrable in a neighbourhood of any point of the singular boundaries. The construction is stable in a suitable sense.
- Assumptions: Einstein vacuum equations, no symmetry; Characteristic data with singular boundaries on two null hypersurfaces; The construction is of impulsive-wave type (Luk-Rodnianski lineage)
- Conclusion type: `theorem`
- **Falsifier:** Find an error in the construction.
- **Falsifier:** Show the singular boundary is actually C^1-extendible, contradicting the non-square-integrability of the connection.

### T-305 — Gurriaran 2026: Lipschitz-inextendibility of the Kerr Cauchy horizon near i_+ [provisional]

- Statement (exact scope): For solutions of the Einstein vacuum equations arising from smooth data on a hypersurface slightly inside a dynamical black hole settling down to a subextremal Kerr black hole and satisfying a precise nonlinear Price's-law-type estimate (expected to hold generically), the maximal globally hyperbolic development admits a non-trivial piece of future null boundary (the Cauchy horizon) emanating from timelike infinity i_+, across which the spacetime metric is Lipschitz-inextendible; this yields a Lipschitz version of SCC for Kerr near timelike infinity under that assumption.
- Assumptions: Einstein vacuum equations, no symmetry; Data slightly inside a dynamical black hole settling to subextremal Kerr; Nonlinear Price's-law-type estimate assumed (expected generically, not proved); Region near timelike infinity only
- Conclusion type: `conditional_theorem`
- **Falsifier:** Show the Price-law estimate fails on an open set of data, making the conditional result vacuous there.
- **Falsifier:** Construct a Lipschitz extension of the Kerr Cauchy horizon near i_+, which would refute the theorem.

### T-401 — Status of AF-SCC-C2-VAC-GEN: no primary-source theorem located for generic asymptotically flat vacuum data [provisional]

- Statement (exact scope): Status of AF-SCC-C2-VAC-GEN at 2026-09-11: the C^2 formulation is (i) proved for model classes (Luk-Oh T-514: spherical EM-scalar two-ended AF), (ii) proved for T^3-Gowdy vacuum (Ringstrom T-520), and (iii) NOW covered for generic rotating vacuum black-hole interiors at PREPRINT level: Luk-Sbierski 2026 (T-526) prove the metric is not Lipschitz-extendible across the forming weak null singularity, and non-Lipschitz-extendibility implies non-C^2-extendibility by regularity inclusion. No peer-reviewed theorem proving C^2-future-inextendibility for generic asymptotically flat vacuum Cauchy data was located.
- Assumptions: Scope of the search: arXiv API queries ('strong cosmic censorship', 'inextendibility'+'Cauchy horizon', 'C^2-inextendibility'+Kerr, 'nonlinear stability'+Kerr), INSPIRE title queries, Crossref, on 2026-09-11/12; The claim is about the state of the literature, not a proof of impossibility
- Conclusion type: `open_problem`
- **Falsifier:** Locate a peer-reviewed C^2-inextendibility theorem for generic AF vacuum Cauchy data (promote); or find an error in T-526/T-527 (demote).

### T-402 — Dafermos-Luk revised SCC picture: C^0-extendible but generically C^2-singular (weak null) Cauchy horizons [verified]

- Statement (exact scope): The Cauchy horizons arising in dynamical vacuum black holes that are C^0-extendible across a non-trivial piece are generically singular in an essential way, representing weak null singularities; hence a revised version of strong cosmic censorship (forbidding the relevant higher-regularity extension) is expected to hold.
- Assumptions: Same setting as T-301; 'Generically singular' is the authors' interpretation of the proof, stated in the abstract, not a theorem with a quantified genericity notion
- Conclusion type: `open_problem`
- **Falsifier:** Construct generic Kerr-interior data whose Cauchy horizon is C^2-extendible (would kill the revised picture).
- **Falsifier:** Show the weak-null-singularity behaviour is non-generic in the interior-data space.

### D-007 — Genericity quantifier: the standard used by the C^2 SCC proof (open + dense in specified weighted topologies) [verified]

- Statement (exact scope): For the C^2 formulation of strong cosmic censorship in the two-ended asymptotically flat Einstein-Maxwell-real-scalar model, 'generic' is made precise as: the exceptional/good set of Cauchy data is open with respect to a weighted C^1 topology and dense with respect to a weighted C^infinity topology.
- Assumptions: Two-ended asymptotically flat Cauchy data; Einstein-Maxwell-real-scalar system in spherical symmetry; The topologies are weighted (weights fixed in Part II of the cited work)
- Conclusion type: `formal_model`
- **Falsifier:** Show that under this genericity standard the C^2 result becomes vacuous (e.g. the good set is empty or the topology trivial), which would force a different quantifier.
- **Falsifier:** Exhibit two reasonable topologies giving opposite verdicts for the same model, which would show the standard is not canonical.

### T-526 — Luk-Sbierski 2026: formation of a weak null singularity in generic rotating black-hole interiors (C^0 extendible, not Lipschitz extendible) [verified]

- Statement (exact scope): Given a characteristic initial value problem with smooth data representing a dynamical event horizon settling down to that of Kerr in the subextremal, strictly rotating range with suitable upper and lower bounds, a weak null singularity forms, across which the spacetime metric is continuously extendible but not Lipschitz extendible.
- Assumptions: Einstein vacuum equations, no symmetry; Characteristic initial data on a dynamical event horizon settling to subextremal, strictly rotating Kerr; Suitable upper and lower bounds on the data (Price-law-type; as in the linear instability works); Not full asymptotically flat Cauchy data: this is a characteristic interior problem
- Conclusion type: `theorem`
- **Falsifier:** Construct a Lipschitz extension across the weak null singularity, contradicting the main theorem.
- **Falsifier:** Find a gap in the dynamical-Teukolsky stability argument.
- **Falsifier:** Show the required upper/lower bounds fail for generic data.

### T-527 — Sbierski 2024/2025: C^{0,1}_loc-inextendibility of weak null singularities from curvature blow-up, no symmetry [verified]

- Statement (exact scope): Weak null singularities are C^{0,1}_loc-inextendible without any symmetry assumptions, via a new strategy inferring C^{0,1}_loc-inextendibility from the blow-up of curvature. The assumed blow-up is expected to hold for weak null singularities in the interior of generic rotating black holes, so the result is expected to contribute directly to the C^{0,1}_loc formulation of SCC in a neighbourhood of subextremal Kerr.
- Assumptions: A curvature blow-up condition at the weak null singularity (the theorem's hypothesis); No symmetry assumptions
- Conclusion type: `theorem`
- **Falsifier:** Construct a Lipschitz extension of a weak null singularity with curvature blow-up.
- **Falsifier:** Show the curvature blow-up hypothesis fails for generic rotating interiors.

## AF-SCC-C0-VAC-GEN

*Asymptotically flat vacuum, SCC, C^0-inextendibility of the MGHD, generic data (F2b schema)*

### D-002 — C^0-inextendibility formulation of SCC (attribution disputed) [verified]

- Statement (exact scope): Strong cosmic censorship in C^0 form: the maximal Cauchy development is inextendible as a Lorentzian manifold with merely continuous metric across its Cauchy horizon.
- Assumptions: A maximal globally hyperbolic development (MGHD) is fixed.; 'Extension' means a non-trivial isometric embedding into a larger C^0 Lorentzian manifold (the embedding may be required to be C^0 or smoother; formulations differ).; Genericity of the initial data must be supplied separately.
- Conclusion type: `open_problem`
- **Falsifier:** Exhibit a generic family of data whose MGHD admits a non-trivial continuous isometric extension (this is exactly what Dafermos-Luk produce for Kerr-like interior data, conditional on Kerr exterior stability).
- **Falsifier:** Show the formulation is vacuous because every MGHD has a continuous extension.

### D-004 — 'Christodoulou-Chrusciel version' (continuous metric, L^2 Christoffel symbols) [provisional]

- Statement (exact scope): A version of SCC in which the forbidden extension is one with continuous metric and Christoffel symbols in L^2_loc; failure means the solution can be extended across the Cauchy horizon with continuous metric and square-integrable Christoffel symbols.
- Assumptions: MGHD fixed; Extension class = C^0 metric with connection in L^2_loc
- Conclusion type: `open_problem`
- **Falsifier:** Locate a primary text defining the Christodoulou-Chrusciel version differently, which would make the quoted usage non-standard and force a rename.
- **Falsifier:** Show that L^2_loc Christoffel extensions exist for generic vacuum data, which would decide the version negatively.

### D-005 — Lipschitz / C^{0,1}_loc and L^s_loc-connection formulations (2020-2026) [verified]

- Statement (exact scope): A family of intermediate inextendibility requirements: the MGHD is not extendible as a Lorentzian manifold in a class where the metric is Lipschitz (C^{0,1}_loc), or where the metric is continuous and the Christoffel symbols lie in L^s_loc for s>1.
- Assumptions: MGHD fixed; Extension class fixed by the exponent s or by Lipschitz regularity of the metric
- Conclusion type: `open_problem`
- **Falsifier:** Produce a Lipschitz extension of a Kerr Cauchy horizon for generic data, which would falsify the Lipschitz version.
- **Falsifier:** Show the L^s_loc blow-up condition of Cameron-Sbierski 2026 fails on an open set of spherical EM-scalar data.

### T-301 — Dafermos-Luk 2025: C^0-stability of the Kerr Cauchy horizon (conditional refutation of C^0 SCC) [verified]

- Statement (exact scope): For Cauchy data for the Einstein vacuum equations posed on a hypersurface already inside the black-hole interior (representing the geometry just inside the event horizon), the maximal Cauchy evolution can be extended across a non-trivial piece of Cauchy horizon as a Lorentzian manifold with continuous metric. Moreover, if the exterior region of the Kerr family is dynamically stable, then the C^0-inextendibility formulation of strong cosmic censorship is false.
- Assumptions: Einstein vacuum equations, no symmetry; Cauchy data defined on a hypersurface already within the black-hole interior; Data represent the expected geometry just inside the event horizon; The conditional statement requires dynamical stability of the Kerr exterior
- Conclusion type: `conditional_theorem`
- **Falsifier:** Prove that generic Kerr interiors admit no continuous extension across the Cauchy horizon (would refute the C^0-stability theorem).
- **Falsifier:** Show that the constructed extension is not an extension of the maximal development (e.g. it fails the vacuum equations or isometric embedding conditions).
- **Falsifier:** Show Kerr exterior stability fails, which would leave the conditional statement with a false antecedent (the C^0-stability theorem itself would survive).

### T-302 — Sbierski 2018: C^0-inextendibility of the maximal analytic Schwarzschild spacetime [verified]

- Statement (exact scope): The maximal analytic Schwarzschild spacetime is inextendible as a Lorentzian manifold with a continuous metric (stronger than the classical statement that it is inextendible as a C^2 Lorentzian manifold). The obstruction to continuous extension through the curvature singularity is captured by a notion of spacelike diameter of a globally hyperbolic region with merely continuous metric, with a sufficient condition for finiteness.
- Assumptions: Exact Schwarzschild spacetime (maximal analytic extension); Extension = isometric embedding into a larger C^0 Lorentzian manifold; Dimension 3+1
- Conclusion type: `theorem`
- **Falsifier:** Construct a non-trivial continuous isometric extension of the maximal analytic Schwarzschild spacetime (would refute the theorem).
- **Falsifier:** Find a gap in the spacelike-diameter argument (the method has since been adapted by others, e.g. SRC-007/008/009/049, suggesting acceptance).

### T-303 — Luk 2018: weak null singularities in vacuum with C^0 extension and non-L^2 connection [verified]

- Statement (exact scope): There is a class of spacetimes without symmetry satisfying the vacuum Einstein equations with singular boundaries on two null hypersurfaces intersecting in the future on a 2-sphere; the metric extends continuously beyond the singularities while the Christoffel symbols fail to be square integrable in a neighbourhood of any point of the singular boundaries. The construction is stable in a suitable sense.
- Assumptions: Einstein vacuum equations, no symmetry; Characteristic data with singular boundaries on two null hypersurfaces; The construction is of impulsive-wave type (Luk-Rodnianski lineage)
- Conclusion type: `theorem`
- **Falsifier:** Find an error in the construction.
- **Falsifier:** Show the singular boundary is actually C^1-extendible, contradicting the non-square-integrability of the connection.

### T-305 — Gurriaran 2026: Lipschitz-inextendibility of the Kerr Cauchy horizon near i_+ [provisional]

- Statement (exact scope): For solutions of the Einstein vacuum equations arising from smooth data on a hypersurface slightly inside a dynamical black hole settling down to a subextremal Kerr black hole and satisfying a precise nonlinear Price's-law-type estimate (expected to hold generically), the maximal globally hyperbolic development admits a non-trivial piece of future null boundary (the Cauchy horizon) emanating from timelike infinity i_+, across which the spacetime metric is Lipschitz-inextendible; this yields a Lipschitz version of SCC for Kerr near timelike infinity under that assumption.
- Assumptions: Einstein vacuum equations, no symmetry; Data slightly inside a dynamical black hole settling to subextremal Kerr; Nonlinear Price's-law-type estimate assumed (expected generically, not proved); Region near timelike infinity only
- Conclusion type: `conditional_theorem`
- **Falsifier:** Show the Price-law estimate fails on an open set of data, making the conditional result vacuous there.
- **Falsifier:** Construct a Lipschitz extension of the Kerr Cauchy horizon near i_+, which would refute the theorem.

### T-402 — Dafermos-Luk revised SCC picture: C^0-extendible but generically C^2-singular (weak null) Cauchy horizons [verified]

- Statement (exact scope): The Cauchy horizons arising in dynamical vacuum black holes that are C^0-extendible across a non-trivial piece are generically singular in an essential way, representing weak null singularities; hence a revised version of strong cosmic censorship (forbidding the relevant higher-regularity extension) is expected to hold.
- Assumptions: Same setting as T-301; 'Generically singular' is the authors' interpretation of the proof, stated in the abstract, not a theorem with a quantified genericity notion
- Conclusion type: `open_problem`
- **Falsifier:** Construct generic Kerr-interior data whose Cauchy horizon is C^2-extendible (would kill the revised picture).
- **Falsifier:** Show the weak-null-singularity behaviour is non-generic in the interior-data space.

### T-515 — Kerr stability status as of 2026-09: full-subextremal nonlinear stability CLAIMED in a 2026 preprint; linear stability peer-reviewed for the full range [verified]

- Statement (exact scope): Status of the Kerr exterior stability antecedent: (a) Hintz (arXiv:2606.28253, 339 pp, Jun/Aug 2026) CLAIMS global nonlinear stability of Kerr in the full subextremal range, with companions on constraint damping (arXiv:2606.27658) and tame estimates (arXiv:2606.28008); (b) earlier unconditional nonlinear stability was established in preprints for small angular momentum |a|/m << 1 (Klainerman-Szeftel arXiv:2104.11857; GKS arXiv:2205.14808); (c) unconditional LINEAR stability is proved for the full subextremal range (Hafner-Hintz-Vasy arXiv:2506.21183, 2025); (d) for Lambda > 0, nonlinear stability of Kerr-de Sitter in the full subextremal range is conditional on mode stability (Hintz-Petersen-Vasy arXiv:2508.06620, 2025); (e) future event horizons in the nonlinear-stability spacetimes are smooth (Chen-Klainerman arXiv:2409.05700, 2024).
- Assumptions: Search performed 2026-09-11/12 via arXiv API (au:Klainerman AND ti:Kerr; ti:'stability of Kerr', sorted by date) and earlier INSPIRE/arXiv queries; Status claim, not a mathematical theorem
- Conclusion type: `open_problem`
- **Falsifier:** Find an error in arXiv:2606.28253 or its companions (would downgrade).
- **Falsifier:** Locate a peer-reviewed full-subextremal nonlinear stability proof (would upgrade clause (a)).

### T-526 — Luk-Sbierski 2026: formation of a weak null singularity in generic rotating black-hole interiors (C^0 extendible, not Lipschitz extendible) [verified]

- Statement (exact scope): Given a characteristic initial value problem with smooth data representing a dynamical event horizon settling down to that of Kerr in the subextremal, strictly rotating range with suitable upper and lower bounds, a weak null singularity forms, across which the spacetime metric is continuously extendible but not Lipschitz extendible.
- Assumptions: Einstein vacuum equations, no symmetry; Characteristic initial data on a dynamical event horizon settling to subextremal, strictly rotating Kerr; Suitable upper and lower bounds on the data (Price-law-type; as in the linear instability works); Not full asymptotically flat Cauchy data: this is a characteristic interior problem
- Conclusion type: `theorem`
- **Falsifier:** Construct a Lipschitz extension across the weak null singularity, contradicting the main theorem.
- **Falsifier:** Find a gap in the dynamical-Teukolsky stability argument.
- **Falsifier:** Show the required upper/lower bounds fail for generic data.

### T-528 — Hintz 2026: nonlinear stability of subextremal Kerr black holes in the full subextremal range [verified]

- Statement (exact scope): Spacetimes evolving from initial data close to those of a subextremal Kerr black hole as solutions of the Einstein vacuum equation Ric(g)=0 settle down to a nearby member of the Kerr family at rate O(t_*^{-2-eps}) in spatially compact regions; the initial data are required to have an arbitrary finite expansion in r^{-z}(log r)^k, z>1, plus an O(r^{-3-eps_0}) remainder.
- Assumptions: Einstein vacuum equations; Initial data close to a subextremal Kerr black hole with the stated finite asymptotic expansion and decay; Generalized wave map gauge with finite-dimensional gauge source terms; nonlinear Nash-Moser iteration
- Conclusion type: `stability_result`
- **Falsifier:** Find an error in the 339-page preprint or its companions.
- **Falsifier:** Show the required initial-data class is empty or the decay rate is not achieved.

## AF-WCC-SCALAR-SPH

*Asymptotically flat massless scalar field, spherical symmetry, weak cosmic censorship, generic data*

### T-101 — Christodoulou 1999: instability of spherical scalar-field naked singularities (rough class) [provisional]

- Statement (exact scope): For the spherically symmetric Einstein-massless-scalar-field system, the naked-singularity solutions constructed in 1994 are unstable under sufficiently rough perturbations: within a rough functional framework, perturbations of those data lead to black-hole formation rather than a naked singularity.
- Assumptions: Spherical symmetry; Massless scalar field coupled to gravity (Einstein-scalar system); Perturbations measured in a rough functional framework; the precise function space is not fixed by the accessible abstract-level evidence (see unresolved); This is a statement about the 1994 continuously self-similar naked-singularity family
- Conclusion type: `theorem`
- **Falsifier:** Construct perturbations of the 1994 data, rough in the same norm, that remain naked-singularity-forming (would contradict the theorem as scoped).
- **Falsifier:** Show the theorem's quantifier is not 'generic' but only 'there exist arbitrarily small rough perturbations', which would force a weaker ledger statement.

### T-102 — Christodoulou 1994: existence of continuously self-similar spherical scalar naked singularities [provisional]

- Statement (exact scope): There exists a one-parameter family of continuously self-similar C^{1,alpha} solutions of the spherically symmetric Einstein-scalar field equations that form naked singularities.
- Assumptions: Spherical symmetry; Massless scalar field; Continuous self-similarity; C^{1,alpha} regularity of the solutions (alpha small)
- Conclusion type: `theorem`
- **Falsifier:** Find an error in the 1994 construction (no verified claim of this exists in the checked literature).
- **Falsifier:** Show the family fails to be a solution of the Einstein-scalar system (would be a retraction-level event; none found).

### T-103 — Choptuik 1993: critical collapse and the threshold naked singularity [verified]

- Statement (exact scope): Numerical study of spherically symmetric massless-scalar collapse: a critical parameter value p* separates black-hole-forming from dispersing solutions; the strong-field p->p* limit is universal and generates structure on arbitrarily small spatiotemporal scales, and black-hole masses obey a power law with universal exponent gamma ~ 0.37.
- Assumptions: Numerical evidence only; One-parameter families of initial data; Spherical symmetry, massless scalar field
- Conclusion type: `numerical_evidence`
- **Falsifier:** A rigorous computation showing the critical solution is not naked-singular, or that the power law fails outside the tested families.

### T-105 — An 2025: anisotropic apparent horizon censors Christodoulou's naked singularity [verified]

- Statement (exact scope): Employing the Einstein-scalar field system, a tiny anisotropic perturbation from the outgoing characteristic initial data of Christodoulou's naked-singularity solutions leads to an anisotropic apparent horizon that covers and censors the naked singularity; the method proves high co-dimensional nonlinear instability of those solutions.
- Assumptions: Einstein-scalar field system (not vacuum); Initial data = Christodoulou's naked-singularity data plus a small anisotropic perturbation on the outgoing characteristic hypersurface; Perturbations allowed finite BV and C^0 norms for shear and scalar derivative; scale-critical norms may be arbitrarily small
- Conclusion type: `theorem`
- **Falsifier:** Show the perturbed solution still has a naked singularity visible from infinity (would contradict the theorem as scoped).
- **Falsifier:** Show the anisotropic apparent horizon does not form for the stated perturbation class.

### T-106 — An-Wu 2026: non-spherical Einstein-scalar naked singularities with singular inner Cauchy horizon [provisional]

- Statement (exact scope): There exist non-spherically-symmetric solutions of the 3+1-dimensional Einstein-scalar field system with incomplete future null infinity and a singular inner Cauchy horizon, obtained by prescribing non-spherical data along incoming and outgoing null hypersurfaces; the solutions satisfy C^{1,kappa/(1-kappa)+} inextendibility at the inner Cauchy horizon for self-similar parameter kappa in (0,1/3).
- Assumptions: Einstein-scalar field system (not vacuum); Characteristic initial data on two transversely intersecting null hypersurfaces; No symmetry assumed; constructed from a generalisation of Christodoulou's self-similar solution
- Conclusion type: `counterexample`
- **Falsifier:** Find a gap in the global existence/inextendibility proof (preprint, unreviewed).
- **Falsifier:** Show the constructed spacetimes are C^{1,...}-extendible across the inner horizon.

### T-107 — Zheng 2026: nonlinear stability of the self-similar naked singularities in a Holder topology [provisional]

- Statement (exact scope): A one-parameter family of continuously self-similar C^{1,alpha} naked-singularity solutions of the spherically symmetric Einstein-scalar field equations is nonlinearly stable under initial perturbations lying in a small open neighbourhood of the generating data, measured in a localized Holder topology, with perturbations of the same regularity as the background.
- Assumptions: Spherical symmetry; Einstein-scalar field equations; Perturbations in a localized Holder topology, same regularity as the background (C^{1,alpha}); Relies on a companion linearized-stability paper (Singh-Zheng) not yet verified
- Conclusion type: `stability_result`
- **Falsifier:** Find an error in the nonlinear stability proof (preprint).
- **Falsifier:** Show the localized Holder topology is empty/trivial for the constraint equations, which would make the open neighbourhood vacuous.

### T-516 — Dafermos-Rodnianski 2005: Price's law (upper bound) for self-gravitating scalar collapse [verified]

- Statement (exact scope): A well-defined upper-bound formulation of Price's law is proved for the collapse of a self-gravitating scalar field with spherically symmetric initial data, optionally with an additional gravitationally coupled Maxwell field; the result supplies the decay input assumed in the interior analysis of charged black holes, and hence applies to the strong cosmic censorship conjecture for the Einstein-Maxwell-real-scalar system with complete spacelike asymptotically flat spherically symmetric initial data, where under Christodoulou's C^0 formulation the conjecture is proved false.
- Assumptions: Spherical symmetry; Self-gravitating scalar field; optional Maxwell field; Complete spacelike asymptotically flat initial data (for the SCC application); Upper-bound formulation of Price's law (not the sharp lower bound)
- Conclusion type: `theorem`
- **Falsifier:** Find an error in the decay estimates (none found; widely used).
- **Falsifier:** Show the upper bound is too weak to imply the mass-inflation input for the stated data class.

### T-523 — Liu-Li 2018: robust non-contradiction proof of the instability of spherical scalar naked singularities [verified]

- Statement (exact scope): New a priori estimates give a robust (non-contradiction) proof that the naked singularities of a self-gravitating scalar field are unstable in spherical symmetry, so that cosmic censorship holds in that context.
- Assumptions: Spherical symmetry; Self-gravitating massless scalar field; Estimates relaxed relative to Christodoulou 1999 but still sufficient
- Conclusion type: `theorem`
- **Falsifier:** Construct a stable spherical scalar naked singularity in the same function space.

### T-524 — Li-Liu 2022: instability of spherical scalar naked singularities under non-symmetric gravitational perturbations [verified]

- Statement (exact scope): For a characteristic initial value problem of the Einstein-scalar system whose incoming null cone is spherically symmetric with a singular vertex and whose outgoing null cone has no symmetries: arbitrarily fixing the initial scalar field, the set of initial conformal metrics on the outgoing cone for which the maximal future development has no sequence of closed trapped surfaces approaching the singularity is of first category (in the space of continuous shear tensors), while the set for which a closed trapped surface forms before any fixed later incoming cone contains an open and dense subset. Hence the spherical naked singularities are unstable under gravitational perturbations without symmetry.
- Assumptions: Characteristic initial data on two intersecting null cones; Incoming cone spherically symmetric and singular at the vertex; outgoing cone without symmetry; Shear tensors continuous; initial scalar field fixed arbitrarily; Einstein-massless-scalar system
- Conclusion type: `theorem`
- **Falsifier:** Show the censoring set is not open in the stated topology, or exhibit a non-meagre exceptional set.

### T-525 — Singh 2025: approximately self-similar naked singularities require non-generic (fine-tuned) perturbations [verified]

- Statement (exact scope): Stable perturbations of k-self-similar naked singularities of the spherically symmetric Einstein-scalar system exist for the full parameter range k^2 in (0,1/3), yielding dynamical constructions of naked-singularity interior and exterior regions outside exact self-similarity; the perturbations are fine-tuned data that must be consistent with the absence of a blue-shift instability and are therefore non-generic (in particular the scalar perturbation along the past light cone of the singular point vanishes to high order).
- Assumptions: Spherical symmetry; Einstein-massless-scalar system; Self-similar bounds on the background; fine-tuned perturbations in the past light cone of the singularity
- Conclusion type: `stability_result`
- **Falsifier:** Exhibit an open set of data (in a stated topology) satisfying the fine-tuning conditions and retaining the naked singularity, which would make the construction generic.

## Tagged entries (no frozen class_id)

These entries carry ledger_tags and/or informs_classes; they are evidence or context, not class coverage.

### D-006 — [LEAD SYNTHESIS, not a primary theorem] The verdict on SCC/WCC is genericity-class and regularity-class dependent [verified] (tags: DEFINITIONS, SYNTHESIS)

- Statement (exact scope): Across the verified primary literature, changing the topology/regularity class in which initial data are perturbed (smooth vs rough; localized Holder vs BV vs energy space) changes whether naked singularities or Cauchy-horizon extensions are generic, without changing the underlying equations or background solutions.
- Assumptions: Same background solution family; only the perturbation class/topology changes
- **Falsifier:** Prove that two of the cited perturbation classes induce the same genericity verdict for the same background family and observable, which would weaken the claim to model-dependence.
- **Falsifier:** Find a formulation whose verdict is invariant across all reasonable topologies.

### T-104 — Christodoulou 1984: open set of dust data violates cosmic censorship [verified] (tags: DUST, OTHER-MODELS)

- Statement (exact scope): For an open subset of initial density distributions of an inhomogeneous spherically symmetric dust cloud, the first singular event (at the centre of symmetry) is the vertex of infinitely many future null geodesic cones that intersect future null infinity; the light rays are infinitely redshifted.
- Assumptions: Spherically symmetric inhomogeneous dust (not vacuum); Open subset of initial density distributions; Dust energy conditions / standard dust model
- **Falsifier:** Show the singular event is censored in a more careful notion of visibility (e.g. only infinitely redshifted, non-observable radiation), which would demote the counterexample to a weaker 'violation'.

### T-207 — Hintz-Vasy 2018: nonlinear stability of Kerr-de Sitter (Lambda > 0) [verified] (tags: KERR-DE-SITTER, LAMBDA-POSITIVE, OTHER-MODELS)

- Statement (exact scope): Full global non-linear stability of the Kerr-de Sitter family of black holes as solutions of the initial value problem for the Einstein vacuum equations with positive cosmological constant, for small angular momenta and without symmetry assumptions on the initial data.
- Assumptions: Einstein vacuum equations with Lambda > 0; Small angular momenta; No symmetry assumptions
- **Falsifier:** Find an error in the proof (no retraction found).
- **Falsifier:** Show the small-angular-momentum restriction is essential in a way that changes the SCC picture.

### T-304 — Cameron-Sbierski 2026: L^s_loc-connection inextendibility of spherical weak null singularities [provisional] (tags: EM-SCALAR, OTHER-MODELS, PREPRINT, WEAK-NULL)

- Statement (exact scope): Spherically symmetric weak null singularities are inextendible as spherically symmetric Lorentzian manifolds with continuous metric and Christoffel symbols in L^s_loc for s > 1, assuming a blow-up condition on the derivative of the area-radius function transverse to the singularity plus a rigidity result on continuous spherically symmetric extensions. The assumptions are satisfied by Reissner-Nordstrom-Vaidya and by a class of spacetimes arising from small and generic spherically symmetric perturbations of subextremal Reissner-Nordstrom under the Einstein-Maxwell-scalar field system.
- Assumptions: Spherical symmetry of the extension (the theorem is restricted to spherically symmetric extensions); Continuous metric; Christoffel symbols in L^s_loc, s>1; Blow-up condition on the transverse derivative of the area radius; Rigidity of continuous spherically symmetric extensions from Cameron-Sbierski 2025
- **Falsifier:** Construct a spherically symmetric continuous extension with Christoffel symbols in L^s_loc for some s>1 of the RN-Vaidya spacetime (would refute the theorem).
- **Falsifier:** Show the blow-up condition fails for the claimed generic perturbations.

### T-306 — Cameron-Sbierski 2025: continuous extensions are not unique in 1+1 dimensions [provisional] (tags: 1+1-MODEL, C0, OTHER-MODELS, PREPRINT)

- Statement (exact scope): In 1+1-dimensional Lorentzian manifolds admitting a continuous spacetime extension across a null boundary v=0, the C^0-structure of the extension is in general not uniquely determined by continuous extendibility of the metric; however, a local-global relation makes the C^0-structure rigid for strongly spherically symmetric continuous extensions across the Reissner-Nordstrom Cauchy horizon. Continuous extensions with the same C^0-structure but inequivalent C^1-structures are constructed; the construction carries over to weak null singularities in 3+1 dimensions.
- Assumptions: 1+1-dimensional model for the uniqueness analysis; Continuous metric extension across a null boundary; Spherical symmetry for the rigidity statement
- **Falsifier:** Prove uniqueness of continuous extensions for the 3+1 Kerr weak null singularity, contradicting the carry-over claim.

### T-501 — Dafermos 2005: mass inflation for spherical EM-scalar with Price-law data (C^0 extendible, C^1 inextendible) [verified] (tags: EM-SCALAR, MASS-INFLATION, OTHER-MODELS)

- Statement (exact scope): For a spherically symmetric double-characteristic initial value problem for the Einstein-Maxwell-scalar field equations with Price-law decay on the outgoing initial characteristic, the maximal future development has a future boundary over which the spacetime is extendible as a C^0 metric but along which the Hawking mass blows up identically; the spacetime is inextendible as a C^1 metric. Under Christodoulou's C^0 formulation, strong cosmic censorship is false for this system.
- Assumptions: Spherical symmetry; Einstein-Maxwell-(real)-scalar field system; Price-law decay of the data on the outgoing characteristic (widely believed for collapse from AF data); with Dafermos-Rodnianski the result applies to compactly supported scalar hair
- **Falsifier:** Find an error in the mass-inflation argument (none found; the result is widely cited and refined by T-505, T-506).
- **Falsifier:** Show the constructed extension fails to be C^0 across the boundary.

### T-502 — Costa-Girao-Natario-Silva 2017: RNdS scalar field admits continuous extensions with L^2 Christoffel symbols [verified] (tags: EM-SCALAR, LAMBDA-POSITIVE, OTHER-MODELS, RN-DS)

- Statement (exact scope): For spherically symmetric characteristic data for the Einstein-Maxwell-scalar field system with positive cosmological constant whose data on the outgoing null hypersurface is a subextremal Reissner-Nordstrom black-hole event horizon, mass inflation may or may not occur depending on the decay rate; when the mass is controlled there are continuous extensions of the metric across the Cauchy horizon with square-integrable Christoffel symbols, and under slightly stronger conditions there are non-isometric extensions that are classical solutions of the Einstein equations. The results provide evidence against SCC when Lambda > 0.
- Assumptions: Spherical symmetry; characteristic initial data; Einstein-Maxwell-scalar with Lambda > 0; Subextremal RN-dS event-horizon data; Exponential Price-law decay rate as the parameter
- **Falsifier:** Find an error in Parts 1-3 (no retraction found).
- **Falsifier:** Show the constructed extensions are isometric to the original development (then they would be trivial).

### T-503 — Costa-Girao-Natario-Silva 2018: open sets of data violating the Christodoulou-Chrusciel version (Lambda > 0) [verified] (tags: EM-SCALAR, LAMBDA-POSITIVE, OTHER-MODELS, RN-DS)

- Statement (exact scope): For the Einstein-Maxwell-scalar field system with positive cosmological constant in the black-hole interior, assuming an exponential Price law along the event horizon, there are open sets of characteristic data converging exponentially to a reference Reissner-Nordstrom black hole at infinity for which mass inflation may or may not occur depending on the decay rate; in the no-mass-inflation decay regime (and not for the open sets as such) the solution extends across the Cauchy horizon with continuous metric and Christoffel symbols in L^2_loc, violating the Christodoulou-Chrusciel version of strong cosmic censorship.
- Assumptions: Spherical symmetry; characteristic data; Lambda > 0; subextremal RN reference at infinity; Exponential Price law along the event horizon; Open sets of characteristic data
- **Falsifier:** Show the constructed extensions are not solutions of the system in the stated regularity.
- **Falsifier:** Show the data sets are not open in the stated topology.

### T-504 — Luk-Oh 2017: generic linear instability of the RN Cauchy horizon [verified] (tags: LINEAR, OTHER-MODELS, RN)

- Statement (exact scope): On a fixed subextremal Reissner-Nordstrom spacetime with non-vanishing charge, generic smooth and compactly supported initial data on a Cauchy hypersurface give rise to solutions of the linear scalar wave equation with infinite non-degenerate energy near the Cauchy horizon; in particular the solution generically does not belong to W^{1,2}_loc. Price's law decay is generically sharp along the event horizon.
- Assumptions: Fixed subextremal RN background (nonlinear backreaction absent); Linear massless scalar wave equation; Generic smooth compactly supported initial data
- **Falsifier:** Find an error in the energy blow-up proof (no retraction found).
- **Falsifier:** Show the exceptional set is larger than meagre in the stated topology.

### T-505 — Van de Moortel 2020: C^2-inextendibility for spherical EM-Klein-Gordon under expected decay [verified] (tags: C2, EM-KG, OTHER-MODELS)

- Statement (exact scope): For the Einstein-Maxwell-Klein-Gordon system in spherical symmetry, assuming sufficiently slow decay of the charged scalar field on the event horizon, the Cauchy horizon emanating from timelike infinity splits into a dynamical set (Hawking mass blows up) and a static set isometric to a Reissner-Nordstrom Cauchy horizon, and is globally C^2-inextendible; in particular two-ended asymptotically flat spacetimes are C^2-future-inextendible, i.e. C^2 strong cosmic censorship holds for this system under the decay assumption.
- Assumptions: Spherical symmetry; Einstein-Maxwell-Klein-Gordon (charged scalar); Assumption: sufficiently slow decay of the charged scalar field on the event horizon (expected rate); Two-ended (and one-ended near i+) settings
- **Falsifier:** Show the decay assumption fails for an open set of admissible data.
- **Falsifier:** Find a C^2 extension of the constructed spacetimes.

### T-506 — Sbierski 2020: C^{0,1}_loc-inextendibility of spherical weak null singularities [verified] (tags: ACCEPTED-IN-PRESS, EM-SCALAR, OTHER-MODELS, WEAK-NULL)

- Statement (exact scope): Using an unbounded local holonomy, spherically symmetric weak null singularities arising at the Cauchy horizon in black-hole interiors are C^{0,1}_loc-inextendible; the theorem does not presuppose mass inflation and applies to Reissner-Nordstrom-Vaidya and to spacetimes from small generic spherically symmetric perturbations of two-ended subextremal RN data for the Einstein-Maxwell-scalar system, improving the Luk-Oh C^2 formulation to a C^{0,1}_loc formulation.
- Assumptions: Spherical symmetry; Continuous metric (C^{0,1}_loc = locally Lipschitz) extension class; Applies to the stated RN-Vaidya and perturbed RN classes
- **Falsifier:** Construct a locally Lipschitz extension of the relevant weak null singularity (would refute the holonomy argument).

### T-507 — Numerical/QNM cluster: SCC violation in near-extremal RN-dS (2018-2023) [verified] (tags: NUMERICAL, OTHER-MODELS, RN-DS)

- Statement (exact scope): Linear and nonlinear numerical studies of massless scalar fields and of coupled gravitational-electromagnetic perturbations on near-extremal Reissner-Nordstrom-de Sitter backgrounds indicate that generic perturbations from smooth initial data have finite energy at the Cauchy horizon, and for coupled perturbations can be extended through it arbitrarily smoothly; the coincidence of interior and exterior quasinormal frequencies that could have invalidated this conclusion does not occur for RNdS or Kerr-dS.
- Assumptions: Fixed RNdS/Kerr-dS background for the linear results; Near-extremal regime; Numerical computation of quasinormal modes / nonlinear spherical evolution for the nonlinear result
- **Falsifier:** A rigorous computation showing the relevant QNM decay rates differ from the numerics, restoring the blow-up.

### T-508 — Dafermos-Shlapentokh-Rothman 2018: rough data restores blue-shift blow-up on Lambda > 0 black holes [verified] (tags: OTHER-MODELS, RN-DS, ROUGH-DATA)

- Statement (exact scope): For the wave equation on Reissner-Nordstrom-de Sitter and Kerr-Newman-de Sitter spacetimes with Lambda > 0, slightly relaxing the smoothness assumption on initial data yields the analogue of the Christodoulou statement in the affirmative: for generic data in the allowed (rougher) class, local energy blows up at the Cauchy horizon for all subextremal parameter ranges, while the data remain regular enough to ensure stability, decay, boundedness and continuous extendibility beyond the Cauchy horizon.
- Assumptions: Wave equation on fixed RN-dS/KN-dS backgrounds; Lambda > 0; Enlarged (rougher) data class, still regular enough for decay/stability; Two independent proofs: mode construction and time-translation-invariance of scattering maps
- **Falsifier:** Show the rough data class is not preserved by the nonlinear evolution (in the nonlinear setting).
- **Falsifier:** Construct rough generic data with bounded local energy at the Cauchy horizon.

### T-509 — Moncrief-Isenberg: analytic vacuum with compact non-degenerate Cauchy horizon forces symmetry [verified] (tags: ANALYTIC, OTHER-MODELS, SYMMETRY-FORCING)

- Statement (exact scope): An analytic vacuum (or electrovacuum) spacetime containing a compact null hypersurface ruled by closed null generators has a non-trivial Killing symmetry; the non-degenerate such null surfaces are always Cauchy horizons across which the Killing fields change from spacelike (globally hyperbolic regions) to timelike (acausal analytic extensions). The LPB condition can be dropped, and for non-closed generators densely filling a 2-torus (non-ergodic case) the spacetime admits at least two independent commuting Killing fields, one combination horizon-generating.
- Assumptions: Analytic category; Vacuum or electrovacuum Einstein equations; Compact null hypersurface / compact non-degenerate Cauchy horizon; Closed generators (1983/1985) or non-ergodic non-closed generators (2019)
- **Falsifier:** Construct a smooth vacuum spacetime with a compact non-degenerate Cauchy horizon and no Killing symmetry, which would show analyticity is essential.

### T-510 — Luk-Oh-Shlapentokh-Rothman 2022: generic class with C^2-future-inextendibility and conditional mass inflation [verified] (tags: EM-SCALAR, GENERIC-CLASS-G, OTHER-MODELS)

- Statement (exact scope): For the spherically symmetric Einstein-Maxwell-real-scalar field system there is a generic class G of Cauchy data whose maximal globally hyperbolic future developments are C^2-future-inextendible; if a conjectural improved exterior decay result holds, then for data in G the Hawking mass blows up identically on the Cauchy horizon (mass inflation). The scattering-map analysis also gives a new proof of linear instability of the RN Cauchy horizon.
- Assumptions: Spherical symmetry; Einstein-Maxwell-real-scalar; Generic class G of Cauchy data (defined via the earlier Luk-Oh work); Improved exterior decay conjecture for the conditional mass-inflation conclusion
- **Falsifier:** Show class G is not generic in the intended topology.
- **Falsifier:** Construct a C^2 extension for data in G.

### T-511 — Ma-Zhang 2023: precise interior late-time asymptotics and H^1_loc-inextendibility of the Kerr Cauchy horizon (linear) [verified] (tags: KERR, LINEAR, OTHER-MODELS)

- Statement (exact scope): Precise late-time asymptotics are computed for the scalar field in the interior of a non-static subextremal Kerr black hole, giving a new proof of the generic H^1_loc-inextendibility of the Kerr Cauchy horizon against scalar perturbations (first shown by Luk-Sbierski, J. Funct. Anal. 2016).
- Assumptions: Fixed non-static subextremal Kerr background; Linear scalar wave equation; Generic perturbations
- **Falsifier:** Find an error in the asymptotics or in the passage to H^1_loc blow-up.

### T-512 — Chrysostomou et al. 2025: review of SCC formulations and RNdS violations [verified] (tags: FORMULATIONS, REVIEW)

- Statement (exact scope): Several strong cosmic censorship conjectures of varying strengths have been formulated in the rigorous literature; for Kerr-Newman-type black holes, SCC preservation hinges on inextendibility past the Cauchy horizon due to blue-shift instability, while in RNdS the positive cosmological constant invites a competing red-shift effect; the parameter space where SCC violations are consistently observed is illustrated.
- Assumptions: Review-level synthesis
- **Falsifier:** Find an error in the review's taxonomy; then the class dossiers must be corrected.

### T-513 — Strong cosmic censorship in T^3-Gowdy spacetimes (Ringstrom 2009 Annals; metadata verified, statement unresolved) [rejected] (tags: GOWDY, OTHER-MODELS, SUPERSEDED)

- Statement (exact scope): Candidate entry: strong cosmic censorship is proved for T^3-Gowdy symmetric vacuum spacetimes (a spatially compact, symmetric class), cited as H. Ringstrom, 'Strong cosmic censorship in T^3-Gowdy spacetimes', Annals of Mathematics 170(3) (2009) 1181-1240, DOI 10.4007/annals.2009.170.1181 (title, author, volume, pages, year and DOI now verified via Crossref).
- Assumptions: T^3-Gowdy symmetry; Vacuum Einstein equations; Compact spatial topology
- **Falsifier:** If the theorem exists as cited, verify and promote; if the title/venue differ, record the correction rather than silently substituting.

### T-514 — Luk-Oh 2017/2019 two-part proof: C^2 SCC holds and C^0 SCC fails for spherical EM-scalar two-ended AF data [verified] (tags: C2, EM-SCALAR, GENERICITY-BENCHMARK, OTHER-MODELS)

- Statement (exact scope): For the Einstein-Maxwell-(real)-scalar-field system in spherical symmetry with two-ended asymptotically flat admissible Cauchy data: (a) the maximal globally hyperbolic future development always possesses a non-empty Cauchy horizon across which the spacetime is C^0-future-extendible, so the C^0 formulation of SCC is false for this model; (b) for a generic class of such data - open in a weighted C^1 topology and dense in a weighted C^infinity topology - the spacetime is C^2-future-inextendible, proving the C^2 formulation of SCC for this model. Part I proves C^2-inextendibility conditional on an L^2-averaged polynomial lower bound for the scalar field along each event horizon; Part II proves that bound holds for the generic class.
- Assumptions: Einstein-Maxwell-(real)-scalar field system; Spherical symmetry; Two-ended asymptotically flat admissible Cauchy data; Genericity = open in weighted C^1 topology and dense in weighted C^infinity topology (Part II)
- **Falsifier:** Find an error in Part I or Part II (no retraction found).
- **Falsifier:** Show the generic set is not open/dense in the stated topologies, contradicting Part II's main claim.
- **Falsifier:** Construct a C^2 extension for data in the generic class, contradicting Part I.

### T-517 — Chrusciel-Isenberg-Moncrief 1990: SCC in polarized Gowdy spacetimes (open dense inextendibility) [verified] (tags: GOWDY, OTHER-MODELS, POLARIZED)

- Statement (exact scope): In the space of Cauchy data for polarized Gowdy spacetimes there is an open dense subset for which the maximal globally hyperbolic development is inextendible; among the extendible polarized Gowdy spacetimes, some admit countably infinitely many inequivalent classes of extensions, and a polarized Gowdy spacetime (T^3 or S^2 x S^1) can be extended as a solution of the Einstein equations with the Gowdy isometries across a compact Cauchy horizon only if it is analytic.
- Assumptions: Polarized Gowdy symmetry; Vacuum Einstein equations; Compact spatial topology (T^3 or S^2 x S^1); Extension class: solutions preserving the Gowdy isometries; Analyticity for the extendibility-across-a-compact-Cauchy-horizon statement
- **Falsifier:** Construct a non-analytic polarized Gowdy spacetime extendible across a compact Cauchy horizon while preserving the Gowdy isometries, contradicting the theorem.
- **Falsifier:** Show the open dense subset is empty.

### T-518 — Luk-Sbierski 2016: conditional instability of the Kerr Cauchy horizon for linear waves [verified] (tags: KERR, LINEAR, OTHER-MODELS)

- Statement (exact scope): A large class of smooth solutions of the linear wave equation on subextremal rotating Kerr spacetimes that are regular and decaying along the event horizon become singular at the Cauchy horizon: assuming appropriate upper and lower bounds on the energy along the event horizon, the solution has infinite non-degenerate energy on any spacelike hypersurface intersecting the Cauchy horizon transversally. The assumed bounds are conjectured to hold for solutions from generic smooth compactly supported initial data.
- Assumptions: Fixed subextremal rotating Kerr background; Linear wave equation; Upper and lower energy bounds along the event horizon (assumed, conjectured generic)
- **Falsifier:** Show the energy bounds fail for an open set of data, which would restrict the theorem to a non-generic class.

### T-519 — Rossetti 2025: C^0 extensions and L^2 Christoffel / H^1 extensions for charged massive KG on RN-dS [verified] (tags: EM-KG, LAMBDA-POSITIVE, OTHER-MODELS, RN-DS)

- Statement (exact scope): For the spherically symmetric Einstein-Maxwell-charged-Klein-Gordon system with positive cosmological constant in a characteristic initial value problem whose outgoing data approach a fixed subextremal Reissner-Nordstrom-de Sitter solution with an exponential Price-law upper bound for the charged scalar field: a Cauchy horizon CH^+ exists; there are C^0 spacetime extensions beyond CH^+; and if the scalar field decays sufficiently fast along the event horizon (a no-mass-inflation scenario that includes near-extremal solutions), the renormalized Hawking mass remains bounded and the spacetime extends across the Cauchy horizon with continuous metric, Christoffel symbols in L^2_loc, and scalar field in H^1_loc. The results reveal a potential failure of the Christodoulou-Chrusciel version of SCC in spherical symmetry.
- Assumptions: Spherical symmetry; characteristic initial data on an outgoing null hypersurface (event horizon); Einstein-Maxwell-charged-Klein-Gordon system with Lambda > 0; Subextremal RN-dS asymptotic reference; exponential Price-law upper bound for the charged scalar; Fast-decay/no-mass-inflation regime for the stronger extension conclusion
- **Falsifier:** Show the extensions fail to be solutions in the stated regularity (continuous metric, L^2 Christoffel, H^1 scalar).
- **Falsifier:** Show mass inflation occurs on an open set of the claimed fast-decay regime, contradicting the bounded-mass conclusion.

### T-520 — Ringstrom 2009: C^2 strong cosmic censorship for T^3-Gowdy spacetimes (open in C^1, dense in C^infinity) [verified] (tags: C2, GOWDY, OTHER-MODELS)

- Statement (exact scope): For T^3-Gowdy symmetric vacuum spacetimes, the set of initial data whose maximal globally hyperbolic development is C^2-inextendible is open in a C^1 topology and dense in a C^infinity topology; for these solutions every causal geodesic is either complete or has unbounded Kretschmann scalar along it. The 2009 Annals paper proves the density statement (the openness and the C^2-inextendibility properties were established in a previous paper by the same author).
- Assumptions: T^3-Gowdy symmetry; Vacuum Einstein equations; Compact spatial topology T^3; Genericity: open in C^1-topology and dense in C^infinity-topology
- **Falsifier:** Construct T^3-Gowdy data in the claimed open set whose MGHD admits a C^2 extension, contradicting C^2-inextendibility.
- **Falsifier:** Show the dense set is not dense in the stated topology.

### T-521 — Dafermos 2003: open set of spherical EM-scalar characteristic data with continuous extension across a curvature-blow-up boundary [verified] (tags: C0, EM-SCALAR, OPEN-SET, OTHER-MODELS)

- Statement (exact scope): For a trapped characteristic initial value problem for the spherically symmetric Einstein-Maxwell-scalar field equations, there is an open set of initial data whose closure contains Reissner-Nordstrom data such that the future boundary of the maximal domain of development is a light-like surface along which the curvature blows up, and yet the metric can be continuously extended beyond it.
- Assumptions: Spherical symmetry; Einstein-Maxwell-scalar field equations; Characteristic initial data; open set whose closure contains RN data
- **Falsifier:** Find an error in the extension construction, or show the boundary curvature does not blow up.

### D-008 — Maximal globally hyperbolic development (MGHD): existence and uniqueness-up-to-isometry [verified] (tags: DEFINITIONS, MGHD)

- Statement (exact scope): Given any set of initial data for Einstein's equations satisfying the constraint conditions, there exists a development that is maximal in the sense that it is an extension of every other development; these maximal developments form a well-defined class of solutions, and any solution with a Cauchy surface embeds in exactly one such maximal development.
- Assumptions: Initial data satisfying the Einstein constraint equations; Development = solution containing an embedding of the data with the data as a Cauchy surface
- **Falsifier:** Find constraint-satisfying data with two non-isometric maximal developments, contradicting the theorem.

### T-522 — Guo-Hadzic-Jang 2023: asymptotically flat isolated naked singularity in the Einstein-Euler system from smooth data [verified] (tags: EINSTEIN-EULER, NS-CONSTRUCTION, OTHER-MODELS)

- Statement (exact scope): The radially symmetric Einstein-Euler system admits asymptotically flat spacetimes with an isolated naked singularity formed dynamically from smooth initial data: the relativistic Larson-Penston self-similar solutions are constructed rigorously and flattened in double-null gauge to obtain an asymptotically flat spacetime with an isolated naked singularity.
- Assumptions: Radial symmetry; Einstein-Euler (perfect fluid) system; Self-similar relativistic Larson-Penston profile; flattening in double-null gauge; Smooth initial data
- **Falsifier:** Find a gap in the self-similar construction or in the flattening to asymptotic flatness.
- **Falsifier:** Show the singularity is not visible from infinity under the paper's definition.

### D-009 — Background singularity theorems (trapped surface / energy conditions imply geodesic incompleteness) [provisional] (tags: DEFINITIONS, BACKGROUND, SINGULARITY-THEOREMS)

- Statement (exact scope): Classical singularity theorems: a spacetime containing a trapped surface (Penrose 1965) or satisfying suitable energy and causality conditions with a closed or collapsing region (Hawking-Penrose 1970) must be null/timelike geodesically incomplete.
- Assumptions: Einstein's equations with suitable energy conditions; Causality/global-hyperbolicity hypotheses as in the original theorems; Exact statements not extracted from the primary texts in this run
- **Falsifier:** Find a counterexample to the classical theorems (none known) or show the hypotheses fail in the intended applications.

### T-529 — C^0-inextendibility methods in cosmological and warped-product models (outside the four classes) [verified] (tags: OTHER-MODELS, C0-METHODS, COSMOLOGICAL)

- Statement (exact scope): Low-regularity inextendibility methods extend beyond Schwarzschild: the maximal analytic Kasner spacetime, classes of FLRW spacetimes (including axisymmetric extensions of earlier results), and a class of warped-product black-hole spacetimes with compact homogeneous fibres and a curvature singularity are C^0-inextendible.
- Assumptions: Exact/analytic model spacetimes or stated symmetry classes; C^0 metric extensions; Warped-product class: closed, connected, homogeneous, orientable fibre; Kretschmann divergence as r->0
- **Falsifier:** Construct a continuous extension in one of the stated model classes, or show the warp-product assumptions exclude the claimed class.

