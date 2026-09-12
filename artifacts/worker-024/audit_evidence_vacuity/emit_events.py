#!/usr/bin/env python3
"""Emit worker-024's W024-AUDIT-EVIDENCE-VACUITY-01 events and checkpoint.

Idempotent: event_ids already present in comms/outbox/worker-024.jsonl are skipped and the
checkpoint is not appended twice. Every event is validated with research_map.schemas.validate_event
before writing. Worker authority: artifacts are emitted validation_status=unverified; no gate
verdict, no node status=done, no validation_status=passed.
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
TASK = "W024-AUDIT-EVIDENCE-VACUITY-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_JOINED = ";".join(CLASS_IDS)
STAMP = NOW.replace("-", "").replace(":", "")[:13]  # YYYYMMDDTHHMM
SLUG = f"w024-aev-{STAMP}"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: str) -> str:
    return f"{p}#{sha256(ROOT / p)[:12]}"


report = json.loads((ART / "report.json").read_text())
res = report["result"]
pins = report["tool_pins"]
audit_sha = pins["research_map/audit_evidence.py"]
superseded = pins["superseded_audit_revisions"]
det_sha = pins["research_map/class_separation.py"]
rep = "artifacts/worker-024/audit_evidence_vacuity/report.json"
driver = "artifacts/worker-024/audit_evidence_vacuity/drive_vacuity.py"
patch = "artifacts/worker-024/audit_evidence_vacuity/proposed_patch.diff"
readme = "artifacts/worker-024/audit_evidence_vacuity/README.md"
entry = "artifacts/worker-024/audit_evidence_vacuity/entry_hashes.json"
exith = "artifacts/worker-024/audit_evidence_vacuity/exit_hashes.json"

assert sha256(ART / "report.json") == sha256(ROOT / rep)
for p in (driver, patch, readme, entry, exith):
    assert (ROOT / p).is_file(), p

claim_statement = (
    f"Instrument claim (not a class-semantics claim): research_map/audit_evidence.py at sha256 "
    f"{audit_sha} (and at its superseded revision {superseded[0]}... , both snapshotted and "
    "replayed) fails open on absent structures. Its structural checks are presence-driven and its "
    "hard count is computed only over structures present: (C1) an empty map returns rc 0 / hard 0; "
    "(C2) a map whose gates list is emptied, with numerics_lock.required_gates cleared, returns "
    "rc 0 / hard 0; (C3) a drifted frozen artifact returns rc 0 / hard 0 once frozen_artifacts is "
    "empty; (C4) an active locked node N1 returns rc 0 / hard 0 once the numerics_lock key is "
    "removed. Positive controls pass (well-formed map rc 0 / hard 0; done-node-with-missing-"
    "artifact plus gate-pass-without-evidence rc 1 / hard 2). The single indirect guard observed "
    "is a dangling numerics_lock.required_gates reference (C2b, rc 1), bypassed by also emptying "
    "that list; the embedded class-separation token detector still fires (C6, rc 1). Separately, "
    "the tool rewrites <its ROOT>/runtime/state/artifact_hashes.json unconditionally on every "
    "non-help invocation, including failing audits; --help exposes only [-h] [--map MAP] "
    "[--write-hashes], --write-hashes is never read, and there is no --dry-run. The sentinel "
    "registry was overwritten in sandbox copies C5 and C5b. Consequence for G-AUDIT: an "
    "audit_evidence_hard: 0 quote certifies only the structures present in the map that was read; "
    "it cannot distinguish 'map clean' from 'map empty, truncated or structure-stripped'. No gate "
    "verdict is asserted."
)

events = [
    {
        "event_id": f"{SLUG}-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "artifact_type": "vacuity_audit_report",
        "path": rep,
        "sha256": sha256(ROOT / rep),
        "validation_status": "unverified",
        "summary": (
            "Fail-open matrix for research_map/audit_evidence.py at sha256 "
            f"{audit_sha[:12]} (replayed at {superseded[0]}): 12 cases, all assertions held, "
            "4 vacuous-pass structures (empty map, gates dropped, frozen dropped, lock dropped), "
            "registry sentinel overwritten in C5/C5b, embedded token detector still fires."
        ),
    },
    {
        "event_id": f"{SLUG}-artifact-driver",
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
        "summary": (
            "Builds revision-aware sandboxes (ROOT=<sandbox>), runs the 12-case matrix and the "
            "6-case patched matrix, records per-case rc/HARD/registry deltas and replays every "
            "snapshotted revision; exit 0 only if every assertion holds."
        ),
    },
    {
        "event_id": f"{SLUG}-artifact-patch",
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
            "Proposal only (not applied): non-vacuity block for empty map / missing groups, gates, "
            "frozen_artifacts, numerics_lock plus a --dry-run flag. Verified on copies: P1-P4 now "
            "exit 1, P0 still exit 0, P5 leaves the sentinel registry untouched."
        ),
    },
    {
        "event_id": f"{SLUG}-artifact-readme",
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
        "summary": "Method, per-case table at both revisions, line-anchored mechanism, patch results, reproduction, falsifier and residual risk.",
    },
    {
        "event_id": f"{SLUG}-artifact-hashpins",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "artifact_type": "entry_exit_hash_pins",
        "path": exith,
        "sha256": sha256(ROOT / exith),
        "validation_status": "unverified",
        "summary": "Entry/exit canonical hashes, drift flags and the sandbox registry-overwrite ledger; entry pins are in entry_hashes.json.",
    },
    {
        "event_id": f"{SLUG}-claim-audit-evidence-fail-open",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": claim_statement,
        "assumptions": [
            "Sandbox copies of the tool and detector are byte-identical to the snapshotted canonical bytes (asserted after copy).",
            "The canonical tool changed mid-session from bebec0843f10 to 6217729e2999; both revisions were replayed with identical per-case outcomes, and the claim binds only to those two hashes.",
            "The registry-overwrite consequence for the canonical path is inferred from the byte-identical sandbox copy plus the fixed ROOT-relative output path; it was not executed on the canonical path to avoid clobbering shared state.",
            "Applying proposed_patch.diff is an owner decision; patched verdicts come from copies under this artifact directory.",
            "C2b is recorded as a partial, indirect guard and is not counted as a vacuous case.",
        ],
        "falsifier": (
            "Re-run artifacts/worker-024/audit_evidence_vacuity/drive_vacuity.py at the audited "
            f"sha256 {audit_sha}. FALSIFIED if any of C1_empty_map, C2_gates_dropped, "
            "C3_frozen_dropped or C4_lock_dropped returns rc != 0 or hard > 0; or if C0_negative "
            "returns rc 0 / hard 0; or if the C5/C5b sentinel registry is not overwritten; or if a "
            "later revision pins a non-empty coverage assertion (minimum groups/nodes/gates/frozen/"
            "lock counts) and the re-run is clean. Any later edit of the tool or detector voids the "
            "claim for the edited bytes."
        ),
        "evidence_refs": [
            ref(rep), ref(readme), ref(patch), ref(driver), ref(entry), ref(exith),
            f"research_map/audit_evidence.py#{audit_sha[:12]}",
            f"research_map/class_separation.py#{det_sha[:12]}",
        ],
        "artifact_refs": [rep, driver, patch, readme, exith],
    },
    {
        "event_id": f"{SLUG}-status-audit-evidence-vacuity",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-024",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": CLASS_JOINED,
        "class_ids": CLASS_IDS,
        "task_id": TASK,
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W024-AUDIT-EVIDENCE-VACUITY-01 complete: artifacts on disk and hash-pinned. Result: "
            "audit_evidence.py fails open on empty/stripped maps (4/4 vacuous structures on both "
            "audited revisions) while both positive controls behave; it also rewrites the global "
            "artifact-hash registry unconditionally with no dry-run. Proposed fail-closed patch "
            "verified on copies. Worker completion claim only: no gate verdict, no node transition."
        ),
        "evidence_refs": [ref(rep), ref(patch), ref(driver)],
        "next_falsifier": (
            "Owner adds a pinned non-vacuity block and a --dry-run to research_map/audit_evidence.py, "
            "then the controller records an audit run that fails on an emptied map and does not "
            "rewrite runtime/state/artifact_hashes.json in dry-run. If the tool is rebuilt, re-run "
            "drive_vacuity.py at the new hash and expect C1-C4 to be non-vacuous."
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
for r in validated[5]["evidence_refs"]:
    p, _, prefix = r.partition("#")
    assert sha256(ROOT / p).startswith(prefix), r

checkpoint = {
    "actor": "worker-024",
    "checkpoint": 3,
    "checkpoint_id": "w24-cp03-audit-evidence-vacuity",
    "task_id": TASK,
    "node_id": "A1",
    "gate": "G-AUDIT",
    "class_ids": CLASS_IDS,
    "created_at": NOW,
    "verdict": res["verdict"],
    "audited_revision": audit_sha,
    "superseded_revision": superseded[0],
    "structural_findings_identical_across_revisions": report["structural_findings_identical_across_revisions"],
    "vacuous_pass_cases": res["vacuous_pass_cases"],
    "detection_controls_ok": res["detection_controls_ok"],
    "registry_overwritten_cases": res["registry_overwritten_cases"],
    "patch_closes_cases": res["patch_closes_cases"],
    "artifacts": {p: sha256(ROOT / p) for p in (rep, readme, patch, driver, entry, exith)},
    "events_emitted": [e["event_id"] for e in validated],
    "outbox": str(OUTBOX.relative_to(ROOT)),
    "next_falsifier": validated[6]["next_falsifier"],
    "isolation_proof": report["isolation_proof"],
    "authority_note": "worker progress record only; not a gate verdict or node completion",
    "no_canonical_input_changed": report["no_canonical_input_changed"],
}

cp_path = STATE / "w24_checkpoint_03.json"
cp_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))
ledger = STATE / "w24_checkpoints.jsonl"
seen = ledger.read_text() if ledger.exists() else ""
if checkpoint["checkpoint_id"] not in seen:
    with ledger.open("a") as f:
        f.write(json.dumps({
            "actor": "worker-024", "at": NOW, "checkpoint_id": checkpoint["checkpoint_id"],
            "path": "runtime/state/w24_checkpoint_03.json", "sha256": sha256(cp_path),
            "task_id": TASK, "node_id": "A1", "verdict": res["verdict"],
        }, sort_keys=True) + "\n")

print(json.dumps({
    "appended_events": [e["event_id"] for e in new],
    "skipped_existing": sorted(existing & {e["event_id"] for e in validated}),
    "checkpoint": "runtime/state/w24_checkpoint_03.json",
    "checkpoint_sha256": sha256(cp_path),
    "validated": len(validated),
    "hashes_reverified": True,
}, indent=1))
