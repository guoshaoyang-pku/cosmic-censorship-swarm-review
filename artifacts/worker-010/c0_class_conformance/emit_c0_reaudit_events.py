#!/usr/bin/env python3
"""Emit the W010-L1-REAUDIT-02 (AF-SCC-C0-VAC-GEN rev12) events to the flash-10 outbox.

Emits: report artifact, wrapper/driver artifact, status. Every event is schema-validated
before any line is written. Appends one JSON object per line; never edits existing lines.
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

REPORT = HERE / "c0_class_conformance_audit.55d0a1ea9bda.json"
WRAPPER = HERE / "c0_reaudit_rev12.py"
DRIVER = HERE / "c0_class_conformance_audit.py"
REV11_REPORT = HERE / "c0_class_conformance_audit.json"
SNAP = HERE / "snapshots" / "af_scc_c0_vacuum.55d0a1ea9bda.yaml"

CST = timezone(timedelta(hours=8))
CLASS = "AF-SCC-C0-VAC-GEN"
TASK_ID = "W010-L1-REAUDIT-02"
ASSIGNMENT_REF = "asg-2026-09-11-L1-deepseek-flash-10-19"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    created = datetime.now(CST).replace(microsecond=0).isoformat()
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    rep_h, wrap_h, drv_h, rev11_h, snap_h = (
        sha256(REPORT), sha256(WRAPPER), sha256(DRIVER), sha256(REV11_REPORT), sha256(SNAP))
    s = rep["summary"]
    ad = rep["revision_addendum"]
    lo = rep["ledger_status_observation"]
    changed = ad["step_drift_rev11_to_rev12"]["fields_changed_beyond_revision"]

    summary = (
        f"W010-L1-REAUDIT-02 rev12 addendum: AF-SCC-C0-VAC-GEN re-derived at F2b rev12 "
        f"55d0a1ea9bda and ledger {lo['measured_ledger_sha256'][:12]} (rev11 report was bound to "
        f"F2b 1bb78ce9b357 / ledger {str(lo['rev11_report_input_ledger_sha256'])[:12]}). "
        f"Extraction-level change: {changed} (parameter renaming `(s,delta)` -> `r`, same comeager "
        f"quantifier structure) -> rev11 report's own falsifier fired; whether it is semantic is "
        f"F1/A1's call. Re-run: n_bound={s['n_bound_entries']}, n_discharging={s['n_discharging']}, "
        f"conclusion state '{s['class_conclusion_state']}'; accepted-status entries at the current "
        f"ledger {lo['n_accepted_status_now']} (rev11 read {lo['n_accepted_status_rev11']}), so D3 "
        f"fails at status level for every binding. Mechanical flags: direction-mismatch candidates "
        f"{s['direction_mismatch_candidates']}, weakening/inflation candidates "
        f"{s['weakening_or_inflation_candidates']}. No completion, no gate verdict."
    )
    next_falsifier = (
        "A further F2b revision changing statement_formal / epistemic_status / genericity_kind / "
        "extension_regularity fields, or a class_definition sha != measured canonical sha, or a "
        "later ledger at which an entry with status=accepted satisfies D1+D2+D3 (then "
        "n_discharging >= 1 and the class conclusion state is 'discharged'), or a formulation-lead "
        "ruling that the `(s,delta)` -> `r` renaming is substantive (which would void the "
        "rev11->rev12 continuity of this reading)."
    )

    ev_report = {
        "event_id": f"flash-10-artifact-c0-reaudit-rev12-{stamp}",
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
        "supersedes": {
            "path": str(REV11_REPORT.relative_to(ROOT)),
            "sha256": rev11_h,
            "reason": ad["supersedes_reason"],
        },
        "evidence_refs": rep["evidence_refs"] + [f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}"],
        "inputs": rep["inputs"],
        "falsifier": rep["falsifier"],
        "next_falsifier": next_falsifier,
        "summary": summary,
    }

    ev_wrapper = {
        "event_id": f"flash-10-artifact-c0-reaudit-rev12-driver-{stamp}",
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
        "artifact_type": "python",
        "path": str(WRAPPER.relative_to(ROOT)),
        "sha256": wrap_h,
        "bytes": WRAPPER.stat().st_size,
        "validation_status": "unverified",
        "claims_completion": False,
        "evidence_refs": [
            f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}",
            f"{DRIVER.relative_to(ROOT)}#{drv_h[:12]}",
            f"{REV11_REPORT.relative_to(ROOT)}#{rev11_h[:12]}",
            f"{SNAP.relative_to(ROOT)}#{snap_h[:12]}",
        ],
        "falsifier": next_falsifier,
        "summary": (
            "Revision-addendum wrapper: imports the unmodified rev11 C0 driver "
            f"({DRIVER.name} {drv_h[:12]}), redirects only OUT to the rev12-prefixed file, and adds "
            "the step-drift / ledger-drift / input-stability record. The rev11 report is preserved "
            "byte-identical."
        ),
    }

    ev_status = {
        "event_id": f"flash-10-status-c0-reaudit-rev12-{stamp}",
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
        "summary": summary,
        "evidence_refs": [
            f"{REPORT.relative_to(ROOT)}#{rep_h[:12]}",
            f"{WRAPPER.relative_to(ROOT)}#{wrap_h[:12]}",
            f"{DRIVER.relative_to(ROOT)}#{drv_h[:12]}",
            f"{REV11_REPORT.relative_to(ROOT)}#{rev11_h[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{rep['inputs']['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}",
            f"ledger/theorems.jsonl#{rep['inputs']['ledger/theorems.jsonl']['sha256'][:12]}",
        ],
        "next_falsifier": next_falsifier,
    }

    events = [ev_report, ev_wrapper, ev_status]
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
