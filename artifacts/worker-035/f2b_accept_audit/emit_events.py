#!/usr/bin/env python3
"""Emit worker-035 F2b accept-audit events and checkpoint. Idempotent-guarded by event_id."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ADIR = os.path.join(ROOT, "artifacts", "worker-035", "f2b_accept_audit")
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-035.jsonl")
CKPT = os.path.join(ROOT, "runtime", "state", "worker-035_F2b_accept_audit_checkpoint.json")
PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
STAMP = "20260912T0118"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


now = datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).isoformat()
report = json.load(open(os.path.join(ADIR, "report.json")))
controls = json.load(open(os.path.join(ADIR, "controls.json")))
h = {
    "report": sha(os.path.join(ADIR, "report.json")),
    "controls": sha(os.path.join(ADIR, "controls.json")),
    "checker": sha(os.path.join(ADIR, "audit_f2b_accepts.py")),
    "readme": sha(os.path.join(ADIR, "README.md")),
    "emit": sha(os.path.abspath(__file__)),
    "snapshot_sums": sha(os.path.join(ADIR, "snapshot", "SHA256SUMS")),
    "census_snapshot": sha(os.path.join(ADIR, "snapshot", "census_map_66ada65f6027.json")),
}
map_sha = report["headline"]["census_map_sha256"]
hl = report["headline"]

ev_artifact = {
    "actor": "worker-035", "event_type": "artifact", "event_id": f"w035-f2b-aa-{STAMP}-artifact-report",
    "created_at": now, "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
    "artifact_type": "f2b_accept_coverage_materiality_audit",
    "path": "artifacts/worker-035/f2b_accept_audit/report.json", "sha256": h["report"],
    "validation_status": "unverified",
    "summary": (
        f"At FROZEN rev29 pin b2ab6acb (canonical==mirror==pin, zero drift) the two live containment "
        f"defects D1 (line 246 'C2 is a strictly larger extension class' vs the file's own chain at "
        f"line 239) and D2 (line 152 stale denial) are reproduced; of {hl['accepts_bound_at_pin']} "
        f"accept records bound to the pin, {hl['full_schema_accepts_strict']} strict / "
        f"{hl['full_schema_accepts_permissive']} permissive full-schema accepts exist, "
        f"{hl['material_accepts_disposing_all_live_defects']} dispose of every live defect family, "
        f"{hl['silent_full_schema_accepts']} never engage either family, and "
        f"{hl['accepts_with_contradicted_resolution_claims']} asserts resolution the bytes contradict. "
        f"Accept coverage is nominal, not material."),
    "evidence_refs": [
        f"artifacts/worker-035/f2b_accept_audit/report.json#sha256:{h['report'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/controls.json#sha256:{h['controls'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/audit_f2b_accepts.py#sha256:{h['checker'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/README.md#sha256:{h['readme'][:12]}",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        f"research_map/research_map.json#sha256:{map_sha[:12]}",
    ],
    "falsifier": report["falsifiers"],
    "non_claims": report["non_claims"],
}

ev_review = {
    "actor": "worker-035", "event_type": "review", "event_id": f"w035-f2b-aa-{STAMP}-review-coverage",
    "created_at": now, "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
    "target_id": "F2b accept coverage @ schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
    "reviewer": "worker-035", "verdict": "revise", "score": 2.5,
    "reviewed_sha256": PIN,
    "hard_failures": report["hard_failures"],
    "findings": [
        (f"D1 live at line {report['defects']['forbidden_transfer_line']}: "
         f"'{report['defects']['forbidden_transfer_reason']}' while the file's chain at line "
         f"{report['defects']['chain_line']} has E_C2 innermost; 0 of "
         f"{hl['full_schema_accepts_permissive']} permissive full-schema accepts at the pin flags it."),
        (f"D2 live at line {report['defects']['denial_line']}: the stale denial "
         f"'{report['defects']['denial_sentence'][:80]}...' is not repaired."),
        (f"Nominal accept bar is met ({hl['full_schema_accepts_strict']} strict / "
         f"{hl['full_schema_accepts_permissive']} permissive hash-bound full-schema accepts) but "
         f"material coverage is 0: 3 accepts are silent on both live families and worker-16 asserts "
         f"the H2_loc/transfer contradictions resolved, which the cited bytes contradict."),
        ("worker-090 C04-one-way-C0-to-C2, re-implemented here, is a structural presence check "
         "(c0_to_c2 and not rev_rows and rev_forbidden) and passes on the inverted reason; it never "
         "inspects forbidden_transfers[*].reason."),
        (f"review_status.independent_reviewers=[] / verdict=pending at the pin while "
         f"{hl['records_bound_to_pin']} F2b verdict records bind the measured bytes."),
        ("This is a post-hoc coverage audit, not a blind verdict: worker-035's blind F2b verdicts "
         "at 55d0a1ea (rev27-b) and b2ab6acb (rev13-bindchain) were already written and ingested."),
    ],
    "evidence_refs": [
        f"artifacts/worker-035/f2b_accept_audit/report.json#sha256:{h['report'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/controls.json#sha256:{h['controls'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/audit_f2b_accepts.py#sha256:{h['checker'][:12]}",
        f"research_map/research_map.json#sha256:{map_sha[:12]}",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/worker-090/f2b_rev13_full_verdict/check_f2b_rev13_full.py",
    ],
    "non_claims": [
        "not a gate verdict; worker events cannot set G-FORM or node status",
        "does not overturn or replace any reviewer verdict; audits coverage materiality only",
        "no physics claim",
    ],
}

ckpt = {
    "checkpoint_id": f"worker-035-F2b-accept-audit-{STAMP}",
    "created_at": now, "actor": "worker-035", "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
    "task_id": "W035-F2B-ACCEPT-AUDIT-01",
    "selection_reason": ("No live inbox card for worker-035: r2 cards audit-r2-F2b-b and "
                         "audit-r2-F2b-bindchain-worker-035 pin rev12 55d0a1ea, which the controller "
                         "voided at astra-life05; their moving-target blocker is already ingested. "
                         "Took one self-selected class-bound task from the live queue (F2b coverage)."),
    "pins": report["pins"],
    "headline": hl,
    "artifacts_written": {k: v for k, v in h.items()},
    "canonical_paths_written": [],
    "events": [ev_artifact["event_id"], ev_review["event_id"], f"w035-f2b-aa-{STAMP}-status-checkpoint"],
    "checkpoint_path": "runtime/state/worker-035_F2b_accept_audit_checkpoint.json",
    "falsifier": report["falsifiers"],
    "next_falsifier": ("Corrected bytes at schema lines 246/152, or a new hash-bound full-schema accept "
                       "that explicitly dispositions both live defect families, voids this coverage finding."),
    "non_claims": report["non_claims"],
}

with open(CKPT, "w", encoding="utf-8") as fh:
    json.dump(ckpt, fh, indent=1, sort_keys=True)
h["checkpoint"] = sha(CKPT)

ev_status = {
    "actor": "worker-035", "event_type": "status", "event_id": f"w035-f2b-aa-{STAMP}-status-checkpoint",
    "created_at": now, "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
    "status": "active", "hours": 0.5,
    "summary": (
        "CHECKPOINT / bounded lifecycle for W035-F2B-ACCEPT-AUDIT-01: report.json, controls.json "
        "(8/8), audit_f2b_accepts.py, README.md and pinned snapshots on disk and hash-pinned; "
        "13 checks, 10 pass, 2 blocking fails are the finding (P08 material accepts=0, P10 one "
        "contradicted resolution claim). Canonical paths untouched; all node/gate states untouched."),
    "evidence_refs": [
        f"runtime/state/worker-035_F2b_accept_audit_checkpoint.json#sha256:{h['checkpoint'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/report.json#sha256:{h['report'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/controls.json#sha256:{h['controls'][:12]}",
        f"artifacts/worker-035/f2b_accept_audit/snapshot/SHA256SUMS#sha256:{h['snapshot_sums'][:12]}",
    ],
    "next_falsifier": ckpt["next_falsifier"],
    "completion_scope": "worker lifecycle only; not a node done / gate verdict",
    "non_claims": report["non_claims"],
}

existing = set()
if os.path.exists(OUTBOX):
    for line in open(OUTBOX, encoding="utf-8"):
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
emitted = []
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in (ev_artifact, ev_review, ev_status):
        if ev["event_id"] in existing:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
        emitted.append(ev["event_id"])
print(json.dumps({"emitted": emitted, "hashes": h}, indent=1))
