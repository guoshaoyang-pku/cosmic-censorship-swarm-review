#!/usr/bin/env python3
"""Emit W090-FCONSEV-REV29-CLOSURE-01 review/claim/status/artifact events + checkpoint.

Validates every event with research_map.schemas.validate_event before appending, so no
event can reach the outbox in a schema-invalid state. Worker-authority only: no
status=done, no validation_status=passed, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ART = Path(__file__).resolve().parent
ROOT = ART.parents[2]
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

TASK = "W090-FCONSEV-REV29-CLOSURE-01"
OUTBOX = ROOT / "comms/outbox/worker-090.jsonl"
STAMP = datetime.now(CST).isoformat(timespec="seconds")
TAG = "w090-fconsev-" + STAMP


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


P = {
    "checker": ART / "check_fconsev_rev29.py",
    "results": ART / "results.json",
    "controls": ART / "controls.json",
    "readme": ART / "README.md",
    "emitter": ART / "emit_events.py",
}
H = {k: sha(v) for k, v in P.items()}
rel = {k: str(v.relative_to(ROOT)) for k, v in P.items()}
R = json.loads(P["results"].read_text())
C = json.loads(P["controls"].read_text())
V = R["verdict"]

REVIEW = {
    "schema": "class-schema-review/v1",
    "review_id": TASK,
    "reviewer": "worker-090",
    "reviewer_role": "bounded execution worker; independent binding audit, not an author of F0/F0R/F1/F2a/F2b or of the rev29 repair",
    "created_at": STAMP,
    "target_id": "F2a",
    "node_id": "F2a",
    "gate": "G-FORM",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "review_scope": "evidence self-binding closure at the post-repair FROZEN rev29 pins: REC-12 item (2) pointer clause, F-CONSEV / W090-R12-01 / W090-F2A-01 embedding clause, sandbox exposure and compensating control. Not a full-schema verdict and not a class-semantics review.",
    "reviewed_pins": R["pins"],
    "frozen_revision": R["frozen_revision"],
    "counts_as_full_schema_verdict": False,
    "verdict": "revise",
    "score": 4.0,
    "hard_failures": [],
    "findings": [
        {"id": "W090-FCONSEV-01", "severity": "minor", "status": "open",
         "finding": "artifacts/formulation/evidence/taxonomy_consistency.json (9e335e9ba1bf) records the two compared paths and consistent=true but contains 0 hex-64 byte-identity witnesses, so the claim does not bind the compared bytes; a change to either tree leaves the file's content unchanged and still matching its declared hash."},
        {"id": "W090-FCONSEV-02", "severity": "minor", "status": "open",
         "finding": "no schema f0_binding hash-pins the supplement side of the comparison: all three carry class_contract_supplement (path) and class_contract_supplement_pointer (key) but no class_contract_supplement_sha256, so the supplement input is resolvable through FROZEN rev29 but not self-bound by the schema."},
        {"id": "W090-FCONSEV-03", "severity": "info", "status": "compensated",
         "finding": "sandbox C2/C3: after a semantic mutation of the compared supplement, every declared f0_binding value still matches while the pinned checker flips to inconsistent; the FROZEN rev29 manifest pin detects the mutation. The residual is therefore minor and compensated only when manifest verification is run."},
        {"id": "W090-F2A-01-CLOSE", "severity": "info", "status": "pointer-clause-closed",
         "finding": "REC-12 item (2) pointer clause is measurably closed at FROZEN rev29: all three declared consistency_evidence_sha256 and declared_f0_sha256 values match live bytes, checked_at not future-stamped, canonical==mirror, 50/50 manifest pins clean. W090-F2A-01 is partially closed; embedding clause open."},
    ],
    "positive_checks": [c["id"] for c in R["checks"] if c["pass"]],
    "negative_checks": [c["id"] for c in R["checks"] if not c["pass"]],
    "checks_total": len(R["checks"]),
    "controls_total": len(C["controls"]),
    "controls_pass": sum(1 for c in C["controls"] if c["pass"]),
    "pin_drift": V["pin_drift"],
    "artifact_refs": [rel["results"], rel["controls"], rel["checker"], rel["readme"]],
    "evidence_refs": [
        f"{rel['results']}#{H['results'][:12]}",
        f"{rel['controls']}#{H['controls'][:12]}",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef",
    ],
    "next_falsifier": "Re-run artifacts/worker-090/fconsev_rev29_closure/check_fconsev_rev29.py at the next stable pins: the embedding clause closes only when the live consistency evidence contains a byte-identity witness for both compared trees (or the schemas hash-pin the supplement) and all A1-A5 checks still pass; any canonical byte change, any A-check failure, or any control not reproducing falsifies this review.",
    "authority_note": "advisory worker review; no gate verdict, no node status, no canonical-file edit",
}
(ROOT / "reviews/F-CONSEV-rev29-closure-090.json").write_text(json.dumps(REVIEW, indent=1) + "\n")
REVIEW_REL = "reviews/F-CONSEV-rev29-closure-090.json"
H["review"] = sha(ROOT / REVIEW_REL)

STATEMENT = (
    "Declaration/binding measurement (not a mathematical result) at the post-repair pins "
    f"(FROZEN rev29 {R['pins']['artifacts/formulation/FROZEN.json'][:12]}, canonical F0 0abb9ed8a961, supplement d7419b4e8963, "
    "F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, consistency evidence 9e335e9ba1bf, "
    "pinned checker de356d999ea3), for class AF-SCC-C2-VAC-GEN (node F2a) and corroborating F1/F2b: "
    "(i) the pointer clause of REC-12 item (2) is measurably closed -- all three schemas' declared "
    "consistency_evidence_sha256 and declared_f0_sha256 equal the measured live hashes, checked_at is "
    "not future-stamped, canonical bytes equal mirror bytes for all three pairs, and all 50 FROZEN rev29 "
    "manifest pins match live bytes with zero problems and zero pin drift; "
    "(ii) the embedding clause of W090-R12-01/W090-F2A-01 and map finding F-CONSEV remain OPEN at rev29 -- "
    "artifacts/formulation/evidence/taxonomy_consistency.json contains 0 hex-64 byte-identity witnesses "
    "(paths and a boolean only) and no schema f0_binding hash-pins the supplement side of the comparison. "
    "A sandbox simulation shows every declared binding value still matches after a semantic mutation of the "
    "compared supplement, while the pinned checker flips to inconsistent and the FROZEN manifest pin is the "
    "only compensating detector. Therefore W090-F2A-01 = partially closed (pointer pass, embedding open); "
    "F-CONSEV = open at rev29. Controls 6/6 as pre-registered."
)

CLAIM = {
    "event_id": TAG + "-claim",
    "event_type": "claim",
    "created_at": STAMP,
    "actor": "worker-090",
    "task_id": TASK,
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "statement": STATEMENT,
    "conclusion_type": "formal_model",
    "assumptions": [
        "canonical paths are authoritative and the measured sha256 pins define the revision under audit",
        "the evidence self-binding requirement is read from map finding F-CONSEV and this worker's W090-R12-01/W090-F2A-01 closure criteria, not inferred as a class-semantics constraint",
        "PyYAML parse of the two compared trees for the sandbox re-run; the pinned checker is executed unmodified on byte copies",
        "the sandbox exposure simulation does not edit any canonical byte and is labeled a simulation",
    ],
    "falsifier": REVIEW["next_falsifier"],
    "artifact_refs": [rel["results"], rel["controls"], rel["checker"], rel["readme"], REVIEW_REL],
    "evidence_refs": REVIEW["evidence_refs"],
    "non_claims": [
        "not a full-schema verdict; quantifiers, topology, physics, vocabulary and class semantics are out of scope",
        "no gate verdict, no node status, no validation_status promotion",
        "no canonical artifact was written or edited by this audit; all mutations are under sandbox/",
        "does not decide whether the embedding clause is required for G-FORM; measures that the property is absent",
        "C2/C3 exposure and compensator are simulations, not observations of a live edit",
    ],
}

ARTIFACTS = [
    ("checker_python", rel["checker"], H["checker"]),
    ("results_json", rel["results"], H["results"]),
    ("controls_json", rel["controls"], H["controls"]),
    ("readme_md", rel["readme"], H["readme"]),
    ("emitter_python", rel["emitter"], H["emitter"]),
    ("review_json", REVIEW_REL, H["review"]),
]

EVENTS = []
for atype, path, h in ARTIFACTS:
    EVENTS.append({
        "event_id": TAG + "-artifact-" + Path(path).name,
        "event_type": "artifact",
        "created_at": STAMP,
        "actor": "worker-090",
        "task_id": TASK,
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "artifact_type": atype,
        "path": path,
        "sha256": h,
        "validation_status": "unverified",
        "evidence_refs": [f"{path}#{h[:12]}"],
        "note": "read-only binding audit output; worker cannot promote validation status",
    })
EVENTS.append(REVIEW | {"event_id": TAG + "-review", "event_type": "review", "actor": "worker-090", "task_id": TASK})
EVENTS.append(CLAIM)
EVENTS.append({
    "event_id": TAG + "-status",
    "event_type": "status",
    "created_at": STAMP,
    "actor": "worker-090",
    "task_id": TASK,
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "status": "active",
    "hours": 0.4,
    "summary": (
        "W090-FCONSEV-REV29-CLOSURE-01 complete at worker level: one class-bound task taken (no inbox card "
        "for worker-090; residual F-CONSEV + own W090-F2A-01). 22 checks (16 pass / 6 fail, all fails in the "
        "embedding clause), 6/6 controls, zero pin drift, canonical files untouched, FROZEN rev29 50/50 pins "
        "clean. Result: REC-12 item (2) pointer clause CLOSED; F-CONSEV / embedding clause OPEN (evidence has 0 "
        "byte-identity witnesses; supplement side not hash-pinned). Verdict revise, minor, no hard failures. "
        "Worker exits for recycling; no node status or gate verdict claimed."
    ),
    "evidence_refs": REVIEW["evidence_refs"],
    "next_falsifier": REVIEW["next_falsifier"],
    "authority_note": "advisory worker status; no gate verdict, no node status promotion",
})

for e in EVENTS:
    try:
        validate_event(e)
    except SchemaError as exc:
        raise SystemExit(f"schema-invalid event {e['event_id']}: {exc}")
with open(OUTBOX, "a") as f:
    for e in EVENTS:
        f.write(json.dumps(e, sort_keys=True) + "\n")

CHECKPOINT = {
    "checkpoint_id": "w090-fconsev-ckpt-" + STAMP,
    "worker": "worker-090",
    "slot": "090",
    "at": STAMP,
    "task": TASK,
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "corroborating_class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "status": "complete",
    "verdict": REVIEW["verdict"],
    "score": REVIEW["score"],
    "hard_failures": [],
    "findings": [f["id"] for f in REVIEW["findings"]],
    "checks": {"total": len(R["checks"]), "pass": sum(1 for c in R["checks"] if c["pass"]),
               "fail": [c["id"] for c in R["checks"] if not c["pass"]]},
    "controls": {"total": len(C["controls"]), "pass": sum(1 for c in C["controls"] if c["pass"])},
    "pins": R["pins"],
    "frozen_revision": R["frozen_revision"],
    "pin_drift": V["pin_drift"],
    "artifacts": {rel[k]: H[k] for k in ("checker", "results", "controls", "readme")} | {REVIEW_REL: H["review"]},
    "events_emitted": [e["event_id"] for e in EVENTS],
    "outbox": "comms/outbox/worker-090.jsonl",
    "next_falsifier": REVIEW["next_falsifier"],
    "authority_note": "worker checkpoint; no status=done, no validation_status=passed, no gate verdict; controller ingests outbox and decides",
}
CKPT = ROOT / "runtime/state/w090_fconsev_rev29_closure_checkpoint.json"
CKPT.write_text(json.dumps(CHECKPOINT, indent=1) + "\n")
with open(ROOT / "runtime/state/w090_checkpoints.jsonl", "a") as f:
    f.write(json.dumps(CHECKPOINT, sort_keys=True) + "\n")

print(json.dumps({"events": len(EVENTS), "outbox": str(OUTBOX.relative_to(ROOT)),
                  "review": REVIEW_REL, "checkpoint": str(CKPT.relative_to(ROOT)),
                  "verdict": REVIEW["verdict"], "fail": CHECKPOINT["checks"]["fail"]}, indent=1))
