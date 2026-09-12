# Lead adjudication of adversarial reviews A and B

- Adjudicated: 2026-09-11 ~23:45 (+08) by lead-literature
- Review inputs: `reviews/adversarial-A.md`, `reviews/adversarial-B.md` (independent subagents, pinned snapshots)
- Policy: an accepted entry must have at least one abstract-level source whose quote entails `statement_exact`; metadata-only sources may appear only as bibliographic anchors and are listed in `MANIFEST.json:counts.accepted_with_metadata_anchors`. Publication status is carried by `entry_kind`/`status`, not by `conclusion_type`.

## Hard failures found and dispositions

| # | Finding | Disposition |
|---|---|---|
| A1 | Accepted entries carried metadata-only sources (D-001→SRC-011; T-105→SRC-067; T-208→SRC-068; also T-501→SRC-020) | **Fixed structurally**: builder now fails if an accepted entry has *only* metadata sources; metadata anchors on accepted entries are enumerated in the manifest (7→9 entries, each with abstract-level support). T-501's SRC-020 replaced by Crossref SRC-060. |
| A2 | T-203/SRC-043 wrong arXiv ID (1207.3167 = unrelated lensing paper) | **Fixed**: SRC-043 re-fetched; correct ID 1207.3164; correction recorded in the source note. |
| A3 | T-101 conclusion inflation ("bounded-variation-type", "generic") | **Fixed**: statement reworded to "sufficiently rough perturbations in a rough functional framework"; status demoted to provisional; precise function space added to unresolved. |
| A4 | D-006 presented as formal_model though it is a cross-paper synthesis; SRC-014 does not support it | **Fixed**: entry_kind = methodological_inference; label marks it as lead synthesis; SRC-014 removed from sources. |
| A5 | Class-tag inflation: T-105 (scalar) and T-207 (Λ>0) tagged AF-WCC-VAC-GEN | **Fixed**: vacuum tags removed; classification now uses `class_ids` (what the statement is about) plus `informs_classes` (cross-references), rendered as an "Informing evidence" section in each class dossier. |
| A6 | Stale T-105 DOI caveat, T-208 unresolved L1 item | **Fixed**. |
| B1 | D-002 contained an inverted sentence ("whether C^0 extensions exist at all" resolved negatively) | **Fixed**: C^0 extensions *exist*; what fails is C^0-*inextendibility*. Rewritten. |
| B2 | T-503 overstated SRC-029 (extension attributed to open sets rather than the no-mass-inflation regime) | **Fixed**: statement restricted to the no-mass-inflation decay regime. |
| B3 | T-511/SRC-066 wrong JFA pages (2189-2235 vs 1948-1995) | **Fixed**: Crossref SRC-089 added; page range corrected. |
| B4 | T-511 carried a vacuum class tag for a linear test-field result | **Fixed** (see A5 mechanism). |
| B5 | Eight matter/test-field entries carried vacuum class tags (T-304, T-306, T-501, T-505, T-506, T-510, T-511, T-514) | **Fixed** (A5 mechanism): all moved to `informs_classes`. |
| B6 | Attribution: ledger said "3-1 for Christodoulou" but its unresolved item pointed at an unevidenced Penrose 1974 lecture; D-002 listed SRC-005/SRC-049 which do not state the C^0 formulation | **Fixed**: D-002 sources = SRC-004 (Penrose possessive) + SRC-021/056/061 (Christodoulou) + SRC-072 (Penrose attribution in the 2003 abstract); Penrose 1974 pointer removed; unresolved text rewritten to state the split over accessible quotes only. |
| B7 | T-515 said "is proved" about unreviewed preprints | **Fixed**: label/statement now say "claimed in preprints"; peer-review watch item added. |
| B8 | T-306/T-304 conclusion_type "theorem" on entry_kind "preprint_result" | **Clarified**: publication status lives in entry_kind/status; T-304 set to conditional_theorem (it is conditional on the blow-up hypothesis); T-306 keeps theorem + preprint caveat. |

## Gaps closed by the reviewers' independent fetches

- Luk-Oh Part I published: Ann. of Math. 190(1), 1-111 (2019), DOI 10.4007/annals.2019.190.1.1 (SRC-086).
- Sbierski 2022 Duke: DOI 10.1215/00127094-2022-0040, Duke Math. J. 171(14) (SRC-087).
- SRC-033 = arXiv:1805.08764 (SRC-088).
- Luk-Sbierski JFA: 271(7), 1948-1995 (SRC-089).
- New unresolved candidate for the "Chrusciel version": Chrusciel 1991, Proc. Centre Math. Appl. Austral. Nat. Univ. 27 (SRC-090, unresolved, not citable yet).

## Not accepted

- Reviewer A's suggestion to demote T-101 to provisional was accepted; the reworded statement is now source-faithful.
- Reviewer B's systemic concern was accepted in the stronger form: `class_ids` now means "the statement is about this class", and cross-class relevance is explicit in `informs_classes`.

## Residual risk

Both reviews pinned earlier ledger hashes; the ledger has since changed (2026 SCC entries T-526..528, the fixes above). A third reviewer (citation integrity) is still running, and a final post-change re-check is queued for checkpoint 05. Until then, the class dossiers should be read with `unresolved.jsonl`.

---

## Addendum — post-change review C2 (2026-09-12 00:05 +08)

Reviewer C2 (`reviews/post-change-C2.md`) audited the corrected ledger against live sources after the reviewer-A/B fixes. Verdicts: SRC-043 correction, SRC-089 page range, D-002 rewording, class-tag mechanism, and the three 2026 entries all **fix-confirmed** against live fetches; five hard failures remained because the fixes were applied to the wrong batch for some IDs or stale text survived.

| # | C2 finding | Disposition |
|---|---|---|
| C2-1 | T-518 still asserted JFA pages 2189-2235 | **Fixed**: T-518 now cites SRC-089 and states 1948-1995; the old value survives only inside explicit correction notes. |
| C2-2 | T-515/T-301/T-206 still said full-subextremal nonlinear Kerr stability was not located, contradicting T-528 | **Fixed**: T-515 rewritten with the Hintz 2026 preprint and both companions; T-301 and T-206 updated. Root cause recorded: an earlier fix script targeted T-515 in the wrong batch file and silently no-op'd. |
| C2-3 | Self-contradictory caveats in T-510, T-506, T-501 | **Fixed**; T-506 evidence_level upgraded to peer-reviewed (Duke 2022 confirmed by SRC-087). |
| C2-4 | T-514 venue item closed by SRC-086 but unlinked | **Fixed**: SRC-086 is in T-514's source_ids; next_action updated. |
| C2-5 | T-101 `regularity` still claimed bounded variation | **Fixed**: replaced with the honest "function space not extracted" plus the review's Liu-Li restatement pointer as an unverified note. |
| C2-6 | T-505 cross-linked Gautam 2024 (EM-scalar) to an EM-Klein-Gordon entry | **Fixed**: model-mismatch warning added; SRC-052 removed from any transfer suggestion. |

Process lesson (recorded for the next session): when a fix must touch an entry, look it up across all batch files by `theorem_id`; never assume the batch the entry was first written in.

---

## Addendum — citation-integrity review C (2026-09-12 00:35 +08)

Reviewer C (`reviews/citation-integrity-C.md`) audited a 93-record snapshot: 46 Crossref DOIs, 20 DataCite DOIs, 16 live page fetches, duplicate/impossible-metadata/quote-liftability screens. Findings and dispositions:

| # | C finding | Disposition |
|---|---|---|
| C-1 | **SRC-041 DOI mismatch**: 10.1142/9789814374552_0002 is the MG12 conference chapter (2012, pp. 24-34), not the 2009 EMS Monograph it was headlined as | **Fixed**: SRC-041 is now explicitly the MG12 conference chapter; the Monograph is SRC-054 (arXiv) + DOI 10.4171/068 (Crossref-verified). T-201 updated. |
| C-2 | SRC-050 pages 1-56 vs Crossref 363-411 | **Fixed**: AHP 24, 363-411 (2023). |
| C-3 | SRC-025 year 2020 vs publisher 2021 | **Fixed**: CMP 382, 1263-1341 (2021). |
| C-4 | SRC-011 DOI is the 2002 GRG reprint | **Annotated**: year 1969 kept for the original; reprint relationship stated. |
| C-5 | SRC-069 title spelling | **Fixed**: "polarised Gowdy spacetimes" per Crossref. |
| C-6 | SRC-022 online 2017 vs print 2018 | **Annotated**. |
| C-7 | 11 duplicate clusters / 23 records | **Annotated, not deleted**: each secondary anchor now carries `mirror_of` pointing at its canonical record (`citation_audit.csv` column added). These are deliberate arXiv/Crossref/OpenAlex anchor pairs, not accidental duplicates. SRC-041/SRC-054 is a related-publication pair, not a mirror. |
| C-8 | 28 records with non-reproducible verification pages; 13 composite metadata strings; SRC-071/072 are machine reconstructions | **Fixed structurally**: every verified source now carries a canonical `evidence_url`; quotes containing elisions are flagged `elided_quote=true` in the audit CSV; OpenAlex reconstructions stay scope-only and are labelled in their notes. The underlying limitation (some `page` fields were query URLs) is now explicit rather than hidden. |
| C-9 | Material quote deviations SRC-016, SRC-025, SRC-046 | **Fixed**: quotes replaced with exact publisher/arXiv abstract text (ASCII transliteration noted where symbols are involved). |
| C-10 | Missing published DOIs: SRC-051, SRC-038, SRC-058 | **Fixed after independent Crossref verification by the lead**: SRC-051 → 10.1090/tran/8957 (TAMS 2023); SRC-038 → 10.23943/princeton/9780691212425.001.0001 (AMS-210, 2020, ISBN 9780691212425); SRC-058 → 10.1007/s40818-019-0062-7 (Ann. PDE 5, 2019). T-205 promoted to accepted; T-514 venue item closed. |
| C-11 | SRC-081/SRC-085 acceptance claims confirmed; SRC-043/SRC-066 in-flight fixes confirmed | **Retained**. |
| C-12 | Not completed: direct paywalled publisher pages; SRC-067/SRC-086 page ranges; SRC-038 series volume | **Recorded as residual audit limits**; page ranges remain unverified where Crossref lacks them. |

Net effect: 0 wrong-paper DOIs remain; all mirror pairs are explicit; quote liftability is machine-visible; accepted count 50 (T-205 promoted on now-verified book metadata and its abstract).

---

## Self-audit addendum — missing `evidence_type` on nine legacy records (2026-09-12 00:47 +08)

While spot-checking the L0 `verification_status` derivation, the lead found that nine source records written in the first two batches (SRC-001..SRC-009 range) had no `verification.evidence_type` field. Consequences and fix:

- The metadata-only source count and the derived L0 verification levels were skewed: entries whose evidence was an abstract quote could be reported as `unverified`.
- Fix: all nine records classified from their evidence text (`INSPIRE recid`/`Crossref record` prefixes → metadata; otherwise abstract). No quote or locator changed.
- After the fix: L0 verification = 61 abstract-read, 1 unverified (D-009, a provisional background entry with metadata-only sources), 0 full-text/page-checked; metadata-only sources = 14.
- Lesson for the next session: the builder derives two fields from `evidence_type`; any new source record must set it explicitly, and `build_literature.py` should be extended to fail when a verified record lacks it. (Not yet implemented — recorded as a tooling TODO.)

---

## Addendum — dossier-consistency review D (2026-09-12 00:00 +08, post-freeze)

Reviewer D (`reviews/dossier-consistency-D.md`) checked the derived documents against the machine ledger. It passed everything structural — exact per-class membership (11/10/11/10), all 42 rendered statements byte-identical to the JSONL, verbatim field rendering, falsifier completeness, and internal MANIFEST/CSV/JSONL consistency — and found only documentation mismatches:

| # | D finding | Disposition |
|---|---|---|
| D-1 | Docs called all three 2026 results "preprints" while T-527 is accepted-in-press (Invent. Math.) | **Fixed** in both LITERATURE_STATUS and FINAL_REPORT. |
| D-2 | Status card said Hintz's second companion was not located | **Fixed**: SRC-091 located and verified (the earlier fix had edited the wrong numbered item; caught by D and by the lead's mechanical re-check). |
| D-3 | FINAL_REPORT still cited "93 audit rows"/"93-source" and stale hashes | **Fixed**: 95 rows and the frozen hashes `7d78d285`/`0b72b419`. |
| D-4 | Supporting-class counts did not match ledger tags (4 vs 3; 15 vs 21; 8 vs 9) | **Fixed**: counts now derived from ledger tags (BH-FORMATION 3, NS-CONSTRUCTION 3/2, OTHER-MODELS 24/21, DEFINITIONS 9), and the archived class tokens are explicitly marked as not classes. |
| D-5 | Provisional T-304 listed under "strongest verified results"; T-514/T-520 presented as class members | **Fixed**: section now says "tag-level (not class members)" and marks T-304 provisional/preprint. |
| D-6 | "2 not-assessed + 1 content-unread" vs "three not-assessed" wording | **Fixed**: 3 not-assessed rows, described precisely. |

The canonical ledger hashes did not change during this addendum (documentation-only edits after the freeze); `FREEZE.md` therefore still describes the frozen revision.
