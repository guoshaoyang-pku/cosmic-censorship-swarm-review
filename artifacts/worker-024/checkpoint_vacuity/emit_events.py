#!/usr/bin/env python3
"""Emit W024-CHECKPOINT-VACUITY-01 events to comms/outbox/worker-024.jsonl (idempotent).

Validates every event with research_map/schemas.validate_event before writing; appends only
event_ids not already present in the outbox file. Does not ingest (the controller owns that).

Usage: python3 artifacts/worker-024/checkpoint_vacuity/emit_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ARTIFACT = Path(__file__).resolve().parent
REPO = ARTIFACT.parents[2]
OUTBOX = REPO / "comms" / "outbox" / "worker-024.jsonl"
CST = timezone(timedelta(hours=8))
STAMP = "w024-ckv-20260912T0105"
TASK = "W024-CHECKPOINT-VACUITY-01"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_ID = ";".join(CLASSES)

sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    report = json.loads((ARTIFACT / "report.json").read_text())
    sealed = json.loads((ARTIFACT / "exit_hashes.json").read_text())
    art = {
        "report.json": "checkpoint_vacuity_audit_report",
        "README.md": "audit_readme",
        "drive_vacuity.py": "reproducible_audit_driver",
        "proposed_fail_closed_patch.diff": "proposed_fail_closed_patch",
        "patched/checkpoint.patched.py": "patched_instrument_copy",
        "exit_hashes.json": "entry_exit_hash_pins",
    }
    events = []
    for rel, kind in art.items():
        p = ARTIFACT / rel
        h = sha(p)
        if rel != "exit_hashes.json" and h != sealed["artifact_files"][rel]["sha256"]:
            print(f"REFUSING: {rel} hash {h[:12]} != sealed {sealed['artifact_files'][rel]['sha256'][:12]}")
            return 2
        events.append({
            "event_id": f"{STAMP}-art-{rel.replace('/', '_')}",
            "event_type": "artifact", "created_at": now(), "actor": "worker-024",
            "node_id": "A1", "gate": "G-AUDIT", "task_id": TASK,
            "class_id": CLASS_ID, "class_ids": CLASSES,
            "artifact_type": kind, "path": f"artifacts/worker-024/checkpoint_vacuity/{rel}",
            "sha256": h, "validation_status": "unverified",
            "summary": {
                "report.json": ("Vacuity/fail-open matrix for research_map/checkpoint.py#152b40ead267 "
                                "against map snapshot #3d45be5969ec: 20 runs, 73/73 assertions held; "
                                "6 vacuous rc-0 structures (missing event stream, unreachable classsep corpus, "
                                "stripped governance, empty registry clobber, INVALID map still recorded, "
                                "same-second record collision); patched matrix closes P1-P7 at rc 1, P0 healthy rc 0."),
                "README.md": "Method, pins, per-case table, mechanisms, patch, reproduction, falsifier, limits.",
                "drive_vacuity.py": ("Sandboxed driver: pinned subset build (ROOT-relative), 20 cases, frozen "
                                     "assertions, patched matrix, pin-drift exit 2."),
                "proposed_fail_closed_patch.diff": ("Proposal only (not applied): non-vacuity block + REASON lines + "
                                                    "exit 1, registry no-clobber, --dry-run, microsecond checkpoint ids. "
                                                    "Verified on sandbox copies."),
                "patched/checkpoint.patched.py": "Patched copy verified on sandbox copies; pin b1ca1e82e943.",
                "exit_hashes.json": "Entry/exit canonical hashes, 51-file artifact rollup, live drift flags.",
            }[rel],
        })
    evidence = [
        f"artifacts/worker-024/checkpoint_vacuity/report.json#{sha(ARTIFACT / 'report.json')[:12]}",
        f"artifacts/worker-024/checkpoint_vacuity/README.md#{sha(ARTIFACT / 'README.md')[:12]}",
        f"artifacts/worker-024/checkpoint_vacuity/drive_vacuity.py#{sha(ARTIFACT / 'drive_vacuity.py')[:12]}",
        f"artifacts/worker-024/checkpoint_vacuity/proposed_fail_closed_patch.diff#{sha(ARTIFACT / 'proposed_fail_closed_patch.diff')[:12]}",
        f"artifacts/worker-024/checkpoint_vacuity/patched/checkpoint.patched.py#{report['patched_hash'][:12]}",
        f"artifacts/worker-024/checkpoint_vacuity/exit_hashes.json#{sha(ARTIFACT / 'exit_hashes.json')[:12]}",
        "research_map/checkpoint.py#152b40ead267",
        "research_map/comms.py#7e905012ad6b",
        "research_map/validate_map.py#0bf3eb3ec4ee",
        "research_map/audit_evidence.py#36cf433a90b6",
        "research_map/class_separation.py#c266dbceca87",
        "artifacts/worker-024/validate_map_vacuity/report.json#65dd3500c68b",
        "artifacts/worker-024/classsep_runner_vacuity/report.json#d090cd20c961",
    ]
    events.append({
        "event_id": f"{STAMP}-claim-checkpoint-vacuity",
        "event_type": "claim", "created_at": now(), "actor": "worker-024",
        "node_id": "A1", "gate": "G-AUDIT", "task_id": TASK,
        "class_id": CLASS_ID, "class_ids": CLASSES,
        "conclusion_type": "formal_model",
        "statement": (
            "Instrument claim (not a class-semantics claim): at research_map/checkpoint.py sha256 "
            "152b40ead267173067acc7fe23df569a30aa0d1fb53b5aadbd786c0035afcac3 (sandbox-pinned sub-instruments "
            "comms.py#7e905012ad6b, validate_map.py#0bf3eb3ec4ee, audit_evidence.py#36cf433a90b6, "
            "class_separation.py#c266dbceca87 frozen, classsep_regression.py#9f1cf9c336be, map snapshot "
            "#3d45be5969ec, events head-200 #3853ef1e72f1), the 15-minute checkpoint record is presence-driven and "
            "fails open on six stripped structures, each reproduced end-to-end in a byte-identical sandbox with "
            "exit code 0 and a written current_checkpoint.json: (C1) research_map/events.jsonl absent -> "
            "event_stream_errors==[] and events_total==0 while map_validator==VALID; the checkpoint's own "
            "comms.ingest re-creates the file empty (comms.py:321-322), so absence is masked even to a file-presence "
            "check; (C4) the 27-fixture corpus's fixtures/ directory unreachable (results.json kept) -> "
            "classsep_regression {tp:0,fn:0,tn:0,fp:0,verdict:PASS,corpus_size:0} embedded as PASS (inherits "
            "W024-CLASSSEP-RUNNER-VACUITY-01); (C5) gates=[] plus numerics_lock/frozen_artifacts/claims removed -> "
            "map_validator==VALID with gates {} and numerics_lock {} (inherits W024-VALIDATE-MAP-VACUITY-01); (C6) all "
            "registry roots absent -> runtime/state/artifact_hashes.json overwritten from a 417-entry registry to "
            "{\"hashes\":{},\"registry\":{}} (PROTOCOL rule-2 registry clobber); (C7) duplicate node id -> "
            "map_validator==INVALID recorded, record and log line still written, rc 0; (C8) two runs in one second "
            "(stamp fixed) -> one ckpt-*.json file holding only the second label while checkpoint_log.jsonl keeps both "
            "lines. The process exits 0 in every non-crashing case, including the INVALID map; only a JSON-corrupt map "
            "(N1) or an absent corpus results.json (N2) crash with rc 1 and no record. Controls: healthy C0 rc 0 "
            "(corpus 27/PASS, 423-entry registry, 200 events, 5 gates, lock present); corrupt-but-present stream C2 "
            "records 1 error yet still exits 0; missing outbox C3 exits 0. A proposed fail-closed patch "
            "(patched/checkpoint.patched.py#b1ca1e82e943, proposal only, verified on sandbox copies) closes the six "
            "vacuous cases at rc 1 with REASON lines while leaving P0 healthy at rc 0 and preserving a previous "
            "non-empty registry when the fresh scan is empty. Consequence for G-AUDIT/G-F0/G-FORM: a 'checkpoint "
            "VALID / 0 hard failures / classsep PASS' quote certifies only the structures present in the tree that was "
            "read; the checkpoint process cannot serve as a guard because it exits 0 on the failures it records. No "
            "gate verdict is asserted."
        ),
        "assumptions": [
            "The audited object is the checkpoint pipeline at the pinned revisions; live research_map/class_separation.py moved c266dbceca87 -> a8c04fc31e4a at 00:56 during the detector repair, so the sandbox uses the frozen c266 revision required by the map snapshot's active frozen_artifacts, and the classsep numbers bind to c266 only.",
            "The event-stream snapshot is the first 200 accepted lines of research_map/events.jsonl taken at 00:58; registry trees are measured live and recorded as counts/rollups, so the claim depends only on non-emptiness and clobbering, not on the exact file list.",
            "C8's collision is demonstrated deterministically with a fixed stamp(); the patched case uses real microsecond stamps. Both are recorded as mechanism-level evidence.",
            "Applying proposed_fail_closed_patch.diff is an owner decision; patched verdicts come from copies under this artifact directory and no canonical file was written by this audit.",
            "The C4/C5 fail-open behavior of class_separation.regression()/validate_map.py is the independently measured W024 series finding re-exercised through the checkpoint, not re-adjudicated here.",
        ],
        "falsifier": (
            "Re-run artifacts/worker-024/checkpoint_vacuity/drive_vacuity.py at the pinned hashes (a sandbox pin "
            "mismatch exits 2). FALSIFIED if any of C1/C4/C5/C6/C7/C8 returns rc != 0 or deviates from the observed "
            "record (absent event stream produces a non-empty event_stream_errors; unreachable corpus yields non-PASS "
            "or corpus_size>0; governance-stripped map is INVALID; empty registry scan leaves the previous registry "
            "intact; INVALID map is not written as the current record; same-second runs produce two files), or if any "
            "of C0/C2/C3/N1/N2 deviates, or if the patched matrix no longer closes P1-P7 with P0 at rc 0 and P3's "
            "previous registry intact. Any later edit of checkpoint.py or a pinned sub-instrument voids the claim for "
            "the edited bytes."
        ),
        "evidence_refs": evidence,
        "artifact_refs": [e.split("#")[0] for e in evidence[:6]],
    })
    events.append({
        "event_id": f"{STAMP}-status-checkpoint-vacuity",
        "event_type": "status", "created_at": now(), "actor": "worker-024",
        "node_id": "A1", "gate": "G-AUDIT", "task_id": TASK,
        "class_id": CLASS_ID, "class_ids": CLASSES,
        "status": "active", "hours": 0.6,
        "authority_note": "worker event: no gate verdict, no validation_status=passed, no node status=done",
        "summary": (
            "W024-CHECKPOINT-VACUITY-01 complete: artifacts on disk and hash-pinned (51 files, rollup in "
            "exit_hashes.json). Result: research_map/checkpoint.py#152b40ead267 fails open on six stripped structures "
            "at rc 0 (missing event stream, unreachable classsep corpus, stripped governance, empty-registry clobber, "
            "INVALID map still recorded, same-second record collision) while only hard crashes are non-zero; controls "
            "behave; a proposed fail-closed patch (proposal only, verified on sandbox copies) closes all six and "
            "preserves the no-clobber property. Worker completion claim only: no gate verdict, no node transition."
        ),
        "evidence_refs": evidence,
        "next_falsifier": (
            "Owner adopts proposed_fail_closed_patch.diff or an equivalent non-vacuity block; then a re-run must fail "
            "C1-C8 at rc 1 with REASON lines and keep the healthy control at rc 0 while preserving a previous "
            "non-empty registry on an empty scan. If checkpoint.py is rebuilt, re-run drive_vacuity.py at the new "
            "hash and expect all 73 checks to hold with updated pins."
        ),
    })
    for e in events:
        validate_event(e)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except (ValueError, KeyError):
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    if new:
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"events total={len(events)} new={len(new)} skipped={len(events) - len(new)}")
    for e in new:
        print(f"  + {e['event_type']:<8} {e['event_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
