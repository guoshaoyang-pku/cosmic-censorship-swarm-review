#!/usr/bin/env python3
"""Emit W098-CLASSSEP-PROSE-SHADOW-01 events to comms/outbox/worker-098.jsonl.

Self-check before writing: every string in every event is scanned with the canonical
class_separation detector (prose mode + claim surface), so this worker's own traffic
cannot add to the CLASSSEP hard count it is measuring.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

OUT = ROOT / "comms/outbox/worker-098.jsonl"
TS = "2026-09-12T00:52:00+08:00"
BASE = "w098-cps-20260912T0051"
ART = "artifacts/worker-098/classsep_prose_shadow"
CKPT = "runtime/state/w098_classsep_prose_shadow_checkpoint_1.json"
CLAIM_STATEMENT = (
    "At the pinned snapshot (canonical detector research_map/class_separation.py#c266dbceca87, "
    "proposal artifacts/formulation/proposals/classsep_prose_precision_patch.md#edeb6588a17b, map "
    "snapshot 6d3f0f2792a2), the proposal's prose-precision patch, implemented in a shadow by "
    "insertions only and tested on 27 corpus fixtures + 12 probes + the frozen map, clears 13 of "
    "17 live hard findings and all 3 synthetic detector-discussion growth probes, but fails 2 of "
    "its own 7 acceptance criteria: one declared false-positive probe still fires and the live hard "
    "count lands at 4, not 0; additionally 6 of 6 adversarial genuine-merge probes are "
    "over-suppressed, a false-negative class the 27-fixture corpus does not cover."
)
FALSIFIER = (
    "Re-run artifacts/worker-098/classsep_prose_shadow/run_shadow_test.py at the pinned hashes: "
    "falsified if the shadow clears the declared 'no composite, then merge' probe and all residual "
    "live claims while the 6 genuine-merge probes still fire and declaration parity holds; or if "
    "research_map/class_separation.py moves off c266dbceca87 or the patch proposal moves off "
    "edeb6588a17b."
)
REFS = [
    "artifacts/worker-098/classsep_prose_shadow/report.json#c27f2a0399d2",
    "artifacts/worker-098/classsep_prose_shadow/raw/probes.json#9a66867609ce",
    "artifacts/worker-098/classsep_prose_shadow/raw/map_battery.json#9ac2b266b107",
    "artifacts/worker-098/classsep_prose_shadow/raw/growth.json#0b46d77cf87c",
    "artifacts/worker-098/classsep_prose_shadow/snapshot/research_map.pinned.json#6d3f0f2792a2",
    "artifacts/formulation/proposals/classsep_prose_precision_patch.md#edeb6588a17b",
    "research_map/class_separation.py#c266dbceca87",
    "runtime/state/w098_classsep_prose_shadow_checkpoint_1.json",
]
CIDS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"

events = [
    {
        "event_id": f"{BASE}-status-take", "event_type": "status", "created_at": TS, "actor": "worker-098",
        "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "status": "active", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
        "hours": 0.1,
        "summary": ("No assignment card exists in comms/inbox for worker-098. Taking ONE bounded class-bound task from the live "
                    "G-AUDIT blocker: W098-CLASSSEP-PROSE-SHADOW-01 = independent read-only shadow implementation and acceptance "
                    "test of the formulation lead's classsep prose-precision proposal, plus adversarial over-suppression controls "
                    "and a growth replication. No canonical write, no gate verdict, no node completion."),
        "evidence_refs": [f"{ART}/pre_registration.json#fbe95b585fca", "research_map/class_separation.py#c266dbceca87"],
        "next_falsifier": FALSIFIER,
    },
    {"event_id": f"{BASE}-art-prereg", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "pre_registration", "path": f"{ART}/pre_registration.json",
     "sha256": "fbe95b585fcad5e0e020d56b82de466b17bc54426959ec0b98f44e3e5fe2021e",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Pins + 8 pre-registered expectations E1-E8, written before the run.",
     "evidence_refs": [f"{ART}/snapshot/MANIFEST.json#bf1cb620f11b"]},
    {"event_id": f"{BASE}-art-instrument", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "shadow_test_instrument", "path": f"{ART}/run_shadow_test.py",
     "sha256": "23f2411f15d2b57ab46241b99d92bc40f1b585792c63138f1483bffeeed902a0",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Deterministic no-network pin-check + shadow generation (insertions only) + 5-battery runner.",
     "evidence_refs": [f"{ART}/raw/shadow_provenance.json#458a3b70ee24"]},
    {"event_id": f"{BASE}-art-shadow", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "shadow_module", "path": f"{ART}/shadow_class_separation.py",
     "sha256": "65c4fef0a89bdba1d360c40de5ff6fce4799eda15bdc0945081fcabffe07da6c",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Test double: canonical bytes + the proposal's insertions only (24 added lines, 0 removed, 3 hunks).",
     "evidence_refs": [f"{ART}/raw/shadow_provenance.json#458a3b70ee24"]},
    {"event_id": f"{BASE}-art-manifest", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "snapshot_manifest", "path": f"{ART}/snapshot/MANIFEST.json",
     "sha256": "bf1cb620f11bafa98feee647e629110ecf5d8d192e0385c6567fd8c7878337f4",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Pins of the map snapshot 6d3f0f2792a2, canonical detector, pre-registration and shadow.",
     "evidence_refs": [f"{ART}/snapshot/research_map.pinned.json#6d3f0f2792a2"]},
    {"event_id": f"{BASE}-art-report", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "artifact_type": "verification_report",
     "path": f"{ART}/report.json", "sha256": "c27f2a0399d2efc220158d78fa0cf1bb1cc896ca117a9eb7be182a38bdcec8f0",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Acceptance 5/7; verdict revise 3.0; findings W098-CPS-01..06.",
     "evidence_refs": [f"{ART}/raw/acceptance.json#e493891f8f76", f"{ART}/raw/map_battery.json#9ac2b266b107"]},
    {"event_id": f"{BASE}-art-raw-probes", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "raw_probe_verdicts", "path": f"{ART}/raw/probes.json",
     "sha256": "9a66867609ced74d86e57324d2aeef47c3306f959a8dcf9c21d4de992a95db3d",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Per-probe canonical/shadow verdicts: 4 declared FP, 2 declared TP, 6 adversarial FN, 10 declaration-parity.",
     "evidence_refs": [f"{ART}/report.json#c27f2a0399d2"]},
    {"event_id": f"{BASE}-art-raw-map", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "raw_map_verdicts", "path": f"{ART}/raw/map_battery.json",
     "sha256": "9ac2b266b1075461ae31f76881e0fd792b6e817c65e118f7d1187c192017a25e",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Frozen-snapshot hard count 17 canonical / 4 shadow; per-claim findings and residual indices.",
     "evidence_refs": [f"{ART}/snapshot/research_map.pinned.json#6d3f0f2792a2"]},
    {"event_id": f"{BASE}-art-raw-growth", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "raw_growth_verdicts", "path": f"{ART}/raw/growth.json",
     "sha256": "0b46d77cf87c79005afb72fd64fb9af0c882821063656f7b7edae9aa5d69fdb6",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "Detector-discussion growth probes: canonical +3 findings, shadow 0.",
     "evidence_refs": [f"{ART}/report.json#c27f2a0399d2"]},
    {"event_id": f"{BASE}-art-readme", "event_type": "artifact", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "class_id": CIDS, "artifact_type": "readme", "path": f"{ART}/README.md",
     "sha256": "207c4814ec4f0b30422934af0ba7489d255d6e6e14f1ac918583ae083887c636",
     "validation_status": "unverified", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": "One-page rendering: method, results table, findings, falsifier, non-claims, file hashes, rerun command.",
     "evidence_refs": [f"{ART}/report.json#c27f2a0399d2"]},
    {"event_id": f"{BASE}-claim", "event_type": "claim", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "conclusion_type": "instrument_finding",
     "task_id": "W098-CLASSSEP-PROSE-SHADOW-01", "statement": CLAIM_STATEMENT,
     "assumptions": [
         "the measured sha256 is the artifact identity; this claim binds only to the pinned bytes",
         "the map snapshot 6d3f0f2792a2, not the live map, is the measurement surface; live drift is reported separately",
         "the shadow module is generated from canonical bytes by insertions only and verified by diff",
         "the canonical gate/regression corpus is cited as reproduced stage evidence, not as the basis of the verdict"],
     "falsifier": FALSIFIER,
     "artifact_refs": [f"{ART}/report.json#c27f2a0399d2", f"{CKPT}"],
     "evidence_refs": REFS},
    {"event_id": f"{BASE}-review", "event_type": "review", "created_at": TS, "actor": "worker-098",
     "reviewer": "worker-098", "target_id": "artifacts/formulation/proposals/classsep_prose_precision_patch.md",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "verdict": "revise", "score": 3.0,
     "reviewed_sha256": "edeb6588a17b31cf2c7fe68b28fbb28ab2b8667cad01d1e5b270ecc91eae9e96",
     "counts_as_full_schema_verdict": False, "counts_as_independent": True,
     "hard_failures": [
         "W098-CPS-01: the proposal's own false-positive probe 'no <composite> merge exists' still fires under the patch; acceptance #3 unmet",
         "W098-CPS-02: live hard count 17 -> 4, not 0; residual claims 144/152/187/192 at the snapshot; acceptance #4 unmet",
         "W098-CPS-03: 6/6 pre-registered genuine merge assertions are over-suppressed by the sentence-wide _META skip; the 27-fixture corpus does not cover this"],
     "findings": [
         "W098-CPS-04 (info): direction confirmed - growth probes 3 -> 0, 13/17 live findings cleared, declaration parity 10/10, shadow diff insertions only",
         "W098-CPS-05 (info): corpus under-specifies the FN side; add the 6 adversarial probes to the regression corpus",
         "W098-CPS-06 (info): all 17 canonical hard findings are claim findings in the frozen map JSON; artifact churn does not affect the count",
         "live growth reproduced during the task: live hard count 17 (snapshot) -> 20 (live f06d40a8226a) driven by w093-metagrowth-20260912T0049-claim, a claim about the detector"],
     "artifact_refs": [f"{ART}/report.json#c27f2a0399d2"],
     "evidence_refs": REFS},
    {"event_id": f"{BASE}-blocker", "event_type": "blocker", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "description": ("The proposed classsep prose-precision patch is not yet sufficient to clear G-AUDIT's CLASSSEP hard count: "
                     "acceptance 5/7 (W098-CPS-01 and -02 fail) and 6 measured over-suppression false negatives (W098-CPS-03). "
                     "The live count also grew 17 -> 20 during the task window via one meta-claim, reproducing the instrument-growth mechanism."),
     "needed_to_unblock": ("Owner + controller: (i) narrow the prose skip so a positive merge assertion is never dropped by _META "
                           "alone and add the 6 adversarial probes to the regression corpus; (ii) fix the negation span so "
                           "'no <composite> merge' is recognised; (iii) re-run this instrument at the repaired hashes and require "
                           "4/4 declared FP probes clean, all residual claims cleared, and 6/6 genuine-merge probes still firing."),
     "evidence_refs": REFS},
    {"event_id": f"{BASE}-checkpoint", "event_type": "status", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "status": "active", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "summary": ("Worker-local checkpoint written (controller runtime checkpoint untouched): 12 artifacts pinned, "
                 "all 6 findings carry executable falsifiers, liveness recheck at emit recorded (detector unchanged; live map "
                 "f06d40a8226a at 20 hard findings)."),
     "artifact_refs": [CKPT], "evidence_refs": [f"{CKPT}", f"{ART}/report.json#c27f2a0399d2"]},
    {"event_id": f"{BASE}-complete", "event_type": "status", "created_at": TS, "actor": "worker-098",
     "node_id": "A1", "gate": "G-AUDIT", "class_id": CIDS, "status": "active", "task_id": "W098-CLASSSEP-PROSE-SHADOW-01",
     "completion_claim": True, "hours": 0.3,
     "summary": ("W098-CLASSSEP-PROSE-SHADOW-01 complete as a bounded task: read-only shadow implementation + acceptance test of "
                 "classsep_prose_precision_patch.md at pins detector c266dbceca87 / proposal edeb6588a17b / map snapshot 6d3f0f2792a2. "
                 "Verdict revise 3.0, acceptance 5/7, findings W098-CPS-01..06, 12 artifacts hash-pinned, worker checkpoint written. "
                 "This is a completion claim for the bounded task only, not node completion, not a gate verdict; lead/controller must "
                 "ingest and decide."),
     "artifact_refs": [f"{ART}/report.json#c27f2a0399d2", CKPT],
     "evidence_refs": REFS, "next_falsifier": FALSIFIER},
]

# ---- self-check: none of this worker's own text may add a CLASSSEP hard finding
problems = []
for ev in events:
    for k, v in ev.items():
        if isinstance(v, str):
            out: list = []
            cs._scan_composite(v, f"{ev['event_id']}.{k}", out, mode="prose")
            problems += [p for p in out if not p.startswith("CLASSSEP-SOFT:")]
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str):
                    out = []
                    cs._scan_composite(x, f"{ev['event_id']}.{k}[{i}]", out, mode="prose")
                    problems += [p for p in out if not p.startswith("CLASSSEP-SOFT:")]
    if ev["event_type"] == "claim":
        problems += [p for p in cs.findings(ev, ev["event_id"], mode="prose")
                     if not p.startswith("CLASSSEP-SOFT:")]

required = {
    "claim": ["event_id", "event_type", "created_at", "actor", "class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
    "artifact": ["event_id", "event_type", "created_at", "actor", "node_id", "artifact_type", "path", "sha256", "validation_status"],
    "review": ["event_id", "event_type", "created_at", "actor", "target_id", "reviewer", "verdict", "score", "hard_failures", "findings"],
}
missing = []
for ev in events:
    for k in required.get(ev["event_type"], ["event_id", "event_type", "created_at", "actor"]):
        if k not in ev:
            missing.append(f"{ev['event_id']}: {k}")
if problems:
    print("SELF-CHECK FAILED — canonical detector would flag this worker's own text:")
    for p in problems:
        print("  ", p[:200])
    sys.exit(2)
if missing:
    print("MISSING REQUIRED FIELDS:", missing)
    sys.exit(2)

with OUT.open("a") as fh:
    for ev in events:
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
print(f"appended {len(events)} events to {OUT}")
print("event_ids:", [e["event_id"] for e in events])
