# Genericity vocabulary map — ledger ↔ F1/F2 class schemas

- Author: lead-literature · 2026-09-12 ~00:10 (+08)
- Purpose: F1/F2 use a controlled vocabulary (`genericity.kind`, `genericity.topology_or_measure`). The primary sources use several different notions. This file maps every ledger entry that carries a genericity claim into (or explicitly outside) the frozen vocabulary, so no class claim can silently inherit a stronger quantifier.
- Frozen vocabulary (from `artifacts/formulation/schemas/*.yaml`): `residual_comeager`, `dense_open`, `measure_one`, `provisional_baire_residual`, `unresolved`; topology must be named before theorem status.

| Entry | Primary-source genericity wording | Frozen-vocabulary mapping | Topology named? |
|---|---|---|---|
| T-514 Luk-Oh 2019 (EM-scalar C² SCC) | "generic (open and dense relative to appropriate topologies)"; Part II: open in weighted C¹, dense in weighted C^∞ | `dense_open` (source); compatible with `residual_comeager` but the source does not claim comeagerness | YES (weighted C¹ / weighted C^∞) |
| T-520 Ringström 2009 (T³-Gowdy C²) | open in a C¹ topology, dense in a C^∞ topology (OpenAlex reconstruction) | `dense_open` | Partially (C¹/C^∞; exact weights unread) |
| T-524 Li-Liu 2022 (non-symmetric scalar perturbations) | exceptional (no-trapped-surface) set is of first category; censoring set open and dense | exception is meager ⇒ good set `residual_comeager`; also states open dense | YES (continuous shear tensors) |
| T-104 Christodoulou 1984 (dust) | "an open subset of initial density distributions" | `open_set` — NOT in the frozen list | NO (exact class not extracted) |
| T-521 Dafermos 2003 (EM-scalar characteristic) | "an open set of initial data whose closure contains RN data" | `open_set` — NOT in the frozen list | NO |
| T-201 Christodoulou 2009 / T-202 Klainerman-Rodnianski 2012 (trapped surfaces) | open set of short-pulse initial conditions | `open_set` (of a special family) | NO |
| T-204 DHRT 2021 (Schwarzschild stability) | data close to Schwarzschild on a codimension-3 submanifold | `open_set` relative to the submanifold — strictly narrower than an open set of all AF data | Partially (data topology in the paper) |
| T-206/T-515/T-528 Kerr stability (GKS/KS, Hintz 2026) | small data / open neighbourhood of a Kerr member | `open_set` | Partially |
| T-105 An 2025 (censoring) | high co-dimensional nonlinear instability | NOT expressible in the frozen vocabulary (codimension, not Baire/measure) | NO |
| T-107 Zheng 2026 (Hölder stability) | small open neighbourhood in a localized Hölder topology | `open_set` in a non-standard topology | YES (localized Hölder) — but topology is not the F1/F2 one |
| T-525 Singh 2025 (fine-tuned naked singularities) | explicitly NON-generic (fine-tuned data) | complement of any generic notion | NO |
| T-101 Christodoulou 1999 | abstract asks about "positive probability"; body quantifier not extracted | `unresolved` (do not map) | NO |
| T-301/T-402 Dafermos-Luk 2025 | "generically singular in an essential way" (interpretation) | `unresolved` (no quantified genericity in the verified text) | NO |
| T-508 Dafermos-Shlapentokh-Rothman 2018 | "generic data in our allowed class" after roughening | `dense_open`-like within a declared rough class; exact kind needs the paper | YES (allowed rough class) |
| T-507 Cardoso et al. 2018 / Dias et al. 2018 | "generic perturbations ... from smooth initial data" (numerical/linear) | numerical genericity; not a measure/Baire statement | NO |

## Consequences for F1/F2

1. Only two verified primary results (T-514, T-524; plus T-520 at lower confidence) state a genericity quantifier at the level the frozen schemas require. Everything else is `open_set`, special-family, numerical, or `unresolved`.
2. The frozen class `AF-WCC-SCALAR-SPH` (genericity slot owned by F1) has no verified `residual_comeager`/`measure_one` theorem in the scalar literature: the 1999 result is framework-relative and the 2026 results are topology-specific or non-generic.
3. `AF-SCC-C2-VAC-GEN` is defined with a comeager generic set; the 2026 Luk-Sbierski/Sbierski results are stated for a characteristic data class with upper/lower bounds, not for a comeager set of AF Cauchy data. F1/F2 must decide whether that discharges the class or only informs it.
4. Any future mapping must name the topology; the ledger will keep refusing to promote entries whose genericity kind is `unresolved`.
