#!/usr/bin/env python3
"""Emit the W082-A1-XTARGET-ERRATUM-AUDIT-01 events to the worker outbox.

Every event is validated against research_map/schemas.py before a single byte is
written; the outbox is appended once, atomically enough for this protocol (one
write call).  The checkpoint is written after the events and referenced by the
delivered status event.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
sys.path.insert(0, ROOT)

from research_map.schemas import validate_event  # noqa: E402

OUT_DIR = os.path.join(ROOT, "artifacts/worker-082/a1_xtarget_erratum_audit")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-082.jsonl")
CHECKPOINT = os.path.join(ROOT, "runtime/state/w082_a1_xtarget_erratum_audit_checkpoint.json")
CHECKPOINT_LOG = os.path.join(ROOT, "runtime/state/w082_a1_xtarget_erratum_audit_checkpoints.jsonl")
VERDICT = os.path.join(OUT_DIR, "verdict.json")
REPORT = os.path.join(OUT_DIR, "REPORT.md")
INSTRUMENT = os.path.join(OUT_DIR, "audit_census_erratum.py")
MAP_PATH = os.path.join(ROOT, "research_map/research_map.json")
EVENTS_PATH = os.path.join(ROOT, "research_map/events.jsonl")

TASK_ID = "W082-A1-XTARGET-ERRATUM-AUDIT-01"
NODE_ID = "A1"
GATE = "G-AUDIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)
TZ = timezone(timedelta(hours=8))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def accepted_w082_ids() -> set[str]:
    ids = set()
    with open(EVENTS_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                eid = str(json.loads(line).get("event_id", ""))
            except json.JSONDecodeError:
                continue
            if eid.startswith("w082-a1xt"):
                ids.add(eid)
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate without appending")
    args = ap.parse_args()
    verdict_sha = sha256_file(VERDICT)
    report_sha = sha256_file(REPORT)
    instrument_sha = sha256_file(INSTRUMENT)
    with open(VERDICT, "r", encoding="utf-8") as fh:
        v = json.load(fh)
    # cite the hashes the audit actually measured (recorded in verdict.json), not emit-time bytes
    map_sha = v["inputs"]["research_map/research_map.json"]
    events_sha = v["inputs"]["research_map/events.jsonl"]
    map_sha_now = sha256_file(MAP_PATH)
    events_sha_now = sha256_file(EVENTS_PATH)
    map_drift = map_sha_now != map_sha
    events_drift = events_sha_now != events_sha
    drift_note = ""
    if map_drift or events_drift:
        drift_note = (f" DRIFT SINCE MEASUREMENT: research_map.json {map_sha[:12]}->{map_sha_now[:12]}; "
                      f"events.jsonl {events_sha[:12]}->{events_sha_now[:12]}; the cited hashes are the measured ones.")
    expected_partition = set(next(c for c in v["checks"] if c["check"] == "current_batch_intact")["current_ids"]) | \
        set(next(c for c in v["checks"] if c["check"] == "map_liveness")["stale_ids_in_applied_event_ids"])
    partition_now = accepted_w082_ids()
    partition_unchanged = partition_now == expected_partition
    if not partition_unchanged:
        raise SystemExit(
            "FAIL CLOSED: the w082-a1xt accepted-stream partition changed since measurement "
            f"(measured {len(expected_partition)} ids, now {len(partition_now)}); re-run the audit before emitting.")
    key = verdict_sha[:12]
    now = datetime.now(TZ).isoformat(timespec="seconds")
    checks = {c["check"]: c["status"] for c in v["checks"]}
    live = next(c for c in v["checks"] if c["check"] == "map_liveness")
    claim_statement = (
        f"At research_map/research_map.json#sha256:{map_sha[:12]} and research_map/events.jsonl#sha256:{events_sha[:12]}, "
        f"the W082 census erratum (w082-a1xt-9651c42845c0-erratum-stale-set) enumerates exactly the 19 accepted-stream "
        f"w082-a1xt event ids outside the final 9651c42845c0 batch (symmetric difference 0) and all 10 final-batch ids are "
        f"applied exactly once; the final report/review/instrument bytes stay hash-bound "
        f"({verdict_sha[:12]} verdict, 9651c42845c0e6d1 census report, be66be532602554c census review, 2e3d12aa0bb6f244 census "
        f"instrument). However the canonical map still carries {len(live['stale_claims_still_live'])} stale census claims and "
        f"{len(live['stale_reviews_still_live'])} stale coverage reviews with no supersession marker, and map.applied_event_ids "
        f"retains all 19 stale ids; the erratum's batch-B 'deduped away' reason is contradicted by the accepted stream (all "
        f"three ccf3ac5f77f3 coverage reviews present and live in map.reviews). The census numbers at the pinned bytes are "
        f"unchanged; what is unenforced is the supersession, and 3 new pin-binding review-shaped records in reviews/ landed "
        f"after the census window, so the published falsifier is a drift/superset check rather than an exact replay."
        + drift_note
    )

    anchor = {
        "actor": "worker-082",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
    }
    events = [
        dict(anchor, event_id=f"w082-a1xtea-{key}-status-open", event_type="status", created_at=now,
             status="active", hours=0.2,
             summary=(f"No assignment card exists in comms/inbox/worker-082.jsonl; taking ONE bounded class-bound task: "
                      f"{TASK_ID}. Independent audit of the supersession/erratum attached to W082-A1-XTARGET-INDEP-CENSUS-01: "
                      f"stale-id exactness, hash binding of the final batch, map-level retirement, erratum-reason accuracy, and "
                      f"falsifier replayability. No gate verdict, no node completion."),
             evidence_refs=[f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}",
                            f"research_map/research_map.json#sha256:{map_sha[:12]}"],
             next_falsifier="Re-run audit_census_erratum.py: a listed stale id never ingested, a missing/duplicated current id, a hash mismatch, or a stale entry that does carry a retirement marker."),
        dict(anchor, event_id=f"w082-a1xtea-{key}-artifact-verdict", event_type="artifact", created_at=now,
             artifact_type="erratum_audit_verdict", path=os.path.relpath(VERDICT, ROOT), sha256=verdict_sha,
             validation_status="unverified",
             evidence_refs=[f"research_map/events.jsonl#sha256:{events_sha[:12]}",
                            "research_map/research_map.json#applied_event_ids"],
             note="Hash-pinned findings W082-EA-01..04, six pre-registered checks with per-check falsifiers, controls, and a controller-side repair recommendation."),
        dict(anchor, event_id=f"w082-a1xtea-{key}-artifact-instrument", event_type="artifact", created_at=now,
             artifact_type="verifier", path=os.path.relpath(INSTRUMENT, ROOT), sha256=instrument_sha,
             validation_status="unverified",
             evidence_refs=[f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}"],
             note="Read-only and deterministic (two runs identical); re-hashes its inputs; does not edit the map or any canonical artifact."),
        dict(anchor, event_id=f"w082-a1xtea-{key}-artifact-report", event_type="artifact", created_at=now,
             artifact_type="audit_report", path=os.path.relpath(REPORT, ROOT), sha256=report_sha,
             validation_status="unverified",
             evidence_refs=[f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}"],
             note="Human-readable rendering of the same verdict; no separate claims."),
        dict(anchor, event_id=f"w082-a1xtea-{key}-claim-audit", event_type="claim", created_at=now,
             statement=claim_statement,
             conclusion_type="formal_model",
             assumptions=[
                 "research_map/events.jsonl and research_map/research_map.json as read at the cited sha256 are the authority for the accepted stream and applied ids",
                 "membership in map.applied_event_ids means an event was ingested, not that the map retired it",
                 "absence of superseded_by/retired/promotion_status=retired on an entry means the map has not marked it superseded",
                 "the three new pin-binding reviews found after the census window are drift, not evidence of a verdict missed inside the window",
                 "this is an evidence-hygiene audit and asserts nothing about the mathematical content of F1, F2a or F2b",
             ],
             falsifier=("Re-run audit_census_erratum.py at the cited hashes: any erratum-listed id that was never ingested, a "
                        "current-batch id missing or duplicated, a measured sha256 differing from the live event pin, a stale "
                        "entry that turns out to carry a retirement marker, or an archived corpus manifest for the observation "
                        "window (which voids W082-EA-03) falsifies this claim."),
             evidence_refs=[
                 f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}",
                 f"{os.path.relpath(REPORT, ROOT)}#sha256:{report_sha[:12]}",
                 "artifacts/worker-082/a1_xtarget_census/report.json#sha256:9651c42845c0",
                 "artifacts/worker-082/a1_xtarget_census/REVIEW-A1-XTARGET-082.json#sha256:be66be532602554c",
                 "comms/outbox/worker-082.jsonl#w082-a1xt-9651c42845c0-erratum-stale-set",
             ],
             artifact_refs=[f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}"],
             ),
        dict(anchor, event_id=f"w082-a1xtea-{key}-blocker-retirement", event_type="blocker", created_at=now,
             description=("Stale W082 census batches remain live and unretired in the canonical map: "
                          f"{len(live['stale_claims_still_live'])} stale claims ({', '.join(live['stale_claims_still_live'])}) and "
                          f"{len(live['stale_reviews_still_live'])} stale coverage reviews "
                          f"({', '.join(live['stale_reviews_still_live'])}); all 19 stale ids stay in applied_event_ids and no entry "
                          "carries a supersession marker, so a consumer counting by task_id sees 3 claims / 9 reviews for one census. "
                          "Worker-082 cannot edit map state."),
             needed_to_unblock=("Controller-side and mechanical: annotate the 8 stale entries with "
                                "superseded_by=w082-a1xt-9651c42845c0-* (the field convention already exists in map.reviews) or add a "
                                "superseded_event_ids register, and issue a corrected erratum note for the contradicted batch-B reason."),
             evidence_refs=[f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}",
                            "research_map/research_map.json#claims",
                            "research_map/research_map.json#reviews",
                            "research_map/research_map.json#applied_event_ids"],
             next_falsifier="A controller pass that annotates or retires the 8 stale entries; then this blocker is resolved and the erratum is enforced."),
    ]
    # strip the placeholder key used above to keep dict construction honest
    for ev in events:
        ev.pop("review_verdicts", None)

    for ev in events:
        validate_event(ev)

    with open(OUTBOX, "r", encoding="utf-8") as fh:
        existing = {json.loads(line)["event_id"] for line in fh if line.strip()}
    collisions = [ev["event_id"] for ev in events if ev["event_id"] in existing]
    if collisions:
        raise SystemExit(f"FAIL CLOSED: event id collision: {collisions}")

    checkpoint_id = f"w082-a1xtea-ckpt-{datetime.now(TZ).strftime('%Y%m%dT%H%M%S%z')}"
    events.append(dict(anchor, event_id=f"w082-a1xtea-{key}-status-delivered", event_type="status", created_at=now,
                       status="active", hours=0.3,
                       summary=(f"{TASK_ID} complete at worker level: erratum stale-set exact (19/19), final batch hash-bound and "
                                f"applied once, but map retirement absent (2 stale claims + 6 stale reviews live) and the batch-B "
                                f"dedup reason contradicted by the accepted stream; corpus not archived so the published falsifier "
                                f"is a drift check. Verdict revise 3.5. Worker completion claim only - does NOT set node status, gate "
                                f"verdict, or validation_status."),
                       evidence_refs=[f"{os.path.relpath(VERDICT, ROOT)}#sha256:{verdict_sha[:12]}",
                                      os.path.relpath(CHECKPOINT, ROOT),
                                      f"comms/outbox/worker-082.jsonl#w082-a1xtea-{key}-claim-audit"],
                       next_falsifier="A controller retirement of the 8 stale entries or a new census emission; either supersedes this audit and it must be re-run."))
    validate_event(events[-1])

    # single append
    if args.dry_run:
        print("DRY RUN: validated", len(events), "events; nothing written")
        for ev in events:
            print(" ", ev["event_type"], ev["event_id"])
        return 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")

    checkpoint = {
        "checkpoint_id": checkpoint_id,
        "created_at": now,
        "worker": "worker-082",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "status": "delivered-active (worker cannot set done/gate verdict)",
        "artifacts": {
            os.path.relpath(VERDICT, ROOT): verdict_sha,
            os.path.relpath(REPORT, ROOT): report_sha,
            os.path.relpath(INSTRUMENT, ROOT): instrument_sha,
        },
        "inputs": {
            "research_map/research_map.json": map_sha,
            "research_map/events.jsonl": events_sha,
            "drift_since_measurement": {
                "research_map/research_map.json_now": map_sha_now,
                "research_map/events.jsonl_now": events_sha_now,
                "drifted": bool(map_drift or events_drift),
                "w082_partition_unchanged": partition_unchanged,
            },
        },
        "result": {
            "verdict": v["verdict"]["verdict"],
            "score": v["verdict"]["score"],
            "checks": checks,
            "findings": [f["id"] for f in v["findings"]],
            "stale_claims_still_live": live["stale_claims_still_live"],
            "stale_reviews_still_live": live["stale_reviews_still_live"],
            "applied_stale_ids": len(live["stale_ids_in_applied_event_ids"]),
            "naive_consumer_counts": live["naive_consumer_counts"],
        },
        "outbox_event_ids": [ev["event_id"] for ev in events],
        "authority": "worker evidence only; no gate verdict, no node status, no validation_status, no map edit",
        "next_falsifier": "A controller retirement of the 8 stale entries, a new census emission, or any moved pin makes this checkpoint stale and the audit must be re-run.",
    }
    with open(CHECKPOINT, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(CHECKPOINT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"checkpoint_id": checkpoint_id, "created_at": now, "task_id": TASK_ID,
                             "verdict": v["verdict"]["verdict"], "checkpoint_sha256": sha256_file(CHECKPOINT),
                             "outbox_event_ids": [ev["event_id"] for ev in events]}, sort_keys=True) + "\n")

    print("appended", len(events), "events to", OUTBOX)
    for ev in events:
        print(" ", ev["event_type"], ev["event_id"])
    print("checkpoint:", CHECKPOINT, sha256_file(CHECKPOINT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
