#!/usr/bin/env python3
"""W48-F2A-REV27-REPIN-01 input snapshotter (worker-048).

Freezes the exact bytes an audit read, because the formulation tree was being
rewritten while this worker ran (FROZEN rev27 frozen_at 00:32:59, then
gate_test_report.json observed rewritten at 00:33:42 and 00:34:00).

Reads each source once into memory, records sha256+bytes+mtime around the read,
writes an immutable copy under snapshot/, and re-verifies the copy hash.  A file
whose mtime moved between the two stats is marked unstable and the manifest is
still written: the audit binds to the recorded bytes, not to the path.

Run:  python3 snapshot_inputs.py [--out snapshot_manifest.json]
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]

INPUTS = [
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/evidence/gate_test_report.json",
    "artifacts/formulation/evidence/close_findings_rev27_report.json",
    "reviews/F2a-review-034.json",
    "reviews/F2a-review-lead-audit-r2.json",
    "reviews/F2b-review-lead-audit-r2.json",
]


def snapshot_one(rel, snapdir):
    src = ROOT / rel
    if not src.exists():
        return {"path": rel, "exists": False}
    st0 = src.stat()
    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    st1 = src.stat()
    stem = src.name
    if stem.endswith(".yaml"):
        stem = stem[: -len(".yaml")]
        ext = ".yaml"
    elif stem.endswith(".json"):
        stem = stem[: -len(".json")]
        ext = ".json"
    else:
        ext = "".join(src.suffixes)
        stem = src.name[: -len(ext)] if ext else src.name
    copy = snapdir / f"{stem}.{digest[:12]}{ext}"
    copy.write_bytes(data)
    copy_digest = hashlib.sha256(copy.read_bytes()).hexdigest()
    return {
        "path": rel,
        "exists": True,
        "sha256": digest,
        "bytes": len(data),
        "snapshot": str(copy.relative_to(ROOT)),
        "copy_sha256": copy_digest,
        "copy_matches": copy_digest == digest,
        "mtime_ns_before": st0.st_mtime_ns,
        "mtime_ns_after": st1.st_mtime_ns,
        "size_before": st0.st_size,
        "size_after": st1.st_size,
        "stable_during_read": (st0.st_mtime_ns == st1.st_mtime_ns and st0.st_size == st1.st_size),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="snapshot_manifest.json")
    ap.add_argument("--inputs", nargs="*", default=None)
    args = ap.parse_args()

    here = pathlib.Path(__file__).resolve().parent
    snapdir = here / "snapshot"
    snapdir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    t_wall = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    records = [snapshot_one(rel, snapdir) for rel in (args.inputs or INPUTS)]
    manifest = {
        "task_id": "W48-F2A-REV27-REPIN-01",
        "worker": "worker-048",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "measured_at": t_wall,
        "elapsed_s": round(time.time() - started, 3),
        "root": str(ROOT),
        "records": records,
    }
    out = here / args.out
    out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    bad = [r["path"] for r in records if r.get("exists") and not r.get("copy_matches")]
    unstable = [r["path"] for r in records if r.get("exists") and not r.get("stable_during_read")]
    print(f"snapshot: {len(records)} inputs, {sum(1 for r in records if r.get('exists'))} present, "
          f"{len(bad)} copy mismatches, {len(unstable)} unstable-during-read")
    for r in records:
        if r.get("exists"):
            print(f"  {r['sha256'][:12]} {r['bytes']:>7} {r['path']}")
        else:
            print(f"  ABSENT       {r['path']}")
    print(f"manifest -> {out.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
