#!/usr/bin/env python3
"""Emit worker-08 comms/outbox messages reproducibly.

Writes one-line JSON files (valid JSON and valid JSONL) into comms/outbox/.
Schema-valid event types per research_map/schemas.py: claim, artifact, resource_request.
Contract-listed but schema-unsupported types (status, blocker) are written as *.msg.json
and are deliberately excluded from event validation; see e08_README.md.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "comms" / "outbox"
ART = REPO / "artifacts" / "worker08"
TS = "2026-09-11T23:23:00+08:00"
ACTOR = "deepseek-flash-08"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


gate = ART / "map_artifact_gate.json"
proposal_json = ART / "proposal_E08_F2a.json"
proposal_md = ART / "proposal_E08_F2a.md"
checker = ART / "check_map_artifacts.py"

CLASS_IDS_ALL = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

events = {
    # ---- schema-valid: artifact ----
    "e08_artifact_map_gate.event.json": {
        "event_id": "e08-art-20260911T2323-map-gate",
        "event_type": "artifact",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F0",
        "covers_nodes": ["F0", "A0"],
        "group_id": "formulation+audit",
        "class_ids": CLASS_IDS_ALL,
        "artifact_type": "validation_gate_report",
        "path": "artifacts/worker08/map_artifact_gate.json",
        "sha256": sha256(gate),
        "validation_status": "passed",
        "validation_scope_note": (
            "'passed' refers to this gate report: it is deterministic and reproducible "
            "(generator artifacts/worker08/check_map_artifacts.py, sha256 "
            f"{sha256(checker)}). The gate's own verdict on the map is FAIL: "
            "2/2 done nodes declare artifacts that do not exist on disk."
        ),
        "gate_verdict": "fail",
        "gate_result": {"done_nodes": 2, "done_nodes_with_existing_artifact": 0},
        "generator_path": "artifacts/worker08/check_map_artifacts.py",
        "generator_sha256": sha256(checker),
        "reproduce": "python3 artifacts/worker08/check_map_artifacts.py  # exit 1 == gate fail",
        "map_sha256": sha256(REPO / "research_map" / "research_map.json"),
        "evidence_refs": [
            "research_map/ASTRA_HANDOFF.md#hard-decisions item 4",
            "research_map/validate_map.py lines 23-26 (declares-artifact-only check)",
            "research_map/research_map.json F0 line 26, A0 line 54",
        ],
        "next_falsifier": (
            "Place research_map/formulation_taxonomy.yaml and evaluation_rubric.yaml on disk, "
            "re-run check_map_artifacts.py; if it returns exit 0 the blocker is falsified."
        ),
    },
    # ---- schema-valid: claim (proposal, explicitly not a mathematical result) ----
    "e08_claim_f2a.event.json": {
        "event_id": "e08-claim-20260911T2323-f2a",
        "event_type": "claim",
        "created_at": TS,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "statement": (
            "Proposed assignment E08-F2a (NOT accepted, NOT started): draft "
            "schemas/af_scc_c2_vacuum.yaml for class AF-SCC-C2-VAC-GEN only, with exact "
            "quantifiers, topology, weighted data class, genericity, I+, visibility and "
            "conclusion type; no C0 content, no merged 'C0 or C2'. This is a task proposal, "
            "not a mathematical claim and not a completion claim."
        ),
        "conclusion_type": "open_problem",
        "assumptions": [
            "lead-formulation approves class binding, acceptance tests and artifact schema",
            "F0 taxonomy artifact exists before downstream done-status is credible",
            "L1 citation resolution may remain unresolved in the draft",
        ],
        "falsifier": [
            "FALSIFIER-E08-F2a-1 class leakage: a C0-inextendibility conclusion or 'C0 or C2' outside anti_scope",
            "FALSIFIER-E08-F2a-2 conclusion inflation: conclusion_type=theorem without proof artifact and L1-verified source",
            "FALSIFIER-E08-F2a-3 unenforceable visibility: visibility used in the conclusion but not defined on the completed spacetime",
            "FALSIFIER-E08-F2a-4 unbacked artifact: node marked done while the file is absent or hash-mismatched",
        ],
        "proposal_path": "artifacts/worker08/proposal_E08_F2a.json",
        "proposal_sha256": sha256(proposal_json),
        "proposal_md_path": "artifacts/worker08/proposal_E08_F2a.md",
        "proposal_md_sha256": sha256(proposal_md),
        "acceptance_tests": "T1-T10 in artifacts/worker08/proposal_E08_F2a.json",
        "evidence_refs": [
            "research_map/ASTRA_HANDOFF.md line 39 (immediate queue F2) and lines 30-31 (hard decisions 1-2)",
            "research_map/research_map.json F2 line 28, F0 line 26",
            "research_map/ARCHITECTURE.md lines 13, 22, 46",
            "artifacts/worker08/map_artifact_gate.json",
        ],
        "next_falsifier": "A lead observes that F2a is already assigned or that the acceptance tests admit class leakage; then this proposal is rejected or revised.",
    },
    # ---- schema-valid: resource_request ----
    "e08_resource_request_f2a.event.json": {
        "event_id": "e08-rr-20260911T2323-f2a",
        "event_type": "resource_request",
        "created_at": TS,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "requested_agents": 1,
        "requested_agent_hours": 2.0,
        "justification": (
            "F2 is queued with no owner; it is the only unowned class-bound node on the "
            "immediate queue. One breadth executor can produce a reviewer-ready draft while "
            "F1 remains with lead-formulation. Blocked on F0 artifact existence and lead approval."
        ),
        "expected_information_gain": (
            "Tests whether the F1 schema template generalises to a second, non-merged class; "
            "a negative result (acceptance tests need human judgement) counts against the "
            "cheap-verification entry criterion."
        ),
        "stop_rule": "Stop at draft artifact + self-check T1-T9, or at 2.0 agent-hours, whichever is first; emit artifact and blocker events either way.",
        "preconditions": [
            "F0 artifact research_map/formulation_taxonomy.yaml exists (currently MISSING)",
            "lead-formulation assignment approval",
        ],
        "proposal_path": "artifacts/worker08/proposal_E08_F2a.json",
        "proposal_sha256": sha256(proposal_json),
        "evidence_refs": ["artifacts/worker08/map_artifact_gate.json", "research_map/research_map.json F0/F2"],
        "next_falsifier": "If the requested hours are not available or F0 remains missing at the next checkpoint, withdraw this request and re-propose after the gate passes.",
    },
}

# ---- contract-listed message types that the current schema does not accept ----
messages = {
    "e08_status.msg.json": {
        "event_id": "e08-status-20260911T2323",
        "event_type": "status",
        "created_at": TS,
        "actor": ACTOR,
        "worker": "deepseek-flash-08",
        "group_id": "formulation",
        "node_ids": ["F0", "F2"],
        "class_ids": CLASS_IDS_ALL,
        "assignment_check": {
            "comms_inbox_path": "comms/inbox",
            "files_found": 0,
            "checked_at": TS,
            "result": "no class-bound assignment exists",
        },
        "queue_inspected": ["F1", "F2", "L0/L1", "A1", "N0", "A2"],
        "checkpoint": "1 of up to 8",
        "emitted": [
            "e08_artifact_map_gate.event.json (schema-valid)",
            "e08_claim_f2a.event.json (schema-valid)",
            "e08_resource_request_f2a.event.json (schema-valid)",
            "e08_blocker_f0_a0.msg.json (contract-listed, schema-unsupported)",
            "this status message (contract-listed, schema-unsupported)",
        ],
        "no_completion_claimed": True,
        "evidence_refs": ["artifacts/worker08/map_artifact_gate.json", "artifacts/worker08/proposal_E08_F2a.json"],
        "next_falsifier": "If an assignment appears in comms/inbox before the next checkpoint, this 'no assignment' status is falsified and the assignment is executed instead.",
        "schema_note": "event_type 'status' is in the ASTRA_HANDOFF/ARCHITECTURE communication contract but absent from research_map/schemas.py EVENT_TYPES; recorded as a schema gap, not silently renamed.",
    },
    "e08_blocker_f0_a0.msg.json": {
        "event_id": "e08-blocker-20260911T2323-f0-a0",
        "event_type": "blocker",
        "created_at": TS,
        "actor": ACTOR,
        "worker": "deepseek-flash-08",
        "group_id": "formulation+audit",
        "node_ids": ["F0", "A0"],
        "class_ids": CLASS_IDS_ALL,
        "blocker": (
            "Nodes F0 and A0 are marked status=done, validation_status=passed, but their declared "
            "artifacts do not exist on disk: research_map/formulation_taxonomy.yaml and "
            "evaluation_rubric.yaml. Every downstream node (F1, F2, L0, L1, A1, N0, N1, A2) "
            "inherits this unbacked dependency."
        ),
        "hard_failures": [
            "F0 declared artifact missing: research_map/formulation_taxonomy.yaml",
            "A0 declared artifact missing: evaluation_rubric.yaml",
            "research_map/validate_map.py prints VALID because it never stats declared artifact paths",
        ],
        "secondary_findings": [
            "communication contract lists status/blocker but schemas.py EVENT_TYPES lacks both; review is schema-valid but not in the contract",
        ],
        "suggested_gate_outcome": "A1/lead-audit: reject F0/A0 done-status pending artifact evidence; do not unblock F1/F2/L0/N0 on declared-only artifacts.",
        "adjudication_owner": "lead-audit (A1) / astra",
        "owner_of_fix": "lead-formulation (F0), lead-audit (A0)",
        "evidence_refs": [
            "artifacts/worker08/map_artifact_gate.json",
            "research_map/ASTRA_HANDOFF.md#hard-decisions item 4",
            "research_map/validate_map.py lines 23-26",
        ],
        "next_falsifier": "If both declared artifacts exist with matching hashes and are accepted by A1, this blocker is falsified; re-run check_map_artifacts.py to confirm exit 0.",
        "schema_note": "event_type 'blocker' is contract-listed but absent from research_map/schemas.py EVENT_TYPES; a schema-valid 'review' event would be the nearest supported carrier, which is a contract/schema mismatch to fix.",
    },
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for name, payload in {**events, **messages}.items():
        path = OUT / name
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
        written.append(str(path.relative_to(REPO)))
    print("\n".join(written))
    print(f"schema-valid events: {len(events)}; contract-only messages: {len(messages)}")


if __name__ == "__main__":
    main()
