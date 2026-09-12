# L0 verdict census at the frozen rev-3 hash — measured from the event streams

- **Actor:** `astra-lead-literature` (group `literature`, canonical owner of L0/L1)
- **At:** 2026-09-12T00:57+08:00 · **Gate:** G-LIT · **Node:** L0
- **Target:** `ledger/theorems.jsonl`
  `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` (151521 B, 62 rows,
  mtime 00:39:11, unchanged through this lifecycle; L1 `315c1914…` unchanged)
- **Method:** read-only scan of `comms/outbox/**/*.jsonl|json` (all 63 literature outbox lines plus
  every worker outbox), dedup by `event_id`; script `artifacts/literature/reviews/l0_verdict_census.py`
  (sha256 `6d5b906525e98cdfb10a7bcbb86b7e80b07e3d11fc6fddeeb37107f8911f1b0e`); machine record
  `L0-verdict-census-20260912T0058.json` (sha256 `5053607115fd26ef…`).
- **Authority:** this is **not** an accept, **not** a gate verdict, **not** a node status, and
  `counts_toward_gate_accept = false`. It is a measurement of what independent reviewers already
  emitted. Fluent text is never promoted.

## Inclusion predicate

A review event is an **L0 content verdict** iff all four hold:

1. `event_type == review`;
2. it binds the hash (`artifact_sha256`/`reviewed_sha256` = `a1674f09…`, or an `evidence_ref`
   carries `ledger/theorems.jsonl#a1674f09…`, or `target_id` carries the prefix);
3. its base `target_id` is the ledger as a whole (`L0`, `L0,L1`, or `ledger/theorems.jsonl…`);
4. it is not a sample spot check, a builder/tooling review, or another object's review.

Reviewer independence: the reviewer is not the ledger author. One author-side adjudication
(`reviews/L0-review-rev3-final.json`, actor `astra-lead-literature`) is therefore **excluded by
construction** and does not appear below.

## Result — 12 L0 content verdicts at the unchanged hash

| # | reviewer | verdict | score | full-schema basis | hard failures |
|---|---|---|---|---|---|
| 1 | worker-093 | revise | 3.5 | target-only | HF-02, HF-01 |
| 2 | worker-097 | revise | 1.75 | target+instrument-path | HF-02 (critical) + 3 major |
| 3 | worker-023 | revise | 3.5 | target+instrument-path | HF-02, HF-01 (literal) |
| 4 | worker-037 | revise | 4.0 | target+instrument-path | **none** (token non-lowering; non-blocking recommendation) |
| 5 | deepseek-flash-18 | revise | 3.0 | target+instrument-path | HF-14, HF-02, HF-04 |
| 6 | **worker-072** | **accept** | **4.5** | target+instrument-path | none |
| 7 | **worker-075** | **accept** | **4.0** | **attested full schema** | none |
| 8 | worker-025 | revise | 3.5 | target-only | HF-02 (8-row set) |
| 9 | worker-063 | inconclusive | 2.0 | target-only | none — scope adjudication only |
| 10 | worker-005 | revise | 3.0 | target+instrument-path | HF-W005-L0-01 (`exact_locator` is a discovery query on 67/97 rows) |
| 11 | worker-029 | revise | 3.5 | attested | HF-02 (8-row set, C7) |
| 12 | worker-011 | revise | 3.0 | attested | HF-14 (critical, 60/62), HF-04 (11 rows) |

**Counts: 2 accept · 9 revise · 0 reject · 1 inconclusive · 12 distinct reviewers.**

### The two accepts, and what each one actually covers

- **worker-072 — accept 4.5.** Independent byte-identical re-emission of the announced build
  product from the declared source of truth; HF-14 content/review axis split; invariants; L1
  cross-consistency; controls. It **explicitly disclaims** citation-content and mathematical
  verdicts and **defers HF-02 to A0** (non-blocking note W072E-F5). It lives at
  `artifacts/worker-072/l0_cf19_rederive/report.json#e45aca0ff81f` under the key
  `verdict_recommendation`, which is why the controller's `reviews/`-scoped scan does not see it.
- **worker-075 — accept 4.0, `counts_as_full_schema_verdict: true`.** Independent 11-check
  instrument (pin, rows, HF-14 zero, axes, frozen tokens, disjunction census, theorem rows,
  unresolved, locators, honesty, merge phrases), hash re-measured after the run, peer verdict
  disclosed as read after the report. It records rubric-literal **HF-02 and HF-01 as OPEN
  OBJECTIONS** classified as rubric-scope questions, not ledger hard failures, and flags the
  T-515/T-528 C0 binding as the owner's question.

Both accepts are at the same unchanged bytes, by distinct reviewers, neither of them the author.
Both are **conditional on the HF-02 scope reading**: neither asserts that the 8 two-class rows are
compliant; each classifies the disjunction as a rubric-scope item and accepts the ledger text as
written.

### The nine revises

Seven of the nine revises carry hard failures; the two hard-failure clusters are:

- **HF-02 (8-row class disjunction)** — worker-097, ‑023, ‑025, ‑029 (and flash-18): the set
  `D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528` is independently re-derived at least
  six times from the frozen bytes.
- **HF-14 (renamed-vocabulary support assertion)** — flash-18 (60/62 `author_asserts_supports`)
  and worker-011 (critical, 60/62). The author-side measurement is 0/62 on the literal predicate
  (`status`/`validation_status`/`supports_claim` absent) and 62/62 `review_status =
  not_independently_reviewed`; the disagreement is about whether the renamed vocabulary
  re-implements the forbidden pattern (BL-9, A0-owned).
- worker-037 is a revise with **no hard failures** (token-level non-lowering only) and
  worker-005's hard failure is the L1 `exact_locator` semantics (BL-4/REC-6 territory), not L0 text.

## Why this number differs from the controller's scan

`lifecycle_20260912-005124.json` reports `review_coverage.L0 = 1` and the pass-05-final scan
reported 0 accepts. This census reads **2 accepts**. The difference is measurable, not interpretive:

- worker-072's report is outside `reviews/` and uses `verdict_recommendation` rather than
  `verdict`;
- worker-075's verdict arrived 00:49:30 and is `counts_as_full_schema_verdict: true` but was not
  picked up by the pass-exit scan;
- worker-037, ‑097 and ‑005 likewise sit outside `reviews/`.

This is the same defect recorded as **BL-10**. It is a scan-scope defect, not a missing verdict.

## The one ruling that decides the L0 half of G-LIT (BL-7)

> **Does HF-02 (class disjunction) apply to ledger rows?**

New evidence since BL-7 was raised, independent of the author:

- **worker-063 (inconclusive 2.0, decisive-input finding W063-L0S-R1):** the canonical scanner
  routes **62/62 ledger rows to `corpus['records']`, 0/62 to `corpus['claims']`**;
  `check_class_binding` runs only on claims and reads the singular `class_id` key, while records go
  to `check_self_certification`. Under canonical tooling the live ledger has **0 critical
  HF-01/HF-02 findings**.
- **worker-036 / worker-080:** `class_separation.py` has no branch for a container binding ≥ 2
  frozen class ids; the recorded classsep PASS cannot be cited as HF-02 coverage on the ledger.
- **worker-075:** classifies the 8 rows as `relation_or_variant_mention` (6) and
  `wcc_antecedent_status` (2), i.e. prose relations, not a union-class definition — and accepts.
- The repair is already **proven and scope-clean** if the ruling goes the other way: worker-023's
  patch, independently re-derived by worker-052 (accept 4.5) and validated by worker-025
  (62 rows preserved in order; only `class_ids`/`informs_classes`/`ledger_tags` change;
  idempotent; staged copy `b3ab6a1a635720a9`; T-515/T-528 become singular WCC).

**Branches:**

| BL-7 ruling | consequence |
|---|---|
| **out of scope** (canonical-tooling reading; worker-063) | 2 independent accepts stand at the unchanged hash `a1674f09…`; the L0 half of G-LIT is **proposable**, no ledger write, no fresh round |
| **in scope** (rubric-literal record reading) | both accepts are qualified by the same 8 rows; the repair is a **content** change that moves the hash and **voids all 12 verdicts**; a fresh round is required after the rev-4 class-binding repair (REC-4 forbids it inside the metadata patch) |

No third branch is available: at 2 accepts the gate is no longer reviewer-latency-bound, it is
ruling-bound.

## Falsifier

This census is falsified if (a) either ledger measures a sha256 other than `a1674f09…` / `315c1914…`;
(b) any listed verdict does not bind the stated hash, or a further L0 content verdict at the hash
exists and is omitted; (c) either accept reviewer is not independent of the ledger author or
reuses pre-rebuild verdict text; (d) any event classified out-of-scope is in fact a ledger-wide
verdict.

## Not claimed

Gate verdict · node completion · independent review · accept of L0 · any theorem · that BL-7 or
BL-9 is resolved · that the 8 two-class rows are compliant.
