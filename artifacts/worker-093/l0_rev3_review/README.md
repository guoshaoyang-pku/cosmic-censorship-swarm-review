# W093-L0-REV3-VERDICT-01 — independent L0 review at `ledger/theorems.jsonl#a1674f094979`

`worker-093`, bounded lifecycle, read-only. **No canonical file was edited.** This is a
full-scope, control-backed verdict on the ledger revision that is on disk at review time,
not on the superseded revision the two newest prior verdicts bind.

## Question

At the measured ledger revision, do the A0 rubric hard-failure detectors fire, and is the
accept/revise split on L0 explained by a validator gap rather than by reviewer
disagreement about the bytes?

## Why the pinned revision is `a1674f09`, not `3e3d3553`

The ledger moved twice inside the audit window: `ce42d205` (rev 2) → `3e3d35531421`
(00:30:49) → `a1674f094979` (00:35:19, worker-023 measured the same transition and read it
as a review-status field rename). The two verdicts at `3e3d3553` (worker-006 accept,
deepseek-flash-17 revise) are therefore already void at the current bytes; the audit lead
filed the same observation at 00:36:53. This review binds the bytes it measured:
`a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`.

## Pinned snapshot (pre == post; no input moved during the scan)

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `evaluation_rubric.yaml` (detector authority) | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `ledger/citation_audit.csv` (L1 evidence) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/audit/audit_lib.py` (canonical validator impl) | `ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c` |
| `artifacts/audit/audit_run.py` (canonical validator) | `3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411` |
| `research_map/class_separation.py` | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| `research_map/research_map.json` | `3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005` |

## Results (machine output: `report.json`)

| check | result |
|---|---|
| HF-14 triple predicate (status∈{accepted,passed} ∨ supports_claim=true ∨ validation_status=passed, no reviewer-verdict field) | **0 rows** — the map's requested first check passes; canonical `audit_lib.check_self_certification` also 0 |
| HF-02 rubric-literal disjunction (≥2 frozen class ids in one `class_ids` list) | **8 rows**: D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528 |
| HF-02 canonical-validator coverage of that branch | **not implemented**: ledger rows are routed to `corpus["records"]` (`audit_run.py:244,255`), and `check_class_binding` reads the singular `claim.get("class_id")`; `class_ids` lists are never checked for disjunction. This is the machine-checkable cause of the accept/revise split |
| HF-02 unknown class token | 0 rows |
| HF-01 literal (record reading: `conclusion_type == theorem` and no `artifact_refs`) | **30 rows**; `artifact_refs` key appears on 0 rows. The author reads HF-01 as claim-scoped — the applicability dispute is reported, not silently resolved |
| class-binding metric (singular-class rows / class-bound rows; target 1.0) | **26/34 = 0.7647** |
| HF-03 citation linkage vs `citation_audit.csv` | 92/92 cited sources have audit rows, 0 non-verified verdicts, 97 class-mapping comparisons, 0 mismatches (non-vacuous) |
| HF-07 duplication (shingle Jaccard ≥ 0.60) | 0 pairs; duplication metric 0.0457 (rubric target ≤ 0.25) |
| verification vocabulary | 0 out-of-vocabulary; 61 abstract-read + 1 unverified |
| controls / determinism | 5/5 planted controls pass (disjunction, self-certification, reviewed-accept silent, unknown token, clean); two runs produce the same digest |

## Verdict

`revise`, score 3.5, hard failures `[HF-02, HF-01]` — see
`reviews/L0-review-093.json#33b2afd81d6e`. Two critical detectors fire under the A0
rubric's literal text; the canonical validator disagrees with its own rubric on HF-02.
This is a defect in the rubric/validator pair, not (only) in the ledger: one of the three
must change so they agree —

1. implement the branch (patch proposal below), or
2. amend the rubric to exempt record-shaped corpora and document the blind spot, or
3. move multi-class coverage annotations to the schema's existing `informs_classes` field.

For HF-01 the same choice applies; worker-007's proposal (add `artifact_refs` to the 30
theorem rows) is a fourth path and is not yet in the canonical bytes.

## Patch proposal (proposal only — canonical file untouched)

`proposed_hf02_disjunction_patch.diff` adds `check_ledger_class_disjunction(records,
classes)` to `artifacts/audit/audit_lib.py`. Verified by loading the patched copy:
import OK, flags exactly the 8 corpus rows, planted 2-class control fires 1.
`patched_audit_lib.py` is the post-patch bytes; the diff applies additively (no call site
changed, so integration is one line in `audit_run.py`).

## Overlap with concurrent work

`artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json#0f86158c5bb7` and
`hf02-verify-023.json#4f4f6e10dcda` independently adjudicate the same 8-row set at the
same hash. Membership agrees. The difference is the consequence: worker-023 reads the
rows as coverage annotations; this review holds that the rubric-literal detector still
fires until the rubric or the validator is changed, which is exactly the gap the patch
addresses.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-093/l0_rev3_review/review_l0_rev3.py --selftest-only   # 5/5 controls
python3 artifacts/worker-093/l0_rev3_review/review_l0_rev3.py                   # writes report.json + reviews/L0-review-093.json
```

Exit 0 = scan + controls + determinism pass; 2 = an input moved mid-scan (verdict
withheld); 3 = control failure.

## Falsifier

Re-run at the same pinned ledger sha256. The review is falsified if (a) any
`findings.hf02_disjunction` row carries fewer than two distinct frozen class ids, or a
row with ≥2 is missing; (b) any `findings.hf14_self_certification` row fails the three
predicates or carries a reviewer-verdict field; (c) a control does not reproduce its
expected value; (d) two runs differ in determinism digest; (e) the canonical validator is
shown to flag a `class_ids` disjunction, which would falsify the reported validator gap;
(f) the ledger hash differs from the pinned hash (then the verdict is void, not wrong).

## Scope limits

- No source is re-fetched; citation resolution is cross-checked against L1's
  `citation_audit.csv`, and the ledger's 0/97 source scope metadata remains L1's blind
  spot (a non-vacuum source bound to a vacuum class is not machine-detectable here).
- No page-level re-reading of quoted theorems; that is L1's evidence surface.
- Worker authority: this cannot set `status=done`, `validation_status=passed`, or a gate
  verdict. The audit lead and controller adjudicate.
