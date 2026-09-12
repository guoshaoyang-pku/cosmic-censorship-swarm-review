#!/usr/bin/env python3
"""Emit the w16-REV28-VERIFY-01 events and checkpoint.

Appends artifact/review/status/blocker events to comms/outbox/worker-16.jsonl and writes
runtime/state/w016_checkpoint_rev28_verify.json (+ w016_checkpoints.jsonl).

Every event carries ids, class ids, evidence refs as path#sha256-prefix and a falsifier.
Worker authority is respected: no status=done, no validation_status=passed, no gate verdict.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NOW = dt.datetime.now().astimezone().isoformat(timespec="seconds")
OUTBOX = ROOT / "comms/outbox/worker-16.jsonl"
STATE = ROOT / "runtime/state"
TASK = "W16-REV28-VERIFY-01"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bytes_of(p: Path) -> int:
    return len(p.read_bytes())


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT).as_posix()}#sha256:{sha(p)[:12]}"


DELIVERABLES = {
    "verification_json": HERE / "verification.json",
    "report_md": HERE / "REPORT.md",
    "run_verification_py": HERE / "run_verification.py",
    "finalize_verification_py": HERE / "finalize_verification.py",
}
V = json.loads(DELIVERABLES["verification_json"].read_text())
FINAL_REF = ref(DELIVERABLES["verification_json"])
F1_DOC = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
C2_DOC = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
C0_DOC = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NEXT_FALSIFIER = V["falsifier"]

events = []


def add(ev: dict):
    ev.setdefault("event_id", "")
    assert ev["event_id"], ev
    events.append(ev)


# ---- artifact events
ART_TYPES = {
    "verification_json": "verification_report",
    "report_md": "verification_report_md",
    "run_verification_py": "verification_tool",
    "finalize_verification_py": "verification_tool",
}
for key, p in DELIVERABLES.items():
    add({
        "event_id": f"w16-REV28-VERIFY-01-artifact-{key}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-16",
        "artifact_type": ART_TYPES[key],
        "path": p.relative_to(ROOT).as_posix(),
        "sha256": sha(p),
        "bytes": bytes_of(p),
        "validation_status": "unverified",
        "node_id": "F1,F2a,F2b",
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "group_id": "formulation",
        "task_id": TASK,
        "claims_completion": False,
        "evidence_refs": [ref(p)],
        "summary": "Independent staged re-run + class-binding census at FROZEN revision 28; "
                   "two hard findings (acceptance preflight stale; stage-2 R03 reject on F1).",
        "next_falsifier": NEXT_FALSIFIER,
    })

# ---- review events
add({
    "event_id": "w16-REV28-VERIFY-01-review-acceptance",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-16",
    "target_id": "artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:9b7d6c8208d3",
    "reviewer": "worker-16",
    "verdict": "revise",
    "score": 1,
    "hard_failures": ["W16R28-F1"],
    "findings": [
        "run_acceptance.py exits 3 at the frozen bytes: PREFLIGHT FAIL, rebased corpus base "
        "1bb78ce9b357 != current C0 55d0a1ea9bda.",
        "The report file mtime 2026-09-12T00:27:40+08:00 predates the rev12 schemas "
        "(revised_at 00:31:41, mtime 00:32:02), so its union 31/31 PASS cannot bind rev12.",
        "Needed: re-base the semantic corpus against the frozen C0 hash and re-run "
        "run_acceptance.py; or mark this evidence superseded and re-measure.",
    ],
    "evidence_refs": [FINAL_REF,
                      "artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:9b7d6c8208d3",
                      "artifacts/formulation/evidence/semantic_escape_rebased.json#sha256:7e44de0e3906",
                      "schemas/af_scc_c0_vacuum.yaml#sha256:55d0a1ea9bda"],
    "node_id": "F1,F2a,F2b",
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "task_id": TASK,
    "next_falsifier": "A run_acceptance.py run at the frozen bytes that exits 0 refutes this verdict.",
})
add({
    "event_id": "w16-REV28-VERIFY-01-review-f1-schema",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-16",
    "target_id": f"schemas/af_wcc_vacuum.yaml#sha256:{F1_DOC[:12]}",
    "reviewer": "worker-16",
    "verdict": "revise",
    "score": 3,
    "hard_failures": ["W16R28-F2"],
    "findings": [
        "Stage 2 of the pipeline's own acceptance (artifacts/worker-06/spec_conformance_audit.py, "
        "sha c79d8ab8440a - the tool hash recorded in the corpus evidence) returns reject for "
        "af_wcc_vacuum.yaml#cce9c60146d6 with failed_rules ['R03']: binder '(q,t0)' absent from "
        "formal sentence.",
        "C2 and C0 return accept at 5476a3f2c6bc / 55d0a1ea9bda.",
        "Stage 1 (check_class_schema.py R01-R16) passes on the same bytes.",
        "Disposition is formulation/audit authority: fix the formal sentence to contain the declared "
        "binder, or record R03 as a literal-match false positive and amend the rule/pipeline.",
    ],
    "evidence_refs": [FINAL_REF,
                      f"schemas/af_wcc_vacuum.yaml#sha256:{F1_DOC[:12]}",
                      "artifacts/worker-06/spec_conformance_audit.py#sha256:c79d8ab8440a"],
    "node_id": "F1",
    "class_ids": ["AF-WCC-VAC-GEN"],
    "gate": "G-FORM",
    "task_id": TASK,
    "next_falsifier": f"A stage-2 run at {F1_DOC[:12]} returning accept, or an adjudication "
                      "amending R03 and re-running run_acceptance.py to exit 0.",
})

# ---- status
add({
    "event_id": "w16-REV28-VERIFY-01-status",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-16",
    "node_id": "F1,F2a,F2b",
    "status": "active",
    "hours": 0.4,
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "group_id": "formulation",
    "task_id": TASK,
    "claims_completion": False,
    "summary": (
        "Self-claimed class-bound task complete (worker-level evidence; not a gate verdict). "
        "Independent staged re-run at FROZEN revision 28 (sha256 2f358f6722d9, frozen_at 00:35:08, "
        "44 files, 0/44 drift): stage 1 passes on all 3 canonical schemas + byte-identical mirrors; "
        "class-binding census clean (0 non-frozen class tokens, pointers and f0_binding resolve to "
        "0abb9ed8a961). Green: manifest, stage 1, controls, F0 binding. Red: (1) run_acceptance.py "
        "cannot run at the frozen bytes (exit 3, stale corpus base 1bb78ce9 vs C0 55d0a1ea) and the "
        "pinned acceptance PASS predates rev12 (mtime 00:27:40 < revised_at 00:31:41); (2) stage 2 "
        "rejects af_wcc_vacuum.yaml#cce9c601 (R03 binder '(q,t0)' absent from formal sentence) while "
        "C2/C0 accept. Medium: gate_test_report.json pin is absolute-path dependent. Timeline: FROZEN "
        "moved 27->28 during the pass; rev27 had 3 post-freeze evidence rewrites. No shared artifact "
        "modified; all re-runs staged under artifacts/worker-16/rev27_verify/stage/."),
    "evidence_refs": [FINAL_REF,
                      "artifacts/formulation/FROZEN.json#sha256:2f358f6722d9",
                      f"schemas/af_wcc_vacuum.yaml#sha256:{F1_DOC[:12]}",
                      f"schemas/af_scc_c0_vacuum.yaml#sha256:{C0_DOC[:12]}",
                      "research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961"],
    "next_falsifier": NEXT_FALSIFIER,
})

# ---- blocker
add({
    "event_id": "w16-REV28-VERIFY-01-blocker",
    "event_type": "blocker",
    "created_at": NOW,
    "actor": "worker-16",
    "node_id": "F1,F2a,F2b",
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "group_id": "formulation",
    "task_id": TASK,
    "description": (
        "Independent verification at FROZEN rev28 cannot close G-FORM on the machine evidence as "
        "published: (B-A) acceptance_pipeline_report.json#9b7d6c82 is stale (corpus base 1bb78ce9 vs "
        "C0 55d0a1ea; run_acceptance exits 3; file mtime 00:27:40 predates rev12 schemas), so no "
        "two-stage PASS exists at the frozen hashes; (B-B) stage 2 rejects F1 "
        "af_wcc_vacuum.yaml#cce9c601 with R03 'binder (q,t0) absent from formal sentence'."),
    "needed_to_unblock": (
        "(1) re-base the semantic corpus to the frozen C0 hash "
        "(python3 artifacts/formulation/tools/measure_semantic_escape.py) and re-run "
        "run_acceptance.py to exit 0, or record the corpus number as superseded; (2) fix or adjudicate "
        "R03 for F1 and re-run stage 2 at the frozen hash."),
    "evidence_refs": [FINAL_REF,
                      "artifacts/formulation/evidence/acceptance_pipeline_report.json#sha256:9b7d6c8208d3",
                      f"schemas/af_wcc_vacuum.yaml#sha256:{F1_DOC[:12]}"],
    "next_falsifier": NEXT_FALSIFIER,
})

# ---- write outbox
OUTBOX.parent.mkdir(parents=True, exist_ok=True)
with OUTBOX.open("a") as fh:
    for ev in events:
        fh.write(json.dumps(ev, sort_keys=False) + "\n")

# ---- minimal schema validation of what we emitted
REQUIRED = {
    "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type",
                 "path", "sha256", "validation_status"],
    "review": ["event_id", "event_type", "created_at", "actor", "target_id", "reviewer",
               "verdict", "score", "hard_failures", "findings"],
    "status": ["event_id", "event_type", "created_at", "actor", "node_id", "status"],
    "blocker": ["event_id", "event_type", "created_at", "actor", "node_id", "description",
                "needed_to_unblock"],
}
for ev in events:
    miss = [k for k in REQUIRED[ev["event_type"]] if k not in ev]
    assert not miss, (ev["event_id"], miss)
    json.loads(json.dumps(ev))

# ---- checkpoint
map_path = ROOT / "research_map/research_map.json"
checkpoint = {
    "checkpoint_id": "w16-ckpt-rev28-verify-01",
    "worker": "worker-16",
    "worker_slot": "worker-016",
    "actor": "worker-16",
    "checkpoint_at": NOW,
    "task": {
        "id": TASK,
        "self_claimed": True,
        "reason": "leadform-blocker-0005/0006 and the 00:34 resource request asked for independent "
                  "re-runs at the final frozen hashes; no open worker-16 assignment existed at 00:32.",
        "node_id": "F1,F2a,F2b",
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "budget_agent_hours": 1.0,
    },
    "verdict": V["verdict"],
    "findings": V["findings"],
    "controls": V["controls"],
    "runs_exit_codes": {k: v["exit"] for k, v in V["runs"].items()},
    "deliverables": {k: {"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p), "bytes": bytes_of(p)}
                     for k, p in DELIVERABLES.items()},
    "emitted_events": [e["event_id"] for e in events],
    "outbox": "comms/outbox/worker-16.jsonl",
    "map_snapshot_at_read": {"path": "research_map/research_map.json", "sha256": sha(map_path),
                             "note": "controller is writing; re-measure before citing"},
    "falsifier": NEXT_FALSIFIER,
    "read_only": "No shared artifact was modified by this pass. All tool re-runs executed in "
                 "artifacts/worker-16/rev27_verify/stage/.",
    "authority_note": "worker event cannot set validation_status=passed, node status=done, or a gate "
                      "verdict; review/blocker evidence is for lead-audit and the controller.",
    "hours_this_pass": 0.4,
}
STATE.mkdir(parents=True, exist_ok=True)
ck = STATE / "w016_checkpoint_rev28_verify.json"
ck.write_text(json.dumps(checkpoint, indent=2) + "\n")
with (STATE / "w016_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps({"checkpoint_id": checkpoint["checkpoint_id"], "at": NOW,
                         "path": ck.name, "verdict": V["verdict"]["summary"][:300],
                         "events": len(events)}) + "\n")

print(f"emitted {len(events)} events -> {OUTBOX.relative_to(ROOT)}")
for e in events:
    print(" ", e["event_type"], e["event_id"])
print("checkpoint ->", ck.relative_to(ROOT))
