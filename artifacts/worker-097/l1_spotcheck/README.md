# worker-097 — independent L1 re-fetch spot check (3rd check at the frozen L1 hash)

Task: `astra-life02-l1-spotcheck` — bring the count of independent re-fetch spot
checks bound to the frozen L1 hash to the required `>=3`.
Assignment scope: node `L1`, gate `G-LIT`, classes
`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`.

## Result

| item | value |
|---|---|
| target | `ledger/citation_audit.csv` |
| frozen hash (`sha256`, before and after fetch) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| drifted during fetch | **no** |
| rows checked | 4 (`SRC-003`, `SRC-050`, `SRC-075`, `SRC-083`) |
| citation verdicts | 4 MATCH / 0 PARTIAL / 0 FAIL / 0 fetch failures |
| class-scope notes | 2 (one actionable qualifier on `SRC-050`; one dual-class binding note on `SRC-083`) |
| process finding | `W097-PF-1` clock discipline (see below) |

Rows are disjoint from every earlier check: `reviews/L1-spotcheck-10.json`,
`reviews/L1-spotcheck-11.json`, `artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json`,
`artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json`,
`artifacts/worker-047/l1_spotcheck/spotcheck_report.json`,
`artifacts/worker-076/l1_spotcheck_frozen/spotcheck_report.json`,
`artifacts/literature/reviews/L1-spotcheck-rev2.json`.

## Method and provenance

Primary endpoints were re-fetched live on 2026-09-12 (00:19–00:20 +08:00):

* `https://export.arxiv.org/api/query?id_list=<arxiv_id>` for each row;
* `https://api.crossref.org/works/<doi>` for the journal rows;
* `https://api.datacite.org/dois/10.48550/arXiv.2204.09891` for `SRC-003`.

Raw response bytes are archived under `raw/` with per-file `sha256` in
`raw/raw_sha256.txt` and inside the report's `raw_responses` blocks.
`crossref_SRC-083.json` was HTTP 429 on the first attempt (headers kept as
`raw/crossref_SRC-083.attempt1.http429.headers`) and HTTP 200 on retry; only the
200 bytes are hashed. No ledger text was used as evidence for its own
verification. Titles/authors/years/venues/DOIs and each `evidence_excerpt`
fragment were compared against the fetched text with accent- and
LaTeX-normalised substring matching; all four excerpts are verbatim-supported
(with elisions where the ledger marks `...`).

## Findings for the leads (no gate verdict is claimed)

* `SRC-050` (`class_mapping = AF-SCC-C2-VAC-GEN`): the linked theorem `T-510`
  correctly carries `class_ids: []` and only `informs_classes:
  [AF-SCC-C2-VAC-GEN]`, because the paper's C²-inextendibility result is for the
  Einstein–Maxwell-(real)-scalar system (matter, spherical symmetry), not vacuum.
  Remedy: qualify the citation row's mapping (e.g. `... (informs; matter model)`)
  or copy `T-510`'s `EM-SCALAR`/`OTHER-MODELS` ledger tag, so class-coverage
  counts do not read it as a vacuum-class theorem.
* `SRC-083` (`class_mapping = AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN`): consistent
  with the dual `class_ids` on the linked `T-526`, which states its own
  `does_not_imply` caveats. Recorded as an intentional dual binding, not a
  composite-class violation.
* `W097-PF-1`: `SRC-075`'s recorded `fetched_at` (2026-09-12T00:45:00+08:00) is
  later than this re-fetch's wall-clock, so it cannot be a real observation
  time; consistent with controller finding CF-14.

## Files

| file | sha256 |
|---|---|
| `spotcheck-l1-097.json` | `851412d3a709c82c8ede0cc22378236ac02a540ae946a889b43389418f4e67ed` |
| `run_spotcheck_097.py` | `e6cf610b442d8da69a9d6efb72493bbf42f6006a440fde0a5335251ec6920221` |
| `raw/raw_sha256.txt` | `e3f2751b15922bb569c2f87cd9817071fea4dda8e47d2fae18d9474988247a49` |

Reproduce the report from the archived raw bytes (no network):

```bash
cd artifacts/worker-097/l1_spotcheck && python3 run_spotcheck_097.py
```

## Falsifier / stop rule

Falsified if any cited row re-fetched at another wall-clock time contradicts the
archived raw response, or if `ledger/citation_audit.csv` is re-measured at a
hash other than `315c19145065…` while this check is counted toward `G-LIT`.
Worker authority limit: `validation_status: unverified`; no gate verdict, no
node completion, no ledger edit.
