#!/usr/bin/env python3
"""Emit W077-F1-ANCHORBIND-01 events + checkpoint (append-only, schema-validated).

Reads the frozen report, re-validates every event against research_map/schemas.py,
appends to comms/outbox/worker-077.jsonl, and writes checkpoint 4.
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-077/f1_anchor_bind"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TS = datetime.now(TZ).isoformat(timespec="seconds")
TAG = "w077-f1anchor-" + datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
LIFECYCLE = "worker-077-20260912T005105-968807"
TASK_ID = "W077-F1-ANCHORBIND-01"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


report = json.loads((OUT / "report.json").read_text())
pins = report["pins"]
verdict = report["verdict"]
checks = {c["id"]: c for c in report["checks"]}

paths = {
    "report": "artifacts/worker-077/f1_anchor_bind/report.json",
    "instrument": "artifacts/worker-077/f1_anchor_bind/check_f1_anchor_bind.py",
    "readme": "artifacts/worker-077/f1_anchor_bind/README.md",
    "determinism": "artifacts/worker-077/f1_anchor_bind/determinism.json",
}
hashes = {k: sha(p) for k, p in paths.items()}

entry = {
    "task_id": TASK_ID,
    "inputs": {rel: v["sha256"] for rel, v in pins.items()},
    "outputs": hashes,
}
(OUT / "entry_hashes.json").write_text(json.dumps(entry, indent=1, sort_keys=True) + "\n")
hashes["entry_hashes"] = sha("artifacts/worker-077/f1_anchor_bind/entry_hashes.json")
paths["entry_hashes"] = "artifacts/worker-077/f1_anchor_bind/entry_hashes.json"

evidence = [f"{rel}#sha256:{v['sha256']}" for rel, v in sorted(pins.items())]
evidence += [f"{paths[k]}#sha256:{hashes[k]}" for k in
             ("report", "instrument", "readme", "determinism")]
artifact_refs = [f"{paths[k]}#sha256:{hashes[k]}" for k in ("report", "instrument", "readme")]

f_hard = ", ".join(verdict["hard_failures"])
summary_ruling = (
    "Ruling (worker-level, unverified): at F1 rev29/rev13 sha256 d9cebb9404b2 (FROZEN revision 29), "
    "all 5 declared provenance anchor concepts are identifier-null and unresolved while their "
    "needed_for fields are load-bearing; the four BL-11 items (s>5/2, delta in (1/2,1), positive mass, "
    "predictability) have 0 hits in ledger a1674f09 and citation audit 315c1914, with positive control "
    "'cauchy horizon' at 61/58; A-WSOBOLEV and A-POSMASS have 0 candidate sources in the pinned audit; "
    "SRC-096/SRC-097 are registered but carry no L0 entry; schemas/f1_falsifier_tests.jsonl binds the "
    "superseded rev28 hash on 25/25 rows. Hard: " + f_hard + ". The per-field anchor table is the "
    "deliverable BL-11 asked for. No canonical write, no node status, no gate verdict."
)

events = [
    {
        "event_id": f"{TAG}-status-claim",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "status": "active",
        "hours": 0.5,
        "summary": (
            "No assignment card exists in comms/inbox/worker-077.jsonl (fleet launched 00:51). Took ONE "
            "bounded class-bound task: " + TASK_ID + " = independent field-level anchor-binding census "
            "for AF-WCC-VAC-GEN at the live F1 rev29 bytes, responsive to literature blocker BL-11 "
            "(lit-l7-20260912-007), which asks which schema field each anchor binds. Read-only declared "
            "checker, 10 checks, 7 controls, two-run content determinism, pins stable in-run."
        ),
        "evidence_refs": evidence,
        "next_falsifier": verdict["falsifier"],
    },
    {
        "event_id": f"{TAG}-artifact-report",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "artifact_type": "anchor_binding_census",
        "path": paths["report"],
        "sha256": hashes["report"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": evidence,
        "note": ("Machine report: 10 checks (8 PASS / 2 FAIL), 7/7 controls, 5/5 identifier-null anchors, "
                 "per-field binding table with one unique recovery (quantifiers D2 -> quantifiers.domains.D2), "
                 "BL-11 zero-hit reproduction, registered-unbound sources, suite-binding drift, verdict with "
                 "falsifier and non-claims."),
    },
    {
        "event_id": f"{TAG}-artifact-instrument",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "artifact_type": "verifier",
        "path": paths["instrument"],
        "sha256": hashes["instrument"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
        "note": ("Deterministic, stdlib+PyYAML only, read-only against all canonical paths; strict "
                 "duplicate-key loader; fail-closed pin and control handling; exit 0 iff instrument ok, "
                 "pins stable and no drift."),
    },
    {
        "event_id": f"{TAG}-artifact-readme",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "artifact_type": "report",
        "path": paths["readme"],
        "sha256": hashes["readme"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
        "note": "Method, pin table, per-field anchor table, findings with falsifiers, non-claims, re-run command.",
    },
    {
        "event_id": f"{TAG}-artifact-determinism",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "artifact_type": "determinism_record",
        "path": paths["determinism"],
        "sha256": hashes["determinism"],
        "validation_status": "unverified",
        "task_id": TASK_ID,
        "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
        "note": ("Two-run comparison: content digest excluding the moving FROZEN manifest is identical; "
                 "only created_at and the rewrite mtime of taxonomy_consistency.json vary; FROZEN manifest "
                 "observed at 815e0807 (revision 29) in both runs."),
    },
    {
        "event_id": f"{TAG}-claim",
        "event_type": "claim",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "conclusion_type": "formal_model",
        "statement": (
            "At pins schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2 (FROZEN revision 29), "
            "ledger/theorems.jsonl#sha256:a1674f094979, ledger/citation_audit.csv#sha256:315c19145065 and "
            "schemas/f1_falsifier_tests.jsonl#sha256:56bcb4b3234b: (1) F1 provenance declares 5 anchor "
            "concepts, all with identifier=null and status=unresolved, and their needed_for field bindings "
            "resolve (1 via unique recovery quantifiers.domains.D2); (2) the four BL-11 anchor items have 0 "
            "lexical hits in the pinned ledger and citation audit while positive control 'cauchy horizon' has "
            "61/58; (3) A-WSOBOLEV and A-POSMASS have 0 candidate sources in the pinned citation audit; "
            "(4) SRC-096 and SRC-097 are registered but absent from all ledger source_ids with empty "
            "used_by_theorems; (5) all 25 rows of the declared F1 falsifier suite bind the superseded rev28 "
            "hash cce9c60146d6, none the live rev29 hash. This is an artifact-and-checker measurement, not a "
            "mathematical or physics claim."
        ),
        "assumptions": [
            "A provenance.sources row with identifier=null is an unanchored obligation, not a satisfied anchor.",
            "Lexical zero hits in the pinned corpus mean no registered L1 source anchors the concept; they do not mean no such source exists in the literature.",
            "The needed_for field map is the schema author's declared binding; this census verifies it resolves, not that it is the right binding.",
            "The census is void if any pinned input drifts.",
        ],
        "falsifier": verdict["falsifier"],
        "evidence_refs": evidence,
        "artifact_refs": artifact_refs,
    },
    {
        "event_id": f"{TAG}-review",
        "event_type": "review",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "target_id": "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2",
        "reviewer": "worker-077",
        "verdict": "revise",
        "score": 2.5,
        "counts_as_full_schema_verdict": False,
        "hard_failures": verdict["hard_failures"],
        "findings": [
            {"id": "W077-AB-01", "severity": "major", "type": "unanchored_schema_obligation",
             "finding": "5/5 F1 provenance anchor rows carry identifier=null and status=unresolved while their needed_for fields are load-bearing.",
             "falsifier": "any anchor row at the live hash with a non-null, resolved identifier."},
            {"id": "W077-AB-02", "severity": "major", "type": "no_registered_l1_anchor",
             "finding": "The four BL-11 anchor items have 0 hits in ledger a1674f09 and citation audit 315c1914 (positive control 61/58); A-WSOBOLEV and A-POSMASS have 0 candidate sources.",
             "falsifier": "a lexical variant of any BL-11 item present in the pinned ledger or citation audit."},
            {"id": "W077-AB-03", "severity": "minor", "type": "stale_falsifier_suite_binding",
             "finding": "schemas/f1_falsifier_tests.jsonl binds rev28 cce9c60146d6 on 25/25 rows; 0 rows bind the live rev29 hash.",
             "falsifier": "a suite row binding the live F1 hash."},
            {"id": "W077-AB-04", "severity": "minor", "type": "imprecise_field_binding_token",
             "finding": "needed_for token 'quantifiers D2' is not a resolvable YAML path; unique recovery is quantifiers.domains.D2.",
             "falsifier": "a second same-name leaf under quantifiers."},
        ],
        "evidence_refs": evidence,
    },
    {
        "event_id": f"{TAG}-blocker",
        "event_type": "blocker",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "description": (
            "G-FORM evidence gap for AF-WCC-VAC-GEN at rev29: F1's declared anchor obligations are all "
            "unresolved and four of five have no registered source in the frozen L1 corpus, so either the "
            "anchors must be supplied (new or already-registered primary sources, per BL-11) or the dependent "
            "fields (weighted Sobolev data class, adm_mass sign, predictability equivalence) must be withdrawn. "
            "Additionally the declared F1 falsifier suite is stale against rev29 on 25/25 rows."
        ),
        "needed_to_unblock": (
            "Formulation: populate provenance.sources[*].identifier with the per-field anchor (or record the "
            "field withdrawal) and refresh the 'quantifiers D2' token to quantifiers.domains.D2. Literature: "
            "give SRC-096/SRC-097 L0 entries or register primary sources for weighted Sobolev / positive mass. "
            "Suite owner: re-bind schemas/f1_falsifier_tests.jsonl to the live F1 hash after the schema stops moving."
        ),
        "evidence_refs": evidence,
        "next_falsifier": verdict["falsifier"],
    },
    {
        "event_id": f"{TAG}-status-complete",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-077",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
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
    "checkpoint": 4,
    "at": TS,
    "worker": "worker-077",
    "agent_id": "worker-077",
    "lifecycle": LIFECYCLE,
    "role": "bounded execution worker",
    "task": {
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "artifact": paths["report"],
        "hours_spent_estimate": 0.5,
        "assignment_event": None,
        "origin": "immediate queue; responsive to lit-l7-20260912-007 (BL-11)",
        "verdict": verdict["verdict"],
        "hard_failures": verdict["hard_failures"],
    },
    "inputs_measured": {rel: v["sha256"] for rel, v in pins.items()},
    "freeze_manifest_revision": report["frozen"]["revision"],
    "artifacts": hashes,
    "checks": {c["id"]: c["status"] for c in report["checks"]},
    "controls_ok": all(c["ok"] for c in report["controls"]),
    "drift_in_run": checks["C10-no-drift"]["detail"]["drifted"],
    "authority": ("worker events cannot set node status=done, validation_status=passed, or any gate "
                  "verdict; no canonical path was written"),
    "next_falsifier": verdict["falsifier"],
}
(ROOT / "runtime/state/w077_checkpoint_4.json").write_text(
    json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with (ROOT / "runtime/state/w077_checkpoints.jsonl").open("a") as f:
    f.write(json.dumps(checkpoint, sort_keys=True) + "\n")
(OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

print(json.dumps({"emitted_events": len(events), "tag": TAG,
                  "checkpoint": "runtime/state/w077_checkpoint_4.json",
                  "artifacts": hashes}, indent=1))
