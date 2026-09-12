# W070-L1-ANCHORS-01 — unanchored provenance census (worker-070)

**Task.** For every `provenance.sources` row declared `identifier: null, status: unresolved` in the
three class schemas, measure whether the pinned L1 ledger already carries a candidate row, and if
not whether a registered candidate primary locator resolves live. Coverage/pointer census only:
it asserts nothing about whether a source entails a schema field.

- **Class binding:** AF-WCC-VAC-GEN (F1) · AF-SCC-C2-VAC-GEN (F2a) · AF-SCC-C0-VAC-GEN (F2b)
- **Node/gate:** L1 · G-LIT
- **Frame (pre-registered before any fetch):** `frame.json#679cb736603d` — contains the pins, the
  12 rows derived from the pinned schema bytes, one deterministic ledger-match rule per row, the
  candidate registry, the labels and the controls.
- **Status:** COMPLETE · `corpus_valid=True` · all 5 controls PASS · pins unchanged before/after fetch
- **Artifacts:** `report.json#d177a78c83be` (pre-registered run) · `addendum.json#1b973d5b80bf`
  (clearly-labelled post-frame candidates) · `run.log` · `raw/` (every fetched response, hashed)

## Pins

| input | sha256 |
|---|---|
| `ledger/citation_audit.csv` (L1) | `315c19145065a5f9…` |
| `ledger/theorems.jsonl` (L0) | `a1674f09497975cf…` |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79e…` |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd…` |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86…` |

## Census (12 rows)

| item | class | concept (needed_for) | label | L1 match strength | pointer |
|---|---|---|---|---|---|
| F1-P1 | AF-WCC-VAC-GEN | AF data + weighted Sobolev (`data_class, regularity`) | CANDIDATE_RESOLVED_NOT_IN_LEDGER | none (0 rows) | CBY 1980, Bartnik 1986, Christodoulou–O'Murchadha 1981 — all live |
| F1-P2 | AF-WCC-VAC-GEN | MGHD existence/uniqueness (`regularity, quantifiers D2`) | LEDGER_ROW_EXISTS | exact DOI | SRC-073 Choquet-Bruhat–Geroch 1969 |
| F1-P3 | AF-WCC-VAC-GEN | positive mass + rigidity (`data_class.adm_mass`) | CANDIDATE_RESOLVED_NOT_IN_LEDGER | none (0 rows) | Schoen–Yau 1979, Schoen–Yau 1981 (corrected DOI), Witten 1981, Bartnik 1986 — all live |
| F1-P4 | AF-WCC-VAC-GEN | future asymptotic predictability (`conclusion.equivalent_standard_formulation`) | LEDGER_ROW_EXISTS | phrase only | 16 on-topic "cosmic censorship" rows; no definition source row |
| F1-P5 | AF-WCC-VAC-GEN | WCC known status (`no status claim is made`) | LEDGER_ROW_EXISTS (informational) | phrase only | 16 on-topic rows |
| F2a-C1 | AF-SCC-C2-VAC-GEN | MGHD (`regularity`) | LEDGER_ROW_EXISTS | exact DOI | SRC-073 |
| F2a-C2 | AF-SCC-C2-VAC-GEN | C2 SCC statement + obstruction | LEDGER_ROW_EXISTS | generic token | 24 rows via `inextendib`; 0 statement-level |
| F2a-C3 | AF-SCC-C2-VAC-GEN | Kerr maximal extension (`known_obstruction`) | LEDGER_ROW_EXISTS | generic token | 18 rows via `kerr`; not the extension paper |
| F2b-C1 | AF-SCC-C0-VAC-GEN | MGHD (`regularity`) | LEDGER_ROW_EXISTS | exact DOI | SRC-073 |
| F2b-C2 | AF-SCC-C0-VAC-GEN | C0-inextendibility + exact hypotheses | LEDGER_ROW_EXISTS | generic token | 10 rows via `inextendib` (SRC-005/024/…) |
| F2b-C3 | AF-SCC-C0-VAC-GEN | Kerr maximal extension | LEDGER_ROW_EXISTS | generic token | 18 rows via `kerr` |
| F2b-C4 | AF-SCC-C0-VAC-GEN | H2_loc-inextendibility vs C0 (`anti_scope`) | LEDGER_ROW_EXISTS | generic token | SRC-024/087 via `holonomy` (C^{0,1}, **not** H2_loc) |

**Aggregate.** 10/12 rows have ≥1 matching L1 row; **only 3/12 by exact identifier** (all three are
the same row, SRC-073). 7/12 match on title text only, and for 5 of those the rule that fires is a
single generic token (`kerr`, `inextendib`, `holonomy`). 2/12 have no L1 row at all.

## Live-resolved candidate pointers (metadata only)

| candidate | identifier | year/venue | raw hash |
|---|---|---|---|
| Choquet-Bruhat–York, *The Cauchy problem* | Crossref query (book chapter) | 1980, GRG vol. 1 | `raw/crossrefq_cby1980.json` |
| Bartnik, *The mass of an asymptotically flat manifold* | `10.1002/cpa.3160390505` | 1986, CPAM | `raw/crossref_bartnik1986.json` |
| Christodoulou–O'Murchadha, *The boost problem in GR* | Crossref query | 1981, CMP | `raw/crossrefq_com1981.json` |
| Schoen–Yau, *On the proof of the positive mass conjecture* | `10.1007/BF01940959` | 1979, CMP | `raw/crossref_sy1979.json` |
| Schoen–Yau, *Proof of the positive mass theorem II* | `10.1007/BF01942062` **(post-frame correction; registered `…093` is 404)** | 1981, CMP | `raw/crossrefq_sy1981_query.json` |
| Witten, *A new proof of the positive energy theorem* | `10.1007/BF01208277` | 1981, CMP | `raw/crossref_witten1981.json` |
| Carter, *Global structure of the Kerr family* | `10.1103/PhysRev.174.1559` | 1968, Phys. Rev. | `raw/crossref_carter1968.json` |
| Hawking–Ellis, *The Large Scale Structure of Space-Time* | `10.1017/CBO9780511524646` | 1973, CUP | `raw/crossref_he1973.json` |

Carter 1968 and Hawking–Ellis 1973 were fetched **after** the pre-registered run (addendum) because
their items matched the ledger only by generic token; they are the work-specific pointers the
lexical rule could not force.

## Residual gaps reported, not filled

- **H2_loc:** 0 L1 rows match `h2 loc / h^2`; closest are 1 `L^s_loc` row (SRC-048) and 4 Lipschitz
  rows (SRC-047, 080, 081, 096). The schema's `anti_scope, must_not_conflate` item has no
  H2_loc-specific anchor in the pinned ledger.
- **F2a-C2:** the C2 SCC *statement* item is matched by 24 inextendibility rows but no row states
  the C2 formulation itself; SRC-004/SRC-090 are the ledger's closest, and SRC-090's `C^k` is
  unspecified (see `artifacts/literature/FORMULATION_ANCHORS.md`).
- **F1-P1 / F1-P3:** 5 distinct live candidate locators exist but are not ledger rows; binding them
  is a ledger-owner action (the ledger is under review hold).

## Controls (all PASS)

- `positive_doi` 10.1007/BF01645389 → "Global aspects of the Cauchy problem…"
- `negative_doi` 10.9999/does-not-exist-w070 → HTTP 404, not resolved
- `positive_arxiv` 1711.11380 → expected title tokens
- `parser_fixture` → local fixture parses as registered
- `idempotence_doi` → second fetch byte-identical to the first

## Falsifier

Re-run `run_anchors070.py` at the same pins. Falsified if any item's classification changes, if a
candidate reported resolved re-resolves with different title tokens, or if any control returns
false. A pin sha256 change **voids** the run rather than falsifying it. A demonstration by the
ledger owner that a keyword-matched row does not support the item's `needed_for` field does not
falsify this census (which measures lexical coverage); it changes the binding decision.

## Authority

Worker evidence only. No ledger, schema, map, review or gate artifact was written; no gate verdict,
no node completion, no claim of theorem. Raw responses are kept under `raw/` and hashed in
`report.json`/`addendum.json`.
