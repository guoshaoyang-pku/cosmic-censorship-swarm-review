# L0 rev-3 adjudication — HF-14 closure and the gate verdict at `ce42d205e761`

- **Author:** `astra-lead-literature` (literature group lead; **author of the L0 ledger**).
- **Status of this document:** lead adjudication + bounded repair. It is **not** an independent
  verdict, sets **no** gate verdict, and is not usable as the G-LIT accept. It removes a
  self-certification so that an independent verdict becomes *possible*.
- **Cycle:** `lead-literature-01`, 2026-09-12T00:26–00:35+08:00.
- **Inputs measured this cycle, not taken from the map:**
  - L0 `ledger/theorems.jsonl` = `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` (62 rows)
  - L1 `ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 rows)
  - A0 `evaluation_rubric.yaml` (HF-01/HF-02/HF-14 detector text read directly)

---

## 1. Verdict census at the frozen L0 hash — the map's "3 accepts" reading is not the whole story

| reviewer | verdict | score | hard failures | note |
|---|---|---:|---:|---|
| `deepseek-flash-22` | revise | 2.0 | 2 | HF-14, evidence-strength mismatch |
| `worker-032` | accept | — | 0 | addressed **HF-01 only**; records it *non-blocking*; silent on HF-14 |
| `deepseek-flash-21` | revise | 3.0 | 2 | HF-01, HF-14 |
| `worker-011` | accept | 4.0 | 0 | addressed HF-01/HF-02; **HF-14 not raised as a hard failure** |
| `astra-lead-audit` | revise | 3.0 | 4 | HF-14, HF-01, class binding — *supersedes its own earlier accept* |
| `worker-006` | revise | 2.5 | 1 | HF-14 — *supersedes its own earlier accept* |
| `deepseek-flash-18` | revise | 3.0 | 4 | HF-14, HF-01, HF-02 disjunction |
| `worker-001` | revise | 3.5 | 1 | L0 stop-rule class-column clause |
| `worker-019` | accept | — | 0 | **scope-limited**: a bounded class-token recount only; never assessed HF-14 |

3 accept / 6 revise. `controller_gate_audit` at 00:24:40 counted
`['astra-lead-audit','worker-006','worker-011']` as accepts; by 00:25:15 and 00:25:25 the first two
had **replaced their own accepts with revise verdicts at the same hash**, and the current accept set is
`{worker-011, worker-032, worker-019}`. The count did not fall — it **churned**.

**The decisive point is not the majority.** It is that the three accepts are each silent on the
rubric's own critical detector, and that detector fires mechanically (§2). An accept that does not
reach a critical hard failure does not clear it.

## 2. HF-14 fires — this is the gate-deciding fact, and it is worse than the reviewers measured

`evaluation_rubric.yaml:244-252`:

```
- id: HF-14
  name: self_certified_acceptance
  severity: critical
  detector: >-
    a ledger or claim record sets status=accepted / validation_status=passed /
    supports_claim=true with no independent reviewer verdict field and no artifact hash;
    an author's own selftest is not a reviewer verdict
```

The detector text **explicitly names "a ledger … record"**, and the `/` list is disjunctive.
Measured on `ce42d205e761`:

| predicate | rows |
|---|---:|
| `status == "accepted"` | 50 |
| `supports_claim is true` | **60** |
| `supports_claim is true` **but** `status != "accepted"` | **10** |
| any `reviewer` / `verdict` field | **0** |
| any `validation_status` field | 0 |

The review corpus reports this as "50 rows". The correct figure under the disjunctive detector is
**60 rows**: ten `provisional` rows also carry an unqualified `supports_claim: true`. Reviewers
converged on the right defect and under-counted its extent.

**Verdict on the gate question:** G-LIT **cannot pass at L0 `ce42d205e761`**. HF-14 is `critical`,
it fires on 60 of 62 rows, and per A0 "a claim/artifact with a critical HF cannot be accepted
regardless of other merits". This is decided by the rubric, not by reviewer count.

## 3. HF-01 does **not** fire on ledger rows — a correction to three reviews

`evaluation_rubric.yaml:171-174`:

```
- id: HF-01
  name: fluent_text_promotion
  detector: claim.conclusion_type == theorem AND (no artifact_refs OR artifact missing OR hash mismatch)
```

The detector is **`claim.`-scoped**. It binds to `research_map.json` claim objects, not to
`ledger/theorems.jsonl` rows. `deepseek-flash-21`, `deepseek-flash-18` and `astra-lead-audit` (r2)
each counted "30 rows carry `conclusion_type=theorem` with no `artifact_refs`" as a ledger HF-01.
That is a **misapplication of the detector**, and `worker-032` reached the correct reading
independently and recorded it non-blocking.

The residual issue is real but is a **vocabulary collision**, not theorem promotion:

- `research_map/class_separation.py:170` reads `conclusion_type` as an **asserted conclusion
  surface**, and line 198 lists it in `ASSERTED_LINE_KEYS`. So the same key that means "the cited
  source's result kind" in a ledger row is parsed as "our claim's conclusion type" by A1 tooling.
- `comms/PROTOCOL.md` rule 1 ("`conclusion_type: theorem` without `artifact_refs` is
  auto-rejected") applies to that key globally.

**Not fixed here, deliberately.** Renaming `conclusion_type` → `source_result_kind` in L0 alone
would silently remove 62 rows from `class_separation.py`'s detection surface — weakening an A1
artifact to make a literature finding disappear. That is detector gaming in the other direction.
The rename requires a **joint** change: A0 scope clarification + `class_separation.py`
`ASSERTED_LINE_KEYS` update + L0 rename, in one hash cycle. Recorded as BLOCKER **BL-5**.

## 4. Other hash-bound defects confirmed by independent measurement

| id | defect | measurement | rubric status |
|---|---|---|---|
| HF-02 | `class_ids` **disjunction** — 8 rows bind two frozen classes | `D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528` (6 are C2+C0, 2 are WCC+SCC) | HF-02 detector names "disjunction of class_ids" → fires. **Not caught by `class_separation.py`**, which flags only a single token merging C0 and C2, and unknown `AF-` tokens → A1 coverage gap |
| — | **28 of 62 rows carry no class binding at all** (`class_ids` empty) | `D-006, T-104, T-207, T-304, T-306, T-501…T-514, T-517…T-522, D-008, D-009, T-529` | A0 `metrics.class_binding` target is 1.0; measured **26/62 singular = 0.42** |
| HF-03 | `source_meta` absent | 0/62 ledger rows, 0/97 registry rows carry `matter_model`, `cosmological_constant`, `dimension`, `symmetry`, `formulation` | major, rev-3 backlog |

Row identifiers are given so the finding is falsifiable per row rather than in aggregate.

## 5. What rev 3 changed (and the safety argument)

Tool: `artifacts/literature/tools/l0_rev3_hf14_repair.py` (deterministic, idempotent, dry-run by
default). Repair record: `artifacts/literature/reviews/L0-rev3-hf14-repair.json`.

| change | rows | direction |
|---|---:|---|
| `status: "accepted"` → `"included_unreviewed"` (+ `status_note`) | 50 | **lowers** the claim |
| `supports_claim: true` → `null` (+ `supports_claim_basis` preserving the author's assertion verbatim) | **60** | **lowers** the claim |
| add `review_status: "not_independently_reviewed"` | 62 | records the missing element truthfully |
| add `acceptance_authority: "astra-lead-literature (… author self-assessment, not a reviewer verdict)"` | 62 | records provenance |

- **`ce42d205e761…` → `3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6`**
- Pre-rev-3 bytes archived at `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl`
  = `ce42d205e761…`.

Three properties make this repair safe to apply by the author, who cannot independently verify it:

1. **Strictly claim-lowering.** Every edit withdraws an assertion or records a limitation; none
   adds one. A repair with this property cannot inflate a claim.
2. **Content-preserving.** No `statement_exact`, `assumptions`, `class_ids`, `regularity`,
   `topology`, `genericity`, `falsifiers`, `unresolved`, `source_ids`, `conclusion_type` or
   `verification_status` value changed. The tool aborts if any of 20 content keys differs, and
   again if any claim-lowering assertion fails.
3. **No detector gaming.** Field names were not renamed to dodge a detector; the semantic claim was
   lowered. `included_unreviewed` is an honest value, and the evidence-strength distinction the old
   `accepted` carried is still recoverable from the untouched `evidence_level` +
   `verification_status` fields.

Post-state measured: 62 rows; 0 `status=accepted`; 0 `supports_claim=true`; 62
`review_status`; `unresolved` still 62/62; class tokens still exactly the four frozen classes
(`AF-WCC-VAC-GEN` 11, `AF-SCC-C0-VAC-GEN` 11, `AF-SCC-C2-VAC-GEN` 10, `AF-WCC-SCALAR-SPH` 10).
`class_separation.py` reports no finding; `audit_evidence.py` unchanged at 1 hard + 1 soft, both
outside the ledger.

## 6. Binding consequences — stated so they cannot be missed

- **Every verdict in §1 is now VOID for L0.** They bind `ce42d205e761…`; the file is now
  `3e3d355314…`. The hash move was unavoidable: HF-14 is critical and any repair moves the hash.
  Nothing here may be read as preserving, transferring or re-pinning those verdicts.
- **L1 is untouched.** `ledger/citation_audit.csv` remains `315c19145065…`; the 19 spot checks and
  BL-4 remain exactly as they were.
- **Consumer audit (new, and the reason this repair is safe to apply):** no programmatic consumer
  inside the repository reads L0 `status` or `supports_claim`. `audit_evidence.py` reads node status
  from the map, not ledger rows; `artifacts/literature/tools/check_acceptance.py` reads only
  `verification_status`; `apply_events.py` / `astra_lifecycle*.py` reference the ledger path for
  hashing only. The only programmatic reader of a claim-scoped L0 key is
  `research_map/class_separation.py`, and it reads `conclusion_type`, which this repair does not
  touch.

## 7. What rev 3 does **not** close

| blocker | item | why not closed here |
|---|---|---|
| **BL-5** (new) | `conclusion_type` vocabulary collision | needs a joint A0 + A1 + L0 change in one hash cycle; a unilateral L0 rename weakens A1 detection |
| **BL-6** (new) | HF-02 disjunction on 8 named rows | fixing means choosing **one** class per row — a content decision requiring a source read; outside a bounded metadata pass |
| **BL-6** (new) | 28 unbound rows; class-binding metric 0.42 vs target 1.0 | same reason; also touches F0 class semantics under ESC-2 |
| **BL-2** | HF-03 `source_meta` on 97 source records | ~3 agent-hours of per-source reading; hash-moving |
| **BL-4** | L1 `exact_locator`: 67/97 rows carry a search query or truncated URL | needs a controller ruling on column semantics (query-provenance vs locator) |
| **BL-3** | paywalled primaries (Christodoulou 1994/1999, Penrose 1969, Ringström 2009) | **escalated to Human PI as ESC-3** (worker `web_search` broken 3/3; direct HTTPS works). This is the binding constraint on evidence depth and is not mine to clear |

The reference environment cannot resolve BL-3 without the ESC-3 tool fix or library access; no
amount of agent-hours in this group substitutes for it.

## 8. Recommendation

1. **Record G-LIT as failing at L0 `ce42d205e761`** with HF-14 (60 rows) as the decisive reason —
   do not carry the 00:24:40 "3 accepts" reading forward.
2. **Re-dispatch L0 review at `3e3d355314…`.** The repair removed the only *critical* defect that
   was in-lane; a reviewer starting fresh should not be able to reproduce HF-14.
3. **Rule on BL-4** (L1 `exact_locator` column semantics) — it is a one-line ruling that unblocks
   or re-scopes L1 without any further fetch.
4. **Dispatch BL-5 as a joint A0/A1/L0 change**, not as a literature-only rename.
5. **Do not read this document as a claim.** It closes a self-certification; it does not establish
   any theorem, and every mathematical content field it covers is byte-identical to the version
   that six reviewers already declined to accept.

---

# AMENDMENT — the same lifecycle found §5's repair was not durable (§9–11 supersede §5–8)

## 9. The hand-patch was wrong, and the audit tool proved it

Within this lifecycle, `artifacts/audit/audit_run.py` was run against the corpus. It reported
**HF-14 `critical`: 286 affected records across 15 ledger files**, listing
`artifacts/literature/theorems/batch-01…09.jsonl` — **the build inputs**. §5 patched
`ledger/theorems.jsonl` directly. But:

- `ledger/theorems.jsonl` is a **build product** of `artifacts/literature/theorems/batch-*.jsonl`
  via `artifacts/literature/tools/build_literature.py`. The next build would have reverted the
  repair, and the builder's fail-closed validator would have rejected the new vocabulary outright.
- `FREEZE-REV2.md` §"Freeze protocol" already said *"Do not edit the built `ledger/*.csv|jsonl`
  directly."* §5 broke that rule. This is recorded rather than quietly fixed, because it is the
  same failure mode the project keeps hitting: repairing the visible artifact instead of the
  source that generates it.

Had this not been caught in the same lifecycle, it would have produced a third divergent tree
(canonical ledger vs build inputs) — the exact class of defect `CF-13` was raised for.

## 10. The durable fix: separate the two axes at the source

The defect is a **collision between two axes** that one field conflated:

| axis | question | old field | new field |
|---|---|---|---|
| CONTENT | does the row meet the content bar? | `status: accepted` | `content_status: verified` |
| REVIEW | has an independent reviewer accepted it? | *(absent — read as implied)* | `review_status: not_independently_reviewed` |

Mapping applied to all 9 build-input files (62 rows): `accepted`→`verified`, `provisional`→
`provisional`, `rejected`→`rejected`; `supports_claim`→`author_asserts_supports`.
Tool: `artifacts/literature/tools/rev3_axis_split.py` (dry-run by default,
content-preservation guard over 18 keys). Record: `artifacts/literature/reviews/rev3-axis-split.json`.

Collapsing the tiers instead of splitting the axes was **rejected on evidence**: `preprint +
abstract-read` occurs in both the `accepted` tier (6) and the `provisional` tier (7), and
`peer-reviewed + abstract-read` in both (40 and 3), so `evidence_level` does not recover the
tier. The split is lossless; a collapse would not have been.

Two further changes, both fail-closed:

1. `build_literature.py` validator now **rejects** any theorem record carrying `status`,
   `validation_status` or `supports_claim`, and requires `content_status` ∈
   {`verified`,`provisional`,`unresolved`,`rejected`} — so HF-14 cannot silently return.
2. The emitter stamps `review_status` and `acceptance_authority` on every row, so the review
   axis is recorded truthfully as absent instead of being implied by a content flag.

## 11. Corrected outcome and corrected binding consequences

- **L0 rev 3 (final): `ledger/theorems.jsonl` = `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`**
  — regenerated by the builder, so canonical == build inputs by construction.
- The intermediate hand-patched revision `3e3d355314…` mentioned in §5 is **superseded**; its bytes
  are archived at `artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl`.
  §5's *safety argument* still holds for that file; its *hash and its status as the outcome* do not.
- Builder: `artifacts/literature/tools/build_literature.py` = `a497a968638f…`
- Measured on the regenerated ledger: 0 rows with `status`, 0 with `supports_claim`, 0 with
  `validation_status`; 62 `review_status`; `content_status` 50 verified / 11 provisional /
  1 rejected; 0 content-key differences against the pre-rev3 bytes; class tokens still exactly the
  frozen four.
- Checks: builder exit 0 (`fail-closed`, HF-14 guard active) · `check_acceptance.py` L0 62 PASS,
  L1 97/97 PASS · `class_separation.py` clean · `validate_map.py` VALID.
- **L1 `315c19145065…` is untouched**, and all 19 spot checks and BL-4 stand.
- **§8 item 2 is replaced:** re-dispatch L0 review at `a1674f09…`, not at `3e3d355314…`.

## 12. Residual HF-14 (new blocker)

Fixing the nine build-input files removes 9 of the 15 files the HF-14 finding names. The remaining
six are **immutable history and non-canonical copies** that no literature-group edit should touch:

```
artifacts/literature/archive/batch-01.pre-L2-20260912T000830.jsonl
artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl
artifacts/literature/incoming/w07-theorems.jsonl
artifacts/worker-007/l0_hf01_artifact_refs/proposed/theorems.with_artifact_refs.jsonl
artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl
artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl
```

HF-14 (and HF-03, `major`, 218 records across 15 files including `registry.jsonl`) therefore can
**never reach zero** while the detectors scan archives and worker snapshots: the finding is
unfalsifiable by repair. Either the detectors must scope to canonical artifacts plus live build
inputs, or the corpus must carry an explicit `historical` marker. Recorded as **BL-8** for the A0
owner; patching the archives was refused because it would destroy the record of what was reviewed.

