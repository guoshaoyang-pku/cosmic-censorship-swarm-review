#!/usr/bin/env python3
"""Emit the W098-F2B-BLOCKER-ADJ-01 outbox events (idempotent by event_id).

Appends status / artifact / review / blocker / status(done) events to
comms/outbox/worker-098.jsonl.  Every event is validated against
research_map/schemas.validate_event before it is written; a message is not a
result, the cited artifact hashes are.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-098/f2b_blocker_adjudication"
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
EV = HERE / "f2b_blocker_adjudication_evidence.json"
RV = HERE / "f2b_blocker_adjudication_review.json"
RV_PUB = ROOT / "reviews/F2b-blocker-adjudication-worker-098.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ev = json.loads(EV.read_text())
    rv = json.loads(RV.read_text())
    ev_h, rv_h = sha(EV), sha(RV_PUB)
    now = datetime.now(CST).replace(microsecond=0).isoformat()
    f2b = ev["reviewed_sha256"]
    f0 = ev["hashes"]["canonical_f0_at_start"]
    falsifier = ev["next_falsifier"]
    node, cls, task = "F2b", "AF-SCC-C0-VAC-GEN", ev["task_id"]

    events = [
        {
            "event_id": f"w098-f2b-blk-status-{now}",
            "event_type": "status", "created_at": now, "actor": "worker-098",
            "node_id": node, "class_id": cls, "status": "active", "hours": 0.1,
            "summary": (
                f"{task}: independent adjudication of the four BLOCKING/MAJOR findings raised "
                f"on {cls} at live canonical {f2b[:12]}. Result: B1 duplicate-key CONFIRMED "
                "live, B2 D0-typing CONFIRMED live and family-wide, B3 pointer-unresolved "
                "CONFIRMED but scope-corrected to the F0 publication gap, B4 map-pin NOT live "
                "(repaired). Emits a revise verdict, score 3.0. No node completion, no gate "
                "verdict, no theorem claimed."),
            "evidence_refs": [
                f"schemas/af_scc_c0_vacuum.yaml#{f2b[:12]}",
                f"artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json#{ev_h[:12]}",
                f"research_map/formulation_taxonomy.yaml#{f0[:12]}",
            ],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w098-f2b-blk-art-evidence-{now}",
            "event_type": "artifact", "created_at": now, "actor": "worker-098",
            "node_id": node, "class_id": cls, "artifact_type": "review_evidence",
            "path": "artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json",
            "sha256": ev_h, "validation_status": "unverified",
            "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{f2b[:12]}"],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w098-f2b-blk-art-review-{now}",
            "event_type": "artifact", "created_at": now, "actor": "worker-098",
            "node_id": node, "class_id": cls, "artifact_type": "review_record",
            "path": "reviews/F2b-blocker-adjudication-worker-098.json",
            "sha256": rv_h, "validation_status": "unverified",
            "evidence_refs": [
                "artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json"
                f"#{ev_h[:12]}",
            ],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w098-f2b-blk-review-{now}",
            "event_type": "review", "created_at": now, "actor": "worker-098",
            "reviewer": "worker-098", "target_id": node, "class_id": cls,
            "verdict": rv["verdict"], "score": rv["score"],
            "reviewed_sha256": f2b,
            "hard_failures": rv["hard_failures"],
            "findings": rv["findings"],
            "evidence_refs": rv["evidence_refs"],
            "artifact_refs": rv["artifact_refs"],
            "scope_limit": rv["scope_limit"],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w098-f2b-blk-blocker-{now}",
            "event_type": "blocker", "created_at": now, "actor": "worker-098",
            "node_id": node, "class_id": cls,
            "description": (
                "B1 (live): 8 top-level `revised_at` keys (7 duplicates) make the canonical "
                "bytes fail strict duplicate-key YAML readers while the canonical gate still "
                "returns PASS. B2 (live, family-wide): the `forall (s,delta)` binder ranges over "
                "D0, a disjunction whose smooth-with-decay branch has no (s,delta) values and a "
                "Frechet ambient topology; the same defect shape is in F1/F2a/F2b. B3 (systemic): "
                "class_contract_pointer resolves only in the authoring supplement, not in the "
                "controller-authoritative canonical F0 tree."),
            "needed_to_unblock": (
                "(i) keep one `revised_at` and move the delta history to a list/comment; "
                "(ii) split D0 per branch or split the binder so the smooth class is well typed; "
                "(iii) publish the class_contracts block canonically or make the pointer "
                "canonical-resolvable. Re-run the blocker probes against the repaired bytes."),
            "evidence_refs": [
                "artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json"
                f"#{ev_h[:12]}",
                "reviews/F2b-blocker-adjudication-worker-098.json" + f"#{rv_h[:12]}",
            ],
        },
        {
            "event_id": f"w098-f2b-blk-done-{now}",
            "event_type": "status", "created_at": now, "actor": "worker-098",
            "node_id": node, "class_id": cls, "status": "active",
            "completion_claim": True, "hours": 0.4,
            "summary": (
                f"{task} complete as a bounded task: verdict revise 3.0 at {f2b[:12]}, evidence "
                "and review artifacts hash-pinned, four claims adjudicated with reproductions, "
                "6/6 controls detected, gate-alone blind spots measured (duplicate keys, D0 "
                "typing, sibling check), no drift during review. This is a completion claim for "
                "the bounded task only, not node completion, not a gate verdict; lead/controller "
                "must ingest and decide."),
            "evidence_refs": [
                "artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json"
                f"#{ev_h[:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{f2b[:12]}",
            ],
            "next_falsifier": falsifier,
        },
    ]

    for e in events:
        validate_event(e)

    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line)["event_id"])
            except Exception:  # noqa: BLE001
                pass
    fresh = [e for e in events if e["event_id"] not in seen]
    with OUTBOX.open("a") as f:
        for e in fresh:
            f.write(json.dumps(e) + "\n")
    print(json.dumps({"emitted": len(fresh), "skipped_existing": len(events) - len(fresh),
                      "outbox": str(OUTBOX.relative_to(ROOT)),
                      "evidence_sha256": ev_h, "review_sha256": rv_h,
                      "verdict": rv["verdict"], "score": rv["score"],
                      "reviewed_sha256": f2b}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
