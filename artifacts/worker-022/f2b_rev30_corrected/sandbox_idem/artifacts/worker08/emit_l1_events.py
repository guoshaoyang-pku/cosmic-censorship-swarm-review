#!/usr/bin/env python3
"""Append worker-08's L1 result events to comms/outbox/deepseek-flash-08.jsonl (idempotent)."""
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


shared = LEDGER / "citation_audit.csv"
shard_jsonl = LEDGER / "citation_audit_wcc_flash-08.jsonl"
shard_csv = LEDGER / "citation_audit_wcc_flash-08.csv"
fetch_log = ART / "l1_fetch_log.json"
report = ART / "l1_wcc_citation_report.json"
builder = ART / "build_citation_audit.py"
rep = json.loads(report.read_text())

events = [
    {
        "event_id": "e08-art-20260911T2324-l1-citation-audit",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "literature",
        "node_id": "L1",
        "class_id": "AF-WCC-VAC-GEN",
        "artifact_type": "citation_audit_rows",
        "path": "ledger/citation_audit.csv",
        "sha256": sha256(shared),
        "validation_status": "unverified",
        "validation_scope_note": "'unverified' = submitted for lead-literature/A1 review; rows are self-checked against resolvers but no independent re-fetch has happened yet (G-LIT requires >=3 independent spot checks).",
        "row_count": rep["row_count"],
        "verdict_counts": rep["verdict_counts"],
        "class_counts": rep["class_counts"],
        "shard_jsonl": {"path": "ledger/citation_audit_wcc_flash-08.jsonl", "sha256": sha256(shard_jsonl)},
        "shard_csv": {"path": "ledger/citation_audit_wcc_flash-08.csv", "sha256": sha256(shard_csv)},
        "fetch_log": {"path": "artifacts/worker08/l1_fetch_log.json", "sha256": sha256(fetch_log)},
        "report": {"path": "artifacts/worker08/l1_wcc_citation_report.json", "sha256": sha256(report)},
        "builder": {"path": "artifacts/worker08/build_citation_audit.py", "sha256": sha256(builder)},
        "merge": rep["merge"],
        "evidence_refs": ["comms/inbox/deepseek-flash-08.jsonl", "research_map/ASTRA_HANDOFF.md:41"],
        "next_falsifier": rep["next_falsifier"],
    },
    {
        "event_id": "e08-status-20260911T2324-l1-result",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "literature",
        "node_id": "L1",
        "status": "active",
        "hours": 1.0,
        "summary": (
            "Assignment asg-2026-09-11-L1-deepseek-flash-08-17 executed to the stop rule: 13 WCC-side rows "
            "built with locator + statement + class mapping + verdict; named sources Penrose 1969, "
            "Christodoulou 1999, Dafermos-Rodnianski (x2), Ringstrom (x2) plus 6 more. Scope findings: "
            "(a) Christodoulou 1999 is a WCC-side counterexample in the spherical scalar class "
            "(AF-WCC-SCALAR-SPH), not vacuum support; (b) Dafermos-Rodnianski 2005 is C^0-SCC evidence, "
            "route to worker 09; (c) Ringstrom 2008 scope UNRESOLVED (publisher-blocked) and Ringstrom 2013 "
            "is cosmological Einstein-Vlasov (NON-AF), so neither maps to AF-WCC-VAC-GEN; (d) every "
            "AF-WCC-VAC-GEN-supporting item found is perturbative (small data, codimension-3 data, or "
            "polarized symmetry), so the class currently has NO generic-data theorem in this ledger. "
            "Not claiming L1 done: G-LIT needs reviewer spot checks."
        ),
        "evidence_refs": [
            "ledger/citation_audit.csv",
            "artifacts/worker08/l1_wcc_citation_report.json",
            "artifacts/worker08/l1_fetch_log.json",
        ],
        "next_falsifier": rep["next_falsifier"],
    },
    {
        "event_id": "e08-blocker-20260911T2324-l1-fulltext",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "literature",
        "node_id": "L1",
        "description": (
            "Full-text verification is blocked for 4 of 13 rows: APS returns HTTP 403 for Penrose 1965 and its "
            "harvest fulltext is PDF-only; Springer redirects the Penrose 1969 reprint and the Ringstrom 2008 "
            "PDF to idp.springer.com; ar5iv conversion of arXiv:math/9901147 failed, so Christodoulou 1999's "
            "main theorem number is unextracted. Those rows are marked unverified/UNRESOLVED, not verified."
        ),
        "needed_to_unblock": (
            "Institutional PDF access or a human page-check; alternatively lead-literature accepts "
            "abstract-level rows with the reduced verification_status, and a second worker completes "
            "Ringstrom 2008 scope resolution."
        ),
        "evidence_refs": ["artifacts/worker08/l1_fetch_log.json", "ledger/citation_audit.csv"],
        "next_falsifier": "A page check with library access extracts the missing theorem statements; if any contradicts the abstract-level row, that row is downgraded.",
    },
]

existing_ids = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing_ids.add(json.loads(line)["event_id"])
            except (ValueError, KeyError):
                pass

added = []
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in events:
        if ev["event_id"] in existing_ids:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        added.append(ev["event_id"])

print(json.dumps({"outbox": str(OUTBOX.relative_to(REPO)), "added": added,
                  "total_events": len(existing_ids) + len(added)}, indent=2))
