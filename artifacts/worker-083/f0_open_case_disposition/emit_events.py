#!/usr/bin/env python3
"""Emit the W083-F0-OPENCASE-DISPOSITION-01 manifest, outbox events, and worker checkpoint.

Deterministic given the artifact bytes; every referenced sha256 is measured in this run.
Worker authority limits are encoded in every event: no gate verdict, no node status,
no class id creation.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TASK = "W083-F0-OPENCASE-DISPOSITION-01"
ACTOR = "worker-083"
NODE = "F0"
GATE = "G-F0"
CLASS_JOINED = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

FILES = {
    "disposition.py": HERE / "disposition.py",
    "dispositions.json": HERE / "dispositions.json",
    "REPORT.md": HERE / "REPORT.md",
    "emit_events.py": HERE / "emit_events.py",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    disp = json.loads(FILES["dispositions.json"].read_text())
    hashes = {name: sha256(path) for name, path in FILES.items()}

    manifest = {
        "task_id": TASK,
        "actor": ACTOR,
        "generated_at": now.isoformat(),
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "inputs": disp["inputs"],
        "frozen_schema_hashes": disp["frozen_schema_hashes"],
        "artifacts": hashes,
        "summary": disp["summary"],
        "controls": disp["controls"],
        "falsifier": disp["falsifier"],
        "does_not_claim": disp["does_not_claim"],
        "reproduce": disp["reproduce"],
    }
    manifest_path = HERE / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    manifest_sha = sha256(manifest_path)

    ref = lambda name: f"{FILES[name].relative_to(ROOT)}#{hashes[name][:12]}"  # noqa: E731
    evidence = [
        ref("dispositions.json"),
        ref("REPORT.md"),
        f"artifacts/worker-083/f0_open_case_disposition/MANIFEST.json#{manifest_sha[:12]}",
        f"schemas/taxonomy_cases.jsonl#{disp['inputs']['schemas/taxonomy_cases.jsonl']['sha256'][:12]}",
        f"research_map/formulation_taxonomy.yaml#{disp['inputs']['research_map/formulation_taxonomy.yaml']['sha256'][:12]}",
        f"artifacts/formulation/VARIANT_REGISTRY.json#{disp['inputs']['artifacts/formulation/VARIANT_REGISTRY.json']['sha256'][:12]}",
    ]
    next_falsifier = disp["falsifier"]

    events = [
        {
            "event_id": f"w083-{stamp}-task-claim",
            "event_type": "status",
            "created_at": now.isoformat(),
            "actor": ACTOR,
            "node_id": NODE,
            "gate": GATE,
            "class_id": CLASS_JOINED,
            "class_ids": CLASS_IDS,
            "status": "active",
            "hours": 0.6,
            "summary": (
                f"{TASK}: took one class-bound task from the map's G-F0 unmet item — independently "
                "disposition the 9 open taxonomy cases against the current canonical taxonomy and the "
                "rev-4 variant policy. Result: 7 NEW_CLASS_REQUIRED (CG2, deferred to Human PI), "
                "2 SPLIT_REQUIRED (N14 C0/C2, N15 WCC/SCC+bridge); controls 16/16 positives, 20/20 "
                "negatives, 4/4 planted branches. No gate verdict, no node status, no class id created."
            ),
            "evidence_refs": evidence,
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": f"w083-{stamp}-artifact-dispositions",
            "event_type": "artifact",
            "created_at": now.isoformat(),
            "actor": ACTOR,
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "open_case_disposition_matrix",
            "path": str(FILES["dispositions.json"].relative_to(ROOT)),
            "sha256": hashes["dispositions.json"],
            "validation_status": "unverified",
            "note": (
                "Per-case records: recovered axis vector, deviations from the filed class, admissible "
                "frozen bindings with cited rules, disposition, escalation, per-case falsifier. Bound "
                "to taxonomy 276009f4 (rev 4) and corpus b9699119 in one instant; the 9 per-case "
                "binding_status hashes are stale (66bf917bd368 = the artifact rev 4 supersedes)."
            ),
        },
        {
            "event_id": f"w083-{stamp}-artifact-report",
            "event_type": "artifact",
            "created_at": now.isoformat(),
            "actor": ACTOR,
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "disposition_report",
            "path": str(FILES["REPORT.md"].relative_to(ROOT)),
            "sha256": hashes["REPORT.md"],
            "validation_status": "unverified",
            "note": "Human-readable report: findings, disposition table, prior-art comparison with deepseek-flash-02, controls, falsifier, limits.",
        },
        {
            "event_id": f"w083-{stamp}-artifact-manifest",
            "event_type": "artifact",
            "created_at": now.isoformat(),
            "actor": ACTOR,
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "artifact_type": "artifact_manifest",
            "path": str(manifest_path.relative_to(ROOT)),
            "sha256": manifest_sha,
            "validation_status": "unverified",
            "note": "Measured hashes of inputs, outputs, and controls for this task; single-instant binding.",
        },
        {
            "event_id": f"w083-{stamp}-claim-001",
            "event_type": "claim",
            "created_at": now.isoformat(),
            "actor": ACTOR,
            "node_id": NODE,
            "gate": GATE,
            "class_id": CLASS_JOINED,
            "class_ids": CLASS_IDS,
            "conclusion_type": "stability_result",
            "claims_theorem_status": False,
            "does_not_claim": disp["does_not_claim"],
            "statement": (
                "Artifact-and-checker result (not a mathematics or physics claim): under the current "
                "canonical taxonomy research_map/formulation_taxonomy.yaml rev 4 sha256 276009f4 and "
                "class-scope policy astra-classscope-02 / VARIANT_REGISTRY v2.0, the 9 open=true cases "
                "in schemas/taxonomy_cases.jsonl (sha b9699119) disposition as 7 NEW_CLASS_REQUIRED "
                "(coverage gap CG2; new class ids deferred to Human PI) and 2 SPLIT_REQUIRED "
                "(TC-F0-N14 merged C0/C2 regularities; TC-F0-N15 merged WCC/SCC families requiring a "
                "bridge artifact under X4). No registered variant can absorb any of the 9: all 7 "
                "registered variants preserve their parent's descriptor axis vector and change only "
                "the conclusion/visibility/extension reading, while every open case deviates on at "
                "least one descriptor axis. The 9 per-case binding hashes (66bf917bd368) are stale: "
                "rev 4 declares that hash superseded, so the corpus must be re-bound before a lead "
                "disposition binds."
            ),
            "assumptions": [
                "The four frozen class descriptors in the current canonical taxonomy are the decisive axis vectors; genericity_kind/topology are class-owned placeholders and are not used to separate descriptors.",
                "A case's axis vector defaults to the descriptor of the class it is filed under; only deviations asserted by the record (violated_vocabulary, axis=value literals, prose corroboration) are treated as changes.",
                "A worker may propose dispositions but may not adjudicate them or create class ids (comms/PROTOCOL.md rule 5; astra-classscope-02; controller finding CF-5).",
                "Dispositions are independent of the corpus's authored expected_resolution field; agreement (35/36 exact, 1 repair-refined) is reported as a control, not used as input.",
            ],
            "falsifier": next_falsifier,
            "evidence_refs": evidence,
            "artifact_refs": [
                ref("dispositions.json"),
                ref("REPORT.md"),
                f"artifacts/worker-083/f0_open_case_disposition/MANIFEST.json#{manifest_sha[:12]}",
            ],
        },
    ]

    # The complete-event references the checkpoint hash, so the checkpoint is written first
    # (it lists the event ids, not the event bytes: no circular hash dependency).
    ckpt_path = ROOT / "runtime" / "state" / "w083_checkpoint_1.json"
    complete_id = f"w083-{stamp}-complete"
    checkpoint = {
        "checkpoint": 1,
        "checkpoint_id": f"w083-cp1-{stamp}",
        "worker": ACTOR,
        "at": now.isoformat(),
        "hours_spent_estimate": 0.9,
        "task_id": TASK,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "assignment": "self-selected from research_map.json#gates[0].unmet[3] (9 open taxonomy cases never dispositioned)",
        "status": {
            "summary": disp["summary"],
            "controls": {k: v for k, v in disp["controls"].items() if k != "planted_controls"},
            "open_dispositions": {d["case_id"]: d["disposition"] for d in disp["open_case_dispositions"]},
            "stale_binding": disp["stale_binding"],
            "no_completion_claim": "worker cannot set node status or gate verdict; no theorem, no physics result, no new class id",
        },
        "artifacts": {str(p.relative_to(ROOT)): h for p, h in
                      [(FILES[n], hashes[n]) for n in FILES] + [(manifest_path, manifest_sha)]},
        "events_emitted": [ev["event_id"] for ev in events] + [complete_id],
        "outbox": f"comms/outbox/{ACTOR}.jsonl",
        "reproduce": disp["reproduce"],
        "falsifier": next_falsifier,
    }
    ckpt_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n")

    complete_event = {
        "event_id": complete_id,
        "event_type": "status",
        "created_at": now.isoformat(),
        "actor": ACTOR,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.9,
        "summary": (
            f"{TASK} complete as a bounded worker task (this is a completion claim for the "
            "deliverable, not a node transition: workers cannot set done/passed and G-F0 stays "
            "pending). Checkpoint written to runtime/state/w083_checkpoint_1.json. Next consumer: "
            "the F0 lead can adopt the 7+2 disposition matrix for adjudication after re-binding "
            "the corpus to the current canonical taxonomy hash."
        ),
        "evidence_refs": evidence + [f"runtime/state/w083_checkpoint_1.json#{sha256(ckpt_path)[:12]}"],
        "next_falsifier": next_falsifier,
    }
    events.append(complete_event)

    for ev in events:
        validate_event(ev)

    # idempotent rewrite: drop any earlier emission of this task's events, keep foreign lines
    outbox = ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl"
    kept = []
    if outbox.exists():
        for line in outbox.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                eid = str(json.loads(line).get("event_id", ""))
            except Exception:
                kept.append(line)
                continue
            if not eid.startswith("w083-"):
                kept.append(line)
    with open(outbox, "w") as fh:
        for line in kept:
            fh.write(line + "\n")
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    log = HERE / "checkpoints.jsonl"
    log_lines = []
    if log.exists():
        log_lines = [l for l in log.read_text().splitlines()
                     if l.strip() and '"checkpoint_id": "w083-cp1-' not in l]
    log_lines.append(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "at": now.isoformat(),
                                 "task_id": TASK, "events": len(events),
                                 "artifacts": len(checkpoint["artifacts"])}, ensure_ascii=False))
    log.write_text("\n".join(log_lines) + "\n")

    print(json.dumps({
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": manifest_sha,
        "artifact_hashes": hashes,
        "events": [ev["event_id"] for ev in events],
        "outbox": str(outbox.relative_to(ROOT)),
        "checkpoint": str(ckpt_path.relative_to(ROOT)),
        "checkpoint_sha256": sha256(ckpt_path),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
