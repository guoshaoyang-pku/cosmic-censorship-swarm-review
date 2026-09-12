#!/usr/bin/env python3
"""Repair pass: add the schema-required `reviewer` field to the emitted review
event, then rebuild events.jsonl, KEY_MANIFEST.json and the checkpoint hashes.
Old outbox lines from earlier worker-089 tasks are preserved byte-for-byte."""
import datetime as dt
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TASK = "W089-F2A-REV12-REVIEW-03"
CLASS = "AF-SCC-C2-VAC-GEN"
STAMP = "w089-20260912T003959"
TARGET = "schemas/af_scc_c2_vacuum.yaml"


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


outbox = os.path.join(REPO, "comms/outbox/worker-089.jsonl")
with open(outbox, encoding="utf-8") as fh:
    lines = fh.read().splitlines()

patched, new_events, changed = [], [], 0
for ln in lines:
    if not ln.strip():
        continue
    event = json.loads(ln)
    if event.get("event_id", "").startswith(STAMP):
        if event["event_type"] == "review" and "reviewer" not in event:
            event["reviewer"] = "worker-089"
            changed += 1
        ln = json.dumps(event, sort_keys=True)
        new_events.append(event)
    patched.append(ln)

with open(outbox, "w", encoding="utf-8") as fh:
    fh.write("\n".join(patched) + "\n")
with open(os.path.join(HERE, "events.jsonl"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(json.dumps(e, sort_keys=True) for e in new_events) + "\n")

report = json.load(open(os.path.join(HERE, "f2a_review_report.json")))
target_sha = report["target"]["sha256"]
frozen_sha = report["frozen_manifest"]["sha256"]
rel = {
    "checker": "artifacts/worker-089/f2a_rev12_review/check_f2a_rev12.py",
    "report": "artifacts/worker-089/f2a_rev12_review/f2a_review_report.json",
    "readme": "artifacts/worker-089/f2a_rev12_review/README.md",
    "review": "artifacts/worker-089/f2a_rev12_review/REVIEW.json",
    "snapshot": f"artifacts/worker-089/f2a_rev12_review/pinned/af_scc_c2_vacuum.{target_sha[:12]}.yaml",
    "frozen_snapshot": "artifacts/worker-089/f2a_rev12_review/pinned/FROZEN.rev28.json",
    "emitter": "artifacts/worker-089/f2a_rev12_review/emit_evidence.py",
    "events": "artifacts/worker-089/f2a_rev12_review/events.jsonl",
}
manifest = {
    "schema_version": "1.0",
    "task_id": TASK,
    "worker": "worker-089",
    "class_id": CLASS,
    "node_id": "F2a",
    "gate": "G-FORM",
    "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    "target": {"path": TARGET, "sha256": target_sha, "revision": 12},
    "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": frozen_sha, "revision": 28},
    "files": {p: sha256_file(os.path.join(REPO, p)) for p in rel.values()},
}
with open(os.path.join(HERE, "KEY_MANIFEST.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=1, sort_keys=True)

all_files = {}
for root, _dirs, files in os.walk(HERE):
    for f in files:
        full = os.path.join(root, f)
        all_files[os.path.relpath(full, REPO)] = sha256_file(full)

cp_path = os.path.join(REPO, "runtime/state/w089_checkpoint_3.json")
cp = json.load(open(cp_path))
cp["artifacts"] = all_files
cp["reviewer_field_repaired_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
with open(cp_path, "w", encoding="utf-8") as fh:
    json.dump(cp, fh, indent=1, sort_keys=True)

print(json.dumps({"patched_review_events": changed, "outbox_lines": len(patched),
                  "new_events": len(new_events), "manifest_files": len(manifest["files"]),
                  "artifact_files": len(all_files)}, indent=1))
