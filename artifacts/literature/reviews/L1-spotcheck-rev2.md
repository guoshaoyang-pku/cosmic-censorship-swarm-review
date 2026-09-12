# Independent re-fetch spot check — literature rev 2 (G-LIT)

- **Bound to:** `ledger/theorems.jsonl` = `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72`,
  `ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
- **Checked at:** 2026-09-12T00:17+08:00 (hashes re-measured at check time)
- **Structured evidence:** `artifacts/literature/reviews/L1-spotcheck-rev2.json`
- **Purpose:** supply the `>=3 independent re-fetch spot checks` that `controller_gate_audit.G-LIT` records as missing at the frozen hash.

## Result

| channel | targets | fetched | pass | pass w/ caveat | partial | contradiction |
|---|---|---|---:|---:|---:|---:|
| independent subagent (no ledger access, no writes) | SRC-002, SRC-004, SRC-057, SRC-059 | 4/4 HTTP 200 | 3 | 0 | 1 | 0 |
| lead re-fetch (corroborating, **not** independent) | SRC-058, SRC-016, SRC-069, SRC-081 | 4/4 HTTP 200 | 3 | 1 | 0 | 0 |
| additional DOI corroborations | SRC-002, SRC-058 | 2/2 HTTP 200 | 2 | 0 | 0 | 0 |

**The `>=3 independent` criterion is met (4 independent checks). 0 title/author/excerpt contradictions.**

## What the checks found

1. **Every load-bearing excerpt was present on the live primary page** after whitespace/LaTeX/markup
   normalization. No stored quote was contradicted. The ellipses in SRC-002 and SRC-004 skip exactly
   the sentences the ledger says they skip (for SRC-004, the deferred retrieval of the interior-data
   assumptions — the sentence T-301's scope caveat depends on).
2. **The one `partial`** (SRC-002) is a locator-presentation artifact: the arXiv page shows the 2019
   submission / 2022 revision and no journal-ref, so the ledger's 2023 Annals year is invisible
   *there*. The lead fetched the Crossref record for `10.4007/annals.2023.198.1.3` and confirmed
   title, authors, volume 198(1) and published 2023-07-01. Not a citation error. Crossref exposes no
   page field, so pages "231-391" remain uncorroborated.
3. **SRC-081's accepted-in-press claim is confirmed verbatim** on the live arXiv page: "Version
   accepted for publication in Inventiones Mathematicae". Keep the `accepted-in-press` level; do not
   promote to `peer-reviewed` until volume/pages appear.
4. **Two non-reproducible `exact_locator` fields confirmed** (SRC-016, SRC-069): both are
   search-query URLs, so a later auditor re-fetching only `exact_locator` would fail even though
   `evidence_url` resolves. SRC-069 was *not* in citation-integrity-C's 28-row enumeration, so that
   enumeration was incomplete. This is a metadata defect, not an evidence overstatement.
5. **No verification_status overstatement** (`theorems.jsonl` × `citation_audit.csv` cross-join):
   0 rows claim abstract-level verification without an abstract/full-text source; the single
   `unverified` row (D-009) is `provisional` and metadata-only. The assignment's falsifier does not
   fire at this hash.
6. **Metadata caveats, not errors:** SRC-058's venue string says "194 pp" but Crossref has no page
   field and arXiv says 132 pages — uncorroborated, record as a caveat; SRC-069's title has an
   un-annotated spelling variant (integrity-review item still open at metadata level).

## Limitations

Abstract-level only; no paywalled body text. The 8 targets are purposive (load-bearing,
machine-resolvable), not a random sample of 97. 2025/2026 preprint-only entries were not live-fetched.
Only the 4 subagent checks are independent of ledger authorship.

## Standing

This artifact supplies evidence; it does not accept L0/L1 and sets no gate verdict. L0/L1 remain
`active`, `validation_status: unverified`, and G-LIT remains `pending` until a blind reviewer verdict
binds to the hashes above.
