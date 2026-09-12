#!/usr/bin/env python3
"""Append AMEND-02 events (superseding artifact pins + status) and the exit checkpoint."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-059.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
CKPT_JSON = os.path.join(STATE, "w059_checkpoint_frozen_gen_exit.json")
CKPT_LOG = os.path.join(STATE, "w059_checkpoints.jsonl")
ART = "artifacts/worker-059/gform_frozen_gen_census"
NOW = "2026-09-12T01:18:30+08:00"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
FALSIFIER = ("Re-run verify_reproducibility.py: C1 static_pin_digest 7f23d65b5fc741ad, C3, C4, C5 must "
             "PASS; C2 passes iff the 213 pinned review files are byte-stable, else the drift set must "
             "match a fresh census and no stale-binding row may move. Falsified if static_pin_digest "
             "changes, any pinned input re-hashes differently, any expectation/mutant changes result, "
             "the HF-059-FROZEN-01 stale row set moves, or the canonical focused extract no longer "
             "derives from report.json.")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rp = lambda rel: os.path.join(ROOT, rel)  # noqa: E731
    focused_p = f"{ART}/stale_binding_census.json"
    harness_p = f"{ART}/check_frozen_gen_census.py"
    amend2_p = f"{ART}/reproducibility_amendment_02.json"
    h_focused, h_harness, h_amend2 = sha(rp(focused_p)), sha(rp(harness_p)), sha(rp(amend2_p))
    report_sha = sha(rp(f"{ART}/report.json"))
    old_focused = "322a23dd3d52"
    old_harness = "05bc648ef21f"

    events = [
        {"event_id": "w059-frozengen-20260912T0118-artifact-focused-supersede",
         "event_type": "artifact", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "artifact_type": "registry_legality_matrix", "path": focused_p, "sha256": h_focused,
         "validation_status": "unverified",
         "supersedes_sha256": old_focused,
         "description": ("Superseding pin. The 01:12:30 event pinned " + old_focused + ", which a "
                         "--corpus-from verification run had built from /tmp/w059_verify.json because "
                         "the harness wrote its focused extract to a fixed path. The canonical "
                         "derivation from the pinned report.json is " + h_focused[:12] + " (D2)."),
         "evidence_refs": [f"{ART}/reproducibility_amendment_02.json#{h_amend2[:12]}",
                           f"{ART}/report.json#{report_sha[:12]}"],
         "falsifier": FALSIFIER},
        {"event_id": "w059-frozengen-20260912T0118-artifact-harness-supersede",
         "event_type": "artifact", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "artifact_type": "instrument", "path": harness_p, "sha256": h_harness,
         "validation_status": "unverified",
         "supersedes_sha256": old_harness,
         "description": ("Root-cause fix for D2: focused output path now derives from --out and "
                         "--focused-from/--focused-out allow non-destructive regeneration. Smoke run "
                         "and verifier run both leave report.json and stale_binding_census.json "
                         "byte-unchanged. Predecessor bytes preserved at "
                         "snapshot/superseded.check_frozen_gen_census." + old_harness + ".py."),
         "evidence_refs": [f"{ART}/reproducibility_amendment_02.json#{h_amend2[:12]}",
                           f"{ART}/verify_reproducibility.py"]},
        {"event_id": "w059-frozengen-20260912T0118-artifact-amendment02",
         "event_type": "artifact", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "artifact_type": "instrument_amendment", "path": amend2_p, "sha256": h_amend2,
         "validation_status": "unverified",
         "description": ("AMEND-02: D2 focused-artifact clobber + D3 review-corpus drift (2/213 pinned "
                         "review files rewritten, 8 added); final anchors static_pin_digest "
                         "7f23d65b5fc741ad (reproducible) and review_census_digest edf82c4d35fa "
                         "(conditional on review-byte stability); HF-059-FROZEN-01 unaffected."),
         "evidence_refs": [f"{ART}/report.json#{report_sha[:12]}"],
         "falsifier": FALSIFIER},
        {"event_id": "w059-frozengen-20260912T0118-status-exit",
         "event_type": "status", "created_at": NOW, "actor": "worker-059",
         "node_id": "F1,F2a,F2b", "class_id": CLASSES, "gate": "G-FORM",
         "status": "active", "hours": 0.5,
         "checkpoint_id": "w059-ckpt-frozengen-exit-20260912T0118",
         "task_id": "W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01",
         "task_complete_pending_review": True,
         "summary": ("FINAL CHECKPOINT + EXIT. Deliverable stands: CF-27 FROZEN rev29 generation move "
                     "measured (same revision; 5 superseded + 2 added pins; 0 schema pins moved; live "
                     "50/50 resolve; predecessor 43/48; predecessor bytes 5/5 recoverable), pinned "
                     "213-review binding census (33 stale / 32 generation-B / 148 unbound), and "
                     "HF-059-FROZEN-01: F2a-review-worker-017 is a full-schema accept written 4 s "
                     "after the freeze that still binds FROZEN 3d9e3d77fd87 and VARIANT_REGISTRY "
                     "5eb42f9a384a. Two instrument defects found by executing the emitted falsifier "
                     "before exit (D2 focused clobber, D3 review-corpus drift) are recorded in "
                     "AMEND-02 with superseding pins; static_pin_digest 7f23d65b5fc741ad is the "
                     "reproducible anchor (C1/C3/C4/C5 PASS). No canonical file modified; no "
                     "status=done, no validation_status=passed, no gate verdict claimed."),
         "evidence_refs": [f"{ART}/report.json#{report_sha[:12]}",
                           f"{ART}/stale_binding_census.json#{h_focused[:12]}",
                           f"{ART}/reproducibility_amendment_02.json#{h_amend2[:12]}",
                           f"{ART}/verify_reproducibility.py"],
         "next_falsifier": FALSIFIER},
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

    ckpt = {"checkpoint_id": "w059-ckpt-frozengen-exit-20260912T0118", "actor": "worker-059",
            "task_id": "W059-GFORM-FROZEN-GEN-BINDING-CENSUS-01", "phase": "final-exit",
            "created_at": NOW, "status": "active", "task_complete_pending_review": True, "hours": 0.5,
            "final_pins": {f"{ART}/report.json": report_sha,
                           f"{ART}/stale_binding_census.json": h_focused,
                           f"{ART}/check_frozen_gen_census.py": h_harness,
                           f"{ART}/review_FROZEN_gen_census.json": sha(rp(f"{ART}/review_FROZEN_gen_census.json")),
                           f"{ART}/README.md": sha(rp(f"{ART}/README.md")),
                           f"{ART}/reproducibility_amendment.json": sha(rp(f"{ART}/reproducibility_amendment.json")),
                           f"{ART}/reproducibility_amendment_02.json": h_amend2,
                           f"{ART}/verify_reproducibility.py": sha(rp(f"{ART}/verify_reproducibility.py"))},
            "static_pin_digest": "7f23d65b5fc741ad0b1a7f0f2b353a1d8a442b18514e5d702778b9b7d05ee545",
            "review_census_digest": "edf82c4d35fac27e9753e2d02b1a7ca10d82cc1ab87a9877d7a716f87a65f6f8",
            "headline": "HF-059-FROZEN-01 F2a-review-worker-017 post-freeze stale full-schema accept",
            "events_emitted": [e["event_id"] for e in events],
            "canonical_files_written": [], "next_falsifier": FALSIFIER}
    with open(CKPT_JSON, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1, sort_keys=False)
        fh.write("\n")
    with open(CKPT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"checkpoint_id": ckpt["checkpoint_id"], "actor": "worker-059",
                             "task_id": ckpt["task_id"], "created_at": NOW, "status": "active",
                             "task_complete_pending_review": True,
                             "checkpoint_path": os.path.relpath(CKPT_JSON, ROOT),
                             "checkpoint_sha256": sha(CKPT_JSON)}) + "\n")
    print(f"AMEND-02 events: {len(events)} built, {added} appended")
    print("checkpoint:", os.path.relpath(CKPT_JSON, ROOT), sha(CKPT_JSON)[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
