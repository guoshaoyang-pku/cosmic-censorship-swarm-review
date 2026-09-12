#!/usr/bin/env python3
"""Idempotent addendum emitter for worker-078 W078-GF0-CRITERIA-AUDIT-01.

Appends one `status` addendum event that reconciles the primary batch with the map write that
landed at 00:43:08 (map sha256 11311ab36005): G-F0's audit reason had already been refreshed to
4 distinct accepts, this review makes worker-078 the fifth, and `gates[G-F0].unmet[0]` still
cites a superseded hash.  Fixed event id: re-running is a no-op.

Usage: python3 emit_w078_gf0_addendum.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-078.jsonl"
CREATED = "2026-09-12T00:50:00+08:00"
PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def build() -> list:
    f_review = "reviews/F0-criteria-audit-078.json"
    f_report = "artifacts/worker-078/f0_criteria_audit/report.json"
    f_readme = "artifacts/worker-078/f0_criteria_audit/README.md"
    f_ckpt = "runtime/state/w078_checkpoint_5_gf0_criteria_audit.json"
    eid = "w078-gf0crit-addendum-mapwrite"
    return [{
        "event_id": eid,
        "event_type": "status",
        "created_at": CREATED,
        "actor": "worker-078",
        "task_id": "W078-GF0-CRITERIA-AUDIT-01",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "gate": "G-F0",
        "status": "active",
        "hours": 0.1,
        "summary": (
            "ADDENDUM to W078-GF0-CRITERIA-AUDIT-01 (adds to, does not replace, the "
            "w078-gf0crit-* batch; no verdict change: accept_with_notes, 11 PASS / 1 WARN / 0 "
            "FAIL at pin 0abb9ed8a961). Reconciliation with the map write that landed at "
            "00:43:08 (research_map.json sha256 11311ab36005): (1) the G-F0 controller audit "
            "reason had already been refreshed to 4 distinct accepts "
            "['deepseek-flash-18','deepseek-flash-19','worker-025','worker-038'] at the pinned "
            "hash, so note W078-GF0-04 is narrowed - the review makes worker-078 the fifth "
            "distinct full-accept reviewer (verified by an isolated mirror scan of "
            "astra_lifecycle.review_coverage), and the still-stale item is "
            "gates[G-F0].unmet[0], which cites superseded hash 66bf917bd368; (2) the audit "
            "binding is unaffected because research_map/formulation_taxonomy.yaml still "
            "measures 0abb9ed8a961 at start and end of run; (3) the review body and README were "
            "updated in place for this reconciliation, so their hashes recorded in the earlier "
            "artifact events are superseded by the hashes in this addendum. Read-only on "
            "canonical paths; no gate verdict or node transition."
        ),
        "evidence_refs": [
            f"{f_review}#{sha(f_review)[:12]}",
            f"{f_report}#{sha(f_report)[:12]}",
            f"{f_readme}#{sha(f_readme)[:12]}",
            f"{f_ckpt}#{sha(f_ckpt)[:12]}",
            "research_map/research_map.json#11311ab36005",
            "research_map/formulation_taxonomy.yaml#" + PIN[:12],
        ],
        "next_falsifier": (
            "Re-measure research_map/formulation_taxonomy.yaml: a hash other than " + PIN +
            " voids the F0 audit binding. Re-run audit_gf0_criteria_078.py --pin " + PIN +
            " and obtain any failed check or a report differing from report.json modulo "
            "timestamps. A lifecycle pass showing fewer than 5 distinct accepts at the pinned "
            "hash would falsify the fifth-reviewer claim; a ruling that unmet[0] is not stale "
            "would falsify the reconciliation note."
        ),
        "artifact": "artifacts/worker-078/f0_criteria_audit/",
        "completion_scope": "worker lifecycle addendum only; not a node done / gate verdict",
    }]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    events = build()
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    new = [e for e in events if e["event_id"] not in existing]
    print(json.dumps({"planned": len(events), "already_present": len(events) - len(new),
                      "to_append": len(new), "ids": [e["event_id"] for e in new]}))
    if args.dry_run or not new:
        return 0
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
