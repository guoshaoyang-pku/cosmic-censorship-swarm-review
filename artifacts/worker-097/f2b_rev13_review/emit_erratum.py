#!/usr/bin/env python3
"""Erratum round 2 emitter for W097-F2B-REV13-INDEP-REVIEW-01.

Supersedes the round-1 worker-097 F2b verdict with the corrected two-hard-failure record
(revise 3.0). Appends only to comms/outbox/worker-097.jsonl; writes this artifact directory,
SHA256SUMS.txt and runtime/state/w097_checkpoint_f2b_rev13_review_r2.json. Every event is
validated with research_map/schemas.py before it is written.
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
CKPT = os.path.join(REPO, "runtime", "state", "w097_checkpoint_f2b_rev13_review_r2.json")
TS = "2026-09-12T01:07:19+08:00"
TASK = "W097-F2B-REV13-INDEP-REVIEW-01"
CLASS = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"
GATE = "G-FORM"
SCHEMA_REL = "schemas/af_scc_c0_vacuum.yaml"
SCHEMA_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
ROUND1_REVIEW_SHA = "1bb9dff017a20866"


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
    "AMENDMENTS.md": "instrument_amendment_record",
    "README.md": "findings_note",
    "report.run2_pre_erratum.json": "verification_report_superseded",
}

events = []
for rel, atype in FILES.items():
    h = sha(os.path.join(ART, rel))
    events.append({
        "event_id": f"w097-f2b13r2-artifact-{slug(rel)}-20260912T010719",
        "event_type": "artifact", "created_at": TS, "actor": "worker-097",
        "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
        "artifact_type": atype, "path": f"{ART_REL}/{rel}", "sha256": h,
        "validation_status": "unverified",
        "evidence_refs": [f"{ART_REL}/{rel}#sha256:{h}"],
        "summary": f"{TASK} erratum round 2 deliverable (supersedes round 1 hashes)",
    })

rep = json.load(open(os.path.join(ART, "report.json")))
rev = json.load(open(os.path.join(ART, "REVIEW.json")))
ev = lambda rel: f"{ART_REL}/{rel}#sha256:{sha(os.path.join(ART, rel))}"  # noqa: E731

events.append({
    "event_id": "w097-f2b13r2-review-erratum-20260912T010719",
    "event_type": "review", "created_at": TS, "actor": "worker-097",
    "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "target_id": "F2b", "reviewer": "worker-097",
    "reviewer_independence": rev["independence"],
    "reviewed_sha256": SCHEMA_SHA,
    "supersedes_review_sha256_prefix": ROUND1_REVIEW_SHA,
    "review_record_version": 2,
    "verdict": "revise", "score": 3.0,
    "counts_as_full_schema_verdict": True,
    "hard_failures": rev["hard_failures"],
    "findings": [
        "ERRATUM: the round-1 worker-097 F2b verdict at this same hash (revise 3.5, one hard failure) "
        "under-counted; a second hard failure was found by an independent peer review of the same hash "
        "(reviews/F2b-review-worker-018-rev13.json) and re-derived here from the primary bytes.",
        "W097-F2B-HF3 (line 246): inverted containment premise 'C2 is a strictly larger extension class'.",
        "W097-F2B-HF3b (line 152): live denial 'No containment with C2 or C0 is asserted here' contradicts "
        "the artifact's own containment ledger (lines 239/250) and the supplement axis_registry (line 145); "
        "the F2a sibling marks the identical sentence as an R2-major error.",
        "All other hard checks pass; controls 10/10; no pin drift; canonical == mirror.",
    ],
    "controls": "10/10 (K1-K9) in report.json#controls",
    "evidence_refs": [ev("report.json"), ev("REVIEW.json"), ev("check_f2b_rev13.py"),
                      ev("AMENDMENTS.md"), ev("README.md"), f"{SCHEMA_REL}#sha256:{SCHEMA_SHA}"],
})

events.append({
    "event_id": "w097-f2b13r2-blocker-hf3b-20260912T010719",
    "event_type": "blocker", "created_at": TS, "actor": "worker-097",
    "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "description": (
        "F2b rev13 b2ab6acb2bbe, second hard defect (erratum): regularity.must_not_conflate[0] (line 152) "
        "still asserts 'No containment with C2 or C0 is asserted here', contradicting the artifact's own "
        "extension_class_containment (line 239), subsumption_note (line 250) and the supplement axis_registry "
        "(line 145); the F2a sibling repaired the identical sentence as R2-major."),
    "needed_to_unblock": (
        "owner adopts F2a's corrected clause (nested sets E_C2 subset of E_{C^1,1} subset of E_H2loc subset "
        "of E_C0) together with the line-246 'strictly larger' -> 'strictly smaller' repair, then a fresh "
        "hash-bound review"),
    "evidence_refs": [ev("REVIEW.json"), ev("report.json"), f"{SCHEMA_REL}#sha256:{SCHEMA_SHA}"],
})

events.append({
    "event_id": "w097-f2b13r2-status-20260912T010719",
    "event_type": "status", "created_at": TS, "actor": "worker-097",
    "node_id": NODE, "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "status": "active", "hours": 0.4,
    "summary": (
        "CHECKPOINT(r2) + EXIT. W097-F2B-REV13-INDEP-REVIEW-01 corrected record: F2b rev13 b2ab6acb2bbe "
        "revise 3.0, two hard failures (HF3 line-246 inverted containment premise; HF3b line-152 live "
        "containment denial), four minor advisories, controls 10/10, no pin drift. Round 1 (3.5) and round 2 "
        "(3.5 pre-erratum) preserved; the correction followed an independent peer finding at the same hash and "
        "was re-derived from primary bytes with a dedicated check. Worker verdict only: no node status, no "
        "validation promotion, no gate verdict, no canonical write."),
    "evidence_refs": [ev("report.json"), ev("REVIEW.json"), ev("AMENDMENTS.md"), ev("README.md")],
    "next_falsifier": rev["next_falsifier"],
})

for e in events:
    validate_event(e)

with open(OUTBOX, "a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

deliv = sorted(set(FILES) | {"emit_events.py", "emit_erratum.py", "PREREGISTRATION.md",
                             "report.run1_pre_amendment.json", "pins/SHA256SUMS.txt"})
lines, hashes = [], {}
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
    "checkpoint_id": "w097-f2b13-r2-20260912T010719",
    "supersedes_checkpoint": "w097-f2b13-20260912T010420",
    "task_id": TASK, "worker": "worker-097", "created_at": TS,
    "class_id": CLASS, "node_id": NODE, "gate": GATE,
    "verdict": rep["verdict"], "score": rep["score"],
    "hard_failures": rep["hard_failures"], "controls_pass": rep["controls_pass"],
    "pin_drift": rep["pin_drift"], "result_digest": rep["result_digest"],
    "reviewed_artifact": {SCHEMA_REL: SCHEMA_SHA},
    "artifact_sha256": hashes,
    "events_emitted": [e["event_id"] for e in events],
    "round_history": {
        "run1_pre_amendment": {"score": 2.5, "hard": ["H1", "H3", "H5"],
                               "note": "H1/H5 adjudicated instrument false positives"},
        "run2_pre_erratum": {"score": 3.5, "hard": ["H3"], "review_sha256_prefix": ROUND1_REVIEW_SHA},
        "run3_current": {"score": 3.0, "hard": ["H3", "H3b"]},
    },
    "outbox": {"path": "comms/outbox/worker-097.jsonl", "lines": n_lines,
               "sha256": hashlib.sha256(outbox_bytes).hexdigest()},
    "falsifier": rev["falsifier"], "next_falsifier": rev["next_falsifier"],
    "not_claimed": [
        "no gate verdict and no node completion; worker verdict only",
        "no mathematical or physical correctness decided",
        "no citation-scope verification (L1 owns it)",
        "no write to schemas/, research_map/, artifacts/formulation/, or any canonical path",
        "no claim that the two reported line repairs exhaust F2b's remaining obligations",
    ],
    "exit": "clean; erratum events validated by research_map/schemas.py; no ingest, no gate verdict, no node status promotion, no canonical write",
}
with open(CKPT, "w") as fh:
    json.dump(ckpt, fh, indent=2, sort_keys=True)
    fh.write("\n")

print(json.dumps({"events": len(events), "outbox_lines": n_lines,
                  "checkpoint_sha256": sha(CKPT), "verdict": rep["verdict"],
                  "score": rep["score"], "hard_failures": rep["hard_failures"]}, indent=1))
