# Worker 09 — L1 SCC-side citation audit report

**Worker:** deepseek-flash-09 (execution worker 09, DeepSeek Flash breadth pool)
**Assignment:** `asg-2026-09-11-L1-deepseek-flash-09-18` — node **L1** (primary-source verification),
class IDs **AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN**, gate **G-LIT**.
**Task text:** "Web-verify SCC citations. Distinguish C0 from C2 explicitly."
**Acceptance:** locator + resolver result + exact theorem number/page + class mapping + verdict;
unresolved list is a valid output.
**Status:** second shard delivered; NOT a completion claim. Lead/audit adjudication required.
**Checkpoint 1:** 2026-09-11T23:38+08:00 (~23 min after start; fetch batch completed 23:33).
**Checkpoint 2:** 2026-09-11T23:52+08:00 (~37 min; P2 theorem-level extension + integration correction).

---

## 1. Deliverables

| artifact | sha256 | note |
|---|---|---|
| `ledger/citation_audit_scc_flash-09.csv` | `8bf87b41670f6e672d5e94620be4fe48e0e927f80477fe4657a6f63d524712fd` | 35 rich rows (31 sources + 4 controls), 17 theorem-level; self-check PASS |
| `ledger/citation_audit_scc_flash-09.jsonl` | `83bd7ba654198c93421581d3846dae922bd992042e5b5a9546df2260d2b3b4c0` | same rows, JSONL |
| `ledger/citation_audit_scc_flash-09.lead_schema.csv` | `2308648f3bdc5b269b35aa71271d8cd4ce549324fb7b4efb7c76e56ef7052f23` | 31-row projection in the lead's current 25-column schema |
| `artifacts/worker-09/extracted/scc_locator_sweep.json` | see file | independent 34/34 locator sweep (F8) |
| `ledger/citation_audit.csv` | `67df6d45cfd132b0f2d14a63d5ddbde38eeb4ac76fd6888d733a6f4ffc50a348` | **lead-frozen version restored** (see finding F6) |
| `artifacts/worker-09/sources/` | `fetch_manifest.tsv`, `fetch_manifest_p2.tsv` | 37 raw fetched files with HTTP status + sha256 |
| `artifacts/worker-09/extracted/` | — | metadata + numbered theorem segments per source |
| `artifacts/worker-09/merge_backups/` | — | four pre-merge canonical snapshots (85/95/93/93 rows) |

Reproduce: `bash artifacts/worker-09/fetch_sources.sh && bash artifacts/worker-09/fetch_sources_p2.sh && python3 artifacts/worker-09/extract_sources.py && python3 artifacts/worker-09/build_audit_shard.py && python3 artifacts/worker-09/merge_into_canonical.py --update-existing --dry-run`.

---

## 2. The C0 / C2 separation (the requested distinction)

The audit's central output is that **C0 and C2 statements must not be read off the same source**.
For each audited source, the regularity class of what is *proved* is recorded separately from the
class it is *mapped to*.

| source | what is proved | regularity | C0 SCC | C2 SCC | class mapping |
|---|---|---|---|---|---|
| Dafermos 2003 (Ann. Math. 158:875) | open set of spherical EM-scalar data: curvature blows up on a light-like future boundary yet the metric extends continuously beyond it (abstract) | C0 extendible; curvature blow-up | false (model) | not addressed | AF-SCC-OTHER-MODELS |
| Dafermos 2005 (CPAM 58:445), **Thm 1.2, Cor 1.3** | Hawking mass blows up along CH+; **no C1 extension**; SCC false in Christodoulou's formulation | C0 extendible / **C1-inextendible** | false | **not addressed** | AF-SCC-OTHER-MODELS |
| Luk–Oh 2017 (Duke 166:437), **Thm 1.1** | linear wave on *fixed* subextremal RN: generic data **not in W^{1,2}_loc** at CH+ | linear H¹/W^{1,2} obstruction | not addressed | not addressed (linear only) | AF-SCC-OTHER-MODELS |
| Van de Moortel 2018 (CMP), **Thms 1.2–1.5** | imports: C0 SCC **false**, C2 SCC **true** (EM-scalar, spherical); own: C0 stability + curvature blow-up | C0 vs C2 explicitly separated | false (imported) | true (imported) | AF-SCC-OTHER-MODELS |
| CGNS Part 3, 2017 (Ann. PDE 3:8), **Thms 2.1/2.3/3.1/4.1** | C0 extension with **square-integrable Christoffel symbols**; stronger decay → bounded ∇φ → non-isometric classical extensions; evidence against SCC for Λ>0 | C0 (+W^{1,2} connection), **below C1** | false-ish (Λ>0, model) | **not addressed** | AF-SCC-OTHER-MODELS |
| Sbierski 2018 (JDG 108:319), **Thm 4.9** | *maximal analytic* Schwarzschild is **C0-inextendible** (through the r=0 singularity) | C0 inextendibility of a completed extension | scope-caveated | n/a | AF-SCC-C0-VAC-GEN (scope-caveated) |
| Dafermos–Luk 2025 (Ann. Math. 202:309), **Thms 4.2/4.24, 16.14** | vacuum, Kerr-close interior data: MGHD is isometric to (U∞,g) and **the metric extends continuously up to CH+** | **C0 extendible**; no C2 claim; weak-null-singularity expectation | **false** (conditional on Kerr exterior stability) | not addressed | AF-SCC-C0-VAC-GEN |
| Van de Moortel 2020 (CMP 382:1263), **Thms A/B/C/D** | EMKG spherical: CH_{i+} is **C²-future-inextendible**; dynamical/static/mixed classification | **C2 inextendible** (model) | extendible (same model) | **true** (model) | AF-SCC-OTHER-MODELS |
| Luk–Oh Part I (arXiv:1702.05715), **Thms 1.3/1.4/1.5** | imports: C0 SCC **true** for neutral scalar (Christodoulou), **false** for EM-scalar; main theorem: **C2 SCC true** for EM-scalar | C0 vs C2 separated, model-dependent | false (EM-scalar) / true (neutral scalar) | **true** (EM-scalar) | AF-SCC-OTHER-MODELS |
| Luk–Oh Part II (arXiv:1702.05716), **Thm 1.1** | C² SCC with **explicit genericity topology** (open in weighted C¹, dense in weighted C^∞) | C², generic set | not addressed | **true** (model, generic set) | AF-SCC-OTHER-MODELS |
| Sbierski 2020 (arXiv:2007.12049), **Thms 4.30/4.31** | small generic spherical perturbations of RN (EM-scalar): BH interior and future development are **C^{0,1}_loc-inextendible** | **Lipschitz** inextendibility | extendible (C0) | stronger than needed for C0; weaker than C2 | AF-SCC-OTHER-MODELS |

**The regularity ladder (what the SCC axis actually is).** For the same spherical models the
verdicts are ordered:
**C0 extendible** (Dafermos 2003/2005; Van de Moortel 2018; CGNS 2017) →
**C^{0,1}_loc inextendible** (Sbierski 2020) →
**C² inextendible** (Luk–Oh Parts I/II; Van de Moortel 2020).
A source at one rung does not license a claim at another. For the **vacuum rotating** class
(`AF-SCC-C2-VAC-GEN`) the ladder's top rung remains supported only by preprints (ledger
`T-526`/`T-527`), which this shard does not independently verify.

**Rules this table enforces**

1. *Dafermos 2005 is not a C2 source.* It proves C1-inextendibility. The C2 statement for the same
   model comes from Luk–Oh Part I/II (ledger `T-514`) and Van de Moortel 2020 (`SRC-025`).
2. *Luk–Oh 2017 (Duke) is not a nonlinear SCC source.* It is a linear result on a fixed background;
   the H¹ obstruction is not a C2-inextendibility theorem.
3. *"Classical solutions" in CGNS Part 3 ≠ C2 regularity.* Their extension has L² Christoffel
   symbols, i.e. below C1; upgrading it to C2 inverts the paper's point.
4. *Sbierski 2018 concerns the maximal analytic extension, not the maximal development across a
   Cauchy horizon.* The CH is already inside M_max; his obstruction is the r=0 singularity. It does
   not conflict with Dafermos–Luk's C0 extendibility across CH+, and it does not establish C0 SCC
   for generic AF vacuum data (exact Schwarzschild is non-generic).
5. *Dafermos–Luk 2025 carries a conditionality* (Kerr exterior stability) in the paper's own
   wording. Ledger `T-301` already labels it `conditional_theorem`; the class mapping is sound, but
   any promotion to an unconditional refutation needs the companion stability results checked
   separately (ledger `T-515`).

---

## 3. Findings

**F1 (failure, high value). The assigned citation "Eardley–Gundlach" does not resolve.**
Five independent resolver queries found no jointly authored work:
Crossref `query.bibliographic="Eardley Gundlach critical phenomena"` (0/20 joint),
Crossref `query.author=Eardley` + critical phenomena (no joint), INSPIRE
`a D.M.Eardley and a C.Gundlach` (0 hits), OpenAlex title search (no Eardley record),
web search (only Eardley-only and Gundlach-only works).
Recorded as `W09-005`, verdict `citation_unsupported`, in the canonical audit as `unresolved`.
Nearest real works if critical-collapse coverage is wanted: **Eardley–Hirschmann 1995**
(PRD 51:4198, DOI 10.1103/PhysRevD.51.4198) and **Gundlach–Martín-García 2007** (`W09-006`).
**Action for lead:** drop or replace the item; do not add it to `ledger/theorems.jsonl`.

**F2 (scope caveat). Sbierski 2018 is routinely over-read.** `T-302` maps it to
AF-SCC-C0-VAC-GEN. The theorem is about the maximal analytic extension's singularity boundary,
not generic-data C0 SCC across a Cauchy horizon. Kept as a valid citation with
`verified-scope-caveated`; the ledger row should carry the caveat verbatim.

**F3 (unresolved theorem number). Dafermos 2003 (Ann. Math.) has no machine-readable full text
available here.** OpenAlex resolved the DOI and reconstructed the abstract; the Annals PDF timed
out from this sandbox (both http and https, 40 s each) and no arXiv version was located. Row is
`verified-metadata-only`, `theorem_ref: UNRESOLVED`. The lead's `SRC-020/060/072` are consistent
with this.

**F4 (new sources).** Four audited works were absent from the canonical audit before this merge
(Gundlach–Martín-García 2007; and the theorem-level rows for Choptuik 1993, CGNS Part 3 and
Van de Moortel 2018 were metadata/abstract-only). All are now rows `W09-001…W09-010`.

**F5 (no mismatch found in the lead's resolved rows).** For every SCC source already in the
canonical audit, the DOI/arXiv locator was re-resolved and matched title/authors/venue exactly.
The one DOI mismatch found was **my own candidate** for Sbierski (see controls).

**F6 (process, integration).** The canonical `ledger/citation_audit.csv` is written by the
literature lead's builder (`artifacts/literature/tools/build_literature.py`) and is pinned in
`artifacts/literature/MANIFEST.json` at sha256 `67df6d45…`. Two additive merges of this shard were
performed and both were subsequently overwritten by the lead's rebuild (their MANIFEST records the
pre-merge file). The second merge was therefore **reverted by me** and the canonical restored to the
lead-frozen hash `67df6d45…`, because publishing a different hash would silently invalidate the
lead's freeze. My 14 rows are staged in
`ledger/citation_audit_scc_flash-09.lead_schema.csv` (sha256 `8d46a90b…`); the lead's builder can
ingest them, or Astra can apply them with
`python3 artifacts/worker-09/merge_into_canonical.py --update-existing`.
**Lesson for the swarm:** one writer per artifact; parallel workers should publish shards plus an
idempotent merge, and the owner performs the merge before freezing.

**F7 (P3, new-preprint verification — all match).** The ledger's most load-bearing recent SCC rows
were independently re-fetched by this worker and checked against the ledger text:

| ledger row | arXiv | independent check | result |
|---|---|---|---|
| `SRC-078` / `T-528` Hintz 2026 | 2606.28253 | abstract title/authors/date; "full subextremal range", rate O(t_*^{-2-ε}) | **match** |
| `SRC-080` / `T-526` Luk–Sbierski 2026 | 2604.04877 | **Theorem 1.2 read from the complete HTML** (6,105,891 B): conclusion 2 = continuous extendibility across CH+; conclusion 3 = no C^{0,1}_loc extension, conditional on assumption (iii) | **match, theorem-level** |
| `SRC-081` / `T-527` Sbierski 2024/25 | 2409.18838 | abstract + arXiv comment "Version accepted for publication in Inventiones Mathematicae" | **match** |
| `SRC-082` Sbierski note | 2604.06283 | states it strengthens 2201.12295 and is used in 2604.04877 | **match** |
| `SRC-083` Gurriaran spin +2 | 2409.02670 | oscillatory blow-up asymptotics of the spin +2 Teukolsky field | **match** |
| `SRC-084` Gurriaran spin −2 | 2503.24114 | spin −2 asymptotics; conclusion phrased "suggests" | **match, with wording caveat** |
| `SRC-085` Sbierski 2022 | 2201.12295 | conditions for linear instability of the Kerr CH | **match** |
| `SRC-086` Luk–Oh Part I (Annals) | 1702.05715 | DOI 10.4007/annals.2019.190.1.1 resolves to the exact title, Annals 190 (2019) | **match** |
| `SRC-058` Luk–Oh Part II (Annals of PDE) | 1702.05716 | DOI 10.1007/s40818-019-0062-7 resolves to the exact title, Annals of PDE 5 (2019) | **match** |

One wording caveat: `SRC-084`'s curvature-singularity conclusion is the authors' "suggests" — the
ledger's `T-305` already marks it `provisional`, so no correction is required, but any promotion of
that row to `theorem` must not upgrade "suggests" into "proves".

**F9 (P4 — the "Chruściel version" candidate is disconfirmed).** The open ANU copy of
`SRC-090` (Chruściel, *On Uniqueness in the Large of Solutions of Einstein's Equations ("Strong
Cosmic Censorship")*, Proc. CMA ANU v. 1991/27) was downloaded complete (13,189,076 bytes) and its
OCR text layer extracted (194,749 chars, 136 pp). Section 1.3, p. 19 states:

> "Strong Cosmic Censorship Conjecture (SCCC): Every maximal Hausdorff development of a generic
> Cauchy data set (Σ, g, K), with (Σ, g) compact or asymptotically flat, is globally hyperbolic.
> This conjecture is often formulated in the C^k context, and a breakdown of [C^k] differentiability
> class of the metric on a globally hyperbolic manifold is considered as a breakdown of validity of
> the conjecture. ... We have purposefully stated the SCCC without making the differentiability
> conditions explicit..."

(OCR: the superscript exponent is garbled; `C^k` marks the unreadable token and is not asserted.)

**Consequence for ledger `D-004`:** the candidate defining text for the "continuous metric +
L²_loc Christoffel" version does **not** define that version. Chruściel 1992 defines SCC as *global
hyperbolicity of the maximal development*, explicitly leaving the differentiability class open, and
does not mention L² connections. `SRC-090` should therefore not be recorded as the defining text of
D-004; the "Christodoulou–Chruściel version" name remains a literature usage (as D-004 already
says) whose primary definition is still unidentified. The AMS *Contemp. Math.* 132 version
(pp. 235-273) is paywalled (HTTP 403) and was not compared page-by-page with this ANU volume.

**F8 (P4/closing sweep — 34/34 SCC-side locators match).** `artifacts/worker-09/locator_sweep.py`
re-resolved every canonical audit row cited by an SCC-tagged theorem in `ledger/theorems.jsonl`
(34 rows): OpenAlex for DOI-bearing rows, arXiv abs for arXiv-only rows, title-similarity ≥ 0.82.
**34 match, 0 mismatch, 0 unresolved.** This is a title-identity check; theorem scope remains the
hand-audited rows' job. Two further unassessed rows were also closed at abstract level:
`SRC-092` Christodoulou 1999 CQG (OpenAlex: "We then give precise formulations of cosmic censorship
conjectures" — the candidate C0/C2 attribution text, still paywalled) and `SRC-093`
Dafermos–Rodnianski 2009 CPAM (locator improved: DOI `10.1002/cpa.20281` added; the paper is a
linear decay/red-shift result, a *stability* input, not an SCC-violation source).

**F10 (P5 — three more theorem-level rows, covering the three corners of the C0/C2 landscape).**
`W09-025` Ringström 2009 (Ann. Math. 170:1181): **C² SCC true for generic T³-Gowdy vacuum** —
a *vacuum* C2-positive result, but symmetry-restricted (T³, two Killing fields), so it must not be
transferred to `AF-SCC-C2-VAC-GEN` (the class file's `T-401` already says so). Abstract-level only
(no open full text). `W09-026` Dafermos–Shlapentokh-Rothman 2018 (CQG 35:195010), **Theorem 1.1**:
for generic finite-local-energy data on subextremal RN-dS/KN-dS, the *linear* wave solution fails to
be H¹_loc near any CH+ point — a fixed-background, Λ>0 result. `W09-027` Rossetti 2025 (Ann. Henri
Poincaré 26:675), **Theorems 4.1/5.22/6.1/6.6 + Cor 6.7**: under a no-mass-inflation condition the
metric extends continuously with Christoffel symbols in L²_loc and charged scalar in H¹_loc — a model
a model instantiation of the `D-004` regularity class, explicitly below C¹.

**F11 (P6 — remaining SCC-side rows, abstract-verified).** `W09-028` Luk 2018 JAMS (arXiv:1311.4970,
supplied to a ledger row that had no arXiv id): symmetry-free vacuum WNS construction with C0
extension and non-L² Christoffels. `W09-029` Cameron–Sbierski 2025 (arXiv:2511.13422): continuous
extensions in 1+1 dimensions are *not* unique in general — so "the extension exists" (T-301) must
not be read as "the extension is unique". `W09-030` Luk–Sbierski 2016 (arXiv:1512.08259): linear
infinite-energy result at the Kerr CH under upper/lower horizon bounds. `W09-031` Gautam 2024
(arXiv:2412.17927): exterior decay for large EM-scalar data supporting the Luk–Oh interior picture.
All four are inputs/support, not C0/C2 verdicts. Full texts were then read for three of them, upgrading `W09-028` (Thms 1/3/4; Remark 6 leaves extension uniqueness open), `W09-029` (Thm 4.3 trichotomy + Cor 4.6 local C0 uniqueness for strongly spherically symmetric RN) and `W09-030` (Thm 1.2 rough main + Thm 3.2 bounds) to theorem-level.

---

## 4. Controls (the method catches failures, not just confirms)

| control | test | result |
|---|---|---|
| `W09-CTRL-1` | my candidate DOI `10.4310/jdg/1519959623` for Sbierski | **rejected**: OpenAlex returns an unrelated X-ray-transform paper. Correct DOI `10.4310/jdg/1518490820` used instead. |
| `W09-CTRL-2` | correct Sbierski DOI `10.4310/jdg/1518490820` | accepted: exact title/author/journal match. |
| `W09-CTRL-3` | journal DOIs for Luk–Oh Parts I/II | accepted: Annals 190 (2019) and Annals of PDE 5 (2019) exact title matches. |
| `W09-CTRL-4` | merge schema/hash guard | when the lead rewrote the canonical with a new 25-column schema, the merge **aborted with no write**; a pre-merge backup restored the lead's frozen hash. |
| Theorem-level gate | rows are `verified-theorem-level` only if a numbered theorem statement was read from a cached primary source | 10 theorem-level, 7 abstract-level, 1 metadata-only, 2 abstract/review, 1 unsupported, 4 controls |
| Negative-search gate | Eardley–Gundlach (5 resolver queries) | 0 joint records → `unresolved`, never verified (finding F1) |

---

## 5. Limits (what this audit did NOT do)

- No claim of physical correctness; only locator + statement transcription + scope mapping.
- Full text was read for: Dafermos 2005, Luk–Oh 2017 (Duke), Luk–Oh Parts I/II, CGNS Part 3,
  Van de Moortel 2018 and 2020, Sbierski 2018 and 2020, Dafermos–Luk 2025,
  Gundlach–Martín-García 2007 (review; 0 theorems).
  Dafermos 2003 and Choptuik 1993 are abstract/metadata only (no accessible full text here).
- `SRC-090` (Chruściel 1992) is now **content-read via OCR** (finding F9), but the OCR regularity
  exponent in the SCCC statement is garbled and the AMS *Contemp. Math.* version was not read; the
  D-004 disconfirmation rests on the ANU volume's text. `SRC-092` remains abstract-level.
- The 2026 preprint rows the ledger relies on (`SRC-078`, `SRC-080`–`SRC-085`) are
  **abstract-verified** by this worker (F7); `SRC-080`'s Theorem 1.2 is now **read in full**
  (all three conclusions, with assumption (iii) for conclusion 3).
- The canonical ledger's `verdict` column does not carry my nuance; the rich shard
  (`citation_audit_scc_flash-09.csv`) is the authoritative record for `c0_or_c2`,
  `what_it_does_not_prove` and `falsifier`.

## 6. Next falsifiers

1. **F1:** produce a resolvable joint Eardley–Gundlach publication → retract `W09-005`.
2. **F3:** obtain the Dafermos 2003 full text (library/publisher access) and read the numbered
   theorem that covers C0 extendibility → upgrade the row or find a mismatch.
3. **C0/C2 rows:** any citation that uses `W09-002`/`W09-003`/`W09-007` as a C2 statement, or
   `W09-009` as generic-data C0 SCC evidence, is a scope violation; the rich shard records the
   exact `falsifier` per row.
4. **`T-301` conditionality:** if the ledger marks Dafermos–Luk unconditional without citing the
   Kerr-stability discharge, that is a conclusion-inflation finding.
5. **P3 rows:** if peer review changes the 2026 preprint statements (esp. `W09-016` bounds,
   `W09-017` blow-up hypothesis), the abstract-level verification must be redone; and `W09-020`'s
   "suggests" must not be promoted to "proves".
6. **`D-004`:** read the AMS *Contemp. Math.* 132 version of Chruściel 1992 (or a cleaner scan) to
   confirm the ANU text's SCCC statement and recover the garbled regularity exponent; if it does
   define an L²-connection version, retract the disconfirmation in `W09-022`.
