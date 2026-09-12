#!/usr/bin/env python3
"""Emit W058-CONTAIN-01 upward events, validated against research_map.schemas.

Idempotent: event_ids already present in comms/outbox/worker-058.jsonl are not
re-emitted.  The controller (comms.py ingest) is the only writer of events.jsonl;
this script writes only the worker's own outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-058.jsonl"
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    audit = json.loads((HERE / "containment_premise_audit.json").read_text(encoding="utf-8"))
    selftest = json.loads((HERE / "sensitivity_selftest.json").read_text(encoding="utf-8"))
    f1 = audit["hard_failures"][0]
    now = datetime.now(CST).isoformat(timespec="seconds")
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    c0_live = audit["binding_status"]["live_hashes"]["AF-SCC-C0-VAC-GEN"]
    c2_live = audit["binding_status"]["live_hashes"]["AF-SCC-C2-VAC-GEN"]
    fz = audit["inputs"]["frozen_manifest"]
    ev = f1["yaml_path"]
    base = "artifacts/worker-058/containment_premise"

    artifacts = [
        ("containment_premise_audit_json", f"{base}/containment_premise_audit.json"),
        ("containment_premise_checker", f"{base}/check_containment_premise.py"),
        ("containment_premise_selftest_json", f"{base}/sensitivity_selftest.json"),
        ("containment_premise_report", f"{base}/README.md"),
    ]

    events = []
    for i, (atype, path) in enumerate(artifacts):
        events.append({
            "event_id": f"w058-{stamp}-art-{i}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": "F2b",
            "artifact_type": atype,
            "path": path,
            "sha256": sha(path),
            "validation_status": "unverified",
            "class_id": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
            "note": (
                "Independent containment-premise audit of the frozen SCC ledger pair; "
                "verdict FAIL at C0 line "
                f"{f1['line']}. Unverified: lead-formulation owns interpretation and "
                "any gate consequence."
            ),
        })

    events.append({
        "event_id": f"w058-{stamp}-claim-c0-containment-inversion",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-058",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "statement": (
            "At frozen revision 25 (C0 1bb78ce9..., C2 b6123750..., manifest af24e9c3...), "
            "schemas/af_scc_c0_vacuum.yaml line "
            f"{f1['line']} ({ev}) states 'C2 is a strictly larger extension class', "
            "which contradicts the containment order the same file declares at line 244 "
            "(E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0), where C2 is the "
            "strictly smaller extension class. The row's transfer direction (forbidden) and "
            "its strength consequent (C2-inextendibility strictly weaker) are both correct; "
            "only the class-size antecedent is false. Machine-checked at 23 statements with "
            "a 6/6 mutant sensitivity self-test."
        ),
        "conclusion_type": "counterexample",
        "assumptions": [
            "The implication_ledger.extension_class_containment declaration is the reference order (not re-derived from regularity definitions here).",
            "Strength is monotone in extension-set size: no-proper-extension over a larger set is the stronger statement.",
            "Findings bind to the recorded live sha256 values; the canonical tree was byte-identical to the authoring tree at run time.",
        ],
        "falsifier": audit["next_falsifier"],
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{c0_live}",
            f"schemas/af_scc_c2_vacuum.yaml#{c2_live}",
            f"artifacts/formulation/FROZEN.json#{fz['sha256']}",
            f"{base}/containment_premise_audit.json#{sha(f'{base}/containment_premise_audit.json')}",
            f"{base}/sensitivity_selftest.json#{sha(f'{base}/sensitivity_selftest.json')}",
        ],
        "artifact_refs": [f"{base}/containment_premise_audit.json"],
    })

    events.append({
        "event_id": f"w058-{stamp}-blocker-c0-size-premise",
        "event_type": "blocker",
        "created_at": now,
        "actor": "worker-058",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "description": (
            f"Frozen revision 25 C0 {ev} carries a false class-size antecedent "
            "('C2 is a strictly larger extension class'). The same defect was recorded as "
            "a blocker by deepseek-flash-08 at live hash a8d899d2 (2026-09-12T00:11:04) but "
            "is unchanged at the rev25 freeze 1bb78ce9, i.e. a recorded blocker did not gate "
            "the freeze. Independent re-implementation reproduces it; the sensitivity "
            "self-test passes 6/6 including the exact repair mutest."
        ),
        "needed_to_unblock": (
            "One-word wording repair in implication_ledger.forbidden_transfers[0].reason: "
            "'strictly larger' -> 'strictly smaller' (transfer and consequent unchanged), "
            "then re-freeze and re-run check_containment_premise.py; the audit returns PASS "
            "only if the repair is applied at the new hash. Lead-formulation decides; worker "
            "claims no gate verdict."
        ),
        "evidence_refs": [
            f"schemas/af_scc_c0_vacuum.yaml#{c0_live}",
            f"{base}/containment_premise_audit.json#{sha(f'{base}/containment_premise_audit.json')}",
            f"{base}/sensitivity_selftest.json#{sha(f'{base}/sensitivity_selftest.json')}",
            "comms/outbox/worker-08.jsonl (FORM-SEP-04 blocker 2026-09-12T00:11:04+08:00)",
        ],
    })

    events.append({
        "event_id": f"w058-{stamp}-status-contain-01",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-058",
        "node_id": "F2b",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W058-CONTAIN-01 complete: independent containment-premise audit of the frozen "
            f"SCC ledger pair. Verdict FAIL, 1 hard failure ({f1['code']}, C0 line "
            f"{f1['line']}), 23 statements checked, sensitivity self-test "
            f"{selftest['case_count']}/{selftest['case_count']} expectations met. Boundary "
            "stated: audits internal premise consistency only; no truth, citation, node "
            "completion or gate verdict claimed."
        ),
        "evidence_refs": [
            f"{base}/containment_premise_audit.json#{sha(f'{base}/containment_premise_audit.json')}",
            f"{base}/sensitivity_selftest.json#{sha(f'{base}/sensitivity_selftest.json')}",
            f"schemas/af_scc_c0_vacuum.yaml#{c0_live}",
        ],
        "next_falsifier": audit["next_falsifier"],
    })

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in new:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"emitted {len(new)} new events ({len(events) - len(new)} already present) -> {OUTBOX}")
    for e in new:
        print("  ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
