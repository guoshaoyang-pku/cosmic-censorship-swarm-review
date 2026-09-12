# W029-F1-SUITE-MATERIALITY-06 — L-FORM-04 materiality adjudication

**Worker:** worker-029 · **Node:** F1 · **Class:** `AF-WCC-VAC-GEN` · **Gate:** G-FORM
**Question answered (registered by astra-lead-formulation, `lead-form-20260912T005743-93`):**
`schemas/f1_falsifier_tests.jsonl` (25 rows, 84 probes) declares `binding_sha256` = F1 rev12
`cce9c60146d6` while the canonical F1 schema is rev13 `d9cebb9404b2`. **Must the corpus be
re-bound, and is a mechanical hash rebind sufficient?**

**Authority:** worker evidence only. This note cannot set `status=done`,
`validation_status=passed`, or any gate verdict. No canonical file was written.

## Pins (all matched at T0 and T1; third-party rev12 before-oracle)

| path | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| third-party rev12 snapshot (`artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml`) | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |

Deterministic core digest (`report_core.json`, byte-identical over 2 runs): `13d07b379b27`.

## Measurement

1. **Binding.** 25/25 rows bind the superseded rev12 hash `cce9c60146d6`; 0/25 bind the live
   rev13 pin. Vendor hard check **C1a is false** at the canonical pin (check B2, hard).
2. **rev12 → rev13 structural delta** (8 changed leaves + 4 added, 0 removed):
   `class_identity_variants[0].relation`, `f0_binding.binding_note`,
   `f0_binding.checked_at`, `f0_binding.consistency_evidence_sha256`,
   `quantifiers.domains.D5.definition`, `revised_at`, `revision`, `visibility.definition`,
   plus `revision_history[10].*`.
3. **Per-row materiality** (ancestor/descendant intersection of each row's `deciding_field`,
   `deciding_field_alternates` and probe paths with the delta):

| row | classification | changed path the row exercises |
|---|---|---|
| F1-AMB-11 | MATERIAL_EXERCISED_PATH | `visibility.definition` (deciding field, probed) |
| F1-AMB-17 | MATERIAL_EXERCISED_PATH | `visibility.definition` (deciding field, probed) |
| F1-AMB-23 | MATERIAL_EXERCISED_PATH | `class_identity_variants[0].relation` (deciding field, probed) and alternate `visibility.definition` |
| F1-AMB-25 | PRE_EXISTING_FALSE_EXPECTATION | probe `f0_binding.binding_note` (also decides on `f0_binding.declared_f0_sha256`) |
| F1-AMB-21 | SIBLING_BINDING_CHANGE | only siblings under `f0_binding` moved; the decided leaf itself is unchanged |
| other 20 rows | DECLARATION_ONLY | no exercised path changed |

   **Exercised rows: F1-AMB-11, F1-AMB-17, F1-AMB-23, F1-AMB-25.** The lead's premise that the
   rev13 repair was "prose-direction only" and moved no field any test exercises is **falsified**:
   the `visibility.definition` text that rows 11/17 decide on and the
   `class_identity_variants[0].relation` that row 23 decides on both changed.
4. **Expectation validity (independent recomputation of all 84 stored probes against both
   snapshots).** 82/84 pass at rev12 and 82/84 pass at rev13. **Zero expectations are
   invalidated by rev13** (check M2 passes). The two failures are **pre-existing** at rev12 and
   are both in F1-AMB-25:
   - `f0_binding.declared_f0_sha256` `equals` expects `276009f4…` (F0 rev4); the schema declares
     and the live path measures `0abb9ed8…` (F0 rev5);
   - `f0_binding.binding_note` `contains` expects `astra-classscope-02`; the note no longer
     carries that token.
5. **Cross-artifact resolution (X1, hard).** The suite's only cross-artifact declaration
   (`research_map/formulation_taxonomy.yaml`) is stale: stored `276009f4…`, measured
   `0abb9ed8…`.
6. **Controls C1–C8 pass:** planted material change detected; unrelated change ignored;
   mutated expectation detected; identical trees give an empty delta; metadata-only change is
   not material; the rev12 snapshot reproduces exactly the F1-AMB-25 false set; unknown probe
   kind fails closed; the duplicate-key scan is armed. One false positive was caught by control
   C6 during development and removed: `contains` probes on structured values embed the suite
   author's `json.dumps` spelling, so the evaluator now mirrors
   `json.dumps(value, default=str, ensure_ascii=False)` instead of a compact separator form.

## Verdict

**revise** — and the answer to the two questions is:

- **Rebind required: yes, and it is not optional.** The suite must not be waved through as
  "prose-only": rev13 moved deciding/probed paths of four rows, so the corpus is stale in
  substance, not merely in its declared hash. Vendor C1a must go true for G-FORM r3.
- **Mechanical rebind sufficient: no.** A hash-only rebind would freeze two already-false
  expectations and a stale cross-artifact hash into the next revision. The rebind must be
  paired with content repair.

**Recommended rev14 scope** (one authorized revision, then a fresh independent verdict at the
new suite hash):
1. Re-bind all 25 rows to the current canonical F1 pin.
2. Repair F1-AMB-25: refresh `f0_binding.declared_f0_sha256` to the live F0 rev5
   `0abb9ed8…` and replace the `astra-classscope-02` `binding_note` expectation; re-point the
   cross-artifact declaration.
3. Re-observe rows F1-AMB-11, F1-AMB-17, F1-AMB-23 against the rev13 text (their stored
   expectations still evaluate true, but their `observed_excerpt` values now describe superseded
   bytes).
4. Do not rebind only the hash fields: items 2–3 survive a mechanical rebind.

## Falsifier

Re-run `check_suite_materiality.py` on the same snapshots. Falsified if any material row has no
ancestor/descendant relation to a changed leaf, if a stored expectation flips true→false at rev13
while passing at rev12, if the F1-AMB-25 pre-existing set is not reproduced from the third-party
rev12 snapshot, or if any pin/control behaves differently. A moved F1, suite or FROZEN hash
**supersedes** the measurement (it does not falsify it).

**Next falsifier:** after the next suite rebind, B1/B2 should pass while M2/X1 decide whether the
content repair landed.
