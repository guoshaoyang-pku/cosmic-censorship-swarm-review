#!/usr/bin/env python3
"""
Emit W071-F1-REV27-BLIND-REVIEW-01 events to comms/outbox/worker-071.jsonl and write one
checkpoint to runtime/state/worker-071_F1-review-rev27-a_checkpoint.json.

Event order: blocker (primary), artifact x3, status=blocked (assignment-scoped).
No `review` event is emitted: the assigned schema pin is a moving target and the assigned
verdict path is already occupied, so acceptance clause (1) requires a blocker instead.

The five JSON lines are appended in a single O_APPEND write so the controller's ingest
never sees a partial line. Nothing canonical is modified; research_map/events.jsonl is left
for the controller's locked ingest to pull.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-071.jsonl"
CHECKPOINT = ROOT / "runtime/state/worker-071_F1-review-rev27-a_checkpoint.json"
TZ = timezone(timedelta(hours=8))

TASK_ID = "W071-F1-REV27-BLIND-REVIEW-01"
SCHEMA = "schemas/af_wcc_vacuum.yaml"
TARGET_PATH = "reviews/F1-review-rev27-a.json"
ARTIFACTS = [
    ("artifacts/worker-071/f1_rev27_blind_review/BLOCKER.json", "review_blocker"),
    ("artifacts/worker-071/f1_rev27_blind_review/measurement.json", "measurement_data"),
    ("artifacts/worker-071/f1_rev27_blind_review/measure.py", "verification_instrument"),
    ("artifacts/worker-071/f1_rev27_blind_review/build_blocker.py", "analysis_script"),
]


def now_iso():
    return datetime.now(TZ).isoformat(timespec="milliseconds")


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ts = now_iso()
    stamp = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
    m = json.loads((HERE / "measurement.json").read_text())
    b = json.loads((HERE / "BLOCKER.json").read_text())

    art = {}
    for rel, kind in ARTIFACTS:
        p = ROOT / rel
        art[rel] = {"sha256": sha_file(p), "bytes": p.stat().st_size, "artifact_type": kind}

    blocker_rel = ARTIFACTS[0][0]
    meas_rel = ARTIFACTS[1][0]
    instr_rel = ARTIFACTS[2][0]

    evidence = list(b["evidence_refs"])
    events = []

    events.append(
        {
            "event_id": f"w071-f1rev27-{stamp}-blocker-moving-target",
            "event_type": "blocker",
            "created_at": ts,
            "actor": "worker-071",
            "task_id": TASK_ID,
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "hours": 0.5,
            "description": (
                "MOVING TARGET: assigned pin " + b["assigned_pin"]["sha256"][:12] + " (F1 rev12) "
                "!= measured " + str(b["measured_f1"]["sha256"])[:12] + " (F1 rev13, "
                "2026-09-12T00:53:20+08:00); the assigned verdict path " + TARGET_PATH + " was "
                "already written at " + str(b["target_verdict_path_occupancy"].get("mtime")) +
                " (sha256 " + str(b["target_verdict_path_occupancy"].get("sha256"))[:12] + "), "
                "before this worker started. No blind verdict was written and no existing file "
                "was overwritten. Bind-chain addendum measured and folded into the blocker: all "
                "declared F1 hashes resolve at current bytes (F0 0abb9ed8a961, consistency "
                "evidence 9e335e9ba1bf, provenance 7a3e1f93f77c); refresh rule satisfied; no "
                "mismatch. See " + blocker_rel + "#" + art[blocker_rel]["sha256"][:12] + "."
            ),
            "needed_to_unblock": b["needed_to_unblock"],
            "falsifier": b["falsifier"],
            "evidence_refs": evidence,
        }
    )

    for rel, kind in ARTIFACTS:
        note = {
            "review_blocker": "Decisive blocker artifact: pin mismatch + target occupancy + bind-chain resolution; worker evidence only.",
            "measurement_data": "Machine output of measure.py: before/read/after hashes, pin check, occupancy, declared-hash chain, controls.",
            "verification_instrument": "Reproducible instrument implementing the card's pre-read/post-read hash rule and the f0_binding chain resolution.",
            "analysis_script": "Builder that folds the bind-chain addendum into the single blocker artifact.",
        }[kind]
        events.append(
            {
                "event_id": f"w071-f1rev27-{stamp}-artifact-{Path(rel).name.replace('.', '-')}",
                "event_type": "artifact",
                "created_at": ts,
                "actor": "worker-071",
                "task_id": TASK_ID,
                "node_id": "F1",
                "gate": "G-FORM",
                "class_id": "AF-WCC-VAC-GEN",
                "artifact_type": kind,
                "path": rel,
                "sha256": art[rel]["sha256"],
                "bytes": art[rel]["bytes"],
                "validation_status": "unverified",
                "note": note,
                "evidence_refs": [rel + "#" + art[rel]["sha256"][:12], meas_rel + "#" + art[meas_rel]["sha256"][:12]],
            }
        )

    events.append(
        {
            "event_id": f"w071-f1rev27-{stamp}-status-blocked",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-071",
            "task_id": TASK_ID,
            "node_id": "F1",
            "gate": "G-FORM",
            "class_id": "AF-WCC-VAC-GEN",
            "status": "blocked",
            "hours": 0.5,
            "summary": (
                "Assignment-scoped status only (no node or gate movement): blind F1 review at "
                "rev27 pin " + b["assigned_pin"]["sha256"][:12] + " is unexecutable because the "
                "file is now rev13 " + str(b["measured_f1"]["sha256"])[:12] + " and " +
                TARGET_PATH + " is already occupied. One blocker + three artifacts + this status "
                "emitted; no review verdict. Bind-chain addendum: every declared hash resolves, "
                "refresh rule satisfied, no mismatch. Controller must re-issue at the live hash "
                "to an unoccupied reviewer path."
            ),
            "do_not_claim": "No gate verdict, no validation_status=passed, no node status; worker evidence only.",
            "evidence_refs": evidence,
            "next_falsifier": b["falsifier"],
        }
    )

    # single append write (one JSON object per line)
    blob = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events)
    with OUTBOX.open("a") as f:
        f.write(blob)

    # post-write verification: re-hash written artifacts and confirm canonical paths unchanged
    post = {rel: sha_file(ROOT / rel) for rel, _k in ARTIFACTS}
    canonical = {
        SCHEMA: sha_file(ROOT / SCHEMA),
        TARGET_PATH: sha_file(ROOT / TARGET_PATH),
    }
    unchanged = all(post[rel] == art[rel]["sha256"] for rel, _k in ARTIFACTS)
    canonical_unchanged = canonical[SCHEMA] == m["schemas"][0]["sha256_before_read"] and (
        canonical[TARGET_PATH] == b["target_verdict_path_occupancy"].get("sha256")
    )

    checkpoint = {
        "checkpoint_id": f"w071-f1rev27-blind-review-checkpoint-{stamp}",
        "task_id": TASK_ID,
        "worker": "worker-071",
        "created_at": now_iso(),
        "gate": "G-FORM",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "assignment_event_ids": b["assignment_event_ids"],
        "assignment_deadline": b["assignment_deadline"],
        "assignment_status": "blocked",
        "decision": b["code"],
        "reason": b["headline"],
        "pin_check": b["pin_check"],
        "blocker_type": b["blocker_type"],
        "target_verdict_path_occupancy": b["target_verdict_path_occupancy"],
        "bind_chain_addendum": {
            "all_declared_hashes_resolved": b["bind_chain_addendum"]["all_declared_hashes_resolved"],
            "binding_hashes_resolved": b["bind_chain_addendum"]["binding_hashes_resolved"],
            "any_mismatch": b["bind_chain_addendum"]["any_mismatch"],
            "refresh_rule_satisfied": b["bind_chain_addendum"]["refresh_rule"]["satisfied_at_current_bytes"],
        },
        "artifacts": [{"path": rel, "sha256": art[rel]["sha256"], "bytes": art[rel]["bytes"], "artifact_type": k} for rel, k in ARTIFACTS],
        "driver_script": {
            "path": "artifacts/worker-071/f1_rev27_blind_review/emit_and_checkpoint.py",
            "sha256": sha_file(Path(__file__).resolve()),
        },
        "events_emitted": [e["event_id"] for e in events],
        "outbox": "comms/outbox/worker-071.jsonl",
        "evidence_refs": evidence,
        "next_falsifier": b["falsifier"],
        "void_condition": b["void_condition"],
        "controls_passed": m["controls_passed"],
        "measurement_valid": m["measurement_valid"],
        "no_review_verdict": True,
        "no_gate_verdict": True,
        "no_node_status_set": True,
        "post_write_checks": {
            "artifacts_unchanged_after_event_write": unchanged,
            "canonical_schema_unchanged": canonical[SCHEMA] == m["schemas"][0]["sha256_before_read"],
            "target_verdict_file_unchanged": canonical[TARGET_PATH] == b["target_verdict_path_occupancy"].get("sha256"),
            "canonical_unchanged": canonical_unchanged,
            "measured": canonical,
        },
        "note": (
            "Stop rule satisfied: one blocker artifact + one blocker event + one checkpoint, then "
            "exit. No review verdict was possible under acceptance clause (1). Checkpoint is "
            "worker evidence; only controller/leads move gates or node status."
        ),
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=2) + "\n")

    print("appended", len(events), "events to", OUTBOX.relative_to(ROOT))
    for e in events:
        print("  ", e["event_type"], e["event_id"])
    print("wrote", CHECKPOINT.relative_to(ROOT))
    print("checkpoint sha256", sha_file(CHECKPOINT))
    print("artifacts_unchanged_after_event_write", unchanged)
    print("canonical_unchanged", canonical_unchanged)
    return 0 if (unchanged and canonical_unchanged) else 1


if __name__ == "__main__":
    raise SystemExit(main())
