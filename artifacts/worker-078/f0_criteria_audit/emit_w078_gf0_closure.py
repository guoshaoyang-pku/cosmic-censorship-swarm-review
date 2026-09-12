#!/usr/bin/env python3
"""Idempotent closure emitter for worker-078 W078-GF0-CRITERIA-AUDIT-01.

Appends one final `status` event recording the post-run outcome: the 00:48:44 lifecycle pass set
G-F0 to `pass`, and its audit reason counts 5 distinct accept reviewers including worker-078.
Fixed event id: re-running is a no-op.

Usage: python3 emit_w078_gf0_closure.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms" / "outbox" / "worker-078.jsonl"
CREATED = "2026-09-12T00:53:00+08:00"
PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def build() -> list:
    f_review = "reviews/F0-criteria-audit-078.json"
    f_ckpt = "runtime/state/w078_checkpoint_5_gf0_criteria_audit.json"
    f_map = "research_map/research_map.json"
    return [{
        "event_id": "w078-gf0crit-closure-postrun",
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
            "POST-RUN CLOSURE NOTE (observed after the audit events were emitted; not part of "
            "the audited evidence chain). The 00:48:44 lifecycle pass set G-F0 to pass; its "
            "controller audit reason now reads 'review scan at this hash: 5 distinct accept "
            "reviewer(s) [deepseek-flash-18, deepseek-flash-19, worker-025, worker-038, "
            "worker-078]' at the pinned F0 hash, so this review was counted and the criterion "
            "clause it audited is satisfied. Residual, for the controller: gates[G-F0].unmet "
            "still carries pass-04 text (unmet[0] cites superseded 66bf917bd368); G-F0 passing "
            "alone does not pass G-AUDIT, whose A1 coverage still needs >=2 accepts for F1/F2a/"
            "F2b/L0, and N1 remains locked by G-FORM + G-AUDIT. Worker-078 exits; no further "
            "work claimed."
        ),
        "evidence_refs": [
            f"{f_map}#{sha(f_map)[:12]}",
            f"{f_review}#{sha(f_review)[:12]}",
            f"{f_ckpt}#{sha(f_ckpt)[:12]}",
            "research_map/formulation_taxonomy.yaml#" + PIN[:12],
        ],
        "next_falsifier": (
            "A later map revision that removes G-F0 pass, or whose audit reason at the pinned "
            "hash lists fewer than 5 distinct accepts, falsifies the closure observation. "
            "Re-measure " + f_map + " before citing this note."
        ),
        "artifact": "artifacts/worker-078/f0_criteria_audit/",
        "completion_scope": "worker lifecycle closure only; not a node done / gate verdict",
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
