#!/usr/bin/env python3
"""Emit worker-074's N1-BLOCK-AUDIT-01 checkpoint + comms events (idempotent).

Writes:
  runtime/state/w074_checkpoint_1.json          (worker checkpoint; not the controller's)
  artifacts/worker-074/n1_block_audit/CHECKPOINT.json (copy for artifact-local provenance)
  comms/outbox/worker-074.jsonl                 (append status + artifact events)

Worker authority note: events carry status=active and validation_status=unverified.  This
script never writes research_map/events.jsonl (controller ingest only) and never sets a gate.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
AT = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
TASK = "N1-BLOCK-AUDIT-01"
OUTDIR = ROOT / "artifacts/worker-074/n1_block_audit"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report = json.loads((OUTDIR / "report.json").read_text())
    report_sha = sha256_file(OUTDIR / "report.json")
    script_sha = sha256_file(OUTDIR / "audit_n1_block.py")
    snap = report["snapshot_before"]

    checkpoint = {
        "checkpoint": 1,
        "at": AT,
        "worker": "worker-074",
        "hours_spent_estimate": report.get("hours_spent_estimate", 0.4),
        "task_id": TASK,
        "assignment": ("no assignment card existed for worker-074; one class-bound task taken "
                       "from the map's open queue: N1-BLOCK (AF-WCC-SCALAR-SPH, gate G-NUM)"),
        "node_id": "N1-BLOCK",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "status": {
            "delivered": True,
            "validation_status": "unverified",
            "gate_effect": "none - worker cannot set a gate verdict or node status",
            "measurement": {
                "condition_mapping_one_to_one": report["condition_mapping"]["one_to_one"],
                "state_rows_agree": {k: v.get("agrees")
                                     for k, v in report["state_claims"].items()},
                "guard_tests_agree": {k: v.get("agrees")
                                      for k, v in report["guard_tests"].items()},
                "findings": [f["id"] for f in report["findings"]],
                "headline_defect": ("W074-F3: selfgravity_lock_guard returns PASS with a planted "
                                    "solver when numerics_lock.state is missing or miscased"),
            },
        },
        "artifacts": [
            {"path": "artifacts/worker-074/n1_block_audit/report.json", "sha256": report_sha},
            {"path": "artifacts/worker-074/n1_block_audit/audit_n1_block.py", "sha256": script_sha},
        ],
        "snapshot": {
            "map_sha256": snap["map_sha256"],
            "blockers_md_sha256": snap["blockers_md_sha256"],
            "protocol_sha256": snap["protocol_sha256"],
        },
        "next_falsifier": report["next_falsifier"],
        "authority_note": report["worker_authority_note"],
    }
    ckpt_path = ROOT / "runtime/state/w074_checkpoint_1.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))
    ckpt_sha = sha256_file(ckpt_path)
    (OUTDIR / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

    common = {
        "actor": "worker-074",
        "created_at": AT,
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "gate": "G-NUM",
        "node_id": "N1-BLOCK",
        "task_id": TASK,
    }
    status_event = dict(common, **{
        "event_id": f"w074-{STAMP}-n1-block-audit-task",
        "event_type": "status",
        "status": "active",
        "hours": report.get("hours_spent_estimate", 0.4),
        "summary": (
            "Took one class-bound task (N1-BLOCK-AUDIT-01, class AF-WCC-SCALAR-SPH, node "
            "N1-BLOCK, gate G-NUM): adversarial audit of numerics/blockers.md vs "
            "numerics_lock. Result: release table 1:1 (6/6 conditions, none added/dropped); "
            "all six current-state cells agree with measured artifacts; all five guard runs "
            "behave as declared (release evaluator N1_BLOCKED exit 3; violation tripwire PASS "
            "with no solver present). Adversarial fixtures found one defect: "
            "selfgravity_lock_guard returns PASS with a planted numerics/spherical_solver/ when "
            "numerics_lock.state is missing ('unknown') or 'LOCKED', while numerics.gates.py "
            "defaults an absent state to 'locked' (W074-F3, major, fail-open). Artifact: "
            f"artifacts/worker-074/n1_block_audit/report.json#{report_sha[:12]}. Worker evidence "
            "only; no node status or gate verdict is claimed."
        ),
        "evidence_refs": [
            f"artifacts/worker-074/n1_block_audit/report.json#{report_sha[:12]}",
            f"runtime/state/w074_checkpoint_1.json#{ckpt_sha[:12]}",
            "numerics/blockers.md#33dd7a21ff56",
            f"research_map/research_map.json#{snap['map_sha256'][:12]}",
        ],
        "next_falsifier": (
            "lead-audit re-runs fixtures FX-A/FX-B; if a solver-bearing map with missing or "
            "miscased numerics_lock.state yields FAIL, W074-F3 is void."
        ),
    })
    artifact_event = dict(common, **{
        "event_id": f"w074-{STAMP}-n1-block-audit-report",
        "event_type": "artifact",
        "artifact_type": "audit_report",
        "path": "artifacts/worker-074/n1_block_audit/report.json",
        "sha256": report_sha,
        "validation_status": "unverified",
        "note": (
            "N1-BLOCK-AUDIT-01 evidence: 1:1 condition map, row-by-row state verification, five "
            "guard runs, five planted-violation fixtures (temp dirs only), scope scan. Findings "
            "W074-F1..F5; W074-F3 is a fail-open edge in the violation guard for missing/miscased "
            "numerics_lock.state. Supporting raw outputs under "
            "artifacts/worker-074/n1_block_audit/raw/ and checkpoint "
            f"runtime/state/w074_checkpoint_1.json#{ckpt_sha[:12]}."
        ),
        "evidence_refs": [
            f"artifacts/worker-074/n1_block_audit/report.json#{report_sha[:12]}",
            "artifacts/worker-074/n1_block_audit/audit_n1_block.py",
            "artifacts/worker-074/n1_block_audit/raw/guard_repo_run.txt",
            "artifacts/worker-074/n1_block_audit/raw/gates_check.txt",
            f"runtime/state/w074_checkpoint_1.json#{ckpt_sha[:12]}",
            "numerics/blockers.md#33dd7a21ff56",
        ],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
    })

    outbox = ROOT / "comms/outbox/worker-074.jsonl"
    existing = outbox.read_text().splitlines() if outbox.exists() else []
    existing_ids = set()
    for line in existing:
        try:
            existing_ids.add(json.loads(line).get("event_id"))
        except ValueError:
            pass

    written = []
    for ev in (status_event, artifact_event):
        validate_event(ev)  # fail loudly rather than write an invalid line
        if ev["event_id"] in existing_ids:
            written.append({"event_id": ev["event_id"], "status": "already-present"})
            continue
        with outbox.open("a") as f:
            f.write(json.dumps(ev, sort_keys=True) + "\n")
        written.append({"event_id": ev["event_id"], "status": "appended"})

    print(json.dumps({
        "at": AT,
        "checkpoint_path": str(ckpt_path.relative_to(ROOT)),
        "checkpoint_sha256": ckpt_sha,
        "report_sha256": report_sha,
        "script_sha256": script_sha,
        "outbox": str(outbox.relative_to(ROOT)),
        "events": written,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
