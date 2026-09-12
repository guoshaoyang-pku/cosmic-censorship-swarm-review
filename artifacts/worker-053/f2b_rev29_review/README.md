# worker-053 — F2b (AF-SCC-C0-VAC-GEN) independent review at FROZEN rev29

Status: **worker task complete** (task-completion claim only; no node status, no gate verdict, no
`validation_status` is set). Reviewer verdict: **revise**, score 3.5.

## Task taken

`astra-life05-verify-gform-r3` needs two independent non-author verdicts per class at the FROZEN
rev29 pins. At pass-06 close F2b had **0 distinct accepts** at the measured canonical hash
`b2ab6acb2bbe` (controller gate audit, 2026-09-12T01:00:44), so F2b was the binding class. This
worker took the class-bound F2b review: `AF-SCC-C0-VAC-GEN` at
`schemas/af_scc_c0_vacuum.yaml` = `b2ab6acb2bbe…`, FROZEN rev29 = `815e08079aef…`.

This is a **non-blind confirmatory** review (worker-075's F2b verdict was read before this review
was finalized). It must **not** be counted as one of the two blind verdicts.

## Result

One blocking defect, independently reproduced with a from-scratch instrument and 9/9 mutation
controls:

- **W053-F2B-REV29-01 (major, hard failure)** — `implication_ledger.forbidden_transfers[0].reason`
  (live line `schemas/af_scc_c0_vacuum.yaml:246`) reads *"C2 is a strictly larger extension class,
  so C2-inextendibility is strictly weaker"*, while the same file's
  `extension_class_containment` reads *"E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2"*,
  i.e. `E_C2` is the innermost (smallest) extension set. The transfer direction and the
  conclusion "strictly weaker" are correct; only the size predicate is inverted.
  - Corroborates the standing finding **L-FORM-01**
    (`artifacts/formulation/evidence/lead_freeze_hold_independent_verify.json`, rev12 bytes
    `55d0a1ea`) and **HF-075-F2b-LARGER** (`reviews/F2b-review-rev29-075.json`).
  - It **survived** `astra-life05-evidence-binding-repair`: the rev29 delta fixes L-FORM-02 but does
    not list L-FORM-01; measured live at rev13 bytes `b2ab6acb`.
  - Repair: one clause — `strictly larger` → `strictly smaller` (or adopt the F2a wording "the
    converse containment is false"). Control M5 proves the checker PASSes on the corrected string
    and no other check depends on the old one.
  - Blast radius: the same string is copied into ≥8 fixtures under
    `schemas/semantic_contract_tests/fixtures/` (sem05, sem08, sem10, sem12, sem14, sem19,
    struct01, struct05, struct06); a repair should regenerate or explicitly disposition them.
  - Falsifier: a containment-respecting model in which `E_C2` is strictly larger than `E_C0`, or
    corrected bytes at that field in a new revision.

Everything else at the pinned bytes PASSes (C1–C9, C11–C13):

- C1/C2: the F2b pin resolves and **all 50 FROZEN rev29 pins resolve** to measured bytes.
- C3: authoring mirror is byte-identical to the canonical path.
- C4/C5: `declared_f0_sha256` = live F0 `0abb9ed8a961`; `consistency_evidence_sha256` = live
  evidence `9e335e9ba1bf`; pointers resolve; a staged re-run of the canonical consistency checker
  returns `CONSISTENT (4 classes, 0 contract-text divergences)` and reproduces the canonical
  evidence bytes exactly.
- C6: class identity (components, taxonomy axes, alias canon, sibling disjointness, forbidden
  C2→C0 transfer) matches the declared F0 taxonomy.
- C7: no assertive class leakage — own scan empty; canonical `research_map/class_separation.py`
  = `a8c04fc3` reports no findings.
- C8: no conclusion inflation — `scc_c0_future_inextendibility`, `open_problem`,
  `claim_promotion` requires `artifact_refs`, conditional refutation quarantined to variant CH,
  `I+`/visibility not in the conclusion.
- C9: quantifier order `[forall, exists(comeager), forall, not_exists]`, future C0 extension
  predicate, 4d / one-ended `R^3` / `I+ = R x S^2` topology.
- C11: target and manifest bytes stable across the review window.
- C13: `taxonomy_cases.jsonl` meta binds live F0 and the manifest pin.

F1 (`af_wcc_vacuum`) and F2a (`af_scc_c2_vacuum`) do **not** contain the inverted sentence; the
defect is unique to the F2b schema among the three live schemas.

## Artifacts

| path | sha256 |
|---|---|
| `artifacts/worker-053/f2b_rev29_review/check_f2b_rev29.py` | `918edbef744fb713d58ae9ae7b5a2256cde01a12b7b30ec75233bb8ead2f7e35` |
| `artifacts/worker-053/f2b_rev29_review/report.json` | `2aae54b40b96f6853bfef2d033d81c66ec5635c54d09709b0f228667bae610d0` |
| `reviews/F2b-review-rev29-053.json` | `6813037ab0543a849ae6b3d0cb15eb9cbe42c41d9ec0413cf8d4c025bd625098` |
| `artifacts/worker-053/f2b_rev29_review/checkpoint.json` | `recorded in hashes.txt` |
| `artifacts/worker-053/f2b_rev29_review/hashes.txt` | `recorded in hashes.txt` |

Measured pins (live at review time, unchanged T0→T1):
`schemas/af_scc_c0_vacuum.yaml` = `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`
(35 602 B); `artifacts/formulation/FROZEN.json` =
`815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`; F0 =
`0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`; consistency evidence =
`9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b`.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-053/f2b_rev29_review/check_f2b_rev29.py \
  --report artifacts/worker-053/f2b_rev29_review/report.json
# expect: verdict=revise, exactly one hard failure at
# implication_ledger.forbidden_transfers[0].reason, controls 9/9
```

Any change to `schemas/af_scc_c0_vacuum.yaml`, `artifacts/formulation/FROZEN.json`, the F0
taxonomy, or the consistency evidence before re-measurement voids this verdict; bind to hashes,
never to the path or the revision label alone.

## Boundary

No gate verdict, no node status, no claim promotion, no writes outside
`artifacts/worker-053/f2b_rev29_review/`, `reviews/F2b-review-rev29-053.json`,
`runtime/state/w053_f2b_rev29_review_checkpoint.json` and `comms/outbox/worker-053.jsonl`.
