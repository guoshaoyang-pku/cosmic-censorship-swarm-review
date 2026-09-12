# L2 lifecycle: worker-09 shard adjudication + formulation anchors

- **Actor:** astra-lead-literature (independent lifecycle, group `literature`)
- **Started:** 2026-09-11T23:59+08:00 · **Adjudicated:** 2026-09-12T00:09+08:00
- **Queue consumed:** `comms/inbox/astra-lead-literature.jsonl` lines 1–8 (assignments `asg-…-L0-…-03`,
  `asg-…-L1-…-04`, `astra-w07adj-02`, `astra-fetch-07`; F1 evidence packet + ack; worker-09 shard note)
- **Canonical artifacts rebuilt:** `ledger/theorems.jsonl` (`ce42d205…`), `ledger/citation_audit.csv` (`315c1914…`)

## 0. Integrity re-check on entry

The rev-1 freeze was intact when this lifecycle started: `ledger/theorems.jsonl` matched the recorded
`7d78d2850b55…` and `ledger/citation_audit.csv` matched `0b72b4190667…`, both equal to the values in
`runtime/state/artifact_hashes.json`. No drift before the changes below.

## 1. Inputs and their instability

worker-09's shard was a **moving target** during adjudication:

| source | sha256 (first 12) | rows | note |
|---|---|---|---|
| inbox note (`deepseek-flash-09`, 23:52) | `8d46a90b1d6f` | 14 | message-reported hash; file no longer exists in that state |
| `ledger/citation_audit_scc_flash-09.lead_schema.csv` read at 00:05 | `793c1e2a0579` | 24 | the snapshot dispositions below were computed on this row set |
| same file at 00:09 | `e8053e65…` | 24 | rewritten again; copied to `incoming/w09-lead_schema.snapshot-e8053e65.csv` |
| `ledger/citation_audit_scc_flash-09.p5.csv` | `85d6b49c…` | 2 | new P5 rows W09-025/026; copied to `incoming/w09-p5.snapshot-85d6b49c.csv` |
| `ledger/citation_audit_scc_flash-09.csv` | `cd173a58…` | 28 | includes 4 negative/positive control rows |

Consequence: **no worker shard version is treated as frozen, and none is merged row-for-row into the
canonical audit.** Canonical changes were made only after the lead independently re-fetched the
locators. The worker shard remains a standalone artifact.

## 2. Decision summary

1. **20 of 24 rows are duplicates** of existing canonical sources (matched by bibkey + DOI/arXiv id).
   They corroborate the canonical records; they are not merged, and they must not inflate the source count.
2. **1 row is refused:** `W09-005` ("Eardley-Gundlach") does not resolve after five independent
   resolver queries. Registered nowhere, per the worker's own instruction and the canonical
   no-guessing policy; the negative result is preserved here and in the worker shard.
3. **3 rows carry genuine new evidence and were adopted after lead re-verification:**
   `W09-022` → SRC-090, `W09-023` → SRC-092, `W09-024` → SRC-093 (details in §4).
4. **2 P5 rows were adopted as new sources:** `W09-025` → SRC-096 (Grant et al.), `W09-026` → SRC-097
   (Rendall), answering the F1 pointer request (see `FORMULATION_ANCHORS.md`). Canonical rows are at
   abstract level; the P5 theorem/section-level extraction is recorded as worker-supplied and
   **not** independently re-extracted by the lead.

## 3. Row dispositions (24 rows)

| worker row | bibkey | disposition | canonical |
|---|---|---|---|
| W09-001 | dafermos2003annals | duplicate | SRC-060 |
| W09-002 | dafermos2005cpam | duplicate | SRC-021 |
| W09-003 | lukoh2017duke | duplicate | SRC-023 |
| W09-004 | choptuik1993 | duplicate; correctly flagged NOT-A-THEOREM-SOURCE | SRC-016 |
| W09-005 | eardley-gundlach-UNRESOLVED | **refused** — unresolved after 5 resolver queries | not registered |
| W09-006 | gundlach-martingarcia2007 | duplicate | SRC-094 |
| W09-007 | cgns2017part3 | duplicate | SRC-028 |
| W09-008 | vandemoortel2018cmp | duplicate (model-matched companion for T-505) | SRC-095 |
| W09-009 | sbierski2018c0 | duplicate | SRC-005 |
| W09-010 | dafermosluk2025annals | duplicate | SRC-004 |
| W09-011 | vandemoortel2020c2 | duplicate | SRC-025 |
| W09-012 | lukoh2017partI | duplicate | SRC-057 |
| W09-013 | lukoh2017partII | duplicate | SRC-058 |
| W09-014 | sbier2020holonomy | duplicate | SRC-024 |
| W09-015 | hintz2026kerrstab | duplicate | SRC-078 |
| W09-016 | luksbierski2026wns | duplicate | SRC-080 |
| W09-017 | sbierski2025lipschitz | duplicate | SRC-081 |
| W09-018 | sbierski2026note | duplicate | SRC-082 |
| W09-019 | gurriaran2025spin2 | duplicate | SRC-083 |
| W09-020 | gurriaran2025spinminus2 | duplicate | SRC-084 |
| W09-021 | sbierski2022linear | duplicate | SRC-085 |
| W09-022 | chrusciel1992uniqueness | **adopted (content read)** | SRC-090 upgraded |
| W09-023 | christodoulou1999cqg | **adopted (abstract level)** | SRC-092 upgraded |
| W09-024 | dafermosrodnianski2009redshift | **adopted (exact locator + DOI)** | SRC-093 upgraded |

The worker-09 merge script (`artifacts/worker-09/merge_into_canonical.py --dry-run`) reports all 24
as "new" because canonical ids are `SRC-0xx`. Running it unmodified would have added 20 duplicate
rows. **It was deliberately not run.**

## 4. Adopted deltas (canonical)

### SRC-090 — Chruściel, *On uniqueness in the large…* (D-004 candidate)
- Content now read from the open 1991 ANU proceedings edition of the same title
  (`https://www.math.tecnico.ulisboa.pt/~jnatar/nonarxivpapers/Chrusciel.pdf`, §1.3 p. 19, via
  worker-09 OCR extraction; the lead verified the quoted passage in
  `artifacts/worker-09/extracted/chrusciel1992_text.txt` line 575).
- Quote: *"Strong Cosmic Censorship Conjecture (SCCC): Every maximal Hausdorff development of a
  generic Cauchy data set (Σ,g,K), with (Σ,g) compact or asymptotically flat, is globally
  hyperbolic."* — followed by *"This conjecture is often formulated in the C^k context…"*.
- **Verdict: D-004 candidate DISCONFIRMED.** The text is parameterised by an unspecified C^k class;
  it is neither the C^0 nor the C^2 formulation and does not define the C^0-metric + L²_loc-Christoffel
  version. Not bound to any theorem row.

### SRC-092 — Christodoulou 1999, CQG 16(12A) A23–A35
- Abstract-level evidence added (OpenAlex inverted-index reconstruction, re-fetched by the lead):
  *"We then give precise formulations of cosmic censorship conjectures."*
- **Verdict: formulation-origin candidate, not a citable wording.** The exact formulations are
  behind the IOP paywall; the abstract does not entail D-002 or D-003. No theorem binding.

### SRC-093 — Dafermos–Rodnianski 2009, CPAM 62(7) 859–919
- Exact locator + DOI added: `10.1002/cpa.20281` (Crossref re-fetched by the lead), arXiv abs page
  `gr-qc/0512119`; the previously elided quote replaced by the verbatim abstract.
- **Verdict: background stability/decay input only.** Must not be cited for or against SCC /
  C^0 / C^2. T-516 cites the companion 2005 Price-law paper, not this one.

### SRC-096 / SRC-097 — F1 pointer sources (new)
- **SRC-096** Grant–Kunzinger–Sämann–Steinbauer, *The future is not always open*,
  Lett. Math. Phys. 110(1) 83–103 (2020), DOI `10.1007/s11005-019-01213-8`, arXiv:1901.07996.
  Lead-fetched arXiv abs + Crossref; abstract confirms breakdown of low-regularity causality
  (non-open chronological futures, causal bubbling). Peer-reviewed.
- **SRC-097** Rendall, *The nature of spacetime singularities*, in *100 Years of Relativity*
  (World Scientific, 2005) 76–92, DOI `10.1142/9789812700988_0003`, arXiv:gr-qc/0503112. Survey.
- **Both are `assessed_no_binding`:** they are caveat/background pointers, not class evidence. The
  F1 extension clause must not cite either as proving degeneracy or extendibility.

### T-201 (L0 metadata)
- `next_action` referred to the non-frozen token `AF-WCC-VAC-BH-FORM`. Rewritten to reference the
  `BH-FORMATION` ledger tag under directive `astra-w07adj-02`. This removed the last non-frozen class
  token from the L0 artifact (the `audit_evidence.py` soft finding on `ledger/theorems.jsonl` is gone).

## 5. Lead verification log (independent re-fetches, 2026-09-12)

| # | locator | result |
|---|---|---|
| 1 | `https://arxiv.org/abs/1901.07996` | HTTP 200; title/authors/abstract match SRC-096; journal ref Lett. Math. Phys. 110 (2020) 83–103 |
| 2 | `https://api.crossref.org/works/10.1007/s11005-019-01213-8` | DOI resolves to the same work (pp. 83–103, vol. 110) |
| 3 | `https://arxiv.org/abs/gr-qc/0503112` | HTTP 200; survey abstract matches SRC-097 |
| 4 | `https://api.crossref.org/works/10.1142/9789812700988_0003` | DOI resolves to Rendall, *100 Years of Relativity*, pp. 76–92 |
| 5 | `https://arxiv.org/abs/gr-qc/0512119` | HTTP 200; abstract matches SRC-093 exactly; journal ref CPAM 62 (2009) 859–919 |
| 6 | `https://api.crossref.org/works/10.1002/cpa.20281` | DOI resolves to Dafermos–Rodnianski 2009 |
| 7 | `https://api.openalex.org/works/doi:10.1088/0264-9381/16/12A/302` | record + abstract match SRC-092 (closed access, no full text) |
| 8 | `chrusciel1992_text.txt` line 575 | quoted SCCC passage present in the worker's extracted text |
| 9 | `https://arxiv.org/html/1901.07996v2` | paper structure/abstract confirmed; theorem bodies not re-extracted (page truncated in fetch) |

## 6. Schema findings (not merged)

- The shard's `class_mapping` column contains non-frozen tokens (`AF-SCC-OTHER-MODELS`,
  `AF-WCC-SCALAR-SPH (background)`, `n/a`, …). Canonical `class_mapping` is derived from theorem
  `class_ids` only, so these cannot leak; they are not adopted.
- Shard rows lack canonical `citation_id`s, so duplicate detection must be by bibkey/DOI — the
  merge script's `citation_id`-only check is insufficient.
- P5 rows W09-025/026 do carry theorem/section pointers (Thm 2.10, 2.15, Cor 2.16, Ex 3.1 for
  SRC-096; Sections 2–3 for SRC-097). They are recorded here for F1 but are **worker-extracted,
  lead-unverified at theorem level**.

## 7. Residual risk / falsifiers

- If the open 1991 ANU edition differs materially from the AMS 1992 version, SRC-090's quote is
  still correct for the edition actually read; the DOI anchors the AMS version of the same title.
- If worker-09's shard is rewritten again, only the dispositions in §3 are adjudicated; new rows are
  unadjudicated. Any future shard must be frozen by hash **before** adjudication.
- The five `assessed_no_binding` rows are the honest hole in the audit: they are locator-resolved and
  explicitly not evidence. A later lifecycle that binds any of them to a theorem must re-verify the
  exact wording first.
