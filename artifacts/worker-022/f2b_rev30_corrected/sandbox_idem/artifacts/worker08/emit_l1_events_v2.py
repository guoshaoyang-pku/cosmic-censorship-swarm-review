#!/usr/bin/env python3
"""Append worker-08's L1 v2 events (15 rows, lead-schema shard; shared ledger untouched)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
ART = REPO / "artifacts" / "worker08"
LEDGER = REPO / "ledger"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-08"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


shard_jsonl = LEDGER / "citation_audit_wcc_flash-08.jsonl"
shard_csv = LEDGER / "citation_audit_wcc_flash-08.csv"
lead_shard = LEDGER / "citation_audit_wcc_flash-08.lead_schema.csv"
fetch_log = ART / "l1_fetch_log.json"
report = ART / "l1_wcc_citation_report.json"
shared = LEDGER / "citation_audit.csv"
rep = json.loads(report.read_text())

events = [
    {
        "event_id": "e08-art-20260911T2342-l1-citation-audit-v2",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "literature",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "artifact_type": "citation_audit_rows",
        "path": "ledger/citation_audit_wcc_flash-08.jsonl",
        "sha256": sha(shard_jsonl),
        "validation_status": "unverified",
        "supersedes": "e08-art-20260911T2324-l1-citation-audit",
        "row_count": rep["row_count"],
        "verdict_counts": rep["verdict_counts"],
        "class_counts": rep["class_counts"],
        "lead_schema_shard": {"path": "ledger/citation_audit_wcc_flash-08.lead_schema.csv",
                              "sha256": sha(lead_shard),
                              "rows": rep["merge"]["rows"],
                              "status_counts": rep["merge"]["status_counts"]},
        "shard_csv": {"path": "ledger/citation_audit_wcc_flash-08.csv", "sha256": sha(shard_csv)},
        "fetch_log": {"path": "artifacts/worker08/l1_fetch_log.json", "sha256": sha(fetch_log)},
        "report": {"path": "artifacts/worker08/l1_wcc_citation_report.json", "sha256": sha(report)},
        "shared_path_correction": (
            "ledger/citation_audit.csv is OWNED by lead-literature and was rewritten by them under a "
            "different schema (citation_id/bibkey/.../reviewer; 72 rows). Worker-08 did NOT write to it. "
            "The shared-file sha256 in the superseded rev1 event no longer refers to that file. Merge "
            "instruction: the lead-schema shard above, de-duplicated on doi/arxiv_id."
        ),
        "shared_path_state": {"path": "ledger/citation_audit.csv", "sha256": sha(shared),
                              "owner": "lead-literature", "touched_by_worker_08": False},
        "schema_gaps": rep["merge"]["schema_gaps"],
        "evidence_refs": [
            "comms/inbox/deepseek-flash-08.jsonl#asg-2026-09-11-L1-deepseek-flash-08-17",
            "artifacts/worker08/l1_wcc_citation_report.json#" + sha(report)[:8],
        ],
        "next_falsifier": rep["next_falsifier"],
    },
    {
        "event_id": "e08-status-20260911T2342-l1-v2",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "literature",
        "node_id": "L1",
        "status": "active",
        "hours": 3.5,
        "summary": (
            "L1 delta: +2 rows (15 total). New: Christodoulou 1999 CQG 16 A23 (IOP abstract read) is the "
            "most direct primary formulation source found for precise AF-vacuum WCC/SCC conjectures, and "
            "Dafermos-Rodnianski 2013 Clay lectures (survey/context, no class theorem). WCC scope finding "
            "unchanged: all AF-WCC-VAC-GEN support located is perturbative; Christodoulou 1999 part 2 is "
            "the scalar class; Ringstrom 2008 remains unresolved. Deliverable adapts to the fact that "
            "lead-literature owns ledger/citation_audit.csv under a different schema: full-fidelity shard "
            "+ lead-schema shard (W08-001..W08-015) provided; shared file not touched. Lead schema lacks "
            "class_id, what-it-does-not-prove and an 'unresolved' status - extension request attached. "
            "G-LIT review/spot checks still pending; no completion claimed."
        ),
        "evidence_refs": [
            "ledger/citation_audit_wcc_flash-08.lead_schema.csv#" + sha(lead_shard)[:8],
            "ledger/citation_audit_wcc_flash-08.jsonl#" + sha(shard_jsonl)[:8],
            "ledger/citation_audit.csv#" + sha(shared)[:8] + " (lead-owned, untouched)",
        ],
        "next_falsifier": rep["next_falsifier"],
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing.add(json.loads(line)["event_id"])
            except (ValueError, KeyError):
                pass

added = []
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in events:
        if ev["event_id"] in existing:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        added.append(ev["event_id"])
print(json.dumps({"added": added, "total_events": len(existing) + len(added),
                  "rows": rep["row_count"]}, indent=2))
