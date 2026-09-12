#!/usr/bin/env python3
"""W084-C2C0-ESCAPE-MECHANISM-01 finalizer: artifact hash table + worker checkpoint.

Writes:
  artifacts/heldout/heldout-10-mechanism/checkpoint.json
  runtime/state/w084_escape_mechanism_checkpoint.json   (copy)
Nothing else is written; canonical paths stay read-only.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
CST = timezone(timedelta(hours=8))

ARTIFACTS = [
    "PREREGISTRATION.json",
    "PREREGISTRATION_AMENDMENT_1.json",
    "analyze_escape_mechanism.py",
    "raw/differential.json",
    "diffs.json",
    "adjudication.json",
    "report.json",
    "findings.json",
    "REPORT.md",
    "v1/report.json",
    "v1/adjudication.json",
    "v1/differential.json",
]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    hashes = {}
    for rel in ARTIFACTS:
        p = DIR / rel
        hashes[f"artifacts/heldout/heldout-10-mechanism/{rel}"] = sha(p) if p.exists() else None
    report = json.loads((DIR / "report.json").read_text())
    agg = report["aggregates"]

    ckpt = {
        "task_id": report["task_id"],
        "corpus_id": report["corpus_id"],
        "worker": "worker-084",
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": report["class_ids"],
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "status": "complete_at_worker_level",
        "valid": report["valid"],
        "mechanism_headline": report["mechanism_headline"],
        "headline_numbers": {
            "informative_arms": {
                "mutants": agg["informative_arms"]["mutants"],
                "caught": agg["informative_arms"]["caught"],
                "escape_silent": agg["informative_arms"]["escape_silent"],
                "escape_observed": agg["informative_arms"]["escape_observed"],
                "union_escape": agg["informative_arms"]["union_escape"],
            },
            "strict_contract_only": {
                "mutants": agg["informative_contract_only"]["mutants"],
                "escape_silent": agg["informative_contract_only"]["escape_silent"],
                "union_escape": agg["informative_contract_only"]["union_escape"],
            },
            "meta_only": {
                "mutants": agg["informative_meta_only"]["mutants"],
                "escape_silent": agg["informative_meta_only"]["escape_silent"],
                "union_escape": agg["informative_meta_only"]["union_escape"],
            },
        },
        "controls": {k: v.get("ok") for k, v in report["controls"].items()},
        "stage_tools": report["stages"],
        "preregistration": report["preregistration"],
        "preregistration_amendments": report["preregistration_amendments"],
        "artifact_hashes": hashes,
        "pins_at_checkpoint": report["pins"],
        "falsifier": report["falsifier"],
        "next_falsifier": [
            "A stage revision that makes stage B accept the untouched WCC canonical (R03 repair) removes the strict-H5 blocker; the preserved corpus can then be re-run unchanged and this mechanism audit re-run as a sensitivity check.",
            "A stage revision whose reported rule surface responds to any of the 20 CONTRACT mutants falsifies SILENT-BLINDNESS for that stage.",
            "A re-run of analyze_escape_mechanism.py --verify that reports any mismatch falsifies reproducibility.",
        ],
        "do_not_claim": report["do_not_claim"],
        "independence": report["independence"],
        "reproduce": "python3 artifacts/heldout/heldout-10-mechanism/analyze_escape_mechanism.py --verify",
    }

    out = DIR / "checkpoint.json"
    out.write_text(json.dumps(ckpt, indent=2) + "\n")
    runtime = ROOT / "runtime" / "state" / "w084_escape_mechanism_checkpoint.json"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text(json.dumps(ckpt, indent=2) + "\n")
    ckpt["checkpoint_sha256"] = sha(out)
    print(json.dumps({"checkpoint": str(out.relative_to(ROOT)),
                      "checkpoint_sha256": ckpt["checkpoint_sha256"],
                      "runtime_copy": str(runtime.relative_to(ROOT)),
                      "artifact_hashes": hashes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
