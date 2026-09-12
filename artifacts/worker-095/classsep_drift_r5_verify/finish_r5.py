#!/usr/bin/env python3
"""W095-CLASSSEP-DRIFT-R5-VERIFY-01 finisher: patch verdict with post-run evidence,
emit the six protocol events, ingest, and write the worker checkpoint.

Read-only on every canonical/proposed/review/corpus file. Appends only to
comms/outbox/worker-095.jsonl and runtime/state/w095_* files.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "evidence/raw"
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
TASK = "W095-CLASSSEP-DRIFT-R5-VERIFY-01"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
EID = f"w095-classsep-drift-r5-{STAMP}"

NEXT_FALSIFIER = (
    "Withdrawn if: (i) the window bytes pinned here are re-measured and do not hash to "
    "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed (a later live move voids "
    "the window, not the finding); (ii) any pinned corpus or the r3 adjudication artifact changes "
    "hash; (iii) a recorded controller artifact event binding e36b0d644ca7, or a pre-registration "
    "showing this carve-out meets the adoption bar, is produced; (iv) an independent re-run does not "
    "reproduce the r3-published per-arm numbers. Adoption of any detector revision requires a "
    "clause-scoped, not window-scoped, assertion-vs-mention guard plus corpus_a PASS 17/0/10/0, "
    "labeled sensitivity >=5/6, specificity >=9/10 and 0 HIGH-confidence cue-induced FN."
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sha(ROOT / rel)[:n]}"


def main() -> int:
    verdict_path = HERE / "verdict.json"
    v = json.loads(verdict_path.read_text())
    post = json.loads((RAW / "postrun_drift_r5.json").read_text())
    v["postrun"] = post
    v["window_validity"] = (
        "The measurement window is the pinned copy (sha256 e36b0d644ca7). Live bytes reverted to "
        "a8c04fc31e4a at 01:08:14, after the run closed; that does not void the window and is "
        "recorded as postrun evidence of oscillation."
    )
    v["independent_corroboration"] = post["independent_corroboration"]
    verdict_path.write_text(json.dumps(v, indent=2) + "\n")

    vsha = sha(verdict_path)
    ev = [
        ref("artifacts/worker-095/classsep_drift_r5_verify/verdict.json"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/run_classsep_drift_r5_verify.py"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/README.md"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/pins_r5.json"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/censuses_r5.json"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/authorization_r5.json"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/postrun_drift_r5.json"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/diff_pin_to_live_r5.txt"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/diff_window_to_reverted_r5.txt"),
        ref("artifacts/worker-095/classsep_drift_r5_verify/pinned/class_separation.live.e36b0d644ca7.py"),
        ref("reviews/CLASSSEP-calibration-adjudication.json"),
        ref("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"),
        ref("artifacts/audit/classsep_calibration.py"),
        ref("artifacts/worker-049/classsep_fn_audit/corpus.json"),
        ref("artifacts/worker-049/classsep_prose_fix/worker035_controls.json"),
        ref("artifacts/worker-07/class_separation_falsification/results.json"),
    ]

    events = [
        {
            "actor": "worker-095", "class_id": CLASS_ID, "created_at": NOW,
            "event_id": f"{EID}-task-claim", "event_type": "status",
            "evidence_refs": ev, "hours": 0.3, "next_falsifier": NEXT_FALSIFIER,
            "node_id": "A1", "status": "active",
            "summary": ("No assignment card exists in comms/inbox/worker-095.jsonl; taking ONE bounded "
                        "class-bound task W095-CLASSSEP-DRIFT-R5-VERIFY-01 (node A1, gate G-AUDIT): "
                        "independent verification of the second unrecorded move of the class-separation "
                        "detector to e36b0d644ca7 at 01:06:12, measured against the r3 pre-registered "
                        "adoption bar and the frozen map snapshot f344ed2aaea5."),
        },
        {
            "actor": "worker-095", "artifact_type": "classsep_drift_verification_verdict",
            "class_id": CLASS_ID, "created_at": NOW, "event_id": f"{EID}-artifact-verdict",
            "event_type": "artifact", "node_id": "A1", "path": "artifacts/worker-095/classsep_drift_r5_verify/verdict.json",
            "sha256": vsha, "validation_status": "unverified",
        },
        {
            "actor": "worker-095", "class_id": CLASS_ID, "node_id": "A1", "created_at": NOW,
            "event_id": f"{EID}-claim-drift", "event_type": "claim",
            "conclusion_type": "empirical_measurement",
            "statement": (
                "At pinned corpora and snapshot (frozen map f344ed2aaea5, label set from the pinned r3 "
                "module), the live detector bytes e36b0d644ca7 (live 01:06:12-01:08:14, then reverted to "
                "a8c04fc31e4a) return corpus_a PASS 17/0/10/0, labeled assertion-vs-mention sensitivity "
                "4/6 and specificity 4/10, 1 HIGH-confidence cue-induced FN (A04 clause scope), "
                "worker-035 battery 13/23, and 16 live hard findings (15 labeled metalinguistic FP + 1 "
                "unlabeled) on the frozen snapshot. It therefore does NOT meet the r3 adoption bar "
                "(needs sens >=5/6, spec >=9/10, 0 HIGH cue-FN); the drift is a strict FP improvement "
                "over a8c04fc31e4a (live hard 19->16, spec 3/10->4/10, no corpus_a regression) but "
                "leaves the A04 false negative and the r3 decision (c) stands at these bytes. The same "
                "re-implementation reproduces all r3-published numbers for PRE/APPLIED/STAGED/PROSEFIX, "
                "validating the instrument."),
            "assumptions": [
                "the pinned r3 corpora and label set are the pre-registered ground truth for this window",
                "a detector revision is adoptable only at recorded bytes and only if it meets the r3 bar",
                "worker measurement cannot set node status, gate verdict or validation_status",
                "the measurement binds the pinned window copy; post-run live movement voids the window, not the finding",
            ],
            "falsifier": NEXT_FALSIFIER, "evidence_refs": ev,
            "artifact_refs": ev[:1],
        },
        {
            "actor": "worker-095",
            "reviewer": "worker-095 (independent; not an author of the detector, the corpora, or the r3 adjudication)",
            "class_id": CLASS_ID, "node_id": "A1", "created_at": NOW,
            "event_id": f"{EID}-review-drift", "event_type": "review",
            "target_id": "astra-life06-classsep-detector-adjudication / reviews/CLASSSEP-calibration-adjudication.json",
            "verdict": "revise", "score": 3, "artifact_sha256": vsha,
            "counts_as_full_schema_verdict": False,
            "hard_failures": ["HF-R5-01", "HF-R5-02"],
            "findings": [
                "HF-R5-01 (major): second unrecorded detector drift inside the REC-22 write-freeze; live "
                "e36b0d644ca7 at 01:06:12 matched neither the active pin c266dbecaa87 nor the r3-adjudicated "
                "a8c04fc31e4a; zero events in research_map/events.jsonl or comms/outbox/ bound the hash at "
                "measurement time (worker-090 later recorded the same move as a blocker at 01:08:56). "
                "The audit lead's own blocker audit-l07-b4-audit-author-conflict (01:05:17) had already "
                "flagged the detector-write/freeze conflict.",
                "HF-R5-02 (major): the new bytes fail the r3 pre-registered adoption bar (sens 4/6 "
                "< 5/6; spec 4/10 < 9/10; 1 HIGH cue-induced FN > 0; battery 13/23), so they are not "
                "adoptable as-is and decision (c) is unchanged.",
                "INFO: strict FP improvement vs a8c04fc31e4a -- live hard 19->16 (claims[306] and "
                "claims[336] '0 genuine assertions' quotations now exempt), corpus_c spec 3/10->4/10 "
                "(M7 now TN), no corpus_a regression and no new mention FP; but the carve-out is "
                "window-based, not clause-scoped, so A04 remains a HIGH cue-FN.",
                "INFO: live bytes oscillated c266dbecaa87 -> a8c04fc31e4a (00:52) -> e36b0d644ca7 "
                "(01:06:12) -> a8c04fc31e4a (01:08:14) inside 16 minutes; every CLASSSEP measurement "
                "must cite its detector hash.",
                "INFO: instrument validated -- independent re-implementation reproduced every "
                "r3-published per-arm number for PRE/APPLIED/STAGED/PROSEFIX over corpora (a)/(b)/(c)/(d) "
                "and the worker-035 battery (r3_published_numbers_independently_reproduced=true).",
            ],
            "evidence_refs": ev,
        },
        {
            "actor": "worker-095", "class_id": CLASS_ID, "node_id": "A1", "created_at": NOW,
            "event_id": f"{EID}-blocker-pin-drift", "event_type": "blocker",
            "gate": "G-AUDIT",
            "description": (
                "research_map/class_separation.py moved to e36b0d644ca7 at 01:06:12 and back to "
                "a8c04fc31e4a at 01:08:14 with no artifact event binding either move; the CF-26/REC-22 "
                "detector write-freeze is in force and adjudication (c) pinned c266dbecaa87. The e36b0d "
                "window is measured here: it does not reach the adoption bar, and the A04 clause-scope "
                "HIGH cue-FN persists, so neither the drift nor the revert is validated by measurement. "
                "The r3 adjudication's own 'needs one independent review at the frozen hashes' is "
                "satisfied for the APPLIED arm by this reproduction, but not for the e36b0d move."),
            "needed_to_unblock": (
                "(a) controller/audit decides the canonical detector bytes for this window and records an "
                "artifact event binding the chosen sha256; (b) the frozen_artifacts pin is refreshed "
                "explicitly (to a measured, bar-meeting revision) or the write-freeze is enforced against "
                "further writes; (c) an adoptable revision must be clause-scoped, not window-scoped, and "
                "pass corpus_a 17/0/10/0, sens >=5/6, spec >=9/10, 0 HIGH cue-FN (worker-032's staged "
                "42cdb683 candidate is a separate, not-yet-independently-reviewed claim)."),
            "evidence_refs": ev,
        },
        {
            "actor": "worker-095", "class_id": CLASS_ID, "created_at": NOW,
            "event_id": f"{EID}-task-receipt-complete", "event_type": "status",
            "evidence_refs": ev, "hours": 0.3, "next_falsifier": NEXT_FALSIFIER,
            "node_id": "A1", "status": "active",
            "summary": ("W095-CLASSSEP-DRIFT-R5-VERIFY-01 worker-level receipt complete; node status "
                        "deliberately unchanged (worker events cannot set status=done, "
                        "validation_status=passed or a gate verdict). verdict=revise (3/5) at window "
                        "e36b0d644ca7 / frozen snapshot f344ed2aaea5; artifact + README + independent "
                        "runner + 5 raw evidence files + pin copy written; CHECKPOINT written. "
                        "counts_as_full_schema_verdict=false."),
        },
    ]

    outbox = ROOT / "comms/outbox/worker-095.jsonl"
    with outbox.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    before = sha(ROOT / "research_map/events.jsonl")
    proc = subprocess.run([sys.executable, "research_map/comms.py", "ingest"],
                          cwd=ROOT, capture_output=True, text=True, timeout=180)
    after = sha(ROOT / "research_map/events.jsonl")
    accepted_ids, rejected_ids = set(), set()
    for line in (ROOT / "research_map/events.jsonl").read_text(errors="replace").splitlines():
        try:
            o = json.loads(line)
        except Exception:
            continue
        if str(o.get("event_id", "")).startswith(EID):
            accepted_ids.add(o["event_id"])
    rej = ROOT / "comms/rejected.jsonl"
    if rej.is_file():
        for line in rej.read_text(errors="replace").splitlines():
            try:
                o = json.loads(line)
            except Exception:
                continue
            if str(o.get("event_id", "")).startswith(EID):
                rejected_ids.add(o["event_id"])

    # freshness control: re-check that no canonical byte we pinned moved during the finisher
    drift = {
        "live_canonical_sha256_at_finish": sha(ROOT / "research_map/class_separation.py"),
        "window_pin_sha256": sha(ROOT / "artifacts/worker-095/classsep_drift_r5_verify/pinned/"
                                      "class_separation.live.e36b0d644ca7.py"),
        "verdict_json_sha256": vsha,
        "events_jsonl_before": before,
        "events_jsonl_after": after,
    }

    ckpt_id = f"ckpt-w095-classsep-drift-r5-{STAMP}"
    record = {
        "checkpoint_id": ckpt_id,
        "task_id": TASK, "worker": "worker-095", "class_id": CLASS_ID,
        "node_id": "A1", "gate": "G-AUDIT",
        "verdict": "revise", "score_0_5": 3,
        "counts_as_full_schema_verdict": False,
        "hard_failures": ["HF-R5-01", "HF-R5-02"],
        "window_sha256": "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed",
        "active_pin_sha256": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "adjudicated_applied_sha256": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
        "live_canonical_sha256_at_finish": drift["live_canonical_sha256_at_finish"],
        "artifact": "artifacts/worker-095/classsep_drift_r5_verify/verdict.json",
        "artifact_sha256": vsha,
        "probe": {"path": "artifacts/worker-095/classsep_drift_r5_verify/run_classsep_drift_r5_verify.py",
                  "sha256": sha(HERE / "run_classsep_drift_r5_verify.py")},
        "evidence_dir": "artifacts/worker-095/classsep_drift_r5_verify/evidence/raw/",
        "checkpoint_at": NOW,
        "events_ingested": sorted(accepted_ids),
        "events_rejected": sorted(rejected_ids),
        "ingest_returncode": proc.returncode,
        "ingest_stdout_tail": proc.stdout.strip().splitlines()[-3:],
        "next_falsifier": NEXT_FALSIFIER,
        "freshness": drift,
    }
    state = ROOT / "runtime/state"
    (state / f"w095_classsep_drift_r5_checkpoint_{STAMP}.json").write_text(json.dumps(record, indent=2) + "\n")
    with (state / "w095_classsep_drift_r5_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps({k: record[k] for k in
                             ("checkpoint_id", "task_id", "worker", "verdict", "score_0_5",
                              "window_sha256", "live_canonical_sha256_at_finish", "artifact_sha256",
                              "checkpoint_at", "events_rejected")}) + "\n")
    (state / "w095_latest_checkpoint.json").write_text(json.dumps({
        "task_id": TASK, "worker": "worker-095", "verdict": "revise", "score_0_5": 3,
        "window_sha256": record["window_sha256"],
        "live_canonical_sha256": record["live_canonical_sha256_at_finish"],
        "path": f"runtime/state/w095_classsep_drift_r5_checkpoint_{STAMP}.json",
        "artifact": record["artifact"], "artifact_sha256": vsha,
        "checkpoint_at": NOW, "next_falsifier": NEXT_FALSIFIER,
    }, indent=2) + "\n")

    print(f"verdict sha256 {vsha}")
    print(f"events emitted: {len(events)}; accepted: {len(accepted_ids)}; rejected: {len(rejected_ids)}")
    print(f"ingest rc={proc.returncode} stdout={proc.stdout.strip()[:200]}")
    print(f"checkpoint {ckpt_id}")
    return 0 if len(accepted_ids) == len(events) else 1


if __name__ == "__main__":
    sys.exit(main())
