# W079-L0-HF02-STAGED-REPAIR-VERIFY-01 — pre-registration

- **Worker**: worker-079 (no assignment card exists in `comms/inbox/worker-079.jsonl`; task self-selected from the open G-LIT blocker `lit-l8-20260912-006`, which names the 8-row HF-02 disjunction as "the single gate-deciding question for the L0 half of G-LIT at the unchanged hash a1674f094979").
- **Written before the harness was run** at 2026-09-12T01:09+08:00.
- **Class bound**: `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-VAC-GEN` (the three classes carried by the 8 rows). Node L0, gate G-LIT.
- **Authority**: worker-level completion claim and review verdict only. This task does **not** edit any canonical path, does **not** set a node `done`, `validation_status=passed`, or a gate verdict, and does **not** rule on whether rubric HF-02's disjunction clause applies to ledger `class_ids` arrays (that scope ruling is the audit lead's, per `w025-20260912T004950-l0hf02-blocker`).

## Object under test

Non-canonical staged candidate authored by worker-025 (I am not an author of it, nor of worker-023's proposed patch, nor of any live ledger row):

- live anchor: `ledger/theorems.jsonl` sha256 `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
- staged candidate: `artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl` sha256 `b3ab6a1a635720a97e51fd332bcf1d9f9e6fdc45ad64d886106f1cd298d61cea`
- rubric pin: `evaluation_rubric.yaml` sha256 `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` (HF-02 detector text: `unknown class_id | disjunction of class_ids | ...`)
  - **Correction 01 (before first successful run):** the pin was first written with 63 hex chars (a dropped `c` at `…815371|6dcf…`). Two harness runs aborted with exit 2 and wrote no report — the fail-closed pin gate fired on my own typo. Pin corrected to the measured 64-char value above; no pre-registered expectation or control was changed.
- class vocabulary pins: `research_map/formulation_taxonomy.yaml` `0abb9ed8a961…`, `schemas/taxonomy_cases.jsonl` `ccf7041b0dff…`

Claim already on record and tested here: worker-025's `w025-20260912T004950-l0hf02-*` events assert the 8 rows `D-004, D-005, T-303, T-305, T-402, T-515, T-526, T-528` are the only literal HF-02 disjunction firings at the live anchor, and that the staged candidate clears them while changing only `class_ids`, `informs_classes`, `ledger_tags`.

## Pre-registered expectations (E1–E11)

All are evaluated against the pinned bytes; any pin drift aborts with exit 2 and writes no report.

- **E1** both files parse as JSONL: live 62 rows, staged 62 rows, identical `theorem_id` sequence, no duplicates.
- **E2** the live literal-disjunction set (rows whose `class_ids` contains ≥2 distinct frozen class tokens) equals the declared 8 exactly.
- **E3** the staged literal-disjunction set is empty.
- **E4** for every row, the deep JSON difference between live and staged is confined to `{class_ids, informs_classes, ledger_tags}`; `informs_classes` may be absent live and present staged; every other field is deep-equal.
- **E5** the set of rows with any changed patchable field is exactly the declared 8; no ninth row changes.
- **E6** every class token in staged `class_ids` and `informs_classes` is one of the four frozen ids; `class_ids ∩ informs_classes = ∅` per row; both fields are lists of strings.
- **E7** per changed row: staged `class_ids` ⊆ live `class_ids`; staged `informs_classes` ⊆ live `class_ids`; live `class_ids` has exactly 2 frozen tokens; no token outside live `class_ids` is introduced. Tokens dropped without replacement are reported (semantic question, see non-claims).
- **E8** unchanged rows are deep-equal on every key including patchable ones (no incidental edits).
- **E9** staged `ledger_tags` per changed row is a superset of the live list preserving the live order as a prefix (append-only tags).
- **E10** staged `class_ids` is non-empty on the two WCC rows and empty-or-single on the six SCC rows, with no row left with an empty union of `class_ids ∪ informs_classes` (no informationless row).
- **E11** re-running the harness on the same pins yields a byte-identical report (`report_sha256` stable).

## Controls (must all be detected, else exit 3 and no report)

Mutants are built in memory only; no mutant is written to disk.

- **C1** reintroduce a two-frozen-token `class_ids` on one row → E2/E3 detector must fire.
- **C2** tamper `statement_exact` on one unchanged row → E4 scope check must fire.
- **C3** drop one row → E1 must fire.
- **C4** replace a frozen token with a foreign token → E6 must fire.
- **C5** add a change to a ninth, previously unchanged row → E5 must fire.
- **C6** swap the live file for the staged file (zero live firings) → E2 baseline must fire.

## Verdict rule

- exit 0 `CANDIDATE_VERIFIED` iff E1–E11 hold and C1–C6 all fire.
- exit 1 `CANDIDATE_REJECTED` (report written, failures listed) if any E fails.
- exit 2 no report on pin drift; exit 3 no report if any control is missed.

## Falsifier

At the pinned live hash `a1674f094979` and staged hash `b3ab6a1a6357`: any ninth row with a two-frozen-token `class_ids`, any staged row whose non-patchable fields differ from live, any foreign class token or per-row `class_ids ∩ informs_classes ≠ ∅` in the staged file, a staged disjunction set that is not empty, or a pin drift (either hash changing) falsifies this verification. A semantic demonstration that a staged `informs_classes` assignment names the wrong sibling class would falsify the *mapping*, not the mechanical claims, and is explicitly outside this verdict.

## Non-claims (documented blind spots)

1. I do not rule on whether HF-02's "disjunction of class_ids" clause applies to `theorem`-ledger rows; the candidate is verified as a mechanical repair of the literal firing, conditional on that scope ruling.
2. I do not certify the per-row semantic choice of which sibling class a row informs; I report the full mapping table for the audit lead.
3. I do not certify the mathematical content of any row, and my verdict is not a per-row independent review of the 62 theorems.
4. `reviews/L0-review-worker-079.json` (accept 4.0 at the live hash) checked class tokens for foreignness but did not check the disjunction axis; this task closes that gap in my own prior review and does not supersede it.
