#!/usr/bin/env python3
"""Emit W075-L0-REV3-INDEP-VERDICT-01 outputs:
  1. reviews/L0-review-075-rev3.json   (verdict record, countable by coverage tooling)
  2. comms/outbox/worker-075.jsonl     (status, 4 artifacts, review, claim)
Every event is validated with research_map.schemas.validate_event before it is written.
Read-only with respect to ledger/, research_map/ and runtime/ (only its own files are written).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TAG = "w075-l0rev3"

ART = {
    "report": HERE / "report.json",
    "harness": HERE / "run_l0rev3_review_075.py",
    "verifier": HERE / "verify_l0rev3_review_075.py",
    "readme": HERE / "README.md",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rep = json.loads(ART["report"].read_text())
    hashes = {k: sha(p) for k, p in ART.items()}
    ledger_sha = rep["inputs"]["ledger_sha"]
    audit_sha = rep["inputs"]["audit_sha"]

    review = {
        "review_id": rep["review_id"],
        "event_type": "review",
        "target_id": "L0",
        "target": "ledger/theorems.jsonl",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": rep["class_ids"],
        "reviewer": "worker-075",
        "reviewer_independence": "authored neither the ledger nor any prior L0 verdict",
        "artifact_sha256": ledger_sha,
        "reviewed_sha256": ledger_sha,
        "companion": {"path": "ledger/citation_audit.csv", "sha256": audit_sha},
        "verdict": rep["verdict"]["verdict"],
        "score": rep["verdict"]["score"],
        "hard_failures": rep["verdict"]["hard_failures"],
        "open_objections": rep["verdict"]["open_objections"],
        "findings": [
            f"{c['id']}: {'PASS' if c['ok'] else 'FAIL'} — {c['detail']}" for c in rep["checks"]
        ],
        "controls": f"{sum(1 for c in rep['controls'] if c['detected'])}/{len(rep['controls'])} detected",
        "snapshot_stable": rep["snapshot_stable"],
        "counts_as_full_schema_verdict": True,
        "verdict_scope": rep["verdict_scope"],
        "documented_blind_spots": rep["documented_blind_spots"],
        "peer_work_at_same_hash": rep["independence"]["peer_verdict_at_same_hash"],
        "evidence_refs": [
            f"ledger/theorems.jsonl#{ledger_sha[:12]}",
            f"ledger/citation_audit.csv#{audit_sha[:12]}",
            f"artifacts/worker-075/l0_rev3_review/report.json#{hashes['report'][:12]}",
            f"artifacts/worker-075/l0_rev3_review/run_l0rev3_review_075.py#{hashes['harness'][:12]}",
            f"artifacts/worker-075/l0_rev3_review/verify_l0rev3_review_075.py#{hashes['verifier'][:12]}",
        ],
        "falsifier": rep["falsifier"],
        "measured_at": rep["measured_at"],
        "not_claimed": rep["not_claimed"],
    }
    rev_path = ROOT / "reviews" / "L0-review-075-rev3.json"
    rev_path.write_text(json.dumps(review, indent=1, ensure_ascii=False))
    rev_sha = sha(rev_path)

    tail = rep["verdict"]["open_objections"]
    events = [
        {
            "event_id": f"{TAG}-status", "event_type": "status", "created_at": NOW,
            "actor": "worker-075", "node_id": "L0", "gate": "G-LIT",
            "class_ids": rep["class_ids"], "status": "active", "hours": 0.5,
            "summary": (
                "Second independent L0 rev-3 verdict at ledger/theorems.jsonl#a1674f094979 "
                "(BL-7 request): accept 4.0, 0 hard failures, 2 rubric-scope objections, "
                "11/11 checks and 8/8 mutation controls pass, snapshot stable. Worker level only: "
                "no gate verdict, no node completion."),
            "evidence_refs": [f"ledger/theorems.jsonl#{ledger_sha[:12]}",
                              f"reviews/L0-review-075-rev3.json#{rev_sha[:12]}",
                              f"artifacts/worker-075/l0_rev3_review/report.json#{hashes['report'][:12]}"],
            "next_falsifier": rep["falsifier"],
        },
        *[
            {
                "event_id": f"{TAG}-artifact-{name}", "event_type": "artifact", "created_at": NOW,
                "actor": "worker-075", "node_id": "L0", "gate": "G-LIT",
                "class_ids": rep["class_ids"], "artifact_type": t,
                "path": str(p.relative_to(ROOT)), "sha256": hashes[name],
                "validation_status": "unverified",
                "evidence_refs": [f"ledger/theorems.jsonl#{ledger_sha[:12]}"],
            }
            for name, t in (("report", "review_report"), ("harness", "repro_script"),
                            ("verifier", "repro_script"), ("readme", "summary"))
            for p in [ART[name]]
        ],
        {
            "event_id": f"{TAG}-artifact-verdict-record", "event_type": "artifact",
            "created_at": NOW, "actor": "worker-075", "node_id": "L0", "gate": "G-LIT",
            "class_ids": rep["class_ids"], "artifact_type": "review_verdict",
            "path": "reviews/L0-review-075-rev3.json", "sha256": rev_sha,
            "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-075/l0_rev3_review/report.json#{hashes['report'][:12]}"],
        },
        {
            "event_id": f"{TAG}-review", "event_type": "review", "created_at": NOW,
            "actor": "worker-075", "target_id": "L0", "reviewer": "worker-075",
            "node_id": "L0", "gate": "G-LIT", "class_ids": rep["class_ids"],
            "artifact_sha256": ledger_sha, "reviewed_sha256": ledger_sha,
            "verdict": rep["verdict"]["verdict"], "score": rep["verdict"]["score"],
            "hard_failures": rep["verdict"]["hard_failures"],
            "findings": review["findings"] + [f"OPEN OBJECTION: {o}" for o in tail],
            "controls": review["controls"], "counts_as_full_schema_verdict": True,
            "peer_work_at_same_hash": review["peer_work_at_same_hash"],
            "evidence_refs": review["evidence_refs"],
            "falsifier": rep["falsifier"],
        },
        {
            "event_id": f"{TAG}-claim", "event_type": "claim", "created_at": NOW,
            "actor": "worker-075", "node_id": "L0", "gate": "G-LIT",
            "class_id": ";".join(rep["class_ids"]), "conclusion_type": "stability_result",
            "claims_theorem_status": False,
            "statement": (
                "Artifact-and-checker result (not a mathematics claim): at ledger/theorems.jsonl "
                f"#{ledger_sha[:12]} the L0 rev-3 ledger is honest and well-bound under the G-LIT "
                "criteria — 62/62 rows carry a non-empty unresolved list, 92/92 cited sources "
                "resolve in citation_audit.csv (97/97 resolved), 0 rows carry the retired axes, "
                "content_status is 50 verified / 11 provisional / 1 rejected, all 62 rows are "
                "labelled not_independently_reviewed, and every AF-* token resolves to the four "
                "frozen classes. The rubric-literal HF-01/HF-02 detectors fire on 30 theorem rows "
                "and 8 multi-class rows respectively; independent classification finds no union "
                "class definition and no fluent-text promotion, so both are rubric-scope "
                "objections rather than ledger hard failures."),
            "assumptions": [
                "ledger/theorems.jsonl a1674f094979 and ledger/citation_audit.csv 315c19145065 are "
                "the current canonical bytes; either moving voids this measurement",
                "worker-075 authored neither the ledger nor any prior L0 verdict",
                "the verdict covers the L0/G-LIT node criteria, not per-row mathematical entailment",
            ],
            "falsifier": rep["falsifier"],
            "evidence_refs": review["evidence_refs"],
            "artifact_refs": ["artifacts/worker-075/l0_rev3_review/report.json",
                              "reviews/L0-review-075-rev3.json"],
        },
    ]

    rejected = []
    for e in events:
        try:
            validate_event(e)
        except SchemaError as ex:
            rejected.append((e.get("event_id"), str(ex)))
    if rejected:
        print("SCHEMA REJECTS:", rejected, file=sys.stderr)
        return 2

    out = ROOT / "comms" / "outbox" / "worker-075.jsonl"
    with out.open("a") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"wrote {rev_path.relative_to(ROOT)} sha256={rev_sha[:12]}")
    print(f"appended {len(events)} events to {out.relative_to(ROOT)}")
    for e in events:
        print(" ", e["event_id"], "|", e["event_type"], "|",
              e.get("sha256", e.get("verdict", ""))[:12] if isinstance(e.get("sha256", e.get("verdict", "")), str) else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
