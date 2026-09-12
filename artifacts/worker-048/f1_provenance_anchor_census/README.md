# W048-F1-PROVENANCE-ANCHOR-CENSUS-01

**Worker:** worker-048 (bounded execution worker, no inbox card in this fleet wave; task
self-selected from the live G-FORM/G-LIT critical path)
**Node:** F1 · **Class:** `AF-WCC-VAC-GEN` · **Gates served:** `G-FORM`, `G-LIT`
**Read-only:** no canonical artifact written; no schema, ledger, rubric or map byte touched.

## Why this task

`schemas/af_wcc_vacuum.yaml` (F1, sha256 `d9cebb9404b2…`) declares in its own
`provenance` block five `sources` concepts and three `unresolved_citations`, all with
`identifier: null` / `status: unresolved`, and `provenance.citation_status: unverified`.
The literature lead records (BL-11, `lit-l7-…-007` / `lit-l8-…-008`) that four of these
items have **0 hits** in `ledger/theorems.jsonl` and `ledger/citation_audit.csv`, and asks
formulation to state which F1 field each anchor binds.

That zero-hit statement was a lead assertion, not a pinned measurement. This instrument
measures it: a pre-registered predicate per obligation, applied to the frozen L0 ledger,
the frozen L1 citation audit and the literature registry, with anchor-grade separated from
incidental mention. Whatever the numbers, they are now reproducible and falsifiable.

## Result

Measured at `stamp 2026-09-12T01:30:00+08:00`, all pins resolving, two byte-identical runs.

| obligation (F1 field) | L0 hits / anchor | L1 hits / anchor | registry hits / anchor |
|---|---|---|---|
| O1 weighted Sobolev data class (`sources[0]`) | 0 / 0 | 0 / 0 | 0 / 0 |
| O2 MGHD existence+uniqueness (`sources[1]`) | 1 / 0 | 0 / 0 | 0 / 0 |
| O3 positive mass theorem + rigidity (`sources[2]`) | 0 / 0 | 0 / 0 | 0 / 0 |
| O4 predictability definition (`sources[3]`) | 0 / 0 | 0 / 0 | 0 / 0 |
| O5 known status of WCC for generic AF data (`sources[4]`) | 0 / 0 | **1 / 1** | **1 / 1** |
| U1 `s > 5/2`, `delta in (1/2,1)` | 0 / 0 | 0 / 0 | 0 / 0 |
| U2 conformal completion `k >= 3` | 0 / 0 | 0 / 0 | 0 / 0 |
| U3 predictability equivalence | 0 / 0 | 0 / 0 | 0 / 0 |

BL-11 claim tests (the three named items): weighted-Sobolev thresholds L0 0 / L1 0;
positive mass L0 0 / L1 0; predictability equivalence L0 0 / L1 0 — **the zero-hit claim is
confirmed at the pinned bytes** under the published predicates.

### Findings

* **F-048-01 (confirmation).** BL-11's three named unanchored items reproduce 0 hits in
  both frozen literature artifacts. F1's `unresolved_citations` are genuinely unanchored in
  the frozen 95-source universe, not merely unsearched.
* **F-048-02 (new, actionable).** O5 — "known status of weak cosmic censorship for generic
  AF vacuum data", F1 `provenance.sources[4]`, `identifier: null` — **does have an
  anchor-grade evidence hit**: `SRC-001` (Shlapentokh-Rothman 2025 review, DOI
  `10.5802/crmeca.284`, L1 `class_mapping = AF-WCC-VAC-GEN`), whose recorded abstract
  evidence says the conjecture "remains wide open" for generic asymptotically flat data.
  The matching L0 row is `D-001` (`entry_kind: conjecture`, `conclusion_type: open_problem`,
  used_by_theorems `D-001`). So F1's fifth obligation is closable by binding a source it
  already has, or must state why a review is not admissible. That admissibility call is
  F1/A0's, not this instrument's.
* **F-048-03 (scope note).** O2's single L0 hit is `D-008.genericity =
  "Not applicable (existence/uniqueness of the MGHD object)."` — a metadata-grade
  scope disclaimer, **not** an anchor. MGHD existence/uniqueness remains unanchored at
  statement grade.
* **F-048-04 (instrument cross-check).** The positive control `cauchy horizon` returns
  27 L0 rows / 30 L1 rows, reproducing the literature lead's reported 27/30 exactly.

## Method

* `PREREGISTRATION.json` fixes the populations, the eight predicates (derived from the F1
  obligation strings), the grade taxonomy and the controls **before** the run.
* `census_f1_provenance.py` is stdlib-only, read-only and deterministic. Grades:
  `statement` (`statement_exact`) / `subject` (`label`) / `metadata` for L0; `title` /
  `evidence` (`evidence_excerpt`, `elided_quote`) / `metadata` for L1; `title` /
  `evidence` (`verification.evidence`) / `metadata` for the registry. `anchor_grade`
  requires a statement/subject/title/evidence match plus a record identifier (DOI, arXiv
  id or record-shaped locator; `source_ids` for L0).
* Pins: F1 `d9cebb9404b2…`, L0 `a1674f094979…`, L1 `315c19145065…`, registry
  `ea02d1943fda…`, rubric `d748a9e3574e…`, `FORMULATION_ANCHORS.md` `d952d136f880…`.
* Controls (all pass): C0 pins resolve; C1 populations 62/97/97; C2 L0 class tokens within
  the four frozen classes; C3 positive control 27/30; C4 nonsense predicate 0 hits + five
  synthetic fixtures (near-miss negatives not matched); C5 read-only pre/post hash equality.
* Determinism: two runs, same stamp — `report.json` and `census.tsv` byte-identical
  (`evidence/determinism.json`).

## Falsifier

Re-running `census_f1_provenance.py --stamp 2026-09-12T01:30:00+08:00` on byte-identical
pinned inputs falsifies this census if: (i) any pin measures a different sha256; (ii) a
pinned row/citation that a careful reader identifies as an anchor for one of the eight
obligations is missed by the published predicates; (iii) a reported hit is not a hit under
the published regex; or (iv) the two runs differ.

## Authority limits

Worker evidence only: no gate verdict, no node status, no `validation_status=passed`, no
canonical write, no network resolution, no citation-support adjudication. This is a
negative-result measurement, not a mathematics claim. Events await controller ingest.

## File map

| file | role |
|---|---|
| `PREREGISTRATION.json` | predicates + populations + controls, frozen before the run |
| `census_f1_provenance.py` | instrument (stdlib, read-only, deterministic; exit 3 pin drift, 4 control failure) |
| `report.json` | full census, controls, BL-11 tests, falsifier |
| `census.tsv` | per-hit rows with grade, anchor flag, field and quote |
| `evidence/` | run1/run2 stdout, report and census copies, determinism record |
| `inputs_manifest.json` | measured input and output sha256 |
| `SHA256SUMS` | deliverable hashes |
