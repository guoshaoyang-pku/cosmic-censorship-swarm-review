#!/usr/bin/env python3
"""W040-F1-STRICTNESS-ADJ-04 -- checkpoint writer and idempotent event emitter.

Writes runtime/state/w040_strictness_adjudication_checkpoint.json, appends one
line to runtime/state/w040_checkpoints.jsonl, and appends this worker's events to
comms/outbox/worker-040.jsonl (skipping event_ids already present).

Refuses to emit if schemas/af_wcc_vacuum.yaml has drifted away from cce9c601.
"""
import datetime as dt
import hashlib
import json
import os
import sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
ADJ = os.path.join(ROOT, "artifacts/worker-040/f1_strictness_adjudication")
STATE = os.path.join(ROOT, "runtime/state")
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-040.jsonl")
CHECKPOINT = os.path.join(STATE, "w040_strictness_adjudication_checkpoint.json")
CP_LOG = os.path.join(STATE, "w040_checkpoints.jsonl")
REVIEW = "reviews/F1-review-040-strictness.json"
TARGET = "schemas/af_wcc_vacuum.yaml"
PIN_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
TASK = "W040-F1-STRICTNESS-ADJ-04"
INSTANCE = "worker-040-20260912T003814-968807"
TZ = dt.timezone(dt.timedelta(hours=8))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


# Deterministic emission identity: a re-run must reproduce the same event_ids so
# that appends stay idempotent. EMIT_AT is the wall-clock instant of the first
# successful emission of this task's event batch.
EMIT_AT = dt.datetime(2026, 9, 12, 0, 45, 21, tzinfo=TZ)
now = dt.datetime.now(TZ)
stamp = EMIT_AT.strftime("%Y%m%dT%H%M%S")
iso = EMIT_AT.isoformat()

live_f1 = sha(os.path.join(ROOT, TARGET))
report = json.load(open(os.path.join(ADJ, "report.json"), encoding="utf-8"))
if live_f1 != PIN_F1 or report["target"]["sha256"] != PIN_F1:
    sys.stderr.write(f"DRIFT: live F1 {live_f1} != pinned {PIN_F1}; refusing to emit "
                     "an unbound verdict\n")
    sys.exit(2)

deliverables = ["report.json", "evidence.json", "entry_hashes.json", "README.md",
                "run_adjudication.py", "emit_events.py"]
art_hashes = {f"artifacts/worker-040/f1_strictness_adjudication/{f}":
              sha(os.path.join(ADJ, f)) for f in deliverables}
art_hashes[REVIEW] = sha(os.path.join(ROOT, REVIEW))
art_hashes[TARGET] = live_f1

ev = f"w040-strict-{stamp}"
events = []

events.append({
    "event_id": f"{ev}-task", "event_type": "task", "actor": "worker-040",
    "created_at": iso, "task_id": TASK, "node_id": "F1", "gate": "G-FORM",
    "class_ids": ["AF-WCC-VAC-GEN"], "status": "active",
    "reviewed_sha256": PIN_F1, "hours": 0.4, "claims_completion": False,
    "summary": ("No assignment card exists in comms/inbox/worker-040.jsonl (fleet "
                "2026-09-12T00:38:14). Took ONE bounded class-bound task: "
                "W040-F1-STRICTNESS-ADJ-04, independent adjudication of the live "
                "conflict between HF-040-04 (F1 rev12's whole-curve 'strictly "
                "STRONGER' sentence is false) and F1-review-053 P053-5/C6 (it is true; "
                "a discriminating model separates the readings), via an executable "
                "falsifier over finite causal models plus an audit of the 053 model and "
                "the cited worker-037 withdrawal. Read-only on all shared artifacts."),
    "evidence_refs": [f"{k}#{v[:12]}" for k, v in art_hashes.items()],
    "next_falsifier": report["next_falsifier"]["statement"],
})

artifact_types = {
    "report.json": "independent_class_bound_adjudication",
    "evidence.json": "machine_evidence",
    "entry_hashes.json": "pin_evidence",
    "README.md": "human_readable_adjudication",
    "run_adjudication.py": "deterministic_readonly_instrument",
    "emit_events.py": "event_emitter",
}
for f in deliverables:
    p = f"artifacts/worker-040/f1_strictness_adjudication/{f}"
    events.append({
        "event_id": f"{ev}-artifact-{f}", "event_type": "artifact",
        "actor": "worker-040", "created_at": iso, "task_id": TASK,
        "node_id": "F1", "gate": "G-FORM", "class_ids": ["AF-WCC-VAC-GEN"],
        "artifact_type": artifact_types[f], "path": p, "sha256": art_hashes[p],
        "validation_status": "self_check_passed", "reviewed_sha256": PIN_F1,
        "evidence_refs": [f"{TARGET}#{PIN_F1[:12]}"],
        "next_falsifier": report["next_falsifier"]["statement"],
    })

events.append({
    "event_id": f"{ev}-review-f1", "event_type": "review", "actor": "worker-040",
    "created_at": iso, "task_id": TASK, "node_id": "F1", "gate": "G-FORM",
    "class_ids": ["AF-WCC-VAC-GEN"], "review_id": "F1-review-040-strictness",
    "path": REVIEW, "sha256": art_hashes[REVIEW],
    "reviewed_sha256": PIN_F1, "reviewed_path": TARGET,
    "review_verdict": "revise", "review_score": 3.5,
    "counts_as_independent_verdict": True, "claims_completion": False,
    "findings": ["F-040S-1 HF-040-04 confirmed at the live hash (false strictness "
                 "sentence; equivalence under past-closure; 0/355 preorders)",
                 "F-040S-2 P053-5/C6 rejected (hardcoded literal discriminating "
                 "model; configuration unrealizable under the class hypotheses)",
                 "F-040S-3 inverted citation: line 72 cites W037V2-F1, which its own "
                 "source records as REFUTED and withdrawn",
                 "F-040S-4 defect confined to F1 lines 72/213"],
    "conditions": ["binds cce9c601 only",
                   "not a full schema verdict",
                   "blocking classification is the controller/lead call"],
    "evidence_refs": [f"{REVIEW}#{art_hashes[REVIEW][:12]}",
                      f"artifacts/worker-040/f1_strictness_adjudication/report.json#{art_hashes['artifacts/worker-040/f1_strictness_adjudication/report.json'][:12]}",
                      f"{TARGET}#{PIN_F1[:12]}"],
    "next_falsifier": report["next_falsifier"]["statement"],
})

events.append({
    "event_id": f"{ev}-claim", "event_type": "claim", "actor": "worker-040",
    "created_at": iso, "task_id": TASK, "node_id": "F1", "gate": "G-FORM",
    "class_ids": ["AF-WCC-VAC-GEN"], "confidence": "high",
    "claim": ("FORMAL-MODEL-LEVEL finding (not a theorem about any physical "
              "spacetime; a statement about the schema's declared predicates): under "
              "the schema's own hypothesis that J^-(q) is the standard causal past "
              "(past-closed) and gamma is a future-directed causal geodesic, "
              "tail-containment and whole-curve containment are logically equivalent. "
              "Therefore F1 rev12 line 72 'Whole-curve containment ... is strictly "
              "STRONGER' and the line-213 misclassification example are false; "
              "F1-review-053 P053-5/C6 rests on a hardcoded, unrealizable model."),
    "evidence_refs": ["artifacts/worker-040/f1_strictness_adjudication/report.json",
                      "artifacts/worker-040/f1_strictness_adjudication/evidence.json",
                      f"{TARGET}#{PIN_F1[:12]}",
                      "artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py#95945acf84f6",
                      "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json#61206221ff23"],
    "next_falsifier": report["next_falsifier"]["statement"],
})

# ---- checkpoint (written before the close event so it can be referenced) ----
cp = {
    "task_id": TASK, "worker": "worker-040", "instance": INSTANCE,
    "at": iso, "checkpoint": 1,
    "lifecycle": "bounded execution worker; exited after one class-bound task",
    "assignment_taken": {
        "node_id": "F1", "gate": "G-FORM", "class_ids": ["AF-WCC-VAC-GEN"],
        "kind": ("class-bound task from the open G-FORM queue; no card in "
                 "comms/inbox/worker-040.jsonl"),
        "task": ("independent adjudication of the whole-curve 'strictly STRONGER' "
                 "claim and of the HF-040-04 vs F1-review-053 P053-5/C6 conflict"),
        "why_not_duplicative": ("predecessor worker-040 bound F1 cce9c601 and raised "
                               "HF-040-04; this instance executes its declared "
                               "falsifier, rejects the live contradicting review with a "
                               "static+executable audit, and no event had adjudicated "
                               "the P053-5/C6 model at the time of claim"),
    },
    "target": {"path": TARGET, "sha256": PIN_F1, "revision": 12,
               "mtime": report["pins"][TARGET]["mtime"], "stable_during_run": True},
    "verdict": "confirm_hf040_04", "score": 4.0,
    "checks_summary": report["checks_summary"],
    "hard_failures": ["HF-040-04 (confirmed)", "HF-040-04-CITE (confirmed)"],
    "rejected_claims": ["F1-review-053 P053-5 / C6"],
    "resolved_prior_findings": [],
    "escalated_prior_findings": ["W040-F1-A1 -> HF-040-04-CITE"],
    "artifacts": art_hashes,
    "events_emitted": [e["event_id"] for e in events] + [f"{ev}-status-close"],
    "independence": report["independence"],
    "drift_during_run": report["entry_exit_drift"],
    "next_falsifier": report["next_falsifier"],
    "hours_spent_estimate": 0.4,
    "authority_note": report["authority_note"],
}
with open(CHECKPOINT, "w", encoding="utf-8") as fh:
    json.dump(cp, fh, indent=1, sort_keys=True)
    fh.write("\n")
cp_hash = sha(CHECKPOINT)
kept = []
if os.path.exists(CP_LOG):
    for line in open(CP_LOG, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            if json.loads(line).get("task_id") == TASK:
                continue
        except Exception:
            pass
        kept.append(line)
kept.append(json.dumps({"at": iso, "worker": "worker-040",
                        "checkpoint_path": rel(CHECKPOINT), "task_id": TASK,
                        "verdict": "confirm_hf040_04", "score": 4.0,
                        "reviewed_sha256": PIN_F1}, sort_keys=True))
tmp_log = CP_LOG + ".tmp"
with open(tmp_log, "w", encoding="utf-8") as fh:
    fh.write("\n".join(kept) + "\n")
os.replace(tmp_log, CP_LOG)

events.append({
    "event_id": f"{ev}-status-close", "event_type": "status", "actor": "worker-040",
    "created_at": iso, "task_id": TASK, "node_id": "F1", "gate": "G-FORM",
    "class_ids": ["AF-WCC-VAC-GEN"], "status": "complete",
    "claims_completion": False, "hours": 0.4, "reviewed_sha256": PIN_F1,
    "summary": ("CHECKPOINT W040-F1-STRICTNESS-ADJ-04 complete and exiting. "
                "confirm_hf040_04, all 11 checks PASS, 0 drift: 0 tail-and-not-whole "
                "witnesses over all 355 preorders on 4 points (37464 tail == 37464 "
                "whole), controls fire (804 non-transitive, 22 non-causal), "
                "reviewer-053's discriminating model is a hardcoded literal dict whose "
                "configuration has 0 preorder realizations, and the W037V2-F1 citation "
                "is refuted by its own source. HF-040-04 and HF-040-04-CITE confirmed; "
                "P053-5/C6 rejected. No shared file modified; no node done and no gate "
                "verdict claimed."),
    "evidence_refs": [f"runtime/state/w040_strictness_adjudication_checkpoint.json#{cp_hash[:12]}",
                      f"{REVIEW}#{art_hashes[REVIEW][:12]}",
                      f"{TARGET}#{PIN_F1[:12]}"],
    "next_falsifier": report["next_falsifier"]["statement"],
})

existing = set()
if os.path.exists(OUTBOX):
    for line in open(OUTBOX, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

# ---- correction: the first emitter version used a wall-clock stamp, so the
# idempotency re-run appended a second batch (004525) under fresh ids.  Both
# batches were ingested before the duplication was noticed, so the second is
# withdrawn explicitly here rather than deleted from the stream.
DUP_STAMP = "20260912T004525"
dup_ids = [f"w040-strict-{DUP_STAMP}-task",
           f"w040-strict-{DUP_STAMP}-artifact-report.json",
           f"w040-strict-{DUP_STAMP}-artifact-evidence.json",
           f"w040-strict-{DUP_STAMP}-artifact-entry_hashes.json",
           f"w040-strict-{DUP_STAMP}-artifact-README.md",
           f"w040-strict-{DUP_STAMP}-artifact-run_adjudication.py",
           f"w040-strict-{DUP_STAMP}-artifact-emit_events.py",
           f"w040-strict-{DUP_STAMP}-review-f1",
           f"w040-strict-{DUP_STAMP}-claim",
           f"w040-strict-{DUP_STAMP}-status-close"]
dup_stale = {}
for line in open(OUTBOX, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
    except Exception:
        continue
    if d.get("event_id") == f"w040-strict-{DUP_STAMP}-artifact-emit_events.py":
        dup_stale["emit_events_sha256_in_withdrawn_batch"] = d.get("sha256")
    if d.get("event_id") == f"w040-strict-{DUP_STAMP}-status-close":
        for r in d.get("evidence_refs", []):
            if "w040_strictness_adjudication_checkpoint" in r:
                dup_stale["checkpoint_ref_in_withdrawn_batch"] = r
    if d.get("event_id") == f"{ev}-status-close":
        for r in d.get("evidence_refs", []):
            if "w040_strictness_adjudication_checkpoint" in r:
                dup_stale["checkpoint_ref_in_canonical_batch"] = r

CORRECTION_ID = f"{ev}-correction"
correction = {
    "event_id": CORRECTION_ID, "event_type": "status", "actor": "worker-040",
    "created_at": iso, "task_id": TASK, "node_id": "F1", "gate": "G-FORM",
    "class_ids": ["AF-WCC-VAC-GEN"], "status": "active", "claims_completion": False,
    "hours": 0.1, "reviewed_sha256": PIN_F1,
    "summary": ("CORRECTION to W040-F1-STRICTNESS-ADJ-04. The emitter's first "
                "version used a wall-clock event stamp; the idempotency re-run "
                "appended a second, content-identical batch under ids "
                "w040-strict-20260912T004525-*. Both batches were ingested before "
                "the duplication was noticed, so the 004525 batch is WITHDRAWN as a "
                "duplicate rather than deleted: the canonical batch is "
                "w040-strict-20260912T004521-*, whose findings, verdict "
                "(confirm_hf040_04) and evidence are unchanged. One hash binding in "
                "the withdrawn batch is stale by construction (it pinned the "
                "emitter before the determinism fix); the re-pinned authoritative "
                "hashes are in the evidence_refs below. No shared artifact was "
                "modified; no gate verdict or node completion is claimed."),
    "supersedes": dup_ids,
    "withdrawal_detail": {
        "cause": ("non-deterministic event stamp in emit_events.py v1; re-running "
                  "the emitter produced a new id set instead of being idempotent"),
        "content_changed_by_correction": False,
        "stale_bindings_in_withdrawn_batch": dup_stale,
        "re_pinned_artifacts": art_hashes,
    },
    "evidence_refs": [f"{k}#{v[:12]}" for k, v in art_hashes.items()],
    "next_falsifier": report["next_falsifier"]["statement"],
}

# include the correction id in the checkpoint before it is hashed, so the
# correction event can bind the checkpoint hash without circularity
cp["events_emitted"] = [e["event_id"] for e in events] + [CORRECTION_ID]
cp["corrections"] = {
    "withdrawn_duplicate_batch": dup_ids,
    "canonical_batch_stamp": stamp,
    "cause": correction["withdrawal_detail"]["cause"],
    "content_changed": False,
}
with open(CHECKPOINT, "w", encoding="utf-8") as fh:
    json.dump(cp, fh, indent=1, sort_keys=True)
    fh.write("\n")
cp_hash = sha(CHECKPOINT)
cp_ref = f"runtime/state/w040_strictness_adjudication_checkpoint.json#{cp_hash[:12]}"

# the checkpoint was rewritten to include the correction id, so re-bind the
# status-close event to the final hash: no stale checkpoint reference is emitted
for e in events:
    if e["event_id"] == f"{ev}-status-close":
        e["evidence_refs"] = [
            (cp_ref if "w040_strictness_adjudication_checkpoint" in r else r)
            for r in e["evidence_refs"]]
dup_stale["checkpoint_ref_in_canonical_batch_rebound_to"] = cp_ref
correction["withdrawal_detail"]["stale_bindings_in_withdrawn_batch"] = dup_stale
correction["rebinds"] = {f"{ev}-status-close": cp_ref}
correction["evidence_refs"] = correction["evidence_refs"] + [cp_ref]
events.append(correction)
added = 0
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, sort_keys=True) + "\n")
        added += 1
print(json.dumps({"task_id": TASK, "checkpoint": rel(CHECKPOINT),
                  "checkpoint_sha256": cp_hash, "events_added": added,
                  "events_total": len(events), "review": REVIEW,
                  "reviewed_sha256": PIN_F1}, indent=1))
