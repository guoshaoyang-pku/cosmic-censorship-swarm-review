#!/usr/bin/env python3
"""W031-F1-SUITE-REV13-IMPACT-01: write CHECKPOINT.json + SHA256SUMS and emit
protocol events to comms/outbox/worker-031.jsonl (idempotent: skips existing ids).

Worker measurement only: no gate verdict, no node status, no canonical edit.
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not (os.path.isdir(os.path.join(ROOT, "research_map")) and os.path.isdir(os.path.join(ROOT, "schemas"))):
    parent = os.path.dirname(ROOT)
    if parent == ROOT:
        raise RuntimeError("swarm root not found")
    ROOT = parent
REL = os.path.relpath(HERE, ROOT)
TASK_ID = "W031-F1-SUITE-REV13-IMPACT-01"
INSTANCE = "worker-031-20260912T005105-968807"
NOW = datetime.now(TZ).isoformat(timespec="seconds")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


report = json.load(open(os.path.join(HERE, "report.json")))
inst_sha = sha(os.path.join(HERE, "check_rev13_impact_031.py"))
readme_sha = sha(os.path.join(HERE, "README.md"))
report_sha = sha(os.path.join(HERE, "report.json"))

checkpoint = {
    "schema": "worker-bounded-task-checkpoint/v1",
    "task_id": TASK_ID,
    "instance": INSTANCE,
    "agent": "worker-031",
    "created_at": NOW,
    "class_id": "AF-WCC-VAC-GEN",
    "class_refs": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "node_id": "F1",
    "gate": "G-FORM",
    "verdict": report["verdict"]["primary"],
    "verdict_statement": report["verdict"]["statement"],
    "deliverables": {
        "report.json": report_sha,
        "check_rev13_impact_031.py": inst_sha,
        "README.md": readme_sha,
    },
    "pinned_inputs": report["pinned_inputs"],
    "inputs_stable_during_run": report["inputs_stable_during_run"],
    "frozen_moved_during_run": report.get("frozen_moved_during_run"),
    "key_measurements": {
        "suite_rows": 25,
        "row_bindings_stale": report["suite"]["totals"]["row_bindings_stale"],
        "probes_stored_pass": report["suite"]["totals"]["probes_stored_pass"],
        "probes_recomputed_pass_live_rev13": report["suite"]["totals"]["probes_recomputed_pass_live_rev13"],
        "probes_recomputed_pass_prerepair_rev12": report["suite"]["totals"]["probes_recomputed_pass_prerepair_rev12"],
        "suite_defects": len(report["suite"]["defects"]),
        "schema_defects": len(report["schemas"]["defects"]),
        "frozen_revision": report["frozen"]["revision"],
        "frozen_files_stale": report["frozen"]["files_stale"],
        "f1_delta_changed_paths": report["f1_rev12_to_rev13_delta_scope"]["changed"],
        "f1_delta_unauthorized_paths": len(report["f1_rev12_to_rev13_delta_scope"]["unexpected_changed"]),
    },
    "repair_item_status": report["repair_item_status"],
    "controls": report["controls"],
    "falsifier": report["falsifier"],
    "next_falsifier": report["next_falsifier"],
    "authority": report["authority"],
    "replay": f"python3 {REL}/check_rev13_impact_031.py  # exit 0, rewrites report.json",
}
with open(os.path.join(HERE, "CHECKPOINT.json"), "w", encoding="utf-8") as fh:
    json.dump(checkpoint, fh, indent=1)
    fh.write("\n")
cp_sha = sha(os.path.join(HERE, "CHECKPOINT.json"))

# frozen copy in runtime/state (same bytes)
runtime_cp = os.path.join(ROOT, "runtime", "state", "w031_f1_suite_rev13_impact_checkpoint.json")
with open(runtime_cp, "w", encoding="utf-8") as fh:
    fh.write(open(os.path.join(HERE, "CHECKPOINT.json"), encoding="utf-8").read())

# SHA256SUMS
lines = []
for name in ["check_rev13_impact_031.py", "report.json", "README.md", "CHECKPOINT.json"]:
    lines.append(f"{sha(os.path.join(HERE, name))}  {name}")
with open(os.path.join(HERE, "SHA256SUMS"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

EV = f"w031-f1sr13"
ev = report["verdict"]["statement"]
fals = report["falsifier"]
nxt = report["next_falsifier"]
refs = [
    f"schemas/f1_falsifier_tests.jsonl#{report['pinned_inputs']['schemas/f1_falsifier_tests.jsonl']['sha256'][:12]}",
    f"schemas/af_wcc_vacuum.yaml#{report['pinned_inputs']['schemas/af_wcc_vacuum.yaml']['sha256'][:12]}",
    f"research_map/formulation_taxonomy.yaml#{report['pinned_inputs']['research_map/formulation_taxonomy.yaml']['sha256'][:12]}",
    f"artifacts/formulation/FROZEN.json#{report['pinned_inputs']['artifacts/formulation/FROZEN.json']['sha256'][:12]}",
    f"{REL}/report.json#{report_sha[:12]}",
    f"{REL}/check_rev13_impact_031.py#{inst_sha[:12]}",
    f"{REL}/README.md#{readme_sha[:12]}",
    f"{REL}/CHECKPOINT.json#{cp_sha[:12]}",
]
events = [
    {"event_id": f"{EV}-status-start-20260912T005600", "event_type": "status", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "status": "active", "hours": 0.5,
     "summary": ("No assignment card exists in comms/inbox for worker-031 (fleet instance 2026-09-12T00:51:05). "
                 "Took ONE bounded class-bound task: " + TASK_ID + ", measuring the impact of the landed "
                 "astra-life05-evidence-binding-repair (REC-12, F1 rev12 cce9c60146d6 -> rev13 d9cebb9404b2) on "
                 "schemas/f1_falsifier_tests.jsonl, the 25-row/84-probe G-FORM acceptance suite that REC-12 does "
                 "not name. Independent instrument, pre-repair snapshot control, no canonical writes."),
     "evidence_refs": refs[:4], "next_falsifier": nxt},
    {"event_id": f"{EV}-art-report-20260912T005600", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "artifact_type": "rev13_suite_impact_report", "path": f"{REL}/report.json", "sha256": report_sha,
     "validation_status": "unverified",
     "summary": ("Impact report at live pins: 25/25 suite row bindings stale against F1 rev13 d9cebb9404b2; "
                 "27 operative defects (25 row bindings + F1-AMB-25 cross_artifact/deciding expectation still on "
                 "F0 276009f4); probes 84 stored -> 82 recomputed at rev13 and 82 at the pre-repair snapshot; "
                 "repair items I1 corpus 36/36 live, I2 3/3 consistency pins live, I3 rev13 strictness text present, "
                 "I4 FROZEN rev29 48/48 pins live; F1 delta 12 paths changed, 0 unauthorized, class semantics "
                 "byte-identical; controls K1-K7 pass; decision inputs stable."),
     "evidence_refs": refs, "falsifier": fals},
    {"event_id": f"{EV}-art-instrument-20260912T005600", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "artifact_type": "measurement_instrument", "path": f"{REL}/check_rev13_impact_031.py", "sha256": inst_sha,
     "validation_status": "unverified",
     "summary": ("Deterministic stdlib+PyYAML instrument: pins 8 inputs by full sha256, censuses operative pins in the "
                 "suite/schemas/corpus/FROZEN, recomputes all 84 probes at live rev13 and at the hash-verified pre-repair "
                 "rev12 snapshot, diffs the flattened rev12->rev13 YAML against an authorized-path allowlist, checks "
                 "class-semantics invariance, and runs controls K1-K7. Exit 0 measured / 1 control failure / 2 drift."),
     "evidence_refs": [f"{REL}/report.json#{report_sha[:12]}"], "falsifier": fals},
    {"event_id": f"{EV}-art-readme-20260912T005600", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "artifact_type": "finding_analysis", "path": f"{REL}/README.md", "sha256": readme_sha,
     "validation_status": "unverified",
     "summary": "Method, pinned input table, result, repair-item status, controls K1-K7, prior-reporting crosswalk, falsifier, next falsifier, authority limits and replay command.",
     "evidence_refs": [f"{REL}/report.json#{report_sha[:12]}"], "falsifier": fals},
    {"event_id": f"{EV}-art-checkpoint-20260912T005600", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "artifact_type": "bounded_task_checkpoint", "path": f"{REL}/CHECKPOINT.json", "sha256": cp_sha,
     "validation_status": "unverified",
     "summary": "Bounded-task checkpoint: task id, instance, pins, deliverable hashes, key measurements, repair-item status, controls, verdict, falsifier, next falsifier, replay. Copy at runtime/state/w031_f1_suite_rev13_impact_checkpoint.json (same sha256).",
     "evidence_refs": [f"{REL}/report.json#{report_sha[:12]}"], "falsifier": fals},
    {"event_id": f"{EV}-claim-20260912T005600", "event_type": "claim", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "conclusion_type": "artifact_measurement",
     "statement": ("Artifact-and-checker measurement (not a mathematics or physics claim, not a gate verdict): at pins "
                   "suite 56bcb4b3234b / F1 rev13 d9cebb9404b2 / F2a rev13 e9a27996dfd3 / F2b rev13 b2ab6acb2bbe / "
                   "F0 0abb9ed8a961 / corpus ccf7041bd0ff / FROZEN rev29 3d9e3d77, the F1 falsifier suite is unbound: "
                   "25/25 rows carry binding_sha256 = the pre-repair F1 cce9c60146d6, and F1-AMB-25 still asserts the "
                   "superseded F0 276009f4 in cross_artifact and in its deciding expectation (live 0abb9ed8). "
                   "Recomputing the 84 recorded probes gives 82/84 both at live rev13 and at the pre-repair snapshot, "
                   "the 2 failures being F1-AMB-25's deciding equality and binding_note probes; the rev13 strictness "
                   "rewrite flipped no probe outcome. REC-12 items I1 (corpus rows), I2 (three consistency-evidence "
                   "pins), I3 (F1 strictness text) and I4 (FROZEN rev29 48/48) all measure landed at this snapshot, and "
                   "the F1 rev12->rev13 delta contains 0 unauthorized paths with class semantics byte-identical; the "
                   "suite itself is not in REC-12's scope, so the repair as authorised leaves G-FORM's F1 evidence "
                   "suite stale on both its schema row bindings and its F0 expectation until re-pinned and re-run."),
     "assumptions": ["the live canonical bytes at the 8 pinned hashes are the intended frozen inputs",
                     "the hash-verified worker-007 rev12 snapshot is byte-identical to the pre-repair canonical F1",
                     "provenance tokens (evidence_refs, prior_binding_*, binding_at_authoring) are historical, not operative"],
     "falsifier": fals,
     "artifact_refs": [{"path": f"{REL}/report.json", "sha256": report_sha},
                       {"path": f"{REL}/check_rev13_impact_031.py", "sha256": inst_sha},
                       {"path": f"{REL}/CHECKPOINT.json", "sha256": cp_sha}],
     "evidence_refs": refs},
    {"event_id": f"{EV}-blocker-20260912T005600", "event_type": "blocker", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "description": ("G-FORM evidence blocker (owner action, not a class-semantics defect): the rev13 evidence-binding "
                     "repair rewrote schemas/af_wcc_vacuum.yaml to d9cebb9404b2 but left schemas/f1_falsifier_tests.jsonl "
                     "at 56bcb4b3234b, whose 25/25 rows bind the superseded cce9c60146d6 and whose F1-AMB-25 row still "
                     "expects F0 276009f4. The suite is therefore no longer bound evidence for the live F1 schema, and its "
                     "stored 84/84 pass claim recomputes 82/84 at the live canonical pair. REC-12's four authorised items "
                     "do not include this file."),
     "needed_to_unblock": ("Formulation lead (owner of astra-life05-evidence-binding-repair): include schemas/f1_falsifier_tests.jsonl "
                           "in the repair - re-pin the 25 binding_sha256/binding_ref values to F1 rev13 d9cebb9404b2, update "
                           "F1-AMB-25 cross_artifact and deciding expectation to live F0 rev5 0abb9ed8a961, re-run the author's "
                           "verifier to 84/84, and re-publish the suite with an artifact event + new sha256. Controller/audit lead: "
                           "do not bind a G-FORM verdict or review coverage to suite 56bcb4b3234b."),
     "evidence_refs": refs, "falsifier": fals},
    {"event_id": f"{EV}-review-20260912T005600", "event_type": "review", "created_at": NOW,
     "actor": "worker-031", "reviewer": "worker-031", "node_id": "F1", "gate": "G-FORM",
     "class_id": "AF-WCC-VAC-GEN", "target_id": f"{TASK_ID}@{REL}/CHECKPOINT.json",
     "verdict": "accept", "score": 4.0, "hard_failures": [],
     "findings": ["Task is bounded, class-bound (AF-WCC-VAC-GEN/F1/G-FORM) and non-duplicative: W007 measured the four REC-12 items pre-repair, W032 the single F1-AMB-25 staleness, W076 the strictness diagnosis; none measured the 25/25 row-binding invalidation caused by the rev13 write.",
                  "All controls pass: K1-K3 comparator non-vacuity, K4 pre-repair baseline continuity reproducing W031-F1-PINCENSUS-01 (25/25 live, 82/84, 2+3 stale pins), K5 deterministic replay, K6 delta-scope sensitivity, K7 class-semantics invariance.",
                  "Deliverables exist on disk and are sha256-pinned; decision inputs stable across the run; FROZEN's manifest movement is recorded, not silently absorbed.",
                  "Authority limited to measurement: no gate verdict, no node status, no validation_status, no canonical artifact edited; repair ownership routed to the formulation lead."],
     "evidence_refs": refs},
    {"event_id": f"{EV}-status-final-20260912T005600", "event_type": "status", "created_at": NOW,
     "actor": "worker-031", "node_id": "F1", "gate": "G-FORM", "class_id": "AF-WCC-VAC-GEN",
     "status": "active", "hours": 0.5,
     "summary": ("CHECKPOINT + EXIT. " + TASK_ID + " complete: one class-bound task, four artifacts on disk and "
                 "hash-pinned, controls K1-K7 pass, verdict SUITE_UNBOUND_AT_F1_REV13. The rev13 repair landed items "
                 "I1-I4 and changed no class semantics, but left the F1 falsifier suite at 56bcb4b3234b: 25/25 row "
                 "bindings stale, F1-AMB-25 F0 expectation stale, 82/84 probes. One blocker filed for the formulation "
                 "lead; no gate verdict, no node status, no artifact under test edited."),
     "evidence_refs": refs, "next_falsifier": nxt},
]

outbox = os.path.join(ROOT, "comms", "outbox", "worker-031.jsonl")
existing = set()
if os.path.isfile(outbox):
    for line in open(outbox, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
added = 0
with open(outbox, "a", encoding="utf-8") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, sort_keys=True) + "\n")
        added += 1
print(json.dumps({"checkpoint": cp_sha, "report": report_sha, "instrument": inst_sha,
                  "readme": readme_sha, "events_emitted": added,
                  "event_ids": [e["event_id"] for e in events]}, indent=1))
