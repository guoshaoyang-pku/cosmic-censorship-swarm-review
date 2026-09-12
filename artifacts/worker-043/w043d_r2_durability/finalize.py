#!/usr/bin/env python3
"""W043D step 3 - build MANIFEST.json and the worker checkpoint.

Run after durability_test.py.  Writes:
  MANIFEST.json                                  (task dir)
  runtime/state/w043d_checkpoint.json            (controller-visible checkpoint)
  runtime/state/w043d_checkpoints.jsonl          (append-only trail)

Reads only task-dir files + pins the canonical inputs read-only.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = dt.timezone(dt.timedelta(hours=8))

TASK_ID = "W043D-R2-DURABILITY-01"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_IDS = ["F0", "F1", "F2a", "F2b"]
F2A = "schemas/af_scc_c2_vacuum.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
TOOL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
CHECKER = "artifacts/worker-043/f2a_rev12_verdict/check_f2a_rev12.py"

DELIVERABLES = [
    "README.md",
    "report.json",
    "acceptance.json",
    "durability.patch",
    "patched_check_taxonomy_consistency.py",
    "reconstruct_declared_evidence.py",
    "durability_test.py",
    "finalize.py",
    "emit_events.py",
    "raw/reconstruction.json",
    "raw/evidence_restored_675a99d0.json",
    "raw/instrument_selftest.json",
    "raw/acceptance.json",
    "raw/durability_report.json",
    "raw/reconstruct.stdout",
    "raw/reconstruct.stderr",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel_entry(rel: str) -> dict:
    p = HERE / rel
    return {"sha256": sha(p), "bytes": p.stat().st_size} if p.is_file() else {"missing": True}


def main() -> int:
    now = dt.datetime.now(CST).replace(microsecond=0).isoformat()
    report = json.loads((HERE / "report.json").read_text())

    deliverables = {}
    for rel in DELIVERABLES:
        e = rel_entry(rel)
        if "missing" not in e:
            deliverables[rel] = e

    pins = {rel: {"sha256": sha(ROOT / rel), "bytes": (ROOT / rel).stat().st_size}
            for rel in (F1, F2A, F2B, FROZEN, CONS, TOOL, CHECKER,
                        "research_map/formulation_taxonomy.yaml",
                        "artifacts/formulation/formulation_taxonomy.yaml")}

    manifest = {
        "task_id": TASK_ID,
        "worker": "worker-043",
        "generated_at": now,
        "gate": "G-FORM",
        "class_ids": CLASS_IDS,
        "node_ids": NODE_IDS,
        "verdict": report["verdict"],
        "deliverables": deliverables,
        "pinned_inputs": pins,
        "declared_evidence_sha256": report["declared_sha256"],
        "restored_evidence_sha256": sha(HERE / "raw/evidence_restored_675a99d0.json"),
        "repair": "R2: restore declared bytes + FROZEN rev29 evidence-pin-only + durability.patch",
        "next_falsifier": report["next_falsifier"],
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    manifest_sha = sha(HERE / "MANIFEST.json")

    checkpoint = {
        "worker": "worker-043",
        "task_id": TASK_ID,
        "checkpoint_at": now,
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": CLASS_IDS,
        "node_id": "F2a",
        "node_ids": NODE_IDS,
        "gate": "G-FORM",
        "reviewed_revision": 12,
        "reviewed_sha256": pins[F2A]["sha256"],
        "sibling_sha256": {F1: pins[F1]["sha256"], F2B: pins[F2B]["sha256"]},
        "frozen_revision_reviewed": 28,
        "proposed_frozen_revision": 29,
        "artifact": "artifacts/worker-043/w043d_r2_durability/report.json",
        "artifact_sha256": deliverables["report.json"]["sha256"],
        "acceptance_sha256": deliverables["acceptance.json"]["sha256"],
        "manifest": "artifacts/worker-043/w043d_r2_durability/MANIFEST.json",
        "manifest_sha256": manifest_sha,
        "probe": {"path": "artifacts/worker-043/w043d_r2_durability/durability_test.py",
                  "sha256": deliverables["durability_test.py"]["sha256"]},
        "evidence_dir": "artifacts/worker-043/w043d_r2_durability/raw/",
        "verdict": "accept_for_repair_R2",
        "score_0_5": 4.0,
        "counts_as_full_schema_verdict": False,
        "canonical_writes": [],
        "next_falsifier": report["next_falsifier"],
    }
    state = ROOT / "runtime/state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "w043d_checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
    with (state / "w043d_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps(checkpoint) + "\n")
    print(json.dumps({"manifest_sha256": manifest_sha,
                      "checkpoint": str(state / "w043d_checkpoint.json"),
                      "verdict": manifest["verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
