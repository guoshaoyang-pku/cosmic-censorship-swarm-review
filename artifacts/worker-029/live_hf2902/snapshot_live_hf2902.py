#!/usr/bin/env python3
"""
W029-LIVE-HF2902-04 — snapshot step (read-only on canonical paths).

Task (worker-029, one bounded class-bound task):
  Re-bind the standing hard finding HF-29-02 ("l1_ledger_refs assert
  citation_status=verified_by_L1 while the ledger records abstract-read") to the
  CURRENT bytes, after ledger/theorems.jsonl moved from the rev12-measured
  3e3d35531421 to a1674f094979 (CF-19 freeze breach) and after all three class
  schemas were re-verified unchanged.

This script copies the four canonical formulation inputs plus three ledger
generations into this directory, hashes them BEFORE analysis, and writes
snapshot_manifest.json.  It never writes to a canonical path.

Ledger generations:
  pre_rev3  artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl  (ce42d205e761)
  rev3      artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl (3e3d35531421)
  live      ledger/theorems.jsonl                                                (a1674f094979)
The rev12 closure snapshot (artifacts/worker-029/rev12_closure_verify/ledger_theorems_snapshot.jsonl)
is an independent copy of the rev3 generation; equality is checked, not assumed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # repo root: artifacts/worker-029/live_hf2902 -> ai4math-swarm
REL = "artifacts/worker-029/live_hf2902"
SNAP = HERE / "snapshots"
TASK = "W029-LIVE-HF2902-04"

CANON = {
    "af_wcc_vacuum.yaml": "schemas/af_wcc_vacuum.yaml",
    "af_scc_c2_vacuum.yaml": "schemas/af_scc_c2_vacuum.yaml",
    "af_scc_c0_vacuum.yaml": "schemas/af_scc_c0_vacuum.yaml",
    "formulation_taxonomy.canonical.yaml": "research_map/formulation_taxonomy.yaml",
}

LEDGERS = {
    "live": {
        "source_path": "ledger/theorems.jsonl",
        "snapshot_name": "ledger_live_snapshot.jsonl",
        "label": "current canonical ledger (CF-19 rewrite at 2026-09-12T00:35:19+08:00)",
    },
    "rev3": {
        "source_path": "artifacts/literature/archive/theorems.rev3-handpatch-20260912T003026.jsonl",
        "snapshot_name": "ledger_rev3_snapshot.jsonl",
        "label": "rev-3 handpatch archive (the ledger generation measured by W029-REV12-CLOSURE-03)",
    },
    "pre_rev3": {
        "source_path": "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
        "snapshot_name": "ledger_pre_rev3_snapshot.jsonl",
        "label": "pre-rev3 archive generation",
    },
}

# Pins the prior task measured at; used only to report whether the schema bytes moved.
REV12_PINS = {
    "af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "formulation_taxonomy.canonical.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
REV12_LEDGER = "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6"
REV12_LEDGER_SNAPSHOT = "artifacts/worker-029/rev12_closure_verify/ledger_theorems_snapshot.jsonl"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(TZ).isoformat(timespec="seconds")
    SNAP.mkdir(parents=True, exist_ok=True)

    files = {}
    live_hashes = {}
    for name, rel in CANON.items():
        src = ROOT / rel
        if not src.exists():
            print(f"MISSING canonical path: {rel}", file=sys.stderr)
            return 2
        h = sha256(src)
        dst = SNAP / name
        shutil.copyfile(src, dst)
        files[name] = {
            "source_path": rel,
            "snapshot_path": f"{REL}/snapshots/{name}",
            "sha256": h,
            "bytes": src.stat().st_size,
            "sha256_at_snapshot": h,
            "snapshot_sha256": sha256(dst),
            "rev12_pin": REV12_PINS.get(name),
            "unchanged_from_rev12_pin": h == REV12_PINS.get(name),
        }
        live_hashes[rel] = h

    ledgers = {}
    for tag, meta in LEDGERS.items():
        src = ROOT / meta["source_path"]
        if not src.exists():
            print(f"MISSING ledger path: {meta['source_path']}", file=sys.stderr)
            return 2
        h = sha256(src)
        dst = HERE / meta["snapshot_name"]
        shutil.copyfile(src, dst)
        ledgers[tag] = {
            "source_path": meta["source_path"],
            "snapshot_path": f"{REL}/{meta['snapshot_name']}",
            "sha256": h,
            "bytes": src.stat().st_size,
            "label": meta["label"],
            "sha256_at_snapshot": h,
            "snapshot_sha256": sha256(dst),
        }
        live_hashes[meta["source_path"]] = h

    # Independent copy of the rev3 generation inside the rev12 artifact tree.
    xcheck_path = ROOT / REV12_LEDGER_SNAPSHOT
    xcheck = {
        "path": REV12_LEDGER_SNAPSHOT,
        "exists": xcheck_path.exists(),
        "sha256": sha256(xcheck_path) if xcheck_path.exists() else None,
        "equals_rev3_archive": (sha256(xcheck_path) == ledgers["rev3"]["sha256"]) if xcheck_path.exists() else False,
        "equals_rev12_pin": (sha256(xcheck_path) == REV12_LEDGER) if xcheck_path.exists() else False,
    }

    manifest = {
        "task_id": TASK,
        "worker": "worker-029",
        "purpose": (
            "Re-bind HF-29-02 to the current bytes: three class schemas + taxonomy + three ledger "
            "generations snapshotted before analysis; all canonical paths read-only."
        ),
        "snapshot_created_at": now,
        "repo_root": str(ROOT),
        "files": files,
        "ledgers": ledgers,
        "live_hashes_at_snapshot": live_hashes,
        "rev12_pins": REV12_PINS,
        "rev12_ledger_pin": REV12_LEDGER,
        "rev12_ledger_snapshot_crosscheck": xcheck,
        "read_only_note": "no canonical path was written by this task; snapshots are copies under this directory",
    }
    out = HERE / "snapshot_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote", out.relative_to(ROOT), sha256(out)[:12])
    print(json.dumps({k: v["sha256"][:12] for k, v in files.items()}, indent=1))
    print(json.dumps({k: v["sha256"][:12] for k, v in ledgers.items()}, indent=1))
    print("rev12 snapshot crosscheck equals rev3 archive:", xcheck["equals_rev3_archive"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
