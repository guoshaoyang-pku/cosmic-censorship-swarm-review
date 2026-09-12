# W091 — Independent verification of W047-F2A-EXT-FREEZE-SPEC-02

- **Task**: `W091-W047-F2A-FREEZE-INDEP-01` (self-selected; no inbox card for this target)
- **Node**: F2a · **Class**: `AF-SCC-C2-VAC-GEN` · **Gate**: G-FORM
- **Review target**: `artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json`
  sha256 `c33e8a46866992cfa7b1f3ea9d31c6e10217f4a51e916697848ec6b54a6a3e98`
  (author report `report.json` sha256 `07973b27ec0d6931fc408f80127c3d235bae1f377ca8f1a9b1ea0f32acacbf6d`)
- **Verdict**: **accept** · score **4.5** · hard failures: **none**
- **Authority**: worker evidence only. This file cannot and does not set node status,
  `validation_status=passed`, or any gate verdict. Canonical paths were read-only.

## What was verified (own implementation, not the author's instrument)

All pins were re-measured and matched; no drift occurred during the run
(F2a `e9a27996…`, F2b `b2ab6acb…`, FROZEN `815e0807…`, F0 taxonomy `0abb9ed8…`).
The six freeze axes were re-derived from the live raw bytes, the five declared
option-A edits (`S1`–`S5`) were applied by this checker to a private snapshot,
and every site's `old_text` occurred **exactly once, at the declared line**
(93, 95, 98, 117, 252).

| axis | meaning (author's label) | baseline live pin | after declared patch |
|---|---|---|---|
| A1 | clause (c) freezes M′ manifold category (S2) | unresolved | resolved (`smooth`) |
| A2 | `topology.extension_topology` names the category (S4) | unresolved | resolved (`smooth`) |
| A3 | clause (a) freezes iota differentiability class (S1) | unresolved | resolved (`C-infinity`) |
| A4 | clause (f) interior addition `int(M′−iota(M))` (S3) | unresolved | resolved |
| A5 | `falsifier.tier_1.witness_type` exhibits same class (S5) | unresolved | resolved |
| A6 | F2a category token == F2b sibling token (sibling uniformity) | unresolved | resolved (`smooth`) |

- **Only-intended-leaves control**: the patched copy differs from the snapshot in exactly
  `extension_predicate.definition`, `topology.extension_topology`,
  `falsifier.tier_1.witness_type`; no keys added or removed.
- **Invariants I1–I9**: all hold on the patched copy (strict YAML parse; `frozen_regularity=C2`;
  `classical_ricci`; clause (d) C2 Lorentzian; `scc_c2_future_inextendibility`;
  `residual_comeager`; containment chain unchanged; no WCC/I⁺ content in the conclusion;
  no composite `C0 or C2` regularity used in an asserted slot).
- **Controls**: identity patch preserves baseline statuses; all six planted single-axis
  mutants reproduce the author's control table exactly
  (`A1→{A1,A6}`, `A2→{A2}`, `A3→{A3}`, `A4→{A4}`, `A5→{A5}`, `A6→{A6}`);
  always-resolved/always-unresolved degenerate detectors both diverge (non-vacuous).
- **Canonical gate**: `check_class_schema.py` passes (exit 0, no failed rules) on **both**
  the unrepaired snapshot and the patched copy — the structural gate is insensitive to the
  under-freezing, so this repair must be carried by content review, not by the gate.
- **Determinism**: two full pipeline runs agree on every field except `generated_at`.

## Findings (none blocking)

1. `F-091W-01` (low) — `repair_spec.json` publishes five sites but the control table uses six
   axes; the A6 semantics are only in the author's instrument code. Add an axis table
   (A1–A6 → site, predicate) to the spec so the control table is reproducible from the spec alone.
2. `F-091W-02` (low) — the canonical structural gate passes the unrepaired file; record this in
   the gate's blind-spot list (content completeness is a reviewer duty).
3. `F-091W-03` (low) — Option A freezes a SMOOTH M′ while the metric is only C2; internally
   consistent and sibling-aligned, but the patch text alone should be read with clause (d).

## Falsifier (this verification)

Falsified if, at the pins above: (a) any site `old_text` is not unique or sits at another line;
(b) any of A1–A6 remains unresolved after the declared option-A patch; (c) a YAML leaf outside
the three declared leaves changes; (d) any invariant I1–I9 fails on the patched copy;
(e) any planted mutant stops reproducing the author's unresolved set; (f) the canonical gate
fails on the patched copy where it passed on the baseline; or (g) the pipeline is not
reproducible. Input drift voids (does not falsify) the report.

**Next falsifier**: after the owner applies the repair at a new revision, this instrument's six
predicates must resolve on the new live bytes and a fresh independent verdict must be recorded
at the new sha256; reviewer cards pinned to `e9a27996…` are void for that revision.

## Files

| file | sha256 |
|---|---|
| `report.json` | `1c321711b318269804ba901e918974cac8d6cb7cf27fbca35762dd61b8ca3a17` |
| `verify_w047_f2a_freeze_091.py` | `25926519e37111132b7139a8b63ffd29845f567958b7e8dfbe5db12fb8492302` |
| `patched/af_scc_c2_vacuum.w047-patched.yaml` | `37e650ad6481ad24551d495887d8cc7bdc0ca713b1cdd614e60324cca681c960` |
| `snapshots/af_scc_c2_vacuum.e9a27996.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `snapshots/af_scc_c0_vacuum.b2ab6acb.yaml` | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
