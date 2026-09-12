#!/usr/bin/env python3
"""Emit the lifecycle-05 numerics group-lead events and write the lifecycle record.

Idempotent: every event id is deterministic (content-derived), so re-running the script
returns the already-appended events instead of duplicating them.  Nothing here sets a gate
verdict, a node status, or ``validation_status=passed``; all artifacts are emitted
``unverified`` for the controller/audit to accept.

    python3 numerics/protocol/emit_lifecycle05_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CST = timezone(timedelta(hours=8))
INSTANCE = "lead-numerics-01-20260912T004903-968807"
STARTED = datetime(2026, 9, 12, 0, 49, 3, tzinfo=CST)

from numerics import events  # noqa: E402
from research_map import schemas  # noqa: E402

NOTE = ROOT / "artifacts/numerics/BINDING_REFRESH.md"
RECORD = ROOT / "artifacts/numerics/lifecycle_05_20260912.json"
LEADVERIFY = ROOT / "numerics/protocol/n0_gate_proposal_leadverify.json"
SUCCESSOR = ROOT / "numerics/protocol/fixed_replication_verdict_rev2.json"
BUILDER = ROOT / "numerics/protocol/build_leadverify_b419.py"
DRIVER = ROOT / "numerics/protocol/rebind_fixed_replication_verdict.py"
PROPOSAL = ROOT / "numerics/tests/n0_gate_proposal.json"
OLD_VERDICT = ROOT / "numerics/protocol/fixed_replication_verdict.json"
REV3 = ROOT / "numerics/results/flat_wave_convergence_rev3.json"
CERT = ROOT / "numerics/protocol/n0_fixed_dt_certification.json"
W14 = ROOT / "artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json"
W67 = ROOT / "artifacts/worker-067/n0_provenance_ledger/ledger.json"
W71 = ROOT / "artifacts/worker-071/n0_rev3_verify/report.json"
PROTOCOL = ROOT / "numerics/CONVERGENCE_PROTOCOL.md"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(CST)
    hours = round((now - STARTED).total_seconds() / 3600.0, 3)
    h = {str(p.relative_to(ROOT)): sha(p) for p in
         (LEADVERIFY, SUCCESSOR, BUILDER, DRIVER, NOTE, PROPOSAL, OLD_VERDICT, REV3, CERT,
          W14, W67, W71, PROTOCOL)}

    ids = {
        "a_leadverify": events.det_id("artifact", "leadverify", h[str(LEADVERIFY.relative_to(ROOT))]),
        "a_successor": events.det_id("artifact", "successor", h[str(SUCCESSOR.relative_to(ROOT))]),
        "a_builder": events.det_id("artifact", "leadverify-builder", h[str(BUILDER.relative_to(ROOT))]),
        "a_driver": events.det_id("artifact", "rebind-driver", h[str(DRIVER.relative_to(ROOT))]),
        "a_note": events.det_id("artifact", "binding-refresh-note", h[str(NOTE.relative_to(ROOT))]),
        "a_record": events.det_id("artifact", "lifecycle-05", INSTANCE),
        "b_repin": events.det_id("blocker", "repin-leadverify", h[str(LEADVERIFY.relative_to(ROOT))]),
        "b_c8": events.det_id("blocker", "c8-discharge", h[str(SUCCESSOR.relative_to(ROOT))]),
        "s_n0": events.det_id("status", "n0-refresh", INSTANCE),
        "s_done": events.det_id("status", "global-done", INSTANCE),
    }

    record = {
        "schema": "numerics-lead-lifecycle/v1",
        "group": "numerics",
        "instance_id": INSTANCE,
        "started_at": STARTED.isoformat(timespec="seconds"),
        "ended_at": now.isoformat(timespec="seconds"),
        "agent_hours_this_lead": hours,
        "run_card_consumed": {
            "note": (
                "No new numerics-owned card existed at instance start: astra-life04-n0-stoprule "
                "was discharged at 00:48 (rev-3 report) and the open cards "
                "astra-life04-n0-verify / astra-life05-gnum-protocol-adjudication are "
                "audit-owned. This lifecycle consumed the owner-named binding items in the "
                "live traffic instead: the stale verification of record (worker-14 "
                "W14-GNUM-BINDING-AUDIT-01/02) and the contradicted provenance assertion "
                "(worker-067 W067-N0-PROVENANCE-DRIFT-LEDGER-01)."
            ),
            "numerics_cards_reviewed": [
                "asg-2026-09-11-N0-astra-lead-numerics-05",
                "asg-2026-09-11-N1-astra-lead-numerics-06",
                "astra-n1block-0",
                "astra-adj2-05-assignment",
                "astra-indep-1-N0-numerics",
                "astra-life01-n0-proposal",
                "astra-life04-n0-stoprule",
            ],
            "audit_owned_open": [
                "astra-life04-n0-verify",
                "astra-life05-gnum-protocol-adjudication",
            ],
        },
        "artifacts_produced": {
            str(LEADVERIFY.relative_to(ROOT)): h[str(LEADVERIFY.relative_to(ROOT))],
            str(SUCCESSOR.relative_to(ROOT)): h[str(SUCCESSOR.relative_to(ROOT))],
            str(BUILDER.relative_to(ROOT)): h[str(BUILDER.relative_to(ROOT))],
            str(DRIVER.relative_to(ROOT)): h[str(DRIVER.relative_to(ROOT))],
            str(NOTE.relative_to(ROOT)): h[str(NOTE.relative_to(ROOT))],
            str(RECORD.relative_to(ROOT)): "self (hash in its own artifact event)",
        },
        "verify_commands": [
            {
                "command": "python3 numerics/protocol/verify_convergence_rev3.py",
                "result": "VERIFIED, 11 pins re-measured, report da7c360719950f7e",
            },
            {
                "command": "python3 numerics/protocol/build_leadverify_b419.py",
                "result": "wrote ea4cf6c9bd3c2092; chain 23/23; refit max|dp| 7.958e-05",
            },
            {
                "command": "python3 numerics/protocol/rebind_fixed_replication_verdict.py",
                "result": "wrote 7954d2d355451e3d; 79 numeric leaves, max arithmetic delta 0.0",
            },
            {
                "command": "python3 -m numerics.gates --check",
                "result": "N1_BLOCKED, exit 3, production_allowed=false, contest=true",
            },
            {
                "command": "python3 numerics/tests/flat_wave.py --lock-guard",
                "result": "exit 0, guard_correct_for_state=true, spherical_solver absent",
            },
            {
                "command": "python3 numerics/tests/flat_wave.py --selftest",
                "result": "selftest_pass=true, exit 0",
            },
            {
                "command": "python3 numerics/tests/flat_wave_replication.py --selftest",
                "result": "selftest_pass=true, exit 0",
            },
        ],
        "predicates_closed": {
            "leadverify_refresh_at_current_proposal": True,
            "i2_taxonomy_rebind_successor_delivered": True,
            "successor_arithmetic_delta_zero": True,
            "evidence_chain_23_of_23": True,
        },
        "gate_state_after": {
            "verdict": "N1_BLOCKED",
            "lock": "locked",
            "spherical_solver_present": False,
            "production_allowed": False,
            "protocol_reviewed": True,
            "protocol_contest": True,
            "dissents_machine_visible": 3,
        },
        "open_items_handed_back": [
            "re-pin numerics/protocol/n0_gate_proposal_leadverify.json to ea4cf6c9bd3c2092 in the G-NUM map evidence and runtime/state/artifact_hashes.json (both still hold e0f9ef9f329d)",
            "register numerics/protocol/fixed_replication_verdict_rev2.json#7954d2d355451e3d and the three independent verdict artifacts + worker-071 n0_rev3_verify/report.json#6bbc2d4918612298",
            "bind the successor as the replication evidence of record so the w067-provledger dissent is discharged by supersession; F1/F1' adjudication stays with lead-audit at protocol 1e6cdf04d7a2",
            "N0 node verdict remains audit-owned (audit-r2 revise 00:50:20 on registration + contest grounds; numerics-side items now measured closed)",
        ],
        "events_emitted": ids,
        "scope_compliance": {
            "self_review": False,
            "gate_self_pass": False,
            "n1_status_moved": False,
            "self_gravitating_code_written_or_run": False,
            "spherical_solver_dir_present": False,
        },
    }
    RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    h[str(RECORD.relative_to(ROOT))] = sha(RECORD)

    emitted = []

    def emit(ev: dict) -> None:
        schemas.validate_event(ev)
        emitted.append(ev["event_id"])

    # --- artifacts -----------------------------------------------------------
    emit(events.emit_artifact(
        node_id="N0", artifact_type="gate_proposal_verification",
        path=str(LEADVERIFY.relative_to(ROOT)), validation_status="unverified",
        sha256=h[str(LEADVERIFY.relative_to(ROOT))], event_id=ids["a_leadverify"],
        validation_evidence=[
            "re-verifies proposal b4192221ff7d at current bytes; supersedes e0f9ef9f329d which verified 58a175b52fbe",
            "evidence chain 23/23 entries match disk; independent lead R5 re-fit max |dp| 7.958e-05 <= 0.25",
            "external verifier VERIFIED (11 pins); gates N1_BLOCKED; lock guard PASS; both selftests green",
        ],
    ))
    emit(events.emit_artifact(
        node_id="N0", artifact_type="n0-fixed-replication-verdict-successor",
        path=str(SUCCESSOR.relative_to(ROOT)), validation_status="unverified",
        sha256=h[str(SUCCESSOR.relative_to(ROOT))], event_id=ids["a_successor"],
        validation_evidence=[
            "successor of fixed_replication_verdict.json#dcad962324e3; supersedes the contradicted fixed_taxonomy_sha256_matches_on_disk=true assertion",
            "R1/R2/R4/R5 re-run from the frozen inputs; 79 numeric leaves compared, max arithmetic difference 0.0",
            "frozen predecessor retained unedited because it is pinned by the proposal and worker verdicts",
        ],
    ))
    emit(events.emit_artifact(
        node_id="N0", artifact_type="leadverify_builder",
        path=str(BUILDER.relative_to(ROOT)), validation_status="unverified",
        sha256=h[str(BUILDER.relative_to(ROOT))], event_id=ids["a_builder"],
        validation_evidence=["fails closed on proposal-hash or chain drift; wrote the refreshed record"],
    ))
    emit(events.emit_artifact(
        node_id="N0", artifact_type="rebind_driver",
        path=str(DRIVER.relative_to(ROOT)), validation_status="unverified",
        sha256=h[str(DRIVER.relative_to(ROOT))], event_id=ids["a_driver"],
        validation_evidence=["imports the worker-14 verifier with OUT redirected; does not edit the frozen verdict"],
    ))

    # --- blockers ------------------------------------------------------------
    emit(events.emit_blocker(
        node_id="N0", severity="medium", event_id=ids["b_repin"],
        description=(
            "REGISTRY/MAP RE-PIN after the lead verification refresh: "
            "numerics/protocol/n0_gate_proposal_leadverify.json moved from "
            "e0f9ef9f329d (verified superseded proposal 58a175b52fbe) to ea4cf6c9bd3c2092 "
            "(verifies current proposal b4192221ff7d; chain 23/23, refit max|dp| 7.958e-05, "
            "external verifier VERIFIED, gates N1_BLOCKED). The G-NUM map evidence list and "
            "runtime/state/artifact_hashes.json still pin e0f9ef9f329d, which no longer "
            "matches disk, and the successor verdict "
            "fixed_replication_verdict_rev2.json#7954d2d355451e3d is unregistered. This "
            "closes worker-14 BA-1 (stale verification of record) at the numerics end."
        ),
        needed_to_unblock=(
            "controller re-pins G-NUM evidence to "
            "numerics/protocol/n0_gate_proposal_leadverify.json#ea4cf6c9bd3c2092 and "
            "registers the successor plus, if N0 acceptance needs them, the three "
            "independent verdict artifacts (worker-046/057/081) and "
            "artifacts/worker-071/n0_rev3_verify/report.json#6bbc2d4918612298. Measured "
            "00:52:00 registry coverage of the other numerics canonical paths is green."
        ),
        evidence_refs=[
            f"numerics/protocol/n0_gate_proposal_leadverify.json#{h[str(LEADVERIFY.relative_to(ROOT))][:16]}",
            "numerics/tests/n0_gate_proposal.json#b4192221ff7d",
            f"numerics/protocol/fixed_replication_verdict_rev2.json#{h[str(SUCCESSOR.relative_to(ROOT))][:16]}",
            f"artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#{h[str(W14.relative_to(ROOT))][:16]}",
            "runtime/state/artifact_hashes.json",
        ],
    ))
    emit(events.emit_blocker(
        node_id="N0", severity="medium", event_id=ids["b_c8"],
        description=(
            "C8 PROTOCOL CONTEST now counts three live dissents in numerics.gates "
            "(w067-F1, w081-F1', w067-provledger). The third is a provenance defect, not a "
            "numerical disagreement: fixed_replication_verdict.json#dcad962324e3 asserted "
            "fixed_taxonomy_sha256_matches_on_disk=true while pinning superseded F0 rev2 "
            "66bf917b. The successor fixed_replication_verdict_rev2.json#7954d2d355451e3d "
            "re-runs the identical R1/R2/R4/R5 arithmetic (delta 0.0) with the corrected "
            "measurement, so the finding is dischargeable by supersession. F1/F1' remain "
            "the audit adjudication at protocol 1e6cdf04d7a2; numerics may not self-satisfy C8."
        ),
        needed_to_unblock=(
            "lead-audit adjudicates at numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2 "
            "(card astra-life05-gnum-protocol-adjudication, deadline 02:15) and, if it "
            "accepts the successor as the replication evidence of record, the controller "
            "binds it so the w067-provledger dissent is discharged by supersession. "
            "Numerics has no further self-action; no gate verdict is proposed here."
        ),
        evidence_refs=[
            f"numerics/protocol/fixed_replication_verdict_rev2.json#{h[str(SUCCESSOR.relative_to(ROOT))][:16]}",
            "numerics/protocol/fixed_replication_verdict.json#dcad962324e3",
            f"artifacts/worker-067/n0_provenance_ledger/ledger.json#{h[str(W67.relative_to(ROOT))][:16]}",
            "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
            "reviews/G-NUM-protocol-review.json#8137f18f1a3b2b01",
        ],
    ))

    # --- statuses ------------------------------------------------------------
    emit(events.emit_status(
        node_id="N0", status="active", hours=hours, event_id=ids["s_n0"],
        summary=(
            "NUMERICS LEAD INDEPENDENT LIFECYCLE (queue read; no new numerics-owned card). "
            "Two owner-named binding defects measured and closed: (1) lead verification of "
            "record refreshed to the current proposal b4192221ff7d -- chain 23/23 entries "
            "match disk, independent lead R5 re-fit max |dp| 7.958e-05 <= 0.25, external "
            "verifier VERIFIED (11 pins), gates N1_BLOCKED, lock guard PASS, both selftests "
            "green; (2) contradicted taxonomy assertion repaired by successor "
            "fixed_replication_verdict_rev2.json (79 numeric leaves, arithmetic delta 0.0). "
            "No gate verdict, no node completion; numerics_lock LOCKED, N1 queued, "
            "numerics/spherical_solver absent. Two blockers handed to the controller: "
            "re-pin/register the refreshed paths and bind the successor for the C8 contest."
        ),
        evidence_refs=[
            f"numerics/protocol/n0_gate_proposal_leadverify.json#{h[str(LEADVERIFY.relative_to(ROOT))][:16]}",
            f"numerics/protocol/fixed_replication_verdict_rev2.json#{h[str(SUCCESSOR.relative_to(ROOT))][:16]}",
            "numerics/results/flat_wave_convergence_rev3.json#da7c36071995",
            "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8",
            "runtime/state/artifact_hashes.json",
        ],
        next_falsifier=(
            "any numerics/spherical_solver file while numerics_lock.state==locked, any N1 "
            "activation, the refreshed record verifying a proposal revision that is not on "
            "disk, or the successor's arithmetic diverging from the superseded verdict "
            "beyond runtime_seconds."
        ),
    ))

    # note + record artifacts, then the final global status
    emit(events.emit_artifact(
        node_id="N0", artifact_type="binding_refresh_note",
        path=str(NOTE.relative_to(ROOT)), validation_status="unverified",
        sha256=h[str(NOTE.relative_to(ROOT))], event_id=ids["a_note"],
        validation_evidence=["human-readable record of the refresh, the successor, and the hand-back items"],
    ))
    emit(events.emit_artifact(
        node_id="GLOBAL", artifact_type="numerics_lead_lifecycle_record",
        path=str(RECORD.relative_to(ROOT)), validation_status="unverified",
        sha256=h[str(RECORD.relative_to(ROOT))], event_id=ids["a_record"],
        validation_evidence=["lifecycle record: commands, results, artifacts, open items, scope compliance"],
    ))
    emit(events.emit_status(
        node_id="GLOBAL", status="done", hours=hours, event_id=ids["s_done"],
        summary=(
            "NUMERICS GROUP LEAD INDEPENDENT LIFECYCLE COMPLETE -- exiting. Handoff/map/"
            "comms read; queue consumed (no new numerics-owned card; two owner-named "
            "binding items closed). Deliverables: "
            f"numerics/protocol/n0_gate_proposal_leadverify.json#{h[str(LEADVERIFY.relative_to(ROOT))][:16]} "
            "(verifies current proposal b4192221ff7d; chain 23/23; refit max|dp| 7.958e-05; "
            "external verifier VERIFIED 11 pins; gates N1_BLOCKED; lock guard PASS; both "
            "selftests green) and "
            f"numerics/protocol/fixed_replication_verdict_rev2.json#{h[str(SUCCESSOR.relative_to(ROOT))][:16]} "
            "(successor of dcad962324e3, arithmetic delta 0.0, corrected taxonomy "
            "assertion). Checkpoint written after this status. Record: "
            "artifacts/numerics/lifecycle_05_20260912.json; note: "
            "artifacts/numerics/BINDING_REFRESH.md. Two blockers handed back: re-pin/"
            "register the moved paths, and bind the successor so the third C8 dissent is "
            "discharged by supersession (F1/F1' adjudication stays audit-owned). No gate "
            "self-pass; numerics_lock LOCKED; N1 queued; numerics/spherical_solver absent."
        ),
        evidence_refs=[
            f"artifacts/numerics/lifecycle_05_20260912.json#{h[str(RECORD.relative_to(ROOT))][:16]}",
            f"artifacts/numerics/BINDING_REFRESH.md#{h[str(NOTE.relative_to(ROOT))][:16]}",
            f"numerics/protocol/n0_gate_proposal_leadverify.json#{h[str(LEADVERIFY.relative_to(ROOT))][:16]}",
            f"numerics/protocol/fixed_replication_verdict_rev2.json#{h[str(SUCCESSOR.relative_to(ROOT))][:16]}",
            "research_map/research_map.json#numerics_lock",
        ],
        next_falsifier=(
            "any numerics/spherical_solver file while locked, any N1 activation, or a gate "
            "pass recorded before G-FORM + G-AUDIT pass and an N0 accept at one hash."
        ),
    ))

    print(json.dumps({
        "record": str(RECORD.relative_to(ROOT)),
        "record_sha256": h[str(RECORD.relative_to(ROOT))],
        "events": emitted,
        "hours": hours,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
