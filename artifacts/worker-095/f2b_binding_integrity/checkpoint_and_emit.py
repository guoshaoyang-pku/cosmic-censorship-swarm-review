#!/usr/bin/env python3
"""W095-F2B-BIND-INTEGRITY-01 - checkpoint + valid JSON outbox events.

Reads verdict.json, writes the worker checkpoint pair under runtime/state/, and appends
schema-validated events to comms/outbox/worker-095.jsonl. It never mutates the map, the
canonical artifacts, or the accepted event stream (ingest is the controller's job).

Run: python3 artifacts/worker-095/f2b_binding_integrity/checkpoint_and_emit.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK_ID = "W095-F2B-BIND-INTEGRITY-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE_ID = "G-FORM"
OUTBOX = ROOT / "comms" / "outbox" / "worker-095.jsonl"
STATE = ROOT / "runtime" / "state"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    verdict_path = HERE / "verdict.json"
    script_path = HERE / "measure_binding.py"
    verdict = json.loads(verdict_path.read_text())
    vsha = sha256(verdict_path)
    msha = sha256(script_path)
    rev = verdict["reviewed_sha256"]
    failures = [f for f in verdict["findings"] if f["severity"] in {"blocking", "major"}]
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    prefix = f"w095-f2b-{stamp}"
    created = now()
    evidence_refs = [
        f"artifacts/worker-095/f2b_binding_integrity/verdict.json#{vsha[:12]}",
        f"artifacts/worker-095/f2b_binding_integrity/measure_binding.py#{msha[:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{rev[:12]}",
        "research_map/formulation_taxonomy.yaml#276009f4f63d",
        "artifacts/formulation/formulation_taxonomy.yaml#c8e979a1eb48",
        "artifacts/formulation/FROZEN.json#2554e276a0db",
        "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
    ]
    next_falsifier = ("a pass where F2b.class_contract_pointer resolves on the authoritative "
                      "canonical F0, canonical F0 stores the canonical conclusion/genericity "
                      "tokens, one value per YAML key, and FROZEN names exactly one authoritative "
                      "F0 artifact per logical role with all pins matching measured bytes")

    events = [
        {
            "event_id": f"{prefix}-task-claim",
            "event_type": "status",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE_ID,
            "status": "active",
            "hours": 0.4,
            "summary": (f"No assignment card exists in comms/inbox for worker-095 (fleet "
                        f"2026-09-12T00:25:04). Taking ONE bounded class-bound task, {TASK_ID}: "
                        f"binding/publication integrity of F2b {CLASS_ID} at measured canonical "
                        f"sha256 {rev[:12]}, with the published alias policy applied (this is the "
                        "sibling receipt to the prior F2a receipt and does not duplicate worker-096's "
                        "F2b semantic review). Deliverable: artifacts/worker-095/f2b_binding_integrity/."),
            "evidence_refs": evidence_refs,
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": f"{prefix}-artifact-verdict",
            "event_type": "artifact",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "artifact_type": "class_binding_integrity_verdict",
            "path": "artifacts/worker-095/f2b_binding_integrity/verdict.json",
            "sha256": vsha,
            "validation_status": "unverified",
            "companion_script": {"path": "artifacts/worker-095/f2b_binding_integrity/measure_binding.py",
                                 "sha256": msha},
            "reviewed_sha256": rev,
        },
        {
            "event_id": f"{prefix}-review-binding",
            "event_type": "review",
            "created_at": created,
            "actor": "worker-095",
            "reviewer": "worker-095",
            "target_id": NODE_ID,
            "target_path": "schemas/af_scc_c0_vacuum.yaml",
            "reviewed_sha256": rev,
            "class_id": CLASS_ID,
            "verdict": verdict["verdict"],
            "score": verdict["score_0_5"],
            "counts_as_full_schema_verdict": False,
            "hard_failures": [f["id"] for f in failures],
            "findings": [{"id": f["id"], "severity": f["severity"], "finding": f["finding"][:400],
                          "falsifier": f["falsifier"][:300]} for f in verdict["findings"]],
            "summary": (f"Binding/publication receipt on one class at one hash: "
                        f"{verdict['summary']['passed']}/{verdict['summary']['checks']} checks pass; "
                        f"{verdict['summary']['major']} major, {verdict['summary']['minor']} minor "
                        "findings. Pinned FORM-GATE-01 passes F2b at this hash, class-separation is "
                        "clean, canonical/authoring schema bytes are identical, and every FROZEN rev26 "
                        "pin matches; the revise verdict rests on the F0 contract-pointer/publication "
                        "defect (systemic, already under controller adjudication) plus provenance "
                        "hygiene. Not a content accept."),
            "evidence_refs": evidence_refs,
        },
        {
            "event_id": f"{prefix}-blocker-binding",
            "event_type": "blocker",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE_ID,
            "description": (f"G-FORM class-binding blocker re-measured for F2b {CLASS_ID} at "
                            f"{rev[:12]} / declared canonical F0 276009f4: (1) class_contract_pointer "
                            "targets artifacts/formulation/formulation_taxonomy.yaml#class_contracts."
                            f"{CLASS_ID}, which resolves only in the authoring supplement; the "
                            "declared canonical F0 has no class_contracts key. The defect is systemic "
                            "(all three frozen schemas). (2) The prior F2a blocker's second half is "
                            "REFINED, not repeated: canonical F0's conclusion/genericity tokens are "
                            "accepted aliases under VOCAB_ALIASES.json, the alias-normalized taxonomy "
                            "consistency run is consistent=true with 0 errors, and the pinned gate "
                            "passes, so the token difference is vocabulary hygiene, not a class-contract "
                            "contradiction. FROZEN rev26 already names declared-taxonomy and "
                            "class-contract-supplement as separate logical artifacts and carries a "
                            "blocked-pending-controller-adjudication request."),
            "needed_to_unblock": ("One controller decision on the F0 artifact of record (REC-1 "
                                  "pairs-check exception, or REC-2 bounded re-freeze with schema "
                                  "pointer refresh + re-review), then a published revision in which "
                                  "class_contract_pointer resolves on the authoritative artifact. "
                                  "Separately: one-value-per-key revision for the schemas, and "
                                  "canonical tokens in a future canonical F0 revision."),
            "evidence_refs": evidence_refs + ["artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf"],
        },
        {
            "event_id": f"{prefix}-task-receipt-complete",
            "event_type": "status",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE_ID,
            "status": "active",
            "hours": 0.5,
            "summary": (f"{TASK_ID} worker-level receipt complete; node status deliberately "
                        "unchanged (worker events cannot set status=done, validation_status=passed, "
                        "or a gate verdict). verdict=" + verdict["verdict"] + " at " + rev[:12] +
                        "; reproducible probe + 11 raw evidence files + checkpoint written. "
                        "counts_as_full_schema_verdict=false."),
            "evidence_refs": evidence_refs,
            "next_falsifier": next_falsifier,
        },
    ]

    # validate before writing: invalid JSON never reaches the outbox
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line)["event_id"])
                except (ValueError, KeyError):
                    pass
    new_events = [e for e in events if e["event_id"] not in existing]
    for e in new_events:
        validate_event(e)
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a") as f:
        for e in new_events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # checkpoint pair
    STATE.mkdir(parents=True, exist_ok=True)
    ckpt = {
        "worker": "worker-095",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE_ID,
        "verdict": verdict["verdict"],
        "score_0_5": verdict["score_0_5"],
        "reviewed_sha256": rev,
        "artifact": "artifacts/worker-095/f2b_binding_integrity/verdict.json",
        "artifact_sha256": vsha,
        "probe": {"path": "artifacts/worker-095/f2b_binding_integrity/measure_binding.py",
                  "sha256": msha},
        "evidence_dir": "artifacts/worker-095/f2b_binding_integrity/evidence/raw/",
        "counts_as_full_schema_verdict": False,
        "checkpoint_at": created,
        "next_falsifier": next_falsifier,
    }
    ckpt_path = STATE / f"w095_f2b_checkpoint_{stamp}.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    (STATE / "w095_latest_checkpoint.json").write_text(json.dumps({
        "worker": "worker-095", "task_id": TASK_ID, "path": str(ckpt_path.relative_to(ROOT)),
        "verdict": verdict["verdict"], "reviewed_sha256": rev, "checkpoint_at": created,
        "next_falsifier": next_falsifier,
    }, indent=2, sort_keys=True) + "\n")
    with (STATE / "w095_f2b_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(json.dumps({
        "events_appended": [e["event_id"] for e in new_events],
        "events_skipped_duplicate": [e["event_id"] for e in events if e["event_id"] in existing],
        "checkpoint": str(ckpt_path.relative_to(ROOT)),
        "verdict_sha256": vsha,
        "probe_sha256": msha,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
