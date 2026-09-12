#!/usr/bin/env python3
"""Emit the rev12 drift/re-measure addendum events for W037-F1-VISIBILITY-03. Idempotent."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
TASK = "W037-F1-VISIBILITY-03-ADDENDUM-REV12"
CLASS = "AF-WCC-VAC-GEN"
NODE = "F1"
GATE = "G-FORM"
OUTBOX = ROOT / "comms" / "outbox" / "worker-037.jsonl"
CKPT_DIR = ROOT / "runtime" / "state"
NOTE = "artifacts/worker-037/f1_visibility_equivalence_adjudication/rev12_remeasure.json"
SCRIPT = "artifacts/worker-037/f1_visibility_equivalence_adjudication/remeasure_rev12.py"
PRIMARY = "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"
F1 = "schemas/af_wcc_vacuum.yaml"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(CST)
    ts = now.strftime("%Y%m%dT%H%M%S")
    created = now.strftime("%Y-%m-%dT%H:%M:%S%z")
    eid = lambda s: f"w037-{ts}-{s}"  # noqa: E731

    rec = json.loads((ROOT / NOTE).read_text())
    assert rec["pins_stable"], "pins moved; re-run remeasure_rev12.py"
    assert rec["discharged"]["binder_repair_landed"], "binder repair absent; note is wrong"
    h_note, h_script, h_f1 = sha(NOTE), sha(SCRIPT), sha(F1)
    h_primary = sha(PRIMARY)
    assert h_f1 == rec["pins"]["T0"][F1], "F1 moved since re-measure"

    falsifier = rec["falsifier"]
    nxt = rec["next_falsifier"]
    common = {"actor": "worker-037", "task_id": TASK, "class_id": CLASS, "class_ids": [CLASS], "gate": GATE}

    events = [
        {**common, "event_id": eid("art-visibility-rev12-remeasure"), "event_type": "artifact",
         "created_at": created, "node_id": NODE, "artifact_type": "verification_report",
         "path": NOTE, "sha256": h_note, "validation_status": "unverified",
         "evidence_refs": [f"{NOTE}#{h_note[:12]}", f"{SCRIPT}#{h_script[:12]}", f"{PRIMARY}#{h_primary[:12]}",
                           f"{F1}#{h_f1[:12]}", "research_map/formulation_taxonomy.yaml#0abb9ed8a961"],
         "summary": "Post-emit drift + re-measure at F1 rev12 cce9c60146d6 (primary adjudication bound b474fbc49cdd; "
                    "FROZEN moved 2554e276->5fa3b3bf, F0 unchanged). The rev12 rewrite replaced the whole-curve formal "
                    "clause and D5 reading with the (q,t0) tail binder, so the binder recommendation is DISCHARGED. "
                    "Not fixed: the rev12 D5 justification 'whole-curve containment ... is strictly STRONGER' (line 72) "
                    "and the surviving 'would misclassify' sentence in visibility.definition remain false under (H) - "
                    "the two predicates are equivalent for D4 geodesics. Non-blocking precision item; the chosen "
                    "predicate is correct. Logical result (LEMMA-W026-1) is revision-independent.",
         "next_falsifier": nxt},
        {**common, "event_id": eid("art-visibility-rev12-checker"), "event_type": "artifact",
         "created_at": created, "node_id": NODE, "artifact_type": "verification_tool",
         "path": SCRIPT, "sha256": h_script, "validation_status": "unverified",
         "evidence_refs": [f"{SCRIPT}#{h_script[:12]}", f"{NOTE}#{h_note[:12]}", f"{F1}#{h_f1[:12]}"],
         "summary": "Read-only re-measure script: pins T0/T1, old/new needle table, discharge and residual-claim "
                    "extraction with line numbers, revision-independent result, drift disclosure.",
         "next_falsifier": nxt},
        {**common, "event_id": eid("status-visibility-rev12-note"), "event_type": "status",
         "created_at": created, "node_id": NODE, "status": "active", "hours": 0.1,
         "summary": "ADDENDUM to W037-F1-VISIBILITY-03 (primary events w037-20260912T003325-*). The canonical F1 was "
                    "rewritten to rev12 cce9c60146d6 (from the primary's b474fbc49cdd) while the primary events were "
                    "being emitted, and FROZEN.json moved with it. Measured at rev12: the binder repair landed (formal "
                    "tail clause + D5 (q,t0) present; whole-curve needles gone) -> the W037V2-F1 operational "
                    "recommendation is discharged. Residual, non-blocking: rev12's D5 sentence at line 72 ('Whole-curve "
                    "containment ... is strictly STRONGER and is NOT the predicate of this class') and the line-213 "
                    "'would misclassify' sentence assert a strictness relation that the primary adjudication refutes "
                    "for D4 geodesics under (H); recommend stating the equivalence instead. Controller bindings must "
                    "re-pin to the rev12/FROZEN hashes. No gate verdict, no node status, no canonical edit.",
         "evidence_refs": [f"{NOTE}#{h_note[:12]}", f"{SCRIPT}#{h_script[:12]}", f"{PRIMARY}#{h_primary[:12]}",
                           f"{F1}#{h_f1[:12]}"],
         "next_falsifier": nxt},
    ]

    seen: set[str] = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    appended = []
    with OUTBOX.open("a") as f:
        for e in events:
            if e["event_id"] in seen:
                print("skip existing", e["event_id"])
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended.append(e["event_id"])
            seen.add(e["event_id"])

    ckpt_rel = f"runtime/state/w037_checkpoint_{ts}_visibility_rev12_note.json"
    ckpt = {"actor": "worker-037", "authority_note": "worker event; no node status, validation_status or gate verdict",
            "checkpoint_id": f"w037-ckpt-{ts}-visibility-rev12-note", "class_ids": [CLASS], "created_at": created,
            "events": [e["event_id"] for e in events], "gate": GATE, "node_id": NODE, "task_id": TASK,
            "artifacts": {NOTE: h_note, SCRIPT: h_script, PRIMARY: h_primary},
            "F1_at_note": h_f1, "F1_at_primary": rec["primary_binding"]["F1_at_T0_T1_of_primary"],
            "FROZEN_now": rec["pins"]["T0"]["artifacts/formulation/FROZEN.json"],
            "result": "binder repair landed at rev12 -> primary recommendation discharged; residual non-blocking "
                      "false-strictness sentences at F1 lines 72 and 213",
            "next_falsifier": nxt}
    (ROOT / ckpt_rel).write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    log = CKPT_DIR / "w037_checkpoints.jsonl"
    already = False
    if log.exists():
        already = any(json.loads(l).get("checkpoint_id") == ckpt["checkpoint_id"]
                      for l in log.read_text().splitlines() if l.strip())
    if not already:
        with log.open("a") as f:
            f.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "created_at": created, "path": ckpt_rel,
                                "task_id": TASK, "events": ckpt["events"],
                                "result": ckpt["result"]}, sort_keys=True) + "\n")
    print(f"appended {len(appended)} events; checkpoint {ckpt_rel}")
    for e in appended:
        print("  +", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
