# AMENDMENT 01 — first-run result vs pre-registered expectations

**Task:** W099-GFORM-R3-F2B-COVERAGE-REPLICATION-01 (class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM).
**Amendment written:** 2026-09-12T01:26+08:00, after run 1 of the instrument and before the claim event.
**Rule:** the pre-registered method (R1/R2/R3, M1–M7) and the expectations E1–E6 in `PREREGISTRATION.json`
are **not edited**. This amendment records where the first run disagreed with them and what is
*reporting* change (new columns, role labels) versus what is a *result*.

## Result of run 1 (core_digest `b40a7021e9b2`, reproduced identically on run 2)

| expectation | pre-registered | measured | status |
|---|---|---|---|
| E1 pins + mirrors | 4/4 pins, 3/3 mirror pairs byte-equal | 4/4 pins match; 3/3 mirror pairs byte-equal | **met** |
| E2 R2 adjusted accepts = exactly {052,071,090} | 3 | **7** (`052,053,061,071,082,090,16`) | **not met** |
| E3 raw R3 accept count = 4, 4th = 072 superseded | 4 | R3 raw = **8**; 072 supersession confirmed | **partly met** (072 supersession is real and detected; the raw count is 8, not 4) |
| E4 `artifact_sha256`-keyed census = 0 accepts | 0 | **1** (worker-061, a variant-strength accept, not a schema review) | **not met** |
| E5 worker-018 count reproduced | 3 {052,071,090} | reproduced under **R1** (`counts_as_full_schema_verdict is true`): 3 {052,071,090}; **not** under R2 | **met only under R1** |
| E6 review-file quiescence | 0 mismatches, or all enumerated | **2 live-file mismatches** enumerated (worker-094 F1 review +13 s; worker-086 collision review +20 s), 1 historical supersede declaration, plus 1 FROZEN-manifest pin drift | **met as "enumerated"** |

## What the disagreement means

1. **R2 is broader than the controller's "full accept" notion.** R2 binds any review event
   declaring `reviewed_sha256 == b2ab6acb2bbe` and not carrying a candidate/aspect token in
   `target_id`. That set legitimately includes accepts of *other questions asked at the same pin*:
   worker-061's variant-strength accept (`task_id W061-F1-VARSTRENGTH-05`), worker-053's
   binding-chain accept (`FROZEN@... / F1@... / F2a@... / F2b@...`, no `reviewed_sha256`),
   worker-16's convergence triage, and worker-082's self-declared
   `review_kind: "A1 coverage / review-independence census (NOT a schema content review)"`
   with `counts_as_full_schema_verdict: false`.
   The pre-registered expectation E2 assumed R2 would coincide with the schema-content count; the
   measurement shows it does not. This is a finding about *counting rules*, not about the schema.

2. **The decisive count is reproduced under the narrowest self-declared rule R1.**
   `counts_as_full_schema_verdict is true` yields raw accepts {worker-052, worker-071, worker-090,
   worker-072}; supersession-adjusted (072's 01:15:24 revise supersedes its 01:10:13 accept)
   yields exactly {worker-052, worker-071, worker-090} — the same three-file set worker-018
   reported, obtained here from the append-only event stream rather than from live files.

3. **The field-key effect is smaller than reported.** Binding accepts on `artifact_sha256` at the
   pin returns worker-061 (one accept, non-schema), not zero; binding on `reviewed_sha256` returns
   seven under R2. The 0-vs-4 divergence is therefore reproduced only after a schema-scope filter
   (R1), not at the raw field-key level.

4. **Reporting change (not a rule change):** the mutation table now carries a `role` column.
   `review_path/review_sha256`-style pairs are live-file declarations and can mismatch;
   `supersedes_path/supersedes_sha256` pairs are declarations about the *superseded* revision, so
   a moved live file is expected and is labelled `historical_revision_declared` instead of
   `mismatch`. Run 1 had mislabelled worker-072's supersede pair; run 2+ does not.

## Independent material findings

* `reviews/F1-review-094.json`: event `REV-W094-F1-02-EV` (00:19:35) declared
  `review_sha256 1ff2f3d7…`; the file on disk measures `8ce9ba52…` (mtime 00:19:48, **+13 s**).
* `reviews/G-FORM-evidence-collision-086.json`: event `w086-20260912T004500-review-evidence-collision`
  (00:42:49) declared `a2a037f1…`; the file measures `888477f5…` (mtime 00:43:09, **+20 s**).
* FROZEN rev29 (`815e08079aef`, still declaring revision 29 at 01:24:43) resolves **49/50** files:
  `artifacts/formulation/tools/check_variant_registry.py` declares `c471da4b…` (4726 B) but measures
  `8c7ef46f…` (6043 B, mtime **01:21:56**). `VARIANT_REGISTRY.json` was also rewritten at 01:21:59
  but is byte-identical to its pin. This is inside the REC-36 rev14 window and is consistent with
  the authorised SET-label edit in progress; it is recorded as a per-file pin that no longer
  resolves, not as a verdict on the revision.

## Effect on the emitted claim

The claim reports R1/R2/R3 side by side, the R1 decisive set, the R2 over-count and its named
causes, the refined field-key result, the two live-file mutations, and the manifest drift at the
measured instant. It does not assert that worker-018 is wrong: it asserts that worker-018's
decisive three-file set is reproduced under R1 and that its `artifact_sha256`-keyed zero is a
file-census fact that does not transfer to the event stream at the raw field level.
