#!/usr/bin/env python3
"""W071-F1-HF071R3-DISPOSITION-01 event emitter (fail-closed).

Validates every event against research_map/schemas.py before appending one JSON object
per line to comms/outbox/worker-071.jsonl.  Nothing is written if any event fails
validation.  Worker events only: no gate verdict, node status=done, or
validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat()
OUT = ROOT / "comms" / "outbox" / "worker-071.jsonl"


def sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


BASE = {"task_id": "W071-F1-HF071R3-DISPOSITION-01", "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM"}

FILES = {
    "prereg": ("artifacts/worker-071/f1_hf071r3_disposition/PREREGISTRATION.json", "preregistration"),
    "instrument": ("artifacts/worker-071/f1_hf071r3_disposition/dispose_f1_hf071r3.py", "verification_instrument"),
    "disposition": ("artifacts/worker-071/f1_hf071r3_disposition/disposition.json", "disposition_record"),
    "report": ("artifacts/worker-071/f1_hf071r3_disposition/report.json", "report"),
    "readme": ("artifacts/worker-071/f1_hf071r3_disposition/README.md", "summary"),
    "sums": ("artifacts/worker-071/f1_hf071r3_disposition/SHA256SUMS", "manifest"),
    "emitter": ("artifacts/worker-071/f1_hf071r3_disposition/emit_events.py", "emitter"),
}

DISP = json.loads((ROOT / FILES["disposition"][0]).read_text())
CORE = DISP["core_digest"]
REF = {
    "f1": "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
    "review": "reviews/F1-review-rev29-worker-071.json#1bddd000638d",
    "sem": "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
    "suite": "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b",
    "report": "artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c8208d3",
    "rec41": "runtime/state/controller_verification/astra-lifecycle-08-decisions.json#REC-41",
    "candg": "artifacts/worker-029/f1_r03_scope_safety/variants/CAND-A__G_grouped_correct.yaml#0d2525d9c15f",
    "disposition": "artifacts/worker-071/f1_hf071r3_disposition/disposition.json#" + sha(FILES["disposition"][0])[:12],
    "report_artifact": "artifacts/worker-071/f1_hf071r3_disposition/report.json#" + sha(FILES["report"][0])[:12],
    "checkpoint": "runtime/state/worker-071_f1_hf071r3_disposition_checkpoint.json",
}

EVENTS = []
for key, (path, atype) in FILES.items():
    EVENTS.append({
        "event_id": f"w071-hf071r3-20260912T0126-artifact-{key}",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-071", **BASE,
        "artifact_type": atype, "path": path, "sha256": sha(path),
        "bytes": (ROOT / path).stat().st_size, "validation_status": "unverified",
        "note": "W071-F1-HF071R3-DISPOSITION-01 deliverable; worker-level, no promotion.",
        "evidence_refs": [REF["disposition"], REF["report_artifact"]],
    })

EVENTS.append({
    "event_id": "w071-hf071r3-20260912T0126-claim",
    "event_type": "claim", "created_at": NOW, "actor": "worker-071", **BASE,
    "class_ids": ["AF-WCC-VAC-GEN"], "conclusion_type": "formal_model",
    "statement": (
        "At the pinned bytes (F1 schema d9cebb9404b2; stage-B auditor c79d8ab8440a), the recorded hard "
        "failure HF-071R3-01 is a literal binder-notation miss of exactly one ordered binder, '(q,t0)': that "
        "string is absent from quantifiers.formal, which renders the same not-exists quantifier variable-wise "
        "('not exists q in I+ and t0 in [0,T)'). Under a canonical-tuple-aware containment reading all six "
        "binders match, and the auditor's R03 failure detail contains no other reason, so R03 passes. This "
        "agrees with controller REC-41 (the literal-substring binder is the defect; the fix is assigned to "
        "worker-006 and had not landed at measurement time, auditor hash unchanged). HF-071R3-01 is therefore "
        "INSTRUMENT_SIDE_CONFIRMED at the schema level, with residuals: (a) the stage-B fix plus pipeline re-run, "
        "or a rev14 rendering that carries the literal (worker-029 CAND-A__G does); (b) the pinned acceptance "
        "report 9b7d6c82 has no input schema hash and predates rev12, so it cannot certify the frozen bytes. "
        "HF-071R3-02 is LIVE_UNCHANGED: 25/25 falsifier rows bind rev12 cce9c60146d6, 0 bind the reviewed "
        "d9cebb9404b2, and F1-AMB-25 expects the superseded F0 276009f4f63d. History: rev11 9a8bd4c9 accepts "
        "under the same auditor; rev12 introduced the tuple binder. This is a reviewer-side disposition of its "
        "own recorded hard failures; it changes no verdict, gate, node status or canonical byte."),
    "assumptions": [
        "All pinned inputs were stable across the run (frame t0==t1, moved_during_run=[]); any later write to a pinned path voids the measurement at that path.",
        "The stage-B auditor is the declared semantic stage of the canonical two-stage acceptance pipeline; it is invoked as a subprocess exactly as run_acceptance.py invokes it.",
        "The canonical-tuple-aware predicate is a reading of R03's own text ('quantifiers.formal is a single sentence using those binders'): each component of a parenthesised tuple binder occurs in the formal sentence in tuple order.",
        "No project module is imported by the measurement instrument; predicates are independently re-implemented from the pinned rule text.",
        "Worker events cannot set a gate verdict, node status=done, or validation_status=passed; the recorded review verdict is not edited."
    ],
    "falsifier": (
        "Re-run the pinned auditor on the pinned F1 bytes: an accept or R03-pass falsifies INSTRUMENT_SIDE_CONFIRMED "
        "(it becomes CLOSED_BY_FIX); any R03 failure reason other than the literal containment miss makes it "
        "SCHEMA_SIDE_RESIDUAL; a suite re-issue binding all 25 rows to the then-live F1 pin falsifies LIVE_UNCHANGED."),
    "evidence_refs": [REF["f1"], REF["review"], REF["sem"], REF["suite"], REF["report"], REF["rec41"],
                      REF["candg"], REF["disposition"], REF["report_artifact"]],
    "artifact_refs": [REF["disposition"], REF["report_artifact"]],
    "next_falsifier": "Re-run dispose_f1_hf071r3.py against the fixed stage-B auditor (astra-life08-stageb-r03) or the landed rev14 F1.",
})

EVENTS.append({
    "event_id": "w071-hf071r3-20260912T0126-blocker-residuals",
    "event_type": "blocker", "created_at": NOW, "actor": "worker-071", **BASE,
    "description": (
        "Residuals recorded by the HF-071R3 disposition, all already inside controller scope: (1) stage-B R03 "
        "literal-substring binder still rejects the pinned F1 bytes; astra-life08-stageb-r03 (worker-006) had not "
        "landed at measurement time (auditor c79d8ab8440a unchanged) and the literal-bearing remedy exists only as "
        "worker-029 CAND-A__G, not as canonical bytes; (2) acceptance_pipeline_report.json 9b7d6c82 has no input "
        "schema sha256 and predates F1 rev12, so the frozen schema cannot cite a passing canonical acceptance at "
        "its own hash; (3) HF-071R3-02: 25/25 falsifier rows bind rev12 cce9c60146d6, 0 bind d9cebb9404b2, and "
        "F1-AMB-25 expects superseded F0 276009f4f63d. This blocker records measurement state; it asks for no "
        "duplicate work and moves no gate."),
    "needed_to_unblock": (
        "Lead-formulation: land rev14 with the suite rebind (REC-36 item 6) and either a literal-bearing R03 "
        "rendering or the instrument fix; worker-006: land astra-life08-stageb-r03 and re-run the two-stage "
        "pipeline; lead-audit (astra-life05-verify-gform-r3): cite this disposition when binding F1 verdicts."),
    "evidence_refs": [REF["f1"], REF["sem"], REF["suite"], REF["report"], REF["rec41"], REF["disposition"]],
})

EVENTS.append({
    "event_id": "w071-hf071r3-20260912T0126-status",
    "event_type": "status", "created_at": NOW, "actor": "worker-071", **BASE,
    "status": "active", "hours": 0.6,
    "summary": (
        "One bounded class-bound task complete at worker level: W071-F1-HF071R3-DISPOSITION-01 (F1 / "
        "AF-WCC-VAC-GEN / G-FORM), successor to the already-blocked rev27 card and to worker-068's open item. "
        "Read-only disposition of the two hard failures recorded in reviews/F1-review-rev29-worker-071.json: "
        "HF-071R3-01 = INSTRUMENT_SIDE_CONFIRMED (single literal tuple-binder miss; tuple-aware R03 passes; "
        "agrees with REC-41; fix not landed), HF-071R3-02 = LIVE_UNCHANGED (25/25 rows bind rev12 cce9c60146d6), "
        "acceptance report staleness LIVE. 9/9 checks, 7/7 controls, 0 pin drift, core_digest " + CORE +
        ". No gate verdict, node status or validation_status set; recorded verdict unchanged; exiting for recycling."),
    "evidence_refs": [REF["f1"], REF["review"], REF["sem"], REF["suite"], REF["report"], REF["rec41"],
                      REF["disposition"], REF["report_artifact"]],
    "next_falsifier": (
        "Re-run dispose_f1_hf071r3.py after the fixed stage-B auditor or the landed rev14 F1; if the fixed "
        "pipeline still rejects the landed schema on non-literal grounds, the residual is schema-side and rev14 "
        "must cover it. A suite re-issue binding all 25 rows to the live F1 pin closes HF-071R3-02."),
    "do_not_claim": "No gate verdict, no node completion, no validated artifact; worker evidence only.",
})

for ev in EVENTS:
    validate_event(ev)

with OUT.open("a", encoding="utf-8") as f:
    for ev in EVENTS:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")

print(json.dumps({"appended": len(EVENTS), "out": str(OUT.relative_to(ROOT)),
                  "event_ids": [e["event_id"] for e in EVENTS]}, indent=1))
