#!/usr/bin/env python3
"""Pin the inputs for W042-GATE-SCAN-GAP-02.

Copies research_map/events.jsonl, research_map/research_map.json,
runtime/state/artifact_hashes.json and every reviews/*.json into
artifacts/worker-042/gate_scan_gap/snapshot/ and writes a manifest with a
sha256 for every copied byte.  Read-only with respect to the repo: the only
writes are under artifacts/worker-042/gate_scan_gap/snapshot/.

Usage:
  python3 pin_snapshot.py [--repo <root>] [--out <dir>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "snapshot"))
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve()
    (out / "reviews").mkdir(parents=True, exist_ok=True)

    manifest = {
        "task_id": "W042-GATE-SCAN-GAP-02",
        "actor": "worker-042",
        "pinned_at": datetime.now(CST).isoformat(timespec="seconds"),
        "repo": str(repo),
        "files": {},
    }

    def pin(src: Path, dst_name: str) -> dict:
        b = src.read_bytes()
        h = sha256_bytes(b)
        dst = out / dst_name
        dst.write_bytes(b)
        rec = {"source": str(src.relative_to(repo)), "snapshot": dst_name,
               "sha256": h, "bytes": len(b)}
        manifest["files"][dst_name] = rec
        return rec

    ev = pin(repo / "research_map" / "events.jsonl",
             "events_" + sha256_bytes((repo / "research_map" / "events.jsonl").read_bytes())[:12] + ".jsonl")
    mp = pin(repo / "research_map" / "research_map.json",
             "research_map_" + sha256_bytes((repo / "research_map" / "research_map.json").read_bytes())[:12] + ".json")
    ah = pin(repo / "runtime" / "state" / "artifact_hashes.json",
             "artifact_hashes_" + sha256_bytes((repo / "runtime" / "state" / "artifact_hashes.json").read_bytes())[:12] + ".json")

    reviews = {}
    for rp in sorted((repo / "reviews").glob("*.json")):
        b = rp.read_bytes()
        h = sha256_bytes(b)
        dst = out / "reviews" / rp.name
        dst.write_bytes(b)
        reviews[rp.name] = {"sha256": h, "bytes": len(b)}
    manifest["reviews_manifest"] = reviews
    manifest["reviews_count"] = len(reviews)
    reviews_digest = sha256_bytes(json.dumps(reviews, sort_keys=True).encode())
    manifest["reviews_manifest_sha256"] = reviews_digest

    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "ok": True,
        "events": ev, "map": mp, "artifact_hashes": ah,
        "reviews_count": len(reviews), "reviews_manifest_sha256": reviews_digest,
        "manifest_sha256": sha256_bytes((out / "manifest.json").read_bytes()),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
