#!/usr/bin/env python3
"""Emit the W036-CLASSSEP-COMPOSE-01 *correction* events (append-only).

Reason: the first `artifact` event (w036-compose-20260912T010500-artifact, ingested 00:58:23)
recorded the run-2 `report.json` digest.  A post-checkpoint idempotence re-run at 00:59:01 rewrote
`report.json` changing only `created_at` (all 48 checks and every measurement byte-identical), so
`CHECKPOINT.json` was re-pinned.  These events register the current full digests.  The canonical
events stream is append-only and controller-owned; nothing already ingested is edited.

Writes: comms/outbox/worker-036.jsonl (append) and a local copy under this directory.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-036.jsonl"
LOCAL = HERE / "events_w036_compose_correction.jsonl"

REQUIRED = {
    "status": ("event_id", "event_type", "created_at", "actor", "node_id", "status"),
    "artifact": ("event_id", "event_type", "created_at", "actor", "node_id", "path", "sha256",
                 "validation_status"),
}


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate(events: list) -> list:
    problems, ids = [], set()
    for e in events:
        eid = e.get("event_id")
        if eid in ids:
            problems.append(f"duplicate event_id {eid}")
        ids.add(eid)
        for k in REQUIRED[e["event_type"]]:
            if k not in e or e[k] in (None, "", []):
                problems.append(f"{eid}: missing {k}")
        if e.get("class_ids"):
            problems.append(f"{eid}: carries a class_ids container (class-binding discipline)")
        try:
            json.dumps(e)
        except TypeError as exc:  # pragma: no cover
            problems.append(f"{eid}: not JSON-serializable: {exc}")
    return problems


def main() -> int:
    ck = json.loads((HERE / "CHECKPOINT.json").read_text())
    rep_sha = h(HERE / "report.json")
    ck_sha = h(HERE / "CHECKPOINT.json")
    build_sha = h(HERE / "candidate_build.json")
    # the superseded run-2 digest, as recorded in the first artifact event's note/evidence
    superseded = None
    for line in OUTBOX.read_text().splitlines():
        e = json.loads(line)
        if e.get("event_id") == "w036-compose-20260912T010500-artifact":
            superseded = e.get("sha256")
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    base = "w036-compose-20260912T010500-corr"
    scope = ck["scope_classes"]
    events = [
        {
            "event_id": f"{base}-artifact",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "scope_classes": scope,
            "artifact_type": "composition_calibration_packet_correction",
            "path": "artifacts/worker-036/classsep_compose/report.json",
            "sha256": rep_sha,
            "validation_status": "unverified",
            "supersedes": "w036-compose-20260912T010500-artifact",
            "superseded_report_sha256": superseded,
            "note": ("Correction of the digest binding only: the earlier artifact event recorded the run-2 "
                     "report.json digest %s. An idempotence re-run at 00:59:01 rewrote report.json changing "
                     "only created_at; all 48 checks and every measurement are identical between runs "
                     "(verified by full-document comparison: only top-level key 'created_at' differs). "
                     "Current report.json sha256 %s; re-pinned CHECKPOINT.json sha256 %s; candidate_build.json "
                     "sha256 %s. No measurement, check, claim or falsifier changed."
                     % ((superseded or '<unknown>')[:12], rep_sha[:12], ck_sha[:12], build_sha[:12])),
            "evidence_refs": [
                f"artifacts/worker-036/classsep_compose/report.json#{rep_sha[:12]}",
                f"artifacts/worker-036/classsep_compose/CHECKPOINT.json#{ck_sha[:12]}",
                f"artifacts/worker-036/classsep_compose/candidate_build.json#{build_sha[:12]}",
            ],
            "next_falsifier": ("Re-hash report.json and CHECKPOINT.json; if either differs from the digests above "
                               "without a further correction event, the packet's declared binding is stale again. "
                               "The claim's falsifier (re-run the 48 checks) is unchanged."),
        },
        {
            "event_id": f"{base}-status",
            "event_type": "status",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "scope_classes": scope,
            "status": "active",
            "hours": 0.0,
            "summary": ("Correction tick for W036-CLASSSEP-COMPOSE-01: artifact digest re-bound after a "
                        "post-checkpoint idempotence re-run that changed only report.json's created_at. "
                        "Result unchanged: PASS 48/48, 0 interactions both windows, C0-window aggregate "
                        "48/48/383/383, C1-window aggregate 43/43/378/378, live map C0 window 20/21/228/229 "
                        "and C1 window 16/17/224/225. Worker evidence only; no gate verdict, no node done, "
                        "no canonical patch applied."),
            "evidence_refs": [f"artifacts/worker-036/classsep_compose/CHECKPOINT.json#{ck_sha[:12]}",
                              f"artifacts/worker-036/classsep_compose/report.json#{rep_sha[:12]}"],
            "next_falsifier": "Same as the main claim: any of the 48 checks failing on re-run voids the packet.",
        },
    ]
    problems = validate(events)
    if problems:
        print(json.dumps({"validation": "FAILED", "problems": problems}, indent=1))
        return 1
    payload = "".join(json.dumps(e, sort_keys=True) + "\n" for e in events)
    with OUTBOX.open("a") as f:
        f.write(payload)
    LOCAL.write_text(payload)
    print(json.dumps({"appended": len(events), "validation": "OK", "report_sha256": rep_sha,
                      "checkpoint_sha256": ck_sha, "superseded_report_sha256": superseded,
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
