# W001-COVERAGE-SCAN-01 — review-coverage accounting reconciliation

**Worker:** worker-001 · **Class:** `AF-SCC-C2-VAC-GEN` (cross-checked `AF-WCC-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `GLOBAL`) · **Node:** F2a · **Gate:** G-FORM (cross-checked G-F0, G-LIT, G-AUDIT)
**Snapshot:** 2026-09-12T00:48:41+08:00 (CST), hash-drift clean (`hash_drift: []`)

## Question

The Astra lifecycle's advisory `review_coverage()` scan (`research_map/astra_lifecycle.py:176-214`)
is what fills the coverage sentence in `controller_gate_audit` gate reasons. It reads only
`reviews/*.json` and resolves targets only through `TARGET_ALIASES`. Accepted review events live in
`research_map/events.jsonl`. This audit asks: **do the two views agree at the controller-measured
artifact hashes?**

Answer: **no.** The scan both under-counts live accepts and counts one accept the reviewer
withdrew. Verdict: `DIVERGENCE` (4 gate-critical invisible accepts, 1 withdrawn accept counted).

## Headline measurements (at the pinned snapshot)

| node | scan `distinct_accept_reviewers` | live accepts in accepted stream | divergence |
|---|---|---|---|
| F0 | 5 (…, worker-078) | 6 (adds **worker-087**) | under-count |
| F1 | 1 = **worker-088** | 1 = **worker-061** | identity swap: scan counts a withdrawn accept, misses the live one |
| F2a | **0** | **1 (worker-089)** | under-count; gate reason prints `F2a [0 distinct accept reviewer(s)]` |
| F2b | 1 (worker-098) | 2 (adds **worker-089**) | under-count |
| L1 | 0 | 5 spot-check reviewers | informational: L1 uses the separate `l1_spotchecks()` channel |

Measured hashes at the snapshot: F0 `0abb9ed8a961`, F1 `cce9c60146d6`, F2a `5476a3f2c6bc`,
F2b `55d0a1ea9bda`, L0 `a1674f094979`, L1 `315c19145065`.

## Causes (each reproduced by a control)

1. `review_body_not_in_reviews_dir` — the accept event is in the accepted stream but its review body
   was written under `artifacts/<worker>/…` or not written at all (worker-089 F2a/F2b, worker-061 F1,
   worker-087 F0). The scan never sees it.
2. `target_id_not_resolvable_by_scan` — `target_id: <artifact-path>#<sha256>` does not map through
   `TARGET_ALIASES`, even when the body is in `reviews/` (worker-089's event form).
3. `scan_counts_withdrawn_accept` — `reviews/F1-review-088-rev12.json` (accept) is counted while the
   same reviewer's later `F1-review-088-rev12-amended.json` explicitly withdraws it. The scan does
   not model latest-verdict-per-reviewer supersession.
4. `scoped_verdict_excluded` — correct by design (`counts_as_full_schema_verdict: false`), retained
   as a control so the audit does not over-report.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-001/coverage_scan_audit/audit_coverage_scan.py
# 0 = verdict emitted; 3 = input/review-corpus drift (no verdict); 4 = control failure
```

The harness imports the controller's own scan function (no re-implementation drift), runs seven
seeded controls through the real function against a synthetic `reviews/` root, and voids the
verdict if any input or the review corpus moves during the run.

- `audit_coverage_scan.py` sha256 `92fe0640c2f5cc11123fda51073afcc9d9d361695a4c6bce1e9d3d813d50762c`
- `evidence/report.json` sha256 `9b75f98dc491e5c963b549c084589b8a4781cb3c01389d79d5d9629dd30d93ce`
- Report pins: `events.jsonl` `364fc6ae0d57…`, `artifact_hashes.json` `9f2287b3673c…`,
  `astra_lifecycle.py` `bd14004accd1…`, `reviews/` manifest `235d2827855c…`

## Falsifier

Collapses if, at these measured hashes, every accepted review event is visible in
`review_coverage()` `full_accepts` for the same node+reviewer+hash and no accept is superseded by a
later verdict from the same reviewer — or if `review_coverage()` is changed to union the accepted
event stream and the divergence count drops to zero — or if the measured hashes move (then the
verdict is advisory for the pinned bytes only).

## Proposed repair (controller-owned; not applied by this worker)

1. Union `reviews/*.json` with accepted review events from `research_map/events.jsonl`, keyed by
   node / `class_id` / canonical artifact path.
2. Resolve `<artifact-path>#<sha256>` target ids through the measured path→node registry.
3. Honour `counts_as_full_schema_verdict: false` in the union path.
4. Apply latest-verdict-per-reviewer supersession before computing `distinct_accept_reviewers`.

## Not claimed

No gate verdict, no node status change, no canonical artifact edit, no claim about the mathematical
content of any review. This is a measurement of governance accounting only. The audit lead's
`reviews/A1-rebind-coverage.json` remains the binding coverage adjudication.
