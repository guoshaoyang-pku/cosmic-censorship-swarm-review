# Checkpoint 15 — literature lifecycle L12 (staged HF-02 repair independently re-derived: mechanically faithful, license-incomplete; BL-7 stays OPEN)

- **At:** 2026-09-12T01:19+08:00 · **Actor:** `astra-lead-literature` (independent lifecycle, group `literature`)
- **Node:** L0 (primary) with L1 cross-reference · **Gate:** G-LIT · **Budget:** ~0.5 agent-hour of lead
  time; no subagents dispatched, no ledger/build-input/canonical write, no node promotion, no gate verdict.
- **One lifecycle, then exit.** No goal loop.

## Entry state (re-measured this pass, not read from the map)

| artifact | sha256 (measured) | rows | mtime |
|---|---|---:|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` | 62 | 00:39:11 |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` | 97 | 00:39:11 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | — | 00:31:41 |
| `research_map/class_separation.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` | — | 01:08:14 |
| `evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` | — | — |
| `research_map/research_map.json` (cited) | `a2585ffc2152da9ada4a32ea10bc61bc…` | — | 01:16 |

- **Freeze held**, CF-19 not reopened: no write to either ledger, build inputs, or canonical artifacts.
- Taxonomy untouched (G-F0 at 7 accepts stays safe); detector at the adjudicated `a8c04fc31e4a` (CF-29 restore holds).
- Queue consumed: `python3 research_map/comms.py ingest` → **5 accepted**, 0 rejected, 7100 duplicates.

## What this lifecycle did

| step | outcome |
|---|---|
| Re-measured the freeze | unchanged at L0 `a1674f09` / L1 `315c19145065`; no hash move |
| Consumed the queue | ingest run; 5 new accepted events (literature-relevant: worker-099 HF-02 staged verify, worker-025 L1 identity audit) |
| Reviewed the new L1 evidence | `reviews/L1-identity-audit-025.json` (97-row identifier census: 0 mismatches, `hard_failures: []`, **not** a gate verdict) and the rewritten `reviews/L1-spotcheck-10.json` (accept 4.0, 8 rows, resolves worker-028's five PARTIALs; explicitly "does not move the gate") |
| Reviewed the new L0 evidence | `artifacts/worker-099/hf02_staged_adoption_verify/RESULTS.json` — non-author verification of the staged HF-02 repair (worker-025 `b3ab6a1a6357`); verdict **revise 3.0**, `counts_toward_gate_accept: false`, **BL-7 remains OPEN** |
| Independent read-only re-derivation | wrote and ran `artifacts/literature/reviews/l12_hf02_staged_rederive.py` → machine record `L12-hf02-staged-rederive.json`; offline, deterministic, re-runnable, no ledger or map write |
| Lead spot-check on L1 dedup | identifier-keyed duplicate groups re-counted; annotation state read |

## Independent re-derivation — 7/7 decisive counts reproduce

At the two pinned files only (`a1674f09` live vs `b3ab6a1a6357` staged), independently coded:

| quantity | live | staged | w099 reported | my re-derivation |
|---|---:|---:|---|---|
| rubric-literal HF-02 rows (`class_ids` ⊇ 2 frozen tokens) | **8** | **0** | 8 → 0 | matches |
| rows / order preserved | 62 | 62 | 62, order preserved | matches (`stage_id_seq` sha `bd32fd4bf806…`) |
| `class_ids == []` | **28** | **34** | 28 → 34 | matches |
| theorem-like unbound (`theorem`/`conditional_theorem`, empty `class_ids`) | **21** | **24** | 21 → 24 | matches |
| newly unbound rows | — | — | T-303, T-305, T-526 | matches exactly |
| changed rows / fields | — | — | 8 rows; `class_ids`/`informs_classes`/`ledger_tags` only | matches: `class_ids` 8, `informs_classes` 8, `ledger_tags` 6 |

The 8 HF-02 rows are `D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528`. Pins verified:
staged `b3ab6a1a6357…` and instrument/`RESULTS.json` `33cfcd5d8d67…` both measure as declared.

## Two findings the re-derivation adds (both predicate-scoped, neither a gate verdict)

1. **R6 predicate divergence, direction-identical.** Under a re-implementation of the pinned
   `R6_self_declared_scope` predicate, the staged repair removes **every** self-declared-scope
   contradiction inside the 8-row HF-02 population — but my stricter transcription scores the live
   population **7/8**, not w099's 8/8. The single difference is **T-528**, whose disclaimer reads
   *"Does not **by itself** prove C^0 SCC false"*: my regex requires the verb adjacent to the
   negator, w099's evidently allows the intervening adverb. This is a predicate-coverage difference,
   not a factual disagreement (staged T-528 `class_ids` `[AF-WCC-VAC-GEN]` clears the disjunction
   either way). Recorded so the gate binder cites a predicate, not a bare count.
2. **The repair is not population-complete under its own predicate.** Applied to all 62 rows, the
   same R6 predicate fires on **14 rows live → 7 rows staged**; the 7 survivors (`T-201…T-205`,
   `T-301`, `T-302`) lie **outside** worker-023's 8-row disposition set and are untouched. Whether
   they are defects is *the same pending HF-02 scope question* — but if the ruling goes against
   class binding on self-disclaimer grounds, the staged repair fixes 8 of 15 rows, not all of them.
   Stated as measurement, not as an accusation against the repair.

## L1-side lead spot-check (bounded)

`ledger/citation_audit.csv` has **10 identifier-keyed duplicate groups** (6 DOI + 4 arXiv),
reproducing `reviews/L1-identity-audit-025.json`'s `duplicate_identifier_groups: 10` exactly.
**10/10 are annotated mirror pairs** — every duplicate row carries `mirror_of` pointing at a primary
(SRC-002, SRC-020, SRC-021, SRC-023, SRC-024, SRC-033, SRC-057, SRC-059, SRC-066; SRC-060 and
SRC-072 are two mirrors of SRC-020). This closes the **identifier-keyed** subset of the
citation-integrity "unannotated duplicate clusters" hard failure. It is not a title-level dedup
census and does not claim one.

## Gate position (unchanged by design)

**G-LIT stays pending.** Nothing this lifecycle measured is a gate verdict, and I did not set one.
What is now stronger: L1 evidence binding (95/97 record-shaped `evidence_url` under REC-6; +1 bound
re-fetch spot check; a full 97-row identifier census with 0 mismatches). What still blocks:

- **L0 verdict split unadjudicated** — 2 accept / 5 revise / 1 inconclusive at `a1674f09`; the
  adjudication is owned by `astra-life05-verify-l0-final` (lead-audit, artifact
  `reviews/L0-review-final-verify.json`, deadline 02:30). No pass-08 ruling exists; my pass-08 read
  confirms it is still open.
- **One HF-02 scope ruling** (BL-7) — does rubric-literal HF-02 (`evaluation_rubric.yaml:175-180`)
  apply to ledger `class_ids` arrays, and for L1 does the binding criterion read on `evidence_url`
  per REC-6. No pass-08 decision (REC-36…REC-42) addresses it.
- **`exact_locator` remains a non-binding documentation defect** on 67/97 rows; `L0_L1_ACCEPTANCE.md:18`
  is still false for those rows.

## Blocker emitted

`BL-7-consolidated` (updated, still gate-blocking): the one ruling is still unanswered, and the only
remedy candidate now on the table has been independently measured as **license-incomplete**
(T-526 `NEEDS_F1_RULING`; adopting it empties `class_ids` on 6 more rows and adds 3 theorem-like
unbound rows, so it trades an HF-02 firing-set violation for a G-LIT scope-match violation). Adoption
also moves the L0 hash, which under CF-19 voids every L0 verdict bound to `a1674f09` and opens a new
review round. Request stands: **one controller/A0 ruling on the HF-02 scope**, recorded at rubric
`d748a9e3574e`.

## Authority and compliance

- No gate verdict, no node `status=done`, no `validation_status=passed`, no ledger/map/taxonomy/
  detector write; freeze at L0 `a1674f09` / L1 `315c19145065` held byte-stable through the pass.
- All counts above are read-only re-derivations from pinned bytes; the instrument is deterministic
  and offline (`python3 artifacts/literature/reviews/l12_hf02_staged_rederive.py`).
- No self-review promoted: worker-099's verdict is evidence, cited as evidence.

## Handoff for the next literature lifecycle

1. Re-measure both pins first; any move voids this record.
2. Watch `astra-life05-verify-l0-final` (due 02:30) — that adjudication, plus one HF-02 scope ruling,
   is the whole distance to an adjudicable G-LIT.
3. If a ruling admits a ledger revision: the staged candidate `b3ab6a1a6357` is mechanically faithful
   (8/8, order preserved, 3 fields) but needs the T-526 licence resolved and the 7 residual
   R6 rows dispositioned before it can be called complete.
