# W48-GATE-COVERAGE-INTEGRITY-01 — independent audit of the controller gate-coverage counts

**Worker:** worker-048 · **node:** F1 (class-bound task, class `AF-WCC-VAC-GEN`) ·
**gate under audit:** G-FORM (plus G-F0 / G-LIT as cross-checks) ·
**role:** bounded execution worker, independent measurement only.

**Verdict:** the controller's `review_coverage()` arithmetic is *reproducible* but
**under-counts and mis-attributes** at the pass-05 snapshot. It scans only `reviews/*.json`,
has no supersession filter, and reads a narrower identity/target vocabulary than the review
records actually use. Corrected at the pinned snapshot: **F1 1 → 1 but the person changes
(recorded `worker-088` was retracted by the same reviewer's own later revise; the surviving
accept is `worker-061`, invisible to the scan), F2a 0 → 1, F2b 1 → 2, L0 0 → 1, F0 5 → 7.**
This is coverage arithmetic, not a gate verdict and not a schema-content review.

## Pinned inputs (re-measured before and after the run; no census-relevant drift)

| input | sha256 |
|---|---|
| audited lifecycle snapshot `runtime/state/controller_verification/lifecycle_20260912-004919.json` | `c743bcf6116fce4d…` (file copied byte-identical into this directory) |
| `research_map/astra_lifecycle.py` (rule under audit) | recorded in `report.json#snapshot.measured_canonical_hashes` |
| `research_map/research_map.json` (live, for drift only) | recorded in `report.json#snapshot.map_sha256` |
| canonical F0 / F1 / F2a / F2b / L0 anchors | from the snapshot's own `measured_hashes` |

The snapshot pins rev12: F1 `cce9c60146d6`, F2a `5476a3f2c6bc`, F2b `55d0a1ea9bda`,
F0 `0abb9ed8a961`, L0 `a1674f094979`. At audit time the F1/F2a/F2b **live** schemas had
already moved (`d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`, i.e. the pass-05 evidence-binding
repair landed); the audit therefore binds to the snapshot's recorded anchors, and the corrected
census describes the rev12 coverage state the controller last audited.

## What was measured

Rule variants (`report.json#per_node.<node>.variants`):

- **A** — exact controller replica: `reviews/*.json`, alias targets only, `reviewer|actor`,
  distinct accepts with `counts_as_full_schema_verdict != false`.
- **B** — A + first-party review records under `artifacts/**` (path contains `review`,
  snapshot/mirror/tmp/sandbox/events copies excluded).
- **C** — B + canonical-path targets (`schemas/…`, `ledger/…`).
- **D** — C + hash-only attribution when a record names no target but pins exactly one anchor.
  D is the corrected census.

Supersession: within one `(reviewer, node)`, a later hash-bound `revise|reject` retracts an
earlier `accept` (ordering by `created_at`, else mtime).

### Corrected census at the pinned snapshot

| node | recorded | corrected | corrected reviewers | criterion (≥2 accepts) |
|---|---|---|---|---|
| F0 | 5 | 7 | 18, 19, 025, 038, 041, 052, 078 | met |
| **F1** | 1 (`worker-088`) | **1 (`worker-061`)** | identity changed; 088 retracted | **not met** |
| F2a | 0 | 1 | worker-089 | not met |
| F2b | 1 | 2 | worker-089, worker-098 | met at rev12 |
| L0 | 0 | 1 | worker-075 | not met |

The headline item is F1: `reviews/F1-review-088-rev12.json` (accept, 00:37:25) is retracted by
`reviews/F1-review-088-rev12-amended.json` (revise, 00:38:49, same reviewer, same hash,
`counts_as_full_schema_verdict: true`). The controller reason at the snapshot still lists
`worker-088` as F1's one accept. The surviving F1 accept, `artifacts/worker-061/f1_rev12_gate/REVIEW.json`,
is hash-bound (`reviewed_sha256 = cce9c60146d6…`) but uses `worker` / `node_id` keys, so the
controller rule cannot see it. Net count is unchanged (1), but the evidence identity is not.

## Controls (9/9 pass, `report.json#controls`)

Synthetic corpus, each rule exercised and asserted: clean 2-accept pair; same-reviewer
retraction; unbound accept not counted; scoped accept not counted; artifacts-only accept
invisible to A and visible to B; snapshot/mirror copy excluded; path-targeted accept invisible
to B and visible to C; author-identity accept measured and separable; hash-only accept
attributed in D.

Controller self-replication (`report.json#controller_self_replication`): variant A's raw accept
set equals the snapshot's own `review_coverage.distinct_accept_reviewers` exactly for
F1/F2a/F2b (corpora unchanged); F0 and L0 differ only by verdicts published *after* the
snapshot (worker-041/052 accepts; worker-075 accept), which are listed as such.

## Falsifier

At the sha256 pins in `report.json#snapshot` and the per-record hashes in
`snapshot_manifest.json#corpus_record_sha256`: (a) any accept marked retracted for which no
later hash-bound revise/reject by the same reviewer exists; (b) any corrected count an
independent implementation of the published rules does not reproduce; (c) any counted file
that is a snapshot/mirror copy rather than a first-party verdict; (d) any control that does
not classify as declared. A later write to the live corpus is a new revision to re-run
against, not a falsifier of this snapshot.

## Reproduce

```bash
cd <repo>
python3 artifacts/worker-048/gate_coverage_integrity/audit_gate_coverage.py \
  --root . \
  --out-dir artifacts/worker-048/gate_coverage_integrity \
  --snapshot artifacts/worker-048/gate_coverage_integrity/audited_snapshot_lifecycle_20260912-004919.json
# exit 0 = controls pass, no census drift; 2 = control failure; 3 = census file drifted
```

## Limits / not claimed

- No gate verdict, no node status, no `validation_status=passed`, no schema-content review.
- The rev12 anchors are now superseded by the pass-05 repair; the actionable recommendation is
  to run this instrument against the FROZEN rev29 pins before the r3 reviewers' accepts are
  counted, with the supersession filter and artifacts-side scan enabled (variants C/D).
- Reviewer labels are treated as identities; alias pairs (`deepseek-flash-15` vs `flash-15`)
  are not merged here. `?` (no reviewer/actor/worker key) is reported separately and is never
  counted as an independent person.
- The extended variants are a *declared* rule extension, not the controller's current rule;
  each counted file is listed in `report.json` so a reader can reject any individual record.
