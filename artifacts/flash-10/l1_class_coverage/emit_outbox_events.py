#!/usr/bin/env python3
"""Emit flash-10's structured comms/outbox events for the L1 assignment.

Writes single-line JSON files so research_map/validate_map.py can validate the
schema-supported ones directly.  Re-runnable: each run recomputes hashes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "comms" / "outbox"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def write(name: str, event: dict) -> Path:
    p = OUT / name
    p.write_text(json.dumps(event, ensure_ascii=False) + "\n")
    return p


CSV = ROOT / "ledger" / "class_coverage.csv"
SPOT = ROOT / "reviews" / "L1-spotcheck-10.json"
PREV_STATUS = sorted(OUT.glob("flash-10_status_*.json")) if OUT.exists() else []
SUMMARY = HERE / "coverage_summary.json"
BUILD = HERE / "build_ledger_class_coverage.py"
VALIDATE = HERE / "validate_class_coverage.py"
README = HERE / "README.md"
REGISTRY = HERE / "sources.json"
summary = json.loads(SUMMARY.read_text())
counts = summary["coverage_totals"]

events = []
events.append(write(f"flash-10_status_{STAMP}.json", {
    "event_id": f"flash-10-status-{STAMP}",
    "event_type": "status",
    "created_at": NOW,
    "actor": "flash-10",
    "worker": "deepseek-flash-10",
    "to": ["lead-literature"],
    "cc": ["astra", "lead-audit"],
    "assignment_received": True,
    "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
    "node_id": "L1",
    "gate": "G-LIT",
    "class_id": "GLOBAL",
    "checkpoint": "2 of N",
    "status": "active",
    "delivery_state": "delivered_unverified",
    "hours": 0.7,
    "budget_agent_hours": 4,
    "summary": ("Executed astra asg-2026-09-11-L1-deepseek-flash-10-19 (source x class coverage "
                "matrix, ledger/class_coverage.csv, structural completeness + 8-mutant checker) and "
                "astra-glit-00 (6/6 independent locator re-fetch spot check, verdict accept). "
                "No completion claimed; artifact validation_status=unverified pending lead/A1."),
    "claims_completion": False,
    "task": "Map each ledger source to the 4 frozen classes.",
    "delivered": {"ledger/class_coverage.csv": sha(CSV),
                  "artifacts/flash-10/l1_class_coverage/coverage_summary.json": sha(SUMMARY),
                  "artifacts/flash-10/l1_class_coverage/README.md": sha(README),
                  "reviews/L1-spotcheck-10.json": sha(SPOT) if SPOT.exists() else None},
    "result": {
        "rows": summary["rows"], "sources": summary["audit_sources"],
        "coverage_totals": counts,
        "per_class": {k: v for k, v in summary["classes"].items()},
        "inputs": summary["inputs"],
    },
    "supersedes": (PREV_STATUS[-1].name + " (stale snapshot)" if PREV_STATUS else None),
    "headline_finding": ("No generic asymptotically flat vacuum C^2-inextendibility theorem appears "
                         "in any covered AF-SCC-C2-VAC-GEN cell. The C2 covered set decomposes into "
                         "(a) non-AF Gowdy vacuum T-520, (b) matter models T-514, (c) vacuum "
                         "weak-null-singularity structure T-303, (d) Lipschitz-type weak-null result "
                         "T-526/T-527 (C^{0,1}_loc, conditional). Corroborates the ledger's "
                         "provisional T-401 by an independent route."),
    "empty_cells": {"none": counts["none"], "unassessed": counts["unassessed"],
                    "unassessed_sources": summary["unassessed_sources"]},
    "spotcheck": {"artifact": "reviews/L1-spotcheck-10.json", "checked": 6, "match": 6,
                  "mismatch": 0, "verdict": "accept"},
    "review_queue": {"scope_flag_rows": len(summary["scope_flag_review_queue"]),
                     "artifact": "artifacts/flash-10/l1_class_coverage/coverage_summary.json#scope_flag_review_queue"},
    "no_completion_claimed": True,
    "evidence_refs": ["research_map/ASTRA_HANDOFF.md:36-43 (immediate queue L0/L1)",
                      "research_map/research_map.json#L1",
                      f"ledger/theorems.jsonl#{summary['inputs']['ledger/theorems.jsonl'][:12]}",
                      f"ledger/citation_audit.csv#{summary['inputs']['ledger/citation_audit.csv'][:12]}",
                      f"artifacts/flash-10/l1_class_coverage/coverage_summary.json#{sha(SUMMARY)[:12]}",
                      f"reviews/L1-spotcheck-10.json#{(sha(SPOT)[:12]) if SPOT.exists() else 'missing'}"],
    "next_falsifier": ("Re-run build_ledger_class_coverage.py against the frozen L0 hash; if any "
                       "covered cell changes class or strength, or if one accepted generic AF "
                       "vacuum C^2-inextendibility theorem appears, the headline finding and T-401 "
                       "are falsified."),
    "schema_note": "event_type 'status' is in the ASTRA_HANDOFF communication contract but absent from research_map/schemas.py EVENT_TYPES; emitted as contract-listed, not silently renamed.",
}))
events.append(write(f"flash-10_artifact_class_coverage_{STAMP}.json", {
    "event_id": f"flash-10-artifact-cc-{STAMP}", "event_type": "artifact", "created_at": NOW,
    "actor": "flash-10", "to": ["lead-literature"], "cc": ["astra", "lead-audit"],
    "node_id": "L1", "class_id": "GLOBAL",
    "artifact_type": "source_class_coverage_matrix_csv",
    "path": rel(CSV), "sha256": sha(CSV), "validation_status": "unverified",
    "validation_evidence": {"checker": rel(VALIDATE), "checker_sha256": sha(VALIDATE),
                            "self_test": "8/8 mutants caught; clean fixture accepted",
                            "structural_check": "77/77 audit sources x 4 classes, exactly one row per pair"},
    "generator_path": rel(BUILD), "generator_sha256": sha(BUILD),
    "inputs": summary["inputs"],
    "reproduce": "python3 artifacts/flash-10/l1_class_coverage/build_ledger_class_coverage.py && python3 artifacts/flash-10/l1_class_coverage/validate_class_coverage.py",
    "completion_claim": False,
    "next_falsifier": "Lead-literature or A1 reviewer re-runs the checker on the frozen ledger hash and finds a source/class pair missing or a covered cell unsupported by its cited theorem.",
}))
events.append(write(f"flash-10_artifact_summary_{STAMP}.json", {
    "event_id": f"flash-10-artifact-summary-{STAMP}", "event_type": "artifact", "created_at": NOW,
    "actor": "flash-10", "to": ["lead-literature", "lead-audit"], "cc": ["astra"],
    "node_id": "L1", "class_id": "GLOBAL",
    "artifact_type": "coverage_summary_json",
    "path": rel(SUMMARY), "sha256": sha(SUMMARY), "validation_status": "unverified",
    "contents": ["coverage totals per class", "covered source lists", "input hashes",
                 "8 unmapped sources", "34-row scope-flag review queue"],
    "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/README.md#{sha(README)[:12]}",
                      f"artifacts/flash-10/l1_class_coverage/coverage_summary.json#{sha(SUMMARY)[:12]}"],
    "completion_claim": False,
    "next_falsifier": "A1 finds a scope-flag queue row whose binding is unjustified and whose removal changes a class's covered count.",
}))
events.append(write(f"flash-10_resource_request_{STAMP}.json", {
    "event_id": f"flash-10-rr-{STAMP}", "event_type": "resource_request", "created_at": NOW,
    "actor": "flash-10", "to": ["lead-literature"], "cc": ["astra", "lead-audit"],
    "group_id": "literature", "node_id": "L1", "class_id": "GLOBAL",
    "requested_agents": 1, "requested_agent_hours": 1.0,
    "justification": (f"Zero-cost follow-up on the delivered matrix: (a) map the "
                      f"{len(summary['unassessed_sources'])} sources with no ledger entry "
                      f"({', '.join(summary['unassessed_sources'])}), (b) bind the matrix to the frozen "
                      f"L0 hash before G-LIT, (c) have A1 adjudicate the "
                      f"{len(summary['scope_flag_review_queue'])}-row scope-flag queue."),
    "expected_information_gain": ("Removes the 32 unassessed cells and tests the headline finding that "
                                  "no generic AF vacuum C^2-inextendibility theorem is in the ledger."),
    "stop_rule": "Stop at a frozen L0 hash with the matrix re-run and 0 unassessed cells, or at 1.0 agent-hour.",
    "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/coverage_summary.json#{sha(SUMMARY)[:12]}",
                      f"ledger/class_coverage.csv#{sha(CSV)[:12]}"],
    "next_falsifier": "If the ledger's next revision adds such a C^2 theorem, withdraw the headline finding.",
}))
events.append(write(f"flash-10_blocker_{STAMP}.json", {
    "event_id": f"flash-10-blocker-{STAMP}", "event_type": "blocker", "created_at": NOW,
    "actor": "flash-10", "worker": "deepseek-flash-10",
    "to": ["lead-literature"], "cc": ["astra", "lead-audit"],
    "node_id": "L1", "class_id": "GLOBAL",
    "blockers": [
        {"id": "B1-web-search-tool", "severity": "workaround_in_place",
         "detail": "web_search failed 3/3 with TypeError: fetch failed against https://api.deepseek.com/anthropic/v1/messages. Direct HTTPS from Python/curl works; plain HTTP port 80 times out."},
        {"id": "B2-unmapped-sources", "severity": "open",
         "detail": f"{len(summary['unassessed_sources'])} of {summary['audit_sources']} audit sources have zero ledger theorem entries, producing {counts['unassessed']} unassessed rows: {', '.join(summary['unassessed_sources'])}."},
        {"id": "B3-live-ledger-drift", "severity": "open",
         "detail": "ledger/theorems.jsonl and ledger/citation_audit.csv changed during this run; the matrix records input hashes and must be re-run at freeze."},
        {"id": "B4-schema-gap", "severity": "documented",
         "detail": "contract lists status/blocker but research_map/schemas.py EVENT_TYPES lacks both; this blocker is contract-listed and schema-unsupported (same finding as worker-08)."},
        {"id": "B5-unverified-class-bindings", "severity": "handed_to_A1",
         "detail": "coverage inherits L0 class_ids; 34 covered/partial rows carry scope flags suggesting the binding's own scope may not be the frozen class. Review queue in coverage_summary.json."},
    ],
    "description": ("Five open items: (B1) web_search tool unreachable, HTTPS API workaround in place; "
                    "(B2) unmapped ledger sources produce unassessed matrix rows; (B3) live ledger drift "
                    "requires re-run at freeze; (B4) contract/schema gap for status/blocker event types; "
                    "(B5) class bindings inherited from L0 need A1 adjudication."),
    "needed_to_unblock": ("B2: map the listed sources to ledger entries and re-run the builder. "
                          "B3: freeze the ledger and re-run. B4: add status/blocker to "
                          "research_map/schemas.py EVENT_TYPES. B5: A1 verdicts on the scope-flag queue."),
    "adjudication_owner": "lead-literature (mapping) / lead-audit A1 (bindings)",
    "evidence_refs": [f"artifacts/flash-10/l1_class_coverage/README.md#{sha(README)[:12]}",
                      f"artifacts/flash-10/l1_class_coverage/coverage_summary.json#{sha(SUMMARY)[:12]}"],
    "schema_note": "event_type 'blocker' is contract-listed but absent from research_map/schemas.py EVENT_TYPES.",
    "next_falsifier": "All five blockers clear when the frozen-ledger re-run yields 0 unassessed rows, 0 unresolved scope flags, and a schema that accepts status/blocker.",
}))

print("emitted:")
for p in events:
    print(" ", p.relative_to(ROOT))
