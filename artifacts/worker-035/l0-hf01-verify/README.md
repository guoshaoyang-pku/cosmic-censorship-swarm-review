# W035-L0-HF01-VERIFY-01 — independent verification of the L0 HF-01 repair proposal

Worker: `worker-035` (bounded execution worker). Node: `L0`. Gate: `G-LIT`.
Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.

## What is being verified

`artifacts/worker-007/l0_hf01_artifact_refs/` proposes a fix for the A0 HF-01
(`fluent_text_promotion`) hard failure on `ledger/theorems.jsonl`: 30 rows carry
`conclusion_type == "theorem"` while the frozen row schema has no `artifact_refs`
field at all. The proposal supplies a machine-applicable patch that adds
class-bound `artifact_refs` to those 30 rows, plus a generator and a self-report.

`reviews/L0-review-lead-audit-r2.json` and `reviews/L0-review-21/22.json` record
the repair path as **not reviewed**. This is that review, done with an independent
implementation.

## Method

`verify_hf01_proposal.py` re-parses every input from bytes and re-implements the
checks independently of the proposal generator (the generator is executed only
for the determinism control, into a throwaway directory).

Checks P1–P16:

| id | check |
|---|---|
| P1 | proposal input pins equal measured bytes |
| P2 | proposal/patch/canonical hashes match the verification record |
| P3 | row count and order preserved; 30 theorem + 32 other rows |
| P4 | patch is minimal — only `artifact_refs` added, all other keys identical |
| P4b | patch refs equal the proposal's per-row refs |
| P5 | canonical ledger lines are in canonical (sort_keys) form |
| P6 | ref coverage equals `source_ids` × evidence-file presence |
| P7 | every ref path exists, hash-matches, and is not self-referential |
| P8 | every `path:line` locator resolves to the cited source record |
| P9 | ref metadata fields equal the cited record's fields |
| P10 | all `class_ids` stay inside the frozen four |
| P11 | HF-01 (as read) fires on 30 rows before, 0 after |
| P12 | HF-14 residual measured (not repaired by this patch) |
| P13 | the proposal's self-reported metrics recompute |
| P14 | generator is deterministic on the pinned inputs |
| P15 | canonical ledger byte-unchanged across verification |
| P16 | `ledger_line` anchors resolve to the right canonical rows |

Adversarial controls M1–M7 mutate the proposal and the patch in memory and require
the named check to flip to fail: dropped refs, corrupted ref hash, edited
non-theorem row, class leak, bad locator, dropped row field, extra ref. The null
control (unmutated input) must pass every check.

## Result (pinned hashes)

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72` |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `artifacts/literature/registry.jsonl` | `ea02d1943fda50e5e1c7ce10fe2a1cd6e7784a2c9f2467c7cb8597c63442652d` |
| proposal | `893556c6fb289b6b1a8c9c152ad1c49a3c374f3ec01ad4891fcf285c4954a2de` |
| proposed ledger (patch) | `dad1ccc169beec01aa4c38df844c940460544cc31e983d204542b92d771b9048` |

17/17 checks pass, 8/8 controls pass: 148 refs and 148 locators verified, patch
minimal and deterministic, HF-01 fires 30 → 0 under the rubric's stated reading,
canonical ledger byte-unchanged.

## Conditional scope (does not travel as an accept)

- Whether HF-01 applies to *ledger rows* at all is an open adjudication owned by
  `astra-lead-audit`; this report verifies the proposal **against the stated
  detector reading** and does not decide applicability.
- HF-14 (`self_certified_acceptance`) is **not** repaired: 50 rows remain
  accepted/supporting with no reviewer or verdict field. G-LIT's L0 criterion
  still needs that adjudication or a separate repair.
- The refs are locator/provenance pins; they do not upgrade any
  `verification_status` and do not establish citation support.

## Non-claims

Not a gate verdict; cannot pass G-LIT or move L0. The canonical ledger and every
other canonical artifact were only read. The patch was not applied. Fluent text is
not promoted: all claims above are recomputable from the files in this directory.
