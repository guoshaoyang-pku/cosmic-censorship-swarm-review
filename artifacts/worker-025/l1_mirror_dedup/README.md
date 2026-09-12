# W025-L1-MIRROR-DEDUP-01 — mirror-graph vs identifier-graph reconciliation at the frozen L1 audit

Bounded worker task, `worker-025`, node `L1`, gate `G-LIT`, classes
`AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH`.
Read-only: no ledger, map, schema, rubric or detector file was written.

## Question

At `ledger/citation_audit.csv` `sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
the declared `mirror_of` graph and the identifier-keyed work graph are two different
dedup instruments. Do they agree, and what deterministic rule keyed on the *resolved
record* produces the canonical-merge map the L1 owner needs?

## Inputs (pinned, re-measured at run time)

| input | sha256 |
|---|---|
| `ledger/citation_audit.csv` (97 rows) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/worker-025/l1_identity_audit/report.json` (prior worker-025 evidence) | `5bd6b3263feaf9ff497a1c96c2afb269e9c7cad088d1c377e1b016d1d4f3603b` |

## Method (rules R1–R6, pre-registered)

1. `identifier_key` = normalized DOI, else normalized arXiv id (legacy `subj/NNNNNNN`
   also matches its bare numeric form).
2. Rows are unioned when they share an identifier **or** are joined by a declared
   `mirror_of` edge; a mirror edge is *suspect* (excluded) when the endpoint titles
   disagree or the year gap exceeds 4.
3. `artifact_class` is read from the record URL only: `PREPRINT` (arXiv),
   `PUBLISHED` (Crossref / OpenAlex / INSPIRE record / DOI), else `UNKNOWN`.
4. Same component + same class + title agreement → **MERGE_DUPLICATE** with a
   pre-registered precedence (resolved locator, then verification-method rank
   `primary-page-fetch > crossref-api > inspirehep-api > openalex`, then evidence
   rank, then lowest citation id). Different classes → **LINK_ONLY**. No shared
   identifier at all → **MIRROR_ONLY_LINK**. Title conflict → **SUSPECT_MIRROR**.
5. A merge proposal must union `used_by_theorems` and `class_mapping`, so no
   citation edge is lost; the ledger itself is not written.

### Amendment 1 (disclosed, not silent)

The initial rule (Jaccard ≥ 0.90 only) failed prediction P7 on two legitimate
variants: `SRC-086` (Crossref) drops the subtitle present in `SRC-057`
(Jaccard 0.70), and `SRC-024`/`SRC-087` differ only by `spacetimes` vs
`space-times` (Jaccard 0.82). The initial run is preserved byte-for-byte
(`report.v1-initial-rule.json`, `d2f3f8cc91a8`); amendment 1 adds compact-form
equality and a long-title prefix rule. `SRC-093 → SRC-033` remains suspect
(different works, year gap > 4).

## Result — `report.json`

| quantity | value |
|---|---|
| rows / unique ids | 97 / 97 |
| identifier pair edges / unique pairs | 10 / 9 |
| mirror edges declared / suspect | 12 / 1 |
| work components | 85 |
| MERGE_DUPLICATE components (rows superseded) | 3 (4) |
| LINK_ONLY components | 7 |
| MIRROR_ONLY_LINK components | 1 |
| proposed net row reduction | 4 |

### Merge proposal (owner action; not applied)

| component | canonical | superseded | edges the naive merge would drop |
|---|---|---|---|
| `SRC-020,SRC-060,SRC-072` | `SRC-060` (Crossref) | `SRC-020`, `SRC-072` | `D-002` + class `AF-SCC-C0-VAC-GEN` (on `SRC-072`) |
| `SRC-044,SRC-067` | `SRC-067` (Crossref) | `SRC-044` | `T-101` (on `SRC-044`) |
| `SRC-059,SRC-071` | `SRC-059` (Crossref) | `SRC-071` | none |

### Findings

- **F1 (major)** `SRC-093` declares `mirror_of SRC-033` but is a different work
  (title, year 2009 vs 2018, DOI, arXiv id). The edge is excluded from the union
  and flagged; it should be corrected or withdrawn by the owner.
- **F2 (major)** `SRC-020` and `SRC-044` carry no DOI and no arXiv id and are
  reachable **only** through `mirror_of`. Identifier-keyed dedup misses them, so a
  dedup keyed on the identifier string alone is incomplete.
- **F3 (info)** `SRC-041`/`SRC-054` share no identifier either; the mirror edge is
  the only link.
- **F4 (major)** For two of the three merge groups, merging on the identifier alone
  would drop citation edges (`D-002`, `T-101`) and one class mapping. The union
  rule is required, not optional.
- **F5** Seven components are preprint/published pairs and must stay **linked, not
  merged**: `SRC-021/056`, `SRC-033/088`, `SRC-023/055`, `SRC-002/068`,
  `SRC-066/089`, `SRC-057/086`, `SRC-024/087`.

## Controls (all fired)

`C2` identifier-only graph = 88 components / 9 multi-row groups; `C3` a rewritten
`SRC-072` title flips the group to a title conflict; `C4` reversed row order gives
an identical merge signature; `C5` swapping the two citation-edge lists leaves the
union unchanged; `C6` no cross-class merge is proposed; `C7` the legacy arXiv
alias joins. `P1`–`P7` all pass; `P8` (determinism) is the byte-identical
`run2.stdout.txt` / `run3.stdout.txt` pair.

## Reproduction

```bash
python3 artifacts/worker-025/l1_mirror_dedup/run_l1_mirror_dedup_025.py --csv ledger/citation_audit.csv \
  --expected-pin 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9
python3 artifacts/worker-025/l1_mirror_dedup/verify_readme_numbers_025.py
```

## Falsifier

Re-run the instrument twice. Falsified if the measured pin differs, any
pre-registered prediction fails without being recorded, the two reports are not
byte-identical, or any disposition is not derivable from R1–R6 on the pinned bytes
alone.

## Non-claims

Not a mathematical or physics claim; not a gate verdict (G-LIT stays pending and
only Astra/leads move it); no frozen file written; the merge map is an unfrozen
proposal. Title agreement is a normalization heuristic, not an identity proof.
