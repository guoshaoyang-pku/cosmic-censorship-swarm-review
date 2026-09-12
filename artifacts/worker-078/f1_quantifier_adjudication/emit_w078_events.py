#!/usr/bin/env python3
"""Emit W078-F1-QUANT-ADJ-01 upward events (schema-validated) and the worker checkpoint.

Idempotent: events whose event_id already exists in the outbox are skipped.
Appends to comms/outbox/worker-078.jsonl and writes
runtime/state/w078_checkpoint_2_f1_quant_adjudication.json + .jsonl.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-078.jsonl"
STATE = ROOT / "runtime" / "state"
PIN = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
NOW = datetime.now(CST).isoformat(timespec="seconds")
# Fixed per-task stamps: event ids must be stable across re-runs so the emitter is idempotent.
# STAMP is the core batch already ingested by the controller at 00:28; do not change it.
STAMP = "20260912T002847"
# Correction batch: names the double-emission incident and records the corrected emitter hash.
FIX_STAMP = "20260912T0030"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def art(rel: str) -> dict:
    return {"path": rel, "sha256": sha256(ROOT / rel)}


REPORT = art("artifacts/worker-078/f1_quantifier_adjudication/report.json")
RERUN = art("artifacts/worker-078/f1_quantifier_adjudication/report_rerun.json")
HARNESS = art("artifacts/worker-078/f1_quantifier_adjudication/adjudicate_f1_quantifier.py")
README = art("artifacts/worker-078/f1_quantifier_adjudication/README.md")
SNAPSHOT = art("artifacts/worker-078/f1_quantifier_adjudication/snapshot/af_wcc_vacuum.9a8bd4c96800.yaml")
REVIEW = art("reviews/F1-quantifier-adjudication-078.json")
EMITTER = art("artifacts/worker-078/f1_quantifier_adjudication/emit_w078_events.py")

SUMMARY = ("W078-F1-QUANT-ADJ-01: independent adjudication of the contested critical F1 defect "
           "(worker-19 F-1 / HF-06) at pinned hash 9a8bd4c96800. 9/9 primary defect checks CONFIRMED, "
           "4 secondary defects confirmed, 0 binding failures, pinned test-retest reproduced every "
           "check status. quantifiers.formal (:54-55) and D5 (:79-81) expand visibility as whole-curve "
           "single-q containment while the canonical predicate (:220) is tail-based; the formal is "
           "strictly weaker than the conclusion and quantifiers.negation (:84-88) does not negate it. "
           "Verdict: revise. Scope: structural/contract only.")

NEXT_FALSIFIER = ("Re-run adjudicate_f1_quantifier.py --pin 9a8bd4c96800 and obtain any CLEAR primary "
                  "check; or exhibit a tail-constrained formal/D5 in the pinned bytes; or show "
                  "whole-curve non-containment follows from tail non-containment; or a notation ruling "
                  "that 'gamma subset J^-(q)' denotes a tail. A later revision hash supersedes (does not "
                  "refute) this verdict.")

EVENTS = [
    {"event_id": f"w078-{STAMP}-task-claim", "event_type": "status", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "status": "active", "hours": 0.5,
     "class_id": "AF-WCC-VAC-GEN",
     "summary": "No assignment card in comms/inbox for worker-078. Taking one bounded class-bound task: "
                "independent adjudication of the contested critical F1 quantifier defect (worker-19 F-1, "
                "nearest HF-06) at the audit-measured hash, with a pin-then-verify drift-voiding "
                "protocol. Reason: at 00:21-00:22 the F1 corpus carried both an accept and three revises "
                "on the same bytes, and a critical contradiction cannot be left unadjudicated.",
     "evidence_refs": [f"schemas/af_wcc_vacuum.yaml#{PIN[:12]}",
                       "reviews/F1-review-19.json", "reviews/F1-review-lead-audit-r2.json"],
     "next_falsifier": "A tail-constrained formal/D5 in the pinned bytes, or a monotonicity lemma "
                       "collapsing the strictness argument."},
    {"event_id": f"w078-{STAMP}-artifact-harness", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "verifier_code",
     "path": HARNESS["path"], "sha256": HARNESS["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-artifact-report", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "audit_report",
     "path": REPORT["path"], "sha256": REPORT["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-artifact-rerun", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "audit_report",
     "path": RERUN["path"], "sha256": RERUN["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-artifact-readme", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "summary",
     "path": README["path"], "sha256": README["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-artifact-snapshot", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "artifact_snapshot",
     "path": SNAPSHOT["path"], "sha256": SNAPSHOT["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-artifact-review-body", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "review_body",
     "path": REVIEW["path"], "sha256": REVIEW["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-artifact-emitter", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "artifact_type": "event_emitter",
     "path": EMITTER["path"], "sha256": EMITTER["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{STAMP}-review-f1", "event_type": "review", "created_at": NOW,
     "actor": "worker-078", "reviewer": "worker-078", "target_id": f"schemas/af_wcc_vacuum.yaml#{PIN[:12]}",
     "verdict": "revise", "score": 3.0,
     "hard_failures": ["HF-06 (worker-19 F-1) independently CONFIRMED: quantifiers.formal:54-55 and "
                       "D5:79-81 use whole-curve single-q containment while visibility.definition:220 is "
                       "tail-based; formal is strictly weaker than the conclusion and quantifiers."
                       "negation:84-88 does not negate it."],
     "findings": ["9/9 primary defect checks CONFIRMED at the pinned bytes; 4 secondary defects "
                  "confirmed (D0 mixed-type domain; class_contract_pointer does not resolve in the "
                  "canonical taxonomy; consistency evidence not hash-bound; duplicate/future-dated "
                  "revised_at keys). Repair is local: keep the predicate-name reference at :251 and "
                  "rewrite the expansion and D5 to the tail form, then republish.",
                  "Binding: snapshot == live canonical == authoring mirror at 9a8bd4c96800 during the "
                  "review window; pinned test-retest reproduced every check status.",
                  "Scope: structural/contract semantics only; no truth or physics claim. Worker verdict "
                  "only; no gate verdict or node status set."],
     "evidence_refs": [f"{REPORT['path']}#{REPORT['sha256'][:12]}",
                       f"{RERUN['path']}#{RERUN['sha256'][:12]}",
                       f"{SNAPSHOT['path']}#{SNAPSHOT['sha256'][:12]}"]},
    {"event_id": f"w078-{STAMP}-status-final", "event_type": "status", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "status": "active", "hours": 0.5,
     "class_id": "AF-WCC-VAC-GEN",
     "summary": SUMMARY,
     "evidence_refs": [f"{REPORT['path']}#{REPORT['sha256'][:12]}",
                       f"{REVIEW['path']}#{REVIEW['sha256'][:12]}",
                       f"{SNAPSHOT['path']}#{SNAPSHOT['sha256'][:12]}"],
     "next_falsifier": NEXT_FALSIFIER},
    {"event_id": f"w078-{FIX_STAMP}-artifact-emitter-fixed", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-078", "node_id": "F1", "artifact_type": "event_emitter",
     "path": EMITTER["path"], "sha256": EMITTER["sha256"], "validation_status": "unverified",
     "class_id": "AF-WCC-VAC-GEN"},
    {"event_id": f"w078-{FIX_STAMP}-dup-note", "event_type": "status", "created_at": NOW,
     "actor": "worker-078", "node_id": "F1", "status": "active", "hours": 0.1,
     "class_id": "AF-WCC-VAC-GEN",
     "summary": "CORRECTION NOTE (emitter double-emission, benign). "
                "w078-20260912T002827-* and w078-20260912T002847-* in comms/outbox/worker-078.jsonl "
                "carry the SAME payloads (identical artifact paths and sha256 for harness/report/rerun/"
                "readme/snapshot/review-body, identical review verdict), because the first emitter "
                "derived event ids from wall clock and was re-run once. The 002847 batch differs only by "
                "adding the emitter-hash artifact event. Both batches are already ingested (event ids "
                "differ, so ingest could not dedupe them). Controller instruction: count the "
                "W078-F1-QUANT-ADJ-01 review ONCE for reviewer worker-078 and do not double-count the "
                "artifact events. The worker has no retraction authority and did not modify "
                "events.jsonl. The emitter is now deterministic (fixed id stamp); re-running it is a "
                "no-op. Corrected emitter hash and the full incident record are in "
                "runtime/state/w078_checkpoint_2_f1_quant_adjudication.json (corrections block).",
     "evidence_refs": [f"{REVIEW['path']}#{REVIEW['sha256'][:12]}",
                       "runtime/state/w078_checkpoint_2_f1_quant_adjudication.json",
                       "runtime/state/ingested_ids.json"],
     "next_falsifier": "Any controller ruling that the duplicate review/artifact events were "
                       "double-applied to a gate criterion; then the duplicate batch must be "
                       "disregarded by event id."},
]


def main() -> int:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    emitted, skipped = [], []
    with OUTBOX.open("a") as f:
        for ev in EVENTS:
            validate_event(ev)
            if ev["event_id"] in existing:
                skipped.append(ev["event_id"])
                continue
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            emitted.append(ev["event_id"])

    checkpoint = {
        "checkpoint": 2,
        "at": NOW,
        "worker": "worker-078",
        "lifecycle": "fleet batch worker-037..100; this is worker-078's second bounded run in the window "
                     "(run 1 = W078-F2A-INDEP-VERIFY-01, checkpoint 1). No assignment card in comms/inbox.",
        "assignment_taken": {
            "kind": "class-bound task taken from the open gate queue",
            "task_id": "W078-F1-QUANT-ADJ-01",
            "task": "independent adjudication of the contested critical F1 quantifier defect "
                    "(worker-19 F-1 / HF-06) at a pinned hash",
            "class_id": "AF-WCC-VAC-GEN",
            "node_id": "F1",
            "gate": "G-FORM",
            "why_not_duplicative": "F1 carried an accept and three revises on the same bytes at 00:21-00:22; "
                                   "this run adjudicates the critical claim from the pinned bytes only instead "
                                   "of adding another whole-schema verdict.",
        },
        "hours_spent_estimate": 0.5,
        "snapshot_sha256": SNAPSHOT["sha256"],
        "result": {
            "verdict": "revise",
            "primary_defect_checks": 9,
            "primary_defects_confirmed": 9,
            "secondary_defects_confirmed": 4,
            "binding_failures": 0,
            "test_retest": "pinned re-run reproduced every check status",
            "scope": "structural/contract semantics of the pinned bytes only",
        },
        "artifacts": {REPORT["path"]: {"sha256": REPORT["sha256"]},
                      RERUN["path"]: {"sha256": RERUN["sha256"]},
                      HARNESS["path"]: {"sha256": HARNESS["sha256"]},
                      README["path"]: {"sha256": README["sha256"]},
                      SNAPSHOT["path"]: {"sha256": SNAPSHOT["sha256"]},
                      REVIEW["path"]: {"sha256": REVIEW["sha256"]},
                      EMITTER["path"]: {"sha256": EMITTER["sha256"]}},
        "evidence": {
            "schemas/af_wcc_vacuum.yaml": {"sha256_at_snapshot": PIN,
                                           "live_recheck_at_0027": PIN,
                                           "authoring_mirror_at_0027": PIN},
            "review_verdicts_at_pin": {
                "worker-078": "revise (this run, critical HF-06 confirmed)",
                "astra-lead-audit": "revise (F1-review-lead-audit-r2.json)",
                "worker-019": "revise (HF-06 origin)",
                "worker-034/090/094": "revise"},
        },
        "observed_drift": "F1 canonical stable at 9a8bd4c96800 across 00:21:55-00:27:00 (mtime 00:19:14); "
                          "no live drift during the pinned window.",
        "events_emitted_task_total": [ev["event_id"] for ev in EVENTS],
        "last_run": {"at": NOW, "emitted": emitted, "skipped_idempotent": skipped},
        "corrections": {
            "incident": "the emitter's first version derived event ids from wall clock; a second run "
                        "produced a second batch (w078-20260912T002847-*) with identical payloads, and "
                        "both batches were ingested before cleanup was possible.",
            "action": "no deletion attempted (events.jsonl is controller-owned); an explicit "
                      "count-once note was emitted (w078-20260912T0030-dup-note) with a corrected "
                      "emitter hash event (w078-20260912T0030-artifact-emitter-fixed).",
            "count_once": "review W078-F1-QUANT-ADJ-01 must be counted once for reviewer worker-078.",
            "emitter_now_deterministic": True,
        },
        "falsifier": NEXT_FALSIFIER,
        "authority_note": "Worker verdict only. No gate verdict, node status, or validation_status is set; "
                          "status remains active pending controller adjudication.",
    }
    STATE.mkdir(parents=True, exist_ok=True)
    cp = STATE / "w078_checkpoint_2_f1_quant_adjudication.json"
    cp.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    with (STATE / "w078_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps({"at": NOW, "worker": "worker-078", "checkpoint": 2,
                            "task_id": "W078-F1-QUANT-ADJ-01", "verdict": "revise",
                            "snapshot_sha256": SNAPSHOT["sha256"],
                            "checkpoint_file": str(cp.relative_to(ROOT))}, ensure_ascii=False) + "\n")
    print(json.dumps({"emitted": emitted, "skipped": skipped,
                      "checkpoint": str(cp), "checkpoint_sha256": sha256(cp)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
