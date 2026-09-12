#!/usr/bin/env python3
"""W042-ORDER-INVERSION-03 input pinning.

Freeze-first: copy the three inputs the audit reads (accepted event stream, the map
it feeds, and the applier that defines the stream's semantics) into snapshot/ under
sha256-named copies plus a manifest. The checker reads only the snapshot, so its
classification replays from pinned bytes even while the live files keep moving.

Writes only under artifacts/worker-042/cf14_order_inversion/snapshot/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"

SOURCES = {
    "events": ROOT / "research_map" / "events.jsonl",
    "map": ROOT / "research_map" / "research_map.json",
    "apply_events": ROOT / "research_map" / "apply_events.py",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(SNAP))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "task_id": "W042-ORDER-INVERSION-03",
        "actor": "worker-042",
        "pinned_at": datetime.now(CST).isoformat(timespec="seconds"),
        "purpose": ("pin the accepted event stream, the map it feeds, and the applier that "
                    "defines its overwrite semantics; the checker reads only this snapshot"),
        "files": {},
    }
    for name, src in SOURCES.items():
        if not src.is_file():
            print(f"FAIL missing source {src}", file=__import__("sys").stderr)
            return 2
        raw = src.read_bytes()
        digest = sha256_bytes(raw)
        suffix = "".join(src.suffixes)
        dest = out / f"{name}_{digest[:12]}{suffix}"
        if not dest.exists() or dest.read_bytes() != raw:
            dest.write_bytes(raw)
        entry = {
            "source_path": str(src.relative_to(ROOT)),
            "snapshot_path": str(dest.relative_to(ROOT)),
            "sha256": digest,
            "bytes": len(raw),
            "source_mtime": datetime.fromtimestamp(src.stat().st_mtime, CST).isoformat(timespec="seconds"),
        }
        if src.suffix == ".jsonl":
            entry["lines"] = sum(1 for ln in raw.decode("utf-8", "replace").splitlines() if ln.strip())
        manifest["files"][name] = entry

    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["sha256"][:12] for k, v in manifest["files"].items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
