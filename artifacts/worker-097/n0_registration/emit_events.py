#!/usr/bin/env python3
"""W097-N0-REGISTRATION-01: write the worker checkpoint and append the outbox events.

Appends to comms/outbox/worker-097.jsonl (never rewrites) and writes
runtime/state/w097_n0_registration_checkpoint.json (+ .jsonl).

Usage: python3 artifacts/worker-097/n0_registration/emit_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
TASK = "W097-N0-REGISTRATION-01"
OUTBOX = ROOT / "comms" / "outbox" / "worker-097.jsonl"
STATE = ROOT / "runtime" / "state"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    controls = json.loads((HERE / "controls.json").read_text())
    created = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    pin = report["pins"]["runtime/state/artifact_hashes.json"]
    snap = ROOT / report["pins"]["registry_snapshot"]
    n0_review = ROOT / "reviews" / "N0-review-final-verify.json"

    artifacts = {
        "report.json": HERE / "report.json",
        "controls.json": HERE / "controls.json",
        "measure.py": HERE / "measure.py",
        "FINDINGS.md": HERE / "FINDINGS.md",
        "PRE_REGISTRATION.md": HERE / "PRE_REGISTRATION.md",
        report["pins"]["registry_snapshot"]: snap,
    }
    hashes = {p: sha256_file(f) for p, f in artifacts.items()}
    focus = report["b_n0_r2_1"]
    census = report["census"]

    checkpoint = {
        "checkpoint_id": f"w097-n0reg-{stamp}",
        "task_id": TASK,
        "worker": "worker-097",
        "created_at": created,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "status": "task-complete-worker-level",
        "registry_pin": pin,
        "focus_b_n0_r2_1": {"registered": focus["registered"], "unregistered": focus["unregistered"],
                            "paths": [{k: r[k] for k in ("path", "status", "measured_sha256", "bytes", "registered")}
                                      for r in focus["paths"]]},
        "census": {k: census[k] for k in ("resolvable_refs", "files", "registered", "unregistered",
                                          "mutable_excluded", "dangling", "stale_no_match")},
        "controls_pass": report["controls_pass"],
        "predictions": report["predictions_summary"],
        "proposed_repair_effect": {"option_a_files": report["proposed_repair"]["option_a"]["effect_files_registered"],
                                   "option_b_entries": report["proposed_repair"]["option_b"]["effect_new_entries"]},
        "artifact_sha256": hashes,
        "falsifier": report["falsifier"],
        "not_claimed": report["not_claimed"],
        "next_falsifier": "A cited review evidence path that resolves and is covered by an existing scan root while the "
                          "report calls it unregistered; a re-run against the pinned snapshot that disagrees; or the live "
                          "registry acquiring artifacts/worker-* keys before the controller applies a repair.",
        "exit": "clean; no ingest, no gate verdict, no node status, no canonical write",
    }
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "w097_n0_registration_checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))
    with (STATE / "w097_n0_registration_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "created_at": created,
                            "task_id": TASK, "registry_pin": pin,
                            "focus_registered": focus["registered"], "focus_unregistered": focus["unregistered"],
                            "controls_pass": report["controls_pass"]}) + "\n")

    def ev(e):
        return json.dumps(e, sort_keys=True)

    events = []
    for path, f in artifacts.items():
        if "/snapshot/" in path:
            node_art = "registry_snapshot"
        elif path.endswith(".json"):
            node_art = "measurement_report" if path == "report.json" else "control_set"
        else:
            node_art = "audit_script" if path.endswith(".py") else "findings_note"
        events.append(ev({
            "event_id": f"w097-n0reg-artifact-{path.replace('/', '_')}-{stamp}", "event_type": "artifact",
            "created_at": created, "actor": "worker-097", "node_id": "N0", "gate": "G-NUM",
            "class_id": "AF-WCC-SCALAR-SPH", "task_id": TASK, "artifact_type": node_art, "path": path,
            "sha256": hashes[path], "validation_status": "unverified",
            "summary": f"W097-N0-REGISTRATION-01 deliverable at registry pin {pin[:12]}",
            "evidence_refs": [f"{path}#sha256:{hashes[path]}"],
        }))

    claim_statement = (
        f"At registry pin {pin[:12]} (snapshot {report['pins']['registry_snapshot']}#sha256:{hashes[report['pins']['registry_snapshot']]}): "
        f"of the six evidence paths named by B-N0-R2-1, 3 resolve and are registered "
        f"(numerics/CONVERGENCE_PROTOCOL.md 1e6cdf04d7a2, numerics/results/flat_wave_convergence.json e9e124227c4d, "
        f"numerics/gates.py fcd1d70991b6); the 3 N0 independent-replication artifacts under artifacts/worker-046, "
        f"-057, -081 exist on disk (measured 814452111bc8 / b906445878f3 / 65ae766d9e4c) but are absent from both "
        f"registry sections, because the final registry contains 0 keys under artifacts/worker-* while 11823 worker "
        f"files exist on disk. Bounded repair options measured: add the three dirs to the scan roots (630 files) or "
        f"register review-cited files (294 entries, 217 under artifacts/worker-*). Controls 6/6 PASS; worker "
        f"measurement only, no canonical write and no gate verdict."
    )
    events.append(ev({
        "event_id": f"w097-n0reg-claim-b-n0-r2-1-{stamp}", "event_type": "claim", "created_at": created,
        "actor": "worker-097", "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "task_id": TASK, "conclusion_type": "stability_result", "statement": claim_statement,
        "assumptions": [
            "PROTOCOL rule 2 binds a done node's declared artifact to a sha256 in runtime/state/artifact_hashes.json; "
            "the audit lead's B-N0-R2-1 additionally treats the six cited review paths as requiring registration",
            "registration scope is defined by the audit_evidence.py scan roots; out-of-root citations are not "
            "automatically rule-2 violations, so B-N0-R2-1 is reported as the actionable subset",
            "runtime/state/artifact_hashes.json is controller-mutable by design; the saved snapshot, not the live "
            "file, is the pin for this measurement",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [
            f"report.json#sha256:{hashes['report.json']}",
            f"controls.json#sha256:{hashes['controls.json']}",
            f"measure.py#sha256:{hashes['measure.py']}",
            f"{report['pins']['registry_snapshot']}#sha256:{hashes[report['pins']['registry_snapshot']]}",
            f"reviews/N0-review-final-verify.json#sha256:{sha256_file(n0_review)}",
        ],
    }))

    events.append(ev({
        "event_id": f"w097-n0reg-status-final-{stamp}", "event_type": "status", "created_at": created,
        "actor": "worker-097", "node_id": "N0", "gate": "G-NUM", "class_id": "AF-WCC-SCALAR-SPH",
        "task_id": TASK, "status": "active", "hours": 0.2,
        "summary": "CHECKPOINT + EXIT. W097-N0-REGISTRATION-01 complete at worker level: the B-N0-R2-1 residual is "
                   "exactly the 3 worker replication artifacts (worker-046/-057/-081), which exist on disk and are "
                   "structurally outside every audit_evidence.py scan root (0 registry keys under artifacts/worker-*); "
                   "the 3 numerics/ paths are registered; 6/6 controls PASS at a stable registry pin; P1/P2/P5 "
                   "confirmed, P3/P4 disconfirmed and reported. Worker measurement only; no ingest, no gate verdict, "
                   "no node status, no canonical write.",
        "evidence_refs": [
            f"report.json#sha256:{hashes['report.json']}",
            f"controls.json#sha256:{hashes['controls.json']}",
            f"runtime/state/w097_n0_registration_checkpoint.json#sha256:{sha256_file(STATE / 'w097_n0_registration_checkpoint.json')}",
        ],
        "next_falsifier": checkpoint["next_falsifier"],
    }))

    with OUTBOX.open("a") as f:
        for e in events:
            f.write(e + "\n")
    print(json.dumps({"appended": len(events), "outbox": str(OUTBOX.relative_to(ROOT)),
                      "checkpoint": checkpoint["checkpoint_id"], "registry_pin": pin[:16],
                      "artifacts": hashes}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
