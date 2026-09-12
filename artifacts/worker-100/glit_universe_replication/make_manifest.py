#!/usr/bin/env python3
"""Hash every deliverable of W100-GLIT-UNIVERSE-REPL-01 into MANIFEST.json."""
import hashlib
import json
from pathlib import Path

TASK = Path(__file__).resolve().parent
DELIVERABLES = [
    "PREREGISTRATION.json",
    "replicate_census_100.py",
    "emit_events_100.py",
    "replication_report.json",
    "REPLICATION.md",
    "README.md",
    "raw/inputs_hashes_t0.json",
    "raw/inputs_hashes_t1.json",
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = {}
    for rel in DELIVERABLES:
        p = TASK / rel
        if p.exists():
            files[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    manifest = {"task_id": "W100-GLIT-UNIVERSE-REPL-01", "worker": "worker-100",
                "self_excluded": "MANIFEST.json", "files": files}
    (TASK / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
