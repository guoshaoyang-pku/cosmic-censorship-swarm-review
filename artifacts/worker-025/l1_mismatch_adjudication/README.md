# W025-L1-MISMATCH-ADJ-01 — DOI-side adjudication of spot check #4's MISMATCH verdicts

**Actor** worker-025 · **Node** L1 · **Gate** G-LIT · **Classes** `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN` (rows also load `AF-WCC-*` theorem rows via `used_by_theorems`).
**Question.** L1 spot check #4 (`artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json`,
sha256 `90419534696974ee…`) reported three MISMATCH hard failures: `SRC-004`, `SRC-025`,
`SRC-033`. Are those genuine citation defects, or artifacts of comparing an arXiv preprint
against a journal-of-record citation?

**Method.** After pre-registering the frozen ledger revision (`315c19145065a5f9…`, the sha the
G-LIT criterion names) and the exact CSV records (`freeze/frozen_inputs.json`,
`freeze/frozen_rows.json`, both written before any network call), the *declared DOI* of each
contested row was fetched from Crossref (registry of record) and compared against the ledger on
work identity — title, author families, year, container/volume/page tokens, DOI identity. Raw
response bytes are kept under `raw/` with per-fetch sha256. Seven fetches, all HTTP 200,
172,280 bytes; the ledger was re-hashed after the fetches and did not drift.

**Result — all three MISMATCH verdicts are refuted at metadata level.**

| row | ledger class | declared DOI | Crossref record | verdict |
|---|---|---|---|---|
| SRC-004 | C0+C2 | 10.4007/annals.2025.202.2.1 | Annals of Math. 202(2), 2025, title exact | **DOI_MATCH** |
| SRC-025 | C2 | 10.1007/s00220-020-03923-w | Comm. Math. Phys. 382, 1263–1341, 2021, title exact | **DOI_MATCH** |
| SRC-033 | C2 | 10.1088/1361-6382/aadbcf | Class. Quantum Grav. 35(19), 195010, 2018, title exact | **DOI_MATCH** |

The divergence spot check #4 measured is the **version of record**: e.g. SRC-004 was fetched from
`arXiv:1710.01722` (submitted 2017) while the ledger cites the 2025 Annals article; SRC-025 was
fetched from `arXiv:2001.11156` (v1 2020) while the ledger cites the 2021 CMP article. The
ledger's own `venue` fields already carry both the journal citation and the arXiv version, so the
ledger is correct as written. These three should be re-dispositioned as false positives of the
spot-check comparator, **not** carried as G-LIT hard failures.

**Controls (all three discriminating, all passed).**
- `CTRL-NEG-MUTATED-DOI` — SRC-004 DOI with the last digit changed resolved 200 to a *different*
  Annals article (title mismatch, no author overlap) → rejected, so the pipeline is not a rubber stamp.
- `CTRL-NEG-SYNTHETIC-TITLE` — SRC-004 ledger row with title replaced by "Zeta functions of
  nothing", compared against the real fetched record → `DOI_MISMATCH`.
- `CTRL-POS-SRC-001` — a row spot check #4 scored MATCH → `DOI_MATCH`.

**Self-caught comparator defect (kept as evidence).** The first pass classified SRC-033
`DOI_MISMATCH` because the registry writes "Λ &gt; 0" where the ledger writes "Lambda > 0" —
a normalizer false positive of exactly the kind under adjudication. `report.firstpass.json` is
retained; `report.json` records the correction (HTML unescape + Greek transliteration, revision 2).
No verdict from the first pass is used.

**Falsifier.** Any target row whose declared DOI fails to resolve, or whose Crossref record
disagrees with the ledger on work identity (title/authors) or year beyond ±1, confirms a genuine
defect and refutes this adjudication; the adjudication is void if any control above fails or if
the ledger hash drifts from `315c19145065a5f9…` during the fetch window. Status:
**NOT_TRIGGERED** at `2026-09-12T00:20+08:00`; ledger stable before and after, controls passed.

**Frozen inputs / artifacts.**
- ledger `ledger/citation_audit.csv` sha256 `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (before and after)
- spot check #4 artifact sha256 `90419534696974ee8f77dd35b8959a29eaf505a60546df996d214f826c08be58`
- report `report.json` sha256 `676f080d485d8221b4189a38bffc1fff9373ef81e8f8d39b90884a209053a08b`
- controls `controls.json` sha256 `46a20574650cf412d33a9cde5cbc9bd13e1e34d9659d5e3d2275c12f822b9c9a`
- all files listed in `SHA256SUMS`

**What this does NOT claim.** Metadata identity only. It does not verify theorem-to-class scope
binding for `D-002/D-003/D-006/D-007/T-301/T-305/T-401/T-402/T-505/T-508`, does not clear the
locator-quality findings in spot check #4 (SRC-009/016/017/033 `exact_locator` are search queries,
not exact locators — still open), and sets no gate verdict or node status. Reproduction:
`python3 freeze_inputs.py && python3 adjudicate.py` (network required; read-only on the ledger).
