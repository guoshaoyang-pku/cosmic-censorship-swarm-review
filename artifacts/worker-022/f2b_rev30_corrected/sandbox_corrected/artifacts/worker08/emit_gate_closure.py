#!/usr/bin/env python3
"""Close the worker-08 F0/A0 evidence-gap loop with a fresh gate run (map_artifact_gate_v2)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
ART = REPO / "artifacts" / "worker08"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


gate = ART / "map_artifact_gate_v2.json"
g = json.loads(gate.read_text())
artifacts = {
    "research_map/formulation_taxonomy.yaml": REPO / "research_map" / "formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": REPO / "artifacts" / "formulation" / "formulation_taxonomy.yaml",
    "evaluation_rubric.yaml": REPO / "evaluation_rubric.yaml",
    "schemas/af_scc_regularities.yaml": REPO / "schemas" / "af_scc_regularities.yaml",
}
present = {k: (sha(v) if v.exists() else None) for k, v in artifacts.items()}

events = [
    {
        "event_id": "e08-art-20260911T2350-map-gate-v2-closure",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "deepseek-flash-08",
        "group_id": "formulation+audit",
        "node_id": "F0",
        "covers_nodes": ["F0", "A0"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact_type": "validation_gate_report",
        "path": "artifacts/worker08/map_artifact_gate_v2.json",
        "sha256": sha(gate),
        "validation_status": "passed",
        "gate_verdict": g["gate_result"]["verdict"],
        "gate_result": g["gate_result"],
        "supersedes": "e08-art-20260911T2323-map-gate",
        "remediation_evidence": present,
        "findings": g["findings"],
        "reproduce": "python3 artifacts/worker08/check_map_artifacts.py --out artifacts/worker08/map_artifact_gate_v2.json",
        "evidence_refs": [
            "research_map/research_map.json",
            "research_map/formulation_taxonomy.yaml#" + (present["research_map/formulation_taxonomy.yaml"] or "")[:8],
            "evaluation_rubric.yaml#" + (present["evaluation_rubric.yaml"] or "")[:8],
        ],
        "next_falsifier": (
            "Any node later marked done whose declared artifact is absent on disk reopens the gap; the "
            "gate exits 1 in that case."
        ),
    },
    {
        "event_id": "e08-status-20260911T2350-f0-a0-closure",
        "event_type": "status",
        "created_at": NOW,
        "actor": "deepseek-flash-08",
        "group_id": "formulation+audit",
        "node_id": "F0",
        "status": "active",
        "hours": 4.2,
        "summary": (
            "Loop closure on the initial worker-08 finding: the F0/A0 done-status evidence gap is "
            "remediated. The map no longer marks F0/A0 done (both active/unverified pending reviews); "
            "the F0 taxonomy exists at research_map/formulation_taxonomy.yaml and "
            "artifacts/formulation/formulation_taxonomy.yaml, the A0 rubric at evaluation_rubric.yaml, "
            "and the F2 regularities file at schemas/af_scc_regularities.yaml. Fresh gate run: pass, "
            "0 done nodes, 0 unbacked. Remaining structural gap: research_map/validate_map.py still does "
            "not stat declared artifact paths; recommend adopting artifacts/worker08/check_map_artifacts.py "
            "(exit 1 on an unbacked done node) as the controller-side gate."
        ),
        "evidence_refs": [
            "artifacts/worker08/map_artifact_gate_v2.json#" + sha(gate)[:8],
            "artifacts/worker08/check_map_artifacts.py",
        ],
        "next_falsifier": "A done node with an absent declared artifact passes validate_map.py again without the stat gate.",
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing.add(json.loads(line)["event_id"])
            except (ValueError, KeyError):
                pass
added = []
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in events:
        if ev["event_id"] in existing:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        added.append(ev["event_id"])
print(json.dumps({"added": added, "total_events": len(existing) + len(added),
                  "gate_verdict": g["gate_result"]["verdict"], "present": present}, indent=2))
