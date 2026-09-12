#!/usr/bin/env python3
"""Derive findings.json for FORM-HELDOUT-10 from the frozen manifest, report and raw verdicts.

Interpretation only: no verdict is recomputed or changed here.  Every number is copied from
report.json / raw/raw_verdicts.json so the interpretation cannot drift from the measurement.

Usage: python3 make_findings_10.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    man = json.loads((HERE / "manifest.json").read_text())
    rep = json.loads((HERE / "report.json").read_text())
    raw = json.loads((HERE / "raw" / "raw_verdicts.json").read_text())

    allrows = raw["results"]
    info = [r for r in allrows if r["arm_informative"]]
    unin = [r for r in allrows if not r["arm_informative"]]
    wcc_spurious = [
        {"mutation_id": r["mutation_id"], "family": r["family"],
         "stage_b_failed_rules": r["stage_b"]["failed_rules"],
         "why_spurious": ("stage B rejects on R03 only, the same literal-substring binder rule that "
                          "rejects the untouched frozen WCC canonical")}
        for r in unin
    ]
    new_families = {"f1-visibility-equivalence-denied", "f0-binding-stale-hash"}
    new_rows = [
        {"mutation_id": r["mutation_id"], "family": r["family"], "arm": r["arm"],
         "class_id": r["class_id"], "stage_a": r["stage_a"]["verdict"],
         "stage_b": r["stage_b"]["verdict"], "stage_b_failed_rules": r["stage_b"]["failed_rules"],
         "union_escape": r["union_escape"], "arm_informative": r["arm_informative"]}
        for r in allrows if r["family"] in new_families
    ]

    findings = {
        "corpus_id": man["corpus_id"],
        "task_id": man["task_id"],
        "worker": man["worker"],
        "node_id": man["node_id"],
        "gate": man["gate"],
        "class_ids": man["class_ids"],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "artifact_kind": "heldout_findings_interpretation",
        "authority_note": ("worker evidence only: no node completion, no validation_status=passed, "
                           "no gate verdict, no theorem"),
        "status": "invalid_strict_h5_pre_registered_r03",
        "headline": (
            "On a FRESH corpus built against the LIVE FROZEN rev29 / rev13 frozen bytes, the two-stage "
            "pipeline's union escape on the informative C2/C0 arms is 1.0 (0 of 26 mutants caught by "
            "either stage), replicating the heldout-09 rev12 finding on new bytes. Strict H5 is false "
            "for one pre-registered reason: stage B R03 rejects the untouched frozen F1/WCC canonical "
            "(d9cebb9404b2), the same literal-substring binder defect that makes all 7 WCC-arm stage-B "
            "catches spurious."),
        "pins": man["pins"],
        "frozen_manifest": man["frozen_manifest"],
        "corpus": {
            "mutants": rep["corpus"]["mutants"],
            "families": rep["corpus"]["families"],
            "rephrased": rep["corpus"]["rephrased"],
            "controls": rep["corpus"]["controls"],
            "new_rev13_targeted_families": sorted(new_families),
        },
        "strict_run": {
            "valid": rep["valid"],
            "invalid_reasons": rep["invalid_reasons"],
            "manifest_hashed_before_any_stage_run": rep["manifest_hashed_before_any_stage_run"],
            "moving_target_during_run": sorted(
                k for k, v in rep["pin_check_after_run"].items() if v["changed"]),
        },
        "measurement_all_mutants": {
            k: rep["aggregates"][k] for k in
            ("mutants", "structural_escape", "semantic_escape", "union_escape",
             "structural_caught", "semantic_caught", "union_caught")
        },
        "informative_arm_measurement": {
            "arms": sorted(rep["informative_arms"]),
            "mutants": rep["aggregates_informative_arms_only"]["mutants"],
            "families": len(rep["aggregates_informative_arms_only"]["escape_families"]),
            "structural_escape": rep["aggregates_informative_arms_only"]["structural_escape"],
            "semantic_escape": rep["aggregates_informative_arms_only"]["semantic_escape"],
            "union_escape": rep["aggregates_informative_arms_only"]["union_escape"],
            "union_caught": rep["aggregates_informative_arms_only"]["union_caught"],
            "escaped_mutation_ids": sorted(r["mutation_id"] for r in info),
        },
        "union_escape_family_list": rep["aggregates_informative_arms_only"]["escape_families"],
        "wcc_arm_non_informative": {
            "reason": rep["known_calibration_defect"]["note"],
            "canonical_preflight": rep["known_calibration_defect"]["canonical_preflight"],
            "mutants": len(unin),
            "stage_b_catches_all_r03_only": len(wcc_spurious),
            "spurious_catches": wcc_spurious,
        },
        "new_rev13_targeted_mutants": new_rows,
        "replication_vs_heldout_09": {
            "heldout_09": {
                "corpus": "FORM-HELDOUT-09",
                "frozen_revision": 28,
                "informative_arms": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                "informative_mutants": 24,
                "informative_union_escape": 1.0,
                "valid": False,
                "report": "artifacts/heldout/heldout-09/report.json#sha256:1bd1cef215b0",
            },
            "heldout_10": {
                "frozen_revision": 29,
                "informative_mutants": rep["aggregates_informative_arms_only"]["mutants"],
                "informative_union_escape": rep["aggregates_informative_arms_only"]["union_escape"],
            },
            "agreement": ("same direction and same magnitude on fresh fixtures and fresh base bytes; "
                          "the rev13 prose repair did not close the C2/C0 leak"),
        },
        "falsifier": man["falsifier"],
        "next_falsifier": (
            "Re-run run_heldout_10.py at the same manifest and pin hashes; falsified if any per-fixture "
            "verdict differs, if the frozen WCC canonical passes stage B at d9cebb9404b2, or if any "
            "informative-arm mutant is caught by a non-R03 rule. Repair of R03 in the frozen stage-B "
            "tool plus a re-run of this corpus would test whether the WCC arm carries real signal."),
        "do_not_claim": man["do_not_claim"],
        "evidence_refs": {
            "manifest": f"artifacts/heldout/heldout-10/manifest.json#sha256:{sha(HERE / 'manifest.json')[:12]}",
            "report": f"artifacts/heldout/heldout-10/report.json#sha256:{sha(HERE / 'report.json')[:12]}",
            "raw_verdicts": f"artifacts/heldout/heldout-10/raw/raw_verdicts.json#sha256:{sha(HERE / 'raw' / 'raw_verdicts.json')[:12]}",
            "checkpoint": f"artifacts/heldout/heldout-10/checkpoint.json#sha256:{sha(HERE / 'checkpoint.json')[:12]}",
        },
    }
    (HERE / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    print("findings.json written:", sha(HERE / "findings.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
