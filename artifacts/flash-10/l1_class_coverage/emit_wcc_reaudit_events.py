#!/usr/bin/env python3
"""Emit the W010-L1-REAUDIT-01 artifact + status events to the flash-10 outbox.

Validates every event against research_map/events.schema.json before writing; a validation
failure aborts without touching the outbox. Appends one JSON object per line.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-10.jsonl"
SCHEMA = json.loads((ROOT / "research_map" / "events.schema.json").read_text(encoding="utf-8"))

REPORT = HERE / "wcc_class_conformance_reaudit.json"
REAUDIT = HERE / "wcc_class_conformance_audit.9a8bd4c96800.json"
DRIVER = HERE / "wcc_reaudit_rev11.py"
AUDIT = HERE / "wcc_class_conformance_audit.py"

CST = timezone(timedelta(hours=8))
CLASS = "AF-WCC-VAC-GEN"
TASK_ID = "W010-L1-REAUDIT-01"
ASSIGNMENT_REF = "asg-2026-09-11-L1-deepseek-flash-10-19"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = datetime.now(CST).replace(microsecond=0).isoformat()
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    rep_h, re_h, drv_h, aud_h = sha256(REPORT), sha256(REAUDIT), sha256(DRIVER), sha256(AUDIT)
    summary = rep["rerun"]["summary"]

    ev_report = {
        "event_id": f"flash-10-artifact-wcc-reaudit-{stamp}",
        "event_type": "artifact",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "artifact_type": "json",
        "path": str(REPORT.relative_to(ROOT)),
        "sha256": rep_h,
        "bytes": REPORT.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "evidence_refs": rep["evidence_refs"] + [
            f"{DRIVER.relative_to(ROOT)}#{drv_h[:12]}",
        ],
        "inputs": rep["inputs"],
        "falsifier": rep["falsifier"],
        "summary": (
            f"W010-L1-REAUDIT-01: re-bound the AF-WCC-VAC-GEN class-conformance audit to current "
            f"canonical hashes. Schema drift rev10 {rep['drift_comparison']['pinned_revision_label']} "
            f"-> rev{rep['drift_comparison']['current_revision']} is machine-verified as "
            f"non-substantive (differing fields: {rep['drift_comparison']['differing_fields']}); the "
            f"re-run reads class_definition sha 9a8bd4c96800 and again finds "
            f"n_bound={summary['n_bound_entries']}, n_discharging={summary['n_discharging']}. New: at "
            f"ledger {rep['ledger_status_observation']['measured_ledger_sha256'][:12]} all 11 bound "
            f"entries carry status != accepted ({rep['ledger_status_observation']['bound_status_counts']}), "
            f"so D3 fails for all of them independently of the schema revision. No completion, no gate "
            f"verdict; artifact is unverified pending A1."
        ),
    }

    ev_reaudit = {
        "event_id": f"flash-10-artifact-wcc-reaudit-raw-{stamp}",
        "event_type": "artifact",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "artifact_type": "json",
        "path": str(REAUDIT.relative_to(ROOT)),
        "sha256": re_h,
        "bytes": REAUDIT.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "evidence_refs": [
            f"{REAUDIT.relative_to(ROOT)}#{re_h[:12]}",
            f"schemas/af_wcc_vacuum.yaml#{rep['inputs']['schemas/af_wcc_vacuum.yaml'][:12]}",
            f"ledger/theorems.jsonl#{rep['inputs']['ledger/theorems.jsonl'][:12]}",
        ],
        "falsifier": rep["falsifier"],
        "summary": (
            "Raw re-run of the unmodified WCC conformance audit (only OUT redirected) at canonical "
            f"F1 sha 9a8bd4c96800 and ledger sha {rep['inputs']['ledger/theorems.jsonl'][:12]}: "
            f"11 bound entries, 0 discharging, class conclusion state "
            f"'{rep['rerun']['class_definition']['epistemic_status']}'."
        ),
    }

    ev_status = {
        "event_id": f"flash-10-status-wcc-reaudit-{stamp}",
        "event_type": "status",
        "created_at": created,
        "actor": "deepseek-flash-10",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "class_ids": [CLASS],
        "assignment_ref": ASSIGNMENT_REF,
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.2,
        "summary": ev_report["summary"],
        "evidence_refs": [
            f"{REPORT.relative_to(ROOT)}#{rep_h[:12]}",
            f"{REAUDIT.relative_to(ROOT)}#{re_h[:12]}",
            f"{DRIVER.relative_to(ROOT)}#{drv_h[:12]}",
            f"artifacts/flash-10/l1_class_coverage/wcc_class_conformance_audit.py#{aud_h[:12]}",
            f"ledger/theorems.jsonl#{rep['inputs']['ledger/theorems.jsonl'][:12]}",
            f"ledger/citation_audit.csv#{rep['inputs']['ledger/citation_audit.csv'][:12]}",
        ],
        "next_falsifier": (
            "Re-run wcc_reaudit_rev11.py at a later schema/ledger revision: a substantive "
            "(non-revision) class-definition diff, a class_definition sha != measured canonical "
            "sha, or n_discharging >= 1 falsifies this reading; a ledger revision that returns "
            "bound entries to status=accepted would also change the D3 picture."
        ),
    }

    events = [ev_report, ev_reaudit, ev_status]
    errors = []
    # events.schema.json covers artifact/claim/review/direction_update/resource_request only.
    # `status` is an upward type defined in comms/PROTOCOL.md, so validate it against the
    # protocol's required field list instead.
    protocol_status_fields = ("node_id", "status", "hours", "summary", "evidence_refs",
                              "next_falsifier")
    for e in events:
        if e["event_type"] == "status":
            missing = [f for f in protocol_status_fields if f not in e]
            if missing:
                errors.append(f"{e['event_id']}: status missing {missing}")
            continue
        try:
            jsonschema.validate(e, SCHEMA)
        except jsonschema.ValidationError as ex:
            errors.append(f"{e['event_id']}: {ex.message}")
    if errors:
        for x in errors:
            print("SCHEMA FAIL:", x, file=sys.stderr)
        return 1

    with OUTBOX.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_type"], e["event_id"], e.get("sha256", "")[:12])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
