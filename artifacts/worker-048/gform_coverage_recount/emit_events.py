#!/usr/bin/env python3
"""Emit W48-GFORM-COVERAGE-DRIFT-RECOUNT-01 events to comms/outbox/worker-048.jsonl.

Idempotent: re-running skips event_ids already present in the outbox. Worker events cannot set
status=done, validation_status=passed, or any gate verdict.
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/worker-048.jsonl"
ART = ROOT / "artifacts/worker-048/gform_coverage_recount"
REVIEW = ROOT / "reviews/W048-GFORM-COVERAGE-RECOUNT-01.json"
TASK = "W48-GFORM-COVERAGE-DRIFT-RECOUNT-01"
GATE = "G-FORM"
NODE = "F1/F2a/F2b"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
FALSIFIER = ("At the bytes recorded in report.json inputs_manifest and corpus digest e16661b084ddf3b9: "
             "(a) any R1 file set differing from astra_lifecycle.review_coverage at 957c61e3eb0e on that "
             "corpus; (b) any pass-06 accept still counted at live bytes that the report lists as demoted; "
             "(c) any R2 accept violating the closed binding rule; (d) any control not flipping as declared; "
             "(e) corpus digest unchanged but per-file manifest differing. A later write to a review file or "
             "the instrument is a new revision to re-run against, not a falsifier.")


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def main():
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    files = {
        "report": ART / "report.json",
        "report_run2": ART / "report_run2.json",
        "instrument_script": ART / "recount_coverage.py",
        "readme": ART / "README.md",
        "review_record": REVIEW,
    }
    hashes = {k: sha12(v) for k, v in files.items()}
    report = json.loads(files["report"].read_text())
    summary = report["summary"]
    ev = []

    ev.append({
        "event_id": "w48-covrecount-status-start",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-048",
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "status": "active",
        "hours": 0.1,
        "summary": ("Took ONE bounded class-bound task (no assignment card exists for worker-048): "
                    "W48-GFORM-COVERAGE-DRIFT-RECOUNT-01 = independent recount of the G-FORM "
                    "at-pin review coverage for F1/F2a/F2b, reconciled against pass-06."),
        "evidence_refs": [],
        "next_falsifier": FALSIFIER,
    })

    for key, p in files.items():
        ev.append({
            "event_id": f"w48-covrecount-artifact-{key}",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-048",
            "node_id": NODE,
            "gate": GATE,
            "class_ids": CLASS_IDS,
            "task_id": TASK,
            "artifact_type": "review_record" if key == "review_record" else "audit_artifact",
            "path": str(p.relative_to(ROOT)),
            "sha256": hashes[key],
            "validation_status": "unvalidated",
            "summary": f"{key} for {TASK}",
        })

    ev.append({
        "event_id": "w48-covrecount-claim",
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-048",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
        "node_id": NODE,
        "gate": GATE,
        "task_id": TASK,
        "conclusion_type": "audit_measurement",
        "statement": (
            "At the pinned snapshot (202 review files, corpus digest e16661b084ddf3b9; instrument "
            "research_map/astra_lifecycle.py#957c61e3eb0e; schemas d9cebb9404b2 / e9a27996dfd3 / "
            "b2ab6acb2bbe; FROZEN rev29 815e08079aef), a controller-equivalent recount (R1, oracle-checked "
            "against astra_lifecycle.review_coverage) gives full-accept coverage F1 4 (052,072,075,085), "
            "F2a 2 (017,072), F2b 2 (090,072); the extended binding rule R2 gives F1 5 (+089 path#hash "
            "target), F2a 2, F2b 2. The published pass-06 reason 'F1 4 / F2a 3 / F2b 0' is not reproducible "
            "at live bytes: F2a lost one accept to a post-report rewrite (F2a-review-rev29-075.json "
            "accept->revise 01:03:36 > report 01:01:17) and F2b gained two full accepts after it "
            "(F2b-rev13-full-090.json 01:08:56; F2b-review-worker-072-rev29.json 01:09:13), both exact-64 "
            "target-bound pins with no hard failures. Instrument defect measured: _targets_in_review drops "
            "path#hash-target reviews and _explicit_pins drops dict-valued reviewed_sha256, so worker-089's "
            "F1 accept is invisible to the controller (R1 4 vs R2 5) and the F2b verdict census is 2 vs 10. "
            "An intermediate run at instrument e096b14beb6a found F2b 0 before those accepts landed; it is "
            "superseded. This is an advisory measurement, not a gate verdict."),
        "assumptions": [
            "reviews/*.json are the review corpus and are mutable, unpinned files",
            "the controller rule treats a missing counts_as_full_schema_verdict as full",
            "reviewer independence is only measured as distinct reviewer ids; author/blind adjudication is the audit lead's",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [
            f"artifacts/worker-048/gform_coverage_recount/report.json#{hashes['report']}",
            f"artifacts/worker-048/gform_coverage_recount/recount_coverage.py#{hashes['instrument_script']}",
            "runtime/state/controller_verification/lifecycle_20260912-010117.json#076d03a64321",
            "reviews/F2b-rev13-full-090.json#345f74bb73f4",
            "reviews/F2b-review-worker-072-rev29.json#187bff41af23",
            "reviews/F1-review-worker-089.json#9a4bb3f3268c",
            "reviews/F2a-review-rev29-075.json#d3c34527ec35",
        ],
        "artifact_refs": [
            f"artifacts/worker-048/gform_coverage_recount/report.json#{hashes['report']}",
            f"artifacts/worker-048/gform_coverage_recount/README.md#{hashes['readme']}",
        ],
    })

    ev.append({
        "event_id": "w48-covrecount-review",
        "event_type": "review",
        "created_at": now,
        "actor": "worker-048",
        "reviewer": "worker-048",
        "target_id": "research_map/astra_lifecycle.py#957c61e3eb0e5002",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
        "node_id": NODE,
        "gate": GATE,
        "task_id": TASK,
        "verdict": "revise",
        "score": 3.5,
        "counts_as_full_schema_verdict": False,
        "review_kind": "instrument and process audit of the G-FORM review-coverage counter; not a schema semantics review",
        "hard_failures": [
            {"id": "HF-W48-CR-1", "check": "review-byte stability",
             "claim": "published coverage not reproducible from live bytes; F2a 3 is false at live bytes (2); F1 count stable only by coincidence; review files carry no pin and gate reasons no corpus digest"},
            {"id": "HF-W48-CR-2", "check": "target normalization",
             "claim": "_targets_in_review drops path#hash targets and _explicit_pins drops dict-valued reviewed_sha256; worker-089 F1 accept invisible (R1 4 vs R2 5); F2b census 2 vs 10"},
        ],
        "findings": [
            {"id": "W48-CR-F1", "severity": "info",
             "detail": "live recount F1 4 (R2 5), F2a 2, F2b 2 full accepts at current schema bytes"},
            {"id": "W48-CR-F2", "severity": "info",
             "detail": "pass-06 'F2b 0' stale: two full accepts landed 01:08:56 and 01:09:13 after the 01:01:17 report"},
            {"id": "W48-CR-F3", "severity": "advisory",
             "detail": "F2b independence caveats: worker-072 blind=true non-author, flag omitted; worker-090 blind=false with disclosure; adjudication is the audit lead's"},
            {"id": "W48-CR-F4", "severity": "info",
             "detail": "instrument moved 032d4afcb061 -> e096b14beb6a -> 957c61e3eb0e mid-task; oracle re-run at final bytes"},
        ],
        "evidence_refs": [
            f"artifacts/worker-048/gform_coverage_recount/report.json#{hashes['report']}",
            f"reviews/W048-GFORM-COVERAGE-RECOUNT-01.json#{hashes['review_record']}",
            "reviews/F2b-rev13-full-090.json#345f74bb73f4",
            "reviews/F2b-review-worker-072-rev29.json#187bff41af23",
            "reviews/F1-review-worker-089.json#9a4bb3f3268c",
            "reviews/F2a-review-rev29-075.json#d3c34527ec35",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        ],
        "falsifier": FALSIFIER,
    })

    ev.append({
        "event_id": "w48-covrecount-status-complete",
        "event_type": "status",
        "created_at": now,
        "actor": "worker-048",
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "status": "active",
        "hours": 0.3,
        "summary": (
            "W48-GFORM-COVERAGE-DRIFT-RECOUNT-01 complete at worker level: 5 hash-pinned deliverables "
            "(two byte-identical reports 53faf0cccd1d, 526-line deterministic instrument f57f09145605, "
            "README, hash-bound review record). 10/10 controls pass, including an oracle call into the "
            "controller's own review_coverage at instrument 957c61e3eb0e. Live coverage F1 4 (R2 5), "
            "F2a 2, F2b 2; pass-06 published numbers are stale in both directions; two instrument defects "
            "measured (unpinned review bytes; path#hash/dict-pin normalization blind spot). Not a gate "
            "verdict, no node transition, no canonical write. Checkpoint "
            "runtime/state/w048_coverage_recount_checkpoint.json."),
        "evidence_refs": [
            f"artifacts/worker-048/gform_coverage_recount/report.json#{hashes['report']}",
            f"reviews/W048-GFORM-COVERAGE-RECOUNT-01.json#{hashes['review_record']}",
        ],
        "next_falsifier": FALSIFIER,
    })

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    emitted = [e for e in ev if e["event_id"] not in existing]
    with open(OUTBOX, "a") as fh:
        for e in emitted:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    (ART / "emitted_events.json").write_text(json.dumps(
        {"events": ev, "newly_emitted": [e["event_id"] for e in emitted],
         "skipped_existing": [e["event_id"] for e in ev if e["event_id"] in existing],
         "hashes": hashes}, indent=1, sort_keys=True) + "\n")
    print(f"emitted {len(emitted)} events, skipped {len(ev) - len(emitted)} existing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
