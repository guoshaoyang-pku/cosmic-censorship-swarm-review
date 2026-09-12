#!/usr/bin/env python3
"""W48-GFORM-VOCAB-ADJUDICATION-01 / snapshot_inputs.py

Read-only snapshot of the bytes the vocabulary adjudication binds to.

Design (why): the G-FORM pins were written twice inside the audit window on
2026-09-12 (00:31:41 F0 rev5, 00:32:02 schemas).  A verdict that cites a live
path is only as good as the instant it read it, so this tool copies every input
into ./snapshot/ , records the sha256 measured from the *source* bytes, and then
re-reads the source to prove the read was stable.  Nothing outside
artifacts/worker-048/gform_vocab_adjudication/ is written.

Usage:
  python3 snapshot_inputs.py [--out snapshot_manifest.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

INPUTS = [
    "research_map/formulation_taxonomy.yaml",              # F0 canonical taxonomy (declared)
    "artifacts/formulation/formulation_taxonomy.yaml",     # F0 companion supplement
    "schemas/af_wcc_vacuum.yaml",                          # F1
    "schemas/af_scc_c2_vacuum.yaml",                       # F2a
    "schemas/af_scc_c0_vacuum.yaml",                       # F2b
    "artifacts/formulation/rule_spec.json",                # SPEC_D, gate vocabulary
    "artifacts/formulation/VOCAB_ALIASES.json",            # alias registry / policy
    "artifacts/formulation/FROZEN.json",                   # rev28 pins
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/KEY_MANIFEST.json",
]

SAFE = {
    "research_map/formulation_taxonomy.yaml": "f0_canonical.formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": "f0_supplement.formulation_taxonomy.yaml",
    "schemas/af_wcc_vacuum.yaml": "f1.af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "f2a.af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "f2b.af_scc_c0_vacuum.yaml",
    "artifacts/formulation/rule_spec.json": "rule_spec.json",
    "artifacts/formulation/VOCAB_ALIASES.json": "VOCAB_ALIASES.json",
    "artifacts/formulation/FROZEN.json": "FROZEN.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "taxonomy_consistency.json",
    "artifacts/formulation/tools/check_class_schema.py": "check_class_schema.py",
    "artifacts/formulation/KEY_MANIFEST.json": "KEY_MANIFEST.json",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="snapshot_manifest.json")
    args = ap.parse_args()

    snap = OUT_DIR / "snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    manifest = {
        "task_id": "W48-GFORM-VOCAB-ADJUDICATION-01",
        "worker": "worker-048",
        "snapshot_at": datetime.now(CST).isoformat(timespec="seconds"),
        "root": str(ROOT),
        "inputs": {},
        "copy_mismatches": [],
        "unstable_reads": [],
    }
    for rel in INPUTS:
        src = ROOT / rel
        if not src.is_file():
            manifest["copy_mismatches"].append({"path": rel, "reason": "missing"})
            continue
        stable = False
        for _ in range(3):
            b1 = src.read_bytes()
            h1 = sha256_bytes(b1)
            dst = snap / SAFE[rel]
            dst.write_bytes(b1)
            b2 = src.read_bytes()
            h2 = sha256_bytes(b2)
            if h1 == h2:
                stable = True
                break
        if not stable:
            manifest["unstable_reads"].append({"path": rel, "hash_first": h1, "hash_last": h2})
        if sha256_bytes(dst.read_bytes()) != h2:
            manifest["copy_mismatches"].append({"path": rel, "reason": "copy hash != source hash"})
        manifest["inputs"][rel] = {
            "sha256": h2,
            "bytes": len(b2),
            "snapshot_file": str(dst.relative_to(OUT_DIR)),
            "source_mtime": datetime.fromtimestamp(src.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "stable_read": stable,
        }

    # cross-check the frozen manifest's declared pins for the files it covers
    froz = json.loads((snap / "FROZEN.json").read_text())
    declared = {p: v.get("sha256") for p, v in froz.get("files", {}).items()}
    mismatches = []
    for rel, rec in manifest["inputs"].items():
        if rel in declared and declared[rel] != rec["sha256"]:
            mismatches.append({"path": rel, "frozen_rev28": declared[rel], "measured": rec["sha256"]})
    manifest["frozen_rev28"] = {
        "revision": froz.get("revision"),
        "frozen_at": froz.get("frozen_at"),
        "declared_vs_measured_mismatches": mismatches,
        "files_covered": sorted(k for k in declared if k in manifest["inputs"]),
    }
    out = OUT_DIR / args.out
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"snapshot: {len(manifest['inputs'])} inputs, "
          f"{len(manifest['copy_mismatches'])} copy mismatches, "
          f"{len(manifest['unstable_reads'])} unstable reads, "
          f"{len(mismatches)} FROZEN mismatches -> {out.name}")
    for rel, rec in sorted(manifest["inputs"].items()):
        print(f"  {rec['sha256'][:12]}  {rel}")
    return 0 if not manifest["copy_mismatches"] and not manifest["unstable_reads"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
