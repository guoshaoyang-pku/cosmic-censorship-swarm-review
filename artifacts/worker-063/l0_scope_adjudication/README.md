# W063-L0-SCOPE-ADJUDICATION-01 — HF-02 scope on the live L0 ledger

Bounded, read-only adjudication input for `reviews/L0-freeze-reconciliation.json` blocker **BL-7**
(L0 has 0 independent accepts; two verdicts fail it on HF-02 because 8 rows' `class_ids` list holds
two frozen ids). Worker-063, node **L0**, gates **G-LIT / G-AUDIT**, classes
`AF-SCC-C2-VAC-GEN` + `AF-SCC-C0-VAC-GEN`.

## Question

Do the 8 rows `D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528` assert class leakage under
HF-02, or are they record-scope relevance rows misread by a claim-scoped detector?

## Method (all measured, all pinned)

No canonical file is written. `run_l0_scope_063.py` (stdlib only) pins
`ledger/theorems.jsonl a1674f094979`, `evaluation_rubric.yaml d748a9e3574e`,
`audit_lib.py ae573db84631`, `audit_run.py 3b27dd3fef7f`, `class_separation.py c266dbceca87`,
re-measures them after the run and fails closed on drift; runs the whole measurement twice and
requires identical per-check digests; and executes the **canonical** modules (imported from disk)
rather than paraphrasing them.

Checks: parse integrity → class-binding census → canonical claim/record routing → canonical
class-separation scans (declaration + prose) → independent statement-level merge/identity scan →
HF-14 self-certification at the live hash → in-memory repair simulation → 8 mutation controls.

## Results

| # | Measurement | Result |
|---|---|---|
| C01 | 62 rows, unique ids, full key set | PASS |
| C02 | 42 `class_ids` + 7 `informs_classes` = 49 tokens, all frozen; multi-id rows exactly the 8; 28 rows empty `class_ids` | PASS |
| C03 | `audit_run.scan_corpus` routes **0** ledger rows to `claims`, **62** to `records`; `check_class_binding` reads singular `class_id`; only `check_self_certification` sees records | PASS |
| C04 | canonical scanner flags the 8 two-id lists **not at all**; it flags exactly one live row — `T-402.regularity` = "Between C0 and C2 (weak null singularity)." (bare composite, declaration mode) | census |
| C05 | independent statement scan: **0 / 62** statements contain a positive merge/identity assertion of two frozen classes | PASS |
| C06 | HF-14 clean: no `status` / `validation_status` / `supports_claim` keys; `review_status` + `acceptance_authority` on all 62 rows | PASS |
| C07 | dry-run repair (secondary ids → `informs_classes`): literal disjunctions clear, 49-token census preserved, all other keys unchanged, **hash moves** to `833337de8450…`, and the T-402 `regularity` finding remains | PASS |
| C08 | mutation controls | **8/8** |

Status `MEASURED`, determinism digest `79d20294ee1d`, zero post-run drift on the frozen subject.

## Decision inputs (no ruling is made here)

- **R1 record-scope (canonical tooling):** HF-01/HF-02 never see ledger rows; under canonical
  tooling the live ledger has 0 critical HF-02/HF-01 findings and HF-14 is clean.
- **R2 field-literal (reviewer reading):** 8 disjunctions fire; repair is a class-binding content
  decision that moves the hash and voids both current verdicts (REC-4 currently forbids it).
- **R3 statement-literal (rubric text, `evaluation_rubric.yaml:52-54`):** 0/62 statements assert a
  merge, so the 8 firings are field-scope false positives, consistent with controller CF-16.
- **New observation:** any scope ruling must also cover free-text `regularity` fields — the
  canonical scanner flags `T-402.regularity`, and a `class_ids`-only repair does not clear it.

## Not claimed

No gate verdict, no node status, no `validation_status`, no class-binding repair, no theorem.

## Falsifier

Re-run `run_l0_scope_063.py` at the pinned hashes. Falsified if the ledger no longer measures
`a1674f094979…`; if any of the 62 rows routes to `claims`; if any of the 8 statements asserts a
merge of two frozen classes; if the canonical declaration/prose scan flags a live row other than
`T-402.regularity`; if any control M1–M8 stops reproducing; if two runs differ; or if a pinned
input drifts.

## Files

- `report.json` — full measurement, pins, decision inputs, falsifier
- `run_l0_scope_063.py` — instrument
- `entry_hashes.json` — sha256 of every file here + the review
