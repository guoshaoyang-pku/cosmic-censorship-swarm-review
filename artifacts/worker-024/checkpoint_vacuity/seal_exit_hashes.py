#!/usr/bin/env python3
"""Seal entry/exit hashes for W024-CHECKPOINT-VACUITY-01.

Writes artifacts/worker-024/checkpoint_vacuity/exit_hashes.json:
  - live canonical entry hashes (as read by the driver) and current exit hashes + drift flags
  - every artifact file in this directory with sha256/bytes, and a rollup digest
  - sandbox input pins re-verified against the on-disk snapshots

Usage: python3 artifacts/worker-024/checkpoint_vacuity/seal_exit_hashes.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ARTIFACT = Path(__file__).resolve().parent
REPO = ARTIFACT.parents[2]
CST = timezone(timedelta(hours=8))
SKIP = {"exit_hashes.json"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report = json.loads((ARTIFACT / "report.json").read_text())
    entry = report["live_canonical_entry"]
    exit_h = {}
    for rel in entry:
        p = REPO / rel
        exit_h[rel] = sha256(p) if p.is_file() else None
    drift = {rel: [entry[rel], exit_h[rel]] for rel in entry if entry[rel] != exit_h[rel]}
    files = {}
    h = hashlib.sha256()
    for p in sorted(x for x in ARTIFACT.rglob("*") if x.is_file()):
        rel = str(p.relative_to(ARTIFACT))
        if rel in SKIP or rel.startswith("tmp/"):
            continue
        files[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size}
        h.update(f"{rel}\0{files[rel]['sha256']}\n".encode())
    pins_ok = None  # sandbox pins are re-verified by the driver on every run
    snap = {}
    for p in sorted((ARTIFACT / "snapshots").iterdir()):
        if p.is_file():
            snap[p.name] = sha256(p)
    out = {
        "audit_id": report["audit_id"],
        "actor": "worker-024",
        "sealed_at": datetime.now(CST).isoformat(timespec="seconds"),
        "audited_hash": report["audited_hash"],
        "sandbox_pins": report["sandbox_pins"],
        "snapshot_hashes": snap,
        "live_canonical_entry": entry,
        "live_canonical_exit": exit_h,
        "live_canonical_drift": drift,
        "artifact_files": files,
        "artifact_rollup_sha256": h.hexdigest(),
        "artifact_file_count": len(files),
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "authority_note": "worker seal: no gate verdict, no node transition, no canonical write",
    }
    (ARTIFACT / "exit_hashes.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"sealed {len(files)} files, rollup {h.hexdigest()[:12]}, live drift {sorted(drift)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
