#!/usr/bin/env python3
"""Emit W097-F2B-REV13-INDEP-REVIEW-01 events, manifest and checkpoint.

Read-only w.r.t. canonical paths: appends only to comms/outbox/worker-097.jsonl and writes
inside artifacts/worker-097/f2b_rev13_review/ plus runtime/state/w097_checkpoint_f2b_rev13_review.json.
Every event is validated with research_map/schemas.py before it is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research_map"))
from schemas import validate_event  # noqa: E402

ART_REL = "artifacts/worker-097/f2b_rev13_review"
ART = os.path.join(REPO, ART_REL)
OUTBOX = os.path.join(REPO, "comms", "outbox", "worker-097.jsonl")
CKPT = os.path.join(REPO, "runtime", "state", "w097_checkpoint_f2b_rev13_review.json")
TS = "2026-09-12T01:04:20+08:00"
TASK = "W097-F2B-REV13-INDEP-REVIEW-01"
CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"
SCHEMA_REL = "schemas/af_scc_c0_vacuum.yaml"
SCHEMA_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(name: str) -> str:
    return name.replace("/", "_").replace(".", "-")


FILES = {
    "report.json": "verification_report",
    "REVIEW.json": "review_record",
    "check_f2b_rev13.py": "audit_script",
    "make_review.py": "audit_script",
    "PREREGISTRATION.md": "preregistration",
    "AMENDMENTS.md": "instrument_amendment_record",
    "README.md": "findings_note",
    "report.run1_pre_amendment.json": "verification_report_superseded",
    "pins/SHA256SUMS.txt": "pin_manifest",
}

events = []
for rel, atype in FILES.items():
    full = os.path.join(ART, rel)
    h = sha(full)
    events.append({
        "event_id": f"w097-f2b13-artifact-{slug(rel)}-20260912T010420",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-097",
        "node_id": NODE,
        "class_id": CLASS,
        "gate": GATE,
        "task_id": TASK,
        "artifact_type": atype,
        "path": f"{ART_REL}/{rel}",
        "sha256": h,
        "validation_status": "unverified",
        "evidence_refs": [f"{ART_REL}/{rel}#sha256:{h}"],
        "summary": f"{TASK} deliverable (class-bound F2b rev13 independent review)",
    })

rep = json.load(open(os.path.join(ART, "report.json")))
rev = json.load(open(os.path.join(ART, "REVIEW.json")))
ev = lambda rel: f"{ART_REL}/{rel}#sha256:{sha(os.path.join(ART, rel))}"

events.append({
    "event_id": "w097-f2b13-review-20260912T010420",
    "event_type": "review",
    "created_at": TS,
    "actor": "worker-097",
    "node_id": NODE,
    "class_id": CLASS,
    "gate": GATE,
    "task_id": TASK,
    "target_id": "F2b",
    "reviewer": "worker-097",
    "reviewer_independence": rev["independence"],
    "reviewed_sha256": SCHEMA_SHA,
    "reviewed_bytes": os.path.getsize(os.path.join(REPO, SCHEMA_REL)),
    "review_scope": "full class-contract conformance at rev13, ten hard checks + alias-aware vocabulary + FROZEN rev29 pin closure; first hash-bound F2b verdict at this revision",
    "verdict": "revise",
    "score": 3.5,
    "counts_as_full_schema_verdict": True,
    "hard_failures": rev["hard_failures"],
    "findings": [f"{f['id']} [{f['severity']}] {f['finding'] if 'finding' in f else f.get('measured','')}" for f in rev["findings"]],
    "controls": "8/8 (K1-K8); instrument amendments documented in AMENDMENTS.md; run 1 preserved",
    "evidence_refs": [ev("report.json"), ev("REVIEW.json"), ev("check_f2b_rev13.py"),
                      ev("PREREGISTRATION.md"), ev("AMENDMENTS.md"),
                      f"{SCHEMA_REL}#sha256:{SCHEMA_SHA}"],
})

events.append({
    "event_id": "w097-f2b13-claim-20260912T010420",
    "event_type": "claim",
    "created_at": TS,
    "actor": "worker-097",
    "node_id": NODE,
    "class_id": CLASS,
    "gate": GATE,
    "task_id": TASK,
    "statement": (
        "Artifact-and-checker measurement (not a mathematical claim, not a gate verdict): at F2b rev13 "
        f"schemas/af_scc_c0_vacuum.yaml {SCHEMA_SHA[:12]} / FROZEN rev29 815e08079aef, an independently written "
        "fail-closed checker finds exactly one hard class-contract failure - "
        "implication_ledger.forbidden_transfers[0].reason states 'C2 is a strictly larger extension class', "
        "inverting the same artifact's extension_class_containment ('E_C0 contains E_H2loc contains E_{C^1,1} "
        "contains E_C2') and the F2a sibling - plus four minor advisories (alias tokens in a canonical artifact; "
        "hash-free consistency evidence; F0 contract (s,delta) vs D0 smooth branch; revision-history collapse). "
        "The other 9/10 hard checks pass, controls 8/8, pin drift none. Recommended one-line repair: "
        "'strictly larger' -> 'strictly smaller'."),
    "conclusion_type": "stability_result",
    "assumptions": [
        "F0 field_vocabulary + VOCAB_ALIASES.json are the authoritative token sets for G-FORM class-bound slots",
        "FROZEN rev29 is the operative freeze manifest for the rev13 pins",
        "the review is mechanical conformance; a clean verdict would not assert mathematical correctness",
    ],
    "falsifier": rev["falsifier"],
    "evidence_refs": [ev("report.json"), ev("REVIEW.json"), ev("check_f2b_rev13.py"),
                      ev("AMENDMENTS.md"), f"{SCHEMA_REL}#sha256:{SCHEMA_SHA}"],
})

events.append({
    "event_id": "w097-f2b13-blocker-20260912T010420",
    "event_type": "blocker",
    "created_at": TS,
    "actor": "worker-097",
    "node_id": NODE,
    "class_id": CLASS,
    "gate": GATE,
    "task_id": TASK,
    "description": (
        "F2b rev13 b2ab6acb2bbe is not cleanly acceptable: implication_ledger.forbidden_transfers[0].reason "
        "(line 246) inverts the artifact's own extension-class containment, so the forbidden-transfer rationale "
        "contradicts extension_class_containment and the F2a sibling. Owner action; one line."),
    "needed_to_unblock": (
        "owner edit of implication_ledger.forbidden_transfers[0].reason ('strictly larger' -> 'strictly smaller', "
        "or restate as 'E_C2 subset of E_C0') in a new revision, then a fresh hash-bound review at the new hash; "
        "no other class-semantics change is required by this review"),
    "evidence_refs": [ev("REVIEW.json"), ev("report.json"), f"{SCHEMA_REL}#sha256:{SCHEMA_SHA}"],
})

events.append({
    "event_id": "w097-f2b13-status-20260912T010420",
    "event_type": "status",
    "created_at": TS,
    "actor": "worker-097",
    "node_id": NODE,
    "class_id": CLASS,
    "gate": GATE,
    "task_id": TASK,
    "status": "active",
    "hours": 0.3,
    "summary": (
        "CHECKPOINT + EXIT. W097-F2B-REV13-INDEP-REVIEW-01 complete at worker level: first hash-bound full-schema "
        "verdict for F2b at rev13 (b2ab6acb2bbe) - revise 3.5, one hard failure (line-246 inverted containment "
        "premise), four minor advisories, controls 8/8, no pin drift, canonical/mirror byte-identical, FROZEN "
        "rev29 closure verified. Run 1 (score 2.5) preserved; its H1/H5 were adjudicated instrument false "
        "positives. Worker verdict only: no node status, no validation promotion, no gate verdict, no canonical write."),
    "evidence_refs": [ev("report.json"), ev("REVIEW.json"), ev("check_f2b_rev13.py"),
                      ev("PREREGISTRATION.md"), ev("AMENDMENTS.md")],
    "next_falsifier": rev["next_falsifier"],
})

for e in events:
    validate_event(e)

with open(OUTBOX, "a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

# manifest of deliverables, written after the events exist
deliv = sorted(set(FILES) | {"emit_events.py"})
lines = []
hashes = {}
for rel in deliv:
    full = os.path.join(ART, rel)
    if not os.path.exists(full):
        continue
    h = sha(full)
    hashes[rel] = h
    lines.append(f"{h}  {rel}")
with open(os.path.join(ART, "SHA256SUMS.txt"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
hashes["SHA256SUMS.txt"] = sha(os.path.join(ART, "SHA256SUMS.txt"))

outbox_bytes = open(OUTBOX, "rb").read()
n_lines = len([l for l in outbox_bytes.decode().splitlines() if l.strip()])
ckpt = {
    "checkpoint_id": "w097-f2b13-20260912T010420",
    "task_id": TASK,
    "worker": "worker-097",
    "created_at": TS,
    "class_id": CLASS,
    "node_id": NODE,
    "gate": GATE,
    "verdict": rep["verdict"],
    "score": rep["score"],
    "hard_failures": rep["hard_failures"],
    "controls_pass": rep["controls_pass"],
    "pin_drift": rep["pin_drift"],
    "result_digest": rep["result_digest"],
    "reviewed_artifact": {SCHEMA_REL: SCHEMA_SHA},
    "artifact_sha256": hashes,
    "events_emitted": [e["event_id"] for e in events],
    "outbox": {"path": "comms/outbox/worker-097.jsonl", "lines": n_lines,
               "sha256": hashlib.sha256(outbox_bytes).hexdigest()},
    "falsifier": rev["falsifier"],
    "next_falsifier": rev["next_falsifier"],
    "not_claimed": [
        "no gate verdict and no node completion; worker verdict only",
        "no mathematical or physical correctness decided",
        "no citation-scope verification (L1 owns it)",
        "no write to schemas/, research_map/, artifacts/formulation/, or any canonical path",
        "no claim that repairing line 246 exhausts F2b's remaining obligations",
    ],
    "exit": "clean; events validated by research_map/schemas.py; no ingest, no gate verdict, no node status promotion, no canonical write",
}
with open(CKPT, "w") as fh:
    json.dump(ckpt, fh, indent=2, sort_keys=True)
    fh.write("\n")

print(json.dumps({"events": len(events), "outbox_lines": n_lines,
                  "checkpoint_sha256": sha(CKPT),
                  "manifest_sha256": hashes["SHA256SUMS.txt"],
                  "verdict": rep["verdict"], "score": rep["score"]}, indent=1))
