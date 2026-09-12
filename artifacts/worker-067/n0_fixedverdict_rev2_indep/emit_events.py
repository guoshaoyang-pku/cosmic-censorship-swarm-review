#!/usr/bin/env python3
"""Emit W067-N0-FIXEDVERDICT-REV2-INDEP-01 events to comms/outbox/worker-067.jsonl and
checkpoint 9. Idempotent: re-running skips event_ids already present and does not duplicate the
checkpoint log line. Writes only the outbox file, the checkpoint file and the checkpoint log.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ADIR = ROOT / "artifacts" / "worker-067" / "n0_fixedverdict_rev2_indep"
OUTBOX = ROOT / "comms" / "outbox" / "worker-067.jsonl"
CKPT = ROOT / "runtime" / "state" / "worker-067_checkpoint_9.json"
CKPT_LOG = ROOT / "runtime" / "state" / "worker-067_checkpoints.jsonl"
TASK = "W067-N0-FIXEDVERDICT-REV2-INDEP-01"
# Fixed run identity: makes both the outbox emission and the checkpoint byte-idempotent.
RUN_TS = "20260912T010036"
RUN_AT = "2026-09-12T01:00:36+08:00"
PINS = {
    "numerics/protocol/fixed_replication_verdict.json":
        "dcad962324e3be156d1ef1577b7ee2613fac803058351b643d2c8f67bc787a36",
    "numerics/protocol/fixed_replication_verdict_rev2.json":
        "7954d2d355451e3dbd3e7b7c23769ba204451cc8adf5eb04515910069a10fa60",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json":
        "6542db93eebc5095cb903478dfa6a8d24f09776513f9accb1e73f9d0a58ba38e",
    "numerics/tests/n0_gate_proposal.json":
        "b4192221ff7d96dbb61ce37fa667e1a59b7b290b8ca34f77e7674c03ca5ba2e3",
    "numerics/CONVERGENCE_PROTOCOL.md":
        "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
}
FALSIFIER = (
    "Withdrawn if any of: (a) either verdict artifact, the canonical taxonomy, the frozen run, or "
    "verify_fixed_scheme_independence.py no longer hashes to its pinned prefix at re-measurement; "
    "(b) a re-run finds any differing numeric leaf or any successor difference outside the "
    "declared rebind metadata; (c) the successor's declared chain has an unresolved entry; (d) a "
    "live consumer citing dcad9623 without the successor is re-pinned by an authoritative event "
    "(F2 only); (e) the rebind/naming ambiguity is removed in the successor (F1 only)."
)
AUTHORITY = ("Worker verification event: advisory; does not accept the repair, close G-NUM, set "
             "validation_status=passed, or claim any node transition. Read-only on all canonical "
             "paths; wrote only under artifacts/worker-067/ and runtime/state/worker-067_checkpoint_9.json.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = RUN_AT
    ts = RUN_TS
    report = json.loads((ADIR / "report.json").read_text())
    h_checker, h_report, h_readme = (sha(ADIR / "check_fixedverdict_rev2.py"),
                                     sha(ADIR / "report.json"), sha(ADIR / "README.md"))
    base = f"artifacts/worker-067/n0_fixedverdict_rev2_indep"
    refs = [f"{base}/check_fixedverdict_rev2.py#{h_checker[:12]}",
            f"{base}/report.json#{h_report[:12]}",
            f"{base}/README.md#{h_readme[:12]}",
            "numerics/protocol/fixed_replication_verdict_rev2.json#7954d2d355451e3d",
            "numerics/protocol/fixed_replication_verdict.json#dcad962324e3be15",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "numerics/tests/n0_gate_proposal.json#b4192221ff7d",
            "numerics/protocol/n0_c4_registration_manifest.json#49e8316fde60",
            "numerics/protocol/format_conditions_disposition.json#e7c05ff33fe2",
            "numerics/protocol/n0_gate_proposal_leadverify.json#ea4cf6c9bd3c"]
    common = {"actor": "worker-067", "created_at": now, "class_id": "AF-WCC-SCALAR-SPH",
              "node_id": "N0", "gate": "G-NUM", "next_falsifier": FALSIFIER}
    events = [
        dict(common, event_id=f"w067-rev2indep-{ts}-01-checker", event_type="artifact",
             artifact_type="deterministic_verification_checker", path=f"{base}/check_fixedverdict_rev2.py",
             sha256=h_checker, validation_status="unverified", evidence_refs=refs,
             summary=("Stdlib-only read-only checker: 6 hard pins + 4 canaries measured before and "
                      "after; leaf-level independent comparison of the successor vs the superseded "
                      "verdict; declared-hash chain resolution; generator-semantics recomputation; "
                      "live-consumer citation count; 5 in-memory controls; exit 2 on drift/control "
                      "failure, 1 on unexpected difference.")),
        dict(common, event_id=f"w067-rev2indep-{ts}-02-ledger", event_type="artifact",
             artifact_type="verification_ledger", path=f"{base}/report.json", sha256=h_report,
             validation_status="unverified", evidence_refs=refs,
             summary=("verdict=REV2_METADATA_ONLY_AND_PINS_RESOLVE__SUPERSESSION_NOT_YET_BOUND; "
                      "controls 5/5; 79 numeric leaves equal / 0 differ (declared claim reproduced); "
                      "9/9 resolvable chain claims resolve; 0 unexpected successor differences; 3 "
                      "live consumers unbound; anchors byte-stable.")),
        dict(common, event_id=f"w067-rev2indep-{ts}-03-readme", event_type="artifact",
             artifact_type="method_and_findings_note", path=f"{base}/README.md", sha256=h_readme,
             validation_status="unverified", evidence_refs=refs,
             summary=("Findings F1 field-name ambiguity (non-blocking), F2 supersession not yet "
                      "bound in proposal/C4 manifest/disposition, F3 arithmetic independence "
                      "confirmed; method, controls, reproduction, falsifier, non-claims.")),
        dict(common, event_id=f"w067-rev2indep-{ts}-10-review", event_type="review",
             target_id="numerics/protocol/fixed_replication_verdict_rev2.json#7954d2d355451e3d",
             reviewer="worker-067", verdict="accept", score=4.0, hard_failures=[],
             counts_as_full_schema_verdict=False, counts_as_independent_second_verdict=False,
             authority_note=AUTHORITY, evidence_refs=refs,
             findings={
                 "F1_metadata_only_reproduced": ("Independent leaf walk: 79 numeric leaves equal, 0 "
                    "differ, max difference 0.0 -- reproduces the successor's declared "
                    "numeric_delta_vs_superseded claim; only the 3 declared rebind fields, 2 refresh "
                    "stamps, runtime_seconds and the 4 documented new blocks differ."),
                 "F2_chain_resolves": ("All 9 resolvable declared hashes resolve on disk at "
                    "re-measurement; the frozen-run rev2 taxonomy pin is correctly classed historical."),
                 "F3_flag_semantics": ("fixed_taxonomy_sha256_matches_on_disk=false is consistent with "
                    "the generating script's definition (frozen run pin 66bf917b != live 0abb9ed8); "
                    "the field NAME is ambiguous against the rebound provenance.taxonomy_sha256 and "
                    "a fail-closed consumer keying on the bare boolean could misread the record as "
                    "unbound. Non-blocking; documentation fix only."),
                 "F4_operativity": ("Supersession not yet bound: numerics/tests/n0_gate_proposal.json"
                    "#b4192221ff7d (4 citations), n0_c4_registration_manifest.json#49e8316fde60 (8) "
                    "and format_conditions_disposition.json#e7c05ff33fe2 (5) still cite dcad9623 "
                    "without citing the successor; leadverify#ea4cf6c9bd3c cites both (5/3). The C8 "
                    "w067-provledger dissent is dischargeable by an owner binding action, not by "
                    "this worker verdict."),
                 "F5_scope": ("This task verifies the successor artifact only; it does not re-run the "
                    "solver, does not adjudicate the C8 protocol contest, does not repair either "
                    "artifact, and proposes no gate verdict."),
             }),
        dict(common, event_id=f"w067-rev2indep-{ts}-20-blocker", event_type="blocker",
             severity="medium", evidence_refs=refs,
             description=("C8 supersession not yet bound: the arithmetic-correct successor "
                "fixed_replication_verdict_rev2.json#7954d2d355451e3d is cited by the lead "
                "verification artifact but not by n0_gate_proposal.json, the C4 registration "
                "manifest or the format-conditions disposition, all of which still cite the "
                "superseded dcad9623 as an active evidence pin. The third live C8 dissent "
                "(w067-provledger) therefore remains open until an owner binds the successor."),
             needed_to_unblock=("Owner action only: lead-audit adjudication "
                "astra-life05-gnum-protocol-adjudication (deadline 02:15) or controller binding "
                "of fixed_replication_verdict_rev2.json#7954d2d355451e3d as the replication "
                "evidence of record; then re-pin the proposal/C4 manifest/disposition consumers "
                "or record them as historical. No numerics self-action is required.")),
        dict(common, event_id=f"w067-rev2indep-{ts}-31-claim-corrected", event_type="claim",
             conclusion_type="numerical_evidence", artifact_refs=refs, evidence_refs=refs,
             falsifier=FALSIFIER,
             correction_of="w067-rev2indep-20260912T010036-30-claim",
             correction_note=("Append-only correction: the first claim emission carried the "
                "non-schema conclusion_type 'verification_result' and was rejected by "
                "research_map/schemas.py. This event is otherwise identical and is the claim of "
                "record for this task."),
             status_note="advisory worker verification; not a gate verdict",
             assumptions=["the 6 hard pins are the operative revisions during this run",
                          "exact numeric-leaf equality (no tolerance) is the right test for a metadata-only rebind"],
             statement=("At the pinned hashes, fixed_replication_verdict_rev2.json#7954d2d355451e3d "
                "is a metadata-only rebind of dcad962324e3be15: 79/79 shared numeric leaves equal "
                "(max difference 0.0), all resolvable declared hashes resolve, and the corrected "
                "taxonomy pin 0abb9ed8a961 matches the live canonical taxonomy. The supersession is "
                "not yet bound in three live consumers, so it discharges the provenance dissent only "
                "upon an owner binding action. Advisory worker result, not a gate verdict.")),
        dict(common, event_id=f"w067-rev2indep-{ts}-99-complete", event_type="status",
             status="active", hours=0.4,
             summary=(f"{TASK} complete at worker level: {report['verdict']}; controls 5/5; "
                "0 canonical writes; checkpoint runtime/state/worker-067_checkpoint_9.json. "
                "Completion claim for the task only; not a node transition and not a gate verdict."),
             next_falsifier=FALSIFIER, evidence_refs=refs),
    ]

    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    lock_state = json.loads((ROOT / "research_map" / "research_map.json").read_text()) \
        .get("numerics_lock", {}).get("state")
    ckpt = {
        "schema": "worker-checkpoint/v1", "task_id": TASK, "worker": "worker-067",
        "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM", "status": "active",
        "created_at": now, "verdict": report["verdict"], "controls_passed": "5/5",
        "numerics_lock": lock_state, "authority": AUTHORITY,
        "artifacts": {f"{base}/check_fixedverdict_rev2.py": h_checker,
                      f"{base}/report.json": h_report, f"{base}/README.md": h_readme},
        "pins": PINS,
        "measurements": {"numeric_leaves_equal": 79, "numeric_leaves_differ": 0,
                         "declared_numeric_leaves_compared": 79, "unexpected_differences": 0,
                         "chain_resolved": 9, "chain_unresolved": 0,
                         "flag_consistent_with_generator_semantics": True,
                         "field_name_reading_ambiguous": True,
                         "unbound_consumers": report["operativity"]["unbound_consumers"]},
        "key_findings": ["F1 metadata-only rebind reproduced (79/0)",
                         "F2 all declared hashes resolve",
                         "F3 frozen-run flag consistent, name ambiguous",
                         "F4 supersession not yet bound in 3 live consumers"],
        "next_falsifier": FALSIFIER,
        "outbox_events": [e["event_id"] for e in events],
        "anchors_stable": report["no_write_canary_ok"],
    }
    CKPT.write_text(json.dumps(ckpt, indent=2) + "\n")
    ckpt_sha = sha(CKPT)
    log_line = {"checkpoint": "runtime/state/worker-067_checkpoint_9.json",
                "checkpoint_sha256": ckpt_sha, "task_id": TASK,
                "created_at": now, "verdict": report["verdict"],
                "artifacts": ckpt["artifacts"], "controls_passed": "5/5"}
    have = set()
    if CKPT_LOG.is_file():
        for line in CKPT_LOG.read_text().splitlines():
            try:
                have.add(json.loads(line).get("checkpoint_sha256"))
            except json.JSONDecodeError:
                pass
    if ckpt_sha not in have:
        with CKPT_LOG.open("a") as f:
            f.write(json.dumps(log_line, ensure_ascii=False) + "\n")

    print(json.dumps({"new_events": len(new), "skipped_existing": len(events) - len(new),
                      "checkpoint": "runtime/state/worker-067_checkpoint_9.json",
                      "checkpoint_sha256": ckpt_sha, "verdict": report["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
