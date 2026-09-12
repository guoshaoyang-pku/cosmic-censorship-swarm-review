#!/usr/bin/env python3
"""W037-F1-VISIBILITY-02 event emitter + checkpoint (worker-037).

Reads the adjudication report, emits schema-valid upward events into
comms/outbox/worker-037.jsonl (append; idempotent by event_id), validates every event
with research_map.schemas.validate_event BEFORE writing, and records a worker-level
checkpoint under runtime/state/.

Authority: worker events cannot set status=done, validation_status=passed, or a gate
verdict. This emitter writes only: artifact, review, blocker, status + a checkpoint.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-037.jsonl"
STATE = ROOT / "runtime" / "state"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

REPORT = OUT / "report.json"
SCRIPT = OUT / "check_f1_visibility.py"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE = "F1"
GATE = "G-FORM"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_parts():
    lt = time.localtime()
    return (time.strftime("%Y%m%dT%H%M%S", lt),
            time.strftime("%Y-%m-%dT%H:%M:%S", lt) + time.strftime("%z", lt))


def main() -> int:
    rep = json.loads(REPORT.read_text())
    rhash = sha256_file(REPORT)
    shash = sha256_file(SCRIPT)
    stamp, created = now_parts()
    f1 = rep["reviewed_f1_sha256"]
    f0 = rep["reviewed_f0_sha256"]
    findings = {f["id"]: f for f in rep["findings"]}

    events = [
        {
            "event_id": f"w037-{stamp}-art-f1-visibility-report",
            "event_type": "artifact", "created_at": created, "actor": "worker-037",
            "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "artifact_type": "verification_report",
            "path": "artifacts/worker-037/f1_visibility_adjudication/report.json",
            "sha256": rhash, "validation_status": "unverified",
            "summary": "Independent adjudication of F1 HF-06 at sha 9a8bd4c96800: "
                       "quantifiers.formal/D5 use whole-curve single-q containment while "
                       "visibility.definition/negation use the tail predicate; formal "
                       "expansion confirmed strictly weaker; gate blind spot measured by "
                       "mutation tests M0-M4.",
            "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#{f1[:12]}",
                              f"artifacts/worker-037/f1_visibility_adjudication/report.json#{rhash[:12]}"],
            "next_falsifier": rep["next_falsifier"],
        },
        {
            "event_id": f"w037-{stamp}-art-f1-visibility-tool",
            "event_type": "artifact", "created_at": created, "actor": "worker-037",
            "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "artifact_type": "verification_tool",
            "path": "artifacts/worker-037/f1_visibility_adjudication/check_f1_visibility.py",
            "sha256": shash, "validation_status": "unverified",
            "summary": "Read-only checker: T0/T1 hash snapshots, predicate-site extraction, "
                       "tests V1-V7, finite-model strictness witness, mutation tests M0-M4 "
                       "against check_class_schema.py. No canonical artifact edited.",
            "evidence_refs": [f"artifacts/worker-037/f1_visibility_adjudication/check_f1_visibility.py#{shash[:12]}"],
        },
        {
            "event_id": f"w037-{stamp}-review-f1-visibility",
            "event_type": "review", "created_at": created, "actor": "worker-037",
            "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "target_id": f"schemas/af_wcc_vacuum.yaml#{f1}",
            "reviewer": "worker-037",
            "verdict": "revise", "score": 2.5,
            "hard_failures": [
                {"id": "W037V2-F1", "severity": "critical",
                 "finding": findings["W037V2-F1"]["statement"]},
                {"id": "W037V2-F2", "severity": "major",
                 "finding": findings["W037V2-F2"]["statement"]},
                {"id": "W037V2-F3", "severity": "major",
                 "finding": findings["W037V2-F3"]["statement"]},
            ],
            "findings": [
                "V1/V2/V6 fail: quantifiers.formal lines 54-55 and D5 lines 79-81 bind the "
                "whole curve; visibility.definition line 220 binds the tail and calls the "
                "whole-curve reading a misclassification (exterior-start / black-hole-end).",
                "V5 fail: formal = not-P_whole, stated negation = P_tail; P_whole => P_tail "
                "strictly (finite-model witness gamma=[a,b], U_q1={b}), so they are not "
                "exact negations and can hold together.",
                "V7 fail: AF_{I+}(M_D) at line 251 is undefined (single occurrence).",
                "Mutations: check_class_schema.py passes on M1 (formal clause inverted to "
                "ASSERT visibility) and M4 (visibility.definition replaced by the forbidden "
                "whole-curve reading); positive control M3 fails; run_acceptance.py exits 0. "
                "The recorded PASS is not agreement evidence.",
                "Repair path is gate-clean: M2 (formal clause repaired to the tail predicate) "
                "passes; the same t0/tail binder must be added to D5, then re-freeze/re-hash.",
            ],
            "evidence_refs": [
                f"artifacts/worker-037/f1_visibility_adjudication/report.json#{rhash[:12]}",
                f"artifacts/worker-037/f1_visibility_adjudication/check_f1_visibility.py#{shash[:12]}",
                f"schemas/af_wcc_vacuum.yaml#{f1[:12]}",
                "schemas/af_wcc_vacuum.yaml:54-55", "schemas/af_wcc_vacuum.yaml:79-81",
                "schemas/af_wcc_vacuum.yaml:220", "schemas/af_wcc_vacuum.yaml:222",
                "schemas/af_wcc_vacuum.yaml:251",
                "artifacts/formulation/tools/check_class_schema.py:285-297",
            ],
            "authority_note": "independent verification evidence; not one of the two required "
                              "accepts and not a gate verdict.",
        },
        {
            "event_id": f"w037-{stamp}-blocker-f1-visibility",
            "event_type": "blocker", "created_at": created, "actor": "worker-037",
            "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "description": "G-FORM accept for F1 is blocked at sha "
                           f"{f1[:12]} by a confirmed content-level defect: quantifiers.formal "
                           "(lines 54-55) and D5 (lines 79-81) use whole-curve single-q "
                           "containment while the canonical predicate (line 220) and its "
                           "negation (line 222) use the tail predicate. The formal expansion is "
                           "strictly weaker than the conclusion it expands; formal and negation "
                           "are not exact negations. The canonical checker is insensitive to "
                           "this class of defect (mutation M1/M4 pass, control M3 fails).",
            "needed_to_unblock": "Owner edit (lead-formulation) to add the t0/tail binder to "
                                 "quantifiers.formal lines 54-55 AND to D5, define or remove "
                                 "AF_{I+}(M_D) at line 251, re-freeze/re-hash, then re-run this "
                                 "checker: V1/V2/V5/V6/V7 must flip to pass. A reviewer rebuttal "
                                 "naming the definitional bridge that makes line 55 the tail "
                                 "predicate falsifies W037V2-F1 instead.",
            "evidence_refs": [
                f"artifacts/worker-037/f1_visibility_adjudication/report.json#{rhash[:12]}",
                f"schemas/af_wcc_vacuum.yaml#{f1[:12]}",
                "schemas/af_wcc_vacuum.yaml:54-55", "schemas/af_wcc_vacuum.yaml:220",
                "schemas/af_wcc_vacuum.yaml:222",
            ],
            "severity": "critical",
            "next_falsifier": rep["next_falsifier"],
        },
        {
            "event_id": f"w037-{stamp}-status-f1-visibility",
            "event_type": "status", "created_at": created, "actor": "worker-037",
            "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
            "status": "active", "hours": 0.2,
            "summary": "Class-bound task W037-F1-VISIBILITY-02 done (worker-037 slot): "
                       "independent adjudication of HF-06 at F1 sha "
                       f"{f1[:12]} / F0 sha {f0[:12]}; T0==T1 (no movement); verdict revise "
                       "with one confirmed critical content-level hard failure and one dangling "
                       "symbol; gate blind spot measured; artifact + events emitted; no "
                       "canonical file edited.",
            "evidence_refs": [
                f"artifacts/worker-037/f1_visibility_adjudication/report.json#{rhash[:12]}",
                f"artifacts/worker-037/f1_visibility_adjudication/check_f1_visibility.py#{shash[:12]}",
                f"schemas/af_wcc_vacuum.yaml#{f1[:12]}",
            ],
            "next_falsifier": rep["next_falsifier"],
        },
    ]

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except ValueError:
                continue
    appended = []
    with OUTBOX.open("a") as f:
        for e in events:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            appended.append(e["event_id"])

    checkpoint = {
        "checkpoint_at": created,
        "worker": "worker-037",
        "task_id": rep["task_id"],
        "class_id": CLASS_ID, "node_id": NODE, "gate": GATE,
        "authority": "worker-level progress record only; not a gate verdict",
        "verdict": rep["worker_verdict"],
        "reviewed_sha256": {NODE: f1, "F0": f0,
                            "authoring_mirror_F1": rep["authoring_mirror_f1_sha256"]},
        "artifacts": {
            "artifacts/worker-037/f1_visibility_adjudication/report.json": rhash,
            "artifacts/worker-037/f1_visibility_adjudication/check_f1_visibility.py": shash,
        },
        "tests": {t["id"]: t["status"] for t in rep["tests"]},
        "mutations": {m["name"]: ("pass" if m["ok"] else "fail") for m in rep["mutations"]},
        "gate_insensitivity_demonstrated": rep["gate_insensitivity_demonstrated"],
        "findings": [{"id": f["id"], "severity": f["severity"]} for f in rep["findings"]],
        "events_emitted": appended,
        "next_falsifier": rep["next_falsifier"],
        "moved_during_check": rep["moved_during_check"],
    }
    cp_path = STATE / f"w037_checkpoint_{stamp}_f1_visibility.json"
    cp_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
    with (STATE / "w037_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

    print(json.dumps({"appended_events": appended,
                      "checkpoint": str(cp_path.relative_to(ROOT)),
                      "report_sha256": rhash, "script_sha256": shash,
                      "validated_events": len(events)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
