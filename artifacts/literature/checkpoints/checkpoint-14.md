# Checkpoint 14 — literature lifecycle L11 (L1 evidence-binding measured on the record anchor; one consolidated scope ruling requested)

- **At:** 2026-09-12T01:14+08:00 · **Actor:** `astra-lead-literature` (independent lifecycle, group `literature`)
- **Node:** L1 (with L0 cross-reference) · **Gate:** G-LIT · **Budget:** ~0.5 agent-hour of lead time;
  no subagents dispatched, no ledger or build-input write, no node promotion, no gate verdict.
- **One lifecycle, then exit.** No goal loop.

## Entry state (re-measured, not read from the map)

| artifact | sha256 | rows | bytes | mtime |
|---|---|---:|---:|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` | 62 | 151521 | 00:39:11 |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` | 97 | 102771 | 00:39:11 |
| `artifacts/literature/L0_L1_ACCEPTANCE.md` | `fde5600b45a58698d1cb4e625127bcd54952dc9eaf17a47449329cccc28806c5` | — | 727 | 00:39:14 |
| `research_map/class_separation.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` | — | 11457 | 01:08:14 |

- **Freeze held**, CF-19 not reopened: no write to either ledger, build inputs, or canonical
  artifacts. The live detector is the adjudicated `a8c04fc31e4a` (CF-29 mechanical restore
  confirmed read-only; no write by this lifecycle).
- Queue consumed: `python3 research_map/comms.py ingest` → 46 newly accepted events (mostly F2b
  revision traffic); 1 reject (`worker-075` claim, `invalid conclusion_type`) — not
  literature-owned.

## What this lifecycle did

| step | outcome |
|---|---|
| Re-measured the freeze | unchanged at L0 `a1674f09` / L1 `315c19145065`; hash-move holds untouched |
| Consumed the queue | ingest run; accepted stream +46 events |
| Read controller pass-07 | `G-LIT` stays pending per **REC-35** for two reasons: L0 divergent verdicts (2 accept vs 5 revise + 1 inconclusive, → `astra-life05-verify-l0-final`) **and** the live L1 locator revise (worker-025: 71/97 `exact_locator` values are not record locators) |
| Identified an ownership gap | the open L0 card is L0-only; **no open assignment adjudicates the L1 locator revise** (L11-L1-F4) |
| Independent read-only measurement | wrote and ran `artifacts/literature/reviews/l11_l1_locator_scope_audit.py` → machine record; deterministic, offline, re-runnable |
| Scope-decisive result | under controller ruling **REC-6** (“`evidence_url` is the locator column”), **L1 evidence binding is MET at the frozen hash**: 95/97 `evidence_url` are record-shaped, the other 2 rows (SRC-094, SRC-095) carry record-shaped `url`+`arxiv_id`; **0/97 rows lack a record anchor** |
| Defect confirmed, correctly scoped | `exact_locator` is a fetch trail for 67/97 rows (40 discovery query + 27 literally truncated with `...`); `L0_L1_ACCEPTANCE.md:18` is false for 67/97 — a **documentation defect on a non-binding column**, not HF-03 |
| HF-02 scope widened | the same rubric question also binds L1: 26 multi-class `class_mapping` rows (24 two-class + 2 three-class) + 8 dual-class L0 rows; 0 foreign class tokens on either surface |
| One ruling requested | `BL-7-consolidated`, covering both surfaces and the REC-6 column reading |

## Independent measurement (agreement and divergence with worker-025)

`exact_locator`: **30 record-shaped / 67 non-record** — 20 record pages, 10 record endpoints,
40 live API discovery queries, 27 truncated `...` URLs.

Worker-025 reports 26 record / 40 discovery query / 27 truncated / 4 metadata-or-other. The 27-row
malformed subclass and the 40-row discovery-query subclass reproduce **exactly**. The residual
difference is classification of 4 rows carrying `inspirehep.net/api/literature/<id>`: L11 counts a
record endpoint with an id as record-shaped, worker-025 classes them as metadata APIs. This is a
predicate difference, not a factual one, and it is reported as such.

`evidence_url`: **95 record-shaped / 2 absent / 0 non-record**. The two absent rows have
record-shaped `url`, `doi`, `arxiv_id`, and `exact_locator` (arXiv abs pages).

## Decision requested (one, consolidated, blocking G-LIT)

**BL-7-consolidated** — owner: controller + A0 (rubric owner), on the standing
`astra-life04-verify-a0` / REC-35 path.

1. Does rubric-literal **HF-02** (“disjunction of class_ids”, critical,
   `evaluation_rubric.yaml:175-180`) apply to ledger records at all, or only to claim objects? The
   detector text is written over claims; the ledger rows are citation/theorem records and the cards’
   acceptance criteria are citation/coverage criteria.
2. For L1: is the evidence-binding criterion read on the operative locator column
   (`evidence_url`, per REC-6) — in which case L1 is met at `315c19145065` and the 67-row
   `exact_locator` defect is post-accept metadata backlog — or on `exact_locator`, in which case L1
   is revise and worker-025’s staged 97/97 repair is the branch?

- **Out of scope** → record the ruling at rubric hash `d748a9e3574e`; correct
  `L0_L1_ACCEPTANCE.md:18` and annotate the column in one bounded metadata patch; no hash move; the
  23 spot checks stay valid. L0 remains governed by `astra-life05-verify-l0-final`.
- **In scope** → authorize worker-025’s staged repair; the hash move voids all pre-move L1
  verdicts, the two L0 accepts and the 23 spot checks; re-dispatch under CF-19.
- **Either way** → no ledger write while the ruling is open.

## State at exit

| artifact | sha256 |
|---|---|
| `artifacts/literature/reviews/l11_l1_locator_scope_audit.py` | recorded in outbox event `lit-l11-20260912-001` |
| `artifacts/literature/reviews/L1-locator-scope-L11-machine.json` | recorded in outbox event `lit-l11-20260912-002` |
| `reviews/L1-gate-adjudication-lead-literature-L11.json` | recorded in outbox event `lit-l11-20260912-003` |
| `artifacts/literature/checkpoints/checkpoint-14.md` | recorded in outbox event `lit-l11-20260912-004` |
| `ledger/theorems.jsonl` (**held, unchanged**) | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` (**held, unchanged**) | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |

## Handoff to the next literature lifecycle

1. **If BL-7-consolidated is ruled** → execute the corresponding branch, then re-pin. Do not
   re-derive the ruling. Out-of-scope: one bounded metadata patch (acceptance note + column
   annotation), no claim/class change. In-scope: adopt worker-025’s staged 97/97 repair, announce
   the hash, re-dispatch.
2. **If unruled** → do not re-run the accept census; the L0 count is stable and L0 is
   adjudication-bound. The L1 half now has a measured scope position (this checkpoint) and needs
   the ruling, not another census.
3. **Carry forward** BL-10 (controller review-scan undercount; L1 reads `[]` while 23 spot checks
   bind the hash) and BL-13 (worker-050 verdict scope).
4. **New since pass-07, not yet in controller coverage:** `w009-namedsrc-20260912T0116-review-01/02`
   (SRC-016, SRC-094 accepts) and worker-025’s `l1_identity_audit` report (0 title mismatches,
   95/97 resolved via ≥1 channel, 10 duplicate identifier groups, 19 author/year flags).
