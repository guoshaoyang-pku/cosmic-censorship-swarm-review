#!/usr/bin/env python3
"""Freeze-first pinner for W090-F2B-REV13-FULL-01.

Copies each audited input into snapshot/ under a sha256-named copy, then
re-hashes every live input to flag pin-window drift.  Read-only with respect
to canonical paths.  stdlib only.
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(OUT, "snapshot")
CST = timezone(timedelta(hours=8))

INPUTS = [
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "schemas/taxonomy_cases.jsonl",
    "schemas/semantic_contract_tests/observed_verdicts.json",
    "schemas/semantic_contract_tests/manifest.json",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(SNAP, exist_ok=True)
    entries = []
    for rel in INPUTS:
        live = os.path.join(ROOT, rel)
        if not os.path.isfile(live):
            entries.append({"path": rel, "status": "MISSING"})
            continue
        h_before = sha256(live)
        dest = os.path.join(SNAP, h_before + "__" + rel.replace("/", "__"))
        shutil.copy2(live, dest)
        h_copy = sha256(dest)
        h_after = sha256(live)
        entries.append({
            "path": rel,
            "sha256": h_before,
            "copy_sha256": h_copy,
            "bytes": os.path.getsize(live),
            "mtime_utc": datetime.fromtimestamp(os.path.getmtime(live), timezone.utc).isoformat(),
            "pin_window_drift": h_before != h_after,
        })
    manifest = {
        "schema": "w090-pin-manifest/v1",
        "task_id": "W090-F2B-REV13-FULL-01",
        "actor": "worker-090",
        "pinned_at": datetime.now(CST).isoformat(),
        "pin_order": "copy-then-rehash (freeze-first)",
        "root": ROOT,
        "n_inputs": len(INPUTS),
        "n_pinned": sum(1 for e in entries if e.get("sha256")),
        "entries": entries,
    }
    with open(os.path.join(SNAP, "MANIFEST.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    drift = [e["path"] for e in entries if e.get("pin_window_drift")]
    print("pinned", manifest["n_pinned"], "inputs; pin-window drift:", drift)
    for e in entries:
        print(" ", (e.get("sha256") or "MISSING")[:12], e["path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
