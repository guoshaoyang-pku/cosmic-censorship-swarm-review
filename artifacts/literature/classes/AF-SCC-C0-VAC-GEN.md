# AF-SCC-C0-VAC-GEN

*Asymptotically flat vacuum, SCC, C^0-inextendibility of the MGHD, generic data (F2b schema)*

Entries whose statement is about this class: 11 (0 accepted, 11 provisional/unresolved).

## D-002 — C^0-inextendibility formulation of SCC (attribution disputed) [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

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

## D-004 — 'Christodoulou-Chrusciel version' (continuous metric, L^2 Christoffel symbols) [provisional]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** A version of SCC in which the forbidden extension is one with continuous metric and Christoffel symbols in L^2_loc; failure means the solution can be extended across the Cauchy horizon with continuous metric and square-integrable Christoffel symbols.

**Assumptions.** MGHD fixed; Extension class = C^0 metric with connection in L^2_loc

**Conclusion type.** `open_problem`

**Sources.** SRC-029

**Scope caveats.** The name is quoted verbatim from Costa-Girao-Natario-Silva 2018: 'thus violating the Christodoulou-Chrusciel version of strong cosmic censorship'.; The Chrusciel reference intended by that name has not yet been identified in the primary literature; the naming is therefore recorded as a literature usage, not as an established attribution.

**Does not imply.** Not the C^2 formulation (L^2 connection is weaker than C^1, hence much weaker than C^2).; Not the C^0 formulation (which forbids even continuous extensions).

**Unresolved.** Identify the Chrusciel paper that defines this version: candidate SRC-090 is now locator-verified (Chrusciel 1992, Contemp. Math. 132, 235-273, DOI 10.1090/conm/132/1188443) but its content is unread, so it cannot yet be cited as scope evidence.; Check whether 'L^2_loc Christoffel' or 'H^1_loc metric' is the intended class.

**Falsifiers.**

- Locate a primary text defining the Christodoulou-Chrusciel version differently, which would make the quoted usage non-standard and force a rename.
- Show that L^2_loc Christoffel extensions exist for generic vacuum data, which would decide the version negatively.

## D-005 — Lipschitz / C^{0,1}_loc and L^s_loc-connection formulations (2020-2026) [verified]

**Evidence level (derived).** `accepted-in-press` · **L0 verification.** `abstract-read`

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

## T-301 — Dafermos-Luk 2025: C^0-stability of the Kerr Cauchy horizon (conditional refutation of C^0 SCC) [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** For Cauchy data for the Einstein vacuum equations posed on a hypersurface already inside the black-hole interior (representing the geometry just inside the event horizon), the maximal Cauchy evolution can be extended across a non-trivial piece of Cauchy horizon as a Lorentzian manifold with continuous metric. Moreover, if the exterior region of the Kerr family is dynamically stable, then the C^0-inextendibility formulation of strong cosmic censorship is false.

**Assumptions.** Einstein vacuum equations, no symmetry; Cauchy data defined on a hypersurface already within the black-hole interior; Data represent the expected geometry just inside the event horizon; The conditional statement requires dynamical stability of the Kerr exterior

**Conclusion type.** `conditional_theorem`

**Sources.** SRC-004, SRC-006, SRC-040, SRC-037, SRC-062, SRC-063, SRC-065

**Scope caveats.** The paper assumes data already inside the black-hole interior; the authors state that subsequent work will retrieve these assumptions from event-horizon asymptotics to Kerr. That subsequent work was NOT located in the verified set as of 2026-09-11.; The conclusion 'C^0 SCC is false' is conditional on Kerr exterior stability. Verified stability results cover (a) Schwarzschild (DHRT 2021, preprint; codim-3 restriction), (b) polarized perturbations (Klainerman-Szeftel), (c) slowly rotating Kerr |a|/m << 1 (GKS 2022, preprint), and now (d) a 2026 preprint CLAIMS nonlinear stability in the full subextremal range (Hintz, SRC-078; see T-528/T-515).; The paper itself says the resulting C^0-metric Cauchy horizons are 'generically singular in an essential way' (weak null singularities), so the failure is only of the C^0-inextendibility formulation.

**Does not imply.** Does not refute C^2 or Lipschitz formulations of SCC.; Does not settle AF-SCC-C0-VAC-GEN for all generic AF vacuum data, because the data assumptions are interior and the stability input is restricted.; Does not assert that the extension is unique (see T-306).

**Unresolved.** Locate 'The interior of dynamical vacuum black holes II' or equivalent retrieval of the interior-data assumptions (searched, not found).; The full-subextremal antecedent now rests on the 2026 Hintz preprint (SRC-078); peer review pending.; Verify the published Annals version's statement, since the arXiv v1 (2017) predates the 2025 publication.

**Falsifiers.**

- Prove that generic Kerr interiors admit no continuous extension across the Cauchy horizon (would refute the C^0-stability theorem).
- Show that the constructed extension is not an extension of the maximal development (e.g. it fails the vacuum equations or isometric embedding conditions).
- Show Kerr exterior stability fails, which would leave the conditional statement with a false antecedent (the C^0-stability theorem itself would survive).

## T-302 — Sbierski 2018: C^0-inextendibility of the maximal analytic Schwarzschild spacetime [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** The maximal analytic Schwarzschild spacetime is inextendible as a Lorentzian manifold with a continuous metric (stronger than the classical statement that it is inextendible as a C^2 Lorentzian manifold). The obstruction to continuous extension through the curvature singularity is captured by a notion of spacelike diameter of a globally hyperbolic region with merely continuous metric, with a sufficient condition for finiteness.

**Assumptions.** Exact Schwarzschild spacetime (maximal analytic extension); Extension = isometric embedding into a larger C^0 Lorentzian manifold; Dimension 3+1

**Conclusion type.** `theorem`

**Sources.** SRC-005, SRC-006

**Scope caveats.** Scope is the maximal analytic Schwarzschild spacetime, NOT a generic dynamical black hole and NOT the Cauchy-horizon problem. Schwarzschild has no inner horizon; its r=0 singularity is the relevant boundary.; Do NOT cite this as evidence against T-301: Dafermos-Luk concern extension across a Cauchy horizon of a dynamical black hole, a different boundary and a different question.; The C^0-inextendibility question can also be asked for the maximal development of data on a partial Cauchy surface; Sbierski's statement is about the maximal analytic extension.

**Does not imply.** Does not imply C^0 SCC for generic AF vacuum data.; Does not imply that the Cauchy horizon of Kerr is C^0-inextendible (the opposite is proved conditionally in T-301).

**Unresolved.** Journal/volume verification is secondary-anchored (JDG 108(2) 319-378 from SRC-001 bibliography); the arXiv API record shows no journal ref.

**Falsifiers.**

- Construct a non-trivial continuous isometric extension of the maximal analytic Schwarzschild spacetime (would refute the theorem).
- Find a gap in the spacelike-diameter argument (the method has since been adapted by others, e.g. SRC-007/008/009/049, suggesting acceptance).

## T-303 — Luk 2018: weak null singularities in vacuum with C^0 extension and non-L^2 connection [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** There is a class of spacetimes without symmetry satisfying the vacuum Einstein equations with singular boundaries on two null hypersurfaces intersecting in the future on a 2-sphere; the metric extends continuously beyond the singularities while the Christoffel symbols fail to be square integrable in a neighbourhood of any point of the singular boundaries. The construction is stable in a suitable sense.

**Assumptions.** Einstein vacuum equations, no symmetry; Characteristic data with singular boundaries on two null hypersurfaces; The construction is of impulsive-wave type (Luk-Rodnianski lineage)

**Conclusion type.** `theorem`

**Sources.** SRC-022

**Scope caveats.** This is a construction, not a statement about the interior of generic black holes; the abstract says such singularities are 'conjecturally' present in generic black-hole interiors.; It shows the L^2-connection formulation (D-004) can fail in vacuum for a special class.

**Does not imply.** Does not prove that generic collapse produces weak null singularities.; Does not decide C^0 SCC.; Does not provide an example with a complete AF exterior; it is a local characteristic construction.

**Unresolved.** Whether these spacetimes arise as interiors of asymptotically flat collapse solutions with complete I+.

**Falsifiers.**

- Find an error in the construction.
- Show the singular boundary is actually C^1-extendible, contradicting the non-square-integrability of the connection.

## T-305 — Gurriaran 2026: Lipschitz-inextendibility of the Kerr Cauchy horizon near i_+ [provisional]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

**Exact statement.** For solutions of the Einstein vacuum equations arising from smooth data on a hypersurface slightly inside a dynamical black hole settling down to a subextremal Kerr black hole and satisfying a precise nonlinear Price's-law-type estimate (expected to hold generically), the maximal globally hyperbolic development admits a non-trivial piece of future null boundary (the Cauchy horizon) emanating from timelike infinity i_+, across which the spacetime metric is Lipschitz-inextendible; this yields a Lipschitz version of SCC for Kerr near timelike infinity under that assumption.

**Assumptions.** Einstein vacuum equations, no symmetry; Data slightly inside a dynamical black hole settling to subextremal Kerr; Nonlinear Price's-law-type estimate assumed (expected generically, not proved); Region near timelike infinity only

**Conclusion type.** `conditional_theorem`

**Sources.** SRC-047, SRC-004, SRC-040

**Scope caveats.** Preprint (v2, Mar 2026), not peer-reviewed.; The Price-law estimate is an assumption, not a theorem, in this paper.; Only the piece of the Cauchy horizon emanating from i_+ is controlled.; Between C^0 (T-301: extension exists) and C^2 (still open), Lipschitz is the intermediate verdict.

**Does not imply.** Does not prove C^2 SCC.; Does not prove C^0 SCC.; Does not remove the genericity assumption.

**Unresolved.** Whether the nonlinear Price-law estimate has been proved in the cited literature (GKS programme) or remains conjectural.; Refereeing status.

**Falsifiers.**

- Show the Price-law estimate fails on an open set of data, making the conditional result vacuous there.
- Construct a Lipschitz extension of the Kerr Cauchy horizon near i_+, which would refute the theorem.

## T-402 — Dafermos-Luk revised SCC picture: C^0-extendible but generically C^2-singular (weak null) Cauchy horizons [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** The Cauchy horizons arising in dynamical vacuum black holes that are C^0-extendible across a non-trivial piece are generically singular in an essential way, representing weak null singularities; hence a revised version of strong cosmic censorship (forbidding the relevant higher-regularity extension) is expected to hold.

**Assumptions.** Same setting as T-301; 'Generically singular' is the authors' interpretation of the proof, stated in the abstract, not a theorem with a quantified genericity notion

**Conclusion type.** `open_problem`

**Sources.** SRC-004, SRC-022

**Scope caveats.** This is the authors' stated interpretation ('The proof suggests, however, ...'), not a proved theorem.; It is the strongest available pointer for why the C^2 formulation might survive while the C^0 one fails.

**Does not imply.** Does not prove C^2 SCC.; Does not quantify 'generic'.

**Unresolved.** Turn 'the proof suggests' into a theorem with a topology.; Interaction with the Lipshitz result T-305.

**Falsifiers.**

- Construct generic Kerr-interior data whose Cauchy horizon is C^2-extendible (would kill the revised picture).
- Show the weak-null-singularity behaviour is non-generic in the interior-data space.

## T-515 — Kerr stability status as of 2026-09: full-subextremal nonlinear stability CLAIMED in a 2026 preprint; linear stability peer-reviewed for the full range [verified]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

**Exact statement.** Status of the Kerr exterior stability antecedent: (a) Hintz (arXiv:2606.28253, 339 pp, Jun/Aug 2026) CLAIMS global nonlinear stability of Kerr in the full subextremal range, with companions on constraint damping (arXiv:2606.27658) and tame estimates (arXiv:2606.28008); (b) earlier unconditional nonlinear stability was established in preprints for small angular momentum |a|/m << 1 (Klainerman-Szeftel arXiv:2104.11857; GKS arXiv:2205.14808); (c) unconditional LINEAR stability is proved for the full subextremal range (Hafner-Hintz-Vasy arXiv:2506.21183, 2025); (d) for Lambda > 0, nonlinear stability of Kerr-de Sitter in the full subextremal range is conditional on mode stability (Hintz-Petersen-Vasy arXiv:2508.06620, 2025); (e) future event horizons in the nonlinear-stability spacetimes are smooth (Chen-Klainerman arXiv:2409.05700, 2024).

**Assumptions.** Search performed 2026-09-11/12 via arXiv API (au:Klainerman AND ti:Kerr; ti:'stability of Kerr', sorted by date) and earlier INSPIRE/arXiv queries; Status claim, not a mathematical theorem

**Conclusion type.** `open_problem`

**Sources.** SRC-078, SRC-079, SRC-091, SRC-040, SRC-062, SRC-063, SRC-064, SRC-065, SRC-035

**Scope caveats.** Clause (a) is a PREPRINT claim, not peer-reviewed; clause (b) is from preprints; only (c) has been widely scrutinised to date.; This entry directly constrains how far the Dafermos-Luk conditional refutation of C^0 SCC (T-301) reaches: at preprint level it now reaches the full subextremal range.

**Does not imply.** Does not assert that full-subextremal nonlinear stability is false or unprovable.; Does not by itself decide any SCC formulation.

**Unresolved.** Peer review of arXiv:2606.28253 and its two companions.; Whether the initial-data asymptotics required by Hintz 2026 are compatible with the Dafermos-Luk interior-data assumptions.

**Falsifiers.**

- Find an error in arXiv:2606.28253 or its companions (would downgrade).
- Locate a peer-reviewed full-subextremal nonlinear stability proof (would upgrade clause (a)).

## T-526 — Luk-Sbierski 2026: formation of a weak null singularity in generic rotating black-hole interiors (C^0 extendible, not Lipschitz extendible) [verified]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

**Exact statement.** Given a characteristic initial value problem with smooth data representing a dynamical event horizon settling down to that of Kerr in the subextremal, strictly rotating range with suitable upper and lower bounds, a weak null singularity forms, across which the spacetime metric is continuously extendible but not Lipschitz extendible.

**Assumptions.** Einstein vacuum equations, no symmetry; Characteristic initial data on a dynamical event horizon settling to subextremal, strictly rotating Kerr; Suitable upper and lower bounds on the data (Price-law-type; as in the linear instability works); Not full asymptotically flat Cauchy data: this is a characteristic interior problem

**Conclusion type.** `theorem`

**Sources.** SRC-080, SRC-081, SRC-082, SRC-083, SRC-085, SRC-084

**Scope caveats.** Preprint (arXiv:2604.04877 v1, April 2026); not peer-reviewed.; The result is nonlinear vacuum without symmetry: this is the strongest vacuum SCC-type statement in the ledger.; Because C^1 and C^2 extensions are locally Lipschitz, non-Lipschitz-extendibility implies non-C^2-extendibility; this inference is the ledger's (standard regularity inclusion), not a quoted sentence from the paper, and is flagged for F1 review.; The data are characteristic/interior, not a full asymptotically flat Cauchy data set; AF-SCC class binding is therefore provisional.

**Does not imply.** Does not prove a C^2 SCC theorem for generic asymptotically flat vacuum Cauchy data.; Does not prove C^0-inextendibility (the metric is C^0-extendible).; Does not cover non-rotating (a=0) Kerr.

**Unresolved.** Peer review.; Removal of the 'suitable upper and lower bounds' assumption.; Whether the AF-SCC class should count a characteristic interior result as discharging it.

**Falsifiers.**

- Construct a Lipschitz extension across the weak null singularity, contradicting the main theorem.
- Find a gap in the dynamical-Teukolsky stability argument.
- Show the required upper/lower bounds fail for generic data.

## T-528 — Hintz 2026: nonlinear stability of subextremal Kerr black holes in the full subextremal range [verified]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

**Exact statement.** Spacetimes evolving from initial data close to those of a subextremal Kerr black hole as solutions of the Einstein vacuum equation Ric(g)=0 settle down to a nearby member of the Kerr family at rate O(t_*^{-2-eps}) in spatially compact regions; the initial data are required to have an arbitrary finite expansion in r^{-z}(log r)^k, z>1, plus an O(r^{-3-eps_0}) remainder.

**Assumptions.** Einstein vacuum equations; Initial data close to a subextremal Kerr black hole with the stated finite asymptotic expansion and decay; Generalized wave map gauge with finite-dimensional gauge source terms; nonlinear Nash-Moser iteration

**Conclusion type.** `stability_result`

**Sources.** SRC-078, SRC-079, SRC-091, SRC-063, SRC-062, SRC-040

**Scope caveats.** Preprint (arXiv:2606.28253 v2, Aug 2026, 339 pages); not peer-reviewed as of 2026-09-11. Relies on two companion preprints, both now located (SRC-079, SRC-091).; This supersedes the earlier small-|a|/m limitation at preprint level; the nonlinear stability of the full subextremal Kerr family was previously open (T-515).

**Does not imply.** Does not by itself prove C^0 SCC false; combined with Dafermos-Luk it discharges the antecedent (still modulo the interior-data assumptions of T-301).; Does not address the black-hole interior.

**Unresolved.** Peer review of arXiv:2606.28253 and its two companions (SRC-079 constraint damping; SRC-091 tame estimates, now located).; Whether the initial-data asymptotics required by Hintz 2026 are compatible with the Dafermos-Luk interior-data assumptions.

**Falsifiers.**

- Find an error in the 339-page preprint or its companions.
- Show the required initial-data class is empty or the decay rate is not achieved.

## Informing evidence (other-model or tagged results that bear on this class)

- T-306 [provisional] Cameron-Sbierski 2025: continuous extensions are not unique in 1+1 dimensions — tags: 1+1-MODEL, C0, OTHER-MODELS, PREPRINT
- T-501 [verified] Dafermos 2005: mass inflation for spherical EM-scalar with Price-law data (C^0 extendible, C^1 inextendible) — tags: EM-SCALAR, MASS-INFLATION, OTHER-MODELS
- T-511 [verified] Ma-Zhang 2023: precise interior late-time asymptotics and H^1_loc-inextendibility of the Kerr Cauchy horizon (linear) — tags: KERR, LINEAR, OTHER-MODELS

