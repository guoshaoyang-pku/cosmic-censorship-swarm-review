#!/usr/bin/env python3
"""Emit worker-067's W067-N0-STOPRULE-CLOSURE-01 events to comms/outbox/worker-067.jsonl.

Every event is validated with research_map/schemas.py::validate_event before it is
written; a validation failure aborts without writing. Emission is idempotent: event_ids
already present in the outbox are skipped.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/worker-067.jsonl"
DIR = ROOT / "artifacts/worker-067/n0_stoprule_closure"
SCR = DIR / "check_stoprule_closure.py"
CLO = DIR / "closure.json"
RMD = DIR / "README.md"
CKPT = ROOT / "runtime/state/worker-067_checkpoint_6.json"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    clo = json.loads(CLO.read_text())
    ts = datetime.datetime.fromisoformat(clo["generated_at"]).strftime("%Y%m%dT%H%M%S")
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    summary = clo["summary"]
    i1, i2, i3 = clo["items"]
    pin = {
        "script": sha(SCR), "closure": sha(CLO), "readme": sha(RMD),
        "checkpoint": sha(CKPT) if CKPT.exists() else None,
    }
    ev = f"w067-stoprule-{ts}"
    base = [
        "artifacts/worker-067/n0_stoprule_closure/closure.json#" + pin["closure"][:12],
        "artifacts/worker-067/n0_stoprule_closure/check_stoprule_closure.py#" + pin["script"][:12],
        "artifacts/worker-067/n0_stoprule_closure/README.md#" + pin["readme"][:12],
        "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
        "numerics/tests/n0_gate_proposal.json#b4192221ff7d",
        "numerics/protocol/fixed_replication_verdict.json#dcad962324e3",
        "runtime/state/controller_verification/lifecycle_20260912-003718.json#29b3af744943",
    ]
    next_falsifier = (
        "Void for the recorded anchor hashes if any of the twelve anchors re-hashes "
        "differently; I1 flips if the certification shows <4 rungs / non-constant dt / a "
        "scheme out of band; I2 flips if the proposal F0 pin moves; I3 flips if no accept "
        "binds either frozen hash. The script exits 2 fail-closed on drift or a failed "
        "control.")
    events = [
        {
            "event_id": ev + "-00-take",
            "event_type": "status",
            "actor": "worker-067",
            "created_at": now,
            "class_id": "AF-WCC-SCALAR-SPH",
            "node_id": "N0",
            "gate": "G-NUM",
            "status": "active",
            "hours": 0.1,
            "summary": ("No worker-067 inbox assignment (fleet 2026-09-12T00:38). Took ONE "
                        "bounded class-bound task, W067-N0-STOPRULE-CLOSURE-01: independent, "
                        "read-only, hash-bound closure audit of the three G-NUM stop-rule "
                        "items named in the live controller gate audit (4th resolution / F0 "
                        "re-bind / independent replication verdict). Not a gate verdict and "
                        "no canonical writes."),
            "evidence_refs": [
                "runtime/state/controller_verification/lifecycle_20260912-003718.json#29b3af744943",
                "research_map/research_map.json#controller_gate_audit.G-NUM",
            ],
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": ev + "-10-art-script",
            "event_type": "artifact",
            "actor": "worker-067",
            "created_at": now,
            "class_id": "AF-WCC-SCALAR-SPH",
            "node_id": "N0",
            "gate": "G-NUM",
            "artifact_type": "deterministic_closure_audit_instrument",
            "path": "artifacts/worker-067/n0_stoprule_closure/check_stoprule_closure.py",
            "sha256": pin["script"],
            "validation_status": "unverified",
            "summary": "12-anchor read-only audit; 5 fail-closed controls, mutation controls in memory only.",
        },
        {
            "event_id": ev + "-11-art-closure",
            "event_type": "artifact",
            "actor": "worker-067",
            "created_at": now,
            "class_id": "AF-WCC-SCALAR-SPH",
            "node_id": "N0",
            "gate": "G-NUM",
            "artifact_type": "stoprule_closure_ledger",
            "path": "artifacts/worker-067/n0_stoprule_closure/closure.json",
            "sha256": pin["closure"],
            "validation_status": "unverified",
            "summary": ("I1 MET; I2 PARTIAL_RESIDUAL (downstream rev2 taxonomy pin remains in "
                        "fixed_replication_verdict.json); I3 MET with binding drift (no "
                        "external verdict binds the frozen 3-rung run). Controls 5/5; no "
                        "canonical writes."),
        },
        {
            "event_id": ev + "-12-art-readme",
            "event_type": "artifact",
            "actor": "worker-067",
            "created_at": now,
            "class_id": "AF-WCC-SCALAR-SPH",
            "node_id": "N0",
            "gate": "G-NUM",
            "artifact_type": "method_and_findings_note",
            "path": "artifacts/worker-067/n0_stoprule_closure/README.md",
            "sha256": pin["readme"],
            "validation_status": "unverified",
            "summary": "Per-item status table, method, controls, falsifiers, reproduction, non-claims.",
        },
        {
            "event_id": ev + "-20-review",
            "event_type": "review",
            "actor": "worker-067",
            "created_at": now,
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": ["AF-WCC-SCALAR-SPH"],
            "node_id": "N0",
            "gate": "G-NUM",
            "target_id": "G-NUM-stoprule-closure/N0",
            "reviewer": "worker-067",
            "verdict": "revise",
            "score": 4.0,
            "hard_failures": [],
            "counts_as_full_schema_verdict": False,
            "counts_as_independent_second_verdict": False,
            "authority_note": ("Worker review event: advisory; does not set status=done, "
                               "validation_status=passed, or any gate verdict. Lead-audit "
                               "owns astra-life04-n0-verify."),
            "findings": [
                ("I1 fourth resolution MET: numerics/protocol/n0_fixed_dt_certification.json#"
                 "1677822ceb9c has 4 rungs, dt=1e-4 on every rung of all three schemes "
                 "(lffd 1.999943 / cnfd 1.999864 / cnfem 1.999916), all monotone and in band; "
                 "the proposal re-binds that exact hash and the constant-CFL ladder is "
                 "relabelled mixed-order (9/9 machine checks)."),
                ("I2 F0 re-bind PARTIAL_RESIDUAL: the gate proposal pins the measured canonical "
                 "rev5 taxonomy 0abb9ed8a961, but numerics/protocol/fixed_replication_verdict."
                 "json#dcad962324e3 still carries the superseded rev2 hash 66bf917b in "
                 "chained_evidence_hashes and provenance.taxonomy_sha256. My prior check "
                 "measured that re-bind inert for class membership (5/5 controls); the "
                 "artifact-level repair is still owned by astra-lead-numerics."),
                ("I3 independent replication verdict MET with binding drift: accepts bind both "
                 "the frozen run 6542db93 (deepseek-flash-14, 00:07, numerics-group member, "
                 "against the later-relabelled constant-CFL basis) and the re-based "
                 "certification 1677822ceb9c (worker-081 00:42:05, worker-057 00:42:30, both "
                 "external but worker-advisory). No external verdict binds the frozen run."),
                ("Lock guard intact: numerics_lock.state=locked, locked_nodes=[N1], "
                 "numerics/spherical_solver absent, guard present. N0 node verdict on disk "
                 "remains revise 3.5 (reviews/N0-review-lead-audit.json#e3c314f886be), "
                 "explicitly superseded for adjudication by astra-life04-n0-verify."),
                ("Method limits: this ledger audits binding/closure of already-filed evidence; "
                 "it does not re-run the solver, does not adjudicate the protocol-review "
                 "contest, and does not claim any dissent is formally discharged."),
            ],
            "evidence_refs": base,
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": ev + "-99-complete",
            "event_type": "status",
            "actor": "worker-067",
            "created_at": now,
            "class_id": "AF-WCC-SCALAR-SPH",
            "node_id": "N0",
            "gate": "G-NUM",
            "status": "active",
            "hours": 0.5,
            "summary": ("W067-N0-STOPRULE-CLOSURE-01 complete at worker level: "
                        + summary["disposition"] + "; 5/5 controls, no canonical writes. "
                        "This is a completion claim for the task, not a node transition and "
                        "not a gate verdict; N0 stays active and numerics_lock stays LOCKED."),
            "evidence_refs": base + ["runtime/state/worker-067_checkpoint_6.json"],
            "next_falsifier": next_falsifier,
        },
    ]

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    written = 0
    with open(OUTBOX, "a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            written += 1
    print(f"validated {len(events)} events; appended {written} new to {OUTBOX}")
    for e in events:
        print(" ", "SKIP" if e["event_id"] in existing else "ADD ", e["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
