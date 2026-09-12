# F1 ambiguity attack bundle (worker `deepseek-flash-04`)

Assignment `asg-2026-09-11-F1-deepseek-flash-04-13`: attack worker 03's F1 schema
with >=10 ambiguity tests (spacetime description + does it satisfy F1? + which
field decides) and deliver `schemas/f1_falsifier_tests.jsonl`.

**Status: unverified draft. No node completion claimed. Class `AF-WCC-VAC-GEN`,
node `F1`, gate `G-FORM`. Currently bound to the **frozen rev4** schema
`artifacts/formulation/schemas/af_wcc_vacuum.yaml#f512af5f…`; delta vs the r3
worker draft in `frozen_rev4_delta_report.json`.**

## Deliverables

| path | role |
|---|---|
| `schemas/f1_falsifier_tests.jsonl` | declared artifact: 17 tests, one JSON object per line |
| `ambiguity_report.json` | generated: per-test structural binding + contract-leaf audit |
| `FINDINGS.md` | result summary, open findings, hash-drift finding, next falsifiers |
| `run_f1_ambiguity.py` | runner: contract mode, schema mode, suite validation, self-test |
| `build_tests.py` | deterministic generator for the JSONL |
| `binding_rev4.py` | frozen-rev4 field binding and per-row dispositions |
| `delta_report.py`, `frozen_rev4_delta_report.json` | r3 → frozen-rev4 delta accounting |
| `audit_adjudication_queue.py`, `adjudication_crosscheck.json` | coverage/attribution vs the schema's own queue |
| `r3_7a3e1f93_report.json` | baseline report for the delta |
| `versions/` | content-addressed copies of the declared artifact |
| `schema_snapshots/` | content-addressed F1 copies the suite is bound to |
| `runner_selftest.txt`, `suite_validation.txt` | captured runner evidence |
| `BUNDLE.sha256` | per-file hashes of this bundle |

## Result in one line

Frozen rev4 `f512af5f…`: 13/17 tests structurally decided, 4 open accepted
obligations (`AMB-01/02/03/15`); two r3 findings closed (AMB-09, AMB-10), two
more closed by ruling (AMB-07 set-level membership, AMB-08 R³-only slices). The
assignment's declared falsifier ("a test no schema field can decide") did **not**
fire on r3/r4 but **did** fire on revision 2 (`f15ea523`), where the R08
`non_vacuity` block and the R11 `conclusion.conclusion_type` leaf were absent.

## Reproduce

```bash
cd artifacts/flash-04/f1_ambiguity
python3 run_f1_ambiguity.py --validate-only            # SUITE VALID
python3 run_f1_ambiguity.py --self-test                # runner controls
python3 run_f1_ambiguity.py --schema schema_snapshots/af_wcc_vacuum.7a3e1f93.yaml \
    --expect-sha 7a3e1f93 --out ambiguity_report.json  # exit 1 = open findings
python3 build_tests.py                                 # regenerate the JSONL
```

Exit codes: `0` structurally bound, `1` open findings, `2` suite/runner invalid,
`3` configuration error. A non-zero exit from the schema run means the attack
found unresolved ambiguity, not that the runner failed.

## Test row schema (one line = one test)

Required keys: `test_id`, `node_id`, `class_id`, `gate`, `schema_under_test`,
`spacetime_description`, `known_properties`, `question`,
`does_it_satisfy_f1`, `satisfies_in_class`, `satisfies_conclusion`,
`deciding_field`, `deciding_field_contract`, `deciding_field_alternates`,
`deciding_field_status`, `schema_finding`, `schema_open_expected`,
`falsifier_strength`, `evidence_refs`, `literature_status`, `citation_status`,
`next_falsifier`.

`falsifier_strength: decided` rows are controls; every other value is a finding.
`deciding_field = null` is allowed and would be the assignment's declared
falsifier; revision 3 has no such row (revision 2 did).

## Non-claims

Structural binding only; no physics or literature verification; literature
pointers are `unresolved_pending_L1`; this worker did not edit the schema, the
map, or any lead-owned path other than the assigned artifact path.
