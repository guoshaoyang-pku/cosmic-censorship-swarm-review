#!/usr/bin/env python3
"""Emit worker-024's W024-CLASSSEP-RUNNER-VACUITY-01 events and checkpoint.

Idempotent: an event_id already present in comms/outbox/worker-024.jsonl is skipped, and the
checkpoint is not appended twice. Validates every event with research_map.schemas.validate_event
before writing. Worker authority: artifacts are emitted as validation_status=unverified; no gate
verdict, no status=done, no validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

ART = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-024.jsonl"
STATE = ROOT / "runtime/state"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TASK = "W024-CLASSSEP-RUNNER-VACUITY-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_JOINED = ";".join(CLASS_IDS)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: str) -> str:
    return f"{p}#{sha256(ROOT / p)[:12]}"


report = json.loads((ART / "report.json").read_text())
pins = report["pins"]
res = report["result"]
readme = "artifacts/worker-024/classsep_runner_vacuity/README.md"
patch = "artifacts/worker-024/classsep_runner_vacuity/proposed_patch.diff"
driver = "artifacts/worker-024/classsep_runner_vacuity/drive_vacuity.py"
rep = "artifacts/worker-024/classsep_runner_vacuity/report.json"
entry = "artifacts/worker-024/classsep_runner_vacuity/entry_hashes.json"
exith = "artifacts/worker-024/classsep_runner_vacuity/exit_hashes.json"

assert sha256(ART / "report.json") == sha256(ROOT / rep)
for p in (readme, patch, driver, entry, exith):
    assert (ROOT / p).is_file(), p

events = [
    {
        "event_id": "w024-vac-20260912T0029-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "artifact_type": "runner_vacuity_audit_report",
        "path": rep,
        "sha256": sha256(ROOT / rep),
        "validation_status": "unverified",
        "summary": (
            "Independent fail-open audit of runtime/bin/classsep_regression.py at sha256 "
            "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091: empty, unreachable "
            "and leak-truncated corpora all return VERDICT: PASS / exit 0; positive control "
            "reproduces 17/17 leaks + 10/10 controls at corpus sha256 d69ad584..."
        ),
    },
    {
        "event_id": "w024-vac-20260912T0029-artifact-patch",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "artifact_type": "proposed_fail_closed_patch",
        "path": patch,
        "sha256": sha256(ROOT / patch),
        "validation_status": "unverified",
        "summary": (
            "Minimal fail-closed patch for both entry points: assert declared corpus totals "
            "(27/17/10), fail on any missing fixture path, print REASON lines. Verified on copies: "
            "T0 still PASS, T1-T5 all exit 1 with an explicit reason."
        ),
    },
    {
        "event_id": "w024-vac-20260912T0029-artifact-driver",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "artifact_type": "reproducible_audit_driver",
        "path": driver,
        "sha256": sha256(ROOT / driver),
        "validation_status": "unverified",
        "summary": "Builds six corpus-integrity sandboxes, runs the pinned runner and the module-level regression in each, then re-runs all six against the patched copies; deterministic, exit 0 on the recorded assertions.",
    },
    {
        "event_id": "w024-vac-20260912T0029-artifact-readme",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "artifact_type": "audit_readme",
        "path": readme,
        "sha256": sha256(ROOT / readme),
        "validation_status": "unverified",
        "summary": "Method, per-case results table, mechanism, patch, reproduction command, falsifier and residual risk for the runner-vacuity audit.",
    },
    {
        "event_id": "w024-vac-20260912T0029-claim-runner-fail-open",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": (
            "Instrument claim (not a class-semantics claim): at runtime/bin/classsep_regression.py "
            "sha256 9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091, the standing "
            "class-separation regression used as CF-3 gate evidence fails open on an incomplete "
            "corpus. The runner decides PASS iff fn==0 and fp==0 over readable fixtures; it never "
            "compares scored counts with results.json.summary (fixtures_total=27, leaks_total=17, "
            "controls_total=10), never fails on a missing fixture path, and never pins the truth "
            "file. Three byte-identical sandbox cases certify PASS with exit 0: (T1) fixtures list "
            "emptied, 0/0 and 0/0; (T2) all 27 paths unreachable, 27 MISSING rows and 0/0 and 0/0; "
            "(T3) the 17 leak fixtures removed, 10/10 controls, 0/0 leaks. The module-level "
            "class_separation.regression() at sha256 c266dbceca87 shows the same shape "
            "(missing fixtures skipped with `continue`; T1/T2 return PASS with corpus_size 0). The "
            "positive control T0 reproduces the standing evidence exactly (17/17 leaks, 10/10 "
            "controls, exit 0), and the attached patch closes T1-T5 while leaving T0 at PASS. "
            "Consequence for G-AUDIT: a PASS from this runner certifies the detector only for the "
            "corpus actually read; it cannot distinguish 'detector clean' from 'corpus empty or "
            "truncated'. No gate verdict is asserted."
        ),
        "assumptions": [
            "The sandbox copies of the runner and detector are byte-identical to the canonical files at the pinned hashes (asserted after copy).",
            "The corpus ground truth is worker-07's results.json at sha256 d69ad584; this audit does not re-adjudicate its semantic labels.",
            "T4/T5 are incidental detections (FP/FN side effects), not fail-open cases, and are excluded from the claim.",
            "Applying the patch to canonical paths is an owner decision; the patched verdicts here are from copies under this artifact directory.",
        ],
        "falsifier": (
            "Re-run artifacts/worker-024/classsep_runner_vacuity/drive_vacuity.py at the pinned "
            "runner sha256 9f1cf9c3. FALSIFIED if T1_empty_list, T2_missing_paths or T3_leaks_dropped "
            "returns exit != 0 or prints VERDICT: DEFECTIVE under the unpatched runner; or if T0_real "
            "does not reproduce 17/17 leaks + 10/10 controls; or if any patched sandbox passes an "
            "incomplete corpus. Any later edit of the runner/detector/corpus voids the claim for the "
            "edited bytes."
        ),
        "evidence_refs": [
            ref(rep), ref(readme), ref(patch), ref(driver), ref(entry), ref(exith),
            "runtime/bin/classsep_regression.py#9f1cf9c336be",
            "research_map/class_separation.py#c266dbceca87",
            "artifacts/worker-07/class_separation_falsification/results.json#d69ad58468be",
        ],
        "artifact_refs": [rep, patch, driver, readme],
    },
    {
        "event_id": "w024-vac-20260912T0029-status-runner-vacuity",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "status": "active",
        "hours": 0.4,
        "summary": (
            "W024-CLASSSEP-RUNNER-VACUITY-01 complete: artifacts on disk and hash-pinned. Result: "
            "the CF-3 standing class-separation regression returns PASS/exit 0 on empty, "
            "unreachable and leak-truncated corpora (3/3 vacuous cases) while the real corpus "
            "reproduces 17/17 + 10/10; proposed fail-closed patch verified on copies. Worker "
            "completion claim only: no gate verdict, no node transition."
        ),
        "evidence_refs": [ref(rep), ref(patch), ref(driver)],
        "next_falsifier": (
            "Owner applies proposed_patch.diff at the canonical path and adds an emptied-corpus "
            "case to the standing A1 evidence. Defect closed only if every incomplete corpus exits "
            "1 with a printed REASON while T0_real still exits 0 at 17/17 and 10/10. If the runner "
            "is rebuilt, re-run drive_vacuity.py at the new hash and expect the six cases to be "
            "non-vacuous."
        ),
        "authority_note": "worker event: no gate verdict, no validation_status=passed, no node status=done",
    },
]

validated = [validate_event(e) for e in events]

OUTBOX.parent.mkdir(parents=True, exist_ok=True)
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
new = [e for e in validated if e["event_id"] not in existing]
if new:
    with OUTBOX.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")

# Re-verify every emitted hash against disk.
for e in validated:
    if e["event_type"] == "artifact":
        assert sha256(ROOT / e["path"]) == e["sha256"], e["path"]
for r in validated[4]["evidence_refs"]:
    p, _, prefix = r.partition("#")
    assert sha256(ROOT / p).startswith(prefix), r

checkpoint = {
    "actor": "worker-024",
    "checkpoint": 2,
    "checkpoint_id": "w24-cp02-classsep-runner-vacuity",
    "task_id": TASK,
    "node_id": "A1",
    "gate": "G-AUDIT",
    "class_ids": CLASS_IDS,
    "created_at": NOW,
    "verdict": res["verdict"],
    "positive_control_ok": res["positive_control_ok"],
    "vacuous_pass_cases": res["vacuous_pass_cases"],
    "incidentally_detected_cases": res["incidentally_detected_cases"],
    "patched_closes_cases": res["patched_closes_cases"],
    "pins": pins,
    "artifacts": {p: sha256(ROOT / p) for p in (rep, readme, patch, driver, entry, exith)},
    "events_emitted": [e["event_id"] for e in validated],
    "outbox": str(OUTBOX.relative_to(ROOT)),
    "next_falsifier": validated[5]["next_falsifier"],
    "authority_note": "worker progress record only; not a gate verdict or node completion",
    "no_canonical_input_changed": json.loads((ART / "exit_hashes.json").read_text())["no_canonical_input_changed_during_run"],
}

cp_path = STATE / "w24_checkpoint_02.json"
cp_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))
ledger = STATE / "w24_checkpoints.jsonl"
seen = ledger.read_text() if ledger.exists() else ""
if checkpoint["checkpoint_id"] not in seen:
    with ledger.open("a") as f:
        f.write(json.dumps({
            "actor": "worker-024", "at": NOW, "checkpoint_id": checkpoint["checkpoint_id"],
            "path": "runtime/state/w24_checkpoint_02.json", "sha256": sha256(cp_path),
            "task_id": TASK, "node_id": "A1", "verdict": res["verdict"],
        }, sort_keys=True) + "\n")

print(json.dumps({
    "appended_events": [e["event_id"] for e in new],
    "skipped_existing": sorted(existing & {e["event_id"] for e in validated}),
    "checkpoint": "runtime/state/w24_checkpoint_02.json",
    "checkpoint_sha256": sha256(cp_path),
    "validated": len(validated),
    "hashes_reverified": True,
}, indent=1))
