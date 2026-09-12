#!/usr/bin/env python3
"""Check whether worker-18 reviews still bind to the files on disk.

The reviews declare pinned sha256 values. This script re-hashes the current files and exits 1
if any pin is stale, naming the review and the changed artifact. Run it before reusing any
worker-18 verdict; a stale review must be re-issued, never silently reused.

Usage: python3 verify_reviews_current.py [--json OUT]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REVIEWS = {
    "reviews/F2-review-18.json": ["schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"],
    "reviews/F2a-review-18.json": ["schemas/af_scc_c2_vacuum.yaml"],
    "reviews/F2b-review-18.json": ["schemas/af_scc_c0_vacuum.yaml"],
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def pins_of(doc: dict) -> dict:
    pins = {}
    if "inputs" in doc and isinstance(doc["inputs"], dict):
        for cid, meta in doc["inputs"].items():
            if isinstance(meta, dict) and meta.get("path") and meta.get("sha256"):
                pins[meta["path"]] = meta["sha256"]
    if doc.get("artifact") and doc.get("artifact_sha256"):
        pins[doc["artifact"]] = doc["artifact_sha256"]
    return pins


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    rows, stale = [], []
    for rel, targets in REVIEWS.items():
        rp = ROOT / rel
        if not rp.exists():
            rows.append({"review": rel, "exists": False, "status": "missing"})
            stale.append(rel)
            continue
        doc = json.loads(rp.read_text())
        pins = pins_of(doc)
        for t in targets:
            disk = sha(ROOT / t) if (ROOT / t).exists() else None
            pinned = pins.get(t) or pins.get(str(t))
            ok = bool(disk and pinned and disk == pinned)
            rows.append({"review": rel, "artifact": t, "pinned": (pinned or "")[:16],
                         "disk": (disk or "")[:16], "current": ok})
            if not ok:
                stale.append(f"{rel} -> {t}")
    verdict = "current" if not stale else "stale"
    out = {"verdict": verdict, "stale": stale, "rows": rows}
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0 if not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
