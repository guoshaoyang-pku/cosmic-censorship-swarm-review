# W031-A2-HARNESS-REPAIR-INDEP-01 — independent verification of the A2 harness repair

Actor `worker-031`, node `A2`, class `GLOBAL`, gate `G-AUDIT`. Read-only; no canonical write.

**Artifact under review**: `evaluation/ablation_harness.py#0fae94bf0190` (v0.2.0-repair),
design `evaluation/ablation_design.yaml#1b2a83ef670b`.

**Verdict**: accept, score 4.0, 0 hard failures — scoped to the harness artifact and its
design-bound synthetic dry run only. No node status, no `validation_status=passed`, no gate verdict.

## What was independently measured

* Producer manifest: 11/11 sha256 recomputed and matching.
* `--self-test`: 21/21, exit 0. Dry run twice, `PYTHONHASHSEED=0`: byte-identical CSV
  (1992f62f0c40) and reports equal modulo `generated_at`.
  The CSV is byte-identical to the producer's design-bound CSV; the report differs from the
  producer's in exactly 2 of 538 leaves (the two `generated_at` stamps).
* Budget match: token spread 0.0101, wall-consumption spread 0.0101, tolerance 0.02/0.02,
  `matched=true`, primary arms token-limited (not wall-limited).
* Marking: `simulated=true`, `run_mode=dry_run_synthetic`, disclaimer present, CSV leading
  columns `simulated,run_mode,harness_sha256`, 5/5 rows marked.
* All four declared matched fields measured; the two unequalisable ones are named in
  `design_deviations` (+`unmatched_declared_fields`).
* Guardrail applied before contrasts; NULL arm is a non-primary control; no universal score.
* Offline: AST import scan finds no network module.
* CLI probes: unmarked output name refused exit 2 with no file created; `--execute` refused
  exit 3; tolerance-violation run exit 1.
* Independent checker `check_a2_indep.py`: 10/10 checks on the genuine run; 8/8 negative
  controls fire (simulated flag, old 0.15 tolerance, constant walls, zeroed CSV hash, silent
  unmatched field, stale harness bytes, unmarked header, end-to-end 0.15 mutant harness).
* Every canonical pin (harness, design, canonical CSVs/reports) unchanged after all runs.

## Prior findings

The harness-side blocking findings of `A2-review-18`, `A2-review-19`, `A2-review-022` and
`A2-review-worker-067` are closed at the pinned bytes (see `report.json`
`prior_finding_disposition`). Not closed by the harness, recorded as owner residues:
R1 design line 172 names the audit harness copy; R2 two declared matched fields cannot be
equalised under token matching (correctly surfaced, not hidden); R3 the map-pinned canonical
dry-run outputs still bind the old harness hash and were not regenerated (CF-12 owner call).

## Non-blocking observation

O1: under a tolerance override, `declared_matched_fields[*].tolerance` (fixed 0.02) can differ
from the effective `token_tolerance` used in `violations`. No effect at the pinned default run.

## Reproduce

```bash
python3 evaluation/ablation_harness.py --self-test
python3 evaluation/ablation_harness.py --dry-run --design evaluation/ablation_design.yaml \
    --outdir artifacts/worker-031/a2_harness_repair_indep/out/run_a
python3 artifacts/worker-031/a2_harness_repair_indep/check_a2_indep.py \
    --report artifacts/worker-031/a2_harness_repair_indep/out/run_a/ablation_dryrun_report.json \
    --csv artifacts/worker-031/a2_harness_repair_indep/out/run_a/ablation_dryrun.csv
```

Falsifier: any byte change of the harness or design voids this review; a re-run at the pinned
bytes that reports `budget_check.matched=false`, constant wall consumption, an unmarked dry-run
row, or an unlisted unmatched declared field falsifies the accept.
