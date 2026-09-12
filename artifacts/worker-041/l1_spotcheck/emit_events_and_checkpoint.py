#!/usr/bin/env python3
"""Emit worker-041 upward events and a checkpoint for the L1 spot check.

Writes (append for outbox/checkpoint log, replace for the latest checkpoint):
  comms/outbox/worker-041.jsonl
  runtime/state/w041_checkpoint_1.json
  runtime/state/w041_checkpoints.jsonl

Worker authority note: these events claim bounded-execution completion only.
They set no node status, no validation_status=passed, and no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-041.jsonl"
CKPT = ROOT / "runtime" / "state" / "w041_checkpoint_1.json"
CKPT_LOG = ROOT / "runtime" / "state" / "w041_checkpoints.jsonl"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")

ART = HERE / "spotcheck-l1-041.json"
RAW = HERE / "raw"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    doc = json.loads(ART.read_text(encoding="utf-8"))
    art_sha = sha(ART)
    assert art_sha == open(HERE / "spotcheck-l1-041.json.sha256").read().split()[0], \
        "artifact sha256 sidecar mismatch"
    assert sha(LEDGER) == LEDGER_SHA, "ledger drifted before event emission"
    raw_hashes = {p.name: sha(p) for p in sorted(RAW.glob("*")) if p.is_file()}
    assert len(raw_hashes) == len(doc["results"]), "raw body count != checked rows"
    art_ts = doc["created_at"][:19].replace("-", "").replace(":", "")  # YYYYMMDDTHHMMSS

    counts = doc["summary"]["counts"]
    findings = doc["findings"]
    ev_claim = {
        "event_id": f"w041-l1-{art_ts}-claim",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.4,
        "task_id": "W041-L1-SPOTCHECK-05",
        "completion_scope": "bounded worker lifecycle only; not a node done or gate verdict",
        "summary": (
            "No assignment card exists in comms/inbox for worker-041. Took ONE bounded "
            "class-bound task: W041-L1-SPOTCHECK-05 = independent live re-fetch spot check #5 "
            "of ledger/citation_audit.csv at frozen sha256 315c19145065, sampling data rows "
            "21-40 (stride 22,26,30,34,38 + targeted 29,40; excluded 25,33), declared before "
            "any fetch and disjoint from binding checks #3 (rows 41-95) and #4 "
            "(1,4,9,16,17,25,33,96,97). Result: 7 rows, 6 MATCH, 1 PARTIAL (SRC-022 journal "
            "issue year 2018 vs Crossref online 2017), 0 identity MISMATCH, 0 FETCH_FAILED. "
            "Locator-quality finding: 6/7 rows carry registry search queries in exact_locator, "
            "not exact locators. Ledger sha stable across the run."
        ),
        "evidence_refs": [
            f"ledger/citation_audit.csv#{LEDGER_SHA[:12]}",
            f"artifacts/worker-041/l1_spotcheck/spotcheck-l1-041.json#{art_sha[:12]}",
            "runtime/state/controller_verification/lifecycle_20260912-001727.json",
        ],
        "next_falsifier": doc["next_falsifier"],
        "artifact": "artifacts/worker-041/l1_spotcheck/spotcheck-l1-041.json",
    }
    ev_artifact = {
        "event_id": f"w041-l1-{art_ts}-artifact",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "L1",
        "gate": "G-LIT",
        "artifact_type": "l1_refetch_spotcheck",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "path": "artifacts/worker-041/l1_spotcheck/spotcheck-l1-041.json",
        "sha256": art_sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": (
            f"Independent re-fetch spot check #5: {counts.get('MATCH',0)} MATCH, "
            f"{counts.get('PARTIAL',0)} PARTIAL, {counts.get('MISMATCH',0)} MISMATCH, "
            f"{counts.get('FETCH_FAILED',0)} FETCH_FAILED over 7 rows; raw bodies retained "
            "under artifacts/worker-041/l1_spotcheck/raw/ with per-file sha256. No gate "
            "verdict or node status is claimed."
        ),
        "evidence_refs": [
            f"artifacts/worker-041/l1_spotcheck/spotcheck-l1-041.json#{art_sha[:12]}",
            f"ledger/citation_audit.csv#{LEDGER_SHA[:12]}",
        ] + [f"artifacts/worker-041/l1_spotcheck/raw/{k}#{v[:12]}"
             for k, v in raw_hashes.items()],
        "falsifier": doc["falsifier"],
        "to": ["astra", "astra-lead-literature", "astra-lead-audit"],
    }
    ev_review = {
        "event_id": f"w041-l1-{art_ts}-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "target_id": "ledger/citation_audit.csv",
        "reviewer": "worker-041",
        "verdict": "revise",
        "score": 4,
        "reviewed_sha256": LEDGER_SHA,
        "scope": "independent_re_fetch_spot_check_7_of_97_rows",
        "counts_as_full_ledger_verdict": False,
        "hard_failures": doc["hard_failures"],
        "findings": (
            ["0 identity MISMATCH / 0 FETCH_FAILED across the 7 sampled rows; sampled rows "
             "resolve to the cited works at the primary registry.",
             "SRC-022: title exact and first author match; ledger year 2018 is the JAMS 31(1) "
             "issue year while Crossref records online publication 2017-09-27 (no print date "
             "deposited) - year-convention PARTIAL, not an identity failure.",
             "LOCATOR QUALITY (actionable): 6 of 7 sampled rows carry registry search queries in "
             "exact_locator rather than exact locators; this matches the same class of finding "
             "in spot check #4 and is the concrete revise item.",
             "Class mapping was checked topically only: 3 rows topically consistent with their "
             "mapped class, 4 rows carry no class claim; this is not a class-binding verdict."]
        ),
        "evidence_refs": [
            f"artifacts/worker-041/l1_spotcheck/spotcheck-l1-041.json#{art_sha[:12]}",
            f"ledger/citation_audit.csv#{LEDGER_SHA[:12]}",
        ],
        "next_falsifier": doc["next_falsifier"],
    }
    events = [ev_claim, ev_artifact, ev_review]
    with OUTBOX.open("a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    ckpt = {
        "checkpoint": 1,
        "at": NOW,
        "worker": "worker-041",
        "lifecycle": "bounded execution worker; exited after one class-bound task",
        "assignment_taken": {
            "kind": "class-bound task taken from the open G-LIT queue; no card in "
                    "comms/inbox/worker-041.jsonl",
            "task": "W041-L1-SPOTCHECK-05 independent live re-fetch spot check #5, "
                    "ledger/citation_audit.csv data rows 21-40",
            "node_id": "L1",
            "gate": "G-LIT",
            "class_ids": CLASS_IDS,
            "why_not_duplicative": ("sample frozen before fetch and disjoint from binding checks "
                                    "#3 (rows 41-95) and #4 (1,4,9,16,17,25,33,96,97); "
                                    "concurrent peers picked other frames (noted, not claimed "
                                    "unique)"),
        },
        "hours_spent_estimate": 0.4,
        "artifacts": {
            "artifacts/worker-041/l1_spotcheck/spotcheck-l1-041.json": art_sha,
            "artifacts/worker-041/l1_spotcheck/run_spotcheck_041.py":
                sha(HERE / "run_spotcheck_041.py"),
            **{f"artifacts/worker-041/l1_spotcheck/raw/{k}": v for k, v in raw_hashes.items()},
        },
        "ledger_sha256_before": doc["inputs"]["ledger/citation_audit.csv"]["sha256_before"],
        "ledger_sha256_after": doc["inputs"]["ledger/citation_audit.csv"]["sha256_after"],
        "verdict": doc["summary"]["overall"],
        "counts": counts,
        "hard_failures": len(doc["hard_failures"]),
        "events_emitted": [e["event_id"] for e in events],
        "next_falsifier": doc["next_falsifier"],
        "authority_note": ("worker event: cannot set status=done, validation_status=passed, or "
                           "any gate verdict; controller/leads own those with artifact+review "
                           "evidence"),
    }
    CKPT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with CKPT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ckpt, ensure_ascii=False) + "\n")
    print(json.dumps({"outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint": str(CKPT.relative_to(ROOT)),
                      "artifact_sha256": art_sha, "events": [e["event_id"] for e in events],
                      "raw_files": len(raw_hashes)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
