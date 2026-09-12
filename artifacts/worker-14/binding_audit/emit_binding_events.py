#!/usr/bin/env python3
"""Emit worker-14's binding-audit events to the outbox and write checkpoint 8.

Idempotent: an event whose event_id already exists in comms/outbox/deepseek-flash-14.jsonl
is not appended again.  Appends only to this worker's own outbox and writes only
runtime/state/w14_checkpoint_8.json.  No canonical artifact or other agent's file is touched.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/deepseek-flash-14.jsonl"
REPORT = "artifacts/worker-14/binding_audit/n0_proposal_binding_audit.json"
BUILDER = "artifacts/worker-14/binding_audit/audit_proposal_binding.py"
CP7 = "runtime/state/w14_checkpoint_7.json"
CP8 = ROOT / "runtime/state/w14_checkpoint_8.json"


def sha256_file(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S%z")
    report = json.loads((ROOT / REPORT).read_text())
    report_sha = sha256_file(REPORT)
    builder_sha = sha256_file(BUILDER)
    cp7_sha = sha256_file(CP7)
    # Deterministic ids: a re-run over the same report bytes is a no-op, not a duplicate.
    tag = report_sha[:8]
    vor = report["verification_of_record"]
    reg = report["registry_coverage"]["summary"]
    chain = report["evidence_chain"]["summary"]

    refs = [
        f"numerics/tests/n0_gate_proposal.json#{vor['current_proposal_sha256'][:12]}",
        f"numerics/protocol/n0_gate_proposal_leadverify.json#{report['pins']['numerics/protocol/n0_gate_proposal_leadverify.json']['sha256'][:12]}",
        f"runtime/state/artifact_hashes.json#{report['pins']['runtime/state/artifact_hashes.json']['sha256'][:12]}",
        f"{REPORT}#{report_sha[:12]}",
    ]

    events = [
        {
            "event_id": f"w14-bind-{tag}-artifact",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "gate": "G-NUM",
            "artifact_type": "n0-proposal-binding-audit/v1",
            "path": REPORT,
            "sha256": report_sha,
            "validation_status": "unverified",
            "builder": {"path": BUILDER, "sha256": builder_sha},
            "verdict": report["verdict"],
            "instrument_valid": report["instrument_valid"],
            "summary": (
                "W14-GNUM-BINDING-AUDIT-01: read-only binding audit of the N0 gate proposal at "
                f"proposal {vor['current_proposal_sha256'][:12]}. Evidence chain {chain['match']}/"
                f"{sum(chain.values())} match disk, 0 stale, 0 missing. The filed verification of "
                f"record {vor['record']} pins proposal {str(vor['verified_proposal_sha256'])[:12]}, "
                "i.e. a superseded revision: no binding verification covers the current bytes; "
                f"{len(vor['added_evidence_entries'])} evidence entries were added and "
                f"{len(vor['changed_declared_hashes'])} declared hashes changed across the rebase. "
                f"Registry snapshot {report['pins']['runtime/state/artifact_hashes.json']['sha256'][:12]}: "
                f"{reg['registered_match']} match, {reg['registered_stale']} stale, "
                f"{reg['unregistered']} unregistered of 25 chain/proposal/leadverify paths; the C4 "
                "items 6542db93 and 1e6cdf04 remain unregistered."
            ),
            "evidence_refs": refs,
            "falsifier": report["falsifier"],
        },
        {
            "event_id": f"w14-bind-{tag}-status",
            "event_type": "status",
            "created_at": ts,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "gate": "G-NUM",
            "status": "active",
            "hours": 0.4,
            "summary": (
                "One bounded class-bound task taken (no inbox card; the three astra cards on "
                "deepseek-flash-14 are worker-side complete and hash-stable): W14-GNUM-BINDING-AUDIT-01, "
                "verdict BINDING_GAP_VERIFICATION_OF_RECORD_STALE, 7/7 controls behaved, "
                "instrument_valid=true, deterministic rebuild. Findings: BA-1 (load-bearing) the "
                "leadverify record must be re-issued at the current proposal hash before it is cited "
                "for astra-life04-n0-verify; BA-2 revision delta 12 added / 5 removed / 2 changed; "
                "BA-3 registry coverage 1/25 with C4 open for the fixed run and protocol; BA-4 no "
                "scanned record that mentions the current hash is a verification-of-record. No gate "
                "verdict, no node completion, no lock change."
            ),
            "evidence_refs": refs,
            "next_falsifier": report["falsifier"],
        },
        {
            "event_id": f"w14-bind-{tag}-blocker",
            "event_type": "blocker",
            "created_at": ts,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "gate": "G-NUM",
            "description": (
                "The N0 gate proposal's only filed verification record "
                f"({vor['record']}) is pinned to superseded revision "
                f"{str(vor['verified_proposal_sha256'])[:12]}; current disk bytes are "
                f"{vor['current_proposal_sha256'][:12]}. The current revision's 23-entry evidence "
                "chain is internally consistent but independently unverified. C4 registration is "
                "also still open: n0_replication_astra_run2_FIXED.json#6542db93 and "
                "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04 are not in artifact_hashes.json at the "
                "measured registry snapshot."
            ),
            "needed_to_unblock": (
                "An independent verifier (lead-audit or another reviewer) re-issues the proposal "
                "verification at the current hash before citing it in astra-life04-n0-verify; the "
                "controller registers 6542db93 and 1e6cdf04 (C4). Worker-side no action can close either."
            ),
            "evidence_refs": refs,
        },
    ]

    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    appended = []
    with OUTBOX.open("a", encoding="utf-8") as fh:
        for ev in events:
            if ev["event_id"] in seen:
                continue
            fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
            appended.append(ev["event_id"])

    result = {
        "verdict": report["verdict"],
        "instrument_valid": report["instrument_valid"],
        "chain": chain,
        "registry": reg,
        "coverage_gap": vor["coverage_gap"],
        "added_evidence_entries": len(vor["added_evidence_entries"]),
        "removed_evidence_entries": len(vor["removed_evidence_entries"]),
        "changed_declared_hashes": len(vor["changed_declared_hashes"]),
        "deterministic_rebuild": True,
        "controls_passed": sum(1 for c in report["controls"] if c["behaved"]),
        "controls_total": len(report["controls"]),
    }
    checkpoint = {
        "actor": "deepseek-flash-14",
        "artifact": {"path": REPORT, "sha256": report_sha,
                     "type": "n0-proposal-binding-audit/v1", "validation_status": "unverified"},
        "builder": {"path": BUILDER, "sha256": builder_sha},
        "assignment_ref": "W14-GNUM-BINDING-AUDIT-01 (no inbox card; bounded class-bound task from the open N0/G-NUM verification queue)",
        "at": datetime.now(CST).isoformat(timespec="seconds"),
        "checkpoint": 8,
        "checkpoint_label": "CP14(worker-14/8)",
        "class_id": "AF-WCC-SCALAR-SPH",
        "continuation_of": {"path": CP7, "sha256": cp7_sha},
        "does_not_claim": [
            "no G-NUM verdict and no gate self-pass; G-NUM adjudication is Astra's",
            "no N0 completion and no re-issue of the leadverify record; numerics_lock stays LOCKED, N1 queued, numerics/spherical_solver absent",
            "no independent review and no judgement that the current proposal revision is wrong; its chain matches disk",
            "no controller registration write; the C4 registration remains controller-owned",
            "no edit of any other agent's artifact; all inputs were read read-only",
        ],
        "gate": "G-NUM",
        "inbox_lines": 4,
        "inbox_note": "No new card since astra-numfix-03 (2026-09-11T23:40); the three cards are worker-side delivered and hash-stable. astra-life04-n0-verify belongs to lead-audit; this audit only supplies independent worker-side provenance evidence for it.",
        "node_id": "N0",
        "outbox_events": [ev["event_id"] for ev in events],
        "appended_now": appended,
        "pins": {k: v["sha256"] for k, v in report["pins"].items()},
        "result": result,
        "next_falsifier": report["falsifier"],
    }
    CP8.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    print("appended:", appended)
    print("checkpoint:", CP8.relative_to(ROOT), "sha256", sha256_file(str(CP8.relative_to(ROOT))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
