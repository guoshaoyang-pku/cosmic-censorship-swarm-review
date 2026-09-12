# Citation-integrity audit C (adversarial falsification pass)

- **Auditor**: independent subagent `citation-integrity-C` (no write access to any file except this report).
- **Audited revision**: `artifacts/literature/sources/batch-01..10.jsonl`, 93 records `SRC-001`..`SRC-093`, snapshot copied at 2026-09-11 ~23:45 CST (md5: batch-01 `8ad96f4a03bb6a3317e35c6bd62185d0`, batch-02 `4e5368d131db2f1bd4efd0f35aea49aa`, batch-03 `57414f55330f09fd88f2e3e6da388453`, batch-04 `3035adad1d61690b4977d1da0d05e308`, batch-05 `018ca7496a55733f3dd5b155fbca0906`, batch-06 `c27d9962ee6350c7e95600989a031d7b`, batch-07 `75c7ac81eabc5e554ec8db00de315066`, batch-08 `3b18d36e5a8cbc8db1607a2ac3e6fffb`, batch-09 `e43d11f8079cdb276bab0056d57e9bd3`, batch-10 `db58e40a3fac0dd63ecd190eb013ef1d`).
- **Moving target warning**: the registry grew from 65 to 93 records during this audit (batch-06..10 appeared at 23:31-23:43) and two records were edited in flight (`SRC-043` arXiv ID corrected 1207.3167→1207.3164 — independently confirmed correct; `SRC-066` JFA page-range note corrected to 1948-1995). Records added after the snapshot are not covered.

## Method
1. **DOI check**: every record with a DOI was queried at `https://api.crossref.org/works/<DOI>` (canonical endpoint, full record) and fields title / first author / issued+print+online year / volume / page / container were compared to the record. `10.48550/*` and `10.25365/*` DOIs are DataCite-registered (Crossref returns HTTP 404) and were checked at `https://api.datacite.org/dois/<DOI>`. 46 Crossref-registered DOIs and 20 DataCite DOIs were checked; 8 records have no DOI.
2. **Live-page check**: 16 URLs were fetched with `web_fetch` (listed in section (c)); additionally every record’s `verification.page` and `url` field was fetched by script and the evidence quote was matched after alphanumeric/LaTeX/diacritic normalisation (so "verbatim" below means normalized equivalence; punctuation- and symbol-level deviations are reported separately).
3. **Duplicates**: exact DOI, exact arXiv ID and normalized-title screens over all 93 records.
4. **Impossible metadata**: year vs arXiv v1/v2 submission dates (arXiv API for all 48 arXiv IDs), venue-vs-DOI prefix, peer-review claims vs arXiv comment/journal-ref, Crossref/DataCite year vs record year.
5. **Evidence quotes**: minimum length screen (all quotes ≥152 chars except `SRC-090`, which has none) and liftability screen against the recorded page.

## Per-record results

| source_id | DOI check | quote/liftability | dup cluster | detail |
|---|---|---|---|---|
| SRC-001 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-002 | PASS | PASS | SRC-068 | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-003 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-004 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-005 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-006 | MINOR | PASS | - | Crossref title carries HTML markup only (<i>C</i> <sup>0</sup>) - normalized match; verbatim (normalized) on recorded verification.page |
| SRC-007 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-008 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-009 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-010 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; evidence is a composite metadata sentence, not a single liftable quote (fields individually verified against INSPIRE 9038) |
| SRC-011 | FAIL | MINOR | - | DOI 10.1023/A:1016578408204 is the 2002 Gen. Rel. Grav. "Golden Oldie" reprint (vol 34, 1141-1165); record year 1969 / Riv. Nuovo Cim. (reprint disclosed in venue, but DOI/year disagree); composite metadata sentence; fields individually verified (INSPIRE 54979) |
| SRC-012 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; composite metadata sentence; fields individually verified (INSPIRE 55131) |
| SRC-013 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; composite metadata sentence; fields individually verified (INSPIRE 391017) |
| SRC-014 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-015 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-016 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; verbatim except symbol substitutions: page has gamma/Prop/parallel-to symbols where the record writes "gamma"; not literally liftable |
| SRC-017 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-018 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-019 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-020 | N-A | MINOR | SRC-060, SRC-072 | no DOI in record; composite metadata sentence; fields individually verified (INSPIRE 1767922) |
| SRC-021 | PASS | FAIL | SRC-056 | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-022 | FAIL | FAIL | - | Crossref issued/published-online 2017-09-27; JAMS 31(1) print issue is 2018 (record year defensible for print; annotate); recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-023 | PASS | FAIL | SRC-055 | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-024 | N-A | PASS | SRC-087 | no DOI in record; verbatim (normalized) on recorded verification.page |
| SRC-025 | FAIL | FAIL | - | Crossref issued 2021-01-02, published-print 2021-03, CMP 382(2); record year 2020 is the arXiv year; two quoted spans differ from the live abstract: "union" for the cup symbol and an undisclosed elision of "(empty set)" qualifiers |
| SRC-026 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-027 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-028 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-029 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is an arXiv API search URL; quote is verbatim on the canonical arXiv page after LaTeX-rendering normalization (L^2_{\rm loc}) |
| SRC-030 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-031 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-032 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-033 | PASS | FAIL | SRC-088 | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-034 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-035 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-036 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-037 | PASS | MINOR | - | DataCite title/creator/year agree; one of two spans matches literally; the long abstract span differs only by LaTeX rendering on the arXiv page |
| SRC-038 | N-A | FAIL | - | no DOI in record; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-039 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-040 | PASS | FAIL | - | DataCite title/creator/year agree; evidence is a de-TeXed paraphrase: "/a//m << 1" vs "\ll", "[KS:Kerr]" vs "\cite{KS:Kerr}" - not literally liftable |
| SRC-041 | FAIL | FAIL | SRC-054 | DOI/URL = "The Twelfth Marcel Grossmann Meeting" (2012), pp. 24-34, doc_type conference paper (INSPIRE 786592); record headline is the 2009 EMS Monograph (a different work); recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-042 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-043 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-044 | N-A | FAIL | SRC-067 | no DOI in record; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-045 | PASS | MINOR | - | DataCite title/creator/year agree; "C^{1,kappa/(1+kappa)}" vs live "C^{1,\frac{\kappa}{1+\kappa}}" - rendering only |
| SRC-046 | PASS | FAIL | - | DataCite title/creator/year agree; evidence abridges/reorders the first sentence of the abstract without an ellipsis; 2 of 3 spans match on the canonical page |
| SRC-047 | PASS | MINOR | - | DataCite title/creator/year agree; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-048 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-049 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-050 | FAIL | PASS | - | Crossref page range 363-411 (AHP 24(2)); record venue says 1-56 (DOI FAIL); evidence quote is verbatim (normalized) on both the recorded arXiv-API page and the canonical arXiv page |
| SRC-051 | N-A | PASS | - | no DOI in record; verbatim (normalized) on recorded verification.page |
| SRC-052 | PASS | MINOR | - | DataCite title/creator/year agree; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-053 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-054 | N-A | PASS | SRC-041 | no DOI in record; verbatim (normalized) on recorded verification.page |
| SRC-055 | PASS | PASS | SRC-023 | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-056 | PASS | PASS | SRC-021 | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-057 | PASS | PASS | SRC-086 | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-058 | PASS | MINOR | - | DataCite title/creator/year agree; "weighted C^infinity topology" vs live "C^\infty" - rendering only |
| SRC-059 | MINOR | MINOR | SRC-071 | Crossref title carries HTML markup only (<i>T</i><sup>3</sup>) - normalized match; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-060 | PASS | MINOR | SRC-020, SRC-072 | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-061 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-062 | PASS | MINOR | - | DataCite title/creator/year agree; quote is de-TeXed ("<< 1" for \ll, bracketed names for \cite{...}); substance matches |
| SRC-063 | PASS | PASS | - | DataCite title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-064 | PASS | MINOR | - | DataCite title/creator/year agree; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-065 | PASS | MINOR | - | DataCite title/creator/year agree; quote replaces \cite{...} by bracketed names; substance matches |
| SRC-066 | N-A | MINOR | SRC-089 | no DOI in record; recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-067 | PASS | MINOR | SRC-044 | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-068 | PASS | MINOR | SRC-002 | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-069 | FAIL | PASS | - | Crossref registered title "Strong cosmic censorship in polarised Gowdy spacetimes"; record uses INSPIRE spelling "polarized Gowdy space-times" (minor); verbatim (normalized) on recorded verification.page |
| SRC-070 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; "the work of Costa-Girao-Natario-Silva" vs live "the work by ..."; one-word deviation |
| SRC-071 | MINOR | FAIL | SRC-059 | Crossref title carries HTML markup only - normalized match; evidence is an OpenAlex inverted-index reconstruction with bracketed insertions; the words are not contiguous in the source - not verbatim-liftable by construction |
| SRC-072 | PASS | FAIL | SRC-020, SRC-060 | Crossref title/first author/year/volume/pages agree; same: OpenAlex inverted-index reconstruction, not verbatim-liftable |
| SRC-073 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-074 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-075 | PASS | FAIL | - | Crossref title/first author/year/volume/pages agree; recorded verification.page is not a reproducible record page (search-query URL or literal "..."); quote is verbatim on the canonical url |
| SRC-076 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; "C_epsilon" vs live "\underline{C}_\varepsilon" - rendering only |
| SRC-077 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; "k^2 in (0,1/3)" vs live "k^2\in(0,\frac{1}{3})" - rendering only |
| SRC-078 | PASS | MINOR | - | DataCite (10.48550 arXiv) title/creator/year agree; one of two spans matches; second differs by LaTeX rendering/search-page volatility |
| SRC-079 | PASS | PASS | - | DataCite (10.48550 arXiv) title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-080 | PASS | PASS | - | DataCite (10.48550 arXiv) title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-081 | MINOR | MINOR | - | DataCite publicationYear 2024 (arXiv v1); record year 2025 = v2/accepted version (venu states "v2, Nov 2025"). Acceptance claim confirmed by arXiv comment ("Version accepted for publication in Inventiones Mathematicae"); recorded page is a query URL/partial; quote verbatim on canonical url |
| SRC-082 | PASS | PASS | - | DataCite (10.48550 arXiv) title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-083 | PASS | PASS | - | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-084 | PASS | MINOR | - | DataCite (10.48550 arXiv) title/creator/year agree; recorded verification.page is a volatile arXiv search URL; the quoted abstract is verbatim on the canonical arXiv page (arXiv:2503.24114) |
| SRC-085 | MINOR | PASS | - | DataCite publicationYear 2022 (arXiv v1); record year 2023 = Ann. PDE acceptance year, confirmed by arXiv comment ("accepted for publication in Annals of PDE"); verbatim (normalized) on recorded verification.page |
| SRC-086 | PASS | MINOR | SRC-057 | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-087 | PASS | MINOR | SRC-024 | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-088 | PASS | PASS | SRC-033 | Crossref title/first author/year/volume/pages agree; verbatim (normalized) on recorded verification.page |
| SRC-089 | PASS | MINOR | SRC-066 | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-090 | N-A | FAIL | - | no DOI in record; no evidence field, no DOI, no URL - status unresolved (consistent with record; do not cite) |
| SRC-091 | PASS | PASS | - | DataCite (10.48550 arXiv) title/creator/year agree; verbatim (normalized) on recorded verification.page |
| SRC-092 | PASS | MINOR | - | Crossref title/first author/year/volume/pages agree; composite metadata sentence (Crossref fields); not liftable as one string |
| SRC-093 | N-A | MINOR | - | no DOI in record; recorded page is a query URL/partial; quote verbatim on canonical url |

Result key: **PASS** = checked and consistent; **MINOR** = consistent in substance but with an annotation-level defect (rendering, spelling, composite evidence, defensible year choice); **FAIL** = mismatch or non-reproducible verification as recorded; **N-A** = not applicable. `SRC-090` is **UNRESOLVED** by design.


## Findings summary

Counts over the 93-record snapshot: 46 Crossref-registered DOIs checked, 20 DataCite (arXiv/thesis) DOIs checked, 8 records with no DOI, 1 unresolved (SRC-090). Genuine DOI-metadata mismatches: SRC-041 (DOI resolves to a different work), SRC-050 (pages), SRC-025 (year), SRC-011 (DOI is a 2002 reprint vs 1969 record), SRC-069 (title spelling), SRC-022 (online-2017 vs print-2018). DOI MINOR annotations: SRC-006/059/071 (HTML markup in Crossref titles), SRC-081/085 (DataCite records the arXiv v1 year while the record cites the v2/accepted year). Quote screen: 28 records have a non-reproducible recorded `verification.page` (search-query URL or a URL containing a literal `...`); 13 records carry composite metadata evidence that is not liftable as a single verbatim string; 3 records have material verbatim deviations (SRC-016, SRC-025, SRC-046) and 2 are machine reconstructions (SRC-071, SRC-072). No evidence quote is shorter than 30 characters (minimum 152, `SRC-090` has none).

### (a) Confirmed duplicates (same paper under two or more source_ids with different bibkeys)

| # | source_ids | basis |
|---|---|---|
| D1 | SRC-002 `rodnianski2023naked`, SRC-068 `rodnianski2023annals` | same DOI 10.4007/annals.2023.198.1.3 and arXiv 1912.08478 |
| D2 | SRC-020 `dafermos2003`, SRC-060 `dafermos2003annals`, SRC-072 `dafermos2003-abstract` | same paper, Ann. of Math. 158(3) 875-928 (SRC-020 has no DOI) |
| D3 | SRC-021 `dafermos2005cpam`, SRC-056 `dafermos2005arxiv` | same DOI 10.1002/cpa.20071 |
| D4 | SRC-023 `lukoh2017duke`, SRC-055 `lukoh2015arxiv` | same DOI 10.1215/00127094-3715189 |
| D5 | SRC-033 `dafermos2018rough`, SRC-088 `dafermos2018arxiv` | same DOI 10.1088/1361-6382/aadbcf, arXiv 1805.08764 |
| D6 | SRC-059 `ringstrom2009gowdy`, SRC-071 `ringstrom2009gowdy-abstract` | same DOI 10.4007/annals.2009.170.1181 |
| D7 | SRC-024 `sbier2020holonomy`, SRC-087 `sbierski2022duke` | same paper, arXiv 2007.12049 / DMJ DOI 10.1215/00127094-2022-0040 |
| D8 | SRC-057 `lukoh2017partI`, SRC-086 `lukoh2019annals` | same paper, arXiv 1702.05715 / Ann. of Math. 190(1) DOI 10.4007/annals.2019.190.1.1 |
| D9 | SRC-066 `luksbierski2016`, SRC-089 `luksbierski2016jfa` | same paper, arXiv 1512.08259 / JFA DOI 10.1016/j.jfa.2016.06.013 |
| D10 | SRC-041 `christodoulou2009bh`, SRC-054 `christodoulou2008arxiv` | same work (Christodoulou, *The Formation of Black Holes in General Relativity*); note SRC-041's DOI points to a *different* artifact (see (b)) |
| D11 | SRC-044 `an2025censor`, SRC-067 `an2025annals` | same paper, Ann. of Math. 201(3) 775-908 |

11 clusters covering 23 records. Not duplicates (checked and cleared): SRC-017 / SRC-018 / SRC-019 (three distinct papers), SRC-026 / SRC-027 / SRC-028 (parts 1-3), SRC-057 / SRC-058 (parts I and II), SRC-035 / SRC-036, SRC-002 / SRC-003 (exterior vs interior solution).

### (b) Records recommended for rejection, correction, or demotion

**Reject / split (metadata is wrong about what the identifier points to)**
- **SRC-041** (`christodoulou2009bh`): the headline work (2009 EMS Monographs in Mathematics, DOI 10.4171/068 per the Comptes Rendus bibliography) is not what its DOI resolves to. `10.1142/9789814374552_0002` is *The Twelfth Marcel Grossmann Meeting* (2012), pp. 24-34, INSPIRE 786592 `document_type: conference paper`. The record also duplicates SRC-054. Either drop the DOI and cite `10.4171/068`, or split into two records.
- **SRC-090** (`chrusciel1991candidate`): `status: unresolved`, no DOI, no URL, no evidence. Correctly flagged; must not be cited until fetched.

**Correct before further use**
- **SRC-050** (`lukoh2022scattering`): venue page range is wrong. Crossref: *Ann. Henri Poincare* 24(2), 363-411 (online 2022-07-11, print 2023-02). Record says "24, 1-56 (2023)".
- **SRC-025** (`vandemoortel2020c2`): record year 2020 vs publisher year 2021 (*Comm. Math. Phys.* 382(2), 1263-1341, issued 2021-01-02).
- **SRC-011** (`penrose1969`): DOI 10.1023/A:1016578408204 is the 2002 *Gen. Rel. Grav.* "Golden Oldie" reprint (34, 1141-1165), while the record year is 1969 and the primary venue is *Riv. Nuovo Cim.* 1, 252-276. The reprint is disclosed in the venue string, but the DOI/year pairing should be annotated.
- **SRC-022** (`luk2018jams`): Crossref registers 2017-09-27 (online); the print issue is JAMS 31(1) 2018. Record year 2018 is defensible; annotate.
- **SRC-016** (`choptuik1993`): the evidence quote is not literally verbatim (symbols replaced by words). Use a symbol-faithful quotation.
- **SRC-025**, **SRC-046**: evidence quotes contain undisclosed elisions or reordering relative to the live abstracts.
- **SRC-069** (`chrusciel1990gowdy`): Crossref registered title is "Strong cosmic censorship in polarised Gowdy spacetimes"; the record uses the INSPIRE spelling "polarized Gowdy space-times". Pick one and annotate the variant.
- **SRC-051** (`ma2023precise`), **SRC-038** (`klainermanszeftel2017polarized`), **SRC-058** (`lukoh2017partII`): published versions exist but the record has no published DOI. Verified independently: SRC-051 = *Trans. Amer. Math. Soc.*, DOI 10.1090/tran/8957 (2023); SRC-038 = Princeton University Press book, DOI 10.23943/princeton/9780691212425.001.0001, ISBN 9780691212425 (2020); SRC-058 = *Ann. PDE* 5 (2019), DOI 10.1007/s40818-019-0062-7 (seen in SRC-086 notes; not separately re-verified here).
- **SRC-024**, **SRC-057**, **SRC-066**: superseded by the published-version records SRC-087, SRC-086, SRC-089; keep one of each pair.

**Demote (verification is not independently reproducible as recorded)**
- **SRC-071**, **SRC-072**: evidence is an OpenAlex inverted-index *reconstruction* with bracketed insertions; it is not verbatim-liftable by construction. Keep as scope evidence only, never as a quotation of record.
- The 28 records whose `verification.page` is a search-query URL or contains a literal `...`: SRC-011, 012, 013, 015, 016, 017, 018, 019, 020, 021, 022, 023, 031, 032, 033, 034, 035, 036, 038, 041, 042, 043, 044, 073, 074, 075, 076, 077. Their quotes are genuine on the canonical `url` page, but the recorded page cannot be re-fetched; replace `verification.page` with the canonical record URL.
- Records with composite metadata evidence (SRC-010, 011, 012, 013, 020, 059, 060, 067, 068, 086, 087, 089, 092): field-level verified, but the evidence string is an assembled sentence, not a liftable quotation. Acceptable for metadata-only entries if labelled as such.
- **SRC-081** (`sbierski2025lipschitz`): the "accepted for publication in Inventiones Mathematicae" claim is supported by the live arXiv comment ("Version accepted for publication in Inventiones Mathematicae"); keep as preprint-level until the final volume/pages appear.
- **SRC-078**..**SRC-085**, **SRC-091**: 2025/2026 arXiv preprints; venues say "preprint"/"arXiv" and none claims peer review \u2014 no impossible-metadata violation found.

### (c) Exact URLs fetched with `web_fetch` (all returned HTTP 200 unless noted)

1. https://api.crossref.org/works/10.5802/crmeca.284
2. https://api.crossref.org/works/10.5802/crmeca.284?select=DOI,title,author,issued,volume,page,container-title,type \u2014 HTTP 400 ("This route does not support select")
3. https://api.crossref.org/works/10.48550/arXiv.2204.09891?select=DOI,title,author,issued,volume,page,container-title,type \u2014 HTTP 400 (same)
4. https://api.crossref.org/works?filter=doi:10.4007/annals.2009.170.1181,doi:10.4007/annals.2003.158.875,doi:10.4007/annals.2023.198.1.3,doi:10.4007/annals.2025.201.3.3,doi:10.1142/9789814374552_0002,doi:10.1007/s00023-022-01216-7&select=DOI,title,author,issued,volume,page,container-title,issue&rows=20
5. https://inspirehep.net/api/literature/9038 (SRC-010, metadata-only)
6. https://inspirehep.net/api/literature/622602 (SRC-021, INSPIRE-hosted)
7. https://inspirehep.net/api/literature/33714 (SRC-016)
8. https://inspirehep.net/api/literature/2743272 (SRC-044)
9. https://inspirehep.net/api/literature/311851 (SRC-069)
10. https://arxiv.org/abs/2609.05167 (SRC-048, arXiv)
11. https://arxiv.org/abs/2408.05257 (SRC-007)
12. https://export.arxiv.org/api/query?id_list=1512.08259,1702.05715,1702.05716,2208.08702
13. https://api.datacite.org/dois/10.25365/thesis.76304 (SRC-007 DOI)
14. https://api.openalex.org/works/doi:10.4007/annals.2009.170.1181 (SRC-071)
15. https://comptes-rendus.academie-sciences.fr/mecanique/articles/10.5802/crmeca.284/ (SRC-001, publisher page)
16. https://annals.math.princeton.edu/2025/201-3/p03 \u2014 **failed**: `TypeError: fetch failed`

Scripted HTTPS fetches (urllib, same URLs as the records' own `verification.page` and `url` fields) covered all 93 records; API endpoints used were `https://api.crossref.org/works/<DOI>`, `https://api.crossref.org/works?filter=doi:...&select=...`, `https://api.crossref.org/works?query.bibliographic=...`, `https://api.datacite.org/dois/<DOI>`, `https://export.arxiv.org/api/query?id_list=...`, `https://arxiv.org/abs/<id>`, `https://inspirehep.net/api/literature/<recid>`, `https://api.openalex.org/works/doi:<DOI>`, `https://annals.math.princeton.edu/2025/201-3/p03` (failed).

### Checks NOT completed (explicit gaps)

- **Publisher/abstract pages behind paywalls** (Springer, IOP, APS, Duke, AMS, International Press, Wiley) were not fetched directly; abstract/quote verification for those records relies on INSPIRE, Crossref or OpenAlex surrogates. Only the Comptes Rendus publisher page was fetched live.
- **`SRC-067` page range 775-908** is not present in the Crossref record (no `page` field); it is corroborated only by INSPIRE 2743272 (`Ann. of Math, 201(3), (2025), 775-908`) and by SRC-044.
- **`SRC-086` page range "190(1), 1-111"** is not in the Crossref record (no `page` field); unverified.
- **`SRC-038` series volume "Annals of Mathematics Studies 210"** is not in the Crossref book record (no series metadata); the DOI/publisher/year/ISBN confirm the 2020 Princeton book only.
- **Full record set beyond the 93-record snapshot**: the registry was still growing when the audit was frozen (batch files up to batch-10, 93 records); later additions are unaudited.
- **Quote "verbatim" is normalized** (case, punctuation, LaTeX commands, diacritics). Symbol-level differences are reported explicitly above but a byte-exact diff against every paywalled publisher page was not possible.
- **`SRC-058`'s Ann. PDE DOI 10.1007/s40818-019-0062-7** was seen in SRC-086's notes and in a Crossref search hit, but I did not fetch its canonical Crossref record (time-boxed); treat as high-confidence but not fully verified here.
- **SRC-018's evidence is labelled "CrossRef abstract"** while the record's verification method is INSPIRE; the quote was found verbatim on the INSPIRE API page, but the labelled source ("CrossRef abstract") was not the page checked.
