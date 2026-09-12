#!/usr/bin/env python3
"""Emit W023-F2B-REVIEW-PROVENANCE-01 events to comms/outbox/worker-023.jsonl.

Validates every event against research_map/schemas.py before writing (worker events cannot set
status=done, validation_status=passed, or a gate verdict). Also writes SHA256SUMS for the task
directory. Idempotent per invocation only by timestamped event ids; re-running after a corpus
move is expected and produces a new observation, never an edit of an old one.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research_map"))
import schemas  # noqa: E402

ACTOR = "worker-023"
NODE = "F2b"
CLASS = "AF-SCC-C0-VAC-GEN"
CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]
GATE = "G-FORM"
OUTBOX = os.path.join(REPO, "comms", "outbox", "worker-023.jsonl")
TASK = "W023-F2B-REVIEW-PROVENANCE-01"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def main() -> int:
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    prefix = f"w23-revprov-{stamp}"
    rel = lambda p: os.path.relpath(p, REPO)  # noqa: E731

    files = {
        "instrument": ROOT + "/review_provenance_ledger.py",
        "report": ROOT + "/evidence/report.json",
        "selftest": ROOT + "/evidence/selftest.json",
        "window": ROOT + "/evidence/w036_window_delta.json",
        "check": ROOT + "/evidence/check_seed.json",
        "verify": ROOT + "/evidence/verify.json",
        "readme": ROOT + "/README.md",
        "ledger": ROOT + "/ledger.jsonl",
    }
    h = {k: sha256_file(v) for k, v in files.items()}
    refs = {
        "instrument": f"{rel(files['instrument'])}#{h['instrument'][:12]}",
        "report": f"{rel(files['report'])}#{h['report'][:12]}",
        "selftest": f"{rel(files['selftest'])}#{h['selftest'][:12]}",
        "window": f"{rel(files['window'])}#{h['window'][:12]}",
        "check": f"{rel(files['check'])}#{h['check'][:12]}",
        "verify": f"{rel(files['verify'])}#{h['verify'][:12]}",
        "readme": f"{rel(files['readme'])}#{h['readme'][:12]}",
        "ledger": f"{rel(files['ledger'])}#{h['ledger'][:12]}",
    }
    summary = json.load(open(files["report"]))
    counts = summary["corpus_snapshot"]["post_seed_check"]
    window = summary["window_delta_vs_worker036_snapshot"]["counts"]
    falsifier = summary["falsifier"]
    checkpoint_ref = "runtime/state/w023_checkpoint_6.json"

    events = [
        {"event_id": f"{prefix}-artifact-instrument", "event_type": "artifact",
         "artifact_type": "review_provenance_instrument", "path": rel(files["instrument"]),
         "sha256": h["instrument"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": "Content-addressed review-verdict provenance ledger: seed/check/verify/"
                    "diff-manifest/selftest; distinguishes SUPERSEDED (hash-bearing pointer, "
                    "exit 0) from REWRITTEN (silent byte loss, fail closed) and preserves every "
                    "seeded byte sequence write-once.",
         "evidence_refs": [refs["report"], refs["selftest"], refs["verify"]],
         "falsifier": falsifier},
        {"event_id": f"{prefix}-artifact-report", "event_type": "artifact",
         "artifact_type": "measurement_report", "path": rel(files["report"]),
         "sha256": h["report"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": f"Measured: selftest 18/18; corpus {summary['corpus_snapshot']['n_review_files']} "
                    f"files all UNCHANGED at digest "
                    f"{summary['corpus_snapshot']['snapshot_digest'][:12]}; store "
                    f"{summary['corpus_snapshot']['store_entries']} byte sequences verify ok; "
                    f"worker-036 window delta {window}; F2b-072 flip hash-acknowledged in rev2 "
                    f"and in the accepted stream (#7487f310d208).",
         "evidence_refs": [refs["check"], refs["verify"], refs["selftest"], refs["window"]],
         "falsifier": falsifier},
        {"event_id": f"{prefix}-artifact-selftest", "event_type": "artifact",
         "artifact_type": "control_evidence", "path": rel(files["selftest"]),
         "sha256": h["selftest"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": "18/18 synthetic-corpus controls: silent rewrite flagged (exit 2), "
                    "hash-acknowledged supersession accepted (exit 0), touch != rewrite, "
                    "restore detected, add/remove detected, store tamper caught, manifest diff.",
         "evidence_refs": [refs["report"]], "falsifier": falsifier},
        {"event_id": f"{prefix}-artifact-window", "event_type": "artifact",
         "artifact_type": "window_delta", "path": rel(files["window"]),
         "sha256": h["window"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": f"Live corpus vs worker-036 pinned snapshot (MANIFEST "
                    f"beab69e12028): {window}. A0-review-worker-089 SUPERSEDED (carries "
                    f"9cade89e600c); A0-review-final-verify REWRITTEN (prose supersession only, "
                    f"no replaced-hash token).",
         "evidence_refs": [refs["report"], refs["check"]], "falsifier": falsifier},
        {"event_id": f"{prefix}-artifact-check", "event_type": "artifact",
         "artifact_type": "drift_check", "path": rel(files["check"]),
         "sha256": h["check"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": f"Final seed-time check: {counts} at snapshot digest "
                    f"{summary['corpus_snapshot']['snapshot_digest'][:12]}; exit 0 (no "
                    f"REWRITTEN/REMOVED).",
         "evidence_refs": [refs["verify"]], "falsifier": falsifier},
        {"event_id": f"{prefix}-artifact-verify", "event_type": "artifact",
         "artifact_type": "store_integrity", "path": rel(files["verify"]),
         "sha256": h["verify"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": f"Write-once store verify ok=True over "
                    f"{summary['corpus_snapshot']['store_entries']} entries; 0 store-name "
                    f"mismatches, 0 dangling ledger records.",
         "evidence_refs": [refs["check"]], "falsifier": falsifier},
        {"event_id": f"{prefix}-artifact-readme", "event_type": "artifact",
         "artifact_type": "task_readme", "path": rel(files["readme"]),
         "sha256": h["readme"], "validation_status": "unverified", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "summary": "Task rationale, semantics table, case studies, exact reproduce commands, "
                    "limits and falsifier.",
         "evidence_refs": [refs["report"]], "falsifier": falsifier},
        {"event_id": f"{prefix}-claim", "event_type": "claim",
         "class_id": CLASS, "class_ids": CLASSES, "node_id": NODE, "gate": GATE,
         "conclusion_type": "formal_model",
         "statement": "At the F2b rev13 pin b2ab6acb2bbe, reviews/*.json verdict files are "
                      "mutable under fixed names; a content-addressed write-once ledger seeded "
                      "over the live corpus preserves every observed verdict byte sequence and "
                      "classifies a byte move as SUPERSEDED when the replacement contains the "
                      "replaced sha256 as a hex token (exit 0) or REWRITTEN when it does not "
                      "(fail closed). Measured: 18/18 controls; 240 live files, 242 preserved "
                      "byte sequences, store verify ok; over the worker-036 window 190 "
                      "UNCHANGED / 48 ADDED / 1 SUPERSEDED / 1 REWRITTEN. The CF-31 F2b flip is "
                      "hash-acknowledged: reviews/F2b-review-worker-072-rev29.json rev2 carries "
                      "supersedes_sha256 7487f310d208... (supersedes_verdict accept) and the "
                      "accepted stream holds the accept event w072-2026-09-12T01:10:13+08:00-"
                      "review-f2b received 01:10:14, so the withdrawn accept is a documented "
                      "self-supersession, not a silent loss; only the rev1 bytes are gone.",
         "assumptions": [
             "corpus is the live reviews/*.json glob read from the repo root; the ledger "
             "records the paths and sha256 it actually saw",
             "acknowledgement is judged mechanically: the replaced sha256 must appear in the "
             "replacement bytes as a hex token of at least 12 chars",
             "the worker-036 manifest comparison uses basename keys and its pinned bytes; a "
             "window delta is a snapshot comparison, not a full history",
             "this is worker-level evidence; coverage and gate adjudication stay with the "
             "audit lead and the controller",
         ],
         "artifact_refs": [refs["instrument"], refs["report"], refs["selftest"],
                           refs["window"], refs["check"], refs["verify"], refs["ledger"]],
         "evidence_refs": [refs["report"], refs["selftest"], refs["window"], refs["verify"],
                           "research_map/events.jsonl#w072-2026-09-12T01:10:13+08:00-review-f2b"],
         "falsifier": falsifier},
        {"event_id": f"{prefix}-status", "event_type": "status", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE, "status": "active",
         "hours": 0.5,
         "summary": "CHECKPOINT + EXIT. One bounded class-bound task (W023-F2B-REVIEW-"
                    "PROVENANCE-01), self-selected from CF-31's root cause and worker-036's "
                    "byte-preservation gap: review-verdict provenance ledger + drift detector "
                    "(18/18 controls, 242 byte sequences preserved, verify ok), live window "
                    "delta vs worker-036 (190/48/1/1), and a correction that the worker-072 F2b "
                    "flip is hash-acknowledged in rev2 and in the accepted stream, not silent. "
                    "No inbox card existed for worker-023; no canonical path written.",
         "evidence_refs": [refs["report"], refs["selftest"], refs["check"], refs["verify"],
                           refs["window"], checkpoint_ref],
         "next_falsifier": falsifier},
        {"event_id": f"{prefix}-blocker", "event_type": "blocker", "node_id": NODE,
         "class_id": CLASS, "class_ids": CLASSES, "gate": GATE,
         "description": "reviews/*.json has no immutability or supersession-pointer policy: a "
                        "verdict byte sequence can be replaced in place with no durable copy "
                        "(worker-072 rev1 accept 7487f310d208...) and one in-window A0 rewrite "
                        "(A0-review-final-verify) replaces its predecessor with a prose-only "
                        "'supersedes' note that carries no hash. The ledger now preserves bytes "
                        "from its seed forward, but nothing yet runs it at pass boundaries or "
                        "requires hash-bearing pointers.",
         "needed_to_unblock": "Controller/audit-lead adoption (worker cannot set policy): run "
                              "artifacts/worker-023/review_provenance_ledger/review_provenance_"
                              "ledger.py check immediately before and after each controller "
                              "pass; treat REWRITTEN/REMOVED as making the affected coverage "
                              "count non-re-derivable; require replacement verdict bytes at an "
                              "occupied path to carry the replaced file's sha256 "
                              "(supersedes_sha256 or revision_history).",
         "evidence_refs": [refs["report"], refs["window"], refs["check"], refs["verify"]],
         "falsifier": falsifier},
    ]

    created = now_iso()
    for e in events:
        e["actor"] = ACTOR
        e["created_at"] = created
    for e in events:
        schemas.validate_event(e)  # raises SchemaError on any invalid event
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # SHA256SUMS over the deliverables (store entries are self-verifying by filename)
    lines = []
    for k in sorted(files):
        lines.append(f"{h[k]}  {rel(files[k])}")
    lines.append("# store/: 242 entries, each named by its own sha256 (see evidence/verify.json)")
    with open(ROOT + "/SHA256SUMS", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({"events_emitted": len(events), "event_ids": [e["event_id"] for e in events],
                      "outbox": rel(OUTBOX), "hashes": h}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
