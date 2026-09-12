#!/usr/bin/env python3
"""Hash every file of the W092 F2a review and pin the reviewed target. Deterministic."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

files = ["verify_f2a.py", "make_verdict.py", "report.json", "controls.json",
         "acceptance_run.log", "README.md"]
manifest = {
    "task_id": "W092-F2A-CLASSBIND-REVIEW-01",
    "reviewer": "worker-092",
    "created_at": datetime.now(TZ).isoformat(timespec="seconds"),
    "reviewed_target": {
        "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "gate": "G-FORM",
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": sha(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "mirror_sha256": sha(ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
        "frozen_revision": json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())["revision"],
    },
    "files": {f: {"sha256": sha(HERE / f), "bytes": (HERE / f).stat().st_size} for f in files},
    "review_verdict_file": {
        "path": "reviews/F2a-review-rev27-c.json",
        "sha256": sha(ROOT / "reviews/F2a-review-rev27-c.json"),
    },
    "verdict": json.loads((ROOT / "reviews/F2a-review-rev27-c.json").read_text())["verdict"],
    "score": json.loads((ROOT / "reviews/F2a-review-rev27-c.json").read_text())["score"],
    "hard_failures": [h["id"] for h in json.loads(
        (ROOT / "reviews/F2a-review-rev27-c.json").read_text())["hard_failures"]],
    "read_only_on_canonical_paths": True,
}
out = HERE / "manifest.json"
out.write_text(json.dumps(manifest, indent=1, sort_keys=True))
print("wrote", out)
print("manifest sha256", sha(out))
