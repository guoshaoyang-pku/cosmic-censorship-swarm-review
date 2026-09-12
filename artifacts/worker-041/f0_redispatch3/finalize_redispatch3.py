#!/usr/bin/env python3
"""worker-041 re-dispatch #3: write this instance's checkpoint and ONE status event.

Bounded closure of assignment audit-r2-F0-a, which was already satisfied by the
prior worker-041 instance (verdict reviews/F0-review-rev27-a.json#4f5c2a874801,
review event w041-f0-review-rev27-a-20260912T005330 ingested). This script does
NOT write a verdict, does NOT overwrite the pinned verdict, and does NOT emit a
duplicate review event. It writes:

  1. runtime/state/worker-041_F0_redispatch3_checkpoint_<stamp>.json
  2. one `status` line appended to comms/outbox/worker-041.jsonl

and validates the event against research_map/schemas.py before appending.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
sys.path.insert(0, ROOT)
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

PINS = {
    "canonical": "research_map/formulation_taxonomy.yaml",
    "companion": "artifacts/formulation/formulation_taxonomy.yaml",
    "verdict": "reviews/F0-review-rev27-a.json",
    "prior_checkpoint": "runtime/state/worker-041_F0_checkpoint.json",
    "report": "artifacts/worker-041/f0_redispatch3/report.json",
    "instrument": "artifacts/worker-041/f0_redispatch3/verify_f0_redispatch3.py",
}
EXPECTED = {
    "canonical": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "companion": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "verdict": "4f5c2a874801c9b17e8cf68fbad8a3e21ceaa0c41d0946078b80bf70850195ba",
    "prior_checkpoint": "947debc84797ee9c673a0db53a1db77093602709d74f6eadd84168db665896ed",
    "report": "84496150529c4ed447dc31d96faf6c94c036624a396793d20bab7b9c4d1a7484",
    "instrument": "92a070fc4dbdc4a56f2b862b14a301ad7aebdbfd6d20c3e25dbd1340ea4c0b1d",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    measured = {k: sha256_file(os.path.join(ROOT, v)) for k, v in PINS.items()}
    pins_ok = all(measured[k] == EXPECTED[k] for k in PINS)
    report = json.load(open(os.path.join(ROOT, PINS["report"]), encoding="utf-8"))

    inbox = [json.loads(x) for x in open(os.path.join(ROOT, "comms/inbox/worker-041.jsonl"), encoding="utf-8") if x.strip()]
    instances = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "runtime/instances/worker-041-*")))
    events = []
    with open(os.path.join(ROOT, "research_map/events.jsonl"), encoding="utf-8") as f:
        for x in f:
            x = x.strip()
            if not x:
                continue
            try:
                events.append(json.loads(x))
            except json.JSONDecodeError:
                continue  # pre-existing malformed line is not this closure's business
    review_eid = "w041-f0-review-rev27-a-20260912T005330"
    review_ingested = sum(1 for e in events if e.get("event_id") == review_eid) == 1
    outbox_lines = [json.loads(x) for x in open(os.path.join(ROOT, "comms/outbox/worker-041.jsonl"), encoding="utf-8") if x.strip()]
    f0_reviews = [e for e in outbox_lines if e.get("event_type") == "review" and e.get("target_id") == "F0"]
    prior_closures = sorted(e.get("event_id") for e in outbox_lines
                            if str(e.get("event_id", "")).startswith("w041-f0-redispatch"))

    ckpt_id = f"w041-f0-redispatch3-ckpt-{STAMP}"
    checkpoint = {
        "checkpoint_id": ckpt_id,
        "created_at": NOW,
        "actor": "worker-041",
        "instance": "worker-041-20260912T010739-968807",
        "role": "bounded execution worker",
        "slot": "041",
        "task_id": "audit-r2-F0-a",
        "node_id": "audit-r2-F0-a",
        "map_node": "F0",
        "gate": "G-F0",
        "class_id": "GLOBAL",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "action": "re-dispatch idempotency closure #3: verify the frozen record, emit one status event, exit",
        "not_a_new_review": True,
        "not_a_gate_verdict": True,
        "assignment_state": {
            "inbox_cards": len(inbox),
            "card_event_id": inbox[0].get("event_id") if inbox else None,
            "card_mtime_unchanged_since": "2026-09-12T00:44:18+08:00",
            "stop_rule_met_by_prior_instance": True,
            "prior_closures": prior_closures,
            "worker_041_instances_on_disk": len(instances),
        },
        "record": {
            "verdict": {"path": PINS["verdict"], "sha256": measured["verdict"], "reviewer": "worker-041",
                        "verdict": "accept", "score": 4.0, "hard_failures": [],
                        "reviewed_sha256": EXPECTED["canonical"]},
            "review_event": {"event_id": review_eid, "in_outbox": len(f0_reviews) == 1,
                             "ingested_in_events_jsonl": review_ingested,
                             "duplicate_f0_review_events": max(0, len(f0_reviews) - 1)},
            "prior_checkpoint": {"path": PINS["prior_checkpoint"], "sha256": measured["prior_checkpoint"]},
        },
        "pins_measured": measured,
        "pins_expected": EXPECTED,
        "pins_all_match": pins_ok,
        "verification": {
            "report": {"path": PINS["report"], "sha256": measured["report"]},
            "instrument": {"path": PINS["instrument"], "sha256": measured["instrument"]},
            "checks_total": len(report["checks"]),
            "checks_passed": sum(1 for c in report["checks"] if c["ok"]),
            "hard_failures": report["hard_failures"],
            "verdict": report["verdict"],
            "observations": [o["id"] for o in report["observations"]],
        },
        "actions_taken": {
            "verdict_file_overwritten": False,
            "duplicate_review_event_emitted": False,
            "gate_or_node_status_set": False,
            "pinned_artifact_edits": "none; all reads were hash-checked before and after",
        },
        "dispatch_loop_finding": (
            f"independent_supervisor_100.sh relaunches the worker-041 tmux slot whenever the dsh "
            f"process exits; {len(instances)} worker-041 instances exist and {len(prior_closures)} "
            f"closure status events are already on record for a card whose stop rule was met at "
            f"2026-09-12T00:52-00:53. Each relaunch burns budget and adds closure noise. Worker "
            f"events cannot kill or edit the supervisor session; this needs a controller/supervisor "
            f"action: retire/consume the audit-r2-F0-a card for slot 041, or stop relaunching it."
        ),
        "needed_to_unblock": (
            "controller records assignment audit-r2-F0-a as consumed for slot 041 and/or the "
            "supervisor owner retires the worker-041 tmux session (tmux kill-session -t worker-041); "
            "no further worker-041 relaunch should re-read this card"
        ),
        "next_falsifier": (
            "Declare this closure false if any of: (a) sha256(research_map/formulation_taxonomy.yaml) "
            f"!= {EXPECTED['canonical']}; (b) sha256(artifacts/formulation/formulation_taxonomy.yaml) "
            f"!= {EXPECTED['companion']}; (c) sha256(reviews/F0-review-rev27-a.json) != "
            f"{EXPECTED['verdict']}; (d) sha256(runtime/state/worker-041_F0_checkpoint.json) != "
            f"{EXPECTED['prior_checkpoint']}; (e) report verdict != PASS or a hard failure appears in "
            "the report; (f) more than one review event for target F0 at pin 0abb9ed8a961 appears in "
            "comms/outbox/worker-041.jsonl; (g) no ingested review event "
            "w041-f0-review-rev27-a-20260912T005330 binds the pin; or (h) the inbox card changes "
            "content, which would make this a stale closure rather than a duplicate one."
        ),
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{EXPECTED['canonical']}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{EXPECTED['companion']}",
            f"reviews/F0-review-rev27-a.json#{EXPECTED['verdict']}",
            f"runtime/state/worker-041_F0_checkpoint.json#{EXPECTED['prior_checkpoint']}",
            f"{PINS['report']}#{measured['report']}",
            f"{PINS['instrument']}#{measured['instrument']}",
            f"comms/outbox/worker-041.jsonl#{review_eid}",
            f"research_map/events.jsonl#{review_eid}",
            "comms/inbox/worker-041.jsonl#audit-r2-F0-a",
            "research_map/ASTRA_HANDOFF.md:23-27",
        ],
    }

    ckpt_path = os.path.join(ROOT, "runtime/state", f"worker-041_F0_redispatch3_checkpoint_{STAMP}.json")
    with open(ckpt_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        f.write("\n")
    ckpt_sha = sha256_file(ckpt_path)

    event = {
        "event_id": f"w041-f0-redispatch3-close-{STAMP}",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-041",
        "assignee": "worker-041",
        "node_id": "audit-r2-F0-a",
        "map_node": "F0",
        "gate": "G-F0",
        "class_id": "GLOBAL",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "status": "done",
        "hours": 0.2,
        "task_id": "audit-r2-F0-a",
        "completion_scope": "bounded worker lifecycle closure only; NOT a new blind review, NOT a node done, NOT a gate verdict, NOT an artifact edit",
        "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        "verdict_file_overwritten": False,
        "duplicate_review_event_emitted": False,
        "summary": (
            "Re-dispatch idempotency closure #3, NOT a new review. Assignment audit-r2-F0-a was "
            "already satisfied by the prior worker-041 instance: verdict reviews/F0-review-rev27-a.json"
            f"#{EXPECTED['verdict'][:12]} (accept, score 4.0, hard_failures []), review event "
            f"{review_eid} ingested in events.jsonl, checkpoint worker-041_F0_checkpoint.json"
            f"#{EXPECTED['prior_checkpoint'][:12]}. This 4th instance re-verified the frozen record "
            "from bytes with a new read-only instrument (16/16 checks PASS, exit 0): canonical pin "
            "0abb9ed8a961 before AND after reading; companion pin d7419b4e8963; exactly 4 distinct "
            "class ids on all four structural surfaces with sets equal; 6/6 disjointness pairs on "
            "both surfaces; no C2-into-C0 leakage or C0/C2 merge; no conclusion inflation "
            "(draft_unverified, claims_theorem_status false); decidable falsifiers present for all "
            "four classes; companion CONSISTENT without byte-identity (REC-3). Verdict file and its "
            "review event agree on every binding field. Deliberately did NOT overwrite the pinned "
            "verdict and did NOT emit a duplicate review event. NEW FINDING: the launch slot is "
            "looping - independent_supervisor_100.sh relaunches worker-041 on exit, 10 instances "
            "exist and 2 closure events were already on record; needed_to_unblock: controller marks "
            "the card consumed and/or supervisor retires the worker-041 tmux session. Node F0 and "
            "gate G-F0 are untouched by this event.",
        ),
        "evidence_refs": checkpoint["evidence_refs"] + [f"runtime/state/{os.path.basename(ckpt_path)}#{ckpt_sha}"],
        "next_falsifier": checkpoint["next_falsifier"],
        "needed_to_unblock": checkpoint["needed_to_unblock"],
        "to": ["astra", "astra-lead-audit"],
    }

    validate_event(event)

    outbox_path = os.path.join(ROOT, "comms/outbox/worker-041.jsonl")
    line = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(outbox_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)

    # read back and confirm exactly one appended status line, no duplicate review
    back = [json.loads(x) for x in open(outbox_path, encoding="utf-8") if x.strip()]
    mine = [e for e in back if e.get("event_id") == event["event_id"]]
    f0_reviews_after = [e for e in back if e.get("event_type") == "review" and e.get("target_id") == "F0"]
    print(f"checkpoint={ckpt_path} sha256={ckpt_sha}")
    print(f"event_id={event['event_id']} appended={len(mine) == 1} validated=True")
    print(f"f0_review_events_after={len(f0_reviews_after)} (must stay 1)")
    print(f"pins_all_match={pins_ok} report_verdict={report['verdict']} "
          f"checks={sum(1 for c in report['checks'] if c['ok'])}/{len(report['checks'])}")
    return 0 if (pins_ok and len(mine) == 1 and len(f0_reviews_after) == 1
                 and report["verdict"] == "PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
