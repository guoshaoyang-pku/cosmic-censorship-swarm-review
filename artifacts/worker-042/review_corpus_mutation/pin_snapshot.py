#!/usr/bin/env python3
"""W042-REVIEW-CORPUS-MUTATION-09 freeze-first pin.

Copies every live review file (reviews/*), the live map / event stream /
artifact-hash registry, and the T0 manifest written by worker-042's
W042-GATE-SCAN-GAP-02 (gate_scan_gap/snapshot/manifest.json, T0 pin
2026-09-12T00:26:27+08:00) into snapshot/ under sha256-named copies plus a
manifest.  Writes only under this worker's artifacts path.

Usage:
  python3 artifacts/worker-042/review_corpus_mutation/pin_snapshot.py
Exit codes: 0 ok, 2 pin-window drift.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SNAP = os.path.join(HERE, "snapshot")
TASK_ID = "W042-REVIEW-CORPUS-MUTATION-09"
CST = timezone(timedelta(hours=8))

# Sources pinned byte-for-byte.  T0 reviews live in the worker's own
# gate_scan_gap snapshot; the T0 manifest is pinned as a source file too.
SOURCES = [
    ("research_map/research_map.json", "map"),
    ("research_map/events.jsonl", "events"),
    ("runtime/state/artifact_hashes.json", "artifact_hashes"),
    ("artifacts/worker-042/gate_scan_gap/snapshot/manifest.json", "t0_manifest"),
]
T0_REVIEWS = "artifacts/worker-042/gate_scan_gap/snapshot/reviews"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    os.makedirs(SNAP, exist_ok=True)
    t1_dir = os.path.join(SNAP, "reviews_t1")
    os.makedirs(t1_dir, exist_ok=True)
    manifest = {
        "schema": "w042-pin/v1",
        "task_id": TASK_ID,
        "actor": "worker-042",
        "pinned_at": now(),
        "repo": REPO,
        "sources": {},
        "reviews_count": 0,
        "reviews_manifest": {},
        "t0": {},
        "pin_window_drift": [],
    }

    # --- live review corpus (T1) ------------------------------------------
    live_reviews = os.path.join(REPO, "reviews")
    names = sorted(n for n in os.listdir(live_reviews)
                   if os.path.isfile(os.path.join(live_reviews, n)))
    for name in names:
        src = os.path.join(live_reviews, name)
        h = sha256_file(src)
        dst = os.path.join(t1_dir, name)
        shutil.copyfile(src, dst)
        st = os.stat(src)
        manifest["reviews_manifest"][name] = {
            "sha256": h,
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
        }
    manifest["reviews_count"] = len(names)

    # --- single-file sources ----------------------------------------------
    for rel, tag in SOURCES:
        src = os.path.join(REPO, rel)
        h = sha256_file(src)
        ext = os.path.splitext(rel)[1] or ".bin"
        dst = os.path.join(SNAP, "%s_%s%s" % (tag, h[:12], ext))
        shutil.copyfile(src, dst)
        st = os.stat(src)
        manifest["sources"][tag] = {
            "path": rel,
            "sha256": h,
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
            "snapshot": os.path.basename(dst),
        }

    # --- T0 substrate (worker-042's own earlier pin) ----------------------
    t0_manifest = json.load(open(os.path.join(REPO, "artifacts/worker-042/gate_scan_gap/snapshot/manifest.json")))
    manifest["t0"] = {
        "manifest_path": "artifacts/worker-042/gate_scan_gap/snapshot/manifest.json",
        "manifest_sha256": manifest["sources"]["t0_manifest"]["sha256"],
        "pinned_at": t0_manifest.get("pinned_at"),
        "reviews_count": t0_manifest.get("reviews_count"),
        "reviews_dir": T0_REVIEWS,
        "reviews_manifest_sha256": hashlib.sha256(
            json.dumps(t0_manifest["reviews_manifest"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    # verify the T0 bytes are still the bytes the T0 manifest describes
    t0_ok, t0_bad = 0, []
    for name, rec in sorted(t0_manifest["reviews_manifest"].items()):
        p = os.path.join(REPO, T0_REVIEWS, name)
        if not os.path.exists(p) or sha256_file(p) != rec["sha256"]:
            t0_bad.append(name)
        else:
            t0_ok += 1
    manifest["t0"]["snapshot_selfcheck_ok"] = t0_ok
    manifest["t0"]["snapshot_selfcheck_bad"] = t0_bad

    # --- pin-window drift: re-hash every live source we copied ------------
    for name in names:
        p = os.path.join(live_reviews, name)
        if sha256_file(p) != manifest["reviews_manifest"][name]["sha256"]:
            manifest["pin_window_drift"].append("reviews/" + name)
    for rel, tag in SOURCES:
        if sha256_file(os.path.join(REPO, rel)) != manifest["sources"][tag]["sha256"]:
            manifest["pin_window_drift"].append(rel)

    with open(os.path.join(SNAP, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")

    print("T1 pin: %d review files, T0 substrate %d/%d verified" % (
        manifest["reviews_count"], t0_ok, t0_ok + len(t0_bad)))
    for tag, rec in manifest["sources"].items():
        print("  %-16s %s  %s" % (tag, rec["sha256"][:12], rec["path"]))
    print("  t0 manifest      %s (reviews_manifest %s)" % (
        manifest["t0"]["manifest_sha256"][:12], manifest["t0"]["reviews_manifest_sha256"][:12]))
    if t0_bad:
        print("T0 SNAPSHOT SELFCHECK FAILED:", t0_bad)
        return 2
    if manifest["pin_window_drift"]:
        print("PIN WINDOW DRIFT:", manifest["pin_window_drift"])
        return 2
    print("pin window drift: []")
    return 0


if __name__ == "__main__":
    sys.exit(main())
