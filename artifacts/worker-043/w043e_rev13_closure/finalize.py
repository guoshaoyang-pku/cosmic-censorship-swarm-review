#!/usr/bin/env python3
"""W043E step 2 - hash the deliverables and write MANIFEST.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["report.json", "closure_probe.py", "README.md"] + \
    sorted(str(p.relative_to(HERE)) for p in (HERE / "raw").glob("*.json"))

deliverables = {}
for rel in FILES:
    b = (HERE / rel).read_bytes()
    deliverables[rel] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}

report = json.loads((HERE / "report.json").read_text())
manifest = {
    "task_id": report["task_id"],
    "worker": "worker-043",
    "created_at": report["created_at"],
    "node_ids": report["node_ids"],
    "class_ids": report["class_ids"],
    "gate": report["gate"],
    "verdict": report["verdict"],
    "scope": report["scope"],
    "moving_target": report["moving_target"],
    "deliverables": deliverables,
    "reproduce": "python3 artifacts/worker-043/w043e_rev13_closure/closure_probe.py",
    "authority_note": report["authority_note"],
}
(HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"MANIFEST.json: {len(deliverables)} deliverables, verdict={report['verdict']}")
