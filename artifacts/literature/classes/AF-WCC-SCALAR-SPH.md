# AF-WCC-SCALAR-SPH

*Asymptotically flat massless scalar field, spherical symmetry, weak cosmic censorship, generic data*

Entries whose statement is about this class: 10 (0 accepted, 10 provisional/unresolved).

## T-101 — Christodoulou 1999: instability of spherical scalar-field naked singularities (rough class) [provisional]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** For the spherically symmetric Einstein-massless-scalar-field system, the naked-singularity solutions constructed in 1994 are unstable under sufficiently rough perturbations: within a rough functional framework, perturbations of those data lead to black-hole formation rather than a naked singularity.

**Assumptions.** Spherical symmetry; Massless scalar field coupled to gravity (Einstein-scalar system); Perturbations measured in a rough functional framework; the precise function space is not fixed by the accessible abstract-level evidence (see unresolved); This is a statement about the 1994 continuously self-similar naked-singularity family

**Conclusion type.** `theorem`

**Sources.** SRC-014, SRC-046, SRC-044

**Scope caveats.** The arXiv abstract fixes only the system and the question; the precise genericity quantifier is in the paper body, which was not machine-read.; Scope is cross-checked against SRC-046 ('instability to black hole formation under sufficiently rough perturbations ... verifying weak cosmic censorship within a rough functional framework') and SRC-044 ('high co-dimensional nonlinear instability').; Matter is a scalar field, NOT vacuum.; Spherical symmetry is essential to the proof.

**Does not imply.** Does not prove WCC for smooth data, nor for vacuum, nor without symmetry.; Does not say naked singularities cannot form; the 1994 family exists.; Zheng 2026 shows stability of the same family in a localized Holder topology, so this theorem cannot be promoted to 'naked singularities are unstable, period'.

**Unresolved.** Exact theorem number, function space, and quantifier in Christodoulou 1999 not extracted from the paper body (JSTOR/publisher text not machine-accessible; arXiv migration has abstract only).; Whether the statement is about all sufficiently rough perturbations, a dense set, or a codimension statement.; Liu-Li arXiv:1710.02922 (SRC-075) is now locator-verified; its abstract does not state a BV class, so the BV restatement remains unconfirmed.

**Falsifiers.**

- Construct perturbations of the 1994 data, rough in the same norm, that remain naked-singularity-forming (would contradict the theorem as scoped).
- Show the theorem's quantifier is not 'generic' but only 'there exist arbitrarily small rough perturbations', which would force a weaker ledger statement.

## T-102 — Christodoulou 1994: existence of continuously self-similar spherical scalar naked singularities [provisional]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** There exists a one-parameter family of continuously self-similar C^{1,alpha} solutions of the spherically symmetric Einstein-scalar field equations that form naked singularities.

**Assumptions.** Spherical symmetry; Massless scalar field; Continuous self-similarity; C^{1,alpha} regularity of the solutions (alpha small)

**Conclusion type.** `theorem`

**Sources.** SRC-013, SRC-046

**Scope caveats.** SRC-013 is metadata-verified only (no abstract available); the precise C^{1,alpha}/self-similar description is quoted from SRC-046 (2026 preprint) and is consistent with SRC-014's framing.; Matter model is a scalar field, not vacuum.

**Does not imply.** Does not contradict T-101: existence of a special family is compatible with its instability under rough perturbations.; Does not give an open set of naked-singularity data in any smooth topology.

**Unresolved.** Primary abstract/theorem statement of the 1994 paper not machine-retrieved.; Whether the family is exactly one-parameter with a smooth parameterisation is not confirmed from the primary text.

**Falsifiers.**

- Find an error in the 1994 construction (no verified claim of this exists in the checked literature).
- Show the family fails to be a solution of the Einstein-scalar system (would be a retraction-level event; none found).

## T-103 — Choptuik 1993: critical collapse and the threshold naked singularity [verified]

**Evidence level (derived).** `numerical` · **L0 verification.** `abstract-read`

**Exact statement.** Numerical study of spherically symmetric massless-scalar collapse: a critical parameter value p* separates black-hole-forming from dispersing solutions; the strong-field p->p* limit is universal and generates structure on arbitrarily small spatiotemporal scales, and black-hole masses obey a power law with universal exponent gamma ~ 0.37.

**Assumptions.** Numerical evidence only; One-parameter families of initial data; Spherical symmetry, massless scalar field

**Conclusion type.** `numerical_evidence`

**Sources.** SRC-016, SRC-094

**Scope caveats.** Not a theorem; numerical evidence from 1993.; The threshold solution is the standard heuristic naked singularity; it is not an open-set counterexample to WCC.; SRC-094 (Gundlach-Martin-Garcia, Living Reviews 2007) is a review of the numerical status and states the codimension-one attractor picture.

**Does not imply.** Does not prove naked-singularity formation.; Does not establish genericity either way.

**Unresolved.** No rigorous proof of critical-collapse universality located in the verified set; the review confirms the numerical status, not a theorem.

**Falsifiers.**

- A rigorous computation showing the critical solution is not naked-singular, or that the power law fails outside the tested families.

## T-105 — An 2025: anisotropic apparent horizon censors Christodoulou's naked singularity [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** Employing the Einstein-scalar field system, a tiny anisotropic perturbation from the outgoing characteristic initial data of Christodoulou's naked-singularity solutions leads to an anisotropic apparent horizon that covers and censors the naked singularity; the method proves high co-dimensional nonlinear instability of those solutions.

**Assumptions.** Einstein-scalar field system (not vacuum); Initial data = Christodoulou's naked-singularity data plus a small anisotropic perturbation on the outgoing characteristic hypersurface; Perturbations allowed finite BV and C^0 norms for shear and scalar derivative; scale-critical norms may be arbitrarily small

**Conclusion type.** `theorem`

**Sources.** SRC-044, SRC-067

**Scope caveats.** Published Ann. of Math. 201(3) (2025); DOI 10.4007/annals.2025.201.3.3 now verified via Crossref (SRC-067).; Matter model is Einstein-scalar, NOT vacuum; the AF-WCC-VAC-GEN tag was removed after adversarial review A.

**Does not imply.** Does not prove WCC for generic data: it censors one specific constructed family.; Does not transfer to vacuum without symmetry.

**Unresolved.** Whether the same censoring mechanism works for the non-spherical 2026 construction (SRC-045) is open.

**Falsifiers.**

- Show the perturbed solution still has a naked singularity visible from infinity (would contradict the theorem as scoped).
- Show the anisotropic apparent horizon does not form for the stated perturbation class.

## T-106 — An-Wu 2026: non-spherical Einstein-scalar naked singularities with singular inner Cauchy horizon [provisional]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

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

## T-107 — Zheng 2026: nonlinear stability of the self-similar naked singularities in a Holder topology [provisional]

**Evidence level (derived).** `preprint` · **L0 verification.** `abstract-read`

**Exact statement.** A one-parameter family of continuously self-similar C^{1,alpha} naked-singularity solutions of the spherically symmetric Einstein-scalar field equations is nonlinearly stable under initial perturbations lying in a small open neighbourhood of the generating data, measured in a localized Holder topology, with perturbations of the same regularity as the background.

**Assumptions.** Spherical symmetry; Einstein-scalar field equations; Perturbations in a localized Holder topology, same regularity as the background (C^{1,alpha}); Relies on a companion linearized-stability paper (Singh-Zheng) not yet verified

**Conclusion type.** `stability_result`

**Sources.** SRC-046

**Scope caveats.** Preprint (v1, May 2026); not peer-reviewed.; Part I of a series; the companion linearized stability result is cited but not independently verified here.; Does not contradict T-101: different topology, so both can hold.

**Does not imply.** Does not make naked singularities generic in a smooth/rough topology.; Does not establish WCC or its failure for the class as a whole.

**Unresolved.** The companion paper (Singh-Zheng, Part II) not yet fetched/verified.; Whether the Holder topology is physically/numerically natural is a modelling judgement, not settled by the preprint.

**Falsifiers.**

- Find an error in the nonlinear stability proof (preprint).
- Show the localized Holder topology is empty/trivial for the constraint equations, which would make the open neighbourhood vacuous.

## T-516 — Dafermos-Rodnianski 2005: Price's law (upper bound) for self-gravitating scalar collapse [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

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

## T-523 — Liu-Li 2018: robust non-contradiction proof of the instability of spherical scalar naked singularities [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** New a priori estimates give a robust (non-contradiction) proof that the naked singularities of a self-gravitating scalar field are unstable in spherical symmetry, so that cosmic censorship holds in that context.

**Assumptions.** Spherical symmetry; Self-gravitating massless scalar field; Estimates relaxed relative to Christodoulou 1999 but still sufficient

**Conclusion type.** `theorem`

**Sources.** SRC-075, SRC-014

**Scope caveats.** Confirms T-101 scope; does not extend it beyond spherical symmetry (that is T-524).; Matter model scalar field; not vacuum.

**Does not imply.** Does not prove WCC for vacuum.; Does not address the Holder-topology stability result T-107.

**Unresolved.** Exact function spaces and the 'robustness' claim in the published version (abstract-level evidence).

**Falsifiers.**

- Construct a stable spherical scalar naked singularity in the same function space.

## T-524 — Li-Liu 2022: instability of spherical scalar naked singularities under non-symmetric gravitational perturbations [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** For a characteristic initial value problem of the Einstein-scalar system whose incoming null cone is spherically symmetric with a singular vertex and whose outgoing null cone has no symmetries: arbitrarily fixing the initial scalar field, the set of initial conformal metrics on the outgoing cone for which the maximal future development has no sequence of closed trapped surfaces approaching the singularity is of first category (in the space of continuous shear tensors), while the set for which a closed trapped surface forms before any fixed later incoming cone contains an open and dense subset. Hence the spherical naked singularities are unstable under gravitational perturbations without symmetry.

**Assumptions.** Characteristic initial data on two intersecting null cones; Incoming cone spherically symmetric and singular at the vertex; outgoing cone without symmetry; Shear tensors continuous; initial scalar field fixed arbitrarily; Einstein-massless-scalar system

**Conclusion type.** `theorem`

**Sources.** SRC-076, SRC-075

**Scope caveats.** Matter model scalar field; not vacuum.; The exceptionality is explicitly weaker than the codimension-one statement in spherical symmetry (abstract).; Result is about trapped-surface formation (censoring), not directly about completeness of I+.

**Does not imply.** Does not prove WCC for non-symmetric data in general.; Does not give a full-genericity WCC theorem.

**Unresolved.** Whether 'first category' can be upgraded to measure zero or codimension one in this topology.; Whether the result extends to vacuum.

**Falsifiers.**

- Show the censoring set is not open in the stated topology, or exhibit a non-meagre exceptional set.

## T-525 — Singh 2025: approximately self-similar naked singularities require non-generic (fine-tuned) perturbations [verified]

**Evidence level (derived).** `peer-reviewed` · **L0 verification.** `abstract-read`

**Exact statement.** Stable perturbations of k-self-similar naked singularities of the spherically symmetric Einstein-scalar system exist for the full parameter range k^2 in (0,1/3), yielding dynamical constructions of naked-singularity interior and exterior regions outside exact self-similarity; the perturbations are fine-tuned data that must be consistent with the absence of a blue-shift instability and are therefore non-generic (in particular the scalar perturbation along the past light cone of the singular point vanishes to high order).

**Assumptions.** Spherical symmetry; Einstein-massless-scalar system; Self-similar bounds on the background; fine-tuned perturbations in the past light cone of the singularity

**Conclusion type.** `stability_result`

**Sources.** SRC-077, SRC-014

**Scope caveats.** Published Ann. Henri Poincare 26(7) (2025).; The word 'stable' here means stable within a fine-tuned non-generic family, NOT stable in an open set. This is a scope trap worth flagging for downstream consumers.; Matter model scalar field; not vacuum.

**Does not imply.** Does not show naked singularities are generic.; Does not contradict T-101/T-523/T-524; it reinforces the non-genericity picture.

**Unresolved.** Exact conditions on the fine-tuned data, and whether any open set of data satisfies them (the abstract says no).

**Falsifiers.**

- Exhibit an open set of data (in a stated topology) satisfying the fine-tuning conditions and retaining the naked singularity, which would make the construction generic.

