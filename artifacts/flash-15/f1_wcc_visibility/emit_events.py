#!/usr/bin/env python3
"""Emit the worker-015 F1 visibility review as validated outbox events (append-only)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


now = datetime.now(CST).isoformat()
art = ROOT / "artifacts" / "flash-15" / "f1_wcc_visibility"
review_file = ROOT / "reviews" / "F1-review-15-wccvis.json"
review = json.loads(review_file.read_text())

events = [
    {
        "event_id": "w015-f1-artifact-probe-20260912T0029",
        "event_type": "artifact",
        "created_at": now,
        "actor": "deepseek-flash-15",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "review_probe",
        "path": "artifacts/flash-15/f1_wcc_visibility/probe_report.json",
        "sha256": sha(art / "probe_report.json"),
        "validation_status": "unverified",
        "note": "Machine probe for the F1 visibility-quantifier adjudication: quantifier/predicate coherence, exhaustive finite-model non-equivalence proof, duplicate-key/future-timestamp hygiene, F0 pointer resolution, canonical gate on pinned and repaired bytes. Read-only on schemas/.",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#9a8bd4c96800"],
    },
    {
        "event_id": "w015-f1-artifact-readme-20260912T0029",
        "event_type": "artifact",
        "created_at": now,
        "actor": "deepseek-flash-15",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "review_note",
        "path": "artifacts/flash-15/f1_wcc_visibility/README.md",
        "sha256": sha(art / "README.md"),
        "validation_status": "unverified",
        "note": "Task ID, pinned hashes, confirmed finding, gate blindness, repair proposal, falsifiers, authority boundary.",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#9a8bd4c96800"],
    },
    {
        "event_id": "w015-f1-artifact-repair-20260912T0029",
        "event_type": "artifact",
        "created_at": now,
        "actor": "deepseek-flash-15",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": "repair_proposal",
        "path": "artifacts/flash-15/f1_wcc_visibility/repaired_proposal.af_wcc_vacuum.yaml",
        "sha256": sha(art / "repaired_proposal.af_wcc_vacuum.yaml"),
        "validation_status": "unverified",
        "note": "Proposed (NOT applied) minimal repair of the tail/whole-curve incoherence; passes check_class_schema.py rc=0. schemas/ is lead-owned.",
        "evidence_refs": ["schemas/af_wcc_vacuum.yaml#9a8bd4c96800"],
    },
    {
        "event_id": review["event_id"],
        "event_type": "review",
        "created_at": now,
        "actor": "deepseek-flash-15",
        "reviewer": review["reviewer"],
        "group_id": "formulation",
        "node_id": "F1",
        "target_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "gate": "G-FORM",
        "artifact": "reviews/F1-review-15-wccvis.json",
        "artifact_sha256": sha(review_file),
        "target_artifact": "schemas/af_wcc_vacuum.yaml",
        "target_artifact_sha256": review["artifact_sha256"],
        "verdict": review["verdict"],
        "score": review["score"],
        "hard_failures": review["hard_failures"],
        "findings": review["findings"],
        "evidence_refs": review["evidence_refs"],
        "falsifier": review["falsifier"],
        "counts_as_full_schema_verdict": True,
        "counts_as_independent_second_verdict": True,
        "claims_no_gate_verdict": True,
    },
]

out = ROOT / "comms" / "outbox" / "deepseek-flash-15.jsonl"
with out.open("a") as f:
    for e in events:
        validate_event(e)
        f.write(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n")
        print("VALID + appended", e["event_type"], e["event_id"])
print("outbox:", out)
