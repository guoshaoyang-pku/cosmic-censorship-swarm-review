# Literature status card — WCC/SCC primary-source ledger

**Author:** lead-literature · **Built:** 2026-09-12 ~00:02 (+08) · **Ledger:** `ledger/theorems.jsonl` (62 entries: 50 accepted, 11 provisional, 1 rejected-as-superseded) · **Audit:** `ledger/citation_audit.csv` (95 sources: all locator-resolved; 3 not-assessed with reasons — 2 retrievability-blocked candidates and 1 locator-verified content-unread record)
**Class policy:** `class_ids` contains only the four frozen classes; all other labels are `ledger_tags` (see `tag_index.md`, `ASTRA_COMPLIANCE.md`). Cross-class relevance is `informs_classes`.
**Evidence standard:** every non-metadata source record carries a verbatim quote from a directly fetched primary page (arXiv, INSPIRE mirror of publisher abstracts, Crossref, OpenAlex with cross-check) plus fetch time and URL. A claim is `accepted` only if at least one abstract-level source's quote entails the statement; metadata-only sources are bibliographic anchors only and are enumerated in `MANIFEST.json`. Adversarial review findings and dispositions: `reviews/lead-adjudication.md`.

> **Late-breaking (2026):** Luk-Sbierski (arXiv:2604.04877, preprint) prove a weak null singularity forms in generic rotating vacuum interiors with the metric C^0- but not Lipschitz-extendible; Sbierski (arXiv:2409.18838) supplies the symmetry-free Lipschitz criterion and is **accepted in Inventiones Mathematicae** (accepted-in-press); Hintz (arXiv:2606.28253, preprint) claims nonlinear stability of full-subextremal Kerr. These change the SCC picture below. Peer review is pending for the two preprints only.

---

## 1. The four map classes, one screen each

### AF-WCC-VAC-GEN — asymptotically flat vacuum, WCC, generic data

| | |
|---|---|
| **Status** | Open. No counterexample; no generic theorem. |
| **Definition** | Generically, singularities from regular asymptotically flat vacuum data have complete future null infinity (D-001). The genericity quantifier is not fixed by the conjecture (D-007). **F1 refinement (binding map statement):** complete I+ *and* no future-incomplete causal geodesic visible from I+ (hiddenness, not absence), with `residual_comeager` genericity in the weighted-Sobolev subspace topology (schema `f512af5f4db3`). No verified primary theorem reaches that bar. |
| **Positive evidence** | Trapped-surface formation from short-pulse data (Christodoulou 2009, T-201; Klainerman-Rodnianski 2012, T-202); complete AF vacuum data free of trapped surfaces evolving to a trapped surface (Li-Yu 2015, T-203); complete `I+` near Schwarzschild on a codim-3 submanifold (DHRT 2021 preprint, T-204), polarized perturbations (T-205); nonlinear slowly rotating Kerr (GKS/KS preprints, T-206); **NEW: Hintz 2026 preprint claims full-subextremal nonlinear Kerr stability (T-528/T-515)**. |
| **Negative evidence** | Explicit vacuum naked-singularity constructions, non-generic: RSR exterior (Ann. Math. 198(1) 2023, T-208) + interior/gluing (preprint 2022, T-209). |
| **Open items** | No generic WCC theorem; peer review of T-528; whether the naked-singularity constructions sit in an open set of AF data. |
| **Falsifier** | A generic (declared topology) family of AF vacuum data with incomplete `I+`. |
| **Confidence** | 0.8 — positive corner well documented; absence of a generic theorem robust across five channels. |

### AF-SCC-C2-VAC-GEN — asymptotically flat vacuum, SCC, C²-inextendibility

| | |
|---|---|
| **Status** | **Covered at preprint level for generic rotating interiors; still no peer-reviewed full-AF Cauchy theorem.** Formulation decision (D-003) outstanding. |
| **Definition issue** | Four non-equivalent regularities in use: C²-inextendibility; C^0 + L²_loc Christoffel ("Christodoulou-Chrusciel version", D-004, defining text still unidentified — candidate SRC-090); Lipschitz/C^{0,1}_loc; L^s_loc connection, s>1 (D-005). |
| **Strongest verified results** | Tag-level (not class members: T-514/T-520/T-505/T-304 are `OTHER-MODELS` evidence informing C2): C² SCC for spherical EM-scalar two-ended AF, generic = open weighted C¹ + dense weighted C^∞ (Luk-Oh, T-514, peer-reviewed); T³-Gowdy vacuum (Ringstrom 2009, T-520, peer-reviewed); spherical EM-KG under expected decay (Van de Moortel, T-505, peer-reviewed); L^s_loc connection for spherical weak null singularities (Cameron-Sbierski 2026, T-304, provisional preprint). |
| **Vacuum results** | **Luk-Sbierski 2026 (preprint): weak null singularity in generic rotating interiors, C^0-extendible but NOT Lipschitz-extendible (T-526). Sbierski 2024/25 (Invent. Math. accepted): symmetry-free Lipschitz-inextendibility criterion from curvature blow-up (T-527).** Non-Lipschitz-extendibility implies non-C²-extendibility by regularity inclusion (ledger inference, flagged). |
| **Open items** | Peer review of T-526 (T-527 is accepted-in-press; only final volume/pages confirmation remains); whether characteristic interior data discharge the AF class; the "suitable upper/lower bounds" assumption; C² formulation origin text. |
| **Falsifier** | A Lipschitz (hence C²) extension for the T-526 data class; or an error in the 2026 proofs. |
| **Confidence** | 0.7 that C² SCC holds for generic rotating vacuum interiors at preprint level; 0.45 that the map's AF class is thereby discharged. |

### AF-SCC-C0-VAC-GEN — asymptotically flat vacuum, SCC, C⁰-inextendibility

| | |
|---|---|
| **Status** | **Refuted at preprint level, in the Kerr-like corner** — do not mark the whole class refuted. |
| **Core result** | Dafermos-Luk (Ann. Math. 202(2) 309-630, 2025): interior vacuum data ⇒ maximal evolution extends across a non-trivial CH piece with continuous metric; if Kerr exterior stability holds, the C⁰-inextendibility formulation is false (T-301). |
| **Antecedent** | **Discharged at preprint level by Hintz 2026 (full subextremal nonlinear stability, T-528)**, on top of earlier small-|a|/m and Schwarzschild results. The interior-data retrieval promised by Dafermos-Luk has still not been located; T-526 covers generic rotating interiors directly in a characteristic setting. |
| **Tension to state carefully** | Sbierski 2018 proves C⁰-inextendibility of maximal analytic **Schwarzschild** through the r=0 curvature singularity, not a Cauchy horizon; it does not contradict T-301 (T-302). |
| **Model precedents** | C⁰ SCC false for spherical EM-scalar (Dafermos 2005 T-501; Luk-Oh T-514; Dafermos 2003 open set T-521); non-uniqueness of continuous extensions in a 1+1 model (T-306). |
| **Falsifier** | Prove no continuous extension exists for generic Kerr interiors; or find an error in Hintz 2026/T-301. |
| **Confidence** | 0.8 in the conditional statement; 0.6 that the full class is refuted (data-class caveats). |

### AF-WCC-SCALAR-SPH — spherical massless scalar, WCC, generic data

| | |
|---|---|
| **Status** | WCC holds in the rough framework; naked singularities exist but are non-generic; "genericity" is framework-dependent. |
| **Chain** | Christodoulou 1994 (family exists, T-102) → 1999 (instability in rough framework, T-101, now provisional after review) → Liu-Li 2018 (robust proof, T-523) → Li-Liu 2022 (instability under non-symmetric perturbations; exceptional set first category, T-524) → An 2025 Ann. Math. (anisotropic apparent horizon censors the family, T-105). |
| **Counter-currents** | Choptuik 1993 numerical threshold (T-103); Zheng 2026 preprint: stability in a localized Holder topology (T-107); Singh 2025: stable perturbations only for fine-tuned **non-generic** data (T-525); An-Wu 2026 preprint: non-spherical naked singularities with incomplete `I+` (T-106). |
| **Trap** | "Stable" in Zheng 2026 / Singh 2025 must not be read as "generic". |
| **Falsifier** | An open (declared topology) set of scalar data with naked singularities; or a gap in the instability chain. |
| **Confidence** | 0.8 in the non-genericity picture; 0.55 that the rough framework is "right" (methodological, D-006). |

### Supporting classes

- `BH-FORMATION` tag: 3 accepted trapped-surface-formation theorems (T-201, T-202, T-203), all special data classes; not a class (the class is AF-WCC-VAC-GEN).
- `NS-CONSTRUCTION` tag: 3 entries, 2 accepted (T-208 published exterior; T-522 Einstein-Euler) + 1 provisional (T-209 unpublished gluing interior); not a class.
- `OTHER-MODELS` tag (cross-class evidence): 24 entries, 21 accepted (EM-scalar, EM-KG, RN-dS, Gowdy, Einstein-Euler); not a class — relevance is carried by `informs_classes`.
- `DEFINITIONS` tag: 9 entries (8 excluding the metadata-only background D-009): WCC statement; SCC formulations; genericity vocabularies; MGHD; the class-dependence synthesis.

---

## 2. Unresolved register (headline items)

1. **F0 artifact missing** (`research_map/formulation_taxonomy.yaml` claimed done, absent) — class IDs remain provisional.
2. **C² formulation primary text** not retrieved; attribution unresolved (D-003).
3. **"Chrusciel" defining reference**: candidate SRC-090 is now locator-verified (Chruściel, Contemp. Math. 132, 235-273, 1992, DOI 10.1090/conm/132/1188443) but its content is unread, so it is still not citable as scope evidence (D-004).
4. **C⁰ attribution**: three accessible primary quotes say "Christodoulou's C^0 formulation"; Dafermos-Luk say "of Penrose" in an ambiguous possessive (D-002).
5. **Christodoulou 1999/1994 exact theorem quantifiers** not extracted from paywalled bodies; T-101 provisional (T-102 too).
6. **Peer review of the 2026 SCC/Kerr results**: T-526 (Luk-Sbierski, preprint), T-527 (accepted-in-press, Inventiones Mathematicae; final volume/pages pending), T-528 (Hintz 339 pp; both companions located — SRC-079 and SRC-091, CSV-verified).
7. **Penrose 1969 exact wording**; OpenAlex abstract channel contaminated for Penrose 1965.
8. **Ringstrom 2009 published page** not read (abstract is a machine reconstruction).
9. **An-Wu / Zheng / Cameron-Sbierski / Gurriaran preprints** unreviewed; flagged where load-bearing.
10. **Gowdy/Choptuik historical texts** partly metadata-only.

## 3. What would change the picture fastest

1. Peer review landing for T-526/T-528 — would move AF-SCC-C2 and AF-SCC-C0 from "preprint-level" to established.
2. A human/library fetch of four texts (Christodoulou 1994, 1999, 2009 introduction; Chrusciel 1991) — closes items 2, 3, 5.
3. An F1 decision on whether characteristic interior data discharge the AF classes — determines how much of the 2026 progress transfers.
4. A vacuum Cauchy-data analogue of Luk-Oh's C² theorem — would retire T-401.
