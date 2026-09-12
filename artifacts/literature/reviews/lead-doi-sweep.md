# Lead-run DOI integrity sweep (independent of reviewer C)

- Run: 2026-09-12 ~00:15–00:22 (+08) by lead-literature
- Method: Crossref REST API, multi-DOI `filter=doi:...` and single-DOI endpoints; every returned title/author/venue compared against the ledger record.
- Result: **33/33 DOIs resolve to the expected work. Zero mismatches, zero retractions, zero wrong-paper resolutions.**
- Transient failures: the multi-filter endpoint intermittently returned `unsupported content type`; failed batches were retried in smaller groups and every DOI eventually resolved. No negative result was recorded from a transient failure.

## Checks

| DOI | Crossref title (match) | Ledger source |
|---|---|---|
| 10.1103/PhysRevLett.14.57 | Gravitational Collapse and Space-Time Singularities | SRC-010 |
| 10.1098/rspa.1970.0021 | The singularities of gravitational collapse and cosmology | SRC-012 |
| 10.1023/A:1016578408204 | "Golden Oldie": Gravitational Collapse: The Role of General Relativity | SRC-011 |
| 10.2307/2118619 | Examples of Naked Singularity Formation… | SRC-013 |
| 10.2307/121023 | The Instability of Naked Singularities… | SRC-014 |
| 10.1007/BF01223743 | Violation of cosmic censorship in the gravitational collapse of a dust cloud | SRC-015 |
| 10.1103/PhysRevLett.70.9 | Universality and scaling… | SRC-016 |
| 10.1007/BF01214662 | Symmetries of cosmological Cauchy horizons | SRC-017 |
| 10.1063/1.526587 | Symmetries of cosmological Cauchy horizons with exceptional orbits | SRC-018 |
| 10.1007/s00220-019-03571-9 | Symmetries of Cosmological Cauchy Horizons with Non-Closed Orbits | SRC-019 |
| 10.4007/annals.2003.158.875 | Stability and instability of the Cauchy horizon… | SRC-020/060 |
| 10.1002/cpa.20071 | The interior of charged black holes… | SRC-021/056 |
| 10.1090/jams/888 | Weak null singularities in general relativity | SRC-022 |
| 10.1215/00127094-3715189 | Proof of linear instability of the RN Cauchy horizon under scalar perturbations | SRC-023/055 |
| 10.1215/00127094-2022-0040 | On holonomy singularities… C^{0,1}_loc-inextendibility | SRC-087 |
| 10.1016/j.jfa.2016.06.013 | Instability results for the wave equation in the interior of Kerr black holes (271(7) 1948-1995) | SRC-089 |
| 10.1007/s00220-020-03923-w | Mass Inflation and the C²-inextendibility… (382, 1263-1341) | SRC-025 |
| 10.1088/0264-9381/32/1/015017 | …cosmological constant: I. Well posedness… | SRC-026 |
| 10.1007/s00220-015-2433-6 | …cosmological constant: II (CMP 339, 903-947) | SRC-027 |
| 10.1007/s40818-017-0028-6 | …Part 3. Mass inflation… (Ann. PDE 3) | SRC-028 |
| 10.1007/s00220-018-3122-z | On the Occurrence of Mass Inflation… (CMP 361, 289-341) | SRC-029 |
| 10.1103/PhysRevD.99.064014 | Strong cosmic censorship: The nonlinear story | SRC-030 |
| 10.1103/PhysRevLett.120.031103 | Quasinormal Modes and Strong Cosmic Censorship | SRC-031 |
| 10.1007/JHEP10(2018)001 | Strong cosmic censorship: taking the rough with the smooth | SRC-032 |
| 10.1088/1361-6382/aadbcf | Rough initial data and the strength of the blue-shift instability… | SRC-033/088 |
| 10.1103/PhysRevD.103.064077 | Interior quasinormal modes and strong cosmic censorship | SRC-034 |
| 10.4310/acta.2018.v220.n1.a1 | The global non-linear stability of the Kerr-de Sitter family (220, 1-206) | SRC-035 |
| 10.4310/acta.2019.v222.n1.a1 | The linear stability of the Schwarzschild solution… (222, 1-214) | SRC-036 |
| 10.1007/s11511-012-0077-3 | On the formation of trapped surfaces (Acta 208, 211-333) | SRC-042 |
| 10.1007/s00222-005-0450-3 | A proof of Price's law… (Invent. Math. 162(2), 381-457) | SRC-061 |
| 10.1007/BF01645389 | Global aspects of the Cauchy problem in general relativity | SRC-073 |
| 10.1007/s40818-022-00144-3 | Naked Singularities in the Einstein-Euler System | SRC-074 |
| 10.1007/s00220-018-3157-1 | A Robust Proof of the Instability of Naked Singularities… (CMP 363, 561-578) | SRC-075 |
| 10.4310/jdg/1641413698 | Instability of spherical naked singularities… (JDG 120) | SRC-076 |
| 10.1007/s00023-024-01489-0 | A Construction of Approximately Self-Similar Naked Singularities… | SRC-077 |
| 10.4310/jdg/1518490820 | The C⁰-inextendibility of the Schwarzschild spacetime… (JDG 108) | SRC-005 |
| 10.1088/1742-6596/968/1/012012 | On the proof of the C⁰-inextendibility… (JPCS 968) | SRC-006 |
| 10.1007/s00023-024-01454-x | SCC for the EM-charged-Klein-Gordon system with Λ>0 (AHP 26, 675-753) | SRC-070 |
| 10.4007/annals.2019.190.1.1 | SCC in spherical symmetry… Part I (Ann. Math. 190(1), 1-111) | SRC-086 |
| 10.4007/annals.2025.202.2.1 | The interior of dynamical vacuum black holes I (Ann. Math. 202(2)) | SRC-004 |
| 10.4007/annals.2023.198.1.3 | Naked singularities… The exterior solution | SRC-002/068 |
| 10.4007/annals.2025.201.3.3 | Naked singularity censoring with anisotropic apparent horizon | SRC-044/067 |
| 10.4171/068 | The Formation of Black Holes in General Relativity (EMS Monographs) | SRC-041/054 |
| 10.1088/0264-9381/16/12A/302 | On the global initial value problem and the issue of singularities | SRC-092 |
| 10.1090/conm/132/1188443 | On uniqueness in the large… ("strong cosmic censorship"), Contemp. Math. 132, 235-273 (1992) | SRC-090 |

(Some DOIs serve two source records where the ledger keeps both a mirror and a primary page; both rows are listed against the same DOI.)

## Notable closures

1. **10.4171/068** — the Christodoulou 2009 EMS monograph DOI, previously only secondary-anchored, is now Crossref-verified.
2. **10.1090/conm/132/1188443** — the Chruściel "uniqueness in the large / strong cosmic censorship" paper is now locator-verified (Contemp. Math. 132, 235-273, 1992; the earlier 1991 Canberra preprint reference is superseded). Its content is still unread, so the "Chruściel version" of SCC remains an open attribution.
3. **10.4007/annals.2025.202.2.1** — Dafermos-Luk 2025 Annals publication date 2025-09-01 confirmed.
4. **10.1016/j.jfa.2016.06.013** — confirms Luk-Sbierski pages 1948-1995 (the earlier 2189-2235 ledger value was wrong).

## Limitations

- Crossref verifies bibliographic identity, not that the quoted scope matches the paper body. Scope claims still rest on the abstract-level evidence recorded in the source registry.
- Paywalled full texts (JSTOR/IOP/Springer/AMS) were not read; "exact theorem number/page" is therefore the abstract-level locator except where explicitly noted.
- Reviewer C (independent citation-integrity spot-check) is running separately; this sweep does not replace it.
