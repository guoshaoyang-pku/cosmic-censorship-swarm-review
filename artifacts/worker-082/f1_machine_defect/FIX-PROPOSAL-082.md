# FIX-PROPOSAL-082 — F1 machine defects at sha256 9a8bd4c96800

**Status:** advisory only. Worker-082 does not edit canonical artifacts; the canonical path has one owner
(CF-12), here `lead-formulation`. This file exists so the owner can apply a mechanical fix without
re-deriving the defects. Evidence: `evidence.json` (sha256 `ed90d9a9dc4c…`), checker `run_checks.py`
(sha256 `296eda8a5240…`), frozen bytes `frozen_f1_9a8bd4c96800.yaml` (sha256 `9a8bd4c96800…`).

Apply in the authoring source of record, then publish byte-identically so `schemas/af_wcc_vacuum.yaml`
carries the new bytes; confirm both trees hash equal before requesting re-review.

## 1. Collapse the duplicate `revised_at` timeline (W082M-02/03/04)

Lines 7–28 currently contain **seven** `revised_at` scalars (lines 8, 10, 12, 14, 16, 20, 23) and **two**
`revised_at_unused` scalars (lines 26, 28), interleaved with the per-revision comments. Every YAML load
keeps only the last value (`2026-09-12T00:30:00+08:00`) and silently discards the other six stamps, so
`revision: 11` (line 30) cannot be checked against the file.

Replace the whole block with one `revised_at` scalar plus an explicit list. Recovered values in document
order (note: the comments precede the value they describe; rev8/rev11 placement is **ambiguous in the
current bytes and must be resolved by the author**, which is itself a symptom of the defect):

```yaml
revised_at: "<the true wall-clock time of this edit, <= now>"   # do NOT future-date
revision_timeline:
  - {at: "2026-09-11T23:30:35+08:00", line_was: 28, comment: "rev3 delta: AMB-07 membership_ruling, AMB-09 ambient_space_is_data_space, vocabulary alias ref, adjudication ref"}
  - {at: "2026-09-11T23:32:53+08:00", line_was: 26, comment: "rev8 delta: explicit F0 hash binding (flash-17 blocker accepted)"}
  - {at: "2026-09-11T23:34:10+08:00", line_was: 8,  comment: "unlabelled in current bytes"}
  - {at: "2026-09-11T23:37:51+08:00", line_was: 10, comment: "rev4 delta: explicit symmetry slot"}
  - {at: "2026-09-11T23:42:45+08:00", line_was: 12, comment: "rev5 delta: R1 review corrections (falsifier logic, visibility equivalence, genericity well-definedness, transfer witnesses)"}
  - {at: "2026-09-11T23:46:17+08:00", line_was: 14, comment: "rev6 delta: R2 corrections (transfer container split, dense_escape strength, containment chain)"}
  - {at: "2026-09-11T23:51:53+08:00", line_was: 16, comment: "rev7 delta: L1 verified-ledger integration (status signals, class-identity variants, scope caveats)"}
  - {at: "2026-09-12T00:15:00+08:00", line_was: 20, comment: "rev9 delta (astra-classscope-02): ONE canonical visibility predicate (single-q tail)"}
  - {at: "2026-09-12T00:30:00+08:00", line_was: 23, comment: "labelled rev10 in the preceding comment; the 00:30 stamp is future-dated and must be replaced by the real edit time"}
  - {at: "<real time>",              line_was: 24, comment: "rev11 delta: variant delta-filename references normalized; f0_binding re-checked"}
```

Delete `revised_at_unused` entirely; the name states it has no reader and it cannot carry the lost stamps.

## 2. Clock discipline (W082M-05)

`f0_binding.checked_at` (line 311) and the effective `revised_at` were both `2026-09-12T00:30:00+08:00`,
**+119 s ahead of the wall clock** at check time (00:28:00). Set each stamp to the real time of the action
it describes; never pre-date an edit or a check.

## 3. Repoint the contract binding into the canonical tree (W082M-06)

Current: `class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN`
and `f0_binding.class_contract_supplement: artifacts/formulation/formulation_taxonomy.yaml`.
Measured authoring mirror `c8e979a1eb48` ≠ declared canonical `276009f4f63d`.

- Repoint both to `research_map/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN`.
- Re-run the consistency check against the canonical F0 hash `276009f4f63d…` and record the canonical
  path + hash actually used, so `binding_note`'s "0 contract-text divergences" is checkable through the
  pointer.
- If the contract text genuinely differs between trees, record the divergence as a `direction_update`
  rather than asserting zero divergence.

## 4. Refresh the self-report (W082M-07)

Line 332–336 reports `independent_reviewers: []`, `verdict: pending` while **nine** reviews (and counting)
declare this exact hash — eight `revise`, one `inconclusive`, zero `accept` — plus this data-integrity
record. Set the reviewer list/count and the current verdict to what is true; do not leave a pending
self-report on a hash that has been reviewed.

## 5. Re-publish and re-check

1. Apply §1–§4, bump `revision` to 12, and publish byte-identically.
2. `sha256sum` both trees; they must match, and neither may equal `9a8bd4c96800…`.
3. Re-run `python3 artifacts/worker-082/f1_machine_defect/run_checks.py --artifact <new canonical> --out /tmp/rc.json`
   (exit 0 = no blocking machine defect) and attach the output to the re-publication note.
4. Only then request a fresh **full-schema** F1 review; all verdicts that bind `9a8bd4c96800…` become
   advisory on a superseded revision.

## 6. Same defect class elsewhere (observation, no verdict attached)

The same scan found duplicate top-level `revised_at` x8 in `schemas/af_scc_c2_vacuum.yaml` (F2a) and x8 in
`schemas/af_scc_c0_vacuum.yaml` (F2b). `research_map/formulation_taxonomy.yaml` (F0) is clean. F2a/F2b are
owned by the same lead and are outside this proposal's binding; fix them in the same pass before re-running
their reviews, or their revise verdicts will recur for the same mechanical reason.
