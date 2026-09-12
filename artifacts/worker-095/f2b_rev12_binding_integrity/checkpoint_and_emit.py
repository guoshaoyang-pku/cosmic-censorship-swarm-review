#!/usr/bin/env python3
"""W095-F2B-BIND-INTEGRITY-02 - checkpoint + valid JSON outbox events.

Reads verdict.json, validates every event with research_map.schemas.validate_event, appends them
to comms/outbox/worker-095.jsonl, and writes the worker checkpoint pair under runtime/state/.
It never mutates the map, the canonical artifacts, or the accepted event stream (ingest is the
controller's job).

Run: python3 artifacts/worker-095/f2b_rev12_binding_integrity/checkpoint_and_emit.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
TASK_ID = "W095-F2B-BIND-INTEGRITY-02"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
GATE_ID = "G-FORM"
OUTBOX = ROOT / "comms" / "outbox" / "worker-095.jsonl"
STATE = ROOT / "runtime" / "state"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    verdict_path = HERE / "verdict.json"
    script_path = HERE / "measure_binding.py"
    readme_path = HERE / "README.md"
    verdict = json.loads(verdict_path.read_text())
    snap = json.loads((HERE / "evidence" / "raw" / "snapshot.json").read_text())
    ev = json.loads((HERE / "evidence" / "raw" / "evidence_binding.json").read_text())
    vsha = sha256(verdict_path)
    msha = sha256(script_path)
    rsha = sha256(readme_path)
    rev = verdict["reviewed_sha256"]
    frozen_rev = verdict["frozen_revision_reviewed"]
    failures = [f for f in verdict["findings"] if f["severity"] in {"blocking", "major"}]
    blocker = next((f for f in verdict["findings"] if f["id"] == "F-EVID-1"), None)
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    prefix = f"w095-f2b-rev12-{stamp}"
    created = now()

    evidence_refs = [
        f"artifacts/worker-095/f2b_rev12_binding_integrity/verdict.json#{vsha[:12]}",
        f"artifacts/worker-095/f2b_rev12_binding_integrity/measure_binding.py#{msha[:12]}",
        f"artifacts/worker-095/f2b_rev12_binding_integrity/README.md#{rsha[:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{rev[:12]}",
        f"research_map/formulation_taxonomy.yaml#{snap['f0_declared']['sha256'][:12]}",
        f"artifacts/formulation/FROZEN.json#{snap['frozen_manifest']['sha256'][:12]}",
        f"artifacts/formulation/evidence/taxonomy_consistency.json#{snap['consistency_evidence']['sha256'][:12]}",
        f"artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
        f"#{snap['consistency_evidence_pinned_copy']['sha256'][:12]}",
    ]
    next_falsifier = verdict["task_falsifier"]
    summary_core = (f"Binding/publication receipt on one class at one revision: "
                    f"{verdict['summary']['passed']}/{verdict['summary']['checks']} checks pass; "
                    f"{verdict['summary']['major']} major, {verdict['summary']['minor']} minor. "
                    f"F2b rev12 {rev[:12]} under FROZEN rev{frozen_rev}: pointer, duplicate-key and "
                    "future-stamp defects CLOSED, all FROZEN rev28 pins match measured bytes, gate "
                    "passes, class-separation clean; the revise verdict rests on the stale "
                    "consistency-evidence declaration (schema declares 675a99d0, canonical path and "
                    "freeze pin 9e335e9ba1bf) plus canonical-F0 alias hygiene. Not a content accept.")

    events = [
        {
            "event_id": f"{prefix}-task-claim",
            "event_type": "status",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE_ID,
            "status": "active",
            "hours": 0.4,
            "summary": (f"No assignment card exists in comms/inbox for worker-095 (fleet "
                        f"2026-09-12T00:30:49). Taking ONE bounded class-bound task, {TASK_ID}: "
                        f"re-measure binding/publication integrity of F2b {CLASS_ID} at canonical "
                        f"rev12 {rev[:12]} / FROZEN rev{frozen_rev}, testing the explicit "
                        "next-falsifier of W095-F2B-BIND-INTEGRITY-01 (rev11). Does not duplicate the "
                        "F2b semantic reviews or the workers-043/086/092 rev12/F0 adjudication "
                        "artifacts. Deliverable: artifacts/worker-095/f2b_rev12_binding_integrity/."),
            "evidence_refs": evidence_refs,
            "next_falsifier": next_falsifier,
        },
        {
            "event_id": f"{prefix}-artifact-verdict",
            "event_type": "artifact",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "artifact_type": "class_binding_integrity_verdict",
            "path": "artifacts/worker-095/f2b_rev12_binding_integrity/verdict.json",
            "sha256": vsha,
            "validation_status": "unverified",
            "companion_script": {
                "path": "artifacts/worker-095/f2b_rev12_binding_integrity/measure_binding.py",
                "sha256": msha},
            "reviewed_sha256": rev,
            "reviewed_revision": verdict.get("reviewed_revision"),
            "frozen_revision_reviewed": frozen_rev,
        },
        {
            "event_id": f"{prefix}-review-binding",
            "event_type": "review",
            "created_at": created,
            "actor": "worker-095",
            "reviewer": "worker-095",
            "target_id": NODE_ID,
            "target_path": "schemas/af_scc_c0_vacuum.yaml",
            "reviewed_sha256": rev,
            "class_id": CLASS_ID,
            "verdict": verdict["verdict"],
            "score": verdict["score_0_5"],
            "counts_as_full_schema_verdict": False,
            "hard_failures": [f["id"] for f in failures],
            "findings": [{"id": f["id"], "severity": f["severity"], "finding": f["finding"][:400],
                          "falsifier": f["falsifier"][:300]} for f in verdict["findings"]],
            "summary": summary_core,
            "evidence_refs": evidence_refs,
        },
        {
            "event_id": f"{prefix}-blocker-evidence",
            "event_type": "blocker",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE_ID,
            "description": (f"G-FORM binding blocker for F2b {CLASS_ID} at rev12 {rev[:12]} / "
                            f"FROZEN rev{frozen_rev}: F2b.f0_binding.consistency_evidence_sha256 "
                            f"declares {str(ev['declared_sha256'])[:12]} (enriched rev12 run, "
                            "coherent, present at the worker-086 pinned copy), but the canonical "
                            f"path measures {str(ev['measured_canonical_path_sha256'])[:12]} and the "
                            f"freeze pins {str(ev['frozen_pin_sha256'])[:12]}. All other rev28 pins "
                            "match measured bytes, so the inconsistency is the stale schema "
                            "declaration, not a missing artifact. Root-cause hazard: "
                            "check_taxonomy_consistency.py:80 rewrites the canonical evidence path "
                            "unconditionally with a summary format lacking the hash fields."),
            "needed_to_unblock": ("One of: (a) restore the declared enriched bytes at "
                                  "artifacts/formulation/evidence/taxonomy_consistency.json and "
                                  "re-freeze pinning them; or (b) refresh the three schemas' "
                                  "f0_binding.consistency_evidence_sha256 to the frozen canonical "
                                  "bytes and re-freeze + re-review. Either path changes schema bytes "
                                  "and requires a new freeze revision; additionally guard the "
                                  "checker's unconditional write (line 80) behind an explicit "
                                  "output flag so a verification run cannot clobber a frozen "
                                  "artifact."),
            "evidence_refs": evidence_refs,
        },
        {
            "event_id": f"{prefix}-task-receipt-complete",
            "event_type": "status",
            "created_at": created,
            "actor": "worker-095",
            "node_id": NODE_ID,
            "class_id": CLASS_ID,
            "gate": GATE_ID,
            "status": "active",
            "hours": 0.5,
            "summary": (f"{TASK_ID} worker-level receipt complete; node status deliberately "
                        "unchanged (worker events cannot set status=done, validation_status=passed, "
                        f"or a gate verdict). verdict={verdict['verdict']} at rev12 {rev[:12]} / "
                        f"FROZEN rev{frozen_rev}; reproducible probe + 14 raw evidence files + "
                        "checkpoint written. counts_as_full_schema_verdict=false."),
            "evidence_refs": evidence_refs,
            "next_falsifier": next_falsifier,
        },
    ]

    # validate before writing: invalid JSON never reaches the outbox
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line)["event_id"])
                except (ValueError, KeyError):
                    pass
    new_events = [e for e in events if e["event_id"] not in existing]
    for e in new_events:
        validate_event(e)
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a") as f:
        for e in new_events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    # checkpoint pair
    STATE.mkdir(parents=True, exist_ok=True)
    ckpt = {
        "worker": "worker-095",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE_ID,
        "verdict": verdict["verdict"],
        "score_0_5": verdict["score_0_5"],
        "reviewed_sha256": rev,
        "reviewed_revision": verdict.get("reviewed_revision"),
        "frozen_revision_reviewed": frozen_rev,
        "artifact": "artifacts/worker-095/f2b_rev12_binding_integrity/verdict.json",
        "artifact_sha256": vsha,
        "probe": {"path": "artifacts/worker-095/f2b_rev12_binding_integrity/measure_binding.py",
                  "sha256": msha},
        "evidence_dir": "artifacts/worker-095/f2b_rev12_binding_integrity/evidence/raw/",
        "counts_as_full_schema_verdict": False,
        "checkpoint_at": created,
        "next_falsifier": next_falsifier,
    }
    ckpt_path = STATE / f"w095_f2b_rev12_checkpoint_{stamp}.json"
    ckpt_path.write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
    (STATE / "w095_latest_checkpoint.json").write_text(json.dumps({
        "worker": "worker-095", "task_id": TASK_ID, "path": str(ckpt_path.relative_to(ROOT)),
        "verdict": verdict["verdict"], "reviewed_sha256": rev, "checkpoint_at": created,
        "next_falsifier": next_falsifier,
    }, indent=2, sort_keys=True) + "\n")
    with (STATE / "w095_f2b_rev12_checkpoints.jsonl").open("a") as f:
        f.write(json.dumps(ckpt, sort_keys=True) + "\n")

    print(json.dumps({
        "events_appended": [e["event_id"] for e in new_events],
        "events_skipped_duplicate": [e["event_id"] for e in events if e["event_id"] in existing],
        "checkpoint": str(ckpt_path.relative_to(ROOT)),
        "verdict_sha256": vsha,
        "probe_sha256": msha,
        "readme_sha256": rsha,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
