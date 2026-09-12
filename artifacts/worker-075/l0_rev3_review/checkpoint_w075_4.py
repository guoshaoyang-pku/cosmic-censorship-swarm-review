#!/usr/bin/env python3
"""Write the W075-L0-REV3 checkpoint (numbered 4 for slot 075) and append it to the log."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
HERE = ROOT / "artifacts" / "worker-075" / "l0_rev3_review"
FILES = [
    HERE / "report.json",
    HERE / "run_l0rev3_review_075.py",
    HERE / "verify_l0rev3_review_075.py",
    HERE / "README.md",
    HERE / "emit_events_075.py",
    HERE / "checkpoint_w075_4.py",
    ROOT / "reviews" / "L0-review-075-rev3.json",
]
INPUTS = [ROOT / "ledger" / "theorems.jsonl", ROOT / "ledger" / "citation_audit.csv"]
EVENTS = [
    "w075-l0rev3-status",
    "w075-l0rev3-artifact-report",
    "w075-l0rev3-artifact-harness",
    "w075-l0rev3-artifact-verifier",
    "w075-l0rev3-artifact-readme",
    "w075-l0rev3-artifact-verdict-record",
    "w075-l0rev3-review",
    "w075-l0rev3-claim",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rep = json.loads((HERE / "report.json").read_text())
    ck = {
        "checkpoint": 4,
        "at": datetime.now(CST).isoformat(timespec="seconds"),
        "assignment": ("no assignment card for slot worker-075; bounded class-bound task "
                       "W075-L0-REV3-INDEP-VERDICT-01 taken from astra-lead-literature blocker BL-7 / "
                       "resource_request lit-l5-20260912-022"),
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": rep["class_ids"],
        "hours_spent_estimate": 0.5,
        "inputs": {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
                   for p in INPUTS},
        "artifacts": {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size}
                      for p in FILES},
        "status": {
            "delivered": True,
            "events_accepted": EVENTS,
            "events_rejected": 0,
            "events_validated_against_schema": len(EVENTS),
            "ingest_dry_run": "0 rejected; all 8 pending",
            "independent_verifier": {
                "path": "artifacts/worker-075/l0_rev3_review/verify_l0rev3_review_075.py",
                "sha256": sha(HERE / "verify_l0rev3_review_075.py"),
                "result": "PASS",
                "tamper_control": "3/3 mutations detected",
            },
            "measurement": {
                "rows": 62,
                "content_status": {"verified": 50, "provisional": 11, "rejected": 1},
                "review_status": {"not_independently_reviewed": 62},
                "rows_without_unresolved": 0,
                "cited_sources": 92,
                "audit_rows_resolved": "97/97",
                "multi_class_rows": 8,
                "multi_class_categories": {"relation_or_variant_mention": 6,
                                           "wcc_antecedent_status": 2},
                "theorem_rows": 30,
                "foreign_class_tokens": 0,
                "verdict": rep["verdict"]["verdict"],
                "score": rep["verdict"]["score"],
                "hard_failures": rep["verdict"]["hard_failures"],
                "open_objections": len(rep["verdict"]["open_objections"]),
            },
            "drift_at_checkpoint": {
                "drifted_inputs": [str(p.relative_to(ROOT)) for p in INPUTS
                                   if sha(p) != rep["inputs"][
                                       "ledger_sha" if p.name == "theorems.jsonl" else "audit_sha"]],
                "expected": {"ledger/theorems.jsonl": rep["inputs"]["ledger_sha"],
                             "ledger/citation_audit.csv": rep["inputs"]["audit_sha"]},
            },
            "authority_note": ("worker level only: no node completion, no validation_status=passed, "
                              "no gate verdict"),
        },
        "falsifier": rep["falsifier"],
        "next_falsifier": ("lead/controller: adjudicate the two rubric-scope objections (HF-01 "
                           "artifact_refs on ledger rows, HF-02 multi-class binding) and count this "
                           "verdict against L0 coverage only if it binds a1674f094979 at adjudication "
                           "time; re-hash the ledger before counting."),
    }
    out = ROOT / "runtime" / "state" / "w075_checkpoint_4.json"
    out.write_text(json.dumps(ck, indent=1, ensure_ascii=False))
    log = ROOT / "runtime" / "state" / "w075_checkpoints.jsonl"
    keep = []
    for line in log.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            if json.loads(line).get("checkpoint") == 4:
                continue
        except ValueError:
            pass
        keep.append(line)
    keep.append(json.dumps(ck, ensure_ascii=False))
    log.write_text("\n".join(keep) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
    print("drift:", ck["status"]["drift_at_checkpoint"]["drifted_inputs"] or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
