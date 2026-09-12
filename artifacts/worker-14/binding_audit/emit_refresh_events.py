#!/usr/bin/env python3
"""Emit the W14-GNUM-BINDING-AUDIT-02 events and checkpoint.

Bounded worker lifecycle close-out: append exactly five JSONL events (artifact report,
artifact instrument, status, claim, blocker) to comms/outbox/deepseek-flash-14.jsonl and
write runtime/state/w14_checkpoint_9.json.  Idempotent: existing event_ids are not
re-appended.  Does not touch any other agent's files, the registry, the map, or any gate.

Run:  python3 artifacts/worker-14/binding_audit/emit_refresh_events.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
REPORT = OUT_DIR / "n0_binding_audit_refresh.json"
SCRIPT = OUT_DIR / "audit_binding_refresh.py"
OUTBOX = ROOT / "comms/outbox/deepseek-flash-14.jsonl"
CHECKPOINT = ROOT / "runtime/state/w14_checkpoint_9.json"
PREV_CHECKPOINT = ROOT / "runtime/state/w14_checkpoint_8.json"
CST = timezone(timedelta(hours=8))
PROPOSAL = "numerics/tests/n0_gate_proposal.json"
LEADVERIFY = "numerics/protocol/n0_gate_proposal_leadverify.json"
REGISTRY = "runtime/state/artifact_hashes.json"
MAP = "research_map/research_map.json"
BASELINE = "artifacts/worker-14/binding_audit/n0_proposal_binding_audit.json"


def sha(rel_or_path: str | Path) -> str:
    p = Path(rel_or_path)
    if not p.is_absolute():
        p = ROOT / p
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    report = json.loads(REPORT.read_text())
    r_sha = sha(REPORT)
    s_sha = sha(SCRIPT)
    short = r_sha[:12]

    chain = report["A_evidence_chain"]["summary"]
    union = report["C_registry_coverage"]["union_summary"]
    reg_sha = report["C_registry_coverage"]["registry_snapshot_sha256"]
    prop_sha = report["B_verification_of_record"]["proposal_on_disk_sha256"]
    lv_sha = report["pins"][LEADVERIFY]["sha256"]
    base_sha = report["supersedes_baseline"]["sha256"]
    verdict = report["verdict"]
    open_findings = [f["id"] for f in report["findings"] if f.get("status") == "open"]

    evidence = [
        f"{PROPOSAL}#{prop_sha[:12]}",
        f"{LEADVERIFY}#{lv_sha[:12]}",
        f"{REGISTRY}#{reg_sha[:12]}",
        f"{BASELINE}#{base_sha[:12]}",
        f"artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#{short}",
    ]
    falsifier = report["falsifier"]

    summary = (
        f"W14-GNUM-BINDING-AUDIT-02 ({verdict}): refresh of the N0 proposal binding audit at "
        f"registry {reg_sha[:12]}. Evidence chain {chain['match']}/{sum(chain.values())} match disk, "
        f"0 stale, 0 missing. C4 delta vs audit-01 (d63b67f1): union coverage of the 25 "
        f"proposal-chain + proposal + leadverify paths is now {union['registered_match']}/25 "
        f"registered_match, 0 stale, 0 unregistered -- audit-01 BA-3 measured 1/25 at "
        f"c9f20343cc46 with the four C4 items open, so the registration gap is CLOSED at this "
        f"snapshot. BA-1 remains open: leadverify {lv_sha[:12]} pins superseded proposal "
        f"58a175b5 while disk bytes are {prop_sha[:12]}, and the bounded 12-record binding scan "
        f"finds no record that binds the current revision as verified. New BA-5: the proposal's "
        f"declared mutable registry snapshot d69b62dc @ 2026-09-12T01:06 matches neither the "
        f"registry on disk ({reg_sha[:12]}) nor a reachable instant at audit time. BA-6: "
        f"leadverify criteria_status still records registration UNMET, now stale. 10/10 controls "
        f"behaved, deterministic rebuild, baseline d63b67f1 unchanged, lock intact, "
        f"numerics/spherical_solver absent. No gate verdict, no node completion, no registry write."
    )

    events = [
        {
            "event_id": f"w14-bind2-{short}-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": report["class_id"],
            "artifact_type": "n0-binding-audit-refresh/v1",
            "task_id": "W14-GNUM-BINDING-AUDIT-02",
            "path": "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json",
            "sha256": r_sha,
            "bytes": REPORT.stat().st_size,
            "validation_status": "unverified",
            "verdict": verdict,
            "supersedes_baseline": {
                "path": BASELINE, "sha256": base_sha,
                "unchanged": report["supersedes_baseline"]["unchanged"],
            },
            "open_findings": open_findings,
            "resolved_findings": [f["id"] for f in report["findings"]
                                  if f.get("status") == "closed-at-current-snapshot"],
            "summary": summary,
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w14-bind2-{short}-artifact-instrument",
            "event_type": "artifact",
            "created_at": now,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": report["class_id"],
            "artifact_type": "audit-instrument/v1",
            "task_id": "W14-GNUM-BINDING-AUDIT-02",
            "path": "artifacts/worker-14/binding_audit/audit_binding_refresh.py",
            "sha256": s_sha,
            "validation_status": "unverified",
            "controls_passed": report["controls_ok"],
            "controls_total": len(report["controls"]),
            "summary": ("Read-only deterministic refresh instrument; 10/10 planted controls "
                        "behaved (match/stale/missing/dir/registry-match/registry-stale/"
                        "registry-absent/real stale pin/baseline unchanged/load-bearing facts), "
                        "with a registry before-after drift guard."),
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w14-bind2-{short}-status",
            "event_type": "status",
            "created_at": now,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": report["class_id"],
            "status": "active",
            "hours": 0.5,
            "task_id": "W14-GNUM-BINDING-AUDIT-02",
            "summary": ("One bounded class-bound task taken (no new inbox card for the relaunched "
                        "slot; the three astra cards on deepseek-flash-14 are worker-side complete "
                        "and hash-stable): " + summary),
            "evidence_refs": evidence,
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w14-bind2-{short}-claim-c4",
            "event_type": "claim",
            "created_at": now,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": report["class_id"],
            "conclusion_type": "numerical_evidence",
            "statement": (
                f"Provenance measurement at registry snapshot {reg_sha[:12]}: the 25 paths of the "
                f"N0 gate proposal evidence chain plus the proposal and its leadverify record are "
                f"all registered with matching sha256 ({union['registered_match']}/25 "
                f"registered_match, 0 stale, 0 unregistered), closing audit-01 finding BA-3/C4 at "
                f"this snapshot; independently, the filed verification of record "
                f"(n0_gate_proposal_leadverify.json#{lv_sha[:12]}) still pins superseded proposal "
                f"revision 58a175b52fbe, so the current revision {prop_sha[:12]} has no binding "
                f"verification, and the proposal's declared mutable registry snapshot d69b62dc "
                f"does not match the measured registry."
            ),
            "assumptions": [
                "registry bytes are controller-rewritten and are a snapshot, not stable evidence",
                "the 23 declared evidence_hashes match disk at the pinned proposal hash",
                "the bounded 12-record binding scan is not exhaustive over the whole repository",
            ],
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w14-bind2-{short}-blocker",
            "event_type": "blocker",
            "created_at": now,
            "actor": "deepseek-flash-14",
            "node_id": "N0",
            "gate": "G-NUM",
            "class_id": report["class_id"],
            "description": (
                f"BA-1 open: the only filed verification of record for the N0 gate proposal "
                f"({LEADVERIFY}#{lv_sha[:12]}) covers proposal revision 58a175b52fbe, while the "
                f"bytes on disk are {prop_sha[:12]} (23-entry chain matches disk but is "
                f"independently unverified); no record in the bounded scan binds the current "
                f"revision as verified. BA-5 open: the proposal's declared mutable registry "
                f"snapshot d69b62dc measured_at 2026-09-12T01:06 matches neither the registry on "
                f"disk ({reg_sha[:12]}) nor a reachable audit instant."
            ),
            "needed_to_unblock": (
                "An independent verifier (lead-audit or another reviewer) re-issues the proposal "
                "verification at the current proposal hash before citing the leadverify record in "
                "astra-life04-n0-verify, or the lead re-issues n0_gate_proposal_leadverify.json at "
                "the current hash; separately, the proposal's mutable_registry_snapshots entry for "
                f"{REGISTRY} should be corrected or annotated as unreproducible. Worker-side no "
                "action can close either."
            ),
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
    ]

    # Idempotent append: only events whose id is not already present.
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    appended = []
    with OUTBOX.open("a") as fh:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
            appended.append(ev["event_id"])

    prev_sha = sha(PREV_CHECKPOINT)
    checkpoint = {
        "actor": "deepseek-flash-14",
        "at": now,
        "checkpoint": 9,
        "checkpoint_label": "CP14(worker-14/9)",
        "continuation_of": {"path": str(PREV_CHECKPOINT.relative_to(ROOT)),
                            "sha256": prev_sha},
        "assignment_ref": ("W14-GNUM-BINDING-AUDIT-02 (no new inbox card; bounded class-bound "
                           "refresh of audit-01 from the open N0/G-NUM verification queue)"),
        "class_id": report["class_id"],
        "node_id": "N0",
        "gate": "G-NUM",
        "artifact": {
            "path": str(REPORT.relative_to(ROOT)), "sha256": r_sha,
            "type": "n0-binding-audit-refresh/v1", "validation_status": "unverified",
        },
        "builder": {"path": str(SCRIPT.relative_to(ROOT)), "sha256": s_sha},
        "pins": {
            PROPOSAL: prop_sha,
            LEADVERIFY: lv_sha,
            REGISTRY: reg_sha,
            MAP: sha(MAP),
        },
        "result": {
            "verdict": verdict,
            "instrument_valid": report["instrument_valid"],
            "controls_passed": len([c for c in report["controls"] if c["behaved"]]),
            "controls_total": len(report["controls"]),
            "deterministic_rebuild": True,
            "chain": chain,
            "registry_union": union,
            "c4_closed": report["C_registry_coverage"]["c4_closed"],
            "pin_is_current": report["B_verification_of_record"]["pin_is_current"],
            "any_binding_record_for_current": report["B_verification_of_record"]["any_binding_record_for_current"],
            "declared_snapshot_matches_measured": report["D_declared_registry_snapshot"]["matches_measured"],
            "baseline_unchanged": report["supersedes_baseline"]["unchanged"],
            "open_findings": open_findings,
        },
        "outbox_events": [ev["event_id"] for ev in events],
        "appended_now": appended,
        "next_falsifier": falsifier,
        "does_not_claim": report["not_claimed"],
    }
    CHECKPOINT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"appended": appended, "checkpoint": str(CHECKPOINT),
                      "checkpoint_sha256": sha(CHECKPOINT), "report_sha256": r_sha},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
