#!/usr/bin/env python3
"""W098-CLASSSEP-ADJ-REVIEW-01: checkpoint + comms emission (valid JSON, hash-pinned)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"
CKPT = ROOT / "runtime/state/w098_classsep_r3_adjudication_review_checkpoint_1.json"
ADJ = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"

FILES = {
    "report": HERE / "report.json",
    "raw_measurements": HERE / "raw/measurements.json",
    "pre_registration": HERE / "pre_registration.json",
    "review_instrument": HERE / "run_review.py",
    "prereg_instrument": HERE / "prereg.py",
    "report_writer": HERE / "write_report.py",
    "readme": HERE / "README.md",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path, n: int = 12) -> str:
    return f"{p.relative_to(ROOT).as_posix()}#{sha(p)[:n]}"


def main() -> int:
    h = {k: sha(p) for k, p in FILES.items()}
    rep = json.loads(FILES["report"].read_text())
    m = json.loads(FILES["raw_measurements"].read_text())
    adj_hash = sha(ADJ)
    det_hash = sha(ROOT / "research_map/class_separation.py")
    map_hash = sha(ROOT / "research_map/research_map.json")
    arm_rows = rep["arms"]

    ckpt = {
        "schema": "worker-098/checkpoint/v1",
        "task_id": "W098-CLASSSEP-ADJ-REVIEW-01",
        "actor": "worker-098", "node_id": "A1", "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "created_at": NOW,
        "status": "complete_bounded_task",
        "scope": "independent read-only review of the r3 CLASSSEP adjudication",
        "pins": {"adjudication": adj_hash, "detector_at_close": det_hash,
                 "map_at_close": map_hash, "frozen_snapshot":
                 "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749",
                 "cf29_forensics":
                 "b573dcfdcc20c7ada64ac2e6ebd78787713d55343d9ae46298fa7b390dee9491"},
        "deliverables": {k: {"path": p.relative_to(ROOT).as_posix(), "sha256": h[k]}
                         for k, p in FILES.items()},
        "verdict": {"target": "reviews/CLASSSEP-calibration-adjudication.json",
                    "verdict": rep["verdict"], "score": rep["score"],
                    "reviewed_sha256": adj_hash,
                    "counts_as_independent": True,
                    "counts_as_full_schema_verdict": False},
        "expectations": {e["id"]: e["status"] for e in rep["expectations"]},
        "arms": arm_rows,
        "reproduced": rep["adjudication_reproduced"],
        "next_falsifier": rep["falsifier"],
        "non_claims": ["no gate verdict", "no node completion", "no canonical write",
                       "no claim retirement", "review of an audit artifact, not of the detector"],
    }
    CKPT.write_text(json.dumps(ckpt, indent=2) + "\n")
    ckpt_hash = sha(CKPT)

    cid = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
    ev = []

    def add(tag, etype, **kw):
        e = {"event_id": f"w098-car-{STAMP}-{tag}", "event_type": etype,
             "created_at": NOW, "actor": "worker-098"}
        e.update(kw)
        ev.append(e)

    for tag, key in (("art-report", "report"), ("art-raw", "raw_measurements"),
                     ("art-prereg", "pre_registration"),
                     ("art-instrument", "review_instrument"),
                     ("art-prereg-instrument", "prereg_instrument"),
                     ("art-report-writer", "report_writer"), ("art-readme", "readme")):
        p = FILES[key]
        add(tag, "artifact", node_id="A1", class_id=cid, gate="G-AUDIT",
            artifact_type=f"classsep_r3_adjudication_review/{key}",
            path=p.relative_to(ROOT).as_posix(), sha256=h[key],
            validation_status="unverified", summary=f"W098-CLASSSEP-ADJ-REVIEW-01 {key}.")

    add("review", "review", node_id="A1", gate="G-AUDIT", class_id=cid,
        target_id="reviews/CLASSSEP-calibration-adjudication.json",
        reviewer="worker-098", verdict=rep["verdict"], score=rep["score"],
        reviewed_sha256=adj_hash, counts_as_independent=True,
        counts_as_full_schema_verdict=False, hard_failures=rep["hard_failures"],
        findings=rep["findings"], evidence_refs=rep["evidence_refs"])

    add("claim", "claim", node_id="A1", gate="G-AUDIT", class_id=cid,
        conclusion_type="instrument_finding",
        statement=("At the pins (adjudication 7714ffd5b467 r3-life06; APPLIED a8c04fc3 "
                   "(restored; CF-29); PRE c266dbeca87; STAGED e2d24b927ee8; PROSEFIX "
                   "dc8aa0de3869; frozen map f344ed2aaea5/383 claims), an independent "
                   "worker-098 harness reproduces the adjudication's four-arm census in all "
                   "20 cells across corpora A/B/C/D/E, so decision (c) -- assertion-vs-mention "
                   "is not lexically separable at this window -- is supported by measurement: "
                   "no arm meets 27-fixture PASS + sens>=5/6 + spec>=9/10 + 0 HIGH cue-induced "
                   "FN + 0 live metalinguistic findings. The attribution correction is "
                   "confirmed (PROSEFIX carries 10 HIGH cue-FN; STAGED 0). Expanding the pool "
                   "does not defeat (c): W098 v3 6f1a24c441fb passes the 27-fixture corpus and "
                   "reaches spec 9/10 but fails 5 HIGH cue-FN and 1 frozen-map hard finding "
                   "(claims[327]). CF-29 unauthorized bytes e36b0d64 also fail the bar "
                   "(spec 4/10, hard 16, 1 HIGH cue-FN). Residual live count 19 hard on the "
                   "frozen snapshot = 17 labeled metalinguistic FP + 2 unlabeled DETECTOR_SELF "
                   "meta-claims (claims[327],[336]); live map at close 5ab4bed18107/414 claims, "
                   "so all live counts are snapshot-bound."),
        assumptions=["the measured sha256 is the artifact identity; the claim binds only to "
                     "the pins recorded in pre_registration.json",
                     "the adjudication's four cited arms are the review target; W098 v3 and the "
                     "CF-29 bytes are extra arms, not candidates proposed for adoption",
                     "corpus A/B/C/D/E ground truth is taken as registered, not re-adjudicated",
                     "the frozen map snapshot, not the moving live map, is the live-count surface"],
        falsifier=rep["falsifier"],
        evidence_refs=rep["evidence_refs"] + [ref(CKPT)],
        artifact_refs=[ref(FILES["report"]), ref(FILES["raw_measurements"]),
                       ref(FILES["pre_registration"])])

    add("checkpoint", "status", node_id="A1", gate="G-AUDIT", class_id=cid,
        status="active",
        summary=("Worker-local checkpoint written (controller runtime checkpoint untouched): "
                 f"runtime/state/{CKPT.name}; pins adjudication {adj_hash[:12]}, detector "
                 f"{det_hash[:12]} (restored cited bytes), map {map_hash[:12]}."),
        evidence_refs=[ref(CKPT), ref(FILES["report"])])

    add("complete", "status", node_id="A1", gate="G-AUDIT", class_id=cid,
        status="active", completion_claim=True, hours=0.5,
        summary=("W098-CLASSSEP-ADJ-REVIEW-01 complete as a bounded class-bound task: "
                 "independent read-only review of the r3 CLASSSEP adjudication at its frozen "
                 "hashes. Verdict accept 4.5, 12/12 pre-registered expectations PASS, all 20 "
                 "per-arm corpus cells reproduced, decision (c) supported, attribution "
                 "correction confirmed, fifth arm measured, CF-29 churn recorded, residual "
                 "hard count restated (19 = 17 labeled FP + 2 unlabeled). Task-completion "
                 "claim only: no gate verdict, no node completion, no canonical write; the "
                 "lead/controller must ingest and decide."),
        evidence_refs=rep["evidence_refs"] + [ref(CKPT)],
        next_falsifier=rep["falsifier"])

    with OUTBOX.open("a") as f:
        for e in ev:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # validate what was written
    lines = [ln for ln in OUTBOX.read_text().splitlines() if ln.strip()]
    mine = [json.loads(ln) for ln in lines if json.loads(ln).get("event_id", "").startswith(
        f"w098-car-{STAMP}")]
    print(f"checkpoint {CKPT.relative_to(ROOT)} sha256={ckpt_hash}")
    print(f"appended {len(mine)} events to {OUTBOX.relative_to(ROOT)}; all parse OK")
    for e in mine:
        print(" ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
