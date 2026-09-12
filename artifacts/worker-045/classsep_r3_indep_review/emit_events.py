#!/usr/bin/env python3
"""Emit W045-CLASSSEP-R3-INDEP-REVIEW-01 events to comms/outbox/worker-045.jsonl.

Validates every event with research_map.schemas.validate_event, appends once
(idempotent by event_id), and never touches research_map.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

W = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(W / "research_map"))
from schemas import validate_event  # noqa: E402

BASE = Path(__file__).resolve().parent
OUT = W / "comms/outbox/worker-045.jsonl"
STAMP = "20260912T011500"
CLASS = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN;AF-WCC-SCALAR-SPH"
CLASSES = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"]
TARGET = "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467"


def sha(rel: str) -> str:
    return hashlib.sha256((BASE / rel).read_bytes()).hexdigest()


R = "artifacts/worker-045/classsep_r3_indep_review"
E36 = "artifacts/worker-045/classsep_e36_arm/pinned/class_separation_e36b0d644ca.py"
EV = {
    "report": f"{R}/report.json",
    "runner": f"{R}/run_independent_recount.py",
    "readme": f"{R}/README.md",
    "checkpoint": f"{R}/checkpoint.json",
    "replay": f"{R}/pinned/replay_run_final_output.json",
    "e36": E36,
}
H = {"report": sha("report.json"), "runner": sha("run_independent_recount.py"),
     "readme": sha("README.md"), "checkpoint": sha("checkpoint.json"),
     "replay": sha("pinned/replay_run_final_output.json"),
     "e36": hashlib.sha256((W / E36).read_bytes()).hexdigest()}

FALSIFIER = (
    "Withdrawn if any of: (a) a replay at the declared pins does not reproduce the declared "
    "corpus A/B/C/D censuses (any mismatch beyond volatile paths/timestamps); (b) the live "
    "canonical research_map/class_separation.py does not measure a8c04fc31e4a at re-measurement "
    "time (voids the live-vs-APPLIED comparison only); (c) some arm in fact meets all four "
    "adoption bounds (voids choice (c)); (d) a genuine first-order C0/C2 merge assertion is found "
    "in a claim the artifact labels FP (voids the metalinguistic-FP classification); (e) any "
    "pinned input hash drifts during the run (voids the affected comparison).")

EVIDENCE = [
    f"{R}/report.json#{H['report'][:12]}",
    f"{R}/run_independent_recount.py#{H['runner'][:12]}",
    f"{R}/README.md#{H['readme'][:12]}",
    f"{R}/checkpoint.json#{H['checkpoint'][:12]}",
    f"{R}/pinned/replay_run_final_output.json#{H['replay'][:12]}",
    f"{E36}#{H['e36'][:12]}",
    TARGET,
    "reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467",
    "artifacts/audit/classsep_r3_adjudication.py#fc92f4eac503",
    "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json#f344ed2aaea5",
    "artifacts/audit/classsep_calibration.py#8f2efd262f97",
    "artifacts/worker-049/classsep_fn_audit/corpus.json#9eb2ea9e2743",
    "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py#6e5306aafe7b",
    "artifacts/worker-049/classsep_prose_fix/worker035_controls.json#ef881c3aa6ef",
    "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py#a8c04fc31e4a",
    "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#c266dbceca87",
    "proposed/class_separation.py#e2d24b927ee8",
    "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py#dc8aa0de3869",
    "comms/inbox/astra.jsonl:3 (astra-detector-patch-result-0112)",
]

STATEMENT = (
    "At the declared pins (reviewed artifact reviews/CLASSSEP-calibration-adjudication.json"
    "#7714ffd5b467 r3-life06; frozen map snapshot artifacts/audit/"
    "classsep_r3_map_snapshot_20260912T010324.json#f344ed2aaea5, 383 claims; runner "
    "artifacts/audit/classsep_r3_adjudication.py#fc92f4eac503; arms APPLIED a8c04fc31e4a / PRE "
    "c266dbceca87 / STAGED e2d24b927ee8 / PROSEFIX dc8aa0de3869), an independent read-only review "
    "measures: (1) an unmodified two-run replay of the reviewed runner in a sandbox at those pins "
    "reproduces every measured section of the published artifact identically (25/25 non-volatile "
    "sections, deterministic run1==run2), with exactly one declared-only section "
    "'controller_corroboration' that the runner does not emit and whose substance (APPLIED "
    "hard=19 = 17 labeled metalinguistic FP + 2 unlabeled DETECTOR_SELF meta-claims, claims[327] "
    "and claims[336]) is independently verified against the frozen snapshot; (2) independent "
    "recounts without the reviewed census wrappers reproduce corpus A (all four arms PASS "
    "17/0/10/0 on 27 fixtures) and corpus B hard/soft/claims-flagged counts (APPLIED 19/0/14, PRE "
    "24/0/16, STAGED 25/0/16, PROSEFIX 1/0/1); (3) the pre-registered adoption arithmetic "
    "recomputes to choice (c): no arm meets all four bounds (APPLIED 4/6 sens, 3/10 spec, 1 "
    "cue-FN-high; PRE 4/6, 1/10, 0; STAGED 5/6, 1/10, 0; PROSEFIX 4/6, 10/10, 10), and the "
    "choice-(b) rollback branch is false because PRE sensitivity is below 5/6; (4) the "
    "attribution correction is supported by a fresh run of the pinned worker-049 harness: the "
    "10/10 cue-induced high-confidence FN belongs to PROSEFIX dc8aa0de, not to the staged "
    "candidate e2d24b92 (STAGED cue-FN high = 0); (5) five controls pass: genuine-merge "
    "sensitivity (all arms fire), detector-FP-quote suppression, the e36-only '0 genuine "
    "assertions' carve-out delta, negation suppression, and the runner's hash gate fail-closed "
    "(rc=2, CITED HASH MISMATCH). Witnessed outside the artifact's scope: research_map/"
    "class_separation.py measured e36b0d644ca (an unaccepted direct patch per the controller's "
    "astra-detector-patch-result-0112) from 01:06:12 until about 01:08, i.e. after the r3 "
    "artifact was published, and measures the declared APPLIED pin a8c04fc3 again at review "
    "close (byte snapshot pinned). This is a mechanical/provenance measurement; it re-adjudicates "
    "no label and sets no gate verdict."
)

EVENTS = [
    {"event_id": f"w045-art-{STAMP}-r3-indep-report", "event_type": "artifact",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "artifact_type": "independent_review_report",
     "path": EV["report"], "sha256": H["report"], "validation_status": "unverified",
     "summary": "W045-CLASSSEP-R3-INDEP-REVIEW-01: replay 25/25 measured sections identical + "
                "deterministic; independent corpus A/B recounts zero mismatches; decision (c) "
                "recomputed; attribution correction supported; 5/5 controls; pins stable; "
                "verdict accept (minor provenance finding W045-R3-07).",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
    {"event_id": f"w045-art-{STAMP}-r3-indep-runner", "event_type": "artifact",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "artifact_type": "runner", "path": EV["runner"], "sha256": H["runner"],
     "validation_status": "unverified",
     "summary": "Deterministic read-only reviewer: sandbox replay (2 runs), wrapper-free corpus "
                "A/B recount, decision-arithmetic recompute, pinned-instrument corpus C/D replay, "
                "4 phrase controls + fail-closed hash-gate control, pin drift guard.",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
    {"event_id": f"w045-art-{STAMP}-r3-indep-readme", "event_type": "artifact",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "artifact_type": "readme", "path": EV["readme"], "sha256": H["readme"],
     "validation_status": "unverified",
     "summary": "Method, result tables, 7 findings, controls, falsifier, scope limits and "
                "authority note.",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
    {"event_id": f"w045-art-{STAMP}-r3-indep-checkpoint", "event_type": "artifact",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "artifact_type": "checkpoint", "path": EV["checkpoint"], "sha256": H["checkpoint"],
     "validation_status": "unverified",
     "summary": "Worker checkpoint: 20 artifact hashes, reviewed pins stable, live target "
                "unchanged at 7714ffd5b467, live detector back at declared APPLIED a8c04fc3, "
                "map sha at checkpoint, next falsifier.",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
    {"event_id": f"w045-art-{STAMP}-r3-replay-evidence", "event_type": "artifact",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "artifact_type": "replay_evidence", "path": EV["replay"], "sha256": H["replay"],
     "validation_status": "unverified",
     "summary": "Final sandbox replay output at the declared pins (raw run1/run2 differ only in "
                "volatile fields; normalized sections byte-identical).",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
    {"event_id": f"w045-art-{STAMP}-r3-e36-snapshot", "event_type": "artifact",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "artifact_type": "detector_byte_snapshot", "path": E36, "sha256": H["e36"],
     "validation_status": "unverified",
     "summary": "Byte snapshot of the third detector image e36b0d644ca taken while it was live "
                "(01:06:12-~01:08); differs from the declared APPLIED a8c04fc3 by one regex "
                "alternative ('0 genuine assertions?') isolated by control C3.",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
    {"event_id": f"w045-review-{STAMP}-r3-indep", "event_type": "review",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045", "reviewer": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "target_id": TARGET, "verdict": "accept", "score": 4.5, "hard_failures": [],
     "findings": [
         "W045-R3-01 info: replay at the declared pins reproduces 25/25 measured sections "
         "identically; two runs normalized-byte-identical.",
         "W045-R3-02 info: independent corpus-B recount (no census wrappers) matches hard/soft/"
         "claims-flagged for all four arms.",
         "W045-R3-03 info: independent corpus-A recount matches 17/0/10/0 PASS for all four arms.",
         "W045-R3-04 info: decision arithmetic recomputes to choice (c); adoptable arms = none.",
         "W045-R3-05 info: attribution correction supported; PROSEFIX carries the 10/10 cue-FN, "
         "STAGED does not.",
         "W045-R3-06 witnessed: third detector image e36b0d644ca was live for ~1 minute after "
         "publication (unaccepted patch, astra-detector-patch-result-0112); live path is back at "
         "the declared APPLIED pin a8c04fc3; byte snapshot pinned.",
         "W045-R3-07 minor provenance: the published artifact carries one section its declared "
         "runner never emits ('controller_corroboration'); its substance holds independently "
         "(19 = 17 labeled FP + claims[327],[336]).",
     ],
     "scope_note": "Mechanical/provenance review only; labels inside the audited instruments "
                   "were replayed, not independently re-adjudicated. No gate verdict.",
     "evidence_refs": EVIDENCE},
    {"event_id": f"w045-claim-{STAMP}-r3-indep", "event_type": "claim",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "conclusion_type": "formal_model", "statement": STATEMENT,
     "assumptions": [
         "the pinned byte copies are identical to the paths they were taken from at the recorded "
         "times (verified by sha256 at pin time and again at review close)",
         "the reviewed artifact's declared runner artifacts/audit/classsep_r3_adjudication.py is "
         "its declared generator, and the one section it does not emit was appended after the run",
         "corpus C/D re-execution uses the pinned shared instruments (classsep_calibration.py, "
         "w049 harness); labeling authority remains the audit lead's",
         "the frozen map snapshot f344ed2aaea5 binds corpus-B counts; live map traffic after "
         "01:03:24+08:00 is out of scope",
         "formal_model is used because this is an artifact/provenance measurement, not a "
         "mathematical theorem",
     ],
     "falsifier": FALSIFIER, "evidence_refs": EVIDENCE,
     "artifact_refs": [{"path": EV["report"], "sha256": H["report"]},
                       {"path": EV["runner"], "sha256": H["runner"]},
                       {"path": EV["readme"], "sha256": H["readme"]},
                       {"path": EV["checkpoint"], "sha256": H["checkpoint"]},
                       {"path": EV["replay"], "sha256": H["replay"]},
                       {"path": E36, "sha256": H["e36"]}]},
    {"event_id": f"w045-status-{STAMP}-r3-indep", "event_type": "status",
     "created_at": "2026-09-12T01:15:00+08:00", "actor": "worker-045",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS, "class_ids": CLASSES,
     "status": "active", "hours": 0.7,
     "summary": "W045-CLASSSEP-R3-INDEP-REVIEW-01 complete at worker level (no node/gate "
                "transition claimed). VERDICT accept 4.5 on reviews/"
                "CLASSSEP-calibration-adjudication.json#7714ffd5b467: unmodified 2-run sandbox "
                "replay reproduces every measured section (25/25, deterministic); wrapper-free "
                "corpus A/B recounts zero mismatches; decision (c) and no-adoptable-arm "
                "recomputed; attribution correction (PROSEFIX not STAGED carries 10/10 cue-FN) "
                "supported; 5/5 controls including fail-closed hash gate; pins stable. Findings: "
                "one minor provenance deviation (appended 'controller_corroboration' section) and "
                "one witnessed out-of-scope detector excursion (e36b0d644ca live ~01:06-01:08, "
                "since rolled back to a8c04fc3), byte-snapshotted. Artifacts "
                "artifacts/worker-045/classsep_r3_indep_review/report.json#"
                f"{H['report'][:12]}.",
     "evidence_refs": EVIDENCE, "next_falsifier": FALSIFIER},
]


def main() -> int:
    seen = set()
    if OUT.exists():
        for ln in OUT.read_text().splitlines():
            ln = ln.strip()
            if ln.startswith("{"):
                try:
                    seen.add(json.loads(ln)["event_id"])
                except Exception:
                    pass
    added = 0
    for e in EVENTS:
        validate_event(e)
        if e["event_id"] in seen:
            print("skip idempotent", e["event_id"])
            continue
        with OUT.open("a") as fh:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
        added += 1
        print("emitted", e["event_type"], e["event_id"])
    print(f"added={added} total_events_in_file={len(seen)+added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
