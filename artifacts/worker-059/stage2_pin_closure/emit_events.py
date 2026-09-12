#!/usr/bin/env python3
"""Emit the W059-GFORM-STAGE2-PIN-CLOSURE-01 upward events to the worker-059 outbox.

Idempotent: event_ids already present in the outbox are skipped. Validates every
event against research_map.schemas.validate_event before writing.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-059.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = datetime.timezone(datetime.timedelta(hours=8))
NOW = datetime.datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")
TAG = "w059-stage2pin-20260912T0126"
CKPT = "w059-stage2pin-ckpt-20260912T0126"
NODES = "F1,F2a,F2b"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


report = json.loads((HERE / "report.json").read_text(encoding="utf-8"))
digest = report["measurement_digest"]
falsifier = report["measurement"]["falsifier"]

files = {
    "report": HERE / "report.json",
    "harness": HERE / "check_stage2_closure.py",
    "tracer": HERE / "trace_run.py",
    "readme": HERE / "README.md",
}

events = [
    {
        "event_id": f"{TAG}-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "artifact_type": "measurement_report",
        "path": "artifacts/worker-059/stage2_pin_closure/report.json",
        "sha256": sha(files["report"]),
        "validation_status": "unverified",
        "description": (
            "Stage-2 pin-closure census + mutation control at FROZEN rev29 815e08079aef: 48-file repo-local "
            "closure (11 PINNED_OK / 37 UNPINNED_UNTRACKED); a one-line edit to the unpinned stage-2 engine "
            f"flips canonical F1 reject/R03 -> accept with 0/50 pins moved; digest {digest[:16]}."
        ),
        "evidence_refs": [
            f"artifacts/worker-059/stage2_pin_closure/report.json#{digest[:12]}",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        ],
    },
    {
        "event_id": f"{TAG}-artifact-harness",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "artifact_type": "instrument",
        "path": "artifacts/worker-059/stage2_pin_closure/check_stage2_closure.py",
        "sha256": sha(files["harness"]),
        "validation_status": "unverified",
        "description": "Deterministic harness: FROZEN pin census, static + audit-hook dynamic closure, "
        "PINNED/UNPINNED classification, sandbox mutation control, 14 expectations + 3 mutants, reproducible digest.",
        "evidence_refs": ["artifacts/worker-059/stage2_pin_closure/report.json#" + digest[:12]],
    },
    {
        "event_id": f"{TAG}-artifact-tracer",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "artifact_type": "instrument",
        "path": "artifacts/worker-059/stage2_pin_closure/trace_run.py",
        "sha256": sha(files["tracer"]),
        "validation_status": "unverified",
        "description": "sys.addaudithook file-access tracer used to measure the executed dependency closure of each pipeline stage.",
        "evidence_refs": ["artifacts/worker-059/stage2_pin_closure/report.json#" + digest[:12]],
    },
    {
        "event_id": f"{TAG}-artifact-readme",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "artifact_type": "note",
        "path": "artifacts/worker-059/stage2_pin_closure/README.md",
        "sha256": sha(files["readme"]),
        "validation_status": "unverified",
        "description": "Findings HF-059-STAGE2-01..03, observations OBS-1 (live pin drift) / OBS-2 (preflight exit 3), reproduce/falsify, non-claims.",
        "evidence_refs": ["artifacts/worker-059/stage2_pin_closure/report.json#" + digest[:12]],
    },
    {
        "event_id": f"{TAG}-claim-closure",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "statement": (
            "At FROZEN rev29 815e08079aef (measured 2026-09-12T01:24+08:00): the two-stage acceptance pipeline's "
            "repo-local executable closure is 48 files, of which 11 are PINNED_OK and 37 are UNPINNED_UNTRACKED "
            "(the stage-2 engine artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a plus 36 fixture/manifest "
            "files). The pinned run_acceptance.py#e544c36d2d16 resolves stage 2 to that unpinned engine. Baseline "
            "stage 2 rejects the untouched canonical F1 d9cebb9404b2 on R03 (exit 1); a one-line exact-substring -> "
            "variable-wise binder edit confined to the unpinned engine flips it to accept (exit 0) while all 50 "
            "FROZEN rev29 pins still measure as pinned (drift_after == drift_before). The same edit also accepts the "
            "negation-scope-error variant that baseline rejects, while the sem12 leak control stays rejected on R11. "
            f"measurement_digest {digest}."
        ),
        "conclusion_type": "numerical_evidence",
        "assumptions": [
            "FROZEN rev29 815e08079aef is the operative pin set at measured_at; any later revision voids this measurement.",
            "Sandbox copies are byte-identical to live inputs except the single R03 edit (verified by tree diff: exactly one file differs).",
            "Worker measurement only: no canonical write, no node status, no gate verdict.",
        ],
        "falsifier": falsifier,
        "evidence_refs": [
            f"artifacts/worker-059/stage2_pin_closure/report.json#{digest[:12]}",
            "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
            "artifacts/formulation/tools/run_acceptance.py#e544c36d2d16",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        ],
        "artifact_refs": ["artifacts/worker-059/stage2_pin_closure/report.json"],
    },
    {
        "event_id": f"{TAG}-blocker-stage2-unpinned",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "description": (
            "INDEPENDENT CONFIRMATION of lead-form-life08-123 (instrument governance gap), with a mutation control: "
            "the stage-2 engine that run_acceptance.py executes has zero occurrences in FROZEN.json, and editing only "
            "that unpinned file flips the canonical F1 verdict reject->accept with 0/50 pins moved. Any R03 repair "
            "adopted into stage 2 therefore changes gate-relevant behaviour without a visible pin move unless the "
            "engine (and the fixture/rule data its verdicts depend on) is pinned in the same revision."
        ),
        "needed_to_unblock": (
            "In the same FROZEN revision that adopts any stage-2/R03 revision, pin artifacts/worker-06/spec_conformance_audit.py "
            "plus artifacts/formulation/rule_spec.json and the semantic fixture corpus manifest (or record them as non-evidential). "
            "Do not adopt a stage-2 revision while the engine is outside the pin set; re-run this harness afterwards and expect E5 to flip."
        ),
        "evidence_refs": [
            f"artifacts/worker-059/stage2_pin_closure/report.json#{digest[:12]}",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
            "comms/outbox/astra-lead-formulation.jsonl#lead-form-life08-123",
        ],
    },
    {
        "event_id": f"{TAG}-status-exit",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-059",
        "node_id": NODES,
        "class_id": CLASSES,
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.6,
        "summary": (
            "One bounded class-bound task complete (self-selected; no inbox card): W059-GFORM-STAGE2-PIN-CLOSURE-01. "
            "Pin census 50/50; closure 48 files = 11 PINNED_OK / 37 UNPINNED_UNTRACKED; canonical F1 reject/R03 -> accept "
            "under a one-line sandbox edit of the unpinned stage-2 engine with 0/50 pins moved; scope-error variant "
            "accepted by the edited engine while the sem12 leak control stays rejected; digest "
            f"{digest[:16]} reproducible (--verify MATCH). Observation OBS-1: check_variant_registry.py drifted against "
            "its FROZEN rev29 pin during the window (8c7ef46f vs c471da4b, mtime 01:21:56); harness introduced no drift. "
            "Worker event only; no node done, no gate verdict."
        ),
        "checkpoint_id": CKPT,
        "evidence_refs": [
            f"artifacts/worker-059/stage2_pin_closure/report.json#{digest[:12]}",
            "artifacts/worker-059/stage2_pin_closure/check_stage2_closure.py#" + sha(files["harness"])[:12],
            "artifacts/worker-059/stage2_pin_closure/README.md#" + sha(files["readme"])[:12],
        ],
        "next_falsifier": falsifier,
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except ValueError:
            pass

appended = []
for ev in events:
    validate_event(ev)
    if ev["event_id"] in existing:
        print(f"skip duplicate {ev['event_id']}")
        continue
    with OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
    appended.append(ev["event_id"])
    print(f"appended {ev['event_id']}")

print(json.dumps({"appended": appended, "checkpoint": CKPT, "digest": digest}, indent=1))
