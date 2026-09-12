#!/usr/bin/env python3
"""Emit FORM-PROBE-10 events to comms/outbox/worker-06.jsonl (idempotent by event_id).

Every event carries IDs, evidence refs as path#sha256-prefix, and a falsifier.
No node completion, no theorem, no gate verdict is claimed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-06.jsonl"
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


FALSIFIER = ("a pass_control rejected by either stage at the pinned hashes, a fixture shown not to "
             "violate its documented invariant, or a later revision whose gate catches these "
             "fixtures (re-run the frozen corpus and compare)")
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def artifact_events():
    arts = [
        ("manifest", "artifacts/worker-06/probe10/manifest.json", "probe_corpus_manifest",
         "pre-registered 12 mutants / 8 families / 7 controls; base and gate hashes pinned"),
        ("report", "artifacts/worker-06/probe10/report.json", "measurement_report",
         "two-stage aggregates, controls, validity; union escape 0.9167 (11/12) at FROZEN rev28"),
        ("blindspot", "artifacts/worker-06/probe10/blindspot_report.json", "blindspot_report",
         "per-fixture caught/blindspot with minimal repro; 11/12 union escapes across 8 families"),
        ("posthoc", "artifacts/worker-06/probe10/posthoc_report.json", "posthoc_observation",
         "POST-HOC (not pre-registered): 2/2 synonym probes escape all stages"),
        ("toolchain", "artifacts/worker-06/probe10/run_probes.py", "measurement_toolchain",
         "generator/runner + documented single-delta calibrated auditor derivation"),
    ]
    evs = []
    for tag, rel, atype, note in arts:
        evs.append({
            "event_id": f"w06-20260912-form-probe10-{tag}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-06",
            "node_id": "A1",
            "gate": "G-CLASSBIND",
            "class_ids": CLASSES,
            "artifact_type": atype,
            "path": rel,
            "sha256": sha(rel),
            "validation_status": "unverified",
            "summary": note,
            "evidence_refs": [
                f"artifacts/worker-06/probe10/manifest.json#{sha('artifacts/worker-06/probe10/manifest.json')[:12]}",
                f"artifacts/formulation/FROZEN.json#{sha('artifacts/formulation/FROZEN.json')[:12]}",
                "artifacts/formulation/evidence/gate_probe_blindspot_measurement.json#877de7d73b15",
            ],
            "falsifier": FALSIFIER,
            "not_claimed": "no gate verdict, no node completion, no theorem, no physics result",
        })
    return evs


def status_event():
    mrel = "artifacts/worker-06/probe10/manifest.json"
    rrel = "artifacts/worker-06/probe10/report.json"
    brel = "artifacts/worker-06/probe10/blindspot_report.json"
    return {
        "event_id": "w06-20260912-form-probe10-status",
        "event_type": "status",
        "created_at": now(),
        "actor": "worker-06",
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": CLASSES,
        "status": "active",
        "hours": 2.0,
        "summary": ("FORM-PROBE-10, one class-bound task: independent out-of-sample rephrased probe "
                    "corpus on FROZEN rev28. VALID (5/5 pass controls accepted by both stages, 2/2 "
                    "sensitivity controls caught). 12 mutants / 8 families: structural escape 0.9167, "
                    "semantic escape 1.0000, union escape 0.9167 (11/12); the single catch (m03) is "
                    "R09's token-level 'complete' scan, and a post-hoc synonym probe escapes all "
                    "stages. Frozen auditor rejects canonical WCC on an R03 binder format false "
                    "positive, so stage B' is a documented single-delta calibration; frozen-B and "
                    "hardened-B rates reported beside every B' number. Deliverable: blindspot_report."
                    "json with the 8 escaping families and candidate fixes per family."),
        "evidence_refs": [
            f"{mrel}#{sha(mrel)[:12]}", f"{rrel}#{sha(rrel)[:12]}", f"{brel}#{sha(brel)[:12]}",
            f"artifacts/formulation/FROZEN.json#{sha('artifacts/formulation/FROZEN.json')[:12]}",
            f"artifacts/formulation/tools/check_class_schema.py#{sha('artifacts/formulation/tools/check_class_schema.py')[:12]}",
        ],
        "next_falsifier": FALSIFIER,
        "not_claimed": "no gate verdict, no node completion, no theorem; interpretation is bound to the pinned hashes only",
    }


def main() -> int:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:  # noqa: BLE001
                    pass
    events = artifact_events() + [status_event()]
    added = 0
    with OUTBOX.open("a") as fh:
        for e in events:
            if e["event_id"] in existing:
                print("skip existing", e["event_id"])
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            added += 1
            print("appended", e["event_id"], e["sha256"][:12] if "sha256" in e else "")
    print(f"appended {added} events to {OUTBOX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
