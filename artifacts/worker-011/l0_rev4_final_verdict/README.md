# W011-L0-REV4-FINAL-VERDICT-02

Independent blind L0 / G-LIT verdict at the announced rev-4 ledger bytes.
**Verdict: revise 3.0** (worker verdict; cannot set a gate verdict or node status).

## Pins

- `ledger/theorems.jsonl` = `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
- `ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9`
- `evaluation_rubric.yaml` = `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885`
- `artifacts/literature/registry.jsonl` = `ea02d1943fda50e5e1c7ce10fe2a1cd6e7784a2c9f2467c7cb8597c63442652d`
- no drift during the run; instrument exits 3 (UNMEASURED) on any pin mismatch

## Machine findings (firing sets are the deliverable)

### V-011-L0-01 — HF-14

60 of 62 ledger rows set a truthy support assertion (author_asserts_supports) with no independent reviewer verdict field and no artifact hash; review_status is 'not_independently_reviewed' on all 62 rows. HF-14's own detector text names ledger records.

- rows (60): D-001, D-002, D-003, D-004, D-005, D-006, T-101, T-102, T-103, T-104, T-105, T-106, T-107, T-201, T-202, T-203, T-204, T-205, T-206, T-207, T-208, T-209, T-301, T-302, T-303, T-304, T-305, T-306, T-401, T-402, T-501, T-502, T-503, T-504, T-505, T-506, T-507, T-508, T-509, T-510
- falsifier: Produce one row whose support assertion is backed by an independent reviewer verdict field plus an artifact hash, or an audit-lead scope ruling that HF-14 does not apply to ledger rows.

### V-011-L0-02 — HF-04

11 rows assert a bound/rate/codimension in statement_exact or label and no quantity_check field exists anywhere in the ledger (sensitivity: 36 rows if bare regularity-class mentions count, 40 if the regularity field is also counted); G-LIT criterion 4 and verifiers.literature.checks require a quantity_check for quantitative claims.

- rows (11): D-005, T-103, T-204, T-304, T-305, T-501, T-502, T-503, T-504, T-516, T-519
- falsifier: Add a quantity_check (field or evidence ref) to each listed row and re-run; or rule G-LIT criterion 4 claim-scoped; or show that the listed statements carry no quantity under the rubric's rate/exponent/codimension reading.

### V-011-L0-03 — blocking-criterion

G-LIT criterion 3 ('matter/Lambda/dimension/symmetry of the source explicitly recorded') is not met at either pinned source artifact: registry.jsonl and citation_audit.csv record class_mapping only.

- rows (0): 
- falsifier: Show a pinned column carrying matter/Lambda/dimension/symmetry/formulation per source; class_mapping alone does not count.

### V-011-L0-04 — HF-02 (scope-disputed) (soft)

8 rows carry >1 frozen token in class_ids. Literal HF-02 firing; the ledger's own does_not_imply fields disclaim the union readings, and a tested staged repair exists (artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl#b3ab6a1a6357). The accept at this hash does not discharge this.

- rows: D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528
- falsifier: An audit-lead scope ruling that the HF-02 disjunction clause is claim/schema-scoped; or publish the staged repair and re-review.

### V-011-L0-05 — HF-01 (scope-disputed) (soft)

30 rows use conclusion_type=theorem and the ledger row schema has no artifact_refs field (field absent from all 62 rows). Detector text begins 'claim.conclusion_type', so a claim-scoped reading is defensible; recorded, not silently counted.

- rows: T-101, T-102, T-105, T-201, T-202, T-203, T-302, T-303, T-306, T-501, T-502, T-504, T-506, T-508, T-509, T-511, T-513, T-514, T-516, T-517, T-519, T-520, T-521, D-008, T-523, T-524, T-526, T-527, D-009, T-529
- falsifier: An audit-lead ruling either way; if ledger-scoped, theorem rows need artifact_refs.

### V-011-L0-06 — minor (soft)

21 rows carry no class token in class_ids or informs_classes; several are class-external by design (e.g. dust counterexamples), so this is recorded as a scope note, not a hard failure.

- rows: D-006, T-104, T-207, T-502, T-503, T-504, T-507, T-508, T-509, T-512, T-513, T-514, T-517, T-518, T-519, T-520, T-521, D-008, T-522, D-009, T-529
- falsifier: Show a listed row that is class-internal under the frozen taxonomy.

## Checks and controls

- checks: {"K01": "PASS", "K02": "PASS", "K03": "PASS", "K04": "PASS", "K05": "PASS", "K06": "PASS", "K07": "PASS", "K08": "PASS", "K09": "PASS", "K10": "FAIL", "K11": "PASS", "K12": "PASS"}
- controls: 7/7 planted defects detected

## Scope and blind spots

G-LIT criteria at the pinned bytes plus the class-binding and honesty fields. Excludes per-row mathematical entailment and live re-fetch (documented blind spots).

- No per-row semantic entailment check that a quoted source entails the row's statement.
- No live re-fetch: resolution is measured against the pinned citation_audit.csv.
- No judgement on the mathematical truth or scope of any individual theorem row.

## Rerun

```bash
python3 artifacts/worker-011/l0_rev4_final_verdict/check_l0_rev4.py
python3 artifacts/worker-011/l0_rev4_final_verdict/make_artifacts.py
```

A worker verdict is not a gate verdict. Worker-011 cannot set `status=done`, `validation_status=passed`, or a gate verdict.
