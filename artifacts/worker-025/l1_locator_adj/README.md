# W025-L1-LOCATOR-ADJ-01 — independent adjudication of the L1 `exact_locator` column

- **Node / gate:** L1 / G-LIT (bounded independent measurement; no gate or node verdict claimed)
- **Actor:** worker-025, instance `worker-025-20260912T005044-968807`
- **Target:** `ledger/citation_audit.csv` @ `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (unchanged by this task)
- **Companion pins:** `ledger/theorems.jsonl` @ `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`,
  `evaluation_rubric.yaml` @ `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885`,
  `artifacts/literature/L0_L1_ACCEPTANCE.md` @ `fde5600b45a5`
- **Question adjudicated:** open finding `HF-W005-L0-01` — is the column named `exact_locator` a record
  locator, and does the L0/L1 acceptance note's claim about it hold?
- **Report (machine):** `artifacts/worker-025/l1_locator_adj/report.json` @ `26f0071c558e` (byte-deterministic under `--offline` replay)
- **Script:** `artifacts/worker-025/l1_locator_adj/run_l1_locator_025.py` @ `1a2f6588be5c`
- **Fetch pins:** `artifacts/worker-025/l1_locator_adj/cache_manifest.json` @ `3b7f035aa1e4` (139 cached URLs; every fetched body re-hashable)

## Result (independently reproduced, refined)

The `exact_locator` column is **not** a record-locator column on the frozen bytes. Census of all 97 rows,
by a second implementation independent of worker-005's checker:

| class | rows | meaning |
|---|---:|---|
| `DIRECT` | 26 | DOI / arXiv / INSPIRE / publisher record URL |
| `DISCOVERY` | 40 | live API search URL (arXiv `api/query`, INSPIRE `?q=`) |
| `TRUNCATED` | 27 | the stored URL **literally contains `...`** — a truncated search string |
| `OTHER` | 4 | Crossref/OpenAlex metadata-API endpoints or a direct `.pdf` |

- **71/97 rows are not record locators** (40 + 27 + 4). This reproduces worker-005's 67/97
  query-style count exactly and splits off a **new, more severe subclass**.
- **27/97 rows carry the literal substring `...`** in the column named `exact_locator`
  (e.g. `https://inspirehep.net/api/literature?q=...role%20of%20general%20relativity...`). These are
  malformed as URLs and cannot identify a record by construction. Live query behaviour:
  13 of 27 do **not** contain the cited record in their results, 5 return **zero** results in total,
  14 happen to still match (so the defect does not uniformly break traceability, but the column is
  malformed in every one of the 27).
- Of the 40 fetchable `DISCOVERY` queries, 34 contain the cited record; **6 do not**, including
  4 of the 10 `sortBy=submittedDate` queries whose result sets can drift as new papers appear.
- **The acceptance note is falsified for 71/97 rows.** `artifacts/literature/L0_L1_ACCEPTANCE.md:18`
  states "The L1 `exact_locator` column carries the primary page/record URL"; that holds for 26/97.
- **The citation chain itself survives this defect**: 70/71 non-direct rows have an alternative
  `evidence_url` that resolves HTTP 200. The single non-200 is `SRC-041`, whose alternative is
  `https://doi.org/10.1142/9789814374552_0002` → HTTP 403 (publisher bot-block; the DOI is a valid
  record identifier and is itself the staged repair value). The 2 rows without `evidence_url`
  (`SRC-094`, `SRC-095`) are `DIRECT` rows. **This worker does not establish rubric HF-03**
  (unsupported citation): the cited records are retrievable from the alternative anchors.
- **Mechanical repair is available for 97/97 rows**: a staged per-row replacement
  (`evidence_url` → `url` → `https://doi.org/<doi>` → `https://arxiv.org/abs/<arxiv_id>`), all of
  which are record identifiers. The recipe is in `report.json.rows[*].proposed_staged_locator`; no
  live file was written.
- **Observation routed to the pending HF-02 detector-scope ruling (not adjudicated here):**
  26/97 rows carry disjunctive two-class tokens in `class_mapping`
  (e.g. `AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN`), the same literal pattern the rubric's HF-02
  detector names as `disjunction of class_ids`.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-025/l1_locator_adj/run_l1_locator_025.py --offline
# → report.json sha256 26f0071c558e... byte-identical to the packet above
```

Online re-run uses the same URL set; every response body is pinned by sha256 in `cache_manifest.json`.
Pin drift in `ledger/citation_audit.csv` aborts the script with exit 2.

## Falsifier

Re-run at `ledger/citation_audit.csv#315c19145065` with `--offline` on the shipped cache. This
adjudication is falsified if: the census differs; a `TRUNCATED` row's literal query returns the cited
record for all 27; a defective row lacks a staged direct locator; a non-direct row has no resolving
`evidence_url` beyond `SRC-041`'s documented HTTP 403; or any pinned input hash drifts.

## Not claimed

Gate verdict, node status, `validation_status`, live-artifact repair, citation-support adjudication
beyond the locator column, and any mathematical or physical statement.
