#!/usr/bin/env python3
"""Build MANIFEST.json: sha256 per bundle file plus one bundle digest.

The manifest excludes itself and any __pycache__/.pyc byproducts, so the digest is
stable across runs. digest_definition is recorded in the manifest.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "MANIFEST.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = sorted(
        p
        for p in HERE.rglob("*")
        if p.is_file()
        and p.name != MANIFEST.name
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    )
    entries = [
        {
            "path": str(p.relative_to(HERE)),
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        }
        for p in files
    ]
    digest = hashlib.sha256(
        "\n".join(f"{e['path']} {e['sha256']}" for e in entries).encode("utf-8")
    ).hexdigest()
    manifest = {
        "bundle": "artifacts/worker-17/class_binding_gate",
        "file_count": len(entries),
        "bundle_digest_sha256": digest,
        "digest_definition": (
            "sha256 of '<relpath> <sha256>' lines sorted by path, "
            "MANIFEST.json/__pycache__/.pyc excluded"
        ),
        "files": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST} ({len(entries)} files, bundle_digest={digest})")


if __name__ == "__main__":
    main()
