#!/usr/bin/env python3
"""Finalize W026-F2B-CANDIDATE-ELECTION-CONSUMPTION-01.

Writes MANIFEST.json, SHA256SUMS, worker-local CHECKPOINT.json, a runtime/state
checkpoint, and validated outbox events. Read-only on every canonical path; the
only files written are this worker's own artifacts, its own runtime checkpoint
files, and its own outbox stream.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT = os.path.join(ROOT, "artifacts/worker-026/f2b_candidate_convergence")
CST = timezone(timedelta(hours=8))
TASK_ID = "W026-F2B-CANDIDATE-ELECTION-CONSUMPTION-01"

sys.path.insert(0, os.path.join(ROOT, "research_map"))
import schemas  # noqa: E402


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    now = datetime.now(CST).isoformat(timespec="seconds")
    report = json.load(open(os.path.join(OUT, "report.json")))
    controls = json.load(open(os.path.join(OUT, "controls.json")))

    deliverables = ["report.json", "evidence.json", "controls.json", "converge.py",
                    "REPORT.md", "run_stdout.txt"]
    hashes = {f: sha(os.path.join(OUT, f)) for f in deliverables}

    checkpoint = {
        "task_id": TASK_ID, "actor": "worker-026", "node_id": "F2b",
        "gate": "G-FORM", "class_id": "AF-SCC-C0-VAC-GEN",
        "created_at": now,
        "verdict": report["verdict"],
        "elected_hashes": report["election"]["elected_hashes"],
        "inverted_hashes": [c["sha256"] for c in report["candidates"]
                            if c["scope"] == "MINIMAL_TWO_CARRIER"
                            and c["classification"]["R3_entailment_direction"] == "INVERTED"],
        "rehearsed_by_W058": report["election"]["rehearsed_by_W058"],
        "recommended_by_W083": report["election"]["recommended_by_W083"],
        "role_intersection_empty": report["election"]["role_intersection_empty"],
        "controls": f"{controls['passed']}/{controls['total']}",
        "deliverable_hashes": hashes,
        "falsifier": report["falsifier"],
        "authority": report["authority"],
        "non_claims": report["non_claims"],
    }
    ckpt_path = os.path.join(OUT, "CHECKPOINT.json")
    json.dump(checkpoint, open(ckpt_path, "w", encoding="utf-8"), indent=1, sort_keys=True)
    checkpoint["worker_checkpoint_path"] = "artifacts/worker-026/f2b_candidate_convergence/CHECKPOINT.json"
    checkpoint["worker_checkpoint_sha256"] = sha(ckpt_path)

    manifest = {
        "task_id": TASK_ID, "actor": "worker-026", "created_at": now,
        "files": dict(hashes),
        "checkpoint": {"path": checkpoint["worker_checkpoint_path"],
                       "sha256": checkpoint["worker_checkpoint_sha256"]},
        "related_input_pins": report["pins"],
    }
    json.dump(manifest, open(os.path.join(OUT, "MANIFEST.json"), "w", encoding="utf-8"),
              indent=1, sort_keys=True)
    with open(os.path.join(OUT, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        for f in deliverables:
            fh.write(f"{hashes[f]}  {f}\n")
        fh.write(f"{checkpoint['worker_checkpoint_sha256']}  CHECKPOINT.json\n")
        fh.write(f"{sha(os.path.join(OUT, 'MANIFEST.json'))}  MANIFEST.json\n")

    # runtime/state checkpoint (worker-specific filenames only)
    state = os.path.join(ROOT, "runtime/state")
    os.makedirs(state, exist_ok=True)
    rt = os.path.join(state, "w026_f2b_candidate_election_checkpoint.json")
    json.dump(checkpoint, open(rt, "w", encoding="utf-8"), indent=1, sort_keys=True)
    with open(os.path.join(state, "w026_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"task_id": TASK_ID, "actor": "worker-026", "at": now,
                             "checkpoint": "runtime/state/w026_f2b_candidate_election_checkpoint.json",
                             "sha256": sha(rt),
                             "verdict": report["verdict"]}, sort_keys=True) + "\n")

    # outbox events
    ev = []
    base_refs = [
        f"artifacts/worker-026/f2b_candidate_convergence/report.json#{hashes['report.json'][:12]}",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
    ]
    ev.append({
        "event_id": "w026-ce-status-active-20260912", "event_type": "status",
        "created_at": now, "actor": "worker-026", "node_id": "F2b", "status": "active",
        "hours": 0.4,
        "summary": ("W026-F2B-CANDIDATE-ELECTION-CONSUMPTION-01 start: read-only "
                    "direction-aware election over the F2b rev29 two-carrier repair "
                    "candidate field plus a consumption-role map."),
        "evidence_refs": base_refs,
        "next_falsifier": report["falsifier"],
    })
    ev.append({
        "event_id": "w026-ce-claim-election-20260912", "event_type": "claim",
        "created_at": now, "actor": "worker-026", "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN", "conclusion_type": "stability_result",
        "statement": ("At FROZEN rev29 (F2b b2ab6acb2bbe) nine minimal two-carrier repair "
                      "candidates exist; eight pass R1-R4 and one (84b5d3fa29a6) is "
                      "direction-rejected; no candidate is simultaneously elected, "
                      "recommended by W083 and rehearsed by W058."),
        "assumptions": [
            "the artifact's own implication_ledger defines the allowed entailment direction",
            "bracketed/quoted mentions of the superseded denial are not assertions",
            "candidate identity is the measured sha256, never a path or label",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": base_refs + [
            "artifacts/worker-058/rev30_freeze_rehearsal/report.json#1e31bbe5e933",
            "artifacts/worker-083/f2b_candidate_adjudication/report.json#83b50c27976a",
            "artifacts/worker-080/f2b_repair_entailment_audit/report.json#f0dae0292f1d",
        ],
    })
    art_files = [
        ("report_json", "report.json", "machine-readable election report"),
        ("evidence_json", "evidence.json", "candidate/leaf/consumer evidence"),
        ("controls_json", "controls.json", "11 mutation controls"),
        ("checker", "converge.py", "deterministic read-only checker"),
        ("report_md", "REPORT.md", "human-readable report"),
        ("run_stdout", "run_stdout.txt", "verbatim run output"),
        ("checkpoint", "CHECKPOINT.json", "worker-local checkpoint"),
        ("manifest", "MANIFEST.json", "deliverable manifest"),
    ]
    for slug, fn, desc in art_files:
        p = os.path.join(OUT, fn)
        ev.append({
            "event_id": f"w026-ce-artifact-{slug}-20260912", "event_type": "artifact",
            "created_at": now, "actor": "worker-026", "node_id": "F2b",
            "artifact_type": "worker_report", "path": f"artifacts/worker-026/f2b_candidate_convergence/{fn}",
            "sha256": sha(p), "validation_status": "unverified", "summary": desc,
        })
    ev.append({
        "event_id": "w026-ce-blocker-rehearsed-candidate-20260912", "event_type": "blocker",
        "created_at": now, "actor": "worker-026", "node_id": "F2b",
        "description": ("The rev30 freeze rehearsal (W058, report 1e31bbe5e933) is bound to "
                        "candidate 84b5d3fa29a6, which this audit rejects on R3 "
                        "(inverted entailment 'H2_loc-inextendibility entails this class'); "
                        "the current W083 recommendation 1315427fbc92 is electable but "
                        "unrehearsed, and no candidate holds elected+recommended+rehearsed "
                        "roles. A rev30 freeze on the rehearsed bytes would freeze a "
                        "direction-defective repair."),
        "needed_to_unblock": ("owner elects one candidate by sha256, re-runs the rev30 "
                              "rehearsal + freeze-identity guard against that exact hash, and "
                              "records the election; independent review of the W083 "
                              "self-recommendation (author_conflict=true) is also needed."),
        "evidence_refs": base_refs + [
            "artifacts/worker-058/rev30_freeze_rehearsal/report.json#1e31bbe5e933",
            "artifacts/worker-083/f2b_candidate_adjudication/report.json#83b50c27976a",
            "artifacts/worker-080/f2b_repair_entailment_audit/report.json#f0dae0292f1d",
        ],
    })
    ev.append({
        "event_id": "w026-ce-status-done-20260912", "event_type": "status",
        "created_at": now, "actor": "worker-026", "node_id": "F2b", "status": "done",
        "hours": 0.4,
        "summary": (f"{TASK_ID} complete at worker level: one bounded class-bound task, "
                    f"11/11 controls, canonical tree untouched. Verdict "
                    f"{report['verdict']}."),
        "evidence_refs": base_refs + [
            "runtime/state/w026_f2b_candidate_election_checkpoint.json#"
            + sha(rt)[:12]],
        "next_falsifier": report["falsifier"],
    })

    outbox = os.path.join(ROOT, "comms/outbox/worker-026.jsonl")
    ok, ids = 0, set()
    with open(outbox, "a", encoding="utf-8") as fh:
        for e in ev:
            e.setdefault("class_ids", ["AF-SCC-C0-VAC-GEN"])
            e.setdefault("gate", "G-FORM")
            schemas.validate_event(e)
            assert e["event_id"] not in ids
            ids.add(e["event_id"])
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            ok += 1
    print(json.dumps({
        "events_validated": f"{ok}/{len(ev)}", "outbox": "comms/outbox/worker-026.jsonl",
        "checkpoint": "runtime/state/w026_f2b_candidate_election_checkpoint.json",
        "checkpoint_sha256": sha(rt),
        "manifest_sha256": sha(os.path.join(OUT, "MANIFEST.json")),
        "report_sha256": hashes["report.json"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
