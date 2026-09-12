# worker-041 — F0 independent re-verification (W041-F0-REDISPATCH4-01)

Bounded, read-only verification of the F0 canonical formulation taxonomy at the accepted pins,
plus a consistency check of the companion authoring artifact (REC-3: byte-identity is neither
possible nor required).

## Pins

| artifact | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (canonical F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/formulation_taxonomy.yaml` (companion) | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` |
| `artifacts/formulation/FROZEN.json` (manifest read) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |

## Files

- `run_f0_reverify.py` — deterministic read-only instrument, 126 checks. `--root DIR` verifies a
  sandbox tree; `--expect-mutation --mutation-expects IDS` is the positive-control mode.
- `raw/independent_checks.json` — live run, 126/126 PASS, 0 hard findings, 2 recorded notes.
- `raw/mutation_control.json` + `raw/mutation_control.stdout.txt` — positive control: the same
  instrument run on a sandbox copy with `AF-SCC-C2-VAC-GEN` removed from `class_ids` and its
  `regularity_token` flipped to `C0` fails 6 checks and exits 1.
- `raw/sandbox_taxonomy_consistency.json` — byte-identical re-run of the frozen checker
  `artifacts/formulation/tools/check_taxonomy_consistency.py` in an isolated sandbox
  (same sha256 as the live evidence), proving the published consistency evidence is exactly
  what the current canonical + companion + aliases derive.

## Verdict

`accept` at score 4.0 with no hard failures; recorded as `reviews/F0-review-rev27-a-r4.json`
(a new name, so the earlier pinned verdict `reviews/F0-review-rev27-a.json#4f5c2a874801` is not
overwritten). Two minor notes (F-041-R4-01, F-041-R4-02) and one process escalation
(F-041-R4-03: the supervisor relaunches this completed slot in a loop) are in the verdict file.

No gate verdict, no node status, no `validation_status=passed` is claimed. Nothing under
`research_map/`, `schemas/`, `artifacts/formulation/` or `reviews/` was modified by this run
except the two new files named above.
