#!/usr/bin/env python3
"""Freeze the exact bytes this audit classified. Review files are known to move (worker-048
HF-W48-CR-1 measured accept->revise rewrites), so the accept corpus must be pinned."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PIN = OUT / "pinned"
PIN.mkdir(exist_ok=True)

INPUTS = [
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/rule_spec.json",
    # the four accepts binding b2ab6acb2bbe at audit time
    "reviews/F2b-rev13-full-090.json",
    "reviews/F2b-review-rev13-052.json",
    "reviews/F2b-review-rev13-worker-071.json",
    "reviews/F2b-review-worker-072-rev29.json",
    # one representative non-accept carrier source per carrier
    "reviews/F2b-review-rev29-053.json",
    "reviews/F2b-review-worker-018-rev13.json",
    "reviews/F2b-containment-normativity-worker-066.json",
    # the two staged repair candidates used only as controls
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


sums = {}
for rel in INPUTS:
    src = ROOT / rel
    if not src.is_file():
        sums[rel] = None
        continue
    dst = PIN / rel.replace("/", "__")
    shutil.copy2(src, dst)
    sums[rel] = {"sha256": sha(dst), "pinned_copy": str(dst.relative_to(ROOT))}

(OUT / "evidence" / "pinned_inputs.json").write_text(json.dumps(sums, indent=1, sort_keys=True))
(PIN / "SHA256SUMS").write_text(
    "".join(f"{v['sha256']}  {k}\n" for k, v in sorted(sums.items()) if v))
print(json.dumps({k: (v or {}).get("sha256", "MISSING")[:12] for k, v in sums.items()}, indent=1))
