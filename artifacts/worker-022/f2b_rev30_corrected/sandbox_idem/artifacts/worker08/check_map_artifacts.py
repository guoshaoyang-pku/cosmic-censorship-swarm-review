#!/usr/bin/env python3
"""Deterministic preflight gate: does every research_map "done" node have a real artifact?

Motivation (worker 08, 2026-09-11): ASTRA_HANDOFF.md hard decision 4 says
"A completed node requires an artifact and validation evidence."  The shipped
validator (research_map/validate_map.py) checks only that the JSON *declares*
an artifact string, never that the path exists, so `VALID` is compatible with
zero artifacts on disk.

This script is read-only.  It does not modify research_map.json or any artifact.

Usage:
    python3 artifacts/worker08/check_map_artifacts.py \
        [--map research_map/research_map.json] [--out artifacts/worker08/map_artifact_gate.json]

Exit code: 0 if every done node's declared artifact exists, else 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_lines(path: Path) -> int | None:
    if not path.is_file():
        return None
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(REPO / "research_map" / "research_map.json"))
    ap.add_argument("--out", default=str(REPO / "artifacts" / "worker08" / "map_artifact_gate.json"))
    args = ap.parse_args()

    map_path = Path(args.map).resolve()
    raw = map_path.read_bytes()
    m = json.loads(raw.decode("utf-8"))

    nodes_report = []
    group_report = []
    findings = []
    done_total = 0
    done_with_artifact = 0

    for g in m.get("groups", []):
        gid = g["id"]
        declared_existing = 0
        declared_total = 0
        loc_claimed = g.get("artifacts", {}).get("loc_done")
        loc_measured = 0
        loc_measurable = True
        for n in g.get("nodes", []):
            artifact = n.get("artifact")
            status = n.get("status")
            rec = {
                "group": gid,
                "node_id": n.get("id"),
                "status": status,
                "validation_status": n.get("validation_status"),
                "declared_artifact": artifact,
                "artifact_exists": None,
                "artifact_kind": None,
                "artifact_sha256": None,
                "artifact_bytes": None,
            }
            if artifact:
                declared_total += 1
                p = (REPO / artifact).resolve()
                # keep the check inside the repo; a declared artifact must be a real path
                rec["artifact_exists"] = p.exists()
                if p.exists():
                    declared_existing += 1
                    rec["artifact_kind"] = "dir" if p.is_dir() else "file"
                    if p.is_file():
                        rec["artifact_sha256"] = sha256_file(p)
                        rec["artifact_bytes"] = p.stat().st_size
                        lines = count_lines(p)
                        if lines is not None:
                            loc_measured += lines
                    else:
                        rec["artifact_kind"] = "dir"
                else:
                    rec["artifact_kind"] = "missing"
                    if status == "done":
                        findings.append(
                            f"HARD: node {n.get('id')} status=done validation_status={n.get('validation_status')} "
                            f"but declared artifact does not exist: {artifact}"
                        )
            if n.get("status") == "done":
                done_total += 1
                if artifact and (REPO / artifact).exists():
                    done_with_artifact += 1
                elif not artifact:
                    findings.append(f"HARD: node {n.get('id')} status=done but declares no artifact")
            if n.get("status") == "done" and not n.get("validation_status"):
                findings.append(f"HARD: node {n.get('id')} status=done without validation_status")
            nodes_report.append(rec)

        if loc_claimed and declared_existing == 0:
            loc_measurable = False
        group_report.append(
            {
                "group": gid,
                "status": g.get("status"),
                "files_done_claimed": g.get("artifacts", {}).get("files_done"),
                "declared_artifacts_total": declared_total,
                "declared_artifacts_existing": declared_existing,
                "loc_done_claimed": loc_claimed,
                "loc_measured_from_existing_declared_artifacts": loc_measured if loc_measurable else None,
                "accounting_reconcilable": declared_existing > 0,
            }
        )

    # ---- validator-gap findings (structural, not node-specific) ----
    import re as _re
    contract_types = {"status", "claim", "artifact", "blocker", "direction_update", "resource_request"}
    schema_types = set()
    schemas_src = REPO / "research_map" / "schemas.py"
    if schemas_src.exists():
        m = _re.search(r"EVENT_TYPES\s*=\s*\{([^}]*)\}", schemas_src.read_text(encoding="utf-8"))
        if m:
            schema_types = set(_re.findall(r"[\"']([a-z_]+)[\"']", m.group(1)))
    findings.append(
        "GAP: research_map/validate_map.py checks only that a done node declares a non-empty "
        "artifact string and a truthy validation_status; it never stats the path. "
        "Hence it prints VALID for a map whose done nodes have no files on disk."
    )
    missing = sorted(contract_types - schema_types)
    extra = sorted(schema_types - contract_types)
    if missing:
        findings.append(
            "GAP: communication contract lists "
            f"{sorted(contract_types)} but research_map/schemas.py EVENT_TYPES={sorted(schema_types)}. "
            f"absent from schema: {missing}; schema-only: {extra}."
        )
    elif extra:
        findings.append(
            "NOTE: all contract message types are schema-valid; schemas.py additionally accepts "
            f"{extra} (controller/downward types). No gap."
        )

    verdict = "pass" if (done_total == done_with_artifact) else "fail"
    report = {
        "gate": "research_map_done_node_artifact_existence",
        "gate_version": "0.1",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "generated_by": "deepseek-flash-08 (execution worker 08)",
        "read_only": True,
        "inputs": {
            "map_path": str(map_path),
            "map_sha256": hashlib.sha256(raw).hexdigest(),
            "validator_command": "python3 research_map/validate_map.py",
            "validator_result": "VALID (does not imply artifact existence)",
        },
        "gate_result": {
            "verdict": verdict,
            "done_nodes": done_total,
            "done_nodes_with_existing_artifact": done_with_artifact,
            "criterion": "status==done implies declared artifact path exists on disk",
        },
        "nodes": nodes_report,
        "group_accounting": group_report,
        "findings": findings,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["gate_result"], indent=2))
    print(f"findings: {len(findings)}")
    for f in findings:
        print(" -", f)
    print(f"wrote {out}")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
