#!/usr/bin/env python3
"""Emit the W098 drift-recheck (pass 2) events. Same self-check as the pass-1 emitter:
no string this worker writes may add a CLASSSEP hard finding under the live detector."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

OUT = ROOT / "comms/outbox/worker-098.jsonl"
TS = "2026-09-12T00:54:00+08:00"
BASE = "w098-cps-20260912T0054"
ART = "artifacts/worker-098/classsep_prose_shadow"
CK1 = "runtime/state/w098_classsep_prose_shadow_checkpoint_1.json"
CK2 = "runtime/state/w098_classsep_prose_shadow_checkpoint_2.json"
LIVE = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
FALSIFIER = ("Re-run artifacts/worker-098/classsep_prose_shadow/drift_recheck.py: falsified if the live detector clears "
             "all 4 declared false-positive probes and reaches 0 hard findings on the live map while the 6 genuine-merge "
             "probes still fire; or if research_map/class_separation.py moves off a8c04fc31e4a or the live map moves off "
             "ed28b714464e before the next measurement.")
CIDS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
REF = [f"{ART}/drift_recheck.json#ffabb753313f", f"{ART}/report.json#c27f2a0399d2",
       f"research_map/class_separation.py#{LIVE[:12]}", CK1, CK2]

events = [
    {"event_id": f"{BASE}-drift-notice", "event_type": "status", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "status": "active", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": ("Moving-target correction: the canonical detector moved c266dbceca87 -> a8c04fc31e4a at 00:52:00 (3 added lines, "
                 "0 removed: a context-scoped skip for false-positive / non-merge / not-a-merge / no-genuine-composite-merge / "
                 "detector-finding / quoted-detector phrasing). This is NOT the lead's proposal; no sentence-level skip was applied. "
                 "My pass-1 verdict (revise 3.0 at c266dbceca87) is therefore ADVISORY ONLY. Pass 2 re-ran the same battery against "
                 "the live detector: corpus PASS, TP probes 2/2 intact, 0/6 over-suppression (safer than the proposal), but only "
                 "1/4 declared false-positive probes clean, growth probes still 3/3, and the hard count 17 -> 13 on the frozen map "
                 "snapshot (20 -> 16 on the live map ed28b714464e, 292 claims). The applied fix is safe but insufficient."),
     "evidence_refs": REF, "next_falsifier": FALSIFIER},
    {"event_id": f"{BASE}-art-drift-tool", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "drift_recheck_instrument", "path": f"{ART}/drift_recheck.py",
     "sha256": "7ed06e7fc1b1fa6045810040a7a53e8305ca76d93837d3e05db58c2c07b70dec", "validation_status": "unverified",
     "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Re-runs corpus + probes + map + growth against the live detector; read-only, deterministic, no network.",
     "evidence_refs": [f"{ART}/raw/drift_recheck.json#ffabb753313f"]},
    {"event_id": f"{BASE}-art-drift-report", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "artifact_type": "drift_recheck_report",
     "path": f"{ART}/drift_recheck.json", "sha256": "ffabb753313fdf76fe5df3760ed0a0f52eb5c8539b6e0e9d6b0800fbfe3a6395",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Diff of the applied change + per-battery pass-2 measurements at a8c04fc31e4a.",
     "evidence_refs": REF},
    {"event_id": f"{BASE}-review-drift", "event_type": "review", "created_at": TS, "actor": "worker-098",
     "reviewer": "worker-098", "target_id": "research_map/class_separation.py", "node_id": "A1", "gate": "G-AUDIT",
     "class_id": CIDS, "verdict": "revise", "score": 3.0, "reviewed_sha256": LIVE,
     "counts_as_full_schema_verdict": False, "counts_as_independent": True,
     "hard_failures": [
         "3 of the proposal's 4 declared false-positive probes still fire under the applied fix (only the non-merge phrasing is covered)",
         "the live hard count is 16, not 0; growth probes still add 3 findings across 3 detector-discussion statements"],
     "findings": [
         "safe: 0/6 over-suppression, corpus PASS 17/17 + 10/10, both true-positive probes intact",
         "residual shapes: negative cue spanning the composite without the literal word 'genuine'; a split sentence where a merge-assert word suppresses the split exemption; mention phrasing with no covered cue",
         "the applied fix clears 4 findings (17 -> 13 on the frozen snapshot, 20 -> 16 live), so it is a strict improvement but not a closure"],
     "artifact_refs": [f"{ART}/drift_recheck.json#ffabb753313f"], "evidence_refs": REF},
    {"event_id": f"{BASE}-blocker-drift", "event_type": "blocker", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "description": ("G-AUDIT remains blocked after the controller's applied detector change a8c04fc31e4a: 16 live hard findings, "
                     "3/4 declared false-positive probes still firing, and the growth mechanism (a claim about the detector adds "
                     "findings) untouched. The applied fix is safe but insufficient."),
     "needed_to_unblock": ("Extend the skip predicates to the three residual mention shapes: a negative cue spanning the composite "
                           "without 'genuine'; a split/supersede cue that should win even when a merge-assert word is present; and the "
                           "quoted/discussed forms. Then re-run drift_recheck.py and require 4/4 declared FP probes clean, growth 0, and "
                           "0 hard findings on the live map while the 6 genuine-merge probes still fire and the corpus stays PASS."),
     "evidence_refs": REF},
    {"event_id": f"{BASE}-checkpoint2", "event_type": "status", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "status": "active", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": ("Worker-local checkpoint 2 written for the drift pass: pass-1 superseded, pass-2 measurements at a8c04fc31e4a, "
                 "3 new artifacts pinned, controller runtime checkpoint untouched."),
     "artifact_refs": [CK2, f"{ART}/drift_recheck.json#ffabb753313f"], "evidence_refs": REF},
    {"event_id": f"{BASE}-complete2", "event_type": "status", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "status": "active", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "completion_claim": True, "hours": 0.4,
     "summary": ("W098-CLASSSEP-PROSE-SHADOW-01 closed with two passes: pass 1 (proposal shadow at c266dbceca87, advisory) and pass 2 "
                 "(live detector drift recheck at a8c04fc31e4a). Pass-2 verdict revise 3.0: the applied fix is safe but leaves 16 live "
                 "hard findings and 3/4 declared false-positive probes firing. 15 artifacts hash-pinned across both passes, two worker "
                 "checkpoints written. Task-completion claim only; no node completion, no gate verdict."),
     "artifact_refs": [f"{ART}/report.json#c27f2a0399d2", f"{ART}/drift_recheck.json#ffabb753313f", CK1, CK2],
     "evidence_refs": REF, "next_falsifier": FALSIFIER},
]

problems = []
for ev in events:
    for k, v in ev.items():
        vals = v if isinstance(v, list) else [v]
        for i, x in enumerate(vals):
            if isinstance(x, str):
                out: list = []
                cs._scan_composite(x, f"{ev['event_id']}.{k}[{i}]", out, mode="prose")
                problems += [p for p in out if not p.startswith("CLASSSEP-SOFT:")]
    if ev["event_type"] == "claim":
        problems += [p for p in cs.findings(ev, ev["event_id"], mode="prose") if not p.startswith("CLASSSEP-SOFT:")]
required = {
    "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type", "path", "sha256", "validation_status"],
    "review": ["event_id", "event_type", "created_at", "actor", "target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
}
missing = [f"{ev['event_id']}: {k}" for ev in events for k in required.get(ev["event_type"], ["event_id", "event_type", "created_at", "actor"]) if k not in ev]
if problems or missing:
    print("SELF-CHECK FAILED", problems, missing)
    sys.exit(2)
with OUT.open("a") as fh:
    for ev in events:
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
print(f"appended {len(events)} drift events to {OUT}")
print([e["event_id"] for e in events])
