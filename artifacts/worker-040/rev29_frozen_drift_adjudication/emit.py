#!/usr/bin/env python3
"""Emit the W040-FROZEN-REV29-DRIFT-07 events to comms/outbox/worker-040.jsonl and write the
worker checkpoint.  Every event is validated with research_map.schemas.validate_event before it is
appended.  Idempotent: an event_id already present in the outbox is skipped.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TASK_ID = "W040-FROZEN-REV29-DRIFT-07"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN"
NODE_ID = "F1,F2a,F2b"
GATE = "G-FORM"
OUTBOX = ROOT / "comms/outbox/worker-040.jsonl"
CKPT = ROOT / "runtime/state/w040_rev29_drift_checkpoint.json"
CKPT_LOG = ROOT / "runtime/state/w040_checkpoints.jsonl"
GLOBAL_LOG = ROOT / "runtime/state/checkpoint_log.jsonl"

now = datetime.now(TZ).replace(microsecond=0).isoformat()
stamp = now.replace("-", "").replace(":", "").replace("+", "")[0:15]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#{sha(p)[:12]}"


m = json.loads((TASK / "measurements.json").read_text())
r = json.loads((TASK / "report.json").read_text())
c = json.loads((TASK / "controls.json").read_text())

FALSIFIER = m["falsifier"]
EVIDENCE = [
    ref(TASK / "adjudicate.py"),
    ref(TASK / "measurements.json"),
    ref(TASK / "controls.json"),
    ref(TASK / "report.json"),
    ref(TASK / "entry_hashes.json"),
    "artifacts/formulation/FROZEN.json#" + sha(ROOT / "artifacts/formulation/FROZEN.json")[:12],
    "artifacts/formulation/VARIANT_REGISTRY.json#" + sha(ROOT / "artifacts/formulation/VARIANT_REGISTRY.json")[:12],
    "artifacts/formulation/tools/check_variant_registry.py#" + sha(ROOT / "artifacts/formulation/tools/check_variant_registry.py")[:12],
]
ARTIFACT_REFS = [ref(TASK / f) for f in ["adjudicate.py", "emit.py", "measurements.json", "controls.json", "report.json", "entry_hashes.json"]]

review = m["verdict"]
events = []


def add(ev):
    ev.setdefault("created_at", now)
    ev.setdefault("actor", "worker-040")
    ev.setdefault("class_id", CLASS_ID)
    ev.setdefault("node_id", NODE_ID)
    ev.setdefault("gate", GATE)
    ev.setdefault("task_id", TASK_ID)
    validate_event(ev)
    events.append(ev)


for fname, atype in [("adjudicate.py", "adjudication_script"),
                     ("emit.py", "adjudication_emitter"),
                     ("measurements.json", "adjudication_measurements"),
                     ("controls.json", "control_results"),
                     ("report.json", "independent_class_bound_verdict"),
                     ("entry_hashes.json", "entry_hash_record")]:
    add({"event_id": f"w040-rev29drift-20260912-artifact-{fname.replace('.', '-')}",
         "event_type": "artifact", "artifact_type": atype,
         "path": str((TASK / fname).relative_to(ROOT)), "sha256": sha(TASK / fname),
         "validation_status": "unverified", "artifact_edited": False,
         "evidence_refs": [ref(TASK / fname)], "next_falsifier": FALSIFIER,
         "summary": f"W040-FROZEN-REV29-DRIFT-07 {atype} ({sha(TASK / fname)[:12]})."})

add({"event_id": "w040-rev29drift-20260912-review-frozen",
     "event_type": "review", "target_id": review["target_id"], "reviewer": "worker-040",
     "verdict": review["verdict"], "score": review["score"], "blind_review": False,
     "hard_failures": [
         "FROZEN rev29 carries two byte-identities under one revision label (3d9e3d77fd87 -> 815e08079aef, frozen_at 00:57:26): 7 bound paths moved (5 modified, 2 added).",
         "A structured r3 reviewer binding points at the superseded manifest: reviews/F1-review-worker-018.json reviewed_sha256['artifacts/formulation/FROZEN.json']=3d9e3d77fd87 at 00:57:00, 26 s before B.",
         "The owner's 'check_variant_registry VALID' is a metalinguistic false positive for the SET direction: the checker's substring test passes only because the corrected entry quotes the old wrong direction in a bracketed note.",
     ],
     "findings": [f["statement"] for f in m["findings"]],
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER,
     "summary": review["summary"]})

add({"event_id": "w040-rev29drift-20260912-blocker-gform",
     "event_type": "blocker",
     "description": ("G-FORM r3 cannot close on FROZEN 815e08079aef while the same revision label 29 also names "
                     "3d9e3d77fd87: an A-structured reviewer verdict exists and the A->B move changed a class-relevant "
                     "assertion (AF-WCC-VAC-GEN SET strength stronger -> weaker) after the r3 window opened."),
     "needed_to_unblock": ("Controller decision: (a) publish the B bytes as rev30 with a revision/revised_at bump and a "
                           "fresh artifact event and require the r3 reviewers to re-pin at the new hash (schema bytes are "
                           "unchanged, so this is a pin re-bind), or (b) record an explicit same-revision re-freeze exception "
                           "listing the 7 changed paths and force the A-bound reviewers to re-run at B."),
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER})

add({"event_id": "w040-rev29drift-20260912-claim",
     "event_type": "claim",
     "statement": m["claim"]["statement"], "conclusion_type": "open_problem",
     "assumptions": [
         "the two A-era snapshots (worker-007 rev29 preflight, worker-074 landing guard) are faithful copies of the manifest bytes that reviewers measured at 00:55:02",
         "the B manifest on disk at adjudication time is the artifact of the 00:57:26 re-freeze (worker-019 recorded the three writes e1a8aaa394eb -> 3d9e3d77fd87 -> 815e08079aef)",
         "a bracketed correction note is not an assertion of the direction it quotes",
     ],
     "falsifier": FALSIFIER, "evidence_refs": EVIDENCE, "artifact_refs": ARTIFACT_REFS})

add({"event_id": "w040-rev29drift-20260912-status-close",
     "event_type": "status", "status": "active", "hours": 0.4,
     "summary": (f"W040-FROZEN-REV29-DRIFT-07 complete: 13/13 controls, 0 entry/exit drift, 7 changed paths measured, "
                 f"{m['reviewer_pins']['A_structured_binding_count']} A-structured r3 binding(s), sandboxed checkers exit 0, "
                 f"note-removal mutation INVALID. Verdict revise/2.5 on FROZEN 815e08079aef; blocker raised for G-FORM."),
     "claims_completion": False,
     "authority_note": "advisory worker status; no gate verdict, no node status promotion, no canonical artifact modified",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER})

# ---- append events (idempotent) ------------------------------------------------
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(errors="replace").splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            continue
written = []
with OUTBOX.open("a") as fh:
    for ev in events:
        if ev["event_id"] in existing:
            continue
        fh.write(json.dumps(ev) + "\n")
        written.append(ev["event_id"])

# ---- checkpoint -----------------------------------------------------------------
artifacts = {}
for p in sorted(TASK.rglob("*")):
    if p.is_file() and "__pycache__" not in p.parts and "sandbox" not in p.parts:
        artifacts[str(p.relative_to(ROOT))] = sha(p)
checkpoint = {
    "checkpoint_id": f"w040-rev29drift-{stamp}",
    "created_at": now,
    "task_id": TASK_ID,
    "class_id": CLASS_ID,
    "node_id": NODE_ID,
    "gate": GATE,
    "assignment_taken": {
        "kind": "class-bound independent adjudication from the open G-FORM queue; no card in comms/inbox/worker-040.jsonl",
        "task": "adjudicate CF-27: the FROZEN rev29 manifest moved 3d9e3d77fd87 -> 815e08079aef under one revision label inside the r3 review window",
        "why_not_duplicative": ("CF-27 is recorded-for-review-round only; prior workers recorded the churn (001/019/029/085/089/066) "
                                "but no artifact measures the 7-path content delta, the class-assertion flip, the structured review-pin split, "
                                "or the checker metalinguistic false positive. read-only, re-runnable, hash-bound."),
    },
    "checks": {
        "controls_passed": f"{c['passed']}/{c['total']}",
        "changed_paths": m["path_delta"]["changed_count"],
        "modified": m["path_delta"]["modified"],
        "added": m["path_delta"]["added"],
        "semantic_write": "AF-WCC-VAC-GEN SET strength: strictly stronger -> strictly weaker (delta + registry)",
        "A_structured_review_bindings": m["reviewer_pins"]["A_structured_binding_count"],
        "revision_held": m["revision_discipline"]["revision_B"],
        "structural_rev30_events": len(m["revision_discipline"]["rev30_or_supersedes_hits"]),
        "checkers_sandboxed": {k: v["exit"] for k, v in m["checker_runs"].items()},
        "note_removal_mutation_exit": m["checker_mutation_after_note_removal"]["exit"],
        "entry_exit_drift": m["drift_watched"],
        "verdict": review["verdict"],
        "score": review["score"],
    },
    "artifacts": artifacts,
    "events_emitted": written,
    "exit": "clean",
}
CKPT.write_text(json.dumps(checkpoint, indent=2) + "\n")
with CKPT_LOG.open("a") as fh:
    fh.write(json.dumps(checkpoint) + "\n")
with GLOBAL_LOG.open("a") as fh:
    fh.write(json.dumps({"agent": "worker-040", "checkpoint": str(CKPT.relative_to(ROOT)),
                         "claims_completion": False, "state": "complete", "task_id": TASK_ID,
                         "time": now, "verdict": review["verdict"]}) + "\n")

print(json.dumps({"events_written": written, "checkpoint": str(CKPT.relative_to(ROOT)),
                  "artifacts_hashed": len(artifacts), "controls": f"{c['passed']}/{c['total']}"}, indent=1))
