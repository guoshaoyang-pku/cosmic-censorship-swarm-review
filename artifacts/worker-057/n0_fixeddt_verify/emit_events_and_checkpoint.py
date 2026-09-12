#!/usr/bin/env python3
"""Emit the W057-N0-FIXEDDT-VERIFY-01 events and checkpoint.

Idempotent: event ids already present in comms/outbox/worker-057.jsonl are skipped.
Appends only to worker-057's own outbox and runtime/state/w057_* files.  Never
writes the map, a schema, or another agent's artifact.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-057.jsonl"
STATE = ROOT / "runtime/state"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST)
    stamp = now.strftime("%Y%m%dT%H%M%S%z")
    checker = OUT / "verify_fixed_dt_certification.py"
    report = OUT / "report.json"
    md = OUT / "REPORT.md"
    cert = ROOT / "numerics/protocol/n0_fixed_dt_certification.json"
    module = ROOT / "numerics/tests/flat_wave_replication.py"
    protocol = ROOT / "numerics/CONVERGENCE_PROTOCOL.md"

    h = {
        "checker": sha256_file(checker),
        "report": sha256_file(report),
        "md": sha256_file(md),
        "cert": sha256_file(cert),
        "module": sha256_file(module),
        "protocol": sha256_file(protocol),
    }
    rep = json.loads(report.read_text())
    assert rep["verdict"] == "REPRODUCED" and rep["instrument_valid"]
    assert rep["drift"]["stable"] and rep["drift"]["cert_sha256_at_end"] == h["cert"]

    cert_ref = f"numerics/protocol/n0_fixed_dt_certification.json#{h['cert'][:12]}"
    report_ref = f"artifacts/worker-057/n0_fixeddt_verify/report.json#{h['report'][:12]}"
    checker_ref = f"artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py#{h['checker'][:12]}"
    md_ref = f"artifacts/worker-057/n0_fixeddt_verify/REPORT.md#{h['md'][:12]}"
    module_ref = f"numerics/tests/flat_wave_replication.py#{h['module'][:12]}"
    protocol_ref = f"numerics/CONVERGENCE_PROTOCOL.md#{h['protocol'][:12]}"
    falsifier = rep["falsifier"]
    # stable id prefix (report hash), so re-runs skip instead of duplicating
    eid = f"w057-n0fixeddt-{h['report'][:12]}"

    events = [
        {
            "event_id": f"{eid}-status-start",
            "event_type": "status",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "group_id": "numerics",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "status": "active",
            "hours": 0.1,
            "summary": (
                "No card exists in comms/inbox/worker-057.jsonl; took ONE bounded class-bound task "
                "(AF-WCC-SCALAR-SPH / N0 / G-NUM), permitted under numerics_lock (N0 flat-space only, no "
                "solver code): independent re-analysis of the lead-numerics fixed-dt certification from its "
                "own embedded per-rung rows. The generator script is not imported; this instrument recomputes "
                "the order with least squares, pairwise log-ratio orders and a robust median-of-slopes "
                "estimator, and checks the protocol's internal rules (fixed dt, cfl, steps, monotone ladder, "
                "ratio 2, >=4 rungs, R5 uncertainty, exact cross-scheme agreement rule)."
            ),
            "evidence_refs": [cert_ref, module_ref, protocol_ref],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"{eid}-artifact-checker",
            "event_type": "artifact",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "artifact_type": "independent_reanalysis_instrument",
            "path": "artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py",
            "sha256": h["checker"],
            "validation_status": "unverified",
            "evidence_refs": [cert_ref, module_ref, protocol_ref],
            "falsifier": falsifier,
        },
        {
            "event_id": f"{eid}-artifact-report",
            "event_type": "artifact",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "artifact_type": "fixed_dt_certification_reanalysis_report",
            "path": "artifacts/worker-057/n0_fixeddt_verify/report.json",
            "sha256": h["report"],
            "validation_status": "unverified",
            "measured_inputs": {
                "numerics/protocol/n0_fixed_dt_certification.json": h["cert"],
                "numerics/tests/flat_wave_replication.py": h["module"],
                "numerics/CONVERGENCE_PROTOCOL.md": h["protocol"],
            },
            "reproduce": "python3 artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py",
            "evidence_refs": [report_ref, checker_ref, cert_ref, module_ref, protocol_ref],
            "falsifier": falsifier,
        },
        {
            "event_id": f"{eid}-artifact-reportmd",
            "event_type": "artifact",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "artifact_type": "human_summary",
            "path": "artifacts/worker-057/n0_fixeddt_verify/REPORT.md",
            "sha256": h["md"],
            "validation_status": "unverified",
            "evidence_refs": [md_ref, report_ref],
            "falsifier": falsifier,
        },
        {
            "event_id": f"{eid}-review-cert",
            "event_type": "review",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "target_id": f"numerics/protocol/n0_fixed_dt_certification.json#{h['cert']}",
            "reviewer": "worker-057 (independent of astra-lead-numerics; advisory only)",
            "verdict": "accept",
            "score": 4.0,
            "hard_failures": [],
            "findings": [
                {"severity": "advisory", "check": "A4b",
                 "finding": "citation token 'section 3.4' not literal in CONVERGENCE_PROTOCOL.md; rule resolves at section 3 item 4 line 58"},
                {"severity": "advisory", "check": "A6",
                 "finding": "R5a error-norm naming is implicit only via the 'l2_error' key, not explicit in the claim text"},
                {"severity": "info",
                 "finding": "reproduction covers the derivation chain from the embedded rows; it does not re-run the solver"},
            ],
            "authority_note": ("worker review is advisory; only the controller / leads may move G-NUM or "
                               "numerics_lock. No gate verdict or node status is claimed."),
            "evidence_refs": [report_ref, cert_ref, module_ref, protocol_ref],
        },
        {
            "event_id": f"{eid}-claim",
            "event_type": "claim",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "conclusion_type": "numerical_evidence",
            "statement": (
                f"Artifact-and-checker result, not a physics claim: at numerics/protocol/n0_fixed_dt_certification.json "
                f"sha256 {h['cert']}, every derived number reproduces from the file's own embedded per-rung (dr, l2_error) "
                "rows under an independent least-squares/pairwise/robust estimator battery and the protocol's internal rules: "
                "67/67 checks pass with 0 findings; order estimates 1.999943173893314 (lffd), 1.9998635927240203 (cnfd), "
                "1.9999163079874884 (cnfem) with delta_R5 = max(pair half-range, LS SE) of 8.4437e-05 / 9.3177e-05 / 2.4644e-04; "
                "the robust median-of-pairwise-slopes estimates agree inside delta_R5; all three fixed-dt ladders are strictly "
                "monotone with dt = 1e-4, cfl_effective = dt/dr, steps = 60000, ratio 2 and 4 rungs; cross-scheme max |dp| = "
                "7.958e-05 satisfies the exact R5 rule max(0.25, sqrt(dA^2+dB^2)) = 0.25 per pair; the constant-CFL blocks are "
                "correctly relabelled controls and the declared order shifts reproduce. Two documentation-precision advisories "
                "(A4b citation token, A6 implicit R5a norm naming) do not affect reproduction. This does not re-run the solver, "
                "sets no gate verdict and does not release numerics_lock or N1."
            ),
            "assumptions": [
                "the embedded (dr, l2_error) rows are the published evidence and are taken as given; the frozen module hash is guarded but the solver is not re-run",
                "order is estimated in natural-log space with the certificate's own stated uncertainty rule (delta = max(pair half-range, LS SE))",
                "the protocol rule for two-scheme agreement is |p_A - p_B| <= max(0.25, sqrt(delta_A^2 + delta_B^2))",
            ],
            "falsifier": falsifier,
            "evidence_refs": [report_ref, checker_ref, cert_ref, module_ref, protocol_ref],
        },
        {
            "event_id": f"{eid}-status-complete",
            "event_type": "status",
            "created_at": now.isoformat(),
            "actor": "worker-057",
            "node_id": "N0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM",
            "group_id": "numerics",
            "task_id": "W057-N0-FIXEDDT-VERIFY-01",
            "status": "active",
            "hours": 0.4,
            "claims_completion": False,
            "summary": (
                "W057-N0-FIXEDDT-VERIFY-01 complete as one bounded class-bound worker task: verdict REPRODUCED "
                "(67/67 checks, 0 findings, 6/6 fail-closed controls, certificate hash stable end-to-end), 2 non-blocking "
                "documentation advisories, advisory review accept 4.0 at the pinned certificate hash. Checkpoint written to "
                "runtime/state/w057_checkpoint_n0fixeddt.json and w057_checkpoints.jsonl. No gate verdict, no node completion, "
                "no numerics_lock change; worker slot can be recycled."
            ),
            "evidence_refs": [report_ref, checker_ref, md_ref, cert_ref],
            "next_falsifier": falsifier,
        },
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue

    appended = []
    with OUTBOX.open("a") as f:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev) + "\n")
            appended.append(ev["event_id"])

    checkpoint = {
        "checkpoint": "w057-n0fixeddt-1",
        "at": now.isoformat(),
        "worker": "worker-057",
        "hours_spent_estimate": 0.4,
        "assignment": "W057-N0-FIXEDDT-VERIFY-01 (self-selected; no inbox card)",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "verdict": rep["verdict"],
            "instrument_valid": rep["instrument_valid"],
            "checks": len(rep["checks"]),
            "failed_checks": rep["finding_count"],
            "advisories": rep["advisory_count"],
            "controls": f"{sum(1 for c in rep['controls'] if c['pass'])}/{len(rep['controls'])}",
            "no_completion_claim": "worker cannot set done/passed, a gate verdict, or release numerics_lock/N1",
        },
        "inputs": {
            "numerics/protocol/n0_fixed_dt_certification.json": {"sha256": h["cert"], "stable": rep["drift"]["stable"]},
            "numerics/tests/flat_wave_replication.py": {"sha256": h["module"]},
            "numerics/CONVERGENCE_PROTOCOL.md": {"sha256": h["protocol"]},
        },
        "recomputed_order": {
            s: {"ls": rep["recomputed"][s]["order_ls"], "robust": rep["recomputed"][s]["order_robust"],
                "delta_R5": rep["recomputed"][s]["delta_R5"]} for s in rep["recomputed"]
        },
        "artifacts": {
            "artifacts/worker-057/n0_fixeddt_verify/verify_fixed_dt_certification.py": {"sha256": h["checker"]},
            "artifacts/worker-057/n0_fixeddt_verify/report.json": {"sha256": h["report"]},
            "artifacts/worker-057/n0_fixeddt_verify/REPORT.md": {"sha256": h["md"]},
        },
        "events_appended": appended,
        "falsifier": falsifier,
        "next_falsifier": "Any change to the certification sha256 voids this report for the new bytes; G-NUM still requires the gate chain and the lead/controller verdict.",
    }
    (STATE / "w057_checkpoint_n0fixeddt.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    log = STATE / "w057_checkpoints.jsonl"
    already_logged = False
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                if json.loads(line).get("checkpoint") == checkpoint["checkpoint"]:
                    already_logged = True
                    break
            except json.JSONDecodeError:
                continue
    if not already_logged:
        with log.open("a") as f:
            f.write(json.dumps(checkpoint) + "\n")

    print(json.dumps({"appended_events": appended, "checkpoint": str(STATE / "w057_checkpoint_n0fixeddt.json"),
                      "hashes": h}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
