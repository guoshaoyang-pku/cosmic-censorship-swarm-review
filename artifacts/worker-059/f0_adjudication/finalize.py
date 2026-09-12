#!/usr/bin/env python3
"""Finalize W059-F0-ADJUDICATE-01: adjudication_report.json, checkpoint, hashes.json."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = ROOT / "artifacts/worker-059/f0_adjudication"
CST = timezone(timedelta(hours=8))
now = datetime.now(CST).isoformat(timespec="seconds")
REVIEWED = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


artifacts = [
    D / "adjudicate_f0.py",
    D / "adjudication_checks.json",
    D / "blindspot_test.py",
    D / "blindspot_test/blindspot_result.json",
    D / "canonical_validate_taxonomy.json",
    D / "canonical_validate_taxonomy.stdout.txt",
    D / "canonical_classsep_findings.json",
    D / "classsep_regression.stdout.txt",
    D / "review_F0_276009f4.json",
    D / "README.md",
    D / "snapshot/f0.276009f4f63d.yaml",
]
hashes = {rel(p): sha(p) for p in artifacts}
(D / "hashes.json").write_text(json.dumps(
    {"task_id": "W059-F0-ADJUDICATE-01", "created_at": now, "files": hashes}, indent=2) + "\n")

checks = json.loads((D / "adjudication_checks.json").read_text())
blind = json.loads((D / "blindspot_test/blindspot_result.json").read_text())
canonical_f0 = sha(ROOT / "research_map/formulation_taxonomy.yaml")
drift = {
    "canonical_f0_sha256_at_finalize": canonical_f0,
    "matches_reviewed": canonical_f0 == REVIEWED,
    "checked_at": now,
    "authoring_f0_sha256_at_finalize": sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml"),
}

report = {
    "task_id": "W059-F0-ADJUDICATE-01",
    "actor": "worker-059",
    "created_at": now,
    "node_id": "F0",
    "gate": "G-F0",
    "class_ids": checks["adjudication"]["w082_f01"]["measurements"] and [
        "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "reviewed_path": "research_map/formulation_taxonomy.yaml",
    "reviewed_sha256": REVIEWED,
    "reviewed_snapshot": rel(D / "snapshot/f0.276009f4f63d.yaml"),
    "verdict": "revise",
    "score": 3.0,
    "adjudication": checks["adjudication"],
    "measured_green_baseline": checks["measured_green_baseline"],
    "tool_blindspot": {
        "runs": blind["runs"],
        "static_tool_analysis": blind["static_tool_analysis"],
        "conclusion": blind["conclusion"],
    },
    "canonical_support": {
        "validate_taxonomy": json.loads((D / "canonical_validate_taxonomy.json").read_text()),
        "classsep_findings_for_text": json.loads((D / "canonical_classsep_findings.json").read_text())["findings"],
        "classsep_regression_exit_and_tail": (D / "classsep_regression.stdout.txt").read_text().strip().splitlines()[-4:],
    },
    "drift_guard": drift,
    "artifact_hashes": hashes,
    "global_state_mutated": False,
    "authority_note": "worker review only; no node completion, no validation_status=passed, no gate verdict",
}
(D / "adjudication_report.json").write_text(json.dumps(report, indent=2) + "\n")

review_p = D / "review_F0_276009f4.json"
checkpoint = {
    "checkpoint_id": "w059-ckpt-f0adj-20260912T0028",
    "task_id": "W059-F0-ADJUDICATE-01",
    "actor": "worker-059",
    "created_at": now,
    "node_id": "F0",
    "gate": "G-F0",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
    "status": "active",
    "scope": "worker-level checkpoint (artifacts/worker-059 only; no runtime/state or map mutation)",
    "reviewed_sha256": REVIEWED,
    "review_artifact": rel(review_p),
    "review_artifact_sha256": sha(review_p),
    "verdict": "revise",
    "score": 3.0,
    "hard_failure_ids": ["HF-059-F0-01", "HF-059-F0-02", "HF-059-F0-03"],
    "finding_ids": ["F-059-F0-04", "F-059-F0-05", "F-059-F0-06", "F-059-F0-07", "F-059-F0-08"],
    "artifact_hashes": hashes,
    "drift_guard": drift,
    "next_falsifier": checks["adjudication"]["w082_f01"]["claim"] and
        ("A canonical F0 revision in which all four conclusion texts bind an explicit quantifier "
         "before the data and the AF-WCC-SCALAR-SPH 'equivalently' is sourced or moved to "
         "candidate_consequences; or a demonstration that the bare 'generic data' phrasing is an "
         "intended descriptor-level placeholder exempt from field_vocabulary.genericity_kind.rule. "
         "Hash drift of research_map/formulation_taxonomy.yaml voids this checkpoint immediately."),
    "global_state_mutated": False,
}
(D / "checkpoint_w059_f0adj.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
hashes[rel(D / "checkpoint_w059_f0adj.json")] = sha(D / "checkpoint_w059_f0adj.json")
hashes[rel(D / "adjudication_report.json")] = sha(D / "adjudication_report.json")
hashes[rel(D / "hashes.json")] = sha(D / "hashes.json")
print(json.dumps({"hashes": hashes, "drift": drift}, indent=1))
