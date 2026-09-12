# W096-F2A-BINDING-RECEIPT-01 — independent hash-bound receipt (two snapshots)

**Class:** `AF-SCC-C2-VAC-GEN` · **Node:** F2a · **Gate:** G-FORM · **Worker:** worker-096
**Harness:** `run_receipt.py` (generic, read-only, self-tested, drift fail-closed exit 2)
**Verdict: revise at both snapshots** — reviewer input only; no node/gate transition (`comms/PROTOCOL.md:46`).

| snapshot | target sha256 | rev | report | verdict |
|---|---|---|---|---|
| before repair | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` | 11 | `report.json` @ `0b64fc41f40d` | revise: 2 blocking + 1 critical + 2 hard |
| after repair | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` | 12 | `report_rev12_5476a3f2.json` @ `f6395c22b76b` | revise: 2 hard (B11, B12) |

Reproduce a snapshot: `python3 artifacts/worker-096/f2a_binding_receipt/run_receipt.py [--out <path>]`.
The target was re-hashed before and after every run; both runs closed with `drift=false`.

## Before repair (rev11) — defects reproduced

| id | sev | finding | falsifier |
|---|---|---|---|
| B02 | blocking | `revised_at` appears **8×** (lines 8,10,12,14,16,18,21,23); PyYAML last-wins keeps 00:30:00. Prior F-086-3/F-088-1 also claim `revised_at_unused` **twice** in F2a — **not reproducible** (once, line 26). | strict duplicate-key parse exiting 0 |
| B03 | blocking | `revised_at`/`f0_binding.checked_at` = 00:30:00 postdate the write they describe (mtime 00:19:14); the "ahead of wall clock" part is time-dependent and no longer held after 00:30. | declared stamps ≤ mtime |
| B04 | hard | `class_contract_pointer` resolved only on the **authoring** tree; canonical `research_map/formulation_taxonomy.yaml` (`276009f4f63d`) has `classes`, not `class_contracts`. | canonical taxonomy exposing the fragment |
| B06 | critical | `(s,delta)` binder ranged over disjunctive `D0` (Sobolev pair **or** smooth-with-decay); the smooth branch gave no pair and a Fréchet topology with no ambient set. | defined branch ambient set + well-typed binder |
| B11 | hard | `review_status.independent_reviewers: []`, `verdict: pending`, while 6 reviews bind that hash (4 revise, 1 accept, 1 inconclusive). | review_status matching the ledger |

Superseded at rev11 (not defects there): `F2a-review-18` HF-A1/HF-A2 (dangling `extension_predicate`, `D_gen`) — predicate defined at line 91, `statement_formal` uses `proper_future_extension_in_class`. Canonical checker at rev11: **PASS** (exit 0, `failed_rules=[]`), superseding `F2a-review-18` HF-A4.

## After repair (rev12 @ 5476a3f2) — repairs verified, one regression found

- **Closed by measurement:** B02 (single `revised_at`), B03 (declared 00:31:41 ≤ mtime 00:32:02), B04 (pointer re-pointed to `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN`, resolves), B06 (D0 is a tagged disjoint union with per-branch ambient space; the `(s,delta)` pair binder is gone), B07 order/defined-symbol check passes, classsep clean 0 findings.
- **B12 hard regression:** canonical `check_class_schema.py` @ `000e09e46b2f` now **FAILS (exit 1, R22)**: unknown keys `['at', 'class_contract_supplement_pointer', 'consistency_evidence_sha256', 'index', 'notes', 'revision_history']` (move under `extensions:` or add to `KEY_MANIFEST`). At rev11 the same checker passed. Falsifier: a checker run at this hash returning pass/`failed_rules=[]`.
- **B11 still open:** `review_status` is unchanged (empty reviewers, verdict pending) at rev12.
- **B09 advisory (unchanged):** F1/F2a/F2b load-bearing data-class leaves are byte-identical on `s`, `delta`, `default`; `spaces` differs only by F1's annotation `(weighted Sobolev)` (normalized-identical). The G-FORM unmet reason "no single frozen data class is shared" is **not reproduced on the regularity axis at these hashes**; adjudication belongs to the audit lead.
- **B10 advisory (unchanged):** C2's distinctive signature tokens (`H^4`, `1/2+eps`, `s = 4`) appear nowhere in the frozen C2 schema (corroborates lead-audit-r2 MAJOR).

## Controls

Self-tests N1/P1–P5 all PASS at both snapshots (strict-duplicate specificity/sensitivity, pointer positive/negative, comparator, timestamp predicates). Verdict ledger, per-file review sha256, command lines, tool hashes and every check's falsifier are in the two report JSONs. `classsep_regression.py` @ `9f1cf9c336be`: leaks 17/17, controls 10/10, FP 0, FN 0.

## Not claimed

No mathematical re-adjudication; no independence from prior reviewers (D0 typing, pointer and duplicate-key defects are correlated with 086/088/047/lead-audit-r2 and named in `report.json.named_by_prior_work`). Two independent corrections are contributed: the non-reproducible `revised_at_unused` sub-claim (B02) and the non-reproducible "no shared data class" gate reason (B09), plus the rev12 R22 regression. A later revision voids the binding, not the measurement.
