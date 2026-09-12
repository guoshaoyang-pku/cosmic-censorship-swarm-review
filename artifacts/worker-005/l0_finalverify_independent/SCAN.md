# W005-L0-FINALVERIFY-INDEP-01 — independent verification of the L0 gate-final-verify

* target: `reviews/L0-review-final-verify.json#8f3ddc732983` (event `audit-l09-art-l0-20260912T011904`)
* pins: ledger `a1674f094979`, audit csv `315c19145065`
* verdict: **accept 4.0** — 0 hard failures, 6/6 controls pass
* core_digest: `5025e4f28b8f`

## Checks

* **C1 PASS** — target hash / pin binding / stability
  * target hash, internal pin binding and T0==T1 stability all reproduce
* **C2 PASS** — ledger facts
  * 62 rows / 151521 bytes / 62 unique ids
* **C3 PASS** — HF-14 predicate triple + review axis
  * 0/62 for each of status/validation_status/supports_claim
* **C4 PASS** — coverage_table rows vs durable sources
  * 4/4 coverage rows reproduce against durable sources
* **C5 PASS** — binding-verdict universe / rule sensitivity
  * universe reproduces: 2 full accepts, 2 full revises, 2 flag-absent revises, 2 flag-false scoped verdicts, 2 event-only accepts, 2 stale any-hash accepts
* **C6 PASS** — verdict basis and falsifiers
  * verdict basis, carried objections and declared falsifiers present

## Binding-verdict universe at the pin (R1, file records)

* deepseek-flash-18: revise 3.0 full_schema=None hard_failures=3 (2026-09-12T00:47:40+08:00) — `reviews/L0-review-18-rev3.json`
* worker-005: revise 3.0 full_schema=None hard_failures=1 (2026-09-12T00:51:00+08:00) — `reviews/L0-review-worker-005-rev3.json`
* worker-011: revise 3.0 full_schema=True hard_failures=3 (2026-09-12T00:54:50+08:00) — `reviews/L0-review-011-rev4.json`
* worker-025: revise 3.5 full_schema=False hard_failures=1 (2026-09-12T00:49:30+08:00) — `reviews/L0-hf02-staged-repair-025.json`
* worker-063: inconclusive 2.0 full_schema=False hard_failures=0 (2026-09-12T00:50:48+08:00) — `reviews/w063-l0-scope-adjudication.json`
* worker-075: accept 4.0 full_schema=True hard_failures=0 (2026-09-12T00:49:01+08:00) — `reviews/L0-review-075-rev3.json`
* worker-079: accept 4.0 full_schema=True hard_failures=0 (2026-09-12T01:03:17+08:00) — `reviews/L0-review-worker-079.json`
* worker-093: revise 3.5 full_schema=True hard_failures=2 (2026-09-12T00:37:45+08:00) — `reviews/L0-review-093.json`

  event-only accepts (R2): worker-050, worker-072

## Findings

* **A-W005-L0FV-01** (advisory) — 2 of the 4 accepts in coverage_table (worker-072 4.5, worker-050 4.0) are event-only verdicts: they exist as accepted review events, not as review files in reviews/. They bind the pin through evidence_refs; worker-050's event carries no target_id field at all. The accept basis is unaffected (both are non-author and both backing artifacts hash-match), but the gate record should record the binding class.
* **A-W005-L0FV-02** (advisory) — The G-LIT criteria line counts '5 revise' at the pin, but the verdict count is rule-dependent. R1 (pin-exact review files, n=8): accepts ['worker-075', 'worker-079'], full-schema revises ['worker-011', 'worker-093'], no-full-flag revises ['deepseek-flash-18', 'worker-005'], scoped/no-full-flag verdicts ['worker-025', 'worker-063']. R2 (R1 + L0-target review events at the pin, self/owner excluded) adds event-only accepts ['worker-050', 'worker-072'] and 4 event-only non-accept verdicts ['worker-023:revise', 'worker-037:revise', 'worker-073:revise', 'worker-097:revise']. The decisive 'two full-schema non-author accepts' basis is robust under every rule; any quoted revise/inconclusive count must name its rule.
* **A-W005-L0FV-03** (info) — Two stale any-hash accepts exist on disk and are correctly excluded by the target: worker-006 accept at 3e3d35531421 (older revision) and worker-011 accept at ce42d205 (superseded by that reviewer's own rev4 revise at the pin). A supersession-aware reading is required to reach the target's count.

## Falsifier

Any of: reviews/L0-review-final-verify.json not at 8f3ddc732983; ledger/theorems.jsonl not at a1674f094979 or row/byte counts changed; any HF-14 predicate nonzero; either full accept (worker-075, worker-079) no longer binding, full-schema, non-author, 0-hard-failure; a coverage_table row not reproducing against its durable source; a moved backing-artifact hash; a new full-schema accept at the pin that the universe misses.

Worker-level measurement only: no node status, validation_status or gate verdict is set.
Reproduce: `python3 artifacts/worker-005/l0_finalverify_independent/check_l0_finalverify.py`
