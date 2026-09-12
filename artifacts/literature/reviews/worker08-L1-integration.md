# Worker-08 L1 shard: lead integration note

- Integrated: 2026-09-11 ~23:55 (+08) by lead-literature (L1 owner)
- Shard: `ledger/citation_audit_wcc_flash-08.jsonl` (+ `.csv`, `.lead_schema.csv`), 15 rows, worker `deepseek-flash-08`, generated 23:33:43
- Shard hashes (from its own report): jsonl `e9740fbe…`, csv `dc61adab…`, lead_schema csv `e6a33765…`, fetch log `artifacts/worker08/l1_fetch_log.json` `8751834e…`
- Shard's own verdict counts: 4 verified-primary, 10 verified-api, 1 unresolved; rule followed: "failed lookups recorded unresolved/unverified, never verified".

## Row dispositions

| Worker row | Disposition | Canonical record |
|---|---|---|
| Penrose 1965 PRL 14, 57-59 | duplicate; keep metadata-only | SRC-010 |
| Penrose 1969 Riv. Nuovo Cim. 1, 252-276 | duplicate; keep metadata-only | SRC-011 |
| Christodoulou 1999 Ann. Math. 149, 183-217 | duplicate; abstract-read | SRC-014 |
| Christodoulou-Klainerman 1993 (book) | candidate background; not needed for class scope | not registered |
| Friedrich 1986 CMP 107, 587-609 | candidate background (future-complete solutions) | not registered |
| Lindblad-Rodnianski 2010 Ann. Math. 171, 1401-1477 | candidate background (Minkowski stability, harmonic gauge) | not registered |
| Dafermos-Rodnianski 2009 red-shift, CPAM 62, 859-919 | **added** as SRC-093 (arXiv abstract) | SRC-093 |
| Dafermos-Rodnianski 2005 Price's law, Invent. Math. 162 | duplicate | SRC-061 |
| DHRT 2021 Schwarzschild stability | duplicate (preprint) | SRC-037 |
| Klainerman-Szeftel 2020 polarized (AMS-210) | duplicate | SRC-038 |
| Ringstrom 2008 Invent. Math. 173, 123-208 | **unresolved candidate** (publisher blocked; scope unknown; worker correctly refused the AF mapping) | not registered |
| Ringstrom 2013 (OUP book) | **rejected for AF-WCC-VAC-GEN**; cosmological, outside the four frozen classes; recorded as non-class context | not registered |
| Choquet-Bruhat-Geroch 1969 CMP 14, 329-335 | duplicate | SRC-073 |
| Christodoulou 1999 CQG 16(12A), A23-A35 | **added** as SRC-092 (metadata-only via Crossref); candidate formulation text, page check pending | SRC-092 |
| Dafermos-Rodnianski lectures, Clay Proc. 17 | candidate background; survey only | not registered |

## Attestation

- Scope findings in the shard agree with the canonical ledger: Christodoulou 1999 belongs to the scalar class (not vacuum WCC); Price's law is SCC-side evidence for a scalar+Maxwell model; all AF-WCC-VAC-GEN support found is perturbative/symmetry-restricted; Penrose 1965 and Choquet-Bruhat-Geroch 1969 are foundational only.
- No fabricated locator was found in the shard. Two rows were adopted after independent checks (SRC-092 Crossref, SRC-093 arXiv API); the remaining rows duplicate already-registered sources.
- Schema gaps the shard reported ("lead schema has no class_id column", "no what_it_does_not_prove column") are now closed in `ledger/citation_audit.csv`: `class_mapping`, `exact_locator`, `resolver_result`, `verdict`, `reviewer` columns; `does_not_imply` remains on the L0 rows in `ledger/theorems.jsonl`.

## Not adopted

- The shard's class token `GLOBAL-foundational`, `UNRESOLVED`, `NON-AF-COSMOLOGICAL` are **not** classes; under controller directive astra-w07adj-02 the canonical ledger restricts `class_ids` to the four frozen classes and carries such labels as `ledger_tags` only.
