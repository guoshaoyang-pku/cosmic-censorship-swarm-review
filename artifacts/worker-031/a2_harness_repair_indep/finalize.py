#!/usr/bin/env python3
"""W031-A2-HARNESS-REPAIR-INDEP-01 finalize: assemble report.json, README.md, CHECKPOINT.json.

Reads only files inside artifacts/worker-031/a2_harness_repair_indep/ plus the pinned
canonical inputs (read-only). Worker measurement only: no canonical write, no node status,
no validation_status=passed, no gate verdict.
"""
import hashlib
import json
import os
import subprocess
import time

D = "artifacts/worker-031/a2_harness_repair_indep"
TASK = "W031-A2-HARNESS-REPAIR-INDEP-01"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")
PIN_HARNESS = "0fae94bf01903ec7b8076a6b11706bc4444b19f98e6d0985e4ac2d1b2921f157"
PIN_DESIGN = "1b2a83ef670b7e757a1a54d4849b49a597d5dc33e9205c0b5b10646d811cfb0a"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


genuine = json.load(open(f"{D}/out/indep_check_genuine.json"))
controls = json.load(open(f"{D}/controls/control_results.json"))
c8 = json.load(open(f"{D}/controls/c8_mut_harness_check.json"))

# prior findings -> disposition (each refuted/closed by an independent check id)
disposition = [
    {"finding": "w018-B1 / w022-B1 / w067-B1: wall-clock matching vacuous (constant wall_clock_s)",
     "closed": True, "check": "I4_matched_budget",
     "evidence": "primary wall_clock_s = [30.0, 30.0, 29.7, 29.76] (non-constant); "
                 "wall_consumption_spread_fraction = 0.0101 <= 0.02; harness selftest "
                 "'wall_consumption_falsifier_fires' (consumption spread 0.485 -> matched=False)"},
    {"finding": "w018-B2 / w022-B2: declared matched fields not measured",
     "closed": True, "check": "I5_declared_fields_measured",
     "evidence": "all 4 design matched_fields measured=True; the 2 unequalisable ones "
                 "(verifier_calls_per_accepted_artifact spread 1.074, human_review_minutes "
                 "spread 3.547) are named in design_deviations and unmatched_declared_fields"},
    {"finding": "w018-B3 / w022-B3 / w067-B2: tolerance 0.15 vs pre-registered 2%",
     "closed": True, "check": "I4_matched_budget + control C8",
     "evidence": "report tolerance = 0.02 for tokens and wall; C8 re-runs a copy with "
                 "token_tolerance/matched_field_tolerance 0.15 and the checker fires I4"},
    {"finding": "w022-B3: the design-named audit harness copy differs from the canonical path",
     "closed": False, "check": "residue R1",
     "evidence": "evaluation/ablation_design.yaml line 172 still names "
                 "artifacts/audit/ablation_harness.py; map/owner path is "
                 "evaluation/ablation_harness.py (owner decision, outside the harness artifact)"},
    {"finding": "HF-A2-19-01: dry run mistakable for a real result / unmarked canonical artifact",
     "closed": True, "check": "I3_simulated_marking",
     "evidence": "report simulated=True, run_mode=dry_run_synthetic, non-empty disclaimer; CSV "
                 "leading columns simulated,run_mode,harness_sha256; 5/5 rows marked; "
                 "unmarked canonical output name refused exit 2 (probe)"},
    {"finding": "HF-A2-19-02: two harness copies / pre-registration not single-sourced",
     "closed": False, "check": "residue R1",
     "evidence": "identical to w022-B3; requires a lead-audit design edit (line 172)"},
    {"finding": "HF-A2-19-03: unquoted 'id: NULL' loader failure",
     "closed": True, "check": "I7_null_control + selftest 'null_arm_id_normalized'",
     "evidence": "design NULL normalised to string; report has 5 arms with random_iid_null "
                 "is_null=True and is_primary=False"},
    {"finding": "w067-N3: envelope vs consumption ambiguity",
     "closed": True, "check": "I4_matched_budget",
     "evidence": "both readings computed (wall_consumption_spread_fraction and wall_clock_s "
                 "spread both 0.0101); wall_match_basis=consumption reported; selftest fires "
                 "when the two readings diverge (envelope matched=True, consumption matched=False)"},
    {"finding": "19-06: guardrail not applied before contrasts",
     "closed": True, "check": "I6_guardrail_first + selftest 'guardrail_applied_first'",
     "evidence": "primary_endpoint.guardrail_applied=True; flagged arms truncated to 0 before "
                 "the endpoint"},
    {"finding": "19: unreliable exit status",
     "closed": True, "check": "CLI probes",
     "evidence": "selftest 0, dry run 0, guard refusal 2 (no file created), --execute refusal 3, "
                 "tolerance-violation dry run 1"},
]

report = {
    "schema": "w031-a2-harness-repair-indep/v1",
    "task_id": TASK,
    "actor": "worker-031",
    "node_id": "A2",
    "class_id": "GLOBAL",
    "gate": "G-AUDIT",
    "created_at": NOW,
    "authority": "worker measurement only; read-only on every canonical path; no gate verdict, "
                 "no node status, no validation_status=passed, no canonical write",
    "question": "Does evaluation/ablation_harness.py at 0fae94bf0190 (v0.2.0-repair) actually "
                "close the four independent revise verdicts' harness-side blocking findings, "
                "and does its design-bound synthetic dry run reproduce off the producer's machine?",
    "pins": {
        "evaluation/ablation_harness.py": sha("evaluation/ablation_harness.py"),
        "evaluation/ablation_design.yaml": sha("evaluation/ablation_design.yaml"),
        "evaluation/ablation.csv": sha("evaluation/ablation.csv"),
        "evaluation/ablation_dryrun.csv": sha("evaluation/ablation_dryrun.csv"),
        "evaluation/ablation_report.json": sha("evaluation/ablation_report.json"),
        "evaluation/ablation_dryrun_report.json": sha("evaluation/ablation_dryrun_report.json"),
        "artifacts/worker-020/a2_harness_repair_20260912T0116/manifest.json":
            sha("artifacts/worker-020/a2_harness_repair_20260912T0116/manifest.json"),
        "reviews/A2-review-18.json": sha("reviews/A2-review-18.json"),
        "reviews/A2-review-19.json": sha("reviews/A2-review-19.json"),
        "reviews/A2-review-022.json": sha("reviews/A2-review-022.json"),
        "reviews/A2-review-worker-067.json": sha("reviews/A2-review-worker-067.json"),
    },
    "pin_guard_start_end_equal": json.load(open(f"{D}/pins_end.json"))["all_unchanged"],
    "method": [
        "1. Independently recomputed every sha256 in the producer manifest (11/11 match).",
        "2. Re-ran --self-test (21/21, exit 0) and the design-bound dry run twice with "
        "PYTHONHASHSEED=0 into a fresh outdir.",
        "3. Wrote a separate stdlib-only checker (check_a2_indep.py, does not import the harness) "
        "with 10 checks and 8 negative controls.",
        "4. Probed the CLI guards (unmarked output name, --execute, tolerance override).",
        "5. Re-measured every canonical pin after the runs (all unchanged).",
    ],
    "reproduction": {
        "csv_byte_identical_to_producer": True,
        "csv_sha256": sha(f"{D}/out/run_a/ablation_dryrun.csv"),
        "producer_csv_sha256": "1992f62f0c40dffe1d76ddbe60afc44efec996f0453a71d81b736ff769a4ce60",
        "report_leaf_diff_vs_producer": 2,
        "report_diff_fields": ["/generated_at", "/provenance/generated_at"],
        "report_leaves_total": 538,
        "determinism_two_runs_byte_identical": True,
        "note": "the only report difference from the producer's design-bound report is the "
                "generated_at timestamp; all 536 numeric/structural leaves are equal",
    },
    "checks": genuine["checks"],
    "checks_pass": f"{genuine['n_pass']}/{genuine['n_total']}",
    "controls": controls,
    "controls_all_fire": all(c["fired"] for c in controls),
    "end_to_end_regression_control_C8": {
        "mutation": "copy of the harness with token_tolerance and matched_field_tolerance "
                    "restored to 0.15 (the pre-repair defect)",
        "mutant_sha256": sha(f"{D}/controls/mut_harness_tol015b.py"),
        "checker_verdict": c8["verdict"],
        "failing_checks": [c["id"] for c in c8["checks"] if not c["pass"]],
        "detail": [c["detail"] for c in c8["checks"] if c["id"] == "I4_matched_budget"][0],
    },
    "cli_probes": {
        "self_test_exit": 0,
        "dry_run_exit": 0,
        "unmarked_output_name_exit": 2,
        "unmarked_output_file_created": False,
        "marked_output_name_exit": 0,
        "execute_exit": 3,
        "tolerance_override_0.001_exit": 1,
        "tolerance_override_report": {
            "budget_matched": False,
            "primary_comparison_valid": False,
            "violation": "primary token consumption spread 0.0101 > tolerance 0.001",
        },
    },
    "prior_finding_disposition": disposition,
    "non_blocking_observations": [
        {"id": "O1",
         "observation": "budget_check.declared_matched_fields[*].tolerance reports the fixed "
                        "matched_field_tolerance (DEFAULTS line 121, 0.02) while the primary "
                        "matched-budget violation test uses the effective token_tolerance "
                        "(DEFAULTS line 118). Under a CLI/design override the two fields can "
                        "diverge: my --token-tolerance 0.001 probe reports tolerance 0.02 in the "
                        "field but '> tolerance 0.001' in violations.",
         "impact": "none for the pinned genuine run (both are 0.02); only a reporting nuance if a "
                   "future run overrides token_tolerance without also changing "
                   "matched_field_tolerance.",
         "falsifier": "a run where the effective token_tolerance != the reported "
                      "declared_matched_fields[*].tolerance AND the report does not list the "
                      "override in config/provenance"}
    ],
    "residues_for_design_owner": [
        {"id": "R1", "item": "evaluation/ablation_design.yaml line 172 names "
                              "artifacts/audit/ablation_harness.py, not the canonical "
                              "evaluation/ablation_harness.py",
         "owner": "astra-lead-audit", "blocks_harness_accept": False},
        {"id": "R2", "item": "verifier_calls_per_accepted_artifact and human_review_minutes are "
                              "declared matched but cannot be equalised under token matching "
                              "across accuracy-different arms; correctly surfaced as "
                              "design_deviations",
         "owner": "astra-lead-audit", "blocks_harness_accept": False},
        {"id": "R3", "item": "the map-pinned canonical dry-run outputs (evaluation/ablation.csv "
                              "ee3aa6cb97d0 et al.) still bind the old harness hash and were not "
                              "regenerated at 0fae94bf0190",
         "owner": "artifact owner / lead-audit (CF-12)", "blocks_harness_accept": False},
    ],
    "verdict": "accept",
    "verdict_scope": "the harness artifact evaluation/ablation_harness.py#0fae94bf0190 and its "
                     "design-bound synthetic dry run only",
    "score": 4.0,
    "hard_failures": [],
    "does_not_claim": [
        "no node A2 completion or status transition",
        "no validation_status=passed",
        "no G-AUDIT gate verdict",
        "no claim about real model behaviour: the dry run is synthetic",
        "no claim that the design-side residues R1-R3 are resolved",
    ],
    "falsifier": "Any byte change of evaluation/ablation_harness.py or "
                 "evaluation/ablation_design.yaml voids this review. Re-running the two dry runs "
                 "at the pinned bytes must reproduce the byte-identical CSV and a report equal "
                 "modulo generated_at; the genuine checker must stay 10/10 and every control "
                 "C1-C8 must keep firing; a run at the pinned bytes reporting "
                 "budget_check.matched=false, constant wall consumption, an unmarked dry-run row, "
                 "or an unlisted unmatched declared field falsifies the accept.",
    "next_falsifier": "Re-measure the pins and re-run check_a2_indep.py plus the dry runs; if the "
                      "design owner edits line 172 or the map pin is regenerated at the new "
                      "harness hash, re-run this review at the new design/output pins.",
}

json.dump(report, open(f"{D}/report.json", "w"), indent=1, sort_keys=True)

# README
readme = f"""# W031-A2-HARNESS-REPAIR-INDEP-01 — independent verification of the A2 harness repair

Actor `worker-031`, node `A2`, class `GLOBAL`, gate `G-AUDIT`. Read-only; no canonical write.

**Artifact under review**: `evaluation/ablation_harness.py#0fae94bf0190` (v0.2.0-repair),
design `evaluation/ablation_design.yaml#1b2a83ef670b`.

**Verdict**: accept, score 4.0, 0 hard failures — scoped to the harness artifact and its
design-bound synthetic dry run only. No node status, no `validation_status=passed`, no gate verdict.

## What was independently measured

* Producer manifest: 11/11 sha256 recomputed and matching.
* `--self-test`: 21/21, exit 0. Dry run twice, `PYTHONHASHSEED=0`: byte-identical CSV
  ({report['reproduction']['csv_sha256'][:12]}) and reports equal modulo `generated_at`.
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
python3 evaluation/ablation_harness.py --dry-run --design evaluation/ablation_design.yaml \\
    --outdir artifacts/worker-031/a2_harness_repair_indep/out/run_a
python3 artifacts/worker-031/a2_harness_repair_indep/check_a2_indep.py \\
    --report artifacts/worker-031/a2_harness_repair_indep/out/run_a/ablation_dryrun_report.json \\
    --csv artifacts/worker-031/a2_harness_repair_indep/out/run_a/ablation_dryrun.csv
```

Falsifier: any byte change of the harness or design voids this review; a re-run at the pinned
bytes that reports `budget_check.matched=false`, constant wall consumption, an unmarked dry-run
row, or an unlisted unmatched declared field falsifies the accept.
"""
open(f"{D}/README.md", "w").write(readme)

# checkpoint
files = ["report.json", "README.md", "check_a2_indep.py", "pins_start.json", "pins_manifest_check.json",
         "pins_end.json", "controls/control_results.json", "out/indep_check_genuine.json",
         "out/run_a/ablation_dryrun_report.json", "out/run_a/ablation_dryrun.csv",
         "out/run_b/ablation_dryrun_report.json", "out/run_b/ablation_dryrun.csv"]
ck = {
    "schema": "w031-a2-harness-repair-indep-checkpoint/v1",
    "task_id": TASK, "actor": "worker-031", "node_id": "A2", "class_id": "GLOBAL",
    "gate": "G-AUDIT", "created_at": NOW,
    "verdict": "accept", "score": 4.0, "checks": f"{genuine['n_pass']}/{genuine['n_total']}",
    "controls_all_fire": True, "canonical_pins_unchanged": True,
    "artifact_hashes": {f: sha(f"{D}/{f}") for f in files},
    "report_sha256": sha(f"{D}/report.json"),
    "falsifier": report["falsifier"],
    "authority": "worker measurement only; no gate verdict, no node status, no canonical write",
}
json.dump(ck, open(f"{D}/CHECKPOINT.json", "w"), indent=1, sort_keys=True)
for k in ("report.json", "README.md", "CHECKPOINT.json"):
    print(k, sha(f"{D}/{k}"))
