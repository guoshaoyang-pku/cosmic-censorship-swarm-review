#!/usr/bin/env python3
"""One bounded self-erratum for W010-F2A-C2-CONFORMANCE-REV13-01 (event-stream honest fix).

The four c2rev13 events emitted at 2026-09-12T01:08:31 were accepted into
research_map/events.jsonl before this defect was noticed, so they are immutable. The defect
is informational only:

  claim event w010-20260912T010831-c2rev13-claim, field `corrects.artifact`, held the string
  "artifacts/worker-010/c2_conformance_rev13/class_binding_reconcile/binding_reconcile_audit.json"
  built by string replacement. The audited CBR artifact actually lives at
  artifacts/worker-010/class_binding_reconcile/binding_reconcile_audit.json
  (sha256 dc391cad38cd..., which the same field carried correctly).

No evidence_ref / artifact_ref / count / verdict depends on it: every reference in the four
events was re-verified as an existing path with a matching sha256 prefix (0 problems). This
script appends ONE idempotent `status` event recording the correction; it does not modify the
result JSON, the checkpoint, the reports, or any previously written outbox line.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-010.jsonl"
CST = timezone(timedelta(hours=8))
EVENT_ID = "w010-c2rev13-erratum-pathfix-20260912T010831"
CBR = "artifacts/worker-010/class_binding_reconcile/binding_reconcile_audit.json"
RESULT = "artifacts/worker-010/c2_conformance_rev13/W010_F2A_C2_REV13_result.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    if EVENT_ID in existing:
        print("erratum already present, nothing to do:", EVENT_ID)
        return 0

    cbr_sha = sha256(ROOT / CBR)
    result_sha = sha256(ROOT / RESULT)
    now = datetime.now(CST).isoformat(timespec="seconds")
    event = {
        "event_id": EVENT_ID,
        "event_type": "status",
        "created_at": now,
        "actor": "worker-010",
        "run_id": "run-2026-09-11T23:15+08:00",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "task_id": "W010-F2A-C2-CONFORMANCE-REV13-01",
        "status": "active",
        "hours": 0.05,
        "summary": (
            "Self-erratum, informational field only. The accepted claim event "
            "w010-20260912T010831-c2rev13-claim carries corrects.artifact = "
            "'artifacts/worker-010/c2_conformance_rev13/class_binding_reconcile/"
            "binding_reconcile_audit.json' (a path built by string replacement); the audited "
            "CBR artifact is at 'artifacts/worker-010/class_binding_reconcile/"
            "binding_reconcile_audit.json' with sha256 " + cbr_sha[:12] + ", which the same "
            "field carried correctly as artifact_sha256. All evidence_refs and artifact_refs "
            "of the four c2rev13 events were re-verified after ingestion: every path exists "
            "and every sha256 prefix matches (0 problems), so no count, verdict, direction "
            "reading, or gate state depends on the wrong string. The emitter source is fixed "
            "in place; the accepted event is not rewritten."
        ),
        "defect": {
            "event_id": "w010-20260912T010831-c2rev13-claim",
            "field": "corrects.artifact",
            "observed": "artifacts/worker-010/c2_conformance_rev13/class_binding_reconcile/"
                        "binding_reconcile_audit.json",
            "correct": CBR,
            "sha256_of_target": cbr_sha,
            "impact": "informational only; artifact_sha256, evidence_refs and artifact_refs "
                      "were already correct and hash-verified; no promotion, gate or "
                      "conclusion depends on the string",
            "repair": "emit_w010_c2_events.py now hardcodes the canonical CBR path; the "
                      "accepted event stays as written per PROTOCOL.md immutability of the "
                      "accepted stream",
        },
        "evidence_refs": [f"{CBR}#{cbr_sha[:12]}", f"{RESULT}#{result_sha[:12]}"],
        "next_falsifier": "A path string in any accepted worker-010 event that does not "
                          "resolve to the file whose sha256 prefix it carries.",
        "validation_status": "unverified",
        "claims_completion": False,
    }
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    print("appended", EVENT_ID)
    print("cbr sha256:", cbr_sha)
    print("result sha256 unchanged:", result_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
