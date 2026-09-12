#!/usr/bin/env python3
"""Emit worker-006 L0 review events to comms/outbox/worker-006.jsonl (append-only).

Fail-closed: aborts if ledger/citation hashes moved or the review file's verdict
does not match the composed checks. Validates every event against
research_map/events.schema.json and runs `comms.py ingest --dry-run` afterwards.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LEDGER = REPO / "ledger" / "theorems.jsonl"
AUDIT = REPO / "ledger" / "citation_audit.csv"
REVIEW = REPO / "reviews" / "L0-review-worker-006.json"
OUTBOX = REPO / "comms" / "outbox" / "worker-006.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
TAG = "w006-20260912T0033-l0-rev3"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    checks = json.loads((HERE / "checks.json").read_text())
    pins = checks["pins"]
    if sha256(LEDGER) != pins["ledger_sha256"] or sha256(AUDIT) != pins["audit_sha256"]:
        print("FAIL-CLOSED: pinned artifact moved; refusing to emit", file=sys.stderr)
        return 2
    review = json.loads(REVIEW.read_text())
    if review["verdict"] != ("accept" if not checks["hard_failures"] else "revise"):
        print("FAIL-CLOSED: review verdict inconsistent with checks", file=sys.stderr)
        return 2

    ledger_h, audit_h = pins["ledger_sha256"], pins["audit_sha256"]
    review_h = sha256(REVIEW)
    checks_h = sha256(HERE / "checks.json")
    runner_h = sha256(HERE / "review_l0_006.py")
    ev = [
        {
            "event_id": f"{TAG}-artifact-review",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-006",
            "node_id": "L0",
            "artifact_type": "l0_review",
            "path": "reviews/L0-review-worker-006.json",
            "sha256": review_h,
            "validation_status": "unverified",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
            "summary": (f"Independent L0 ledger review at ledger {ledger_h[:12]}: verdict "
                        f"{review['verdict']} score {review['score']}, hard failure "
                        f"{review['hard_failures']}. Full-scope, hash-pinned."),
            "evidence_refs": [f"ledger/theorems.jsonl#sha256:{ledger_h}",
                              f"reviews/L0-review-worker-006.json#sha256:{review_h}"],
            "falsifier": review["falsifier"],
        },
        {
            "event_id": f"{TAG}-artifact-checks",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-006",
            "node_id": "L0",
            "artifact_type": "l0_review_harness",
            "path": "artifacts/worker-006/l0_review/checks.json",
            "sha256": checks_h,
            "validation_status": "unverified",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
            "summary": (f"19 reproducible checks over 62 ledger rows; hard: "
                        f"{checks['hard_failures']}; soft: {checks['soft_findings']}. "
                        f"Runner sha256 {runner_h[:12]}."),
            "evidence_refs": [f"artifacts/worker-006/l0_review/checks.json#sha256:{checks_h}",
                              f"artifacts/worker-006/l0_review/review_l0_006.py#sha256:{runner_h}"],
            "falsifier": ("A re-run at the pinned hashes yielding different check results "
                          "voids the harness's evidence value."),
        },
        {
            "event_id": f"{TAG}-review",
            "event_type": "review",
            "created_at": NOW,
            "actor": "worker-006",
            "node_id": "L0",
            "target_id": "L0",
            "reviewer": "worker-006",
            "verdict": review["verdict"],
            "score": review["score"],
            "hard_failures": review["hard_failures"],
            "findings": review["findings"],
            "artifact_sha256": ledger_h,
            "counts_as_full_schema_verdict": True,
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
            "evidence_refs": review["evidence_refs"],
            "falsifier": review["falsifier"],
        },
        {
            "event_id": f"{TAG}-status",
            "event_type": "status",
            "created_at": NOW,
            "actor": "worker-006",
            "node_id": "L0",
            "status": "active",
            "hours": 0.5,
            "summary": (f"One class-bound task, final state: independent L0 review at ledger "
                        f"{ledger_h[:12]} -> {review['verdict']} ({review['hard_failures'] or 'no hard failures'}). "
                        "The literature lead republished the ledger at 00:30:49 with row-level provenance "
                        "(review_status=not_independently_reviewed, acceptance_authority=author self-assessment, "
                        "status=included_unreviewed), closing HF-14; this is the fresh hash-pinned verdict. "
                        "The earlier review at ce42d205e761 (revise, HF-14) is preserved as "
                        "reviews/L0-review-worker-006-superseded-ce42d205.json and its event batch "
                        "w006-20260912T0025-l0-* binds that superseded hash. No gate verdict is claimed. "
                        "Checkpoint: runtime/state/w006_checkpoint_7.json (worker-local)."),
            "evidence_refs": [f"ledger/theorems.jsonl#sha256:{ledger_h}",
                              f"reviews/L0-review-worker-006.json#sha256:{review_h}",
                              "evaluation_rubric.yaml#hard_failures.HF-14",
                              "reviews/L0-review-21.json", "reviews/L0-review-22.json"],
            "next_falsifier": ("A controller adjudication that HF-14 is claim-scoped only "
                               "(which would make this revise vacuous), or a new L0 revision "
                               "with row-level reviewer/artifact provenance re-reviewed at "
                               "its own hash."),
        },
    ]

    # authoritative validation: the controller's own normalize+validate path
    sys.path.insert(0, str(REPO / "research_map"))
    import comms  # noqa: E402
    from schemas import SchemaError  # noqa: E402
    for e in ev:
        doc = dict(e)
        doc["_received_at"] = NOW
        doc = comms.normalize_event(doc, "comms/outbox/worker-006.jsonl")
        try:
            comms.validate_event(doc)
        except SchemaError as ex:
            print(f"FAIL-CLOSED: event {e['event_id']} rejected by controller validator: {ex}",
                  file=sys.stderr)
            return 2

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    if any(e["event_id"] in existing for e in ev):
        print("idempotent: events already emitted; nothing appended")
        return 0
    with OUTBOX.open("a") as f:
        for e in ev:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    dry = subprocess.run([sys.executable, "research_map/comms.py", "ingest", "--dry-run"],
                         cwd=REPO, capture_output=True, text=True)
    blob = (dry.stdout or "") + (dry.stderr or "")
    rejected_mine = [e["event_id"] for e in ev if f"REJECT" in blob and e["event_id"] in blob]
    print("controller-validator: all events valid")
    print("appended", len(ev), "events to", OUTBOX.relative_to(REPO))
    print("dry-run rc", dry.returncode, "| my events rejected:", rejected_mine or "none")
    print(blob[-900:])
    return 0 if dry.returncode == 0 and not rejected_mine else 1


if __name__ == "__main__":
    sys.exit(main())
