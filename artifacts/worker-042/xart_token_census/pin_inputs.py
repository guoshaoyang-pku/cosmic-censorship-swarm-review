#!/usr/bin/env python3
"""W042-XART-TOKEN-CENSUS-07 pin tool (freeze-first).

Copies every audited input into snapshot/ under a flat, sha256-named copy and
writes snapshot/manifest.json. Live hashes are measured before and after the
copy; a mismatch between the two is a pin-window move and voids the run.

Read-only with respect to every input: nothing outside this artifact directory
is written. No network. Deterministic given identical input bytes.

Usage:
  python3 pin_inputs.py [--root <swarm root>] [--out <artifact dir>]
Exit codes: 0 pinned, 2 pin window moved, 3 input missing.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

INPUTS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        return None
    return {"sha256": sha256_file(p), "bytes": os.path.getsize(p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    root, out = os.path.abspath(args.root), os.path.abspath(args.out)
    snap = os.path.join(out, "snapshot")
    os.makedirs(snap, exist_ok=True)

    before = {}
    for rel in INPUTS:
        m = measure(root, rel)
        if m is None:
            print("MISSING INPUT: %s" % rel, file=sys.stderr)
            return 3
        before[rel] = m

    copied = {}
    for rel, m in sorted(before.items()):
        name = rel.replace("/", "__")
        dst = os.path.join(snap, "%s.%s" % (name, m["sha256"][:12]))
        shutil.copyfile(os.path.join(root, rel), dst)
        copied[rel] = {"snapshot_name": os.path.basename(dst), "sha256": sha256_file(dst), "bytes": os.path.getsize(dst)}

    after = {rel: measure(root, rel) for rel in INPUTS}

    drift = [rel for rel in INPUTS if before[rel]["sha256"] != after[rel]["sha256"]]
    mismatch = [rel for rel in INPUTS if copied[rel]["sha256"] != before[rel]["sha256"]]

    manifest = {
        "tool": "artifacts/worker-042/xart_token_census/pin_inputs.py",
        "root_at_pin": root,
        "inputs": copied,
        "live_before": before,
        "live_after": after,
        "pin_window_drift": drift,
        "copy_mismatch": mismatch,
        "status": "PINNED" if not drift and not mismatch else "VOID_PIN_WINDOW_MOVED",
    }
    man_path = os.path.join(snap, "manifest.json")
    with open(man_path, "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("manifest sha256: %s" % sha256_file(man_path))
    print("status: %s" % manifest["status"])
    for rel in INPUTS:
        print("  %s %s" % (before[rel]["sha256"][:16], rel))
    if drift or mismatch:
        print("PIN WINDOW MOVED: drift=%s mismatch=%s" % (drift, mismatch), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
