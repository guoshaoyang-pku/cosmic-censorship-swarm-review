#!/usr/bin/env python3
"""W066-F2B-REV29-CONTAINMENT-01 -- pin step.

Read-only. Copies every input into pinned/ and records sha256/bytes/mtime.
Fails closed (exit 2) if any input does not hash to the expected value, so a
verdict can never be emitted against moving bytes.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

PINS = {
    "c0_canonical": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "role": "target class schema AF-SCC-C0-VAC-GEN (F2b, rev13)",
    },
    "c0_mirror": {
        "path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "role": "byte-identical mirror",
    },
    "c2_canonical": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "role": "sibling class schema AF-SCC-C2-VAC-GEN (F2a, rev13)",
    },
    "f1_canonical": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "role": "sibling class schema AF-WCC-VAC-GEN (F1, rev13)",
    },
    "f0_taxonomy": {
        "path": "research_map/formulation_taxonomy.yaml",
        "sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "role": "G-F0-frozen declared taxonomy (rev5)",
    },
    "frozen_manifest": {
        "path": "artifacts/formulation/FROZEN.json",
        "sha256": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
        "role": "FROZEN rev29, third write (frozen_at 2026-09-12T00:57:26+08:00)",
    },
    "taxonomy_consistency": {
        "path": "artifacts/formulation/evidence/taxonomy_consistency.json",
        "sha256": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
        "role": "consistency evidence declared by all three rev13 schemas",
    },
    "candidate_98f9ec83": {
        "path": "artifacts/worker-008/f2b_rev11_dualrepair/candidate_rev12/af_scc_c0_vacuum.yaml",
        "sha256": "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c",
        "role": "reference 2-edit repair candidate (worker-008), rev12 base",
    },
    "c0_rev12_archive": {
        "path": "artifacts/worker-066/f2b_repair_prereg/pinned/c0_live__af_scc_c0_vacuum.yaml",
        "sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
        "role": "superseded rev12 C0 bytes, for carried-over-clause proof",
    },
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    pinned = OUT / "pinned"
    pinned.mkdir(exist_ok=True)
    measured, failed = {}, []
    for key, spec in PINS.items():
        src = ROOT / spec["path"]
        if not src.exists():
            failed.append({"key": key, "path": spec["path"], "error": "absent"})
            continue
        digest = sha256_file(src)
        rec = {
            "path": spec["path"],
            "expected_sha256": spec["sha256"],
            "measured_sha256": digest,
            "match": digest == spec["sha256"],
            "bytes": src.stat().st_size,
            "mtime": datetime.fromtimestamp(src.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "role": spec["role"],
        }
        dst = pinned / f"{key}__{src.name}"
        shutil.copyfile(src, dst)
        rec["pinned_copy"] = str(dst.relative_to(ROOT))
        rec["pinned_copy_sha256"] = sha256_file(dst)
        measured[key] = rec
        if not rec["match"]:
            failed.append({"key": key, "path": spec["path"], "expected": spec["sha256"], "measured": digest})

    doc = {
        "task_id": "W066-F2B-REV29-CONTAINMENT-01",
        "actor": "worker-066",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "pin_count": len(PINS),
        "all_match": not failed and len(measured) == len(PINS),
        "failures": failed,
        "pins": measured,
    }
    (OUT / "evidence").mkdir(exist_ok=True)
    (OUT / "evidence" / "pins.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"all_match": doc["all_match"], "failures": failed, "pins": len(measured)}))
    return 0 if doc["all_match"] else 2


if __name__ == "__main__":
    sys.exit(main())
