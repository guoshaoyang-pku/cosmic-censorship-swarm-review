# L0 rev-2 finding disposition — three revise verdicts vs `ce42d205e761`

- **Frozen revision under assessment:** `ledger/theorems.jsonl` = `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72`
  (62 rows), `ledger/citation_audit.csv` = `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` (97 rows).
- **Prior verdicts are pinned to `5fb8bf3a3d14…`** (rev 1): `lead-audit` revise 3.0, `deepseek-flash-16` revise 3.5,
  `deepseek-flash-17` revise 2.5. None binds to the current hash. This document is the lead's *self*-assessment of
  what rev 2 changed; it is **not** an independent verdict and does not accept anything.
- **Instruction followed:** freeze-first. The revision was not rewritten again (see "Why no rev 3 in this pass").

## A. flash-17 (revise 2.5) — `reviews/L0-review-17.json`

| # | finding | state at `ce42d205` | evidence |
|---|---|---|---|
| 1 | **HF-01** 30 rows `conclusion_type=theorem` with no `artifact_refs` | **OPEN (deliberate)** — still 30 rows, field still absent | `grep -c` on L0; rubric detector is claim-scoped (`evaluation_rubric.yaml:174`: `claim.conclusion_type == theorem AND (no artifact_refs …)`), so no HF-01 fires against ledger rows, but the vocabulary collision is real |
| 2 | 4 entries `accepted` with `verification_status='unverified'` | **FIXED** — 0 at this hash; the remaining `unverified` row (D-009) is `provisional` | cross-join §D below |
| 3 | Evidence depth: 45/49 accepted are `abstract-read`; 30 accepted cite only `verified-api` | **PARTIALLY ADDRESSED / inherent** — 61 `abstract-read`, 1 `unverified`; L1 evidence types 84 abstract / 12 metadata / 1 full-text. `abstract-read` is explicitly allowed by the G-LIT acceptance list; paywalled bodies are the binding constraint | `artifacts/literature/L0_L1_ACCEPTANCE.md`; blocker BL-2 |
| 4 | Registry independence nominal; Kish ESS ≈ 1 | **UNCHANGED** — every audit row still carries `reviewer=lead-literature`/`astra-lead-literature` | `citation_audit.csv` reviewer column; fixed only by an independent review pass, not by editing |
| 5 | Reviewed hash ≠ assignment-pinned hash | **SUPERSEDED** — this lifecycle binds to the measured hash; the falsifier is a moving-target process defect recorded in `reviews/A1-rebind-coverage.md` §7 | `reviews/A1-rebind-coverage.md` |
| 6 | D-009 metadata-only, provisional | **CORRECT, no action** | D-009 `unverified` + `provisional`, 2 metadata sources |

## B. lead-audit (revise 3.0) — `reviews/L0-review-lead-audit.json`

| # | finding | state at `ce42d205` | evidence |
|---|---|---|---|
| 1 | **HF-03** `source_meta` (matter_model, cosmological_constant, dimension, symmetry, formulation) absent | **OPEN (deliberate, rev-3 backlog)** — 0 of 97 registry rows and 0 of 62 ledger rows carry `source_meta` | `artifacts/literature/registry.jsonl` key census |
| 2 | **HF-02** non-class token `DEFINITIONS` in `class_ids` (8 entries) | **FIXED** — `DEFINITIONS` is in `ledger_tags` on 9 rows, in `class_ids` on 0 | L0 key census; `audit_evidence.py` reports no literature finding |
| 3 | 24 `source_ids` do not resolve in the registry | **FIXED** — 0 unresolved references; every `source_id` in all 62 rows resolves in both the registry (97) and the audit (97) | resolution cross-join |
| 4 | Duplication: 11 near-duplicate title pairs across five ledger files | **ADDRESSED for the canonical pair** — one canonical L0 and one canonical L1; duplicate *anchors* now carry `mirror_of` (13 rows). Worker shard files remain on disk as non-canonical history | `citation_audit.csv#mirror_of`; `ledger/citation_audit_{wcc_flash-08,scc_flash-09}*` |
| 5 | Coverage: no Christodoulou 1999 bound to `AF-WCC-SCALAR-SPH`; no Luk-Oh I/II bound to `AF-SCC-C2-VAC-GEN`; no Kerr/Schwarzschild exterior stability entry | **ADDRESSED WITH A SCOPE CORRECTION** — T-101 (Christodoulou 1999) is class-bound to `AF-WCC-SCALAR-SPH`; Kerr/Schwarzschild stability is bound to `AF-WCC-VAC-GEN` (T-204, T-205, T-206, T-515, T-528). Luk-Oh I/II (T-514) and Gowdy (T-520) exist but are **deliberately tag-only** (`C2`, `OTHER-MODELS`): they are matter-model / T³-Gowdy results, so binding them to `AF-SCC-C2-VAC-GEN` would be class leakage (HF-02). The absence of a discharging theorem for the vacuum class is recorded as a **state-of-field finding in T-401**, not hidden | T-101/T-514/T-520/T-401 rows; tags |
| 6–8 | POSITIVE notes (honest `unresolved.jsonl`, publication status, exclusions; 14/14 spot checks) | **RETAINED** | `artifacts/literature/unresolved.jsonl` |

## C. flash-16 (revise 3.5, conditional on T-301) — `reviews/L0-conditional-review-16.json`

| # | finding | state at `ce42d205` | evidence |
|---|---|---|---|
| 1 | T-301 class binding to `AF-SCC-C0-VAC-GEN` unsupported as stated; needs interior/local binding or explicit ingredient + transfer obligation | **PARTIALLY ADDRESSED** — T-301 is now `conclusion_type=conditional_theorem`, labelled "conditional refutation"; `does_not_imply` states it "does not settle AF-SCC-C0-VAC-GEN for all generic AF vacuum data, because the data assumptions are interior"; `scope_caveats` records the missing retrieval paper. Residual: `class_ids` still binds the class and it is not moved to `informs_classes`, so a strict reviewer may still ask for reclassification | T-301 row fields |
| 2 | Statement drops the source's "appropriate" qualifier | **ADDRESSED** — `statement_exact` retains "(representing the geometry just inside the event horizon)" and `assumptions` lists "Data represent the expected geometry just inside the event horizon"; live abstract re-verified 2026-09-12 (SRC-004 pass) | T-301; `L1-spotcheck-rev2.json` |

## D. Assignment acceptance — `astra-life01-l0-revise`

| acceptance criterion | state | evidence |
|---|---|---|
| every `class_ids` token is one of the frozen four or explicitly tagged non-class | **MET** — 49 class tokens across `class_ids`+`informs_classes`, all four frozen values; 0 extension tokens; `DEFINITIONS`, `WCC-STATEMENT`, `OTHER-MODELS`, … are `ledger_tags` | token census |
| every unresolved citation is marked unresolved with what would resolve it | **MET** — 62/62 rows carry a non-empty `unresolved` list naming the resolving action | L0 `unresolved` field |
| `>=3` independent re-fetch spot checks bind to the new ledger hash | **MET this lifecycle** — 4 independent (separate agent, no ledger access) + 4 lead corroborating re-fetches + 2 Crossref DOI corroborations, all bound to `ce42d205`/`315c1914`; 0 contradictions | `artifacts/literature/reviews/L1-spotcheck-rev2.json` |
| **assignment falsifier:** `audit_evidence.py` reports CLASSSEP-SOFT extension tokens, or a row's `verification_status` overstates its locator evidence | **DOES NOT FIRE** — no literature class-token finding; 0 verification_status overstatements across all 62 rows | falsifier cross-join below |

## E. `astra-indep-1-L0-L1-literature` (older card) — residual

| item | state |
|---|---|
| source_meta scope fields | **NOT MET** — rev-3 backlog, deliberately deferred (see below) |
| replace self-certified accepted records with reviewer verdicts | **PARTIAL** — reviewer identity is now recorded per audit row (`lead-literature` 92 / `astra-lead-literature` 5); independent verdicts at the frozen hash still absent → blocker BL-1 |
| relabel invented class tokens | **MET** |
| merge and dedupe ledger files | **MET for canonical**; shard history retained |
| record the C2 no-primary-theorem blocker as a map-level state-of-field finding | **MET at map level** — `research_map.json` `claims[33]` and literature node blockers cite `ledger/theorems.jsonl#T-401`; T-401 is the ledger's state-of-field statement |
| four citation-integrity hard failures fixed or marked unresolved | **MET** — C-1 SRC-041 split/relabelled, C-2 SRC-050 pages fixed, C-3 SRC-025 year fixed, C-4 SRC-011 annotated; dispositions in `artifacts/literature/reviews/lead-adjudication.md` §C |

## F. Falsifier cross-join (the one the assignment names)

For every L0 row, its `verification_status` was compared against the `evidence_type` of every source in
`source_ids`: **0 rows** claim `abstract-read`/`full-text`/`page-checked` without at least one
abstract-or-full-text source; **0 accepted rows** rest on metadata only; the single `unverified` row is
`provisional`. The falsifier does not fire.

## G. Why no rev 3 in this pass (and what it would contain)

`reviews/A1-rebind-coverage.md` §1–2 documents the actual failure mode on this project: artifacts were
rewritten faster than a review round could complete, so *no* verdict binds to any current hash, on any
node. Rewriting L0 again to close HF-01/HF-03 would repeat that pattern and keep G-LIT unjudgeable.

**Therefore this lifecycle freezes `ce42d205`/`315c1914` and requests blind review at those hashes.**
The two remaining major findings are recorded as a **rev-3 backlog to be executed only after the frozen
hash is reviewed**, with a bounded scope:

1. `source_meta` on all 97 source records (per-source matter model, Λ, dimension, symmetry, formulation) —
   requires a per-source read; ~3 agent-hours; moves the hash.
2. `conclusion_type` vocabulary collision — either add per-row source `artifact_refs` or rename the field to
   `mathematical_result_kind` and update its consumers; needs a consumer audit first.
3. Metadata annotations: SRC-058 "194 pp" uncorroborated; SRC-069 title-spelling variant; SRC-016/SRC-069
   non-reproducible `exact_locator` (replace with the record URL).
4. Optional: move T-301 to `informs_classes` if the formulation lead rules the interior data class is an
   ingredient rather than a member.

None of items 1–4 changes a claim or a class binding; all are metadata/hygiene. Item 3 is cheap and could be
done without a full rev 3 if the controller prefers a metadata-only patch **before** review — the lead
recommends against it for the moving-target reason above.
