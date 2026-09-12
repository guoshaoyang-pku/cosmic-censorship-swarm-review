# W063-L0-C0-THEOREM-01 — C0 `status_risk` vs per-row `conclusion_type`

Bounded, read-only scope measurement for the new clause in literature blocker
`lit-l7-20260912-004` (CRITICAL PATH): three L0 rows bound to **AF-SCC-C0-VAC-GEN**
(`T-302`, `T-303`, `T-526`) carry `conclusion_type: theorem`, while
`evaluation_rubric.yaml:100-104` says this class' status MUST be recorded as
`conditional` or `refuted_candidate`, **never** `theorem`.

Node **L0**, gates **G-LIT / G-AUDIT**, classes `AF-SCC-C0-VAC-GEN` + `AF-SCC-C2-VAC-GEN`.
Worker-063, one bounded task, then exit. No ruling is made here.

## Method (all measured, all pinned)

`run_l0_c0_theorem_063.py` (stdlib + PyYAML) pins and re-measures at exit:

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f094979…` (62 rows) |
| `evaluation_rubric.yaml` | `d748a9e3574e…` |
| `ledger/citation_audit.csv` | `315c19145065…` (97 rows) |
| `artifacts/audit/audit_lib.py` | `ae573db84631…` |
| `artifacts/audit/audit_run.py` | `3b27dd3fef7f…` |
| `research_map/class_separation.py` | `a8c04fc31e4a…` |

The whole core measurement runs twice and must produce identical per-check digests; the
canonical modules are imported from disk and executed, not paraphrased; eight mutation
controls run in memory only. **Observed live movement recorded, not hidden:** the canonical
detector was `c266dbceca87` (11152 B) at 00:50:31 and became `a8c04fc31e4a` (11457 B) at
00:52:00, inside the pass-05 classsep calibration window; `proposed/class_separation.py`
is unchanged at `e2d24b927ee8`. C04 is measured on the live bytes; no post-run drift.

## Results

| # | Measurement | Result |
|---|---|---|
| C01 | 62 rows, unique ids, single key set; no `status`/`validation_status`/`supports_claim`/`class_status` keys | PASS |
| C02 | C0-bound rows = **11**; conclusion_type census `open_problem 5, conditional_theorem 2, theorem 3, stability_result 1`; theorem rows exactly `{T-302, T-303, T-526}`; multi-class-token rows = 8 (the BL-7 set); 0 unknown class tokens | MATCH |
| C03 | Clause text extracted verbatim; HF-02 says "conclusion_type not allowed for class" but **no** frozen class carries a machine-readable allowed/forbidden conclusion_type list; the C0 restriction exists only as `status_risk` prose | GAP |
| C04 | `scan_corpus` routes **62 records / 0 claims**; `check_self_certification(records)` = **0**; `class_separation` flags **0** of the three rows and **0** findings for the whole ledger text; regression corpus 17 TP / 0 FN / 10 TN / 0 FP PASS | canonical tooling does **not** produce the finding |
| C05 | **0** rows carry any explicit class-status field; class status is carried only by per-row `conclusion_type`/`entry_kind`/`ledger_tags`; all 11 C0 rows have `unresolved` entries | no class-status record exists to constrain |
| C06 | Clause condition "Until L1 binds the exact hypotheses": SRC-004 Dafermos–Luk is `verified-primary/resolved`, but exact-hypotheses binding is **False**; the one hypothesis-mentioning citation is SRC-097 (unresolved); T-301 `unresolved` records the interior-data assumptions as "searched, not found" | restriction **remains in force** on the clause's own terms |
| C07 | mutation controls | **8/8** |

Determinism digest `e77521c41eec`, status `MEASURED`, zero pin drift.

## Decision inputs (no ruling is made here)

- **D1 field-literal:** the clause forbids recording this class' status as `theorem`; three
  rows bound to it record `conclusion_type: theorem` → HF-02 fires on 3 rows.
- **D2 row-vs-class:** `conclusion_type` types the cited source result, not the class
  conjecture status; the ledger contains no class-status record at all (C05), so the clause
  constrains a record that is not present.
- **D3 canonical-tooling:** the canonical audit stack routes ledger rows to `records`,
  never `claims`; it flags none of the three rows. The finding is a reviewer/manual reading,
  not a canonical-tool output — so it cannot be discharged, or confirmed, by re-running
  canonical audits.
- **D4 machine-readability:** HF-02's "conclusion_type not allowed for class" has no
  enumerable per-class list; the rule is inferable only from `status_risk` prose.
- **D5 side-observation:** `T-526` is `entry_kind: preprint_result` typed `theorem` and bound
  to C0 although its own scope caveats say it "Does not prove C^0-inextendibility"; `T-303`
  carries both C2 and C0 with one `conclusion_type`. A second, independent binding question
  sits in the same three rows.
- **D6 clause condition:** the "until L1 binds the exact hypotheses" antecedent is unresolved
  (C06), so the restriction is live on its own terms.

## Not claimed

No gate verdict, no node status, no `validation_status`, no class-binding repair, no write to
any pinned file, no claim that the three rows are or are not class leakage.

## Falsifier

Re-run `run_l0_c0_theorem_063.py` at the pins above. Falsified if any pinned input drifts;
if the C0-bound census or the three theorem rows change; if any canonical module flags the
three rows for the C0-status pattern; if any control M1–M8 stops reproducing; or if the two
core runs differ.

## Files

- `report.json` — full measurement, pins, decision inputs, falsifier
- `run_l0_c0_theorem_063.py` — instrument
- `entry_hashes.json` — sha256 of every file here
