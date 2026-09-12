# W041-F1-CORPUS-REBIND-01 — L-FORM-04 adjudication input

Bounded class-bound worker task by `worker-041`
(instance `worker-041-20260912T005751-968807`), class `AF-WCC-VAC-GEN`,
node `F1`, gate `G-FORM`, budget 1.0 agent-hour.

## Subject

Blocker **L-FORM-04** (`lead-form-20260912T005743-93`): `schemas/f1_falsifier_tests.jsonl`
(pin `56bcb4b3234b`) declares `binding_ref` / `binding_sha256` = F1 rev12
`cce9c60146d6`, superseded by the rev13 evidence-binding repair F1
`d9cebb9404b2`. The lead's stated position is that the rev13 edits are
"prose-direction only" and did not change any field the 25 rows exercise; the
lead asked for a controller/audit ruling on whether re-binding is required.

L-FORM-04's own falsifier: *"a reviewer shows the rev13 edits change a field any
of the 25 tests exercises, or the corpus is re-bound and the staleness
disappears."* This task measures the first disjunct.

## Pins (measured before and after the run, no drift)

| role | path | sha256 |
|---|---|---|
| F1 rev13 (live) | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| F1 rev12 (baseline A) | `artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| F1 rev12 (baseline B) | `artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| corpus | `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |
| manifest | `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |

## Verdict

**`FALSIFIER_FIRES` — severity `semantic`.** Four of the 25 rows exercise at
least one field whose value changed between rev12 and rev13:

| row | test | changed exercised field(s) |
|---|---|---|
| 10 | F1-AMB-11 | `visibility.definition` |
| 16 | F1-AMB-17 | `visibility.definition` |
| 22 | F1-AMB-23 | `visibility.definition`, `class_identity_variants[0].relation` |
| 24 | F1-AMB-25 | `f0_binding.binding_note`, `class_identity_variants[0].relation` |

The rev12→rev13 diff has 12 changed/added leaves in total; the other eight are
`revision`, `revised_at`, `revision_history[10].*`, `f0_binding.checked_at`,
`f0_binding.consistency_evidence_sha256`. The three semantic leaves are the
direction correction `strictly STRONGER` → `strictly WEAKER` in
`class_identity_variants[0].relation`, the `visibility.definition` rewrite
(removes the rev12 misclassification example, asserts tail/whole-curve
equivalence for causal geodesics), and the appended rev13 note in
`f0_binding.binding_note`. `quantifiers.domains.D5.definition` also changed but
is not exercised by any row.

**Outcome level (secondary, honest counterweight):** no calibrated probe's
pass/fail changes between rev12 and rev13 under the pre-registered natural
semantics (`rows_with_changed_probe_outcome` is empty). So the literal
falsifier fires, while the corpus's decisions would remain reproducible at
rev13. A purely mechanical re-pin is therefore *not* sufficient in principle:
the exercised-field change makes the declared rev12 binding a false statement
about which bytes the tests were evaluated against, and the lead's
"not changed" premise is falsified.

**Additional finding (pre-existing, independent of rev13):** 81/84 probes
reproduce their recorded `pass` at the bound rev12 revision. The three misses
decompose mechanically into (a) one JSON-representation artifact (row 22's
`"is_this_class": false` expectation is JSON-shaped; the stored YAML value is
a list of mappings), and (b) **two genuinely stale expectations already present
at rev12** in row 24 / F1-AMB-25:
`f0_binding.declared_f0_sha256` expects the superseded `276009f4…` while rev12
and rev13 both declare `0abb9ed8a961…`, and `f0_binding.binding_note` expects
`astra-classscope-02`, which the rev12 note no longer contains. Both were left
behind by the earlier `astra-life03-repin-claims` rev11→rev12 rebind, which
rewrote binding metadata without refreshing probe expectations. Any rev14
re-bind must therefore be content-aware, not mechanical.

## Controls (all pass, exit 0)

C1 both rev12 copies hash to the pin; C2 rev13/corpus/manifest hashes stable
before/after; C3 positive control — 12 changed leaves including all three
expected semantic paths; C4 negative control — mutating an unexercised leaf
(`adjudication_queue.adjudication_ref`) touches no row; C6 two in-process
analyses byte-identical.

## Artifacts

| artifact | sha256 |
|---|---|
| `report.json` | `3f5563c2e0271e484087168c5236b2b4ccbb3f347f41a2199d8fb868a7fb2516` |
| `run_f1_corpus_rebind.py` | `fcf8c4283d74fbdc36ec92fe43b2834fc791b6faddee20e77823a927710d8980` |
| `PREREGISTRATION.md` | `62f329fa753bfcd733bb1184438d638a2171db1b4cbaf4ec2044421b1026b990` |
| `raw/run1.stdout.txt`, `raw/run2.stdout.txt` | run logs |

Reproduce: `python3 artifacts/worker-041/f1_corpus_rebind/run_f1_corpus_rebind.py`
(exit 0; exit 3 = pin drift, exit 4 = control failure).

Reproduction semantics: the measurement payload is deterministic (control C6,
two in-process runs identical). `report.json` embeds a wall-clock `created_at`,
so a fresh run regenerates the same findings under a new file hash; compare the
`verdict`/`changed_leaves`/`row_reports` blocks and the exit code, or diff out
the single `created_at` field, rather than expecting the archived byte hash.
The archived pins are the schema/corpus hashes, which must not move.

## Authority

Worker measurement only. No gate verdict, no node status, no
`validation_status=passed`, no canonical file edited. The L-FORM-04 ruling
belongs to the controller/audit; this report is its adjudication input.
