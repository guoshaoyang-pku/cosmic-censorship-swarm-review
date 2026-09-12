#!/usr/bin/env python3
"""Emit W032-CF16-DELTA-01 events to comms/outbox/worker-032.jsonl.

Self-rejection pass first (PROTOCOL rule 5): every artifact must exist on disk
with the declared sha256, the class ids must match the task, and every event must
pass research_map.schemas.validate_event before a single line is appended.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = ROOT / "comms" / "outbox" / "worker-032.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W032-CF16-DELTA-01"
D = "artifacts/worker-032/cf16-delta"
CLASS_ID = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M")
    report = json.loads((ROOT / D / "report.json").read_text())
    assert report["task_id"] == TASK
    assert report["class_id"] == CLASS_ID

    artifacts = {
        "verification_report": f"{D}/report.json",
        "verification_tool": f"{D}/adjudicate_delta.py",
        "classification": f"{D}/classification.json",
        "readme": f"{D}/README.md",
        "checkpoint": f"{D}/CHECKPOINT.json",
        "event_emitter": f"{D}/emit_events.py",
        "pinned_map_snapshot": f"{D}/pinned/research_map.11311ab36005.json",
        "pinned_detector": f"{D}/pinned/class_separation.c266dbceca87.py",
        "drift_observation": f"{D}/drift_observation.json",
    }
    measured = {}
    for kind, rel in artifacts.items():
        p = ROOT / rel
        if not p.is_file():
            print(f"SELF-REJECT: missing artifact {rel}", file=sys.stderr)
            return 1
        measured[kind] = (rel, sha256(p))
    if measured["verification_report"][1] != (
        "e9a185ba9fdfeeb266c23e1368b0de94806ea9fae5a56275089da11ec28347f1"
    ):
        print("SELF-REJECT: report.json changed since the adjudication; re-run required", file=sys.stderr)
        return 1
    ckpt_sha = measured["checkpoint"][1]

    ev = []
    ev.append({
        "event_id": f"w032-cf16delta-{stamp}-status-start",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "status": "active",
        "hours": 0.15,
        "summary": (
            "W032-CF16-DELTA-01 started: no assignment existed for slot 032 in comms/inbox, so one "
            "bounded class-bound task was self-selected from the open audit queue. Scope: adjudicate the "
            "7 CLASSSEP hard claim-prose findings that are new at map 11311ab36005 relative to the 10 "
            "adjudicated at 3d45be59, plus an independent converse false-negative scan over all 207 claims. "
            "Read-only on canonical paths; no claim text edited."
        ),
        "evidence_refs": [f"{D}/pinned/research_map.11311ab36005.json#11311ab3600514cd"],
        "next_falsifier": "Any new finding is a genuine composite assertion, or the converse scan finds an unflagged genuine merge.",
    })
    ev.append({
        "event_id": f"w032-cf16delta-{stamp}-claim",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "conclusion_type": "formal_model",
        "statement": (
            "Instrument/checker-calibration measurement, not a mathematics or physics claim. At pinned "
            "research_map snapshot 11311ab3600514cd (207 claims, updated_at 00:43:08) with pinned detector "
            "c266dbceca87fb99, the hard CLASSSEP claim-prose set is 17 findings on 12 claims: 10 reproduce "
            "the worker-021/worker-035 adjudications at 3d45be59 exactly and 7 are new (claims 180, 187, "
            "192 x5, authored by worker-044/worker-085/worker-035). Independent cue classification plus a "
            "curated per-finding judgement labels all 17 as mention-level (NEGATED 7, CASE_LABEL 4, QUOTED 4, "
            "DETECTOR_SELF 1, DESCRIPTIVE 1): 0 genuine assertions that C0 and C2 are one class. No flagged "
            "claim declares a composite class token; every class_id token resolves to the frozen four. An "
            "independently written converse scan over all 207 claims finds 38 composite mentions, 21 "
            "assertion-cued, 5 unflagged candidates, 0 genuine, so no missed first-order merge was found. "
            "Controls 4/4 positive, 13/13 negative, worker-07 regression 17/0/10/0 PASS. Concurrent with and "
            "independently replicating worker-093 W093-CLASSSEP-METAGROWTH-01 at the same pin (0/17). The "
            "live map moved during the run to f06d40a8226a (278 claims, 20 hard); the 3 extra entries are "
            "exactly the self-mint worker-093 predicted, confirming the metagrowth mechanism."
        ),
        "assumptions": [
            "The frozen four class ids are the only valid class tokens (ASTRA_HANDOFF hard decision 1).",
            "The pinned detector c266dbceca87 is the audit's current checker at the pinned map.",
            "claim event_id is a stable key across map rebuilds; array indices are not.",
            "Per-finding label judgement is inspectable in classification.json (one reason per finding).",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            f"{D}/report.json#e9a185ba9fdfeeb2",
            f"{D}/classification.json#118b9441887d7ae2",
            f"{D}/pinned/research_map.11311ab36005.json#11311ab3600514cd",
            f"{D}/pinned/class_separation.c266dbceca87.py#c266dbceca87fb99",
            f"{D}/drift_observation.json#8d2919f4fbb41c9c",
        ],
        "artifact_refs": [f"{D}/report.json#e9a185ba9fdfeeb2"],
    })
    for kind, (rel, digest) in measured.items():
        ev.append({
            "event_id": f"w032-cf16delta-{stamp}-artifact-{kind}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-032",
            "node_id": "A1",
            "class_id": CLASS_ID,
            "artifact_type": kind,
            "path": rel,
            "sha256": digest,
            "validation_status": "unverified",
            "note": "W032-CF16-DELTA-01 artifact; measurement evidence only, not a gate verdict.",
            "evidence_refs": [f"{rel}#{digest[:16]}"],
        })
    ev.append({
        "event_id": f"w032-cf16delta-{stamp}-review-w093",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-032",
        "target_id": "w093-metagrowth-20260912T0049-claim",
        "reviewer": "worker-032",
        "verdict": "accept",
        "score": 4.5,
        "hard_failures": [],
        "findings": (
            "Advisory independent replication. W093-CLASSSEP-METAGROWTH-01 and W032-CF16-DELTA-01 pinned "
            "the same map 11311ab3600514cd and the same detector c266dbceca87, and both reproduce 0/17 "
            "first-order C0/C2 assertions; my run used a separately written classifier and a separate label "
            "set and adds a converse false-negative scan over all 207 claims (0 unflagged genuine). "
            "worker-093's self-mint prediction is confirmed by my drift observation: the live map at "
            "f06d40a8226a has exactly 3 extra hard entries, all from w093-metagrowth-20260912T0049-claim. "
            "Deduction only for the claim's scope wording: the metagrowth claim is itself meta-traffic, so a "
            "future reader should not treat the live hard count as a monotone evidence signal."
        ),
        "evidence_refs": [
            f"{D}/report.json#e9a185ba9fdfeeb2",
            "artifacts/worker-093/classsep_metagrowth/report.json#9d8574474639",
            f"{D}/drift_observation.json#8d2919f4fbb41c9c",
        ],
    })
    ev.append({
        "event_id": f"w032-cf16delta-{stamp}-status-complete",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-032",
        "node_id": "A1",
        "class_id": CLASS_ID,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "W032-CF16-DELTA-01 complete from the worker side (node completion NOT claimed). CHECKPOINT + EXIT. "
            f"checkpoint artifacts/worker-032/cf16-delta/CHECKPOINT.json#{ckpt_sha[:16]} (state copy "
            f"runtime/state/w032_cf16_delta_checkpoint_1.json, same sha256 {ckpt_sha[:16]}). Result: 17/17 hard findings "
            "mention-level, 7/7 new findings adjudicated as meta-traffic, 0 genuine, 0 composite class tokens, "
            "converse scan 0 unflagged genuine, controls pass, regression PASS. No gate verdict, no "
            "validation_status=passed, no canonical file or claim text edited."
        ),
        "evidence_refs": [
            f"{D}/CHECKPOINT.json#{ckpt_sha[:16]}",
            f"runtime/state/w032_cf16_delta_checkpoint_1.json#{ckpt_sha[:16]}",
            f"{D}/report.json#e9a185ba9fdfeeb2",
        ],
        "next_falsifier": (
            "Re-run adjudicate_delta.py against a fresh pin: any GENUINE_ASSERTION label, any composite class "
            "token inside a flagged claim's class_id, or any unflagged first-order merge assertion in the "
            "converse scan falsifies this measurement."
        ),
    })

    for e in ev:
        try:
            validate_event(e)
        except Exception as exc:  # noqa: BLE001
            print(f"SELF-REJECT: event {e.get('event_id')} invalid: {exc}", file=sys.stderr)
            return 1
    with OUT.open("a") as f:
        for e in ev:
            f.write(json.dumps(e) + "\n")
    print(f"appended {len(ev)} events to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
