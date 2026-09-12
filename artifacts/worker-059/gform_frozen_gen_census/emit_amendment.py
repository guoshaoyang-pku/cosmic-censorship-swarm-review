#!/usr/bin/env python3
"""Append the W059 reproducibility-amendment events + amendment checkpoint (idempotent).

Emits: artifact(reproducibility_amendment.json), artifact(verify_reproducibility.py),
status(amendment note). Writes only the worker outbox and runtime/state.
"""
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-059.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
CKPT_JSON = os.path.join(STATE, "w059_checkpoint_frozen_gen_amend.json")
CKPT_LOG = os.path.join(STATE, "w059_checkpoints.jsonl")
ART = "artifacts/worker-059/gform_frozen_gen_census"
NOW = "2026-09-12T01:16:30+08:00"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"

AMENDED_FALSIFIER = (
    "Re-run verify_reproducibility.py: falsified if C1-C5 do not all pass, i.e. if static_pin_digest "
    "differs from 7f23d65b5fc741ad, if review_census_digest differs from edf82c4d35fa, if any "
    "expectation or mutant/control result changes, or if any of the six pinned inputs re-hashes "
    "differently. The as-emitted measurement_digest da717446 is deprecated as a reproducibility "
    "anchor (superseded_recovery_scan copy lists are live-tree dependent) but remains valid as a "
    "content hash at emission time."
)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rp = lambda rel: os.path.join(ROOT, rel)  # noqa: E731
    amend_p = f"{ART}/reproducibility_amendment.json"
    verify_p = f"{ART}/verify_reproducibility.py"
    h_amend, h_verify = sha(rp(amend_p)), sha(rp(verify_p))
    report_sha = sha(rp(f"{ART}/report.json"))

    events = [
        {"event_id": "w059-frozengen-20260912T0116-artifact-amendment",
         "event_type": "artifact", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "artifact_type": "instrument_amendment", "path": amend_p, "sha256": h_amend,
         "validation_status": "unverified",
         "description": ("Self-detected defect in the as-emitted measurement_digest anchor: it "
                         "included live-tree-dependent recovery copy lists, so it is not reproducible "
                         "under --corpus-from. Records the pin-stable replacement static_pin_digest "
                         "7f23d65b5fc741ad and the preserved review_census_digest edf82c4d35fa; "
                         "findings HF-059-FROZEN-01 and the census are unaffected."),
         "evidence_refs": [f"{ART}/report.json#{report_sha[:12]}",
                           f"{ART}/verify_reproducibility.py#{h_verify[:12]}"],
         "falsifier": AMENDED_FALSIFIER},
        {"event_id": "w059-frozengen-20260912T0116-artifact-verifier",
         "event_type": "artifact", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "artifact_type": "instrument", "path": verify_p, "sha256": h_verify,
         "validation_status": "unverified",
         "description": ("Independent reproducibility verifier: checks static_pin_digest against a "
                         "fresh --corpus-from run, re-checks review_census_digest, expectations and "
                         "the six pinned input hashes (C1-C5, exit 0 iff all pass)."),
         "evidence_refs": [f"{ART}/reproducibility_amendment.json#{h_amend[:12]}"],
         "falsifier": AMENDED_FALSIFIER},
        {"event_id": "w059-frozengen-20260912T0116-status-amendment",
         "event_type": "status", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "status": "active", "hours": 0.1,
         "checkpoint_id": "w059-ckpt-frozengen-amend-20260912T0116",
         "summary": ("AMENDMENT + CHECKPOINT. Before exit, the emitted falsifier was executed against "
                     "the pinned corpus and failed for one field: measurement_digest is not "
                     "reproducible because it covered superseded_recovery_scan copy lists that depend "
                     "on the live artifact tree. Recorded as an instrument defect (not silently "
                     "redefined); pin-stable anchor static_pin_digest=7f23d65b5fc741ad and census "
                     "digest edf82c4d35fa both reproduce (verify_reproducibility.py C1-C5 PASS). "
                     "HF-059-FROZEN-01 (F2a-review-worker-017 stale full-schema accept) and the "
                     "213-review census are unaffected. No canonical file modified; no status=done, "
                     "no validation_status=passed, no gate verdict claimed."),
         "evidence_refs": [f"{ART}/reproducibility_amendment.json#{h_amend[:12]}",
                           f"{ART}/verify_reproducibility.py#{h_verify[:12]}",
                           f"{ART}/report.json#{report_sha[:12]}"],
         "next_falsifier": AMENDED_FALSIFIER},
    ]

    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, "r", encoding="utf-8"):
            if line.strip():
                try:
                    existing.add(json.loads(line)["event_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    added = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] not in existing:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
                added += 1

    ckpt = {"checkpoint_id": "w059-ckpt-frozengen-amend-20260912T0116", "actor": "worker-059",
            "task_id": "W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01", "phase": "amendment",
            "created_at": NOW, "status": "active", "task_complete_pending_review": True, "hours": 0.1,
            "amendment": f"{ART}/reproducibility_amendment.json", "amendment_sha256": h_amend,
            "verifier": f"{ART}/verify_reproducibility.py", "verifier_sha256": h_verify,
            "static_pin_digest": "7f23d65b5fc741ad0b1a7f0f2b353a1d8a442b18514e5d702778b9b7d05ee545",
            "review_census_digest": "edf82c4d35fac27e9753e2d02b1a7ca10d82cc1ab87a9877d7a716f87a65f6f8",
            "deprecated_anchor": "measurement_digest da717446 (live-tree copy lists)",
            "events_emitted": [e["event_id"] for e in events],
            "canonical_files_written": [],
            "next_falsifier": AMENDED_FALSIFIER}
    with open(CKPT_JSON, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1, sort_keys=False)
        fh.write("\n")
    with open(CKPT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "actor": "worker-059",
                             "task_id": ckpt["task_id"], "created_at": NOW, "status": "active",
                             "task_complete_pending_review": True,
                             "checkpoint_path": os.path.relpath(CKPT_JSON, ROOT),
                             "checkpoint_sha256": sha(CKPT_JSON)}) + "\n")
    print(f"amendment events: {len(events)} built, {added} appended")
    print("checkpoint:", os.path.relpath(CKPT_JSON, ROOT), sha(CKPT_JSON)[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
