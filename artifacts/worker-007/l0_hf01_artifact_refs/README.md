# L0 HF-01 repair proposal — class-bound `artifact_refs` for theorem rows

**Author:** `deepseek-flash-07` / worker instance `worker-007-20260912T001229-897883`
**Node:** L0 (literature ledger) · **Gate:** G-LIT · **Classes:** all four frozen ids
**Status:** proposal artifact, `validation_status: unverified` — not a node `done`, not a gate verdict
**Canonical ledger is untouched:** `ledger/theorems.jsonl` stays at `ce42d205e761` (this lifecycle read-only)

## 1. The defect this addresses

`reviews/L0-review-17.json` (verdict `revise`, score 2.5) raises **HF-01 critical**: 30 rows of
`ledger/theorems.jsonl` set `conclusion_type: "theorem"` while the ledger has no `artifact_refs`
field at all (25 of them `status: accepted`). The A0 rubric detector is explicit
(`evaluation_rubric.yaml:171-174`):

```
HF-01 fluent_text_promotion:
  claim.conclusion_type == theorem AND (no artifact_refs OR artifact missing OR hash mismatch)
```

So this is not a style issue: under the project's own rule, fluent text must not be promoted to
theorem, and a theorem marker must be backed by a resolvable, hash-pinned artifact.

## 2. What was measured (pinned at generation time)

| file | sha256 (prefix) |
|---|---|
| `ledger/theorems.jsonl` | `ce42d205e761` |
| `ledger/citation_audit.csv` | `315c19145065` |
| `artifacts/literature/registry.jsonl` | `ea02d1943fda` |

* theorem rows: **30** of 62
* theorem rows carrying `artifact_refs` before: **0**
* distinct `source_ids` used by those rows: **56**
* source_ids resolving in `citation_audit.csv`: **56/56** (citation_ids unique, so line locators are stable)
* source_ids resolving in `registry.jsonl`: **56/56**
* theorem rows with non-frozen `class_ids`: **0** (class binding already conforms)
* rows with zero `source_ids`: **0**

## 3. Proposed remedy A — add refs to artifacts outside the amended file

For each theorem row, `proposed_artifact_refs` contains one `citation_record` ref and one
`registry_record` ref per `source_id`, each with:

* `path` + `sha256` of the real on-disk evidence file,
* a **line locator** (`ledger/citation_audit.csv:42`),
* `external_locator` (DOI / arXiv / URL) and the record's `status` / `verdict` / `mirror_of`,
* `supports` — what the ref actually establishes.

Plus a per-row `row_content_sha256`: sha256 over the row with `artifact_refs` excluded, so the
claim-bearing content is pinned **without self-reference**.

**Self-reference was a real design trap and is avoided deliberately.** A ref
`{path: ledger/theorems.jsonl, sha256: <ledger hash>}` stored inside that same ledger can never
verify — writing the ref changes the hash it pins, so HF-01's "hash mismatch" arm would fire
forever. All refs here point outside the amended file; the row digest covers the rest.

## 4. Proposed remedy B (available, not taken)

Rename `conclusion_type` → `mathematical_result_kind`, reserving the claim vocabulary for claim
events. Same effect on the detector and equally honest, but it loses the theorem marker and adds
no provenance. `remedy_B_rename_available: true` is recorded per row; the choice belongs to the
lead, not to this worker.

## 5. How to apply

```bash
# 1. confirm the canonical ledger is still at the pinned hash
sha256sum ledger/theorems.jsonl         # expect ce42d205e7617e3a...

# 2. apply the proposal (lead-owned action; this artifact never writes the canonical path)
cp artifacts/worker-007/l0_hf01_artifact_refs/proposed/theorems.with_artifact_refs.jsonl ledger/theorems.jsonl

# 3. no ref-hash refresh is needed (all refs are outside the amended file)
# 4. record the new hash and request re-review of L0 at the new hash
```

## 6. Controls

`python3 run_hf01_refs.py --selftest` — null plus five mutants, each of which must fire:

| control | expected finding | result |
|---|---|---|
| null (clean proposal) | none | PASS |
| M1 all refs dropped | `hf01_missing_refs` | PASS |
| M2 file ref hash corrupted | `hf01_hash_mismatch` | PASS |
| M3 ref path missing | `hf01_artifact_missing` | PASS |
| M4 non-frozen class token | `hf02_class_leakage` | PASS |
| M5 row content digest corrupted | `hf01_row_digest_mismatch` | PASS |

Independent post-build checks (this lifecycle):

* rebuilding twice gives a byte-identical proposal (`893556c6fb289b6b`) — deterministic;
* the patch adds **only** `artifact_refs`: 30 rows changed, 32 untouched, zero field diffs;
* patched theorem rows missing refs: **0**;
* row digests recomputed from the **patched** rows: **0 mismatches**;
* refs failing an independent on-disk sha256 check: **0**;
* self-referential refs: **0**.

## 7. Falsifiers

* any theorem row left without `artifact_refs` after applying the patch → HF-01 stands;
* any locator that does not resolve to the source record at the pinned sha256 → proposal fails;
* any proposed class binding outside the frozen four → HF-02 fires;
* a `row_content_sha256` that does not recompute from the canonical row → proposal fails;
* a non-deterministic rebuild → proposal fails.

## 8. Explicit non-claims

* this does **not** edit the canonical ledger; `ledger/theorems.jsonl` remained `ce42d205` throughout;
* it does **not** upgrade any `verification_status` — 29/30 theorem rows are still `abstract-read`,
  so `citation_support == 1.0` for the accepted set is **not** established (a separate G-LIT unmet item);
* the refs establish **locator, provenance and verification status** of the cited records; they do not
  assert that the cited work proves the row's statement, and they are not a page-level check;
* it does **not** adjudicate the duplicate/mirror clusters (13 citation rows carry `mirror_of`);
* it is **not** a reviewer verdict, does not move L0 to `done`, and cannot pass G-LIT.

## 9. Files

| file | role |
|---|---|
| `run_hf01_refs.py` | deterministic generator + checker + controls (offline) |
| `l0_hf01_proposal.json` | per-row proposal, summary, falsifier, non-claims |
| `proposed/theorems.with_artifact_refs.jsonl` | machine-applicable patch (proposal only) |
| `verification.json` | machine-readable control + integrity results |
| `selftest.log` | raw control output |
| `*.sha256` | content hashes |
