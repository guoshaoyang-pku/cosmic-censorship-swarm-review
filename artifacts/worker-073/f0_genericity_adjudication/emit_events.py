#!/usr/bin/env python3
"""Emit worker-073's adjudication events and worker checkpoint.

Fail-closed: re-measures the F0 pins and the artifact hashes before emitting;
refuses to write events if any pin moved (the adjudication would then cite
stale bytes). Every event is validated against research_map/schemas.py before
it is appended to comms/outbox/worker-073.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/FROZEN.json":
        "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
}
CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
ARTIFACTS = {
    "artifacts/worker-073/f0_genericity_adjudication/adjudicate.py": None,
    "artifacts/worker-073/f0_genericity_adjudication/report.json": None,
    "artifacts/worker-073/f0_genericity_adjudication/README.md": None,
    "artifacts/worker-073/f0_genericity_adjudication/emit_events.py": None,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    for rel, expected in PINS.items():
        got = sha256(ROOT / rel)
        if got != expected:
            print(f"PIN DRIFT {rel}: {got}", file=sys.stderr)
            return 3
    for rel in ARTIFACTS:
        if not (ROOT / rel).exists():
            print(f"missing artifact {rel}", file=sys.stderr)
            return 3
        ARTIFACTS[rel] = sha256(ROOT / rel)

    report = json.loads((OUT / "report.json").read_text(encoding="utf-8"))
    adj = report["adjudication"]
    evidence = [
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
        "artifacts/formulation/FROZEN.json#2f358f6722d92062",
        f"artifacts/worker-073/f0_genericity_adjudication/report.json#{ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/report.json'][:12]}",
        f"artifacts/worker-073/f0_genericity_adjudication/adjudicate.py#{ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/adjudicate.py'][:12]}",
    ]
    falsifier = report["falsifiers"][0]

    events = [
        {
            "event_id": f"w073-f0gen-{STAMP}-status-task",
            "event_type": "status",
            "created_at": NOW,
            "actor": "worker-073",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": CLASSES,
            "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "No assignment card exists in comms/inbox for worker-073 (recycled slot). "
                "Took ONE bounded class-bound task: independent mechanical adjudication of the "
                "F0V-S1 (worker-073, blocking) vs B3 (worker-087, non-blocking) disposition split "
                "at the pinned F0 pair. Pre-registered decision rule + 9 controls; result H-DEFER. "
                "No gate verdict, node status or validation_status is set."
            ),
            "evidence_refs": evidence,
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w073-f0gen-{STAMP}-artifact-instrument",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-073",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": CLASSES,
            "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
            "artifact_type": "adjudication_instrument",
            "path": "artifacts/worker-073/f0_genericity_adjudication/adjudicate.py",
            "sha256": ARTIFACTS[
                "artifacts/worker-073/f0_genericity_adjudication/adjudicate.py"
            ],
            "validation_status": "unverified",
            "summary": (
                "Deterministic read-only adjudicator: strict duplicate-key YAML loader, "
                "pre-registered D1-D6 decision rule, 9 in-memory controls plus a duplicate-key "
                "loader control; exit 0/2/3, fail-closed on pin drift."
            ),
        },
        {
            "event_id": f"w073-f0gen-{STAMP}-artifact-report",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-073",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": CLASSES,
            "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
            "artifact_type": "adjudication_report",
            "path": "artifacts/worker-073/f0_genericity_adjudication/report.json",
            "sha256": ARTIFACTS[
                "artifacts/worker-073/f0_genericity_adjudication/report.json"
            ],
            "validation_status": "unverified",
            "summary": (
                "Adjudication H-DEFER: F0V-S1 measurement confirmed, blocking label not supported "
                "at the pin (in-vocabulary 'unresolved', no theorem status asserted, 4/4 deferral "
                "declarations, companion supplement agrees); genericity_topology absent 4/4 axes is "
                "a promotion blocker; 9/9 controls fired."
            ),
        },
        {
            "event_id": f"w073-f0gen-{STAMP}-artifact-readme",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-073",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": CLASSES,
            "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
            "artifact_type": "adjudication_note",
            "path": "artifacts/worker-073/f0_genericity_adjudication/README.md",
            "sha256": ARTIFACTS[
                "artifacts/worker-073/f0_genericity_adjudication/README.md"
            ],
            "validation_status": "unverified",
            "summary": "One-page record: question, pins, decision rule, result, controls, limits, falsifiers, reproduction.",
        },
        {
            "event_id": f"w073-f0gen-{STAMP}-claim-disposition",
            "event_type": "claim",
            "created_at": NOW,
            "actor": "worker-073",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": CLASSES,
            "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
            "statement": (
                "At the pinned F0 pair (declared 0abb9ed8a961, supplement d7419b4e8963, FROZEN "
                "rev28 2f358f6722d92062), F0V-S1 is confirmed as a measurement but reclassified: "
                "axes.genericity_kind='unresolved' with a comeager-quantified scalar conclusion is "
                "a must-discharge-before-promotion objection, NOT a G-F0 hard failure, because "
                "'unresolved' is in-vocabulary, the artifact asserts no theorem status, the "
                "unresolved state is declared 4/4 ways inside the artifact and corroborated by the "
                "companion supplement, and the four declared G-F0 criteria do not include "
                "genericity resolution. Secondary mechanical gap: genericity_topology is absent "
                "from 4/4 class axes while 4/4 conclusions carry a generic quantifier; the "
                "artifact's own topology rule defers naming until a theorem-status claim exists. "
                "Erratum to worker-073's prior review: severity label only, measurement unchanged. "
                "This claim asserts no theorem and sets no gate verdict."
            ),
            "conclusion_type": "formal_model",
            "assumptions": [
                "research_map/research_map.json is the sole global state; FROZEN rev28 pins the two F0 logical artifacts at the measured hashes",
                "the declared G-F0 criteria are exactly: file exists; exactly 4 separate class ids; disjointness tests; 2 independent reviewer verdicts",
                "the artifact's own field_vocabulary and status semantics govern whether the genericity state is legal at draft_unverified status",
            ],
            "falsifier": falsifier,
            "evidence_refs": evidence,
            "artifact_refs": [
                f"artifacts/worker-073/f0_genericity_adjudication/report.json#{ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/report.json'][:12]}",
                f"artifacts/worker-073/f0_genericity_adjudication/adjudicate.py#{ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/adjudicate.py'][:12]}",
            ],
        },
        {
            "event_id": f"w073-f0gen-{STAMP}-status-complete",
            "event_type": "status",
            "created_at": NOW,
            "actor": "worker-073",
            "node_id": "F0",
            "gate": "G-F0",
            "class_id": "AF-WCC-SCALAR-SPH",
            "class_ids": CLASSES,
            "task_id": "W073-F0-GENERICITY-ADJUDICATION-01",
            "status": "active",
            "hours": 0.5,
            "summary": (
                "CHECKPOINT + worker-level completion (not a node done and not a gate verdict). "
                f"One class-bound task delivered: F0V-S1 disposition adjudicated H-DEFER, 9/9 "
                f"controls fired, pins stable. Artifacts: adjudicate.py {ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/adjudicate.py'][:12]}, "
                f"report.json {ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/report.json'][:12]}, "
                f"README.md {ARTIFACTS['artifacts/worker-073/f0_genericity_adjudication/README.md'][:12]}. "
                f"Worker checkpoint runtime/state/w073_checkpoint_f0_genericity_{STAMP}.json."
            ),
            "evidence_refs": evidence
            + [
                f"runtime/state/w073_checkpoint_f0_genericity_{STAMP}.json"
            ],
            "next_falsifier": falsifier,
        },
    ]

    for ev in events:
        validate_event(ev)

    outbox = ROOT / "comms/outbox/worker-073.jsonl"
    with outbox.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # research map hash at checkpoint time
    map_sha = sha256(ROOT / "research_map/research_map.json")
    checkpoint = {
        "checkpoint_id": f"w073-ckpt-f0-genericity-{STAMP}",
        "actor": "worker-073",
        "agent_id": "worker-073",
        "created_at": NOW,
        "measured_at": NOW,
        "task": (
            "One class-bound task: independent mechanical adjudication of the F0V-S1 (worker-073, "
            "blocking) vs B3 (worker-087, non-blocking) disposition split at the pinned F0 pair; "
            "pre-registered decision rule, 9 controls, strict duplicate-key parsing."
        ),
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": CLASSES,
        "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        "assignment_ref": "none (no inbox card for worker-073; task self-selected from the live F0 dispute)",
        "artifacts": ARTIFACTS,
        "reviewed_pins": PINS,
        "adjudication": {
            "overall": adj["overall"],
            "F1_scalar_unresolved_vs_comeager": adj["F1_scalar_unresolved_vs_comeager"],
            "F2_genericity_topology_slot": adj["F2_genericity_topology_slot"],
            "F3_pair_consistency": adj["F3_pair_consistency"],
            "F4_supplement_value_list": adj["F4_supplement_value_list"],
            "F5_class_merge": adj["F5_class_merge"],
        },
        "controls": {
            "all_fired": all(c["fired"] for c in report["controls"]),
            "n": len(report["controls"]),
            "duplicate_key_loader_control": report["duplicate_key_loader_control"]["fired"],
        },
        "erratum": report["erratum"],
        "disposition": report["disposition"],
        "pins_stable_during_run": True,
        "map_sha256_measured": map_sha,
        "events_emitted": [e["event_id"] for e in events],
        "next_falsifier": falsifier,
        "reproduce": "python3 artifacts/worker-073/f0_genericity_adjudication/adjudicate.py",
    }
    ckpt_path = ROOT / f"runtime/state/w073_checkpoint_f0_genericity_{STAMP}.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"emitted {len(events)} events to {outbox}")
    print(f"checkpoint {ckpt_path} sha256={sha256(ckpt_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
