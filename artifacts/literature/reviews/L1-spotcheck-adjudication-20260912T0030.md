# L1 spot-check adjudication — lead review of the independent re-fetch corpus

- **Adjudicator:** `astra-lead-literature` (ledger author — this is **not** an independent verdict)
- **Frozen pins under review:** `ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 rows);
  `ledger/theorems.jsonl` = `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` (62 rows)
- **Machine record:** `artifacts/literature/reviews/L1-spotcheck-adjudication-20260912T0030.json`
  (`sha256:261373902972bc532f0196a11c85d4eaaa05e83bdee251494eb8d1a550bd307b`)
- **Assignment consumed:** `astra-life02-l1-spotcheck`
- **No hash was moved.** Neither ledger file was edited by this lifecycle.

## 1. The acceptance test is met, with margin

`astra-life02-l1-spotcheck` asked for **two further** independent re-fetch spot checks at the frozen L1
hash, distinct from `deepseek-flash-07` and from each other, each recording the fetched source hash, a
MATCH/PARTIAL/FAIL verdict, the locator, and a post-fetch ledger re-hash. The corpus now contains:

| | count |
|---|---:|
| spot-check artifacts examined (snapshot 00:30) | 20 |
| **qualifying** (frozen-hash binding + post-fetch re-hash + ≥1 raw-body sha256 + ≥1 real comparison) | **12** |
| distinct reviewers among qualifying checks | **11** |
| disqualified | 8 |

Requirement was 3 at the frozen hash. Qualifying reviewers: `worker-006`, `worker-022`, `worker-026`,
`worker-028`, `worker-031`, `worker-041`, `worker-056`, `deepseek-flash-07`, `worker-070`, `worker-077`,
`worker-079` (11 distinct; `worker-026` qualifies twice with a preregistered and an amended instrument).
Disqualified and why: `worker-023` (three files — no post-fetch re-hash recorded; kept as instrument
history), `worker-031/ERRATUM-01.json` (an erratum, not a check), `worker-063` and `worker-075` (all
fetches failed — environment, not evidence), `worker-086` (no raw-body sha256 stored), `worker-097` (no
comparison verdicts in the artifact). None of the disqualifications is a ledger defect and none removes a
qualifying check: `worker-031`'s erratum explicitly leaves its measured verdicts and byte hashes
unchanged.

**Decision: `astra-life02-l1-spotcheck` = MET.**

## 2. No bibliographic MISMATCH survives adjudication

Twenty MISMATCH/FAIL verdicts were reported across the corpus. Seventeen are instrument false positives
and one is unresolved; two are confirmed. Every false positive is one of five mechanical classes:

| instrument class | count | why it is not a ledger defect |
|---|---:|---|
| fixed first-400-char excerpt metric | 9 | the ledger excerpt is a mid-abstract fragment; an offset-aware re-read of the same hashed raw body scores 0.915 where the fixed-offset metric scores 0.0025 (`worker-026`, on `SRC-025`) |
| excerpt metric + year convention | 5 | the ledger year is the journal year; the fetch returns the arXiv v1 year. Titles/author match. |
| title convention (Crossref drops the arXiv subtitle) | 1 | `SRC-086`: same DOI, same venue; token-Jaccard 0.556 is the subtitle |
| HTML/diacritic normalisation | 3 | `SRC-071` `<i>T</i><sup>3</sup>` / `Ringström`; `SRC-069` `Chruściel`. `worker-023` retracted its own rev-1 MISMATCH for exactly this and shipped the fix as `spotcheck-l1-023.rev1-instrument-bug.json`. The third (`SRC-029`) is the one item left **unresolved** |
| non-replayable `exact_locator` | 2 | `SRC-069`, `SRC-077`: truncated INSPIRE search URLs — a real defect, counted under §3 |

Unresolved: `SRC-029` (`author=false`, title and year exact). The same failure shape as the confirmed
`Chruściel` diacritic case, so it is recorded as *unresolved pending a diacritic-folded re-read*, not as a
defect.

A process finding worth keeping: **the pre-registered fixed-offset metric produced a 22% false-positive
rate**, and `worker-026` refuted its own pre-registered rule against hashed raw bodies before publishing.
Any mechanical reuse of first-N-character similarity as a quote-support test needs an offset/window search.

## 3. The one defect class that survives: `exact_locator` is not a locator

| | count |
|---|---:|
| rows in the frozen ledger | 97 |
| rows whose `exact_locator` is a search query or a truncated URL | **67 (69%)** |
| distinct locator strings covering those 67 rows | **43** |
| rows sharing a single locator string (worst case) | **7** |
| rows carrying a direct per-record locator | 30 |

Worst offenders: `search_query=all:"inextendibility" AND all:"Cauchy horizon"` is the `exact_locator` of
**seven different rows**; `ti:"inextendibility" AND all:Schwarzschild` covers five; the Costa
Einstein–Maxwell-scalar query covers five. All 67 affected rows are `verification_status=verified-api`
(`arxiv-api` 38, `inspirehep-api` 29) — so the *verification level* is honestly stated; the column name is
what is wrong. Every affected row already carries a resolving `evidence_url` / `doi` / `arxiv_id`.

This is judgeable now: the G-LIT criterion "ledger rows have resolvable locators" either (a) fails at
`315c19145065` under a per-row uniqueness reading, or (b) passes under a "the query resolves" reading
provided the controller records that `evidence_url` is the locator column and `exact_locator` is a
query-provenance column. **It cannot pass silently under both.** Recorded as blocker **BL-4**.

A metadata-only patch that rewrites the 67 cells from `evidence_url` is ~30 minutes of work, but it moves
the L1 hash and would void all 12 qualifying spot checks. Consistent with `reviews/A1-rebind-coverage.md`
§1–2 and the prior lifecycle's freeze-first decision, this lifecycle does **not** apply it and asks for a
ruling.

## 4. What this changes for G-LIT

- **L1's `>=3` spot-check clause is satisfied** — 12 qualifying checks, 11 reviewers, zero surviving
  bibliographic mismatches.
- **L1's "resolvable locators" clause is now the live question**, and it is a one-line policy ruling
  (BL-4) or a bounded hash-moving patch.
- **L0 still has no accept at its frozen hash.** The three revise verdicts (lead-audit 3.0, flash-16 3.5,
  flash-17 2.5) are pinned to a superseded hash; at `ce42d205e761` the class-token and unresolved-citation
  findings are closed, but `conclusion_type=theorem` on 30 rows with no `artifact_refs` (flash-17 HF-01)
  and `source_meta` on 0 of 62 rows (lead-audit HF-03) remain open. The open 2-reviewer resource request
  `lit-l3-20260912-010` is the shortest path; no duplicate request is issued here.
- **No gate verdict is claimed.** Only the controller moves gate verdicts.

## 5. Falsifiers for this adjudication

1. A qualifying check whose frozen-hash binding does not actually appear in the named file.
2. A MISMATCH/FAIL recorded here as a false positive whose work identity (DOI/title/author) does in fact
   differ from the ledger row.
3. A ledger hash change after 00:30, which voids the binding of every check listed.
4. A replay showing a search-query `exact_locator` uniquely and stably identifies the recorded work.
