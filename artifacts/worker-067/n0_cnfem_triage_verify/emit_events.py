#!/usr/bin/env python3
"""Emit worker-067 W067-N0-CNFEM-TRIAGE-VERIFY-01 events to comms/outbox.

Appends one JSON object per line.  Does not ingest, does not touch the map,
does not set validation_status=passed or any gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
OUT = ROOT / "comms" / "outbox" / "worker-067.jsonl"

LEDGER = ART / "ledger.json"
CHECKER = ART / "check_cnfem_triage.py"
README = ART / "README.md"

TASK = "W067-N0-CNFEM-TRIAGE-VERIFY-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE = "N0"
GATE = "G-NUM"
TRIAGE = "numerics/tests/replication_triage.md"
TRIAGE_SHA = "f27a253ec928bc09e8e786cfbfd87626102cae6b2641ec5d81ff01c209748792"
MOD = "numerics/tests/flat_wave_replication.py"
MOD_SHA = "8ade1cdc163ea420790b9fdfdab41157b4f3d4219d6a0bcf827baafe69a6f422"

FALSIFIER = (
    "Withdrawn if any of: (a) the wrong-RHS variant constructed here measures order >= 0.5 or no amplitude "
    "growth at dr=0.2; (b) the live cnfem order study leaves the harness band or its own-energy drift exceeds "
    "1e-12; (c) the published JSON's cnfem rows disagree with a re-run at hash 8ade1cdc; (d) "
    "numerics/tests/flat_wave_replication.py no longer hashes to 8ade1cdc, which voids M2-M4 by hash and "
    "transfers no claim to the new revision; (e) the docstring no longer contains the pre-fix recurrence, "
    "which voids F2 only."
)
AUTHORITY = (
    "Worker verification event: advisory; does not accept the triage, close G-NUM, set validation_status=passed, "
    "or claim any node transition.  Read-only on all canonical paths; wrote only under artifacts/worker-067/ "
    "and runtime/state/worker-067_checkpoint_8.json."
)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    for p in (LEDGER, CHECKER, README):
        if not p.exists():
            print(f"missing artifact: {p}", file=sys.stderr)
            return 2
    ledger = json.loads(LEDGER.read_text())
    h_led, h_chk, h_read = sha256(LEDGER), sha256(CHECKER), sha256(README)
    if ledger.get("verdict") != "CNFEM_ROOT_CAUSE_AND_FIX_REPRODUCED_WITH_DOCSTRING_DEFECT":
        print("ledger verdict is not the verified outcome; refusing to emit", file=sys.stderr)
        return 2

    ts = datetime.now(timezone(timedelta(hours=8)))
    stamp = ts.strftime("%Y%m%dT%H%M%S")
    now = ts.isoformat(timespec="seconds")
    refs = [
        f"{CHECKER.relative_to(ROOT)}#{h_chk[:12]}",
        f"{LEDGER.relative_to(ROOT)}#{h_led[:12]}",
        f"{README.relative_to(ROOT)}#{h_read[:12]}",
        f"{TRIAGE}#{TRIAGE_SHA[:12]}",
        f"{MOD}#{MOD_SHA[:12]}",
        "numerics/results/flat_wave_replication.json#298a4d921c22",
        "runtime/state/controller_verification/N0_adjudication.md#003baf8b31d9",
        "numerics/protocol/format_conditions_disposition.json#e7c05ff33fe2",
    ]
    summary = (
        "Independent read-only verification of the open G-NUM unmet item 'cnfem triage ... fix with root cause, "
        "or exclude with evidence'.  The pre-fix recurrence constructed independently here (wrong CN/FEM "
        "right-hand side) measures order -0.07727 with amplitude 1.0->2.52 at dr=0.2; the live fixed scheme "
        "measures order 1.9863235066828981, own-energy drift 2.04e-14, harness drift 8.48e-09 (tol 1e-6); the "
        "published JSON reproduces bit-exactly.  New minor finding: the live CrankNicolsonFEM docstring (line "
        "305) still documents the pre-fix recurrence while the code is correct.  Controls 10/10, 0 canonical writes."
    )
    events = [
        {"event_id": f"w067-cnfemverify-{stamp}-00-task", "event_type": "status", "created_at": now,
         "actor": "worker-067", "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
         "status": "active", "task_id": TASK, "hours": 0.6,
         "summary": f"Task {TASK} claimed from the live G-NUM unmet list; read-only verification, no gate verdict.",
         "evidence_refs": refs[:1], "next_falsifier": FALSIFIER},
        {"event_id": f"w067-cnfemverify-{stamp}-01-checker", "event_type": "artifact", "created_at": now,
         "actor": "worker-067", "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
         "artifact_type": "deterministic_verification_checker", "path": str(CHECKER.relative_to(ROOT)),
         "sha256": h_chk, "validation_status": "unverified",
         "summary": "Re-runs the published harness driver on an independently constructed pre-fix CN/FEM "
                    "recurrence and on the live fixed scheme; 10 fail-closed controls; exit 2 on any failure.",
         "evidence_refs": refs[:1] + [f"{MOD}#{MOD_SHA[:12]}"], "next_falsifier": FALSIFIER},
        {"event_id": f"w067-cnfemverify-{stamp}-02-ledger", "event_type": "artifact", "created_at": now,
         "actor": "worker-067", "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
         "artifact_type": "cnfem_triage_verification_ledger", "path": str(LEDGER.relative_to(ROOT)),
         "sha256": h_led, "validation_status": "unverified",
         "summary": f"verdict=CNFEM_ROOT_CAUSE_AND_FIX_REPRODUCED_WITH_DOCSTRING_DEFECT; controls "
                    f"{ledger.get('controls_passed')}; wrong-order -0.07727 vs fixed-order 1.9863235066828981; "
                    f"published JSON bit-exact; 0 canonical writes; anchors stable.",
         "evidence_refs": [f"{CHECKER.relative_to(ROOT)}#{h_chk[:12]}", f"{TRIAGE}#{TRIAGE_SHA[:12]}",
                                      "numerics/results/flat_wave_replication.json#298a4d921c22"],
         "next_falsifier": FALSIFIER},
        {"event_id": f"w067-cnfemverify-{stamp}-03-readme", "event_type": "artifact", "created_at": now,
         "actor": "worker-067", "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
         "artifact_type": "method_and_findings_note", "path": str(README.relative_to(ROOT)),
         "sha256": h_read, "validation_status": "unverified",
         "summary": "Per-measurement table M1-M5, findings F1-F4, minimal recommended action, reproduction, "
                    "falsifier, non-claims.",
         "evidence_refs": [f"{LEDGER.relative_to(ROOT)}#{h_led[:12]}"], "next_falsifier": FALSIFIER},
        {"event_id": f"w067-cnfemverify-{stamp}-10-review", "event_type": "review", "created_at": now,
         "actor": "worker-067", "target_id": f"{TRIAGE}#{TRIAGE_SHA[:12]}", "reviewer": "worker-067",
         "class_id": CLASS_ID, "node_id": NODE, "gate": GATE, "verdict": "accept", "score": 4.0,
         "counts_as_full_schema_verdict": False, "counts_as_independent_second_verdict": False,
         "authority_note": AUTHORITY, "hard_failures": [],
         "findings": ledger.get("findings"),
         "next_falsifier": FALSIFIER,
         "evidence_refs": refs},
        {"event_id": f"w067-cnfemverify-{stamp}-99-complete", "event_type": "status", "created_at": now,
         "actor": "worker-067", "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
         "status": "active", "task_id": TASK, "hours": 0.6,
         "summary": "W067-N0-CNFEM-TRIAGE-VERIFY-01 complete at worker level: root cause and fix reproduced from "
                    "the pinned bytes, published numbers bit-exact, F2 docstring defect recorded, controls 10/10, "
                    "0 canonical writes, checkpoint runtime/state/worker-067_checkpoint_8.json.  Completion claim "
                    "for the task only; not a node transition and not a gate verdict.",
         "evidence_refs": refs, "next_falsifier": FALSIFIER},
    ]
    with OUT.open("a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
    print(json.dumps({"appended": len(events), "outbox": str(OUT.relative_to(ROOT)),
                      "event_ids": [e["event_id"] for e in events],
                      "hashes": {"checker": h_chk, "ledger": h_led, "readme": h_read}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
