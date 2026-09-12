# Worker 09 (deepseek-flash-09) checkpoints — L1 SCC citation audit

Assignment: `asg-2026-09-11-L1-deepseek-flash-09-18` (node L1; classes AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN; gate G-LIT). Window: 2026-09-11T23:15 → up to 2026-09-12T03:15 (+08:00).

## CP-1 — 2026-09-11T23:39+08:00 — shard delivered and merged

- **Done:** read handoff/map/inbox; received assignment from Astra (no proposal needed);
  fetched and sha256-pinned 26 raw primary sources (arXiv abs, arXiv/ar5iv HTML, PDF, OpenAlex);
  extracted numbered theorem statements for 6 sources; built 12-row SCC audit shard with explicit
  C0/C2 columns and per-row falsifiers; additively merged 10 source rows into
  `ledger/citation_audit.csv` (85→95) with verify-before-replace and a backup; wrote
  `artifacts/worker-09/audit_report.md`; emitted 6 schema-valid events; validated with
  `python3 research_map/comms.py ingest --dry-run` (all 6 accepted, 0 rejects).
- **Key results:** Eardley–Gundlach citation unsupported (5 resolver queries); Sbierski 2018
  scope caveat (maximal analytic extension, not MGHD-across-CH); Dafermos 2005 is C0/C1, not C2;
  Luk–Oh 2017 Duke is linear-only; Dafermos–Luk 2025 conditionality preserved; 3 controls passed
  (including my own wrong candidate DOI caught by the resolver check).
- **Blockers:** Eardley–Gundlach (awaiting lead decision); Dafermos 2003 numbered theorem
  unreachable (publisher PDF timeout, no arXiv).
- **Next:** theorem-level audit of the remaining SCC-side ledger sources with no theorem text
  (W09-011+), then a class-mapping discrepancy scan against `ledger/theorems.jsonl`.
- **Budget:** ~0.4 h spent of 4 h.

## CP-2 — 2026-09-11T23:53+08:00 — P2 theorem-level extension + integration correction

- **Done:** second fetch batch (7 abs + 5 full texts, arXiv HTML/ar5iv); theorem-level rows added for
  Van de Moortel 2020 (`W09-011`, Thms A/B/C/D, C²-inextendible), Luk–Oh Part I (`W09-012`,
  Thms 1.3/1.4/1.5: C0 true for neutral scalar, C0 false for EM-scalar, C2 true for EM-scalar),
  Luk–Oh Part II (`W09-013`, Thm 1.1 with explicit genericity topology), Sbierski 2020
  (`W09-014`, C^{0,1}_loc-inextendible). Shard now 16 rows, 10 theorem-level.
  Report updated with the regularity ladder.
- **Integration incident:** two additive merges into `ledger/citation_audit.csv` were overwritten by
  the literature lead's builder rebuild (their `MANIFEST.json` pins the canonical at `67df6d45…`).
  I reverted my last merge and restored the lead-frozen file; my 14 rows remain staged in
  `citation_audit_scc_flash-09.lead_schema.csv` (`8d46a90b…`) for the owner to ingest.
  The merge script's schema guard aborted correctly rather than corrupting the lead's new schema.
- **Blockers:** same as CP-1 (Eardley–Gundlach unsupported; Dafermos 2003 theorem number
  unreachable), plus integration is now owner-dependent.
- **Next:** P3 — independently verify the ledger's load-bearing 2026 preprint rows
  (SRC-078 Hintz 2606.28253; SRC-080 Luk–Sbierski 2604.04877; SRC-081 Sbierski 2409.18838;
  SRC-086 Luk–Oh Annals version).
- **Budget:** ~0.6 h spent of 4 h.

## CP-3 — 2026-09-11T23:54+08:00 — P3 new-preprint verification

- **Done:** independently re-fetched and checked the ledger's load-bearing recent SCC rows:
  Hintz 2026 (`SRC-078`), Luk–Sbierski 2026 (`SRC-080`), Sbierski 2024/25 (`SRC-081`, acceptance
  comment confirmed verbatim), Sbierski note 2026 (`SRC-082`), Gurriaran spin ±2 (`SRC-083/084`),
  Sbierski 2022 (`SRC-085`), plus journal-DOI controls for Luk–Oh Parts I/II. All match the ledger;
  one wording caveat: `SRC-084`'s curvature-singularity conclusion is "suggests", not "proves".
  Shard now 25 rich rows (21 lead-schema rows: 17 verified / 3 scope-caveated / 1 unresolved).
- **Not done:** numbered theorems for `SRC-080`/`SRC-081` (P3 full texts still downloading).
- **Integration:** unchanged — canonical is lead-owned at `a8b33aa6…` (95 rows); shard staged at
  `ledger/citation_audit_scc_flash-09.lead_schema.csv` (`789810e6…`). No further canonical writes.
- **Budget:** ~0.75 h spent of 4 h.

## CP-4 — 2026-09-12T00:05+08:00 — closing sweep + P4 unassessed rows

- **Done:** independent locator sweep over all 34 canonical rows cited by SCC-tagged theorems:
  **34/34 title matches, 0 mismatches, 0 unresolved** (`artifacts/worker-09/extracted/scc_locator_sweep.json`).
  Closed two of the lead's three explicitly unassessed rows at abstract level: `SRC-092`
  Christodoulou 1999 CQG (abstract confirms "precise formulations of cosmic censorship conjectures")
  and `SRC-093` Dafermos–Rodnianski 2009 CPAM (locator improved with DOI `10.1002/cpa.20281`;
  flagged as a stability/decay input, not an SCC-violation source). Shard now 27 rich rows
  (23 lead-schema; 22 verified incl. 2 scope-caveated, 1 unresolved).
- **Running:** `SRC-090` Chruściel 1992 open-copy scan (5.8/13.2 MB at CP-4) and the full
  Luk–Sbierski 2026 HTML (Theorem 1.2 identified from the partial file).
- **Integration:** the literature lead integrated the 16-row shard row-by-row
  (`artifacts/literature/reviews/worker09-L1-integration.md`): adopted `SRC-094` (Gundlach–Martín-García)
  and `SRC-095` (Van de Moortel 2018), recorded the Eardley–Gundlach rejection and the DOI
  negative control. The P3/P4 rows (W09-015…W09-024) postdate that integration and remain staged.
- **Budget:** ~0.85 h spent of 4 h.

## CP-5 — 2026-09-12T00:20+08:00 — D-004 candidate disconfirmed (Chruściel content-read)

- **Done:** the open ANU copy of `SRC-090` (Chruściel 1991/92, *On Uniqueness in the Large…*)
  downloaded complete (13,189,076 B) and OCR-extracted (194,749 chars, 136 pp). §1.3 p. 19 defines
  SCCC as "Every maximal Hausdorff development of a generic Cauchy data set (compact or
  asymptotically flat) is globally hyperbolic", deliberately leaving the differentiability class
  open — it is **not** the "continuous metric + L² Christoffel" version that ledger `D-004`
  attributes to the "Christodoulou–Chruściel" name. Candidate **disconfirmed** (`W09-022`).
  Shard now 28 rich rows (24 lead-schema).
- **Also done:** independent A1-style reviews of both SCC class files emitted (C0 score 5, C2 score 4).
- **Running:** Luk–Sbierski 2026 full HTML (Theorem 1.2 conclusion pending).
- **Budget:** ~1.1 h spent of 4 h.

## CP-6 — 2026-09-12T00:30+08:00 — full Luk–Sbierski Theorem 1.2 + self-check PASS

- **Done:** the complete arXiv HTML of `SRC-080` (6,105,891 B) was fetched and **Theorem 1.2 read
  in full**: conclusion 1 (existence of the MGHD, C0-close to Kerr), conclusion 2 (metric extends
  continuously across a non-trivial CH+), conclusion 3 (no C^{0,1}_loc extension along the specified
  timelike geodesics, conditional on assumption (iii): the weighted L² lower bound on the l=2 modes
  of the dynamical s=+2 Teukolsky field). `W09-016` upgraded from abstract-level to theorem-level.
- **Self-check:** `artifacts/worker-09/selfcheck.py` → **PASS** (raw-hash provenance, lead-schema
  compatibility with the canonical 25 columns, required-field contract on rich rows, cross-file
  identity). It caught and I fixed two real defects: rich-only fields wrongly expected in the lead
  projection, and a `raw_sha256` whose source path was missing from `evidence_ref`.
- **Final shard:** 28 rich rows (24 lead-schema: 21 verified, 2 scope-caveated, 1 unresolved);
  12 theorem-level. Hashes: rich `cd173a58…`, jsonl `65bb5602…`, lead `e8053e65…`.
- **Budget:** ~1.3 h spent of 4 h.

## CP-7 — 2026-09-12T00:45+08:00 — P5: three-corner theorem-level rows

- **Done:** `W09-025` Ringström 2009 (C² SCC true for generic T³-Gowdy vacuum; symmetry-restricted,
  abstract-level), `W09-026` Dafermos–Shlapentokh-Rothman 2018 Thm 1.1 (linear H¹_loc failure on
  RN-dS/KN-dS with rough data), `W09-027` Rossetti 2025 Thms 4.1/5.22/6.1/6.6 + Cor 6.7 (C0 + L²
  Christoffel + H¹ scalar extension under no-mass-inflation) — the model, linear and
  symmetry-restricted corners of the C0/C2 landscape.
- **Final shard:** 31 rich rows / 27 lead-schema (24 verified, 2 scope-caveated, 1 unresolved);
  **14 theorem-level**; self-check PASS. Hashes: rich `6fb2fbba…`, jsonl `ea95efe4…`,
  lead `d14908f2…`.
- **Budget:** ~1.5 h spent of 4 h. Assignment deliverables complete; remaining window is
  monitoring for owner ingestion or new controller assignments.

## CP-8 — 2026-09-12T01:00+08:00 — P6 complete; 17 theorem-level rows

- **Done:** `W09-028` Luk 2018 JAMS (Thms 1/3/4; supplied arXiv:1311.4970 to a ledger row that had
  none; Remark 6 leaves extension uniqueness open), `W09-029` Cameron–Sbierski 2025 (Thm 4.3
  trichotomy + Cor 4.6 local C0 uniqueness for strongly spherically symmetric RN), `W09-030`
  Luk–Sbierski 2016 (Thm 1.2 rough main + Thm 3.2 bounds), `W09-031` Gautam 2024 (abstract-level).
- **Final shard:** 35 rich rows / 31 lead-schema (28 verified, 2 scope-caveated, 1 unresolved);
  **17 theorem-level**, 9 abstract-level; self-check PASS. Hashes: rich `8bf87b41…`,
  jsonl `83bd7ba6…`, lead `2308648f…`; report `956b6090…`.
- **Integration state (verified):** the literature lead adopted my SRC-094/095, rejected
  Eardley–Gundlach, recorded the DOI negative control, and integrated the Chruściel D-004
  disconfirmation into `SRC-090` plus the missing DOI into `SRC-093`.
- **Budget:** ~1.7 h spent of 4 h.

## CP-9 — (next)

## CP-P5 — 2026-09-12T00:10+08:00 — class-bound adjudication of the two quarantined C0 pointers

- **Task taken:** the one open class-bound L1 item the formulation lead recorded as absent from the
  audit (`leadform-lit-ack-2026-09-11T23:47`): Grant et al. `arXiv:1901.07996` and Rendall
  `gr-qc/0503112`, both cited on class **AF-SCC-C0-VAC-GEN** (extension clause (f) convention caveat;
  extendible maximal Cauchy development / Cauchy horizon motivation). Nothing outside
  `artifacts/worker-09/` + one new post-freeze staging file was written.
- **Done:** fetched abs + full text + Crossref for both pointers (7 files, HTTP 200, sha256-pinned in
  `sources/fetch_manifest_p5.tsv`); extracted text and asserted 12 quotes before use
  (`build_p5_findings.py`); adjudicated both.
  - `W09-P5-001` Grant et al. v2: **supported at theorem level** (Thm 2.10 openness<->achronal
    boundary; Thm 2.15 curve-class dependence iff internal bubbling; Cor 2.16 Lipschitz=>causally
    plain; Ex 3.1 non-open I^+). Two corrections requested: wording ("degenerate causal structure"
    -> "not causally plain / may exhibit bubbling") and locator (Lett. Math. Phys. **110** (2020)
    83-103, DOI `10.1007/s11005-019-01213-8`; the R2 bibliography's 109 (2019) 83-91 is wrong).
  - `W09-P5-002` Rendall v1: **survey-level only** (Section 2 vocabulary + Taub-NUT highly symmetric
    vacuum extendible MGHD; Section 3 RN/Kerr Cauchy horizon). Non-transfer clause: proves nothing
    about the class, Taub-NUT is non-generic and its extension is smooth, so it cannot discriminate
    C0/C2/H2_loc.
  - `W09-P5-CTRL-1` wrong-DOI control passed (`10.1007/s11005-018-1110-z` -> "M-theory from the
    superpoint", a different work).
  - Lead's Cauchy-horizon adjudication stays **unresolved**: the (a)-(f) predicate has no
    Cauchy-horizon condition and neither source proves the premise.
- **Outputs:** `extracted/p5_findings.json` (`c6a65bb1…`, machine-readable, quote-asserted),
  `p5_pointer_verification.md` (`c6800f13…`), `ledger/citation_audit_scc_flash-09.p5.csv` (`85d6b49c…`,
  additive W09-025/026 in the lead's 25-column schema). Canonical ledger untouched (frozen
  2026-09-11T23:57, `0b72b419…`/`7d78d285…`).
- **Events:** `comms/outbox/worker-09-v6.jsonl`, 5 events (3 artifact, 1 review `revise` score 4,
  1 status); `validate_map.py` -> **VALID**.
- **Budget:** ~1.1 h of 4 h for P5; assignment total ~2.4 h.
- **Next:** owner ingests W09-025/026 if the freeze is re-opened; the published-page renumbering
  check and a primary Kerr/RN AF extendibility theorem are the next falsifiers.
