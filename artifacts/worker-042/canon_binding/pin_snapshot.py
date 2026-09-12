#!/usr/bin/env python3
"""Freeze-first pinning tool for W042-CANON-BIND-04.

Copies, byte-exactly and read-only:
  * research_map/events.jsonl          (accepted stream, line order = arrival order)
  * research_map/research_map.json     (sole global state at pin)
  * every declared canonical gate-input path (see DECLARED_PATHS)

into artifacts/worker-042/canon_binding/snapshot/ and writes manifest.json
last.  The audit checker reads ONLY the snapshot directory, so every number in
report.json replays from pinned bytes; later writes to the live tree cannot
change the measurement.

The tool never writes to a canonical path and never edits the map.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CST = timezone(timedelta(hours=8))

# Declared canonical gate-input set.  `role` is the gate/authority that names the
# path; `source` is where the declaration lives.  The list is intentionally
# explicit (no globbing) so the same set can be re-pinned later.
DECLARED_PATHS = [
    {"path": "research_map/formulation_taxonomy.yaml", "node": "F0", "role": "G-F0 canonical taxonomy",
     "source": "controller_gate_audit.G-F0", "retired": False},
    {"path": "artifacts/formulation/formulation_taxonomy.yaml", "node": "F0", "role": "F0 class-contract supplement (F0-R)",
     "source": "CF-17 / REC-3 companion pair", "retired": False},
    {"path": "schemas/af_wcc_vacuum.yaml", "node": "F1", "role": "G-FORM F1 schema",
     "source": "controller_gate_audit.G-FORM", "retired": False},
    {"path": "schemas/af_scc_c2_vacuum.yaml", "node": "F2a", "role": "G-FORM F2a schema",
     "source": "controller_gate_audit.G-FORM", "retired": False},
    {"path": "schemas/af_scc_c0_vacuum.yaml", "node": "F2b", "role": "G-FORM F2b schema",
     "source": "controller_gate_audit.G-FORM", "retired": False},
    {"path": "schemas/af_scc_regularities.yaml", "node": "F2", "role": "retired merged F2 artifact (must not be a gate input)",
     "source": "map.frozen_artifacts active=false", "retired": True},
    {"path": "ledger/theorems.jsonl", "node": "L0", "role": "G-LIT L0 theorems ledger",
     "source": "controller_gate_audit.G-LIT / CF-19", "retired": False},
    {"path": "ledger/citation_audit.csv", "node": "L1", "role": "G-LIT L1 citation audit",
     "source": "controller_gate_audit.G-LIT", "retired": False},
    {"path": "evaluation_rubric.yaml", "node": "A0", "role": "G-AUDIT A0 rubric",
     "source": "controller_gate_audit.G-AUDIT", "retired": False},
    {"path": "numerics/CONVERGENCE_PROTOCOL.md", "node": "N0", "role": "G-NUM convergence protocol (C8)",
     "source": "controller_gate_audit.G-NUM", "retired": False},
    {"path": "artifacts/formulation/FROZEN.json", "node": "F0/F1/F2", "role": "freeze authority manifest (rev28)",
     "source": "astra-led04-freeze-hold pins", "retired": False},
    {"path": "research_map/class_separation.py", "node": "A1", "role": "active frozen class-separation gate tool",
     "source": "map.frozen_artifacts active=true", "retired": False},
    {"path": "runtime/bin/classsep_regression.py", "node": "A1", "role": "active frozen class-separation regression runner",
     "source": "map.frozen_artifacts active=true", "retired": False},
]

# 12-hex prefixes the pinned map's controller_gate_audit / handoff declare for the
# gate inputs above.  Read from research_map.json at 2026-09-12T00:37:18+08:00.
MAP_DECLARED = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a961",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda",
    "ledger/theorems.jsonl": "a1674f094979",
    "ledger/citation_audit.csv": "315c19145065",
    "evaluation_rubric.yaml": "d748a9e3574e",
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963",
    "artifacts/formulation/FROZEN.json": "2f358f6722d9",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flat(name: str) -> str:
    return name.replace("/", "__")


def pin_file(src_abs: str, dst_abs: str) -> dict:
    before = sha256_file(src_abs)
    shutil.copyfile(src_abs, dst_abs)
    after = sha256_file(dst_abs)
    return {
        "sha256_before_copy": before,
        "sha256_snapshot": after,
        "stable_during_copy": before == after,
        "bytes": os.path.getsize(dst_abs),
        "mtime_ns": os.stat(src_abs).st_mtime_ns,
        "mtime_iso": datetime.fromtimestamp(os.stat(src_abs).st_mtime, CST).isoformat(timespec="seconds"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()
    root, out = os.path.abspath(args.root), os.path.abspath(args.out)

    snap = os.path.join(out, "snapshot")
    canon = os.path.join(snap, "canonical")
    if os.path.isdir(snap):
        shutil.rmtree(snap)
    os.makedirs(canon)

    pinned_at = datetime.now(CST).isoformat(timespec="seconds")
    manifest = {
        "task_id": "W042-CANON-BIND-04",
        "worker": "worker-042",
        "pinned_at": pinned_at,
        "root": root,
        "stream": {},
        "declared_paths": [],
        "map_declared_prefixes": MAP_DECLARED,
    }

    for key, src in (("events", "research_map/events.jsonl"),
                     ("map", "research_map/research_map.json")):
        dst = os.path.join(snap, key + ".jsonl" if key == "events" else key + ".json")
        info = pin_file(os.path.join(root, src), dst)
        info.update({"source_path": src, "snapshot_path": os.path.relpath(dst, snap)})
        manifest["stream"][key] = info

    for item in DECLARED_PATHS:
        src_abs = os.path.join(root, item["path"])
        if not os.path.exists(src_abs):
            manifest["declared_paths"].append(dict(item, exists=False))
            continue
        dst = os.path.join(canon, flat(item["path"]))
        info = pin_file(src_abs, dst)
        rec = dict(item)
        rec.update(info)
        rec["snapshot_path"] = os.path.relpath(dst, snap)
        manifest["declared_paths"].append(rec)

    mpath = os.path.join(snap, "manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({
        "pinned_at": pinned_at,
        "manifest": os.path.relpath(mpath, root),
        "manifest_sha256": sha256_file(mpath),
        "events_sha256": manifest["stream"]["events"]["sha256_snapshot"],
        "map_sha256": manifest["stream"]["map"]["sha256_snapshot"],
        "declared": len(manifest["declared_paths"]),
        "missing": sum(1 for d in manifest["declared_paths"] if not d.get("exists", True)),
        "unstable": sum(1 for d in manifest["declared_paths"] if d.get("stable_during_copy") is False),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
