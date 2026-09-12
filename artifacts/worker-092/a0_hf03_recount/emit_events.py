#!/usr/bin/env python3
"""Emit the W092-A0-HF03-STAGING-RECOUNT-01 review record, checkpoint and protocol events.

Appends to comms/outbox/worker-092.jsonl only.  No canonical path is written.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-092.jsonl"
REVIEW = ROOT / "reviews/A0-hf03-recount-worker-092.json"
CKPT = ROOT / "runtime/state/worker-092_A0_hf03_recount_checkpoint.json"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


REPORT = HERE / "report.json"
SCRIPT = HERE / "recount_a0_hf03.py"
README = HERE / "README.md"
rep_sha, scr_sha, rd_sha = sha(REPORT), sha(SCRIPT), sha(README)
rep = json.loads(REPORT.read_text())

EVID = [
    f"artifacts/worker-092/a0_hf03_recount/report.json#{rep_sha[:12]}",
    f"artifacts/worker-092/a0_hf03_recount/recount_a0_hf03.py#{scr_sha[:12]}",
    f"artifacts/worker-092/a0_hf03_recount/README.md#{rd_sha[:12]}",
    "evaluation/A0_detector_scope_adjudication.json#a26be4b85706",
    "evaluation_rubric.yaml#d748a9e3574e",
    "comms/outbox/astra-lead-audit.jsonl#audit-l06-b3-staging-20260912T005926",
    "comms/outbox/worker-021.jsonl#w021-a0hf03-20260912T010943-claim",
]
FALSIFIER = ("Re-run artifacts/worker-092/a0_hf03_recount/recount_a0_hf03.py at the pins: "
             "falsified if any of the 15 declared per-file HF-03 counts differs, if the totals "
             "are not 218 before / 194 kept / 17 excluded / 7 staging, if the staging sources "
             "file does not measure 7, if the staging theorems file does not measure 12, or if "
             "any affected file pin differs from live bytes. A write to the adjudication "
             "artifact or the rubric voids the binding (re-run against the new revision).")

review = {
    "event_id": f"w092-a0hf03-review",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-092",
    "node_id": "A0",
    "class_id": "GLOBAL",
    "class_ids": ["GLOBAL"],
    "gate": "G-AUDIT",
    "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
    "target_id": "blocker/audit-l06-b3-staging-20260912T005926#hf03-count",
    "reviewer": "worker-092",
    "verdict": "revise",
    "score": 2.0,
    "counts_as_full_schema_verdict": False,
    "counts_toward_gate_accept": False,
    "authority_note": ("Scoped review of the b3 blocker's HF-03 staging count only. This is not an "
                       "A0 node verdict, not an adjudication-artifact verdict, and does not move "
                       "G-AUDIT, node status or validation_status."),
    "hard_failures": [
        "b3-HF03-COUNT: audit-l06-b3-staging-20260912T005926 states '1 HF-03 record' for the "
        "worker-07 staging contribution; the independently measured count is 7 records in "
        "artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl, which is also "
        "what evaluation/A0_detector_scope_adjudication.json itself records as "
        "staging_unresolved=7."
    ],
    "findings": [
        {"id": "F-092-HF03-01", "kind": "count", "severity": "hard",
         "finding": "b3's '1 HF-03 record' is contradicted by two independent counts (this one "
                    "and worker-021's): 7 records measure under the declared implementation "
                    "predicate; 7 is the artifact's own staging_unresolved value. b3's '12 HF-14 "
                    "records' half is correct (batch-w07-theorems.jsonl = 12)."},
        {"id": "F-092-HF03-02", "kind": "reproduction", "severity": "positive",
         "finding": "All 15 declared per-file HF-03 counts reproduce exactly under an "
                    "independently written stdlib predicate; totals 218/194/17/7 reconcile; all "
                    "15 affected file pins match live bytes."},
        {"id": "F-092-HF03-03", "kind": "rubric scope", "severity": "info",
         "finding": "The rubric-literal HF-03 branch fires on 0 of the 194 kept-live rows; the "
                    "194 survive only under the major-severity absence-of-scope-metadata "
                    "implementation predicate while rubric HF-03 is critical. This independently "
                    "reproduces worker-021's discrepancy (3); it is a rubric-owner ruling, not a "
                    "counting defect, and no count in the adjudication artifact is wrong."},
        {"id": "F-092-HF03-04", "kind": "owner action", "severity": "info",
         "finding": "Owner repair is text-level: correct b3's HF-03 number to 7 (or annotate the "
                    "card); do not edit the adjudication artifact's counts, which reproduce."}
    ],
    "evidence_refs": EVID,
    "reviewed_sha256": "a26be4b857068d2608387848035b6ddb5fda746447bf5750d6a7527ce5e2d24c",
    "independence": ("not the author of evaluation/A0_detector_scope_adjudication.json, the "
                     "rubric, the audit-lead outbox, or worker-021's replication; the only author "
                     "artifact reviewed here is none; this slot's prior A0 review "
                     "(W092-A0-SCOPE-INDEP-01) was scoped to pins/detectors and is not reused as "
                     "evidence."),
    "falsifier": FALSIFIER,
}
REVIEW.write_text(json.dumps(review, indent=1, sort_keys=True) + "\n")
rev_sha = sha(REVIEW)

ckpt = {
    "checkpoint_id": f"w092-a0hf03-recount-{STAMP}",
    "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
    "actor": "worker-092",
    "node_id": "A0",
    "class_id": "GLOBAL",
    "gate": "G-AUDIT",
    "created_at": NOW,
    "status_at_exit": "task_complete_worker_level_exit",
    "result": rep["headline"],
    "b3_verdict": rep["b3_adjudication"]["verdict"],
    "pins": {
        "adjudication_artifact": rep["inputs"]["adjudication_artifact"]["sha256"],
        "rubric": rep["inputs"]["rubric"]["sha256"],
        "staging_sources": rep["measured"]["per_file"][
            "artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl"]["sha256"],
    },
    "files": {
        "artifacts/worker-092/a0_hf03_recount/report.json": rep_sha,
        "artifacts/worker-092/a0_hf03_recount/recount_a0_hf03.py": scr_sha,
        "artifacts/worker-092/a0_hf03_recount/README.md": rd_sha,
        "reviews/A0-hf03-recount-worker-092.json": rev_sha,
    },
    "not_claimed": ["no gate verdict", "no node completion", "no validation_status=passed",
                    "no canonical write", "no repair of b3"],
    "falsifier": FALSIFIER,
}
CKPT.write_text(json.dumps(ckpt, indent=1, sort_keys=True) + "\n")
ckpt_sha = sha(CKPT)

events = [
    {"event_id": f"w092-a0hf03-{STAMP}-artifact-report", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "artifact_type": "hf03_independent_recount",
     "path": "artifacts/worker-092/a0_hf03_recount/report.json", "sha256": rep_sha,
     "validation_status": "unverified", "headline": rep["headline"],
     "b3_verdict": rep["b3_adjudication"]["verdict"],
     "evidence_refs": EVID},
    {"event_id": f"w092-a0hf03-{STAMP}-artifact-script", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "artifact_type": "independent_recount_implementation",
     "path": "artifacts/worker-092/a0_hf03_recount/recount_a0_hf03.py", "sha256": scr_sha,
     "validation_status": "unverified",
     "note": "stdlib only; imports no author detector code", "evidence_refs": EVID},
    {"event_id": f"w092-a0hf03-{STAMP}-artifact-readme", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "artifact_type": "recount_readme",
     "path": "artifacts/worker-092/a0_hf03_recount/README.md", "sha256": rd_sha,
     "validation_status": "unverified", "evidence_refs": EVID},
    {"event_id": f"w092-a0hf03-{STAMP}-review", "event_type": "review",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "target_id": review["target_id"], "reviewer": "worker-092", "verdict": review["verdict"],
     "score": review["score"], "hard_failures": review["hard_failures"],
     "findings": [f["finding"] for f in review["findings"]],
     "counts_as_full_schema_verdict": False, "counts_toward_gate_accept": False,
     "reviewed_sha256": review["reviewed_sha256"],
     "evidence_refs": EVID + [f"reviews/A0-hf03-recount-worker-092.json#{rev_sha[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w092-a0hf03-{STAMP}-artifact-review", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "artifact_type": "review_record", "path": "reviews/A0-hf03-recount-worker-092.json",
     "sha256": rev_sha, "validation_status": "unverified", "evidence_refs": EVID},
    {"event_id": f"w092-a0hf03-{STAMP}-artifact-checkpoint", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "artifact_type": "checkpoint",
     "path": "runtime/state/worker-092_A0_hf03_recount_checkpoint.json", "sha256": ckpt_sha,
     "validation_status": "unverified", "evidence_refs": EVID},
    {"event_id": f"w092-a0hf03-{STAMP}-claim", "event_type": "claim",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "conclusion_type": "measurement",
     "statement": ("Independent artifact-and-checker measurement, not a mathematics claim and not "
                   "a gate verdict: at evaluation/A0_detector_scope_adjudication.json#a26be4b85706 "
                   "and evaluation_rubric.yaml#d748a9e3574e, an independently written stdlib "
                   "recount reproduces all 15 declared per-file HF-03 counts exactly and the "
                   "totals 218 before / 194 kept-live / 17 excluded / 7 staging, with all 15 "
                   "affected file pins stable. The staging file "
                   "artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl "
                   "carries 7 HF-03 records, so blocker card audit-l06-b3-staging-20260912T005926 "
                   "('1 HF-03 record') is textually wrong while its '12 HF-14' half is correct. "
                   "The rubric-literal HF-03 branch fires on 0 of the 194 kept-live rows, "
                   "independently reproducing the implementation-vs-literal gap; that axis is a "
                   "rubric-owner ruling, not a counting defect, and no count in the adjudication "
                   "artifact is wrong."),
     "assumptions": ["the declared implementation predicate is the one documented in "
                     "artifacts/audit/audit_lib.py::check_ledger_scope and re-implemented here "
                     "from its public text",
                     "only the 15 files in the artifact's declared HF-03 before-map are treated "
                     "as in-scope for reproduction; live corpus growth is not part of this task"],
     "falsifier": FALSIFIER,
     "evidence_refs": EVID + [f"artifacts/worker-092/a0_hf03_recount/report.json#{rep_sha[:12]}"]},
    {"event_id": f"w092-a0hf03-{STAMP}-blocker", "event_type": "blocker",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "blocker_kind": "owner_text_repair",
     "target_id": "blocker/audit-l06-b3-staging-20260912T005926#hf03-count",
     "description": ("b3's HF-03 staging count is wrong (1 stated, 7 measured and 7 declared by "
                     "the adjudication artifact itself). It is a card-text defect, not an "
                     "adjudication-artifact defect; the artifact's counts reproduce exactly."),
     "needed_to_unblock": ("audit lead corrects or annotates the b3 HF-03 number to 7; no "
                           "canonical count needs editing and no gate movement follows from this "
                           "task"),
     "evidence_refs": EVID + [f"reviews/A0-hf03-recount-worker-092.json#{rev_sha[:12]}"],
     "falsifier": FALSIFIER},
    {"event_id": f"w092-a0hf03-{STAMP}-status", "event_type": "status",
     "created_at": NOW, "actor": "worker-092", "node_id": "A0", "class_id": "GLOBAL",
     "gate": "G-AUDIT", "task_id": "W092-A0-HF03-STAGING-RECOUNT-01",
     "status": "active", "hours": 0.4,
     "summary": ("CHECKPOINT + EXIT. One bounded class-bound task self-selected (no inbox card "
                 "for worker-092): W092-A0-HF03-STAGING-RECOUNT-01, independent read-only recount "
                 "of the A0 HF-03 staging dispute at the pinned artifact/rubric. Measured: 15/15 "
                 "per-file counts reproduce; 218/194/17/7 reconcile; 15/15 pins stable; staging "
                 "sources file = 7 HF-03 (b3 says 1 -> text defect confirmed); staging theorems "
                 "file = 12 HF-14 (b3 correct); rubric-literal HF-03 on the 194 kept-live rows = "
                 "0. Verdict on the b3 count axis: revise (2.0), scoped, not an A0 node verdict. "
                 "Node status, gate verdicts and validation_status NOT moved; no canonical write."),
     "evidence_refs": EVID + [
         "reviews/A0-hf03-recount-worker-092.json#{0}".format(rev_sha[:12]),
         "runtime/state/worker-092_A0_hf03_recount_checkpoint.json#{0}".format(ckpt_sha[:12])],
     "next_falsifier": FALSIFIER},
]

with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

print("review", rev_sha)
print("checkpoint", ckpt_sha)
print("events appended:", len(events))
for e in events:
    print(" ", e["event_id"])
