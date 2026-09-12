#!/usr/bin/env python3
"""W068-FORM-HELDOUT10-XAGENT-15 shadow builder (worker-068, bounded class-bound task).

Builds a worker-068-owned, fully pinned snapshot of:
  * the two canonical class-binding stage tools + their relative dependencies
    (stage A resolves rule_spec.json and KEY_MANIFEST.json relative to its own location,
    so the snapshot mirrors artifacts/formulation/),
  * the three rev13 canonical schemas (used as frozen canonical controls),
  * the binding context (taxonomy, FROZEN.json),
  * the complete FORM-HELDOUT-10 corpus authored by worker-084
    (3 bases, 33 mutants, 4 authored controls) plus its manifest / raw verdicts / report,

and writes manifest.json with a sha256 for every snapshot byte. Fails closed on any pinned
source or corpus fixture whose hash does not match the pre-registration / corpus manifest.

Writes nothing outside artifacts/worker-068/heldout10xagent15/. Read-only on canonical paths.

Usage: python3 build_shadow15.py
Exit 0 built; 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshot"
CST = timezone(timedelta(hours=8))
HELDOUT = "artifacts/heldout/heldout-10"

PINNED = {
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
}

TARGET = {
    f"{HELDOUT}/manifest.json":
        "d026fec40fe4dab9ae51c51a8fa870337224b973418c0139685cf2f3faa0c236",
    f"{HELDOUT}/raw/raw_verdicts.json":
        "b3480625da10cd3c6b3a69b7d400b20094fb500d308bbd7c2c009f672a9f44a3",
    f"{HELDOUT}/report.json":
        "5629e2a69c8664abe4b322281318bf5ca0754967cb87607c5818da7e015efd35",
    f"{HELDOUT}/verify/verification.json":
        "26a7399e78376d3920e49d7f7faf25a0f7e9543ab54e10845b55f6527e33672c",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    problems: list[str] = []
    if SNAP.exists():
        shutil.rmtree(SNAP)
    SNAP.mkdir(parents=True)

    # ---- 1. pre-registration present -----------------------------------------
    pre_path = HERE / "PREREGISTRATION.json"
    if not pre_path.exists():
        problems.append("PREREGISTRATION.json missing; it must exist before any build")
        print(json.dumps({"verdict": "PRECONDITION_FAILED", "problems": problems}, indent=1))
        return 2
    pre_sha = sha256_file(pre_path)

    # ---- 2. pinned upstream sources ------------------------------------------
    for rel, want in PINNED.items():
        src = ROOT / rel
        got = sha256_file(src) if src.exists() else None
        if got != want:
            problems.append(f"pinned source mismatch {rel}: {got} != {want}")
            continue
        dst = SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    # ---- 3. replication target (worker-084 artifacts) ------------------------
    for rel, want in TARGET.items():
        src = ROOT / rel
        got = sha256_file(src) if src.exists() else None
        if got != want:
            problems.append(f"replication target mismatch {rel}: {got} != {want}")
            continue
        dst = SNAP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    # ---- 4. corpus fixtures against the corpus manifest ----------------------
    corpus_manifest = None
    cm_path = ROOT / HELDOUT / "manifest.json"
    if sha256_file(cm_path) == TARGET[f"{HELDOUT}/manifest.json"]:
        corpus_manifest = json.loads(cm_path.read_text())
    else:
        problems.append("heldout-10 manifest unreadable or drifted; cannot enumerate corpus")

    corpus_files: list[str] = []
    if corpus_manifest is not None:
        corpus_files = (
            [b["path"] for b in corpus_manifest["bases"].values()]
            + [m["path"] for m in corpus_manifest["mutants"]]
            + [c["path"] for c in corpus_manifest["controls"]]
        )
        declared = {}
        for b in corpus_manifest["bases"].values():
            declared[b["path"]] = b["sha256"]
        for m in corpus_manifest["mutants"]:
            declared[m["path"]] = m["sha256"]
        for c in corpus_manifest["controls"]:
            declared[c["path"]] = c["sha256"]
        for rel in corpus_files:
            src = ROOT / rel
            want = declared[rel]
            got = sha256_file(src) if src.exists() else None
            if got != want:
                problems.append(f"corpus fixture mismatch {rel}: {got} != {want}")
                continue
            dst = SNAP / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)

    if problems:
        print(json.dumps({"verdict": "PRECONDITION_FAILED", "problems": problems}, indent=1))
        return 2

    # ---- 5. manifest of every snapshot byte ----------------------------------
    entries = {}
    for p in sorted(SNAP.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(SNAP))
            entries[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    manifest = {
        "schema": "worker-068/heldout10xagent15/snapshot-manifest/v1",
        "task_id": "W068-FORM-HELDOUT10-XAGENT-15",
        "actor": "worker-068",
        "built_at": now(),
        "source_root": str(ROOT),
        "preregistration_sha256": pre_sha,
        "pinned_sources": PINNED,
        "replication_target": TARGET,
        "corpus_id": "FORM-HELDOUT-10",
        "corpus_manifest_sha256": TARGET[f"{HELDOUT}/manifest.json"],
        "corpus_counts": {
            "bases": len(corpus_manifest["bases"]),
            "mutants": len(corpus_manifest["mutants"]),
            "authored_controls": len(corpus_manifest["controls"]),
            "frozen_canonical_controls": len(corpus_manifest["frozen_canonical_controls"]),
        },
        "corpus_fixture_paths": sorted(corpus_files),
        "entries": entries,
    }
    mp = HERE / "manifest.json"
    mp.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "verdict": "BUILT",
        "manifest": str(mp.relative_to(ROOT)),
        "manifest_sha256": sha256_file(mp),
        "files": len(entries),
        "corpus_counts": manifest["corpus_counts"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
