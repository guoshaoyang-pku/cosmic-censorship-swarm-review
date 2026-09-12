#!/usr/bin/env python3
"""Build MANIFEST.json for W083-F0-GENERICITY-DELEGATION-01.

Hashes every deliverable and every snapshot input, re-hashes the live inputs at manifest time
(moving-target record), and pins the previous-revision cross-check. MANIFEST.json itself is the
only file not listed (it cannot contain its own hash).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))

DELIVERABLES = [
    "check_genericity_delegation.py",
    "make_manifest.py",
    "evidence.json",
    "REPORT.md",
    "inputs/formulation_taxonomy.yaml",
    "inputs/af_wcc_vacuum.yaml",
    "inputs/af_scc_c2_vacuum.yaml",
    "inputs/af_scc_c0_vacuum.yaml",
    "inputs/VOCAB_ALIASES.json",
]
LIVE = [
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json",
]
PREV_PINS = [
    "artifacts/worker-061/f1_independent_verdict/pinned/formulation_taxonomy.canonical.yaml",
    "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml",
    "artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c2_vacuum.yaml",
    "artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c0_vacuum.yaml",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


ev = json.loads((HERE / "evidence.json").read_text())
snap = {i["live_path"]: i["sha256"] for i in ev["inputs"]}

manifest = {
    "schema": "w083-genericity-delegation-manifest/v1",
    "task_id": "W083-F0-GENERICITY-DELEGATION-01",
    "worker": "worker-083",
    "node_id": "F0",
    "gate": "G-F0",
    "class_ids": ev["class_ids"],
    "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
    "canonical_digest_sha256": ev["canonical_digest_sha256"],
    "controls_ok": ev["controls_ok"],
    "deliverables": {rel: sha256(HERE / rel) for rel in DELIVERABLES},
    "snapshot_inputs": snap,
    "previous_revision_pins": {rel: sha256(ROOT / rel) for rel in PREV_PINS},
    "live_recheck": {
        rel: {
            "sha256": sha256(ROOT / rel),
            "equals_snapshot": sha256(ROOT / rel) == snap.get(rel),
        }
        for rel in LIVE
    },
    "validation_status": "unverified",
    "claims_not_made": ev["claims_not_made"],
}

out = HERE / "MANIFEST.json"
out.write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n")
print("manifest:", out)
print("deliverables:")
for k, v in manifest["deliverables"].items():
    print(f"  {k}  {v[:16]}")
print("live:", {k: v["equals_snapshot"] for k, v in manifest["live_recheck"].items()})
