# worker-006 submission — independent L0 review (bounded run)

**Task taken (one class-bound task).** With the L1 spot-check requirement already over-satisfied
(19 recorded spot checks) and F1/F2 schemas under review by peers, the uncovered high-value slot was
**L0**: `research_map.json` gate audit showed *0 distinct accepts* at the current ledger hash and
G-LIT was the only gate with no accept evidence. Node **L0**, gate **G-LIT**, classes
`AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH`.

**Status.** Review delivered: **revise**, score 2.5, one critical hard failure (HF-14). No node
completion, no theorem, no gate verdict; worker cannot set `done`/`passed`.

## Binding

| artifact | sha256 |
|---|---|
| `ledger/theorems.jsonl` (reviewed) | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |
| `ledger/citation_audit.csv` (companion) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |

Both hashes were re-measured after the run; no drift.

## Result

19 reproducible checks (`checks.json`, runner `review_l0_006.py`) over 62 rows.

**Hard failure — HF-14 `self_certified_acceptance` (critical).** 60/62 rows set `status=accepted`
(50) or `supports_claim=true` (60, overlap 50) and the frozen row schema has no
reviewer / verdict / artifact-hash key, so the requirement is structurally unsatisfiable. The frozen
detector (`evaluation_rubric.yaml`, HF-14) is explicitly ledger-inclusive — *"a ledger or claim
record ... with no independent reviewer verdict field and no artifact hash"* — and the rubric states
a critical HF cannot be accepted regardless of other merits.

**Soft findings.** HF-01 (30 theorem rows without artifact binding) reported but not counted, since
its detector is claim-scoped and the ledger-scope question is under controller adjudication;
13 accepted rows keep an acceptance-qualifying item in `unresolved[]`; 3 rows do not echo
citation-registry metadata corrections (T-103/T-505/T-510, none load-bearing).

**Checks that pass** (the dimensions repaired in this revision): 62 rows ≥ 15; unique ids; every
required field present; every `class_ids` token frozen-four and every non-class token in
`ledger_tags`; verification vocabulary legal with 0 rows claiming more than abstract-level
evidence; reciprocal source linkage both directions; conclusion-inflation controls on all strong
rows; lexical grounding ≥ 0.174 on every strong row.

## Adjudication note (recorded, not hidden)

A first pass of this review checked only ledger-discipline dimensions and returned **accept**. The
00:24:40 controller lifecycle live-scanned that file (worker-006 briefly listed as an L0 accept).
Sibling reviews `L0-review-21.json` / `L0-review-22.json` flagged HF-14 at the same hash;
re-reading the frozen detector text, the ledger-inclusive reading is the plain one. The review file
was corrected to **revise at 00:25:25, before any event was emitted** — the accept version was never
published to the outbox. The next lifecycle re-scan (`checked_at` still `00:24:40` at exit) should
drop worker-006 from the L0 accepts; no gate verdict was ever falsely set.

## Artifacts

| artifact | role |
|---|---|
| `reviews/L0-review-worker-006.json` | the review the controller scans (verdict revise, pinned) |
| `artifacts/worker-006/l0_review/checks.json` | 19 checks, per-check evidence, pins |
| `artifacts/worker-006/l0_review/review_l0_006.py` | fail-closed runner (aborts on hash drift) |
| `artifacts/worker-006/l0_review/make_review.py` | composer + controller-scan self-test |
| `artifacts/worker-006/l0_review/emit_l0_events.py` | event emitter (controller validator + dry-run) |
| `artifacts/worker-006/l0_review/review_selfcheck.json` | proof the scan counts the review |

Events emitted to `comms/outbox/worker-006.jsonl` (4; dry-run ingest 4 accepted / 0 rejected):
`w006-20260912T0025-l0-artifact-review`, `-artifact-checks`, `-review`, `-status`.

Checkpoint: `runtime/state/w006_checkpoint_6.json` (+ `w006_checkpoints.jsonl`), worker-local by
design — the shared `current_checkpoint.json` / `artifact_hashes.json` are written by the live
controller lifecycle every few minutes and a worker-side `checkpoint.py` run would race it.

## Next falsifier

A controller adjudication that HF-14 is claim-scoped only, or a new L0 revision that pins the
meaning of `status`, adds row-level reviewer/artifact provenance, and re-passes these checks at its
own hash.

---

## Addendum — revision 2 (final state, 00:33)

The literature lead republished `ledger/theorems.jsonl` at **00:30:49** while this run was
finishing. New revision hash `3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6`
(the citation audit is unchanged at `315c19145065…`). The revision is an HF-14 repair: every row
now declares `review_status: not_independently_reviewed`, `acceptance_authority: astra-lead-
literature (author self-assessment, not a reviewer verdict)`, `status: included_unreviewed`
(50) / `provisional` (11) / `rejected` (1), and `supports_claim` is never true.

**Re-review at the new hash: verdict `accept`, score 4.0, 0 hard failures, 21 checks pass.**
Soft findings unchanged: HF-01 scope (30 theorem rows without artifact binding — detector
claim-scoped, under adjudication) and the 3-row citation-correction echo gap (T-103/T-505/T-510).

History is preserved, not overwritten:

| file | binds | verdict |
|---|---|---|
| `reviews/L0-review-worker-006-superseded-ce42d205.json` | ledger `ce42d205…` | revise (HF-14, since repaired) |
| `reviews/L0-review-worker-006.json` | ledger `3e3d3553…` | **accept** |

Events: batch `w006-20260912T0025-l0-*` binds the superseded hash; batch
`w006-20260912T0033-l0-rev3-*` binds the current one. Checkpoint:
`runtime/state/w006_checkpoint_7.json`. The superseded revision itself was overwritten in place
at the canonical path, so only its hash and the review survive — noted as an observation, not a
blocker.
