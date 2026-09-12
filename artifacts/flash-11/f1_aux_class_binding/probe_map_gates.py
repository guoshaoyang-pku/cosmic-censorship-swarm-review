#!/usr/bin/env python3
"""Supporting evidence probe (not part of the conformance harness).

Cross-checks every research-map node whose status is 'done' against the declared
artifact path on disk, and re-runs the map validator. Motivated by hard decision
#4: "A completed node requires an artifact and validation evidence."

Output: evidence/gate_integrity.json  (plus a human-readable stdout table).
This tool only *reports*; it does not edit the map and does not decide gates.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # artifacts/flash-11/f1_aux_class_binding -> repo root
EV = HERE / "evidence"


def main() -> int:
    map_path = REPO / "research_map" / "research_map.json"
    m = json.loads(map_path.read_text(encoding="utf-8"))
    rows = []
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            status = n.get("status")
            art = n.get("artifact")
            if status != "done":
                continue
            p = REPO / str(art) if art else None
            rows.append(
                {
                    "node_id": n.get("id"),
                    "group_id": g.get("id"),
                    "status": status,
                    "validation_status": n.get("validation_status", n.get("validated")),
                    "artifact": art,
                    "artifact_exists": bool(p and p.exists()),
                    "evidence_refs": n.get("evidence_refs", []),
                }
            )

    validator = subprocess.run(
        [sys.executable, str(REPO / "research_map" / "validate_map.py")],
        cwd=str(REPO / "research_map"),
        capture_output=True,
        text=True,
        timeout=60,
    )
    report = {
        "probe": "done-node artifact existence vs research_map.json",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "map_updated_at": m.get("updated_at"),
        "validator_exit_code": validator.returncode,
        "validator_stdout": validator.stdout.strip(),
        "validator_stderr": validator.stderr.strip(),
        "done_nodes": rows,
        "done_nodes_missing_artifact": [r for r in rows if not r["artifact_exists"]],
    }
    EV.mkdir(exist_ok=True)
    (EV / "gate_integrity.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"validator: exit={report['validator_exit_code']} {report['validator_stdout']!r}")
    for r in rows:
        mark = "OK " if r["artifact_exists"] else "MISSING"
        print(f"  {mark:8s} {r['node_id']} ({r['group_id']}) artifact={r['artifact']!r} validation_status={r['validation_status']!r}")
    print(f"{len(report['done_nodes_missing_artifact'])}/{len(rows)} done nodes have a missing declared artifact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
