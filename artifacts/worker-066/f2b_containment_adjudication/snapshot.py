#!/usr/bin/env python3
"""W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01 -- pin step.

Copies every input byte-for-byte into pinned/ and records sha256, size, mtime.
Nothing is judged here; this only freezes the adjudication target so that every
later check runs on bytes that cannot move underneath the run.

Usage: python3 snapshot.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # artifacts/worker-066/f2b_containment_adjudication -> repo root

# name -> repo-relative path (primary judgment targets first)
INPUTS = {
    "c0_canonical": "schemas/af_scc_c0_vacuum.yaml",
    "c2_canonical": "schemas/af_scc_c2_vacuum.yaml",
    "frozen_manifest": "artifacts/formulation/FROZEN.json",
    "worker008_candidate_rev12": "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml",
    "worker008_addendum_evidence": "artifacts/worker-008/f2b_rev11_dualrepair/evidence/rev12_addendum.json",
    "worker008_candidate_audit": "artifacts/worker-008/f2b_rev11_dualrepair/evidence/audit_candidate_rev12.json",
    "rule_spec": "artifacts/formulation/rule_spec.json",
    "gate_checker": "artifacts/formulation/tools/check_class_schema.py",
    "f0_declared_taxonomy": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
}

PRIMARY = ["c0_canonical", "c2_canonical"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> dict:
    pinned = HERE / "pinned"
    pinned.mkdir(exist_ok=True)
    record = {
        "task_id": "W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "pinned_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "inputs": {},
    }
    for name, rel in INPUTS.items():
        src = REPO / rel
        if not src.exists():
            record["inputs"][name] = {"path": rel, "exists": False}
            continue
        dst = pinned / (name + "__" + Path(rel).name)
        shutil.copy2(src, dst)
        record["inputs"][name] = {
            "path": rel,
            "pinned_path": str(dst.relative_to(REPO)),
            "exists": True,
            "sha256": sha256(dst),
            "bytes": dst.stat().st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(src.stat().st_mtime)),
        }
    record["primary_targets"] = {
        k: record["inputs"][k]["sha256"] for k in PRIMARY if record["inputs"][k].get("exists")
    }
    out = HERE / "PINNED.json"
    out.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=1))
    return record


if __name__ == "__main__":
    main()
