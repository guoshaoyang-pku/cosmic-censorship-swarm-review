# W093-HF14-VOCABMIG-01 — pre-registration

- task_id: `W093-HF14-VOCABMIG-01`
- actor: `worker-093` (slot self-selected; no inbox card exists for worker-093)
- node: `L0`; gate scope: `G-LIT`; classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
- recorded_at (measured, this write is not earlier): `2026-09-12T01:03:42+08:00`
- status: **pre-registered before the ladder was run**; no reading below was measured before this file was written (prior reconnaissance read field inventories and the canonical predicate only, to define the readings; the row counts of the ladder were not computed).

## Question

`ledger/theorems.jsonl` rev3 (`a1674f094979`, 62 rows) is reported by two reviewers as having opposite HF-14 states at the same bytes:

- worker-029 and worker-073: canonical HF-14 detector fires **0** rows ("HF-14 closed").
- worker-011 (`V-011-L0-01`, reviews/L0-review-011-rev4.json): **60 of 62** rows set a truthy support assertion with no independent reviewer verdict field and no artifact hash; "HF-14's own detector text names ledger records."

This artifact measures the *mechanism* of the disagreement. It does not issue a review verdict, does not rule on HF-14 scope, and does not touch any canonical file.

## Frozen inputs

| input | path | sha256 |
|---|---|---|
| live ledger rev3 | `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| pre-repair ledger | `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |
| canonical HF-14 implementation | `artifacts/audit/audit_lib.py` (`check_self_certification`, lines 459-473) | `ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c` |
| rubric HF-14 text | `evaluation_rubric.yaml` (lines 243-252) | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |

Byte-identical copies of all four are snapshotted under `pinned/`. Live inputs are re-hashed at run start and run end; any drift **voids** the run for the new bytes (fails closed, exit non-zero).

Canonical detector semantics (verbatim from the pinned module): a row is `accepted` if `status` in {accepted, passed} **or** `validation_status == "passed"` **or** `supports_claim is True`; it `has_review` if any of `reviewer_verdicts`, `review_verdict`, `reviewed_by` is truthy; HF-14 fires when `accepted and not has_review`. The implementation has **no artifact-hash clause**.

Rubric HF-14 text (verbatim): "a ledger or claim record sets status=accepted / validation_status=passed / supports_claim=true with no independent reviewer verdict field **and no artifact hash**; an author's own selftest is not a reviewer verdict".

## Observed field migration (inventory only; counts are measured by the ladder)

Pre-repair rows carry `status` and `supports_claim`; rev3 rows carry neither. Rev3 adds `author_asserts_supports` (truthy on 60) and `review_status` (`not_independently_reviewed` on 62) and `acceptance_authority` (author-self-assessment prose on 62).

## Pre-registered reading ladder

Each reading is applied to both revisions. Row lists and counts are reported per reading.

| id | acceptance marker | review clearance | hash clearance |
|---|---|---|---|
| `R0` | canonical verbatim: `status`/`validation_status`/`supports_claim` | canonical `has_review` | none (matches implementation) |
| `R1` | canonical verbatim | canonical `has_review` | required (adds rubric-literal hash clause) |
| `R2` | R0 + alias `author_asserts_supports is True` ⇔ `supports_claim is True` | canonical `has_review` | none |
| `R3` | R2 markers | canonical `has_review`; a bare `review_status` string is **not** a verdict (fail-closed) | required |

`R3` is the strictest semantically faithful reading: same acceptance semantics under the rename, rubric hash clause included, and no credit for status strings or author prose. A reading "fires" on a row when the marker holds and neither clearance holds.

## Controls (planted rows, run through the same predicate as the corpus)

- `C1` canonical marker only (`supports_claim=true`) → fires R0-R3.
- `C2` alias marker only (`author_asserts_supports=true`) → fires R2, R3; does **not** fire R0, R1.
- `C3` alias marker + `reviewer_verdict` + `artifact_sha256` → clears R1-R3.
- `C3-canonical` as `C3` but with the canonical spelling `review_verdict` → clears R1-R3.
- `C4` alias marker + `review_status="not_independently_reviewed"` → still fires R2, R3 (status string is not a verdict).
- `C5` alias marker + `review_status="independently_reviewed"` but no verdict field and no hash → still fires R3 (fail-closed; a bare status is not an identity-bearing verdict).
- `C6` honest negative (`author_asserts_supports=false`) → fires no reading.
- `C7` pre-repair marker (`status="accepted"`) → fires R0-R3 on the pre-repair corpus path.
- `C8` determinism: two full passes over identical bytes produce one digest.

### Amendment 1 (recorded 2026-09-12T01:05:45+08:00, after the first instrument execution)

Clock note (CF-14): the first draft of this amendment carried a stamp of 01:06:30, ahead of the write time; it was corrected to the measured clock (01:05:58) before the final report was generated. The amendment was authored after the first failing execution and before the passing re-run.

The first instrument execution failed exactly two harness checks, `CTRL-C3` and `DETERMINISM`. Cause, disclosed rather than silently fixed:

- The pre-registered `C3` row spelled the verdict field `reviewer_verdict`. The canonical detector recognises only `reviewer_verdicts`, `review_verdict`, `reviewed_by`; `reviewer_verdict` is **not** recognised, so the intended "recognised verdict clears the finding" control actually measured the detector's fail-closed treatment of an unrecognised spelling. `C3` is therefore kept **as originally written** and its expectation corrected to "fires R2, clears R3" (alias marker plus hash), and a new `C3-canonical` with the canonical spelling is added, expected to clear R1-R3.
- `DETERMINISM` compared two differently shaped JSON structures, a harness bug; it now compares two identical ladder passes.

The reading ladder itself, its expectations, and every other control are unchanged. Ladder values were produced by the first (failing) execution; the amendment changes only control spellings and the digest shape.

## Pre-registered expectations (stated before running)

- `R0`: pre-repair fires 60 rows; live fires 0 rows (reproduces both reviewers' canonical counts).
- `R2`/`R3`: pre-repair fires 60; live fires 60, and the live firing `theorem_id` set equals the pre-repair firing set and equals worker-011's listed 60 ids.
- Hash fields and identity-bearing verdict fields: 0 rows in both revisions.
- Total rows 62 in both revisions, identical `theorem_id` sets.

## Falsifier

Re-run `verify_hf14_vocabmig.py` at the pinned hashes. This measurement is FALSIFIED if (a) any pinned input hash differs; (b) R0 does not reproduce 60 pre / 0 live; (c) R2/R3 do not reproduce 60 live or the firing set differs from worker-011's listed ids; (d) any control C1-C7 does not reproduce its stated behaviour; (e) the two revisions differ in row count or `theorem_id` set; (f) two runs produce different digests. A ledger re-publication voids the result for the new bytes only; re-run and re-pin. A canonical detector-rule edit after these results voids the alias reading, not the field inventory.

## Scope limits

This artifact measures field vocabularies, marker migration and predicate readings. It does **not** adjudicate whether the rename discharges HF-14 (audit-lead scope ruling), does not classify the ledger's honesty annotations as sufficient or insufficient, does not re-review L0 content, and claims no gate verdict, node status, or `validation_status=passed`.
