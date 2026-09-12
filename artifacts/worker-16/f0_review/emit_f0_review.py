#!/usr/bin/env python3
"""Emit the W16-F0-INDEP-REVIEW-01 events to comms/outbox/worker-16.jsonl.

Fail-closed on target drift. Every event is validated with research_map.schemas
.validate_event before the JSON line is appended. Idempotent: an event_id that
already exists in the outbox is skipped.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TAX = "research_map/formulation_taxonomy.yaml"
PINNED = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
OUTBOX = "comms/outbox/worker-16.jsonl"
REVIEW = "reviews/F0-review-16.json"
D = "artifacts/worker-16/f0_review"
NOW = datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, p), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def existing_ids():
    p = os.path.join(ROOT, OUTBOX)
    ids = set()
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
    return ids


def main():
    measured = sha256_file(TAX)
    if measured != PINNED:
        print(f"FAIL-CLOSED: taxonomy drifted {measured} != {PINNED}", file=sys.stderr)
        return 2

    review = json.load(open(os.path.join(ROOT, REVIEW)))
    if review["artifact_sha256"] != measured:
        print("FAIL-CLOSED: review binds a different target hash", file=sys.stderr)
        return 2

    files = {
        "review": (REVIEW, "review_verdict",
                   "independent F0 review, verdict revise (3 blocking findings), bound to 276009f4f63d"),
        "checker": (f"{D}/check_f0.py", "validation_tool",
                    "fail-closed F0 taxonomy checker: hash pin, dup-key loader, 18 structural/semantic checks"),
        "results": (f"{D}/check_results.json", "check_report",
                    "checker output at the pinned hash: 13 PASS / 3 FAIL / 2 NOTE"),
        "controls": (f"{D}/controls.json", "control_report",
                     "P1 repaired fixture -> 0 FAIL; N1 wrong pin -> exit 2, no results file"),
        "report": (f"{D}/REPORT.md", "human_report",
                   "human-readable summary of the F0 review and controls"),
    }
    hashes = {k: sha256_file(v[0]) for k, v in files.items()}

    events = []

    def ev(eid, etype, **kw):
        e = {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": "worker-16"}
        e.update(kw)
        validate_event(e)
        events.append(e)

    ev("w16-F0-INDEP-REVIEW-01-claim-20260912T0024", "status",
       node_id="F0", status="active", hours=0.4,
       summary=("Took one class-bound task (no unclaimed F0 review existed for the 00:12/00:16 fleet): "
                "W16-F0-INDEP-REVIEW-01, independent full-schema review of the canonical F0 taxonomy at "
                "276009f4f63d. Result: 13 PASS / 3 FAIL / 2 NOTE; blocking findings B-16F0-1 (D1 set-based "
                "reading survives in AF-WCC-SCALAR-SPH), B-16F0-2 (D3 comeager binding missing there), "
                "B-16F0-3 (C2/C0 schema_owner point at map-recorded legacy aggregator). Controls P1/N1 pass."),
       evidence_refs=[f"{TAX}#276009f4f63d", REVIEW,
                      f"{D}/check_results.json", f"{D}/controls.json"],
       next_falsifier=("quote the pinned bytes to show the attributed reading is absent, or show "
                       "schemas/af_scc_regularities.yaml is canonical and not in map legacy_artifacts"))

    ev("w16-F0-INDEP-REVIEW-01-meta-20260912T0024", "claim",
       class_id="GLOBAL", statement=(
           "Artifact-and-checker result (not a mathematics claim): at research_map/formulation_taxonomy.yaml "
           "sha256 276009f4f63d, 3 of 18 deterministic checks FAIL - C10: the set-based J-(I+) visibility "
           "reading demoted by D1 is still used in the AF-WCC-SCALAR-SPH conclusion (line 406); C11: the D3 "
           "comeager binding recorded as explicit for each class is absent there (line 405); C13: the C2/C0 "
           "schema_owner pointers (lines 305, 374) target schemas/af_scc_regularities.yaml, which "
           "research_map.json legacy_artifacts records as a non-class aggregator. 13 PASS, 2 NOTE. Controls: "
           "repairing exactly those three defects yields 0 FAIL; a wrong hash pin exits 2 with no results."),
       conclusion_type="formal_model",
       assumptions=["target measured and stable at the pinned sha256",
                    "research_map.json read at the same wall-clock window",
                    "strict YAML loader with duplicate-key detection",
                    "reviewer is not an author of F0"],
       falsifier=review["falsifier"],
       evidence_refs=[f"{TAX}#276009f4f63d", f"{TAX}:406", f"{TAX}:75", f"{TAX}:72", f"{TAX}:405",
                      f"{TAX}:305", f"{TAX}:374", "research_map/research_map.json#legacy_artifacts"],
       artifact_refs=[REVIEW, f"{D}/check_results.json", f"{D}/controls.json"])

    for key, (path, atype, note) in files.items():
        ev(f"w16-F0-INDEP-REVIEW-01-artifact-{key}-20260912T0024", "artifact",
           node_id="F0", artifact_type=atype, path=path, sha256=hashes[key],
           validation_status="unverified", note=note,
           evidence_refs=[f"{TAX}#276009f4f63d"])

    review_event = dict(review)
    review_event["actor"] = "worker-16"
    validate_event(review_event)
    events.append(review_event)

    ev("w16-F0-INDEP-REVIEW-01-ckpt-20260912T0024", "status",
       node_id="F0", status="active", hours=0.4,
       summary=("CHECKPOINT: bounded class-bound task complete (worker-level, not a gate verdict). "
                "Deliverables on disk and hash-pinned: reviews/F0-review-16.json, "
                "artifacts/worker-16/f0_review/{check_f0.py,check_results.json,controls.json,REPORT.md}. "
                "Verdict revise 3.5 with 3 blocking findings; G-F0 still needs two independent accepts at "
                "one hash, so the lead should dispose B-16F0-1/2/3 and re-run the checker before any accept."),
       evidence_refs=[f"{TAX}#276009f4f63d", REVIEW, f"{D}/check_results.json", f"{D}/controls.json"],
       next_falsifier="re-run check_f0.py at the next revision; 0 FAIL is the acceptance test for the fixes")
    have = existing_ids()
    new = [e for e in events if e["event_id"] not in have]
    with open(os.path.join(ROOT, OUTBOX), "a") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"appended {len(new)}/{len(events)} events to {OUTBOX}")
    for k, v in hashes.items():
        print(f"  {k:8} {v}  {files[k][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
