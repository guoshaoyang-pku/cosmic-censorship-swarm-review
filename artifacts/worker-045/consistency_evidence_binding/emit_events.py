#!/usr/bin/env python3
"""Emit the W045-CONSISTENCY-EVIDENCE-BINDING-01 checkpoint and upward events.

Idempotent: event_ids already present in comms/outbox/worker-045.jsonl are not
appended again. Every event is validated with research_map.schemas.validate_event
before it is written. The checkpoint is written under this task directory and
mirrored to runtime/state/.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-045.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

DELIVERABLES = {
    "report": "artifacts/worker-045/consistency_evidence_binding/report.json",
    "runner": "artifacts/worker-045/consistency_evidence_binding/run_consistency_evidence_binding.py",
    "readme": "artifacts/worker-045/consistency_evidence_binding/README.md",
    "emitter": "artifacts/worker-045/consistency_evidence_binding/emit_events.py",
}
CHECKPOINT = "artifacts/worker-045/consistency_evidence_binding/checkpoint.json"
MIRROR = "runtime/state/w045_consistency_evidence_binding_checkpoint.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M")
    hashes = {k: sha256_file(ROOT / v) for k, v in DELIVERABLES.items()}
    report = json.loads((ROOT / DELIVERABLES["report"]).read_text())

    checkpoint = {
        "task_id": report["task_id"],
        "worker": "worker-045",
        "created_at": now,
        "node_id": report["node_id"],
        "class_id": report["class_id"],
        "verdict": report["verdict"],
        "controls_pass": report["controls_pass"],
        "pins": report["pins"],
        "deliverables": {k: {"path": v, "sha256": hashes[k]} for k, v in DELIVERABLES.items()},
        "findings": [f["finding"] for f in report["findings"]],
        "hard_failures": [f["finding"] for f in report["findings"] if f["severity"] == "major"],
        "next_falsifier": report["falsifier"],
        "authority_note": report["authority_note"],
    }
    ckpt_path = ROOT / CHECKPOINT
    ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    mirror_path = ROOT / MIRROR
    mirror_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    report_ref = f"{DELIVERABLES['report']}#{hashes['report'][:12]}"
    runner_ref = f"{DELIVERABLES['runner']}#{hashes['runner'][:12]}"
    readme_ref = f"{DELIVERABLES['readme']}#{hashes['readme'][:12]}"
    ckpt_ref = f"{CHECKPOINT}#{sha256_file(ckpt_path)[:12]}"
    evidence_refs = [
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
        "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
        "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
        "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "artifacts/formulation/FROZEN.json#2f358f6722d9",
        "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json#675a99d0d25b",
    ]
    falsifier = report["falsifier"]
    summary = (
        "W045-CONSISTENCY-EVIDENCE-BINDING-01 complete at worker level (no node/gate transition "
        "claimed). VERDICT REVISE, 5 findings, 5/5 controls pass, zero canonical drift. F-1: all three "
        "class artifacts declare consistency_evidence_sha256 675a99d0d25b while the canonical path "
        "measures 9e335e9ba1bf. F-2: FROZEN rev28 (2f358f6722d9) pins the same path at 9e335e9b, so the "
        "frozen corpus carries two mutually exclusive pins for one path. F-3: the canonical evidence is "
        "input-hash-unbound (no map_taxonomy_sha256/lead_contract_sha256); the declared enriched variant "
        "carries both and they equal the live F0/supplement. F-5: a non-compared F0 edit leaves the "
        "evidence byte-identical (control C3), so the evidence hash does not bind F0 bytes. Class "
        "pointers, declared_f0_sha256 and FROZEN class pins all match live. Artifact "
        f"{report_ref}."
    )

    events = [
        {
            "event_id": f"w045-art-{stamp}-consistency-binding-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F0,F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "measurement_report",
            "path": DELIVERABLES["report"],
            "sha256": hashes["report"],
            "validation_status": "unverified",
            "evidence_refs": evidence_refs,
            "next_falsifier": falsifier,
            "summary": summary,
        },
        {
            "event_id": f"w045-art-{stamp}-consistency-binding-runner",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F0,F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "runner",
            "path": DELIVERABLES["runner"],
            "sha256": hashes["runner"],
            "validation_status": "unverified",
            "evidence_refs": [report_ref],
            "summary": "Deterministic read-only runner: per-class declaration table, FROZEN pin check, "
                       "input-binding detector, sandboxed checker controls C1-C5, canonical hash guard.",
        },
        {
            "event_id": f"w045-art-{stamp}-consistency-binding-readme",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F0,F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "artifact_type": "readme",
            "path": DELIVERABLES["readme"],
            "sha256": hashes["readme"],
            "validation_status": "unverified",
            "evidence_refs": [report_ref, runner_ref],
            "summary": "Method, pins, result table, controls including the C3 misprediction, three "
                       "repair options, falsifier, limitations and authority note.",
        },
        {
            "event_id": f"w045-claim-{stamp}-consistency-binding",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F0,F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "statement": (
                "At the drift-guarded instant with canonical hashes F0 0abb9ed8a961, supplement "
                "d7419b4e8963, F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda, evidence "
                "9e335e9ba1bf, FROZEN rev28 2f358f6722d9: (1) all three class artifacts' "
                "f0_binding.consistency_evidence_sha256 declares 675a99d0d25b, which is not the "
                "canonical evidence bytes, while FROZEN rev28 pins the same path at 9e335e9b; (2) the "
                "canonical evidence records input paths but no map_taxonomy_sha256/lead_contract_sha256, "
                "whereas the declared enriched variant archived at "
                "artifacts/worker-086/evidence_collision/restore_candidate/"
                "taxonomy_consistency.675a99d0d25b.json carries both and they equal the live F0 and "
                "supplement; (3) a re-serialised F0 with an added non-compared field leaves the evidence "
                "byte-identical (control C3), so the evidence hash does not bind F0 bytes at all, and the "
                "load-bearing input binding is each schema's declared_f0_sha256, which does equal live "
                "F0; (4) the declared checker is deterministic and semantically sensitive (two sandbox "
                "runs reproduce 9e335e9b exactly; an F2a family mutation flips consistent=false). "
                "Consequence: one frozen revision carries two mutually exclusive pins for one path, and "
                "re-pinning to 9e335e9b versus restoring the enriched evidence are mutually exclusive "
                "without a further FROZEN move. This is a provenance/binding measurement, not class "
                "leakage and not a semantics defect; class_contract_pointer, supplement pointer, "
                "declared_f0_sha256 and FROZEN rev28 class pins all match the live bytes."
            ),
            "conclusion_type": "formal_model",
            "assumptions": [
                "the declared checker bytes de356d999ea3b6ae are the authoritative generator of the evidence file",
                "pins are bound to the measured instant; concurrent writers can move any path",
                "formal_model is used because this is an artifact/provenance measurement, not a mathematical theorem",
                "checker executions are sandboxed because the declared checker rewrites its output in place at the tree it runs from",
            ],
            "falsifier": falsifier,
            "evidence_refs": evidence_refs,
            "artifact_refs": [report_ref, runner_ref, readme_ref, ckpt_ref],
        },
        {
            "event_id": f"w045-review-{stamp}-consistency-binding",
            "event_type": "review",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "target_id": "F1,F2a,F2b:f0_binding.consistency_evidence_sha256@675a99d0d25b",
            "reviewer": "worker-045",
            "verdict": "revise",
            "score": 3.0,
            "hard_failures": [
                "F-1: uniform stale consistency-evidence declaration (675a99d0 vs live 9e335e9b) in F1/F2a/F2b",
                "F-2: FROZEN rev28 pins the same evidence path at 9e335e9b while the schemas it freezes declare 675a99d0",
                "F-3: canonical evidence is input-hash-unbound and cannot show which F0 bytes it evaluated",
            ],
            "findings": [f["finding"] for f in report["findings"]],
            "evidence_refs": evidence_refs,
            "scope_note": "Binding-only review of the evidence chain; semantics, pointers and class separation were not re-adjudicated here.",
        },
        {
            "event_id": f"w045-status-{stamp}-consistency-binding",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F0,F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "status": "active",
            "hours": 0.4,
            "summary": summary,
            "evidence_refs": [report_ref, runner_ref, readme_ref, ckpt_ref],
            "next_falsifier": falsifier,
        },
        {
            "event_id": f"w045-blocker-{stamp}-consistency-binding",
            "event_type": "blocker",
            "created_at": now,
            "actor": "worker-045",
            "node_id": "F1,F2a,F2b",
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "description": (
                "Binding decision needed on the consistency-evidence chain (artifact-level, no measured "
                "number changes): the three class artifacts declare 675a99d0d25b, the canonical path and "
                "FROZEN rev28 hold 9e335e9b, and the canonical bytes are input-hash-unbound (F-1..F-3). "
                "Two repairs are mutually exclusive without a further freeze: (1) re-pin the three "
                "schemas to 9e335e9b and accept path-only evidence; (2) make the checker emit "
                "map_taxonomy_sha256/lead_contract_sha256/measured_at again, restore the enriched "
                "evidence, and pin 675a99d0 across schemas and FROZEN."
            ),
            "needed_to_unblock": "Formulation lead decision on repair (1) vs (2), then one atomic re-freeze plus a gate-scan re-run; no worker may edit another agent's canonical artifact.",
            "evidence_refs": [report_ref, ckpt_ref],
        },
    ]

    for ev in events:
        validate_event(ev)

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
    new = [ev for ev in events if ev["event_id"] not in existing]
    if new:
        with OUTBOX.open("a") as f:
            f.write("".join(json.dumps(ev, sort_keys=True) + "\n" for ev in new))
    print(json.dumps({
        "checkpoint": ckpt_ref,
        "mirror": MIRROR,
        "deliverable_hashes": hashes,
        "events_new": [ev["event_id"] for ev in new],
        "events_skipped_existing": [ev["event_id"] for ev in events if ev["event_id"] in existing],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
