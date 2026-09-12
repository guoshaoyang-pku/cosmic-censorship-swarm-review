# AF-SCC-C2-VAC-GEN

*Asymptotically flat vacuum, SCC, C^2-inextendibility of the MGHD, generic data (F2a schema)*

Entries whose statement is about this class: 10 (0 accepted, 10 provisional/unresolved).

## D-003 — C^2 (and C^k) inextendibility formulation of SCC [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** Strong cosmic censorship in C^2 form: the maximal globally hyperbolic development is future-inextendible as a Lorentzian manifold whose metric is twice continuously differentiable, for generic initial data.

**Assumptions.** MGHD fixed.; Extension = non-trivial isometric embedding into a larger C^2 Lorentzian manifold.; Genericity supplied separately.

**Conclusion type.** `open_problem`

**Sources.** SRC-024, SRC-025, SRC-050

**Scope caveats.** The literature names 'the C^2-formulation' / 'C^2 Strong Cosmic Censorship Conjecture' (Sbierski 2020; Van de Moortel 2020; Luk-Oh-Shlapentokh-Rothman 2022), but the primary text that first isolated the C^2 formulation was not retrieved.; C^2-inextendibility is strictly weaker than C^0-inextendibility: a spacetime can be C^0-extendible but not C^2-extendible.

**Does not imply.** Does not imply C^0-inextendibility.; A C^2-inextendibility result in a matter model says nothing directly about vacuum.

**Unresolved.** Primary attribution of the C^2 formulation (Christodoulou 2009 book introduction) not machine-verified; book DOI 10.4171/068 appears only in a secondary bibliography.; Candidate formulation text SRC-092 (Christodoulou 1999 CQG 16 A23-A35) is metadata-only; needs a page check before use.; Whether the intended class is C^2 metrics or C^2 with additional fall-off is not uniform.

**Falsifiers.**

- Construct generic data whose MGHD admits a C^2 isometric extension across the Cauchy horizon (for the RNdS model with smooth data, Dias-Reall-Santos report exactly this in the linear coupled setting).
- Exhibit a C^2-inextendibility proof in the model and show its hypotheses fail on an open set.

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

## T-401 — Status of AF-SCC-C2-VAC-GEN: no primary-source theorem located for generic asymptotically flat vacuum data [provisional]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

**Exact statement.** Status of AF-SCC-C2-VAC-GEN at 2026-09-11: the C^2 formulation is (i) proved for model classes (Luk-Oh T-514: spherical EM-scalar two-ended AF), (ii) proved for T^3-Gowdy vacuum (Ringstrom T-520), and (iii) NOW covered for generic rotating vacuum black-hole interiors at PREPRINT level: Luk-Sbierski 2026 (T-526) prove the metric is not Lipschitz-extendible across the forming weak null singularity, and non-Lipschitz-extendibility implies non-C^2-extendibility by regularity inclusion. No peer-reviewed theorem proving C^2-future-inextendibility for generic asymptotically flat vacuum Cauchy data was located.

**Assumptions.** Scope of the search: arXiv API queries ('strong cosmic censorship', 'inextendibility'+'Cauchy horizon', 'C^2-inextendibility'+Kerr, 'nonlinear stability'+Kerr), INSPIRE title queries, Crossref, on 2026-09-11/12; The claim is about the state of the literature, not a proof of impossibility

**Conclusion type.** `open_problem`

**Sources.** SRC-080, SRC-081, SRC-078, SRC-004, SRC-022, SRC-047

**Scope caveats.** Absence of a peer-reviewed full-AF C^2 theorem is search evidence, not impossibility.; The Luk-Sbierski result is a preprint and uses characteristic rather than Cauchy data; whether that discharges the map's AF class is an F1 decision.; The C^2 formulation may not be what the map class intends (D-003).

**Does not imply.** Does not assert the conjecture is false or unprovable.; Does not downgrade the matter-model C^2 results, which remain valid for their own classes.

**Unresolved.** Peer review of Luk-Sbierski 2026 and Sbierski 2024/25 (Invent. Math. acceptance per arXiv comment).; Whether the 'suitable upper and lower bounds' in T-526 hold for generic AF Cauchy data.; MathSciNet/zbMATH systematic sweep.

**Falsifiers.**

- Locate a peer-reviewed C^2-inextendibility theorem for generic AF vacuum Cauchy data (promote); or find an error in T-526/T-527 (demote).

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

## D-007 — Genericity quantifier: the standard used by the C^2 SCC proof (open + dense in specified weighted topologies) [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

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

## T-527 — Sbierski 2024/2025: C^{0,1}_loc-inextendibility of weak null singularities from curvature blow-up, no symmetry [verified]

**Evidence level (derived).** `accepted-in-press` · **L0 verification.** `abstract-read`

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

## Informing evidence (other-model or tagged results that bear on this class)

- T-304 [provisional] Cameron-Sbierski 2026: L^s_loc-connection inextendibility of spherical weak null singularities — tags: EM-SCALAR, OTHER-MODELS, PREPRINT, WEAK-NULL
- T-505 [verified] Van de Moortel 2020: C^2-inextendibility for spherical EM-Klein-Gordon under expected decay — tags: C2, EM-KG, OTHER-MODELS
- T-506 [verified] Sbierski 2020: C^{0,1}_loc-inextendibility of spherical weak null singularities — tags: ACCEPTED-IN-PRESS, EM-SCALAR, OTHER-MODELS, WEAK-NULL
- T-510 [verified] Luk-Oh-Shlapentokh-Rothman 2022: generic class with C^2-future-inextendibility and conditional mass inflation — tags: EM-SCALAR, GENERIC-CLASS-G, OTHER-MODELS

