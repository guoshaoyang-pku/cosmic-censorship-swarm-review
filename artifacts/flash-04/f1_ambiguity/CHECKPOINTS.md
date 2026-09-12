# Worker 04 checkpoints — F1 ambiguity attack

Assignment `asg-2026-09-11-F1-deepseek-flash-04-13` (node `F1`, class
`AF-WCC-VAC-GEN`, gate `G-FORM`, artifact `schemas/f1_falsifier_tests.jsonl`,
budget 4 agent-hours, deadline 2026-09-12T03:15+08:00). All times +08:00.

| time | checkpoint | outcome |
|---|---|---|
| 23:15 | CP0 boot | read `HANDOFF.md`, `README.md`, `research_map/*`, runtime state; `comms/inbox` empty; map claimed F0/A0 done with missing artifacts (0/10 declared artifacts on disk) |
| 23:17 | CP1 pre-assignment | began unassigned N0-path work (flat-space acceptance harness) per the "no assignment -> propose" rule; draft only, never emitted as a proposal |
| 23:19 | CP2 assignment | `comms/inbox/deepseek-flash-04.jsonl` assignment F1 arrives; pivot to it; N0 draft frozen, unclaimed, namespaced under `artifacts/flash-04/n0_acceptance/` |
| 23:22 | CP3 contract read | read `artifacts/formulation/rule_spec.json` (R01–R16) and `research_map/formulation_taxonomy.yaml`; authored 15-test suite against the contract while `schemas/af_wcc_vacuum.yaml` was absent |
| 23:26 | CP4 r2 appears | F1 revision 2 `f15ea523` lands; runner binds and shows the assignment falsifier firing (no `non_vacuity` block, R11 name collision) |
| 23:28 | CP5 drift observed | schema changes under the same revision label: `f55722a7`, then `a7ef0398`; snapshots preserved |
| 23:30 | CP6 r3 settled | F1 `7a3e1f93`; rebind all rows to actual paths, add `F1-AMB-16/17`; result 11/17 decided, 6 structurally open, 7 findings; expectations match 17/17 |
| 23:30 | CP7 emit | outbox `comms/outbox/deepseek-flash-04.jsonl`: status + 2 artifacts + blocker, all schema-validated (`validate_map.py` prints VALID); `unverified`, no completion claim |
| 23:31 | CP8 monitor | started `watch_drift.sh` to re-audit on schema hash change or inbound message |
| 23:31 | CP9 self-review | corrected five overstated answers (AMB-02/03/08/09/13); rebuilt artifact `106cf329`; emitted superseding outbox events with `supersedes` links |
| 23:33 | CP10 lead adjudication | `ADJUDICATION_flash04_ambiguity.md` rules every finding; F1 frozen (message cites 17873b9d) |
| 23:35 | CP11 freeze drift | `FROZEN.json` updates the F1 pin to `f512af5f`; snapshot renamed accordingly; `17873b9d` never audited |
| 23:36 | CP12 delta rebind | suite rebound to frozen rev4 (`18102c20`); 13/17 determinate, 4 obligations open, 0 expectation mismatches; delta: 2 closed, 2 finding-closed, 4 reclassified, 4 still open; cross-check vs `open_rows` 3/3 leaves matched, AMB-03 queue gap found |
| 23:37 | CP13 emit | delta-only status + 2 artifacts + blocker (obligations, AMB-03 queue gap, FROZEN self-hash) appended with supersedes links |
| 00:08 | CP13b rev19 rebind | suite rebound to FROZEN rev19 `f962c117` (22 tests, sha `6e8e7f44`); post-run drift note: authoring head moved to `b65fcc0f` at 00:08:37 |
| 00:11 | CP14 rev20 freeze | FROZEN revision 20 pins `b65fcc0f` (schema internal rev9); prior `f962c117` recovered from two independent 30904-byte copies |
| 00:14 | CP15 rev20 rebind+emit | 24 tests rebound to `b65fcc0f` (sha `bd405cff`); 22 unchanged, 1 field_added (`class_identity_variants`), 1 field_content_changed (`anti_scope.not_this_class`), new F1-AMB-23/24; 0 failures, 0 flips; 4 events emitted; worker checkpoint `runtime/state/w04_checkpoint_f1_rev20.json` |

## State at CP14 (rev20 rebind)

* declared artifact `schemas/f1_falsifier_tests.jsonl` sha256
  `bd405cffcc2d87e97c18ce521a50e6636a02edb67702eb7b428ee10905147692` (24 rows).
* bound schema: frozen rev20 `artifacts/formulation/schemas/af_wcc_vacuum.yaml`
  sha256 `b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94` (internal rev9);
  canonical copy `schemas/af_wcc_vacuum.yaml` byte-identical (publication resolved).
* delta vs rev19 `f962c117`: 22 unchanged, 1 field_added (`class_identity_variants`),
  1 field_content_changed (`anti_scope.not_this_class`); probes F1-AMB-23/24 cover the rev9
  surfaces; 0 probe failures, 0 probe flips.
* report `artifacts/flash-04/f1_ambiguity/rebind_b65fcc0f_delta_report.json` sha256
  `7ddef02aeaa06440d0333418e02af597124d205535dd3f026cc6fa3ae44ad866`; runner
  `rebind_b65fcc0f.py`; version copy + prior/new schema snapshots under
  `artifacts/flash-04/f1_ambiguity/`.
* node state: `F1` stays `active`; `validation_status: unverified`; no gate verdict.
* remaining open obligations: F1-AMB-01, F1-AMB-02, F1-AMB-03, F1-AMB-15.

## Next falsifier

A content-hash change of `artifacts/formulation/schemas/af_wcc_vacuum.yaml` (or of its canonical
copy) after `b65fcc0f` invalidates the binding: re-run `rebind_b65fcc0f.py` with the new hash and
emit a fresh status line. A lead/A1 reply in `comms/inbox/deepseek-flash-04.jsonl` takes
precedence over all of the above.
| 00:20 | CP15 rebind 9a8bd4c9 | suite rebound b65fcc0f -> 9a8bd4c9; 25 tests (1 new); 84/84 probes pass; verdict verify_pass; F0 cross-artifact match=True |
