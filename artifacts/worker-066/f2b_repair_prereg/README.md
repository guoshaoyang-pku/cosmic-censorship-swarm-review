# W066-F2B-REPAIR-PREREG-01 — pre-registered repair-acceptance harness for F2b

Bounded worker-066 lifecycle, 2026-09-12. Node **F2b**, class **AF-SCC-C0-VAC-GEN**
(siblings referenced: AF-SCC-C2-VAC-GEN, AF-WCC-VAC-GEN). No canonical artifact was written
and no node/gate status was moved.

## Why this task

worker-066's prior lifecycle (`W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01`, verdict
`revise 2.5`, hard failures `W066-R12-F2B-H1`/`H2`) confirmed two live text-level defects in
`schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda` (rev12) and named a minimal 2-edit repair
(candidate semantics `98f9ec83`). The open blocker says: publish an equivalent repair, bump,
re-freeze, re-run a containment check to PASS. The owner is `lead-formulation`; workers may
not edit canonical paths. This task turns the blocker into a **pre-registered, re-runnable
acceptance gate** plus a ready-to-apply proposal patch, so the repair can be adjudicated in
one command when it lands. It also performs the first family-wide sweep for the same defect
kinds in the two sibling schemas.

No assignment card existed in `comms/inbox/worker-066.jsonl`; the task is proposed and
artifact-backed per the worker contract (worker events cannot move nodes or gates).

## Defect kinds under test (re-implemented, not copied)

- **`size_premise_inverted`** — a `forbidden_transfers` reason asserts a size/containment
  relation contradicting the file's own declared extension-class chain.
- **`false_containment_denial`** — a *live* `must_not_conflate` clause denies containment
  while the same file declares it. Quoted/withdrawn copies inside bracketed corrections
  (e.g. `[R2 major: the earlier 'no containment ...' was wrong]`) do not count; the checker
  strips bracket spans and `'...' was wrong` fragments before scanning.

The checker (`prereg.py`) parses the declared chain from
`implication_ledger.extension_class_containment` (both `contains`-descending and
`subset of`-ascending forms), re-derives set-size ranks, checks every entailment and
forbidden-transfer row for licensing against those ranks, checks each explicit
"strictly larger/smaller extension class" premise against the ranks, and sweeps for live
denials. It is a fresh implementation; worker-008's `audit_candidate_rev12.py` is used only
as an external cross-check, never as the instrument.

## Pinned inputs

| key | path | sha256 |
|---|---|---|
| c0_live | `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda` (rev12) |
| c2_live | `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc` (rev12) |
| f1_live | `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` (rev12) |
| candidate | `artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml` | `98f9ec83c487` |

Byte copies of all four pins are in `pinned/`; `evidence/pins.json` records bytes and mtimes.
Any pin move aborts the run with exit 2 (`blocked_pin_drift`). All four pins were re-measured
after the run: unchanged.

## Results

| run | finding kinds | expected |
|---|---|---|
| live C0 rev12 `55d0a1ea` | `size_premise_inverted`, `false_containment_denial` | fail (both) |
| reference candidate `98f9ec83` | none | clean |
| sibling C2 rev12 `5476a3f2` | none | clean |
| sibling F1 rev12 `cce9c601` | none | clean |

The proposal patch (`proposed_patch.diff`) is exactly two hunks:

1. `implication_ledger.forbidden_transfers[0].reason`: "strictly **larger** extension class"
   → "strictly **smaller** extension class (E_C2 subset of E_C0)" (line 245).
2. `regularity.must_not_conflate[0]`: live denial → the nesting statement plus the H2_loc
   entailment, with the earlier denial recorded as wrong (line 151).

Re-applying those two edits to the live bytes reproduces the reference candidate's sha256
`98f9ec83c487` exactly. The patch is a **proposal**: canonical writes belong to the owner.

## Controls (pre-registered, 10/10 matched)

| id | control | expected → observed |
|---|---|---|
| C1 | pristine live rev12 | both defects → both |
| C2 | reference candidate | clean → clean |
| C3 | candidate with H1 edit reverted | `size_premise_inverted` → same |
| C4 | candidate with H2 edit reverted | `false_containment_denial` → same |
| C5 | candidate with a still-inverted H1 premise (opposite claim) | `size_premise_inverted` → same |
| C6 | candidate with the denial re-inserted live | `false_containment_denial` → same |
| C7 | candidate with the declared chain direction reversed | 3 kinds (entailment/forbidden/size) → same |
| C8 | sibling C2 | clean → clean |
| C9 | sibling F1 | clean → clean |
| C10 | gutted file (no chain) | `chain_missing` → same (checker is non-vacuous) |

## Acceptance / definition of done

`report.json.acceptance` is all-true only when live rev12 fails with exactly the two defect
kinds, the reference candidate is clean, both siblings are clean, and all controls match:
`prereg_ready_live_FAILS_candidate_PASSES`.

When the owner publishes the repair (revision bump + mirror + re-freeze), re-run
`python3 artifacts/worker-066/f2b_repair_prereg/prereg.py`: acceptance then requires the
live file to be clean, with C2 `5476a3f2` unchanged, all controls still matching, and the
harness re-pinned to the new revision.

## Limits / not claimed

- This is a text-consistency and binding instrument, **not** a full-schema review and **not**
  a claim about the mathematics of C0/C2 inextendibility.
- It does not edit canonical artifacts, set node status, or move gates (worker authority).
- C2/F1 "clean" means clean **for these two defect kinds at these pins only**; the in-flight
  blind rev27 reviews (workers 015/035/046/091/071/085) remain the class-coverage instrument.
- The H2 detection rule deliberately ignores bracketed/quoted-withdrawn denials; a denial
  phrased without the literal "no containment" would be a documented blind spot.

## Falsifier

Re-run `prereg.py` on the same pins. This report is falsified if live `55d0a1ea` does not
yield exactly the two defect kinds, or the reference candidate `98f9ec83` produces any
finding, or any control departs from its pre-registered expectation, or a third instance of
the two defect kinds appears in C2/F1 at their pins, or re-applying the two edits to live
does not reproduce `98f9ec83`, or any pinned byte moves mid-run.

## Files

| file | role |
|---|---|
| `prereg.py` | fresh checker + controls + proposal generator (re-runnable) |
| `proposed_patch.diff` | exact 2-edit proposal against live `55d0a1ea` |
| `evidence/pins.json` | pin measurements (bytes, mtime, match) |
| `evidence/checks.json` | primary runs + acceptance booleans |
| `evidence/controls.json` | 10 pre-registered controls, expected vs observed |
| `evidence/sibling_scan.json` | C2/F1 premise and denial sweeps |
| `report.json` | verdict, proposal, definition of done, falsifier |
| `CHECKPOINT.json` | artifact hashes + next falsifier |
