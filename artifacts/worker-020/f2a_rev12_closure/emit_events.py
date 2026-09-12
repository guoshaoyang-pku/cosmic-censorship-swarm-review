#!/usr/bin/env python3
"""Emit the W020-F2A-REV12-CLOSURE-01 receipt.

Writes:
  * manifest.json                     (sha256 of every deliverable)
  * comms/outbox/worker-020.jsonl     (append-only structured events)
  * runtime/state/w020_rev12_closure_checkpoint.json
  * runtime/state/w020_checkpoints.jsonl (append-only checkpoint log)

Never touches canonical artifacts, gates, or node status.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TZ = timezone(timedelta(hours=8))
ACTOR = "worker-020"
TASK = "W020-F2A-REV12-CLOSURE-01"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
GATE = "G-FORM"
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-020.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, short: int = 12) -> str:
    """PROTOCOL evidence reference: path#sha256-prefix."""
    return f"{path}#{sha256_file(os.path.join(ROOT, path))[:short]}"


def main() -> int:
    verdict_path = os.path.join(HERE, "closure_verdict.json")
    report_path = os.path.join(HERE, "closure_report.md")
    script_path = os.path.join(HERE, "verify_c15_closure.py")
    verdict = json.load(open(verdict_path))
    assert verdict["closing_verdict"] == "C15_CLOSED_NO_NEW_OWNED_HARD_FINDING"

    # Fail closed: never emit a receipt against moved bytes.
    for p, pin in verdict["pins"].items():
        live = sha256_file(os.path.join(ROOT, p))
        if live != pin:
            raise SystemExit(
                f"ABORT: {p} moved since the closure run: live {live} != pin {pin}")

    deliverable_paths = [
        "artifacts/worker-020/f2a_rev12_closure/verify_c15_closure.py",
        "artifacts/worker-020/f2a_rev12_closure/closure_verdict.json",
        "artifacts/worker-020/f2a_rev12_closure/closure_report.md",
        "artifacts/worker-020/f2a_rev12_closure/snapshots/f2a_5476a3f2c6bc.yaml",
        "artifacts/worker-020/f2a_rev12_closure/snapshots/f0_canonical_0abb9ed8a961.yaml",
        "artifacts/worker-020/f2a_rev12_closure/snapshots/f0_supplement_d7419b4e8963.yaml",
        "artifacts/worker-020/f2a_rev12_closure/snapshots/vocab_aliases_46cd9f1eb534.json",
    ]

    manifest = {
        "task_id": TASK,
        "actor": ACTOR,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "generated_at": now(),
        "pins": verdict["pins"],
        "closing_verdict": verdict["closing_verdict"],
        "files": {
            p: {
                "sha256": sha256_file(os.path.join(ROOT, p)),
                "bytes": os.path.getsize(os.path.join(ROOT, p)),
            }
            for p in deliverable_paths
        },
    }
    manifest_path = os.path.join(HERE, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    manifest_rel = "artifacts/worker-020/f2a_rev12_closure/manifest.json"

    pin_refs = [ref(p) for p in [
        "schemas/af_scc_c2_vacuum.yaml",
        "research_map/formulation_taxonomy.yaml",
        "artifacts/formulation/formulation_taxonomy.yaml",
        "artifacts/formulation/VOCAB_ALIASES.json",
    ]]
    ev_refs = [
        ref("artifacts/worker-020/f2a_rev12_closure/closure_verdict.json"),
        ref("artifacts/worker-020/f2a_rev12_closure/closure_report.md"),
        ref(manifest_rel),
    ] + pin_refs

    events = []

    # 1) task claim
    events.append({
        "event_id": f"w020c-{STAMP}-status-task",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "status": "active",
        "hours": 0.0,
        "summary": (
            "No assignment card exists in comms/inbox for worker-020 (fleet instance "
            "2026-09-12T00:42:17). Took ONE bounded class-bound task, "
            "W020-F2A-REV12-CLOSURE-01: execute the falsifier recorded by this slot's "
            "prior lifecycle -- re-review the F2a class-binding pointer at its own "
            "measured hash -- and emit a machine-checked closure receipt for prior "
            "finding C15 / blocker w020-20260912T0024-f2a-blocker, which is still "
            "listed as open on node F2a although F2a was revised at 2026-09-12T00:31:41."),
        "evidence_refs": [ref(manifest_rel)],
        "next_falsifier": (
            "a re-measurement of schemas/af_scc_c2_vacuum.yaml differing from "
            "5476a3f2c6bc, or a canonical F0 revision in which "
            "classes.AF-SCC-C2-VAC-GEN no longer resolves the pointer, voids this "
            "closure receipt"),
    })

    # 2) artifacts
    for p in deliverable_paths + [manifest_rel]:
        events.append({
            "event_id": f"w020c-{STAMP}-artifact-{os.path.basename(p)}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": ACTOR,
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "artifact_type": (
                "verification_script" if p.endswith(".py") else
                "frozen_snapshot" if "/snapshots/" in p else
                "review_evidence" if p.endswith(".json") or p.endswith(".md") else
                "review_evidence"),
            "path": p,
            "sha256": sha256_file(os.path.join(ROOT, p)),
            "bytes": os.path.getsize(os.path.join(ROOT, p)),
            "validation_status": "unverified",
            "evidence_refs": [ref(p)],
            "note": "closure receipt deliverable; worker-level evidence only",
        })

    # 3) claim (with falsifier, per the task instruction)
    events.append({
        "event_id": f"w020c-{STAMP}-claim-c15-closure",
        "event_type": "claim",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-checker measurement at FROZEN rev28 pins (F2a "
            "schemas/af_scc_c2_vacuum.yaml 5476a3f2c6bc7196, canonical F0 "
            "research_map/formulation_taxonomy.yaml 0abb9ed8a96135c9, companion "
            "supplement d7419b4e8963cb71, VOCAB_ALIASES 46cd9f1eb534): the prior "
            "worker-020 hard finding C15 is CLOSED. At rev11 b6123750b37d the "
            "class_contract_pointer was artifacts/formulation/formulation_taxonomy.yaml"
            "#class_contracts.AF-SCC-C2-VAC-GEN and did not resolve in the then-declared "
            "canonical F0 276009f4f63d; at rev12 the pointer is "
            "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN and "
            "resolves, the supplement pointer resolves separately in the companion, and "
            "declared_f0_sha256 equals the measured canonical F0 hash. The canonical "
            "classes.<id> entry and the supplement class_contracts.<id> entry denote the "
            "same C2 contract on the fixed comparison set (alias-normalized "
            "conclusion_type scc_c2_future_inextendibility, class-identity axes, "
            "components, comeager quantifier, mutual C0 exclusion). No new owned hard "
            "finding was produced by this instrument. One inherited cross-cutting hard "
            "item is re-measured and NOT re-filed: "
            "f0_binding.consistency_evidence_sha256 declares 675a99d0d25b while the file "
            "at the declared path measures 9e335e9ba1bf (already tracked as HF-086-R1 et "
            "al.). This is a worker completion claim; it sets no gate verdict, no node "
            "status and no validation_status."),
        "assumptions": [
            "Frozen bytes only: the receipt binds to the measured sha256 values; any later revision voids it.",
            "Verdicts bind to the canonical artifact path, per publication policy; the supplement is a companion, not a mirror.",
            "No canonical tool was imported: resolution, strict-YAML duplicate-key detection and the alias normalization were re-implemented and controlled.",
            "Alias equivalence for conclusion_type uses the frozen VOCAB_ALIASES.json map; it does not assert the literal tokens are equal.",
            "The cross-cutting consistency-evidence mismatch is inherited, owned elsewhere, and not re-filed.",
        ],
        "falsifier": (
            "a re-measurement of schemas/af_scc_c2_vacuum.yaml showing a hash other than "
            "5476a3f2c6bc, or a canonical F0 revision whose classes key no longer resolves "
            "the pointer, or a re-run of verify_c15_closure.py at the same pins returning "
            "C10 FAIL, or a control that does not fire"),
        "artifact_refs": ev_refs,
        "evidence_refs": ev_refs,
        "supersedes_blocker": "w020-20260912T0024-f2a-blocker",
        "supersedes_finding": "C15",
        "prior_blocker_now_superseded_by_revision": True,
    })

    # 4) review (closure-first; not a full-schema accept)
    events.append({
        "event_id": f"w020c-{STAMP}-review-c15-closure",
        "event_type": "review",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "target_id": "schemas/af_scc_c2_vacuum.yaml",
        "reviewer": ACTOR,
        "verdict": "revise",
        "score": 4.0,
        "artifact": "schemas/af_scc_c2_vacuum.yaml",
        "reviewed_sha256": verdict["pins"]["schemas/af_scc_c2_vacuum.yaml"],
        "artifact_sha256": verdict["pins"]["schemas/af_scc_c2_vacuum.yaml"],
        "counts_as_gate_accept": False,
        "counts_as_full_schema_verdict": False,
        "hard_failures": [f["id"] for f in verdict["findings"]],
        "findings": [
            "C15 CLOSED at 5476a3f2c6bc: class_contract_pointer resolves in the declared "
            "canonical F0 0abb9ed8a961 at classes.AF-SCC-C2-VAC-GEN; supplement pointer "
            "separately resolvable; declared_f0_sha256 matches measured (C03, C05, C06, C10).",
            "Rev11->rev12 delta machine-checked: at b6123750 the same test returned "
            "resolved=False against the then-canonical 276009f4; the rev11 bytes also "
            "carried duplicate revised_at keys (x2..x8), absent at rev12 (C01, C10).",
            "Contract equivalence canonical vs supplement holds on the fixed comparison set; "
            "conclusion_type is equal only after the frozen alias map "
            "(strong_cosmic_censorship_C2 -> scc_c2_future_inextendibility) is applied (C09).",
            "HF-020-R12-1 (inherited, not owned here): f0_binding.consistency_evidence_sha256 "
            "declares 675a99d0d25b but the declared path measures 9e335e9ba1bf. Already tracked "
            "by worker-086/092/045/078/041/005; not re-filed. It keeps this verdict at revise.",
            "Controls K1-K5 all fired (duplicate-key detector, pointer retarget, missing "
            "supplement key, hash flip, alias discrimination); drift window C12 PASS.",
        ],
        "does_not_claim": ["gate verdict", "node completion", "full-schema accept",
                           "mathematical theorem"],
        "evidence_refs": ev_refs,
        "falsifier": (
            "a canonical F2a revision at a new hash, or a re-run showing C10 FAIL, or a "
            "controller determination that C15 was not in fact the prior worker-020 blocker"),
    })

    # 5) completion + checkpoint
    events.append({
        "event_id": f"w020c-{STAMP}-status-complete",
        "event_type": "status",
        "created_at": now(),
        "actor": ACTOR,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "status": "active",
        "hours": 0.6,
        "summary": (
            "W020-F2A-REV12-CLOSURE-01 complete at worker level (completion claim only: "
            "workers cannot set done/passed or a gate verdict). Verdict "
            "C15_CLOSED_NO_NEW_OWNED_HARD_FINDING at F2a 5476a3f2c6bc / canonical F0 "
            "0abb9ed8a961; 12/12 checks pass (one observation check expected-FAIL), 5/5 "
            "controls fire, drift window stable. The prior blocker "
            "w020-20260912T0024-f2a-blocker is superseded by the rev12 repair and should "
            "be closed on the DAG by the controller; this worker does not set node status. "
            "Evidence: artifacts/worker-020/f2a_rev12_closure/closure_verdict.json. "
            "Checkpoint: runtime/state/w020_rev12_closure_checkpoint.json."),
        "evidence_refs": ev_refs,
        "next_falsifier": (
            "a hash move on either pinned artifact, or the controller finding that the "
            "rev12 pointer repair regressed; then re-run verify_c15_closure.py"),
    })

    os.makedirs(os.path.dirname(OUTBOX), exist_ok=True)
    existing_ids = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                existing_ids.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    dupes = [e["event_id"] for e in events if e["event_id"] in existing_ids]
    if dupes:
        raise SystemExit(f"ABORT: event ids already emitted: {dupes}")
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    checkpoint = {
        "task_id": TASK,
        "actor": ACTOR,
        "slot": "020",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": now(),
        "verdict": verdict["closing_verdict"],
        "c15_closed": verdict["closure_delta"]["c15_closed"],
        "hard_check_failures": verdict["hard_check_failures"],
        "controls_ok": verdict["controls_ok"],
        "drift": verdict["drift"],
        "pins": verdict["pins"],
        "prior_blocker": verdict["prior_blocker"],
        "findings": verdict["findings"],
        "next_falsifier": (
            "hash move on schemas/af_scc_c2_vacuum.yaml or "
            "research_map/formulation_taxonomy.yaml; then re-run verify_c15_closure.py"),
        "files": manifest["files"],
        "events_file": "comms/outbox/worker-020.jsonl",
        "does_not_claim": ["gate verdict", "node completion", "validation_status=passed"],
    }
    os.makedirs(STATE, exist_ok=True)
    cp_path = os.path.join(STATE, "w020_rev12_closure_checkpoint.json")
    with open(cp_path, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(STATE, "w020_checkpoints.jsonl"), "a",
              encoding="utf-8") as fh:
        fh.write(json.dumps({**checkpoint, "checkpoint_path":
                             "runtime/state/w020_rev12_closure_checkpoint.json"},
                            ensure_ascii=False, sort_keys=True) + "\n")

    print(json.dumps({
        "events_written": len(events),
        "outbox": "comms/outbox/worker-020.jsonl",
        "manifest": manifest_rel,
        "checkpoint": "runtime/state/w020_rev12_closure_checkpoint.json",
        "closing_verdict": verdict["closing_verdict"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
