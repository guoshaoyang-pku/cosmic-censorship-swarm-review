# Evidence graph — WCC/SCC classes

- Author: lead-literature · 2026-09-12 ~00:25 (+08)
- Purpose: for each frozen class, state the class conclusion, then list which ledger entries support it, which only support a sub-case, and which refute or tension it. Entry statuses and evidence levels are in `ledger/theorems.jsonl`; this is the map-facing digest.

Notation: **S** = supports the class conclusion; **S-sub** = supports only a strict sub-case (special data, symmetry, model, or topology); **R** = refutes (or would refute) the conclusion as stated; **N** = neutral/background. A refutation of the *class* requires a generic-set statement (F1/F2 falsifier rules).

## AF-WCC-VAC-GEN — "generic AF vacuum data have complete I+ and no visible incompleteness"

| Evidence | Direction | Why |
|---|---|---|
| T-201 Christodoulou 2009 (open set of short-pulse data forms a trapped surface) | S-sub | Special short-pulse family; no I+ statement. |
| T-202 Klainerman-Rodnianski 2012 (enlarged admissible set) | S-sub | Same family, weaker hypotheses. |
| T-203 Li-Yu 2015 (complete AF data free of trapped surfaces whose development forms one) | S-sub | Existence, not genericity; no I+ completeness. |
| T-204 DHRT 2021 (complete I+ near Schwarzschild, codim-3 submanifold) | S-sub | Open neighbourhood intersected with a codim-3 submanifold; preprint. |
| T-205 Klainerman-Szeftel 2020 (polarized perturbations) | S-sub | Symmetry-restricted. |
| T-206 GKS/KS small-|a|/m Kerr stability | S-sub | Open neighbourhood of slowly rotating Kerr; preprints. |
| T-528 Hintz 2026 (full subextremal Kerr stability) | S-sub | Preprint; neighbourhood of each subextremal Kerr member, not a comeager set; does not by itself give visibility. |
| T-515 status entry | N | Status table. |
| T-208/T-209 vacuum naked-singularity constructions | R (non-generic) | Refute any "for all data" reading, not the generic statement. |
| T-301 Dafermos-Luk (C0 extension in interiors) | N/R for WCC? | Interior result; does not produce an incomplete I+. |
| **Net** | **Open** | No entry reaches the F1 `residual_comeager` bar. Decisive open item: a generic-set statement for complete I+ (or a generic naked-singularity construction). |

## AF-SCC-C2-VAC-GEN — "generic AF vacuum MGHD has no proper future C² vacuum extension"

| Evidence | Direction | Why |
|---|---|---|
| T-526 Luk-Sbierski 2026 (weak null singularity; metric not Lipschitz-extendible) | S-sub (strongest) | Nonlinear vacuum, strictly rotating subextremal Kerr; characteristic data with upper/lower bounds; preprint. `not Lipschitz ⇒ not C²` by regularity inclusion (ledger inference). |
| T-527 Sbierski 2024/25 (Lipschitz inextendibility from curvature blow-up, no symmetry) | S-sub | Criterion; hypothesis supplied for the T-526 class; accepted-in-press (Invent. Math.). |
| T-305 Gurriaran 2026 (Lipschitz-inextendibility near i+ under Price law) | S-sub | Conditional; only near timelike infinity; preprint. |
| T-514 Luk-Oh 2019 (C² SCC for spherical EM-scalar two-ended AF) | S-sub (model benchmark) | Matter model, not vacuum; genericity = open weighted C¹, dense weighted C^∞. |
| T-520 Ringström 2009 (T³-Gowdy C²-inextendibility) | S-sub (model) | Compact symmetric vacuum, not AF; genericity open C¹/dense C^∞ (abstract reconstruction). |
| T-505 Van de Moortel 2020 (C²-inextendibility for spherical EM-KG) | S-sub (model) | Conditional on expected decay. |
| T-303 Luk 2018 (weak null singularities, C0 but not L² connection) | S-sub | Special impulsive construction; shows C0 extension coexists with connection blow-up. |
| T-401 status entry | N | Records absence of a peer-reviewed full-AF Cauchy theorem. |
| T-402 revised-SCC conjecture | S-sub/conjectural | Interpretation by Dafermos-Luk; not quantified. |
| **Net** | **Preprint-level coverage of a generic rotating interior; class not discharged as defined** | Decisive open item: whether F2a accepts characteristic/interior data with bounds, and peer review of T-526/T-527. |

## AF-SCC-C0-VAC-GEN — "generic AF vacuum MGHD has no proper future continuous extension"

| Evidence | Direction | Why |
|---|---|---|
| T-301 Dafermos-Luk 2025 (C0 extension across a non-trivial CH piece; C0-inextendibility formulation false if Kerr stable) | R (conditional) | Interior data; antecedent now claimed by T-528 at preprint level. |
| T-526 Luk-Sbierski 2026 (metric continuously extendible across the weak null singularity) | R (for the T-526 class) | Nonlinear vacuum, generic rotating interiors; preprint. |
| T-514 Luk-Oh 2019 (C0 formulation false for spherical EM-scalar) | R (model) | Matter model. |
| T-501 Dafermos 2005 / T-521 Dafermos 2003 (C0 extension; mass inflation) | R (model) | EM-scalar spherical. |
| T-306 Cameron-Sbierski 2025 (continuous extensions non-unique in 1+1) | N/R (method) | 1+1 model; complicates "the extension" language. |
| T-302 Sbierski 2018 (C0-inextendibility of maximal analytic Schwarzschild) | N | Different boundary (r=0 curvature singularity), not a Cauchy horizon; does not rescue the class. |
| T-515/T-528 | R-support | Kerr-stability antecedent at preprint level. |
| **Net** | **Refuted at preprint level in the Kerr-like corner; not globally** | Decisive open items: peer review of T-528/T-301's interior-data retrieval; whether the class quantifies over characteristic/interior data. |

## AF-WCC-SCALAR-SPH — "generic spherical massless-scalar collapse has complete I+ / no visible singularity"

| Evidence | Direction | Why |
|---|---|---|
| T-101 Christodoulou 1999 (instability of the 1994 naked singularities, rough framework) | S-sub | Provisional (function space unextracted); framework-relative. |
| T-523 Liu-Li 2018 (robust instability proof) | S-sub | Confirms T-101 scope. |
| T-524 Li-Liu 2022 (instability under non-symmetric perturbations; exceptional set first category) | S-sub | Strongest genericity statement in the class (meager exceptional set, continuous shear topology). |
| T-105 An 2025 (anisotropic apparent horizon censors the 1994 family) | S-sub | Annals paper; censors one family. |
| T-102 Christodoulou 1994 (naked-singularity family exists) | R (non-generic) | Provisional metadata/scope. |
| T-106 An-Wu 2026 (non-spherical naked singularities with incomplete I+) | R (non-generic) | Preprint; constructed data. |
| T-103 Choptuik 1993 (threshold naked singularity) | R (codim-1) | Numerical. |
| T-107 Zheng 2026 (Hölder-topology stability of naked singularities) | Tension | Topology-specific; not generic in the rough framework. |
| T-525 Singh 2025 (stable perturbations only for fine-tuned data) | Tension | Explicitly non-generic. |
| T-516 Price's law (upper bound) | N (input) | Decay input for the SCC side. |
| **Net** | **WCC holds in the rough framework; non-genericity picture robust** | Decisive open item: which topology F1 adopts for the scalar class; if smooth/Hölder, the verdict changes. |

## Cross-class dependencies

- `AF-SCC-C2` and `AF-SCC-C0` both depend on the 2026 Kerr-interior results; a failure of T-526/T-527 would revert both to "model evidence only".
- `AF-SCC-C0` additionally depends on the Kerr-stability antecedent (T-528) through T-301; a failure of T-528 reverts the refutation to the small-|a|/m corner.
- `AF-WCC-VAC-GEN` depends on no single entry; it is an absence-of-generic-theorem state.
