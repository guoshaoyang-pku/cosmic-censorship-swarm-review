# W48-F2A-REV27-REPIN-01 — F2a (AF-SCC-C2-VAC-GEN) independent hash-bound audit

Worker: `worker-048`. Class: `AF-SCC-C2-VAC-GEN`, node `F2a`, gate `G-FORM`.
Under open assignment `astra-life03-verify-gform` (owner `astra-lead-audit`).

Authority: worker verdict / evidence only. **Not** a gate verdict, **not** a node
completion, no `validation_status=passed`. Workers cannot promote.

## Why this snapshot exists

The formulation tree was being rewritten while this worker ran. `FROZEN.json`
went rev27 (00:32:59) → rev28 (00:35:08); `gate_test_report.json` was observed
at 00:33:42 / 00:34:00 / 00:34:47 and `taxonomy_consistency.json` at
00:36:36 / 00:38:07. Every claim below therefore binds to bytes frozen by
`snapshot_inputs.py` at `2026-09-12T00:34:42+08:00` (second pass 00:35:0x), not
to the live paths. A live-manifest re-check (A10) is reported separately.

## Snapshotted inputs (sha256, 12 hex)

| path | sha256 |
|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (F2a canonical) | `5476a3f2c6bc` |
| `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` (mirror) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (sibling control) | `55d0a1ea9bda` |
| `schemas/af_wcc_vacuum.yaml` (context) | `cce9c60146d6` |
| `research_map/formulation_taxonomy.yaml` (canonical F0) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963` |
| `artifacts/formulation/FROZEN.json` (rev27) | `5fa3b3bf95f2` |
| `artifacts/formulation/evidence/gate_test_report.json` | `6def01264a1d` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |

## Verdict: `revise-contested`

* **No current machine blocker.** All rev25/26 blocking defects are cleared at
  F2a `5476a3f2`: 0 duplicate YAML keys, `class_contract_pointer` resolves in the
  canonical F0 tree, `declared_f0_sha256` matches the canonical F0 bytes, the
  exact quantifier prefix has no disjunction, no future-dated timestamp,
  `class_separation` 0 findings, R22 top-level-key scan clean, owner
  `check_class_schema.py` PASS, and the owner gate-test report `6def0126` binds
  `canonical_sha256[AF-SCC-C2-VAC-GEN] = 5476a3f2…` with canonical PASS,
  6/6 null controls, 31/31 mutants caught.
* **Two binding defects existed at the rev27 snapshot** and were repaired by the
  live rev28 within ~2 minutes: rev27 pinned `gate_test_report.json` at
  `2f699be9` while the passing report is `6def0126`; and F2a declared
  `consistency_evidence_sha256 = 675a99d0` while the evidence file read
  `9e335e9b`. Both are recorded as `blocking-superseded-at-audit`; A10 confirms
  live rev28 re-pins every F2a-relevant byte.
* **One contested-policy item stands**: G-FORM's "one frozen data class shared
  by F1/F2a/F2b" criterion is not met. `data_class` is not key-identical across
  F2a/F2b (25 vs 26 keys) nor F2a/F1 (8 value differences), and no
  Sobolev/data-class variant is registered for `AF-SCC-C2-VAC-GEN`. rev12
  reframed `D0` as a tagged disjoint union with per-branch topology, which fixes
  the ill-typed `or` form; whether that satisfies the criterion or needs a
  registered variant is a gate-owner ruling, not a machine error.
* **Advisory**: the frozen F2a `review_status` (`independent_reviewers: []`,
  `pending`) is understated at audit time — two hash-paired revise verdicts at
  `5476a3f2` appeared at 00:37:30 / 00:38:08 (`reviews/F2a-review-034-repin.json`,
  `reviews/F2a-rev12-069.json`). Concurrent workers independently measured the
  same consistency-evidence drift.

## Checks and controls

`report.json` is authoritative: 22 checks (16 pass; A5/A6/B4 superseded at
audit time; A9 live-drift info; B6b contested; B7 advisory) and **7/7 mutation
controls flip as declared** — positive control clean, duplicate-key,
future-date, broken-pointer, corrupted-F0-hash, sibling-class, and
formal-prefix-disjunction injections each detected.

## Falsifier

At the recorded snapshot bytes: (a) any FAIL check that passes on an independent
re-implementation; (b) any PASS check whose recorded value is not the measured
value; (c) any control that does not flip; (d) a FROZEN revision that already
pinned the passing gate report and the snapshot consistency-evidence bytes *at
snapshot time* (not merely later); (e) a `VARIANT_REGISTRY` entry registering a
Sobolev/data-class variant for `AF-SCC-C2-VAC-GEN`. A later write to the live
files is a new revision to re-run against, not a falsifier.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-048/f2a_rev27_repin_audit/snapshot_inputs.py
python3 artifacts/worker-048/f2a_rev27_repin_audit/snapshot_inputs.py \
  --out snapshot_manifest_extra.json --inputs \
  artifacts/formulation/evidence/taxonomy_consistency.json \
  artifacts/formulation/VARIANT_REGISTRY.json \
  artifacts/formulation/tools/check_class_schema.py \
  artifacts/formulation/KEY_MANIFEST.json
python3 artifacts/worker-048/f2a_rev27_repin_audit/audit_f2a_rev27.py --controls
```

Artifacts: `report.json`, `snapshot_inputs.py`, `audit_f2a_rev27.py`,
`snapshot_manifest.json`, `snapshot_manifest_extra.json`, `snapshot/`.
