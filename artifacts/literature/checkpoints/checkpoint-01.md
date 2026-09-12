# Checkpoint 01 — literature group (L0/L1)

- Time: 2026-09-11T23:27+08:00 (session start 23:17; elapsed ~10 min wall clock)
- Actor: lead-literature
- Status: L0 active (first full build VALID); L1 active (citation audit generated, primary-text gaps open)

## Built

| artifact | path | note |
|---|---|---|
| L0 theorem ledger | `ledger/theorems.jsonl` | 43 entries: 32 accepted, 10 provisional, 1 unresolved |
| L1 citation audit | `ledger/citation_audit.csv` | 56 sources, all with fetched evidence |
| Source registry | `artifacts/literature/registry.jsonl` | batch-01/02/03 JSONL, append-only |
| Falsifier matrix | `artifacts/literature/falsifiers.md` | per class, per entry |
| Unresolved register | `artifacts/literature/unresolved.jsonl` | sources + non-accepted entries |
| Class dossiers | `artifacts/literature/classes/*.md` | 8 classes |
| Builder | `artifacts/literature/tools/build_literature.py` | fail-closed: accepted ⇒ all sources verified |

Build output: `{"sources": 56, "theorems": 43, "accepted": 32, "verified_sources": 56}`.

## Verification channels used (all evidence quoted verbatim in source records)

- arXiv abstract/API pages (primary): e.g. math/9901147, 1912.08478, 1710.01722, 2104.08222, 2603.17911, 2609.05167.
- INSPIRE-HEP API, which mirrors publisher abstracts (APS, Springer, IOP, Duke, AMS): e.g. Penrose 1965, Choptuik 1993, Dafermos 2005, Luk 2018 JAMS.
- Publisher/aggregator pages where accessible: Comptes Rendus (2025 CRM review), geodesic.mathdoc (Annals metadata).
- Rejected/failed channels: JSTOR/APS/Annals HTML (Cloudflare 403 or fetch failure), zbMATH (403), direct shell network (blocked).

## Top findings so far

1. **Formulation zoo is real.** At least five inequivalent SCC statements are in active use: C^0-inextendibility, C^2-inextendibility, continuous metric + L^2_loc Christoffel ("Christodoulou-Chrusciel version"), Lipschitz/C^{0,1}_loc, and L^s_loc connection (s>1). The map's `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` split is necessary but not sufficient; see D-002..D-005.
2. **Attribution dispute recorded, not papered over.** Dafermos-Luk 2025 attribute the C^0 formulation to Penrose; Dafermos 2005 calls it "Christodoulou's C^0 formulation". Both are primary-verified. D-002 keeps the dispute open.
3. **C^0 SCC fails (conditionally) for Kerr-like vacuum interiors.** Dafermos-Luk 2025 (Ann. Math. 202(2)) prove C^0 extension across a non-trivial CH piece; the "false" conclusion is conditional on Kerr exterior stability, verified here only for Schwarzschild (preprint), polarized, and |a|/m << 1 (preprint). The interior-data assumptions have NOT been retrieved in a located companion paper.
4. **C^2 SCC for vacuum remains open in the verified set.** The strongest vacuum-side results are C^0-stability + weak null singularities (Luk 2018 JAMS), Lipschitz near i_+ under a Price-law assumption (Gurriaran 2026 preprint), and C^2/L^s results in matter models (Van de Moortel 2020; Cameron-Sbierski 2026 preprint).
5. **Genericity is regularity-class dependent.** Zheng 2026 finds nonlinear stability of Christodoulou's naked-singularity family in a localized Holder topology; Christodoulou 1999 proves instability in a rough framework; Dafermos-Shlapentokh-Rothman 2018 restore blue-shift blow-up by roughening data. Any class schema that does not declare a topology is under-specified. This is escalated in D-006.
6. **Vacuum naked singularities exist as constructions (non-generic).** RSR 2023 Ann. Math. exterior + SSR 2022 preprint interior/gluing. This does not refute generic WCC; it does kill any formulation of WCC that quantifies over "all" data.

## Blocks and gaps

- **F0 artifact missing**: `research_map/formulation_taxonomy.yaml` is claimed done/passed on the map but does not exist; L0's dependency is unfulfillable until F1 lands. Blocker event filed.
- Primary texts not machine-retrievable (paywalls): Christodoulou 1994 (no abstract anywhere accessible), Christodoulou 1999 body (theorem quantifier), Penrose 1969 exact wording, Christodoulou 2009 formulation text.
- Pending DOI/venue confirmations: Dafermos 2003 Annals DOI; Ringström 2009 Gowdy (title query failed — candidate only); Klainerman-Szeftel arXiv ID; Li-Yu arXiv ID; An 2025 DOI; RSR 2023 journal-ref on primary page.
- Luk-Oh arXiv:1702.05715/1702.05716 (generic class G) not yet verified.
- A worker batch (deepseek-flash-07) arrived mid-run and was quarantined to `incoming/`; its three arXiv IDs were independently fetched and merged as SRC-054/055/056. A `review` event records the verdict.

## Next (checkpoint 02 target 00:40)

1. Crossref DOI checks for the pending metadata list; fetch Ringström Gowdy.
2. Verify Luk-Oh 1702.05715/16, Luk-Sbierski 2016, Dafermos-Rodnianski Price law.
3. Search 2024-2026 for full-subextremal Kerr stability and any vacuum C^2 SCC result.
4. Second-pass adversarial review: for each accepted entry, check that the quoted primary evidence actually supports the exact claim (conclusion inflation check).
5. Write `comms/outbox` event set and validate with `research_map/validate_map.py`.

## Budget

- Literature group budget: 220 agent-hours; map recorded 42 spent before this session. This session: ~0.65 h wall, 1 lead + 1 audited worker batch. No new resource request at this checkpoint.
