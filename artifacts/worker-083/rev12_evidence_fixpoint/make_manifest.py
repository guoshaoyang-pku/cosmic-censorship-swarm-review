#!/usr/bin/env python3
"""Write MANIFEST.json for the W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01 artifact directory.

Deterministic; hashes every regular file in this directory except MANIFEST.json itself
and any __pycache__. Re-run after any intentional edit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = "W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    files = {}
    for p in sorted(HERE.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(HERE))
        if rel == "MANIFEST.json" or "__pycache__" in rel:
            continue
        files[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    manifest = {
        "task_id": TASK,
        "worker": "worker-083",
        "artifact_root": "artifacts/worker-083/rev12_evidence_fixpoint",
        "files": files,
        "file_count": len(files),
        "self_reference": ("MANIFEST.json cannot contain its own post-write sha256; its hash is recorded "
                           "in the artifact event that publishes it. Excluded from its own files map."),
        "authority_note": ("Measurement artifact only; no gate verdict, node status or validation_status; "
                           "no canonical artifact was edited."),
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=1))
    for k, v in files.items():
        print(f"  {v['sha256'][:16]}  {v['bytes']:>7}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
