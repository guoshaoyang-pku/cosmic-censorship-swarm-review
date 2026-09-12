#!/usr/bin/env python3
"""Emit worker-050's upward events for W050-F2A-FROZEN-BIND-01 and self-validate them.

Writes comms/outbox/worker-050.jsonl (append, idempotent by event_id), validates every
event with research_map.schemas.validate_event (the same validator comms.py ingest uses),
and writes a local checkpoint record. Never touches canonical paths.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTDIR = Path(__file__).resolve().parent
AUDIT = OUTDIR / "audit_f2a_frozen_bind.json"
SCRIPT = OUTDIR / "verify_f2a_frozen_bind.py"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


d = json.loads(AUDIT.read_text())
stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
created = datetime.now(CST).isoformat(timespec="seconds")
reviewed = d["reviewed_sha256"]
audit_h = sha(AUDIT)
script_h = sha(SCRIPT)

findings = [
    {"id": f["id"], "severity": f["severity"], "finding": f["finding"]}
    for f in d["findings"]
]
conditions = [
    "F-BINDNOTE: regenerate f0_binding.binding_note with the actual refresh history (it currently "
    "describes the superseded rev4 refresh).",
    "F-CLOCK: re-stamp checked_at / revised_at / frozen_at with wall-clock time at write (CF-14).",
    "F-CONSEV: record the compared hashes inside taxonomy_consistency.json so the evidence is self-binding.",
    "F-REVNOTE/others: make the revision note describe the delta actually present in this file.",
    "F-SYM/F-VOCAB: name the omitted symmetry axis and the status-vs-evidence-level vocabulary explicitly.",
]

events = [
    {
        "event_id": f"w050-{stamp}-artifact-f2a-frozen-bind",
        "event_type": "artifact",
        "created_at": created,
        "actor": "worker-050",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_type": "frozen_binding_audit",
        "path": str(AUDIT.relative_to(ROOT)),
        "sha256": audit_h,
        "validation_status": "unverified",
        "gate": "G-FORM",
        "reviewed_sha256": reviewed,
        "checked_frozen_manifest_revision": d.get("frozen_manifest_revision"),
        "artifact_refs": [
            f"{AUDIT.relative_to(ROOT)}#sha256:{audit_h}",
            f"{SCRIPT.relative_to(ROOT)}#sha256:{script_h}",
        ],
        "evidence_refs": d["evidence_refs"],
        "falsifier": d["falsifiers"][0],
    },
    {
        "event_id": f"w050-{stamp}-review-f2a-frozen-bind",
        "event_type": "review",
        "created_at": created,
        "actor": "worker-050",
        "reviewer": "worker-050",
        "target_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "verdict": "accept",
        "score": 4,
        "hard_failures": [],
        "findings": findings,
        "conditions": conditions,
        "reviewed_sha256": reviewed,
        "review_scope": "declared cross-artifact bindings of the frozen F2a revision: FROZEN pin, "
        "f0_binding hash, class_contract_pointer resolution, canonical-vs-supplement contract "
        "consistency re-run, l1_ledger_refs against the pinned ledger, class separation and "
        "conclusion-token vocabulary. Not a re-derivation of the physics.",
        "artifact_refs": [
            f"{AUDIT.relative_to(ROOT)}#sha256:{audit_h}",
            f"{SCRIPT.relative_to(ROOT)}#sha256:{script_h}",
        ],
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#{reviewed[:12]}",
            "artifacts/formulation/FROZEN.json",
            "ledger/theorems.jsonl#ce42d205e761",
            "research_map/formulation_taxonomy.yaml#276009f4f63d",
            "artifacts/formulation/formulation_taxonomy.yaml#c8e979a1eb48",
        ],
        "falsifier": d["falsifiers"][1],
    },
    {
        "event_id": f"w050-{stamp}-status-f2a-frozen-bind",
        "event_type": "status",
        "created_at": created,
        "actor": "worker-050",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "active",
        "hours": 0.4,
        "summary": "No assignment card exists in comms/inbox for worker-050. Took one bounded "
        "class-bound task, W050-F2A-FROZEN-BIND-01: independent audit of the frozen F2a revision's "
        f"declared bindings at sha256 {reviewed[:16]} (FROZEN rev {d.get('frozen_manifest_revision')}). "
        "Result: 6/6 binding checks pass, 0 hard failures, accept score 4 with 5 minor documentation "
        "findings (stale binding note, future-dated stamps, unbinding consistency evidence, revision-note "
        "mismatch, explicit-vocabulary gaps). No gate verdict, no validation_status=passed, no node "
        "completion claimed.",
        "artifact": str(AUDIT.relative_to(ROOT)),
        "reviewed_sha256": reviewed,
        "artifact_refs": [f"{AUDIT.relative_to(ROOT)}#sha256:{audit_h}"],
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#{reviewed[:12]}",
            "artifacts/formulation/FROZEN.json",
            "ledger/theorems.jsonl#ce42d205e761",
        ],
        "next_falsifier": "Any drift of schemas/af_scc_c2_vacuum.yaml away from "
        f"{reviewed[:16]}, any l1_ledger_ref unresolved at the pinned ledger, or a FROZEN pin "
        "mismatch voids this review; re-bind to the new hash before citing it.",
    },
]

# ---- validate with the ingest validator, fail closed ----
errors = []
for e in events:
    try:
        validate_event(e)
    except SchemaError as exc:
        errors.append(f"{e['event_id']}: {exc}")
if errors:
    print("VALIDATION FAILED")
    for x in errors:
        print("  " + x)
    sys.exit(1)

out = ROOT / "comms" / "outbox" / "worker-050.jsonl"
seen = set()
if out.exists():
    for line in out.read_text().splitlines():
        if line.strip():
            seen.add(json.loads(line).get("event_id"))
new = [e for e in events if e["event_id"] not in seen]
with out.open("a") as fh:
    for e in new:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

# ---- local checkpoint ----
ckpt = {
    "checkpoint_id": f"w050-ckpt-{stamp}",
    "actor": "worker-050",
    "task_id": d["task_id"],
    "node_id": d["node_id"],
    "class_id": d["class_id"],
    "gate": d["gate"],
    "created_at": created,
    "status": "task_complete_exiting",
    "reviewed_sha256": reviewed,
    "verdict": "accept",
    "score": 4,
    "hard_failures": 0,
    "minor_findings": len(d["findings"]),
    "artifacts": {
        str(AUDIT.relative_to(ROOT)): audit_h,
        str(SCRIPT.relative_to(ROOT)): script_h,
        "artifacts/worker-050/f2a_frozen_bind_audit/measured_hashes.json": sha(OUTDIR / "measured_hashes.json"),
    },
    "events_written": [e["event_id"] for e in new],
    "outbox": str(out.relative_to(ROOT)),
    "next_falsifier": events[2]["next_falsifier"],
    "non_claims": d["non_claims"],
}
(OUTDIR / "CHECKPOINT.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n")
log = ROOT / "artifacts" / "worker-050" / "checkpoints.jsonl"
with log.open("a") as fh:
    fh.write(json.dumps(ckpt, ensure_ascii=False) + "\n")

print(json.dumps({"validated": len(events), "written": len(new), "audit_sha256": audit_h, "script_sha256": script_h, "outbox": str(out)}, indent=1))
