# W038-F1-REV13-REVIEW-01 — independent G-FORM conformance review of F1 at rev13

Worker: `worker-038` · Class: `AF-WCC-VAC-GEN` · Node: `F1` · Gate: `G-FORM`
Bounded, read-only, class-bound task taken from the live queue (no inbox card exists for
worker-038). Independent instrument; no owner checker is imported or executed in place.

## Question

Does `schemas/af_wcc_vacuum.yaml` at the FROZEN rev29 pin `d9cebb9404b2` (revision 13) satisfy
its class-bound acceptance contract, and is the rev13 evidence-binding/visibility repair real at
the live bytes? The gate needs a rev13-live independent verdict for F1; F2a and F2b already had
rev13 verdicts from other workers.

## Pinned inputs (sha256 measured at run start; all byte-stable through the review)

| input | sha256 (prefix) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (canonical F1, rev13) | `d9cebb9404b2` |
| `artifacts/formulation/schemas/af_wcc_vacuum.yaml` (mirror) | `d9cebb9404b2` |
| `artifacts/formulation/FROZEN.json` (rev29, 50 files, frozen_at 00:57:26) | `815e08079aef` |
| `research_map/formulation_taxonomy.yaml` (declared F0, G-F0 frozen) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |
| `artifacts/formulation/tools/check_taxonomy_consistency.py` (pinned checker) | `de356d999ea3` |
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` |
| `.../variants/AF-WCC-VAC-GEN.variant-SET.delta.json` | `64b8d6394a04` |

## Method

`run_f1_rev13_review.py` re-implements 17 checks from the class-bound contract (pin, mirror,
duplicate-key-safe YAML integrity, identity/scope, revision history, F0 binding chain, isolated
checker regeneration determinism, quantifier order, frozen class semantics, visibility rev13
repair, falsifier tiers, no status inflation, ledger refs, pointer resolution, alias-aware
cross-file semantics, cross-artifact SET-direction census, guard stability). It is independent:
it does not import `check_class_schema.py`, `run_gate_tests.py`, or any owner checker, and it
re-executes the pinned consistency checker only inside a temporary copy of its four inputs.

11 mutation controls (M1–M10, M8 split in two) must fire the corresponding check or the
instrument reports a dead predicate. All 11 fired.

## Result

**F1 conformance verdict: `accept`, score 4.0/5, `hard_failures: []`** (16/17 checks pass,
11/11 controls pass). The one failing check is the cross-artifact census, which is an owner
action against the G-F0-frozen declared taxonomy, not an F1 semantic defect.

Verified at the live bytes:

- canonical and mirror are byte-identical and FROZEN-rev29-pinned;
- the `f0_binding` chain resolves (declared F0 live, both pointers resolve, consistency
  evidence live and green, `checked_at` a wall-clock stamp);
- `artifacts/formulation/evidence/taxonomy_consistency.json` is **exactly reproducible** by the
  FROZEN-pinned checker from the live inputs (two byte-identical isolated reruns);
- quantifier order holds (comeager binder before the data forall), frozen class semantics hold
  (WCC, `residual_comeager`, vacuum/Lambda=0, one AF end, all three sibling classes excluded);
- the visibility rev13 repair is real and internally consistent: single-q TAIL predicate, the
  whole/tail EQUIVALENCE justified by past-closedness of `J^-(q)`, and the SET variant recorded
  as **strictly WEAKER** and non-equivalent. Every surviving `STRONGER` in F1 is either on
  another axis (genericity/B-containment) or a quoted historical "corrected from" note.

## Gate-blocking cross-artifact finding (W038-F1R13-01, severity H)

Two **operative** claims in the G-F0-frozen `research_map/formulation_taxonomy.yaml` still say the
SET/union reading is *strictly stronger* than the single-q tail predicate, contradicting F1 rev13:

- `research_map/formulation_taxonomy.yaml:94` — SET variant `definition` block:
  "Strictly stronger than the parent class: gamma outside the union implies no single q sees a
  tail of gamma, but not conversely."
- `research_map/formulation_taxonomy.yaml:200` — class conclusion text:
  "The set-based reading ... is strictly stronger".

Delta versus the previously filed L-FORM-03: line 94 was **not** in L-FORM-03's location list;
`VARIANT_REGISTRY.json:57` and the SET delta lines 11/22 now carry the corrected direction plus a
quoted historical note; `formulation_taxonomy.yaml:176` is a historical D1 record
(`f0_reading ... (strictly stronger)`, status resolved), not an operative claim. Full census in
`report.json.cross_artifact.residual_mentions`.

The two surviving locations are inside the file whose hash G-F0 passed on
(`0abb9ed8a961`), so editing it voids G-F0; the repair must be an atomic owner decision (re-freeze
with a revision bump, or a controller-recorded exception), not a silent write.

## Non-claims / authority

Worker review evidence only. This cannot set `status=done`, `validation_status=passed`, or any
gate verdict. It is not a mathematics or physics result; it bounds an evidence-binding defect.
`counts_as_full_schema_verdict: true` for F1 conformance at the pins above, subject to the audit
lead's adjudication.

## Falsifier

Any of: a K01–K17 check or mutation control flips; the F1 canonical/mirror bytes move from
`d9cebb9404b2`; FROZEN.json bytes move from `815e08079aef` (rev29, 50 files); the live
`taxonomy_consistency.json` stops being byte-reproducible by the pinned checker from live inputs;
F1 is shown to state the SET variant as stronger than the single-q predicate; or a hard failure is
found at a hash other than the one pinned here.

## Replay

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-038/f1_rev13_review/run_f1_rev13_review.py   # exit 0 = accept, 2 = revise/dead control
```

Raw pinned report copies: `raw/run_*.json`. The filed `report.json` is byte-identical to
`raw/run_20260912T010234.json`; earlier `raw/run_*` copies are pre-fix classifier iterations kept
for provenance (they are not the filed result).
