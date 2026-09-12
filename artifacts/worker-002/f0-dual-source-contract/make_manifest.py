#!/usr/bin/env python3
"""Generate manifest.json and CHECKPOINT.json for W002-F0-DUALSOURCE-01.

Reads report.json / controls.json produced by check_dual_source_contract.py and
hash-pins every input and output.  Order: pin stable outputs -> write
CHECKPOINT.json -> pin it -> write manifest.json.  Neither file hashes itself.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def pin(path: Path) -> dict:
    return {"path": str(path.resolve().relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path)}


def main() -> None:
    report = json.loads((HERE / "report.json").read_text())
    controls = json.loads((HERE / "controls.json").read_text())
    now = datetime.now(CST).isoformat(timespec="seconds")

    input_paths = [
        ROOT / "research_map" / "formulation_taxonomy.yaml",
        ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml",
        ROOT / "artifacts" / "formulation" / "VOCAB_ALIASES.json",
        ROOT / "artifacts" / "formulation" / "FROZEN.json",
        ROOT / "schemas" / "af_wcc_vacuum.yaml",
        ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
        ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
    ]
    stable_outputs = [
        HERE / "check_dual_source_contract.py",
        HERE / "make_manifest.py",
        HERE / "emit_events.py",
        HERE / "report.json",
        HERE / "controls.json",
        HERE / "SUMMARY.md",
        HERE / "snapshots" / "SHA256SUMS",
    ] + sorted((HERE / "snapshots").glob("F0-*.yaml"))
    stable_pins = {pin(p)["path"]: pin(p) for p in stable_outputs if p.exists()}

    checkpoint = {
        "schema_version": "0.1",
        "checkpoint_id": "W002-F0-DUALSOURCE-01-CKPT",
        "record_id": report["record_id"],
        "actor": "worker-002",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": report["class_ids"],
        "created_at": now,
        "measured_at": report["created_at"],
        "inputs": {
            "canonical": {"path": report["inputs"]["canonical"]["path"],
                          "revision": report["inputs"]["canonical"]["revision"],
                          "sha256": report["inputs"]["canonical"]["sha256_scan_pin"]},
            "supplement": {"path": report["inputs"]["supplement"]["path"],
                           "revision": report["inputs"]["supplement"]["revision"],
                           "sha256": report["inputs"]["supplement"]["sha256_scan_pin"]},
        },
        "outputs": {k: v["sha256"] for k, v in stable_pins.items()},
        "controls": {"total": controls["total"], "passed": controls["passed"],
                     "failed": controls["failed"]},
        "headline_counts": report["headline"]["counts"],
        "residual": report["headline"]["residual"],
        "next_falsifier": report["next_falsifier"],
        "authority_note": report["authority_note"],
        "checkpoint_kind": "bounded-worker-task",
        "state": "complete_pending_controller_ingest",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    all_pins = dict(stable_pins)
    all_pins[pin(HERE / "CHECKPOINT.json")["path"]] = pin(HERE / "CHECKPOINT.json")

    manifest = {
        "schema_version": "0.1",
        "record_id": report["record_id"],
        "task_id": report["task_id"],
        "actor": "worker-002",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": report["class_ids"],
        "created_at": now,
        "measured_at": report["created_at"],
        "question": report["question"],
        "method": report["method"],
        "canonical_scan_pin": report["inputs"]["canonical"]["sha256_scan_pin"],
        "supplement_scan_pin": report["inputs"]["supplement"]["sha256_scan_pin"],
        "live_stable_during_run": report["inputs"]["canonical"]["stable_during_run"],
        "inputs": {pin(p)["path"]: pin(p) for p in input_paths},
        "outputs": all_pins,
        "outputs_note": ("manifest.json does not hash itself; every other input and output, "
                         "including CHECKPOINT.json, is hash-pinned here"),
        "controls": {"total": controls["total"], "passed": controls["passed"],
                     "failed": controls["failed"]},
        "headline_counts": report["headline"]["counts"],
        "residual": report["headline"]["residual"],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "authority_note": report["authority_note"],
        "reproduction": report["reproduction"],
        "determinism_digest": report["determinism_digest"],
        "superseded_context": (
            "Measured the F0 surface after the formulation lead's rev5 (canonical) / rev9 "
            "(supplement) publication at 00:31-00:32; the earlier revisions 276009f4f63d / "
            "c8e979a1eb48 carried the scalar-class set-based D1 residue and duplicate "
            "revised_at keys, both absent at these pins."),
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"manifest": sha256(HERE / "manifest.json"),
                      "checkpoint": sha256(HERE / "CHECKPOINT.json"),
                      "outputs_pinned": len(all_pins)}, indent=1))


if __name__ == "__main__":
    main()
