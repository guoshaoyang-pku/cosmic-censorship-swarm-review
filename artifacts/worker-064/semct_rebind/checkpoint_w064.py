#!/usr/bin/env python3
"""Write the W064-SEMCT-REBIND-01 checkpoint.

Writes runtime/state/w064_semct_checkpoint.json and appends
runtime/state/w064_checkpoints.jsonl.  Hashes are re-measured at checkpoint time;
canonical hashes are recorded so later drift can be detected against this audit.

Usage: python3 checkpoint_w064.py --instance-id <runtime instance id>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
REPO = BUNDLE.parents[2]
CST = timezone(timedelta(hours=8))
STATE = REPO / "runtime" / "state"
TASK = "W064-SEMCT-REBIND-01"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance-id", default="worker-064-20260912T002404-968807")
    args = ap.parse_args()

    pinned = {}
    for ln in (BUNDLE / "manifest.sha256").read_text().splitlines():
        h, name = ln.split(maxsplit=1)
        pinned[name.strip()] = h
    bad = [n for n, h in pinned.items() if sha(BUNDLE / n) != h]
    if bad:
        raise SystemExit(f"FAIL: bundle hash mismatch at checkpoint: {bad}")

    report = json.loads((BUNDLE / "report.json").read_text())
    report_sha = pinned["report.json"]
    canonical_now = {
        "research_map/formulation_taxonomy.yaml": sha(REPO / "research_map/formulation_taxonomy.yaml"),
        "schemas/af_scc_c0_vacuum.yaml": sha(REPO / "schemas/af_scc_c0_vacuum.yaml"),
        "schemas/af_scc_c2_vacuum.yaml": sha(REPO / "schemas/af_scc_c2_vacuum.yaml"),
        "schemas/af_wcc_vacuum.yaml": sha(REPO / "schemas/af_wcc_vacuum.yaml"),
        "schemas/semantic_contract_tests/manifest.json": sha(REPO / "schemas/semantic_contract_tests/manifest.json"),
    }
    drift = {
        "C0": canonical_now["schemas/af_scc_c0_vacuum.yaml"] != report["measured"]["canonical"]["AF-SCC-C0-VAC-GEN"],
        "C2": canonical_now["schemas/af_scc_c2_vacuum.yaml"] != report["measured"]["canonical"]["AF-SCC-C2-VAC-GEN"],
        "F1": canonical_now["schemas/af_wcc_vacuum.yaml"] != report["measured"]["canonical"]["AF-WCC-VAC-GEN"],
        "suite_manifest": canonical_now["schemas/semantic_contract_tests/manifest.json"] != report["measured"]["suite_manifest"],
    }

    ckpt = {
        "checkpoint_id": f"w064-semct-ckpt-{now().replace(':', '').replace('+', 'p')}",
        "task_id": TASK,
        "actor": "worker-064",
        "instance_id": args.instance_id,
        "created_at": now(),
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "status": "worker_task_complete_no_node_transition",
        "verdict": "REBIND_REQUIRED_VALIDITY_FALSE",
        "artifacts": {f"artifacts/worker-064/semct_rebind/{k}": v for k, v in sorted(pinned.items())},
        "canonical_hashes_at_checkpoint": canonical_now,
        "canonical_drift_since_audit": drift,
        "measured_results": {
            "run_original_exit": report["run_original"]["exit"],
            "run_original_integrity_errors": report["run_original"]["error_count"],
            "run_rebound_exit": report["run_rebound"]["exit"],
            "mutants_structural_caught": report["run_rebound"]["summary"]["structural_caught"],
            "mutants_semantic_baseline_caught": report["run_rebound"]["summary"]["semantic_baseline_caught"],
            "mutants_semantic_hardened_caught": report["run_rebound"]["summary"]["semantic_hardened_caught"],
            "escaped_adopted_stages": report["escaped_adopted_stages"],
            "frozen_controls_accepted_both_stages": report["run_rebound"]["summary"]["controls_accepted_both_stages"],
            "canonical_controls_accepted": report["run_rebound"]["summary"]["conforming_canonical_accepted_both_stages"],
            "valid_for_calibration": report["run_rebound"]["validity"]["valid_for_calibration"],
            "determinism_38_of_38": json.loads((BUNDLE / "determinism_check.json").read_text())["deterministic"],
            "stage_tools_unchanged_since_00_14_40": report["stage_tools_unchanged_since_00_14_40"],
        },
        "evidence_refs": [
            f"artifacts/worker-064/semct_rebind/report.json#{report_sha[:12]}",
            f"artifacts/worker-064/semct_rebind/original_run.json#{pinned['original_run.json'][:12]}",
            f"artifacts/worker-064/semct_rebind/rebound_observed.json#{pinned['rebound_observed.json'][:12]}",
            f"artifacts/worker-064/semct_rebind/rebind_patch.json#{pinned['rebind_patch.json'][:12]}",
            f"artifacts/worker-064/semct_rebind/determinism_check.json#{pinned['determinism_check.json'][:12]}",
        ],
        "falsifier": report["findings"][0]["falsifier"] + " " + report["findings"][3]["falsifier"],
        "next_falsifier": (
            "After the lead applies rebind_patch.json and resolves ADJ-CONTROL-STALENESS, re-run "
            "semct_rebind_audit.py and determinism_check.py; expect run A exit 0 (or run B exit 0 with "
            "valid_for_calibration=true), frozen controls 3/3 accepted, canonical controls 3/3 accepted, "
            "and unchanged 32/11/32 mutant counts."
        ),
        "not_claimed": report["not_claimed"],
        "outbox": "comms/outbox/worker-064.jsonl",
        "outbox_event_ids": [
            "w064-semct-01-artifact-report",
            "w064-semct-01-artifact-original-run",
            "w064-semct-01-artifact-rebound-run",
            "w064-semct-01-artifact-rebind-patch",
            "w064-semct-01-artifact-determinism",
            "w064-semct-01-review-suite",
            "w064-semct-01-claim",
            "w064-semct-01-blocker",
            "w064-semct-01-status",
        ],
        "summary": (
            "Independent rev25 rebind audit of schemas/semantic_contract_tests: canonical manifest exits 2 "
            "with exactly 3 stale conforming-canonical pins; 3-pin rebind restores execution and reproduces "
            "00:14:40 exactly (structural 32/32, baseline 11/32, hardened 32/32, 0 escapes, 38/38 "
            "deterministic); valid_for_calibration stays false on ADJ-CONTROL-STALENESS. Worker-level "
            "completion only; no gate verdict and no canonical file modified."
        ),
    }

    STATE.mkdir(parents=True, exist_ok=True)
    ckpt_path = STATE / "w064_semct_checkpoint.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=1) + "\n")
    with (STATE / "w064_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(ckpt, sort_keys=True) + "\n")
    print(f"checkpoint -> {ckpt_path.relative_to(REPO)}  drift={drift}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
