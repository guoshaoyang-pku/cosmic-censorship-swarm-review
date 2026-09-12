#!/usr/bin/env python3
"""Emit the W010-L1-REAUDIT-01 rev12 addendum events to the flash-10 outbox.

Supersedes the rev11-bound events (already ingested) with a re-derivation at F1 rev12
cce9c60146d6, and discloses that the rev11 report's extraction-level falsifier fired.
Validates every event before writing; appends one JSON object per line.
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

REPORT12 = HERE / "wcc_class_conformance_reaudit.rev12.json"
REAUDIT12 = HERE / "wcc_class_conformance_audit.cce9c60146d6.json"
WRAPPER = HERE / "wcc_reaudit_rev12.py"
DRIVER11 = HERE / "wcc_reaudit_rev11.py"
REPORT11 = HERE / "wcc_class_conformance_reaudit.json"

CST = timezone(timedelta(hours=8))
CLASS = "AF-WCC-VAC-GEN"
TASK_ID = "W010-L1-REAUDIT-01"
ASSIGNMENT_REF = "asg-2026-09-11-L1-deepseek-flash-10-19"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = datetime.now(CST).replace(microsecond=0).isoformat()
    rep = json.loads(REPORT12.read_text(encoding="utf-8"))
    rep_h, re_h, wrap_h, drv_h = sha256(REPORT12), sha256(REAUDIT12), sha256(WRAPPER), sha256(DRIVER11)
    rep11_h = sha256(REPORT11)
    s = rep["rerun"]["summary"]
    ad = rep["revision_addendum"]

    ev_report = {
        "event_id": f"flash-10-artifact-wcc-reaudit-rev12-{stamp}",
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
        "path": str(REPORT12.relative_to(ROOT)),
        "sha256": rep_h,
        "bytes": REPORT12.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "supersedes": {
            "path": str(REPORT11.relative_to(ROOT)),
            "sha256": rep11_h,
            "reason": ad["supersedes_reason"],
        },
        "evidence_refs": rep["evidence_refs"] + [f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}"],
        "inputs": rep["inputs"],
        "falsifier": rep["falsifier"],
        "summary": (
            f"W010-L1-REAUDIT-01 rev12 addendum: F1 moved rev11 9a8bd4c96800 -> rev12 "
            f"cce9c60146d6 with extraction-level substantive differences "
            f"({ad['fields_changed']}), firing the rev11 report's own falsifier. Re-derived at "
            f"rev12: class_definition sha cce9c60146d6, n_bound={s['n_bound_entries']}, "
            f"n_discharging={s['n_discharging']}, conclusion state '{s['class_conclusion_state']}'; "
            f"all inputs stable during the run. The visible rev11->rev12 difference is a parameter "
            f"renaming ((s,delta) -> r, same comeager quantifier structure); whether that is "
            f"semantic is F1/A1's call, not this worker's. Ledger at "
            f"{rep['ledger_status_observation']['measured_ledger_sha256'][:12]} still has 0 of 11 "
            f"bound entries with status=accepted. No completion, no gate verdict."
        ),
    }

    ev_reaudit = {
        "event_id": f"flash-10-artifact-wcc-reaudit-rev12-raw-{stamp}",
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
        "path": str(REAUDIT12.relative_to(ROOT)),
        "sha256": re_h,
        "bytes": REAUDIT12.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "evidence_refs": [
            f"{REAUDIT12.relative_to(ROOT)}#{re_h[:12]}",
            f"schemas/af_wcc_vacuum.yaml#{rep['inputs']['schemas/af_wcc_vacuum.yaml'][:12]}",
            f"ledger/theorems.jsonl#{rep['inputs']['ledger/theorems.jsonl'][:12]}",
            f"{DRIVER11.relative_to(ROOT)}#{drv_h[:12]}",
        ],
        "falsifier": rep["falsifier"],
        "summary": (
            "Raw rev12 re-run of the unmodified WCC conformance audit (rev11 driver, OUT "
            f"redirected) at canonical F1 sha cce9c60146d6 and ledger sha "
            f"{rep['inputs']['ledger/theorems.jsonl'][:12]}: 11 bound, 0 discharging."
        ),
    }

    ev_status = {
        "event_id": f"flash-10-status-wcc-reaudit-rev12-{stamp}",
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
        "hours": 0.1,
        "summary": ev_report["summary"],
        "evidence_refs": [
            f"{REPORT12.relative_to(ROOT)}#{rep_h[:12]}",
            f"{REAUDIT12.relative_to(ROOT)}#{re_h[:12]}",
            f"{REPORT11.relative_to(ROOT)}#{rep11_h[:12]}",
            f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}",
            f"{DRIVER11.relative_to(ROOT)}#{drv_h[:12]}",
            f"schemas/af_wcc_vacuum.yaml#{rep['inputs']['schemas/af_wcc_vacuum.yaml'][:12]}",
            f"ledger/theorems.jsonl#{rep['inputs']['ledger/theorems.jsonl'][:12]}",
        ],
        "next_falsifier": (
            "Re-run wcc_reaudit_rev12.py at a later F1 revision: a further change to "
            "quantifier_formal / conclusion_statement_formal / genericity fields, a "
            "class_definition sha != measured canonical sha, or n_discharging >= 1 falsifies this "
            "rev12 reading. A formulation-lead ruling that the parameter renaming is non-semantic "
            "would restore continuity across rev10/rev11/rev12 for the 0-discharge reading."
        ),
    }

    events = [ev_report, ev_reaudit, ev_status]
    errors = []
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
