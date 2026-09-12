#!/usr/bin/env python3
"""W095-HOLD-BIND-INTEGRITY-03 -- build verdict.json, checkpoint, and append outbox events.

Run once after measure_hold.py:
    python3 artifacts/worker-095/freeze_hold_binding_integrity/build_and_emit.py

Safety: the outbox is opened in append mode only, and events whose event_id is already
present are skipped, so re-running cannot truncate or duplicate the log.
"""
import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence" / "raw"
OUTBOX = ROOT / "comms/outbox/worker-095.jsonl"
STATE = ROOT / "runtime/state"
TS = time.strftime("%Y%m%dT%H%M%S")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")

TASK_ID = "W095-HOLD-BIND-INTEGRITY-03"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"
F2B_SHA = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
FROZEN_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"


def sha12(p):
    h = hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    return h, h[:12]


def ev(path):
    full, short = sha12(path)
    return f"{path}#{short}", full


report = json.loads((RAW / "hold_probe_report.json").read_text())
f2b = json.loads((RAW / "f2b_and_frozen_slice.json").read_text())
checks = report["checks"]
failed = [c["id"] for c in checks if not c["pass"]]

probe_path = "artifacts/worker-095/freeze_hold_binding_integrity/measure_hold.py"
probe_sha = sha12(probe_path)[0]

evidence_paths = [
    probe_path,
    "artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/hold_probe_report.json",
    "artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/held_path_hashes.json",
    "artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/event_stream_slice.json",
    "artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/map_and_registry.json",
    "artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/f2b_and_frozen_slice.json",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "research_map/research_map.json",
    "research_map/events.jsonl",
    "runtime/state/artifact_hashes.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
]
evidence_refs = [ev(p)[0] for p in evidence_paths]

H6 = [c for c in checks if c["id"] == "H6-NO-NEWER-STALE-EVENT"][0]
shadow_summary = {
    d["path"]: [f'{s["sha256"]}@{s["created_at"]}' for s in d["shadowing_stale_events"]]
    for d in H6["detail"] if d["shadowing_stale_events"]
}

verdict_doc = {
    "artifact_id": TASK_ID,
    "artifact_type": "hold_binding_integrity_verdict",
    "actor": "worker-095",
    "created_at": NOW,
    "task_id": TASK_ID,
    "supersedes": {
        "task_id": "W095-F2B-BIND-INTEGRITY-02",
        "reviewed_sha256": F2B_SHA,
        "note": "successor scope: astra-life04 freeze-hold verification at FROZEN rev28; "
                "does not re-review class semantics",
    },
    "class_id": CLASS_ID,
    "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
    "node_id": NODE,
    "node_scope": "F0,F1,F2a,F2b",
    "gate": GATE,
    "reviewed_revision": 12,
    "reviewed_sha256": F2B_SHA,
    "final_sha256": F2B_SHA,
    "frozen_revision_reviewed": 28,
    "counts_as_full_schema_verdict": False,
    "no_completion_claim": True,
    "authority_note": "worker events cannot set node status done, validation_status passed, or a gate verdict; "
                      "this is a binding/publication-integrity receipt, not a semantic content accept",
    "verdict": "revise",
    "score_0_5": 3,
    "checks": checks,
    "findings": report["findings"],
    "hard_failures": ["F-EVENT-1"],
    "carried_findings": ["F-EVID-1 (major, unchanged from W095-F2B-BIND-INTEGRITY-02)"],
    "task_falsifier": "A re-probe in which (a) the newest-by-created_at artifact event for every one of the five "
                      "held paths carries the FROZEN rev28 pin with no future-dated stale event shadowing it, "
                      "(b) all five held paths still measure their rev28 pins with zero drift, and (c) F2b's "
                      "declared consistency-evidence hash resolves on its declared canonical path would falsify "
                      "this receipt's revise verdict.",
    "event_shadow_detail": shadow_summary,
    "f2b_intra_bindings": f2b["f2b_f0_binding"],
    "reproduce_command": "python3 artifacts/worker-095/freeze_hold_binding_integrity/measure_hold.py",
    "probe": {"path": probe_path, "sha256": probe_sha},
    "evidence_refs": evidence_refs,
    "summary": {
        "held_paths": 5,
        "checks": len(checks),
        "passed": sum(1 for c in checks if c["pass"]),
        "failed": failed,
        "hold_byte_integrity": "confirmed",
        "hold_event_hygiene": "falsified (stale rev11/rev4 events sort newer by created_at)",
        "f2b_intra_binding": "f0_binding + both pointers resolve; declared consistency evidence hash 675a99d0 "
                             "does not resolve on its declared canonical path (measured 9e335e9ba1bf, the "
                             "FROZEN rev28 pin) -- carried finding",
        "counts_as_full_schema_verdict": False,
    },
    "next_falsifier": "Any of: a held path byte changing; a new artifact event for a held path with a non-pin "
                      "sha256; a created_at-sorted resolution choosing a stale event; or a re-probe in which the "
                      "F2b canonical consistency-evidence bytes carry the declared 675a99d0 hash.",
    "stop_rule": "one class-bound receipt + checkpoint; no canonical artifact edit, no gate verdict, no node completion",
}
(HERE / "verdict.json").write_text(json.dumps(verdict_doc, indent=2) + "\n")
verdict_sha = sha12("artifacts/worker-095/freeze_hold_binding_integrity/verdict.json")[0]

checkpoint = {
    "worker": "worker-095",
    "task_id": TASK_ID,
    "checkpoint_at": NOW,
    "class_id": CLASS_ID,
    "node_id": NODE,
    "gate": GATE,
    "reviewed_revision": 12,
    "reviewed_sha256": F2B_SHA,
    "frozen_revision_reviewed": 28,
    "artifact": "artifacts/worker-095/freeze_hold_binding_integrity/verdict.json",
    "artifact_sha256": verdict_sha,
    "evidence_dir": "artifacts/worker-095/freeze_hold_binding_integrity/evidence/raw/",
    "probe": {"path": probe_path, "sha256": probe_sha},
    "verdict": "revise",
    "score_0_5": 3,
    "counts_as_full_schema_verdict": False,
    "next_falsifier": verdict_doc["next_falsifier"],
}
ck_name = f"w095_hold_binding_integrity_checkpoint_{TS}.json"
(STATE / ck_name).write_text(json.dumps(checkpoint, indent=2) + "\n")
with open(STATE / "w095_hold_binding_integrity_checkpoints.jsonl", "a") as fh:
    fh.write(json.dumps({k: checkpoint[k] for k in (
        "worker", "task_id", "checkpoint_at", "class_id", "node_id", "gate", "reviewed_revision",
        "reviewed_sha256", "frozen_revision_reviewed", "artifact", "artifact_sha256", "probe",
        "verdict", "score_0_5", "counts_as_full_schema_verdict", "next_falsifier")}) + "\n")
latest = {
    "worker": "worker-095", "task_id": TASK_ID, "checkpoint_at": NOW, "verdict": "revise",
    "path": f"runtime/state/{ck_name}", "artifact_sha256": verdict_sha,
    "reviewed_sha256": F2B_SHA, "next_falsifier": verdict_doc["next_falsifier"],
}
(STATE / "w095_latest_checkpoint.json").write_text(json.dumps(latest, indent=2) + "\n")

# ---- outbox events (append-only, idempotent by event_id) ----------------------
base = f"w095-hold-{TS}"
events = [
    {
        "event_id": f"{base}-task-claim", "event_type": "status", "actor": "worker-095",
        "created_at": NOW, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID,
        "status": "active", "hours": 0.4,
        "summary": "No assignment card exists in comms/inbox for worker-095 (fleet 2026-09-12T00:40). Taking ONE "
                   "bounded class-bound task, W095-HOLD-BIND-INTEGRITY-03: independently verify astra-life04-"
                   "freeze-hold's publication/binding acceptance at FROZEN rev28 for the five held canonical "
                   "paths, anchored on AF-SCC-C0-VAC-GEN / F2b. Tests the card's own falsifier: any byte change "
                   "after the pin events, a FROZEN pin that stops matching measured bytes, or a declared hash "
                   "left at rev11. Does not duplicate the -01/-02 F2b receipts (new scope: hold state, map "
                   "declarations, event coverage, timestamp hygiene, zero drift) and is not a semantic review.",
        "evidence_refs": evidence_refs[:6],
        "next_falsifier": verdict_doc["task_falsifier"],
    },
    {
        "event_id": f"{base}-artifact-verdict", "event_type": "artifact", "actor": "worker-095",
        "created_at": NOW, "node_id": NODE, "class_id": CLASS_ID,
        "artifact_type": "hold_binding_integrity_verdict",
        "path": "artifacts/worker-095/freeze_hold_binding_integrity/verdict.json",
        "sha256": verdict_sha, "validation_status": "unverified",
        "reviewed_revision": 12, "reviewed_sha256": F2B_SHA, "frozen_revision_reviewed": 28,
        "companion_script": {"path": probe_path, "sha256": probe_sha},
        "evidence_refs": evidence_refs,
    },
    {
        "event_id": f"{base}-review-binding", "event_type": "review", "actor": "worker-095",
        "created_at": NOW, "node_id": NODE, "class_id": CLASS_ID,
        "target_id": NODE, "target_path": "schemas/af_scc_c0_vacuum.yaml",
        "reviewer": "worker-095", "verdict": "revise", "score": 3,
        "reviewed_sha256": F2B_SHA, "frozen_revision_reviewed": 28,
        "counts_as_full_schema_verdict": False,
        "summary": "Freeze-hold receipt on one class at one revision: 6/8 checks pass. HOLD BYTE INTEGRITY "
                   "CONFIRMED at FROZEN rev28 (five held paths measure their pins two passes with zero drift; no "
                   "post-pin-event writes; FROZEN.json bytes match its newest event; map declarations and the "
                   "runtime registry agree; newest-ingested artifact event carries the pin for all five paths). "
                   "Revise verdict rests on event-stream hygiene: stale rev11/rev4 artifact events carry "
                   "created_at 00:44:00/00:45:00/01:15:00, later than the 00:35:52 pin events, so a "
                   "created_at-sorted consumer binds superseded hashes -- the assignment falsifier 'a declared "
                   "hash left at rev11' fires in the accepted stream even though the map's current declarations "
                   "are correct. Carried: F-EVID-1 unchanged (F2b declares consistency evidence 675a99d0 while "
                   "the canonical path measures the FROZEN pin 9e335e9ba1bf).",
        "hard_failures": ["F-EVENT-1"],
        "findings": report["findings"],
        "evidence_refs": evidence_refs,
    },
    {
        "event_id": f"{base}-blocker-event-shadow", "event_type": "blocker", "actor": "worker-095",
        "created_at": NOW, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID,
        "description": "astra-life04-freeze-hold event-stream falsifier: for four of the five held paths "
                       "(F1/F2a/F2b and canonical F0), the newest artifact events by agent-reported created_at "
                       "are stale submissions (F1 9a8bd4c96800, F2a b6123750b37d, F2b 1bb78ce9b357/cb897b29db12/"
                       "e6b1af2bd692, F0 276009f4f63d) with created_at 00:44:00-01:15:00, which sort after the "
                       "rev12/rev5 pin events at 00:35:52. Measured bytes and map declarations are correct, so "
                       "the hold itself is intact; the hazard is resolution-by-created_at or by stream reading. "
                       "Root cause: machine timestamps emitted ahead of wall clock (self-reported by the "
                       "formulation lead) plus append-only history that cannot be rewritten.",
        "needed_to_unblock": "Controller-side event resolution guard: rank artifact events by _received_at/ingest "
                             "order (or reject created_at > _received_at) when computing 'latest' for a path, "
                             "and/or emit tombstone/supersede events for the stale F1/F2a/F2b/F0 submissions so "
                             "the pin events are unambiguous. No canonical byte edit; the hold stays in force.",
        "evidence_refs": [evidence_refs[1], evidence_refs[2], evidence_refs[3], evidence_refs[8],
                          ev("schemas/af_scc_c0_vacuum.yaml")[0], ev("artifacts/formulation/FROZEN.json")[0]],
    },
    {
        "event_id": f"{base}-task-receipt-complete", "event_type": "status", "actor": "worker-095",
        "created_at": NOW, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID,
        "status": "active", "hours": 0.5,
        "summary": "W095-HOLD-BIND-INTEGRITY-03 worker-level receipt complete; node status deliberately "
                   "unchanged (worker events cannot set status=done, validation_status=passed, or a gate "
                   "verdict). verdict=revise at F2b rev12 55d0a1ea9bda / FROZEN rev28; reproducible probe + "
                   "5 raw evidence files + checkpoint written. counts_as_full_schema_verdict=false.",
        "evidence_refs": evidence_refs,
        "next_falsifier": verdict_doc["task_falsifier"],
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        m = re.search(r'"event_id":\s*"([^"]+)"', line)
        if m:
            existing.add(m.group(1))
with open(OUTBOX, "a") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e) + "\n")

print(json.dumps({"verdict_sha256": verdict_sha, "probe_sha256": probe_sha, "checkpoint": ck_name,
                  "events_appended": [e["event_id"] for e in events if e["event_id"] not in existing],
                  "events_skipped": [e["event_id"] for e in events if e["event_id"] in existing]}, indent=2))
