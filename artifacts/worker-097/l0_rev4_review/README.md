# W097-L0-REV4-INDEP-REVIEW-01 — independent hash-pinned L0 review at rev 4

- **Reviewer:** `worker-097` (recycled slot; no L0 artifact authored — not the ledger, the
  repair tool, the rev-4 builder, or any L0 adjudication).
- **Target:** `ledger/theorems.jsonl` @ `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
  (rev 4, live canonical head; controller measured the same hash at 00:36:03).
- **Gate / class:** `G-LIT` / L0 (`AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`).
- **Verdict:** **revise — score 1.75** (1 critical, 3 major, 3 minor findings).
  This is a worker verdict, **not** a gate verdict; it sets no node status and promotes nothing.
- **Machine report:** `report.json` (sha256 `86b6e86a4dff…`), 21 checks + 12 controls, all controls PASS.

## Revision chain measured (not taken from the map)

| rev | bytes | sha256 | what changed |
|---|---|---|---|
| archive | pre-rev3 | `ce42d205e761…` | last revision with 9 binding reviewer verdicts (now void) |
| rev 3 | — | `3e3d35531421…` | HF-14 closed by **claim lowering**: 50× `status accepted→included_unreviewed`, 60× `supports_claim true→null`, 62× `review_status=not_independently_reviewed` |
| rev 4 | 151521 B | `a1674f094979…` | **axis split** (`build_literature.py`): `status`/`supports_claim`/`status_note`/`supports_claim_basis` removed; `content_status` (50 verified / 11 provisional / 1 rejected) + `author_asserts_supports` (60 true / 2 false) added |

Independently re-derived: all 62 `theorem_id`s persist across all three revisions, and
**0 non-axis keys changed** — the revision is content-preserving (D01/D02 PASS).

## Findings

| id | severity | finding |
|---|---|---|
| **F1** | **critical** | **HF-02 fires: 8 rows disjoin two frozen class ids** — `D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528` (detector: `evaluation_rubric.yaml:179-183`, "disjunction of class_ids"). A critical HF cannot be accepted regardless of other merits. Independently agrees with `reviews/L0-review-093.json` (HF-02). |
| **F2** | major | `metrics.class_binding` = **0.4194** (26/62 singular) vs target 1.0; 36 rows carry no class binding (target `evaluation_rubric.yaml:255-259`). |
| **F3** | major | **G-LIT scope criterion unmet**: 0/62 ledger rows and 0/97 audit rows record `matter_model` / `cosmological_constant` / `dimension` / `symmetry` / `formulation`, so source scope cannot be matched to `class_id` (`evaluation_rubric.yaml:138-142`). |
| **F6** | major | **Rev-4 axis vocabulary is not in A0.** `content_status` / `author_asserts_supports` are defined only in `build_literature.py:25-28` and `MANIFEST.json`; A0 at `d748a9e3574e` never names them. The ledger's strongest content assertion is therefore invisible to A0 detectors/metrics. Requires the joint A0 + `class_separation.py` + ledger amendment the L0 lead already recorded as BL-5 (for `conclusion_type`). |
| **F4** | minor | G-LIT `citation_support == 1.0` is **not computable as written**: registry status `verified-api` (78/97 rows) has no weight in the rubric vocabulary (`verified_primary`, `verified_secondary`, `partial`, `unresolved`, `contradicted`). |
| **F5** | minor | HF-01 / `PROTOCOL.md` rule 1 **vocabulary collision**: 30 ledger rows with `conclusion_type=theorem` carry no `artifact_refs`; A0's detector is `claim.`-scoped, so this is not a ledger hard failure (independent of `reviews/L0-review-093.json`, which counts HF-01). |
| **F7** | minor | 11 `content_status=verified` rows carry a metadata-only cited source (manifest-confirmed: `D-001, T-105, T-208, T-501, T-506, T-511, T-514, T-517, T-518, T-520, T-521`); the builder guard only rejects rows whose sources are **all** metadata-only. |

## What did *not* fire (controls and nulls)

- **HF-14 (as written) is closed at rev 4: 0 fires** (positive control: 60 fires on the archive).
  The rev-4 builder fails closed on the three fields A0 reads, and the axis split attributes the
  content assertion to the author while every row says `review_status=not_independently_reviewed`.
- HF-03: 0 rows cite an unresolved/contradicted source (all 97 audit rows are `resolved`).
- HF-07 duplication: 0 statement pairs above the 0.60 threshold.
- HF-02 unknown class tokens: 0; all class tokens are inside the frozen four.
- 12/12 mutation controls PASS (accepted status, supports_claim, unknown class, disjunction,
  content mutation, missing source, duplicate, forged review_status, field-removal silence,
  theorem-without-refs); `report.json`/`controls.json` carry the full table.

## Falsifier

Re-run `run_l0_rev4_review.py` at the same five pins and find a check whose status differs; or
exhibit a rev-4 row that disjoins class ids but is not in the F1 list; or a clause in A0
HF-02 / class_binding whose scope excludes ledger rows (which would void F1/F2). A rubric or
ledger revision changes the pin and voids the corresponding finding, **not** the measurement.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-097/l0_rev4_review/run_l0_rev4_review.py \
        --repo . --out artifacts/worker-097/l0_rev4_review
# exit 0 = pin stable + all controls pass ; 3 = stale pin ; 2 = control failure or drift
```

## Non-claims and limits

- No gate verdict, no node completion, no `validation_status` promotion, no mathematical claim.
- The instrument compares **ledger rows** to A0's detectors; it does not adjudicate whether the
  cited theorems are true.
- F6 assesses the axis split on its own documentation; it does **not** allege fabrication — the
  builder's guard is fail-closed and content is preserved.
- `MAP01`/`D03`/`H14S`/`META`/`H01`/`XREF` are INFO measurements, not pass/fail gates.
