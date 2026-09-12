# W096-F1-BINDING-RECEIPT-01 — class-bound binding/publication receipt for F1

One bounded class-bound task, one class, one hash: **AF-WCC-VAC-GEN** (`F1`, gate `G-FORM`).
Read-only audit; no schema, map, review, or controller file was edited. This is reviewer input,
not a node completion or gate verdict (workers cannot set `done` / `passed`).

## What was measured

| item | value |
|---|---|
| target | `schemas/af_wcc_vacuum.yaml` (`class_id=AF-WCC-VAC-GEN`, `node_id=F1`, `revision=11`) |
| target sha256 at receipt | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` (33642 B, mtime 00:19:14) |
| canonical F0 taxonomy | `research_map/formulation_taxonomy.yaml#276009f4f63d` (measured) |
| authoring F0 taxonomy | `artifacts/formulation/formulation_taxonomy.yaml#c8e979a1eb48` (divergent) |
| drift during run | none (start = end = `9a8bd4c9…`) |
| canonical checklist (corroboration only) | `artifacts/formulation/tools/check_class_schema.py#000e09e46b2f` exit 0, `verdict=pass`, `failed_rules=[]` |

## Result: 5 binding defects reproduced; 0 semantic checks failed

The canonical structural checklist passes these bytes. The failures are all in
binding/publication integrity, which is why a lexical gate pass must not be read as a
G-FORM receipt:

| id | defect | named by (corpus) | machine evidence |
|---|---|---|---|
| W096-F1-01 | duplicate top-level mapping keys | HF090-02, HF-094-2, C12-duplicate-keys | `revised_at` at lines 8,10,12,14,16,20,23 (6 duplicates); `revised_at_unused` at 26,28 (1 duplicate). PyYAML last-wins. |
| W096-F1-02 | future-dated effective timestamps | HF090-02, HF-094-2, C15-timestamp-sanity | effective `revised_at=2026-09-12T00:30:00+08:00` and `f0_binding.checked_at` same, both **after** mtime 00:19:14 and the review wall clock. |
| W096-F1-04 | `class_contract_pointer` resolves only on the non-authoritative tree | HF090-01, C14-contract-pointer | pointer targets `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN`; that key exists only in the authoring tree (`c8e979a1…`). The authoritative canonical taxonomy (`276009f4…`) has top-level `classes`, not `class_contracts` → the fragment does not resolve on the canonical path. |
| W096-F1-05 | normative statement uses undefined symbols | HF090-03, HF-06 (flash-19) | `conclusion.statement_formal` (line 251) uses `AF_{I+}(M_D)` and `complete(I+_D)`; each occurs exactly once in the whole document, i.e. defined nowhere. |
| W096-F1-06 | quantifier block states a different visibility predicate than the class declares | HF-06 (flash-19) | `quantifiers.formal` (54–55) and `domains.D5` (79–81) use whole-curve single-q containment (`gamma subset J^-(q)`), no `t0`/tail; `visibility.definition` (220) defines the **tail** predicate and explicitly forbids the whole-geodesic reading. Whole-curve single-q is strictly stronger than the declared tail predicate. |

Passing checks: `R1` identity/single class binding, `R4` canonical==authoring F1 bytes,
`R8` declared F0 hash == measured canonical F0 hash, `R10` canonical checklist corroboration.

Not reproduced from the corpus: worker-059's `HF-1` (map `declared_hash_matches_measured`) was
already withdrawn by its author; this receipt finds the map agrees on the measured F1 hash.

## Falsifiers (each finding can be killed independently)

Re-run `python3 run_receipt.py` against `schemas/af_wcc_vacuum.yaml#9a8bd4c96800`:

1. Any `fail` check flipping to pass on byte-identical input falsifies that finding.
2. Controls `N1`/`P1`/`P4` (clean file → no duplicates; synthetic duplicate → detected; the real
   file with the duplicate lines removed → no longer detected) falsify a stuck detector.
3. Controls `P2`/`P3` (existing fragment resolves; missing fragment fails closed) falsify a
   pointer resolver that always answers the same way.
4. A canonical `research_map/formulation_taxonomy.yaml` that resolves
   `#class_contracts.AF-WCC-VAC-GEN`, a duplicate-key-free strict parse, declared timestamps
   `<=` mtime and `<=` wall clock, tail-based `quantifiers.formal`/`D5`, and definitions for
   `AF_{I+}`/`complete(I+_D)` falsify the corresponding revise items.
5. If the target hash moves, every verdict here is advisory and must be re-run against the new
   canonical bytes (the script exits 2 on drift; drift was none in this run).

## Gate receipt (for the controller, not a verdict)

At `9a8bd4c9…` the live review corpus contains **0 accepts** and **2 revises**
(`reviews/F1-review-090.json#46870ff6dc2d`, `reviews/F1-review-lead-audit-r2.json#df6114bc7c80`;
one inconclusive from `deepseek-flash-22`). The repair set implied by this receipt is exactly:
remove the duplicate keys and keep one non-future `revised_at`, define `AF_{I+}` and
`complete(I+_D)` in the document (or rewrite `statement_formal` in already-defined terms), align
`quantifiers.formal`/`D5` to the tail predicate, and repoint `class_contract_pointer` to an
authoritative canonical fragment (or add the `class_contracts` section to the canonical
taxonomy). After a frozen repair revision, two independent accepts are still required.

Risk note: `reviews/*.json` are mutable in place (the lead-audit F1 file changed verdict between
00:22 and 00:25); the ledger rows therefore carry per-file sha256.

## Files

- `run_receipt.py` — deterministic harness (no network; fail-closed on drift; self-tests + controls).
- `report.json` — machine output (pins, per-check evidence, reproduced findings, verdict ledger).
- `README.md` — this summary.
