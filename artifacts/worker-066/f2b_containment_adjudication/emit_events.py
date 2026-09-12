#!/usr/bin/env python3
"""Emit the W066 F2b adjudication events to comms/outbox/worker-066.jsonl.

Every event is validated against research_map/events.schema.json before it is
appended. Event ids are stable (re-running skips ids already present). Timestamps
are wall-clock +08:00, never future-dated (CF-14).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # authoritative controller validator (research_map/schemas.py)

SCHEMA = json.loads((REPO / "research_map/events.schema.json").read_text(encoding="utf-8"))
JSONSCHEMA_TYPES = {"claim", "artifact", "review", "direction_update", "resource_request"}
OUT = REPO / "comms/outbox/worker-066.jsonl"
TASK = "W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01"
NODE = "F2b"
CLASS = "AF-SCC-C0-VAC-GEN"
C0_SHA = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
C2_SHA = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
CAND_SHA = "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main() -> None:
    checks = json.loads((HERE / "evidence/checks.json").read_text(encoding="utf-8"))
    report = json.loads((HERE / "report.json").read_text(encoding="utf-8"))
    h = {
        "adjudicate.py": sha(HERE / "adjudicate.py"),
        "snapshot.py": sha(HERE / "snapshot.py"),
        "PINNED.json": sha(HERE / "PINNED.json"),
        "report.json": sha(HERE / "report.json"),
        "README.md": sha(HERE / "README.md"),
        "checks.json": sha(HERE / "evidence/checks.json"),
        "controls.json": sha(HERE / "evidence/controls.json"),
        "candidate_check.json": sha(HERE / "evidence/candidate_check.json"),
    }
    t = now()
    ev = []
    ev.append({
        "event_id": "w066-f2b-r12-01-status-task", "event_type": "status", "created_at": t,
        "actor": "worker-066", "node_id": NODE, "class_id": CLASS,
        "class_ids": [CLASS, "AF-SCC-C2-VAC-GEN"], "status": "active", "hours": 0.2, "task_id": TASK,
        "summary": "No assignment card exists in comms/inbox for worker-066. Taking one bounded class-bound task: independent hash-bound adjudication of the open F2b blocker w008-f2b-20260912T003407+0800-blocker-rev12 at the FROZEN rev27/28 pin schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda (class AF-SCC-C0-VAC-GEN). Reviewer verdict only; workers cannot set gates.",
        "evidence_refs": [f"artifacts/worker-066/f2b_containment_adjudication/PINNED.json#{h['PINNED.json'][:12]}",
                          f"schemas/af_scc_c0_vacuum.yaml#{C0_SHA[:12]}"],
        "next_falsifier": "any pinned byte changes mid-run, or the checker fails to reproduce both findings on the pinned bytes, or a control departs from its pre-registered expectation",
    })
    for name, atype, note in [
        ("PINNED.json", "manifest", "ten pinned inputs, sha256/bytes/mtime + byte copies in pinned/"),
        ("report.json", "verdict", "adjudication report: verdict revise 2.5, H1/H2 confirmed, candidate 98f9ec83 verified, falsifier"),
        ("README.md", "readme", "method, result table, controls, resolution, limits"),
        ("checks.json", "evidence", "every independent check with raw observations incl. the rescue-reading analysis"),
        ("controls.json", "evidence", "7 pre-registered controls with expected vs observed verdicts"),
        ("candidate_check.json", "evidence", "leaf diff, binding equality, defect clearance for candidate 98f9ec83"),
        ("adjudicate.py", "code", "fresh order-relative checker + controls; re-runnable on the pins"),
        ("snapshot.py", "code", "pin/snapshot step"),
    ]:
        ev.append({
            "event_id": f"w066-f2b-r12-01-artifact-{name.replace('.', '-').lower()}", "event_type": "artifact",
            "created_at": t, "actor": "worker-066", "node_id": NODE, "artifact_type": atype,
            "path": f"artifacts/worker-066/f2b_containment_adjudication/{name}", "sha256": h[name],
            "validation_status": "unverified", "task_id": TASK, "class_ids": [CLASS, "AF-SCC-C2-VAC-GEN"],
            "note": note,
        })
    ev.append({
        "event_id": "w066-f2b-r12-01-review-c0", "event_type": "review", "created_at": t, "actor": "worker-066",
        "reviewer": "worker-066", "node_id": NODE, "class_id": CLASS,
        "target_id": f"schemas/af_scc_c0_vacuum.yaml#{C0_SHA}", "reviewed_sha256": C0_SHA,
        "verdict": "revise", "score": 2.5, "task_id": TASK,
        "hard_failures": ["W066-R12-F2B-H1", "W066-R12-F2B-H2"],
        "findings": [
            "W066-R12-F2B-H1 [hard] implication_ledger.forbidden_transfers[0].reason (line 245) says 'C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker'. The file's own chain at implication_ledger.extension_class_containment (line 238) is E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2, so E_C2 is the strictly SMALLEST extension set; the clause's conclusion is correct under the chain but its premise token is inverted, so the stated reason does not support the transfer prohibition as written. Byte-identical to rev11 1bb78ce9:251 (carried over, not introduced by rev12).",
            "W066-R12-F2B-H2 [hard] regularity.must_not_conflate[0] (line 151) states 'No containment with C2 or C0 is asserted here' in a file that asserts exactly that containment at :238, :242-243 and :274, and whose sibling C2@5476a3f2 rev12 replaced the same sentence with the nesting statement and recorded the earlier wording as wrong ('[R2 major: the earlier \\'no containment with C2 is asserted\\' was wrong]'). The preceding curvature-vs-differentiability clause does not scope the denial; rescue reading tested and rejected in evidence/checks.json (c0_denial_rescue_reading). Byte-identical denial clause at rev11 1bb78ce9:157.",
            "Machine-green at the same bytes (not blocking): 0 duplicate YAML mapping keys in C0 and C2; C0/C2 declared chains agree; f0_binding declared_f0_sha256 equals the live declared-F0 taxonomy 0abb9ed8a961; class_contract_pointer resolves in classes.AF-SCC-C0-VAC-GEN; FROZEN rev28 declares exactly the measured C0/C2 hashes. The sibling C2 passes the same checker, so the finding is not a blanket containment mention.",
            "Resolution: owner publishes an equivalent 2-edit repair (candidate 98f9ec83 semantics: 'strictly smaller extension class' + nesting statement), bumps revision, mirrors byte-identically, re-freezes and re-runs a containment check to PASS with C2 unchanged; alternatively a reviewer may rule the two clauses non-normative at the bound hash, which this adjudication does not. This verdict binds 55d0a1ea only and is void on any hash move.",
        ],
        "evidence_refs": report["evidence_refs"],
    })
    ev.append({
        "event_id": "w066-f2b-r12-01-claim", "event_type": "claim", "created_at": t, "actor": "worker-066",
        "node_id": NODE, "class_id": CLASS, "class_ids": [CLASS, "AF-SCC-C2-VAC-GEN"],
        "conclusion_type": "formal_model", "task_id": TASK,
        "statement": "At the FROZEN rev27/28 pins schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda and schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc, an independent order-relative checker written from scratch reproduces both text-level containment inconsistencies claimed by worker-008 on C0 (H1 inverted size premise at :245, H2 live containment denial at :151) and confirms the sibling asymmetry: C2 rev12 at the corresponding must_not_conflate entry carries the corrected nesting wording and marks the earlier denial wrong, while C0 does not. Both C0 clauses are byte-identical to the superseded rev11 bytes 1bb78ce9 (lines 251/157), so the rev12 rework carried them over rather than introducing them. Worker-008's candidate 98f9ec83c487 changes exactly the two named leaf paths, leaves class_id/revision/f0_binding/pointers/revision_history byte-equal, and clears both defects; reverting either single edit fires exactly its own finding. All seven pre-registered controls match. Reviewer verdict: revise 2.5. This is a machine-checker and text-consistency result, not a claim about the mathematics of C0/C2 inextendibility.",
        "assumptions": [
            "a verdict binds bytes, not paths; every check ran on pinned copies",
            "the document's own implication_ledger.extension_class_containment sentence is the reference order; the order is not re-derived from the physics",
            "'extension class' refers to the extension set E_X as the document itself defines it; no competing definition exists in the file",
            "the sibling C2 rev12 correction is evidence of intended wording, not authority for C0 content",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": report["evidence_refs"],
        "artifact_refs": [f"artifacts/worker-066/f2b_containment_adjudication/report.json#{h['report.json'][:12]}",
                          f"artifacts/worker-066/f2b_containment_adjudication/README.md#{h['README.md'][:12]}"],
    })
    ev.append({
        "event_id": "w066-f2b-r12-01-blocker-f2b", "event_type": "blocker", "created_at": t, "actor": "worker-066",
        "node_id": NODE, "class_id": CLASS, "class_ids": [CLASS, "AF-SCC-C2-VAC-GEN"], "task_id": TASK,
        "description": "F2b at the FROZEN rev27/28 pin 55d0a1ea still carries two live containment inconsistencies with its own declared chain (:245 inverted size premise, :151 containment denial), independently reproduced here; both clauses are byte-identical to the superseded rev11 bytes, so they are carried over. G-FORM cannot accept F2b at this hash while they stand.",
        "needed_to_unblock": "lead-formulation: publish an equivalent 2-edit repair (candidate 98f9ec83 semantics), bump revision, publish the mirror byte-identically, re-freeze; re-run adjudicate.py/containment checker to PASS with C2 5476a3f2 unchanged. lead-audit/reviewer: dispose of the finding in the G-FORM r2 corpus at the frozen hash (or rule the two clauses non-normative, with reasons).",
        "evidence_refs": report["evidence_refs"],
        "stop_rule": "repair + re-freeze + independent re-run to PASS, or a hash-bound reviewer ruling that the clauses are non-normative prose",
    })
    ev.append({
        "event_id": "w066-f2b-r12-01-status-complete", "event_type": "status", "created_at": t,
        "actor": "worker-066", "node_id": NODE, "class_id": CLASS,
        "class_ids": [CLASS, "AF-SCC-C2-VAC-GEN"], "status": "active", "hours": 0.7, "task_id": TASK,
        "summary": "W066-REV12-F2B-CONTAINMENT-ADJUDICATION-01 complete as a bounded worker lifecycle: worker-008's rev12 dual-defect claim independently CONFIRMED at 55d0a1ea (verdict revise 2.5, 2 hard findings), sibling C2 passes, candidate 98f9ec83 verified minimal and PASS, 7/7 pre-registered controls matched, provenance measured against rev11. All eight artifacts exist on disk and are hash-pinned; events are schema-validated. This is a completion claim, not a node/gate transition. Checkpoint follows.",
        "evidence_refs": [f"artifacts/worker-066/f2b_containment_adjudication/report.json#{h['report.json'][:12]}",
                          f"artifacts/worker-066/f2b_containment_adjudication/evidence/controls.json#{h['controls.json'][:12]}",
                          f"schemas/af_scc_c0_vacuum.yaml#{C0_SHA[:12]}"],
        "next_falsifier": report["falsifier"],
    })

    # validate then append, skipping ids already emitted
    existing = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    appended = 0
    with OUT.open("a", encoding="utf-8") as fh:
        for e in ev:
            validate_event(e)  # controller validator: all 13 event types
            if e["event_type"] in JSONSCHEMA_TYPES:  # draft schema covers the typed subset
                jsonschema.validate(e, SCHEMA)
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1
    print(json.dumps({"validated": len(ev), "appended": appended, "outbox": str(OUT.relative_to(REPO)),
                      "artifact_hashes": h}, indent=1))


if __name__ == "__main__":
    main()
