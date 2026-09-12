# W052-BL8-DETECTOR-SCOPE-01 — independent measurement of literature BL-8

**Worker:** worker-052 (instance worker-052-20260912T004157-968807)
**Node / gate:** A0 (evaluation rubric / detector scope), gates affected: G-AUDIT, G-LIT
**Class scope:** audit-process claim (`GLOBAL`); the measured corpus rows are bound to the
frozen four `AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN / AF-WCC-SCALAR-SPH`
**Verdict:** `BL8_CONFIRMED` — advisory evidence only, no gate verdict, no node status.

## 1. What was asked

`astra-lead-literature` filed BL-8 (`comms/outbox/astra-lead-literature.jsonl` →
`lit-l5-20260912-021`): the A0 hard failure **HF-14 (self_certified_acceptance)** is reported
at corpus level over every `.json/.jsonl` under `artifacts/`, `comms/outbox` and `ledger`, so
it also fires on immutable archives, incoming shards and worker review snapshots. If true,
HF-14 can never reach zero through any legitimate repair of the live corpus, and the finding
is unfalsifiable by repair.

This is a **measurement** of that claim, not an endorsement: an independent re-implementation
of the corpus-selection rule and the HF-14 predicate (`artifacts/audit/audit_lib.py:458-473`,
`artifacts/audit/audit_run.py:57-112`, rubric text `evaluation_rubric.yaml:243-252`), with
pre-registered expectations and controls. **No author code is imported.**

## 2. Pins and reproduction

```bash
cd workdir/ai4math-swarm/artifacts/worker-052/bl8_detector_scope
python3 verify_bl8_scope_052.py        # exit 0 iff every expectation and control holds
```

Inputs are hash-measured at start and re-measured at end (drift ⇒ fail). Headline pins:

| path | sha256 (12) |
|---|---|
| `ledger/theorems.jsonl` | `a1674f094979` |
| `evaluation_rubric.yaml` | `d748a9e3574e` |
| `artifacts/audit/audit_lib.py` | see `report.json:pins` |
| `artifacts/audit/audit_run.py` | see `report.json:pins` |
| `artifacts/audit/reports/audit-20260912T003820.json` | see `report.json:pins` |
| `artifacts/literature/tools/build_literature.py` | see `report.json:pins` |
| `comms/outbox/astra-lead-literature.jsonl` | see `report.json:pins` |
| 10 × `artifacts/literature/theorems/batch-*.jsonl` | see `report.json:pins` |

Artifacts of this task:

| artifact | sha256 (12) |
|---|---|
| `report.json` | `ea424736bf34` |
| `verify_bl8_scope_052.py` | `98df75f65dcc` |
| `logs/harness_stdout.txt` | `56308d78da42` |

## 3. Pre-registered expectations (all pass, exit 0)

| id | expectation | observed |
|---|---|---|
| E1 | every pinned input readable and hash-measured; no drift during the run | 18 pins, 0 problems, drift none |
| E2 | canonical ledger: 0 forbidden-key rows, 0 HF-14 hits, class tokens exactly the frozen four | 62 rows, 0 forbidden, 0 hits, frozen-token check true |
| E3 | live build inputs: 0 forbidden-key rows, 0 HF-14 hits, same record count as canonical | 10 files, 62 rows, 0/0 |
| E4 | the 00:38:20 report's own 8-file measurement reproduces exactly | report 8 files / 346 records; replicated **346** |
| E5 | every live HF-14 hit file is historical (archive / incoming / snapshot / proposed / worker batch) | 11/11 historical; 0 canonical or live |
| E6 | total hits > 0 while canonical+live hits = 0 (repair-unfalsifiability) | **526** historical hits, 0 live |
| E7 | allowlist predicate returns 0 on the live corpus **and** fires on a tampered canonical ledger | both true (C4) |
| E8 | allowlist predicate reports `MISSING_CANONICAL` instead of a silent pass | C6 |
| E9 | controls C0–C7 all behave as pre-registered | 8/8 |

## 4. Measurements

**Live corpus (pinned instant, wall-clock stamped in `report.json`).** Canonical
`ledger/theorems.jsonl` `a1674f094979` carries 62 rows: 0 rows with `status`,
`validation_status` or `supports_claim`, 62 rows with `content_status`, 62 with
`review_status`, 0 HF-14 predicate hits. The 10 live build inputs
(`artifacts/literature/theorems/batch-*.jsonl`, of which `batch-00` is empty) hold the same
62 rows with 0 forbidden keys and 0 HF-14 hits. The rev-3 axis split and the fail-closed
builder therefore hold on the live path.

**HF-14 is not zero anywhere else.** The remaining hits:

| records | classification | file |
|---|---|---|
| 22 | ARCHIVE | `artifacts/literature/archive/batch-01.pre-L2-20260912T000830.jsonl` |
| 60 | ARCHIVE | `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` |
| 12 | INCOMING | `artifacts/literature/incoming/w07-theorems.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-007/claim42_verify/snapshot/theorems.ce42d205e761.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-007/l0_hf01_artifact_refs/proposed/theorems.with_artifact_refs.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-029/live_hf2902/ledger_pre_rev3_snapshot.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-036/classsep_disj_rule/snapshots/theorems.ce42d205e761.jsonl` |
| 12 | WORKER_BATCH | `artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-097/l0_rev3_review/snapshots/theorems.pre-rev3-20260912T003026.jsonl` |
| 60 | HISTORICAL | `artifacts/worker-097/l0_rev4_review/snapshots/theorems.pre-rev3-20260912T003026.jsonl` |

Two independent facts, both measured:

1. **Exact replication of the 00:38:20 audit.** The 8 files named in
   `audit-20260912T003820.json` carry exactly **346** records under my re-implementation —
   the same number the report states. The replication is not approximate.
2. **The count grows with review activity.** Between 00:38:20 and this measurement, three
   *new* snapshot files appeared (`worker-029/live_hf2902`, `worker-036/classsep_disj_rule`,
   `worker-097/l0_rev4_review`) and the count rose from 346 to **526**. These are reviewers
   snapshotting the pre-rev3 ledger in order to do their job. HF-14 therefore punishes
   exactly the behaviour the blind-review protocol requires.

Hence: no legitimate change to the live corpus can zero HF-14. Patching or deleting the
archives was correctly refused — they are the record of what was actually reviewed at
`ce42d205` — so the finding is repair-unfalsifiable while the detector scans history.

## 5. Recommendation (owner: lead-audit, A0)

Run HF-14 over an **allowlist**, not the whole corpus:

1. `ledger/theorems.jsonl` (canonical) plus the live build inputs
   `artifacts/literature/theorems/batch-*.jsonl`;
2. the allowlist itself declared in one hash-pinned manifest, so a renamed or missing
   canonical path is a violation (`MISSING_CANONICAL`), never a silent pass;
3. keep the corpus-wide scan **for information only** — report historical hits as a
   separate advisory count, never as a blocking HF.

Do **not** use a path denylist. Control C7 shows a denylist that drops any path containing
`snapshot` silently passing a canonical file that lives under such a path; the allowlist
still fails closed.

Do **not** edit the archives. Control C3 shows the allowlist ignores the historical copy and
still checks the live path; the record stays intact.

**Scope limit / correction.** BL-8 bundles HF-03 into the same shape. Measured: HF-03's 218
records sit in 15 files, of which **12 are live work products**
(`artifacts/literature/registry.jsonl` 97; `artifacts/literature/sources/batch-*.jsonl` 104)
and 3 are historical. HF-03's live portion is repairable by the already-deferred BL-2
metadata patch, so HF-03 is not structurally unfalsifiable the way HF-14 is. This harness
measures HF-14 only.

## 6. Controls

| id | control | observed |
|---|---|---|
| C0 | sandbox outside the repository tree (synthetic records cannot pollute the standing audit) | `/data3/guoshaoyang/tmp/w052_bl8_sandbox` |
| C1 | self-certified row, no reviewer verdict → fires | 1 hit |
| C2 | same row with `review_verdict` → does not fire | 0 hits |
| C3 | mini tree: hit only in the archive copy; allowlist ignores it, passes | scan 1 archive hit, allowlist `[]` |
| C4 | tampered canonical ledger → both predicates fire | scan 1, allowlist 1 |
| C5 | clean canonical → neither fires (negative control) | 0 / 0 |
| C6 | missing canonical → `MISSING_CANONICAL`, fail closed | reported |
| C7 | denylist silently passes a canonical file under a `snapshots/` path; allowlist fails closed | denylist `[]`, allowlist 1 |

## 7. Falsifier and non-claims

**Falsifier.** Re-run `verify_bl8_scope_052.py` at the pinned inputs: falsified if
`ledger/theorems.jsonl` or any live `batch-*.jsonl` carries an HF-14 forbidden key or
predicate hit; or if any HF-14 hit file classifies as CANONICAL / LIVE_BUILD_INPUT; or if the
8-file replication no longer equals the 00:38:20 report's count; or if the allowlist
predicate fails to fire on the C4 tampered canonical sandbox or silently passes the C6
missing-canonical sandbox.

**Non-claims.** No gate verdict (G-AUDIT/G-LIT remain pending); no node status change; no
mathematical claim; no canonical file was modified. This artifact is advisory evidence for
the A0 owner and the controller.
