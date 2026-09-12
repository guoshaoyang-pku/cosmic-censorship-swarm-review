# A0 rubric — independent review (worker-008)

- target: `evaluation_rubric.yaml` node A0, gate G-AUDIT
- target sha256: `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` (13969 bytes)
- reviewer: worker-008 (not the author `lead-audit`)
- verdict: **revise**  score: **3.25**
- generated: 2026-09-12T00:18:58+08:00

## Checks

| check | status | detail |
|---|---|---|
| A0-C1 | pass | rubric bytes, map measurement and registry agree at one sha256 |
| A0-C2 | pass | rubric frozen_classes equals the canonical four; all binding fields present; no unknown AF-* token |
| A0-C3 | warn | no explicit evidence rule for literature (block starts line 25), numerics (block starts line 32), formalization (block starts line 38); only schema_formulation names `evidence:` (line 23) |
| A0-C4 | pass | unique ids with severity+detector; severity counts {'critical': 7, 'major': 6, 'minor': 1} |
| A0-C5 | warn | no target for metric(s) novel_accepted_coverage (line 282); 7 metrics otherwise diagnostic and per-type |
| A0-C6 | pass | every gate has criteria/scope/verdict; every non-machine acceptance item is a named human-adjudication item |
| A0-C7 | warn | map gate G-F0 (taxonomy, research_map.json#gates.G-F0) has no rubric gate row; class-id binding is covered by frozen_classes + metric class_binding, but the taxonomy gate's disjointness test is not represented in the rubric |
| A0-C8 | fail | declared validator has never been recorded as run (evaluation_rubric.yaml:48 last_run/report_sha256 null); the rubric's own line 46 says a rubric with no passing self-test is not a gate |

## Blocking finding

- declared validator has never been recorded as run (evaluation_rubric.yaml:48 last_run/report_sha256 null); the rubric's own line 46 says a rubric with no passing self-test is not a gate

## Concrete unblock

- A0-C8 (blocking): populate evaluation_rubric.yaml:45-50 `validation` after defining what 'passing self-test' means for artifacts/audit/audit_run.py, then record last_run, last_run_result and report_sha256. Note audit_run.py exits 0 with 9 critical live-corpus findings unless --fail-on-critical is passed, so the pass predicate must be stated.
- A0-C3 (minor): add an explicit `evidence:` line to the literature (line 25), numerics (line 32) and formalization (line 38) verifier blocks, as schema_formulation has (line 23).
- A0-C5 (minor): give novel_accepted_coverage (line 282) a target, as the other 6 metrics have.
- A0-C7 (minor): add a G-F0 row to `gates` or state that taxonomy disjointness is covered by metric class_binding; the map carries G-F0 and the rubric does not.

## Evidence

- `evaluation_rubric.yaml#d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885`
- `research_map/formulation_taxonomy.yaml#276009f4f63d`
- `research_map/research_map.json#4d8291c9a9ae`
- `research_map/events.schema.json`
- `artifacts/worker-008/a0_rubric_review/a0_check_report.json#25987cbd8c691d8210a16459c92559527ebc91472d233b352bf271c471301436`

## Declared validator (`artifacts/audit/audit_run.py`) run

- report: `artifacts/worker-008/a0_rubric_review/audit_run_out/LATEST.json` sha256 `bfefe70164571058`
- rubric_sha256 at run: `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885`
- live-corpus summary: `{"by_hf": {"HF-02": 8, "HF-03": 1, "HF-06": 1, "HF-13": 9, "HF-14": 1}, "by_severity": {"critical": 9, "major": 2, "minor": 9}, "critical": 9, "total": 20}`
- live-corpus gates: `{"G-AUDIT": "fail", "G-FORM": "pending", "G-LIT": "fail", "G-NUM": "pending"}`
- this is an enforcement run over the live workspace, not a recorded rubric self-test;
  it does not write `validation.last_run` and its critical findings belong to other nodes.

## Falsifier

- a recorded audit_run.py run with last_run_result pass and report_sha256 in evaluation_rubric.yaml at this sha256 falsifies A0-C8; a canonical taxonomy with different class_ids, or an unknown AF-* token in the rubric, falsifies A0-C2
- next: re-run this checker after the owner records the self-test; if A0-C8 passes and no check fails, the verdict moves to accept at the same hash

## Limits

- structural/semantic conformance only: physical correctness of the class definitions is not assessed here
- verdict is evidence for the audit lead; worker events cannot set gate verdicts
