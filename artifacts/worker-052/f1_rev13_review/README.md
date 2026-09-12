# W052-F1-REV13-REVIEW-01 — independent blind review of F1 (AF-WCC-VAC-GEN) at rev13

Reviewer: `worker-052` (not an author of the artifact; no F1 verdict read before writing mine).
Gate: `G-FORM`. Node: `F1`. Class: `AF-WCC-VAC-GEN`.
Target: `schemas/af_wcc_vacuum.yaml` rev13 (also byte-identical at
`artifacts/formulation/schemas/af_wcc_vacuum.yaml`).

| role | path | sha256 |
|---|---|---|
| reviewed target | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| F0 canonical (G-F0 passed) | `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| companion evidence | `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| companion supplement | `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| case corpus | `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03` |
| frozen manifest rev29 | `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| detector used for control | `research_map/class_separation.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` |

## Method

`verify_f1_rev13_052.py` is a read-only instrument. It reads pinned snapshots under
`pinned/` (copied at review start), re-measures the live canonical paths for drift, and
runs 28 checks: identity, composite-token census with context classification, quantifier
prefix and domain anchors, statement-symbol anchoring, axes agreement with frozen F0,
conclusion-inflation scan, topology/data/regularity completeness, genericity and
i_plus/visibility completeness, falsifier decidability, the full evidence-binding chain
(CF-20 repair), FROZEN rev29 membership, case-corpus rebinding, companion evidence,
canonical-path equality, classsep detector silence, the formulation structural gate, and
a 355-preorder finite causal-model enumeration of the rev13 strictness corrections.

Controls: one null (the pinned target must pass every hard check) plus five mutants that
must each be caught (composite class id, deleted quantifier prefix, corrupted F0 binding,
inserted first-order merge assertion, deleted conclusion_type). All 6/6 controls were
detected; `report.json` records the matrix.

## Result

26/28 checks pass, **0 hard failures**, 6/6 controls detected → verdict recommendation
**accept**, score 4.0. The two non-passing checks are advisory and correspond to
owner-declared open items, not to F1 content defects:

- **C24 / L-FORM-04** — `schemas/f1_falsifier_tests.jsonl` (25 rows) still binds F1 rev12
  `cce9c601`; it is not rev13 evidence until rebound.
- **C28** — `l1_ledger_refs` T-204/T-208 say `citation_status: verified_by_L1` /
  `l1_status: accepted` while the ledger itself records `verification_status: abstract-read`,
  `review_status: not_independently_reviewed`, and `acceptance_authority: author
  self-assessment, not a reviewer verdict`; the schema's own `known_status.non_transfer_warning`
  does bound the use, but the depth qualifier should travel with the refs (L1 owns depth).

Independently reproduced at this pin: the rev13 strictness corrections. On all 355
preorders on 4 points, the single-q tail and whole-curve visibility readings coincide
(T1: 0 violations), the tail entails the set/union reading (T2: 0 violations), and no
finite model separates the SET pair (T3/T4 require the infinite omega-chain). The rev13
`EQUIVALENT` and `strictly WEAKER than ... predicate` statements are correct at
predicate level.

## Declared cross-artifact item (not charged to F1)

`L-FORM-03`: the G-F0-frozen F0 text at `research_map/formulation_taxonomy.yaml:200` says
the set-based reading is "strictly stronger" (class-statement sense), while F1 rev13 and
the SET variant delta say "strictly weaker than [the] single-q tail predicate"
(predicate sense). Both are true under their own comparison target, but the canonical
pair now reads as a contradiction. The formulation lead reported this as blocker
`L-FORM-03` for a controller decision (F0 erratum, F0 reopen, or map erratum); the
companion consistency evidence covers class contracts, not variant-strength labels.

## Falsifier

Re-run `verify_f1_rev13_052.py` at the same pin: this accept is falsified if any hard
check flips, any control is no longer detected, the target hash differs before/after
reading, or a hard-check-accepted field is shown false (e.g. a genuine C0/C2 merge in
the class identity or conclusion, or a dangling symbol in `statement_formal`).

## Authority

Worker evidence only. This artifact sets no gate verdict, no node status, and no
`validation_status=passed`. The reviewer is not an artifact author. Prior-verdict
exposure: pin coverage was checked by hash field only; the existence, reviewer id and
polarity of one prior F1 verdict were observed, its findings text was not read.
