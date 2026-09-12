# WCC/SCC primary-source theorem ledger — final report (L0/L1)

**Author:** lead-literature · **Session:** 2026-09-11 23:17 → 2026-09-12 (four-hour envelope, checkpoints 01–05) · **Status:** L0/L1 active; class semantics pending G-F0
**Canonical artifacts:** `ledger/theorems.jsonl` (62 entries: 50 accepted, 11 provisional, 1 rejected-as-superseded) · `ledger/citation_audit.csv` (95 sources)
**Current hashes:** L0 `7d78d2850b5577f8…` · L1 `0b72b4190667fc81…` (rebuild after each change; see `MANIFEST.json`)

---

## 1. What was delivered

| Artifact | Content |
|---|---|
| `ledger/theorems.jsonl` (L0) | 62 entries: 50 accepted, 11 provisional, 1 rejected-as-superseded. Every row carries `source_ids`, `statement_exact`, `assumptions`, `class_ids` (four frozen classes only), `ledger_tags`, `informs_classes`, `does_not_imply`, `falsifiers`, `status`, `evidence_level`, `verification_status` ∈ {unverified, abstract-read, full-text, page-checked} (currently 61 abstract-read, 1 unverified, 0 full-text/page-checked). |
| `ledger/citation_audit.csv` (L1) | 95 sources, all locator-resolved. Columns include locator, resolver result, verification method, exact locator, canonical evidence_url, elided-quote flag, mirror_of anchor, evidence excerpt, class mapping, assessment (assessed/not_assessed + reason), verdict, reviewer. |
| `artifacts/literature/falsifiers.md` | Falsifier matrix per class and per entry. |
| `artifacts/literature/unresolved.jsonl` | Machine-readable unresolved register (sources + entries). |
| `artifacts/literature/classes/*.md` | Four class dossiers (frozen class IDs), with an "informing evidence" section from `informs_classes`. |
| `artifacts/literature/LITERATURE_STATUS.md` | Human-facing class status card with confidence and open items. |
| `artifacts/literature/GENERICITY_MAP.md` | Maps every genericity claim in the ledger into (or explicitly outside) the F1/F2 controlled vocabulary. |
| `artifacts/literature/EVIDENCE_GRAPH.md` | Per-class support/refute/sub-case graph for the four frozen classes. |
| `artifacts/literature/reviews/lead-doi-sweep.md` | Lead-run Crossref sweep: 33 DOI checks, 33/33 match; closed the Christodoulou 2009 monograph DOI and located the Chruściel 1992 SCC paper. |
| `artifacts/literature/L0_L1_ACCEPTANCE.md` | Machine check of the Astra L0/L1 assignment acceptance criteria; both PASS (62 rows, 95 audit rows). |
| `artifacts/literature/ASTRA_COMPLIANCE.md` | Compliance note for controller directives `astra-w07adj-02`, `astra-fetch-07`, and the L0/L1 assignment cards, plus the F1/F2 binding table. |
| `artifacts/literature/reviews/` | Independent reviews A (scalar/vacuum), B (SCC), C2 (post-change) and C (citation integrity), plus worker-08 and worker-09 L1 integrations, the lead DOI sweep, and the lead adjudication with fixes. |
| `artifacts/literature/proposed_map_changes.json` | Proposal for Astra (map node updates, evidence-level policy, cross-group edges). |
| `artifacts/literature/checkpoints/checkpoint-0{1..4}.md` | Checkpoint trail. |

## 2. Method and evidence standard

- **Primary-source verification only.** Every non-metadata source carries a verbatim quote from a directly fetched page (arXiv abs/API, INSPIRE mirroring publisher abstracts, Crossref, OpenAlex with a cross-check) plus fetch timestamp and URL. A claim is `accepted` only if at least one abstract-level source's quote entails its `statement_exact`; metadata-only sources are bibliographic anchors only and are enumerated in `MANIFEST.json`.
- **Fail-closed builder.** `tools/build_literature.py` refuses to emit if an accepted entry lacks an abstract-level source, if any `class_ids` token is outside the four frozen classes, if a falsifier or assumption is missing, or if a cited source is unknown/unresolved.
- **Four-class compliance.** `class_ids` ∈ {AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH}; all extension labels are `ledger_tags` (`tag_index.md`), cross-class relevance is `informs_classes`.
- **Evidence level.** Every entry is labelled peer-reviewed / accepted-in-press / preprint / numerical (44/2/13/2 currently; 1 metadata-only) so preprints cannot be read as established.
- **Rejection discipline.** Wrong IDs and overstated claims found by review were corrected, not hidden: SRC-043 (arXiv 1207.3167 → 1207.3164), SRC-066/089 (JFA pages 2189-2235 → 1948-1995), T-101 conclusion inflation, D-002 inverted statement, empty-set or metadata-only accepted rows.
- **Channels rejected.** Publisher HTML (APS/JSTOR/IOP/Annals) is Cloudflare-blocked; zbMATH returns 403; OpenAlex abstracts are accepted only with a second channel (its Penrose-1965 abstract is contaminated with an unrelated cosmic-ray text); shell network is blocked so all retrieval used the platform web tools.

## 3. Findings by class (see `LITERATURE_STATUS.md` for the full card)

- **AF-WCC-VAC-GEN — open.** Positive evidence is a chain of special/perturbative results: short-pulse trapped-surface formation (Christodoulou 2009; Klainerman-Rodnianski 2012), complete AF data evolving to a trapped surface (Li-Yu 2015), complete I+ near Schwarzschild (DHRT 2021 preprint), polarized perturbations (Klainerman-Szeftel), nonlinear slowly rotating Kerr (GKS/KS preprints), and now a 2026 preprint claiming full-subextremal nonlinear Kerr stability (Hintz). Non-generic vacuum naked-singularity constructions exist (RSR 2023 Ann. Math. + interior preprint). No generic WCC theorem.
- **AF-SCC-C2-VAC-GEN — covered at preprint level for generic rotating interiors; no peer-reviewed full-AF Cauchy theorem.** Luk-Sbierski 2026 prove a weak null singularity forms in generic rotating vacuum interiors, C^0-extendible but not Lipschitz-extendible; Sbierski (Invent. Math., accepted) supplies the symmetry-free Lipschitz criterion. Model-class benchmarks: Luk-Oh C² SCC for spherical EM-scalar two-ended AF (open weighted C¹ / dense weighted C^∞); Ringström 2009 T³-Gowdy C²-inextendibility.
- **AF-SCC-C0-VAC-GEN — refuted at preprint level in the Kerr-like corner.** Dafermos-Luk 2025 (Ann. Math.) prove C^0 extension across a non-trivial Cauchy-horizon piece; the antecedent (Kerr exterior stability) is claimed in the 2026 Hintz preprint. Caveats: characteristic/interior data, assumed bounds, peer review pending.
- **AF-WCC-SCALAR-SPH — WCC holds in a rough framework; naked singularities are non-generic.** The chain Christodoulou 1994 → 1999 → Liu-Li 2018 → Li-Liu 2022 → An 2025 (Ann. Math.) coexists with topology-specific or fine-tuned counter-currents (Choptuik 1993 numerical threshold; Zheng 2026 Hölder-topology stability; Singh 2025 non-generic stable perturbations; An-Wu 2026 non-spherical preprint). "Stable" in those papers must never be read as "generic".

## 4. The 2026 updates that changed the map

1. **Luk-Sbierski, arXiv:2604.04877** (Apr 2026): nonlinear vacuum, strictly rotating subextremal Kerr; weak null singularity; metric C^0- but not Lipschitz-extendible.
2. **Sbierski, arXiv:2409.18838**: C^{0,1}_loc-inextendibility of weak null singularities without symmetry; accepted, Inventiones Mathematicae.
3. **Hintz, arXiv:2606.28253 + companions 2606.27658, 2606.28008** (Jun–Aug 2026): claims nonlinear stability in the full subextremal Kerr range.

Consequence: `AF-SCC-C2` moved from "no theorem located" to preprint-level coverage; `AF-SCC-C0`'s refuted corner extends to the full subextremal range at preprint level. Two are preprints (T-526, T-528) and one is accepted-in-press (T-527, Inventiones); the ledger labels each with `evidence_level`, and Astra is asked not to promote class nodes without a preprint-evidence policy.

## 5. Adversarial review chain

- **A (scalar/vacuum WCC):** 3 hard failures + 3 partials; fixed (wrong arXiv ID, metadata-only accepted rows, conclusion inflation in T-101, class-tag inflation).
- **B (SCC):** 6 partials + 1 hard failure; fixed (inverted D-002 sentence, T-503 overstatement, wrong JFA pages, vacuum class tags on matter/test-field results, attribution audit).
- **C2 (post-change):** 5 hard failures, all stale-text/wrong-batch defects; fixed. Verdicts on the corrected items: fix-confirmed (SRC-043, SRC-089, D-002, tag mechanism, T-526/527/528).
- **C (citation integrity, 95-source DOI/URL spot-check):** report landed at `reviews/citation-integrity-C.md`; all actionable findings applied (SRC-041 split, exact quotes restored, mirror anchors, three published DOIs independently re-verified before adoption).
- **D (dossier consistency):** 4 hard failures, all documentation-count/staleness mismatches; fixed (T-527 accepted-in-press wording, both Hintz companions, 95 audit rows, tag-derived supporting counts, hashes).
- **Independent checks by the reviewers confirmed:** SRC-043 = arXiv:1207.3164; SRC-089 = JFA 271(7) 1948-1995; D-002 correction; T-526 "continuously extendible but not Lipschitz extendible" verbatim; T-527 Inventiones acceptance comment; T-528 full-subextremal statement verbatim and correctly flagged preprint.

## 6. Unresolved register (headline)

1. G-F0 has not passed; class semantics remain provisional even though F1/F2a/F2b are frozen (FROZEN.json rev 5).
2. C²/C⁰ formulation origin texts: SRC-092 (Christodoulou 1999 CQG) metadata-only; SRC-090 is now locator-verified (Chruściel, Contemp. Math. 132, 235-273, 1992, DOI 10.1090/conm/132/1188443) but its content is unread, so the "Chruściel version" still has no verified defining text.
3. C⁰ attribution: three accessible primary quotes say "Christodoulou's C⁰ formulation"; Dafermos-Luk say "of Penrose" (ambiguous possessive).
4. Christodoulou 1994/1999 theorem bodies not extracted (function space/quantifier unknown); T-101/T-102 provisional.
5. Peer review of the 2026 vacuum SCC/Kerr results.
6. Penrose 1969 wording; Ringström 2009 published page; Liu-Li arXiv:1710.02922 is now locator-verified (its abstract does not state a BV class, so the BV restatement stays unconfirmed).
7. Three explicitly not-assessed sources with reasons (SRC-090, SRC-092, SRC-093) — no silent gaps.

## 7. Handoff for the next session

- Re-run `python3 artifacts/literature/tools/build_literature.py` after any edit; it fails closed and rewrites the manifest with fresh hashes.
- To change an entry, look it up by `theorem_id` across **all** `theorems/batch-*.jsonl` files (an earlier fix silently no-op'd on the wrong batch; reviewer C2 caught it).
- Do not add class tokens outside the four; put labels in `ledger_tags`. New classes require Human-PI approval.
- If G-F0/F1/F2 hashes change, re-bind the four class dossiers to the new FROZEN.json hashes and record the re-check.
- The fastest legitimate upgrades: peer review landing for T-526/T-528; a library fetch of Christodoulou 1994/1999 and Chruściel 1991; an F1 decision on whether characteristic interior data discharge the AF class.

## 8. Checkpoint log

| Checkpoint | Time (+08) | Counts | Notes |
|---|---|---|---|
| 01 | 23:27 | 56 sources / 43 entries | first full build VALID; worker-07 batch quarantined and 3 IDs merged |
| 02 | 23:30 | 65/47 | DOIs, Price's law, Kerr-stability status bounded |
| 03 | 23:34 | 77/57 | Gowdy promotion, scalar chain, OpenAlex contamination found |
| 04 | 23:39–23:59 | 93/62 | 2026 SCC/Kerr preprints; A/B adjudication; four-class compliance; coverage directive closed |
| 05 | 00:22 | 93/62 | C2 fixes applied; lead DOI sweep 33/33; all sources locator-resolved; reviewer C pending at report time |
