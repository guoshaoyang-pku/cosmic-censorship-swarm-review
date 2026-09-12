#!/usr/bin/env python3
"""W062-GFORM-R03V2-SCOPE-REPLICATION-01 -- emit valid JSON events + checkpoint, then exit.

Appends to comms/outbox/worker-062.jsonl (own outbox only) and writes
runtime/state/w062_r03v2_scope_replication_checkpoint.json plus the artifact CHECKPOINT.json.
Idempotent: existing event_ids in the outbox are skipped. Worker events set no status=done,
no validation_status=passed and no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-062.jsonl"
STATE = ROOT / "runtime/state/w062_r03v2_scope_replication_checkpoint.json"
CST = timezone(timedelta(hours=8))
LABEL = "w062-r03v2rep-20260912T0124"


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> None:
    report = json.loads((HERE / "report.json").read_text())
    review = json.loads((HERE / "REVIEW.json").read_text())
    prereg = json.loads((HERE / "PREREGISTRATION.json").read_text())
    manifest = json.loads((HERE / "fixture_manifest.json").read_text())
    ts = now()

    arts = {}
    for name, atype in [
        ("PREREGISTRATION.json", "preregistration"),
        ("fixture_manifest.json", "scope_corpus_manifest"),
        ("run_replication.py", "deterministic_harness"),
        ("raw_verdicts.json", "raw_measurement"),
        ("report.json", "replication_report"),
        ("REVIEW.json", "independent_review"),
    ]:
        p = HERE / name
        if not p.is_file():
            raise SystemExit(f"FAIL: artifact missing: {p}")
        arts[name] = {"path": str(p.relative_to(ROOT)), "sha256": sha256_path(p),
                      "artifact_type": atype}

    evidence = [
        f"{arts['report.json']['path']}#{arts['report.json']['sha256'][:12]}",
        f"{arts['raw_verdicts.json']['path']}#{arts['raw_verdicts.json']['sha256'][:12]}",
        f"{arts['PREREGISTRATION.json']['path']}#{arts['PREREGISTRATION.json']['sha256'][:12]}",
        f"{arts['fixture_manifest.json']['path']}#{arts['fixture_manifest.json']['sha256'][:12]}",
        "artifacts/worker-06/r03scope/report.json#e81f7818d026",
        "artifacts/worker-06/r03scope/raw_verdicts.json#33ab1e03e690",
        "artifacts/worker-06/r03scope/fixture_manifest.json#40a457905eee",
        "artifacts/worker-06/r03v2/audit_r03v2.py#e41a4b23a840",
        "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ]

    events = []
    for name, a in arts.items():
        slug = name.replace(".json", "").replace(".py", "").replace("_", "-").lower()
        events.append({
            "event_type": "artifact", "event_id": f"{LABEL}-artifact-{slug}",
            "created_at": ts, "actor": "worker-062", "node_id": "A1",
            "gate": "G-FORM/G-CLASSBIND",
            "class_ids": report["class_ids"],
            "artifact_type": a["artifact_type"],
            "path": a["path"], "sha256": a["sha256"],
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": report["cells"]["cand_r03v2::neg_free_in_restriction.yaml"] and (
                "Re-run any reported cell at the same pins and find a different verdict, or "
                "show a pinned input moved between the pre/post measurements in report.json."),
            "summary": f"W062 R03-v2 scope replication artifact: {name}",
        })

    claim = {
        "event_type": "claim", "event_id": f"{LABEL}-claim",
        "created_at": ts, "actor": "worker-062", "node_id": "A1",
        "gate": "G-FORM/G-CLASSBIND", "class_id": "AF-WCC-VAC-GEN",
        "class_ids": report["class_ids"],
        "conclusion_type": "formal_model",
        "statement": review["claim_statement"],
        "assumptions": review["assumptions"],
        "falsifier": review["falsifier"],
        "evidence_refs": evidence,
        "artifact_refs": [f"{arts['report.json']['path']}#{arts['report.json']['sha256'][:12]}",
                          f"{arts['PREREGISTRATION.json']['path']}#{arts['PREREGISTRATION.json']['sha256'][:12]}"],
        "not_claimed": ["no gate verdict", "no node completion", "no theorem", "no adoption recommendation"],
    }
    events.append(claim)

    events.append({
        "event_type": "review", "event_id": f"{LABEL}-review",
        "created_at": ts, "actor": "worker-062", "reviewer": "worker-062",
        "reviewer_role": "bounded execution worker; not an author of W006-R03-SCOPE-01",
        "target_id": review["target_id"],
        "verdict": review["verdict"], "score": review["score"],
        "hard_failures": review["hard_failures"], "findings": review["findings"],
        "reviewed_sha256": review["reviewed_sha256"],
        "counts_as_full_schema_verdict": False,
        "evidence_refs": evidence,
    })

    events.append({
        "event_type": "status", "event_id": f"{LABEL}-status",
        "created_at": ts, "actor": "worker-062", "node_id": "A1",
        "gate": "G-FORM/G-CLASSBIND", "status": "active", "hours": review.get("hours", 0.9),
        "summary": review["status_summary"],
        "class_ids": report["class_ids"],
        "evidence_refs": evidence,
        "artifact_refs": [f"{arts['report.json']['path']}#{arts['report.json']['sha256'][:12]}"],
        "next_falsifier": review["next_falsifier"],
        "not_claimed": "no gate verdict, no node completion, no theorem, no adoption recommendation",
    })

    if review["verdict"] == "inconclusive":
        events.append({
            "event_type": "blocker", "event_id": f"{LABEL}-blocker",
            "created_at": ts, "actor": "worker-062", "node_id": "A1",
            "description": review["findings"][:800],
            "needed_to_unblock": "owner/controller adjudication of the inconclusive cells",
            "evidence_refs": evidence,
        })

    # idempotent append
    seen = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    appended = 0
    with OUTBOX.open("a") as f:
        for e in events:
            if e["event_id"] in seen:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended += 1

    checkpoint = {
        "checkpoint_id": f"w062-r03v2rep-{ts.replace(':', '').replace('-', '')}",
        "task_id": report["task_id"], "worker": "worker-062",
        "created_at": ts, "node_id": "A1",
        "gate": "G-FORM/G-CLASSBIND", "class_ids": report["class_ids"],
        "outcome_under_preregistered_rule": report["outcome_under_preregistered_rule"],
        "part_a_reproduce": report["part_a_reproduce_w006"],
        "part_b_scored": report["part_b_heldout"]["per_tool_scored"],
        "prediction_deviations": len(report["part_b_heldout"]["prediction_deviations"]),
        "pin_drift": report["pin_drift"],
        "artifacts": {k: v["sha256"] for k, v in arts.items()},
        "event_ids": [e["event_id"] for e in events],
        "events_appended_this_run": appended,
        "next_falsifier": review["next_falsifier"],
        "status": "worker-task-complete-at-worker-level; no gate/node status set",
    }
    HERE.joinpath("CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    STATE.write_text(json.dumps(checkpoint, indent=1) + "\n")
    print(json.dumps({"appended_events": appended, "checkpoint": str(STATE),
                      "artifacts": {k: v["sha256"][:12] for k, v in arts.items()}}, indent=1))


if __name__ == "__main__":
    main()
