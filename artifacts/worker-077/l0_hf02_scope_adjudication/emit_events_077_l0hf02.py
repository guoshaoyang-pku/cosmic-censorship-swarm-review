#!/usr/bin/env python3
"""Emit W077-L0-HF02-SCOPE-01 events + checkpoint (append-only, schema-validated)."""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-077/l0_hf02_scope_adjudication"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TS = datetime.now(TZ).isoformat(timespec="seconds")
TAG = "w077-l0hf02-" + datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
LIFECYCLE = "worker-077-20260912T004218-968807"
TASK_ID = "W077-L0-HF02-SCOPE-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


report = json.loads((OUT / "report.json").read_text())
pins = report["pins"]
verdict = report["verdict"]
sc = [c for c in report["checks"] if c["id"] == "S-C-substantive-recheck"][0]

paths = {
    "report": "artifacts/worker-077/l0_hf02_scope_adjudication/report.json",
    "harness": "artifacts/worker-077/l0_hf02_scope_adjudication/adjudicate_hf02_scope.py",
    "readme": "artifacts/worker-077/l0_hf02_scope_adjudication/README.md",
}
hashes = {k: sha(p) for k, p in paths.items()}
entry = json.loads((OUT / "entry_hashes.json").read_text())
entry["outputs"] = hashes
(OUT / "entry_hashes.json").write_text(json.dumps(entry, indent=1, sort_keys=True) + "\n")

evidence = [
    f"ledger/theorems.jsonl#sha256:{pins['ledger/theorems.jsonl']}",
    f"evaluation_rubric.yaml#sha256:{pins['evaluation_rubric.yaml']}",
    f"comms/PROTOCOL.md#sha256:{pins['comms/PROTOCOL.md']}",
    f"research_map/formulation_taxonomy.yaml#sha256:{pins['research_map/formulation_taxonomy.yaml']}",
    f"artifacts/audit/audit_run.py#sha256:{pins['artifacts/audit/audit_run.py']}",
    f"artifacts/audit/audit_lib.py#sha256:{pins['artifacts/audit/audit_lib.py']}",
    f"artifacts/literature/tools/build_literature.py#sha256:{pins['artifacts/literature/tools/build_literature.py']}",
    f"{paths['report']}#sha256:{hashes['report']}",
    f"{paths['harness']}#sha256:{hashes['harness']}",
]
artifacts_refs = [f"{paths['report']}#sha256:{hashes['report']}",
                  f"{paths['harness']}#sha256:{hashes['harness']}",
                  f"{paths['readme']}#sha256:{hashes['readme']}"]

summary_ruling = (
    "Ruling: A0 HF-02's disjunction branch operates on the singular claim field class_id "
    "(metric 'claims whose class_id is ... singular'; guard G1; canonical check_class_binding; "
    "ledger rows routed to records; ledger-scoped HF-02 branch = invented-token membership only; "
    "builder contract makes class_ids a designed list restricted to the four frozen classes). "
    "Applied to ledger rows' plural class_ids it is out of scope, so W097-L0R3-F1 is VOID ON ITS "
    "STATED BASIS (worker-097's own declared void-condition). Substantive recheck of all 8 rows: "
    "0/8 merged-regularity, 0/8 non-frozen token, 4 intermediate-regularity relations, "
    "2 intermediate-regularity definitions, 2 shared antecedents. Residual is taxonomy coverage / "
    "ledger schema, not content. No gate verdict, no ledger write."
)

events = [
    {
        "event_id": f"{TAG}-status-claim",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "No assignment card exists in comms/inbox for worker-077 (fleet launched 00:42). Taking "
            "ONE bounded class-bound task: " + TASK_ID + " = independent scope adjudication of A0 HF-02 "
            "'disjunction of class_ids' as applied by W097-L0R3-F1 to 8 ledger rows at ledger sha "
            "a1674f094979. Output: read-only deterministic harness, report, and a scope ruling. "
            "Does not accept L0 and issues no gate verdict."
        ),
        "evidence_refs": evidence,
        "next_falsifier": verdict["falsifier"],
    },
    {
        "event_id": f"{TAG}-artifact-report",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "artifact_type": "adjudication_report",
        "path": paths["report"],
        "sha256": hashes["report"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": evidence,
        "note": ("Full check tree S-A..S-E, 5 mutation/oracle controls, determinism digests, T0/T1 pin "
                 "drift, and the verdict with its falsifier and non-claims."),
    },
    {
        "event_id": f"{TAG}-artifact-harness",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "artifact_type": "verifier",
        "path": paths["harness"],
        "sha256": hashes["harness"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
        "note": "Deterministic, stdlib+PyYAML only, read-only against all canonical paths; exit 0 iff instrument ok and no drift.",
    },
    {
        "event_id": f"{TAG}-artifact-readme",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "artifact_type": "report",
        "path": paths["readme"],
        "sha256": hashes["readme"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
        "note": "Method, result table, reproduction command, falsifier, and the honest rubric-phrase tension.",
    },
    {
        "event_id": f"{TAG}-claim",
        "event_type": "claim",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "class_ids": CLASS_IDS,
        "conclusion_type": "formal_model",
        "statement": (
            "At ledger/theorems.jsonl sha256 a1674f094979 and evaluation_rubric.yaml sha256 "
            + pins["evaluation_rubric.yaml"] + ", the A0 HF-02 'disjunction of class_ids' branch is "
            "claim-scoped in operation (class_binding metric over singular class_id; guard G1; "
            "audit_lib.check_class_binding reads claim.get('class_id') only; audit_run.py routes "
            "ledger rows to records and implements only invented-token membership for them; "
            "build_literature.py designs class_ids as a list restricted to the four frozen classes). "
            "The 8-row finding W097-L0R3-F1 is therefore void on its stated basis. Independent "
            "substantive recheck of the 8 rows: 0/8 match the G3 merged-regularity pattern, 0/8 carry "
            "a non-frozen class token, and each binding is a definite intermediate-regularity "
            "relation/definition or a shared Kerr-stability antecedent."
        ),
        "assumptions": [
            "The frozen rubric text and the canonical audit implementation define HF-02's operational scope.",
            "A ledger row is a record, not a claim; its plural class_ids is a designed scope list, not a disjunction.",
            "The G3 merged-regularity regex is copied from artifacts/worker-01/validate_taxonomy.py, not re-derived.",
            "The ruling is void if any pinned input drifts during the run.",
        ],
        "falsifier": verdict["falsifier"],
        "evidence_refs": evidence,
        "artifact_refs": artifacts_refs,
    },
    {
        "event_id": f"{TAG}-status-complete",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "GLOBAL",
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.5,
        "summary": "TASK COMPLETE (unverified, worker-level): " + summary_ruling,
        "evidence_refs": evidence,
        "next_falsifier": verdict["falsifier"],
    },
]

for e in events:
    validate_event(e)

outbox = ROOT / "comms/outbox/worker-077.jsonl"
with outbox.open("a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

checkpoint = {
    "checkpoint": 3,
    "at": TS,
    "worker": "worker-077",
    "agent_id": "worker-077",
    "lifecycle": LIFECYCLE,
    "path": "runtime/state/w077_checkpoint_3.json",
    "role": "bounded execution worker",
    "task": {
        "task_id": TASK_ID,
        "node_id": "L0",
        "gate": "G-LIT",
        "scope_token": "GLOBAL",
        "class_ids_in_scope": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "artifact": paths["report"],
        "hours_spent_estimate": 0.5,
        "assignment_event": None,
        "target_finding": "W097-L0R3-F1",
        "disposition": "void_on_stated_basis",
    },
    "inputs_measured": pins,
    "freeze_drift_during_task": bool(report["input_drift"]),
    "artifacts": {v: hashes[k] for k, v in paths.items()},
    "instrument_results": {
        "instrument_ok": report["instrument_ok"],
        "checks_passed": sum(1 for c in report["checks"] if c.get("pass")),
        "checks_total": len(report["checks"]),
        "controls_passed": sum(1 for c in report["controls"] if c["pass"]),
        "controls_total": len(report["controls"]),
        "determinism": report["determinism"]["equal"],
        "rows_classified": sc["classification_counts"],
        "merged_regularity_rows": sc["merged_regularity_rows"],
        "non_frozen_token_rows": sc["non_frozen_class_token_rows"],
    },
    "verdict": {
        "ruling": "HF-02 disjunction branch is claim-scoped; W097-L0R3-F1 void on its stated basis",
        "two_readings": verdict["two_readings"],
        "residual": verdict["residual"],
        "falsifier": verdict["falsifier"],
    },
    "events": [e["event_id"] for e in events],
    "next": (
        "Controller/adjudicator: record the scope ruling; if a strict single-class ledger row schema is "
        "wanted, that is a documentation/schema extension, not a hash-moving content repair. L0's "
        "remaining findings (worker-097 F2/F3/F4/F5, worker-093 HF-03) are untouched by this ruling."
    ),
    "authority_note": "worker evidence only; cannot set status=done, validation_status=passed, or a gate verdict",
}

(ROOT / "runtime/state/w077_checkpoint_3.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with (ROOT / "runtime/state/w077_checkpoints.jsonl").open("a") as f:
    f.write(json.dumps({
        "checkpoint": 3, "at": TS, "worker": "worker-077", "lifecycle": LIFECYCLE,
        "path": "runtime/state/w077_checkpoint_3.json",
        "verdict": "scope_ruling", "score": None,
        "events": [e["event_id"] for e in events],
    }, sort_keys=True) + "\n")

print("emitted", len(events), "events; hashes:", json.dumps(hashes, indent=1))
print("checkpoint written: runtime/state/w077_checkpoint_3.json")
