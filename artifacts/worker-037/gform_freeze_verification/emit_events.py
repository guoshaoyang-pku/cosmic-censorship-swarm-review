#!/usr/bin/env python3
"""Emit worker-037's result events to comms/outbox/worker-037.jsonl and checkpoint.

Validates every event against research_map/schemas.validate_event before writing.
Authority: worker events cannot set status=done, validation_status=passed, or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")
STAMP = time.strftime("%Y%m%dT%H%M%S")
REPORT = "artifacts/worker-037/gform_freeze_verification/report.json"
SCRIPT = "artifacts/worker-037/gform_freeze_verification/verify_gform_freeze.py"


def sha(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


REPORT_SHA = sha(REPORT)
SCRIPT_SHA = sha(SCRIPT)
R = json.loads((ROOT / REPORT).read_text())
DISK = {n: v["sha256"] for n, v in R["snapshot_T0"].items()}
FROZEN_SHA = DISK["artifacts/formulation/FROZEN.json"]
NEXT_FALSIFIER = R["next_falsifier"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
EVIDENCE = [
    f"{REPORT}#{REPORT_SHA[:12]}",
    f"{SCRIPT}#{SCRIPT_SHA[:12]}",
    f"artifacts/formulation/FROZEN.json#{FROZEN_SHA[:12]}",
    f"schemas/af_wcc_vacuum.yaml#{DISK['schemas/af_wcc_vacuum.yaml'][:12]}",
    f"schemas/af_scc_c2_vacuum.yaml#{DISK['schemas/af_scc_c2_vacuum.yaml'][:12]}",
    f"schemas/af_scc_c0_vacuum.yaml#{DISK['schemas/af_scc_c0_vacuum.yaml'][:12]}",
    f"research_map/formulation_taxonomy.yaml#{DISK['research_map/formulation_taxonomy.yaml'][:12]}",
]
DNC = ["G-FORM pass/fail", "G-F0 pass/fail", "node completion", "theorem", "physics result",
       "authority to edit canonical artifacts", "one of the two required accepts"]

events = []
for node, cls in zip(["F1", "F2a", "F2b"], CLASSES):
    events.append({
        "event_id": f"w037-{STAMP}-art-{node.lower()}-gform-freeze-verification",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-037",
        "node_id": node,
        "class_id": cls,
        "artifact_type": "verification_report",
        "path": REPORT,
        "sha256": REPORT_SHA,
        "validation_status": "unverified",
        "gate": "G-FORM",
        "task_id": "W037-GFORM-FREEZE-01",
        "checker": f"{SCRIPT}#{SCRIPT_SHA[:12]}",
        "evidence_refs": EVIDENCE,
        "worker_verdict": R["worker_verdict"],
        "findings": [f["id"] for f in R["findings"]],
        "falsifier": NEXT_FALSIFIER,
        "does_not_claim": DNC,
    })

events.append({
    "event_id": f"w037-{STAMP}-status-gform-freeze-verification",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-037",
    "node_id": "F2",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "status": "active",
    "hours": 0.7,
    "summary": "W037-GFORM-FREEZE-01 independent verification (read-only) of "
               f"{R['request_under_test']['event_id']}. Result at measured bytes: all 40 FROZEN.json pins "
               "match disk (drift 0 at T0 and T1), check_class_schema.py PASS x3, run_acceptance.py exit 0, "
               "verify_frozen.py clean, check_taxonomy_consistency.py CONSISTENT, f0_binding matches the "
               "measured canonical F0 -> the current bytes are machine-green. BUT the four hashes the request "
               "names (F1/F2a/F2b/F0) are ALL superseded: the canonical files were rewritten again at "
               "00:19:14 and FROZEN.json regenerated, so a verdict bound to the requested pins cites bytes "
               "that are no longer on disk. Second blocking finding: all three schemas still bind (s,delta) "
               "over a disjunctive D0 ('Sobolev variant ... or the smooth-with-decay default'), so each is a "
               "family of two class statements - the G-FORM 'single frozen data class' unmet item is not "
               "discharged. Worker authority: evidence only, no gate verdict, no node completion.",
    "evidence_refs": EVIDENCE,
    "next_falsifier": NEXT_FALSIFIER,
    "does_not_claim": DNC,
})

events.append({
    "event_id": f"w037-{STAMP}-blocker-gform-request-pins-superseded",
    "event_type": "blocker",
    "created_at": NOW,
    "actor": "worker-037",
    "node_id": "F2",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "description": "G-FORM/G-F0 independent review is blocked by freeze churn: the hashes in "
                   f"{R['request_under_test']['event_id']} were already superseded at measurement "
                   "(requested F1 68392dd82050 vs disk 9a8bd4c96800; F2a 4f97273ef440 vs b6123750b37d; "
                   "F2b a2aef5ac7fe3 vs 1bb78ce9b357; F0 0fcc6a1928fd vs 276009f4f63d). Between 00:18:37 and "
                   "00:19:14 the canonical schemas were rewritten twice and FROZEN.json regenerated; at "
                   "00:19:38 the same checker measured 14/40 declared-vs-disk drifts and run_acceptance.py "
                   "PREFLIGHT FAIL, at 00:19:56 zero drift and all tools green. Separately, the "
                   "single-frozen-data-class criterion is still unmet at the measured bytes: D0 is a "
                   "disjunction in all three schemas (report finding W037-F5).",
    "needed_to_unblock": "Re-dispatch independent reviewers with the instruction to re-measure the artifact "
                         "hash at review time and bind only that measured hash (or declare a quiet freeze "
                         "window and confirm T0==T1 hash stability before issuing verdicts). Separately, "
                         "discharge the class-arity criterion: freeze one regularity setting (s,delta,norm) "
                         "and demote the other to a named variant class, then re-emit the artifact events.",
    "evidence_refs": EVIDENCE,
    "falsifier": NEXT_FALSIFIER,
    "does_not_claim": DNC,
})

events.append({
    "event_id": f"w037-{STAMP}-review-gform-freeze-verification",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-037",
    "reviewer": "worker-037",
    "target_id": "F1,F2a,F2b",
    "gate": "G-FORM",
    "class_ids": CLASSES,
    "verdict": "inconclusive",
    "score": 0.0,
    "artifact": REPORT,
    "artifact_sha256": REPORT_SHA,
    "hard_failures": [
        "W037-F1 (critical): every hash named by the lead's review request is superseded on disk at "
        "measurement time; no verdict can bind them.",
        "W037-F5 (major): disjunctive D0 regularity domain with an (s,delta) binder in all three class "
        "schemas; the single-frozen-data-class precondition is unmet.",
    ],
    "findings": "Current canonical bytes are machine-green (drift 0 at T0/T1, all six canonical tool runs "
                "exit 0, f0_binding fresh), but the freeze is not stable across a two-minute window and the "
                "review request pins stale hashes. This is verification evidence for G-FORM; it is not one of "
                "the two required independent accepts and it does not move any gate.",
    "evidence_refs": EVIDENCE,
    "falsifier": NEXT_FALSIFIER,
    "does_not_claim": DNC,
})

for ev in events:
    validate_event(ev)

OUTBOX = ROOT / "comms/outbox/worker-037.jsonl"
OUTBOX.parent.mkdir(parents=True, exist_ok=True)
existing = OUTBOX.read_text() if OUTBOX.exists() else ""
seen_ids = set()
for line in existing.splitlines():
    if line.strip():
        seen_ids.add(json.loads(line).get("event_id"))
new = [e for e in events if e["event_id"] not in seen_ids]
with OUTBOX.open("a") as f:
    for e in new:
        f.write(json.dumps(e, sort_keys=True) + "\n")

checkpoint = {
    "path": f"runtime/state/w037_checkpoint_{STAMP}.json",
    "worker": "worker-037",
    "checkpoint_at": NOW,
    "task_id": "W037-GFORM-FREEZE-01",
    "class_ids": CLASSES,
    "gate": "G-FORM",
    "verdict": "INCONCLUSIVE",
    "blocking_findings": ["W037-F1 requested pins superseded",
                          "W037-F5 disjunctive D0 / class-arity unmet"],
    "current_bytes_machine_green": R["machine_green_at_T1"],
    "measured_hashes_T0": {k: v["sha256"] for k, v in R["snapshot_T0"].items()},
    "artifacts": {REPORT: REPORT_SHA, SCRIPT: SCRIPT_SHA},
    "events_emitted": [e["event_id"] for e in events],
    "checkpoint_authority": "worker-level progress record only; not a gate verdict",
    "next_falsifier": NEXT_FALSIFIER,
}
cp_path = ROOT / checkpoint["path"]
cp_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

print(f"appended {len(new)} events to {OUTBOX.relative_to(ROOT)}")
print(f"checkpoint {checkpoint['path']} sha256={sha(checkpoint['path'])}")
print(json.dumps([e["event_id"] for e in new], indent=1))
