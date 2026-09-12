#!/usr/bin/env python3
"""W098-CLASSSEP-RESTORE-REPRO-01 event emitter.

Builds the upward events for the bounded task, validates each against
research_map/schemas.py::validate_event, and appends only new event_ids to
comms/outbox/worker-098.jsonl (idempotent on re-run).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"


def load_schemas():
    import sys
    spec = importlib.util.spec_from_file_location("w098_schemas", ROOT / "research_map/schemas.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["w098_schemas"] = mod
    spec.loader.exec_module(mod)
    return mod


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


S = load_schemas()
T = "2026-09-12T01:15:40+08:00"
A = "worker-098"
NODE = "A1"
GATE = "G-AUDIT"
CLASS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
TASK = "W098-CLASSSEP-RESTORE-REPRO-01"

report = json.loads((HERE / "report.json").read_text())
raw = json.loads((HERE / "raw/restore_repro.json").read_text())
checkpoint = ROOT / "runtime/state/w098_classsep_restore_repro_checkpoint_1.json"

P = {
    "prereg": "artifacts/worker-098/classsep_restore_repro/pre_registration.json",
    "tool": "artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py",
    "raw": "artifacts/worker-098/classsep_restore_repro/raw/restore_repro.json",
    "report": "artifacts/worker-098/classsep_restore_repro/report.json",
    "readme": "artifacts/worker-098/classsep_restore_repro/README.md",
    "writer": "artifacts/worker-098/classsep_restore_repro/write_report.py",
    "checkpoint": "runtime/state/w098_classsep_restore_repro_checkpoint_1.json",
    "adjudication": "reviews/CLASSSEP-calibration-adjudication.json",
    "detector": "research_map/class_separation.py",
    "voided": "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
    "forensics": "runtime/state/controller_verification/cf29-detector-write-forensics.json",
    "adj_snap": "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
    "w098_snap": "artifacts/worker-098/classsep_prose_shadow/snapshot/research_map.pinned.json",
    "live_map": "research_map/research_map.json",
}
H = {k: sha(ROOT / v) for k, v in P.items()}
REF = [f"{P['report']}#{H['report'][:12]}", f"{P['raw']}#{H['raw'][:12]}",
       f"{P['prereg']}#{H['prereg'][:12]}", f"{P['detector']}#{H['detector'][:12]}",
       f"{P['adjudication']}#{H['adjudication'][:12]}", f"{P['adj_snap']}#{H['adj_snap'][:12]}",
       f"{P['w098_snap']}#{H['w098_snap'][:12]}", f"{P['voided']}#{H['voided'][:12]}",
       f"{P['checkpoint']}#{H['checkpoint'][:12]}"]

FALSIFIER = ("Re-run artifacts/worker-098/classsep_restore_repro/verify_restore_repro.py at the pins in "
             "pre_registration.json: FALSIFIED if any of E1-E12 fails, i.e. if the live detector or an a8c04fc31e4a pin "
             "moves, if any bound figure changes on the pinned bytes, if any adjudication-cited hard count does not "
             "reproduce, or if the VOID arm becomes indistinguishable from RESTORED. A later write to "
             "research_map/class_separation.py does not falsify the measurement; it voids the rebase.")

events = [
    {"event_id": f"w098-rr-20260912T011540-status-take", "event_type": "status", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "status": "active", "hours": 0.1, "task_id": TASK,
     "summary": ("Took ONE bounded class-bound task on the live G-AUDIT critical path: W098-CLASSSEP-RESTORE-REPRO-01 = "
                 "independent read-only reproduction of the worker-098 drift-recheck evidence bound by research_map.json "
                 "assignment astra-life06-classsep-detector-adjudication, re-measured AFTER the CF-29 unauthorized detector "
                 "write and the controller's restore to a8c04fc31e4a. Pre-registered 12 expectations before measuring. "
                 "No canonical write, no gate verdict, no node completion."),
     "evidence_refs": [f"{P['prereg']}#{H['prereg'][:12]}", f"{P['detector']}#{H['detector'][:12]}"],
     "next_falsifier": FALSIFIER},
    {"event_id": "w098-rr-20260912T011540-art-prereg", "event_type": "artifact", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "artifact_type": "pre_registration", "path": P["prereg"], "sha256": H["prereg"], "validation_status": "unverified",
     "summary": "Pins (4-way restore, adjudication, two snapshots, voided/pre bytes, corpus) + expectations E1-E12 + void conditions, written before measurement.",
     "evidence_refs": [f"{P['detector']}#{H['detector'][:12]}", f"{P['adjudication']}#{H['adjudication'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-art-instrument", "event_type": "artifact", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "artifact_type": "restore_repro_instrument", "path": P["tool"], "sha256": H["tool"], "validation_status": "unverified",
     "summary": "Deterministic no-network read-only 3-arm instrument (RESTORED/VOID/PRE): pin guards, worker-07 corpus, 4 FP + 2 TP + 6 FN probes, 3 growth probes, hard counts on two frozen snapshots and the live map.",
     "evidence_refs": [f"{P['prereg']}#{H['prereg'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-art-raw", "event_type": "artifact", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "artifact_type": "raw_measurements", "path": P["raw"], "sha256": H["raw"], "validation_status": "unverified",
     "summary": "Raw per-arm battery output, pin checks, read-only proof (detector/adjudication/map hashes unchanged at run end), E1-E12 evaluation.",
     "evidence_refs": [f"{P['tool']}#{H['tool'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-art-report", "event_type": "artifact", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "artifact_type": "verification_report", "path": P["report"], "sha256": H["report"], "validation_status": "unverified",
     "summary": "Verdict REPRODUCED, 12/12 expectations; binding table, 3-arm census, adjudication cross-check 19/24/16, residual live count, falsifier, non-claims.",
     "evidence_refs": [f"{P['raw']}#{H['raw'][:12]}", f"{P['adj_snap']}#{H['adj_snap'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-art-readme", "event_type": "artifact", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "artifact_type": "readme", "path": P["readme"], "sha256": H["readme"], "validation_status": "unverified",
     "summary": "One-page rendering: restore table, bound-figure reproduction, 3-arm census, rerun command, non-claims.",
     "evidence_refs": [f"{P['report']}#{H['report'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-art-checkpoint", "event_type": "artifact", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "artifact_type": "worker_checkpoint", "path": P["checkpoint"], "sha256": H["checkpoint"], "validation_status": "unverified",
     "summary": "Worker-local checkpoint (controller runtime checkpoint untouched): pins, result, 6 artifact hashes, emit-time liveness, falsifier.",
     "evidence_refs": [f"{P['report']}#{H['report'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-review", "event_type": "review", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "target_id": P["adjudication"], "reviewer": A, "verdict": "accept", "score": 4.5,
     "reviewed_sha256": H["adjudication"], "counts_as_independent": True, "counts_as_full_schema_verdict": False,
     "hard_failures": [],
     "findings": [
         "W098-RR-01 (info): restore is byte-exact in 4 independent ways (live, worker-073 restore source, worker-032 APPLIED pin, CF-29 forensics restored_sha256) = a8c04fc31e4a; the adjudicated round runs at unchanged hashes.",
         "W098-RR-02 (info): all map-binding figures reproduce at the restored bytes: corpus PASS 17/0/0/10, 3/4 declared FP probes firing, growth 3, 0/6 over-suppression, 2/2 TP intact.",
         "W098-RR-03 (info): r3 adjudication hard counts on snapshot f344ed2aaea5 reproduce exactly (APPLIED 19, PRE 24, VOID 16); pass-2 snapshot line reproduces (PRE 17, RESTORED 13).",
         "W098-RR-04 (info): discrimination holds - VOID differs from RESTORED (16 vs 19 on the adjudication snapshot) and is nowhere worse, consistent with a strict suppression widening that remains unadopted.",
         "W098-RR-05 (info): liveness - live map moved a5e5ec532371/483 -> 66ada65f6027/498 during pre-registration, stable during the run; live residual 23 hard under RESTORED is snapshot-bound.",
         "W098-RR-06 (info): no canonical file modified; detector/adjudication/map hashes identical at run start and end; 0 detector writes observed.",
     ],
     "evidence_refs": REF,
     "artifact_refs": [f"{P['report']}#{H['report'][:12]}", f"{P['raw']}#{H['raw'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-claim", "event_type": "claim", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "task_id": TASK,
     "conclusion_type": "numerical_evidence",
     "statement": (
         "At the pins (live detector research_map/class_separation.py#a8c04fc31e4a equals the worker-073 restore-source pin, "
         "the worker-032 APPLIED pin and cf29-detector-write-forensics.detector.restored_sha256; adjudication "
         "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467 decision (c); adjudication snapshot f344ed2aaea5; "
         "worker-098 snapshot 6d3f0f2792a2; live map 66ada65f6027 / 498 claims), a newly written independent 3-arm instrument "
         "(RESTORED a8c04fc3 / VOID e36b0d64 / PRE c266dbec) reproduces 12/12 pre-registered expectations: the restore is "
         "byte-exact 4 ways; the map-bound worker-098 drift-recheck figures reproduce at the restored bytes (corpus PASS "
         "17/0/0/10; 3/4 declared FP probes firing; growth 3; 0/6 over-suppression; 2/2 TP probes intact); the r3 "
         "adjudication's hard counts on f344ed2aaea5 reproduce exactly (APPLIED 19, PRE 24, VOID 16) and the pass-2 snapshot "
         "line reproduces (PRE 17, RESTORED 13); VOID is discriminated from RESTORED (16 vs 19) and is nowhere worse, "
         "consistent with a strict suppression widening that remains unadopted. Live residual under RESTORED is 23 hard on "
         "map 66ada65f6027/498 claims and is snapshot-bound. No canonical write; the REC-22 recorded pin stays c266dbecaa87."
     ),
     "assumptions": [
         "the measured sha256 is the artifact identity; this claim binds only to the pins recorded in pre_registration.json",
         "the frozen snapshots, not the moving live map, are the comparable measurement surfaces",
         "the worker-07 corpus is the registered ground truth; PASS means no new FN there, not detector defect-freedom",
         "the adjudication's cited arms are the cross-check target; no arm is proposed for adoption or rollback",
         "structural detection rates only, not a physics verdict",
     ],
     "falsifier": FALSIFIER,
     "evidence_refs": REF,
     "artifact_refs": [f"{P['report']}#{H['report'][:12]}", f"{P['raw']}#{H['raw'][:12]}",
                       f"{P['prereg']}#{H['prereg'][:12]}", f"{P['tool']}#{H['tool'][:12]}"]},
    {"event_id": "w098-rr-20260912T011540-checkpoint", "event_type": "status", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "status": "active", "hours": 0.1, "task_id": TASK,
     "summary": "Worker-local checkpoint written (controller runtime checkpoint untouched): runtime/state/w098_classsep_restore_repro_checkpoint_1.json; emit-time liveness detector a8c04fc31e4a, adjudication 7714ffd5b467, live map 66ada65f6027/498 claims, 0 detector writes.",
     "evidence_refs": [f"{P['checkpoint']}#{H['checkpoint'][:12]}", f"{P['report']}#{H['report'][:12]}"],
     "next_falsifier": FALSIFIER},
    {"event_id": "w098-rr-20260912T011540-complete", "event_type": "status", "created_at": T, "actor": A,
     "node_id": NODE, "gate": GATE, "class_id": CLASS, "status": "active", "hours": 0.4, "task_id": TASK,
     "completion_claim": True,
     "summary": ("W098-CLASSSEP-RESTORE-REPRO-01 complete as a bounded class-bound task: read-only independent reproduction "
                 "of the bound worker-098 drift recheck at the restored adjudicated bytes. Verdict REPRODUCED, 12/12 "
                 "pre-registered expectations, 6 artifacts + checkpoint hash-pinned, falsifier execable, no canonical write. "
                 "Task-completion claim only: no gate verdict, no node completion, no adoption/rollback; lead/controller must "
                 "ingest and decide."),
     "evidence_refs": REF,
     "next_falsifier": FALSIFIER},
]

for e in events:
    S.validate_event(e)

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

new = [e for e in events if e["event_id"] not in existing]
with OUTBOX.open("a") as f:
    for e in new:
        f.write(json.dumps(e, sort_keys=True) + "\n")
print(json.dumps({"emitted": len(new), "skipped_existing": len(events) - len(new),
                  "validated": len(events), "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
