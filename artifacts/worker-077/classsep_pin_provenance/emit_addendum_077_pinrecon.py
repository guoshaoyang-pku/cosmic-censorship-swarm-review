#!/usr/bin/env python3
"""Addendum for W077-CLASSSEP-PINRECON-01: refresh README + entry_hashes after the README
pin-table was completed post-emission (hash hygiene), and record the new hashes.

Writes only:
  artifacts/worker-077/classsep_pin_provenance/entry_hashes.json
  comms/outbox/worker-077.jsonl            (append)
  runtime/state/worker-077_classsep_pin_provenance_checkpoint_v2.json
  runtime/state/w077_checkpoints.jsonl     (append)
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-077/classsep_pin_provenance"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
TS = datetime.now(TZ).isoformat(timespec="seconds")
TAG = "w077-pinrecon-addendum-" + datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
TASK_ID = "W077-CLASSSEP-PINRECON-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASS_IDS)


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


report = json.loads((OUT / "report.json").read_text())
entry = json.loads((OUT / "entry_hashes.json").read_text())
paths = {
    "report": "artifacts/worker-077/classsep_pin_provenance/report.json",
    "report_run2": "artifacts/worker-077/classsep_pin_provenance/report.run2.json",
    "instrument": "artifacts/worker-077/classsep_pin_provenance/reconcile_classsep_pin.py",
    "readme": "artifacts/worker-077/classsep_pin_provenance/README.md",
    "determinism": "artifacts/worker-077/classsep_pin_provenance/determinism.json",
    "entry_hashes": "artifacts/worker-077/classsep_pin_provenance/entry_hashes.json",
}
hashes = {k: sha(p) for k, p in paths.items() if k != "entry_hashes"}
hashes["emit_script_1"] = sha("artifacts/worker-077/classsep_pin_provenance/emit_events_077_pinrecon.py")
hashes["emit_script_2"] = sha("artifacts/worker-077/classsep_pin_provenance/emit_addendum_077_pinrecon.py")
entry["at"] = TS
entry["outputs"] = {k: hashes[k] for k in
                    ("report", "report_run2", "instrument", "readme", "determinism",
                     "emit_script_1", "emit_script_2")}
entry["addendum"] = ("README pin table completed after the first emission (the entry_hashes "
                     "self-hash was removed to break the circular reference); entry outputs and "
                     "emitter hashes refreshed.")
(OUT / "entry_hashes.json").write_text(json.dumps(entry, indent=1, sort_keys=True) + "\n")
hashes["entry_hashes"] = sha(paths["entry_hashes"])

evidence = [f"{paths[k]}#sha256:{hashes[k]}" for k in
            ("report", "instrument", "readme", "determinism", "entry_hashes")]

events = []


def add(ev):
    ev.setdefault("actor", "worker-077")
    ev.setdefault("class_id", CLASS_ID)
    ev.setdefault("class_ids", CLASS_IDS)
    ev.setdefault("node_id", "A1")
    ev.setdefault("gate", "G-AUDIT")
    validate_event(ev)
    events.append(ev)


add({
    "event_id": f"{TAG}-artifact-readme-v2", "event_type": "artifact", "created_at": TS,
    "artifact_type": "report", "path": paths["readme"], "sha256": hashes["readme"],
    "validation_status": "unverified",
    "note": ("Supersedes the README hash in the first emission (9bf5ff6d): the pins paragraph now "
             "cites the four concrete run pins and no longer leaves an incomplete '#...' for "
             "entry_hashes.json; the self-hash is omitted to avoid a circular reference. Content "
             "and verdict unchanged."),
    "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
})
add({
    "event_id": f"{TAG}-artifact-entry-hashes-v2", "event_type": "artifact", "created_at": TS,
    "artifact_type": "entry_hashes", "path": paths["entry_hashes"],
    "sha256": hashes["entry_hashes"], "validation_status": "unverified",
    "note": "Refreshed outputs map (README 9bf5ff6d -> " + hashes["readme"] + ") and both emitter hashes.",
    "evidence_refs": [f"{paths['report']}#sha256:{hashes['report']}"],
})
add({
    "event_id": f"{TAG}-status", "event_type": "status", "created_at": TS, "status": "active",
    "hours": 0.75,
    "summary": ("Addendum to W077-CLASSSEP-PINRECON-01 (no verdict change): the README pin table "
                "was completed after emission to remove an incomplete self-referential hash, and "
                "entry_hashes.json was refreshed. New hashes: README " + hashes["readme"]
                + ", entry_hashes " + hashes["entry_hashes"] + ". The measured result, checks, "
                "controls and falsifier are unchanged."),
    "evidence_refs": evidence, "next_falsifier": report["falsifier"],
})

with open(ROOT / "comms/outbox/worker-077.jsonl", "a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

checkpoint = {
    "checkpoint": "v2",
    "at": TS, "worker": "worker-077",
    "lifecycle": "worker-077-20260912T011000-968807",
    "task_id": TASK_ID, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS_ID,
    "verdict": "measurement_complete",
    "result": {
        "attested_digest": report["attested_digest"],
        "unattested_digest": report["unattested_digest"],
        "orphan_citation_sites": report["verdict"]["orphan_citation_sites"],
        "orphan_full_cited": report["verdict"]["orphan_fulls_cited"],
        "sweep_files": report["sweep"]["files_scanned"],
        "content_digest": report["content_digest"],
        "checks_pass_total": [sum(1 for c in report["checks"] if c["status"] == "PASS"),
                              len(report["checks"])],
        "controls_pass_total": [sum(1 for c in report["controls"] if c["status"] == "PASS"),
                                len(report["controls"])],
    },
    "files": hashes,
    "pins": entry["pins"],
    "change": "README pin table completed post-emission; entry_hashes refreshed; events appended, no rewrite.",
    "next_falsifier": report["falsifier"],
    "non_claims": report["non_claims"],
}
(ROOT / "runtime/state/worker-077_classsep_pin_provenance_checkpoint_v2.json").write_text(
    json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with open(ROOT / "runtime/state/w077_checkpoints.jsonl", "a") as f:
    f.write(json.dumps(checkpoint, sort_keys=True) + "\n")

print(json.dumps({"events_written": [e["event_id"] for e in events],
                  "readme": hashes["readme"], "entry_hashes": hashes["entry_hashes"]}, indent=1))
