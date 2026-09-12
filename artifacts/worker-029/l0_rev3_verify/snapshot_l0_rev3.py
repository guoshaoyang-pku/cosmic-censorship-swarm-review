#!/usr/bin/env python3
"""W029-L0-REV3-VERDICT-05 — freeze the inputs for an independent L0 rev3 verdict.

Read-only over canonical artifacts: copies each source file into ./snapshots/ and
records {source_path (repo-root-relative), snapshot_path, sha256, bytes, mtime_iso}
in snapshot_manifest.json. Never writes outside artifacts/worker-029/l0_rev3_verify/.

Usage:
    python3 artifacts/worker-029/l0_rev3_verify/snapshot_l0_rev3.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshots"
CST = timezone(timedelta(hours=8))

# repo-root-relative source paths, frozen for this verdict
SOURCES = [
    "ledger/theorems.jsonl",
    "ledger/citation_audit.csv",
    "evaluation_rubric.yaml",
    "research_map/class_separation.py",
    "artifacts/audit/audit_lib.py",
    "artifacts/audit/audit_run.py",
    "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
    "artifacts/literature/tools/rev3_axis_split.py",
    "artifacts/literature/reviews/rev3-axis-split.json",
    "artifacts/literature/reviews/L0-rev3-hf14-repair.json",
    "artifacts/literature/reviews/L0-rev3-adjudication-20260912T0035.md",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "research_map/formulation_taxonomy.yaml",
    "reviews/A1-rebind-coverage.json",
    "reviews/L0-review-093.json",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    SNAP.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "worker-029/l0-rev3-snapshot/v1",
        "task_id": "W029-L0-REV3-VERDICT-05",
        "actor": "worker-029",
        "measured_at": datetime.now(CST).isoformat(timespec="seconds"),
        "root": str(ROOT),
        "files": [],
    }
    for rel in SOURCES:
        src = ROOT / rel
        if not src.is_file():
            manifest["files"].append({"source_path": rel, "snapshot_path": None,
                                      "sha256": None, "bytes": None, "mtime_iso": None,
                                      "missing": True})
            continue
        dst = SNAP / rel.replace("/", "__")
        shutil.copyfile(src, dst)
        st = src.stat()
        manifest["files"].append({
            "source_path": rel,
            "snapshot_path": str(dst.relative_to(ROOT)),
            "sha256": sha256_file(src),
            "bytes": st.st_size,
            "mtime_iso": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
            "missing": False,
        })
    out = HERE / "snapshot_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(ROOT)} ({len(manifest['files'])} files)")
    for f in manifest["files"]:
        print(f"  {f['source_path']}: {str(f['sha256'])[:12]} "
              f"{'(MISSING)' if f['missing'] else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
