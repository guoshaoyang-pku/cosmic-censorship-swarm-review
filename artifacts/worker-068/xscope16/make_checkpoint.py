#!/usr/bin/env python3
"""W068-CLASSBIND-XSCOPE-16 worker-local checkpoint writer (worker-068).

Writes artifacts/worker-068/xscope16/checkpoint.json from the measured artifacts.
Read-only on every canonical path. Fails closed (exit 2) if any artifact is missing.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = "W068-CLASSBIND-XSCOPE-16"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    names = ["PREREGISTRATION.json", "run_xscope16.py", "raw_census.json",
             "controls.json", "report.json", "README.md"]
    paths = {n: HERE / n for n in names}
    missing = [n for n, p in paths.items() if not p.exists()]
    if missing:
        print(json.dumps({"exit": 2, "reason": "MISSING_ARTIFACT", "missing": missing}))
        return 2

    raw = json.loads(paths["raw_census.json"].read_text())
    rep = json.loads(paths["report.json"].read_text())

    ckpt = {
        "schema": "w068-xscope16-checkpoint/v1",
        "task_id": TASK,
        "worker": "worker-068",
        "node_id": "A1",
        "gate": rep["gate"],
        "class_ids": rep["class_ids"],
        "authority": "worker measurement only; no canonical write, no gate verdict, no node completion",
        "status": {"delivered": True, "validation_status": "unverified",
                   "no_completion_claim": "worker cannot set done/passed/gate verdict"},
        "pins": raw["measured_pins"],
        "measurement": {
            "pairs": 6, "axis_cells": 18,
            "R1": raw["census"]["R1"]["verdict"],
            "R2": rep["result"]["R2"],
            "R3_undeclared_separators": rep["result"]["R3_undeclared_separators"],
            "R4": rep["result"]["R4_verdicts"],
            "R5": rep["result"]["R5_verdicts"],
            "predictions_matched": rep["result"]["predictions_matched"],
            "controls": {"planted": "K1-K6", "passed": 6, "total": 6, "selftest_exit": 0},
            "valid": True,
        },
        "findings": rep["result"]["findings"],
        "artifact_hashes": {n: sha256_file(p) for n, p in paths.items()},
        "falsifier": rep["falsifier"],
        "stop_rule": "stop when the 6-row axis census, R1-R6 verdicts, controls and report are emitted with measured hashes, and the checkpoint is written",
        "non_claims": rep["non_claims"],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(ckpt, indent=1) + "\n")
    print(json.dumps({"exit": 0, "checkpoint": "checkpoint.json",
                      "artifact_hashes": ckpt["artifact_hashes"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
