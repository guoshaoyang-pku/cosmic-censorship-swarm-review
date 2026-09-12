# W093-HF14-VOCABMIG-01 — HF-14 marker-field migration at ledger rev3

**One-line result.** At the pinned bytes, the HF-14 disagreement between worker-011 (60/62 rows) and worker-029/worker-073 (0/62) is fully explained by a **marker-field rename**: rev3 removed `status`/`supports_claim` and added `author_asserts_supports`. Neither revision contains a single independent reviewer-verdict field or artifact-hash field. Under an alias-closed reading the same 60 `theorem_id`s fire, and the set is exactly worker-011's list.

- task_id: `W093-HF14-VOCABMIG-01` · actor `worker-093` · node `L0` · gate scope `G-LIT`
- classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- overall verdict: **PASS** · checks **30/30** · determinism digest `29f143dbe06cf005…`
- report: `report.json` · instrument: `verify_hf14_vocabmig.py` · protocol: `PREREGISTRATION.md`
- report generated: `2026-09-12T01:06:12+08:00`

## Measurements (all at pinned hashes)

| reading | pre-repair `ce42d205` | rev3 `a1674f09` |
|---|---:|---:|
| `R0` canonical detector verbatim | 60 | 0 |
| `R1` canonical + rubric artifact-hash clause | 60 | 0 |
| `R2` alias-closed (`author_asserts_supports` ⇔ `supports_claim`) | 60 | **60** |
| `R3` alias-closed + hash clause, bare `review_status` is not a verdict | 60 | **60** |

- Canonical module `check_self_certification` (pinned `audit_lib.py`) reproduced exactly: **60 pre / 0 live**.
- Live `R3` firing set = pre-repair `R0` firing set = worker-011's `V-011-L0-01` row list (**60/60 set equality**, `reviews/L0-review-011-rev4.json#f21c5ce978b6`).
- Field census: identity-bearing verdict fields **0/62 in both revisions**; artifact-hash fields **0/62 in both revisions**.
- Migration: `supports_claim` → `author_asserts_supports` on **62/62** rows with truth value preserved **62/62**; `status` → `review_status` on **62/62**; 62/62 `theorem_id`s identical across revisions.
- Value shifts: pre `status=accepted` 50, `supports_claim=true` 60 → live `author_asserts_supports=true` 60, `review_status=not_independently_reviewed` 62, `acceptance_authority` author-prose 62.

**Mechanism, stated precisely:** rev3 did not acquire independent review or artifact hashes; it renamed the two fields the canonical detector reads. The added `review_status` / `acceptance_authority` fields are explicit *declarations that no independent review exists* — honesty annotations, not reviewer verdicts.

## What this does and does not decide

- It **measures** why the canonical detector reads 0 while worker-011 reads 60, and reconciles the two counts.
- It does **not** rule on whether the rename discharges HF-14 (that is the audit lead's scope ruling), does not re-review L0 content, and claims no gate verdict, node status or `validation_status`.
- The strictest reading `R3` is deliberately fail-closed: a bare `review_status` string, affirmative or not, never clears the marker; only an identity-bearing verdict field (`reviewer_verdicts` / `review_verdict` / `reviewed_by`) or a hash clears.

## Pinned inputs

| input | path | sha256 |
|---|---|---|
| live ledger rev3 | `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| pre-repair ledger | `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |
| canonical detector | `artifacts/audit/audit_lib.py` | `ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c` |
| rubric HF-14 text | `evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| worker-011 review compared against | `reviews/L0-review-011-rev4.json` | `f21c5ce978b67958fb92f7942dad7e249fbf4d65f306f4b88a9052968f54cffd` |

Byte-identical copies of the four inputs are in `pinned/`; the instrument re-hashes the live files at run start and run end (drift fails closed).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-093/hf14_vocabmig/verify_hf14_vocabmig.py; echo "EXIT=$?"
```

Exit 0 iff all 30 pinned/check/control/determinism checks pass; `report.json` is rewritten with a fresh measured `finished_at` and the same content digest.

## Falsifier

Re-run at the pinned hashes. FALSIFIED if (a) any pinned input differs; (b) R0 is not 60 pre / 0 live; (c) R2/R3 are not 60 live or their firing set differs from worker-011's 60 ids; (d) any control misses its stated behaviour; (e) row count or `theorem_id` set differs across revisions; (f) the two passes differ in digest. A ledger re-publication voids the result for the new bytes only; re-run and re-pin. A canonical detector-rule edit after these results voids the alias reading, not the field inventory.

## Process notes (disclosed, not hidden)

- **Amendment 1** (`PREREGISTRATION.md`): the first instrument execution failed `CTRL-C3` and `DETERMINISM`. C3's pre-registered row spelled `reviewer_verdict`, which the canonical detector does **not** recognise (it recognises `reviewer_verdicts` / `review_verdict` / `reviewed_by`); the control was kept as written (now labelled `C3-literal`, recording the fail-closed spelling behaviour) and `C3-canonical` was added. `DETERMINISM` compared differently shaped structures, a harness bug. The ladder, its expectations, and all other controls are unchanged.
- **Clock discipline (CF-14):** the first draft of Amendment 1 carried a stamp 33 s ahead of the write time; it was corrected to the measured clock before the final report. No content timestamp in the shipped artifacts is ahead of its file mtime.
