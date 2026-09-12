# Dossier consistency review (Reviewer D) — derived docs vs machine ledger

**Reviewed revision (final stamp, 2026-09-11 23:54 +08).** The tree was rebuilt four times while this
review ran (23:49, 23:50, 23:51, 23:54); the checks below were re-run after each rebuild. The final
stamp is the 23:54 revision; all findings are against these files:

| file | sha256 (first 20) | mtime |
|---|---|---|
| `ledger/theorems.jsonl` | `7d78d2850b5577f82e38` | 23:54:55 |
| `ledger/citation_audit.csv` | `0b72b4190667fc812528` | 23:54:55 |
| `artifacts/literature/MANIFEST.json` | `eba963a3c05c5997782f` | 23:54:55 |
| `artifacts/literature/LITERATURE_STATUS.md` | `562b218a8bb6ca012943` | 23:51:43 |
| `artifacts/literature/FINAL_REPORT.md` | `f992e76a9025c07cc407` | 23:54:30 |
| `artifacts/literature/L0_L1_ACCEPTANCE.md` | `8764de76743f20e2f347` | 23:54:34 |
| `classes/AF-WCC-VAC-GEN.md` | `c026dd4db3fa423a8931` | 23:54:55 |
| `classes/AF-SCC-C2-VAC-GEN.md` | `cc7bc9abf8612b721835` | 23:54:55 |
| `classes/AF-SCC-C0-VAC-GEN.md` | `30edba60336fcf84b8aa` | 23:54:55 |
| `classes/AF-WCC-SCALAR-SPH.md` | `9a174b8ebd65e6f897dd` | 23:54:55 |

Machine state used: JSONL 62 entries (50 accepted / 11 provisional / 1 rejected, line 43 `T-513`);
evidence levels 44 peer-reviewed / 2 accepted-in-press / 13 preprint / 2 numerical / 1 metadata-only;
L0 verification 1 unverified / 61 abstract-read; CSV 95 rows, 95 `verified`; MANIFEST counts
95 sources / 62 entries / 50 accepted, and every `artifacts.*` hash matches the file on disk.
**Caveat:** the builder is still being re-run by the lead; if any stamped file moves again, findings
1–5 must be re-checked (each rebuild regenerates dossiers, MANIFEST and hashes).

## Findings

| # | Location | Expected (JSONL / MANIFEST / CSV) | Found | Verdict | Recommended action |
|---|---|---|---|---|---|
| 1 | `LITERATURE_STATUS.md:7` and `FINAL_REPORT.md:50` | `T-527` (JSONL line 59) `evidence_level=accepted-in-press`; MANIFEST `accepted-in-press: 2` | "All three are **preprints**; peer review is pending" / "All three are preprints and are labelled as such", immediately after both docs say Sbierski is "accepted, Invent. Math." | **mismatch (hard)** | Replace "three preprints" with "two preprints + one accepted-in-press (T-527)". |
| 2 | `LITERATURE_STATUS.md:76` | `T-528` (line 60) scope: "Relies on two companion preprints, **both now located** (SRC-079, SRC-091)"; CSV verifies SRC-079 and SRC-091 | "T-528 (Hintz 339pp + companions; **second companion not located**)" | **stale (hard)** | Delete "second companion not located"; SRC-091 (arXiv:2606.28008) is verified in the CSV. |
| 3 | `FINAL_REPORT.md:22`, `:57` | CSV has 95 rows; MANIFEST `sources: 95`, `verified_sources: 95`; `L0_L1_ACCEPTANCE.md:4` already updated to "95 for 95 sources" | "both PASS (62 rows, **93 audit rows**)"; "**93-source** DOI/URL spot-check" | **stale (hard)** | Update both remaining 93s to 95; the acceptance file is already fixed. |
| 4 | `LITERATURE_STATUS.md:62` | No `AF-WCC-VAC-BH-FORM` token exists in `ledger_tags`; nearest tag `BH-FORMATION` = 3 accepted (`T-201`, `T-202`, `T-203`); `archive/AF-WCC-VAC-BH-FORM.pre-four-class.md:5` says "3 accepted" | "`AF-WCC-VAC-BH-FORM`: **4 accepted** trapped-surface formation theorems" | **mismatch (hard)** | Enumerate the 4th entry or correct to 3 and align the group name with a real ledger tag. |
| 5 | `FINAL_REPORT.md:5` | MANIFEST `generated_at 23:54:55` records L0 `7d78d2850b5577f8…`, L1 `0b72b4190667fc81…` | "**Current hashes:** L0 `87d9b6cc85ae8d06…` · L1 `a8b33aa66ff2c386…`" (the previous revision's hashes) | **stale (hard)** | Re-quote the current L0/L1 hashes (or drop the line and point only at `MANIFEST.json`). |
| 6 | `LITERATURE_STATUS.md:64` | No `AF-SCC-OTHER-MODELS` token in `ledger_tags`; tag `OTHER-MODELS` = 24 rows, 21 accepted; archived pre-four-class dossier says 24 accepted / 4 provisional | "`AF-SCC-OTHER-MODELS`: **15 accepted** entries" | mismatch (not reproducible) | Define the group, or derive the count from `OTHER-MODELS` (21 accepted after the four-class split); 15 matches no ledger/tag/archive count. |
| 7 | `LITERATURE_STATUS.md:65` | Tag `DEFINITIONS` = 9 rows (`D-001`–`D-009`; 7 accepted, `D-004`/`D-009` provisional; `D-009` metadata-only background) | "`DEFINITIONS`: **8 entries**" | mismatch (wording) | Say "8 entries excluding metadata-only background `D-009`" or correct to 9. |
| 8 | `LITERATURE_STATUS.md:31` | `T-304` (line 26) `status=provisional`, `evidence_level=preprint`; `T-514`/`T-520` carry neither `AF-SCC-C2-VAC-GEN` in `class_ids` nor in `informs_classes` (tag-only `C2`) | `T-304` listed under "**Strongest verified results**" without a provisional flag; `T-514`/`T-520` presented as AF-SCC-C2 model-class results | mismatch (soft) | Add "[provisional/preprint]" to T-304; mark T-514/T-520 as tag-level (`C2`) evidence, not class members. |
| 9 | `LITERATURE_STATUS.md:33` | `T-527` is `accepted-in-press`; peer review is open only for T-526 | "Open items: Peer review of T-526/**T-527**" | stale | Drop T-527 from pending peer review (leave final volume/pages confirmation). |
| 10 | `LITERATURE_STATUS.md:3` vs `FINAL_REPORT.md:68` | CSV: 3 rows with assessment `not_assessed_in_this_run` (`SRC-090`, `SRC-092`, `SRC-093`); MANIFEST `unassessed_sources` = those 3 | STATUS: "2 explicitly not-assessed with reasons; 1 content-unread candidate"; REPORT: "Three explicitly not-assessed sources with reasons" | mismatch (wording) | Reword STATUS to "3 not-assessed (2 retrievability-blocked + 1 locator-verified content-unread)". |
| 11 | `FINAL_REPORT.md:57` | `reviews/citation-integrity-C.md` exists (23:49, 29 954 B) | "running at the time of writing; its report **will land** at `reviews/citation-integrity-C.md`" | stale (minor) | Past tense; note the report has landed and reviewer D is the remaining check. |
| 12 | `MANIFEST.json` counts | JSONL/CSV as above | sources 95, theorems 62, accepted 50, verified 95, metadata-only 14, evidence 44/2/13/2/1/0, L0 1/61/0/0, 11 metadata anchors, 3 unassessed, 0 extension tokens; every artifact hash matches | **consistent** | None. (Dict comparison against JSONL differs only by explicit zero-count keys `unresolved:0`, `full-text:0`, `page-checked:0` — not a defect.) |

## Checks that passed cleanly (machine-verified, no prose trusted)

- **Per-class membership (item 2): exact.** Dossier main sections = `class_ids` members for all four
  classes: AF-WCC-VAC-GEN 11, AF-SCC-C2-VAC-GEN 10, AF-SCC-C0-VAC-GEN 11, AF-WCC-SCALAR-SPH 10;
  zero omissions, zero extras, zero duplicates. Header counts match statuses
  (11 = 10 accepted + 1 provisional; 10 = 7 + 3; 11 = 9 + 2; 10 = 6 + 4).
  "Informing evidence" sections equal `informs_classes` exactly (C2: T-304/T-505/T-506/T-510;
  C0: T-306/T-501/T-511) with matching status/label/tags.
- **Statement fidelity (item 3): exhaustive.** All **42/42** dossier `Exact statement` texts are
  byte-identical to `statement_exact` in the JSONL — not just the 8-entry sample. Sample
  (2 per dossier): D-001, T-204 (WCC-VAC-GEN); D-003, T-526 (C2); D-002, T-301 (C0); T-103, T-524
  (SCALAR-SPH); all matched exactly, no truncation or reflow. Every other rendered field
  (label, status, evidence level, L0, conclusion type, sources, assumptions, scope caveats,
  does_not_imply, unresolved, falsifier bullets) is also verbatim-consistent with its JSONL row.
- **Contradictions inside dossiers (item 4): none.** All 42 heading statuses equal `status`;
  all 42 evidence-level/L0 lines equal `evidence_level`/`verification_status`. No dossier presents a
  provisional/preprint row as established, and no accepted row is presented as provisional.
- **Falsifier completeness (item 6): complete.** All 32 accepted dossier entries (10+7+9+6) carry
  ≥1 falsifier bullet; JSONL has zero empty `falsifiers` lists across all 62 rows.
- **Stale text attached to T-515/T-528/SRC-086/SRC-087 (item 5):** the four dossiers are clean.
  T-515/T-528 sections say both Hintz companions are located, matching JSONL lines 46/60 and CSV
  SRC-079/SRC-091. `SRC-086`/`SRC-087` appear nowhere in the dossiers/status card (CSV: `SRC-086`
  assessed to T-514, `SRC-087` to T-506, both verified). The only "NOT located" string
  (C0 dossier line 88) is the Dafermos-Luk promised interior-data retrieval and is a verbatim copy
  of `T-301.scope_caveats` — consistent, not stale.
- **Counts (item 1):** all headline ledger counts in both docs match the machine ledger
  (`LITERATURE_STATUS.md:3` 62/50/11/1 and 95 sources; `FINAL_REPORT.md:4` 62/50/11/1 and 95 sources;
  `FINAL_REPORT.md:33` 44/2/13/2 + 1 metadata-only; MANIFEST counts above; `L0_L1_ACCEPTANCE.md`
  62 L0 / 95 L1 rows and per-class coverage {11,10,11,10}).
  The only count mismatches are rows 3, 4, 6, 7 and 10 above.

## Hard failures (real contradictions only)

1. **T-527 is labelled a preprint with peer review pending** (`LITERATURE_STATUS.md:7`,
   `FINAL_REPORT.md:50`) while the JSONL (line 59) and MANIFEST record `accepted-in-press`
   (Inventiones), and both docs say "accepted, Invent. Math." in the same passage.
2. **`LITERATURE_STATUS.md:76` says the second Hintz companion is not located** while `T-528`
   (JSONL line 60) states both companions are now located (SRC-079, SRC-091) and the CSV verifies both.
3. **`FINAL_REPORT.md:22`/`:57` still say 93 audit rows / "93-source"** while the CSV and MANIFEST
   have **95** sources (`L0_L1_ACCEPTANCE.md` has already been corrected to 95).
4. **`AF-WCC-VAC-BH-FORM: 4 accepted`** (`LITERATURE_STATUS.md:62`) while the ledger tag
   `BH-FORMATION` and the archived pre-four-class dossier both have **3** accepted
   (T-201, T-202, T-203).
5. **`FINAL_REPORT.md:5` advertises stale "Current hashes"** (`87d9b6cc…`/`a8b33aa6…`) while the
   files and MANIFEST are at `7d78d285…`/`0b72b419…`.

## Limitations / checks not completed

- Citation content, DOI/URL resolution and quote fidelity were **not** re-checked (Reviewer C's scope);
  the CSV was used only for counts, statuses and `evidence_type`.
- FINAL_REPORT §5 review-chain counts (A: "3 hard + 3 partials", B: "6 partials + 1 hard", C2: "5 hard")
  were not recounted against `reviews/adversarial-A.md`, `adversarial-B.md`, `post-change-C2.md`.
- Checkpoint-log counts (56/43, 65/47, 77/57, 93/62, 93/62) were not verified against the
  checkpoint files; they are historical records, not current-state claims.
- The build was still running when this review began; findings 1–5 are valid for the stamped
  23:54 revision only and must be re-checked after any further rebuild.
