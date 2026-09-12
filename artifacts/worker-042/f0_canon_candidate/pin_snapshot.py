#!/usr/bin/env python3
"""W042-F0-CANON-CANDIDATE-08 freeze-first pin tool (read-only on canonical paths).

Copies the declared inputs into ./snapshot/<relpath>, hashes each copy of record and each live
file, and writes ./snapshot/manifest.json last. Exits 2 if any live file does not re-hash to its
snapshot copy (pin drift), so downstream tools can fail closed.

Writes only under artifacts/worker-042/f0_canon_candidate/.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshot"
CST = timezone(timedelta(hours=8))

ACTOR = "worker-042"
RUN = "W042-F0-CANON-CANDIDATE-08"

DECLARED_PATHS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "artifacts/worker-019/f2a_review/results.json",
    "artifacts/worker-097/f2b_rev13_review/check_f2b_rev13.py",
    "research_map/events.jsonl",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    SNAP.mkdir(parents=True, exist_ok=True)
    entries = {}
    missing = []
    for rel in DECLARED_PATHS:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst = SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        entries[rel] = {
            "snapshot_path": str(dst.relative_to(ROOT)),
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
            "mtime_ns": src.stat().st_mtime_ns,
        }

    # Live stability re-hash after the copy window.
    drift = []
    for rel, ent in entries.items():
        live = ROOT / rel
        live_sha = sha256_file(live) if live.is_file() else None
        if live_sha != ent["sha256"]:
            drift.append({"path": rel, "snapshot_sha256": ent["sha256"], "live_sha256": live_sha})

    manifest = {
        "schema": "worker-pin-manifest/v1",
        "actor": ACTOR,
        "run": RUN,
        "task_id": RUN,
        "pinned_at": now,
        "root": str(ROOT),
        "declared_paths": DECLARED_PATHS,
        "missing_paths": missing,
        "file_count": len(entries),
        "files": entries,
        "live_rehash_at": datetime.now(CST).isoformat(timespec="seconds"),
        "drift": drift,
    }
    mpath = SNAP / "manifest.json"
    mpath.write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n")
    print(f"pinned {len(entries)} files, missing {len(missing)}, drift {len(drift)}")
    print(f"manifest {mpath.relative_to(ROOT)} sha256 {sha256_file(mpath)}")
    if drift or missing:
        for d in drift:
            print(f"  DRIFT {d['path']}: {d['snapshot_sha256'][:12]} -> {(d['live_sha256'] or 'MISSING')[:12]}")
        for m in missing:
            print(f"  MISSING {m}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
