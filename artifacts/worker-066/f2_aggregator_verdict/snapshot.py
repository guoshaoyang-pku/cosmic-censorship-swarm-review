#!/usr/bin/env python3
"""W066-F2AGG-VERDICT-01 -- freeze the byte set this verdict binds to.

Read-only against the repo: copies the target bytes into ./pinned/ and records
sha256 + bytes + mtime_ns for every pinned input.  A verdict binds bytes, not
paths, so every later check runs against these copies as well as the live files.

Usage: python3 snapshot.py [--root ../../..] [--out PINNED.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

CST_OFFSET = 8 * 3600


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# (logical id, repo-relative path, why pinned)
TARGETS = [
    ("F2-AGG", "schemas/af_scc_regularities.yaml",
     "verdict target: F2 aggregator / thin index, class_ids AF-SCC-C2-VAC-GEN + AF-SCC-C0-VAC-GEN"),
    ("F2A-C2", "schemas/af_scc_c2_vacuum.yaml", "component 1 of the aggregator"),
    ("F2B-C0", "schemas/af_scc_c0_vacuum.yaml", "component 2 of the aggregator"),
    ("RULE-SPEC", "artifacts/formulation/rule_spec.json",
     "aggregator schema_binding_note claims rule_spec v1.1; measured spec_version"),
    ("CLASS-GATE", "artifacts/formulation/tools/check_class_schema.py",
     "gate the aggregator names as binding_component_gate; enforced rule ids"),
    ("F0-CANON", "research_map/formulation_taxonomy.yaml",
     "canonical F0; aggregator revision_note cites declared-F0 0fcc6a19"),
    ("F0-AUTHORING", "artifacts/formulation/formulation_taxonomy.yaml", "authoring-tree F0"),
    ("FROZEN", "artifacts/formulation/FROZEN.json", "rev26 manifest: is the aggregator freeze-bound?"),
    ("PRIOR-PINCHECK", "artifacts/worker18/f2_review/aggregator_pin_check.json",
     "the recorded review_owner pin check; which bytes does it target?"),
    ("MAP", "research_map/research_map.json", "sole global state read at snapshot time"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "PINNED.json"))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    here = Path(__file__).resolve().parent
    pinned = here / "pinned"
    pinned.mkdir(parents=True, exist_ok=True)

    rec = {
        "artifact": "W066-F2AGG-VERDICT-PINS",
        "task_id": "W066-F2AGG-VERDICT-01",
        "actor": "worker-066",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F2",
        "gate": "G-FORM",
        "snapshot_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(time.time() + CST_OFFSET)),
        "root": str(root),
        "files": {},
    }
    for logical, rel, why in TARGETS:
        src = root / rel
        row = {"path": rel, "why": why, "exists": src.exists()}
        if src.exists():
            digest = sha256(src)
            st = src.stat()
            row.update({
                "sha256": digest,
                "bytes": st.st_size,
                "mtime_ns": st.st_mtime_ns,
                "mtime": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(st.st_mtime + CST_OFFSET)),
                "snapshot": f"pinned/{logical}{src.suffix}",
            })
            shutil.copy2(src, pinned / f"{logical}{src.suffix}")
        rec["files"][logical] = row
    Path(a.out).write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v.get("sha256", "MISSING")[:16] for k, v in rec["files"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
