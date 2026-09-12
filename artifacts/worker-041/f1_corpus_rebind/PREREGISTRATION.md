# W041-F1-CORPUS-REBIND-01 — pre-registration (rules fixed before execution)

Worker: `worker-041` (instance `worker-041-20260912T005751-968807`).
Class: `AF-WCC-VAC-GEN` (all 25 corpus rows are F1/WCC rows).
Subject: blocker **L-FORM-04** (`comms/outbox/astra-lead-formulation.jsonl`,
event `lead-form-20260912T005743-93`): `schemas/f1_falsifier_tests.jsonl`
(pin `56bcb4b3234b`) still declares `binding_ref` / `binding_sha256` =
F1 rev12 `cce9c60146d6`, superseded by the rev13 repair F1 `d9cebb9404b2`.

L-FORM-04's own falsifier: *"a reviewer shows the rev13 edits change a field
any of the 25 tests exercises, or the corpus is re-bound and the staleness
disappears."*

## Pins (measured by me, before analysis)

| role | path | sha256 |
|---|---|---|
| F1 rev13 (live canonical) | `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| F1 rev12 (baseline copy A) | `artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| F1 rev12 (baseline copy B) | `artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml` | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| corpus under test | `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |
| manifest at run | `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |

Both rev12 copies must hash to the pin or the run stops (exit 3). Rev13 and
the corpus are re-hashed after reading; any drift voids the run.

## Pre-registered definitions

1. **Leaf value**: a scalar (or null) reached by descending mappings by key
   and sequences by index. A path like `a.b[0].c` is a leaf path.
2. **Changed leaf set**: leaf paths where rev12 and rev13 values differ, plus
   leaf paths present on only one side.
3. **Exercised path of a row**: the union of
   (a) `probe_results[*].path` (exact strings), and
   (b) every dotted path token found in `deciding_field`,
   `deciding_field_alternates[*]`, `deciding_field_contract` that resolves
   (as a leaf or as a container prefix) in rev12.
4. **Tier-1 touched row**: a row is TOUCHED iff some exercised path of that
   row has at least one changed leaf at or below it. Metadata leaves are not
   excluded from tier 1: the falsifier text says *any field any test
   exercises*, so the literal reading is used. Metadata-only overlap is
   additionally labelled `metadata_only`.
5. **Tier-2 textual mention**: a non-tier-1 string leaf of the row contains
   one of the changed path names (`visibility.definition`,
   `class_identity_variants`, `quantifiers.domains.D5`,
   `f0_binding.binding_note`) or the exact changed leaf path. Reported
   separately; never the sole basis of the falsifier verdict.
6. **Probe re-execution semantics** (natural reading of the corpus's declared
   `kind`s): `contains` = `expected` substring of `str(value)`;
   `equals` = `expected == value`; `is_none` = `value is None`;
   `is_true` = `value is True`; `path_exists` = path resolves;
   `nonnull` = `value is not None`.
7. **Calibration**: for each probe, my re-executed pass at rev12 is compared
   with the `pass` recorded in the corpus row. Outcome-level claims use only
   calibrated probes; uncalibrated probes are reported and excluded.
8. **Decisive verdict**:
   - `FALSIFIER_FIRES` iff ≥1 row is tier-1 touched by a changed leaf.
   - severity `semantic` iff a tier-1 touched leaf is outside
     `{revision, revised_at, revision_history[...], f0_binding.checked_at}`,
     or iff a calibrated probe outcome changes between revisions;
     otherwise `metadata_only`.
   - If no row is tier-1 touched, `FALSIFIER_DOES_NOT_FIRE` (hash-only
     staleness; rebinding is then a pin-discipline decision, not a
     semantics-forced one).
9. **Controls** (any failure ⇒ exit 4, report marked control_failed):
   C1 both rev12 copies hash to the pin; C2 rev13 + corpus hashes stable
   before/after; C3 positive control: changed-leaf set is non-empty and
   contains the three expected semantic paths (`visibility.definition`,
   `quantifiers.domains.D5.definition`,
   `class_identity_variants[0].relation`); C4 negative control: mutating a
   leaf that lies under no exercised path changes no row's touched status;
   C5 probe-semantics calibration is reported; C6 the whole analysis is
   deterministic over two in-process runs.
10. **Authority**: worker measurement only. No gate verdict, no node status,
    no `validation_status=passed`, no canonical file is edited. The
    controller/audit owns the L-FORM-04 ruling.
