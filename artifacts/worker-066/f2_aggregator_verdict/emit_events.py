#!/usr/bin/env python3
"""W066-F2AGG-VERDICT-01 -- emit schema-valid events to comms/outbox/worker-066.jsonl.

Deterministic event ids derived from the report hash, so re-running is idempotent.
Each line is validated with research_map.schemas.validate_event before it is appended.

Usage:
  python3 emit_events.py                    # task/review/artifact/claim/blocker/complete
  python3 emit_events.py --phase checkpoint # + checkpoint status (needs CHECKPOINT.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

OUTBOX = ROOT / "comms" / "outbox" / "worker-066.jsonl"
CST = timezone(timedelta(hours=8))
TASK = "W066-F2AGG-VERDICT-01"
NODE = "F2"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
AGG = "schemas/af_scc_regularities.yaml"
TARGET = f"{AGG}#94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ref(rel: str, prefix: int = 12) -> str:
    return f"{rel}#{sha256(ROOT / rel)[:prefix]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("main", "checkpoint"), default="main")
    a = ap.parse_args()

    report = json.loads((HERE / "report.json").read_text())
    token = sha256(HERE / "report.json")[:6]
    base = f"w066-f2agg-{token}"
    ts = now()
    verdict = report["verdict"]
    findings = report["findings"]
    live = report["live_recheck"]

    def ev(eid, etype, **kw):
        e = {"event_id": eid, "event_type": etype, "created_at": ts, "actor": "worker-066"}
        e.update(kw)
        return e

    events = []
    if a.phase == "main":
        events += [
            ev(f"{base}-status-task", "status", node_id=NODE, status="active", hours=0.2,
               task_id=TASK, class_id=CLASS_IDS[0], class_ids=CLASS_IDS,
               summary=("No assignment card exists for worker-066 (fleet instance 20260912T002907). Took one bounded "
                        "class-bound task, W066-F2AGG-VERDICT-01: independent hash-bound verification of the live F2 "
                        "aggregator schemas/af_scc_regularities.yaml#94562101a816 (classes AF-SCC-C2-VAC-GEN, "
                        "AF-SCC-C0-VAC-GEN), which the only recorded pin check had reviewed only at the retired "
                        "c6bfda2b. Verdict below is a reviewer verdict; workers cannot move gates."),
               evidence_refs=[ref("artifacts/worker-066/f2_aggregator_verdict/PINNED.json")],
               next_falsifier=report["next_falsifier"]),
            ev(f"{base}-artifact-pinned", "artifact", node_id=NODE, artifact_type="manifest",
               path="artifacts/worker-066/f2_aggregator_verdict/PINNED.json",
               sha256=sha256(HERE / "PINNED.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="ten pinned inputs, sha256/bytes/mtime + byte copies in pinned/"),
            ev(f"{base}-artifact-report", "artifact", node_id=NODE, artifact_type="verdict",
               path="artifacts/worker-066/f2_aggregator_verdict/report.json",
               sha256=sha256(HERE / "report.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="full verdict: 15 checks, 5 hard findings, falsifiers, evidence refs"),
            ev(f"{base}-artifact-checks", "artifact", node_id=NODE, artifact_type="evidence",
               path="artifacts/worker-066/f2_aggregator_verdict/evidence/checks.json",
               sha256=sha256(HERE / "evidence" / "checks.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="every independent check with raw observations"),
            ev(f"{base}-artifact-controls", "artifact", node_id=NODE, artifact_type="evidence",
               path="artifacts/worker-066/f2_aggregator_verdict/evidence/controls.json",
               sha256=sha256(HERE / "evidence" / "controls.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="8/8 controls: pristine passes, seven mutants each rejected by the pre-registered rule"),
            ev(f"{base}-artifact-staleness", "artifact", node_id=NODE, artifact_type="evidence",
               path="artifacts/worker-066/f2_aggregator_verdict/evidence/staleness.json",
               sha256=sha256(HERE / "evidence" / "staleness.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="rule-spec/F0-pointer/prior-pin-check/freeze-membership/map-label probes"),
            ev(f"{base}-artifact-livedrift", "artifact", node_id=NODE, artifact_type="evidence",
               path="artifacts/worker-066/f2_aggregator_verdict/evidence/live_drift.json",
               sha256=sha256(HERE / "evidence" / "live_drift.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="components moved 00:32:02; C2 -> 5476a3f2c6bc, C0 -> 55d0a1ea9bda"),
            ev(f"{base}-artifact-authorlint", "artifact", node_id=NODE, artifact_type="evidence",
               path="artifacts/worker-066/f2_aggregator_verdict/evidence/author_lint_report.json",
               sha256=sha256(HERE / "evidence" / "author_lint_report.json"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="author lint cross-check: aggregator=fail, failing only A3/C6 component pins"),
            ev(f"{base}-artifact-verifier", "artifact", node_id=NODE, artifact_type="code",
               path="artifacts/worker-066/f2_aggregator_verdict/verify_aggregator.py",
               sha256=sha256(HERE / "verify_aggregator.py"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="independent checker + control builder; re-runnable on the pins"),
            ev(f"{base}-artifact-snapshotter", "artifact", node_id=NODE, artifact_type="code",
               path="artifacts/worker-066/f2_aggregator_verdict/snapshot.py",
               sha256=sha256(HERE / "snapshot.py"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="pin/snapshot step"),
            ev(f"{base}-artifact-readme", "artifact", node_id=NODE, artifact_type="readme",
               path="artifacts/worker-066/f2_aggregator_verdict/README.md",
               sha256=sha256(HERE / "README.md"), validation_status="unverified", task_id=TASK,
               class_ids=CLASS_IDS, note="method, results table, findings + falsifiers, limits"),
            ev(f"{base}-review-aggregator", "review", target_id=TARGET, reviewer="worker-066",
               verdict=verdict["verdict"], score=verdict["score"], hard_failures=verdict["hard_failures"],
               findings=[f"{f['id']} [{f['severity']}] {f['statement'][:400]}" for f in findings],
               reviewed_sha256="94562101a81645349e1ff17b9184dd956887d8fc6b54a3d7ed7cd786ed8b4ce4",
               node_id=NODE, class_id=CLASS_IDS[0], class_ids=CLASS_IDS, task_id=TASK,
               note=verdict["note"]),
            ev(f"{base}-claim-verdict", "claim", node_id=NODE, task_id=TASK, class_id=CLASS_IDS[0],
               class_ids=CLASS_IDS, conclusion_type="formal_model",
               statement=("At the pinned F2 aggregator schemas/af_scc_regularities.yaml#94562101a816 with component "
                          "pins C2 b6123750b37d / C0 1bb78ce9b357, an independent re-implementation confirms all seven "
                          "declared separation invariants and the contract booleans, and eight pre-registered controls "
                          "behave as specified (pristine passes; seven hand-built mutants each rejected by their rule). "
                          "The same bytes fail five independent probes: duplicate root key revised_at x4 (lines 11-14); "
                          "stale bindings (rule_spec v1.1 declared vs 1.2 frozen; 14 gate-enforced rule ids undeclared; "
                          "F0 pointer 0fcc6a19 matches neither live F0 tree); no pin re-check at these bytes (the recorded "
                          "check targets retired c6bfda2b and fails); not freeze-bound (absent from FROZEN rev26) and the "
                          "map legacy_artifacts record mislabels these bytes as the retired merged file; and, measured "
                          "during the task, the live C2/C0 components moved at 00:32:02 so the pins no longer resolve. "
                          "Reviewer verdict: revise 2.5. This is a machine-checker result, not a claim about the "
                          "mathematics of either component."),
               assumptions=["a verdict binds bytes, not paths; all checks ran on pinned copies",
                            "the aggregator declares itself a non-class reference index, so only structural invariants are in scope",
                            "controls use the pinned component bytes so that a mutation is the only variable",
                            "live drift is reported as measured; no canonical file was written by this task"],
               falsifier=report["next_falsifier"],
               evidence_refs=[ref("artifacts/worker-066/f2_aggregator_verdict/evidence/checks.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/evidence/controls.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/evidence/staleness.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/evidence/live_drift.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/PINNED.json")],
               artifact_refs=[ref("artifacts/worker-066/f2_aggregator_verdict/report.json")]),
            ev(f"{base}-blocker-repin", "blocker", node_id=NODE, task_id=TASK, class_ids=CLASS_IDS,
               description=("F2 aggregator schemas/af_scc_regularities.yaml#94562101a816 pins C2 b6123750b37d / C0 "
                            "1bb78ce9b357, but the live schemas were rewritten at 00:32:02 to "
                            f"C2 {live['c2_live_sha256'][:12]} / C0 {live['c0_live_sha256'][:12]}; SEP-6 and the author "
                            "lint A3/C6 both fail at verdict time, so the aggregator is invalidated as a G-FORM input "
                            "until re-pinned."),
               needed_to_unblock=("re-pin both component sha256 values to the live schemas, re-run the independent pin "
                                  "check at the new aggregator hash, re-emit the artifact event, and (for freeze use) "
                                  "add the aggregator to the FROZEN manifest with a corrected map role label"),
               evidence_refs=[ref("artifacts/worker-066/f2_aggregator_verdict/evidence/live_drift.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/evidence/author_lint_report.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/evidence/checks.json")]),
            ev(f"{base}-status-complete", "status", node_id=NODE, status="active", hours=0.7,
               task_id=TASK, class_id=CLASS_IDS[0], class_ids=CLASS_IDS,
               summary=("W066-F2AGG-VERDICT-01 complete as a bounded worker lifecycle: verdict revise 2.5 with 5 hard "
                        "findings and explicit falsifiers; all artifacts exist on disk and are hash-pinned; events are "
                        "schema-validated. This is a completion claim, not a node/gate transition. Checkpoint follows."),
               evidence_refs=[ref("artifacts/worker-066/f2_aggregator_verdict/report.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/evidence/checks.json"),
                              ref("artifacts/worker-066/f2_aggregator_verdict/README.md")],
               next_falsifier=report["next_falsifier"]),
        ]
    else:
        ck = json.loads((HERE / "CHECKPOINT.json").read_text())
        events.append(ev(f"{base}-status-checkpoint", "status", node_id=NODE, status="active", hours=0.8,
                         task_id=TASK, class_id=CLASS_IDS[0], class_ids=CLASS_IDS,
                         summary=(f"Checkpoint {ck['checkpoint_id']} (label {ck['label']}) run after the "
                                  f"{ck['events_emitted']} W066-F2AGG events: map {ck['map_validator']}, gates "
                                  f"{ck['gates']}, live pin drift still present, evidence hard failures "
                                  f"{ck['evidence_hard_failures']} (one is a CLASSSEP detector false positive on this "
                                  "task's own claim wording 'live C2/C0 components', documented in CHECKPOINT.json; "
                                  "precedent CF-16). worker-066 lifecycle complete; this event lands in the next "
                                  "ingest cycle."),
                         evidence_refs=[ref("artifacts/worker-066/f2_aggregator_verdict/CHECKPOINT.json"),
                                        ref("artifacts/worker-066/f2_aggregator_verdict/report.json")],
                         next_falsifier=report["next_falsifier"]))

    for e in events:
        try:
            validate_event(e)
        except SchemaError as ex:
            print(f"SCHEMA REJECT {e['event_id']}: {ex}")
            return 2

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"phase": a.phase, "validated": len(events), "appended": len(new),
                      "skipped_existing": len(events) - len(new),
                      "event_ids": [e["event_id"] for e in events]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
