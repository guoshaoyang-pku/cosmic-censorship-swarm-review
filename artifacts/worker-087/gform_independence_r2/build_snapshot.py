#!/usr/bin/env python3
"""W087-GFORM-INDEP-05: freeze a hash-pinned copy of the audit input corpus.

The live swarm appends to research_map/events.jsonl and comms/outbox/*.jsonl and writes
new reviews/*.json several times per minute, so a coverage measurement taken directly
against the live tree is not reproducible (three back-to-back runs of the frozen
instrument produced three different verdict digests on 2026-09-12 between 01:00 and
01:01). This tool copies every input the instrument reads into a snapshot tree at a
recorded instant, records a sha256 for every copied file, and emits a manifest digest.
The instrument is then run against the snapshot, so the measurement is explicitly
"as of" the snapshot rather than "as of whenever the last run happened to read".

Read-only against the live tree. Writes only under the --out directory.

Usage: python3 build_snapshot.py --root <repo> --out <snapshot-dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))

INCLUDE_DIRS = [
    "comms/outbox",
    "reviews",
    "schemas",
    "artifacts/formulation",
]
INCLUDE_FILES = [
    "research_map/events.jsonl",
    "research_map/formulation_taxonomy.yaml",
]

# Canonical pins that the measurement is about. Recorded live at snapshot close so the
# snapshot's own copies can be checked against the live bytes at that instant.
PINS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, CST).isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    out = Path(a.out).resolve()
    started = datetime.now(CST)

    rels: list[str] = []
    for d in INCLUDE_DIRS:
        base = root / d
        if not base.is_dir():
            print(f"WARN missing include dir {d}")
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                if "__pycache__" in p.parts or p.name.startswith("._") or p.name == ".DS_Store":
                    continue
                rels.append(str(p.relative_to(root)))
    for f in INCLUDE_FILES:
        if (root / f).is_file():
            rels.append(f)
        else:
            print(f"WARN missing include file {f}")
    rels = sorted(set(rels))

    files: dict[str, dict] = {}
    for rel in rels:
        src = root / rel
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        files[rel] = {
            "sha256": sha256_file(dst),
            "bytes": dst.stat().st_size,
            "mtime_iso": iso(dst.stat().st_mtime),
        }

    live_pins = {rel: sha256_file(root / rel) for rel in PINS if (root / rel).is_file()}
    snap_pins = {rel: files[rel]["sha256"] for rel in PINS if rel in files}
    pin_match = {rel: (live_pins.get(rel) == snap_pins.get(rel)) for rel in live_pins}

    files_blob = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    manifest_digest = hashlib.sha256(files_blob).hexdigest()
    finished = datetime.now(CST)

    manifest = {
        "tool": "build_snapshot.py",
        "task_id": "W087-GFORM-INDEP-05",
        "actor": "worker-087",
        "snapshot_started_at": started.isoformat(timespec="seconds"),
        "snapshot_finished_at": finished.isoformat(timespec="seconds"),
        "root": str(root),
        "include_dirs": INCLUDE_DIRS,
        "include_files": INCLUDE_FILES,
        "n_files": len(files),
        "files": files,
        "manifest_digest_sha256": manifest_digest,
        "live_pins_at_snapshot_close": live_pins,
        "snapshot_pins": snap_pins,
        "snapshot_pin_matches_live": pin_match,
        "all_snapshot_pins_match_live": all(pin_match.values()) and len(pin_match) == len(PINS),
        "note": ("Per-file copies are taken over a short window; the append-only files "
                 "(events.jsonl, comms/outbox/*.jsonl) are read once each and their sha256 "
                 "is recorded above. The instrument must be run with --root pointing at this "
                 "snapshot so its corpus is byte-fixed."),
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "snapshot_out": str(out),
        "n_files": len(files),
        "manifest_digest_sha256": manifest_digest,
        "all_snapshot_pins_match_live": manifest["all_snapshot_pins_match_live"],
        "snapshot_started_at": manifest["snapshot_started_at"],
        "snapshot_finished_at": manifest["snapshot_finished_at"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
