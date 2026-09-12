#!/usr/bin/env python3
"""
W089-F2B-F0ADJ-02 lifecycle emitter.

Reads f0adj_report.json, emits the worker's upward events to
comms/outbox/worker-089.jsonl (idempotent by event_id), writes a local
events.jsonl record, and writes the worker checkpoint to
runtime/state/w089_checkpoint_2.json (+ append-only log).

Writes only: this artifact directory, comms/outbox/worker-089.jsonl,
runtime/state/w089_checkpoint_2.json, runtime/state/w089_checkpoints.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-089.jsonl"
STATE = ROOT / "runtime/state"

sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402  (repo-local validator)

TASK = "W089-F2B-F0ADJ-02"
CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"

FALSIFIER = (
    "Any of the following falsifies this report: (i) the measured sha256 of either taxonomy path "
    "differs from the value cited here or in f0_mirror_conflict.json; (ii) F2b's "
    "class_contract_pointer fragment resolves in the canonical declared-F0 taxonomy (falsifies "
    "'load-bearing on the supplement'); (iii) the canonical taxonomy gains any of "
    "class_contracts/axis_registry/implication_ledger or the supplement gains any of "
    "class_ids/classes/transfer_rules (falsifies 'two different artifacts'); (iv) FROZEN.json's "
    "declared hashes for canonical/supplement/F2b cease to equal measured bytes; (v) any planted "
    "control stops being caught or the no-false-positive baseline fails."
)
NEXT_FALSIFIER = (
    "Re-run against a newer FROZEN revision or after any republication: a flip of C2/C3/C4/C5 or a "
    "C1 hash move voids the dependency proof for the newer revision and re-opens the REC-1/REC-2 "
    "adjudication."
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> None:
    report = json.loads((HERE / "f0adj_report.json").read_text())
    created = report["created_at"]
    ts = datetime.fromisoformat(created).strftime("%Y%m%dT%H%M%S")
    base = f"w089-{ts}"

    pins = report["target_pins"]
    art = {
        "checker": HERE / "check_f2b_f0adj.py",
        "report": HERE / "f0adj_report.json",
        "readme": HERE / "README.md",
        "console": HERE / "run_console.log",
        "pin_canonical": HERE / "pinned/formulation_taxonomy.canonical.276009f4f63d.yaml",
        "pin_supplement": HERE / "pinned/formulation_taxonomy.supplement.c8e979a1eb48.yaml",
        "pin_frozen": HERE / "pinned/FROZEN.2554e276a0db.json",
        "pin_conflict": HERE / "pinned/f0_mirror_conflict.json",
    }
    h = {k: sha(p) for k, p in art.items()}

    findings = [
        f"11/11 mechanical checks pass at pins F2b {pins['schemas/af_scc_c0_vacuum.yaml'][:12]}, "
        f"canonical {pins['research_map/formulation_taxonomy.yaml'][:12]}, "
        f"supplement {pins['artifacts/formulation/formulation_taxonomy.yaml'][:12]}.",
        "Key partition confirmed: canonical carries class_ids/classes/transfer_rules; supplement "
        "carries class_contracts/axis_registry/implication_ledger; neither carries the other's roles.",
        "F2b class_contract_pointer resolves to a full class contract in the supplement and does NOT "
        "resolve in the canonical taxonomy; the two sibling schemas behave identically.",
        "Structural destructive simulation: supplement-as-canonical loses class_ids/classes/"
        "transfer_rules; canonical-as-supplement loses class_contracts/axis_registry/"
        "implication_ledger and dangles the F2b pointer.",
        "Controls: M1-M8 planted defects all caught; N0 no-false-positive baseline clean "
        f"({report['controls_caught']}/{report['controls_total']}).",
        "Soft note (not a failure): f0_mirror_conflict.json cites FROZEN rev25, measured rev26; both "
        "hash pins unchanged, evidence not re-based.",
        "Scope: mechanical dependency verification only; NOT a semantic review, NOT a REC-1/REC-2 "
        "adjudication, NOT a G-F0/G-FORM gate accept. worker-089 authored no canonical artifact.",
    ]

    events = [
        {
            "actor": "worker-089",
            "class_id": CLASS,
            "created_at": created,
            "event_id": f"{base}-claim",
            "event_type": "status",
            "evidence_refs": [
                f"artifacts/formulation/evidence/f0_mirror_conflict.json#{h['pin_conflict'][:12]}",
                f"artifacts/formulation/FROZEN.json#{sha(ROOT / 'artifacts/formulation/FROZEN.json')[:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{pins['schemas/af_scc_c0_vacuum.yaml'][:12]}",
            ],
            "gate": GATE,
            "hours": 0.3,
            "next_falsifier": NEXT_FALSIFIER,
            "node_id": NODE,
            "status": "active",
            "summary": (
                "No assignment card existed for worker-089; took one bounded class-bound task: "
                "independent controlled verification of the withheld-F0 dependency claims in "
                "artifacts/formulation/evidence/f0_mirror_conflict.json as they bind AF-SCC-C0-VAC-GEN "
                f"(F2b) at pinned hash {pins['schemas/af_scc_c0_vacuum.yaml'][:12]}. 11 mechanical "
                "checks, 8 planted-defect controls, 1 no-false-positive control, 60 s hash-stability "
                "window. Does not adjudicate REC-1/REC-2 and does not claim a gate verdict."
            ),
            "task_id": TASK,
        },
        {
            "actor": "worker-089",
            "artifact_type": "checker_code",
            "class_id": CLASS,
            "created_at": created,
            "event_id": f"{base}-art-checker_code",
            "event_type": "artifact",
            "evidence_refs": [
                f"{rel(art['checker'])}#{h['checker'][:12]}",
                f"artifacts/formulation/evidence/f0_mirror_conflict.json#{h['pin_conflict'][:12]}",
            ],
            "gate": GATE,
            "next_falsifier": NEXT_FALSIFIER,
            "node_id": NODE,
            "note": (
                "Deterministic read-only stdlib+PyYAML checker; 11 checks + 8 in-memory planted-defect "
                "controls + no-false-positive baseline; writes only under this artifact directory."
            ),
            "path": rel(art["checker"]),
            "sha256": h["checker"],
            "task_id": TASK,
            "validation_status": "unverified",
        },
        {
            "actor": "worker-089",
            "artifact_type": "audit_report",
            "class_id": CLASS,
            "created_at": created,
            "event_id": f"{base}-art-audit_report",
            "event_type": "artifact",
            "evidence_refs": [
                f"{rel(art['report'])}#{h['report'][:12]}",
                f"schemas/af_scc_c0_vacuum.yaml#{pins['schemas/af_scc_c0_vacuum.yaml'][:12]}",
            ],
            "gate": GATE,
            "next_falsifier": NEXT_FALSIFIER,
            "node_id": NODE,
            "note": (
                f"Result at pins: verdict=accept, checks=11/11, controls=9/9, notes=2 (rev25->rev26 "
                "manifest drift; consistency checker static-only)."
            ),
            "path": rel(art["report"]),
            "sha256": h["report"],
            "task_id": TASK,
            "validation_status": "unverified",
        },
        {
            "actor": "worker-089",
            "artifact_type": "summary",
            "class_id": CLASS,
            "created_at": created,
            "event_id": f"{base}-art-readme",
            "event_type": "artifact",
            "evidence_refs": [f"{rel(art['readme'])}#{h['readme'][:12]}"],
            "gate": GATE,
            "next_falsifier": NEXT_FALSIFIER,
            "node_id": NODE,
            "note": "One-page summary: why, checks, controls, pins, limits, falsifier, re-run command.",
            "path": rel(art["readme"]),
            "sha256": h["readme"],
            "task_id": TASK,
            "validation_status": "unverified",
        },
        {
            "actor": "worker-089",
            "artifact_type": "pinned_snapshot",
            "class_id": CLASS,
            "created_at": created,
            "event_id": f"{base}-art-pinned-snapshot",
            "event_type": "artifact",
            "evidence_refs": [
                f"{rel(art['pin_canonical'])}#{h['pin_canonical'][:12]}",
                f"{rel(art['pin_supplement'])}#{h['pin_supplement'][:12]}",
                f"{rel(art['pin_frozen'])}#{h['pin_frozen'][:12]}",
                f"{rel(art['pin_conflict'])}#{h['pin_conflict'][:12]}",
            ],
            "gate": GATE,
            "next_falsifier": "A pinned snapshot hash differs from its source hash: the report is mis-bound.",
            "node_id": NODE,
            "note": (
                "Byte-exact snapshots of the audited revisions: canonical taxonomy, supplement, "
                "FROZEN rev26, and the f0_mirror_conflict evidence."
            ),
            "path": rel(art["pin_canonical"]),
            "sha256": h["pin_canonical"],
            "task_id": TASK,
            "validation_status": "unverified",
        },
        {
            "actor": "worker-089",
            "artifact": "artifacts/formulation/evidence/f0_mirror_conflict.json",
            "artifact_sha256": h["pin_conflict"],
            "class_id": CLASS,
            "counts_as_gate_accept": False,
            "created_at": created,
            "event_id": f"{base}-review",
            "event_type": "review",
            "evidence_refs": [
                f"{rel(art['report'])}#{h['report'][:12]}",
                f"artifacts/formulation/evidence/f0_mirror_conflict.json#{h['pin_conflict'][:12]}",
                f"artifacts/formulation/FROZEN.json#{sha(ROOT / 'artifacts/formulation/FROZEN.json')[:12]}",
            ],
            "findings": findings,
            "gate": GATE,
            "hard_failures": [],
            "independence": (
                "worker-089 authored no canonical artifact, no part of f0_mirror_conflict.json, and no "
                "schema; the previous W089-F2B-XREF-01 audit did not examine this evidence. Controls "
                "are included so a pass is controlled rather than asserted."
            ),
            "next_falsifier": NEXT_FALSIFIER,
            "node_id": NODE,
            "review_kind": "mechanical_dependency_verification",
            "reviewer": "worker-089",
            "scope": "mechanical dependency verification only; no semantic or adjudicative authority",
            "score": 4.0,
            "target_id": f"artifacts/formulation/evidence/f0_mirror_conflict.json#{h['pin_conflict'][:12]}",
            "task_id": TASK,
            "verdict": "accept",
        },
        {
            "actor": "worker-089",
            "class_id": CLASS,
            "created_at": created,
            "event_id": f"{base}-done",
            "event_type": "status",
            "evidence_refs": [f"{rel(art['report'])}#{h['report'][:12]}"],
            "gate": GATE,
            "hours": 0.3,
            "next_falsifier": NEXT_FALSIFIER,
            "node_id": NODE,
            "status": "done",
            "summary": (
                "Worker lifecycle complete (completion claim only; not a node done and not a gate "
                "verdict). One class-bound task delivered: the withheld-F0 dependency claims hold "
                "mechanically as they bind F2b at 1bb78ce9b357."
            ),
            "task_id": TASK,
        },
    ]

    # validate every event against the repo schema before writing anything
    for e in events:
        schemas.validate_event(e)
    print(f"schema validation: {len(events)}/{len(events)} events valid")

    # idempotent append to the outbox
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    (HERE / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))

    # checkpoint
    artifacts_map = {rel(p): h[k] for k, p in art.items()}
    for extra in sorted(HERE.glob("controls/*.json")) + sorted(HERE.glob("pinned/*")):
        artifacts_map[rel(extra)] = sha(extra)
    artifacts_map[rel(HERE / "events.jsonl")] = sha(HERE / "events.jsonl")
    artifacts_map[rel(OUTBOX)] = sha(OUTBOX)
    checkpoint = {
        "worker": "worker-089",
        "checkpoint": 2,
        "at": now(),
        "task_id": TASK,
        "class_id": CLASS,
        "node_id": NODE,
        "gate": GATE,
        "related_gate": "G-F0",
        "verdict": report["verdict"],
        "verdict_scope": report["verdict_scope"],
        "gate_verdict_claimed": False,
        "checks": {k: v["status"] for k, v in report["checks"].items()},
        "controls": {k: v["status"] for k, v in report["controls"].items()},
        "target": {
            "path": "artifacts/formulation/evidence/f0_mirror_conflict.json",
            "audited_sha256": h["pin_conflict"],
            "recheck_sha256": sha(ROOT / "artifacts/formulation/evidence/f0_mirror_conflict.json"),
            "drift_since_audit": sha(ROOT / "artifacts/formulation/evidence/f0_mirror_conflict.json") != h["pin_conflict"],
        },
        "pins": pins,
        "stability": report["stability"],
        "notes": report["notes"],
        "falsifier": FALSIFIER,
        "next_falsifier": NEXT_FALSIFIER,
        "events_emitted": [e["event_id"] for e in events],
        "events_new": [e["event_id"] for e in new],
        "artifacts": artifacts_map,
    }
    (STATE / "w089_checkpoint_2.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
    with (STATE / "w089_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps({k: checkpoint[k] for k in
                             ("worker", "checkpoint", "at", "task_id", "class_id", "node_id",
                              "gate", "verdict", "checks", "controls", "notes")}, sort_keys=True) + "\n")

    print(f"emitted {len(new)} new events (of {len(events)}); outbox={rel(OUTBOX)}")
    print(f"checkpoint: {rel(STATE / 'w089_checkpoint_2.json')}")


if __name__ == "__main__":
    main()
