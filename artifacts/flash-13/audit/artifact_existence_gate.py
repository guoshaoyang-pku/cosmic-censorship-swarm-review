#!/usr/bin/env python3
"""Audit probe: does the research map's done-gate actually check that declared artifacts exist?

Reads research_map.json, resolves every node's declared `artifact` path relative to a root, and
reports (a) done nodes whose artifact is absent, (b) any entry in a node's `artifacts` list whose
file is missing or whose sha256 does not match.

This is a READ-ONLY probe. It does not modify research_map.json. It exists to substantiate the
claim in proposals/flash-13/WP13-F1-GATE.yaml that validate_map.py's done-gate is textual only:
validate_map.py:23-26 checks `n.get("artifact")` truthiness, never the filesystem.

Exit 0 = no violations, 1 = violations found, 2 = input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]  # artifacts/flash-13/audit/<this> -> repo root


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("map", nargs="?", default=str(REPO / "research_map" / "research_map.json"))
    ap.add_argument("--root", default=str(REPO))
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    mp = Path(args.map)
    if not mp.exists():
        print(f"INPUT ERROR: {mp} missing")
        return 2
    root = Path(args.root)
    data = json.loads(mp.read_text())

    violations, pending, hashed_ok, hashed_bad = [], [], 0, 0
    for g in data.get("groups", []):
        for n in g.get("nodes", []):
            declared = n.get("artifact")
            if declared:
                p = root / declared
                rec = {"node": n["id"], "group": g["id"], "status": n["status"], "artifact": declared,
                       "exists": p.exists()}
                if not p.exists():
                    if n.get("status") == "done":
                        violations.append({**rec, "kind": "done_node_missing_artifact",
                                           "validator_verdict": "validate_map.py accepts this map"})
                    else:
                        pending.append(rec)
            for a in n.get("artifacts", []) or []:
                if not isinstance(a, dict) or "path" not in a:
                    continue
                p = root / a["path"]
                if not p.exists():
                    hashed_bad += 1
                    violations.append({"node": n["id"], "kind": "listed_artifact_missing",
                                       "path": a["path"]})
                elif a.get("sha256") and sha256_file(p) != a["sha256"]:
                    hashed_bad += 1
                    violations.append({"node": n["id"], "kind": "listed_artifact_hash_mismatch",
                                       "path": a["path"]})
                else:
                    hashed_ok += 1

    report = {
        "probe": "artifact_existence_gate",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "map": str(mp),
        "map_sha256": sha256_file(mp),
        "violations": violations,
        "pending_artifacts_not_yet_written": pending,
        "listed_artifacts_verified": hashed_ok,
        "listed_artifacts_failed": hashed_bad,
        "note": "read-only; research_map.json is not modified",
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2) + "\n")

    print(f"artifact_existence_gate: map={mp}")
    print(f"  done-node violations: {len([v for v in violations if v['kind'] == 'done_node_missing_artifact'])}")
    for v in violations:
        print(f"  VIOLATION {v['kind']}: node={v.get('node')} artifact={v.get('artifact', v.get('path'))}")
    print(f"  pending (active/queued, not yet expected): {len(pending)}")
    print(f"  listed artifacts verified={hashed_ok} failed={hashed_bad}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
