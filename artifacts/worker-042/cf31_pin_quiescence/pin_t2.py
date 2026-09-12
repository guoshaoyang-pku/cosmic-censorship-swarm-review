#!/usr/bin/env python3
"""W042-CF31-PIN-QUIESCENCE-10 freeze-first pin (T2).

Read-only on every canonical path. Copies the live review corpus and the
adjudication-relevant canonical files byte-for-byte into snapshot_t2/, with a
manifest of sha256/bytes/mtime. Also verifies the T1 substrate
(artifacts/worker-042/review_corpus_mutation/snapshot, pinned 2026-09-12T01:19:28+08:00)
still re-hashes to its own manifest, and re-hashes every live file it copied to
detect in-window drift.

Writes only under artifacts/worker-042/cf31_pin_quiescence/.
Usage: python3 artifacts/worker-042/cf31_pin_quiescence/pin_t2.py
Exit codes: 0 ok, 2 pin-window drift or T1 substrate self-check failure.
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
SNAP = os.path.join(HERE, "snapshot_t2")
TASK_ID = "W042-CF31-PIN-QUIESCENCE-10"
CST = timezone(timedelta(hours=8))

T1_MANIFEST = "artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json"
T1_REVIEWS_DIR = "artifacts/worker-042/review_corpus_mutation/snapshot/reviews_t1"
F2B_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"

# Single-file sources pinned this round (adjudication-relevant).
SOURCES = [
    ("research_map/research_map.json", "map"),
    ("research_map/events.jsonl", "events"),
    ("runtime/state/artifact_hashes.json", "artifact_hashes"),
    ("artifacts/formulation/FROZEN.json", "frozen_manifest"),
    ("schemas/af_scc_c0_vacuum.yaml", "f2b_schema"),
    ("schemas/af_scc_c2_vacuum.yaml", "f2a_schema"),
    ("schemas/af_wcc_vacuum.yaml", "f1_schema"),
    ("artifacts/worker-017/cf31_f2b_census/binding_table.json", "w017_binding_table"),
    (T1_MANIFEST, "t1_manifest"),
]


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
    rev_dir = os.path.join(SNAP, "reviews_t2")
    os.makedirs(rev_dir, exist_ok=True)
    manifest = {
        "schema": "w042-pin/v1",
        "task_id": TASK_ID,
        "actor": "worker-042",
        "pinned_at": now(),
        "repo": REPO,
        "f2b_pin_full_sha256": F2B_PIN,
        "sources": {},
        "reviews_count": 0,
        "reviews_manifest": {},
        "t1": {},
        "pin_window_drift": [],
    }

    live_reviews = os.path.join(REPO, "reviews")
    names = sorted(n for n in os.listdir(live_reviews)
                   if os.path.isfile(os.path.join(live_reviews, n)))
    for name in names:
        src = os.path.join(live_reviews, name)
        h = sha256_file(src)
        shutil.copyfile(src, os.path.join(rev_dir, name))
        st = os.stat(src)
        manifest["reviews_manifest"][name] = {
            "sha256": h,
            "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
        }
    manifest["reviews_count"] = len(names)

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

    # T1 substrate self-check (the bytes the T1 manifest describes must be intact).
    t1m = json.load(open(os.path.join(REPO, T1_MANIFEST)))
    ok, bad = 0, []
    for name, rec in sorted(t1m["reviews_manifest"].items()):
        p = os.path.join(REPO, T1_REVIEWS_DIR, name)
        if not os.path.exists(p) or sha256_file(p) != rec["sha256"]:
            bad.append(name)
        else:
            ok += 1
    manifest["t1"] = {
        "manifest_path": T1_MANIFEST,
        "manifest_sha256": manifest["sources"]["t1_manifest"]["sha256"],
        "pinned_at": t1m.get("pinned_at"),
        "reviews_count": t1m.get("reviews_count"),
        "reviews_dir": T1_REVIEWS_DIR,
        "reviews_manifest_sha256": hashlib.sha256(
            json.dumps(t1m["reviews_manifest"], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "snapshot_selfcheck_ok": ok,
        "snapshot_selfcheck_bad": bad,
    }

    # Re-hash every live file copied, to detect drift inside this pin window.
    for name in names:
        if sha256_file(os.path.join(live_reviews, name)) != manifest["reviews_manifest"][name]["sha256"]:
            manifest["pin_window_drift"].append("reviews/" + name)
    for rel, tag in SOURCES:
        if sha256_file(os.path.join(REPO, rel)) != manifest["sources"][tag]["sha256"]:
            manifest["pin_window_drift"].append(rel)

    out = os.path.join(SNAP, "manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")

    print("T2 pin: %d review files; T1 substrate %d/%d verified" % (
        manifest["reviews_count"], ok, ok + len(bad)))
    for tag, rec in manifest["sources"].items():
        print("  %-18s %s  %s" % (tag, rec["sha256"][:12], rec["path"]))
    print("  t1 reviews_manifest %s" % manifest["t1"]["reviews_manifest_sha256"][:12])
    print("  t2 manifest         %s" % sha256_file(out)[:12])
    if bad:
        print("T1 SUBSTRATE SELFCHECK FAILED:", bad)
        return 2
    if manifest["pin_window_drift"]:
        print("PIN WINDOW DRIFT:", manifest["pin_window_drift"])
        return 2
    print("pin window drift: []")
    return 0


if __name__ == "__main__":
    sys.exit(main())
