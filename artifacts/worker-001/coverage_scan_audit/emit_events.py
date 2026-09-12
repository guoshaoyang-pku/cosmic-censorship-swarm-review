#!/usr/bin/env python3
"""Emit W001-COVERAGE-SCAN-01 events to comms/outbox/worker-001.jsonl.

Every event is validated with research_map.schemas.validate_event before append; the script
refuses to write anything if one fails. Idempotent: skips event_ids already present.
Does NOT run comms.py ingest (controller-owned), does NOT touch research_map.json.
"""
from __future__ import annotations
import json
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

OUT = REPO / "comms/outbox/worker-001.jsonl"
NOW = "2026-09-12T00:50:30+08:00"
TASK = "W001-COVERAGE-SCAN-01"
CLS = "AF-SCC-C2-VAC-GEN"
CLS_ALL = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
BASE = "artifacts/worker-001/coverage_scan_audit"
PIN = {
    "report": f"{BASE}/evidence/report.json#9b75f98dc491",
    "script": f"{BASE}/audit_coverage_scan.py#92fe0640c2f5",
    "readme": f"{BASE}/README.md#b3be19b92bae",
    "report_full": "9b75f98dc491e5c963b549c084589b8a4781cb3c01389d79d5d9629dd30d93ce",
    "script_full": "92fe0640c2f5cc11123fda51073afcc9d9d361695a4c6bce1e9d3d813d50762c",
    "readme_full": "b3be19b92bae3db9fc9afc87d65f264c2bb3279345bf1c069f3a9d32571eaacb",
}
EVIDENCE = [
    PIN["report"], PIN["script"], PIN["readme"],
    "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
    "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
    "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
    "reviews/F1-review-088-rev12.json#c41daebeba77",
    "reviews/F1-review-088-rev12-amended.json#f49f1c2c4f5a",
    "comms/outbox/worker-089.jsonl#c7c26354373c",
]

events = [
    {
        "event_id": "w001-covscan-artifact-report-20260912T005030+0800",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-001",
        "node_id": "F2a",
        "artifact_type": "coverage_accounting_reconciliation",
        "path": f"{BASE}/evidence/report.json",
        "sha256": PIN["report_full"],
        "validation_status": "unverified",
        "class_ids": CLS_ALL,
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": ("Hash-pinned reconciliation of review_coverage() against the accepted review "
                    "stream: DIVERGENCE, 4 gate-critical invisible accepts, 1 withdrawn accept "
                    "counted, 7/7 controls, drift clean."),
    },
    {
        "event_id": "w001-covscan-artifact-harness-20260912T005030+0800",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-001",
        "node_id": "F2a",
        "artifact_type": "reproduction_harness",
        "path": f"{BASE}/audit_coverage_scan.py",
        "sha256": PIN["script_full"],
        "validation_status": "unverified",
        "class_ids": CLS_ALL,
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": ("Imports the controller's own review_coverage(); exit 0 verdict / 3 drift / "
                    "4 control failure; 7 seeded controls through the real scan function."),
    },
    {
        "event_id": "w001-covscan-claim-20260912T005030+0800",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-001",
        "class_id": CLS,
        "class_ids": CLS_ALL,
        "node_id": "F2a",
        "gate": "G-FORM",
        "task_id": TASK,
        "statement": (
            "At the measured hashes of 2026-09-12T00:48:41+08:00 (F1 cce9c60146d6, F2a "
            "5476a3f2c6bc, F2b 55d0a1ea9bda, F0 0abb9ed8a961), the controller's advisory "
            "review_coverage() scan misstates gate-accept coverage: (a) 4 gate-critical full "
            "accepts present in research_map/events.jsonl are invisible to it (worker-089 F2a "
            "5476a3f2c6bc and F2b 55d0a1ea9bda, worker-061 F1 cce9c60146d6, worker-087 F0 "
            "0abb9ed8a961); (b) it counts reviews/F1-review-088-rev12.json (accept) although the "
            "same reviewer's later amended file withdraws it (revise), so F1's scan coverage "
            "['worker-088'] is wrong in both directions; (c) F2a's gate reason prints 0 accepts "
            "while the accepted stream has 1 live full accept (worker-089). Causes: bodies absent "
            "from reviews/*.json, path#hash target ids unresolved by TARGET_ALIASES, and no "
            "latest-verdict supersession."),
        "conclusion_type": "numerical_evidence",
        "assumptions": [
            "the controller's measured hashes and accepted stream are authoritative inputs",
            "the scan implementation is unchanged during the run (pinned bd14004accd1)",
            "L1 coverage is intentionally excluded: it is measured by l1_spotchecks(), not by "
            "full-schema accepts",
        ],
        "falsifier": (
            "Collapses if at these measured hashes every accepted review event is visible in "
            "review_coverage() full_accepts for the same node+reviewer+hash and no accept is "
            "superseded by a later verdict from the same reviewer; or if review_coverage() is "
            "changed to union the accepted event stream and the divergence count drops to zero; "
            "or if the measured hashes move (verdict then advisory for the pinned bytes only)."),
        "evidence_refs": EVIDENCE,
        "artifact_refs": [PIN["report"], PIN["script"], PIN["readme"]],
        "not_claimed": ["no gate verdict", "no node status change", "no canonical artifact edit",
                        "no mathematical claim"],
    },
    {
        "event_id": "w001-covscan-status-20260912T005030+0800",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-001",
        "node_id": "F2a",
        "class_id": CLS,
        "class_ids": CLS_ALL,
        "gate": "G-FORM",
        "task_id": TASK,
        "status": "active",
        "hours": 0.4,
        "claims_completion": False,
        "summary": (
            "W001-COVERAGE-SCAN-01 complete at the worker level: reconciled review_coverage() "
            "against the accepted review stream at the 00:48:41 measured hashes. Verdict "
            "DIVERGENCE (4 gate-critical invisible accepts incl. F2a worker-089; 1 withdrawn "
            "accept counted for F1), 7/7 controls, hash-drift clean. Controller-owned repair "
            "proposed (union stream + path#hash resolution + supersession); not applied."),
        "evidence_refs": EVIDENCE,
        "next_falsifier": (
            "Re-run the harness after the next controller pass: if the gate reason for F2a still "
            "reads 0 accepts while worker-089's accept stands at 5476a3f2c6bc, the divergence is "
            "confirmed live; if review_coverage() is repaired and the divergence count is 0, this "
            "task is superseded and should be closed."),
    },
]

pre_existing = set()
if OUT.is_file():
    for line in OUT.read_text().splitlines():
        try:
            pre_existing.add(json.loads(line).get("event_id"))
        except Exception:
            continue

appended = 0
for ev in events:
    validate_event(ev)  # raises SchemaError -> no partial append
    if ev["event_id"] in pre_existing:
        print("skip (already present):", ev["event_id"])
        continue
    with open(OUT, "a") as f:
        f.write(json.dumps(ev, sort_keys=True) + "\n")
    appended += 1
print(f"appended {appended}/{len(events)} validated events to {OUT.relative_to(REPO)}")
