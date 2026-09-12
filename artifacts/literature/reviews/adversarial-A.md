# Adversarial verification — classes AF-WCC-SCALAR-SPH / AF-WCC-VAC-GEN / AF-WCC-VAC-BH-FORM / AF-WCC-VAC-NS-CONSTR

Reviewer: adversarial-A. Date: 2026-09-11 23:36 (+08).

**Basis / pinned snapshot.** 22 entries match the four class_ids: the 19 in the requested window (D-001, D-006, T-101…T-209) plus T-515, T-516 and T-523/T-524/T-525, which also carry an in-scope class. File digests at review time: batch-01 `daa95fb84c30c7ab8c7513a23a7b9fd1`, batch-02 `65fcf1eb18a0241a5a2a82ef6e260916`, batch-03 `f0a6cc50e32dc697cde82c246bac2a0e`, batch-04 `3cd5b71a6bde0d7fcb41b90fa266e3bb`, batch-05 `2936ba7414f0448b3e0fca0b1ccb4dc5`, batch-06 `5dafe07e568e94159fdd49e66dab4e15`, batch-07 `b9a018d819e1d988a8ea7fabd71c8275`; sources through SRC-077.

**Concurrency note.** The ledger was being written while this review ran. batch-06/07 and SRC-066…SRC-077 appeared mid-review; T-105 and T-208 gained SRC-067/SRC-068 mid-review; T-523/T-524/T-525 were created mid-review. Findings are against the pinned snapshot above. T-523/524/525 have not been in the ledger long enough for a second-pass review; their stored abstracts were verified live once.

**Method.** For every entry, `statement_exact` was compared against the verbatim evidence of its `source_ids`. 33 live retrievals were made (arXiv abs pages, INSPIRE API records, Crossref API records, the Comptes Rendus landing page) — see the URL list. No ledger file was modified.

## Findings

| theorem_id | verdict | specific issue | recommended action |
|---|---|---|---|
| D-001 | supported | Statement is verbatim SRC-001 (Comptes Rendus abstract; live page confirms wording and "remains wide open"). SRC-011 (Penrose 1969) is metadata-only yet sits on an accepted entry (see hard failures). | keep statement; move SRC-011 to attribution-only / drop from `source_ids` |
| D-006 | partial | Cross-paper synthesis, not a theorem. SRC-014's abstract (the primary) contains no topology/regularity-class contrast; the smooth-vs-rough contrast rests on SRC-033/SRC-032 and the rough-vs-Hölder contrast on SRC-046 + T-101/SRC-044. The entry concedes this in `scope_caveats`. | keep as methodological finding, but reword to "inference from the cited model problems"; `conclusion_type: formal_model` overstates it |
| T-101 | partial | "bounded-variation-type" and "generic" are in no cited evidence. The primary abstract (math/9901147) says nothing about rough/BV data; the live SRC-046 abstract says only "sufficiently rough perturbations" and "a rough functional framework". The BV label is an unsupported regularity claim. | reword: drop "(bounded-variation-type)" and the "generic/" disjunct → "sufficiently rough perturbations (norm not fixed at abstract level)"; demote to provisional until the 1999 body is read |
| T-102 | supported | Live SRC-046 abstract confirms one-parameter family, continuous self-similarity, C^{1,α}; SRC-013 is metadata-only but the entry is provisional and says so. | keep |
| T-103 | supported | Choptuik abstract verified verbatim (INSPIRE 33714). Only addition is "dispersing"; the abstract says "those which do not [contain black holes]". | keep; optional reword "dispersing" → "non-black-hole" |
| T-105 | partial | Statement text matches the live INSPIRE abstract verbatim (tiny anisotropic perturbation, finite BV/C^0, high co-dimensional instability). But `class_ids` carries AF-WCC-VAC-GEN for a theorem whose matter model is a scalar field; SRC-067 is metadata-only on an accepted entry; `scope_caveats`/`unresolved` still say "DOI not machine-verified" although SRC-067's DOI (10.4007/annals.2025.201.3.3) is live-confirmed. | fix `class_ids` (drop AF-WCC-VAC-GEN; it is scalar-field evidence); clear stale DOI caveat; keep statement |
| T-106 | supported | Live 2607.07134 abstract matches: no symmetry, incomplete I+, singular inner Cauchy horizon, C^{1,κ/(1-κ)+}, κ∈(0,1/3). Provisional is correct (v1 only). | keep |
| T-107 | supported | Live 2605.16235 abstract matches: small open neighbourhood, localized Hölder topology, perturbations of the same regularity, companion linearized-stability paper. | keep |
| T-201 | supported | SRC-041 (0805.3880) and SRC-042 (INSPIRE 841287) live abstracts support no-symmetry, open set, trapped-surface formation, first long-time result. "Short-pulse" is not in either quoted abstract but is the monograph's own method; no quantifier inflation. | keep; optionally cite the monograph's short-pulse terminology |
| T-202 | supported | INSPIRE 841287 abstract verbatim: simpler finite problem, enlarged admissible set, relaxed propagation estimates, curvature derivatives 2→1. | keep |
| T-203 | partial | Wrong arXiv ID in SRC-043 and in `citation_audit.csv`: 1207.3167 is Wong–Harko–Cheng–Gergely, "Weyl fluid dark matter model tested on the galactic scale by weak gravitational lensing" (PRD 86, 044038). The Li–Yu paper is **arXiv:1207.3164** (INSPIRE search + abs page). The statement itself is supported by the INSPIRE abstract; DOI 10.4007/annals.2015.181.2.6 and Ann. Math. 181(2) 699–768 verified via Crossref. | correct `arxiv_id` → 1207.3164 in SRC-043 and the audit CSV, then keep |
| T-204 | supported | Live 2104.08222 abstract matches all three clauses incl. the codimension-3 restriction; 513 pp, no journal ref confirmed. | keep |
| T-205 | supported | INSPIRE 1637357 confirms arXiv:1711.07597, polarized class, 907 pp; statement matches abstract. The entry's L1 flag on the arXiv ID can be cleared. | keep provisional; update the source note |
| T-206 | supported | Live 2205.14808, 2104.11857, 2002.02740 abstracts match; small-|a|/m restriction explicit in all. | keep |
| T-207 | partial | Statement is verbatim Hintz–Vasy (Acta Math. 220(1) 1–206; live INSPIRE abstract), but `class_ids` includes AF-WCC-VAC-GEN although the result is Λ>0 and explicitly not asymptotically flat. | fix `class_ids` (remove AF-WCC-VAC-GEN; keep AF-SCC-OTHER-MODELS); keep statement |
| T-208 | supported | Live 1912.08478 abstract matches; Crossref SRC-068 confirms Ann. Math. 198(1) 231–391. SRC-068 is metadata-only on an accepted entry, and `unresolved` still lists the already-closed journal-ref L1 gap while `scope_caveats` says it is closed. | clear the stale `unresolved` item; see hard failures re SRC-068 |
| T-209 | supported | Live 2204.09891 abstract matches incl. the gluing claim; v1 only, no journal ref — provisional is correct. | keep |
| T-515 | supported | Every cited claim checked live: 2104.11857 (small-|a|/m nonlinear), 2205.14808 (completion), 2506.21183 (full-range linear), 2508.06620 (conditional Kerr–dS), 2409.05700 (smooth horizons). | keep |
| T-516 | supported | Live gr-qc/0307013 and gr-qc/0309115 abstracts contain the exact claims, incl. "under Christodoulou's C^0 formulation, the strong cosmic censorship conjecture is false"; 1702.05715 confirms the C^0-false / C^2-generic framing. | keep |
| T-523 | supported | Added mid-review. Stored SRC-075 abstract verified live; statement matches ("robust … not by contradiction", cosmic censorship true in that context). | keep; re-verify against the next snapshot |
| T-524 | supported | Added mid-review. Stored SRC-076 abstract verified live; first-category / open-and-dense statement matches; entry correctly notes exceptionality is weaker than codimension one. | keep; re-verify against the next snapshot |
| T-525 | supported | Added mid-review. Stored SRC-077 abstract verified live, incl. "non-generic" and "vanishes to high order"; entry correctly flags the "stable = fine-tuned family, not open set" scope trap. | keep; re-verify against the next snapshot |

### Inflation checks that came back clean

- No evidence that says "open set" is inflated to "generic" in `statement_exact` (T-201/T-202/T-204 correctly say open set / special class). The one exception is T-101's ambiguous "generic/sufficiently rough" (flagged above).
- No scalar-field theorem claims vacuum in its statement text; only the machine-readable `class_ids` of T-105 and T-207 overstate scope (flagged above).
- T-208 does not claim a full maximal development from the exterior-only paper (it defers to SRC-003); T-209's gluing claim is explicit in its abstract.
- T-206/T-515 carry the small-|a|/m restriction into the statement; T-204 carries the codimension-3 restriction.

## URLs fetched (exact title line seen)

- https://arxiv.org/abs/1912.08478 — `# Title:Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution`
- https://arxiv.org/abs/2204.09891 — `# Title:Naked Singularities for the Einstein Vacuum Equations: The Interior Solution`
- https://arxiv.org/abs/math/9901147 — `# Title:The instability of naked singularities in the gravitational collapse of a scalar field`
- https://arxiv.org/abs/2104.08222 — `# Title:The non-linear stability of the Schwarzschild family of black holes`
- https://arxiv.org/abs/2607.07134 — `# Title:Naked Singularities beyond Spherical Symmetry: Singular Inner Cauchy Horizons for the Einstein-Scalar Field System`
- https://arxiv.org/abs/2605.16235 — `# Title:Nonlinear stability of continuously self-similar naked singularities for the Einstein-scalar field equations I: main results`
- https://arxiv.org/abs/0805.3880 — `# Title:The Formation of Black Holes in General Relativity`
- https://arxiv.org/abs/2205.14808 — `# Title:Wave equations estimates and the nonlinear stability of slowly rotating Kerr black holes`
- https://arxiv.org/abs/2104.11857 — `# Title:Kerr stability for small angular momentum`
- https://arxiv.org/abs/2506.21183 — `# Title:Linear stability of Kerr black holes in the full subextremal range`
- https://arxiv.org/abs/1207.3167 — `# Title:Weyl fluid dark matter model tested on the galactic scale by weak gravitational lensing` (**does not match SRC-043; wrong ID**)
- https://arxiv.org/abs/1207.3164 — `# Title:Construction of Cauchy Data of Vacuum Einstein field equations Evolving to Black Holes` (correct Li–Yu ID)
- https://arxiv.org/abs/2002.02740 — `# Title:A general formalism for the stability of Kerr`
- https://arxiv.org/abs/2508.06620 — `# Title:Conditional non-linear stability of Kerr-de Sitter spacetimes in the full subextremal range`
- https://arxiv.org/abs/2409.05700 — `# Title:Regularity of the Future Event Horizon in Perturbations of Kerr`
- https://arxiv.org/abs/gr-qc/0307013 — `# Title:The interior of charged black holes and the problem of uniqueness in general relativity`
- https://arxiv.org/abs/gr-qc/0309115 — `# Title:A proof of Price's law for the collapse of a self-gravitating scalar field`
- https://arxiv.org/abs/1702.05715 — `# Title:Strong cosmic censorship in spherical symmetry for two-ended asymptotically flat initial data I. The interior of the black hole region`
- https://comptes-rendus.academie-sciences.fr/mecanique/articles/10.5802/crmeca.284/ — `Weak cosmic censorship, trapped surfaces, and naked singularities for the Einstein vacuum equations`
- https://inspirehep.net/api/literature/2743272 — `"Naked Singularity Censoring with Anisotropic Apparent Horizon"`
- https://inspirehep.net/api/literature/841287 — `"On the formation of trapped surfaces"`
- https://inspirehep.net/api/literature/786592 — `"The Formation of Black Holes in General Relativity"`
- https://inspirehep.net/api/literature/33714 — `"Universality and scaling in gravitational collapse of a massless scalar field"`
- https://inspirehep.net/api/literature/1685783 — `"Strong cosmic censorship: taking the rough with the smooth"`
- https://inspirehep.net/api/literature/1674350 — `"Rough initial data and the strength of the blue-shift instability on cosmological black holes with Λ > 0"`
- https://inspirehep.net/api/literature/1469117 — `"The global non-linear stability of the Kerr–de Sitter family of black holes"`
- https://inspirehep.net/api/literature/1637357 — `"Global Nonlinear Stability of Schwarzschild Spacetime under Polarized Perturbations"`
- https://inspirehep.net/api/literature/1629145 — `"A robust proof of the instability of naked singularities of a scalar field in spherical symmetry"`
- https://inspirehep.net/api/literature/1628972 — `"Instability of spherical naked singularities of a scalar field under gravitational perturbations"`
- https://inspirehep.net/api/literature/2168006 — `"A Construction of Approximately Self-Similar Naked Singularities for the Spherically Symmetric Einstein-Scalar Field System"`
- https://inspirehep.net/api/literature?q=title%20%22Construction%20of%20Cauchy%20data%20of%20vacuum%20Einstein%20field%20equations%22 — hit title `"Construction of Cauchy Data of Vacuum Einstein field equations Evolving to Black Holes"`, `arxiv_eprints: 1207.3164`
- https://api.crossref.org/works/10.4007/annals.2015.181.2.6 — `"title":["Construction of Cauchy data of vacuum Einstein field equations evolving to black holes"]`
- https://api.crossref.org/works/10.4007/annals.2023.198.1.3 — `"title":["Naked singularities for the Einstein vacuum equations: The exterior solution"]`
- https://api.crossref.org/works/10.4007/annals.2025.201.3.3 — `"title":["Naked singularity censoring with anisotropic apparent horizon"]`

## Hard failures (accepted-entry rule only)

Rule applied: an entry with `status: accepted` must not carry a source whose only verification is bibliographic metadata (`verification.evidence_type == "metadata"`).

1. **D-001** (accepted, `entry_kind: conjecture`) lists **SRC-011** (Penrose 1969, INSPIRE recid 54979) — `evidence_type: "metadata"`, evidence is a title/venue/DOI record only.
2. **T-105** (accepted, `entry_kind: theorem`) lists **SRC-067** (Crossref record for Ann. of Math. 201(3)) — `evidence_type: "metadata"`; added to the entry during this review.
3. **T-208** (accepted, `entry_kind: counterexample_candidate`) lists **SRC-068** (Crossref record for Ann. of Math. 198(1)) — `evidence_type: "metadata"`; added to the entry during this review.

Boundary conditions on these three, stated precisely: in each case the mathematical statement is separately covered by an abstract-level source (D-001←SRC-001; T-105←SRC-044; T-208←SRC-002/SRC-003), so **no in-scope accepted entry rests on metadata alone for its theorem text**. These are the only accepted in-scope entries carrying a metadata-only `source_id`. Also: SRC-001/SRC-002/SRC-003 have `evidence_type` absent/empty in both the JSONL and `citation_audit.csv` while carrying real abstract quotes — a schema gap, not a metadata-only violation. T-102's metadata-only SRC-013 is not a violation because T-102 is `provisional`.

Separate citation-integrity defect (not an accepted-entry-rule violation): **T-203/SRC-043 carries the wrong arXiv ID 1207.3167** (an unrelated dark-matter lensing paper); the correct ID is 1207.3164. The entry self-flagged the ID as unverified, but the ID is still wrong in the source record and in `citation_audit.csv`.
