#!/usr/bin/env python3
"""Emit worker-071 F2b rev13 review checkpoint + outbox events (idempotent by event_id).

Writes:
  runtime/state/worker-071_F2b_checkpoint.json
  appends to comms/outbox/worker-071.jsonl   (artifact x5, review, status)
Re-running skips event_ids already present.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-071.jsonl"
CKPT = ROOT / "runtime/state/worker-071_F2b_checkpoint.json"
NOW = "2026-09-12T01:11:30+08:00"
TARGET = "schemas/af_scc_c0_vacuum.yaml"
PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


FILES = {
    "verdict": ROOT / "reviews/F2b-review-rev13-worker-071.json",
    "prereg": BASE / "PREREGISTRATION.json",
    "instrument": BASE / "review_f2b_rev13.py",
    "results": BASE / "review_checks.json",
    "firstrun": BASE / "review_checks.firstrun-instrument-bugs.json",
    "emit": BASE / "emit_events.py",
}
H = {k: sha(v) for k, v in FILES.items()}

checkpoint = {
    "checkpoint_kind": "worker_review_checkpoint",
    "worker": "worker-071",
    "slot": "071",
    "assignment_event_ids": [],
    "pre_dispatch_for": "astra-life05-verify-gform-r3",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "created_at": NOW,
    "phase": "done",
    "hours_spent": 0.5,
    "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
    "target": {
        "path": TARGET,
        "pin_sha256": PIN,
        "sha256_before_read": PIN,
        "sha256_after_read": PIN,
        "sha256_after_all_probes": PIN,
        "mirror_path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "mirror_sha256": PIN,
        "schema_revision": 13,
        "frozen_manifest": "artifacts/formulation/FROZEN.json",
        "frozen_sha256": FROZEN_PIN,
        "frozen_revision": 29,
        "frozen_rev29_matches_live_bytes": True,
    },
    "verdict": "accept",
    "score": 4,
    "hard_failure_ids": [],
    "finding_ids": ["F-071-F2B-01", "F-071-F2B-02", "F-071-F2B-03", "F-071-F2B-04",
                    "F-071-F2B-05", "F-071-F2B-06", "F-071-F2B-07"],
    "checks": {"passed": 26, "total": 26, "control_families_fired": 6, "control_families_total": 6,
               "moved_during_run": []},
    "outputs": {
        "verdict_file": {"path": rel(FILES["verdict"]), "sha256": H["verdict"]},
        "preregistration": {"path": rel(FILES["prereg"]), "sha256": H["prereg"]},
        "instrument": {"path": rel(FILES["instrument"]), "sha256": H["instrument"]},
        "check_results": {"path": rel(FILES["results"]), "sha256": H["results"]},
        "first_run_before_instrument_corrections": {"path": rel(FILES["firstrun"]), "sha256": H["firstrun"]},
    },
    "independence": {"author_of_target": False, "read_other_f2b_verdicts": False,
                     "target_edit": "none", "blind": True},
    "next_falsifier": "re-run review_f2b_rev13.py at the pins; any check flip, non-firing control, or pin move voids the verdict; a demonstrable misbinding via F-071-F2B-01 promotes the finding to a hard failure",
    "authority_note": "Worker verdict; does not set node status, validation_status=passed, or any gate verdict.",
}
CKPT.write_text(json.dumps(checkpoint, indent=1), encoding="utf-8")
ckpt_sha = sha(CKPT)

ev = []


def add(e):
    ev.append(e)


ref = lambda p, k: f"{rel(FILES[p])}#{H[k][:12]}"

add({"event_id": "w071-f2brev13-20260912T0111-artifact-prereg", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
     "artifact_type": "preregistration", "path": rel(FILES["prereg"]), "sha256": H["prereg"],
     "validation_status": "unverified",
     "note": "Checks C01-C26, six control families, decision rule and falsifier fixed before the run (mtime precedes review_checks.json).",
     "evidence_refs": [ref("prereg", "prereg")]})
add({"event_id": "w071-f2brev13-20260912T0111-artifact-instrument", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
     "artifact_type": "verification_instrument", "path": rel(FILES["instrument"]), "sha256": H["instrument"],
     "validation_status": "unverified",
     "note": "Independent stdlib+PyYAML instrument; no project module imported; canonical structural checker invoked as corroboration only.",
     "evidence_refs": [ref("instrument", "instrument")]})
add({"event_id": "w071-f2brev13-20260912T0111-artifact-checks", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
     "artifact_type": "measurement_data", "path": rel(FILES["results"]), "sha256": H["results"],
     "validation_status": "unverified",
     "note": "26/26 checks pass, 6/6 control families fire, t0==t1 frame, moved_during_run=[]; C06/C15 first-run implementation bugs preserved separately.",
     "evidence_refs": [ref("results", "results")]})
add({"event_id": "w071-f2brev13-20260912T0111-artifact-firstrun", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
     "artifact_type": "superseded_measurement_data", "path": rel(FILES["firstrun"]), "sha256": H["firstrun"],
     "validation_status": "unverified",
     "note": "Superseded first run: C06/C15 predicates had implementation bugs (dict vs list; plural substring; quoted 'suitable'). Criterion text unchanged; kept for audit.",
     "evidence_refs": [ref("firstrun", "firstrun")]})
add({"event_id": "w071-f2brev13-20260912T0111-artifact-verdict", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
     "artifact_type": "independent_review_verdict", "path": rel(FILES["verdict"]), "sha256": H["verdict"],
     "validation_status": "unverified",
     "note": "Blind full-schema F2b verdict at rev13 pin: accept 4.0, 0 hard failures, 7 findings (1 major non-blocking).",
     "evidence_refs": [ref("verdict", "verdict")]})
add({"event_id": "w071-f2brev13-20260912T0111-review-F2b", "event_type": "review",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "target_id": "F2b", "reviewer": "worker-071", "verdict": "accept", "score": 4,
     "reviewed_path": TARGET, "reviewed_sha256": PIN,
     "reviewed_frozen_sha256": FROZEN_PIN, "reviewed_frozen_revision": 29,
     "verdict_file": rel(FILES["verdict"]), "verdict_file_sha256": H["verdict"],
     "counts_as_full_schema_verdict": True, "blind": True, "independent_of_authors": True,
     "checks_passed": 26, "checks_total": 26, "control_families_fired": 6,
     "hard_failures": [],
     "findings": ["F-071-F2B-01", "F-071-F2B-02", "F-071-F2B-03", "F-071-F2B-04",
                  "F-071-F2B-05", "F-071-F2B-06", "F-071-F2B-07"],
     "next_falsifier": "re-run review_f2b_rev13.py at the pins; any check flip, non-firing control, or pin move voids the verdict; a demonstrable formal-conclusion misbinding (F-071-F2B-01) promotes it to a hard failure",
     "evidence_refs": [ref("verdict", "verdict"), ref("results", "results"), f"{TARGET}#{PIN[:12]}",
                       f"artifacts/formulation/FROZEN.json#{FROZEN_PIN[:12]}"]})
add({"event_id": "w071-f2brev13-20260912T0111-status", "event_type": "status",
     "created_at": NOW, "actor": "worker-071", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "gate": "G-FORM", "class_ids": ["AF-SCC-C0-VAC-GEN"], "task_id": "W071-F2B-REV13-BLIND-REVIEW-01",
     "status": "active", "hours": 0.5,
     "summary": "One class-bound task complete at worker level: blind independent full-schema review of F2b (schemas/af_scc_c0_vacuum.yaml, AF-SCC-C0-VAC-GEN) at rev13 pin b2ab6acb2bbe under FROZEN rev29 815e08079aefbc. 26/26 pre-registered checks pass, 6/6 control families fire, t0==t1 frame stable, canonical structural checker corroborates PASS. Verdict accept 4.0, 0 hard failures, 7 findings: F-071-F2B-01 (major, non-blocking) statement_formal byte-identical to F2a with class distinction only in conclusion_type and the class-local predicate; minor/info wording and provenance items. Soft flag disposed as annotation. No node completion, no validation_status=passed, no gate verdict; audit lead adjudicates at astra-life05-verify-gform-r3.",
     "measurements": {"checks_passed": 26, "checks_total": 26, "control_families_fired": 6,
                      "moved_during_run": 0, "hard_failures": 0, "findings": 7},
     "next_falsifier": "re-run artifacts/worker-071/f2b_rev13_blind_review/review_f2b_rev13.py at the pins; any check flip, non-firing control, or pin move voids; a demonstrable formal-conclusion misbinding promotes F-071-F2B-01 to hard failure",
     "evidence_refs": [ref("verdict", "verdict"), ref("results", "results"),
                       f"runtime/state/worker-071_F2b_checkpoint.json#{ckpt_sha[:12]}"]})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

written = []
with OUTBOX.open("a", encoding="utf-8") as fh:
    for e in ev:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, sort_keys=False) + "\n")
        written.append(e["event_id"])

print(json.dumps({"checkpoint": rel(CKPT), "checkpoint_sha256": ckpt_sha,
                  "events_written": written,
                  "hashes": H}, indent=1))
