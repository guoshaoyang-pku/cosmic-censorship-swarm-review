#!/usr/bin/env python3
"""Finalize W026-CF31-DIVERGENCE-ATTRIBUTION-01: MANIFEST.json, CHECKPOINT.json, SHA256SUMS.

Reads report.json (produced by attribute.py) and writes the delivery metadata. Does not touch
any canonical path; writes only inside this artifact directory plus one worker-local checkpoint
under runtime/state/ following the worker-026 precedent.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
TASK = "W026-CF31-DIVERGENCE-ATTRIBUTION-01"
DELIVERABLES = ["attribute.py", "finalize.py", "emit_events.py", "report.json",
                "corpus_manifest.json", "lattice.json", "mutation_census.json",
                "snapshot_replay.json", "controls.json", "reanchor.json", "REPORT.md",
                "run_stdout.txt"]


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def iso_now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def main() -> int:
    rep = json.loads((HERE / "report.json").read_text())
    ctl = json.loads((HERE / "controls.json").read_text())
    att = rep["attribution"] if "attribution" in rep else rep.get("attribution", {})
    files = {name: {"sha256": sha256(HERE / name), "bytes": (HERE / name).stat().st_size}
             for name in DELIVERABLES}

    manifest = {
        "task_id": TASK,
        "actor": "worker-026",
        "gate": rep["gate"], "node_id": rep["node_id"], "class_id": rep["class_id"],
        "class_ids": rep["class_ids"],
        "verdict": rep["verdict"],
        "generated_at": iso_now(),
        "authority": rep["authority"],
        "non_duplication": rep["non_duplication"],
        "pins": rep["pins"],
        "corpus": rep["corpus"],
        "controls": {"passed": ctl["passed"], "total": ctl["total"]},
        "replay": [{"label": r["label"], "at": r.get("at"), "published": r.get("published"),
                    "replayed": r.get("replayed"), "match": r.get("match")}
                   for r in rep["scan_replay"]],
        "findings": [{"id": f["id"], "severity": f["severity"]} for f in rep["findings"]],
        "instrument_move_during_task": json.loads((HERE / "reanchor.json").read_text()),
        "falsifier": rep["falsifier"],
        "non_claims": rep["non_claims"],
        "deliverables": files,
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))

    checkpoint = {
        "task_id": TASK,
        "actor": "worker-026",
        "status": "worker_level_complete_bounded_exit",
        "created_at": iso_now(),
        "gate": rep["gate"], "node_id": rep["node_id"], "class_id": rep["class_id"],
        "verdict": rep["verdict"],
        "controls": f"{ctl['passed']}/{ctl['total']}",
        "canonical_tree_untouched": True,
        "writes": [str((HERE / n).relative_to(ROOT)) for n in DELIVERABLES] +
                  ["artifacts/worker-026/cf31_divergence_attribution/MANIFEST.json",
                   "artifacts/worker-026/cf31_divergence_attribution/CHECKPOINT.json",
                   "artifacts/worker-026/cf31_divergence_attribution/SHA256SUMS",
                   "runtime/state/w026_cf31_divergence_checkpoint.json"],
        "key_evidence": {
            "pre_rewrite_accept_copy": "artifacts/worker-066/f2b_accept_disposition/pinned/reviews__F2b-review-worker-072-rev29.json",
            "live_file": "reviews/F2b-review-worker-072-rev29.json",
            "replay_load_bearing_instants_match": rep["replay_summary"]["load_bearing_instants_match"],
            "method_c_target_blindspot_control": "C14",
        },
        "next_falsifier": rep["falsifier"],
        "note": ("Worker events cannot set status=done, validation_status=passed or a gate verdict. "
                 "This checkpoint is worker-local only; promotion is the controller's/lead's."),
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1))
    cp_path = ROOT / "runtime" / "state" / "w026_cf31_divergence_checkpoint.json"
    cp_path.write_text(json.dumps(checkpoint, indent=1))

    names = DELIVERABLES + ["MANIFEST.json", "CHECKPOINT.json"]
    lines = [f"{sha256(HERE / n)}  {n}" for n in names]
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(json.dumps({"manifest": str((HERE / 'MANIFEST.json').relative_to(ROOT)),
                      "checkpoint": str(cp_path.relative_to(ROOT)),
                      "files": len(names), "controls": f"{ctl['passed']}/{ctl['total']}",
                      "verdict": rep["verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
