#!/usr/bin/env python3
"""W065-R2-CARDBIND-CENSUS-03 helper: pin the frozen census input bytes by hash.

The census is cutoff-bound and the repo is live (workers keep writing reviews/*.json and the
controller keeps rewriting research_map.json), so a report run against the live tree is not
byte-reproducible. This helper records a sha256 manifest of a frozen snapshot so the report
is reproducible from pinned bytes. Deterministic: same on-disk bytes -> same manifest modulo
the --snapshot root string.

Worker-level measurement only: sets no gate verdict, no node status, no validation_status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            yield rel, full


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="frozen repo copy (reviews/ + research_map/)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cutoff", required=True)
    ap.add_argument("--generated-at", required=True)
    ap.add_argument("--census-tool", required=True, help="census.py actually invoked")
    ap.add_argument("--prereg", required=True)
    ap.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="relative path to omit from entries (e.g. the census out dir if nested)",
    )
    args = ap.parse_args()

    snap = os.path.abspath(args.snapshot)
    entries = []
    for rel, full in walk(snap):
        rel = rel.replace(os.sep, "/")
        if rel in args.exclude:
            continue
        st = os.stat(full)
        entries.append(
            {
                "path": rel,
                "sha256": sha256_file(full),
                "bytes": st.st_size,
                "mtime": st.st_mtime,
            }
        )
    entries.sort(key=lambda e: e["path"])

    manifest = {
        "schema": "w065-input-manifest/1",
        "task_id": "W065-R2-CARDBIND-CENSUS-03",
        "worker": "worker-065",
        "gate": "G-AUDIT",
        "node_id": "A1",
        "cutoff": args.cutoff,
        "generated_at": args.generated_at,
        "snapshot_root": snap,
        "snapshot_ephemeral": (
            "snapshot_root is a scratch copy; the manifest path+sha256 entries are the durable "
            "pins and can be verified against any copy of the same bytes."
        ),
        "map": {
            "path": "research_map/research_map.json",
            "sha256": sha256_file(os.path.join(snap, "research_map", "research_map.json")),
        },
        "prereg": {
            "path": os.path.relpath(os.path.abspath(args.prereg), os.getcwd()).replace(os.sep, "/"),
            "sha256": sha256_file(args.prereg),
        },
        "census_tool": {
            "path": os.path.relpath(os.path.abspath(args.census_tool), os.getcwd()).replace(os.sep, "/"),
            "sha256": sha256_file(args.census_tool),
        },
        "entry_count": len(entries),
        "entries": entries,
        "non_claims": [
            "Worker-level measurement only: no gate verdict, no node status, no validation_status.",
            "The manifest pins bytes read by the census run; it is not a claim about any verdict's substance.",
        ],
    }
    with open(args.out, "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(
        json.dumps(
            {
                "out": args.out,
                "entries": len(entries),
                "map_sha256": manifest["map"]["sha256"],
                "census_tool_sha256": manifest["census_tool"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
