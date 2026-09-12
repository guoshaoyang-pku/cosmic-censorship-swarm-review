#!/usr/bin/env python3
"""Append worker-08's FORM-SEP-04 events to comms/outbox/deepseek-flash-08.jsonl (idempotent)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
ART = REPO / "artifacts" / "worker08"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-08"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


matrix = ART / "c2_c0_separation_matrix.json"
report = ART / "c2_c0_separation_report.md"
auditor = ART / "c2_c0_separation_audit.py"
m = json.loads(matrix.read_text())
prop = m["X3_propagation"]["adjacent_files_carrying_the_defect"]
fail = m["hard_failures"][0]
h1 = fail["hits"][0]

events = [
    {
        "event_id": "e08-art-20260911T2330-form-sep-04",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "separation_audit",
        "path": "artifacts/worker08/c2_c0_separation_matrix.json",
        "sha256": sha256(matrix),
        "validation_status": "unverified",
        "audit_verdict": m["verdict"],
        "hard_failure_count": len(m["hard_failures"]),
        "X1_violations": len(m["X1_pairwise"]["expectation_violations"]),
        "X2_unjustified": m["X2_foreign_semantics"]["unjustified_count"],
        "X3_converse_assertions": len(m["X3_implication_ledger"]["converse_assertions"]),
        "X4_violations": len(m["X4_composite_regularity"]["violations"]),
        "gate_runs": {"C2": m["gate_runs"]["artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"]["verdict"],
                      "C0": m["gate_runs"]["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]["verdict"]},
        "report": {"path": "artifacts/worker08/c2_c0_separation_report.md", "sha256": sha256(report)},
        "auditor": {"path": "artifacts/worker08/c2_c0_separation_audit.py", "sha256": sha256(auditor)},
        "inputs": m["inputs"],
        "reproduce": "python3 artifacts/worker08/c2_c0_separation_audit.py",
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#38b4d285",
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#f389309f",
            "artifacts/formulation/rule_spec.json#c41c4790",
            "comms/inbox/deepseek-flash-08.jsonl",
        ],
        "next_falsifier": m["next_falsifier"],
    },
    {
        "event_id": "e08-status-20260911T2330-form-sep-04",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "status": "active",
        "hours": 2.5,
        "summary": (
            "FORM-SEP-04 executed, read-only, stop rule met (canonical hashes recorded + one gate run "
            "per schema). Verdict FAIL on exactly one genuine separation defect: the C0 schema's "
            "non_vacuity.c0_specific_note asserts that a C2-inextendibility proof SUBSUMES the C0 "
            "conclusion, i.e. the forbidden converse of extension-class containment (valid direction is "
            "C0 => C2 only). X1 frozen-axis violations 0; X2 unjustified foreign-regularity mentions 0 "
            "(5 leakage-block hits are justified exclusions / R10-mandated WCC naming); X4 composite "
            "violations 0; all 4 implication-ledger checks pass. The same wrong sentence has propagated "
            f"into {len(prop)} fixture/control files. L1 citation audit remains submitted and unchanged. "
            "No node completion claimed."
        ),
        "assignment_conflict": (
            "astra-adj1-01-assignment (23:22) told me to author schemas/af_scc_c2_vacuum.yaml; "
            "assign-FORM-SEP-04-20260911T2331 (23:31, lead-formulation) states my proposed deliverable "
            "is superseded, the canonical C2 file is artifacts/formulation/schemas/af_scc_c2_vacuum.yaml, "
            "and 'Do not author schemas'. I followed the group lead's later revision requirement and did "
            "not author a schema; request adjudication if astra still wants a worker-authored copy."
        ),
        "evidence_refs": [
            "artifacts/worker08/c2_c0_separation_matrix.json#" + sha256(matrix)[:8],
            "artifacts/worker08/c2_c0_separation_report.md#" + sha256(report)[:8],
        ],
        "next_falsifier": m["next_falsifier"],
    },
    {
        "event_id": "e08-blocker-20260911T2330-c0-converse",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": ACTOR,
        "group_id": "formulation",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "description": (
            "Exact defect: artifacts/formulation/schemas/af_scc_c0_vacuum.yaml line 161, "
            "non_vacuity.c0_specific_note = \"a C2-inextendibility proof SUBSUMES this class's "
            "conclusion (C0-inextendibility is stronger); ...\". Under C2-extension subset C0-extension, "
            "C0-inextendibility is stronger and the only valid entailment is C0 => C2; the sentence "
            "states the converse. Same phrase copied into "
            f"{len(prop)} fixture/control files: {', '.join(prop[:6])}"
            + (" ..." if len(prop) > 6 else "")
        ),
        "needed_to_unblock": (
            "One-line wording repair at the exact path (\"a C2-inextendibility proof does NOT subsume "
            "this class's conclusion; the implication runs C0 => C2 only (C0-inextendibility is "
            "stronger)\"), regenerate/patch the cloned fixture copies, re-hash, then re-run "
            "artifacts/worker08/c2_c0_separation_audit.py; separation passes only if X3 converse "
            "assertions are empty at the new hash."
        ),
        "evidence_refs": [
            "artifacts/worker08/c2_c0_separation_matrix.json#" + sha256(matrix)[:8],
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#38b4d285",
        ],
        "next_falsifier": (
            "If the repaired sentence still admits the reading 'C2 proof gives C0-inextendibility', or "
            "any fixture retains the old phrase, the audit fails again at the new hash."
        ),
    },
]

existing_ids = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                existing_ids.add(json.loads(line)["event_id"])
            except (ValueError, KeyError):
                pass

added = []
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in events:
        if ev["event_id"] in existing_ids:
            continue
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        added.append(ev["event_id"])

print(json.dumps({"added": added, "total_events": len(existing_ids) + len(added),
                  "propagated_files": len(prop)}, indent=2))
