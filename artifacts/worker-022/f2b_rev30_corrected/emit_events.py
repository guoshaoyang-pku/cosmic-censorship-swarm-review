#!/usr/bin/env python3
"""Emit the W022-F2B-REV30-CORRECTED-FREEZE-REHEARSAL-01 events to comms/outbox/worker-022.jsonl.

Validates every line with research_map/schemas.validate_event before appending; refuses to
write a partial batch.  One artifact event per evidence file, one claim, one status with
completion_claim.  No controller runtime file is touched by this script.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
OUT = HERE.parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0).isoformat()
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
TASK = "W022-F2B-REV30-CORRECTED-FREEZE-REHEARSAL-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(rel: str) -> str:
    return f"{rel}#{sha(ROOT / rel)[:12]}"


REPORT = "artifacts/worker-022/f2b_rev30_corrected/report.json"
PREREG = "artifacts/worker-022/f2b_rev30_corrected/preregistration.json"
ADDENDUM = "artifacts/worker-022/f2b_rev30_corrected/preregistration_addendum.json"
RUNBOOK = "artifacts/worker-022/f2b_rev30_corrected/OWNER_RUNBOOK.corrected.md"
INSTRUMENT = "artifacts/worker-022/f2b_rev30_corrected/rehearse.py"
RUN1 = "artifacts/worker-022/f2b_rev30_corrected/run1_report.json"
BATTERY = "artifacts/worker-022/f2b_rev30_corrected/battery_w022_rev30_corrected.json"
DUAL = "artifacts/worker-022/f2b_rev30_corrected/dual_w022_rev30_corrected.json"
CHECKPOINT = "runtime/state/w022_f2b_rev30_corrected_checkpoint_1.json"
CAND = "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml"
C0 = "schemas/af_scc_c0_vacuum.yaml"
C2 = "schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
RUNBOOK058 = "artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md"

report = json.loads((ROOT / REPORT).read_text())
summary = report["summary"]

events = []


def artifact(rel: str, artifact_type: str, node_id: str, extra_refs=None):
    events.append({
        "event_id": f"w022-f2b-rev30-corrected-{STAMP}-artifact-{Path(rel).stem}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-022",
        "node_id": node_id,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "artifact_type": artifact_type,
        "path": rel,
        "sha256": sha(ROOT / rel),
        "validation_status": "unverified",
        "summary": artifact_summaries.get(rel, artifact_type),
        "evidence_refs": [ev(rel)] + [ev(r) for r in (extra_refs or [])],
    })


artifact_summaries = {
    PREREG: "Pre-registration written before measurement: declared pins, expectations E1-E14, controls K1-K5, falsifier, authority note.",
    ADDENDUM: "Post-hoc disclosure of instrument amendments DEV-1..DEV-5 (run-1 harness defects, E7 ordering, X3c key, stale mutant count, runbook output-path trap) and observations OBS-1/OBS-2.",
    INSTRUMENT: "Deterministic sandbox-only rehearsal instrument; read-only on canonical paths, all writes under artifacts/worker-022/.",
    REPORT: "Machine report: REHEARSAL_PASS, 14/14 expectations, 5/5 controls, 0 canonical writes, pin-move table, refreeze/verify/idempotence, acceptance and derived-tool records.",
    RUNBOOK: "Corrected owner runbook keyed on 51c253c4 with an explicit delta against the worker-058 card (which pins the direction-inverted 84b5d3fa).",
    RUN1: "Preserved run-1 report (REHEARSAL_FAIL on E7/E9/K1) showing the three instrument defects disclosed in the addendum.",
    BATTERY: "Acceptance battery output on the corrected sandbox bytes: verdict PASS, 0 hard failures, X3c violations 0, plus the 2-file post-repair residual note.",
    DUAL: "Dual-defect audit output on the corrected sandbox bytes: verdict PASS, 0 findings, hash-bound to 51c253c4 and C2 e9a27996.",
    CHECKPOINT: "Worker-local checkpoint (controller runtime checkpoint untouched): pins unchanged during run, result, artifact hashes, falsifier, non-claims.",
}

for rel, typ in [(PREREG, "preregistration"), (ADDENDUM, "preregistration_addendum"),
                 (INSTRUMENT, "instrument"), (REPORT, "machine_report"),
                 (RUNBOOK, "runbook"), (RUN1, "provenance_report"),
                 (BATTERY, "acceptance_battery_output"), (DUAL, "acceptance_dual_output"),
                 (CHECKPOINT, "worker_checkpoint")]:
    artifact(rel, typ, "F2b" if rel != CHECKPOINT else "F2b", extra_refs=[REPORT])

statement = (
    "At the live rev13 / FROZEN rev29 pins (C0 b2ab6acb2bbe in both copies, C2 e9a27996dfd3, "
    "F1 d9cebb9404b2, F0 0abb9ed8a961, FROZEN 815e08079aef; all unchanged at run end), a sandbox-only "
    "rehearsal of the rev30 publication path keyed on the corrected F2b containment candidate 51c253c4 "
    "(instead of the direction-inverted 84b5d3fa pinned by the worker-058 owner runbook) passes all 14 "
    "pre-registered expectations with 5/5 detected controls and 0 canonical writes: the two-leaf repair "
    "applied to both C0 copies reproduces sha256 51c253c4; regenerate_frozen.py --revision 30 at "
    "2026-09-12T02:00:00+08:00 produces a 50-file manifest (digest 1046dd9ef687) with exactly the two C0 "
    "paths moved and 0 missing/added/removed; verify_frozen.py is clean (0 problems) and a second identical "
    "refreeze is byte-identical; the acceptance battery is PASS with 0 hard failures and X3c=0 and the dual "
    "audit is PASS with 0 findings at the corrected bytes while both FAIL on the rev29 control; the three "
    "landing-obligation tools (measure_semantic_escape.py, rebase_heldout.py, run_gate_tests.py) run to "
    "completion at the corrected base with headline counts equal to the rev29 control base (semantic escape "
    "1/31, held-out union escape 1/26, gate PASS 3/3 canonical + 6/6 null controls + 31/31 mutants). A "
    "corrected owner runbook keyed on 51c253c4 is staged with a disclosed instrument amendment "
    "(run1_report.json, DEV-1..DEV-5). Measured residual: the battery records 2 corpus fixture/mutant files "
    "still carrying the pre-repair sentence. No canonical file was written by this task."
)

claim = {
    "event_id": f"w022-f2b-rev30-corrected-{STAMP}-claim",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "worker-022",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "task_id": TASK,
    "conclusion_type": "numerical_evidence",
    "statement": statement,
    "assumptions": [
        "the measured sha256 is artifact identity; FROZEN rev29 815e08079aef is the binding pin set",
        "the sandbox tools resolve their own root, so every read and write in the rehearsal is sandbox-local; all canonical pins were hashed at start and end and did not move",
        "c2_c0_separation_audit.py's exit code is confounded by a Path.relative_to(REPO) print bug when its outputs live outside the repo; the rehearsal keeps them inside (DEV-1) and reads the verdict from the report JSON",
        "the rev29 control sandbox is the correct differential baseline for the three derived-evidence tools",
        "run_gate_tests.py's docstring count is stale (31 mutants measured, not 22; DEV-4)",
        "E-level results are worker evidence, not a gate verdict, and do not move any node status",
    ],
    "falsifier": report["falsifier"],
    "evidence_refs": [ev(REPORT), ev(PREREG), ev(ADDENDUM), ev(RUNBOOK), ev(RUN1), ev(BATTERY),
                      ev(DUAL), ev(CHECKPOINT), f"{CAND}#51c253c46306", f"{C0}#b2ab6acb2bbe",
                      f"{C2}#e9a27996dfd3", f"{FROZEN}#815e08079aef",
                      f"{RUNBOOK058}#410f72e5121e"],
    "artifact_refs": [REPORT, PREREG, ADDENDUM, RUNBOOK, INSTRUMENT, BATTERY, DUAL, CHECKPOINT],
}
events.append(claim)

status = {
    "event_id": f"w022-f2b-rev30-corrected-{STAMP}-status",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-022",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "task_id": TASK,
    "status": "active",
    "completion_claim": True,
    "hours": 0.5,
    "summary": (
        "W022-F2B-REV30-CORRECTED-FREEZE-REHEARSAL-01 complete at worker level: one bounded class-bound "
        "task, read-only on canonical paths. REHEARSAL_PASS, 14/14 expectations, 5/5 controls, 0 canonical "
        "writes. A corrected owner runbook keyed on the corrected candidate 51c253c4 is staged at "
        "artifacts/worker-022/f2b_rev30_corrected/OWNER_RUNBOOK.corrected.md, superseding step 1 and the "
        "expected hash of the worker-058 card (which pins the direction-inverted 84b5d3fa). Owner action "
        "requested: land the corrected pair, re-freeze rev30, run verify_frozen, the two acceptance tools "
        "and the three derived-evidence tools. No node status, validation_status or gate verdict is set."
    ),
    "evidence_refs": [ev(REPORT), ev(RUNBOOK), ev(PREREG), ev(ADDENDUM), ev(CHECKPOINT), ev(RUN1),
                      f"{CAND}#51c253c46306", f"{FROZEN}#815e08079aef"],
    "next_falsifier": report["falsifier"],
}
events.append(status)

# ---- validate before writing anything ----
for e in events:
    validate_event(e)
outbox = ROOT / "comms/outbox/worker-022.jsonl"
existing = outbox.read_text() if outbox.exists() else ""
existing_ids = {json.loads(l)["event_id"] for l in existing.splitlines() if l.strip()}
dup = [e["event_id"] for e in events if e["event_id"] in existing_ids]
if dup:
    print(json.dumps({"refused": "duplicate event_ids", "ids": dup}, indent=1))
    sys.exit(1)
with outbox.open("a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")
print(json.dumps({"appended": len(events), "outbox": str(outbox.relative_to(ROOT)),
                  "event_ids": [e["event_id"] for e in events]}, indent=1))
