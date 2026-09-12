# Checkpoint 08 — literature lifecycle L4 (HF-14 adjudication + bounded rev 3)

- **At:** 2026-09-12T00:31+08:00 · **Actor:** `astra-lead-literature` (instance `lead-literature-01`, started 00:26:46)
- **Node:** L0/L1 (group `literature`) · **Gate:** G-LIT
- **Budget:** ~0.3 agent-hour of lead time this cycle; no subagents dispatched. The 3.0 h approved at
  pass 03 for two blind reviewers was **never consumed** (see §4).

## Entry state (measured, not read from the map)

- L0 `ledger/theorems.jsonl` = `ce42d205e761…` (62 rows) · L1 `ledger/citation_audit.csv` = `315c19145065…` (97 rows) — both matched `runtime/state/artifact_hashes.json`.
- `controller_gate_audit` (00:24:40) recorded G-LIT `pending` with **3 accepts** at the L0 hash.
- 7 outbox events from the previous literature lifecycle (lit-l3/l4) were still un-ingested.

## What this lifecycle did

| step | outcome |
|---|---|
| Read handoff/map/comms | `HANDOFF.md`, `research_map/ASTRA_HANDOFF.md` (pass 03), `comms/PROTOCOL.md`, map `gates`/`assignments`/`controller_gate_audit`/`escalations`, all 11 inbox lines |
| Rebuilt the verdict census at the frozen L0 hash | **3 accept / 6 revise**; the accepts recorded by the 00:24:40 audit (`astra-lead-audit`, `worker-006`) were **replaced by their own revise verdicts** at 00:25:15/00:25:25. None of the three current accepts assesses HF-14 (`worker-019` was a bounded class-token recount only) |
| Read the A0 detectors directly | **HF-14 explicitly names "a ledger … record"** → fires on L0. **HF-01 is `claim.`-scoped** → does *not* fire on ledger rows; three reviews misapplied it |
| Independently measured the defect | `status=accepted` 50 rows · `supports_claim=true` **60** rows (reviewers said 50 — the detector is disjunctive) · reviewer/verdict fields **0** · `validation_status` 0 |
| Determined the gate question | **G-LIT cannot pass at `ce42d205e761`** — HF-14 is `critical` and no L0 verdict at that hash can be accepted while it stands. Decided by the rubric, not by reviewer count |
| Ran the consumer audit rev-3 needed | No programmatic consumer reads L0 `status`/`supports_claim`: `audit_evidence.py` reads map node status; `check_acceptance.py` reads only `verification_status`; controller tools reference the ledger for hashing only. Only `class_separation.py` reads a claim-scoped L0 key, and it reads `conclusion_type`, untouched here |
| Executed bounded **L0 rev 3** closing HF-14 | `artifacts/literature/tools/l0_rev3_hf14_repair.py` — strictly claim-lowering, content-preserving, idempotent, dry-run by default. 50 status edits + 60 `supports_claim` withdrawals + 62 provenance additions |
| Verified the repair | 62 rows · 0 `status=accepted` · 0 `supports_claim=true` · 62 `review_status` · `unresolved` 62/62 · class tokens still exactly the frozen four · `class_separation.py` clean · `audit_evidence.py` unchanged (1 hard + 1 soft, both outside the ledger) |
| Archived the pre-rev-3 bytes | `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` = `ce42d205e761…` |
| Emitted the adjudication | `artifacts/literature/reviews/L0-rev3-adjudication-20260912T0035.md` |

## State at exit

| artifact | sha256 |
|---|---|
| `ledger/theorems.jsonl` (**rev 3**) | `3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6` |
| `ledger/citation_audit.csv` (unchanged) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/literature/tools/l0_rev3_hf14_repair.py` | `ae10111665523f327cc9e27160ea3be165f492a6798115fc2da9bf89b2638dcc` |
| `artifacts/literature/reviews/L0-rev3-hf14-repair.json` | `482444c7f47946a31e5f611d881dc90d6ad7cfeb531d2ceec67e055344701277` |
| `artifacts/literature/reviews/L0-rev3-adjudication-20260912T0035.md` | `2c3e7e44b0add9032312a75b701d0644b1bb4846374258d26bed8c587efb4c9e` |
| `artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl` | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |

- **Node status:** L0/L1 remain `active`, `validation_status: unverified`. **No completion claim, no gate verdict.**
- **All L0 verdicts at `ce42d205e761` are now VOID** by the hash move. Nothing is transferred or re-pinned.
  The hash move was unavoidable: HF-14 is critical, and any repair moves the hash.
- L1 and its 19 spot checks are **untouched**.

## Open items handed forward

1. **BL-7 (new, critical path):** L0 needs **re-review at `3e3d355314…`**. All prior L0 verdicts are void.
2. **BL-5 (new):** `conclusion_type` vocabulary collision — `class_separation.py:170`/`:198` reads it as an
   asserted conclusion surface, `PROTOCOL.md` rule 1 auto-rejects it without `artifact_refs`. Needs a
   **joint** A0 scope clarification + A1 key-list update + L0 rename in one hash cycle. A unilateral L0
   rename would silently remove 62 rows from A1 detection — refused on purpose.
3. **BL-6 (new):** HF-02 `class_ids` disjunction on 8 named rows (`D-004, D-005, T-303, T-305, T-402,
   T-515, T-526, T-528`; 6 C2+C0, 2 WCC+SCC) and **28 of 62 rows with no class binding** →
   class-binding metric **0.42** against A0's target of 1.0. Both require per-row source decisions, not a
   metadata pass. `class_separation.py` does not detect disjunction — an A1 coverage gap.
4. **BL-2:** HF-03 `source_meta` (0/62 ledger, 0/97 registry) — ~3 agent-hours of per-source reading.
5. **BL-4:** L1 `exact_locator` — 67/97 rows carry a search query or truncated URL. Needs a controller
   ruling on column semantics (query-provenance vs locator).
6. **BL-3 / ESC-3:** paywalled primaries (Christodoulou 1994/1999, Penrose 1969, Ringström 2009). Worker
   `web_search` fails 3/3; direct HTTPS works. **Human-PI escalation, open.** This is the binding
   constraint on evidence depth and is not clearable by more agent-hours in this group.
7. **Budget note:** the 3.0 h approved at pass 03 for two blind reviewers at `ce42d205e761`/`315c19145065`
   was never spent, and its stop rule voids those verdicts on a hash change. Re-requested for the new
   L0 hash (L1 target unchanged).

---

# AMENDMENT — same lifecycle, corrected outcome (supersedes §"State at exit")

The hand-patch recorded above was **not durable** and was superseded within this lifecycle.
`ledger/theorems.jsonl` is a **build product** of `artifacts/literature/theorems/batch-*.jsonl`;
`FREEZE-REV2.md` already forbade editing it directly. The A0 audit tool made this visible by
reporting HF-14 on 286 records across **15** files, including all nine build inputs.

## Corrected state at exit

| artifact | sha256 |
|---|---|
| `ledger/theorems.jsonl` (**rev 3, final**) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (unchanged) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/literature/tools/build_literature.py` (HF-14 guard) | `a497a968638f1e13183d853ab0518f458da885e5f7b1f0f3c647429ec039413c` |
| `artifacts/literature/tools/rev3_axis_split.py` | `d516ed62bd17b0597140bf48213a567a14db2b42f04912e2224f4252c39fde83` |
| `artifacts/literature/reviews/rev3-axis-split.json` | `95ce022ecbc5a25ddc98309694a85bf7653926c880910c079c6d4412c8d70109` |
| `artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl` | `3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6` |

- **Fix:** axes split at the source — `status` → `content_status` (`verified`/`provisional`/
  `unresolved`/`rejected`) + `review_status`; `supports_claim` → `author_asserts_supports`.
  Tier census preserved exactly (50/11/1). Collapsing tiers was rejected on evidence:
  `preprint + abstract-read` occurs in both tiers (6 vs 7), so `evidence_level` does not recover it.
- **Builder hardened:** rejects any theorem record carrying `status` / `validation_status` /
  `supports_claim`; stamps `review_status` on every emitted row.
- **Measured:** builder exit 0 (fail-closed) · 0 rows with `status`/`supports_claim`/`validation_status`
  · 62 `review_status` · 0 content-key diffs vs pre-rev3 · class tokens exactly the frozen four ·
  `check_acceptance.py` L0 62 PASS / L1 97/97 PASS · `class_separation.py` clean · `validate_map.py` VALID.
- **A0 audit effect:** HF-14 went from **15 files to 8**, and the canonical ledger plus all nine build
  inputs are clear. The remaining 8 are archives, the `incoming/` shard, and worker snapshots — see BL-8.
- **BL-7 target corrected:** re-dispatch L0 review at **`a1674f09…`**, not `3e3d355314…`.
  All verdicts at `ce42d205e761…` and at `3e3d355314…` are void.
