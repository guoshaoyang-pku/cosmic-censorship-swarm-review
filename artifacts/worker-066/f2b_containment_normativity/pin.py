#!/usr/bin/env python3
"""W066-F2B-CONTAINMENT-NORMATIVITY-01 -- pin step.

Copies every input used by the normativity adjudication into pinned/ and records
sha256 / bytes / mtime in PINNED.json.  Read-only against canonical paths.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PINNED = HERE / "pinned"
PINNED.mkdir(exist_ok=True)

CST = timezone(timedelta(hours=8))

INPUTS = {
    # target + siblings
    "target_c0": "schemas/af_scc_c0_vacuum.yaml",
    "sibling_c2": "schemas/af_scc_c2_vacuum.yaml",
    "family_wcc": "schemas/af_wcc_vacuum.yaml",
    # frozen declaration + F0
    "frozen": "artifacts/formulation/FROZEN.json",
    "f0_canonical": "research_map/formulation_taxonomy.yaml",
    "f0_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    # normative rule material
    "rule_spec": "artifacts/formulation/rule_spec.json",
    "gate_tool": "artifacts/formulation/tools/check_class_schema.py",
    "key_manifest": "artifacts/formulation/KEY_MANIFEST.json",
    # repair candidate (worker-008) + predecessor instrument
    "candidate_c0": "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml",
    "predecessor_checker": "artifacts/worker-066/f2b_containment_adjudication/adjudicate.py",
    "predecessor_pins": "artifacts/worker-066/f2b_containment_adjudication/PINNED.json",
    # rev12 snapshot of the same target (provenance: rev13 carried the clauses forward)
    "prior_rev12_c0": "artifacts/worker-066/f2b_containment_adjudication/pinned/c0_canonical__af_scc_c0_vacuum.yaml",
    "prior_rev12_c2": "artifacts/worker-066/f2b_containment_adjudication/pinned/c2_canonical__af_scc_c2_vacuum.yaml",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> dict:
    entries = {}
    for key, rel in INPUTS.items():
        src = REPO / rel
        if not src.exists():
            entries[key] = {"path": rel, "exists": False}
            continue
        dst = PINNED / (key + "__" + src.name)
        shutil.copyfile(src, dst)
        st = src.stat()
        entries[key] = {
            "path": rel,
            "exists": True,
            "sha256": sha256(src),
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(),
            "pinned_copy": str(dst.relative_to(REPO)),
            "pinned_copy_sha256": sha256(dst),
        }
    out = {
        "task_id": "W066-F2B-CONTAINMENT-NORMATIVITY-01",
        "actor": "worker-066",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "pinned_at": datetime.now(CST).isoformat(),
        "inputs": entries,
    }
    (HERE / "PINNED.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: (v.get("sha256") or "MISSING")[:16] for k, v in entries.items()}, indent=1))
    return out


if __name__ == "__main__":
    main()
