#!/usr/bin/env python3
"""Finalize pins/checkpoint/manifest for W083-REF01-REV29-DISPOSITION-01.

Writes only inside artifacts/worker-083/ref01_rev29_disposition/ and runtime/state/.
No canonical artifact is touched. Idempotent (re-running rewrites identical bytes given
unchanged inputs, except the checkpoint timestamp).
"""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-083/ref01_rev29_disposition"
TASK = "W083-REF01-REV29-DISPOSITION-01"


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


report = json.load(open(OUT / "report.json"))
evidence = json.load(open(OUT / "evidence.json"))
now = time.strftime("%Y-%m-%dT%H:%M:%S%z")

bound = [
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/evidence/close_findings_rev27_report.json",
    "artifacts/formulation/tools/close_findings_rev27.py",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/evidence/gate_test_report.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
]
pins = {
    "audit_id": TASK,
    "actor": "worker-083",
    "created_at": now,
    "bound_generation": "FROZEN rev29 815e08079aef (frozen_at 2026-09-12T00:57:26+08:00)",
    "bound_pins": {p: {"sha256": h(ROOT / p), "bytes": (ROOT / p).stat().st_size} for p in bound},
    "intermediate_generations_with_zero_copies": ["b474fbc4", "a7ccae4d", "b71ec02c", "f3c119a8"],
    "recoverability_scan": {k: v for k, v in report["recoverability_scan"].items() if k != "hits"},
    "canonical_digest_sha256": report["canonical_digest_sha256"],
    "verdict": report["verdict"],
    "falsifier": report["falsifier"],
}
(OUT / "pins.json").write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n")

deliverables = ["check_ref01_rev29_disposition.py", "report.json", "evidence.json",
                "REPORT.md", "pins.json"]
manifest_files = {}
for name in deliverables:
    p = OUT / name
    manifest_files[name] = {"sha256": h(p), "bytes": p.stat().st_size}
manifest_files["checkpoint.json"] = {"sha256": "PENDING_SELF", "bytes": 0}
manifest = {
    "audit_id": TASK,
    "actor": "worker-083",
    "created_at": now,
    "verdict": report["verdict"],
    "canonical_digest_sha256": report["canonical_digest_sha256"],
    "files": manifest_files,
    "canonical_writes": False,
}

checkpoint = {
    "task_id": TASK,
    "actor": "worker-083",
    "status": "complete-worker-level",
    "created_at": now,
    "class_ids": report["class_ids"],
    "node_id": report["node_id"],
    "gate": "G-FORM",
    "bound_generation": pins["bound_generation"],
    "verdict": report["verdict"],
    "checks": {c["id"]: c["pass"] for c in report["checks"]},
    "controls": {c["id"]: c["pass"] for c in report["controls"]},
    "drift": report["drift"],
    "canonical_digest_sha256": report["canonical_digest_sha256"],
    "deliverables": manifest_files,
    "falsifier": report["falsifier"],
    "limits": report["limits"],
    "next_consumer": "astra controller / astra-lead-formulation / G-FORM r3 reviewers",
    "remedy_options_not_applied": ["R1 rev30 closure receipt (owner)", "R2 controller finding + pin gate_test_report#26540a6b (controller)"],
}
(OUT / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
state_path = ROOT / "runtime/state/w083_ref01_rev29_disposition_checkpoint.json"
state_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

manifest_files["checkpoint.json"] = {"sha256": h(OUT / "checkpoint.json"),
                                     "bytes": (OUT / "checkpoint.json").stat().st_size}
(OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

print(json.dumps({"pins": str(OUT / "pins.json"), "checkpoint": str(state_path),
                  "manifest": str(OUT / "MANIFEST.json"),
                  "checkpoint_sha256": manifest_files["checkpoint.json"]["sha256"][:12],
                  "digest": report["canonical_digest_sha256"][:14]}, indent=1))
