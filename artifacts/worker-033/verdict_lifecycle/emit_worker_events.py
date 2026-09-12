#!/usr/bin/env python3
"""Emit W033-VERDICT-LIFECYCLE-01 events and the worker checkpoint.

Writes (append-only on the outbox):
  comms/outbox/worker-033.jsonl
  runtime/state/w033_verdict_lifecycle_checkpoint.json
  runtime/state/w033_checkpoints.jsonl  (one appended line)

Every event is validated with research_map/schemas.py:validate_event before it
is written.  Worker events cannot set node status=done, validation_status=passed,
or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
TS = NOW.isoformat()
SLOT = NOW.strftime("%Y%m%dT%H%M%S")
AGENT = "worker-033"
NODES = "F1,F2a,F2b"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


FILES = {
    "checker": TASK / "check_verdict_lifecycle.py",
    "report": TASK / "report.json",
    "controls": TASK / "controls.json",
    "drift": TASK / "drift.json",
    "runlog": TASK / "run.log",
    "readme": TASK / "README.md",
    "pinned_manifest": TASK / "SHA256SUMS",
}
H = {k: sha(p) for k, p in FILES.items()}
report = json.loads(FILES["report"].read_text())
drift = json.loads(FILES["drift"].read_text())
R = report["analysis"]
recon = report["reconciliation"]

statement = (
    "FORMAL-MODEL-LEVEL binding audit (not a mathematical theorem, not a numerical "
    "result) at pinned inputs: events.jsonl from research_map, reviews/*.json x93, and "
    "the two controller lifecycle reports. Verdict-lifecycle measurement for the three "
    "G-FORM classes: at rev11 F1 9a8bd4c96800 / F2a b6123750b37d / F2b 1bb78ce9b357, "
    "the accept sets quoted in the controller gate reason checked_at 2026-09-12T00:24:40 "
    "(F1 [astra-lead-audit], F2a [astra-lead-audit, worker-047], F2b [astra-lead-audit, "
    "deepseek-flash-07, deepseek-flash-17, worker-030]) are not the operative sets. "
    "Applying explicit supersession and same-reviewer latest-wins: F1 operative full "
    "independent accepts = [worker-026] (1, below the two-accept criterion); F2a = "
    "[worker-050, worker-069, worker-072, worker-078, worker-098] (5); F2b = [worker-001, "
    "worker-096, deepseek-flash-17, worker-030, worker-089] (5). astra-lead-audit's three "
    "quoted accepts are declared withdrawn by reviews/F*-review-lead-audit-r2.json; "
    "worker-047 withdrew its F2a accept in event w047-20260912T0030-d0x-review-f2a while "
    "reviews/F2a-review-047.json still records accept; deepseek-flash-07's F2b accept is "
    "superseded by its own corrected reviews/F2b-review-07.json. At the current rev12 "
    "hashes F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda the operative full "
    "accept set is empty (5 bound verdict records, all revise), so G-FORM must remain "
    "pending and no rev11 accept may be carried over. Mechanism: "
    "astra_lifecycle.review_coverage() has no supersession model and reads only "
    "reviews/*.json, so it produced stale positives (withdrawn accepts) and false "
    "negatives (>=4 F2a and >=3 F2b full-schema accepts existed at quote time only in the "
    "accepted event stream)."
)

falsifier = (
    "Re-run artifacts/worker-033/verdict_lifecycle/check_verdict_lifecycle.py on the "
    "pinned snapshot (10/10 controls, fail-closed). Any of: a pinned record in which "
    "astra-lead-audit, worker-047 or deepseek-flash-07 re-issues an accept at the same "
    "rev11 hash after the recorded withdrawal; a pinned reviews/*.json or event accept at "
    "rev11 by worker-050/072/078/098 (F2a) or worker-001/089/096 (F2b); a second binding "
    "full-schema F1 accept at 9a8bd4c96800 or a declaration that worker-031's accept "
    "targets the schema rather than schemas/f1_falsifier_tests.jsonl; any post-rev12 "
    "record binding cce9c60146d6/5476a3f2c6bc/55d0a1ea9bda with accept; or a revision of "
    "astra_lifecycle.review_coverage() that models supersession and reads the event "
    "stream, after which scan A/B agree with the operative ledger."
)

events = [
    {"event_id": f"w033-vl-{SLOT}-claim", "event_type": "status", "created_at": TS,
     "actor": AGENT, "node_id": NODES, "status": "active", "hours": 0.1,
     "summary": ("Took one bounded class-bound task W033-VERDICT-LIFECYCLE-01: operative "
                 "accept sets for AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN at "
                 "the G-FORM canonical hashes, from the union of reviews/*.json and the "
                 "accepted event stream with explicit supersession and same-reviewer "
                 "latest-wins. Output is a hash-pinned measurement, checker, controls and "
                 "reconciliation; no gate verdict, no done-status, no theorem."),
     "evidence_refs": [f"research_map/events.jsonl#{sha(ROOT / 'research_map/events.jsonl')[:12]}",
                       f"reviews/F2a-review-047.json#{sha(ROOT / 'reviews/F2a-review-047.json')[:12]}",
                       f"reviews/F2a-review-lead-audit-r2.json#{sha(ROOT / 'reviews/F2a-review-lead-audit-r2.json')[:12]}"],
     "next_falsifier": falsifier},
]
for key, atype in (("checker", "independent_checker_source"),
                   ("report", "verdict_lifecycle_report"),
                   ("controls", "falsifier_control_matrix"),
                   ("drift", "live_drift_observation"),
                   ("readme", "task_readme"),
                   ("runlog", "run_log"),
                   ("pinned_manifest", "pinned_input_manifest")):
    events.append({
        "event_id": f"w033-vl-{SLOT}-artifact-{key}", "event_type": "artifact",
        "created_at": TS, "actor": AGENT, "node_id": NODES, "artifact_type": atype,
        "path": str(FILES[key].relative_to(ROOT)), "sha256": H[key],
        "validation_status": "unverified", "class_ids": CLASSES.split(";"),
        "evidence_refs": [f"{FILES[key].relative_to(ROOT)}#{H[key][:12]}"],
        "note": "worker-033 bounded task deliverable; worker-level only",
    })
events.append({
    "event_id": f"w033-vl-{SLOT}-claim-formal", "event_type": "claim", "created_at": TS,
    "actor": AGENT, "node_id": NODES, "class_id": CLASSES,
    "class_ids": CLASSES.split(";"), "conclusion_type": "formal_model",
    "statement": statement,
    "assumptions": [
        "Verdicts bind only through explicit target-pin fields (artifact_sha256, "
        "reviewed_sha256, sha256, cited_sha256, target_evidence, target_id); evidence_refs "
        "never bind.",
        "Scope is taken from counts_as_full_schema_verdict (False = scoped, excluded from "
        "full-schema accepts).",
        "Supersession = explicit named reference (S1) or a later verdict by the same "
        "reviewer at the same target+epoch (S2); duplicate channel records are "
        "deduplicated, not treated as withdrawals.",
        "Findings bind the pinned hashes; any byte change to the pinned corpus retires them.",
    ],
    "falsifier": falsifier,
    "artifact_refs": [f"{FILES[k].relative_to(ROOT)}#{H[k][:12]}"
                      for k in ("report", "checker", "controls", "pinned_manifest")],
    "evidence_refs": [f"{FILES[k].relative_to(ROOT)}#{H[k][:12]}"
                      for k in ("report", "checker", "controls", "pinned_manifest", "readme")],
})
events.append({
    "event_id": f"w033-vl-{SLOT}-blocker", "event_type": "blocker", "created_at": TS,
    "actor": AGENT, "node_id": NODES,
    "description": (
        "G-FORM acceptance bookkeeping is not reproducible from the pinned corpus. (1) At "
        "rev11 every F2a accept quoted at 00:24:40 is withdrawn at the same hash, and F1's "
        "only operative full-schema accept is worker-026, below the two-accept criterion. "
        "(2) review_coverage() reads only reviews/*.json and has no supersession model: it "
        "counted withdrawn accepts and missed >=4 F2a and >=3 F2b event-only full-schema "
        "accepts that were already operative at 00:24:40. (3) At rev12 "
        "(cce9c60146d6/5476a3f2c6bc/55d0a1ea9bda) the operative accept set is empty; the "
        "five bound records are all revise."),
    "needed_to_unblock": (
        "Recompute the G-FORM gate reason with a supersession-aware, two-channel ledger "
        "(or patch astra_lifecycle.review_coverage accordingly), and obtain fresh "
        "hash-bound independent accepts at the rev12 hashes; F1 additionally needs a "
        "second binding full-schema accept (or a re-issued accept at whatever hash becomes "
        "canonical). Do not carry over rev11 accepts."),
    "evidence_refs": [f"{FILES[k].relative_to(ROOT)}#{H[k][:12]}"
                      for k in ("report", "checker", "controls")],
})
events.append({
    "event_id": f"w033-vl-{SLOT}-ckpt1", "event_type": "status", "created_at": TS,
    "actor": AGENT, "node_id": NODES, "status": "active", "hours": 0.4,
    "summary": (f"Checkpoint w033-vl-ckpt1: tool {H['checker'][:12]}, report "
                f"{H['report'][:12]}, controls 10/10 PASS, no target drift "
                f"(live == pinned for F0/F1/F2a/F2b). F1 rev11 operative accepts "
                f"{R['F1']['rev11']['operative_accepts_full_independent']}; F2a "
                f"{R['F2a']['rev11']['operative_accepts_full_independent']}; F2b "
                f"{R['F2b']['rev11']['operative_accepts_full_independent']}; current "
                f"rev12 empty for all three."),
    "evidence_refs": [f"{FILES[k].relative_to(ROOT)}#{H[k][:12]}"
                      for k in ("report", "controls", "pinned_manifest")],
    "next_falsifier": "Re-run the checker on the pinned snapshot; any control failure or "
                      "any record contradicting a retirement flips the affected finding."},
)
events.append({
    "event_id": f"w033-vl-{SLOT}-complete", "event_type": "status", "created_at": TS,
    "actor": AGENT, "node_id": NODES, "status": "active", "hours": 0.7,
    "summary": ("W033-VERDICT-LIFECYCLE-01 complete at worker level: artifacts exist on "
                "disk with measured hashes, 10/10 controls pass, checker fail-closed. "
                "Findings W033-VL-01..06 (F2a/F2b quoted accepts withdrawn; F1 rev11 "
                "shortfall; event-only scan blind spot; empty rev12 operative set; two "
                "review_coverage defects) each carry a falsifier. Bounded worker lifecycle "
                "complete; exiting for re-queue. Worker cannot set done/passed or a gate "
                "verdict."),
    "evidence_refs": [f"{FILES[k].relative_to(ROOT)}#{H[k][:12]}"
                      for k in ("report", "checker", "controls", "readme", "runlog",
                                "pinned_manifest")],
    "next_falsifier": falsifier},
)

for e in events:
    validate_event(e)

if "--dry-run" in sys.argv:
    print(f"dry-run OK: {len(events)} events validate")
    for e in events:
        print("  ", e["event_id"], e["event_type"])
    sys.exit(0)

outbox = ROOT / "comms/outbox" / f"{AGENT}.jsonl"
with outbox.open("a") as f:
    for e in events:
        f.write(json.dumps(e, sort_keys=True) + "\n")

checkpoint = {
    "schema": "worker-checkpoint/1",
    "task_id": "W033-VERDICT-LIFECYCLE-01",
    "worker": AGENT,
    "created_at": TS,
    "node_ids": ["F1", "F2a", "F2b"],
    "class_ids": CLASSES.split(";"),
    "status": "complete-worker-level",
    "authority_note": ("worker event; cannot set node status=done, "
                       "validation_status=passed, or a gate verdict"),
    "pinned_manifest_sha256": H["pinned_manifest"],
    "artifacts": {str(FILES[k].relative_to(ROOT)): H[k] for k in FILES},
    "headline": {
        "rev11": {"F1": recon["F1"], "F2a": recon["F2a"], "F2b": recon["F2b"]},
        "current": {t: R[t]["current"]["operative_accepts_full_independent"]
                    for t in ("F1", "F2a", "F2b")},
        "current_hashes": {t: report["epochs"][t]["current"] for t in ("F1", "F2a", "F2b")},
        "drift_live_vs_pinned": drift["drift_live_vs_pinned"],
    },
    "findings": [
        {"id": "W033-VL-01", "target": "F2a",
         "claim": "both quoted accepts withdrawn at b6123750b37d"},
        {"id": "W033-VL-02", "target": "F2b",
         "claim": "lead-audit and deepseek-flash-07 quoted accepts withdrawn"},
        {"id": "W033-VL-03", "target": "F1",
         "claim": "quoted accept withdrawn; operative set = {worker-026}, below threshold"},
        {"id": "W033-VL-04", "target": "F2a,F2b",
         "claim": "event-only full-schema accepts invisible to reviews/*.json scan"},
        {"id": "W033-VL-05", "target": "F1,F2a,F2b",
         "claim": "rev12 operative accept set empty; gate must stay pending"},
        {"id": "W033-VL-06", "target": "A1",
         "claim": "review_coverage has no supersession model and reads one channel"},
    ],
    "falsifier": falsifier,
    "controls_pass": report["controls_pass"],
    "tool_sha256": report["tool_sha256"],
    "rerun": "python3 artifacts/worker-033/verdict_lifecycle/check_verdict_lifecycle.py",
}
ck = ROOT / "runtime/state/w033_verdict_lifecycle_checkpoint.json"
ck.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")
with (ROOT / "runtime/state/w033_checkpoints.jsonl").open("a") as f:
    f.write(json.dumps({"task_id": checkpoint["task_id"], "created_at": TS,
                        "status": checkpoint["status"],
                        "checkpoint_path": str(ck.relative_to(ROOT)),
                        "checkpoint_sha256": sha(ck)}) + "\n")

print(f"wrote {len(events)} validated events to {outbox.relative_to(ROOT)}")
for k, v in H.items():
    print(f"  {k}: {v}")
print(f"checkpoint {ck.relative_to(ROOT)} sha256 {sha(ck)}")
