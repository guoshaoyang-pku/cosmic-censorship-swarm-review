# W029-L0-REV3-VERDICT-05 — independent L0 rev3 verdict (worker-029)

- **Target:** `ledger/theorems.jsonl` @ `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
  (62 rows), with companion `ledger/citation_audit.csv` @
  `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 rows).
- **Node / gate:** L0 / G-LIT. **Classes:** the four frozen classes.
- **Task:** `W029-L0-REV3-VERDICT-05` — the second independent full-L0 verdict at this hash,
  taken because `reviews/A1-rebind-coverage.json` (00:46:56) lists exactly one blocker:
  L0 has only one independent verdict at the measured hash.
- **Reviewer:** worker-029. `author_of_target: false`. A worker review is evidence only; it
  cannot set node status, `validation_status`, or a gate verdict.
- **Verdict: `revise`, score 3.5** — one hard failure, HF-02 on eight named rows.
- **Determinism:** two consecutive runs of `check_l0_rev3.py` produced byte-identical
  `report_core.json`; digest `2895748700ac001efb815518ab1ae85afc6fbfaff844a5d479755ca2dcde4412`.
  All 15 snapshots match their recorded hashes and all live paths still match the snapshots.

## 1. Hard failure

**HF-02 (class leakage) — `class_ids` disjunction, 8 rows:**
`D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528`.

Each carries two frozen class ids in one `class_ids` list (checked at the frozen bytes).
`evaluation_rubric.yaml:175-180` names `disjunction of class_ids` as a critical HF-02 branch.
The formulation group's own `VARIANT_REGISTRY.json` rule allows exactly two binding forms:
one exact frozen `class_id`, or a `(parent_class, variant_id)` pair. A `class_ids` list of two
frozen classes is neither form, so the defect does not depend on the rubric alone.

The two detectors actually implemented do **not** flag these rows:

- `artifacts/audit/audit_run.py:253-263` checks ledger records only for *invented* tokens — 0 hits.
- `research_map/class_separation.py` flags only a single merged token or an unknown `AF-` token
  — 0 hits in prose mode on these rows (control CTRL-4 in the report demonstrates the gap).

This is the A1 coverage gap the ledger author already records as **BL-6** (open, unfixed at this
hash). Remediation is a content decision — which class is primary, and whether the second becomes
`informs_classes` or a registry variant reference — not a metadata pass: 0 of the 8 rows names a
registered variant id literally.

## 2. Closed at this hash (independent confirmation)

- **HF-14 (self-certified acceptance): closed.** No row carries `status`, `validation_status` or
  `supports_claim`; `content_status` and `author_asserts_supports` are present on 62/62 rows and
  `review_status: not_independently_reviewed` on 62/62. The canonical predicate
  (`audit_lib.py:459-473`) reports **0** violations at this hash and **60** at the archived
  pre-rev3 bytes `ce42d205e761` under the same code — the positive control.
- **The rev3 change is rename-only and claim-lowering.** Comparing all 62 rows with the archive on
  18 content keys: **0 diffs, 0 rename mismatches**; keys added are exactly
  `content_status`, `author_asserts_supports`, `review_status`, `acceptance_authority`; keys
  removed are exactly `status`, `supports_claim`.
- **Class-token discipline:** all 42 `class_ids` tokens and all 7 `informs_classes` values (49
  class tokens total) are among the four frozen classes; 0 unknown tokens; taxonomy at snapshot
  declares exactly the four.

## 3. HF-01: not applicable to ledger records (disagrees with `worker-093`)

30 rows carry `conclusion_type: theorem` with no `artifact_refs`, which `worker-093` listed as a
hard failure. The rubric detector is `claim.`-scoped
(`evaluation_rubric.yaml:171-174`), and the canonical audit classifies rows with `theorem_id`
into its **`records`** corpus, never its `claims` corpus
(`artifacts/audit/audit_run.py:100-119`); measured: **0** ledger rows enter the claim corpus, and
**0** of the 30 rows lack `source_ids`. HF-01 therefore does not fire on these bytes.

The residual is real but is a **vocabulary collision** (`conclusion_type` read as an asserted
conclusion by `comms/PROTOCOL.md` rule 1 and `class_separation.py` `ASSERTED_LINE_KEYS`), which
the author already records as **BL-5** and deliberately defers to a joint A0 + A1 + L0 rename.

## 4. Other open items at this hash (not the decisive one)

| id | item | measured |
|---|---|---|
| class-binding metric | A0 `metrics.class_binding` target 1.0 | 26/62 singular = **0.4194**; 28 rows have no class binding |
| HF-03 | `source_meta` scope fields absent | 0/62 ledger rows, 0/97 audit rows |
| BL-4 | L1 `exact_locator` column semantics | audit rows resolve (97/97 resolver+HTTP 200), but column semantics are unresolved |
| BL-5 | `conclusion_type` vocabulary collision | as §3 |
| soft | declaration-mode `class_separation.py` flags one field | `T-402.regularity` "Between C0 and C2 (weak null singularity)"; prose mode 0; T-402 is already in the HF-02 set |

G-LIT's four row-level criteria (resolvable locators, honest `verification_status`, ≥3 independent
re-fetch spot checks, unresolved marked) are **all met** at this hash: 61 `abstract-read` + 1
`unverified`, 0 rows above abstract-read; 62/62 `unresolved` non-empty; 22 distinct spot-check
reviewers across 33 files binding L1 `315c19145065`. The L0 verdict is open because the A0
critical HF-02 is binding, not because a gate criterion fails.

## 5. Peer work at the same hash

- `worker-093` (`reviews/L0-review-093.json`): revise, same 8-row set; listed HF-01 as hard.
  This review agrees on HF-02 and the row set, and disagrees on HF-01 for the reason in §3.
- `worker-023` (`artifacts/worker-023/l0_hf02/`): same 8-row set, patch proposal moving secondary
  classes to `informs_classes`; not applied. This review independently reproduces the set and the
  registry-rule argument, and adds the executed-detector gap measurement and its controls.

## 6. Falsifier

Re-run `check_l0_rev3.py` against the same snapshots. This verdict is falsified if: (a) any of the
8 rows carries fewer than two frozen class ids; (b) any row outside the 8 carries two or more;
(c) the canonical HF-14 predicate reports a violation on the live bytes; (d) the rev3-to-pre-rev3
comparison shows a content-key diff; (e) a control in C10 fails to reproduce; or (f) two runs give
different digests. If `ledger/theorems.jsonl` no longer hashes to `a1674f094979`, this verdict is
**superseded**, not falsified, and must be re-issued against the new revision.

## 7. Reproduction

```bash
python3 artifacts/worker-029/l0_rev3_verify/check_l0_rev3.py
# writes report.json, report_core.json, evidence.json; expected digest
# 2895748700ac001efb815518ab1ae85afc6fbfaff844a5d479755ca2dcde4412
```
